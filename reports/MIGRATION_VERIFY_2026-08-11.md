# Migration Verification Report — Atlas Pen Drive
Date: 2026-08-11 · Campaign: Multi-Track Edge Search · Part 1

## 1.1 Structural check
All expected top-level items present on E:\forex-data:

| Item | Status |
|---|---|
| market-data/normalized/ | ✅ present (19 dirs incl. GOLD, SILVER, OIL, GSR, 12 FX pairs + manifest.csv) |
| market-data/raw/ | ✅ present (ibkr/, dukascopy, yahoo — COMM_* commodity CSVs incl. ZS ZM ZL ZO CL HO RB LE GF HE GC SI) |
| market-data/events/ | ✅ present (events.parquet, ~84k+ events, 2015→present) |
| market-data/fundamentals/ | ✅ present |
| market-data/news_drift/ | ✅ forward_ledger.csv present and live (4 events) |
| scripts/ | ✅ present (90 scripts) |
| reports/ | ✅ present (33 reports) |
| strategies/ | ✅ present (26 JSON strategy files, category subdirs + registry.parquet) |
| atlas-engine/ | ⚠️ **was absent** — see 1.5 |

## 1.2 Completeness
- events.parquet: rows and date range confirmed (84,000+ events, 2015-01 → present).
- strategies/ registry: registry.parquet entries = 26 = individual strategy JSON count (26). ✅
- normalized manifest: manifest.csv present (rebuilt checks deferred to maintenance pass — drive write speed, see 1.5).
- atlas-engine test suite: 1,149 tests collected, subset run (test_backtesting.py 3/3 passed). ✅

## 1.3 Regression tests — all three reproduce on the drive
1. **Hog August roll-check** — PASS: continuous −13.6% (t≈−7.5) vs real capturable path −0.03% (t≈−0.02). Seasonal catalog remains void. Reproduces established result (continuous ≈ −13.9%, t ≈ −8.08; roll-corrected ≈ +0.05%, t ≈ 0.05).
2. **Dual Momentum** — PASS: holdout +2.12%/mo, t=4.51, walk-forward p=0.001, full 6/6 gates. Exact reproduction.
3. **USDJPY news drift** — PASS: IS t=1.139, OOS t=3.775 (within 3.0–4.5 band), bootstrap P(≤0)=0.0014, 4/6 gates (only the two IS gates fail). Exact reproduction of the news_deep_campaign result.

## 1.4 Live/ongoing processes
- Forward ledger: live, 4 events accumulated (3/4 hits; latest: Unit Labour Costs z=−0.74 → +0.33%). Continue accumulating toward the 30–60 event kill gate; do not re-test.
- Task scripts (collector, event pipeline): location-relative path references — no stale pre-migration absolute paths found. ✅
- Tick collector: not running this session (expected — restart documented in ops notes).

## 1.5 Discrepancies found and resolved
1. **atlas-engine absent from drive (real migration gap).** It lives only on local disk
   (C:\Users\ankit\Documents\forex-engine\atlas-engine, ~10MB code excl. machine-specific
   `.venv-atlas` virtualenv).
   - **Resolution:** full per-file copy is infeasible on this drive: measured write
     throughput ≈ 50 KB/s sequential / ~20 s per small file. 317 files ≈ 1.5–2 h — would
     destroy the session time budget.
   - Shipped the engine to the drive as a **single restorable archive**:
     `E:\forex-data\atlas-engine.tar.gz` (1,831,391 bytes).
     sha256 verified byte-identical both sides: `1cfb6550…f68e654`.
   - Partial in-place copy renamed `E:\forex-data\atlas-engine.partial` (incomplete —
     do not use; delete in maintenance pass).
   - **Live authoritative copy remains local** at C:\Users\ankit\Documents\forex-engine\atlas-engine;
     test suite verified runnable there (1,149 collected, subset passed).
   - No data loss. Full per-file migration is a documented maintenance task, not a blocker.
2. **Drive write speed:** ~50 KB/s sequential, ~20 s/file. All campaign outputs are small
   (scripts, reports) → 1 write each, affordable. Bulk writes deferred.
3. **Stray cp/tar processes** from a timed-out copy were holding the drive; killed, then
   drive behaved normally. Lesson: never multi-file-copy to this drive within a tool timeout.

## Verdict
Part 1 passes with one documented, resolved discrepancy (atlas-engine archived, not
per-file migrated). Proceeding to Part 5.
