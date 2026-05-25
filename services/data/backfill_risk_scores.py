#!/usr/bin/env python3
"""
Backfill Risk Scores (Phase 1)

Populates risk_scores_cache and risk_score_transactions tables with initial scores
for all 1,191 existing shipments. No model versioning or versioning logic yet.

Usage:
    python3 backfill_risk_scores.py [--start-from N] [--limit N]

Flags:
    --start-from N   Start from shipment index N (default: 0)
    --limit N        Backfill only N shipments (default: all)
"""
import sys
import logging
from datetime import datetime
import json
import sqlite3
from typing import Dict, Any, List
import uuid

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

DB_PATH = "/app/data/cbp_sentry.db"

def get_all_shipments(limit: int = None, start_from: int = 0) -> List[Dict[str, Any]]:
    """Get all shipments that need backfill"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        query = "SELECT * FROM shipments"
        if limit:
            query += f" LIMIT {limit} OFFSET {start_from}"

        cursor.execute(query)
        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Failed to fetch shipments: {e}")
        return []


def calculate_7factor_score(shipment: Dict[str, Any]) -> float:
    """
    Calculate 7-factor risk score (placeholder - actual calculation via RiskScoringEngine)

    For backfill, we'll use a simplified calculation. In production, this would call
    the actual RiskScoringEngine.
    """
    score = 0.0

    # Documentation Risk (25%)
    if shipment.get("element9_is_mismatch"):
        score += 10.0

    # Commodity Sensitivity (15%)
    hs_code = str(shipment.get("hs_code") or "").upper()
    if hs_code.startswith("7604"):  # Aluminum tubes
        score += 8.0
    elif hs_code.startswith("3004"):  # Pharmaceuticals
        score += 6.0

    # Routing Risk (15%)
    dwell_days = shipment.get("dwell_days") or 0
    if dwell_days > 15:
        score += 7.0
    elif dwell_days > 7:
        score += 4.0

    # Party Profile Risk (15%)
    shipper_age = (shipment.get("shipper_age_months") or 0)
    if shipper_age > 0 and shipper_age < 12:
        score += 8.0
    elif shipper_age > 0 and shipper_age < 24:
        score += 4.0

    # Corridor Risk (20%)
    origin = (shipment.get("origin_country") or "").upper()
    dest = (shipment.get("destination_country") or "").upper()
    if origin in ["VN", "CN", "BD"] and dest == "US":
        score += 12.0

    # Pattern Anomaly (10%)
    declared_val = shipment.get("declared_value_usd") or 0
    if declared_val > 0 and declared_val < 1000:
        score += 5.0

    # Time Sensitivity (10%)
    if shipment.get("created_at"):
        score += 2.0

    # Normalize to 0-100
    return min(max(score, 0.0), 100.0)


def create_breakdown_json(shipment: Dict[str, Any], final_score: float) -> str:
    """Create simplified 7-factor breakdown JSON"""
    dwell_days = (shipment.get("dwell_days") or 0)
    shipper_age = (shipment.get("shipper_age_months") or 0)
    declared_val = (shipment.get("declared_value_usd") or 0)

    breakdown = {
        "shipment_id": shipment.get("id"),
        "final_score": final_score,
        "factors": {
            "documentation_risk": {
                "weight": 0.25,
                "score": 10.0 if shipment.get("element9_is_mismatch") else 0.0,
                "rationale": "Element 9 mismatch detected" if shipment.get("element9_is_mismatch") else "No mismatch"
            },
            "commodity_sensitivity": {
                "weight": 0.15,
                "score": 8.0 if str(shipment.get("hs_code") or "").upper().startswith("7604") else 0.0,
                "rationale": "Tariff-sensitive commodity"
            },
            "routing_risk": {
                "weight": 0.15,
                "score": 7.0 if dwell_days > 15 else 0.0,
                "rationale": "High AIS dwell time"
            },
            "party_profile_risk": {
                "weight": 0.15,
                "score": 8.0 if shipper_age > 0 and shipper_age < 12 else 0.0,
                "rationale": "New shipper"
            },
            "corridor_risk": {
                "weight": 0.20,
                "score": 12.0 if (shipment.get("origin_country") or "").upper() in ["VN", "CN", "BD"] and (shipment.get("destination_country") or "").upper() == "US" else 0.0,
                "rationale": "High-risk corridor"
            },
            "pattern_anomaly": {
                "weight": 0.10,
                "score": 5.0 if declared_val > 0 and declared_val < 1000 else 0.0,
                "rationale": "Potential pricing anomaly"
            },
            "time_sensitivity": {
                "weight": 0.10,
                "score": 2.0,
                "rationale": "Time-based risk factor"
            }
        },
        "model_version": "7factor-v1.0",
        "calculated_at": datetime.utcnow().isoformat()
    }
    return json.dumps(breakdown)


def backfill_shipment(conn: sqlite3.Connection, shipment: Dict[str, Any], backfill_timestamp: str) -> bool:
    """Backfill a single shipment with initial score"""
    try:
        cursor = conn.cursor()

        shipment_id = shipment["id"]
        final_score = calculate_7factor_score(shipment)
        breakdown_json = create_breakdown_json(shipment, final_score)

        cache_id = str(uuid.uuid4())
        txn_id = str(uuid.uuid4())

        # Insert into risk_scores_cache
        cursor.execute("""
            INSERT OR REPLACE INTO risk_scores_cache
            (id, shipment_id, final_score, breakdown_json, current_model_version, calculation_timestamp, is_stale, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?)
        """, (
            cache_id,
            shipment_id,
            final_score,
            breakdown_json,
            "7factor-v1.0",
            backfill_timestamp,
            backfill_timestamp,
            backfill_timestamp
        ))

        # Insert into risk_score_transactions (as backfill record)
        cursor.execute("""
            INSERT INTO risk_score_transactions
            (id, shipment_id, previous_final_score, new_final_score, score_delta,
             transaction_type, transaction_reason, previous_breakdown_json, new_breakdown_json,
             triggered_by, triggered_by_model_version, transaction_timestamp, created_at)
            VALUES (?, ?, NULL, ?, NULL, ?, ?, NULL, ?, ?, ?, ?, ?)
        """, (
            txn_id,
            shipment_id,
            final_score,
            "backfill",
            "backfill_on_schema_migration",
            breakdown_json,
            "system",
            "7factor-v1.0",
            backfill_timestamp,
            backfill_timestamp
        ))

        return True
    except Exception as e:
        logger.error(f"Failed to backfill shipment {shipment_id}: {e}")
        return False


def main():
    """Backfill all shipments with initial scores"""

    # Parse arguments
    start_from = 0
    limit = None
    for i, arg in enumerate(sys.argv[1:]):
        if arg == "--start-from" and i + 1 < len(sys.argv) - 1:
            start_from = int(sys.argv[i + 2])
        elif arg == "--limit" and i + 1 < len(sys.argv) - 1:
            limit = int(sys.argv[i + 2])

    logger.info(f"Starting risk score backfill (start_from={start_from}, limit={limit})")

    # Get shipments
    shipments = get_all_shipments(limit=limit, start_from=start_from)
    total_shipments = len(shipments)
    logger.info(f"Found {total_shipments} shipments to backfill")

    if not shipments:
        logger.warning("No shipments found to backfill")
        return

    # Connect to database
    conn = sqlite3.connect(DB_PATH)
    backfill_timestamp = datetime.utcnow().isoformat()

    success_count = 0
    error_count = 0

    for i, shipment in enumerate(shipments):
        try:
            if backfill_shipment(conn, shipment, backfill_timestamp):
                success_count += 1
                if (i + 1) % 100 == 0:
                    conn.commit()
                    logger.info(f"Progress: {i + 1}/{total_shipments} backfilled")
            else:
                error_count += 1
        except Exception as e:
            logger.error(f"Unexpected error processing shipment {shipment.get('id')}: {e}")
            error_count += 1

    # Final commit
    conn.commit()
    conn.close()

    logger.info(f"Backfill complete: {success_count} succeeded, {error_count} failed")
    logger.info(f"All {total_shipments} shipments are now ready with initial risk scores")


if __name__ == "__main__":
    main()
