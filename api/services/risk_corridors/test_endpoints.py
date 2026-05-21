"""
Test suite for Risk Corridor API endpoints
"""
import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from main import app
from services.risk_corridors.db import init_risk_corridor_tables

client = TestClient(app)


class TestRiskCorridorIndex:
    """Tests for GET /api/risk-corridors"""

    def test_list_risk_corridors_no_filters(self):
        """Test getting all risk corridors"""
        response = client.get("/api/risk-corridors")
        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "corridors" in data
        assert "summary" in data
        assert isinstance(data["corridors"], list)
        assert isinstance(data["summary"], dict)

        # Verify summary fields
        assert "total_active_corridors" in data["summary"]
        assert "high_risk_count" in data["summary"]
        assert "aggregate_manifest_value" in data["summary"]

    def test_list_risk_corridors_with_industry_filter(self):
        """Test filtering by industry code"""
        response = client.get("/api/risk-corridors?industry_filter=7604,8541")
        assert response.status_code == 200
        data = response.json()

        assert "corridors" in data
        assert len(data["corridors"]) >= 0  # May be empty if no matching data

    def test_list_risk_corridors_with_time_period(self):
        """Test different time periods"""
        for period in ["7d", "14d", "30d"]:
            response = client.get(f"/api/risk-corridors?time_period={period}")
            assert response.status_code == 200
            data = response.json()
            assert "corridors" in data
            assert "summary" in data

    def test_corridor_response_schema(self):
        """Test that corridor objects have expected fields"""
        response = client.get("/api/risk-corridors")
        assert response.status_code == 200
        data = response.json()

        if len(data["corridors"]) > 0:
            corridor = data["corridors"][0]
            required_fields = [
                "corridor_id",
                "hts_chapter",
                "industry_segment",
                "origin_country",
                "destination_country",
                "supplier_entity",
                "shipment_count",
                "aggregate_value_usd",
                "yoy_volume_surge_pct",
                "yoy_value_surge_pct",
                "macro_volumetric_delta",
                "ad_cvd_rate_pct",
                "active_vessels",
                "risk_level",
                "last_updated",
            ]
            for field in required_fields:
                assert field in corridor, f"Missing field: {field}"

            # Verify macro_volumetric_delta structure
            assert "status" in corridor["macro_volumetric_delta"]
            assert "outbound_volume_manifest_tons" in corridor["macro_volumetric_delta"]
            assert "estimated_domestic_capacity_tons" in corridor["macro_volumetric_delta"]
            assert "ratio" in corridor["macro_volumetric_delta"]
            assert "signal" in corridor["macro_volumetric_delta"]

            # Verify risk level
            assert corridor["risk_level"] in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]


class TestRiskCorridorDetail:
    """Tests for GET /api/risk-corridors/{corridor_id}"""

    def test_get_corridor_detail(self):
        """Test getting corridor detail"""
        # First get a corridor ID
        response = client.get("/api/risk-corridors")
        data = response.json()

        if len(data["corridors"]) > 0:
            corridor_id = data["corridors"][0]["corridor_id"]

            # Fetch detail
            response = client.get(f"/api/risk-corridors/{corridor_id}")
            assert response.status_code == 200

            detail = response.json()
            assert "corridor" in detail
            assert "entity_chain" in detail

    def test_corridor_detail_with_include_params(self):
        """Test corridor detail with include parameters"""
        # First get a corridor ID
        response = client.get("/api/risk-corridors")
        data = response.json()

        if len(data["corridors"]) > 0:
            corridor_id = data["corridors"][0]["corridor_id"]

            response = client.get(
                f"/api/risk-corridors/{corridor_id}?include=vessel_activity,entity_chain,ftz_events"
            )
            assert response.status_code == 200

    def test_corridor_detail_not_found(self):
        """Test 404 for non-existent corridor"""
        response = client.get("/api/risk-corridors/HC-9999-ZZZZ-XXX")
        assert response.status_code == 404

    def test_corridor_detail_structure(self):
        """Test corridor detail response structure"""
        response = client.get("/api/risk-corridors")
        data = response.json()

        if len(data["corridors"]) > 0:
            corridor_id = data["corridors"][0]["corridor_id"]
            response = client.get(f"/api/risk-corridors/{corridor_id}")
            detail = response.json()

            # Verify corridor structure
            corridor = detail["corridor"]
            assert "corridor_id" in corridor
            assert "active_vessels" in corridor
            assert isinstance(corridor["active_vessels"], list)

            # Verify entity chain structure
            chain = detail["entity_chain"]
            assert "level_1" in chain
            assert "relationships" in chain
            assert isinstance(chain["relationships"], list)


