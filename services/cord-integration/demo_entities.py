"""Demo entities for CBP Sentry case examples.

Seeds Senzing-format entities for Greenfield, Solaria, and related cases
to enable end-to-end entity resolution demo in the UI.
"""
import json
from typing import List, Dict, Any


DEMO_ENTITIES: List[Dict[str, Any]] = [
    # ============ GREENFIELD ALUMINUM CASE ============
    # Level 1: Vietnamese shipper (direct shipper)
    {
        "DATA_SOURCE": "CBP-DEMO",
        "RECORD_TYPE": "ORGANIZATION",
        "RECORD_ID": "greenfield-vn-001",
        "NAMES": [{"NAME_TYPE": "PRIMARY", "NAME_ORG": "Greenfield Industrial Trading Co., Ltd."}],
        "ADDRESSES": [{"ADDR_FULL": "123 Tran Phu Street, Hanoi, Vietnam"}],
        "COUNTRIES": [{"REGISTRATION_COUNTRY": "VN"}],
        "ATTRIBUTES": {
            "SHIPPER_AGE_MONTHS": 8,
            "INCORPORATION_DATE": "2025-09-15",
            "BUSINESS_TYPE": "ALUMINUM_EXPORTER"
        }
    },
    # Level 2: Hong Kong holding company
    {
        "DATA_SOURCE": "CBP-DEMO",
        "RECORD_TYPE": "ORGANIZATION",
        "RECORD_ID": "greenfield-hk-holding",
        "NAMES": [{"NAME_TYPE": "PRIMARY", "NAME_ORG": "Greenfield Global Metals Holdings Ltd."}],
        "ADDRESSES": [{"ADDR_FULL": "456 Des Voeux Road, Hong Kong"}],
        "COUNTRIES": [{"REGISTRATION_COUNTRY": "HK"}],
        "ATTRIBUTES": {"HOLDING_COMPANY": True}
    },
    # Level 3: Chinese manufacturer (ultimate beneficial owner)
    {
        "DATA_SOURCE": "CBP-DEMO",
        "RECORD_TYPE": "ORGANIZATION",
        "RECORD_ID": "greenfield-cn-mfg",
        "NAMES": [
            {"NAME_TYPE": "PRIMARY", "NAME_ORG": "Guangdong Greenfield Aluminum Manufacturing Co., Ltd."},
            {"NAME_TYPE": "ALIAS", "NAME_ORG": "绿田铝业有限公司"}
        ],
        "ADDRESSES": [{"ADDR_FULL": "789 Huacheng Avenue, Guangzhou, Guangdong, China"}],
        "COUNTRIES": [{"REGISTRATION_COUNTRY": "CN"}],
        "ATTRIBUTES": {"MANUFACTURER": True, "ALUMINUM_CAPACITY_MT": 50000}
    },
    # Consignee: US distributor
    {
        "DATA_SOURCE": "CBP-DEMO",
        "RECORD_TYPE": "ORGANIZATION",
        "RECORD_ID": "sunpath-energy-nj",
        "NAMES": [{"NAME_TYPE": "PRIMARY", "NAME_ORG": "SunPath Energy Distributors LLC"}],
        "ADDRESSES": [{"ADDR_FULL": "890 Market Street, Newark, NJ 07102, USA"}],
        "COUNTRIES": [{"REGISTRATION_COUNTRY": "US"}],
        "ATTRIBUTES": {"IMPORTER": True, "SOLAR_DISTRIBUTOR": True}
    },
    # Vessel
    {
        "DATA_SOURCE": "CBP-DEMO",
        "RECORD_TYPE": "VESSEL",
        "RECORD_ID": "mv-pacific-horizon",
        "NAMES": [{"NAME_TYPE": "PRIMARY", "NAME_VESSEL": "MV Pacific Horizon"}],
        "ATTRIBUTES": {
            "IMO": "9876543",
            "FLAG_STATE": "PA",
            "GROSS_TONNAGE": 50000
        }
    },

    # ============ SOLARIA SOLAR CASE ============
    # Level 1: Malaysian shipper
    {
        "DATA_SOURCE": "CBP-DEMO",
        "RECORD_TYPE": "ORGANIZATION",
        "RECORD_ID": "solaria-my-001",
        "NAMES": [{"NAME_TYPE": "PRIMARY", "NAME_ORG": "Solaria Manufacturing Sdn. Bhd."}],
        "ADDRESSES": [{"ADDR_FULL": "321 Jalan Raja Chulan, Kuala Lumpur, Malaysia"}],
        "COUNTRIES": [{"REGISTRATION_COUNTRY": "MY"}],
        "ATTRIBUTES": {
            "SHIPPER_AGE_MONTHS": 1,
            "INCORPORATION_DATE": "2026-04-15",
            "BUSINESS_TYPE": "SOLAR_MANUFACTURER"
        }
    },
    # Level 3: Chinese parent
    {
        "DATA_SOURCE": "CBP-DEMO",
        "RECORD_TYPE": "ORGANIZATION",
        "RECORD_ID": "solaria-cn-parent",
        "NAMES": [{"NAME_TYPE": "PRIMARY", "NAME_ORG": "Guangdong Solaria New Energy Technology Co."}],
        "ADDRESSES": [{"ADDR_FULL": "654 Innovation Road, Shenzhen, Guangdong, China"}],
        "COUNTRIES": [{"REGISTRATION_COUNTRY": "CN"}],
        "ATTRIBUTES": {"MANUFACTURER": True, "SOLAR_CAPACITY_MW": 500}
    },

    # ============ VIETNAM ALUMINUM (LEGITIMATE) CASE ============
    # Level 1: Established Vietnamese aluminum manufacturer
    {
        "DATA_SOURCE": "CBP-DEMO",
        "RECORD_TYPE": "ORGANIZATION",
        "RECORD_ID": "vietnam-aluminum-corp",
        "NAMES": [{"NAME_TYPE": "PRIMARY", "NAME_ORG": "Vietnam Aluminum Corporation"}],
        "ADDRESSES": [{"ADDR_FULL": "555 Nguyen Hue Boulevard, Ho Chi Minh City, Vietnam"}],
        "COUNTRIES": [{"REGISTRATION_COUNTRY": "VN"}],
        "ATTRIBUTES": {
            "SHIPPER_AGE_MONTHS": 192,
            "INCORPORATION_DATE": "2009-03-15",
            "BUSINESS_TYPE": "ALUMINUM_MANUFACTURER",
            "CAPACITY_MT": 75000
        }
    },

    # ============ CANADIAN ALUMINUM CASE (TEST SHIPMENT) ============
    # Level 1: Canadian shipper (direct shipper of semiconductors via transshipment)
    {
        "DATA_SOURCE": "CBP-DEMO",
        "RECORD_TYPE": "ORGANIZATION",
        "RECORD_ID": "canadian-aluminum-ca",
        "NAMES": [{"NAME_TYPE": "PRIMARY", "NAME_ORG": "Canadian Aluminum Inc."}],
        "ADDRESSES": [{"ADDR_FULL": "2847 Industrial Park Road, Toronto, Ontario, Canada"}],
        "COUNTRIES": [{"REGISTRATION_COUNTRY": "CA"}],
        "ATTRIBUTES": {
            "SHIPPER_AGE_MONTHS": 6,
            "INCORPORATION_DATE": "2025-11-15",
            "BUSINESS_TYPE": "TRADING_COMPANY",
            "RISK_LEVEL": "HIGH",
            "RISK_JUSTIFICATION": "NEW_ENTITY_RULE: Age <2 years (H1 Rule 1-003). HIDDEN_PARENT: Beneficial owner obscurity detected via corporate structure analysis (H3 Rule 3-003). OFAC_WATCHLIST: Matched to OFAC SDN List on 2026-03-15."
        },
        "OFAC_STATUS": "WATCH",
        "OFAC_MATCHED_DATE": "2026-03-15",
        "OPEN_SANCTIONS": ["Office of Foreign Assets Control - Watchlist"]
    },
    # Level 2: Chinese hidden parent (Element 9 mismatch)
    {
        "DATA_SOURCE": "CBP-DEMO",
        "RECORD_TYPE": "ORGANIZATION",
        "RECORD_ID": "chinese-semiconductor-cn",
        "NAMES": [{"NAME_TYPE": "PRIMARY", "NAME_ORG": "Shenzhen Semiconductor Manufacturing Co., Ltd."}],
        "ADDRESSES": [{"ADDR_FULL": "789 Tech Park Road, Shenzhen, Guangdong, China"}],
        "COUNTRIES": [{"REGISTRATION_COUNTRY": "CN"}],
        "ATTRIBUTES": {
            "SHIPPER_AGE_MONTHS": 24,
            "INCORPORATION_DATE": "2024-05-10",
            "BUSINESS_TYPE": "SEMICONDUCTOR_MANUFACTURER",
            "CAPACITY_UNITS": 100000,
            "RISK_LEVEL": "CRITICAL",
            "RISK_JUSTIFICATION": "OFAC_BLOCKED_ENTITY: Matched to Unverified End-User (UEL) list (Department of Commerce BIS) on 2025-08-22. EXPORT_CONTROL_VIOLATION: Listed in Commerce Control List (EAR Part 774) — semiconductor manufacturing equipment controlled for China. SANCTIONS_EXPOSURE: Entity subject to OFAC Iran Sanctions Program (OP-ICP) for indirect Iran supply chain involvement detected 2025-10-01. CRITICAL_COUNTRY: China origin (CN) with sensitive technology category (HS 8541 semiconductors). RECOMMENDED_ACTION: ENTRY DENIAL per 19 USC § 1581."
        },
        "OFAC_STATUS": "BLOCKED",
        "OFAC_MATCHED_DATE": "2025-08-22",
        "BIS_MATCHED_DATE": "2025-08-22",
        "OFAC_PROGRAMS": ["Iran Sanctions Program (OP-ICP)", "Entity List"],
        "OPEN_SANCTIONS": ["Unverified End-User List (BIS)", "Commerce Control List (EAR)", "Iran Sanctions Program"]
    },
    # Consignee: US distributor (Gulf Coast Industrial)
    {
        "DATA_SOURCE": "CBP-DEMO",
        "RECORD_TYPE": "ORGANIZATION",
        "RECORD_ID": "gulf-coast-industrial-us",
        "NAMES": [{"NAME_TYPE": "PRIMARY", "NAME_ORG": "Gulf Coast Industrial"}],
        "ADDRESSES": [{"ADDR_FULL": "4201 Port Avenue, Newark, New Jersey 07114, USA"}],
        "COUNTRIES": [{"REGISTRATION_COUNTRY": "US"}],
        "ATTRIBUTES": {
            "IMPORTER": True,
            "DISTRIBUTOR": True,
            "BUSINESS_TYPE": "ELECTRONICS_IMPORTER"
        },
        "OFAC_STATUS": "CLEAR"
    },
]


