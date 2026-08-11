# Deployment — ATLAS + DOURMOUSE commercial stack (C6)

How to bring the whole stack up on a fresh machine, in either role.

## The stack (five processes, two roles)

```
DATA HOST (desktop)                    CLIENT (laptop)
├─ relay_server.py :8787  ◄───────────►├─ agent_bridge.py --me laptop-dourmouse
├─ engine_api.py   :8790               ├─ chat_feed.py :8789 (dashboard)
├─ data_registry (E:/forex-data)       ├─ autonomous_worker.py (inbox/board loop)
└─ supervisor (C5, keeps all alive)    └─ supervisor (restarts worker)
```

- **Relay** (one per tailnet, on the always-on machine): durable per-recipient
  message queues; bridges poll it.
- **Engine** (data host): HTTP over the registry — `/api/keys`, `/api/data/{key}`,
  `/api/backtest`. No data ownership needed on the client.
- **Dashboard** (any machine): live feed + send box; send is token-gated.
- **Workers**: monitor the inbox + board, reply, claim/execute board tasks.

## Prerequisites

- Python 3 (stdlib only — no pip installs needed).
- Tailscale on both machines, same tailnet (`tailscale status` shows both).
- Git clone: `git clone https://github.com/valerygordon200-byte/atlas-strategy-lab.git`
- The shared token in `relay/relay_config.txt` (git-ignored, never committed).

## One-command setup (fresh machine)

```bash
cd atlas-strategy-lab
cp relay/relay_config.example.txt relay/relay_config.txt   # edit URLs/token/ME
python3 scripts/health_check.py                            # verifies everything
```

`health_check.py` prints per-component OK/FAIL (repo, registry, bookshelf,
regressions, relay, engine, gold data) and exits non-zero on breakage —
that's the C7 release gate's first stop.

## Role: data host (desktop)

1. Relay: `python3 relay/relay_server.py --port 8787 --token <token>`
2. Engine: `python3 scripts/engine_api.py --port 8790` (after `data_registry.py`
   has built `registry.json` from the data drive).
3. Bridge: `python3 relay/agent_bridge.py --relay http://<tailscale-ip>:8787 \
   --token <token> --me desktop-atlas`
4. Dashboard: `python3 relay/chat_feed.py --relay ... --token ... --me desktop-atlas \
   --port 8788 --dash-token <secret>`
5. Supervisor (C5): keeps collector/pipeline/ledger/worker/relay/feed alive.

## Role: client (laptop)

1. Bridge: `python3 relay/agent_bridge.py --relay http://100.98.97.23:8787 \
   --token <token> --me laptop-dourmouse`
2. Dashboard: `python3 relay/chat_feed.py --relay ... --token ... --me laptop-dourmouse \
   --port 8789 --dash-token <secret>`
3. Worker: `python3 relay/autonomous_worker.py` (keepalive via
   `relay/supervise_worker.py`).

## Two-machine protocol

- **Relay = conversation**, `coordination/tasks.json` = work, repo = artifacts.
- Claim with `python3 scripts/coord.py claim --me <me> <id>`; commit+push the
  claim immediately (claim lock). `done` with a one-line result + artifact paths.
- Immediate-reply rule enforced mechanically; workers NEVER ack ack-noise
  (that was the ping-pong incident — see relay/autonomous_worker.py policy).

## Adding data / strategies

- Data: put it under the data host's store, add a loader to `data_registry.py`,
  regenerate `registry.json`, run the quality gates.
- Strategy: write the battery script in `scripts/`, run it through the
  4-stage validation framework, keep the verdict + stats in `reports/`.

## Going live

- Paper-first: every strategy lives on the forward ledger / demo fills before
  live capital; live execution only via the audited connector (C3). No
  connector is live today — see `reports/C3_EXECUTION_AUDIT.md`.
