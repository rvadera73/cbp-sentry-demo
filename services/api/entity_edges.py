"""
Track T-Graph / B1 — entity edge materialization.

Derives the CT-2 ``EntityEdge`` graph substrate from the real CORD index and
exposes the CT-4 ``GraphSignalProvider`` (``signals_for`` / ``edges_for``).

Edge derivation (all built off the CORD FTS index, table ``cord_fts``):
  * ``shared_identifier`` — two entities carry the same *normalized* strong
    identifier value (LEI, tax id, national id, passport, OFAC id, ...).
  * ``shared_address``    — two entities carry the same *normalized* address.
  * ``ownership``/``officer`` — drawn from ``RELATIONSHIPS`` arrays
    (GLEIF / OPEN-OWNERSHIP / OPEN-SANCTIONS) where a directional
    ``REL_POINTER`` points at another entity. The relationship *role* text
    decides ownership vs officer.

This is a pure NEW module: it does not import or mutate cord_engine / main /
v4_contracts beyond reading the frozen contract shapes. It opens the CORD
sqlite index read-only and never writes to it. ``persist_edges`` is provided as
a helper (it uses ``ENTITY_EDGES_DDL``) but is NOT invoked here — B1 does not
run migrations.

Entity id convention matches cord_engine.watchlist(): ``"{DATA_SOURCE}:{RECORD_ID}"``.
"""
from __future__ import annotations

import json
import logging
import os
import re
import sqlite3
from collections import defaultdict
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Optional, Tuple

from v4_contracts import (
    EDGE_TYPES,
    ENTITY_EDGES_DDL,
    EntityEdge,
    EntityGraphSignals,
)

logger = logging.getLogger(__name__)

# Default location of the CORD FTS index inside the sentry-api container.
DEFAULT_INDEX_PATH = os.getenv("CORD_INDEX_PATH", "/app/data/cord_index.db")

# Sources whose RELATIONSHIPS arrays carry directional pointers we can resolve.
RELATIONSHIP_SOURCES = ("GLEIF", "OPEN-OWNERSHIP", "OPEN-SANCTIONS")

# Identifier keys that genuinely identify an entity (strong join keys). We list
# (TYPE_KEY, VALUE_KEY) for the keyed "OTHER_*" pairs and bare keys for the
# direct ones. Cross-reference back-pointers (OTHER_ID_TYPE in this set) are
# skipped — they only mirror another source's primary key, not a shared real
# identifier, and would create spurious dense stars.
_DIRECT_ID_KEYS = (
    "LEI_NUMBER",
    "NATIONAL_ID_NUMBER",
    "TAX_ID_NUMBER",
    "PASSPORT_NUMBER",
    "OFAC_ID",
    "TRUSTED_ID_NUMBER",
)
# OTHER_ID_TYPE values that are just source cross-links, not real shared ids.
_XREF_ID_TYPES = {
    "OPEN_SANCTIONS",
    "OPEN-SANCTIONS",
    "OPEN_OWNERSHIP",
    "OPEN-OWNERSHIP",
    "GLEIF",
    "ICIJ",
    "ICIJ_ID",
}

# Role-text classification for RELATIONSHIPS -> edge_type.
_OWNERSHIP_ROLE_RE = re.compile(
    r"own|control|consolidat|shareholder|shares|beneficial|parent|holding|fund-managed",
    re.IGNORECASE,
)
_OFFICER_ROLE_RE = re.compile(
    r"director|officer|manager|secretary|appoint|signator|board|partner|executive|acting for",
    re.IGNORECASE,
)


# --------------------------------------------------------------------------- #
# normalization helpers
# --------------------------------------------------------------------------- #
def _norm_id(value: object) -> str:
    """Normalize an identifier value: upper, strip, collapse non-alnum."""
    if value is None:
        return ""
    s = re.sub(r"[^A-Za-z0-9]", "", str(value)).upper()
    return s if len(s) >= 4 else ""  # too-short values are noise


