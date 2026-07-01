#!/usr/bin/env python3
"""
fetch_eapa_fedreg.py — Real EAPA case reference from the Federal Register API.

CBP publishes EAPA respondent *names* only on cbp.gov (Akamai-blocks datacenter
IPs -> 403). But the Federal Register API (same source fetch_adcvd.py uses, and
NOT bot-blocked) publishes the EAPA "covered merchandise referral from CBP" /
"Enforce and Protect Act evasion" notices. Those reliably give:
  commodity, country of origin, publication date, AD/CVD case number, URL.
Respondent company names are inconsistent (these notices target merchandise, not
importers), so we do a BEST-EFFORT name pull from the document body and report
coverage honestly.

Output schema matches scripts/fetch_eapa.py so the Data Pipelines tab + downstream
consume either:
  eapa_case, respondents, commodity, country_of_origin, determination_date,
  notice_type, source_url

Usage:
    python scripts/fetch_eapa_fedreg.py                 # fetch + write CSV (with names)
    python scripts/fetch_eapa_fedreg.py --no-names      # skip the body name scan (faster)
    python scripts/fetch_eapa_fedreg.py --max-pages 5 --out <path>
    python scripts/fetch_eapa_fedreg.py --dry-run
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

FR_API = "https://www.federalregister.gov/api/v1/documents.json"
UA = {"User-Agent": "cbp-sentry-eapa/1.0"}

COUNTRY_ISO = {
    "socialist republic of vietnam": "VN", "vietnam": "VN",
    "people's republic of china": "CN", "china": "CN",
    "malaysia": "MY", "thailand": "TH", "kingdom of thailand": "TH",
    "indonesia": "ID", "republic of indonesia": "ID",
    "kingdom of cambodia": "KH", "cambodia": "KH",
    "republic of korea": "KR", "south korea": "KR", "korea": "KR",
    "taiwan": "TW", "india": "IN", "republic of india": "IN",
    "türkiye": "TR", "turkey": "TR",
}

COMMODITY_MAP = [
    (re.compile(r"alumin", re.I), ("aluminum", "7604")),
    (re.compile(r"solar|photovoltaic|solar cell", re.I), ("solar", "8541")),
    (re.compile(r"\bsteel\b|steel (wire|nail|pipe|sheet|wheel)|cold-rolled|hot-rolled|tubular", re.I), ("steel", "72")),
    (re.compile(r"\bapparel|garment|textile", re.I), ("apparel", "61")),
    (re.compile(r"\bwood|plywood|cabinet|furniture", re.I), ("wood", "44")),
    (re.compile(r"\btire|tyre", re.I), ("tires", "4011")),
]

# EAPA / covered-merchandise-referral markers in title or abstract.
EAPA_RE = re.compile(r"enforce and protect act|covered merchandise referral|evasion of (the )?(antidumping|countervailing|ad/cvd)", re.I)
TITLE_FROM_RE = re.compile(r"\bFrom\s+(?:the\s+)?(?P<country>[A-Za-z' ]+?)(?:[:,\.]|$)", re.I)
ADCVD_CASE_RE = re.compile(r"\b([AC]-\d{3}-\d{3})\b")
EAPA_CASE_RE = re.compile(r"\bEAPA\s*(?:Cons\.?\s*)?(?:Case\s*)?#?\s*(\d{3,5})\b", re.I)
COMPANY_RE = re.compile(r"\b([A-Z][A-Za-z0-9&.,'\- ]{2,60}?(?:Inc|LLC|L\.L\.C|Corp|Corporation|Co|Company|Ltd|Limited|JSC|GmbH|S\.A|Pte|Sdn Bhd|Group|Trading|Industries|Manufacturing)\.?)\b")


def classify_commodity(text: str):
    for pat, (tag, hs) in COMMODITY_MAP:
        if pat.search(text):
            return tag, hs
    return ("other", "")


def parse_country(title: str):
    m = TITLE_FROM_RE.search(title or "")
    if not m:
        return ""
    name = m.group("country").strip().lower().rstrip(".")
    return COUNTRY_ISO.get(name, "")


def fetch_page(term: str, page: int, per_page: int = 100) -> dict:
    flat = [
        ("per_page", per_page), ("page", page), ("order", "newest"),
        ("conditions[term]", term),
        ("fields[]", "title"), ("fields[]", "abstract"), ("fields[]", "document_number"),
        ("fields[]", "html_url"), ("fields[]", "publication_date"), ("fields[]", "raw_text_url"),
        ("fields[]", "agencies"),
    ]
    url = f"{FR_API}?{urllib.parse.urlencode(flat)}"
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def scan_names(raw_text_url: str) -> str:
    """Best-effort: pull candidate importer/company names from the doc body."""
    if not raw_text_url:
        return ""
    try:
        req = urllib.request.Request(raw_text_url, headers=UA)
        with urllib.request.urlopen(req, timeout=30) as resp:
            text = resp.read().decode(errors="ignore")
    except Exception:
        return ""
    names = set()
    # Look near importer/alleger context to avoid grabbing agency/law-firm noise.
    for m in re.finditer(r"(?:importer|alleg\w+|respondent)[^.\n]{0,200}", text, re.I):
        for cm in COMPANY_RE.finditer(m.group(0)):
            nm = cm.group(1).strip(" ,.")
            if len(nm) > 4 and not re.search(r"\b(Commerce|Department|Customs|Border Protection|Federal Register|International Trade)\b", nm):
                names.add(nm)
    return "; ".join(sorted(names)[:8])


def main() -> int:
    ap = argparse.ArgumentParser(description="Fetch real EAPA cases from the Federal Register API")
    ap.add_argument("--out", default=str(Path(__file__).parent.parent / "services" / "api" / "reference" / "eapa_real.csv"))
    ap.add_argument("--max-pages", type=int, default=4)
    ap.add_argument("--no-names", action="store_true", help="skip the (slower) body name scan")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    terms = ['"Enforce and Protect Act"', '"covered merchandise referral"', "evasion antidumping countervailing"]
    seen_docs, rows = set(), {}
    for term in terms:
        for page in range(1, args.max_pages + 1):
            try:
                data = fetch_page(term, page)
            except Exception as e:
                print(f"  ! term {term!r} page {page} failed: {e}", file=sys.stderr)
                break
            results = data.get("results", [])
            if not results:
                break
            for doc in results:
                dn = doc.get("document_number", "")
                if dn in seen_docs:
                    continue
                title = (doc.get("title") or "").strip()
                abstract = (doc.get("abstract") or "").strip()
                if not EAPA_RE.search(title + " " + abstract):
                    continue
                seen_docs.add(dn)
                tag, hs = classify_commodity(title + " " + abstract)
                country = parse_country(title)
                eapa_m = EAPA_CASE_RE.search(title) or EAPA_CASE_RE.search(abstract)
                adcvd_m = ADCVD_CASE_RE.search(title) or ADCVD_CASE_RE.search(abstract)
                case = (f"EAPA-{eapa_m.group(1)}" if eapa_m else (adcvd_m.group(1) if adcvd_m else dn))
                rows[dn] = {
                    "eapa_case": case,
                    "respondents": "",
                    "commodity": f"{tag} ({hs})" if hs else tag,
                    "country_of_origin": country,
                    "determination_date": doc.get("publication_date", ""),
                    "notice_type": "Covered Merchandise Referral (Federal Register)",
                    "source_url": doc.get("html_url", ""),
                    "_raw": doc.get("raw_text_url", ""),
                }
            time.sleep(0.3)

    # Best-effort name enrichment
    if not args.no_names:
        for dn, r in rows.items():
            r["respondents"] = scan_names(r.pop("_raw", ""))
            time.sleep(0.2)
    else:
        for r in rows.values():
            r.pop("_raw", None)

    with_names = sum(1 for r in rows.values() if r["respondents"])
    in_scope = sum(1 for r in rows.values() if r["commodity"].startswith(("aluminum", "solar")))
    print(f"[fetch_eapa_fedreg] {len(rows)} real EAPA cases | {with_names} with respondent name(s) | {in_scope} aluminum/solar")

    fields = ["eapa_case", "respondents", "commodity", "country_of_origin", "determination_date", "notice_type", "source_url"]
    if args.dry_run:
        for r in list(rows.values())[:15]:
            print("  ", {k: r[k] for k in fields})
        return 0

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for dn in sorted(rows, key=lambda d: rows[d]["determination_date"], reverse=True):
            w.writerow({k: rows[dn][k] for k in fields})
    print(f"[fetch_eapa_fedreg] wrote {out}")
    for dn in sorted(rows, key=lambda d: rows[d]["determination_date"], reverse=True)[:12]:
        r = rows[dn]
        print(f"   {r['determination_date']:11} {r['country_of_origin']:3} {r['commodity']:20} {r['eapa_case']:14} {r['respondents'][:40]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
