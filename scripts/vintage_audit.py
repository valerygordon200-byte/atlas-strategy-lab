"""Vintage audit — verify stored event actuals are as-published, not revisions.

Self-contained (no network needed except the optional EIA comparison, which
reads a saved copy of the current-vintage weekly crude stocks CSV).

Checks:
  1. US GDP "advance" estimates vs documented as-published prints (21 releases,
     2020-2025) — the BEA revises each estimate twice, so a match proves the
     store holds the original print, not the final revision.
  2. Famous, heavily-revised prints: NFP Mar-2020 (-701K), NFP Apr-2020
     (-20.5M), NFP Apr-2021 (+266K), CPI May-2022 (+8.6%).
  3. EIA weekly commercial crude stocks changes vs the CURRENT vintage —
     weeks where the store differs from the current vintage while matching the
     as-published print (e.g. April 2020) prove the store is not the archive.

Usage: point EVENTS_PARQUET at the event store and run:
    python scripts/vintage_audit.py
"""

import pandas as pd

EVENTS_PARQUET = "../market-data/events/events.parquet"
EIA_CSV = "../reports/vintage_data/eia_current_commercial_crude.csv"

# (title, release_date, as_published_value) — documented, heavily-revised prints
KNOWN_PRINTS = [
    ("GDP Growth Rate QoQ Adv", "2020-04-29", -4.8),
    ("GDP Growth Rate QoQ Adv", "2020-07-30", -32.9),
    ("GDP Growth Rate QoQ Adv", "2020-10-29", 33.1),
    ("GDP Growth Rate QoQ Adv", "2021-01-28", 4.0),
    ("GDP Growth Rate QoQ Adv", "2021-04-29", 6.4),
    ("GDP Growth Rate QoQ Adv", "2021-07-29", 6.5),
    ("GDP Growth Rate QoQ Adv", "2021-10-28", 2.0),
    ("GDP Growth Rate QoQ Adv", "2022-01-27", 6.9),
    ("GDP Growth Rate QoQ Adv", "2022-04-28", -1.4),
    ("GDP Growth Rate QoQ Adv", "2022-07-28", -0.9),
    ("GDP Growth Rate QoQ Adv", "2022-10-27", 2.6),
    ("GDP Growth Rate QoQ Adv", "2023-01-26", 2.9),
    ("GDP Growth Rate QoQ Adv", "2023-04-27", 1.1),
    ("GDP Growth Rate QoQ Adv", "2023-07-27", 2.4),
    ("GDP Growth Rate QoQ Adv", "2023-10-26", 4.9),
    ("GDP Growth Rate QoQ Adv", "2024-01-25", 3.3),
    ("GDP Growth Rate QoQ Adv", "2024-04-25", 1.6),
    ("GDP Growth Rate QoQ Adv", "2024-07-25", 2.8),
    ("GDP Growth Rate QoQ Adv", "2024-10-30", 2.8),
    ("GDP Growth Rate QoQ Adv", "2025-01-30", 2.3),
    ("GDP Growth Rate QoQ Adv", "2025-04-30", -0.3),
    ("Non Farm Payrolls", "2020-04-03", -701.0),
    ("Non Farm Payrolls", "2020-05-08", -20500.0),
    ("Non Farm Payrolls", "2021-05-07", 266.0),
    ("Inflation Rate YoY", "2022-06-10", 8.6),
]


def main():
    ev = pd.read_parquet(EVENTS_PARQUET)
    ev["date_utc"] = pd.to_datetime(ev["date_utc"], utc=True)

    ok = tot = 0
    for title, date, expected in KNOWN_PRINTS:
        rows = ev[(ev["title"] == title)
                  & (ev["date_utc"].dt.strftime("%Y-%m-%d") == date)]
        if not len(rows):
            print(f"  MISSING  {title} {date}")
            continue
        actual = rows.iloc[0]["actual"]
        if pd.isna(actual):
            print(f"  NO ACTUAL {title} {date}")
            continue
        tot += 1
        match = abs(actual - expected) < 0.05
        ok += match
        print(f"  {'OK ' if match else 'BAD'}  {title} {date}: store={actual} "
              f"as-published={expected}")

    print(f"\nKnown as-published prints: {ok}/{tot} match")

    # Optional EIA current-vintage comparison
    try:
        eia = pd.read_csv(EIA_CSV)
    except FileNotFoundError:
        print("\nEIA comparison skipped (CSV not present)")
        return

    eia["date"] = pd.to_datetime(eia["date"], format="%Y-%m-%d", errors="coerce")
    eia = eia.dropna().sort_values("date").drop_duplicates("date")
    eia["change_M"] = eia["stocks_kb"].diff() / 1000.0

    st = ev[(ev["title"] == "EIA Crude Oil Stocks Change")
            & ev["actual"].notna()].copy()
    st["d"] = st["date_utc"].dt.tz_localize(None).dt.normalize()

    def friday(day):
        for lag in range(1, 8):  # strictly before the release day
            cand = day - pd.Timedelta(days=lag)
            if cand.weekday() == 4:
                return cand
        return None

    st["friday"] = st["d"].apply(friday)
    m = st.merge(eia[["date", "change_M"]], left_on="friday",
                 right_on="date", how="left").dropna(subset=["change_M"])
    m["absdiff"] = (m["actual"] - m["change_M"]).abs()
    print(f"\nEIA crude stocks vs CURRENT vintage ({len(m)} weeks): "
          f"exact {int((m['absdiff'] < 0.05).sum())}, "
          f"diff>=0.5M {int((m['absdiff'] >= 0.5).sum())} — weeks that differ "
          f"from the current vintage while matching the as-published print "
          f"(e.g. Apr 2020) prove the store is not the archive.")


if __name__ == "__main__":
    main()
