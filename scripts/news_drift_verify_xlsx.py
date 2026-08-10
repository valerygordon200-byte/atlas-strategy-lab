#!/usr/bin/env python3
"""Verify USDJPY_news_drift_verification.xlsx with the REAL Excel engine (COM).

1. Recalculate (CalculateFull) TWICE and confirm identical output (brief 3.4).
2. Compare every computed z / trigger / net cell against the python ground
   truth (the strategy's own numbers, verified against fx_strict_battery.csv).
3. Print manual hand-check rows with raw arithmetic (brief 3.3).
"""
import json
import math
import sys

import win32com.client as w

XLSX = r"E:\forex-data\reports\USDJPY_news_drift_verification.xlsx"
JSON = "E:/forex-data/reports/news_drift_per_event.json"

recs = json.load(open(JSON))
row2rec = {r["sheet_row"]: r for r in recs}
maxrow = max(row2rec) + 6

xl = w.Dispatch("Excel.Application")
xl.Visible = False
xl.DisplayAlerts = False
wb = xl.Workbooks.Open(XLSX)

ERR = -2146826246  # Excel #N/A HRESULT as returned by COM (probed)


def col(sheet, letter):
    """Read a column as {row: value}, translating Excel errors -> 'NA'."""
    rng = wb.Sheets(sheet).Range(f"{letter}1:{letter}{maxrow}")
    vals = rng.Value
    out = {}
    for i, v in enumerate(vals, start=1):
        x = v[0] if isinstance(v, tuple) else v
        if x is None or x == "":
            out[i] = None
        elif isinstance(x, int) and x == ERR:
            out[i] = "NA"
        elif isinstance(x, float) and math.isnan(x):
            out[i] = None
        else:
            out[i] = x
    return out


try:
    def grab():
        return {
            "z": col("Z-Score Calc", "I"),
            "trig": col("Z-Score Calc", "J"),
            "fb": col("Trigger Check", "B"),
            "fc": col("Trigger Check", "C"),
            "fi": col("Trigger Check", "I"),
            "fk": col("Trigger Check", "K"),
        }

    xl.CalculateFull()
    a = grab()
    xl.CalculateFull()
    b = grab()

    # ---- 3.4 recalc twice, identical?
    diffs = 0
    for k in a:
        for r in a[k]:
            if a[k][r] != b[k][r]:
                diffs += 1
    print(f"RECALC TWICE: {'IDENTICAL' if diffs == 0 else f'{diffs} DIFFERENCES'}")

    # ---- compare vs python ground truth
    z_bad = trig_bad = fb_bad = net_bad = move_bad = 0
    z_max = 0.0
    net_max = 0.0
    for r, rec in row2rec.items():
        ez = a["z"].get(r)
        pz = rec["z"]
        # blank/NA in Excel <-> NaN/insufficient-history in python
        if ez is None or ez == "NA":
            ok = pz is None
        elif pz is None:
            ok = False
        else:
            ok = abs(float(ez) - pz) < 1e-9
            z_max = max(z_max, abs(float(ez) - pz))
        if not ok:
            z_bad += 1

        et = a["trig"].get(r)
        pt = rec["trigger"]
        if (et or "") != (pt or ""):
            trig_bad += 1

        fb = a["fb"].get(r)   # formula trigger (mirror of Z-Score Calc J)
        fc = a["fc"].get(r)   # reported trigger
        if (fb or "") != (fc or ""):
            fb_bad += 1
        if (fb or "") != (pt or ""):
            fb_bad += 1

        # net is only meaningful where the strategy actually trades:
        # triggered rows with a measurable next-day return
        if rec["trigger"] == "TRIGGER" and rec["r"] is not None:
            pn = rec["net"]
            en = a["fk"].get(r)
            if en is None or en == "NA" or abs(float(en) - pn) > 1e-9:
                net_bad += 1
            else:
                net_max = max(net_max, abs(float(en) - pn))
            pm = rec["r"]
            em = a["fi"].get(r)
            if em is None or em == "NA" or abs(float(em) - pm) > 1e-9:
                move_bad += 1

    n = len(row2rec)
    print(f"Z vs python: {n - z_bad}/{n} match (max |diff| {z_max:.2e})")
    print(f"Trigger vs python: {n - trig_bad}/{n} match")
    print(f"Formula-vs-reported trigger (Trigger Check B vs C): "
          f"{n - fb_bad}/{n} match")
    net_n = sum(1 for r in row2rec.values()
                if r["trigger"] == "TRIGGER" and r["r"] is not None)
    print(f"Net% formula vs python (triggered rows): {net_n - net_bad}/{net_n} match "
          f"(max |diff| {net_max:.2e})")
    print(f"Raw move formula vs python (triggered rows): {net_n - move_bad}/{net_n} match")
    print(f"MISMATCHES: z={z_bad} trigger={trig_bad} BvsC={fb_bad} "
          f"net={net_bad} move={move_bad}")

    # ---- manual hand-check rows (exact values out of Excel)
    print("\n=== EXCEL HAND-CHECK ROWS (z & trigger cells) ===")
    show = []
    for r, rec in row2rec.items():
        if rec["title"] in ("Non Farm Payrolls", "Initial Jobless Claims") and \
           rec["date"] in ("2016-09-02", "2026-08-07", "2015-05-28", "2026-08-06"):
            show.append((r, rec))
    for r, rec in show:
        ez = a["z"].get(r)
        et = a["trig"].get(r)
        print(f"row {r} | {rec['title']} | {rec['date']} | "
              f"Excel z={ez} | python z={rec['z']} | "
              f"Excel trigger={et!r} | reported={rec['trigger']!r}")
finally:
    wb.Close(False)
    xl.Quit()
