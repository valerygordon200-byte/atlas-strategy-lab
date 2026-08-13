# Dell Inspiron 7586 — dedicated local server / compute node (third node)

Third machine in the DOURMOUSE relay. Pair with `docs/DEPLOYMENT.md`
(fresh-machine setup), `docs/OPERATIONS_RUNBOOK.md` (day-to-day), and
`relay/LAPTOP_SETUP.md` (relay join).

## Hardware verdict (be honest with yourself)

| Spec | Value | Consequence |
|---|---|---|
| CPU | Intel Core i5-8265U (8th gen, 4C/8T, 1.6–3.9 GHz) | Fine for light CPU inference + all server roles |
| RAM | **8 GB** | **The binding constraint.** OS + stack leaves ~4–5 GB free |
| Storage | 224 GB usable SSD | Plenty |
| GPU | None (iGPU only) | **No training, no GPU inference.** CPU-only |

**What the Dell CAN do (its real role):**
- **Always-on relay host** — run `relay_server.py` so the relay no longer depends
  on the desktop being up. This is the single highest-value job it can take.
- **Always-on worker + chat feed + supervisor** — the same laptop-side stack the
  Mac runs, running 24/7.
- **Light Ollama compute node** — serve `qwen3:4b` (2.5 GB) and
  `nomic-embed-text` (0.27 GB) over the tailnet. ~10–15 tok/s on this CPU:
  fine for batch/async jobs and embeddings, not for interactive chat.
- **Scheduled jobs** — data pulls, monthly builds, monitoring, running 24/7.

**What the Dell CANNOT do (kill these expectations now):**
- ❌ Train or fine-tune models (no GPU, 8 GB RAM). The 3B action-model training
  stays on the Mac/desktop/cloud.
- ❌ Serve `dourmouse-finetuned` (7.6B params, 4.71 GB) with the rest of the
  stack on 8 GB — it will swap. Keep it on the Mac. The Dell's ceiling is
  4B-class models.

## Chosen topology (recommended)

```
DESKTOP (Windows, 100.98.97.23)          MACBOOK (100.84.156.49)
├─ engine_api.py :8790                    ├─ bridge + worker + feed :8789
├─ supervisor :8792                       ├─ Ollama: dourmouse-finetuned (prod)
└─ data registry                          └─ app :8765, hub :8791

DELL (always-on, new tailnet IP)
├─ relay_server.py :8787   ← relay host moves here (or mirrors desktop's)
├─ bridge + worker + feed :8789
└─ Ollama: qwen3:4b + nomic-embed-text (tailnet compute node)
```

The Dell being the relay host means a desktop reboot no longer takes the whole
tailnet's message channel down. Desktop keeps the engine + data; Mac keeps the
production model + UI; Dell keeps the fabric alive + does light compute.

## Step-by-step (Windows 10/11 — primary target)

### 1. Preflight
```powershell
# PowerShell (admin)
winget install -e --id Git.Git
winget install -e --id Python.Python.3.12
winget install -e --id Ollama.Ollama
winget install -e --id Tailscale.Tailscale
```
Tailscale: sign in to the same account as the other nodes, then verify:
```powershell
tailscale status   # should show desktop 100.98.97.23 + macbook 100.84.156.49
```

### 2. Repo + deps (use the existing one-command Windows setup)
```powershell
git clone https://github.com/valerygordon200-byte/atlas-strategy-lab.git
cd atlas-strategy-lab
setup.bat
```
`setup.bat` installs deps, creates `relay/relay_config.txt` from the example,
and runs the smoke test as the done-gate.

### 3. Relay config (edit `relay/relay_config.txt`)
```
RELAY_URL=http://127.0.0.1:8787   # if this Dell hosts the relay; else desktop IP
TOKEN=<same-shared-token-as-the-other-nodes>
ME=dell-node
DASH_PORT=8789
```

### 4. Host the relay (if elected)
```powershell
python relay\relay_server.py --port 8787 --token <TOKEN>
```
Message store is `relay/messages/` (durable). All other nodes point their
`RELAY_URL` at this Dell's tailnet IP. Update desktop's + Mac's configs, then
restart their bridges. **Coordinate this flip with desktop** — do not pull the
rug on the live relay (C4/C5 supervise it).

### 5. Compute node (Ollama over tailnet)
```powershell
ollama pull qwen3:4b
ollama pull nomic-embed-text
# serve on all interfaces so Mac/desktop can reach it
setx OLLAMA_HOST "0.0.0.0:11434"
# restart Ollama (taskbar icon → Quit, then relaunch)
```
On the Mac, point one consumer at it:
```
OLLAMA_HOST=http://<dell-tailnet-ip>:11434 python dourmouse/webui.py
```
or use it for the fast/embedding lane only.

### 6. Autostart (Windows)
```powershell
# Task Scheduler: run at logon, restart on failure
schtasks /Create /TN "DOURMOUSE\relay"  /TR "python relay\relay_server.py --port 8787 --token <TOKEN>" /SC ONLOGON /RL HIGHEST /F
schtasks /Create /TN "DOURMOUSE\bridge" /TR "python relay\agent_bridge.py --relay http://127.0.0.1:8787 --token <TOKEN> --me dell-node" /SC ONLOGON /RL HIGHEST /F
schtasks /Create /TN "DOURMOUSE\worker" /TR "python relay\autonomous_worker.py" /SC ONLOGON /RL HIGHEST /F
```
(Or set the machine to auto-login + run these at startup. For a headless server,
consider enabling auto-logon via `netplwiz` or a scheduled task at SYSTEM boot.)

### 7. Verify
```powershell
python scripts\health_check.py --base C:\forex-data   # smoke gate
curl http://127.0.0.1:8787/ping                        # relay {"ok": true}
curl -o NUL -w "%{http_code}" http://127.0.0.1:8789/   # feed 200
```

## Open questions for desktop (post to relay before flipping the relay host)
1. Should the Dell take over relay hosting, or mirror it? (Recommendation: take
   over — desktop reboots are the main outage source; relay server is stdlib and
   durable.)
2. Confirm the shared relay token is the current one — the Mac's two tokens were
   403-blocked earlier; ensure `relay_config.txt` on all three nodes agree.
3. Any engine/data duties the Dell should mirror (it has no `E:\forex-data`;
   engine stays desktop-only unless we ship a read-only copy).
