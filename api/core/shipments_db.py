"""
Shipments database initialization and queries
"""
import sqlite3
import json
from pathlib import Path
from seed_data.shipments_seed import SHIPMENTS

DB_PATH = Path(__file__).parent.parent / "cbp_sentry.db"

def init_shipments_db():
    """Initialize shipments table and load seed data"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Create table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS shipments (
            id INTEGER PRIMARY KEY,
            manifest_id TEXT UNIQUE NOT NULL,
            shipper_name TEXT NOT NULL,
            shipper_country TEXT,
            shipper_city TEXT,
            shipper_lat REAL,
            shipper_lon REAL,
            consignee_name TEXT NOT NULL,
            consignee_country TEXT,
            consignee_city TEXT,
            consignee_lat REAL,
            consignee_lon REAL,
            commodity_code TEXT,
            commodity_name TEXT,
            declared_value INTEGER,
            risk_score INTEGER,
            h1_risk_level TEXT,
            h2_signals TEXT,
            h3_recommendation TEXT,
            status TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create indices
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_risk_score ON shipments(risk_score DESC)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_status ON shipments(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_shipper_country ON shipments(shipper_country)")

    # Check if already loaded
    cursor.execute("SELECT COUNT(*) FROM shipments")
    count = cursor.fetchone()[0]

    if count == 0:
        # Load seed data
        for shipment in SHIPMENTS:
            cursor.execute("""
                INSERT INTO shipments (
                    id, manifest_id, shipper_name, shipper_country, shipper_city,
                    shipper_lat, shipper_lon, consignee_name, consignee_country, consignee_city,
                    consignee_lat, consignee_lon, commodity_code, commodity_name,
                    declared_value, risk_score, h1_risk_level, h2_signals, h3_recommendation, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                shipment["id"],
                shipment["manifest_id"],
                shipment["shipper_name"],
                shipment["shipper_country"],
                shipment["shipper_city"],
                shipment["shipper_lat"],
                shipment["shipper_lon"],
                shipment["consignee_name"],
                shipment["consignee_country"],
                shipment["consignee_city"],
                shipment["consignee_lat"],
                shipment["consignee_lon"],
                shipment["commodity_code"],
                shipment["commodity_name"],
                shipment["declared_value"],
                shipment["risk_score"],
                shipment["h1_risk_level"],
                json.dumps(shipment["h2_signals"]),
                shipment["h3_recommendation"],
                shipment["status"],
            ))
        conn.commit()

    conn.close()


def get_all_shipments(limit: int = 15, offset: int = 0):
    """Get all shipments with pagination"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM shipments")
    total = cursor.fetchone()[0]

    cursor.execute("""
        SELECT * FROM shipments
        ORDER BY risk_score DESC
        LIMIT ? OFFSET ?
    """, (limit, offset))

    rows = cursor.fetchall()
    conn.close()

    shipments = []
    for row in rows:
        shipment = dict(row)
        shipment["h2_signals"] = json.loads(shipment["h2_signals"])
        shipments.append(shipment)

    return {"total": total, "limit": limit, "offset": offset, "shipments": shipments}


def get_shipment_by_id(shipment_id: int):
    """Get single shipment detail"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM shipments WHERE id = ?", (shipment_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    shipment = dict(row)
    shipment["h2_signals"] = json.loads(shipment["h2_signals"])
    return shipment


def search_shipments(
    origin: str = None,
    destination: str = None,
    risk_min: int = None,
    risk_max: int = None,
    status: str = None,
    limit: int = 15,
):
    """Search shipments with filters"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    query = "SELECT * FROM shipments WHERE 1=1"
    params = []

    if origin:
        query += " AND shipper_country = ?"
        params.append(origin)
    if destination:
        query += " AND consignee_country = ?"
        params.append(destination)
    if risk_min is not None:
        query += " AND risk_score >= ?"
        params.append(risk_min)
    if risk_max is not None:
        query += " AND risk_score <= ?"
        params.append(risk_max)
    if status:
        query += " AND status = ?"
        params.append(status)

    query += " ORDER BY risk_score DESC LIMIT ?"
    params.append(limit)

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    shipments = []
    for row in rows:
        shipment = dict(row)
        shipment["h2_signals"] = json.loads(shipment["h2_signals"])
        shipments.append(shipment)

    return shipments


def get_shipments_map_data():
    """Get shipment coordinates for map visualization"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id, manifest_id, shipper_name, shipper_lat, shipper_lon,
            consignee_name, consignee_lat, consignee_lon, risk_score, status
        FROM shipments
        ORDER BY risk_score DESC
    """)

    rows = cursor.fetchall()
    conn.close()

    routes = []
    for row in rows:
        routes.append({
            "id": row["id"],
            "manifestId": row["manifest_id"],
            "shipperName": row["shipper_name"],
            "from": {"lat": row["shipper_lat"], "lon": row["shipper_lon"]},
            "consigneeName": row["consignee_name"],
            "to": {"lat": row["consignee_lat"], "lon": row["consignee_lon"]},
            "riskScore": row["risk_score"],
            "status": row["status"],
        })

    return {"routes": routes}


def get_shipments_stats():
    """Get dashboard statistics"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM shipments")
    total = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM shipments WHERE risk_score >= 80")
    high_risk = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM shipments WHERE risk_score BETWEEN 40 AND 79")
    medium_risk = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM shipments WHERE risk_score < 40")
    low_risk = cursor.fetchone()[0]

    cursor.execute("""
        SELECT shipper_country, COUNT(*) as count
        FROM shipments
        GROUP BY shipper_country
        ORDER BY count DESC
        LIMIT 5
    """)
    top_origins = [{"country": row[0], "count": row[1]} for row in cursor.fetchall()]

    cursor.execute("""
        SELECT consignee_country, COUNT(*) as count
        FROM shipments
        GROUP BY consignee_country
        ORDER BY count DESC
        LIMIT 5
    """)
    top_destinations = [{"country": row[0], "count": row[1]} for row in cursor.fetchall()]

    conn.close()

    return {
        "total": total,
        "highRisk": high_risk,
        "mediumRisk": medium_risk,
        "lowRisk": low_risk,
        "topOrigins": top_origins,
        "topDestinations": top_destinations,
    }
