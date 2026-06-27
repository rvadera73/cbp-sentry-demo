#!/usr/bin/env python3
"""
fetch_adcvd.py — Real AD/CVD order reference pipeline (15% maturity).

Pulls active Antidumping (AD) / Countervailing (CVD) duty *orders* from the
live Federal Register API (International Trade Administration notices) and
writes a DVC-versionable reference CSV that the Commodity risk factor reads.

This replaces the synthetic `ad_cvd_rate` column dependency with a real signal:
"does an active AD/CVD order exist for this (commodity, origin country)?"

Usage:
    python scripts/fetch_adcvd.py --region VN --version v1.0
    python scripts/fetch_adcvd.py --region VN --version v1.0 --max-pages 8

Output:
    reference/adcvd/<region>_<version>.csv
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

FR_API = "https://www.federalregister.gov/api/v1/documents.json"

# Country name (as it appears in FR titles) -> ISO-2
COUNTRY_ISO = {
    "socialist republic of vietnam": "VN", "vietnam": "VN",
    "people's republic of china": "CN", "china": "CN",
    "malaysia": "MY", "thailand": "TH", "kingdom of thailand": "TH",
    "indonesia": "ID", "republic of indonesia": "ID",
    "kingdom of cambodia": "KH", "cambodia": "KH",
    "republic of korea": "KR", "south korea": "KR", "korea": "KR",
    "taiwan": "TW", "india": "IN", "republic of india": "IN",
}

# Region -> set of origin countries of interest (transshipment corridor focus)
REGION_COUNTRIES = {
    "VN": {"VN", "CN", "MY", "TH", "ID", "KH"},   # VN corridor + SE Asia hubs
    "CN": {"CN"},
    "ALL": set(COUNTRY_ISO.values()),
}

# Product keyword -> (commodity tag, HS prefix) for the demo corridor commodities.
COMMODITY_MAP = [
    (re.compile(r"alumin", re.I), ("aluminum", "7604")),
    (re.compile(r"solar|photovoltaic|solar cell", re.I), ("solar", "8541")),
    (re.compile(r"\bsteel\b|steel (wire|nail|pipe|sheet)|cold-rolled|hot-rolled", re.I), ("steel", "72")),
    (re.compile(r"\bapparel|garment|textile", re.I), ("apparel", "61")),
    (re.compile(r"\bwood|plywood|cabinet|furniture", re.I), ("wood", "44")),
    (re.compile(r"\btire|tyre", re.I), ("tires", "4011")),
]

ORDER_RE = re.compile(r"\b(antidumping|countervailing)\b.*\border\b", re.I)
TITLE_RE = re.compile(r"^(?P<product>.+?)\s+From\s+(?:the\s+)?(?P<country>.+?):", re.I)
CASE_RE = re.compile(r"\b([AC]-\d{3}-\d{3})\b")


def classify_commodity(product: str) -> tuple[str, str] | None:
    for pat, (tag, hs) in COMMODITY_MAP:
        if pat.search(product):
            return tag, hs
    return None


def order_type(title: str) -> str:
    has_ad = re.search(r"antidumping", title, re.I) is not None
    has_cvd = re.search(r"countervailing", title, re.I) is not None
    if has_ad and has_cvd:
        return "AD/CVD"
    if has_cvd:
        return "CVD"
    if has_ad:
        return "AD"
    return "UNKNOWN"


def fetch_page(term: str, page: int, per_page: int = 100) -> dict:
    params = {
        "per_page": per_page,
        "page": page,
        "order": "newest",
        "conditions[term]": term,
        "conditions[agencies][]": "international-trade-administration",
        "fields[]": ["title", "abstract", "document_number", "html_url", "publication_date"],
    }
    # urlencode with doseq for repeated keys / list values
    flat = []
    for k, v in params.items():
        if isinstance(v, list):
            for item in v:
                flat.append((k, item))
        else:
            flat.append((k, v))
    url = f"{FR_API}?{urllib.parse.urlencode(flat)}"
    req = urllib.request.Request(url, headers={"User-Agent": "cbp-sentry-adcvd/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        import json
        return json.loads(resp.read().decode())


def main() -> int:
    ap = argparse.ArgumentParser(description="Fetch real AD/CVD orders from Federal Register")
    ap.add_argument("--region", default="VN")
    ap.add_argument("--version", default="v1.0")
    ap.add_argument("--max-pages", type=int, default=6)
    ap.add_argument("--out-dir", default=str(Path(__file__).parent.parent / "reference" / "adcvd"))
    args = ap.parse_args()

    region = args.region.upper()
    countries = REGION_COUNTRIES.get(region, REGION_COUNTRIES["ALL"])
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{region}_{args.version}.csv"

    print(f"[fetch_adcvd] region={region} countries={sorted(countries)} -> {out_path}")

    rows: dict[tuple, dict] = {}
    for term in ("antidumping duty order", "countervailing duty order"):
        for page in range(1, args.max_pages + 1):
            try:
                data = fetch_page(term, page)
            except Exception as e:
                print(f"  ! page {page} term '{term}' failed: {e}", file=sys.stderr)
                break
            results = data.get("results", [])
            if not results:
                break
            for doc in results:
                title = (doc.get("title") or "").strip()
                if not ORDER_RE.search(title):
                    continue
                m = TITLE_RE.match(title)
                if not m:
                    continue
                country_name = m.group("country").strip().lower().rstrip(".")
                iso = COUNTRY_ISO.get(country_name)
                if not iso or iso not in countries:
                    continue
                commodity = classify_commodity(m.group("product"))
                if not commodity:
                    continue
                tag, hs = commodity
                case_m = CASE_RE.search(title) or CASE_RE.search(doc.get("abstract") or "")
                case_number = case_m.group(1) if case_m else ""
                key = (iso, tag)
                # Keep the newest doc per (country, commodity)
                if key not in rows or doc.get("publication_date", "") > rows[key]["publication_date"]:
                    rows[key] = {
                        "origin_country": iso,
                        "commodity": tag,
                        "hs_prefix": hs,
                        "order_type": order_type(title),
                        "case_number": case_number,
                        "has_active_order": "true",
                        "publication_date": doc.get("publication_date", ""),
                        "source_doc": doc.get("document_number", ""),
                        "source_url": doc.get("html_url", ""),
                        "title": title[:200],
                    }
            time.sleep(0.3)  # be polite to the API

    fieldnames = ["origin_country", "commodity", "hs_prefix", "order_type", "case_number",
                  "has_active_order", "publication_date", "source_doc", "source_url", "title"]
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for key in sorted(rows):
            writer.writerow(rows[key])

    print(f"[fetch_adcvd] wrote {len(rows)} active AD/CVD order rows")
    for key in sorted(rows):
        r = rows[key]
        print(f"   {r['origin_country']:3} {r['commodity']:8} HS{r['hs_prefix']:5} {r['order_type']:6} {r['case_number']:10} {r['publication_date']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
