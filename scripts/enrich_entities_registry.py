#!/usr/bin/env python3
"""
enrich_entities_registry.py — Resolve REAL EAPA entities against PUBLIC company
registries to enrich them with addresses, ownership, affiliates, and officers.

This closes the CORD coverage gap: the EAPA determinations give us entity NAMES
and roles, but no structured registry facts. Here we take the distinct
`entity_name` values from services/api/reference/eapa_entities.csv and resolve
each against public registries:

  1. GLEIF (Global LEI Foundation) — free, no API key. PRIMARY source.
     * fuzzy legalName search -> best LEI record (address, status).
     * direct-parent / direct-children relationships -> ownership graph.
     Covers only entities that hold an LEI (larger / international filers);
     many small importers won't match. That is expected.

  2. SEC EDGAR — free, but requires a descriptive User-Agent (SEC fair-access).
     Light match only: company search -> CIK + conformed name if a PUBLIC
     filer exists. Most EAPA importers are private and won't be found.

  3. OpenCorporates — US state registries + officers, the richest US source,
     but token-gated. Activates automatically iff env var OC_API_TOKEN is set;
     otherwise it prints a clear skip line and continues.

Everything uses stdlib urllib (NOT requests) because some government endpoints
fingerprint and deny non-browser clients. We are polite: small inter-request
delay, retries with backoff, and we skip individual failures rather than abort.

Outputs (written to services/api/reference/):
  * entity_registry.csv
      entity_name, source, matched_name, identifier, country, address,
      incorporation_date, status
  * entity_registry_relationships.csv
      src_name, rel_type, dst_name, dst_identifier, source
        rel_type in {OWNED_BY, PARENT_OF, SHARED_OFFICER, AFFILIATE}

Usage:
    python3 scripts/enrich_entities_registry.py                 # full run
    python3 scripts/enrich_entities_registry.py --limit 20      # first 20 names
    python3 scripts/enrich_entities_registry.py --dry-run       # no files written
    OC_API_TOKEN=xxx python3 scripts/enrich_entities_registry.py # + OpenCorporates

Idempotent: re-running overwrites the two output CSVs from scratch.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
REF_DIR = os.path.join(REPO, "services", "api", "reference")
INPUT_CSV = os.path.join(REF_DIR, "eapa_entities.csv")
OUT_REGISTRY = os.path.join(REF_DIR, "entity_registry.csv")
OUT_RELATIONSHIPS = os.path.join(REF_DIR, "entity_registry_relationships.csv")

# --------------------------------------------------------------------------- #
# HTTP settings
# --------------------------------------------------------------------------- #
BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
# SEC fair-access policy REQUIRES a descriptive UA with contact info.
SEC_UA = "cbp-sentry-research contact@cbp-sentry.local"

REQUEST_DELAY = 0.3      # polite delay between HTTP requests (seconds)
MAX_RETRIES = 3
BACKOFF_BASE = 1.5       # seconds; exponential backoff base
TIMEOUT = 30

GLEIF_BASE = "https://api.gleif.org/api/v1"
EDGAR_BASE = "https://www.sec.gov/cgi-bin/browse-edgar"
OC_BASE = "https://api.opencorporates.com/v0.4"


# --------------------------------------------------------------------------- #
# HTTP helper
# --------------------------------------------------------------------------- #
def http_get(url: str, ua: str, accept: str | None = None) -> tuple[int, str]:
    """
    GET a URL with the given User-Agent. Returns (status_code, body_text).

    Retries with exponential backoff on 429/503/timeouts. A 404 is returned
    immediately (it is a meaningful "no such record" for several endpoints).
    Never raises for HTTP errors — returns the status so the caller decides.
    """
    headers = {"User-Agent": ua, "Accept-Language": "en-US,en;q=0.9"}
    if accept:
        headers["Accept"] = accept
    last_status = 0
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                return resp.status, resp.read().decode("utf-8", "ignore")
        except urllib.error.HTTPError as e:
            last_status = e.code
            # 404 is meaningful (e.g. GLEIF direct-parent = no parent on record).
            if e.code == 404:
                return 404, ""
            # Retry on rate-limit / transient server errors.
            if e.code in (429, 500, 502, 503, 504) and attempt < MAX_RETRIES:
                time.sleep(BACKOFF_BASE ** attempt)
                continue
            return e.code, ""
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            last_status = -1
            if attempt < MAX_RETRIES:
                time.sleep(BACKOFF_BASE ** attempt)
                continue
            sys.stderr.write(f"    [net] giving up on {url}: {e}\n")
            return -1, ""
    return last_status, ""


def http_get_json(url: str, ua: str) -> tuple[int, dict | None]:
    status, body = http_get(url, ua, accept="application/vnd.api+json")
    if status == 200 and body:
        try:
            return status, json.loads(body)
        except json.JSONDecodeError:
            return status, None
    return status, None


# --------------------------------------------------------------------------- #
# Name normalization / matching
# --------------------------------------------------------------------------- #
_SUFFIX_RE = re.compile(
    r"\b(inc|incorporated|llc|l\.l\.c|ltd|limited|corp|corporation|co|company|"
    r"gmbh|srl|s\.r\.l|sa|s\.a|plc|lp|llp|group|holdings?|international|intl)\b",
    re.IGNORECASE,
)


def normalize_name(name: str) -> str:
    """Lowercase, strip punctuation + common corporate suffixes for comparison."""
    n = name.lower()
    n = re.sub(r"[.,&/()\-]", " ", n)
    n = _SUFFIX_RE.sub(" ", n)
    n = re.sub(r"\s+", " ", n).strip()
    return n


def names_equal(a: str, b: str) -> bool:
    return normalize_name(a) == normalize_name(b)


def name_overlap_ok(query: str, candidate: str) -> bool:
    """
    Guard against GLEIF/EDGAR fuzzy ranking returning spurious matches
    (e.g. "Allied Group" -> "Allied Marketing Group Inc."). Accept only when
    the normalized token sets are equal OR one is a subset of the other, so we
    require the query's meaningful words to actually appear in the candidate.
    """
    qa = set(normalize_name(query).split())
    qb = set(normalize_name(candidate).split())
    if not qa or not qb:
        return False
    if qa == qb:
        return True
    # subset either direction covers "Accuride" vs "Accuride Corp" style matches
    return qa <= qb or qb <= qa


# --------------------------------------------------------------------------- #
# GLEIF
# --------------------------------------------------------------------------- #
def gleif_search(name: str) -> dict | None:
    """Search GLEIF by legalName; return the best-matching LEI record dict."""
    url = (
        f"{GLEIF_BASE}/lei-records?filter[entity.legalName]="
        f"{urllib.parse.quote(name)}&page[size]=3"
    )
    status, data = http_get_json(url, BROWSER_UA)
    if status != 200 or not data:
        return None
    recs = data.get("data") or []
    if not recs:
        return None
    # Prefer an exact normalized-name match; else fall back to the first.
    for rec in recs:
        legal = (
            rec.get("attributes", {})
            .get("entity", {})
            .get("legalName", {})
            .get("name", "")
        )
        if legal and names_equal(legal, name):
            return rec
    # Fall back to the first result only if its name plausibly overlaps the
    # query — GLEIF's fuzzy ranking otherwise returns unrelated companies.
    first = recs[0]
    first_name = (
        first.get("attributes", {})
        .get("entity", {})
        .get("legalName", {})
        .get("name", "")
    )
    if first_name and name_overlap_ok(name, first_name):
        return first
    return None


def gleif_record_fields(rec: dict) -> dict:
    """Extract the fields we persist from a GLEIF LEI record."""
    lei = rec.get("id", "")
    ent = rec.get("attributes", {}).get("entity", {})
    legal_name = ent.get("legalName", {}).get("name", "")
    addr = ent.get("legalAddress", {}) or {}
    lines = addr.get("addressLines") or []
    first_line = lines[0] if lines else ""
    city = addr.get("city", "") or ""
    country = addr.get("country", "") or ""
    # Human-readable address string.
    parts = [p for p in [first_line, city, addr.get("region", ""), country] if p]
    address = ", ".join(parts)
    status = ent.get("status", "") or ""
    return {
        "lei": lei,
        "legal_name": legal_name,
        "country": country,
        "address": address,
        "status": status,
    }


def gleif_related(lei: str, rel: str) -> list[dict]:
    """
    Fetch direct-parent or direct-children related LEI records.
    Returns a list of {lei, name} (parent endpoint returns a single object;
    children returns a list; 404 => none on record).
    """
    url = f"{GLEIF_BASE}/lei-records/{lei}/{rel}"
    status, data = http_get_json(url, BROWSER_UA)
    if status != 200 or not data:
        return []
    payload = data.get("data")
    out = []
    items = payload if isinstance(payload, list) else ([payload] if payload else [])
    for item in items:
        rlei = item.get("id", "")
        rname = (
            item.get("attributes", {})
            .get("entity", {})
            .get("legalName", {})
            .get("name", "")
        )
        if rlei:
            out.append({"lei": rlei, "name": rname})
    return out


# --------------------------------------------------------------------------- #
# SEC EDGAR (light match)
# --------------------------------------------------------------------------- #
def _edgar_conformed(body: str) -> dict | None:
    """Parse a single-company <company-info> block: cik, conformed-name, addr."""
    cik = re.search(r"<cik>([^<]+)</cik>", body)
    cname = re.search(r"<conformed-name>([^<]+)</conformed-name>", body)
    if not cik or not cname:
        return None
    state_inc = re.search(r"<state-of-incorporation>([^<]+)</", body)
    # Grab a business address if present.
    biz = re.search(
        r'<address type="business">(.*?)</address>', body, re.DOTALL
    )
    addr = ""
    if biz:
        blk = biz.group(1)
        city = re.search(r"<city>([^<]+)</", blk)
        state = re.search(r"<state>([^<]+)</", blk)
        street = re.search(r"<street1>([^<]+)</", blk)
        zipc = re.search(r"<zip>([^<]+)</", blk)
        addr = ", ".join(
            p.group(1) for p in [street, city, state, zipc] if p
        )
    return {
        "cik": cik.group(1),
        "name": cname.group(1),
        "address": addr,
        "state_inc": state_inc.group(1) if state_inc else "",
    }


def edgar_match(name: str) -> dict | None:
    """
    Light EDGAR match. Returns {cik, name, address, state_inc} or None.

    EDGAR's company search prefix-matches. When exactly one company resolves,
    it returns a <company-info> detail block with <conformed-name>. When many
    prefix-match, it returns <entry> blocks with only <cik>. In the multi-match
    case we take the first CIK and do ONE follow-up CIK= lookup to obtain a
    clean conformed name (marked as a fuzzy match by the caller).
    """
    url = (
        f"{EDGAR_BASE}?action=getcompany&company={urllib.parse.quote(name)}"
        f"&type=&output=atom"
    )
    status, body = http_get(url, SEC_UA, accept="application/atom+xml")
    if status != 200 or not body:
        return None
    # Single exact company -> detail block with conformed-name.
    single = _edgar_conformed(body)
    if single:
        single["exact"] = True
        return single
    # Multi-match: pull CIKs, resolve the first one by CIK for a clean name.
    ciks = re.findall(r"<cik>([^<]+)</cik>", body)
    if not ciks:
        return None
    time.sleep(REQUEST_DELAY)
    cik_url = (
        f"{EDGAR_BASE}?action=getcompany&CIK={ciks[0]}&type=&output=atom"
    )
    status2, body2 = http_get(cik_url, SEC_UA, accept="application/atom+xml")
    if status2 != 200 or not body2:
        return None
    detail = _edgar_conformed(body2)
    if detail:
        detail["exact"] = False
    return detail


# --------------------------------------------------------------------------- #
# OpenCorporates (token-gated: officers, US state registrations)
# --------------------------------------------------------------------------- #
def oc_search(name: str, token: str) -> dict | None:
    """Search OpenCorporates; return the top company dict or None."""
    url = (
        f"{OC_BASE}/companies/search?q={urllib.parse.quote(name)}"
        f"&api_token={urllib.parse.quote(token)}"
    )
    status, data = http_get_json(url, BROWSER_UA)
    if status != 200 or not data:
        return None
    companies = data.get("results", {}).get("companies") or []
    if not companies:
        return None
    return companies[0].get("company")


def oc_officers(jurisdiction: str, company_number: str, token: str) -> list[str]:
    """Fetch officer names from a company's OpenCorporates detail endpoint."""
    url = (
        f"{OC_BASE}/companies/{jurisdiction}/{company_number}"
        f"?api_token={urllib.parse.quote(token)}"
    )
    status, data = http_get_json(url, BROWSER_UA)
    if status != 200 or not data:
        return []
    company = data.get("results", {}).get("company", {})
    officers = []
    for o in company.get("officers") or []:
        nm = (o.get("officer") or {}).get("name")
        if nm:
            officers.append(nm)
    return officers


