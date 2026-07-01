#!/usr/bin/env python3
"""
fetch_eapa.py — Scrape REAL CBP Enforce-and-Protect-Act (EAPA) determinations
into a CSV, replacing the synthetic seed used elsewhere in the codebase.

The in-system EAPA data (see services/data/db.py) is SYNTHETIC. CBP publishes
the genuine determinations across several public pages (some HTML lists, some
PDF links). This script fetches those pages with a realistic browser User-Agent
(cbp.gov blocks default python UAs), parses per-case fields with BeautifulSoup,
de-dupes by EAPA case number, and writes a normalized CSV.

Output CSV columns:
    eapa_case, respondents, commodity, country_of_origin,
    determination_date, notice_type, source_url

Usage:
    python3 scripts/fetch_eapa.py                       # live fetch -> default out
    python3 scripts/fetch_eapa.py --dry-run             # print, do not write
    python3 scripts/fetch_eapa.py --from-local data/eapa_raw   # parse saved .html
    python3 scripts/fetch_eapa.py --out /some/path.csv

Notes:
    * HTTP 403 / blocked pages are logged and skipped (pipeline continues).
    * If ALL live pages are blocked and --from-local points at a dir of saved
      .html files, those are parsed instead so the pipeline still works from
      manually-saved pages.
    * PDF entries are captured as (case, title, pdf url). If pdfplumber/pypdf
      is installed, we best-effort pull respondent/commodity from page 1;
      otherwise we just record the link.
"""
from __future__ import annotations

import argparse
import csv
import io
import os
import re
import sys
import time
from dataclasses import dataclass, field, asdict
from typing import Iterable
from urllib.parse import urljoin, urlparse

try:
    import requests
except ImportError:  # pragma: no cover
    print("FATAL: `requests` is not installed. Run: pip install requests beautifulsoup4 lxml", file=sys.stderr)
    raise

try:
    from bs4 import BeautifulSoup
except ImportError:  # pragma: no cover
    print("FATAL: `beautifulsoup4` is not installed. Run: pip install beautifulsoup4 lxml", file=sys.stderr)
    raise

# Optional PDF text extraction (best-effort; not required)
_PDF_BACKEND = None
try:  # prefer pdfplumber
    import pdfplumber  # type: ignore
    _PDF_BACKEND = "pdfplumber"
except ImportError:
    try:
        import pypdf  # type: ignore
        _PDF_BACKEND = "pypdf"
    except ImportError:
        _PDF_BACKEND = None


# --------------------------------------------------------------------------- #
# Config
# --------------------------------------------------------------------------- #

# The public CBP EAPA pages. label is used as a fallback notice_type.
SOURCES: list[tuple[str, str]] = [
    ("Notice of Action",
     "https://www.cbp.gov/trade/eapa/notices-action"),
    ("Final Administrative Determination",
     "https://www.cbp.gov/trade/trade-enforcement/tftea/eapa/requests-administrative-review/final-administrative-determinations"),
    ("Notice of Final Determination",
     "https://www.cbp.gov/trade/trade-enforcement/tftea/enforce-and-protect-act-eapa/notices-final-determination"),
    ("EAPA Actions Archive",
     "https://www.cbp.gov/trade/trade-enforcement/tftea/eapa/eapa-actions-archive"),
]

DEFAULT_OUT = "services/api/reference/eapa_real.csv"
DEFAULT_LOCAL_DIR = "data/eapa_raw"

CSV_FIELDS = [
    "eapa_case",
    "respondents",
    "commodity",
    "country_of_origin",
    "determination_date",
    "notice_type",
    "source_url",
]

# A recent desktop Chrome UA — cbp.gov 403s the default python-requests UA.
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)
HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

# EAPA case numbers appear as e.g. "EAPA 7181", "EAPA Case 7654",
# "EAPA Consolidated Case Number 7501", "Case Number 7185".
CASE_RE = re.compile(
    r"EAPA(?:\s+(?:Consolidated\s+)?Case(?:\s+Number)?)?\s*[#:]?\s*(\d{3,5})",
    re.IGNORECASE,
)
# Country of origin phrases.
COUNTRY_RE = re.compile(
    r"(?:country of origin|origin(?:ating)?\s+(?:in|from)|manufactured in|"
    r"transship(?:ped|ment)\s+(?:through|via))\s*[:\-]?\s*"
    r"(China|Vietnam|Malaysia|Thailand|Cambodia|Taiwan|India|Turkey|"
    r"Indonesia|South Korea|Korea|Mexico|Sri Lanka|Laos|Philippines)",
    re.IGNORECASE,
)
DATE_RE = re.compile(
    r"((?:January|February|March|April|May|June|July|August|September|October|"
    r"November|December)\s+\d{1,2},\s+\d{4}"
    r"|\d{1,2}/\d{1,2}/\d{2,4}"
    r"|\d{4}-\d{2}-\d{2})",
    re.IGNORECASE,
)