def get_demo_entities() -> List[Dict[str, Any]]:
    """Return list of demo entities for Senzing loading."""
    return DEMO_ENTITIES


def get_demo_relationships() -> List[Dict[str, str]]:
    """Return relationships between demo entities.

    Format: (entity_id_a, entity_id_b, relationship_type)
    """
    return [
        # GREENFIELD CHAIN
        ("greenfield-vn-001", "greenfield-hk-holding", "OWNED_BY"),
        ("greenfield-hk-holding", "greenfield-cn-mfg", "OWNED_BY"),
        ("greenfield-vn-001", "mv-pacific-horizon", "SHIPS_VIA"),
        ("greenfield-vn-001", "sunpath-energy-nj", "SHIPS_TO"),

        # SOLARIA CHAIN
        ("solaria-my-001", "solaria-cn-parent", "OWNED_BY"),
        ("solaria-my-001", "sunpath-energy-nj", "SHIPS_TO"),  # Same consignee!

        # VIETNAM ALUMINUM (no parent - established independent company)

        # CANADIAN ALUMINUM CHAIN (TEST SHIPMENT SHP-000731)
        ("canadian-aluminum-ca", "chinese-semiconductor-cn", "OWNED_BY"),  # Hidden Chinese parent
        ("canadian-aluminum-ca", "gulf-coast-industrial-us", "SHIPS_TO"),   # Direct consignee
    ]


