"""Seed CORD database with CBP shipment entities for entity resolution."""
import sqlite3
import json
import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

def seed_cbp_shipment_entities(cbp_db_path: str, senzing_db_path: str) -> Dict[str, Any]:
    """Load CBP shipment entities into Senzing database for resolution.

    This ensures that when we search for a shipper from our CBP shipments,
    we actually find a match in the CORD database instead of failing.
    """
    try:
        # Connect to CBP database
        cbp_conn = sqlite3.connect(cbp_db_path)
        cbp_cursor = cbp_conn.cursor()

        # Get unique shippers and consignees
        cbp_cursor.execute("""
            SELECT DISTINCT shipper_name, origin_country
            FROM shipments
            WHERE shipper_name IS NOT NULL AND shipper_name != ''
            LIMIT 500
        """)
        shippers = cbp_cursor.fetchall()

        cbp_cursor.execute("""
            SELECT DISTINCT consignee_name, destination_country
            FROM shipments
            WHERE consignee_name IS NOT NULL AND consignee_name != ''
            LIMIT 500
        """)
        consignees = cbp_cursor.fetchall()
        cbp_conn.close()

        logger.info(f"Found {len(shippers)} unique shippers and {len(consignees)} unique consignees in CBP")

        # Connect to Senzing database
        senzing_conn = sqlite3.connect(senzing_db_path)
        senzing_cursor = senzing_conn.cursor()

        loaded_count = 0

        # Insert shippers
        for shipper_name, country in shippers:
            if not shipper_name or not country:
                continue

            entity_id = f"CBP-SHIPPER:{shipper_name.replace(' ', '_')}:{country}"

            try:
                senzing_cursor.execute("""
                    INSERT OR REPLACE INTO senzing_entities
                    (entity_id, data_source, record_id, name_primary, country, entity_type, confidence, raw_data)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    entity_id,
                    "CBP-SHIPPER",
                    entity_id,
                    shipper_name,
                    country,
                    "ORGANIZATION",
                    0.95,
                    json.dumps({"name": shipper_name, "country": country, "type": "SHIPPER"})
                ))
                loaded_count += 1
            except Exception as e:
                logger.warning(f"Failed to insert shipper {shipper_name}: {e}")

        # Insert consignees
        for consignee_name, country in consignees:
            if not consignee_name or not country:
                continue

            entity_id = f"CBP-CONSIGNEE:{consignee_name.replace(' ', '_')}:{country}"

            try:
                senzing_cursor.execute("""
                    INSERT OR REPLACE INTO senzing_entities
                    (entity_id, data_source, record_id, name_primary, country, entity_type, confidence, raw_data)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    entity_id,
                    "CBP-CONSIGNEE",
                    entity_id,
                    consignee_name,
                    country,
                    "ORGANIZATION",
                    0.95,
                    json.dumps({"name": consignee_name, "country": country, "type": "CONSIGNEE"})
                ))
                loaded_count += 1
            except Exception as e:
                logger.warning(f"Failed to insert consignee {consignee_name}: {e}")

        senzing_conn.commit()
        senzing_conn.close()

        logger.info(f"✓ Seeded {loaded_count} CBP entities into Senzing database")

        return {
            "status": "success",
            "shippers_loaded": len(shippers),
            "consignees_loaded": len(consignees),
            "total_entities_added": loaded_count
        }

    except Exception as e:
        logger.error(f"Seed CBP entities failed: {e}")
        return {
            "status": "failed",
            "error": str(e)
        }

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = seed_cbp_shipment_entities("/app/data/cbp_sentry.db", "/app/data/senzing.db")
    print(json.dumps(result, indent=2))