REQUEST_TIMEOUT = 30
POLITE_DELAY = 2.0       # seconds between page fetches
MAX_RETRIES = 3
BACKOFF_BASE = 3.0       # seconds; multiplied by attempt number


# --------------------------------------------------------------------------- #
# Data model
# --------------------------------------------------------------------------- #

@dataclass
class EapaRow:
    eapa_case: str = ""
    respondents: str = ""
    commodity: str = ""
    country_of_origin: str = ""
    determination_date: str = ""
    notice_type: str = ""
    source_url: str = ""

    def merge(self, other: "EapaRow") -> None:
        """Fill blank fields on self from other (used when de-duping)."""
        for f in ("respondents", "commodity", "country_of_origin",
                  "determination_date", "notice_type", "source_url"):
            if not getattr(self, f) and getattr(other, f):
                setattr(self, f, getattr(other, f))
        # respondents: union both if both present and different
        if other.respondents and self.respondents and other.respondents != self.respondents:
            existing = {r.strip() for r in self.respondents.split(";") if r.strip()}
            for r in other.respondents.split(";"):
                if r.strip() and r.strip() not in existing:
                    existing.add(r.strip())
            self.respondents = ";".join(sorted(existing))


# --------------------------------------------------------------------------- #
# Fetching
# --------------------------------------------------------------------------- #

def fetch(session: requests.Session, url: str) -> tuple[int, str | None, bytes | None]:
    """Fetch url with retries/backoff. Returns (status_code, text, content).

    status_code 0 means a network-level failure (no HTTP response)."""
    last_status = 0
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = session.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            last_status = resp.status_code
            if resp.status_code == 200:
                return resp.status_code, resp.text, resp.content
            if resp.status_code == 403:
                # blocked — no point retrying aggressively, but try once more slowly
                print(f"    [403 blocked] {url} (attempt {attempt})")
                if attempt < MAX_RETRIES:
                    time.sleep(BACKOFF_BASE * attempt)
                    continue
                return resp.status_code, None, None
            if resp.status_code in (429, 500, 502, 503, 504):
                print(f"    [{resp.status_code}] transient, backing off (attempt {attempt})")
                time.sleep(BACKOFF_BASE * attempt)
                continue
            # other status: give up
            print(f"    [{resp.status_code}] {url}")
            return resp.status_code, None, None
        except requests.RequestException as exc:
            print(f"    [network error] {exc} (attempt {attempt})")
            time.sleep(BACKOFF_BASE * attempt)
    return last_status, None, None


# --------------------------------------------------------------------------- #
# Parsing helpers
# --------------------------------------------------------------------------- #

def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip()


def _extract_country(text: str) -> str:
    m = COUNTRY_RE.search(text)
    if m:
        c = m.group(1).title()
        return "South Korea" if c == "Korea" else c
    return ""


def _extract_date(text: str) -> str:
    m = DATE_RE.search(text)
    return _clean(m.group(1)) if m else ""


def _extract_case(text: str) -> str:
    m = CASE_RE.search(text)
    return m.group(1) if m else ""


def _guess_respondent_from_title(title: str) -> str:
    """Heuristic: the linked-notice title often reads like
    'EAPA Case 7181 - Notice of Action - <Importer>, Inc.'"""
    if not title:
        return ""
    # strip leading EAPA case + notice-type boilerplate
    t = re.sub(CASE_RE, "", title)
    t = re.sub(
        r"(notice of (?:action|final determination|initiation)|"
        r"final (?:administrative )?determination(?:\s+as to evasion)?|"
        r"determination as to evasion|administrative review|"
        r"eapa|consolidated case|case number)",
        "", t, flags=re.IGNORECASE)
    t = t.strip(" -–—:,.–—")
    t = _clean(t)
    # keep only if it looks like a company name (has a corp suffix or 2+ words)
    if re.search(r"\b(Inc|LLC|Ltd|Co|Corp|Company|Group|Holdings|Trading|"
                 r"Industries|International|Import|Export|Sdn|Bhd|JSC|GmbH|"
                 r"Manufacturing|Enterprises)\b", t, re.IGNORECASE):
        return t
    if len(t.split()) >= 2 and len(t) <= 90 and not t.lower().startswith("http"):
        return t
    return ""


