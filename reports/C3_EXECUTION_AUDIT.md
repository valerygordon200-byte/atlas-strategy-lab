# C3 — dourmouse Execution Layer Audit (T6)

Owner: laptop-dourmouse · Date: 2026-08-11 · Task: reports/../coordination (T6)

Audit target: the dourmouse application at `/Applications/dourmouse-dist`
(desktop app, Python) plus the atlas-strategy-lab repo's scripts/reports.
Question: which broker connectors are LIVE vs STUBBED, and can any path
execute a real paper/demo fill today?

## Per-connector verdict

| Connector | State | Evidence |
|---|---|---|
| **MetaTrader 5 (MT5)** | **ABSENT — not present at all** | Zero references to `mt5`/`metatrader` in dourmouse source; no MT5 module; no `.env` keys |
| **Interactive Brokers (IBKR)** | **ABSENT — not present at all** | Zero references to `ibkr`/`interactive broker` in dourmouse source; no TWS/Gateway client; no `.env` keys. Playbook names IBKR paper as the intended venue ("the one we tried to connect earlier and never finished" — nothing was left behind) |
| **Trading 212** | **ABSENT — not present at all** | Zero references; no execution API by design (paper there is manual-only per the C3 brief) |
| **TradingView webhook** | **ABSENT — not present at all** | Zero references in dourmouse source |
| **Alpaca** | **STUBBED** | `.env` has `APCA_API_KEY_ID` / `APCA_API_SECRET_KEY` / `APCA_API_BASE_URL`, and `connections.py` reports their presence — but there is **no order-placing code anywhere**: no `place_order`, no fills handler, no position module, no ledger integration. Credentials only, nothing executes |
| **Forward ledger (NewsDriftForward)** | **LIVE (not a broker)** | Desktop scheduled task writes USDJPY drift paper fills to `forward_ledger.csv` — a data-recording script, not a broker connector; no fills are placed through any venue |

## Conclusions

1. **No connector can place a real demo fill today.** The execution layer is
   entirely absent: four of five named connectors don't exist in the codebase
   (not even stubbed), and the one with credentials (Alpaca) has no execution
   module.
2. **The C3 acceptance criterion ("paper path must execute REAL DEMO FILLS
   through the audited connector") has nothing to audit against yet** — there
   is no connector to audit. The honest state is: `LIVE: 0 · STUBBED: 1
   (Alpaca) · ABSENT: 4 (MT5, IBKR, T212, TradingView)`.
3. **IBKR paper is the right target per the playbook** (covers commodities
   futures + FX; fractional ETFs for dual-momentum if revived) — but it must
   be BUILT first, not audited. Blocking items for an IBKR demo-fill round
   trip, in order:
   - an IBKR connector module in dourmouse (native TWS/Gateway API or
     `ib_insync`); stdlib-only constraint may push toward the raw socket
     API or a small vendored client,
   - TWS or IBKR Gateway running on the desktop (Windows) with a paper
     account, API port open (7497 paper / 7496 live) and `Trusted IPs`
     permitting the connecting machine,
   - network reachability desktop <-> laptop over the tailnet for the API
     port,
   - a place -> fill -> ledger-entry round-trip test (the C3 demo path).

## Recommendation

- Close T6 (this audit) with this report; the audit itself is complete.
- Open the implementation as a new task: "IBKR paper connector: connect,
  place, fill, ledger entry round trip" — build first, then the C3 paper-path
  criterion becomes auditable.
- Interim honesty: the ONLY fills that happen today are the forward-ledger
  entries recorded by the desktop's scheduled USDJPY drift task — no venue,
  no broker, no real demo fills.
