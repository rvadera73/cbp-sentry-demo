"""CORD FTS Index Engine — Search 244K entities efficiently without eval limits."""

import sqlite3
import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


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
