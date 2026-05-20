"""SQLite database initialization and CRUD operations"""
import sqlite3
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)


def init_db(db_path: str = "/app/data/cbp_sentry.db") -> None:
    """Initialize SQLite schema with idempotent migrations"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Shipments table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS shipments (
            id TEXT PRIMARY KEY,
            manifest_id TEXT NOT NULL,
            shipper_name TEXT NOT NULL,
            consignee_name TEXT NOT NULL,
            origin_country TEXT NOT NULL,
            destination_country TEXT NOT NULL,
            hs_code TEXT,
            declared_value_usd REAL,
            declared_weight_kg REAL,
            description TEXT,
            vessel_name TEXT,
            vessel_imo TEXT,
            vessel_flag TEXT,
            dwell_days REAL,
            ais_stuffing_country TEXT,
            port_calls TEXT,
            element9_is_mismatch INTEGER DEFAULT 0,
            element9_confidence REAL,
            element9_declared_country TEXT,
            element9_actual_country TEXT,
            shipper_age_months INTEGER,
            shipper_country TEXT,
            consignee_country TEXT,
            ad_cvd_rate REAL,
            ad_cvd_applicable INTEGER DEFAULT 0,
            status TEXT DEFAULT 'received',
            risk_score REAL,
            risk_delta REAL DEFAULT 0,
            h1_score REAL,
            h2_score REAL,
            h3_score REAL,
            h1_h2_score REAL,
            last_polled_at TIMESTAMP,
            ofac_screened_at TIMESTAMP,
            ofac_match BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP
        )
    """)

    # Manifests table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS manifests (
            id TEXT PRIMARY KEY,
            filename TEXT NOT NULL,
            row_count INTEGER,
            extracted_at TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Scores table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scores (
            id TEXT PRIMARY KEY,
            shipment_id TEXT NOT NULL,
            h1_score REAL,
            h2_score REAL,
            h1_h2_score REAL,
            total_score REAL,
            components TEXT,
            xai_assertions TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (shipment_id) REFERENCES shipments(id)
        )
    """)

    # Idempotent column additions for new schema fields
    cursor.execute("PRAGMA table_info(shipments)")
    columns = {row[1] for row in cursor.fetchall()}

    if "last_polled_at" not in columns:
        cursor.execute("ALTER TABLE shipments ADD COLUMN last_polled_at TIMESTAMP")
        logger.info("Added last_polled_at column to shipments")

    if "risk_delta" not in columns:
        cursor.execute("ALTER TABLE shipments ADD COLUMN risk_delta REAL DEFAULT 0")
        logger.info("Added risk_delta column to shipments")

    if "ofac_screened_at" not in columns:
        cursor.execute("ALTER TABLE shipments ADD COLUMN ofac_screened_at TIMESTAMP")
        logger.info("Added ofac_screened_at column to shipments")

    if "ofac_match" not in columns:
        cursor.execute("ALTER TABLE shipments ADD COLUMN ofac_match BOOLEAN DEFAULT 0")
        logger.info("Added ofac_match column to shipments")

    # Weight Configuration table (for three-level scoring)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS weight_configurations (
            id TEXT PRIMARY KEY,
            corridor TEXT,
            w_corridor REAL NOT NULL,
            w_vessel REAL NOT NULL,
            w_manifest REAL NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP,
            created_by TEXT NOT NULL,
            notes TEXT
        )
    """)

    # Scoring Overrides table (analyst feedback)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scoring_overrides (
            id TEXT PRIMARY KEY,
            shipment_id TEXT NOT NULL,
            original_score REAL NOT NULL,
            override_decision TEXT NOT NULL,
            feedback_type TEXT,
            analyst_id TEXT NOT NULL,
            analyst_name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            notes TEXT,
            FOREIGN KEY (shipment_id) REFERENCES shipments(id)
        )
    """)

    # Weight Suggestions table (AI suggestions for weight adjustments)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS weight_suggestions (
            id TEXT PRIMARY KEY,
            corridor TEXT,
            affected_feature TEXT NOT NULL,
            suggested_value REAL NOT NULL,
            confidence_pct REAL NOT NULL,
            corroboration_count INTEGER NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            reviewed_at TIMESTAMP,
            reviewed_by TEXT,
            rationale TEXT NOT NULL
        )
    """)

    # Idempotent migrations: add new columns if they don't exist
    # This allows running init_db on an existing database without errors
    migrations = [
        "ALTER TABLE shipments ADD COLUMN vessel_imo TEXT",
        "ALTER TABLE shipments ADD COLUMN vessel_flag TEXT",
        "ALTER TABLE shipments ADD COLUMN dwell_days REAL",
        "ALTER TABLE shipments ADD COLUMN ais_stuffing_country TEXT",
        "ALTER TABLE shipments ADD COLUMN port_calls TEXT",
        "ALTER TABLE shipments ADD COLUMN element9_is_mismatch INTEGER DEFAULT 0",
        "ALTER TABLE shipments ADD COLUMN element9_confidence REAL",
        "ALTER TABLE shipments ADD COLUMN element9_declared_country TEXT",
        "ALTER TABLE shipments ADD COLUMN element9_actual_country TEXT",
        "ALTER TABLE shipments ADD COLUMN shipper_age_months INTEGER",
        "ALTER TABLE shipments ADD COLUMN shipper_country TEXT",
        "ALTER TABLE shipments ADD COLUMN consignee_country TEXT",
        "ALTER TABLE shipments ADD COLUMN ad_cvd_rate REAL",
        "ALTER TABLE shipments ADD COLUMN ad_cvd_applicable INTEGER DEFAULT 0",
        "ALTER TABLE shipments ADD COLUMN h3_score REAL",
    ]

    for migration in migrations:
        try:
            cursor.execute(migration)
            logger.info(f"Migration executed: {migration}")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                logger.debug(f"Column already exists, skipping: {migration}")
            else:
                logger.error(f"Migration failed: {migration} — {e}")
                raise

    conn.commit()
    conn.close()


