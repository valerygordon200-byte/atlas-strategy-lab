#!/usr/bin/env python3
"""engine_api.py — C2: the atlas backtest engine as a callable HTTP service.

Lets dourmouse's UI run backtests against the full data stack without owning
the data. Stdlib-only HTTP server (no deps); data + engine live on this
machine (E:\\forex-data), served over loopback (and optionally the tailnet).

Endpoints (per the C1 spec):
    GET  /api/health                  alive + registry key count
    GET  /api/keys                    every key, availability + row counts
    GET  /api/data/{key}?limit=N      head of a series as JSON records
    POST /api/backtest                run a registered backtest by id
    POST /api/backtest/{id}/report    regenerate the markdown report

Registered backtests (id -> runner):
    usdjpy_drift_k1   USDJPY news-drift k=1 (the live strategy's engine test)
    registry_gates    data-quality gate sweep for all keys

Security: reads only on data endpoints; backtest runners are fixed, named
functions — no code from the wire is ever executed. Token optional via
ENGINE_TOKEN env (recommended when bound off loopback).

Run:  python scripts/engine_api.py [--port 8790] [--bind 127.0.0.1]
      (engine_api.py must sit next to data_registry.py, or set
       ATLAS_DATA_PATH to the folder containing it.)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

DATA_DIR = Path(os.environ.get("ATLAS_DATA_PATH", "E:/forex-data/scripts"))
if str(DATA_DIR) not in sys.path:
    sys.path.insert(0, str(DATA_DIR))

import data_registry  # noqa: E402
from data_registry import BASE, load, gate_report  # noqa: E402

TOKEN = os.environ.get("ENGINE_TOKEN", "")


def _keys_with_rows() -> list[dict]:
    reg = json.loads((BASE / "market-data/registry.json").read_text(encoding="utf-8"))
    d = reg["discovered"]
    out = []
    for sym in d["fx_pairs"]:
        for tf in ("d1", "h1"):
            out.append({"key": f"fx:{sym}:{tf}", "kind": "fx", "min_obs": 2500})
    out.append({"key": "events", "kind": "events"})
    for c in d["commodities"]:
        out.append({"key": f"commodity:{c}", "kind": "commodity", "min_obs": 2500})
    for f in d["fundamentals"]:
        out.append({"key": f"fundamental:{f}", "kind": "fundamental", "min_obs": 100})
    for ccy in ("USD", "EUR", "GBP", "JPY", "AUD", "CAD", "CHF", "NZD"):
        out.append({"key": f"rate:{ccy}", "kind": "rate"})
    out.append({"key": "ledger", "kind": "ledger"})
    return out


# ---- registered backtests -------------------------------------------------

def bt_usdjpy_drift_k1(params: dict) -> dict:
    """USDJPY news drift k=1 hold: entry next-day open, exit next close,
    1-pip round-trip cost, IS 2015-2021 / OOS 2022+ (battery convention)."""
    t0 = time.time()
    ev = load("events", currency="USD", impact=("High", "Medium"), z_thr=0.5)
    px = load("fx:USDJPY:d1")["Close"]
    r = px.pct_change()
    next_r = r.shift(-1).dropna()
    next_r.index = next_r.index.date
    ev["r"] = ev["date"].map(next_r)
    ev = ev.dropna(subset=["r"])
    cost = 1.0 * 0.01 / float(px.mean())
    net = 1.0 * ev["z"].apply(lambda z: 1 if z > 0 else -1) * ev["r"] - cost
    ev["net"] = net
    ism = ev["date"].astype(str) < "2022-01-01"
    is_n, oos_n = int(ism.sum()), int((~ism).sum())
    is_t = net[ism].mean() / (net[ism].std(ddof=1) / (is_n ** 0.5)) if is_n > 2 else float("nan")
    oos_t = net[~ism].mean() / (net[~ism].std(ddof=1) / (oos_n ** 0.5)) if oos_n > 2 else float("nan")
    return {
        "backtest": "usdjpy_drift_k1", "params": params,
        "n_is": is_n, "n_oos": oos_n,
        "is_mean_net": round(float(net[ism].mean()), 6),
        "oos_mean_net": round(float(net[~ism].mean()), 6),
        "is_t": round(float(is_t), 3), "oos_t": round(float(oos_t), 3),
        "oos_win": round(float((net[~ism] > 0).mean()), 4),
        "runtime_s": round(time.time() - t0, 2),
        "provenance": {"events": "events.parquet z>=0.5 USD H+M",
                       "price": "fx:USDJPY:d1", "cost": "1 pip RT"},
    }


def bt_registry_gates(params: dict) -> dict:
    t0 = time.time()
    n_ok = n_fail = 0
    fails = []
    for k in [e["key"] for e in _keys_with_rows()]:
        try:
            load(k)
            n_ok += 1
        except Exception as e:  # noqa: BLE001
            n_fail += 1
            fails.append(f"{k}: {e}")
    return {"backtest": "registry_gates", "params": params,
            "keys_ok": n_ok, "keys_fail": n_fail, "failures": fails[:10],
            "runtime_s": round(time.time() - t0, 2)}


BACKTESTS = {"usdjpy_drift_k1": bt_usdjpy_drift_k1, "registry_gates": bt_registry_gates}


# ---- HTTP ----------------------------------------------------------------

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):  # keep the console quiet
        pass

    def _ok(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _err(self, msg, code=400):
        self._ok({"ok": False, "error": msg}, code)

    def _auth(self) -> bool:
        if not TOKEN:
            return True
        return self.headers.get("X-Engine-Token") == TOKEN

    def do_GET(self):
        if not self._auth():
            return self._err("unauthorized", 401)
        path = urlparse(self.path).path
        q = urlparse(self.path).query
        limit = 5
        for kv in q.split("&"):
            if kv.startswith("limit="):
                limit = int(kv.split("=", 1)[1] or 5)
        if path == "/api/health":
            return self._ok({"ok": True, "engine": "atlas", "keys": len(_keys_with_rows()),
                             "time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
        if path == "/api/keys":
            return self._ok({"ok": True, "keys": _keys_with_rows()})
        if path.startswith("/api/data/"):
            key = path[len("/api/data/"):]
            try:
                df = load(key)
            except Exception as e:  # noqa: BLE001
                return self._err(f"load failed: {e}", 404)
            cols = [c for c in df.columns][:8]
            head = df.head(limit).reset_index()
            head.columns = [str(c) for c in head.columns]
            recs = json.loads(head.to_json(orient="records", date_format="iso"))
            return self._ok({"ok": True, "key": key, "rows": int(len(df)),
                             "from": str(df.index.min()), "to": str(df.index.max()),
                             "columns": cols, "sample": recs})
        return self._err("unknown endpoint", 404)

    def do_POST(self):
        if not self._auth():
            return self._err("unauthorized", 401)
        path = urlparse(self.path).path
        length = int(self.headers.get("Content-Length", 0) or 0)
        body = {}
        if length:
            try:
                body = json.loads(self.rfile.read(length).decode())
            except Exception:  # noqa: BLE001
                return self._err("bad json body")
        if path == "/api/backtest":
            bid = body.get("id", "")
            if bid not in BACKTESTS:
                return self._err(f"unknown backtest '{bid}' (have: {sorted(BACKTESTS)})", 404)
            try:
                return self._ok({"ok": True, "result": BACKTESTS[bid](body.get("params", {}))})
            except Exception as e:  # noqa: BLE001
                return self._err(f"backtest failed: {e}", 500)
        return self._err("unknown endpoint", 404)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=int(os.environ.get("ENGINE_PORT", 8790)))
    ap.add_argument("--bind", default=os.environ.get("ENGINE_BIND", "127.0.0.1"))
    args = ap.parse_args()
    srv = ThreadingHTTPServer((args.bind, args.port), Handler)
    print(f"atlas engine API on http://{args.bind}:{args.port} "
          f"(backtests: {sorted(BACKTESTS)})" + ("" if TOKEN else " [NO TOKEN — loopback only]"))
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("stopped")


if __name__ == "__main__":
    main()
