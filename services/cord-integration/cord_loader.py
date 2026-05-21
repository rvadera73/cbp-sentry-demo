"""CORD Data Loader - Load 244K entities from JSONL into Senzing engine."""
import os
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
import sqlite3

logger = logging.getLogger(__name__)


class CORDDataLoader:
    """Load and index CORD JSONL data into Senzing engine."""

    def __init__(self, cord_data_dir: str = "/app/cord-data", db_path: str = "/app/data/senzing.db"):
        """Initialize CORD data loader.

        Args:
            cord_data_dir: Directory containing CORD JSONL files
            db_path: Path to Senzing SQLite database
        """
        self.cord_data_dir = cord_data_dir
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        self.entity_count = 0

    def load_all_entities(self) -> Dict[str, Any]:
        """Load all CORD entities from JSONL files into Senzing.

        Returns:
            Dict with load statistics (total_records, failed_records, etc.)
        """
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.cursor = self.conn.cursor()

            # Ensure tables exist before loading
            self._ensure_schema()

            cord_dir = Path(self.cord_data_dir)
            if not cord_dir.exists():
                logger.warning(f"CORD data directory not found: {cord_dir}")
                return {"status": "failed", "reason": "directory_not_found"}

            jsonl_files = sorted(cord_dir.glob("*.jsonl"))
            logger.info(f"Found {len(jsonl_files)} JSONL files in {cord_dir}")

            total_records = 0
            failed_records = 0
            sources_count = {}

            for jsonl_file in jsonl_files:
                logger.info(f"Loading {jsonl_file.name}...")

                try:
                    with open(jsonl_file, 'r', encoding='utf-8') as f:
                        batch = []
                        batch_size = 500

                        for line_num, line in enumerate(f, 1):
                            if not line.strip():
                                continue

                            try:
                                record = json.loads(line)
                                batch.append(record)
                                total_records += 1

                                # Log progress every 1000 records
                                if total_records % 1000 == 0:
                                    logger.info(f"  Processed {total_records:,} records")

                                # Batch insert when batch size reached
                                if len(batch) >= batch_size:
                                    self._batch_insert(batch, sources_count)
                                    batch = []

                            except json.JSONDecodeError as e:
                                logger.warning(f"  Line {line_num}: Malformed JSON, skipping")
                                failed_records += 1
                                continue

                        # Insert remaining records
                        if batch:
                            self._batch_insert(batch, sources_count)

                except Exception as e:
                    logger.error(f"Error loading {jsonl_file.name}: {e}")
                    continue

            self.conn.commit()
            self.conn.close()

            return {
                "status": "success",
                "total_records": total_records,
                "failed_records": failed_records,
                "successful_records": total_records - failed_records,
                "sources": sources_count,
                "entity_count": self.entity_count
            }

        except Exception as e:
            logger.error(f"Load all entities failed: {e}")
            if self.conn:
                self.conn.close()
            return {
                "status": "failed",
                "reason": str(e)
            }

    def _batch_insert(self, records: List[Dict[str, Any]], sources_count: Dict[str, int]):
        """Batch insert records into Senzing database.

        Args:
            records: List of CORD records to insert
            sources_count: Dict tracking counts by data source
        """
        try:
            for record in records:
                entity_id = self._generate_entity_id(record)
                data_source = record.get("DATA_SOURCE", "CORD")
                record_id = record.get("RECORD_ID", entity_id)

                # Extract name
                name = self._extract_name(record)

                # Extract country
                country = self._extract_country(record)

                # Extract entity type
                entity_type = self._extract_entity_type(record)

                # Set confidence
                confidence = self._extract_confidence(record)

                # Insert into database
                self.cursor.execute("""
                    INSERT OR REPLACE INTO senzing_entities
                    (entity_id, data_source, record_id, name_primary, country, entity_type, confidence, raw_data)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    entity_id,
                    data_source,
                    record_id,
                    name,
                    country,
                    entity_type,
                    confidence,
                    json.dumps(record)
                ))

                self.entity_count += 1
                sources_count[data_source] = sources_count.get(data_source, 0) + 1

        except Exception as e:
            logger.error(f"Batch insert failed: {e}")
            raise

    def _generate_entity_id(self, record: Dict[str, Any]) -> str:
        """Generate unique entity ID from CORD record."""
        data_source = record.get("DATA_SOURCE", "CORD")
        record_id = record.get("RECORD_ID", "")

        if data_source and record_id:
            return f"{data_source}:{record_id}"
        return f"CORD:{record_id}"

    def _extract_name(self, record: Dict[str, Any]) -> str:
        """Extract primary name from CORD record based on data source."""
        data_source = record.get("DATA_SOURCE", "")

        if data_source == "GLEIF":
            names = record.get("NAMES", [])
            for name_obj in names:
                if name_obj.get("NAME_TYPE") == "PRIMARY":
                    return name_obj.get("NAME_ORG", "")

        elif data_source == "OFAC":
            name_list = record.get("NAME_LIST", [])
            for name_obj in name_list:
                if name_obj.get("NAME_TYPE") == "PRIMARY":
                    return name_obj.get("NAME_ORG", "")

        else:
            # Generic extraction
            return record.get("NAME", record.get("name", ""))

        return ""

    def _extract_country(self, record: Dict[str, Any]) -> str:
        """Extract country from CORD record based on data source."""
        data_source = record.get("DATA_SOURCE", "")

        if data_source == "GLEIF":
            countries = record.get("COUNTRIES", [])
            if countries:
                return countries[0].get("REGISTRATION_COUNTRY", "")

        # Generic extraction
        return record.get("COUNTRY_CODE", record.get("country", ""))

    def _extract_entity_type(self, record: Dict[str, Any]) -> str:
        """Extract entity type from CORD record."""
        record_type = record.get("RECORD_TYPE", "ORGANIZATION")
        return record_type.lower() if record_type else "organization"

    def _extract_confidence(self, record: Dict[str, Any]) -> float:
        """Extract or derive confidence score from CORD record."""
        # Default confidence
        confidence = 1.0

        # If OFAC record, slightly lower confidence due to SDN variation
        if record.get("DATA_SOURCE") == "OFAC":
            confidence = 0.95

        # If matches indicate low match quality, lower confidence
        if record.get("MATCH_TYPE") == "PARTIAL":
            confidence = 0.75

        return confidence

    def _ensure_schema(self):
        """Ensure database schema exists (idempotent)."""
        try:
            # Create tables for entities and relationships
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS senzing_entities (
                    entity_id TEXT PRIMARY KEY,
                    data_source TEXT,
                    record_id TEXT,
                    name_primary TEXT,
                    country TEXT,
                    entity_type TEXT,
                    confidence REAL DEFAULT 1.0,
                    raw_data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS senzing_relationships (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entity_id_a TEXT,
                    entity_id_b TEXT,
                    relationship_type TEXT,
                    confidence REAL DEFAULT 1.0,
                    evidence TEXT,
                    FOREIGN KEY(entity_id_a) REFERENCES senzing_entities(entity_id),
                    FOREIGN KEY(entity_id_b) REFERENCES senzing_entities(entity_id)
                )
            """)

            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS cbp_shipments (
                    id TEXT PRIMARY KEY,
                    shipper_id TEXT,
                    shipper_name TEXT,
                    consignee_name TEXT,
                    shipper_age_months INTEGER,
                    ad_cvd_rate REAL,
                    risk_score REAL,
                    element9_declared_country TEXT,
                    element9_actual_country TEXT,
                    confidence REAL DEFAULT 1.0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            self.conn.commit()
            logger.info("✓ Database schema ready")

        except Exception as e:
            logger.error(f"Failed to ensure schema: {e}")
            raise


def load_cord_data_async(
    cord_data_dir: str = "/app/cord-data",
    db_path: str = "/app/data/senzing.db"
) -> Dict[str, Any]:
    """Load CORD data synchronously (called from async context).

    This is a blocking operation that should only be called during startup.

    Args:
        cord_data_dir: Directory containing CORD JSONL files
        db_path: Path to Senzing SQLite database

    Returns:
        Dict with load results
    """
    loader = CORDDataLoader(cord_data_dir, db_path)
    return loader.load_all_entities()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Run loader
    result = load_cord_data_async()
    print(json.dumps(result, indent=2))
