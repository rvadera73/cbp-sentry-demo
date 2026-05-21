"""
Risk Corridor database operations
"""
import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional

DB_PATH = Path(__file__).parent.parent.parent / "cbp_sentry.db"


def init_risk_corridor_tables():
    """Initialize risk corridor-related tables if they don't exist"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # FTZ Events table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ftz_events (
            id INTEGER PRIMARY KEY,
            shipment_id TEXT NOT NULL,
            ftz_code TEXT NOT NULL,
            ftz_name TEXT NOT NULL,
            entry_date DATE NOT NULL,
            exit_date DATE,
            dwell_days INTEGER,
            risk_flag BOOLEAN,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (shipment_id) REFERENCES shipments(manifest_id)
        )
    """)

    # Vessel Tracking table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vessel_tracking (
            id INTEGER PRIMARY KEY,
            vessel_id TEXT NOT NULL UNIQUE,
            vessel_name TEXT NOT NULL,
            flag_state TEXT,
            imo_number TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Port Call History table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS port_call_history (
            id INTEGER PRIMARY KEY,
            vessel_id TEXT NOT NULL,
            port_name TEXT NOT NULL,
            arrival_date DATETIME NOT NULL,
            departure_date DATETIME,
            dwell_days INTEGER,
            baseline_dwell_days REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (vessel_id) REFERENCES vessel_tracking(vessel_id)
        )
    """)

    # Officer Feedback table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS officer_feedback (
            id INTEGER PRIMARY KEY,
            shipment_id TEXT NOT NULL,
            corridor_id TEXT,
            risk_score_original REAL,
            override_action TEXT,
            justification_category TEXT,
            justification_detail TEXT,
            officer_id TEXT,
            override_timestamp DATETIME,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (shipment_id) REFERENCES shipments(manifest_id)
        )
    """)

    # Create indices
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_ftz_shipment ON ftz_events(shipment_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_vessel_id ON vessel_tracking(vessel_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_port_call_vessel ON port_call_history(vessel_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_feedback_shipment ON officer_feedback(shipment_id)")

    conn.commit()
    conn.close()


def get_risk_corridors(
    industry_filter: Optional[List[str]] = None,
    time_period_days: int = 7,
) -> Dict[str, Any]:
    """
    Get aggregated risk corridors grouped by HTS, origin, destination, and supplier entity.
    Calculates YoY surge and macro volumetric deltas.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get current period shipments
    query = """
        SELECT
            commodity_code as hts_6digit,
            shipper_country as origin_country,
            consignee_country as destination_country,
            shipper_name as supplier_entity,
            COUNT(*) as shipment_count,
            SUM(declared_value) as aggregate_value_usd,
            AVG(risk_score) as avg_risk_score,
            COUNT(DISTINCT shipper_name) as active_vessels
        FROM shipments
        WHERE created_at >= datetime('now', '-' || ? || ' days')
    """
    params = [time_period_days]

    if industry_filter:
        # Create HTS filter (first 4 digits for industry segment)
        for prefix in industry_filter:
            query += " AND commodity_code LIKE ?"
            params.append(prefix + "%")

    query += """
        GROUP BY commodity_code, shipper_country, consignee_country, shipper_name
        ORDER BY aggregate_value_usd DESC
    """

    cursor.execute(query, params)
    current_period = cursor.fetchall()

    # Get prior period for YoY calculation
    prior_query = """
        SELECT
            commodity_code as hts_6digit,
            shipper_country as origin_country,
            consignee_country as destination_country,
            shipper_name as supplier_entity,
            COUNT(*) as shipment_count,
            SUM(declared_value) as aggregate_value_usd
        FROM shipments
        WHERE created_at >= datetime('now', '-' || (? * 2) || ' days')
        AND created_at < datetime('now', '-' || ? || ' days')
    """
    prior_params = [time_period_days, time_period_days]

    if industry_filter:
        for prefix in industry_filter:
            prior_query += " AND commodity_code LIKE ?"
            prior_params.append(prefix + "%")

    prior_query += """
        GROUP BY commodity_code, shipper_country, consignee_country, shipper_name
    """

    cursor.execute(prior_query, prior_params)
    prior_period = {
        (row["hts_6digit"], row["origin_country"], row["destination_country"], row["supplier_entity"]): row
        for row in cursor.fetchall()
    }

    corridors = []
    summary = {
        "total_active_corridors": 0,
        "high_risk_count": 0,
        "medium_risk_count": 0,
        "aggregate_manifest_value": 0,
    }

    for row in current_period:
        key = (row["hts_6digit"], row["origin_country"], row["destination_country"], row["supplier_entity"])
        prior = prior_period.get(key, {})

        # Calculate YoY surge
        current_count = row["shipment_count"]
        prior_count = prior.get("shipment_count", 0) if prior else 0
        yoy_volume_surge_pct = ((current_count - prior_count) / prior_count * 100) if prior_count > 0 else 0

        current_value = row["aggregate_value_usd"]
        prior_value = prior.get("aggregate_value_usd", 0) if prior else 0
        yoy_value_surge_pct = ((current_value - prior_value) / prior_value * 100) if prior_value > 0 else 0

        # Determine risk level
        avg_risk = row["avg_risk_score"] or 0
        if avg_risk >= 80:
            risk_level = "HIGH"
        elif avg_risk >= 60:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        # Macro volumetric delta (manifest vs estimated capacity)
        # Estimate: assume 450 tons domestic capacity baseline for industrial goods
        estimated_capacity_tons = 450
        manifest_tons = current_count * 50  # Assume ~50 tons per shipment average
        ratio = manifest_tons / estimated_capacity_tons if estimated_capacity_tons > 0 else 0

        macro_delta = {
            "status": "FLAGGED" if ratio > 2.0 else "NORMAL",
            "outbound_volume_manifest_tons": manifest_tons,
            "estimated_domestic_capacity_tons": estimated_capacity_tons,
            "ratio": round(ratio, 2),
            "signal": f"Outbound volume {ratio:.1f}× estimated production capacity" if ratio > 2.0 else "Normal capacity utilization",
        }

        corridor_id = f"HC-{row['hts_6digit']}-{row['origin_country']}{row['destination_country']}-{row['supplier_entity'][:3].upper()}"

        corridor = {
            "corridor_id": corridor_id,
            "hts_chapter": row["hts_6digit"][:2],
            "industry_segment": _get_industry_segment(row["hts_6digit"]),
            "origin_country": row["origin_country"],
            "destination_country": row["destination_country"],
            "supplier_entity": row["supplier_entity"],
            "shipment_count": current_count,
            "aggregate_value_usd": int(current_value),
            "yoy_volume_surge_pct": round(yoy_volume_surge_pct, 1),
            "yoy_value_surge_pct": round(yoy_value_surge_pct, 1),
            "macro_volumetric_delta": macro_delta,
            "ad_cvd_rate_pct": 374.15,  # Placeholder: would come from tariff DB
            "active_vessels": row["active_vessels"] or 0,
            "risk_level": risk_level,
            "last_updated": datetime.now().isoformat() + "Z",
        }

        corridors.append(corridor)
        summary["total_active_corridors"] += 1
        summary["aggregate_manifest_value"] += int(current_value)
        if risk_level == "HIGH":
            summary["high_risk_count"] += 1
        elif risk_level == "MEDIUM":
            summary["medium_risk_count"] += 1

    conn.close()
    return {"corridors": corridors, "summary": summary}


def get_corridor_detail(corridor_id: str, include_params: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Get detailed view of a specific risk corridor with vessel activity and entity chain.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Parse corridor_id to extract components
    # Format: HC-{hts}-{origin}{destination}-{entity_abbr}
    parts = corridor_id.split("-")
    hts_chapter = parts[1] if len(parts) > 1 else ""
    origin = parts[2][:2] if len(parts) > 2 else ""
    destination = parts[2][2:] if len(parts) > 2 else ""

    # Get corridor shipments
    cursor.execute("""
        SELECT DISTINCT
            commodity_code,
            shipper_country,
            consignee_country,
            shipper_name,
            risk_score
        FROM shipments
        WHERE commodity_code LIKE ?
        AND shipper_country = ?
        AND consignee_country = ?
        LIMIT 1
    """, (hts_chapter + "%", origin, destination))

    corridor_row = cursor.fetchone()
    if not corridor_row:
        return None

    # Get active entities (using shipper as proxy for vessel routes)
    cursor.execute("""
        SELECT DISTINCT shipper_name FROM shipments
        WHERE shipper_country = ? AND consignee_country = ?
    """, (origin, destination))

    shipper_rows = cursor.fetchall()
    vessels = []

    for srow in shipper_rows:
        shipper_name = srow["shipper_name"]

        # Get port call history (simulated)
        port_history = _get_mock_port_call_history(shipper_name)

        vessel_detail = {
            "vessel_id": f"IMO-{hash(shipper_name) % 10000000:07d}",
            "vessel_name": f"MV {shipper_name[:20]}",
            "flag_state": "PK",  # Placeholder
            "current_port": "Port of Los Angeles",  # Placeholder
            "status": "AT_BERTH",
            "port_call_history": port_history,
            "ftz_dwell_events": _get_mock_ftz_events(shipper_name),
            "transshipment_risk_score": 78.0,
            "risk_level": "HIGH",
        }
        vessels.append(vessel_detail)

    # Get entity chain (simulated from CORD API)
    entity_chain = _get_mock_entity_chain(corridor_row["shipper_name"])

    supplier_entity = {
        "entity_id": f"cord-{corridor_id}-001",
        "name": corridor_row["shipper_name"],
        "country": origin,
        "risk_score": corridor_row["risk_score"] or 70,
        "ofac_status": "CLEAN",
    }

    corridor_detail = {
        "corridor_id": corridor_id,
        "hts_chapter": corridor_row["commodity_code"][:2],
        "industry_segment": _get_industry_segment(corridor_row["commodity_code"]),
        "origin_country": origin,
        "destination_country": destination,
        "supplier_entity": supplier_entity,
        "active_vessels": vessels,
    }

    conn.close()
    return {
        "corridor": corridor_detail,
        "entity_chain": entity_chain,
    }


def get_vessels_by_port(
    port_code: str,
    time_window_days: int = 7,
    risk_filter: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Get vessels of interest at a specific port.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Map port codes to port names
    port_names = {
        "USLA": "Port of Los Angeles",
        "USLB": "Port of Long Beach",
        "USNJ": "Port of Newark",
        "USNY": "Port of New York",
    }
    port_name = port_names.get(port_code, f"Port {port_code}")

    # Get shipments destined to this port region in time window
    cursor.execute("""
        SELECT DISTINCT
            shipper_name,
            commodity_code,
            shipper_country,
            SUM(declared_value) as total_value,
            COUNT(*) as manifest_count,
            AVG(risk_score) as avg_risk_score
        FROM shipments
        WHERE consignee_country = 'US'
        AND created_at >= datetime('now', '-' || ? || ' days')
    """, (time_window_days,))

    vessel_rows = cursor.fetchall()

    vessels_of_interest = []
    summary = {
        "total_vessels_at_port": len(vessel_rows),
        "vessels_of_interest": 0,
        "high_risk_count": 0,
        "exam_capacity_available": 5,
    }

    for vrow in vessel_rows:
        avg_risk = vrow["avg_risk_score"] or 0

        # Filter by risk if specified
        if risk_filter == "HIGH" and avg_risk < 70:
            continue

        # Determine cargo risk level
        if avg_risk >= 80:
            cargo_risk = "HIGH"
        elif avg_risk >= 60:
            cargo_risk = "MEDIUM"
        else:
            cargo_risk = "LOW"

        vessel_of_interest = {
            "vessel_id": f"IMO-{hash(vrow['shipper_name']) % 10000000:07d}",
            "vessel_name": f"MV {vrow['shipper_name'][:20]}",
            "eta": (datetime.now() + timedelta(hours=36)).isoformat() + "Z",
            "status": "INBOUND",
            "cargo_risk_level": cargo_risk,
            "cargo_summary": {
                "primary_hts_chapter": vrow["commodity_code"][:2],
                "industry_segment": _get_industry_segment(vrow["commodity_code"]),
                "total_manifest_value_usd": int(vrow["total_value"]),
                "manifest_count": vrow["manifest_count"],
            },
            "route_anomalies": [
                f"Port of Guangzhou dwell: 7 days (3.3× baseline)",
                "Transshipment routing via Hong Kong detected",
                "AIS signal gap: 18 hours near Sulu Strait",
            ] if avg_risk >= 80 else [],
            "recommended_actions": [
                "Enhanced Physical Examination on Arrival",
                "ISF Element 9 review (Stuffing location mismatch)",
                "OFAC check for flag state vessel agents",
            ] if avg_risk >= 80 else [],
        }

        vessels_of_interest.append(vessel_of_interest)
        summary["vessels_of_interest"] += 1
        if cargo_risk == "HIGH":
            summary["high_risk_count"] += 1

    conn.close()
    return {
        "port": port_code,
        "port_name": port_name,
        "vessels_of_interest": vessels_of_interest,
        "summary": summary,
    }


def get_corridor_timeline(
    corridor_id: str,
    start_date: str,
    end_date: str,
    granularity: str = "daily",
) -> Dict[str, Any]:
    """
    Get historical timeline snapshots of a corridor's evolution.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Parse corridor_id
    parts = corridor_id.split("-")
    hts_chapter = parts[1] if len(parts) > 1 else ""
    origin = parts[2][:2] if len(parts) > 2 else ""
    destination = parts[2][2:] if len(parts) > 2 else ""

    # Get daily snapshots
    snapshots = []
    current_date = datetime.fromisoformat(start_date)
    end_dt = datetime.fromisoformat(end_date)

    while current_date <= end_dt:
        date_str = current_date.strftime("%Y-%m-%d")
        next_date = (current_date + timedelta(days=1)).strftime("%Y-%m-%d")

        cursor.execute("""
            SELECT
                COUNT(*) as shipment_count,
                SUM(declared_value) as aggregate_value,
                COUNT(DISTINCT shipper_name) as entity_count
            FROM shipments
            WHERE commodity_code LIKE ?
            AND shipper_country = ?
            AND consignee_country = ?
            AND DATE(created_at) = ?
        """, (hts_chapter + "%", origin, destination, date_str))

        row = cursor.fetchone()
        snapshot = {
            "date": date_str,
            "shipment_count": row["shipment_count"] or 0 if row else 0,
            "aggregate_value_usd": int(row["aggregate_value"] or 0) if row else 0,
            "active_entities": [],
            "active_vessels": [],
            "notable_events": [],
        }

        # Get entities for this date
        if snapshot["shipment_count"] > 0:
            cursor.execute("""
                SELECT DISTINCT shipper_name FROM shipments
                WHERE commodity_code LIKE ?
                AND shipper_country = ?
                AND consignee_country = ?
                AND DATE(created_at) = ?
            """, (hts_chapter + "%", origin, destination, date_str))

            snapshot["active_entities"] = [row["shipper_name"] for row in cursor.fetchall()]

            cursor.execute("""
                SELECT DISTINCT shipper_name FROM shipments
                WHERE commodity_code LIKE ?
                AND shipper_country = ?
                AND consignee_country = ?
                AND DATE(created_at) = ?
            """, (hts_chapter + "%", origin, destination, date_str))

            snapshot["active_vessels"] = [f"MV {row['shipper_name'][:20]}" for row in cursor.fetchall()]

            # Detect notable events
            if len(snapshot["active_entities"]) > len(set(snapshot["active_entities"])):
                snapshot["notable_events"].append("New entity link detected")

        snapshots.append(snapshot)
        current_date += timedelta(days=1)

    # Entity evolution tracking
    entity_formations = []
    cursor.execute("""
        SELECT DISTINCT shipper_name, MIN(DATE(created_at)) as first_date
        FROM shipments
        WHERE commodity_code LIKE ?
        AND shipper_country = ?
        AND consignee_country = ?
        GROUP BY shipper_name
    """, (hts_chapter + "%", origin, destination))

    for row in cursor.fetchall():
        entity_formations.append({
            "date": row["first_date"],
            "entity_name": row["shipper_name"],
            "country": origin,
            "first_shipment_after_formation": 1,
            "suspicious_timing": False,
        })

    entity_evolution = {
        "entities_formed": len(entity_formations),
        "entity_formations": entity_formations,
    }

    conn.close()
    return {
        "corridor_id": corridor_id,
        "timeline_snapshots": snapshots,
        "entity_evolution": entity_evolution,
    }


def log_feedback_override(override_data: Dict[str, Any]) -> Dict[str, str]:
    """
    Log officer feedback override for model retraining.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    override_id = f"OVERRIDE-{datetime.now().strftime('%Y-%m-%d')}-{hash(override_data['shipment_id']) % 1000:03d}"

    cursor.execute("""
        INSERT INTO officer_feedback (
            shipment_id,
            corridor_id,
            risk_score_original,
            override_action,
            justification_category,
            justification_detail,
            officer_id,
            override_timestamp
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        override_data.get("shipment_id"),
        override_data.get("corridor_id"),
        override_data.get("risk_score_original"),
        override_data.get("override_action"),
        override_data.get("justification_category"),
        override_data.get("justification_detail"),
        override_data.get("officer_id"),
        override_data.get("override_timestamp"),
    ))

    conn.commit()
    conn.close()

    return {
        "override_id": override_id,
        "status": "LOGGED",
        "feedback_stored_for_model_retraining": True,
        "next_model_training_window": "2026-06-01",
    }


def _get_industry_segment(hts_code: str) -> str:
    """Map HTS code to industry segment"""
    hts_prefix = hts_code[:4]

    mapping = {
        "7604": "Industrial Aluminum",
        "8541": "Electronic Components",
        "2701": "Energy Products",
        "7210": "Steel Products",
        "2701": "Coal & Minerals",
    }

    return mapping.get(hts_prefix, "Manufacturing & Goods")


def _get_mock_port_call_history(vessel_name: str) -> List[Dict[str, Any]]:
    """Generate mock port call history for a vessel"""
    return [
        {
            "port_name": "Port of Guangzhou",
            "arrival_date": (datetime.now() - timedelta(days=15)).isoformat() + "Z",
            "departure_date": (datetime.now() - timedelta(days=8)).isoformat() + "Z",
            "dwell_days": 7,
            "baseline_dwell_days": 2.1,
            "anomaly": "3.3× baseline dwell",
        },
        {
            "port_name": "Port of Hong Kong",
            "arrival_date": (datetime.now() - timedelta(days=8)).isoformat() + "Z",
            "departure_date": (datetime.now() - timedelta(days=6)).isoformat() + "Z",
            "dwell_days": 2,
            "baseline_dwell_days": 1.8,
            "anomaly": None,
        },
    ]


def _get_mock_ftz_events(vessel_name: str) -> List[Dict[str, Any]]:
    """Generate mock FTZ dwell events for a vessel"""
    return [
        {
            "ftz_code": "FTZ-80",
            "ftz_name": "Los Angeles Foreign Trade Zone",
            "entry_date": (datetime.now() - timedelta(days=2)).isoformat() + "Z",
            "estimated_exit": (datetime.now() + timedelta(days=5)).isoformat() + "Z",
            "dwell_days": 7,
            "status": "HIGH_RISK_DWELL",
        }
    ]


def _get_mock_entity_chain(shipper_name: str) -> Dict[str, Any]:
    """Generate mock entity chain for a shipper"""
    return {
        "level_1": {
            "name": shipper_name,
            "country": "VN",
            "role": "Shipper",
        },
        "level_2": {
            "name": "Greenfield Global Metals Holdings Ltd.",
            "country": "HK",
            "role": "Holding Company",
        },
        "level_3": {
            "name": "Guangdong Greenfield Aluminum Mfg. Co., Ltd.",
            "country": "CN",
            "role": "Manufacturer",
        },
        "relationships": [
            {
                "from": "level_1",
                "to": "level_2",
                "relationship_type": "OWNED_BY",
                "confidence": 0.95,
            }
        ],
    }
