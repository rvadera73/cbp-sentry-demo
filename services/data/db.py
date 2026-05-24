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

    # Corridor definitions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS corridors (
            id TEXT PRIMARY KEY,
            display_name TEXT,
            origin_country TEXT,
            destination_country TEXT,
            risk_level TEXT DEFAULT 'MEDIUM',
            primary_hs_chapters TEXT,
            risk_profile TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_refreshed_at TIMESTAMP
        )
    """)

    # Corridor duties table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS corridor_duties (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            corridor_id TEXT REFERENCES corridors(id),
            case_number TEXT,
            duty_type TEXT,
            product_description TEXT,
            hs_prefix TEXT,
            rate_pct REAL,
            status TEXT DEFAULT 'ACTIVE',
            source_url TEXT,
            last_refreshed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Corridor enforcement actions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS corridor_enforcement_actions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            corridor_id TEXT REFERENCES corridors(id),
            case_id TEXT,
            entity_name TEXT,
            case_status TEXT,
            case_year INTEGER,
            duty_evaded_usd REAL,
            source_description TEXT,
            source_url TEXT,
            last_refreshed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Pre-manifest vessels table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pre_manifest_vessels (
            vessel_imo TEXT PRIMARY KEY,
            vessel_name TEXT,
            mmsi TEXT,
            flag_state TEXT,
            origin_port TEXT,
            origin_country TEXT,
            destination_port TEXT,
            destination_country TEXT,
            corridor_id TEXT,
            eta_us TIMESTAMP,
            ais_status TEXT,
            current_lat REAL,
            current_lon REAL,
            speed_knots REAL,
            last_refreshed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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


def get_shipments_count(status: Optional[str] = None, db_path: str = "/app/data/cbp_sentry.db") -> int:
    """Get total count of manifest shipments (SHP-*)"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    if status:
        cursor.execute("SELECT COUNT(*) FROM shipments WHERE status = ? AND id LIKE 'SHP-%'", (status,))
    else:
        cursor.execute("SELECT COUNT(*) FROM shipments WHERE id LIKE 'SHP-%'")

    count = cursor.fetchone()[0]
    conn.close()
    return count


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


def get_corridors(db_path: str = "/app/data/cbp_sentry.db") -> List[Dict[str, Any]]:
    """Fetch all corridors with computed shipment statistics"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM corridors ORDER BY risk_level DESC, id ASC")
    corridors = [dict(row) for row in cursor.fetchall()]

    # Compute stats for each corridor
    for corridor in corridors:
        origin = corridor["origin_country"]
        dest = corridor["destination_country"]

        cursor.execute("""
            SELECT
                COUNT(*) as shipment_count,
                AVG(risk_score) as avg_risk_score,
                COUNT(CASE WHEN element9_is_mismatch = 1 THEN 1 END) as mismatch_count,
                AVG(shipper_age_months) as avg_shipper_age,
                COUNT(DISTINCT shipper_name) as unique_shippers
            FROM shipments
            WHERE origin_country = ? AND destination_country = ?
        """, (origin, dest))

        stats = cursor.fetchone()
        if stats:
            total = stats["shipment_count"]
            mismatch_rate = (stats["mismatch_count"] / total * 100) if total > 0 else 0
            corridor["computed_stats"] = {
                "shipment_count": total,
                "avg_risk_score": round(stats["avg_risk_score"], 2) if stats["avg_risk_score"] else 0,
                "element9_mismatch_rate_pct": round(mismatch_rate, 1),
                "avg_shipper_age_months": round(stats["avg_shipper_age"], 1) if stats["avg_shipper_age"] else 0,
                "unique_shippers": stats["unique_shippers"] or 0,
            }
        else:
            corridor["computed_stats"] = {
                "shipment_count": 0,
                "avg_risk_score": 0,
                "element9_mismatch_rate_pct": 0,
                "avg_shipper_age_months": 0,
                "unique_shippers": 0,
            }

    conn.close()
    return corridors


def get_corridor_detail(corridor_id: str, db_path: str = "/app/data/cbp_sentry.db") -> Optional[Dict[str, Any]]:
    """Fetch single corridor with duties, enforcement actions, and shipment statistics"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM corridors WHERE id = ?", (corridor_id,))
    corridor = cursor.fetchone()
    if not corridor:
        conn.close()
        return None

    corridor = dict(corridor)

    # Get duties
    cursor.execute("SELECT * FROM corridor_duties WHERE corridor_id = ? AND status = 'ACTIVE'", (corridor_id,))
    corridor["duties"] = [dict(row) for row in cursor.fetchall()]

    # Get enforcement actions
    cursor.execute("SELECT * FROM corridor_enforcement_actions WHERE corridor_id = ?", (corridor_id,))
    corridor["enforcement_actions"] = [dict(row) for row in cursor.fetchall()]

    # Compute pattern stats from shipments
    origin = corridor["origin_country"]
    dest = corridor["destination_country"]

    cursor.execute("""
        SELECT
            COUNT(*) as shipment_count,
            AVG(risk_score) as avg_risk_score,
            COUNT(CASE WHEN element9_is_mismatch = 1 THEN 1 END) as mismatch_count,
            AVG(shipper_age_months) as avg_shipper_age,
            COUNT(DISTINCT shipper_name) as unique_shippers,
            SUM(declared_value_usd) as total_value_usd
        FROM shipments
        WHERE origin_country = ? AND destination_country = ?
    """, (origin, dest))

    stats = cursor.fetchone()
    if stats:
        total = stats["shipment_count"]
        mismatch_rate = (stats["mismatch_count"] / total * 100) if total > 0 else 0
        corridor["pattern_indicators"] = {
            "shipment_count": total,
            "avg_risk_score": round(stats["avg_risk_score"], 2) if stats["avg_risk_score"] else 0,
            "element9_mismatch_rate_pct": round(mismatch_rate, 1),
            "avg_shipper_age_months": round(stats["avg_shipper_age"], 1) if stats["avg_shipper_age"] else 0,
            "unique_shippers": stats["unique_shippers"] or 0,
            "total_value_usd": int(stats["total_value_usd"]) if stats["total_value_usd"] else 0,
        }
    else:
        corridor["pattern_indicators"] = {}

    conn.close()
    return corridor


