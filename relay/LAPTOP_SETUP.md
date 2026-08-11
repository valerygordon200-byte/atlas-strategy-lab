# Laptop Setup — join the agent relay (macOS / Windows)

Your tailnet is already live: this desktop is `100.98.97.23`, your MacBook
(`adits-macbook-air`) is `100.84.156.49`. The relay currently runs on the desktop.
The laptop only needs to run the bridge (and optionally its own chat dashboard).

## 1. One time

```bash
git clone https://github.com/valerygordon200-byte/atlas-strategy-lab.git
cd atlas-strategy-lab
cp relay/relay_config.example.txt relay/relay_config.txt
```

Edit `relay/relay_config.txt`:

```
RELAY_URL=http://100.98.97.23:8787
TOKEN=jXVXaHAeG721UkhMYRSq3rRXAK-iBIAY
ME=laptop-dourmouse
DASH_PORT=8788
```

(`relay_config.txt` is git-ignored — the token never gets committed.)

## 2. Run the bridge (this is the important one)

```bash
cd atlas-strategy-lab
python3 relay/agent_bridge.py --relay http://100.98.97.23:8787 \
    --token jXVXaHAeG721UkhMYRSq3rRXAK-iBIAY --me laptop-dourmouse
```

Keep this running in a terminal (24/7 if possible). That's all the laptop needs to
talk: messages arrive in `relay/inbox_laptop-dourmouse.txt` within ~2 s; append a
line to `relay/outbox_laptop-dourmouse.txt` to reply.

## 3. Optional: the laptop's own chat dashboard

```bash
python3 relay/chat_feed.py --relay http://100.98.97.23:8787 \
    --token jXVXaHAeG721UkhMYRSq3rRXAK-iBIAY --me laptop-dourmouse --port 8788
# open http://127.0.0.1:8788/ on the laptop
```

## 4. Agent instruction (paste into the laptop's Freebuff/agent session)

> Use the coordination protocol in this repo. At the start of every turn read
> `relay/inbox_laptop-dourmouse.txt` for new messages and reply by appending to
> `relay/outbox_laptop-dourmouse.txt`. Keep the task board (`python3 scripts/coord.py
> list`) in sync: claim TODO tasks with `--me laptop-dourmouse`, mark DONE with a
> one-line result, push artifacts to the repo.

## Notes
- Python 3 only, zero dependencies (stdlib).
- If the desktop relay is ever down, messages sent to it are kept on the desktop
  relay's disk and delivered when it's back.
- Prefer the relay host to be an always-on machine. If the MacBook is more reliable
  than the desktop, run `relay/start_relay.bat` equivalent there instead:
  `python3 relay/relay_server.py --port 8787 --token <same-token>` and change
  RELAY_URL to the MacBook's tailnet IP on the desktop's config.
