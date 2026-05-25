"""Test CORD client connectivity and entity resolution.

Run this to verify:
1. CORD microservice is running and accessible
2. CORDClient can successfully resolve entities
3. Response format matches Entity[] interface expectations
"""

import pytest
import asyncio
from services.referral.cord_client import CORDClient
from services.referral.entity_graph_service import EntityGraphService


@pytest.mark.asyncio
async def test_cord_health():
    """Test CORD microservice health check."""
    client = CORDClient()
    health = await client.get_health()

    assert health is not None, "CORD health check failed - is sentry-cord-integration:8004 running?"
    assert health.get("status") == "ready", f"CORD not ready: {health}"
    assert health.get("entity_count", 0) > 100000, f"CORD entity count too low: {health}"


@pytest.mark.asyncio
async def test_cord_resolve_greenfield():
    """Test resolving Greenfield Industrial entity chain."""
    client = CORDClient()

    response = await client.resolve_shipment_entities(
        shipper_name="Greenfield Industrial Trading Co., Ltd.",
        shipper_country="VN",
        consignee_name="SunPath Energy Distributors LLC",
        consignee_country="US",
    )

    assert response is not None, "CORD resolution failed"
    assert "level_1" in response, "Missing level_1 in response"
    assert response["level_1"]["name"] is not None
    assert response["level_1"]["country"] == "VN"
    assert response["level_1"]["confidence"] > 0.8

    # Check relationships
    assert "related_entities" in response["level_1"], "Missing related_entities"
    assert len(response["level_1"]["related_entities"]) > 0, "No relationships found"


@pytest.mark.asyncio
async def test_entity_graph_transformation():
    """Test transforming CORD response to Entity[] format."""
    # Mock CORD response
    cord_response = {
        "level_1": {
            "entity_id": "ENT-GF-VN-001",
            "name": "Greenfield Industrial Trading Co., Ltd.",
            "country": "VN",
            "confidence": 0.98,
            "data_source": "CORD",
            "entity_type": "SHIPPER",
            "related_entities": [
                {
                    "entity_id": "ENT-GF-HK-001",
                    "name": "Greenfield Global Metals Holdings Ltd.",
                    "relationship": "OWNED_BY",
                    "confidence": 0.95,
                }
            ],
        },
        "level_2": {
            "entity_id": "ENT-GF-HK-001",
            "name": "Greenfield Global Metals Holdings Ltd.",
            "country": "HK",
            "confidence": 0.95,
            "data_source": "CORD",
            "entity_type": "HOLDING_COMPANY",
            "related_entities": [
                {
                    "entity_id": "ENT-GF-CN-001",
                    "name": "Guangdong Greenfield Aluminum Mfg. Co., Ltd.",
                    "relationship": "PARENT_COMPANY",
                    "confidence": 0.93,
                }
            ],
        },
        "level_3": {
            "entity_id": "ENT-GF-CN-001",
            "name": "Guangdong Greenfield Aluminum Mfg. Co., Ltd.",
            "country": "CN",
            "confidence": 0.93,
            "data_source": "CORD",
            "entity_type": "MANUFACTURER",
            "risk_score": 85,
        },
        "ofac_detected": False,
        "risk_score": 72,
    }

    entity_graph = EntityGraphService.transform_cord_to_entity_chain(cord_response)

    # Verify structure
    assert "chain" in entity_graph
    assert "data_sources" in entity_graph
    assert "ofac_detected" in entity_graph
    assert "risk_score" in entity_graph

    # Verify chain
    chain = entity_graph["chain"]
    assert len(chain) == 3, f"Expected 3 levels, got {len(chain)}"

    # Verify Level 1 (Shipper)
    shipper = chain[0]
    assert shipper["entity_id"] == "ENT-GF-VN-001"
    assert shipper["name"] == "Greenfield Industrial Trading Co., Ltd."
    assert shipper["country"] == "VN"
    assert shipper["entity_type"] == "SHIPPER"
    assert shipper["role"] == "Shipper"
    assert shipper["confidence"] == 0.98
    assert len(shipper["relationships"]) > 0

    # Verify relationship
    rel = shipper["relationships"][0]
    assert rel["type"] == "OWNED_BY"
    assert rel["target"] == "Greenfield Global Metals Holdings Ltd."
    assert rel["confidence"] == 0.95

    # Verify Level 2 (Parent)
    parent = chain[1]
    assert parent["entity_type"] == "INTERMEDIARY"
    assert parent["role"] == "Parent Company"

    # Verify Level 3 (Manufacturer)
    mfr = chain[2]
    assert mfr["entity_type"] == "MANUFACTURER"
    assert mfr["role"] == "Manufacturer"
    assert "risk_score" in mfr


@pytest.mark.asyncio
async def test_end_to_end_cord_to_entity_graph():
    """Full test: CORD resolution → EntityGraphService transformation."""
    client = CORDClient()

    # Resolve real entity
    cord_response = await client.resolve_shipment_entities(
        shipper_name="Greenfield Industrial Trading Co., Ltd.",
        shipper_country="VN",
        consignee_name="SunPath Energy Distributors LLC",
        consignee_country="US",
    )

    if cord_response is None:
        pytest.skip("CORD service unavailable")

    # Transform to Entity[]
    entity_graph = EntityGraphService.transform_cord_to_entity_chain(cord_response)

    # Verify transformation
    assert entity_graph["chain"], "Empty chain after transformation"
    for entity in entity_graph["chain"]:
        assert "entity_id" in entity
        assert "name" in entity
        assert "country" in entity
        assert "entity_type" in entity
        assert "role" in entity
        assert "confidence" in entity
        assert "relationships" in entity


if __name__ == "__main__":
    # Run tests with: pytest api/tests/test_cord_client.py -v
    # Or run this file directly for quick check:
    print("Running CORD client tests...")
    print("\nNote: Start CORD service with:")
    print("  docker-compose up sentry-cord-integration")
    print("\nThen run tests with:")
    print("  cd api && pytest tests/test_cord_client.py -v -s")
