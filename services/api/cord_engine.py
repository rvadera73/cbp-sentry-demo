"""CORD FTS Index Engine — Search 244K entities efficiently without eval limits.

Track T-Data extensions (A1/A2/A3) live in THIS file only:
  * A1 — EAPA respondents (Postgres ``cbp_sentry.eapa_cases``) surfaced as the
    CORD source ``CBP-EAPA`` (CT-3 ``CordFlagRecord`` shape), with
    ``is_eapa_respondent()`` and flow into ``watchlist()``.
  * A2 — DHS UFLPA Entity List seed loaded from
    ``data/uflpa_entity_list.jsonl`` as source ``UFLPA-ENTITY-LIST``, with
    ``is_uflpa_listed()`` and flow into ``watchlist()``.
  * A3 — ``NPI-PROVIDERS`` / ``GLOBALDATA`` are identity-resolution mass only;
    excluded from ``watchlist()`` and any scoring path. ``is_identity_only()``.
"""

import sqlite3
import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# --- T-Data: frozen contract values (CT-3). Import defensively so the engine
# still loads if the contract module is not on the path in some tooling. -------
try:
    from v4_contracts import (
        EAPA_SOURCE,
        UFLPA_SOURCE,
        IDENTITY_ONLY_SOURCES,
        CordFlagRecord,
    )
except Exception:  # pragma: no cover - keep the engine importable in isolation
    EAPA_SOURCE = "CBP-EAPA"
    UFLPA_SOURCE = "UFLPA-ENTITY-LIST"
    IDENTITY_ONLY_SOURCES = ("NPI-PROVIDERS", "GLOBALDATA")
    CordFlagRecord = None  # type: ignore

# A1 flag value entity_scorer keys on (data_source==CBP-EAPA OR FLAG==this).
EAPA_FLAG = "eapa_respondent"
# A2 flag value entity_scorer keys on (data_source==UFLPA-ENTITY-LIST OR FLAG==this).
UFLPA_FLAG = "uflpa_listed"

# A1 fallback fixture — mirrors the rows seeded into ``cbp_sentry.eapa_cases``
# (services/data/db.py ``_seed_reference_data``). Used ONLY when the Postgres
# ``cbp_sentry.eapa_cases`` table is unreachable from this process (e.g. the
# sentry-api container ships without psycopg2). Tuple shape mirrors the table:
# (entity_name, origin_country, destination_country, case_id, product_description).
_EAPA_FALLBACK_RESPONDENTS = [
    ("Greenfield Industrial Trading Co.", "VN", "US", "EAPA-a4d8bf20", "Aluminum Extrusions (7604)"),
    ("Shanghai Pacific Metals Ltd.", "CN", "US", "EAPA-09af72ea", "Steel Coils"),
    ("Vietnam Trade Solutions", "VN", "US", "EAPA-a10f8f70", "Textiles & Apparel"),
    ("Foshan Global Import", "CN", "US", "EAPA-3aaeea32", "Aluminum Extrusions (7604)"),
    ("ASEAN Commerce Group", "TH", "US", "EAPA-37773c1c", "Electronics"),
]


