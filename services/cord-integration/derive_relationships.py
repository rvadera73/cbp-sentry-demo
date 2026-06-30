"""Derive REAL Senzing relationships FROM the CORD entity data.

Senzing stays the base store; this script POPULATES ``senzing_relationships``
from the CORD records already loaded into ``senzing_entities`` (raw_data carries
the frozen CORD shapes: IDENTIFIERS / ADDRESSES / RELATIONSHIPS).

Edge derivation mirrors services/api/entity_edges.py:
  * SHARED_IDENTIFIER  — two entities carry the same *normalized* strong
    identifier (LEI, tax id, national id, passport, OFAC id, ...).
  * SHARED_ADDRESS     — two entities carry the same *normalized* address.
    High-degree address hubs (many entities at one address = likely
    registered agent) are confidence-down-weighted and, above a hard cap,
    dropped entirely — the main precision fix.
  * SHARED_NAME        — fuzzy normalized name match (corporate suffixes
    CO/LTD/LLC/INC/CORP/JSC/GMBH/SA/BV/PLC... stripped, compared by
    token-set), blocked by a core-token key and emitted only on a strong
    overlap at moderate (~0.6) confidence.
  * OWNED_BY / OFFICER — drawn from RELATIONSHIPS[] directional REL_POINTER_KEY
    pointers (GLEIF / OPEN-OWNERSHIP / OPEN-SANCTIONS). Role text decides
    ownership (-> OWNED_BY, the type the resolver chain reads) vs officer.

The output schema matches exactly what resolver.py / main.py read:
    senzing_relationships(entity_id_a, entity_id_b, relationship_type,
                          confidence, evidence)
``OWNED_BY`` is used for ownership so resolver._get_parent_relationships()
(which filters relationship_type IN ('OWNED_BY','PARENT_COMPANY')) lights up.

SCOPE: to stay tractable over 243K entities we seed from the flagged /
operational sources (OFAC, OPEN-SANCTIONS, US-LABOR-VIOLATIONS == UFLPA/forced
-labor proxy, CBP-* operational entities, NOMINO-RISK) and pull in their
shared-attribute neighbours and ownership-pointer targets. We do NOT scan all
243K for pairwise joins.

IDEMPOTENT: a marker row (relationship_type='__DERIVED_MARKER__') records the
derived-edge count. Re-running is a no-op unless --force is passed.

Reads senzing_entities; writes senzing_relationships only. Does not touch
cord_engine / main / resolver logic.
"""
from __future__ import annotations

import argparse
import json
import logging
import re
import sqlite3
import sys
from collections import defaultdict
from typing import Dict, Iterable, List, Optional, Tuple

logger = logging.getLogger("derive_relationships")

DB_PATH = "/app/data/senzing.db"
MARKER_TYPE = "__DERIVED_MARKER__"

# Flagged / operational seed sources (the entities we care about resolving).
SEED_SOURCES = (
    "OFAC",
    "OPEN-SANCTIONS",
    "US-LABOR-VIOLATIONS",
    "NOMINO-RISK",
    "CBP-EAPA",          # EAPA respondents (so their curated overlaps materialize)
    "CBP-SHIPPER",
    "CBP-CONSIGNEE",
    "CBP-DEMO",
)

# Strong identifier keys (same set as entity_edges.py).
_DIRECT_ID_KEYS = (
    "LEI_NUMBER",
    "NATIONAL_ID_NUMBER",
    "TAX_ID_NUMBER",
    "PASSPORT_NUMBER",
    "OFAC_ID",
    "TRUSTED_ID_NUMBER",
)
_XREF_ID_TYPES = {
    "OPEN_SANCTIONS", "OPEN-SANCTIONS", "OPEN_OWNERSHIP", "OPEN-OWNERSHIP",
    "GLEIF", "ICIJ", "ICIJ_ID",
}

_OWNERSHIP_ROLE_RE = re.compile(
    r"own|control|consolidat|shareholder|shares|beneficial|parent|holding|"
    r"fund-managed|appoint|remove director", re.IGNORECASE)
_OFFICER_ROLE_RE = re.compile(
    r"director|officer|manager|secretary|signator|board|partner|executive|"
    r"acting for", re.IGNORECASE)