def _row_from_text(text: str, source_url: str, notice_type: str) -> EapaRow | None:
    case = _extract_case(text)
    if not case:
        return None
    return EapaRow(
        eapa_case=f"EAPA-{case}",
        respondents="",
        commodity="",
        country_of_origin=_extract_country(text),
        determination_date=_extract_date(text),
        notice_type=notice_type,
        source_url=source_url,
    )


# --------------------------------------------------------------------------- #
# HTML parsing
# --------------------------------------------------------------------------- #

def parse_html(html: str, base_url: str, default_notice: str) -> list[EapaRow]:
    """Best-effort extraction of EAPA cases from a page's HTML.

    Strategy:
      1. Parse tables — each row that mentions a case number becomes a record.
      2. Parse links (li/a) — each anchor whose text/href mentions a case
         becomes a record; PDFs are captured as links.
      3. Fall back to scanning list items / paragraphs for case numbers.
    """
    soup = BeautifulSoup(html, "lxml")
    rows: list[EapaRow] = []

    # 1) Tables --------------------------------------------------------------
    for table in soup.find_all("table"):
        headers = [_clean(th.get_text()).lower() for th in table.find_all("th")]
        for tr in table.find_all("tr"):
            cells = tr.find_all(["td", "th"])
            if not cells:
                continue
            cell_texts = [_clean(td.get_text()) for td in cells]
            joined = " | ".join(cell_texts)
            case = _extract_case(joined)
            if not case:
                continue
            row = EapaRow(eapa_case=f"EAPA-{case}", notice_type=default_notice,
                          source_url=base_url)
            # map columns by header keyword where possible
            for hdr, val in zip(headers, cell_texts):
                if not val:
                    continue
                if any(k in hdr for k in ("respondent", "importer", "alleger",
                                          "party", "company", "name")):
                    row.respondents = _merge_names(row.respondents, val)
                elif any(k in hdr for k in ("commodity", "merchandise",
                                            "product", "good")):
                    row.commodity = val
                elif "origin" in hdr or "country" in hdr:
                    row.country_of_origin = val or row.country_of_origin
                elif "date" in hdr or "determination" in hdr:
                    if DATE_RE.search(val):
                        row.determination_date = _extract_date(val)
                elif "type" in hdr or "notice" in hdr or "action" in hdr:
                    if val:
                        row.notice_type = val
            # fill from free-text if headers were absent/uninformative
            if not row.country_of_origin:
                row.country_of_origin = _extract_country(joined)
            if not row.determination_date:
                row.determination_date = _extract_date(joined)
            # find a link in the row for a better source_url + title respondent
            a = tr.find("a", href=True)
            if a is not None:
                row.source_url = urljoin(base_url, a["href"])
                if not row.respondents:
                    row.respondents = _guess_respondent_from_title(_clean(a.get_text()))
            rows.append(row)

    # 2) Anchors (link lists — many EAPA pages are just <ul><li><a>) ----------
    seen_hrefs: set[str] = set()
    for a in soup.find_all("a", href=True):
        text = _clean(a.get_text())
        href = a["href"]
        blob = f"{text} {href}"
        case = _extract_case(blob)
        if not case:
            continue
        abs_url = urljoin(base_url, href)
        key = f"{case}|{abs_url}"
        if key in seen_hrefs:
            continue
        seen_hrefs.add(key)
        is_pdf = abs_url.lower().endswith(".pdf")
        row = EapaRow(
            eapa_case=f"EAPA-{case}",
            respondents=_guess_respondent_from_title(text),
            commodity="",
            country_of_origin=_extract_country(text),
            determination_date=_extract_date(text),
            notice_type=default_notice,
            source_url=abs_url,
        )
        # look at surrounding text (parent li/p) for extra context
        parent = a.find_parent(["li", "p", "td"])
        if parent is not None:
            ctx = _clean(parent.get_text())
            if not row.country_of_origin:
                row.country_of_origin = _extract_country(ctx)
            if not row.determination_date:
                row.determination_date = _extract_date(ctx)
        row._is_pdf = is_pdf  # type: ignore[attr-defined]
        rows.append(row)

    # 3) Fallback: scan list items / paragraphs for bare case numbers --------
    if not rows:
        for el in soup.find_all(["li", "p", "div"]):
            text = _clean(el.get_text())
            if not text or not CASE_RE.search(text):
                continue
            r = _row_from_text(text, base_url, default_notice)
            if r:
                r.respondents = _guess_respondent_from_title(text)
                rows.append(r)

    return rows


