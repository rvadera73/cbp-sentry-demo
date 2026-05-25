"""Integration tests for Cloud Run staging environment.

Run these tests against a deployed Cloud Run instance:
  pytest -m integration services/api/tests/test_integration_staging.py -v

Requires environment variable: STAGING_API_URL
Example: STAGING_API_URL=https://sentry-api-staging.run.app pytest -m integration
"""

import os
import pytest
import httpx

pytestmark = pytest.mark.integration


@pytest.fixture
def staging_url():
    """Get staging API URL from environment."""
    url = os.getenv("STAGING_API_URL")
    if not url:
        pytest.skip("STAGING_API_URL not set. Example: STAGING_API_URL=https://sentry-api-staging.run.app")
    return url.rstrip("/")


@pytest.fixture
async def async_client(staging_url):
    """Create async HTTP client for staging."""
    async with httpx.AsyncClient(base_url=staging_url, timeout=10.0) as client:
        yield client


@pytest.mark.asyncio
async def test_api_health(async_client):
    """Test API health endpoint."""
    response = await async_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "sentry-api"


@pytest.mark.asyncio
async def test_data_service_health(async_client):
    """Test data service is accessible and healthy."""
    response = await async_client.get("/api/data/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_list_shipments(async_client):
    """Test listing shipments endpoint."""
    response = await async_client.get("/api/shipments?limit=10")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "count" in data
    # Should have some shipments from manifest
    assert data["count"] > 0


@pytest.mark.asyncio
async def test_shipment_detail(async_client):
    """Test getting a specific shipment by ID."""
    # First, get a list of shipments
    list_response = await async_client.get("/api/shipments?limit=1")
    assert list_response.status_code == 200
    shipments = list_response.json()["data"]
    assert len(shipments) > 0

    # Get the first shipment detail
    shipment_id = shipments[0]["id"]
    detail_response = await async_client.get(f"/api/shipments/{shipment_id}")
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["id"] == shipment_id
    assert "risk_score" in detail


@pytest.mark.asyncio
async def test_shipment_not_found(async_client):
    """Test that querying non-existent shipment returns 404."""
    response = await async_client.get("/api/shipments/NONEXISTENT-12345")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_shipment_has_manifest_ids(async_client):
    """Test that manifest JSON was loaded with SHP-* IDs."""
    response = await async_client.get("/api/shipments?limit=5")
    assert response.status_code == 200
    data = response.json()
    shipments = data["data"]

    # Verify all IDs follow SHP-* pattern (not hardcoded shipment-* pattern)
    for shipment in shipments:
        assert shipment["id"].startswith(
            "SHP-"
        ), f"Shipment ID {shipment['id']} does not match SHP-* pattern. Database may not be seeded with manifest JSON."


@pytest.mark.asyncio
async def test_score_consistency_between_list_and_detail(async_client):
    """Test that risk_score is consistent between list and detail views.

    This was the "95 vs 11" bug: list and detail views returned different scores.
    The fix ensures database has the same score in all views.
    """
    # Get list view
    list_response = await async_client.get("/api/shipments?limit=5")
    assert list_response.status_code == 200
    shipments = list_response.json()["data"]

    for shipment in shipments:
        shipment_id = shipment["id"]
        list_score = shipment.get("risk_score")

        # Get detail view
        detail_response = await async_client.get(f"/api/shipments/{shipment_id}")
        assert detail_response.status_code == 200
        detail = detail_response.json()
        detail_score = detail.get("risk_score")

        # Scores should match
        assert list_score == detail_score, f"Score mismatch for {shipment_id}: list={list_score}, detail={detail_score}"


@pytest.mark.asyncio
async def test_shipment_statistics(async_client):
    """Test shipment statistics endpoint."""
    response = await async_client.get("/api/stats")
    assert response.status_code == 200
    stats = response.json()

    # Should have basic statistics
    assert "total_shipments" in stats
    assert stats["total_shipments"] > 0
    assert "high_risk_count" in stats
    assert "medium_risk_count" in stats
    assert "low_risk_count" in stats


@pytest.mark.asyncio
async def test_shipment_search(async_client):
    """Test shipment search endpoint."""
    response = await async_client.get("/api/shipments/search?q=greenfield")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "count" in data
    # May or may not have results depending on seed data


@pytest.mark.asyncio
async def test_h1_scoring_available(async_client):
    """Test that H1 corridor risk scoring is available."""
    # Get a shipment
    list_response = await async_client.get("/api/shipments?limit=1")
    assert list_response.status_code == 200
    shipments = list_response.json()["data"]

    if shipments:
        shipment = shipments[0]
        # Test that shipment has corridor-related fields
        assert "origin_country" in shipment
        assert "destination_country" in shipment


@pytest.mark.asyncio
async def test_h2_isf_fields_available(async_client):
    """Test that H2 ISF Element 9 fields are available from manifest."""
    list_response = await async_client.get("/api/shipments?limit=10")
    assert list_response.status_code == 200
    shipments = list_response.json()["data"]

    # At least some shipments should have ISF fields
    isf_shipments = [s for s in shipments if s.get("element_9") or s.get("ais_stuffing_country")]
    assert len(isf_shipments) > 0, "No shipments have ISF Element 9 or AIS stuffing country data"


@pytest.mark.asyncio
async def test_database_connection_via_data_service(async_client):
    """Test that API can reach database service."""
    # Get a shipment - this proves the data chain works
    response = await async_client.get("/api/shipments?limit=1")
    assert response.status_code == 200

    # If we got here, the API successfully queried the data service's database
    data = response.json()
    assert data["count"] > 0, "Database appears to be empty"


@pytest.mark.asyncio
async def test_service_to_service_connectivity(staging_url):
    """Test that services can communicate (API → Data Service)."""
    # This is tested indirectly via /api/shipments which queries the data service
    async with httpx.AsyncClient(base_url=staging_url, timeout=10.0) as client:
        response = await client.get("/api/shipments?limit=1")
        assert response.status_code == 200
        # If the API couldn't reach the data service, we'd get a 503 or error


@pytest.mark.asyncio
async def test_manifest_json_loaded_not_hardcoded_data(async_client):
    """Test single source of truth: manifest JSON was loaded, not hardcoded data.

    This verifies the fix for the "case not found" error where hardcoded fallback data
    (shipment-greenfield-001, etc.) was being used instead of manifest JSON data (SHP-*).
    """
    response = await async_client.get("/api/shipments?limit=1000")
    assert response.status_code == 200
    data = response.json()
    shipments = data["data"]

    # Should have many shipments (1,191+ from manifest)
    assert (
        data["count"] > 100
    ), f"Only {data['count']} shipments found. Expected 1,191+ from manifest. Database may have fallback data."

    # All should have SHP-* IDs (manifest), not shipment-* (hardcoded)
    for shipment in shipments:
        shipment_id = shipment["id"]
        assert shipment_id.startswith(
            "SHP-"
        ), f"Found hardcoded ID pattern {shipment_id}. Database should only contain manifest JSON data (SHP-*)"
        assert not shipment_id.startswith(
            "shipment-"
        ), f"Found hardcoded fallback ID {shipment_id}. This indicates fallback data is being used instead of manifest."