def create_or_update_corridor(
    corridor_id: str,
    display_name: str,
    origin_country: str,
    destination_country: str,
    risk_level: str = "MEDIUM",
    primary_hs_chapters: Optional[str] = None,
    risk_profile: Optional[str] = None,
    db_path: str = "/app/data/cbp_sentry.db"
) -> bool:
    """Create or update a corridor"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT OR REPLACE INTO corridors
        (id, display_name, origin_country, destination_country, risk_level, primary_hs_chapters, risk_profile, last_refreshed_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (corridor_id, display_name, origin_country, destination_country, risk_level, primary_hs_chapters, risk_profile, datetime.utcnow().isoformat()))

    conn.commit()
    conn.close()
    return True


def create_corridor_duty(
    corridor_id: str,
    case_number: str,
    duty_type: str,
    product_description: Optional[str] = None,
    hs_prefix: Optional[str] = None,
    rate_pct: Optional[float] = None,
    status: str = "ACTIVE",
    source_url: Optional[str] = None,
    db_path: str = "/app/data/cbp_sentry.db"
) -> int:
    """Create a corridor duty record"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO corridor_duties
        (corridor_id, case_number, duty_type, product_description, hs_prefix, rate_pct, status, source_url, last_refreshed_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (corridor_id, case_number, duty_type, product_description, hs_prefix, rate_pct, status, source_url, datetime.utcnow().isoformat()))

    duty_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return duty_id


def create_enforcement_action(
    corridor_id: str,
    case_id: str,
    entity_name: str,
    case_status: str,
    case_year: int,
    duty_evaded_usd: Optional[float] = None,
    source_description: Optional[str] = None,
    source_url: Optional[str] = None,
    db_path: str = "/app/data/cbp_sentry.db"
) -> int:
    """Create a corridor enforcement action record"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO corridor_enforcement_actions
        (corridor_id, case_id, entity_name, case_status, case_year, duty_evaded_usd, source_description, source_url, last_refreshed_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (corridor_id, case_id, entity_name, case_status, case_year, duty_evaded_usd, source_description, source_url, datetime.utcnow().isoformat()))

    action_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return action_id


def get_pre_manifest_vessels(db_path: str = "/app/data/cbp_sentry.db") -> List[Dict[str, Any]]:
    """Fetch all pre-manifest vessels"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM pre_manifest_vessels
        WHERE destination_country = 'US'
        ORDER BY last_refreshed_at DESC
    """)

    vessels = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return vessels


def create_or_update_pre_manifest_vessel(
    vessel_imo: str,
    vessel_name: str,
    mmsi: Optional[str] = None,
    flag_state: Optional[str] = None,
    origin_port: Optional[str] = None,
    origin_country: Optional[str] = None,
    destination_port: Optional[str] = None,
    destination_country: Optional[str] = None,
    corridor_id: Optional[str] = None,
    eta_us: Optional[str] = None,
    ais_status: Optional[str] = None,
    current_lat: Optional[float] = None,
    current_lon: Optional[float] = None,
    speed_knots: Optional[float] = None,
    db_path: str = "/app/data/cbp_sentry.db"
) -> bool:
    """Create or update a pre-manifest vessel"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT OR REPLACE INTO pre_manifest_vessels
        (vessel_imo, vessel_name, mmsi, flag_state, origin_port, origin_country, destination_port, destination_country,
         corridor_id, eta_us, ais_status, current_lat, current_lon, speed_knots, last_refreshed_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (vessel_imo, vessel_name, mmsi, flag_state, origin_port, origin_country, destination_port, destination_country,
          corridor_id, eta_us, ais_status, current_lat, current_lon, speed_knots, datetime.utcnow().isoformat()))

    conn.commit()
    conn.close()
    return True