def _merge_names(existing: str, new: str) -> str:
    # Split ONLY on ';' (CBP's multi-respondent separator). A bare comma is
    # left intact because it commonly appears inside a single company name
    # (e.g. "Global Aluminum Extrusions, Inc.").
    parts = {p.strip() for p in existing.split(";") if p.strip()}
    for p in new.split(";"):
        p = p.strip()
        if p:
            parts.add(p)
    return ";".join(sorted(parts))


# --------------------------------------------------------------------------- #
# PDF (optional, best-effort)
# --------------------------------------------------------------------------- #

def enrich_from_pdf(session: requests.Session, row: EapaRow) -> None:
    """If a PDF backend is available, pull respondent/commodity/country from
    page 1. Silent best-effort — never fatal."""
    if _PDF_BACKEND is None:
        return
    if not row.source_url.lower().endswith(".pdf"):
        return
    if row.respondents and row.commodity and row.country_of_origin:
        return
    try:
        status, _, content = fetch(session, row.source_url)
        if status != 200 or not content:
            return
        text = _read_pdf_first_page(content)
        if not text:
            return
        if not row.country_of_origin:
            row.country_of_origin = _extract_country(text)
        if not row.determination_date:
            row.determination_date = _extract_date(text)
        if not row.commodity:
            m = re.search(r"(?:merchandise|covered merchandise|commodity)\s*"
                          r"(?:is|are|:)?\s*([A-Za-z][^.\n]{5,80})", text,
                          re.IGNORECASE)
            if m:
                row.commodity = _clean(m.group(1))
        if not row.respondents:
            m = re.search(r"(?:importer|respondent)s?\s*(?:of record)?\s*[:,]?\s*"
                          r"([A-Z][A-Za-z0-9 .,&'\-]{3,80}?(?:Inc|LLC|Ltd|Co|"
                          r"Corp|Company|Group|Holdings|Trading)\.?)", text)
            if m:
                row.respondents = _clean(m.group(1))
    except Exception as exc:  # pragma: no cover - defensive
        print(f"    [pdf skip] {row.source_url}: {exc}")


def _read_pdf_first_page(content: bytes) -> str:
    try:
        if _PDF_BACKEND == "pdfplumber":
            import pdfplumber  # type: ignore
            with pdfplumber.open(io.BytesIO(content)) as pdf:
                if pdf.pages:
                    return pdf.pages[0].extract_text() or ""
        elif _PDF_BACKEND == "pypdf":
            import pypdf  # type: ignore
            reader = pypdf.PdfReader(io.BytesIO(content))
            if reader.pages:
                return reader.pages[0].extract_text() or ""
    except Exception:
        return ""
    return ""


# --------------------------------------------------------------------------- #
# Dedupe + write
# --------------------------------------------------------------------------- #

def dedupe(rows: Iterable[EapaRow]) -> list[EapaRow]:
    by_case: dict[str, EapaRow] = {}
    for r in rows:
        if not r.eapa_case:
            continue
        if r.eapa_case in by_case:
            by_case[r.eapa_case].merge(r)
        else:
            by_case[r.eapa_case] = r
    # stable sort by numeric case id
    def _key(row: EapaRow) -> int:
        m = re.search(r"(\d+)", row.eapa_case)
        return int(m.group(1)) if m else 0
    return sorted(by_case.values(), key=_key)


def write_csv(rows: list[EapaRow], out_path: str) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for r in rows:
            writer.writerow({k: getattr(r, k) for k in CSV_FIELDS})


def summarize(rows: list[EapaRow]) -> None:
    distinct_cases = {r.eapa_case for r in rows if r.eapa_case}
    respondents: set[str] = set()
    for r in rows:
        for name in r.respondents.split(";"):
            if name.strip():
                respondents.add(name.strip())
    with_country = sum(1 for r in rows if r.country_of_origin)
    with_date = sum(1 for r in rows if r.determination_date)
    with_resp = sum(1 for r in rows if r.respondents)
    print("\n=== SUMMARY ===")
    print(f"  rows written        : {len(rows)}")
    print(f"  distinct cases      : {len(distinct_cases)}")
    print(f"  distinct respondents: {len(respondents)}")
    print(f"  rows w/ respondent  : {with_resp}")
    print(f"  rows w/ country     : {with_country}")
    print(f"  rows w/ date        : {with_date}")


# --------------------------------------------------------------------------- #
# Collection modes
# --------------------------------------------------------------------------- #

