# PACKAGING AUDIT — 2026-08-12

Status: audit complete. One live-secret leak found and fixed; one data
shipping issue documented with a strip-before-sharing rule.

## Findings

### 1. [FIXED] dourmouse/build_dist.sh copied the WHOLE repo dir wholesale
`cp -R "$ROOT/dourmouse" "$STAGE/dourmouse"` copied the entire repository
directory into the dist — including `.env` (live keys), `.venv` (the
whole virtualenv — the source of the laptop's 8.4GB dist), `workspace/`
(user data, schedules, memory DBs), and `.git/`. The cleanup lines only
removed tests/`__pycache__`/`local_secrets.py`, so everything else shipped.

**Fix:** explicit include-list (`dourmouse/dourmouse` package + `ui` +
launchers + docs + requirements only) — an include-list cannot leak by
accident. Added a **fail-loud leak gate** at the end of the build: any
`.env`, `workspace/`, `.venv`, `.git`, `*.db`, `schedules.jsonl`,
`local_secrets.py`, or `relay_config.txt` inside the staged dist aborts
the build with `RELEASE BLOCKED`.

### 2. [FIXED] FULL_PACKAGE/forex-engine/dourmouse/.env shipped a live secret
The shareable zero-setup package contained the builder's real `.env`
(57 lines) including `TV_WEBHOOK_SECRET` — the only true credential in
it; the rest were machine-specific absolute paths (`ATLAS_REPO_PATH=E:/...`
etc.) that would break on any other device anyway, so the file provided
no real zero-setup value.

**Fix:** replaced with the `.env.example` template. Original preserved
locally at `dourmouse/.env.bak-package-audit` (gitignored) so
`TV_WEBHOOK_SECRET`'s value can be recovered; rotate the secret if the
zip ever left this machine.

### 3. [DOCUMENTED] FULL_PACKAGE contains workspace/ + memory DBs (by user request)
`FULL_PACKAGE/forex-engine/dourmouse/workspace/` (incl.
`memory/atlas_memory.db` — the 2,757-fact memory store) and
`atlas-probabilistic-visual-intelligence/data/atlas_pvi.db` are inside
the package. These were included on the user's explicit "everything, no
setup required" instruction for their own devices — NOT deleted.

**Rule for sharing:** if this zip is ever given to anyone else, strip
before zipping:
```
rm -rf FULL_PACKAGE/forex-engine/dourmouse/workspace \
       FULL_PACKAGE/forex-engine/atlas-probabilistic-visual-intelligence/data
```
Personal memory facts must never leave the owner's devices.

### 4. Clean
- `SETUP_NEW.bat` / `START_HERE.bat`: no stale `E:\` or
  `C:\Users\ankit` path references.
- No `local_secrets.py`, `relay_config.txt`, `schedules.jsonl`,
  `gh_cred*`, or `github_token*` anywhere in the package.
- `start.sh` / `start.command` reference `.env` / `workspace` at runtime
  (correct — those are per-device), and `build_dist.sh` no longer ships
  them.

## The rule going forward (Phase 0.4 / 1.1)
Every packaging lane — `build_dist.sh`, the laptop's dist builder, the
FULL_PACKAGE zip, and any future installer — must use an explicit
include-list and run the leak gate. A dist that contains `.env`,
`workspace/`, `*.db`, or `.venv` is a release blocker by definition.
