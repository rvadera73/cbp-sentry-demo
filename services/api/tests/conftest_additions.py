"""Additional fixtures for entity resolution testing"""
import pytest
from unittest.mock import MagicMock


@pytest.fixture
def greenfield_entities():
    """7-entity fixture with complete entity resolution data."""
    return {
        "shipper_vn": {
            "id": "ENT-VN-001",
            "name": "Greenfield Industrial Trading Co., Ltd.",
            "country": "VN",
            "jurisdiction": "VN",
            "type": "TRADING_COMPANY",
            "incorporated_date": "2025-01-15",
            "director": "Nguyen Van Hung",
            "phone": "+84-8-3826-8888",
            "address": "123 Nguyen Hue Blvd, Ho Chi Minh City, Vietnam",
            "registered": "2025-01-15",
            "prior_filings": 2,
            "senzing_record_id": "rec_vn_001",
            "senzing_confidence": 0.95,
            "risk_score": 45,
            "metadata": {"freight_forwarder": "Saigon Global Logistics", "source": "CBP Manifest"}
        },
        "sibling_vn": {
            "id": "ENT-VN-002",
            "name": "Greenfield Transport Services Co., Ltd.",
            "country": "VN",
            "jurisdiction": "VN",
            "type": "LOGISTICS",
            "incorporated_date": "2024-08-20",
            "director": "Nguyen Van Hung",
            "phone": "+84-8-3826-9999",
            "address": "456 Tran Hung Dao St, Ho Chi Minh City, Vietnam",
            "registered": "2024-08-20",
            "prior_filings": 1,
            "senzing_record_id": "rec_vn_002",
            "senzing_confidence": 0.88,
            "risk_score": 38,
            "metadata": {"freight_forwarder": "Saigon Global Logistics", "source": "CBP Manifest"}
        },
        "parent_hk": {
            "id": "ENT-HK-001",
            "name": "Greenfield Global Metals Holdings Ltd.",
            "country": "HK",
            "jurisdiction": "HK",
            "type": "HOLDING_COMPANY",
            "incorporated_date": "2024-10-15",
            "beneficial_owner": "Nguyen Van Hung",
            "phone": "+852-3500-8888",
            "address": "Level 28, Jardine House, Central, Hong Kong",
            "registered": "2024-10-15",
            "prior_filings": 5,
            "senzing_record_id": "rec_hk_001",
            "senzing_confidence": 0.92,
            "risk_score": 52,
            "metadata": {"freight_forwarder": "Saigon Global Logistics", "source": "CBP Manifest"}
        },
        "parent_cn": {
            "id": "ENT-CN-001",
            "name": "Guangdong Greenfield Aluminum Mfg. Co., Ltd.",
            "country": "CN",
            "jurisdiction": "CN",
            "type": "MANUFACTURER",
            "incorporated_date": "2023-06-10",
            "director": "Wang Haohui",
            "phone": "0757-8888-9999",
            "address": "Industrial Zone, Foshan, Guangdong, China",
            "registered": "2023-06-10",
            "prior_filings": 18,
            "senzing_record_id": "rec_cn_001",
            "senzing_confidence": 0.98,
            "risk_score": 68,
            "metadata": {"aluminum_exporter": True, "ad_cvd_history": True, "source": "CBP Manifest"}
        },
        "consignee_us": {
            "id": "ENT-US-001",
            "name": "TBD Importer LLC",
            "country": "US",
            "jurisdiction": "CA",
            "type": "IMPORTER",
            "incorporated_date": "2020-03-01",
            "director": "John Smith",
            "phone": "+1-213-555-0100",
            "address": "1000 W Olympic Blvd, Los Angeles, CA 90015",
            "registered": "2020-03-01",
            "prior_filings": 0,
            "senzing_record_id": "rec_us_001",
            "senzing_confidence": 0.85,
            "risk_score": 25,
            "metadata": {"source": "CBP Manifest"}
        },
        "vessel": {
            "id": "ENT-VESSEL-001",
            "name": "MV Pacific Horizon",
            "country": "PA",
            "jurisdiction": "PA",
            "type": "VESSEL",
            "incorporated_date": "2015-05-10",
            "imo_number": "9456789",
            "gross_tonnage": 52000,
            "phone": None,
            "address": "Panama",
            "registered": "2015-05-10",
            "prior_filings": 12,
            "senzing_record_id": "rec_vessel_001",
            "senzing_confidence": 0.99,
            "risk_score": 0,
            "metadata": {"source": "AIS Data"}
        },
        "port_terminal": {
            "id": "ENT-PORT-001",
            "name": "Nansha Terminal",
            "country": "CN",
            "jurisdiction": "CN",
            "type": "DISTRIBUTOR",
            "incorporated_date": "2010-01-01",
            "phone": None,
            "address": "Nansha, Guangzhou, China",
            "registered": "2010-01-01",
            "prior_filings": 0,
            "senzing_record_id": "rec_port_001",
            "senzing_confidence": 0.99,
            "risk_score": 15,
            "metadata": {"port_of_call": True, "dwell_days": 11.2, "anomaly_ratio": 5.3, "source": "Port Authority"}
        }
    }