# --- fuzzy name match (SHARED_NAME) tuning ------------------------------------
# Corporate suffix / legal-form tokens stripped before comparing names. These
# carry no discriminating signal (every "... LTD" would otherwise look related).
_CORP_SUFFIXES = {
    "CO", "COMPANY", "LTD", "LIMITED", "LLC", "LLP", "INC", "INCORPORATED",
    "CORP", "CORPORATION", "JSC", "OJSC", "PJSC", "GMBH", "AG", "SA", "SAS",
    "SARL", "SRL", "SPA", "BV", "NV", "PLC", "PTE", "PVT", "PT", "OOO", "AO",
    "ZAO", "KG", "OY", "AB", "AS", "GROUP", "HOLDING", "HOLDINGS", "TRADING",
    "INTERNATIONAL", "INTL", "INDUSTRIES", "INDUSTRIAL", "ENTERPRISE",
    "ENTERPRISES", "IMPORT", "EXPORT", "TRADE", "THE", "AND",
}
# Generic single tokens that should never alone constitute a "rare" name core.
_NAME_STOPWORDS = _CORP_SUFFIXES
# token-set overlap (Jaccard on cores) above this => strong fuzzy name match
_NAME_OVERLAP_THRESHOLD = 0.80
_SHARED_NAME_CONF = 0.6

# --- shared-address hub down-weighting ----------------------------------------
# An address shared by many entities is almost always a registered-agent /
# incorporation-mill hub, not a genuine co-location signal. Scale confidence
# down as the cluster grows, and drop clusters above the hard cap entirely.
_ADDR_HUB_SOFT = 5      # clusters >= this size start losing confidence
_ADDR_HUB_HARD = 25     # clusters >= this size are dropped (pure agent hubs)


# --------------------------------------------------------------------------- #
# normalization helpers (mirror entity_edges.py)
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


def _name_from_raw(raw: Dict) -> str:
    """Best-effort primary name from a raw CORD record (name_primary is blank
    for several sources). Mirrors resolver.EntityResolver._name_from_raw."""
    if not isinstance(raw, dict):
        return ""
    for key in ("NAMES", "NAME_LIST"):
        arr = raw.get(key)
        if isinstance(arr, list) and arr:
            prim = next((n for n in arr
                         if isinstance(n, dict) and n.get("NAME_TYPE") == "PRIMARY"),
                        arr[0])
            if isinstance(prim, dict):
                org = prim.get("NAME_ORG") or prim.get("NAME_FULL")
                if org:
                    return str(org)
                full = " ".join(str(prim.get(k, "")) for k in
                                ("PRIMARY_NAME_FIRST", "PRIMARY_NAME_MIDDLE",
                                 "PRIMARY_NAME_LAST")).strip()
                if full:
                    return full
    for key in ("PRIMARY_NAME_ORG", "LEGAL_NAME_ORG", "NAME", "name", "Title"):
        if raw.get(key):
            return str(raw[key])
    return ""


def _name_tokens(value: object) -> Tuple[str, ...]:
    """Normalize a name to a tuple of core tokens for token-set comparison.

    Lowercase -> uppercase, strip punctuation, drop corporate suffix / legal-
    form / generic trade words. The remaining tokens are the discriminating
    "core" of the name (e.g. "Greenfield Industrial Trading Co., Ltd." ->
    ("GREENFIELD",)).
    """
    if not value:
        return ()
    s = re.sub(r"[^A-Z0-9 ]", " ", str(value).upper())
    s = re.sub(r"\s+", " ", s).strip()
    toks = [t for t in s.split(" ") if t and t not in _CORP_SUFFIXES and len(t) > 1]
    return tuple(toks)


def _name_core_key(value: object) -> str:
    """Blocking key for fuzzy name match: sorted core tokens joined.

    Two names only get compared if they share this key, which keeps the pass
    bounded (blocked) instead of all-pairs. Returns "" for names with no
    discriminating core (all-suffix / too short) so they are never blocked on.
    """
    toks = _name_tokens(value)
    if not toks:
        return ""
    return " ".join(sorted(set(toks)))


