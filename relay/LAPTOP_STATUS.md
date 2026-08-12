# Laptop relay status — 2026-08-12 12:55Z

Read by the desktop worker on next pull. **No secrets in this file.**

## State

- Token rotation (11:08Z) was verified and closed; laptop daemons run on the
  NEW token. **As of 12:46Z the relay returns 403 for BOTH the old and the new
  token from the laptop** — the relay appears to have rotated (or restarted
  with) a third token. Laptop is locked out of /all and /recv and cannot post
  until it holds the current token. Bridge + feed are alive and retrying; the
  instant the relay accepts the NEW token `ccVo_...`, the laptop reconnects
  automatically. If desktop rotated again, please post the current token (or
  point the relay back at `ccVo_...`) — everything else is in place.

## Commercial push — laptop next steps (the plan desktop asked for)

Desktop lane (features, packaging audit, legal, CI draft, bundle) is received
and acknowledged — thank you, the 11:17Z wrap was fully read. Laptop lane,
in priority order:

1. **Dist leak gate (hard release blocker).** Laptop's `build_dist.sh` still
   ships `workspace/` wholesale (lines 115-118) — exactly the leak the audit
   banned. Laptop will apply the same include-list + fail-loud leak gate as
   desktop's `d7a2d41` (exclude workspace/, .env*, relay_config.txt,
   *_secrets*, *.db, tools/ unless whitelisted).
2. **Model-regression gate (hard release blocker).** Adding the locked-model
   strict-JSON gate (<90% on the 13-task suite = release blocker) to
   `golden_regressions.py` alongside the finance checks, per the 1155
   acceptance condition.
3. **v5.20 checkpoint (human-gated).** The laptop tree's ~180 uncommitted
   files still await the human's go-ahead. This unblocks the bundle merge →
   dourmouse origin push (arms CI) → pastel WCAG AA pass. Desktop's refreshed
   bundle (head 31a217d, atlas 32f6f1d) is noted; laptop will re-extract it
   at merge time — the on-disk bundle is currently stale at 4a8c79e.
4. **3B action-model counter (still open).** Desktop's position on verdict
   1168 (train the 3B pivot action model on GPU, keep 7B as dispatcher) is
   awaited; laptop has the v2 dataset (877 rows) + GPU config ready.

## Still open

- Desktop's counter on the 3B action-model plan (verdict 1168).
- The bundle merge / Windows-port patch — blocked on the human's v5.20
  checkpoint decision (laptop tree's uncommitted files).
- Relay token state (see above) — laptop currently cannot post.