def _norm_addr(value: object) -> str:
    """Normalize a free-text address into a coarse join key."""
    if not value:
        return ""
    s = str(value).upper()
    s = re.sub(r"[^A-Z0-9 ]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    # Drop pure-noise / too-generic addresses.
    return s if len(s) >= 10 else ""


def _entity_id(data_source: str, record_id: str) -> str:
    return f"{data_source}:{record_id}"


# --------------------------------------------------------------------------- #
# per-record extractors
# --------------------------------------------------------------------------- #
def _extract_identifiers(raw: Dict) -> List[Tuple[str, str]]:
    """Return [(id_label, normalized_value), ...] of strong join identifiers."""
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
        # Keyed OTHER_ID_TYPE/OTHER_ID_NUMBER pairs, minus cross-ref pointers.
        otype = (idobj.get("OTHER_ID_TYPE") or "").strip()
        onum = idobj.get("OTHER_ID_NUMBER")
        if onum and otype and otype not in _XREF_ID_TYPES:
            add(otype, onum)

    # OFAC carries a top-level OFAC_ID (and no IDENTIFIERS array).
    if raw.get("OFAC_ID"):
        add("OFAC_ID", raw["OFAC_ID"])
    return out


def _extract_addresses(raw: Dict) -> List[str]:
    """Return normalized address join keys from the various address schemas."""
    out: List[str] = []
    seen = set()

    def add(value: str):
        nv = _norm_addr(value)
        if nv and nv not in seen:
            seen.add(nv)
            out.append(nv)

    # GLEIF / OPEN-* / ICIJ : ADDRESSES[].ADDR_FULL
    for addr in raw.get("ADDRESSES", []) or []:
        if isinstance(addr, dict):
            add(addr.get("ADDR_FULL") or addr.get("ADDR_LINE1"))
    # OFAC : ADDR_LIST[] with line/city/country parts
    for addr in raw.get("ADDR_LIST", []) or []:
        if isinstance(addr, dict):
            parts = [
                addr.get("ADDR_LINE1"),
                addr.get("ADDR_CITY"),
                addr.get("ADDR_COUNTRY"),
            ]
            joined = ", ".join(p for p in parts if p)
            add(joined)
    return out


def _classify_relationship(role: str) -> Optional[str]:
    """Map a RELATIONSHIPS role string to 'ownership' | 'officer' | None."""
    if not role:
        # No role text at all -> generic control link; treat as ownership.
        return "ownership"
    if _OWNERSHIP_ROLE_RE.search(role):
        return "ownership"
    if _OFFICER_ROLE_RE.search(role):
        return "officer"
    return "ownership"  # default: a directional control pointer


def _extract_relationships(raw: Dict) -> List[Tuple[str, str, str]]:
    """Return [(edge_type, role, pointer_key), ...] of directional pointers.

    Only ``REL_POINTER_KEY`` entries are edges (they point at another entity).
    ``REL_ANCHOR_KEY`` is the record's own anchor and is ignored.
    """
    out: List[Tuple[str, str, str]] = []
    for rel in raw.get("RELATIONSHIPS", []) or []:
        if not isinstance(rel, dict):
            continue
        ptr = rel.get("REL_POINTER_KEY")
        if not ptr:
            continue
        role = (rel.get("REL_POINTER_ROLE") or "").strip()
        etype = _classify_relationship(role)
        if etype:
            out.append((etype, role, str(ptr)))
    return out


def _newness_signal(raw: Dict) -> float:
    """Best-effort 'newly registered' signal in [0,1]; older -> lower.

    Uses GLEIF DATES[].REGISTRATION_DATE / OPEN-SANCTIONS REGISTRATION_DATE and
    ICIJ INCORPORATED. Entities registered within ~2y read as 1.0, decaying to
    0 by ~10y. Absent date -> 0 (no signal, not penalized).
    """
    dt = None
    for d in raw.get("DATES", []) or []:
        if isinstance(d, dict) and d.get("REGISTRATION_DATE"):
            dt = _parse_date(d["REGISTRATION_DATE"])
            break
    if dt is None and raw.get("INCORPORATED"):
        dt = _parse_date(raw["INCORPORATED"])
    if dt is None:
        return 0.0
    now = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    age_years = max(0.0, (now - dt).days / 365.25)
    if age_years <= 2:
        return 1.0
    if age_years >= 10:
        return 0.0
    return round(1.0 - (age_years - 2) / 8.0, 3)


def _parse_date(value: str) -> Optional[datetime]:
    s = str(value).strip()
    for fmt in ("%Y-%m-%d", "%d-%b-%Y", "%Y-%m-%dT%H:%M:%S", "%Y"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


# --------------------------------------------------------------------------- #
# main builder
# --------------------------------------------------------------------------- #
class EntityEdgeBuilder:
    """Builds and indexes the entity edge set from the CORD FTS index.

    Implements the CT-4 ``GraphSignalProvider`` Protocol
    (``signals_for`` / ``edges_for``).
    """

    def __init__(self, index_path: str = None, limit: int = 2000):
        self.index_path = index_path or DEFAULT_INDEX_PATH
        self._limit = limit
        self._edges: List[EntityEdge] = []
        self._by_entity: Dict[str, List[EntityEdge]] = defaultdict(list)
        # Per-entity raw signals collected during the build.
        self._shared_id_count: Dict[str, int] = defaultdict(int)
        self._shell_density: Dict[str, float] = defaultdict(float)
        self._newness: Dict[str, float] = {}
        self._degree: Dict[str, int] = defaultdict(int)
        self._max_degree: int = 0
        self._built = False

    # -- internal -- #
    def _connect(self) -> sqlite3.Connection:
        # Read-only so we never touch the live index.
        uri = f"file:{self.index_path}?mode=ro"
        try:
            conn = sqlite3.connect(uri, uri=True)
        except sqlite3.OperationalError:
            conn = sqlite3.connect(self.index_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _scan(self, conn: sqlite3.Connection) -> Iterable[Tuple[str, Dict]]:
        cur = conn.cursor()
        cur.execute(
            "SELECT data_source, record_id, raw_json FROM cord_fts LIMIT ?",
            (self._limit,),
        )
        for row in cur.fetchall():
            try:
                raw = json.loads(row["raw_json"])
            except (json.JSONDecodeError, TypeError):
                continue
            yield _entity_id(row["data_source"], row["record_id"]), raw

    def build(self) -> List[EntityEdge]:
        """Scan the index, materialize edges, and pre-compute signal inputs."""
        id_index: Dict[Tuple[str, str], List[str]] = defaultdict(list)
        addr_index: Dict[str, List[str]] = defaultdict(list)
        # Map any anchor/identifier token an entity is known by -> its entity_id,
        # so RELATIONSHIPS pointer keys can be resolved to real entities.
        anchor_to_entity: Dict[str, str] = {}
        rel_pointers: List[Tuple[str, str, str, str]] = []  # src, etype, role, ptr

        edges: List[EntityEdge] = []

        with self._connect() as conn:
            for entity_id, raw in self._scan(conn):
                # newness
                self._newness[entity_id] = _newness_signal(raw)

                # register anchors so pointers can resolve back to this entity
                record_id = entity_id.split(":", 1)[1]
                anchor_to_entity.setdefault(_norm_id(record_id) or record_id, entity_id)
                for anchor_key in ("REL_ANCHOR_KEY",):
                    if raw.get(anchor_key):
                        anchor_to_entity.setdefault(str(raw[anchor_key]), entity_id)
                for rel in raw.get("RELATIONSHIPS", []) or []:
                    if isinstance(rel, dict) and rel.get("REL_ANCHOR_KEY"):
                        anchor_to_entity.setdefault(str(rel["REL_ANCHOR_KEY"]), entity_id)
                for idobj in raw.get("IDENTIFIERS", []) or []:
                    if isinstance(idobj, dict) and idobj.get("OTHER_ID_NUMBER"):
                        anchor_to_entity.setdefault(str(idobj["OTHER_ID_NUMBER"]), entity_id)

                # shared identifier index
                for label, value in _extract_identifiers(raw):
                    id_index[(label, value)].append(entity_id)
                # shared address index
                for addr in _extract_addresses(raw):
                    addr_index[addr].append(entity_id)
                # relationships -> deferred until anchors resolved
                for etype, role, ptr in _extract_relationships(raw):
                    rel_pointers.append((entity_id, etype, role, ptr))

        # --- shared_identifier edges --- #
        for (label, value), members in id_index.items():
            uniq = sorted(set(members))
            if len(uniq) < 2:
                continue
            for a, b in _pairs(uniq):
                conf = _group_confidence(len(uniq), base=0.9)
                edges.append(
                    EntityEdge(
                        src_entity_id=a,
                        dst_entity_id=b,
                        edge_type="shared_identifier",
                        evidence=f"Both carry {label} = {value}",
                        confidence=conf,
                        source="CORD:IDENTIFIERS",
                    )
                )
            for m in uniq:
                self._shared_id_count[m] += len(uniq) - 1
                self._shell_density[m] += (len(uniq) - 1)

        # --- shared_address edges --- #
        for addr, members in addr_index.items():
            uniq = sorted(set(members))
            if len(uniq) < 2:
                continue
            short = (addr[:60] + "...") if len(addr) > 60 else addr
            for a, b in _pairs(uniq):
                conf = _group_confidence(len(uniq), base=0.6)
                edges.append(
                    EntityEdge(
                        src_entity_id=a,
                        dst_entity_id=b,
                        edge_type="shared_address",
                        evidence=f"Shared business address: {short}",
                        confidence=conf,
                        source="CORD:ADDRESSES",
                    )
                )
            for m in uniq:
                self._shell_density[m] += (len(uniq) - 1)

        # --- ownership / officer edges from RELATIONSHIPS --- #
        for src_id, etype, role, ptr in rel_pointers:
            dst_id = anchor_to_entity.get(ptr) or anchor_to_entity.get(_norm_id(ptr))
            if not dst_id:
                # Unresolvable pointer (target outside the scanned slice): keep
                # the edge with the raw pointer key as a placeholder dst so the
                # relationship is not silently lost.
                dst_id = f"UNRESOLVED:{ptr}"
                conf = 0.4
            else:
                conf = 0.85
            if dst_id == src_id:
                continue
            role_txt = role or "control relationship"
            edges.append(
                EntityEdge(
                    src_entity_id=src_id,
                    dst_entity_id=dst_id,
                    edge_type=etype,
                    evidence=f"{etype.title()} link: {role_txt}",
                    confidence=conf,
                    source="CORD:RELATIONSHIPS",
                )
            )

        # validate edge types against the frozen contract
        edges = [e for e in edges if e.edge_type in EDGE_TYPES]

        # --- index + degree --- #
        for e in edges:
            self._by_entity[e.src_entity_id].append(e)
            self._by_entity[e.dst_entity_id].append(e)
            self._degree[e.src_entity_id] += 1
            self._degree[e.dst_entity_id] += 1
        self._max_degree = max(self._degree.values(), default=0)

        self._edges = edges
        self._built = True
        logger.info("entity_edges: built %d edges over limit=%d", len(edges), self._limit)
        return edges

    def _ensure_built(self):
        if not self._built:
            self.build()

    # -- public API -- #
    def edges_for(self, entity_id: str) -> List[EntityEdge]:
        self._ensure_built()
        return list(self._by_entity.get(entity_id, []))

    def signals_for(self, entity_id: str) -> EntityGraphSignals:
        self._ensure_built()
        degree = self._degree.get(entity_id, 0)
        centrality = round(degree / self._max_degree, 3) if self._max_degree else 0.0

        # shell_indicator: blend of shared id/address density and newness.
        density = self._shell_density.get(entity_id, 0.0)
        # squash density into 0-1 (5+ shared-attribute co-members reads as high)
        density_score = min(1.0, density / 5.0)
        newness = self._newness.get(entity_id, 0.0)
        shell = round(min(1.0, 0.7 * density_score + 0.3 * newness), 3)

        return EntityGraphSignals(
            entity_id=entity_id,
            corridor_degree=0,   # operational corridor join — out of scope for B1
            resolved_degree=0,   # ditto
            centrality=centrality,
            shell_indicator=shell,
            shared_identifier_count=self._shared_id_count.get(entity_id, 0),
            corridors=[],
        )


# --------------------------------------------------------------------------- #
# small helpers
# --------------------------------------------------------------------------- #
def _pairs(items: List[str]) -> Iterable[Tuple[str, str]]:
    n = len(items)
    for i in range(n):
        for j in range(i + 1, n):
            yield items[i], items[j]


def _group_confidence(group_size: int, base: float) -> float:
    """Confidence decays as a shared attribute group grows (a value shared by
    many entities is weaker evidence of a real 1:1 link)."""
    penalty = min(0.4, 0.05 * (group_size - 2))
    return round(max(0.2, base - penalty), 3)


# --------------------------------------------------------------------------- #
# module-level entry points
# --------------------------------------------------------------------------- #
_builder: Optional[EntityEdgeBuilder] = None


def build_edges(limit: int = 2000) -> List[EntityEdge]:
    """Build (and cache) the entity edge set from the CORD index."""
    global _builder
    _builder = EntityEdgeBuilder(limit=limit)
    return _builder.build()


def get_provider(limit: int = 2000) -> EntityEdgeBuilder:
    """Return a built GraphSignalProvider over the CORD index."""
    global _builder
    if _builder is None or not _builder._built:
        _builder = EntityEdgeBuilder(limit=limit)
        _builder.build()
    return _builder


def edges_for(entity_id: str) -> List[EntityEdge]:
    """Convenience: edges incident to an entity (builds on first use)."""
    return get_provider().edges_for(entity_id)


def persist_edges(conn, edges: Optional[List[EntityEdge]] = None) -> int:
    """Create the entity_edges table (ENTITY_EDGES_DDL) and upsert ``edges``.

    Helper only — B1 does NOT run this against a live DB. ``conn`` is a DB-API
    connection (psycopg2-style) to the risk_scoring store. Returns the number of
    rows attempted. Uses parameterized inserts with ON CONFLICT DO NOTHING to
    respect the UNIQUE(src,dst,edge_type) constraint in the DDL.
    """
    if edges is None:
        edges = get_provider().build() if not (_builder and _builder._built) else _builder._edges
    cur = conn.cursor()
    # ENTITY_EDGES_DDL is multi-statement; execute it as-is (Postgres handles it).
    cur.execute(ENTITY_EDGES_DDL)
    rows = 0
    for e in edges:
        cur.execute(
            """
            INSERT INTO risk_scoring.entity_edges
                (src_entity_id, dst_entity_id, edge_type, evidence, confidence, source)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (src_entity_id, dst_entity_id, edge_type) DO NOTHING
            """,
            (e.src_entity_id, e.dst_entity_id, e.edge_type,
             e.evidence, e.confidence, e.source),
        )
        rows += 1
    conn.commit()
    return rows
