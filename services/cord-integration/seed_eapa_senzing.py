"""Seed EAPA respondents into senzing_entities WITH curated attribute overlaps.

GAP 1 fix. EAPA (Enforce and Protect Act) respondents previously existed only
as a ``cord_engine`` overlay inside sentry-api -- they were never written into
``senzing_entities``, so ``derive_relationships.py`` never saw them and they
picked up zero relationships. This script writes them into ``senzing_entities``
(the base Senzing store) so the deriver links them to real flagged CORD
entities (the "H2 discovery" story: a transshipment respondent turns out to
share a registered address / strong identifier / owner with an already-flagged
sanctioned or offshore entity).

It writes ONLY ``senzing_entities`` and is fully idempotent (INSERT OR REPLACE
keyed on entity_id). It NEVER touches ``senzing_relationships`` -- the operator
runs ``derive_relationships.py`` separately at integration time, and the curated
overlaps seeded here are exactly what that deriver reads to emit REAL edges.

HOW THE OVERLAPS BECOME EDGES (mechanism is real, the *link* is seeded):
  * derive_relationships._extract_addresses() reads ADDRESSES[].ADDR_FULL and
    normalizes it (uppercase, strip punctuation, collapse spaces). Two entities
    carrying the same normalized ADDR_FULL -> a SHARED_ADDRESS edge.
  * derive_relationships._extract_identifiers() reads IDENTIFIERS[] strong keys
    (NATIONAL_ID_NUMBER / TAX_ID_NUMBER / LEI_NUMBER / PASSPORT_NUMBER ...) AND
    the top-level OFAC_ID. Same normalized value on two entities ->
    SHARED_IDENTIFIER edge.
  * derive_relationships._extract_relationships() reads RELATIONSHIPS[] with a
    REL_POINTER_KEY; the deriver resolves that key against the target entity's
    record_id (for OFAC, record_id == the OFAC id number, e.g. "767") and emits
    an OWNED_BY edge from respondent -> the real OFAC entity.

So this script pulls the *real* normalized attribute off ~6-8 already-flagged
entities (OFAC / OPEN-SANCTIONS / ICIJ) at runtime and copies the matching raw
value into selected EAPA respondents, plus seeds intra-EAPA address clusters
(supply-chain networks) and 2 OFAC ownership pointers.

Reads: senzing_entities (flagged sources) + the EAPA watchlist from the gateway.
Writes: senzing_entities only.
"""
from __future__ import annotations

import json
import logging
import os
import re
import sqlite3
import sys
import urllib.request
from typing import Dict, List, Optional, Tuple

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("seed_eapa_senzing")

DB_PATH = os.getenv("SENZING_DB_PATH", "/app/data/senzing.db")
# Gateway(s) that serve the EAPA watchlist the UI + cord_engine overlay use.
# The prompt's canonical endpoint is http://localhost:3001 (works from the host
# / behind the UI proxy). When this runs at container startup the same route is
# reachable on the docker network at http://sentry-api:8000, so we try that too.
WATCHLIST_PATH = "/api/cord/watchlist?mode=eapa&limit=80"
_env_gateway = os.getenv("CORD_GATEWAY_URL")
GATEWAY_BASES = ([_env_gateway] if _env_gateway else []) + [
    "http://localhost:3001",
    "http://sentry-api:8000",
]

FLAGGED_SOURCES = ("OFAC", "OPEN-SANCTIONS", "ICIJ")


# --------------------------------------------------------------------------- #
# normalization mirrors derive_relationships.py exactly (so tokens match)
# --------------------------------------------------------------------------- #
def _norm_id(value: object) -> str:
    if value is None:
        return ""
    s = re.sub(r"[^A-Za-z0-9]", "", str(value)).upper()
    return s if len(s) >= 4 else ""


def _norm_addr(value: object) -> str:
    if not value:
        return ""
    s = re.sub(r"[^A-Z0-9 ]", " ", str(value).upper())
    s = re.sub(r"\s+", " ", s).strip()
    return s if len(s) >= 10 else ""