class TestVesselsOfInterest:
    """Tests for GET /api/ports/{port_code}/vessels-of-interest"""

    def test_vessels_by_port(self):
        """Test getting vessels of interest by port"""
        port_code = "USLA"
        response = client.get(f"/api/ports/{port_code}/vessels-of-interest")
        assert response.status_code == 200

        data = response.json()
        assert "port" in data
        assert "port_name" in data
        assert "vessels_of_interest" in data
        assert "summary" in data

        assert data["port"] == port_code

    def test_vessels_by_port_with_time_window(self):
        """Test vessels endpoint with different time windows"""
        for window in ["7d", "14d", "30d"]:
            response = client.get(f"/api/ports/USLA/vessels-of-interest?time_window={window}")
            assert response.status_code == 200
            data = response.json()
            assert "vessels_of_interest" in data

    def test_vessels_by_port_with_risk_filter(self):
        """Test filtering vessels by risk level"""
        for risk in ["HIGH", "MEDIUM", "LOW"]:
            response = client.get(
                f"/api/ports/USLA/vessels-of-interest?risk_filter={risk}"
            )
            assert response.status_code == 200
            data = response.json()
            assert "vessels_of_interest" in data

    def test_vessel_of_interest_structure(self):
        """Test vessel of interest response structure"""
        response = client.get("/api/ports/USLA/vessels-of-interest")
        assert response.status_code == 200

        data = response.json()
        if len(data["vessels_of_interest"]) > 0:
            vessel = data["vessels_of_interest"][0]
            required_fields = [
                "vessel_id",
                "vessel_name",
                "eta",
                "status",
                "cargo_risk_level",
                "cargo_summary",
                "route_anomalies",
                "recommended_actions",
            ]
            for field in required_fields:
                assert field in vessel, f"Missing field: {field}"

        # Verify summary structure
        summary = data["summary"]
        assert "total_vessels_at_port" in summary
        assert "vessels_of_interest" in summary
        assert "high_risk_count" in summary
        assert "exam_capacity_available" in summary


class TestTimelineEndpoint:
    """Tests for GET /api/risk-corridors/{corridor_id}/timeline"""

    def test_timeline_basic(self):
        """Test getting corridor timeline"""
        # First get a corridor ID
        response = client.get("/api/risk-corridors")
        data = response.json()

        if len(data["corridors"]) > 0:
            corridor_id = data["corridors"][0]["corridor_id"]

            # Set date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=7)

            response = client.get(
                f"/api/risk-corridors/{corridor_id}/timeline?"
                f"start_date={start_date.strftime('%Y-%m-%d')}&"
                f"end_date={end_date.strftime('%Y-%m-%d')}"
            )
            assert response.status_code == 200

            data = response.json()
            assert "corridor_id" in data
            assert "timeline_snapshots" in data
            assert "entity_evolution" in data

    def test_timeline_with_granularity(self):
        """Test timeline with different granularities"""
        response = client.get("/api/risk-corridors")
        data = response.json()

        if len(data["corridors"]) > 0:
            corridor_id = data["corridors"][0]["corridor_id"]
            end_date = datetime.now()
            start_date = end_date - timedelta(days=7)

            for granularity in ["daily", "weekly", "monthly"]:
                response = client.get(
                    f"/api/risk-corridors/{corridor_id}/timeline?"
                    f"start_date={start_date.strftime('%Y-%m-%d')}&"
                    f"end_date={end_date.strftime('%Y-%m-%d')}&"
                    f"granularity={granularity}"
                )
                assert response.status_code == 200

    def test_timeline_invalid_dates(self):
        """Test timeline with invalid date ranges"""
        response = client.get("/api/risk-corridors")
        data = response.json()

        if len(data["corridors"]) > 0:
            corridor_id = data["corridors"][0]["corridor_id"]

            # Start after end
            response = client.get(
                f"/api/risk-corridors/{corridor_id}/timeline?"
                f"start_date=2026-05-20&end_date=2026-05-10"
            )
            assert response.status_code == 400

    def test_timeline_structure(self):
        """Test timeline response structure"""
        response = client.get("/api/risk-corridors")
        data = response.json()

        if len(data["corridors"]) > 0:
            corridor_id = data["corridors"][0]["corridor_id"]
            end_date = datetime.now()
            start_date = end_date - timedelta(days=7)

            response = client.get(
                f"/api/risk-corridors/{corridor_id}/timeline?"
                f"start_date={start_date.strftime('%Y-%m-%d')}&"
                f"end_date={end_date.strftime('%Y-%m-%d')}"
            )
            assert response.status_code == 200

            data = response.json()
            if len(data["timeline_snapshots"]) > 0:
                snapshot = data["timeline_snapshots"][0]
                assert "date" in snapshot
                assert "shipment_count" in snapshot
                assert "aggregate_value_usd" in snapshot
                assert "active_entities" in snapshot
                assert "active_vessels" in snapshot
                assert "notable_events" in snapshot