# --------------------------------------------------------------------------- #
# Input loading
# --------------------------------------------------------------------------- #
def load_distinct_names(path: str) -> list[str]:
    seen = set()
    ordered = []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            nm = (row.get("entity_name") or "").strip()
            if nm and nm.lower() not in seen:
                seen.add(nm.lower())
                ordered.append(nm)
    return ordered


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--limit", type=int, default=0, help="process first N names")
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="do everything but do not write output CSVs",
    )
    args = ap.parse_args()

    if not os.path.exists(INPUT_CSV):
        sys.stderr.write(f"ERROR: input not found: {INPUT_CSV}\n")
        return 1

    names = load_distinct_names(INPUT_CSV)
    if args.limit and args.limit > 0:
        names = names[: args.limit]

    oc_token = os.environ.get("OC_API_TOKEN", "").strip()
    if not oc_token:
        print(
            "OpenCorporates: no OC_API_TOKEN set — skipped "
            "(free token at opencorporates.com/api_accounts/new)"
        )

    print(
        f"Enriching {len(names)} distinct EAPA entity names "
        f"(dry-run={args.dry_run})...\n"
    )

    registry_rows: list[dict] = []
    rel_rows: list[dict] = []

    # counters
    n_gleif = 0
    n_gleif_parent = 0
    n_gleif_child = 0
    n_edgar = 0
    n_oc = 0

    for i, name in enumerate(names, 1):
        print(f"[{i}/{len(names)}] {name}")

        # ---- 1. GLEIF -------------------------------------------------- #
        rec = gleif_search(name)
        time.sleep(REQUEST_DELAY)
        matched_lei = None
        if rec:
            fields = gleif_record_fields(rec)
            matched_lei = fields["lei"]
            n_gleif += 1
            registry_rows.append(
                {
                    "entity_name": name,
                    "source": "GLEIF",
                    "matched_name": fields["legal_name"],
                    "identifier": fields["lei"],
                    "country": fields["country"],
                    "address": fields["address"],
                    "incorporation_date": "",
                    "status": fields["status"],
                }
            )
            print(f"    GLEIF: {fields['lei']}  {fields['legal_name']}")

            # ownership relationships
            parents = gleif_related(matched_lei, "direct-parent")
            time.sleep(REQUEST_DELAY)
            for p in parents:
                n_gleif_parent += 1
                rel_rows.append(
                    {
                        "src_name": name,
                        "rel_type": "OWNED_BY",
                        "dst_name": p["name"],
                        "dst_identifier": p["lei"],
                        "source": "GLEIF",
                    }
                )
                print(f"    OWNED_BY: {p['name']} ({p['lei']})")

            children = gleif_related(matched_lei, "direct-children")
            time.sleep(REQUEST_DELAY)
            for c in children:
                n_gleif_child += 1
                rel_rows.append(
                    {
                        "src_name": name,
                        "rel_type": "PARENT_OF",
                        "dst_name": c["name"],
                        "dst_identifier": c["lei"],
                        "source": "GLEIF",
                    }
                )
                print(f"    PARENT_OF: {c['name']} ({c['lei']})")

        # ---- 2. SEC EDGAR ---------------------------------------------- #
        edgar = edgar_match(name)
        time.sleep(REQUEST_DELAY)
        # Reject a fuzzy (multi-match) EDGAR hit whose name doesn't overlap the
        # query; exact single-company matches are trusted as-is.
        if edgar and not edgar.get("exact") and not name_overlap_ok(
            name, edgar.get("name", "")
        ):
            edgar = None
        if edgar:
            n_edgar += 1
            registry_rows.append(
                {
                    "entity_name": name,
                    "source": "EDGAR" if edgar.get("exact") else "EDGAR(fuzzy)",
                    "matched_name": edgar["name"],
                    "identifier": edgar["cik"],
                    "country": "US",
                    "address": edgar.get("address", ""),
                    "incorporation_date": "",
                    "status": f"state_inc={edgar.get('state_inc','')}".rstrip("="),
                }
            )
            print(f"    EDGAR: CIK {edgar['cik']}  {edgar['name']}")

        # ---- 3. OpenCorporates ----------------------------------------- #
        if oc_token:
            company = oc_search(name, oc_token)
            time.sleep(REQUEST_DELAY)
            if company:
                n_oc += 1
                jur = company.get("jurisdiction_code", "")
                num = company.get("company_number", "")
                reg_addr = company.get("registered_address_in_full", "") or ""
                registry_rows.append(
                    {
                        "entity_name": name,
                        "source": "OpenCorporates",
                        "matched_name": company.get("name", ""),
                        "identifier": num,
                        "country": jur,
                        "address": reg_addr,
                        "incorporation_date": company.get(
                            "incorporation_date", ""
                        )
                        or "",
                        "status": company.get("current_status", "") or "",
                    }
                )
                print(
                    f"    OpenCorporates: {jur}/{num}  {company.get('name','')}"
                )
                # officers -> SHARED_OFFICER relationships
                if jur and num:
                    officers = oc_officers(jur, num, oc_token)
                    time.sleep(REQUEST_DELAY)
                    for off in officers:
                        rel_rows.append(
                            {
                                "src_name": name,
                                "rel_type": "SHARED_OFFICER",
                                "dst_name": off,
                                "dst_identifier": "",
                                "source": "OpenCorporates",
                            }
                        )
                    if officers:
                        print(f"    officers: {', '.join(officers[:5])}")

    # ------------------------------------------------------------------- #
    # Write outputs
    # ------------------------------------------------------------------- #
    if not args.dry_run:
        os.makedirs(REF_DIR, exist_ok=True)
        with open(OUT_REGISTRY, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(
                f,
                fieldnames=[
                    "entity_name",
                    "source",
                    "matched_name",
                    "identifier",
                    "country",
                    "address",
                    "incorporation_date",
                    "status",
                ],
            )
            w.writeheader()
            w.writerows(registry_rows)
        with open(OUT_RELATIONSHIPS, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(
                f,
                fieldnames=[
                    "src_name",
                    "rel_type",
                    "dst_name",
                    "dst_identifier",
                    "source",
                ],
            )
            w.writeheader()
            w.writerows(rel_rows)
        print(f"\nWrote {OUT_REGISTRY}  ({len(registry_rows)} rows)")
        print(f"Wrote {OUT_RELATIONSHIPS}  ({len(rel_rows)} rows)")
    else:
        print(
            f"\n[dry-run] would write {len(registry_rows)} registry rows, "
            f"{len(rel_rows)} relationship rows"
        )

    # ------------------------------------------------------------------- #
    # Summary
    # ------------------------------------------------------------------- #
    print("\n===== SUMMARY =====")
    print(f"distinct names processed : {len(names)}")
    print(f"GLEIF matched            : {n_gleif}")
    print(f"  with parent (OWNED_BY) : {n_gleif_parent}")
    print(f"  with child  (PARENT_OF): {n_gleif_child}")
    print(f"EDGAR matched            : {n_edgar}")
    if oc_token:
        print(f"OpenCorporates matched   : {n_oc}")
    else:
        print("OpenCorporates           : skipped (no OC_API_TOKEN)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