def create_shipment(
    manifest_id: str,
    shipper_name: str,
    consignee_name: str,
    origin_country: str,
    destination_country: str,
    hs_code: str,
    declared_value_usd: float,
    declared_weight_kg: float,
    description: Optional[str] = None,
    vessel_name: Optional[str] = None,
    db_path: str = "/app/data/cbp_sentry.db"
) -> str:
    """Create a new shipment record, return ID"""
    shipment_id = str(uuid.uuid4())
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO shipments
        (id, manifest_id, shipper_name, consignee_name, origin_country, destination_country,
         hs_code, declared_value_usd, declared_weight_kg, description, vessel_name, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (shipment_id, manifest_id, shipper_name, consignee_name, origin_country,
          destination_country, hs_code, declared_value_usd, declared_weight_kg,
          description, vessel_name, datetime.utcnow().isoformat()))

    conn.commit()
    conn.close()
    return shipment_id


def create_manifest(
    filename: str,
    row_count: int,
    extracted_at: str,
    db_path: str = "/app/data/cbp_sentry.db"
) -> str:
    """Create a new manifest record, return ID"""
    manifest_id = str(uuid.uuid4())
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO manifests (id, filename, row_count, extracted_at, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (manifest_id, filename, row_count, extracted_at, datetime.utcnow().isoformat()))

    conn.commit()
    conn.close()
    return manifest_id


def get_shipment(shipment_id: str, db_path: str = "/app/data/cbp_sentry.db") -> Optional[Dict[str, Any]]:
    """Fetch a single shipment by ID"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM shipments WHERE id = ?", (shipment_id,))
    row = cursor.fetchone()
    conn.close()

    return dict(row) if row else None


def get_all_shipments(
    limit: int = 100,
    offset: int = 0,
    status: Optional[str] = None,
    db_path: str = "/app/data/cbp_sentry.db"
) -> List[Dict[str, Any]]:
    """Fetch all shipments with optional filtering"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    if status:
        cursor.execute(
            "SELECT * FROM shipments WHERE status = ? AND id LIKE 'SHP-%' ORDER BY COALESCE(risk_score, 0) DESC LIMIT ? OFFSET ?",
            (status, limit, offset)
        )
    else:
        # Prioritize manifest records (SHP-*) and sort by risk score descending
        cursor.execute("SELECT * FROM shipments WHERE id LIKE 'SHP-%' ORDER BY COALESCE(risk_score, 0) DESC LIMIT ? OFFSET ?", (limit, offset))

    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def update_shipment(shipment_id: str, updates: Dict[str, Any], db_path: str = "/app/data/cbp_sentry.db") -> bool:
    """Update shipment fields"""
    if not updates:
        return True

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Build dynamic UPDATE query
    set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
    values = list(updates.values()) + [shipment_id]

    cursor.execute(f"UPDATE shipments SET {set_clause}, updated_at = ? WHERE id = ?",
                   values[:-1] + [datetime.utcnow().isoformat(), shipment_id])

    conn.commit()
    conn.close()
    return cursor.rowcount > 0


def get_shipments_stats(db_path: str = "/app/data/cbp_sentry.db") -> Dict[str, Any]:
    """Get dashboard statistics"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) as total FROM shipments")
    total = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM shipments WHERE risk_score >= 80")
    high_risk = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM shipments WHERE risk_score >= 50 AND risk_score < 80")
    medium_risk = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM shipments WHERE risk_score < 50")
    low_risk = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM shipments WHERE ofac_match = 1")
    ofac_matches = cursor.fetchone()[0]

    conn.close()

    return {
        "total_shipments": total,
        "high_risk": high_risk,
        "medium_risk": medium_risk,
        "low_risk": low_risk,
        "ofac_matches": ofac_matches
    }


def search_shipments(
    query: str,
    limit: int = 50,
    db_path: str = "/app/data/cbp_sentry.db"
) -> List[Dict[str, Any]]:
    """Search shipments by shipper/consignee name"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    search_term = f"%{query}%"
    cursor.execute("""
        SELECT * FROM shipments
        WHERE shipper_name LIKE ? OR consignee_name LIKE ? OR hs_code LIKE ?
        ORDER BY created_at DESC LIMIT ?
    """, (search_term, search_term, search_term, limit))

    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]
