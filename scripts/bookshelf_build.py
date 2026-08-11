#!/usr/bin/env python3
"""bookshelf_build.py — generate market-data/bookshelf/bookshelf.json.

A categorized inventory ("bookshelf") of every asset we have data on, its price
data, its available fundamental factor data, and its pre-registered mechanism
factors with data-availability flags. Historical weights are filled by
weight_calibrator.py (weight_hist) and blended into weight_final.

Categories reflect WHAT MOVES the asset (mechanism-first), not asset class
labels alone. Every factor names its forced participant where one exists.
"""
import json
import os
import sys
from pathlib import Path

import pandas as pd

BASE = Path("E:/forex-data")

# ---------- mechanism factor schema (pre-registered design weights) ----------
# weight_design: 0..1 importance of this factor for THIS asset, mechanism-based.
# data: where the factor data lives; MISSING = must be sourced before use.
# participant: the forced (or quasi-forced) participant behind the factor.

MECH = {
    "GOLD": [
        {"name": "central_bank_net_buying", "participant": "central banks (reserve diversification mandate; no price discipline)",
         "data": "MISSING — WGC / national CB disclosures / IMF IFS; not yet sourced", "weight_design": 0.35},
        {"name": "real_yield_10y", "participant": "duration-mandate funds; opportunity-cost pricing", "data": "fundamentals/yield_usd + cpi_usd", "weight_design": 0.25},
        {"name": "usd_basket", "participant": "global USD pricing convention", "data": "derivable from 7 USD pairs", "weight_design": 0.20},
        {"name": "usd_cpi_surprise_z", "participant": "inflation-linked flows (dealer/ETF)", "data": "events.parquet (USD CPI titles)", "weight_design": 0.10},
        {"name": "policy_rate_us", "participant": "carry/opportunity cost", "data": "rates/policy_rates.csv", "weight_design": 0.10},
    ],
    "SILVER": [
        {"name": "gold_silver_ratio_reversion", "participant": "industrial + monetary dual use; ratio arbitrage", "data": "normalized/GSR", "weight_design": 0.30},
        {"name": "industrial_demand_cycle", "participant": "manufacturing (solar/electronics) — no clean free series on drive", "data": "MISSING (proxy: global PMI not on drive)", "weight_design": 0.25},
        {"name": "real_yield_10y", "participant": "same as gold", "data": "fundamentals/yield_usd + cpi_usd", "weight_design": 0.20},
        {"name": "usd_basket", "participant": "USD pricing", "data": "derivable", "weight_design": 0.15},
        {"name": "usd_cpi_surprise_z", "participant": "inflation flows", "data": "events.parquet", "weight_design": 0.10},
    ],
    "OIL": [
        {"name": "inventory_surprise_z", "participant": "physical storage arbitrageurs must reprice on EIA prints", "data": "events.parquet (EIA Crude Stocks Change)", "weight_design": 0.35},
        {"name": "usd_basket", "participant": "USD-priced commodity", "data": "derivable", "weight_design": 0.20},
        {"name": "opec_supply_regime", "participant": "cartel production decisions (scheduled meetings)", "data": "MISSING (meeting calendar + decisions manual)", "weight_design": 0.25},
        {"name": "policy_rate_us", "participant": "demand/financing cost", "data": "rates/policy_rates.csv", "weight_design": 0.10},
        {"name": "api_crude_surprise_z", "participant": "pre-EIA signal", "data": "events.parquet (API Crude)", "weight_design": 0.10},
    ],
    "USDJPY": [
        {"name": "usd_cpi_surprise_z_drift", "participant": "under-reaction: JPY-complex flow/liquidity", "data": "events.parquet — THE tested edge", "weight_design": 0.40},
        {"name": "rate_differential_us_jp", "participant": "carry", "data": "rates/policy_rates.csv", "weight_design": 0.30},
        {"name": "risk_regime", "participant": "carry unwind flows (JPY safe haven)", "data": "MISSING clean proxy (could use BTC/NDX)", "weight_design": 0.20},
        {"name": "boj_intervention", "participant": "MOF/BoJ — irregular, unannounced", "data": "MISSING (manual event log)", "weight_design": 0.10},
    ],
    "EURUSD": [
        {"name": "rate_differential_us_eur", "participant": "carry/ECB vs Fed", "data": "rates/policy_rates.csv", "weight_design": 0.40},
        {"name": "eur_cpi_surprise_z", "participant": "ECB policy expectations", "data": "events.parquet (EUR CPI titles)", "weight_design": 0.25},
        {"name": "usd_cpi_surprise_z", "participant": "US policy expectations", "data": "events.parquet", "weight_design": 0.20},
        {"name": "risk_regime", "participant": "global risk flows", "data": "proxy possible", "weight_design": 0.15},
    ],
    "GBPUSD": [
        {"name": "rate_differential_us_gbp", "participant": "carry/BoE vs Fed", "data": "rates/policy_rates.csv", "weight_design": 0.40},
        {"name": "gbp_cpi_surprise_z", "participant": "BoE policy expectations", "data": "events.parquet (GBP CPI)", "weight_design": 0.25},
        {"name": "usd_cpi_surprise_z", "participant": "US policy", "data": "events.parquet", "weight_design": 0.20},
        {"name": "risk_regime", "participant": "global risk flows", "data": "proxy possible", "weight_design": 0.15},
    ],
    "AUDUSD": [
        {"name": "rate_differential_us_aud", "participant": "carry/RBA vs Fed", "data": "rates/policy_rates.csv", "weight_design": 0.35},
        {"name": "china_demand", "participant": "commodity demand channel", "data": "MISSING (China data not on drive)", "weight_design": 0.25},
        {"name": "commodity_link", "participant": "AUD as commodity currency", "data": "GOLD/OIL normalized", "weight_design": 0.20},
        {"name": "aud_cpi_surprise_z", "participant": "RBA expectations", "data": "events.parquet (AUD CPI)", "weight_design": 0.20},
    ],
    "SP500": [
        {"name": "usd_cpi_surprise_z", "participant": "Fed policy repricing", "data": "events.parquet", "weight_design": 0.30},
        {"name": "policy_rate_us", "participant": "discount rate", "data": "rates/policy_rates.csv", "weight_design": 0.25},
        {"name": "earnings_flow", "participant": "corporate earnings calendar", "data": "MISSING (no earnings data on drive)", "weight_design": 0.25},
        {"name": "risk_regime", "participant": "vol/positioning", "data": "proxy possible", "weight_design": 0.20},
    ],
    "NDX": [
        {"name": "usd_cpi_surprise_z", "participant": "Fed policy repricing (duration-heavy index)", "data": "events.parquet", "weight_design": 0.35},
        {"name": "policy_rate_us", "participant": "discount rate", "data": "rates/policy_rates.csv", "weight_design": 0.25},
        {"name": "earnings_flow", "participant": "megacap earnings", "data": "MISSING", "weight_design": 0.25},
        {"name": "risk_regime", "participant": "vol/positioning", "data": "proxy possible", "weight_design": 0.15},
    ],
    "BTCUSD": [
        {"name": "liquidity_regime", "participant": "global liquidity / dollar", "data": "policy_rates + USD basket", "weight_design": 0.30},
        {"name": "risk_appetite", "participant": "speculative flows", "data": "NDX normalized", "weight_design": 0.25},
        {"name": "halving_supply_schedule", "participant": "algorithmic supply schedule (forced by code)", "data": "known dates (2020, 2024, 2028)", "weight_design": 0.15},
        {"name": "usd_cpi_surprise_z", "participant": "macro repricing", "data": "events.parquet", "weight_design": 0.15},
        {"name": "etf_flows", "participant": "spot ETF flows (institutional)", "data": "MISSING (Farside/SoSoValue)", "weight_design": 0.15},
    ],
}