# --------------------------------------------------------------------------- #
# EAPA watchlist (from the gateway -- EXACT entity_ids + names the UI uses)
# --------------------------------------------------------------------------- #
def fetch_eapa_watchlist() -> List[Dict[str, str]]:
    """GET the EAPA watchlist; fall back to the cord_engine SQLite overlay if the
    gateway is unreachable (so the seed still runs deterministically at build /
    container startup)."""
    for base in GATEWAY_BASES:
        url = base.rstrip("/") + WATCHLIST_PATH
        try:
            with urllib.request.urlopen(url, timeout=15) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            ents = payload.get("entities", []) or []
            out = [
                {
                    "entity_id": e["entity_id"],
                    "name": e.get("name", ""),
                    "country": e.get("country", ""),
                    "program": e.get("program", ""),
                    "route": e.get("route", ""),
                }
                for e in ents
                if e.get("entity_id")
            ]
            if out:
                logger.info("fetched %d EAPA respondents from gateway %s",
                            len(out), base)
                return out
        except Exception as exc:  # noqa: BLE001
            logger.warning("gateway %s unavailable (%s)", base, exc)

    # Fallback: cord_engine overlay (same entity_ids the gateway serves).
    for cand in ("/app/data/cbp_sentry.db", "/app/data/cord_engine.db"):
        if not os.path.exists(cand):
            continue
        try:
            conn = sqlite3.connect(cand)
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT entity_id, name, country FROM cord_entities "
                "WHERE flag='eapa_respondent' OR data_source='CBP-EAPA'"
            ).fetchall()
            conn.close()
            out = [
                {"entity_id": r["entity_id"], "name": r["name"] or "",
                 "country": r["country"] or "", "program": "", "route": ""}
                for r in rows if r["entity_id"]
            ]
            if out:
                logger.info("fetched %d EAPA respondents from overlay %s",
                            len(out), cand)
                return out
        except Exception:  # noqa: BLE001
            continue
    logger.error("could not source EAPA watchlist from gateway or overlay")
    return []


# --------------------------------------------------------------------------- #
# real flagged entities to overlap against (read from senzing_entities)
# --------------------------------------------------------------------------- #
def _primary_name(raw: Dict, fallback: str = "") -> str:
    for key in ("NAMES", "NAME_LIST"):
        arr = raw.get(key)
        if isinstance(arr, list) and arr and isinstance(arr[0], dict):
            return arr[0].get("NAME_ORG") or arr[0].get("NAME_FULL") or fallback
    return fallback