def collect_live(enrich_pdfs: bool) -> tuple[list[EapaRow], bool]:
    """Fetch live pages. Returns (rows, any_success)."""
    session = requests.Session()
    all_rows: list[EapaRow] = []
    any_success = False
    for notice_type, url in SOURCES:
        print(f"[fetch] {notice_type}: {url}")
        status, text, _ = fetch(session, url)
        if status == 200 and text:
            any_success = True
            page_rows = parse_html(text, url, notice_type)
            print(f"    -> {len(page_rows)} candidate case rows")
            all_rows.extend(page_rows)
        elif status == 403:
            print(f"    -> 403 blocked, skipping")
        else:
            print(f"    -> status {status}, skipping")
        time.sleep(POLITE_DELAY)

    if enrich_pdfs and _PDF_BACKEND and any_success:
        pdf_rows = [r for r in all_rows
                    if getattr(r, "_is_pdf", False) or r.source_url.lower().endswith(".pdf")]
        if pdf_rows:
            print(f"[pdf] enriching {len(pdf_rows)} PDF rows via {_PDF_BACKEND} ...")
            for r in pdf_rows:
                enrich_from_pdf(session, r)
                time.sleep(0.5)
    return all_rows, any_success


def collect_local(local_dir: str) -> list[EapaRow]:
    """Parse saved .html files in local_dir. Each file's basename is used as a
    hint for the notice_type."""
    all_rows: list[EapaRow] = []
    if not os.path.isdir(local_dir):
        print(f"[local] directory not found: {local_dir}")
        return all_rows
    html_files = sorted(
        os.path.join(local_dir, f) for f in os.listdir(local_dir)
        if f.lower().endswith((".html", ".htm"))
    )
    if not html_files:
        print(f"[local] no .html files in {local_dir}")
        return all_rows
    for path in html_files:
        notice = _notice_from_filename(os.path.basename(path))
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            html = fh.read()
        # use the filename as source_url stand-in
        page_rows = parse_html(html, f"file://{os.path.abspath(path)}", notice)
        print(f"[local] {os.path.basename(path)} -> {len(page_rows)} case rows")
        all_rows.extend(page_rows)
    return all_rows


def _notice_from_filename(name: str) -> str:
    low = name.lower()
    if "final_admin" in low or "final-admin" in low or "administrative" in low:
        return "Final Administrative Determination"
    if "final" in low:
        return "Notice of Final Determination"
    if "action" in low:
        return "Notice of Action"
    if "archive" in low:
        return "EAPA Actions Archive"
    return "EAPA"


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", default=DEFAULT_OUT,
                        help=f"Output CSV path (default: {DEFAULT_OUT})")
    parser.add_argument("--from-local", metavar="DIR", default=None,
                        help="Parse saved .html files from DIR instead of / in "
                             "addition to fetching live (fallback when blocked).")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print what would be written; do not write the CSV.")
    parser.add_argument("--no-pdf", action="store_true",
                        help="Skip PDF text enrichment even if a backend is available.")
    args = parser.parse_args(argv)

    print(f"[env] PDF backend: {_PDF_BACKEND or 'none (links only)'}")

    rows: list[EapaRow] = []

    if args.from_local:
        # explicit local mode
        print(f"[mode] --from-local {args.from_local}")
        rows = collect_local(args.from_local)
    else:
        live_rows, any_success = collect_live(enrich_pdfs=not args.no_pdf)
        rows = live_rows
        if not any_success:
            print("[warn] all live pages were blocked / failed.")
            fallback = DEFAULT_LOCAL_DIR
            if os.path.isdir(fallback):
                print(f"[fallback] parsing saved pages from {fallback}")
                rows = collect_local(fallback)
            else:
                print(f"[fallback] no local dir '{fallback}' to fall back to. "
                      f"Save pages there and re-run with --from-local {fallback}.")

    deduped = dedupe(rows)

    if not deduped:
        print("\n[result] 0 cases extracted.")
        summarize(deduped)
        if args.dry_run:
            return 0
        # still (re)write an empty-with-header CSV so downstream is deterministic
        write_csv(deduped, args.out)
        print(f"[write] wrote header-only CSV to {args.out}")
        return 0

    summarize(deduped)

    if args.dry_run:
        print(f"\n[dry-run] would write {len(deduped)} rows to {args.out}")
        print("[dry-run] first rows:")
        _print_preview(deduped, limit=10)
        return 0

    write_csv(deduped, args.out)
    print(f"\n[write] wrote {len(deduped)} rows to {args.out}")
    _print_preview(deduped, limit=10)
    return 0


def _print_preview(rows: list[EapaRow], limit: int = 10) -> None:
    for r in rows[:limit]:
        print("  " + " | ".join([
            r.eapa_case,
            (r.respondents or "")[:40],
            (r.commodity or "")[:30],
            r.country_of_origin or "",
            r.determination_date or "",
            r.notice_type or "",
        ]))


if __name__ == "__main__":
    raise SystemExit(main())