# ---------- inventory from disk ----------
def norm_info():
    out = {}
    n = BASE / "market-data/normalized"
    for d in sorted(os.listdir(n)):
        if d == "manifest.csv" or d.endswith(".json"):
            continue
        p = n / d
        files = sorted(os.listdir(p))
        info = {}
        for f in files:
            if f.endswith(".parquet"):
                try:
                    df = pd.read_parquet(p / f)
                    info[f] = {"rows": int(len(df)),
                               "from": str(df.index[0])[:10], "to": str(df.index[-1])[:10]}
                except Exception:
                    info[f] = "unreadable"
        out[d] = info
    return out


def raw_commodities():
    out = {}
    r = BASE / "market-data/raw/yahoo"
    for f in sorted(os.listdir(r)):
        if f.startswith("COMM_") and f.endswith(".csv"):
            hdr = (r / f).read_text(encoding="utf-8", errors="replace").splitlines()[0]
            if "date" not in hdr:
                continue
            df = pd.read_csv(r / f, parse_dates=["date"])
            out[f] = {"rows": int(len(df)), "from": str(df["date"].iloc[0])[:10],
                      "to": str(df["date"].iloc[-1])[:10]}
    return out


def fundamentals():
    out = {}
    f = BASE / "market-data/fundamentals"
    for fn in sorted(os.listdir(f)):
        if fn.endswith(".csv") and fn != "manifest.csv":
            try:
                df = pd.read_csv(f / fn)
                dcol = "date" if "date" in df.columns else "observation_date"
                df[dcol] = pd.to_datetime(df[dcol])
                out[fn] = {"rows": int(len(df)), "from": str(df[dcol].iloc[0])[:10],
                           "to": str(df[dcol].iloc[-1])[:10]}
            except Exception as e:
                out[fn] = f"unreadable: {e}"
    return out


