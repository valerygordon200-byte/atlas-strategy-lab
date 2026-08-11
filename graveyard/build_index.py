#!/usr/bin/env python3
"""graveyard/build_index.py — P2: assemble the graveyard (kill-history) store.

Reads the verified kill records and writes graveyard/data/{id}.json entry
files plus graveyard/index.json (the searchable spine of the product's
honesty story). Every entry carries: hypothesis, mechanism claim, forced
participant (or explicit 'none found' — that absence is itself the kill
reason), data, tests run, kill criterion, post-mortem, killed date, source.

Run:  python graveyard/build_index.py
"""
from __future__ import annotations

import json
import os
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GY = os.path.join(ROOT, "graveyard")
DATA = os.path.join(GY, "data")

SCHEMA = {
    "schema_version": 1,
    "fields": ["id", "name", "family", "mechanism_claim",
               "forced_participant", "data", "tests_run", "kill_criterion",
               "post_mortem", "killed_date", "source", "headline", "status"],
}

# --------------------------------------------------------------------------
# The entries. Numbers come only from verified reports (cited per entry).
# --------------------------------------------------------------------------
ENTRIES = [
    dict(
        id="seasonal-lean-hogs-aug",
        name="Lean Hogs August SHORT (commodity seasonal)",
        family="calendar-forced hedging",
        mechanism_claim="Hog producers must move hogs before summer heat; packers buy at a fixed calendar cadence.",
        forced_participant="Named: hog producers/packers (biological calendar). BUT the effect did not survive the roll check — see post-mortem.",
        data="Yahoo =F continuous front-month, 2000-2026 daily OHLC; roll-decomposed front/back/gap legs.",
        tests_run=["305-cell selection 2000-2014 |t|>2", "blind holdout 2015-2026 net of spread+financing", "roll decomposition (legA held path / legB back path / roll gap)", "golden regression lock"],
        kill_criterion="Roll artifact: apparent edge lives in the roll discontinuity, not in any capturable held position.",
        post_mortem="Continuous series: -13.62% mean, t=-7.53 (looks like a gift). Decomposed: real held-position path -0.03%, t=-0.02 (a coin flip); the roll gap itself carries -13.59%, t=-10.99. The 'edge' was the cost of splicing contracts, never a tradeable return. A short in August on the continuous series is not a short in the contract that is live in August.",
        killed_date="2026-08-11",
        source="reports/SEASONAL_VERDICT.md; E:/forex-data/scripts/hog_august_roll_check; golden_regressions.py",
        headline="continuous -13.62% t-7.53 -> real path -0.03% t-0.02 (roll gap -13.59% t-10.99)",
        status="dead",
    ),
    dict(
        id="seasonal-commodities-28",
        name="All 28 commodity-month seasonals, clean test",
        family="calendar-forced hedging",
        mechanism_claim="Recurring monthly price patterns from forced physical-calendar flows (harvests, blends, seasons).",
        forced_participant="Candidates named per cell, but see result: 0/28 significant on the roll-adjusted test.",
        data="26 instruments x 12 months = 312 cells; Yahoo =F continuous; roll-adjusted returns.",
        tests_run=["312-cell clean roll-adjusted test", "per-cell |t| threshold", "roll-resistance check"],
        kill_criterion="0/28 significant once returns are roll-adjusted and tradeable — the entire family is void.",
        post_mortem="The flagship (Aug hogs) died to the roll artifact; the clean test confirmed the whole family follows. The apparent edge was construction, not market. Do not re-test any single-instrument calendar effect.",
        killed_date="2026-08-11",
        source="reports/SEASONAL_VERDICT.md; campaign brief step 1 roll-adjusted re-run",
        headline="0/28 significant on clean roll-adjusted test — seasonal catalog is void",
        status="dead",
    ),
    dict(
        id="seasonal-portfolio-35",
        name="35-selection seasonal portfolio at $100 (naive)",
        family="calendar-forced hedging (portfolio construction)",
        mechanism_claim="Diversified seasonal basket at $100 compounded.",
        forced_participant="n/a — construction test, not mechanism test.",
        data="Same seasonal universe; $100 starting capital, $100 min notional, platform margin rules.",
        tests_run=["$100 compounded simulation, all 35 selections every year"],
        kill_criterion="Account blown: equity -$1.93 by 2015-09, Sharpe -2.76, max DD -101.9%.",
        post_mortem="The $100 minimum with ~9 concurrent positions forces ~9x gross leverage (280 months forced oversizing). At $100 the platform cap allows 6-8 trades/yr, not 35. A portfolio built without the account-size constraint is untradeable by construction.",
        killed_date="2026-08-11",
        source="reports/SEASONAL_VERDICT.md (Version A)",
        headline="blown account in 8 months at $100; Sharpe -2.76 — untradeable construction",
        status="dead",
    ),
    dict(
        id="fx-donchian-breakout",
        name="Donchian Channel Breakout (Turtle-style)",
        family="breakout",
        mechanism_claim="Trend following on channel breaks, classic Turtle rules.",
        forced_participant="None found. Trend followers are voluntary; no one is forced to transact.",
        data="12 FX pairs D1+H1, 2016-2026, 13,655 backtest trades.",
        tests_run=["registry backtest battery", "IS/OOS split", "strict cost model"],
        kill_criterion="OOS median Sharpe negative (-0.484); best-pair Sharpe 0.297 in-sample decays to negative OOS.",
        post_mortem="Directional breakout systems fade after publication (this project's graveyard rule). No forced participant, no survival.",
        killed_date="2026-08-06",
        source="E:/forex-data/strategies/registry.parquet (donchian-breakout)",
        headline="IS best Sharpe 0.297 -> OOS median -0.484",
        status="dead",
    ),
    dict(
        id="fx-pin-bar-reversal",
        name="Pin Bar / Hammer Reversal",
        family="price-action",
        mechanism_claim="Single-candle rejection patterns predict reversal.",
        forced_participant="None found.",
        data="12 FX pairs, 4,482 backtest trades.",
        tests_run=["registry backtest battery", "IS/OOS split", "strict cost model"],
        kill_criterion="OOS median Sharpe -1.437; IS best 0.662 is noise.",
        post_mortem="Chart patterns without a mechanism and without a forced participant. The IS edge is in-sample noise (as the permutation stages confirm).",
        killed_date="2026-08-06",
        source="E:/forex-data/strategies/registry.parquet (pin-bar-reversal)",
        headline="IS 0.662 -> OOS median -1.437",
        status="dead",
    ),
    dict(
        id="fx-harami-pullback",
        name="Harami Pullback Entry",
        family="price-action",
        mechanism_claim="Candlestick pullback continuation.",
        forced_participant="None found.",
        data="12 FX pairs, 4 backtest trades.",
        tests_run=["registry backtest battery"],
        kill_criterion="Insufficient sample (4 trades) — statistically meaningless.",
        post_mortem="Nothing to believe: 4 trades cannot support any claim. Registry status: insufficient-sample.",
        killed_date="2026-08-06",
        source="E:/forex-data/strategies/registry.parquet (harami-pullback)",
        headline="4 trades total — insufficient sample",
        status="dead",
    ),
    dict(
        id="fx-cross-sectional-momentum",
        name="Cross-sectional momentum on FX pairs",
        family="momentum",
        mechanism_claim="Rank pairs by trailing return, buy the leaders.",
        forced_participant="None found.",
        data="12 FX pairs D1, 2016-2026.",
        tests_run=["full strict battery", "permutation", "walk-forward"],
        kill_criterion="Fails OOS; graveyard-listed.",
        post_mortem="Directional momentum is competed away fast (documented post-publication decay). No forced flow sustains it.",
        killed_date="2026-08-08",
        source="EDGE-FINDING MASTER PLAN graveyard; fx_campaign results",
        headline="dead per project graveyard (no OOS hold)",
        status="dead",
    ),
    dict(
        id="fx-day-of-week-turn-of-month",
        name="Day-of-week / turn-of-month calendar effects",
        family="calendar",
        mechanism_claim="Recurring weekday/month-boundary FX patterns.",
        forced_participant="None named — retail calendar folklore.",
        data="12 FX pairs D1, 2016-2026.",
        tests_run=["full strict battery"],
        kill_criterion="No consistent OOS effect on liquid FX.",
        post_mortem="Calendar patterns on major FX are arbitraged; graveyard-listed.",
        killed_date="2026-08-08",
        source="EDGE-FINDING MASTER PLAN graveyard",
        headline="dead",
        status="dead",
    ),
    dict(
        id="fx-dollar-basket-underreaction",
        name="Dollar-basket EUR/USD news under-reaction",
        family="informed under-reaction",
        mechanism_claim="US releases move the dollar; markets under-react to genuine surprises.",
        forced_participant="Mechanism plausible (hedgers forced to reprice), but the test failed — see post-mortem.",
        data="Forex Factory event archive; 5-pair basket; EURUSD execution leg.",
        tests_run=["404-cell campaign", "surprise z vs basket move", "momentum control arm", "strict battery"],
        kill_criterion="1/404 full-pass initially; per-pair evaluation after a concatenation bug fix — the apparent signal was a construction artifact (all pairs aggregated into one frame).",
        post_mortem="The first-pass 'survivor' was a bug: sizez/volman/streak builders concatenated all 5 pairs, so each 'pair' row was the same aggregate. Fixed to per-pair evaluation: 404 honest tests, no surviving full-pass candidate. The failure was real per-pair null, not just a proxy problem.",
        killed_date="2026-08-11",
        source="fx_campaign_round2.py; fx_strict_battery.py; campaign reports",
        headline="404 tests, 1 artifact 'pass' -> 0 after per-pair fix",
        status="dead",
    ),
    dict(
        id="fx-breakout-family",
        name="Opening-range / Dual Thrust / London breakouts",
        family="breakout",
        mechanism_claim="Range breaks carry momentum.",
        forced_participant="None found.",
        data="12 FX pairs D1, 2016-2026.",
        tests_run=["full strict battery", "walk-forward"],
        kill_criterion="Fades out-of-sample; graveyard-listed.",
        post_mortem="All directional breakout systems tested in this project fade rather than follow.",
        killed_date="2026-08-08",
        source="EDGE-FINDING MASTER PLAN graveyard",
        headline="dead",
        status="dead",
    ),
    dict(
        id="fx-single-instrument-momentum",
        name="Single-instrument time-series momentum / trend-following",
        family="momentum",
        mechanism_claim="Trend persistence on one instrument.",
        forced_participant="None found.",
        data="12 FX pairs D1, 2016-2026.",
        tests_run=["full strict battery"],
        kill_criterion="Decays sharply post-publication (Sharpe 0.96 -> 0.04 documented for the published variant).",
        post_mortem="Genuinely strong in-sample, genuinely gone out-of-sample. The canonical case of an edge being arbitraged the moment it is published.",
        killed_date="2026-08-08",
        source="EDGE-FINDING MASTER PLAN graveyard; prior momentum tests",
        headline="dead — published edges decay",
        status="dead",
    ),
    dict(
        id="fx-cot-standalone",
        name="COT positioning as a standalone signal",
        family="positioning",
        mechanism_claim="Commercial positioning predicts price.",
        forced_participant="Commercials are the forced participants — but the public report is too lagged and too crowded to trade.",
        data="COT weekly reports, FX, 2016-2026.",
        tests_run=["full strict battery"],
        kill_criterion="No standalone OOS edge.",
        post_mortem="The mechanism is real (commercials ARE forced) but the signal is public, weekly, and lagged — everyone trades it, so it prices the information before you can. Mechanism real, tradeability zero.",
        killed_date="2026-08-08",
        source="EDGE-FINDING MASTER PLAN graveyard",
        headline="dead as standalone signal",
        status="dead",
    ),
    dict(
        id="fx-volume-directional",
        name="Volume as a directional predictor",
        family="volume",
        mechanism_claim="Volume precedes price direction.",
        forced_participant="None — volume reflects participation, it forces nothing.",
        data="12 FX pairs D1, 2016-2026.",
        tests_run=["full strict battery"],
        kill_criterion="Volume predicts move SIZE, not direction — confirmed null for direction.",
        post_mortem="A rare confirmed-positive: volume DOES predict the size of future moves (validated with real t-stats), and is null for direction. Repurposed as a risk-sizing input, never an entry signal.",
        killed_date="2026-08-08",
        source="EDGE-FINDING MASTER PLAN graveyard; VOL_MODULE.md",
        headline="null for direction; valid for size (risk-sizing only)",
        status="dead",
    ),
    dict(
        id="fx-weekend-crypto",
        name="Weekend crypto move -> FX prediction",
        family="cross-asset",
        mechanism_claim="Weekend crypto moves leak into Monday FX.",
        forced_participant="None found.",
        data="BTCUSD + FX pairs D1.",
        tests_run=["full strict battery"],
        kill_criterion="No OOS effect.",
        post_mortem="Graveyard-listed after failed test.",
        killed_date="2026-08-08",
        source="EDGE-FINDING MASTER PLAN graveyard",
        headline="dead",
        status="dead",
    ),
    dict(
        id="fx-bollinger-mean-reversion",
        name="Bollinger-band mean reversion (single instrument)",
        family="mean-reversion",
        mechanism_claim="Price reverts to the band.",
        forced_participant="None — without a cointegration structure there is no reason for the level to revert.",
        data="12 FX pairs D1, 2016-2026.",
        tests_run=["full strict battery"],
        kill_criterion="Fails OOS without cointegration; graveyard-listed.",
        post_mortem="Single-instrument band reversion is not mean reversion — it is gambling on a level with no anchor. The cointegration variants (spreads with a real economic link) remain untested/eligible.",
        killed_date="2026-08-08",
        source="EDGE-FINDING MASTER PLAN graveyard",
        headline="dead (single-instrument; no cointegration)",
        status="dead",
    ),
    dict(
        id="campaign-tier1-flows",
        name="Index reconstitution / witching / LETF decay / window dressing",
        family="structurally-forced flows",
        mechanism_claim="Index add/drop, expiry close-outs, LETF daily rebalancing, quarter-end window dressing create forced flows.",
        forced_participant="Named per mechanism (index funds, LETF issuers, fund managers) — but tested and killed in the 30-candidate campaign.",
        data="Russell reconstitution dates, witching dates, leveraged ETF pairs, IPO lockups; yfinance.",
        tests_run=["30-candidate campaign", "full strict battery", "event studies"],
        kill_criterion="No candidate survived the full pipeline; campaign verdict = no promoted survivors.",
        post_mortem="The mechanisms are real (these ARE forced flows) but the effects are either already priced (crowded, e.g. witching) or too small after costs (IPO lockups: 844-name sample, no OOS edge strong enough). Real mechanism does not guarantee a tradeable residual.",
        killed_date="2026-08-11",
        source="reports/campaign_30_verdict.md; TRACK_A/B/C reports",
        headline="0 survivors from the 30-candidate campaign",
        status="dead",
    ),
    dict(
        id="spreads-crush-crack-feed",
        name="Crush / crack / hog-corn feed spreads",
        family="relative-value / statistical arbitrage",
        mechanism_claim="Processor margins (soybean crush, crude crack, hog-corn feed) mean-revert around an economic anchor.",
        forced_participant="Named: processors must hedge margins (forced flows on both legs).",
        data="Continuous + individual contract legs; roll-resistance tested both ways.",
        tests_run=["roll-resistance check (two constructions)", "Engle-Granger cointegration IS+OOS", "full strict battery"],
        kill_criterion="Campaign verdict: no spread candidate survived the full pipeline on the roll-resistant construction.",
        post_mortem="The mechanisms are the project's strongest (genuine forced hedgers) but the tradable residual did not survive: cointegration not stable OOS, or net edge below 2x round-trip cost after two legs of spread + financing. Roll-resistance check ran before any number was trusted (per the standing rule).",
        killed_date="2026-08-11",
        source="reports/TRACK_A_SPREADS.md",
        headline="0/4 spreads survived the pipeline",
        status="dead",
    ),
]

# --------------------------------------------------------------------------
# Build
# --------------------------------------------------------------------------
def main() -> None:
    os.makedirs(DATA, exist_ok=True)
    index = {
        "schema_version": SCHEMA["schema_version"],
        "built": date.today().isoformat(),
        "count": len(ENTRIES),
        "families": sorted({e["family"] for e in ENTRIES}),
        "status_counts": {s: sum(1 for e in ENTRIES if e["status"] == s)
                          for s in sorted({e["status"] for e in ENTRIES})},
        "entries": [],
    }
    for e in ENTRIES:
        missing = [f for f in SCHEMA["fields"] if f not in e]
        assert not missing, f"{e['id']}: missing fields {missing}"
        path = os.path.join(DATA, f"{e['id']}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(e, f, indent=2, ensure_ascii=False)
        index["entries"].append(
            {k: e[k] for k in ("id", "name", "family", "status",
                               "killed_date", "headline", "source")})
    with open(os.path.join(GY, "index.json"), "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2, ensure_ascii=False)
    print(f"wrote {len(ENTRIES)} entries -> graveyard/data/")
    print(f"wrote graveyard/index.json (families: {len(index['families'])})")
    print(f"status counts: {index['status_counts']}")


if __name__ == "__main__":
    main()