def pick_flagged_anchors(conn: sqlite3.Connection) -> Dict[str, List[Dict]]:
    """Pull a small, stable set of real flagged entities and extract the EXACT
    raw attribute value the deriver will normalize, so an EAPA respondent that
    carries the same raw value collides with it in the deriver's index.

    Returns dict with keys: 'address' (OPEN-SANCTIONS/ICIJ ADDR_FULL),
    'identifier' (OPEN-SANCTIONS strong id), 'ofac' (OFAC org owners).
    """
    cur = conn.cursor()

    # --- OPEN-SANCTIONS: take entities that have BOTH a normalizable ADDR_FULL
    #     and a strong identifier; we reuse the address for SHARED_ADDRESS and
    #     the id for SHARED_IDENTIFIER. Deterministic order by entity_id.
    addr_anchors: List[Dict] = []
    id_anchors: List[Dict] = []
    rows = cur.execute(
        "SELECT entity_id, name_primary, raw_data FROM senzing_entities "
        "WHERE data_source='OPEN-SANCTIONS' ORDER BY entity_id LIMIT 4000"
    ).fetchall()
    for eid, name_primary, raw_json in rows:
        try:
            raw = json.loads(raw_json) if raw_json else {}
        except (json.JSONDecodeError, TypeError):
            continue
        # raw ADDR_FULL whose normalization is non-trivial
        addr_full = None
        for a in raw.get("ADDRESSES", []) or []:
            if isinstance(a, dict) and _norm_addr(a.get("ADDR_FULL")):
                addr_full = a.get("ADDR_FULL")
                break
        strong = None  # (id_key, raw_value)
        for idobj in raw.get("IDENTIFIERS", []) or []:
            if not isinstance(idobj, dict):
                continue
            for k in ("NATIONAL_ID_NUMBER", "TAX_ID_NUMBER", "LEI_NUMBER",
                      "PASSPORT_NUMBER"):
                if idobj.get(k) and _norm_id(idobj[k]):
                    strong = (k, idobj[k])
                    break
            if strong:
                break
        name = name_primary or _primary_name(raw, eid)
        if addr_full and len(addr_anchors) < 5:
            addr_anchors.append({"entity_id": eid, "name": name,
                                 "addr_full": addr_full,
                                 "norm": _norm_addr(addr_full)})
        if strong and len(id_anchors) < 4:
            id_anchors.append({"entity_id": eid, "name": name,
                               "id_key": strong[0], "id_value": strong[1],
                               "norm": _norm_id(strong[1])})
        if len(addr_anchors) >= 5 and len(id_anchors) >= 4:
            break

    # --- ICIJ offshore: ADDR_FULL (registered-agent style addresses).
    icij_anchors: List[Dict] = []
    rows = cur.execute(
        "SELECT entity_id, name_primary, raw_data FROM senzing_entities "
        "WHERE data_source='ICIJ' ORDER BY entity_id LIMIT 4000"
    ).fetchall()
    for eid, name_primary, raw_json in rows:
        try:
            raw = json.loads(raw_json) if raw_json else {}
        except (json.JSONDecodeError, TypeError):
            continue
        addr_full = None
        for a in raw.get("ADDRESSES", []) or []:
            if isinstance(a, dict) and _norm_addr(a.get("ADDR_FULL")):
                addr_full = a.get("ADDR_FULL")
                break
        if addr_full:
            name = name_primary or _primary_name(raw, eid)
            icij_anchors.append({"entity_id": eid, "name": name,
                                 "addr_full": addr_full,
                                 "norm": _norm_addr(addr_full)})
        if len(icij_anchors) >= 3:
            break

    # --- OFAC org entities to point OWNED_BY at. For OFAC, the deriver resolves
    #     a respondent's REL_POINTER_KEY against the target's record_id, which
    #     for OFAC equals the OFAC id number (entity_id 'OFAC:<n>', record_id
    #     '<n>'). So the pointer key is just that number.
    ofac_anchors: List[Dict] = []
    rows = cur.execute(
        "SELECT entity_id, record_id, name_primary, raw_data FROM senzing_entities "
        "WHERE data_source='OFAC' ORDER BY entity_id LIMIT 1877"
    ).fetchall()
    for eid, record_id, name_primary, raw_json in rows:
        try:
            raw = json.loads(raw_json) if raw_json else {}
        except (json.JSONDecodeError, TypeError):
            raw = {}
        name = name_primary or _primary_name(raw, eid)
        rid = record_id or (eid.split(":", 1)[1] if ":" in eid else eid)
        if name and any(t in name.upper() for t in
                        ("LTD", "CO.", "COMPANY", "TRADING", "COMMODITIES",
                         "CORP", "BANK", "GROUP", "INTERNATIONAL")):
            ofac_anchors.append({"entity_id": eid, "record_id": str(rid),
                                 "name": name})
        if len(ofac_anchors) >= 2:
            break

    return {
        "address": addr_anchors,
        "identifier": id_anchors,
        "icij": icij_anchors,
        "ofac": ofac_anchors,
    }


# --------------------------------------------------------------------------- #
# build EAPA raw_data records + apply curated overlaps
# --------------------------------------------------------------------------- #
def _eapa_base_raw(ent: Dict) -> Dict:
    """A clean CORD-shaped record for an EAPA respondent."""
    eid = ent["entity_id"]
    case = eid.split(":", 1)[1] if ":" in eid else eid
    name = ent["name"]
    country = ent.get("country") or ""
    raw: Dict = {
        "DATA_SOURCE": "CBP-EAPA",
        "RECORD_ID": case,
        "RECORD_TYPE": "ORGANIZATION",
        "NAMES": [{"NAME_TYPE": "PRIMARY", "NAME_ORG": name}],
        "ADDRESSES": [],
        "IDENTIFIERS": [],
        "RELATIONSHIPS": [],
        "EAPA_PROGRAM": ent.get("program", ""),
        "ROUTE": ent.get("route", ""),
        "FLAG": "eapa_respondent",
        "COUNTRY": country,
    }
    # A generic native address so non-curated respondents still look real.
    if country:
        raw["ADDRESSES"].append({
            "ADDR_TYPE": "BUSINESS",
            "ADDR_FULL": f"{name} Industrial Park, {country}",
            "ADDR_COUNTRY": country,
        })
    return raw


