#!/usr/bin/env python3
"""ibkr_connector.py — C8: IBKR paper connector (place -> fill -> ledger).

Connects to an IBKR TWS/Gateway (paper account, port 7497 by default), places
a market order on a given instrument, waits for the fill, and appends a
ledger row so the paper trade is recorded exactly like the USDJPY drift
forward-ledger entries.

Usage:
  python scripts/ibkr_connector.py --symbol EUR --currency USD --action BUY --qty 1000
  python scripts/ibkr_connector.py --symbol GC --sec-type FUT --currency USD --action SELL --qty 1 --contract-month 202609 --host 192.168.1.95 --port 7497
  python scripts/ibkr_connector.py --check            # connectivity + account check only

Config: reads IBKR_HOST / IBKR_PORT / IBKR_CLIENT_ID from dourmouse/.env if
present (secrets stay out of the repo). Defaults 127.0.0.1:7497, client id 17.

Ledger: appends to <ATLAS_DATA>/market-data/executions/executions.csv with the
same column style as the forward ledger (event ts, instrument, side, qty,
filled price, notional, venue=IBKR_PAPER, strategy tag).

Honest limits:
  - paper fills are instant market fills from the IBKR paper engine; they are
    realistic in price but not in slippage/queueing.
  - client id must not collide with an open TWS connection (pick a unique id).
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = Path(os.environ.get("ATLAS_DATA_PATH", "E:/forex-data"))
EXEC_DIR = DATA / "market-data" / "executions"

try:
    from ib_insync import IB, Stock, Future, Forex
except ImportError:  # pragma: no cover
    sys.exit("ib_insync not installed:  python -m pip install ib_insync")


def _load_env(env_path: Path) -> dict:
    out = {}
    if not env_path.exists():
        return out
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def contract_for(args) -> object:
    """Build the ib_insync contract from CLI args."""
    st = args.sec_type.upper()
    if st in ("STK", "STOCK"):
        c = Stock(args.symbol, args.exchange or "SMART", args.currency)
    elif st == "FUT":
        c = Future(args.symbol, args.contract_month, args.exchange or "GLOBEX",
                   currency=args.currency)
    elif st == "CASH":
        c = Forex(args.symbol)  # e.g. EUR.USD
    elif st == "CFD":
        from ib_insync import CFD
        c = CFD(args.symbol, args.exchange or "SMART", args.currency)
    else:
        sys.exit(f"unsupported sec type: {st} (use STK/FUT/CASH/CFD)")
    return c


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--symbol", help="ticker, e.g. EUR (CASH), GC (FUT), AAPL (STK)")
    ap.add_argument("--sec-type", default="CASH", help="STK/FUT/CASH/CFD")
    ap.add_argument("--currency", default="USD")
    ap.add_argument("--exchange", default="")
    ap.add_argument("--contract-month", default="", help="YYYYMM for futures")
    ap.add_argument("--action", choices=["BUY", "SELL"], default="BUY")
    ap.add_argument("--qty", type=float, default=0.0,
                    help="quantity (units; for futures 1 = 1 contract)")
    ap.add_argument("--host", default="")
    ap.add_argument("--port", type=int, default=0)
    ap.add_argument("--client-id", type=int, default=0)
    ap.add_argument("--strategy", default="manual", help="strategy tag for the ledger")
    ap.add_argument("--check", action="store_true", help="connectivity/account check only")
    args = ap.parse_args()

    env = _load_env(ROOT.parent / "dourmouse" / ".env")
    host = args.host or env.get("IBKR_HOST", "127.0.0.1")
    port = args.port or int(env.get("IBKR_PORT", "7497"))
    cid = args.client_id or int(env.get("IBKR_CLIENT_ID", "17"))

    ib = IB()
    try:
        ib.connect(host, port, clientId=cid, timeout=10)
    except Exception as e:  # noqa: BLE001
        sys.exit(f"CONNECT FAILED to {host}:{port} — is TWS/Gateway running and the "
                 f"paper account logged in?  ({e})")
    print(f"connected to {host}:{port} client={cid}")

    acct = ib.managedAccounts()
    print("managed accounts:", acct)
    if not acct:
        ib.disconnect()
        sys.exit("no managed account returned — confirm the paper account is the active login")

    if args.check:
        for v in ib.accountSummary():
            if v.tag in ("NetLiquidation", "BuyingPower", "CashBalance", "UnrealizedPnL"):
                print(f"  {v.tag}: {v.value} {v.currency}")
        ib.disconnect()
        return

    if not args.symbol:
        ib.disconnect()
        sys.exit("--symbol required to place an order")
    if not args.qty:
        ib.disconnect()
        sys.exit("--qty required to place an order")

    c = contract_for(args)
    # qualify resolves the contract against the gateway's own database
    try:
        q = ib.qualifyContracts(c)
    except Exception as e:  # noqa: BLE001
        ib.disconnect()
        sys.exit(f"qualify failed for {args.symbol}: {e}")
    if not q:
        ib.disconnect()
        sys.exit(f"contract {args.symbol} ({args.sec_type}) not found — check symbol/type/exchange")
    c = q[0]
    print("qualified contract:", c)

    order = ib.marketOrder(args.action, args.qty)
    trade = ib.placeOrder(c, order)
    print(f"order placed: {args.action} {args.qty} {c.symbol}  orderId={order.orderId}")

    # wait for a fill (paper fills are near-instant; generous timeout)
    try:
        filled = ib.waitUntil(lambda: trade.isDone(), timeout=30)
    except Exception:  # noqa: BLE001
        filled = trade.isDone()
    if not filled or not trade.orderStatus.filled:
        print(f"NOT FILLED — status={trade.orderStatus.status} filled={trade.orderStatus.filled}")
        ib.disconnect()
        sys.exit(1)

    avg = trade.orderStatus.avgFillPrice
    print(f"FILLED {trade.orderStatus.filled} @ {avg:.5f} ({trade.orderStatus.status})")

    # ---- ledger entry (append, never overwrite) ----
    EXEC_DIR.mkdir(parents=True, exist_ok=True)
    ledger = EXEC_DIR / "executions.csv"
    ts = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S+00:00")
    notional = float(avg) * float(trade.orderStatus.filled)
    row = {
        "ts": ts, "venue": "IBKR_PAPER", "strategy": args.strategy,
        "symbol": c.symbol, "sec_type": args.sec_type, "currency": args.currency,
        "action": args.action, "qty": float(trade.orderStatus.filled),
        "filled_price": round(float(avg), 6), "notional": round(notional, 2),
        "order_id": int(order.orderId), "status": trade.orderStatus.status,
    }
    write_header = not ledger.exists() or ledger.stat().st_size == 0
    with open(ledger, "a", encoding="utf-8") as fh:
        if write_header:
            fh.write(",".join(row.keys()) + "\n")
        fh.write(",".join(str(row[k]) for k in row) + "\n")
    print(f"ledger -> {ledger}")

    ib.disconnect()
    print("disconnected — round trip complete")


if __name__ == "__main__":
    main()
