"""Tests for API routes."""
import json
import pytest
from app import create_app


@pytest.fixture
def client():
    """Create test client."""
    app = create_app("testing")
    with app.test_client() as client:
        yield client


class TestHealthCheck:
    """Test health check endpoint."""

    def test_health_check(self, client):
        """Test health endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["status"] == "healthy"
        assert data["service"] == "precise-risk-engine-api"
        assert data["port"] == 8004


class TestScoringEndpoints:
    """Test scoring endpoints."""

    def test_score_entity_success(self, client):
        """Test scoring a single entity."""
        payload = {
            "entity_id": "entity_001",
            "entity_data": {
                "entity_risk_score": 25,
                "historical_violation_count": 5,
                "connectivity_score": 40,
                "trade_frequency_anomaly": 35,
                "sanctioned_status": 0,
                "jurisdiction_risk": 20,
                "product_sensitivity": 15,
            },
        }
        response = client.post(
            "/api/v1/scoring/score",
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert "score" in data
        assert data["entity_id"] == "entity_001"
        assert "factors" in data
        assert "gates" in data
        assert "rules" in data

    def test_score_entity_missing_id(self, client):
        """Test scoring with missing entity_id."""
        payload = {
            "entity_data": {
                "entity_risk_score": 25,
            },
        }
        response = client.post(
            "/api/v1/scoring/score",
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_batch_score_success(self, client):
        """Test batch scoring multiple entities."""
        payload = {
            "entities": [
                {
                    "entity_id": "entity_001",
                    "entity_data": {
                        "entity_risk_score": 25,
                        "historical_violation_count": 5,
                        "connectivity_score": 40,
                        "trade_frequency_anomaly": 35,
                        "sanctioned_status": 0,
                        "jurisdiction_risk": 20,
                        "product_sensitivity": 15,
                    },
                },
                {
                    "entity_id": "entity_002",
                    "entity_data": {
                        "entity_risk_score": 80,
                        "historical_violation_count": 50,
                        "connectivity_score": 75,
                        "trade_frequency_anomaly": 65,
                        "sanctioned_status": 100,
                        "jurisdiction_risk": 70,
                        "product_sensitivity": 85,
                    },
                },
            ]
        }
        response = client.post(
            "/api/v1/scoring/batch-score",
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["entities_scored"] == 2
        assert len(data["results"]) == 2

    def test_clear_cache(self, client):
        """Test cache clearing."""
        response = client.post("/api/v1/scoring/clear-cache")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert "message" in data


class TestRulesEndpoints:
    """Test rules management endpoints."""

    def test_list_rules(self, client):
        """Test listing rules."""
        response = client.get("/api/v1/rules/list")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert "rules_count" in data
        assert data["rules_count"] == 8  # Based on cbp.yaml
        assert "rules" in data

    def test_get_rule(self, client):
        """Test getting a specific rule."""
        response = client.get("/api/v1/rules/rule_01_high_volume_low_history")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["name"] == "rule_01_high_volume_low_history"
        assert "condition" in data
        assert "action" in data

    def test_get_nonexistent_rule(self, client):
        """Test getting a nonexistent rule."""
        response = client.get("/api/v1/rules/nonexistent_rule")
        assert response.status_code == 404

    def test_rules_by_severity(self, client):
        """Test filtering rules by severity."""
        response = client.get("/api/v1/rules/severity/high")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["severity_level"] == "high"
        assert "rules_count" in data


class TestFeedbackEndpoints:
    """Test feedback endpoints."""

    def test_submit_feedback(self, client):
        """Test submitting feedback."""
        payload = {
            "entity_id": "entity_001",
            "predicted_score": 45.5,
            "actual_outcome": "low_risk",
            "correction_score": 35.0,
            "notes": "Test feedback",
        }
        response = client.post(
            "/api/v1/feedback/submit",
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert response.status_code == 201
        data = json.loads(response.data)
        assert "id" in data
        assert data["entity_id"] == "entity_001"

    def test_submit_feedback_missing_entity_id(self, client):
        """Test submitting feedback without entity_id."""
        payload = {
            "predicted_score": 45.5,
        }
        response = client.post(
            "/api/v1/feedback/submit",
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_list_feedback(self, client):
        """Test listing feedback."""
        # Submit some feedback first
        payload = {
            "entity_id": "entity_001",
            "predicted_score": 45.5,
            "actual_outcome": "low_risk",
        }
        client.post(
            "/api/v1/feedback/submit",
            data=json.dumps(payload),
            content_type="application/json",
        )

        response = client.get("/api/v1/feedback/list")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert "feedback" in data
        assert "total" in data

    def test_analyze_feedback(self, client):
        """Test feedback analysis."""
        response = client.post("/api/v1/feedback/analyze")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert "total_feedback" in data
        assert "average_correction_magnitude" in data


class TestMetricsEndpoints:
    """Test metrics endpoints."""

    def test_metrics_summary(self, client):
        """Test metrics summary."""
        response = client.get("/api/v1/metrics/summary")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert "scores_computed" in data
        assert "cache_hits" in data
        assert "total_requests" in data

    def test_model_info(self, client):
        """Test model info endpoint."""
        response = client.get("/api/v1/metrics/model-info")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert "model_info" in data
        model_info = data["model_info"]
        assert model_info["factors_count"] == 7
        assert model_info["gates_count"] == 3
        assert model_info["rules_count"] == 8

    def test_factors_endpoint(self, client):
        """Test factors endpoint."""
        response = client.get("/api/v1/metrics/factors")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["factors_count"] == 7
        assert "factors" in data
        assert "weights" in data

    def test_gates_endpoint(self, client):
        """Test gates endpoint."""
        response = client.get("/api/v1/metrics/gates")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["gates_count"] == 3
        assert "gates" in data

    def test_drift_report(self, client):
        """Test drift detection report."""
        response = client.get("/api/v1/metrics/drift-report")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert "drift_report" in data

    def test_record_performance(self, client):
        """Test performance recording."""
        payload = {
            "operation": "score",
            "duration_ms": 45.5,
            "entity_count": 1,
            "success": True,
        }
        response = client.post(
            "/api/v1/metrics/performance",
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert response.status_code == 200

    def test_reset_metrics(self, client):
        """Test metrics reset."""
        response = client.post("/api/v1/metrics/reset")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert "message" in data
