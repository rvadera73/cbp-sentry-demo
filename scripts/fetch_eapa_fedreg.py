#!/usr/bin/env python3
"""
fetch_eapa_fedreg.py — Real EAPA cases from UNBLOCKED sources.

cbp.gov Akamai-blocks server scraping (403). Two unblocked real sources:
  1. WAYBACK MACHINE snapshots of the cbp.gov EAPA notices pages (archive.org is
     not blocked) — the RICH source: case #, respondent name, notice type, date.
     Fetching several snapshots across the last ~2 years unions cases that have
     since rolled off the current page.
  2. FEDERAL REGISTER API — Commerce "covered merchandise referral" notices;
     adds commodity + country of origin (thinner on names).

Merged output -> services/api/reference/eapa_real.csv:
  eapa_case, respondents, commodity, country_of_origin, determination_date,
  notice_type, source_url

Usage:
    python scripts/fetch_eapa_fedreg.py                 # wayback + FR (default)
    python scripts/fetch_eapa_fedreg.py --source wayback
    python scripts/fetch_eapa_fedreg.py --years 2 --dry-run
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
from datetime import datetime
from pathlib import Path

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"}
FR_API = "https://www.federalregister.gov/api/v1/documents.json"

CBP_EAPA_PAGES = [
    "https://www.cbp.gov/trade/eapa/notices-action",
    "https://www.cbp.gov/trade/trade-enforcement/tftea/eapa/eapa-actions-archive",
    "https://www.cbp.gov/trade/trade-enforcement/tftea/enforce-and-protect-act-eapa/notices-final-determination",
]

COUNTRY_ISO = {
    "socialist republic of vietnam": "VN", "vietnam": "VN", "people's republic of china": "CN", "china": "CN",
    "malaysia": "MY", "thailand": "TH", "kingdom of thailand": "TH", "indonesia": "ID", "republic of indonesia": "ID",
    "kingdom of cambodia": "KH", "cambodia": "KH", "republic of korea": "KR", "south korea": "KR", "korea": "KR",
    "taiwan": "TW", "india": "IN", "türkiye": "TR", "turkey": "TR",
}
COMMODITY_MAP = [
    (re.compile(r"alumin", re.I), ("aluminum", "7604")),
    (re.compile(r"solar|photovoltaic|solar cell", re.I), ("solar", "8541")),
    (re.compile(r"\bsteel\b|steel (wire|nail|pipe|sheet|wheel)|cold-rolled|hot-rolled|tubular|pipe|hanger|wire", re.I), ("steel", "72")),
    (re.compile(r"\bapparel|garment|textile", re.I), ("apparel", "61")),
    (re.compile(r"\bwood|plywood|cabinet|vanit|furniture", re.I), ("wood", "44")),
    (re.compile(r"\btire|tyre", re.I), ("tires", "4011")),
    (re.compile(r"glycine|chemical|glutamate|citric", re.I), ("chemical", "29")),
]

FR_EAPA_RE = re.compile(r"enforce and protect act|covered merchandise referral|evasion of (the )?(antidumping|countervailing|ad/cvd)|determination as to evasion", re.I)
FR_FROM_RE = re.compile(r"\bFrom\s+(?:the\s+)?(?P<country>[A-Za-z' ]+?)(?:[:,\.]|$)", re.I)
ADCVD_CASE_RE = re.compile(r"\b([AC]-\d{3}-\d{3})\b")
# cbp.gov anchor text: "EAPA [Cons.] Case ####: <Respondent> (<notice type>, <Month DD, YYYY>)"
EAPA_ANCHOR_RE = re.compile(r"EAPA\s*(?:Cons\.?\s*)?Case\s*(\d{3,5}):\s*(.+?)\s*\((.+?)\)", re.I)


def _get(url: str, timeout: int = 60) -> str:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode(errors="ignore")


def classify_commodity(text: str):
    for pat, (tag, hs) in COMMODITY_MAP:
        if pat.search(text or ""):
            return tag, hs
    return ("", "")


def norm_date(s: str) -> str:
    s = (s or "").strip()
    for fmt in ("%B %d, %Y", "%b %d, %Y", "%B %d %Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(s.replace(".", ""), fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return s


# ---------- Wayback (rich: case + respondent) ----------
def wb_snapshot_url(page: str, timestamp: str) -> str | None:
    try:
        j = json.loads(_get(f"http://archive.org/wayback/available?url={urllib.parse.quote(page)}&timestamp={timestamp}", timeout=30))
        snap = j.get("archived_snapshots", {}).get("closest", {})
        if snap.get("available"):
            return f"http://web.archive.org/web/{snap['timestamp']}id_/{page}"
    except Exception as e:
        print(f"  ! wayback avail {page}@{timestamp}: {e}", file=sys.stderr)
    return None


def parse_cbp_html(html: str, url: str) -> list[dict]:
    out = []
    for anchor in re.findall(r">([^<>]*EAPA[^<>]{5,200})<", html, re.I):
        m = EAPA_ANCHOR_RE.search(re.sub(r"\s+", " ", anchor).strip())
        if not m:
            continue
        case, respondent, paren = m.group(1), m.group(2).strip(" :"), m.group(3).strip()
        # pull "<Month DD, YYYY>" (or M/D/YYYY) off the end; the rest is the notice type
        dm = re.search(r"([A-Za-z]+\.?\s+\d{1,2},?\s+\d{4}|\d{1,2}/\d{1,2}/\d{4})\s*$", paren)
        if dm:
            date = dm.group(1)
            notice_type = paren[: dm.start()].rstrip(" ,")
        else:
            notice_type, date = paren, ""
        commodity_txt = f"{respondent} {notice_type}"
        tag, hs = classify_commodity(commodity_txt)
        out.append({
            "eapa_case": f"EAPA-{case}",
            "respondents": "" if re.fullmatch(r"various importers", respondent, re.I) else respondent,
            "commodity": f"{tag} ({hs})" if hs else "",
            "country_of_origin": "",
            "determination_date": norm_date(date),
            "notice_type": notice_type.strip(),
            "source_url": url,
        })
    return out


def fetch_wayback(years: int) -> dict:
    now = datetime.utcnow()
    stamps = []
    for y in range(years + 1):
        for mm in ("03", "06", "09", "12"):
            stamps.append(f"{now.year - y}{mm}01")
    stamps = sorted(set(s for s in stamps if s <= now.strftime("%Y%m%d")), reverse=True)[: (years + 1) * 4]
    rows: dict[str, dict] = {}
    for page in CBP_EAPA_PAGES:
        seen_snaps = set()
        for ts in stamps:
            snap = wb_snapshot_url(page, ts)
            if not snap or snap in seen_snaps:
                continue
            seen_snaps.add(snap)
            try:
                html = _get(snap, timeout=90)
            except Exception as e:
                print(f"  ! wayback fetch {snap}: {e}", file=sys.stderr)
                continue
            for r in parse_cbp_html(html, page):
                k = r["eapa_case"]
                # keep the row with the most info (respondent + newest date)
                if k not in rows or (r["respondents"] and not rows[k]["respondents"]) or r["determination_date"] > rows[k]["determination_date"]:
                    if k in rows:  # merge, don't lose an existing respondent/commodity
                        for f in ("respondents", "commodity", "country_of_origin"):
                            if not r[f] and rows[k][f]:
                                r[f] = rows[k][f]
                    rows[k] = r
            time.sleep(0.5)
    return rows


# ---------- Federal Register (adds commodity/country) ----------
def fr_fetch_page(term: str, page: int) -> dict:
    flat = [("per_page", 100), ("page", page), ("order", "newest"), ("conditions[term]", term),
            ("fields[]", "title"), ("fields[]", "abstract"), ("fields[]", "document_number"),
            ("fields[]", "html_url"), ("fields[]", "publication_date")]
    return json.loads(_get(f"{FR_API}?{urllib.parse.urlencode(flat)}", timeout=30))


def fetch_fedreg(max_pages: int) -> dict:
    rows: dict[str, dict] = {}
    for term in ('"covered merchandise referral"', '"Enforce and Protect Act"', "evasion antidumping countervailing"):
        for page in range(1, max_pages + 1):
            try:
                data = fr_fetch_page(term, page)
            except Exception as e:
                print(f"  ! FR {term} p{page}: {e}", file=sys.stderr)
                break
            results = data.get("results", [])
            if not results:
                break
            for doc in results:
                title, abstract = (doc.get("title") or ""), (doc.get("abstract") or "")
                if not FR_EAPA_RE.search(title + " " + abstract):
                    continue
                tag, hs = classify_commodity(title + " " + abstract)
                m = FR_FROM_RE.search(title)
                iso = COUNTRY_ISO.get(m.group("country").strip().lower().rstrip(".")) if m else ""
                cm = ADCVD_CASE_RE.search(title) or ADCVD_CASE_RE.search(abstract)
                key = cm.group(1) if cm else doc.get("document_number", "")
                rows[key] = {
                    "eapa_case": key, "respondents": "", "commodity": f"{tag} ({hs})" if hs else "",
                    "country_of_origin": iso or "", "determination_date": doc.get("publication_date", ""),
                    "notice_type": "Covered Merchandise Referral (Federal Register)", "source_url": doc.get("html_url", ""),
                }
            time.sleep(0.3)
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description="Fetch real EAPA cases (Wayback cbp.gov + Federal Register)")
    ap.add_argument("--out", default=str(Path(__file__).parent.parent / "services" / "api" / "reference" / "eapa_real.csv"))
    ap.add_argument("--source", choices=["wayback", "fr", "both"], default="both")
    ap.add_argument("--years", type=int, default=2, help="how many years of Wayback snapshots to union")
    ap.add_argument("--max-pages", type=int, default=4)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    rows: dict[str, dict] = {}
    if args.source in ("wayback", "both"):
        print(f"[eapa] Wayback cbp.gov snapshots, last {args.years}y ...")
        rows.update(fetch_wayback(args.years))
        print(f"[eapa] wayback -> {len(rows)} cases")
    if args.source in ("fr", "both"):
        fr = fetch_fedreg(args.max_pages)
        # merge FR commodity/country into matching cases; add non-duplicates
        for k, r in fr.items():
            if k in rows:
                for f in ("commodity", "country_of_origin"):
                    if not rows[k][f] and r[f]:
                        rows[k][f] = r[f]
            else:
                rows[k] = r
        print(f"[eapa] + federal register -> {len(rows)} total")

    dates = sorted(r["determination_date"] for r in rows.values() if r["determination_date"])
    span = f"{dates[0]}..{dates[-1]}" if dates else "n/a"
    cutoff = f"{datetime.utcnow().year - args.years}-{datetime.utcnow():%m-%d}"
    last_n = sum(1 for d in dates if d >= cutoff)
    with_names = sum(1 for r in rows.values() if r["respondents"])
    in_scope = sum(1 for r in rows.values() if r["commodity"].startswith(("aluminum", "solar")))
    print(f"[eapa] {len(rows)} cases | span {span} | since {cutoff}: {last_n} | {with_names} with respondent name | {in_scope} aluminum/solar")

    fields = ["eapa_case", "respondents", "commodity", "country_of_origin", "determination_date", "notice_type", "source_url"]
    ordered = sorted(rows.values(), key=lambda r: r["determination_date"], reverse=True)
    if args.dry_run:
        for r in ordered[:20]:
            print("  ", r["eapa_case"], "|", r["respondents"][:34], "|", r["commodity"], "|", r["determination_date"], "|", r["notice_type"][:40])
        return 0
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in ordered:
            w.writerow({k: r[k] for k in fields})
    print(f"[eapa] wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
