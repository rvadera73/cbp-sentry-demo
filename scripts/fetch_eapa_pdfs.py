#!/usr/bin/env python3
"""
fetch_eapa_pdfs.py — EAPA determination-PDF *entity + relationship* harvester.

This is a deeper companion to scripts/fetch_eapa.py. Where that script produces a
case-level roll-up from listing pages, THIS script downloads the individual CBP
EAPA notice PDFs and extracts the REAL parties named inside them
(importers/respondents, foreign suppliers/manufacturers, the alleger, and alleger
counsel) plus the within-case relationships between them. This is Gate-1-critical
real data.

WHY IT WORKS (validated):
  * The cbp.gov EAPA *listing* pages are Akamai-blocked (403), but the individual
    /document/publications/eapa-... LANDING pages AND the /sites/default/files/*.pdf
    PDFs are directly fetchable (200) with a browser User-Agent.
  * The case -> landing-page mapping is recovered from the Wayback snapshot of the
    listing pages (archive.org is not blocked). We use the availability API to find
    the closest snapshot, then fetch the raw (id_) capture and scrape the anchors.

PIPELINE:
  1. For each listing page, resolve the closest Wayback snapshot and scrape anchors
     matching /document/... whose text mentions "EAPA ... Case ####: <Respondent>
     (<notice type>, <date>)".  When a case appears with multiple notices, prefer
     "Notice of Determination as to Evasion" (names exporters + scheme) over
     "Initiation".
  2. For each selected case, fetch the landing page directly from cbp.gov, find the
     .pdf link, download it (cached under data/eapa_pdfs/), and parse the first ~8
     pages with pdfplumber.
  3. Extract per case (best-effort heuristics): importers/respondents, alleger +
     alleger counsel, foreign exporter/manufacturer/producer, country_of_origin and
     any transshipment country, adcvd case number(s), and commodity.
  4. Write three CSVs to services/api/reference/:
       eapa_entities.csv       (one row per entity per case)
       eapa_relationships.csv  (within-case edges)
       eapa_enriched.csv       (one roll-up row per case)

USAGE:
    python3 scripts/fetch_eapa_pdfs.py --limit 8      # quick validation on 8 cases
    python3 scripts/fetch_eapa_pdfs.py                # full run
    python3 scripts/fetch_eapa_pdfs.py --out-dir /some/dir

Idempotent. PDFs are cached under data/eapa_pdfs/ so re-runs don't re-download.

Honest caveat: this is messy free-text PDF parsing. Extraction is best-effort;
some rows will be noisy or blank. Determination notices parse far better than
Initiation notices (which name only the importer under investigation).
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass, field

try:
    import pdfplumber  # type: ignore
except ImportError:  # pragma: no cover
    print("FATAL: pdfplumber is required. pip install pdfplumber", file=sys.stderr)
    raise

# requests is optional; urllib works fine and is the fallback.
try:
    import requests  # type: ignore
    _HAVE_REQUESTS = True
except ImportError:  # pragma: no cover
    _HAVE_REQUESTS = False


# --------------------------------------------------------------------------- #
# Config
# --------------------------------------------------------------------------- #

LISTING_PAGES = [
    "https://www.cbp.gov/trade/eapa/notices-action",
    "https://www.cbp.gov/trade/trade-enforcement/tftea/eapa/eapa-actions-archive",
]

CBP_BASE = "https://www.cbp.gov"

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_OUT_DIR = os.path.join(REPO_ROOT, "services", "api", "reference")
PDF_CACHE_DIR = os.path.join(REPO_ROOT, "data", "eapa_pdfs")

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)
HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

REQUEST_TIMEOUT = 60
POLITE_DELAY = 1.2          # polite delay between cbp.gov fetches (Akamai rate-limits bursts)
MAX_RETRIES = 4
BACKOFF_BASE = 3.0
MAX_PDF_PAGES = 8
# cbp.gov returns 403 under Akamai *rate limiting* (not a permanent block) for the
# landing/PDF URLs — so we retry 403 with backoff rather than giving up immediately.
RETRYABLE_STATUS = {403, 429, 500, 502, 503, 504}

# Notice-type ranking: higher = preferred when a case has multiple notices.
NOTICE_RANK = [
    (re.compile(r"determination as to evasion", re.I), 3),
    (re.compile(r"final (administrative )?determination", re.I), 2),
    (re.compile(r"initiation", re.I), 1),
]


# --------------------------------------------------------------------------- #
# HTTP
# --------------------------------------------------------------------------- #

def _read_body(resp) -> bytes:
    data = resp.read()
    enc = (resp.headers.get("Content-Encoding") or "").lower()
    if "gzip" in enc:
        import gzip
        try:
            data = gzip.decompress(data)
        except Exception:
            pass
    elif "deflate" in enc:
        import zlib
        try:
            data = zlib.decompress(data)
        except Exception:
            try:
                data = zlib.decompress(data, -zlib.MAX_WBITS)
            except Exception:
                pass
    return data


def http_get(url: str) -> tuple[int, bytes | None]:
    """GET with retries/backoff. Returns (status, body|None). status 0 = net error.

    NOTE: we deliberately use urllib, NOT requests. cbp.gov sits behind Akamai,
    which fingerprints the `requests` library's TLS/header signature and returns
    403 for it — while the stdlib urllib client is served 200 with the same
    headers. (Verified empirically.) `requests`, if installed, is only used as a
    convenience elsewhere; all fetching goes through urllib here."""
    last = 0
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
                return resp.status, _read_body(resp)
        except urllib.error.HTTPError as e:  # type: ignore[attr-defined]
            last = e.code
            if e.code in RETRYABLE_STATUS and attempt < MAX_RETRIES:
                time.sleep(BACKOFF_BASE * attempt); continue
            return e.code, None
        except Exception as exc:  # network-level
            last = 0
            print(f"    [net error] {exc} (attempt {attempt})")
            time.sleep(BACKOFF_BASE * attempt)
    return last, None


# --------------------------------------------------------------------------- #
# Step 1: case -> landing URL map from Wayback
# --------------------------------------------------------------------------- #

@dataclass
class CaseNotice:
    eapa_case: str          # e.g. "EAPA-8201"
    respondent_text: str    # respondent portion of the anchor text
    notice_type: str        # notice type portion
    date_text: str          # date portion
    landing_path: str       # /document/publications/...
    consolidated: bool = False
    # archive-format anchors put the *commodity* after the dash, not the
    # respondent — so respondent_text is unreliable for those and must not be
    # used as an importer fallback.
    respondent_reliable: bool = True

    @property
    def rank(self) -> int:
        for pat, r in NOTICE_RANK:
            if pat.search(self.notice_type):
                return r
        return 0


# All anchors (we filter by href shape per-format below).
ANCHOR_RE = re.compile(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', re.I | re.S)

# notices-action format:
#   "EAPA [Cons.] Case ####: <Respondent> (<notice type>, <date>)"  -> /document/...
TITLE_RE = re.compile(
    r"EAPA\s+(Cons\.?|Consolidated)?\s*Case\s+(?:Number\s+)?(\d{3,5})\s*:\s*"
    r"(.*?)\s*\((.*?)(?:,\s*([^)]*))?\)\s*$",
    re.I | re.S,
)

# eapa-actions-archive format:
#   "EAPA Action: <notice type> in EAPA Case #### - <Respondent>"
#   (the href points at an intermediate /recent-eapa-actions/ page or /document/...)
ARCHIVE_TITLE_RE = re.compile(
    r"EAPA\s+Action:\s*(.*?)\s+in\s+EAPA\s+(?:Cons\.?\s+)?Case\s+(\d{3,5})\s*[-–—]\s*(.+)$",
    re.I | re.S,
)


def _strip_tags(t: str) -> str:
    t = re.sub(r"<[^>]+>", "", t)
    t = t.replace("&amp;", "&").replace("&nbsp;", " ")
    return re.sub(r"\s+", " ", t).strip()


_WB_HREF_RE = re.compile(r"^/web/\d+(?:id_|im_)?/(https?://[^/]*cbp\.gov)?(/.*)$", re.I)


def _unwrap_wayback_href(href: str) -> str:
    """Wayback pages rewrite links to /web/<ts>/https://www.cbp.gov/<path>.
    Recover the bare cbp.gov path so we can fetch it live."""
    m = _WB_HREF_RE.match(href)
    if m:
        return m.group(2)
    # absolute cbp.gov url -> path
    if href.startswith("http"):
        p = urllib.parse.urlparse(href)
        if "cbp.gov" in p.netloc:
            return p.path + (("?" + p.query) if p.query else "")
    return href


def _wayback_timestamp(page: str) -> str | None:
    """Resolve the closest snapshot timestamp. Tries the availability API first
    (it is occasionally flaky / returns empty) then falls back to the CDX API."""
    enc = urllib.parse.quote(page, safe="")
    # availability API
    for _ in range(2):
        status, body = http_get("http://archive.org/wayback/available?url=" + enc)
        if status == 200 and body:
            try:
                snap = json.loads(body).get("archived_snapshots", {}).get("closest", {})
                if snap.get("timestamp"):
                    return snap["timestamp"]
            except Exception:
                pass
        time.sleep(1.0)
    # CDX fallback: most-recent 200 capture
    cdx = ("http://web.archive.org/cdx/search/cdx?url=" + enc +
           "&output=json&filter=statuscode:200&limit=-3")
    status, body = http_get(cdx)
    if status == 200 and body:
        try:
            rows = json.loads(body)
            if len(rows) > 1:
                return rows[-1][1]  # last data row, timestamp column
        except Exception:
            pass
    return None


def wayback_snapshot_html(page: str) -> str | None:
    ts = _wayback_timestamp(page)
    if not ts:
        print(f"    [wayback] no snapshot resolvable for {page}")
        return None
    raw = f"http://web.archive.org/web/{ts}id_/{page}"
    status, body = http_get(raw)
    if status != 200 or not body:
        print(f"    [wayback] snapshot fetch failed ({status}) {raw}")
        return None
    print(f"    [wayback] {page} @ {ts} ({len(body)} bytes)")
    return body.decode("utf-8", "replace")


def collect_case_notices() -> list[CaseNotice]:
    seen: set[tuple[str, str]] = set()
    notices: list[CaseNotice] = []
    for page in LISTING_PAGES:
        print(f"[listing] {page}")
        html = wayback_snapshot_html(page)
        if not html:
            continue
        n = 0
        for href, raw_text in ANCHOR_RE.findall(html):
            text = _strip_tags(raw_text)
            if "EAPA" not in text.upper():
                continue
            # de-archive wayback-wrapped hrefs (e.g. /web/<ts>/https://www.cbp.gov/x)
            href = _unwrap_wayback_href(href)
            if not href.startswith("/"):
                continue

            cons = num = respondent = notice_type = date_text = None
            respondent_reliable = True
            m = TITLE_RE.search(text)
            if m:
                cons, num, respondent, notice_type, date_text = m.groups()
            else:
                am = ARCHIVE_TITLE_RE.search(text)
                if not am:
                    continue
                # only follow anchors that lead to an actual notice document / action page
                if not (href.startswith("/document/") or
                        "recent-eapa-actions" in href or "eapa-action" in href):
                    continue
                notice_type, num, respondent = am.groups()
                cons = "Cons" if "cons" in text.lower() else None
                # archive text after the dash is the COMMODITY, not the respondent
                respondent_reliable = False

            key = (num, href)
            if key in seen:
                continue
            seen.add(key)
            notices.append(CaseNotice(
                eapa_case=f"EAPA-{num}",
                respondent_reliable=respondent_reliable,
                respondent_text=(respondent or "").strip(" -–—:,"),
                notice_type=(notice_type or "").strip(),
                date_text=(date_text or "").strip(),
                landing_path=href,
                consolidated=bool(cons),
            ))
            n += 1
        print(f"    -> {n} EAPA case-notice anchors")
        time.sleep(POLITE_DELAY)
    return notices


def select_best_per_case(notices: list[CaseNotice]) -> list[CaseNotice]:
    """One notice per case, preferring Determination > Final > Initiation."""
    best: dict[str, CaseNotice] = {}
    for cn in notices:
        cur = best.get(cn.eapa_case)
        if cur is None or cn.rank > cur.rank:
            best[cn.eapa_case] = cn
    def _key(cn: CaseNotice) -> int:
        m = re.search(r"(\d+)", cn.eapa_case)
        return int(m.group(1)) if m else 0
    return sorted(best.values(), key=_key)


# --------------------------------------------------------------------------- #
# Step 2: landing page -> PDF (cached)
# --------------------------------------------------------------------------- #

PDF_LINK_RE = re.compile(r'href="([^"]+\.pdf)"', re.I)


DOC_LINK_RE = re.compile(r'href="(/document/[^"]+)"', re.I)


def find_pdf_url(landing_html: str) -> str | None:
    for href in PDF_LINK_RE.findall(landing_html):
        href = _unwrap_wayback_href(href)
        if "/sites/default/files/" in href or href.lower().endswith(".pdf"):
            return href if href.startswith("http") else CBP_BASE + href
    return None


def find_document_link(landing_html: str, case_num: str | None = None) -> str | None:
    """On intermediate archive 'action' pages there is no direct .pdf; they link
    to a /document/publications/... page which holds the PDF. Prefer the link
    whose slug contains the case number (avoids grabbing unrelated nav links)."""
    hrefs = [_unwrap_wayback_href(h) for h in DOC_LINK_RE.findall(landing_html)]
    if case_num:
        for h in hrefs:
            if case_num in h:
                return h if h.startswith("http") else CBP_BASE + h
        return None  # no case-specific document -> don't guess
    if hrefs:
        h = hrefs[0]
        return h if h.startswith("http") else CBP_BASE + h
    return None


def fetch_pdf_for_case(cn: CaseNotice) -> tuple[str | None, bytes | None]:
    """Return (pdf_url, pdf_bytes). Uses on-disk cache keyed by case number."""
    os.makedirs(PDF_CACHE_DIR, exist_ok=True)
    cache_path = os.path.join(PDF_CACHE_DIR, f"{cn.eapa_case}.pdf")
    meta_path = os.path.join(PDF_CACHE_DIR, f"{cn.eapa_case}.url")
    if os.path.exists(cache_path) and os.path.getsize(cache_path) > 1000:
        url = None
        if os.path.exists(meta_path):
            with open(meta_path, encoding="utf-8") as fh:
                url = fh.read().strip()
        with open(cache_path, "rb") as fh:
            return url, fh.read()

    landing = CBP_BASE + cn.landing_path
    status, body = http_get(landing)
    if status != 200 or not body:
        print(f"    [skip] {cn.eapa_case} landing {status}")
        return None, None
    html = body.decode("utf-8", "replace")
    case_num = cn.eapa_case.split("-")[-1]
    is_doc_landing = cn.landing_path.startswith("/document/")
    pdf_url = find_pdf_url(html) if is_doc_landing else None
    if not pdf_url:
        # intermediate 'action' page (archive listing) -> follow to matching /document page
        doc = find_document_link(html, case_num if not is_doc_landing else None)
        if doc and doc != landing:
            time.sleep(POLITE_DELAY)
            status, body2 = http_get(doc)
            if status == 200 and body2:
                pdf_url = find_pdf_url(body2.decode("utf-8", "replace"))
    if not pdf_url and is_doc_landing:
        pdf_url = find_pdf_url(html)
    if not pdf_url:
        print(f"    [skip] {cn.eapa_case} no case-specific PDF found")
        return None, None
    # guard against obviously-wrong PDFs (unrelated agency reports)
    if re.search(r"annual_review|amo_annual|/fy\d\d[_/]", pdf_url, re.I):
        print(f"    [skip] {cn.eapa_case} resolved to non-notice PDF ({pdf_url[-40:]})")
        return None, None
    time.sleep(POLITE_DELAY)
    status, pdf = http_get(pdf_url)
    if status != 200 or not pdf:
        print(f"    [skip] {cn.eapa_case} PDF fetch {status}")
        return pdf_url, None
    with open(cache_path, "wb") as fh:
        fh.write(pdf)
    with open(meta_path, "w", encoding="utf-8") as fh:
        fh.write(pdf_url)
    return pdf_url, pdf


def pdf_text(pdf_bytes: bytes, max_pages: int = MAX_PDF_PAGES) -> str:
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            return "\n".join((pg.extract_text() or "") for pg in pdf.pages[:max_pages])
    except Exception as exc:
        print(f"    [pdf parse error] {exc}")
        return ""


# --------------------------------------------------------------------------- #
# Step 3: extraction heuristics
# --------------------------------------------------------------------------- #

COMPANY_SUFFIX = (
    r"(?:Inc|LLC|L\.L\.C|Ltd|Limited|Corp|Corporation|Co|Company|Coalition|Group|"
    r"Trading|Industries|Industry|Manufacturing|Enterprises|Holdings|International|"
    r"JSC|Pte|Sdn\s+Bhd|GmbH|S\.A\.|S\.R\.L|SRL|LP|L\.P|Private\s+Limited)"
)
COMPANY_NAME_RE = re.compile(
    r"\b([A-Z][A-Za-z0-9&.,'\-]*(?:\s+[A-Z][A-Za-z0-9&.,'\-]*){0,6}?,?\s+" + COMPANY_SUFFIX + r"\.?)",
)

COUNTRIES = [
    "the People's Republic of China", "People's Republic of China", "China",
    "Vietnam", "Viet Nam", "Malaysia", "Thailand", "Cambodia", "Taiwan", "India",
    "Turkey", "Indonesia", "South Korea", "Korea", "Mexico", "Sri Lanka", "Laos",
    "Philippines", "Dominican Republic", "United Arab Emirates", "Oman", "Pakistan",
    "Bangladesh", "Sri Lanka", "Guatemala", "Colombia", "Brazil",
]
COUNTRY_ALT = "|".join(re.escape(c) for c in COUNTRIES)

ADCVD_RE = re.compile(r"\b([AC]-\d{3}-\d{3})\b")

# "importers X (X), Y (Y), ... (collectively, ...the Importers...)"
IMPORTERS_BLOCK_RE = re.compile(
    r"importers?\s+(.{5,1200}?)\(collectively", re.I | re.S)

# Alleger — several phrasings appear. In priority order:
#   (a) the explicit alias form: <Name> ("<Short>" or "the Alleger")
#   (b) a "the Alleger, <Company Inc.>" form
#   (c) "<Name> (the Alleger)" where <Name> may lead with Coalition/Committee/the
# A "word" token permitted inside an org name (allows lowercase connectors like
# "of"/"for"/"and" so "Coalition of Freight Coupler Producers" survives).
_ORG_WORD = r"(?:[A-Z][A-Za-z0-9&.'\-]*|of|for|and|the)"
# greedy on the name run so "CP Kelco U.S., Inc." is captured whole (not just "U.S., Inc")
ALLEGER_ALIAS_RE = re.compile(
    r"(?:^|[.,;:]\s|\s)((?:[A-Z][A-Za-z0-9&.,'\-]*)(?:[ ,]+" + _ORG_WORD + r"){0,7})\s*"
    r"\(\s*[\"“'][^\"”']{2,60}[\"”']\s+or\s+[\"“']?the Alleger",
)
ALLEGER_THE_RE = re.compile(
    r"\bthe Alleger,\s*((?:[A-Z][A-Za-z0-9&.,'\-]*)(?:\s+" + _ORG_WORD + r"){0,7}?,?\s*"
    + COMPANY_SUFFIX + r"\.?)",
)
ALLEGER_PAREN_RE = re.compile(
    r"\b((?:Coalition|Committee|Ad Hoc|American|National)\b(?:\s+" + _ORG_WORD + r"){0,8}?"
    r"|[A-Z][A-Za-z0-9&.,'\-]*(?:\s+" + _ORG_WORD + r"){0,6}?,?\s*" + COMPANY_SUFFIX + r"\.?)"
    r"\s*\(\s*the Alleger",
)
ALLEGER_ONBEHALF_RE = re.compile(
    r"[Oo]n behalf of\s+(?:the\s+)?((?:[A-Z][A-Za-z0-9&.,'\-]*)(?:\s+" + _ORG_WORD + r"){0,7}?,?\s*"
    + COMPANY_SUFFIX + r"\.?)",
)

# "Counsel to: <Alleger>" header block (page 1)
COUNSEL_TO_RE = re.compile(r"Counsel\s+to:\s*(.+)", re.I)

# Foreign supplier/manufacturer/producer: the captured name MUST begin with an
# uppercase word and end in a company suffix (avoids "in Mexico" / sentence bits).
FOREIGN_ROLE_RE = re.compile(
    r"(?:exporter|manufacturer|producer|supplied by|manufactured by|produced by|"
    r"shipped by|exported by|purchased from)\s*(?:of\s+the\s+covered\s+merchandise|"
    r"is|are|was|were|:|,)?\s*"
    r"([A-Z][A-Za-z0-9&.'\-]*(?:\s+[A-Z][A-Za-z0-9&.'\-]*){0,6}?,?\s*" + COMPANY_SUFFIX + r"\.?)",
    re.I,
)
TRANSSHIP_RE = re.compile(
    r"transship(?:ped|ment|ing)?\s+(?:through|via|to|through\s+)?\s*(" + COUNTRY_ALT + r")",
    re.I,
)

# noise: strings that are agencies / law-generic and should not be entities
NOISE_RE = re.compile(
    r"\b(U\.S\.\s*Customs|United States|Customs and Border|CBP|Department of Commerce|"
    r"Dept\.?\s+Co|Federal Register|Trade Remedy|TRLED|the Order|the Act|the Importers|"
    r"Antidumping Duty|Countervailing|Public Version|the Alleger|the Government|"
    r"Fed\.?\s+Reg|Interim Measures|Notice of)\b",
    re.I,
)


def _norm(name: str) -> str:
    name = re.sub(r"\s+", " ", name).strip(" .,-–—:;\"'")
    return name


def _is_company(name: str) -> bool:
    if not name or len(name) < 3 or len(name) > 90:
        return False
    if NOISE_RE.search(name):
        return False
    return True


# tokens that indicate a captured span is a sentence fragment, not a name
_FRAGMENT_START = re.compile(r"^(?:in|of|the|and|as|to|is|are|was|were|s,|by|from|"
                             r"or|a|an|that|which|for|with|at)\b", re.I)
# generic single-noun words that must not stand alone as an entity
_GENERIC = re.compile(r"^(?:Negotiations|Investigations|Producers|Products|"
                      r"Manufacturers|Importers|Company|Corporation|Group|"
                      r"Trading|Committee|Coalition)$", re.I)


def _is_supplier_name(name: str) -> bool:
    if not _is_company(name):
        return False
    if _FRAGMENT_START.match(name):
        return False
    if not re.match(r"^[A-Z]", name):
        return False
    # must have at least two tokens (a name + suffix) and not be a lone generic word
    if len(re.findall(r"[A-Za-z]{2,}", name)) < 2:
        return False
    # reject if an interior word is lowercase (indicates a sentence fragment like
    # "Hermpac informed Co") — real company names are Title-Cased or all-caps.
    words = name.replace(",", " ").split()
    for w in words[:-1]:  # last token is the suffix (Co/Inc/Ltd)
        if w and w[0].islower() and w.lower() not in ("of", "and", "the", "de", "y"):
            return False
    return True


def _is_alleger(name: str) -> bool:
    if not name or len(name) < 4 or len(name) > 90:
        return False
    if NOISE_RE.search(name):
        return False
    if _FRAGMENT_START.match(name) or _GENERIC.match(name):
        return False
    if not re.match(r"^[A-Z]", name):
        return False
    return True


def _split_paired(name: str) -> list[str]:
    """Split a multi-respondent string into individual company names.

    CBP uses ';' as the real separator for long importer lists
    ("AAA Innovation LLC; Astera Kitchen and Bath, Inc.; FTR LLC; ..."). Only when
    there is no ';' do we split a bare "X and Y" pair (the two-name case) — this
    avoids chopping "Astera Kitchen and Bath, Inc." in half. A trailing
    ", and Z" / "and Z" enumerator is also handled."""
    if ";" in name:
        raw = [p.strip() for p in name.split(";")]
        parts = []
        for p in raw:
            # a final list element may be "and KSA Supply Corporation"
            p = re.sub(r"^and\s+", "", p, flags=re.I)
            if p:
                parts.append(p)
        return [_norm(p) for p in parts if _norm(p)]
    parts = re.split(r"\s+and\s+", name)
    return [_norm(p) for p in parts if _norm(p)]


def extract_country(text: str) -> str:
    m = re.search(r"\bfrom\s+(" + COUNTRY_ALT + r")\b", text)
    if not m:
        m = re.search(r"\b(" + COUNTRY_ALT + r")\b", text)
    if not m:
        return ""
    c = m.group(1)
    if "People's Republic" in c or c == "China":
        return "China"
    if c in ("Viet Nam",):
        return "Vietnam"
    return c


def extract_commodity(text: str) -> str:
    # order "...on <commodity> ("ABBR" or "covered merchandise") from ..."
    m = re.search(
        r"(?:AD|CVD|antidumping duty|countervailing duty)[^.\n]{0,60}?\border[^.\n]{0,40}?\bon\s+"
        r"([a-z][A-Za-z0-9 ,/&\-]{4,70}?)\s*\(", text)
    if m:
        return _norm(m.group(1))
    m = re.search(r"covered merchandise[^.\n]{0,40}?\bis\s+([a-z][A-Za-z0-9 ,/&\-]{4,70})", text, re.I)
    if m:
        return _norm(m.group(1))
    return ""


@dataclass
class CaseExtract:
    cn: CaseNotice
    pdf_url: str = ""
    importers: list[str] = field(default_factory=list)
    foreign_suppliers: list[str] = field(default_factory=list)
    alleger: str = ""
    counsel: str = ""
    country: str = ""
    transship_country: str = ""
    commodity: str = ""
    adcvd_case: str = ""
    paired_from_respondent: list[str] = field(default_factory=list)


def extract_case(cn: CaseNotice, text: str, pdf_url: str) -> CaseExtract:
    ex = CaseExtract(cn=cn, pdf_url=pdf_url)

    # ADCVD
    ad = ADCVD_RE.findall(text)
    if ad:
        # keep unique, order-preserving, join A/C codes
        seen = []
        for a in ad:
            if a not in seen:
                seen.append(a)
        ex.adcvd_case = ";".join(seen[:4])

    ex.country = extract_country(text)
    ex.commodity = extract_commodity(text)

    mt = TRANSSHIP_RE.search(text)
    if mt:
        tc = mt.group(1)
        ex.transship_country = "China" if "China" in tc or "People" in tc else tc

    # Importers: from the "(collectively" block if present (determinations),
    # else fall back to the respondent text from the listing anchor.
    imp_names: list[str] = []
    mb = IMPORTERS_BLOCK_RE.search(text)
    if mb:
        block = mb.group(1)
        # names look like "Chasoe World Inc. (Chasoe), Eminent World Trade Inc. (Eminent World), ..."
        for m in COMPANY_NAME_RE.finditer(block):
            nm = _norm(m.group(1))
            if _is_company(nm) and nm not in imp_names:
                imp_names.append(nm)
    if (not imp_names and cn.respondent_reliable and cn.respondent_text
            and "Various Importers" not in cn.respondent_text):
        for nm in _split_paired(cn.respondent_text):
            if _is_company(nm) or len(nm.split()) >= 2:
                if nm not in imp_names:
                    imp_names.append(nm)
    ex.importers = imp_names

    # paired related entities: ONLY the genuine two-name "X and Y" respondent
    # (e.g. "Dymatec USA, LLC and Dymatec, Ltd."). Semicolon-separated lists are
    # co-respondents, not related entities, so they are excluded here.
    if (cn.respondent_reliable and cn.respondent_text and " and " in cn.respondent_text
            and ";" not in cn.respondent_text and "Various" not in cn.respondent_text):
        pr = re.split(r"\s+and\s+", cn.respondent_text)
        pr = [_norm(p) for p in pr if _norm(p)]
        if len(pr) == 2 and all(_is_company(p) for p in pr):
            ex.paired_from_respondent = pr

    # Alleger — try alias form first (cleanest), then "the Alleger, <Co>",
    # then "<Name> (the Alleger)", then "On behalf of <Co>".
    for rx in (ALLEGER_ALIAS_RE, ALLEGER_THE_RE, ALLEGER_PAREN_RE, ALLEGER_ONBEHALF_RE):
        mo = rx.search(text)
        if mo:
            cand = _norm(mo.group(1))
            # trim stray leading boilerplate ("the Alleger, X" -> "X", "the X" -> "X")
            cand = re.sub(r"^(?:the\s+)?Alleger,?\s+", "", cand, flags=re.I)
            cand = re.sub(r"^(?:the|The)\s+", "", cand)
            # the alleger is the domestic petitioner — never one of the respondents
            if _is_alleger(cand) and cand not in ex.importers:
                ex.alleger = cand
                break

    # Counsel (page-1 "Counsel to: <alleger>" — the law firm precedes it in the
    # address block; grab the nearest company-suffix name just above the marker)
    mc = COUNSEL_TO_RE.search(text)
    if mc:
        head = text[:mc.start()]
        # last company-ish name before "Counsel to:" is usually the firm
        firms = [ _norm(m.group(1)) for m in COMPANY_NAME_RE.finditer(head) ]
        firms = [f for f in firms if _is_company(f)]
        if firms:
            # prefer one containing Law/LLP/LLC/Firm
            law = [f for f in firms if re.search(r"Law|LLP|Firm|PLLC|P\.C", f)]
            ex.counsel = (law[-1] if law else firms[-1])
        # if the anchor said "On behalf of" wasn't found, the Counsel-to target is the alleger
        if not ex.alleger:
            cand = _norm(mc.group(1))
            if _is_company(cand):
                ex.alleger = cand

    # Foreign suppliers / manufacturers / producers (strict company names only)
    for m in FOREIGN_ROLE_RE.finditer(text):
        nm = _norm(m.group(1))
        if (_is_supplier_name(nm) and nm not in ex.importers
                and nm != ex.alleger and nm not in ex.foreign_suppliers):
            ex.foreign_suppliers.append(nm)

    return ex


# --------------------------------------------------------------------------- #
# Step 4: build CSV rows
# --------------------------------------------------------------------------- #

ENTITY_FIELDS = ["eapa_case", "entity_name", "role", "country", "source_pdf"]
REL_FIELDS = ["eapa_case", "src_entity", "rel_type", "dst_entity"]
ENRICHED_FIELDS = ["eapa_case", "importers", "foreign_suppliers", "alleger",
                   "country", "commodity", "adcvd_case", "determination_date",
                   "notice_type", "source_pdf"]


def build_rows(ex: CaseExtract):
    case = ex.cn.eapa_case
    src = ex.pdf_url
    entities = []
    rels = []

    imp_country = ""  # importers are US; leave blank
    for nm in ex.importers:
        entities.append({"eapa_case": case, "entity_name": nm, "role": "importer",
                         "country": "", "source_pdf": src})
    for nm in ex.foreign_suppliers:
        role = "foreign_supplier"
        low = nm.lower()
        if "manufactur" in low:
            role = "manufacturer"
        entities.append({"eapa_case": case, "entity_name": nm, "role": role,
                         "country": ex.country, "source_pdf": src})
    if ex.alleger:
        entities.append({"eapa_case": case, "entity_name": ex.alleger, "role": "alleger",
                         "country": "", "source_pdf": src})
    if ex.counsel and ex.counsel != ex.alleger:
        entities.append({"eapa_case": case, "entity_name": ex.counsel, "role": "counsel",
                         "country": "", "source_pdf": src})

    # relationships -------------------------------------------------------
    imps = ex.importers
    # importer <-> importer = CO_RESPONDENT (undirected, emit once per pair)
    for i in range(len(imps)):
        for j in range(i + 1, len(imps)):
            rels.append({"eapa_case": case, "src_entity": imps[i],
                         "rel_type": "CO_RESPONDENT", "dst_entity": imps[j]})
    # importer -> foreign supplier = SUPPLIED_BY
    for imp in imps:
        for fs in ex.foreign_suppliers:
            rels.append({"eapa_case": case, "src_entity": imp,
                         "rel_type": "SUPPLIED_BY", "dst_entity": fs})
    # respondent -> alleger = ALLEGED_BY
    if ex.alleger:
        for imp in imps:
            rels.append({"eapa_case": case, "src_entity": imp,
                         "rel_type": "ALLEGED_BY", "dst_entity": ex.alleger})
    # paired names in one respondent field = RELATED_ENTITY
    pr = ex.paired_from_respondent
    for i in range(len(pr)):
        for j in range(i + 1, len(pr)):
            rels.append({"eapa_case": case, "src_entity": pr[i],
                         "rel_type": "RELATED_ENTITY", "dst_entity": pr[j]})

    enriched = {
        "eapa_case": case,
        "importers": "; ".join(ex.importers),
        "foreign_suppliers": "; ".join(ex.foreign_suppliers),
        "alleger": ex.alleger,
        "country": ex.country,
        "commodity": ex.commodity,
        "adcvd_case": ex.adcvd_case,
        "determination_date": ex.cn.date_text,
        "notice_type": ex.cn.notice_type,
        "source_pdf": src,
    }
    return entities, rels, enriched


def write_csv(path: str, fields: list[str], rows: list[dict]):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow(r)


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--limit", type=int, default=0,
                    help="Process only the first N selected cases (0 = all).")
    ap.add_argument("--out-dir", default=DEFAULT_OUT_DIR,
                    help=f"Output directory for CSVs (default: {DEFAULT_OUT_DIR})")
    args = ap.parse_args(argv)

    print(f"[env] pdfplumber={pdfplumber.__version__} http=urllib "
          f"(requests {'present-but-unused' if _HAVE_REQUESTS else 'absent'}; "
          f"cbp.gov Akamai 403s the requests fingerprint)")
    print(f"[env] pdf cache: {PDF_CACHE_DIR}")
    print(f"[env] out dir  : {args.out_dir}")

    notices = collect_case_notices()
    cases = select_best_per_case(notices)
    print(f"\n[cases] {len(notices)} anchors -> {len(cases)} unique cases")
    if args.limit:
        cases = cases[:args.limit]
        print(f"[cases] limited to first {len(cases)}")

    all_entities, all_rels, all_enriched = [], [], []
    stats = {"reachable": 0, "no_pdf": 0, "failed": [], "various_resolved": 0}

    for i, cn in enumerate(cases, 1):
        print(f"[{i}/{len(cases)}] {cn.eapa_case} :: {cn.notice_type[:40]} :: "
              f"{cn.respondent_text[:45]}")
        pdf_url, pdf = fetch_pdf_for_case(cn)
        if not pdf:
            stats["failed"].append(cn.eapa_case)
            # still emit an enriched roll-up from the anchor metadata (but only
            # trust the respondent text when it names real parties, not the
            # archive-page commodity descriptions)
            ex = CaseExtract(cn=cn, pdf_url=pdf_url or "")
            if cn.respondent_reliable and cn.respondent_text and "Various" not in cn.respondent_text:
                ex.importers = [n for n in _split_paired(cn.respondent_text) if _is_company(n)]
            e, r, en = build_rows(ex)
            all_entities += e; all_rels += r; all_enriched.append(en)
            time.sleep(POLITE_DELAY)
            continue
        stats["reachable"] += 1
        text = pdf_text(pdf)
        ex = extract_case(cn, text, pdf_url or "")
        if "Various Importers" in cn.respondent_text and ex.importers:
            stats["various_resolved"] += 1
        e, r, en = build_rows(ex)
        all_entities += e; all_rels += r; all_enriched.append(en)
        time.sleep(POLITE_DELAY)

    ent_path = os.path.join(args.out_dir, "eapa_entities.csv")
    rel_path = os.path.join(args.out_dir, "eapa_relationships.csv")
    enr_path = os.path.join(args.out_dir, "eapa_enriched.csv")
    write_csv(ent_path, ENTITY_FIELDS, all_entities)
    write_csv(rel_path, REL_FIELDS, all_rels)
    write_csv(enr_path, ENRICHED_FIELDS, all_enriched)

    # summary -----------------------------------------------------------------
    by_role: dict[str, int] = {}
    for e in all_entities:
        by_role[e["role"]] = by_role.get(e["role"], 0) + 1
    by_rel: dict[str, int] = {}
    for r in all_rels:
        by_rel[r["rel_type"]] = by_rel.get(r["rel_type"], 0) + 1

    print("\n=== SUMMARY ===")
    print(f"  cases processed        : {len(cases)}")
    print(f"  cases with a PDF       : {stats['reachable']}")
    print(f"  cases failed/no PDF    : {len(stats['failed'])}")
    print(f"  'Various Importers' resolved to real names : {stats['various_resolved']}")
    print(f"  entities total         : {len(all_entities)}")
    for role, n in sorted(by_role.items()):
        print(f"      {role:16s}: {n}")
    print(f"  relationships total    : {len(all_rels)}")
    for rt, n in sorted(by_rel.items()):
        print(f"      {rt:16s}: {n}")
    if stats["failed"]:
        print(f"  failed cases: {', '.join(stats['failed'][:40])}")
    print(f"\n[write] {ent_path}")
    print(f"[write] {rel_path}")
    print(f"[write] {enr_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
