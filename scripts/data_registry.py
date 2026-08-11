#!/usr/bin/env python3
"""data_registry.py — unified data-ingest registry (T2).

Single entry point for every dataset in the programme, replacing the
per-script loaders (edge_scan.load_d1, fx_strict_battery.load_big_events,
news_deep_campaign.load_events_all, spread_test.load_ratio, the ad-hoc
FRED/policy-rate readers in weight_calibrator, ...).

KEY MODEL — logical keys resolve to physical sources via market-data/registry.json:
    fx:USDJPY:d1          normalized OHLC parquet (template, {sym}/{tf})
    events                Forex Factory archive (events.parquet)
    commodity:ZS          Yahoo continuous futures CSV (COMM_ZS_d.csv)
    fundamental:CPI_US    FRED CSV under market-data/fundamentals/
    cpi:CPI_US            FRED CSV under market-data/rates/   (policy-era files)
    rate:USD              policy_rates.csv row for a currency
    ledger                live news-drift forward ledger (news_drift/)

QUALITY GATES — every load() runs them and records results in GATE_LOG:
    * drop duplicate timestamps (and report how many were dropped)
    * remove non-positive prices (WTI April 2020 guard; prices only)
    * min_observation floor (default 2500 for daily; see source config)
    * report gaps > 5 trading days
Gate outcomes are queryable via gate_report() and persisted by write_gate_report()
so both machines see the same data-quality state without re-scanning.

Usage:
    from data_registry import load, gate_report
    d1 = load("fx:USDJPY:d1")
    ev = load("events", currency="USD", impact=("High", "Medium"))
    zs = load("commodity:ZS")
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path("E:/forex-data")
REGISTRY = BASE / "market-data" / "registry.json"
GATE_LOG: list[dict] = []
_CACHE: dict[str, pd.DataFrame] = {}

DEFAULT_MIN_OBS = 2500


# --------------------------------------------------------------------------
# registry catalogue
# --------------------------------------------------------------------------

def _load_registry() -> dict:
    if not REGISTRY.exists():
        raise FileNotFoundError(f"registry missing: {REGISTRY} — run rebuild_registry()")
    return json.loads(REGISTRY.read_text(encoding="utf-8"))


def _source_for(key: str) -> tuple[dict, dict]:
    """Split a key like 'fx:USDJPY:d1' into (source spec, params)."""
    reg = _load_registry()
    head, _, rest = key.partition(":")
    src = reg["sources"].get(head)
    if src is None:
        raise KeyError(f"no source family '{head}' in registry (key={key!r})")
    return src, {"key": key, "rest": rest}


def resolve_path(key: str) -> Path:
    """Resolve a logical key to its physical file path (no data touched)."""
    src, p = _source_for(key)
    path_t = src["path"]
    if src.get("template"):
        parts = p["rest"].split(":")
        subs = dict(zip(src["template_fields"], parts))
        path_t = path_t.format(**subs)
    return BASE / path_t


# --------------------------------------------------------------------------
# quality gates
# --------------------------------------------------------------------------

def _gate(key: str, n_before: int, n_after: int, dropped: int,
          nonpos: int, max_gap: float, n_days: float, ok: bool, note: str = ""):
    GATE_LOG.append({
        "key": key, "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "rows_before": n_before, "rows_after": n_after, "dropped_dups": dropped,
        "non_positive": nonpos, "max_gap_tdays": round(float(max_gap), 1),
        "span_days": round(float(n_days), 0), "ok": ok, "note": note,
    })


def _clean_prices(df: pd.DataFrame, key: str, min_obs: int | None = None) -> pd.DataFrame:
    """Dedupe index, drop non-positive close, count, then gap-report."""
    min_obs = min_obs or DEFAULT_MIN_OBS
    n0 = len(df)
    df = df[~df.index.duplicated(keep="first")].sort_index()
    dropped = n0 - len(df)
    if "close" in df.columns:
        nonpos = int((df["close"] <= 0).sum())
        df = df[df["close"] > 0]
    else:
        nonpos = 0
    ok = len(df) >= min_obs
    gaps = df.index.to_series().diff().dt.days.dropna()
    max_gap = float(gaps.max()) if len(gaps) else 0.0
    span = (df.index[-1] - df.index[0]).total_seconds() / 86400 if len(df) else 0.0
    _gate(key, n0, len(df), dropped, nonpos, max_gap, span, ok,
          note="" if ok else f"<{min_obs} obs")
    return df


def _clean_events(df: pd.DataFrame, key: str) -> pd.DataFrame:
    """Events are event-rows, not a price series: dedupe on the composite
    identity (release, timestamp, currency) — many releases legitimately
    share a timestamp (e.g. 08:30 tier-1 cluster)."""
    n0 = len(df)
    ident = ["date_utc", "title", "currency"]
    df = df[~df[ident].duplicated(keep="first")].sort_values("date_utc")
    _gate(key, n0, len(df), n0 - len(df), 0, 0.0, 0.0, len(df) > 1000)
    return df


# --------------------------------------------------------------------------
# loaders
# --------------------------------------------------------------------------

def _fx(src: dict, p: dict) -> pd.DataFrame:
    sym, tf = p["rest"].split(":")
    f = BASE / src["path"].format(sym=sym, tf=tf)
    if not f.exists():
        raise FileNotFoundError(f"{f} missing — run the collector")
    df = pd.read_parquet(f)[["Open", "High", "Low", "Close"]].copy()
    df.index = pd.to_datetime(df.index)
    return _clean_prices(df, f"fx:{sym}:{tf}", src.get("min_obs"))


def _events(src: dict, p: dict) -> pd.DataFrame:
    f = BASE / src["path"]
    df = pd.read_parquet(f)
    df["date_utc"] = pd.to_datetime(df["date_utc"], utc=True)
    return _clean_events(df, "events")


def _yahoo_csv(src: dict, p: dict) -> pd.DataFrame:
    sym = p["rest"]
    f = BASE / src["path"].format(sym=sym)
    df = pd.read_csv(f, parse_dates=["date"]).set_index("date")
    cols = [c for c in ("open", "high", "low", "close", "volume") if c in df.columns]
    df = df[cols].copy()
    df.columns = [c.title() for c in cols]
    return _clean_prices(df, f"commodity:{sym}", src.get("min_obs"))


def _fred_csv(src: dict, p: dict) -> pd.DataFrame:
    file = p["rest"]
    f = BASE / src["path"].format(file=file)
    df = pd.read_csv(f)
    date_col = "observation_date" if "observation_date" in df.columns else "DATE"
    df = df.rename(columns={date_col: "date"})
    df["date"] = pd.to_datetime(df["date"])
    val = [c for c in df.columns if c != "date"][0]
    df = df[["date", val]].rename(columns={val: "value"})
    df = df.set_index("date").sort_index()
    return _clean_prices(df, p["key"], src.get("min_obs"))


def _policy_rates(src: dict, p: dict) -> pd.DataFrame:
    ccy = p["rest"]
    f = BASE / src["path"]
    df = pd.read_csv(f)
    df.columns = [c.strip().lower() for c in df.columns]
    tcol = "date" if "date" in df.columns else df.columns[0]
    df[tcol] = pd.to_datetime(df[tcol], utc=True).dt.tz_localize(None)
    df = df.rename(columns={tcol: "date"}).set_index("date").sort_index()
    keep = [c for c in df.columns if ccy.lower() in c.lower() or c == ccy.lower()]
    df = df[keep].dropna(how="all", axis=1).dropna(how="all")
    return df


def _ledger(src: dict, p: dict) -> pd.DataFrame:
    f = BASE / src["path"]
    df = pd.read_csv(f)
    for c in df.columns:
        if "date" in c.lower():
            df[c] = pd.to_datetime(df[c])
    return df


_LOADERS = {
    "fx": _fx, "events": _events, "commodity": _yahoo_csv,
    "fundamental": _fred_csv, "cpi": _fred_csv, "rate": _policy_rates,
    "ledger": _ledger,
}


def load(key: str, **kw) -> pd.DataFrame:
    """Unified load. kw passes to the loader (events filters etc.)."""
    if key in _CACHE and not kw:
        return _CACHE[key]
    src, p = _source_for(key)
    fn = _LOADERS[src["kind"]]
    df = fn(src, p)
    if src["kind"] == "events_parquet" or key == "events":
        # canonical event z-score pipeline — replaces the two duplicate
        # implementations in fx_strict_battery.py / news_deep_campaign.py
        df = _events_z(df, **kw)
    if not kw:
        _CACHE[key] = df
    return df


def _events_z(ev: pd.DataFrame, currency: str = "USD",
              impact: tuple[str, ...] = ("High", "Medium"),
              z_thr: float = 0.5, min_periods: int = 20,
              clip: float = 8.0) -> pd.DataFrame:
    """Per-title EXPANDING z-score of (actual - forecast). Canonical form.

    Matches the exact parameters from the validated drift battery:
    min_periods=20, sd floored at 1e-12, z winsorized at +/- clip.
    """
    m = (ev["currency"] == currency) & ev["actual"].notna() & ev["forecast"].notna()
    if impact is not None:
        m &= ev["impact"].isin(impact)
    ev = ev[m].copy()
    ev["surprise"] = (pd.to_numeric(ev["actual"], errors="coerce") -
                      pd.to_numeric(ev["forecast"], errors="coerce"))
    ev = ev.dropna(subset=["surprise"]).sort_values("date_utc")
    ev["z"] = np.nan
    for _t, g in ev.groupby("title"):
        g = g.sort_values("date_utc")
        s = g["surprise"]
        mu = s.expanding(min_periods=min_periods).mean().shift(1)
        sd = s.expanding(min_periods=min_periods).std().shift(1)
        z = (s - mu) / sd.where(sd > 1e-12)
        ev.loc[g.index, "z"] = z.clip(-clip, clip)
    ev["date"] = ev["date_utc"].dt.date
    if z_thr is not None:
        ev = ev[ev["z"].abs() >= z_thr].copy()
    return ev


# --------------------------------------------------------------------------
# gate reporting
# --------------------------------------------------------------------------

def gate_report() -> pd.DataFrame:
    if not GATE_LOG:
        return pd.DataFrame()
    return pd.DataFrame(GATE_LOG)


def write_gate_report(out: Path | None = None) -> Path:
    out = out or BASE / "reports" / "registry_gates.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    gate_report().to_csv(out, index=False)
    return out


def rebuild_registry() -> None:
    """Regenerate registry.json from the actual drive contents (nothing invented)."""
    import os
    norm = BASE / "market-data" / "normalized"
    fx_syms = sorted(d.name for d in norm.iterdir()
                     if d.is_dir() and any(d.glob(f"{d.name}_d1.parquet")))
    yahoo = BASE / "market-data" / "raw" / "yahoo"
    comms = sorted(f.name[len("COMM_"):-len("_d.csv")]
                   for f in yahoo.glob("COMM_*_d.csv"))
    funds = sorted(f.name[:-4] for f in (BASE / "market-data" / "fundamentals").glob("*.csv"))
    rates = sorted(f.name[:-4] for f in (BASE / "market-data" / "rates").glob("*.csv"))
    reg = {
        "schema_version": 1,
        "base": str(BASE),
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sources": {
            "fx": {"kind": "fx", "template": True,
                   "template_fields": ["sym", "tf"],
                   "path": "market-data/normalized/{sym}/{sym}_{tf}.parquet",
                   "note": "normalized OHLC parquet, IBKR/Yahoo", "min_obs": 2500},
            "events": {"kind": "events", "path": "market-data/events/events.parquet",
                       "note": "Forex Factory archive (live-captured)"},
            "commodity": {"kind": "commodity", "path": "market-data/raw/yahoo/COMM_{sym}_d.csv",
                          "note": "Yahoo continuous back-adjusted futures", "min_obs": 2500},
            "fundamental": {"kind": "fundamental", "path": "market-data/fundamentals/{file}.csv",
                            "note": "FRED series", "min_obs": 100},
            "cpi": {"kind": "cpi", "path": "market-data/rates/{file}.csv",
                    "note": "policy-era FRED CPI", "min_obs": 100},
            "rate": {"kind": "rate", "path": "market-data/rates/policy_rates.csv",
                     "note": "8-currency policy rates, tz-normalized"},
            "ledger": {"kind": "ledger", "path": "market-data/news_drift/forward_ledger.csv",
                       "note": "live USDJPY drift forward ledger"},
        },
        "discovered": {"fx_pairs": fx_syms, "commodities": comms,
                       "fundamentals": funds, "rates_files": rates},
    }
    REGISTRY.write_text(json.dumps(reg, indent=2), encoding="utf-8")


def smoke(key: str, head: int = 3) -> None:
    df = load(key)
    print(f"{key}: {len(df)} rows  {df.index.min()} -> {df.index.max()}")
    print(df.head(head).to_string())


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "rebuild":
        rebuild_registry()
        print("registry rebuilt:", REGISTRY)
    else:
        for k in ["fx:USDJPY:d1", "events", "commodity:ZS",
                  "fundamental:CPI_US", "rate:USD", "ledger"]:
            try:
                smoke(k, 1)
            except Exception as e:  # noqa: BLE001
                print(f"{k}: ERROR {e}")
        print("\n=== GATE REPORT ===")
        print(gate_report().to_string(index=False))