def _name_overlap(a: Tuple[str, ...], b: Tuple[str, ...]) -> float:
    """Token-set Jaccard overlap of two normalized name cores."""
    sa, sb = set(a), set(b)
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def _extract_identifiers(raw: Dict) -> List[Tuple[str, str]]:
    out: List[Tuple[str, str]] = []
    seen = set()

    def add(label: str, value: object):
        nv = _norm_id(value)
        if nv and nv not in seen:
            seen.add(nv)
            out.append((label, nv))

    for idobj in raw.get("IDENTIFIERS", []) or []:
        if not isinstance(idobj, dict):
            continue
        for key in _DIRECT_ID_KEYS:
            if idobj.get(key):
                add(key.replace("_NUMBER", ""), idobj[key])
        otype = (idobj.get("OTHER_ID_TYPE") or "").strip()
        onum = idobj.get("OTHER_ID_NUMBER")
        if onum and otype and otype not in _XREF_ID_TYPES:
            add(otype, onum)
    if raw.get("OFAC_ID"):
        add("OFAC_ID", raw["OFAC_ID"])
    return out


def _extract_addresses(raw: Dict) -> List[str]:
    out: List[str] = []
    seen = set()

    def add(value: str):
        nv = _norm_addr(value)
        if nv and nv not in seen:
            seen.add(nv)
            out.append(nv)

    for addr in raw.get("ADDRESSES", []) or []:
        if isinstance(addr, dict):
            add(addr.get("ADDR_FULL") or addr.get("ADDR_LINE1"))
    for addr in raw.get("ADDR_LIST", []) or []:
        if isinstance(addr, dict):
            parts = [addr.get("ADDR_LINE1"), addr.get("ADDR_CITY"),
                     addr.get("ADDR_COUNTRY")]
            add(", ".join(p for p in parts if p))
    return out


def _classify_relationship(role: str) -> str:
    if not role:
        return "OWNED_BY"
    if _OWNERSHIP_ROLE_RE.search(role):
        return "OWNED_BY"
    if _OFFICER_ROLE_RE.search(role):
        return "OFFICER"
    return "OWNED_BY"


def _extract_pointer_anchors(raw: Dict) -> List[str]:
    """Tokens by which this entity can be referenced by another's pointer."""
    anchors: List[str] = []
    for rel in raw.get("RELATIONSHIPS", []) or []:
        if isinstance(rel, dict) and rel.get("REL_ANCHOR_KEY"):
            anchors.append(str(rel["REL_ANCHOR_KEY"]))
    for idobj in raw.get("IDENTIFIERS", []) or []:
        if isinstance(idobj, dict) and idobj.get("OTHER_ID_NUMBER"):
            anchors.append(str(idobj["OTHER_ID_NUMBER"]))
    return anchors


def _extract_relationships(raw: Dict) -> List[Tuple[str, str, str]]:
    out: List[Tuple[str, str, str]] = []
    for rel in raw.get("RELATIONSHIPS", []) or []:
        if not isinstance(rel, dict):
            continue
        ptr = rel.get("REL_POINTER_KEY")
        if not ptr:
            continue
        role = (rel.get("REL_POINTER_ROLE") or "").strip()
        out.append((_classify_relationship(role), role, str(ptr)))
    return out


def _group_confidence(group_size: int, base: float) -> float:
    penalty = min(0.4, 0.05 * (group_size - 2))
    return round(max(0.2, base - penalty), 3)


def _pairs(items: List[str]) -> Iterable[Tuple[str, str]]:
    n = len(items)
    for i in range(n):
        for j in range(i + 1, n):
            yield items[i], items[j]


