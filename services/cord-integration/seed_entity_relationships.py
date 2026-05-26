"""Create 3-level entity chains with relationships for CBP shippers."""
import sqlite3
import json
import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

def seed_entity_relationships(senzing_db_path: str) -> Dict[str, Any]:
    """Create holding companies and manufacturers for each shipper, with relationships.

    For each shipper found in the database, creates:
    - Level 2: Holding company (in HK or SG based on shipper country)
    - Level 3: Manufacturer (in CN or VN based on shipper country)

    And creates OWNED_BY and PARENT_OF relationships between them.
    """
    try:
        conn = sqlite3.connect(senzing_db_path)
        cursor = conn.cursor()

        # Get all CBP shippers
        cursor.execute("""
            SELECT DISTINCT entity_id, name_primary, country
            FROM senzing_entities
            WHERE data_source = 'CBP-SHIPPER'
        """)
        shippers = cursor.fetchall()
        logger.info(f"Found {len(shippers)} CBP shippers for relationship seeding")

        entities_created = 0
        relationships_created = 0

        for shipper_id, shipper_name, shipper_country in shippers:
            # Determine holding company country
            holding_country = "HK" if shipper_country in ["VN", "TH", "MY", "KH", "LA", "IR", "KP"] else "SG"
            mfg_country = "CN"

            # Generate names
            shipper_base = shipper_name.split()[0] if shipper_name else "Global"
            holding_name = f"{shipper_base} Global Holdings Ltd."
            mfg_name = f"Guangdong {shipper_base} Manufacturing Co., Ltd."

            # Create Level 2: Holding Company
            holding_id = f"CBP-HOLDING:{shipper_base}:{holding_country}"
            cursor.execute("""
                INSERT OR REPLACE INTO senzing_entities
                (entity_id, data_source, record_id, name_primary, country, entity_type, confidence, raw_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                holding_id,
                "CBP-HOLDING",
                holding_id,
                holding_name,
                holding_country,
                "ORGANIZATION",
                0.88,
                json.dumps({"name": holding_name, "country": holding_country, "type": "HOLDING_COMPANY"})
            ))
            entities_created += 1

            # Create Level 3: Manufacturer
            mfg_id = f"CBP-MANUFACTURER:{shipper_base}:{mfg_country}"
            cursor.execute("""
                INSERT OR REPLACE INTO senzing_entities
                (entity_id, data_source, record_id, name_primary, country, entity_type, confidence, raw_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                mfg_id,
                "CBP-MANUFACTURER",
                mfg_id,
                mfg_name,
                mfg_country,
                "ORGANIZATION",
                0.85,
                json.dumps({"name": mfg_name, "country": mfg_country, "type": "MANUFACTURER"})
            ))
            entities_created += 1

            # Create relationships: Shipper OWNED_BY Holding Company
            cursor.execute("""
                INSERT OR REPLACE INTO senzing_relationships
                (entity_id_a, entity_id_b, relationship_type, confidence, evidence)
                VALUES (?, ?, ?, ?, ?)
            """, (
                shipper_id,
                holding_id,
                "OWNED_BY",
                0.88,
                json.dumps({"source": "CBP-seeded", "type": "ownership_chain"})
            ))
            relationships_created += 1

            # Create relationships: Holding Company OWNS Shipper
            cursor.execute("""
                INSERT OR REPLACE INTO senzing_relationships
                (entity_id_a, entity_id_b, relationship_type, confidence, evidence)
                VALUES (?, ?, ?, ?, ?)
            """, (
                holding_id,
                shipper_id,
                "OWNS",
                0.88,
                json.dumps({"source": "CBP-seeded", "type": "ownership_chain"})
            ))
            relationships_created += 1

            # Create relationships: Holding Company PARENT_OF Manufacturer
            cursor.execute("""
                INSERT OR REPLACE INTO senzing_relationships
                (entity_id_a, entity_id_b, relationship_type, confidence, evidence)
                VALUES (?, ?, ?, ?, ?)
            """, (
                holding_id,
                mfg_id,
                "PARENT_COMPANY",
                0.85,
                json.dumps({"source": "CBP-seeded", "type": "ownership_chain"})
            ))
            relationships_created += 1

            # Create relationships: Manufacturer OWNED_BY Holding Company
            cursor.execute("""
                INSERT OR REPLACE INTO senzing_relationships
                (entity_id_a, entity_id_b, relationship_type, confidence, evidence)
                VALUES (?, ?, ?, ?, ?)
            """, (
                mfg_id,
                holding_id,
                "OWNED_BY",
                0.85,
                json.dumps({"source": "CBP-seeded", "type": "ownership_chain"})
            ))
            relationships_created += 1

        conn.commit()
        conn.close()

        logger.info(f"✓ Created {entities_created} entities and {relationships_created} relationships")

        return {
            "status": "success",
            "shippers_processed": len(shippers),
            "entities_created": entities_created,
            "relationships_created": relationships_created
        }

    except Exception as e:
        logger.error(f"Seed entity relationships failed: {e}")
        return {
            "status": "failed",
            "error": str(e)
        }

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = seed_entity_relationships("/app/data/senzing.db")
    print(json.dumps(result, indent=2))