class CORDEngine:
    """Build and query a searchable FTS5 index from CORD JSONL files."""

    def __init__(self, cord_data_dir: str = None, index_path: str = None):
        """
        Initialize CORD engine.

        Args:
            cord_data_dir: Directory containing CORD JSONL files (default: env CORD_DATA_DIR)
            index_path: Path to SQLite FTS5 index (default: env CORD_INDEX_PATH)
        """
        self.cord_data_dir = cord_data_dir or os.getenv("CORD_DATA_DIR", "/app/cord-data")
        self.index_path = index_path or os.getenv("CORD_INDEX_PATH", "/app/cord-index/cord_index.db")

        # Ensure index directory exists
        os.makedirs(os.path.dirname(self.index_path), exist_ok=True)

        self._ensure_index_exists()

        # --- T-Data flag sources (loaded into memory, flowed into watchlist) ---
        # A1: EAPA respondents (CBP-EAPA). A2: UFLPA Entity List (UFLPA-ENTITY-LIST).
        self._eapa_records: List[Dict] = self._load_eapa_respondents()
        self._eapa_names: set = {
            (r.get("PRIMARY_NAME_ORG") or "").strip().lower()
            for r in self._eapa_records if r.get("PRIMARY_NAME_ORG")
        }
        self._uflpa_records: List[Dict] = self._load_uflpa_entities()
        self._uflpa_names: set = {
            (r.get("PRIMARY_NAME_ORG") or "").strip().lower()
            for r in self._uflpa_records if r.get("PRIMARY_NAME_ORG")
        }
        logger.info(
            "T-Data flag sources loaded: %d CBP-EAPA respondents, %d UFLPA-ENTITY-LIST entries",
            len(self._eapa_records), len(self._uflpa_records),
        )

    # ----------------------------------------------------------------------
    # A1 — EAPA respondents as CORD source CBP-EAPA
    # ----------------------------------------------------------------------
    @staticmethod
    def _flag_record(data_source: str, record_id: str, name: str, flag: str,
                     country: str = "", docket: str = "", commodity: str = "",
                     route: str = "") -> Dict:
        """Build a CT-3 CordFlagRecord-shaped dict (uses the frozen contract
        dataclass when importable, else an equivalent literal)."""
        if CordFlagRecord is not None:
            return CordFlagRecord(
                DATA_SOURCE=data_source, RECORD_ID=record_id,
                PRIMARY_NAME_ORG=name, COUNTRY=country, FLAG=flag,
                DOCKET=docket, COMMODITY=commodity, ROUTE=route,
            ).to_record()
        return {
            "DATA_SOURCE": data_source, "RECORD_ID": record_id,
            "RECORD_TYPE": "ORGANIZATION", "PRIMARY_NAME_ORG": name,
            "COUNTRY": country, "FLAG": flag, "DOCKET": docket,
            "COMMODITY": commodity, "ROUTE": route,
        }

    def _eapa_rows(self) -> List[Tuple]:
        """Fetch EAPA respondents from Postgres ``cbp_sentry.eapa_cases``.

        Returns rows of (entity_name, origin_country, destination_country,
        case_id, product_description). Falls back to the embedded fixture if
        psycopg2 is unavailable or the DB/table is unreachable (the sentry-api
        runtime ships without psycopg2, so the fixture is the live path there)."""
        try:
            import psycopg2  # noqa: WPS433 — optional dependency, DB-only path
            dsn = os.environ.get(
                "DATABASE_URL", "postgresql://sentry:sentry-secret@sentry-db:5432/sentry"
            )
            conn = psycopg2.connect(dsn, options="-c search_path=cbp_sentry")
            try:
                cur = conn.cursor()
                cur.execute(
                    "SELECT entity_name, origin_country, destination_country, "
                    "case_id, product_description FROM eapa_cases "
                    "WHERE entity_name IS NOT NULL"
                )
                rows = cur.fetchall()
                cur.close()
                if rows:
                    logger.info("Loaded %d EAPA respondents from cbp_sentry.eapa_cases", len(rows))
                    return list(rows)
                logger.warning("cbp_sentry.eapa_cases empty; using EAPA fixture")
            finally:
                conn.close()
        except Exception as exc:  # psycopg2 missing or DB unreachable
            logger.warning("EAPA Postgres load unavailable (%s); using EAPA fixture", exc)
        return list(_EAPA_FALLBACK_RESPONDENTS)

    def _load_eapa_respondents(self) -> List[Dict]:
        """A1: build CordFlagRecord-shaped CBP-EAPA records from EAPA rows."""
        out: List[Dict] = []
        for (name, origin, dest, case_id, product) in self._eapa_rows():
            if not name:
                continue
            origin = (origin or "").strip()
            dest = (dest or "").strip()
            route = f"{origin}->{dest}" if origin and dest else (origin or dest or "")
            out.append(self._flag_record(
                data_source=EAPA_SOURCE,
                record_id=str(case_id or name),
                name=str(name).strip(),
                flag=EAPA_FLAG,
                country=origin,
                docket=str(case_id or ""),
                commodity=str(product or ""),
                route=route,
            ))
        return out

    def is_eapa_respondent(self, name: str) -> bool:
        """A1: True iff ``name`` is a confirmed CBP-EAPA respondent (case-insensitive)."""
        if not name:
            return False
        return name.strip().lower() in self._eapa_names

    def eapa_records(self) -> List[Dict]:
        """A1: all CBP-EAPA CordFlagRecord-shaped records."""
        return list(self._eapa_records)

    # ----------------------------------------------------------------------
    # A2 — DHS UFLPA Entity List as CORD source UFLPA-ENTITY-LIST
    # ----------------------------------------------------------------------
    def _uflpa_seed_path(self) -> Optional[Path]:
        """Locate the UFLPA seed JSONL (env override, then alongside this module,
        then the container /app/data path)."""
        candidates = [
            os.getenv("UFLPA_ENTITY_LIST_PATH"),
            str(Path(__file__).with_name("data") / "uflpa_entity_list.jsonl"),
            "/app/data/uflpa_entity_list.jsonl",
        ]
        for c in candidates:
            if c and os.path.exists(c):
                return Path(c)
        return None

    def _load_uflpa_entities(self) -> List[Dict]:
        """A2: build CordFlagRecord-shaped UFLPA-ENTITY-LIST records from the
        seed JSONL. Lines starting with ``//`` (or ``#``) and blank lines are
        ignored so the file can carry provenance comments."""
        path = self._uflpa_seed_path()
        if not path:
            logger.warning("UFLPA seed file not found; UFLPA-ENTITY-LIST will be empty")
            return []
        out: List[Dict] = []
        try:
            with open(path, encoding="utf-8") as f:
                for line in f:
                    s = line.strip()
                    if not s or s.startswith("//") or s.startswith("#"):
                        continue
                    try:
                        rec = json.loads(s)
                    except json.JSONDecodeError:
                        logger.warning("Skipped malformed UFLPA seed line in %s", path.name)
                        continue
                    name = (rec.get("PRIMARY_NAME_ORG") or rec.get("name") or "").strip()
                    if not name:
                        continue
                    out.append(self._flag_record(
                        data_source=UFLPA_SOURCE,
                        record_id=str(rec.get("RECORD_ID") or name),
                        name=name,
                        flag=UFLPA_FLAG,
                        country=str(rec.get("COUNTRY") or "").strip(),
                        docket=str(rec.get("DOCKET") or ""),
                        commodity=str(rec.get("COMMODITY") or ""),
                        route=str(rec.get("ROUTE") or ""),
                    ))
            logger.info("Loaded %d UFLPA-ENTITY-LIST entries from %s", len(out), path.name)
        except Exception as exc:
            logger.error("Error loading UFLPA seed %s: %s", path, exc)
        return out

    def is_uflpa_listed(self, name: str) -> bool:
        """A2: True iff ``name`` is on the DHS UFLPA Entity List (case-insensitive)."""
        if not name:
            return False
        return name.strip().lower() in self._uflpa_names

    def uflpa_records(self) -> List[Dict]:
        """A2: all UFLPA-ENTITY-LIST CordFlagRecord-shaped records."""
        return list(self._uflpa_records)

    # ----------------------------------------------------------------------
    # A3 — NPI-PROVIDERS / GLOBALDATA are identity-resolution mass only
    # ----------------------------------------------------------------------
    @staticmethod
    def is_identity_only(source: str) -> bool:
        """A3: True iff ``source`` is identity-resolution mass only
        (IDENTITY_ONLY_SOURCES) and must be excluded from watchlist + scoring."""
        return (source or "").strip().upper() in {
            s.upper() for s in IDENTITY_ONLY_SOURCES
        }

    def _ensure_index_exists(self) -> None:
        """Create FTS5 index if it doesn't exist."""
        if not os.path.exists(self.index_path) or os.path.getsize(self.index_path) < 1000:
            logger.info(f"Building CORD FTS5 index from {self.cord_data_dir}...")
            self._build_index()
        else:
            logger.info(f"Using existing CORD index at {self.index_path}")

    def _build_index(self) -> None:
        """Build FTS5 index from all JSONL files in cord_data_dir."""
        conn = sqlite3.connect(self.index_path)
        cursor = conn.cursor()

        # Create FTS5 virtual table
        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS cord_fts USING fts5(
                record_id,
                data_source,
                record_type,
                name_primary,
                names_aka,
                country,
                ofac_program,
                sanctions_topic,
                raw_json
            )
        """)

        # Create non-FTS table for OFAC-specific lookups (faster SDN checks)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ofac_sdn (
                record_id TEXT PRIMARY KEY,
                name_primary TEXT,
                names_aka TEXT,
                sdn_program TEXT,
                entity_type TEXT,
                raw_json TEXT
            )
        """)

        cord_dir = Path(self.cord_data_dir)
        if not cord_dir.exists():
            logger.warning(f"CORD data directory not found: {cord_dir}")
            conn.close()
            return

        jsonl_files = list(cord_dir.glob("*.jsonl"))
        logger.info(f"Found {len(jsonl_files)} JSONL files in {cord_dir}")

        total_records = 0
        ofac_records = 0

        for jsonl_file in jsonl_files:
            logger.info(f"Indexing {jsonl_file.name}...")
            try:
                with open(jsonl_file) as f:
                    for line in f:
                        if not line.strip():
                            continue
                        try:
                            record = json.loads(line)
                            self._index_record(cursor, record)
                            total_records += 1

                            # Track OFAC separately for SDN checks
                            if record.get("DATA_SOURCE") == "OFAC":
                                ofac_records += 1

                        except json.JSONDecodeError:
                            logger.warning(f"Skipped malformed JSON in {jsonl_file.name}")
                            continue

            except Exception as e:
                logger.error(f"Error indexing {jsonl_file.name}: {e}")
                continue

        conn.commit()
        conn.close()

        logger.info(f"✓ CORD index built: {total_records} records ({ofac_records} OFAC SDN entries)")

    def _index_record(self, cursor: sqlite3.Cursor, record: Dict) -> None:
        """Index a single CORD record into FTS5 and OFAC tables."""
        record_id = record.get("RECORD_ID", "")
        data_source = record.get("DATA_SOURCE", "")
        record_type = record.get("RECORD_TYPE", "")

        # Extract primary name
        name_primary = ""
        names_aka_list = []

        if data_source == "GLEIF":
            names = record.get("NAMES", [])
            for name_obj in names:
                if name_obj.get("NAME_TYPE") == "PRIMARY":
                    name_primary = name_obj.get("NAME_ORG", "")
                else:
                    names_aka_list.append(name_obj.get("NAME_ORG", ""))

        elif data_source == "OFAC":
            name_list = record.get("NAME_LIST", [])
            for name_obj in name_list:
                if name_obj.get("NAME_TYPE") == "PRIMARY":
                    name_primary = name_obj.get("NAME_ORG", "")
                else:
                    names_aka_list.append(name_obj.get("NAME_ORG", ""))

        else:
            # Generic extraction for other sources
            name_primary = record.get("NAME", record.get("name", ""))

        names_aka = " ".join(names_aka_list)

        # Extract country
        country = ""
        if data_source == "GLEIF":
            countries = record.get("COUNTRIES", [])
            if countries:
                country = countries[0].get("REGISTRATION_COUNTRY", "")
        else:
            country = record.get("COUNTRY_CODE", record.get("country", ""))

        # Extract OFAC program (if OFAC record)
        ofac_program = ""
        if data_source == "OFAC":
            ofac_program = record.get("SDN_PROGRAM", "")

        # Extract sanctions topic (if OpenSanctions)
        sanctions_topic = ""
        if data_source == "OPEN_SANCTIONS":
            risks = record.get("RISKS", [])
            if risks:
                sanctions_topic = risks[0].get("TOPIC", "")

        raw_json = json.dumps(record)

        # Insert into FTS5
        try:
            cursor.execute(
                """
                INSERT INTO cord_fts (record_id, data_source, record_type, name_primary, names_aka, country, ofac_program, sanctions_topic, raw_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    record_id,
                    data_source,
                    record_type,
                    name_primary,
                    names_aka,
                    country,
                    ofac_program,
                    sanctions_topic,
                    raw_json,
                ),
            )
        except sqlite3.IntegrityError:
            pass  # Duplicate, skip

        # If OFAC, also insert into ofac_sdn for faster SDN checks
        if data_source == "OFAC":
            try:
                cursor.execute(
                    """
                    INSERT INTO ofac_sdn (record_id, name_primary, names_aka, sdn_program, entity_type, raw_json)
                    VALUES (?, ?, ?, ?, ?, ?)
                """,
                    (record_id, name_primary, names_aka, ofac_program, record_type, raw_json),
                )
            except sqlite3.IntegrityError:
                pass

    def search(self, name: str, country: str = None, limit: int = 10) -> List[Dict]:
        """
        Search CORD index for entities by name + country.

        Args:
            name: Entity name to search (FTS5 match)
            country: Optional country code filter (exact match)
            limit: Max results to return

        Returns:
            List of matching records with raw JSON
        """
        conn = sqlite3.connect(self.index_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            if country:
                cursor.execute(
                    """
                    SELECT record_id, data_source, name_primary, country, raw_json
                    FROM cord_fts
                    WHERE cord_fts MATCH ? AND country = ?
                    LIMIT ?
                """,
                    (name, country, limit),
                )
            else:
                cursor.execute(
                    """
                    SELECT record_id, data_source, name_primary, country, raw_json
                    FROM cord_fts
                    WHERE cord_fts MATCH ?
                    LIMIT ?
                """,
                    (name, limit),
                )

            results = []
            for row in cursor.fetchall():
                results.append(
                    {
                        "record_id": row["record_id"],
                        "data_source": row["data_source"],
                        "name": row["name_primary"],
                        "country": row["country"],
                        "raw_json": json.loads(row["raw_json"]),
                    }
                )

            logger.debug(f"CORD search '{name}' (country={country}) found {len(results)} matches")
            return results

        finally:
            conn.close()

    def get_ofac_status(self, name: str, country: str = None) -> Optional[Dict]:
        """
        Check if entity is on OFAC SDN list.

        Args:
            name: Entity name
            country: Optional country filter

        Returns:
            OFAC record if found, None otherwise
        """
        conn = sqlite3.connect(self.index_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            # FTS search on OFAC table
            cursor.execute(
                """
                SELECT record_id, name_primary, sdn_program, entity_type, raw_json
                FROM ofac_sdn
                WHERE name_primary LIKE ? OR names_aka LIKE ?
                LIMIT 1
            """,
                (f"%{name}%", f"%{name}%"),
            )

            row = cursor.fetchone()
            if row:
                logger.info(f"OFAC SDN match found for '{name}': {row['name_primary']}")
                return {
                    "matched": True,
                    "entity_name": name,
                    "sdn_name": row["name_primary"],
                    "program": row["sdn_program"],
                    "entity_type": row["entity_type"],
                    "source": "CORD OFAC SDN",
                    "raw": json.loads(row["raw_json"]),
                }

            return None

        finally:
            conn.close()

    # Flagged data sources present in the CORD index, mapped to a watchlist flag.
    WATCHLIST_SOURCES = [
        ("OFAC", "sanctioned"),
        ("OPEN-SANCTIONS", "sanctioned"),
        ("US-LABOR-VIOLATIONS", "forced_labor"),
        ("ICIJ", "offshore"),
        ("NOMINO-RISK", "high_risk"),
    ]

    @staticmethod
    def _name_from_raw(raw: Dict) -> str:
        """Best-effort entity name from a raw CORD record across source schemas
        (the index only special-cases GLEIF/OFAC for name_primary)."""
        for key in ("NAMES", "NAME_LIST"):
            arr = raw.get(key)
            if isinstance(arr, list) and arr:
                prim = next((n for n in arr if n.get("NAME_TYPE") == "PRIMARY"), None) or arr[0]
                org = prim.get("NAME_ORG") or prim.get("NAME_FULL")
                if org:
                    return org
                parts = [prim.get("PRIMARY_NAME_FIRST"), prim.get("PRIMARY_NAME_MIDDLE"), prim.get("PRIMARY_NAME_LAST")]
                full = " ".join(p for p in parts if p).strip()
                if full:
                    return full
        for key in ("PRIMARY_NAME_ORG", "LEGAL_NAME_ORG", "NAME", "name", "Title"):
            v = raw.get(key)
            if v:
                return str(v)
        return ""

    @staticmethod
    def _country_from_raw(raw: Dict) -> str:
        c = raw.get("COUNTRIES")
        if isinstance(c, list) and c:
            c0 = c[0]
            return c0.get("REGISTRATION_COUNTRY") or c0.get("COUNTRY") or c0.get("ADDR_COUNTRY") or ""
        return raw.get("COUNTRY_CODE") or raw.get("BUSINESS_ADDR_STATE") or ""

    def _flag_record_to_watchlist(self, rec: Dict, flag: str) -> Dict:
        """Project a CT-3 CordFlagRecord dict onto the watchlist row shape."""
        program = " / ".join(p for p in (rec.get("DOCKET"), rec.get("COMMODITY")) if p) or None
        return {
            "entity_id": f"{rec['DATA_SOURCE']}:{rec['RECORD_ID']}",
            "name": rec["PRIMARY_NAME_ORG"],
            "country": (rec.get("COUNTRY") or "").upper(),
            "data_source": rec["DATA_SOURCE"],
            "flag": flag,
            "program": program,
            "route": rec.get("ROUTE") or None,
        }

    def watchlist(self, limit: int = 50) -> List[Dict]:
        """Default flagged/sanctioned Entity Resolution watchlist drawn from the
        real flagged CORD sources (OFAC + OpenSanctions, US forced-labor, ICIJ
        offshore leaks, risk data) PLUS the T-Data flag sources CBP-EAPA (A1)
        and UFLPA-ENTITY-LIST (A2). Identity-only sources (A3, NPI-PROVIDERS /
        GLOBALDATA) are always excluded. Shown before any search.

        The list is balanced so no single source floods it: each flagged source
        is capped at a fair per-source share (``ceil(limit / num_sources)``) and
        the sources are interleaved so the watchlist shows a MIX of CBP-EAPA,
        UFLPA-ENTITY-LIST, OFAC, OPEN-SANCTIONS, US-LABOR-VIOLATIONS, ICIJ and
        NOMINO-RISK."""
        import math

        # Buckets keyed by source, each holding already-shaped watchlist rows.
        # A1/A2 overlay flag sources (in-memory CordFlagRecords) ...
        buckets: "Dict[str, List[Dict]]" = {}
        order: List[str] = []

        def _register(src: str, rows: List[Dict]) -> None:
            if rows:
                buckets[src] = rows
                order.append(src)

        _register(EAPA_SOURCE, [self._flag_record_to_watchlist(r, EAPA_FLAG) for r in self._eapa_records])
        _register(UFLPA_SOURCE, [self._flag_record_to_watchlist(r, UFLPA_FLAG) for r in self._uflpa_records])

        # ... plus the FTS-indexed flagged sources.
        # A3: never surface identity-only sources, even if listed.
        fts_sources = [
            (src, flag) for (src, flag) in self.WATCHLIST_SOURCES
            if not self.is_identity_only(src)
        ]
        num_sources = len(order) + len(fts_sources)
        if num_sources == 0:
            return []
        # Fair per-source share so no single source (e.g. the 65 CBP-EAPA rows)
        # floods the default-limit list.
        per_source = max(1, math.ceil(limit / num_sources))

        # Trim the already-shaped overlay buckets to their fair share.
        for src in order:
            buckets[src] = [r for r in buckets[src] if r.get("name")][:per_source]

        # Pull the fair share from each FTS source.
        if fts_sources:
            conn = sqlite3.connect(self.index_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            try:
                for src, flag in fts_sources:
                    cursor.execute(
                        "SELECT record_id, data_source, name_primary, country, ofac_program, sanctions_topic, raw_json "
                        "FROM cord_fts WHERE data_source = ? LIMIT ?",
                        (src, per_source * 4),
                    )
                    rows: List[Dict] = []
                    for row in cursor.fetchall():
                        if len(rows) >= per_source:
                            break
                        name = row["name_primary"]
                        country = row["country"]
                        if not name or not country:
                            try:
                                raw = json.loads(row["raw_json"])
                            except Exception:
                                raw = {}
                            name = name or self._name_from_raw(raw)
                            country = country or self._country_from_raw(raw)
                        if not name:
                            continue
                        rows.append({
                            "entity_id": f"{row['data_source']}:{row['record_id']}",
                            "name": name,
                            "country": (country or "").upper(),
                            "data_source": row["data_source"],
                            "flag": flag,
                            "program": row["ofac_program"] or row["sanctions_topic"] or None,
                        })
                    _register(src, rows)
            finally:
                conn.close()

        # Interleave: round-robin across the source buckets so the watchlist
        # opens on a MIX of sources rather than a single source's block.
        out: List[Dict] = []
        idx = 0
        while len(out) < limit:
            progressed = False
            for src in order:
                bucket = buckets.get(src) or []
                if idx < len(bucket):
                    out.append(bucket[idx])
                    progressed = True
                    if len(out) >= limit:
                        break
            if not progressed:
                break
            idx += 1
        return out[:limit]

    # ----------------------------------------------------------------------
    # Overlay entity resolution — fallback for overlay-source entity_ids.
    # ----------------------------------------------------------------------
    def get_overlay_entity(self, entity_id: str) -> Optional[Dict]:
        """Resolve an overlay-source entity_id to an entity-detail-shaped dict.

        Overlay entity_ids are the watchlist ``entity_id`` values for the T-Data
        flag sources, i.e. prefixed ``CBP-EAPA:`` (A1) or ``UFLPA-ENTITY-LIST:``
        (A2). main.py calls this as a fallback when the CORD service 404s, which
        fixes the workspace "unknown entity" for EAPA/UFLPA actors.

        Returns ``{"entity": {...}}`` (matching the /entity proxy shape the UI
        unwraps) or ``None`` for non-overlay ids."""
        if not entity_id or ":" not in entity_id:
            return None
        src, _, record_id = entity_id.partition(":")
        src = src.strip()
        record_id = record_id.strip()
        if src == EAPA_SOURCE:
            records = self._eapa_records
        elif src == UFLPA_SOURCE:
            records = self._uflpa_records
        else:
            return None
        rec = next((r for r in records if str(r.get("RECORD_ID")) == record_id), None)
        if rec is None:
            return None
        return {
            "entity": {
                "entity_id": entity_id,
                "data_source": src,
                "record_id": record_id,
                "name": rec.get("PRIMARY_NAME_ORG") or "",
                "country": (rec.get("COUNTRY") or "").upper(),
                "entity_type": "organization",
                "confidence": 1.0,
                "raw_data": {
                    "FLAG": rec.get("FLAG") or "",
                    "DOCKET": rec.get("DOCKET") or "",
                    "COMMODITY": rec.get("COMMODITY") or "",
                    "ROUTE": rec.get("ROUTE") or "",
                },
            }
        }

    def build_senzing_subset(self, entities_to_search: List[Tuple[str, str]]) -> List[Dict]:
        """
        Build a subset of ~20 CORD records to load into Senzing SDK.

        Args:
            entities_to_search: List of (name, country) tuples from manifest

        Returns:
            List of Senzing-formatted records (max 20)
        """
        subset = []
        seen_ids = set()

        for entity_name, entity_country in entities_to_search:
            if not entity_name:
                continue

            matches = self.search(entity_name, country=entity_country, limit=5)
            for match in matches:
                record_id = match["record_id"]
                if record_id not in seen_ids and len(subset) < 20:
                    subset.append(
                        {"DATA_SOURCE": match["data_source"], "RECORD_ID": record_id, "raw_record": match["raw_json"]}
                    )
                    seen_ids.add(record_id)

        logger.info(f"Built Senzing subset: {len(subset)} records from {len(entities_to_search)} search queries")
        return subset

    def get_entity_count(self) -> int:
        """Get total number of indexed entities."""
        conn = sqlite3.connect(self.index_path)
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT COUNT(*) FROM cord_fts")
            count = cursor.fetchone()[0]
            return count
        finally:
            conn.close()


# Singleton instance
_cord_engine = None


def get_cord_engine() -> CORDEngine:
    """Get or create singleton CORD engine instance."""
    global _cord_engine
    if _cord_engine is None:
        cord_data_dir = os.getenv("CORD_DATA_DIR", "/app/cord-data")
        _cord_engine = CORDEngine(cord_data_dir)
    return _cord_engine
