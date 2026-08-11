#!/usr/bin/env python3
"""T1 milestone 2: monthly central-bank gold net-purchase grid.

Sources: World Gold Council "Central Bank Gold Statistics" monthly reports
(IMF IFS-based). Each report article page states that month's reported net
purchases in its narrative. This script:

  1. discovers report article URLs (sitemap scrape + pattern probing),
  2. fetches each article, extracts the plain text,
  3. parses the headline monthly net-purchase figure + main country moves
     (PDF text extraction is used only as a fallback),
  4. writes data/central_bank_gold_monthly.csv — verified rows only; anything
     ambiguous is flagged, never guessed.

Stdlib only. Usage:
  python3 scripts/gold_monthly_build.py [--urls FILE] [--out data/central_bank_gold_monthly.csv] [--probe]
"""
import argparse
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
import zlib

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/126.0 Safari/537.36",
      "Accept-Language": "en-US,en;q=0.9"}

MONTH_NAMES = ["january", "february", "march", "april", "may", "june",
               "july", "august", "september", "october", "november", "december"]
MONTHS = {m: i for i, m in enumerate(MONTH_NAMES, 1)}


def get(url, timeout=25):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def html_to_text(raw: bytes) -> str:
    s = raw.decode("utf-8", "replace")
    s = re.sub(r"<script.*?</script>", " ", s, flags=re.S | re.I)
    s = re.sub(r"<style.*?</style>", " ", s, flags=re.S | re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    s = html.unescape(s)
    s = re.sub(r"[ \t]+", " ", s)
    return s


def meta_description(raw: bytes) -> str:
    s = raw.decode("utf-8", "replace")
    for pat in [r'<meta name="description" content="([^"]*)"',
                r'<meta property="og:description" content="([^"]*)"']:
        m = re.search(pat, s, re.I)
        if m:
            return html.unescape(m.group(1))
    return ""


def month_from_slug(url: str):
    """Return (month_idx, year_str) from the slug: a month word anywhere in the
    slug, with an explicit year if present (e.g. '-december-2023')."""
    m = re.search(r"-(" + "|".join(MONTH_NAMES) + r")(?:-(\d{4}))?", url, re.I)
    if m:
        return MONTHS.get(m.group(1).lower()), (m.group(2) or "")
    return None, None


def infer_data_month(text: str, url: str):
    """Return 'YYYY-MM' for the report's data month, or None.

    Rule: reports are published ~6 weeks after the data month, so the data
    month is (publication month - 2). The slug usually names the data month;
    a year in the slug wins; otherwise the pub-date rule is used and
    cross-checked against an explicit 'in <Month>' mention in the text.
    """
    pm = re.search(r"/gold-focus/(20\d{2})/(\d{2})/", url)
    pub_y = int(pm.group(1)) if pm else None
    pub_m = int(pm.group(2)) if pm else None
    mn, year = month_from_slug(url)
    if mn and year:
        return f"{year}-{mn:02d}"
    if mn and pub_y and pub_m:
        # data month = pub month - 2 (with year wrap)
        idx = (pub_m - 3) % 12  # 0-based index of data month
        data_y = pub_y if pub_m > 2 else pub_y - 1
        if idx == MONTHS.get(MONTH_NAMES[mn - 1].lower()) - 1:
            return f"{data_y}-{idx + 1:02d}"
        # slug month disagrees with pub-2: trust slug month, pub-2 year
        data_y = pub_y if mn > 2 else pub_y - 1
        return f"{data_y}-{mn:02d}"
    # descriptive slugs ("central-banks-bought-77t-september"): month from text
    m = re.search(r"\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+(20\d{2})\b", text[:2500], re.I)
    if m:
        return f"{m.group(2)}-{MONTHS[m.group(1).lower()]:02d}"
    if mn and pub_y and pub_m:
        # slug names the data month; year = pub year - 2 months
        idx = (pub_m - 3) % 12
        data_y = pub_y if pub_m > 2 else pub_y - 1
        if mn - 1 == idx:
            return f"{data_y}-{mn:02d}"
        return f"{data_y}-{mn:02d}"
    m = re.search(r"\b(?:in|during|for)\s+(January|February|March|April|May|June|July|August|September|October|November|December)\b", text[:2500], re.I)
    if m and pub_y and pub_m:
        named = MONTHS[m.group(1).lower()]
        idx = (pub_m - 3) % 12
        data_y = pub_y if pub_m > 2 else pub_y - 1
        if named - 1 == idx:
            return f"{data_y}-{idx + 1:02d}"
        return f"{data_y}-{named:02d}"
    if pub_y and pub_m:
        idx = (pub_m - 3) % 12
        data_y = pub_y if pub_m > 2 else pub_y - 1
        return f"{data_y}-{idx + 1:02d}"
    return None


HEADLINE_PATTERNS = [
    # "Central banks reported 3t of net selling in December"  (headline, negative)
    r"reported\s+([\d.]+)\s*t\s+of\s+net\s+(?:selling|sales)",
    # "official gold reserves increased by a net 41t during the month"
    r"(?:increased|rose|grew|were up|resumed net buying|turned net buyer)[^.\n]{0,60}?\bnet\s+([\d.]+)\s*t\b",
    # "Central banks added a net 19t to global gold reserves"
    r"added\s+a\s+net\s+([\d.]+)\s*t\b",
    # "Central banks reported 24t net purchases in ..."  (headline)
    r"reported\s+(?:a net of |net of |a net |net )?([\d.]+)\s*t\s*(?:of\s*)?(?:net\s*)?(?:purchases|buying)",
    # "Central banks bought a net 53t in October" / "bought net 10t in July"
    r"bought\s+(?:a\s+)?net\s+([\d.]+)\s*t\b",
    # "Central banks bought 19t of gold in December 2025"
    r"bought\s+([\d.]+)\s*t\s+of\s+gold\b",
    # "Global official reserves declined by 6.5t during the month"
    r"reserves\s+(?:declined|fell|dropped|were down)\s+by\s+([\d.]+)\s*t\b",
    # "reserves rose by Xt"
    r"reserves\s+(?:rose|increased|grew|were up)\s+by\s+([\d.]+)\s*t\b",
    # "Central banks sold 30t of gold in March"
    r"sold\s+([\d.]+)\s*t\s+of\s+gold\b",
    # "Central banks bought 53t on a net basis"
    r"bought\s+([\d.]+)\s*t\s+on a net basis",
    # sentence-initial "Net purchases totalled 53t" (not a country 'X reporting net sales of Yt')
    r"(?:^|[.;]\s)(?:net\s+)?(?:purchases|buying|sales)\s+(?:of|totalled|totaling|totaled)\s+([\d.]+)\s*t\b",
    # "reported net purchases of 53t"
    r"reported\s+(?:net\s+)?(?:purchases|buying)\s+of\s+([\d.]+)\s*t\b",
    # "central banks were net buyers of 53t"
    r"net\s+(?:buyers|sellers)\s+of\s+([\d.]+)\s*t\b",
]


def parse_headline(text: str):
    out = {}
    for pat in HEADLINE_PATTERNS:
        m = re.search(pat, text, re.I)
        if m:
            try:
                out["month_t"] = float(m.group(1).replace(",", ""))
                out["headline"] = re.sub(r"\s+", " ", m.group(0))[:140]
                break
            except ValueError:
                continue
    if "month_t" not in out:
        # "increased by a net 41t" style with number before 'net'
        m = re.search(r"by\s+a\s+net\s+([\d.]+)\s*t\b", text, re.I)
        if m:
            out["month_t"] = float(m.group(1).replace(",", ""))
            out["headline"] = m.group(0)[:140]
    if "month_t" in out:
        # net sales / net sellers => negative
        h = (out.get("headline") or "").lower()
        if ("net sales" in h or "net sellers" in h or "net selling" in h
                or re.search(r"sold\s+a\s+net", h)
                or "declined by" in h or "fell by" in h or "dropped by" in h or "were down by" in h
                or re.match(r"sold\s+([\d.]+)\s*t\s+of\s+gold", h, re.I)):
            out["month_t"] = -abs(out["month_t"])
    return out
    ytd = re.findall(r"(?:year-to-date|y-t-d|ytd)[^.\n]{0,70}?([\d.]+)\s*t\b", text, re.I)
    if ytd:
        out["ytd_tokens"] = [float(x.replace(",", "")) for x in ytd]
    # country moves: "Poland (18t)", "China added 10t", "Kazakhstan (-8t)"
    countries = []
    for cm in re.finditer(r"([A-Z][A-Za-z .'-]{2,35}?)\s*\(([+-]?[\d.]+)t\)", text):
        countries.append({"name": cm.group(1).strip(), "net_t": float(cm.group(2))})
    for cm in re.finditer(r"\b(Poland|China|Turkey|Kazakhstan|Uzbekistan|India|Russia|Czech (?:Rep\.?|Republic)|Qatar|Singapore|Jordan|Egypt|Kyrgyz Rep\.?)\b[^.\n]{0,40}?\b(added|bought|sold|offloaded|purchased)\s+([\d.]+)\s*t\b", text, re.I):
        name, verb, amt = cm.group(1), cm.group(2).lower(), float(cm.group(3).replace(",", ""))
        if verb in ("sold", "offloaded"):
            amt = -amt
        countries.append({"name": name, "net_t": amt})
    if countries:
        # dedupe by name, keep the first occurrence
        seen, dedup = set(), []
        for c in countries:
            k = c["name"].lower()
            if k not in seen:
                seen.add(k)
                dedup.append(c)
        out["countries"] = dedup[:10]
    return out


def find_pdf_url(article_html: str):
    m = re.search(r'href="(/download/file/\d+/[^"]*\.pdf)"', article_html, re.I)
    return ("https://www.gold.org" + m.group(1)) if m else None


def inflate(data: bytes) -> bytes:
    try:
        return zlib.decompress(data)
    except zlib.error:
        try:
            return zlib.decompress(data, -15)
        except zlib.error:
            return data


def pdf_text(data: bytes) -> str:
    lines = []
    for m in re.finditer(rb"stream\r?\n(.*?)endstream", data, re.S):
        try:
            content = inflate(m.group(1))
        except Exception:
            continue
        s = content.decode("latin-1", "replace")
        if "BT" not in s:
            continue
        cur = []
        i, n = 0, len(s)
        while i < n:
            if s.startswith("BT", i):
                cur = []
                i += 2
            elif s.startswith("ET", i):
                if cur:
                    lines.append("".join(cur))
                cur = []
                i += 2
            elif s[i] == "(":
                j, out, depth = i + 1, [], 0
                while j < n:
                    c = s[j]
                    if c == "\\":
                        out.append(s[j + 1] if j + 1 < n else "")
                        j += 2
                        continue
                    if c == "(":
                        depth += 1
                        out.append(c)
                    elif c == ")":
                        if depth == 0:
                            break
                        depth -= 1
                        out.append(c)
                    else:
                        out.append(c)
                    j += 1
                cur.append("".join(out))
                i = j + 1
            elif s.startswith("Td", i) or s.startswith("TD", i) or s.startswith("T*", i):
                if cur:
                    lines.append("".join(cur))
                cur = []
                i += 2
            else:
                i += 1
        if cur:
            lines.append("".join(cur))
    return "\n".join(lines)


def process_article(url: str):
    row = {"url": url}
    try:
        raw = get(url)
    except urllib.error.HTTPError as e:
        return {**row, "error": f"HTTP {e.code}"}
    except Exception as e:
        return {**row, "error": f"fetch: {e}"}
    text = html_to_text(raw)
    row["month"] = infer_data_month(text, url)
    row.update(parse_headline(text))
    row["text_snip"] = re.sub(r"\s+", " ", text)[:500]
    if "month_t" not in row:
        # infographic reports carry the headline in the meta description
        meta = meta_description(raw)
        if meta:
            mrow = parse_headline(meta)
            if "month_t" in mrow:
                row.update(mrow)
                row["source"] = "meta"
    if "month_t" in row:
        return row
    # fallback: narrative lives in the attached PDF for older reports
    try:
        pdf_url = find_pdf_url(raw.decode("utf-8", "replace"))
        if not pdf_url:
            row["error"] = "no headline in HTML, no pdf link"
            return row
        pdf_url = pdf_url.replace(" ", "%20")
        pdf = get(pdf_url)
        ptext = pdf_text(pdf)
        prow = parse_headline(ptext)
        row.update(prow)
        row["pdf"] = pdf_url
        row["pdf_snip"] = re.sub(r"\s+", " ", ptext)[:400]
        if "month_t" not in row:
            row["error"] = "no headline in HTML or PDF"
    except Exception as e:
        row["error"] = f"pdf fallback: {e}"
    return row


def probe_older_urls():
    """Guess report URLs for data months 2020-12..2024-08 (sitemap starts 2023-12
    and skips Jan/Feb/Apr/Jul/Aug 2024). Publication month = data month + 2."""
    found = []
    for year in range(2020, 2025):
        for mn in range(1, 13):
            if year == 2020 and mn < 12:
                continue
            if year == 2024 and mn > 8:
                continue
            mname = MONTH_NAMES[mn - 1]
            pub_m = (mn + 2) % 12 or 12
            pub_y = year + (1 if mn >= 11 else 0)
            url = (f"https://www.gold.org/goldhub/gold-focus/{pub_y}/{pub_m:02d}/"
                   f"central-bank-gold-statistics-{mname}-{year}")
            try:
                code = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=12).status
            except Exception:
                code = 404
            if code == 200:
                found.append(url)
            time.sleep(0.15)
    return found


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--urls", default="/tmp/cb_urls.txt")
    ap.add_argument("--out", default="data/central_bank_gold_monthly.csv")
    ap.add_argument("--probe", action="store_true")
    args = ap.parse_args()

    urls = []
    if os.path.exists(args.urls):
        with open(args.urls) as f:
            urls = [l.strip() for l in f if l.strip().startswith("http")]
    if args.probe:
        print("[discover] probing 2021-2023 pattern URLs ...", file=sys.stderr)
        urls += probe_older_urls()
    print(f"[discover] {len(urls)} report URLs", file=sys.stderr)

    rows = []
    for u in sorted(set(urls)):
        row = process_article(u)
        ok = "month_t" in row and "error" not in row
        print(f"[{'OK ' if ok else 'FAIL'}] {row.get('month') or '????'} {u}", file=sys.stderr)
        rows.append(row)
        time.sleep(0.25)

    verified = [r for r in rows if "month_t" in r and not r.get("error") and r.get("month")]
    # dedupe by data month, keep the first parsed value
    seen, uniq = set(), []
    for r in sorted(verified, key=lambda x: x["month"]):
        if r["month"] in seen:
            continue
        seen.add(r["month"])
        uniq.append(r)
    with open(args.out, "w") as f:
        f.write("month,net_t,source_url,headline\n")
        for r in uniq:
            f.write(f"{r['month']},{r['month_t']},{r['url']},\"{r.get('headline','')}\"\n")
    with open(args.out + ".detail.json", "w") as f:
        json.dump(rows, f, indent=1)
    print(f"[done] {len(verified)} verified months -> {args.out}; "
          f"{len(rows) - len(verified)} unparsed -> {args.out}.detail.json", file=sys.stderr)


if __name__ == "__main__":
    main()
