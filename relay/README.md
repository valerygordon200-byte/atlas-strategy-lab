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

## 2. Make it reachable

- **Same LAN:** use the laptop's IP, e.g. `http://192.168.1.95:8787`.
- **Different networks:** on the laptop, run a free tunnel (cloudflared is already part
  of the dourmouse tooling):
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

## 5. One-off sends (no bridge running)

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