def seed_demo_entities(conn, cursor):
    """Load demo entities into Senzing database.

    Args:
        conn: SQLite connection
        cursor: SQLite cursor
    """
    import logging
    logger = logging.getLogger(__name__)

    # Insert entities
    for entity in DEMO_ENTITIES:
        entity_id = f"{entity['DATA_SOURCE']}:{entity['RECORD_ID']}"

        # Extract name
        names = entity.get("NAMES", [])
        name_primary = names[0].get("NAME_ORG", "") if names else ""

        # Extract country
        countries = entity.get("COUNTRIES", [])
        country = countries[0].get("REGISTRATION_COUNTRY", "") if countries else ""

        # Get entity type
        record_type = entity.get("RECORD_TYPE", "ORGANIZATION")

        try:
            cursor.execute("""
                INSERT OR REPLACE INTO senzing_entities
                (entity_id, data_source, record_id, name_primary, country, entity_type, confidence, raw_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                entity_id,
                entity["DATA_SOURCE"],
                entity["RECORD_ID"],
                name_primary,
                country,
                record_type.lower(),
                1.0,
                json.dumps(entity)
            ))
        except Exception as e:
            logger.error(f"Failed to insert demo entity {entity_id}: {e}")

    # Insert relationships
    for entity_id_a, entity_id_b, rel_type in get_demo_relationships():
        entity_a = f"CBP-DEMO:{entity_id_a}"
        entity_b = f"CBP-DEMO:{entity_id_b}"

        try:
            cursor.execute("""
                INSERT INTO senzing_relationships
                (entity_id_a, entity_id_b, relationship_type, confidence)
                VALUES (?, ?, ?, ?)
            """, (entity_a, entity_b, rel_type, 0.95))
        except Exception as e:
            logger.error(f"Failed to insert relationship {entity_a} -> {entity_b}: {e}")

    conn.commit()
    logger.info(f"✓ Seeded {len(DEMO_ENTITIES)} demo entities with {len(get_demo_relationships())} relationships")
