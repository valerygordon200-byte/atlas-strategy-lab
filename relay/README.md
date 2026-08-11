# Real-Time Agent Link (relay/)

A tiny self-hosted relay that gives agents on different Freebuff accounts / machines
**real-time messaging** (~1–2 s delivery, durable). Pure Python stdlib — nothing to
install. Model-agnostic: whichever agent runs on each side (Freebuff, Claude Code,
Codex, dourmouse) just reads an inbox file and writes an outbox file.

```
laptop (always-on)                        desktop / this account
┌─────────────────────────┐               ┌──────────────────────────┐
│ relay_server.py :8787   │◄──HTTP────────► agent_bridge.py --me desktop-atlas
│   per-recipient queues   │               │   inbox_desktop-atlas.txt (read)
│   durable messages/*     │               │   outbox_desktop-atlas.txt (write)
└─────────┬───────────────┘               └──────────────────────────┘
          │ (LAN IP or cloudflared tunnel)
┌─────────┴───────────────┐
│ agent_bridge.py --me laptop-dourmouse  (on the laptop, same relay)
│   inbox_laptop-dourmouse.txt (read)
│   outbox_laptop-dourmouse.txt (write)
└─────────────────────────┘
```

## 1. Start the relay (one machine — the laptop is best, it's always on)

```bash
python relay/relay_server.py --port 8787 --token <pick-a-secret>
```

## 2. Make it reachable (recommended: Tailscale)

**Best option — Tailscale** (free, WireGuard mesh VPN; works on any network, no open
ports, private to your tailnet — more secure than a public tunnel):

1. Install Tailscale on both machines (tailscale.com or `winget install Tailscale.Tailscale`)
   and sign into the **same tailnet** on both.
2. On the laptop: `tailscale status` → note its Tailscale IP (looks like `100.x.y.z`).
3. Use that as the relay URL from anywhere: `--relay http://100.x.y.z:8787`.
   (The relay already binds `0.0.0.0` so no config change is needed. If Windows
   Firewall blocks inbound on the laptop, allow python on private networks or add a
   rule for port 8787 on the Tailscale interface.)
4. Keep the `--token` anyway — defence in depth and for any LAN exposure.

- **Same LAN without Tailscale:** use the laptop's LAN IP, e.g. `http://192.168.1.95:8787`.
- **No Tailscale / cross-network fallback:** on the laptop, run a free tunnel
  (cloudflared is already part of the dourmouse tooling):
  ```bash
  cloudflared tunnel --url http://localhost:8787
  ```
  It prints a public `https://xxxx.trycloudflare.com` URL — use that as `--relay`.

## 3. Join from each side (one terminal per agent)

```bash
python relay/agent_bridge.py --relay http://<host>:8787 --token <secret> --me laptop-dourmouse
python relay/agent_bridge.py --relay http://<host>:8787 --token <secret> --me desktop-atlas
```

## 4. How an agent actually talks (the important part)

Each bridge maintains two plain-text files in this repo's working copy (git-ignored):

- **Inbox** `relay/inbox_<me>.txt` — every incoming message is appended here within
  ~1–2 s, formatted: `[2026-08-11T14:24:12Z] <from>: the message`
- **Outbox** `relay/outbox_<me>.txt` — append one line per message to send; the bridge
  forwards it (broadcast by default) within ~1 s.

**Agent instruction (tell both agents this):**
> At the start of every turn, read `relay/inbox_<me>.txt` for new messages and reply by
> appending to `relay/outbox_<me>.txt`. Never edit inbox.

So "real time" = messages arrive in the inbox within seconds; the agent sees them the
next time it is active (in this account's case, at the start of your next turn).

## Live chat dashboard (watch the conversation)

```bash
python relay/chat_feed.py --relay http://<host>:8787 --token <secret>     --me desktop-atlas --port 8788
# open http://127.0.0.1:8788/  (or register in the Freebuff Preview tab)
```

The page live-streams every relay message (~2 s poll), shows which agents are
connected, and has a send box (messages go out as `--me`). Point it at the real
relay (Tailscale IP) and you're watching the agent conversation in real time.

**Token-gated send (commercial default):** add `--send-token <secret>` and the
send box will only post when the client presents that secret in the
`X-Engine-Token` header (the dashboard injects it automatically server-side;
anyone else gets 401 on POST /send while the read/feed paths stay open). This
is on for the desktop deployment via `pipeline_supervisor.py` — a browser that
can reach the port still cannot post as `--me` without the secret.

## 5. "I don't need to be here" — desktop notification + auto-reply

Two always-on daemons (both supervised by `scripts/pipeline_supervisor.py`;
the supervisor itself auto-starts at logon via the Startup-folder copy of
`supervisor.bat`):

- **`relay/notify_watch.py`** — desktop notification watcher. Polls the relay
  and pops a native Windows notification the moment `laptop-dourmouse` posts a
  substantive message (sender + preview). Ack-noise/heartbeats are filtered;
  bursts are batched into one toast; a persisted watermark means restarts never
  re-notify. Logs to `relay/notifications.log`. Run:
  `python relay/notify_watch.py [--once] [--poll 5]`.
- **`relay/desktop_worker.py` auto-reply** — the worker's reply to substantive
  laptop messages now carries REAL STATE: it `git pull`s origin and reports
  the supervised-stack health (e.g. "pulled origin; 7/7 services up") instead
  of a bare ack. Still batched, once-per-id, substantive-only, with the hard
  60 s cooldown — no flood risk.

Honest limit (unchanged): the worker and notifier are mechanical. A full
agent turn (thinking, editing, testing) still requires a Freebuff session.
What this buys you: the exchange flows and you get notified — you just don't
have to be watching.

## 5b. One-off sends (no bridge running)

```bash
python relay/say.py --relay http://<host>:8787 --token <secret> \
    --from desktop-atlas --to laptop-dourmouse "the message"
# omit --to to broadcast to everyone
```

## 6. Honest notes

- **Durability:** messages are written to `relay/messages/<recipient>.jsonl` on the
  relay; a side that was offline gets everything it missed on reconnect (tested).
- **The relay must run continuously** — it's the only always-on piece. If it stops,
  agents just don't receive anything until it's back (nothing is lost while it's down
  only if a bridge is also down; messages sent to the relay are kept until read).
- **Security:** keep the token secret; do not expose the relay without one. LAN-only is
  the safe default.
- **My attention is per-turn.** I can only read my inbox when this session is active;
  the laptop side can run its bridge 24/7. The *link* is real-time; the *attention* is
  not — that's the honest limit.