def build_records(eapa: List[Dict], anchors: Dict[str, List[Dict]]
                  ) -> Tuple[List[Dict], List[Dict]]:
    """Return (records, overlap_report). records carry the curated overlaps."""
    records = {e["entity_id"]: {"ent": e, "raw": _eapa_base_raw(e)}
               for e in eapa}
    order = [e["entity_id"] for e in eapa]
    overlaps: List[Dict] = []

    def by_index(i: int) -> Optional[str]:
        return order[i] if 0 <= i < len(order) else None

    # ----- 1) SHARED_ADDRESS with OPEN-SANCTIONS flagged entities ----------- #
    # curated demo overlap -- mechanism real, link seeded: copy the EXACT
    # ADDR_FULL off a sanctioned entity into a respondent so the deriver's
    # address index buckets them together -> SHARED_ADDRESS edge.
    addr_anchors = anchors.get("address", [])
    addr_targets = [0, 3, 6]  # respondents to attach sanctioned addresses to
    for slot, anc in enumerate(addr_anchors[: len(addr_targets)]):
        eid = by_index(addr_targets[slot])
        if not eid:
            continue
        rec = records[eid]
        rec["raw"]["ADDRESSES"].append({
            "ADDR_TYPE": "REGISTERED",
            # curated demo overlap -- mechanism real, link seeded
            "ADDR_FULL": anc["addr_full"],
            "_OVERLAP_NOTE": "curated demo overlap: shared with flagged "
                             f"{anc['entity_id']}",
        })
        overlaps.append({
            "eapa": eid, "eapa_name": rec["ent"]["name"],
            "real_entity": anc["entity_id"], "real_source": "OPEN-SANCTIONS",
            "via": "SHARED_ADDRESS",
            "shared_value": anc["addr_full"],
            "shared_norm": anc["norm"],
        })

    # ----- 2) SHARED_ADDRESS with ICIJ offshore entities -------------------- #
    icij_anchors = anchors.get("icij", [])
    icij_targets = [1, 4]
    for slot, anc in enumerate(icij_anchors[: len(icij_targets)]):
        eid = by_index(icij_targets[slot])
        if not eid:
            continue
        rec = records[eid]
        rec["raw"]["ADDRESSES"].append({
            "ADDR_TYPE": "REGISTERED",
            # curated demo overlap -- mechanism real, link seeded
            "ADDR_FULL": anc["addr_full"],
            "_OVERLAP_NOTE": "curated demo overlap: shared registered address "
                             f"with ICIJ offshore {anc['entity_id']}",
        })
        overlaps.append({
            "eapa": eid, "eapa_name": rec["ent"]["name"],
            "real_entity": anc["entity_id"], "real_source": "ICIJ",
            "via": "SHARED_ADDRESS",
            "shared_value": anc["addr_full"],
            "shared_norm": anc["norm"],
        })

    # ----- 3) SHARED_IDENTIFIER with OPEN-SANCTIONS strong ids -------------- #
    id_anchors = anchors.get("identifier", [])
    id_targets = [2, 5, 7]
    for slot, anc in enumerate(id_anchors[: len(id_targets)]):
        eid = by_index(id_targets[slot])
        if not eid:
            continue
        rec = records[eid]
        rec["raw"]["IDENTIFIERS"].append({
            # curated demo overlap -- mechanism real, link seeded
            anc["id_key"]: anc["id_value"],
            "_OVERLAP_NOTE": "curated demo overlap: shared "
                             f"{anc['id_key']} with flagged {anc['entity_id']}",
        })
        overlaps.append({
            "eapa": eid, "eapa_name": rec["ent"]["name"],
            "real_entity": anc["entity_id"], "real_source": "OPEN-SANCTIONS",
            "via": f"SHARED_IDENTIFIER ({anc['id_key']})",
            "shared_value": anc["id_value"],
            "shared_norm": anc["norm"],
        })

    # ----- 4) OWNED_BY pointer to OFAC org entities ------------------------- #
    # curated demo overlap -- mechanism real, link seeded: a RELATIONSHIPS
    # pointer whose REL_POINTER_KEY == the OFAC record id; the deriver resolves
    # it to OFAC:<id> and emits OWNED_BY (respondent -> sanctioned owner).
    ofac_anchors = anchors.get("ofac", [])
    ofac_targets = [8, 9]
    for slot, anc in enumerate(ofac_anchors[: len(ofac_targets)]):
        eid = by_index(ofac_targets[slot])
        if not eid:
            continue
        rec = records[eid]
        rec["raw"]["RELATIONSHIPS"].append({
            "REL_POINTER_KEY": anc["record_id"],
            "REL_POINTER_ROLE": "owned / controlled by",
            "_OVERLAP_NOTE": "curated demo overlap: ownership pointer to OFAC "
                             f"{anc['entity_id']}",
        })
        overlaps.append({
            "eapa": eid, "eapa_name": rec["ent"]["name"],
            "real_entity": anc["entity_id"], "real_source": "OFAC",
            "via": "OWNED_BY",
            "shared_value": f"REL_POINTER_KEY={anc['record_id']} -> "
                            f"{anc['entity_id']} ({anc['name']})",
            "shared_norm": _norm_id(anc["record_id"]),
        })

    # ----- 5) Intra-EAPA address clusters (supply-chain networks) ----------- #
    # curated demo overlap -- mechanism real, link seeded: give clusters of
    # respondents a shared consolidation-warehouse address so the deriver wires
    # them into a SHARED_ADDRESS network among themselves.
    clusters = [
        ("Unit 7, Cai Mep Logistics Hub, Ba Ria-Vung Tau, Vietnam",
         [10, 11, 15]),
        ("Block C, Laem Chabang Free Trade Zone, Chonburi, Thailand",
         [12, 16, 20]),
        ("Lot 12, Port Klang Free Zone, Selangor, Malaysia",
         [13, 17, 21]),
    ]
    for addr_full, idxs in clusters:
        members = []
        for i in idxs:
            eid = by_index(i)
            if not eid:
                continue
            records[eid]["raw"]["ADDRESSES"].append({
                "ADDR_TYPE": "CONSOLIDATION",
                # curated demo overlap -- mechanism real, link seeded
                "ADDR_FULL": addr_full,
                "_OVERLAP_NOTE": "curated demo overlap: shared supply-chain "
                                 "consolidation address (intra-EAPA cluster)",
            })
            members.append(eid)
        if len(members) >= 2:
            overlaps.append({
                "eapa": members[0], "eapa_name": records[members[0]]["ent"]["name"],
                "real_entity": ", ".join(members[1:]),
                "real_source": "CBP-EAPA (intra-cluster)",
                "via": "SHARED_ADDRESS (supply-chain network)",
                "shared_value": addr_full,
                "shared_norm": _norm_addr(addr_full),
            })

    return [records[o] for o in order], overlaps


