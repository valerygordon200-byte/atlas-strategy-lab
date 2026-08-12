# SECRETS AUDIT — 2026-08-12

Status: audit complete. One live-credential finding, already mid-remediation (Phase 0.1 token rotation).

## Scope
- Repos: `atlas-strategy-lab`, `dourmouse` (working trees + full git history)
- Patterns: `ghp_`/`gho_` GitHub tokens, `sk-` OpenAI, `nvapi-` NVIDIA, `AKIA` AWS, `APCA-` Alpaca, `BEGIN *PRIVATE KEY` blocks, `TOKEN=`, `password=`, `api_key=`/`secret=` assignments

## Findings

### 1. Live relay token in atlas-strategy-lab HISTORY (12 occurrences) — ROTATING
The old relay token `jXVXaHAeG721UkhMYRSq3rRXAK-iBIAY` is committed in
atlas-strategy-lab history (introduced early, scrubbed from the working
tree in commit 40078b5-era; the scrub also fixed `gateway_watch.py` +
`start_bridge_detached.py` to read the token from config instead of
hardcoding).

- **Severity:** MEDIUM (post-rotation: resolved). The token is the relay
  auth for the agent feed (loopback/Tailscale peers only), not a bank or
  cloud credential.
- **Status:** the replacement token (`ccVo_iuClxf6t-...`) is generated and
  delivered to the laptop (relay id 1143); the server-side flip happens on
  the laptop's ACK. After the flip, the old token is dead and its presence
  in history is harmless (rotated = resolved).
- **Note:** the new token was handed over via a relay message, which also
  transits the unauthenticated loopback chat_feed (`:8788/feed`). Exposure
  surface is local-only (127.0.0.1). Acceptable for the handoff; the old
  token stays live until the coordinated flip.

### 2. Working trees — CLEAN
No live credential patterns in tracked files in either repo. All
`TOKEN=`/key reads go through gitignored config (`relay_config.txt`,
`.env`, env vars). Template placeholders confirmed:
- `dourmouse/hub.html:145` `__ENGINE_TOKEN__` (substituted at serve time)
- `relay/chat.html:46` `__SEND_TOKEN__` (same)
- `DOURMOUSE_ACCESS_TOKEN=CHANGE-ME...` (example config)

### 3. Test fixtures — FAKE, not live
`nvapi-0123456789abcdef`, `sk-abcdefghijklmnop`, `AKIAIOSFODNN7EXAMPLE`,
`ghp_abcdefghijklmnopqrstuvwxyz`, `nvapi-leakedsecretvalue12345` in
`dourmouse/tests/*` are governance/redaction test vectors.

### 4. Ignore coverage — CORRECT
- `atlas-strategy-lab`: `relay/relay_config.txt` and `.env` gitignored;
  no `.env` or `relay_config.txt` tracked.
- `dourmouse`: `.env`, `.venv` gitignored; no `.env` tracked.

## Not yet covered (out of scope this pass)
- `.freebuff/github_token.txt` on the desktop is a **dead token** (401 on
  `/user`) — harmless but should be deleted or replaced with a live one if
  the GitHub push needs to move.
- Local non-repo files (`relay/inbox_desktop-atlas.txt` 32MB of relay
  traffic) contain both tokens in transit. Local disk only; cleaned when
  the relay archive rotates.
- Laptop-side audit (Mac): same scan should be run there for the Mac's own
  env/keys (`nvapi-` etc. live in the laptop's `.env`). Handed to the
  laptop as a follow-up.

## Verdict
**Zero live secrets in either working tree. One dead-after-rotation token
in atlas history. The single live item (relay token) is already in the
coordinated rotation (Phase 0.1) and closes on the laptop's ACK.**