def events_summary():
    ev = pd.read_parquet(BASE / "market-data/events/events.parquet")
    ev["date_utc"] = pd.to_datetime(ev["date_utc"], utc=True)
    return {"rows": int(len(ev)),
            "from": str(ev["date_utc"].min())[:10], "to": str(ev["date_utc"].max())[:10],
            "currencies": sorted(ev["currency"].dropna().unique().tolist()),
            "with_actual_forecast": int((ev["actual"].notna() & ev["forecast"].notna()).sum())}


def main():
    shelf = {
        "schema_version": "1.0",
        "generated": "2026-08-11",
        "digestion_note": ("Raw CSVs -> market-data/raw; FRED/events -> fundamentals+events; "
                           "price bars normalized to market-data/normalized/<ASSET>/; "
                           "strategy loaders (load_d1, load_ratio, load_big_events) feed the "
                           "battery pipeline. No unified ingest layer yet — bookshelf is the map."),
        "categories": {
            "Physical & Commodities": ["GOLD", "SILVER", "OIL", "GSR"] + [k for k in raw_commodities()],
            "FX (7 USD majors + crosses)": ["AUDJPY", "AUDUSD", "EURCHF", "EURGBP", "EURJPY", "EURUSD",
                                            "GBPJPY", "GBPUSD", "NZDUSD", "USDCAD", "USDCHF", "USDJPY"],
            "Equities & Indices": ["SP500", "NDX", "IPO universe (844 names, 2020-25, adjclose)"],
            "Digital": ["BTCUSD"],
            "Rates & Macro (factor side)": ["policy_rates (8 ccy)", "yields (8 ccy)", "CPI (8 ccy)",
                                            "events.parquet (84k+)", "oil_wti (FRED)"],
        },
        "asset_prices": norm_info(),
        "commodity_prices_raw": raw_commodities(),
        "fundamentals": fundamentals(),
        "events": events_summary(),
        "mechanism_factors": MECH,
        "weights_note": ("weight_final = 0.4 * weight_design (mechanism) + 0.6 * weight_hist "
                         "(historical calibration from weight_calibrator.py), renormalised. "
                         "Assets without historical calibration keep weight_design, flagged."),
    }
    out = BASE / "market-data/bookshelf"
    out.mkdir(exist_ok=True)
    with open(out / "bookshelf.json", "w") as fh:
        json.dump(shelf, fh, indent=2)
    print("bookshelf written:", out / "bookshelf.json")
    print("assets on disk:", len(shelf["asset_prices"]),
          "| commodity raws:", len(shelf["commodity_prices_raw"]),
          "| events:", shelf["events"]["rows"])


if __name__ == "__main__":
    main()