# --------------------------------------------------------------------------- #
# write to senzing_entities (ONLY)
# --------------------------------------------------------------------------- #
def write_entities(conn: sqlite3.Connection, records: List[Dict]) -> int:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS senzing_entities ("
        "entity_id TEXT PRIMARY KEY, data_source TEXT, record_id TEXT, "
        "name_primary TEXT, country TEXT, entity_type TEXT, "
        "confidence REAL DEFAULT 1.0, raw_data TEXT, "
        "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
    cur = conn.cursor()
    n = 0
    for rec in records:
        ent = rec["ent"]
        raw = rec["raw"]
        eid = ent["entity_id"]
        case = eid.split(":", 1)[1] if ":" in eid else eid
        cur.execute(
            "INSERT OR REPLACE INTO senzing_entities "
            "(entity_id, data_source, record_id, name_primary, country, "
            "entity_type, confidence, raw_data) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (eid, "CBP-EAPA", case, ent["name"], ent.get("country") or "",
             "organization", 1.0, json.dumps(raw)))
        n += 1
    conn.commit()
    return n


def main() -> int:
    eapa = fetch_eapa_watchlist()
    if not eapa:
        logger.error("no EAPA respondents to seed -- aborting")
        return 1

    conn = sqlite3.connect(DB_PATH)
    try:
        anchors = pick_flagged_anchors(conn)
        records, overlaps = build_records(eapa, anchors)
        inserted = write_entities(conn, records)
    finally:
        conn.close()

    print("=" * 72)
    print(f"EAPA respondents inserted into senzing_entities: {inserted}")
    print("=" * 72)
    print("\nCURATED OVERLAPS (EAPA respondent -> real flagged entity, via):")
    print("-" * 72)
    for ov in overlaps:
        print(f"  [{ov['via']}]")
        print(f"    EAPA  : {ov['eapa']}  ({ov['eapa_name']})")
        print(f"    REAL  : {ov['real_entity']}  [{ov['real_source']}]")
        sv = ov["shared_value"]
        print(f"    SHARED: {sv if len(str(sv)) <= 80 else str(sv)[:77] + '...'}")
        print(f"    NORM  : {ov['shared_norm']}")
        print()
    print(f"Total curated overlaps seeded: {len(overlaps)}")
    print("Run derive_relationships.py to materialize these into "
          "senzing_relationships.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