# --------------------------------------------------------------------------- #
# main deriver
# --------------------------------------------------------------------------- #
class RelationshipDeriver:
    def __init__(self, db_path: str = DB_PATH, neighbor_cap: int = 80000):
        self.db_path = db_path
        # cap on how many candidate (seed + neighbour) records we scan
        self.neighbor_cap = neighbor_cap
        # entity_id -> best-effort primary name (populated by _load_records,
        # consumed by the SHARED_NAME pass in derive()).
        self._names: Dict[str, str] = {}

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def already_derived(self, conn: sqlite3.Connection) -> int:
        cur = conn.cursor()
        cur.execute(
            "SELECT confidence FROM senzing_relationships "
            "WHERE relationship_type = ? LIMIT 1", (MARKER_TYPE,))
        row = cur.fetchone()
        return int(row[0]) if row else 0

    def _load_records(self, conn: sqlite3.Connection
                      ) -> List[Tuple[str, str, Dict]]:
        """Load seed records + any record sharing a strong attribute with them.

        Two-pass: (1) gather seed entities and the set of normalized
        identifier/address tokens they carry; (2) pull every entity that
        carries one of those tokens (the shared-attribute neighbours), plus the
        ownership-pointer targets. Keeps the working set to the flagged
        operational neighbourhood instead of the full 243K.
        """
        cur = conn.cursor()
        placeholders = ",".join("?" * len(SEED_SOURCES))

        # Pass 1 — seeds.
        cur.execute(
            f"SELECT entity_id, data_source, name_primary, raw_data "
            f"FROM senzing_entities "
            f"WHERE data_source IN ({placeholders})", SEED_SOURCES)
        seed_rows = cur.fetchall()

        seed_tokens: set = set()          # id/addr tokens carried by seeds
        pointer_keys: set = set()         # ownership pointer targets to resolve
        records: Dict[str, Tuple[str, str, Dict]] = {}

        def _record_name(row, raw: Dict) -> str:
            try:
                np = row["name_primary"]
            except (IndexError, KeyError):
                np = None
            if np and str(np).strip():
                return str(np).strip()
            return _name_from_raw(raw)

        for row in seed_rows:
            eid = row["entity_id"]
            try:
                raw = json.loads(row["raw_data"]) if row["raw_data"] else {}
            except (json.JSONDecodeError, TypeError):
                raw = {}
            records[eid] = (eid, row["data_source"], raw)
            self._names[eid] = _record_name(row, raw)
            for _, val in _extract_identifiers(raw):
                seed_tokens.add(val)
            for addr in _extract_addresses(raw):
                seed_tokens.add(addr)
            for _, _, ptr in _extract_relationships(raw):
                pointer_keys.add(ptr)
                pointer_keys.add(_norm_id(ptr))

        logger.info("seeds=%d seed_tokens=%d pointer_keys=%d",
                    len(seed_rows), len(seed_tokens), len(pointer_keys))

        # Pass 2 — scan the rest, keeping only records that share a seed token
        # or are a pointer target. Bounded scan over a window of all entities.
        cur.execute(
            "SELECT entity_id, data_source, record_id, name_primary, raw_data "
            "FROM senzing_entities LIMIT ?", (self.neighbor_cap,))
        for row in cur.fetchall():
            eid = row["entity_id"]
            if eid in records:
                continue
            try:
                raw = json.loads(row["raw_data"]) if row["raw_data"] else {}
            except (json.JSONDecodeError, TypeError):
                continue

            keep = False
            for _, val in _extract_identifiers(raw):
                if val in seed_tokens:
                    keep = True
                    break
            if not keep:
                for addr in _extract_addresses(raw):
                    if addr in seed_tokens:
                        keep = True
                        break
            if not keep and pointer_keys:
                # pointer target match (record_id or any anchor token)
                rid = row["record_id"] or ""
                if rid in pointer_keys or _norm_id(rid) in pointer_keys:
                    keep = True
                else:
                    for anchor in _extract_pointer_anchors(raw):
                        if anchor in pointer_keys or _norm_id(anchor) in pointer_keys:
                            keep = True
                            break
            if keep:
                records[eid] = (eid, row["data_source"], raw)
                self._names[eid] = _record_name(row, raw)

        logger.info("working set = %d records (seeds + neighbours)", len(records))
        return list(records.values())

    def derive(self) -> List[Tuple[str, str, str, float, str]]:
        """Return derived edges: (a, b, type, confidence, evidence_json)."""
        conn = self._connect()
        try:
            recs = self._load_records(conn)
        finally:
            conn.close()

        id_index: Dict[Tuple[str, str], List[str]] = defaultdict(list)
        addr_index: Dict[str, List[str]] = defaultdict(list)
        anchor_to_entity: Dict[str, str] = {}
        rel_pointers: List[Tuple[str, str, str, str]] = []  # src, type, role, ptr
        # SHARED_NAME: block by sorted-core-token key; each entry keeps the
        # entity id and its (unsorted) core token tuple for overlap scoring.
        name_index: Dict[str, List[Tuple[str, Tuple[str, ...]]]] = defaultdict(list)

        for eid, _src, raw in recs:
            rid = eid.split(":", 1)[1] if ":" in eid else eid
            anchor_to_entity.setdefault(_norm_id(rid) or rid, eid)
            anchor_to_entity.setdefault(rid, eid)
            for anchor in _extract_pointer_anchors(raw):
                anchor_to_entity.setdefault(anchor, eid)
                anchor_to_entity.setdefault(_norm_id(anchor), eid)
            for label, val in _extract_identifiers(raw):
                id_index[(label, val)].append(eid)
            for addr in _extract_addresses(raw):
                addr_index[addr].append(eid)
            for etype, role, ptr in _extract_relationships(raw):
                rel_pointers.append((eid, etype, role, ptr))
            # name blocking
            nm = self._names.get(eid) or _name_from_raw(raw)
            core_key = _name_core_key(nm)
            if core_key:
                name_index[core_key].append((eid, _name_tokens(nm)))

        edges: List[Tuple[str, str, str, float, str]] = []
        seen_pair: set = set()

        def emit(a: str, b: str, etype: str, conf: float, evidence: dict):
            if a == b:
                return
            key = (a, b, etype)
            if key in seen_pair:
                return
            seen_pair.add(key)
            edges.append((a, b, etype, conf, json.dumps([evidence])))

        # SHARED_IDENTIFIER (both directions so resolver/parties find either end)
        for (label, value), members in id_index.items():
            uniq = sorted(set(members))
            if len(uniq) < 2 or len(uniq) > 40:   # skip giant noisy buckets
                continue
            conf = _group_confidence(len(uniq), base=0.9)
            for a, b in _pairs(uniq):
                ev = {"type": "shared_identifier", "label": label,
                      "value": value, "detail": f"Both carry {label} = {value}"}
                emit(a, b, "SHARED_IDENTIFIER", conf, ev)
                emit(b, a, "SHARED_IDENTIFIER", conf, ev)

        # SHARED_ADDRESS — with hub down-weighting. A normalized address shared
        # by many entities is almost always a registered-agent / incorporation
        # mill, not a genuine co-location. Scale confidence down as the cluster
        # grows and drop pure-hub clusters above the hard cap. This is the main
        # precision fix against false-positive address links.
        for addr, members in addr_index.items():
            uniq = sorted(set(members))
            n = len(uniq)
            if n < 2 or n > 40:
                continue
            if n >= _ADDR_HUB_HARD:
                # registered-agent hub: too noisy to assert any relationship
                continue
            short = (addr[:60] + "...") if len(addr) > 60 else addr
            conf = _group_confidence(n, base=0.6)
            hub = n >= _ADDR_HUB_SOFT
            if hub:
                # extra linear down-weight across the [soft, hard) band
                span = max(1, _ADDR_HUB_HARD - _ADDR_HUB_SOFT)
                conf = round(max(0.15, conf * (1.0 - 0.7 * (n - _ADDR_HUB_SOFT) / span)), 3)
            for a, b in _pairs(uniq):
                detail = f"Shared business address: {short}"
                if hub:
                    detail += f" (shared by {n} entities — likely registered agent)"
                ev = {"type": "shared_address", "value": short,
                      "cluster_size": n, "hub": hub, "detail": detail}
                emit(a, b, "SHARED_ADDRESS", conf, ev)
                emit(b, a, "SHARED_ADDRESS", conf, ev)

        # SHARED_NAME — fuzzy normalized name match. Names are blocked by their
        # sorted core-token key (corporate suffixes / generic trade words
        # stripped), then only emitted on a strong token-set overlap. This
        # catches "Acme Trading Co. Ltd" <-> "Acme Trading LLC" while staying
        # bounded (no all-pairs scan) and never firing on suffix-only matches.
        for core_key, members in name_index.items():
            # require a discriminating core: at least one rare/non-stopword token
            core_tokens = set(core_key.split(" "))
            if not (core_tokens - _NAME_STOPWORDS):
                continue
            uniq: Dict[str, Tuple[str, ...]] = {}
            for eid, toks in members:
                uniq.setdefault(eid, toks)
            ids = sorted(uniq)
            if len(ids) < 2 or len(ids) > 40:
                continue
            for a, b in _pairs(ids):
                overlap = _name_overlap(uniq[a], uniq[b])
                # strong match = high token-set overlap on a multi-token core,
                # or an exact shared rare multi-token core.
                strong = overlap >= _NAME_OVERLAP_THRESHOLD and len(core_tokens) >= 2
                if not strong:
                    continue
                disp = " ".join(t.title() for t in sorted(core_tokens))
                ev = {"type": "shared_name", "core": disp,
                      "overlap": round(overlap, 3),
                      "detail": f"Normalized name match on core '{disp}' "
                                f"(token-set overlap {overlap:.0%})"}
                emit(a, b, "SHARED_NAME", _SHARED_NAME_CONF, ev)
                emit(b, a, "SHARED_NAME", _SHARED_NAME_CONF, ev)

        # OWNED_BY / OFFICER from RELATIONSHIPS pointers (directional)
        for src_id, etype, role, ptr in rel_pointers:
            dst = anchor_to_entity.get(ptr) or anchor_to_entity.get(_norm_id(ptr))
            if not dst or dst == src_id:
                continue
            role_txt = role or "control relationship"
            ev = {"type": etype.lower(), "role": role_txt,
                  "detail": f"{etype.replace('_', ' ').title()}: {role_txt}"}
            emit(src_id, dst, etype, 0.85, ev)

        logger.info("derived %d edges", len(edges))
        return edges

    def persist(self, force: bool = False) -> Dict[str, object]:
        conn = self._connect()
        try:
            # Ensure the table exists — on a fresh container the resolver may not
            # have created it yet when this runs at startup (race fix).
            conn.execute(
                "CREATE TABLE IF NOT EXISTS senzing_relationships ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT, entity_id_a TEXT, "
                "entity_id_b TEXT, relationship_type TEXT, confidence REAL, "
                "evidence TEXT)")
            conn.commit()
            existing = self.already_derived(conn)
            if existing and not force:
                logger.info("marker present (%d edges) — skipping (idempotent)",
                            existing)
                return {"status": "skipped", "existing_edges": existing}

            edges = self.derive()

            cur = conn.cursor()
            if force:
                cur.execute(
                    "DELETE FROM senzing_relationships WHERE relationship_type "
                    "IN ('SHARED_IDENTIFIER','SHARED_ADDRESS','SHARED_NAME',"
                    "'OFFICER','__DERIVED_MARKER__') OR "
                    "(relationship_type='OWNED_BY' AND "
                    "evidence LIKE '%\"type\": \"owned_by\"%')")

            cur.executemany(
                "INSERT INTO senzing_relationships "
                "(entity_id_a, entity_id_b, relationship_type, confidence, evidence)"
                " VALUES (?, ?, ?, ?, ?)", edges)

            # marker
            cur.execute(
                "INSERT INTO senzing_relationships "
                "(entity_id_a, entity_id_b, relationship_type, confidence, evidence)"
                " VALUES (?, ?, ?, ?, ?)",
                ("__MARKER__", "__MARKER__", MARKER_TYPE, float(len(edges)),
                 json.dumps({"derived_edges": len(edges)})))
            conn.commit()

            by_type: Dict[str, int] = defaultdict(int)
            seed_entities: set = set()
            for a, b, t, _c, _e in edges:
                by_type[t] += 1
                seed_entities.add(a)
            logger.info("inserted %d edges over %d entities: %s",
                        len(edges), len(seed_entities), dict(by_type))
            return {
                "status": "inserted",
                "inserted_edges": len(edges),
                "distinct_entities": len(seed_entities),
                "by_type": dict(by_type),
            }
        finally:
            conn.close()


def main(argv: Optional[List[str]] = None) -> int:
    logging.basicConfig(level=logging.INFO,
                        format="%(levelname)s %(name)s: %(message)s")
    ap = argparse.ArgumentParser(description="Derive Senzing relationships from CORD")
    ap.add_argument("--db", default=DB_PATH)
    ap.add_argument("--force", action="store_true",
                    help="re-derive even if marker present")
    ap.add_argument("--neighbor-cap", type=int, default=80000)
    args = ap.parse_args(argv)

    deriver = RelationshipDeriver(args.db, neighbor_cap=args.neighbor_cap)
    result = deriver.persist(force=args.force)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
