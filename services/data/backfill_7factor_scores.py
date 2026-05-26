#!/usr/bin/env python3
"""
Backfill 7-Factor Risk Scores

Populates risk_scores_cache table with 7-factor breakdown scores for all shipments.
This ensures the Risk Score tab can display the full scoring model with evidence.
"""
import sys
import os

# Try to import from available paths
try:
    from risk_scoring_engine import RiskScoringEngine
except ImportError:
    sys.path.insert(0, '/app/services/api')
    from risk_scoring_engine import RiskScoringEngine

import sqlite3
import json
import logging
from datetime import datetime
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Use container path if it exists, otherwise use host path
DB_PATH = "/app/data/cbp_sentry.db" if os.path.exists("/app/data/cbp_sentry.db") else "/home/rahulvadera/cbp-sentry/data/cbp_sentry.db"

def ensure_shipment_fields(shipment):
    """Ensure shipment has all required fields with defaults"""
    defaults = {
        'dwell_days': 0,
        'port_calls': [],
        'element9_is_mismatch': False,
        'element9_declared_country': None,
        'element9_actual_country': None,
        'shipper_age_months': 12,
        'ad_cvd_applicable': False,
        'ad_cvd_rate': 0,
        'h1_score': 0,
        'h2_score': 0,
        'shipper_country': 'XX',
        'destination_country': 'US',
        'hs_code': '9999',
        'commodity_name': 'General Merchandise',
    }

    for field, default_value in defaults.items():
        if field not in shipment or shipment[field] is None:
            shipment[field] = default_value

    # Ensure port_calls is a list
    if isinstance(shipment.get('port_calls'), str):
        try:
            shipment['port_calls'] = json.loads(shipment['port_calls'])
        except:
            shipment['port_calls'] = []

    return shipment

def backfill_scores():
    """Backfill risk scores for all shipments"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Get all shipments
        cursor.execute("SELECT * FROM shipments ORDER BY created_at DESC")
        rows = cursor.fetchall()
        shipments = [dict(row) for row in rows]

        logger.info(f"Found {len(shipments)} shipments to score")

        # Initialize scoring engine
        engine = RiskScoringEngine()

        # Score each shipment
        scored_count = 0
        error_count = 0

        for shipment in shipments:
            try:
                # Ensure all required fields
                shipment = ensure_shipment_fields(shipment)

                # Score the shipment
                breakdown = engine.score_shipment(shipment)

                # Store in risk_scores_cache
                timestamp = datetime.utcnow().isoformat()
                cache_data = {
                    'shipment_id': shipment['id'],
                    'final_score': breakdown.final_score,
                    'confidence_interval': breakdown.confidence_interval,
                    'breakdown_json': json.dumps({
                        'components': [
                            {
                                'component': c.component,
                                'factor': c.factor,
                                'score': c.score,
                                'weight': c.weight,
                                'weighted_result': c.weighted_result,
                                'rationale': c.rationale,
                                'evidence': c.evidence,
                            }
                            for c in breakdown.components
                        ],
                        'subtotal': breakdown.subtotal,
                        'corridor_adjustment': breakdown.corridor_risk_adjustment,
                        'additional_adjustments': breakdown.additional_adjustments,
                        'final_score': breakdown.final_score,
                        'calculation_table': breakdown.calculation_table,
                    }),
                    'updated_at': timestamp,
                    'calculation_timestamp': timestamp,
                }

                # Insert or update cache
                cursor.execute('''
                    INSERT OR REPLACE INTO risk_scores_cache
                    (shipment_id, final_score, confidence_interval, breakdown_json, current_model_version, calculation_timestamp, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    cache_data['shipment_id'],
                    cache_data['final_score'],
                    json.dumps(cache_data['confidence_interval']),
                    cache_data['breakdown_json'],
                    '7-factor-engine-v1.0',
                    cache_data['calculation_timestamp'],
                    cache_data['updated_at'],
                ))

                scored_count += 1
                if scored_count % 10 == 0:
                    logger.info(f"Scored {scored_count}/{len(shipments)} shipments")

            except Exception as e:
                error_count += 1
                logger.warning(f"Failed to score {shipment.get('id', '?')}: {e}")

        # Commit changes
        conn.commit()
        conn.close()

        logger.info(f"✓ Backfill complete: {scored_count} scored, {error_count} errors")

    except Exception as e:
        logger.error(f"Backfill failed: {e}")
        return False

    return True

if __name__ == "__main__":
    success = backfill_scores()
    sys.exit(0 if success else 1)