class TestFeedbackOverride:
    """Tests for POST /api/feedback/override"""

    def test_submit_feedback_override(self):
        """Test submitting feedback override"""
        payload = {
            "shipment_id": "MANIFEST-GRF-001",
            "corridor_id": "HC-7604-VNUS-GDF",
            "risk_score_original": 91.0,
            "override_action": "MARK_FALSE_POSITIVE",
            "justification_category": "VERIFIED_LABOR_STRIKE_PORT_DELAY",
            "justification_detail": "Port of Guangzhou labor action caused extended dwell; not transshipment.",
            "officer_id": "CBP-12345",
            "override_timestamp": datetime.now().isoformat(),
        }

        response = client.post("/api/feedback/override", json=payload)
        assert response.status_code == 201

        data = response.json()
        assert "override_id" in data
        assert "status" in data
        assert data["status"] == "LOGGED"
        assert "feedback_stored_for_model_retraining" in data
        assert data["feedback_stored_for_model_retraining"] is True
        assert "next_model_training_window" in data

    def test_feedback_override_actions(self):
        """Test different override actions"""
        actions = [
            "MARK_FALSE_POSITIVE",
            "MARK_TRUE_POSITIVE",
            "REQUEST_FOLLOW_UP",
        ]

        for action in actions:
            payload = {
                "shipment_id": "MANIFEST-TEST-001",
                "corridor_id": "HC-7604-VNUS-GDF",
                "risk_score_original": 75.0,
                "override_action": action,
                "justification_category": "OTHER",
                "justification_detail": f"Test {action}",
                "officer_id": "CBP-TEST",
                "override_timestamp": datetime.now().isoformat(),
            }

            response = client.post("/api/feedback/override", json=payload)
            assert response.status_code == 201
            assert response.json()["status"] == "LOGGED"

    def test_feedback_override_categories(self):
        """Test different justification categories"""
        categories = [
            "VERIFIED_LABOR_STRIKE_PORT_DELAY",
            "VERIFIED_CAPACITY_EXPANSION",
            "VERIFIED_MISCLASSIFIED_VESSEL",
            "SUSPECTED_TRANSSHIPMENT",
            "SUSPECTED_EVASION_NETWORK",
            "OTHER",
        ]

        for category in categories:
            payload = {
                "shipment_id": "MANIFEST-CAT-001",
                "corridor_id": "HC-7604-VNUS-GDF",
                "risk_score_original": 80.0,
                "override_action": "MARK_FALSE_POSITIVE",
                "justification_category": category,
                "justification_detail": f"Test {category}",
                "officer_id": "CBP-TEST",
                "override_timestamp": datetime.now().isoformat(),
            }

            response = client.post("/api/feedback/override", json=payload)
            assert response.status_code == 201


if __name__ == "__main__":
    # Run tests
    init_risk_corridor_tables()
    pytest.main([__file__, "-v"])