@pytest.fixture
def mock_senzing():
    """Mock Senzing service client"""
    mock_client = MagicMock()

    def load_record_side_effect(record):
        entity_name = record.get("name", "unknown")
        return f"rec_{entity_name[:3].lower()}_001"

    mock_client.load_record = MagicMock(side_effect=load_record_side_effect)

    def search_entity_side_effect(entity_data):
        matches = []
        if "Greenfield" in entity_data.get("name", ""):
            if entity_data.get("country") == "VN":
                matches = [{
                    "record_id": "rec_cn_001",
                    "name": "Guangdong Greenfield Aluminum Mfg. Co., Ltd.",
                    "country": "CN",
                    "confidence": 0.98,
                    "match_key": "NAME_MATCH_ADMIN"
                }]
        return matches

    mock_client.search_entity = MagicMock(side_effect=search_entity_side_effect)

    def why_entities_side_effect(entity_a, entity_b):
        return {
            "why_key": "WHY_ENTITY_RES_CX",
            "entity_a": entity_a,
            "entity_b": entity_b,
            "confidence": 0.98,
            "match_factors": [
                {"match_key": "ADMIN", "score": 0.91, "detail": "Shared director: Nguyen Van Hung"},
                {"match_key": "PHONE", "score": 0.85, "detail": "Shared phone: +84-8-3826-8888"},
                {"match_key": "RELATIONSHIP", "score": 0.87, "detail": "Freight forwarder: Saigon Global Logistics"},
                {"match_key": "COMMERCIAL_RECORDS", "score": 0.98, "detail": "Prior CBP filings: 18"}
            ]
        }

    mock_client.why_entities = MagicMock(side_effect=why_entities_side_effect)

    def related_entities_side_effect(entity_id):
        related_map = {
            "rec_vn_001": ["rec_hk_001", "rec_cn_001"],
            "rec_hk_001": ["rec_vn_001", "rec_cn_001"],
            "rec_cn_001": ["rec_hk_001", "rec_vn_001", "rec_vn_002"]
        }
        return related_map.get(entity_id, [])

    mock_client.related_entities = MagicMock(side_effect=related_entities_side_effect)
    mock_client.health_check = MagicMock(return_value={"status": "ready"})

    return mock_client


@pytest.fixture
def mock_neo4j():
    """Mock Neo4j graph database session"""
    mock_session = MagicMock()

    created_nodes = []
    created_relationships = []

    def run_create_node(query, **params):
        created_nodes.append({"query": query, "params": params})
        return MagicMock(summary=MagicMock(counters=MagicMock(nodes_created=1)))

    def run_create_rel(query, **params):
        created_relationships.append({"query": query, "params": params})
        return MagicMock(summary=MagicMock(counters=MagicMock(relationships_created=1)))

    def run_query(query, **params):
        if "CREATE" in query and "RELATIONSHIP" in query:
            return run_create_rel(query, **params)
        elif "CREATE" in query:
            return run_create_node(query, **params)
        elif "MATCH" in query and "shortest" in query.lower():
            return [MagicMock(nodes=[
                MagicMock(id=1, labels=["Entity"], properties={"name": "VN Shipper"}),
                MagicMock(id=2, labels=["Entity"], properties={"name": "HK Holding"}),
                MagicMock(id=3, labels=["Entity"], properties={"name": "CN Manufacturer"})
            ])]
        return []

    mock_session.run = MagicMock(side_effect=run_query)
    mock_session.write_transaction = MagicMock()
    mock_session.read_transaction = MagicMock()
    mock_session.created_nodes = created_nodes
    mock_session.created_relationships = created_relationships

    return mock_session
