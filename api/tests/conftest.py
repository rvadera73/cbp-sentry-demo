"""Test fixtures"""
import pytest
from fastapi.testclient import TestClient
from main import app
from datetime import datetime
import uuid


@pytest.fixture
def client():
    """FastAPI test client"""
    return TestClient(app)


@pytest.fixture
async def db():
    """Database fixture"""
    # TODO: Initialize test database
    yield
    # TODO: Cleanup


@pytest.fixture
def greenfield_manifest():
    """Greenfield Industrial Trading Co., Ltd. — Vietnam shipper, aluminum extrusions to US"""
    return {
        "bill_id": "BILL-001-GREENFIELD",
        "manifest_id": "MANIFEST-001-GREENFIELD",
        "shipper": "Greenfield Industrial Trading Co., Ltd.",
        "shipper_country": "VN",
        "consignee": "SunPath Energy Distributors LLC",
        "consignee_country": "US",
        "hts_code": "7604.10.1000",
        "country_of_origin": "VN",
        "declared_value_usd": 64896.00,
        "weight_mt": 26.2,
        "weight_kg": 26200,
        "description": "Aluminum extrusions",
        "created_at": datetime.utcnow().isoformat() + "Z",
        "isf_stuffing_location": "Ho Chi Minh City Port",
        "isf_stuffing_country": "CN",  # Actual stuffing is China, not Vietnam
        "declared_coo": "VN",
        "vessel_name": "EVER GIVEN",
        "imo": "9811000",
        # AIS anomaly data
        "ais_dwell_days": 11.2,
        "ais_dwell_baseline": 2.1,
        "ais_anomaly_ratio": 5.3,
        "port_of_lading": "CNGGZ",
        "port_of_discharge": "USHOU",
        # Commodity/pricing data
        "price_declared_per_unit": 2.48,
        "market_price_per_unit": 3.05,
        "price_variance_pct": -18.7,
        # Duty/tariff data
        "hts_duty_rate_pct": 374,
        "ad_cvd_status": "ACTIVE",
        # Shipper age
        "shipper_incorporation_date": "2021-03-15",
        # Prior 6-month history
        "prior_origins_6m": ["MY", "TH", "VN"],
        "prior_ship_count_6m": 3,
    }


@pytest.fixture
def greenfield_entities():
    """Entity resolution results for Greenfield case"""
    return {
        "shipper_vn": {
            "entity_id": "ENT-001-VN-SHIPPER",
            "entity_name": "Greenfield Industrial Trading Co., Ltd.",
            "country": "VN",
            "risk_score": 65,
            "match_confidence": 0.98,
            "senzing_entity_id": 12345,
            "attributes": {
                "incorporation_date": "2021-03-15",
                "age_months": 38,
                "address": "123 Nguyen Hue, HCMC",
            }
        },
        "parent_cn": {
            "entity_id": "ENT-002-CN-PARENT",
            "entity_name": "Greenfield Industrial Holdings (Shenzhen) Co., Ltd.",
            "country": "CN",
            "risk_score": 72,
            "match_confidence": 0.91,
            "senzing_entity_id": 67890,
            "attributes": {
                "incorporation_date": "2008-06-10",
                "age_months": 213,
                "address": "Shenzhen, Guangdong",
            }
        },
        "consignee_us": {
            "entity_id": "ENT-003-US-CONSIGNEE",
            "entity_name": "SunPath Energy Distributors LLC",
            "country": "US",
            "risk_score": 15,
            "match_confidence": 0.87,
            "senzing_entity_id": 11111,
            "attributes": {
                "incorporation_date": "2019-04-20",
                "age_months": 61,
                "address": "Houston, TX",
            }
        }
    }


@pytest.fixture
def greenfield_score_breakdown():
    """Expected score breakdown for Greenfield case (deterministic fixture)"""
    return {
        "total": 91,
        "confidence_tier": "HIGH",
        "components": [
            {
                "name": "Origin Doc Gap",
                "tier": 4,
                "score": 23,
                "max": 25,
                "percentage": 92,
                "description": "ISF Element 9 filed China, manifests declare Vietnam (19 CFR 149.5 violation)"
            },
            {
                "name": "Commodity Sensitivity",
                "tier": 3,
                "score": 14,
                "max": 15,
                "percentage": 93,
                "description": "Aluminum extrusions subject to 374% AD/CVD from China; Vietnam origin evades duties"
            },
            {
                "name": "Routing Consistency",
                "tier": 2,
                "score": 14,
                "max": 15,
                "percentage": 93,
                "description": "AIS tracking shows 11.2-day Guangzhou dwell (5.3× commodity baseline, 99th percentile anomaly)"
            },
            {
                "name": "Party Profile Risk",
                "tier": 1,
                "score": 15,
                "max": 15,
                "percentage": 100,
                "description": "Vietnamese shipper owned by Chinese parent (0.98 Senzing confidence, high-risk linkage)"
            },
            {
                "name": "Historical Pattern",
                "tier": 3,
                "score": 12,
                "max": 15,
                "percentage": 80,
                "description": "6-month origin shift VN→TH→VN, known aluminum transshipment corridor, CRITICAL_STRUCTURAL_RISK"
            },
            {
                "name": "Time Sensitivity",
                "tier": 4,
                "score": 13,
                "max": 15,
                "percentage": 87,
                "description": "72-hour manifest window + AD/CVD active (limited investigation window)"
            }
        ],
        "xai_assertions": [
            "ISF Element 9 filed China, manifests declare Vietnam (19 CFR 149.5 violation)",
            "AIS tracking shows 11.2-day Guangzhou dwell (5.3× commodity baseline, 99th percentile)",
            "Entity resolution: Vietnamese shipper owned by Chinese parent (0.98 Senzing confidence)",
            "Aluminum subject to 374% AD/CVD from China; Vietnam origin evades duties",
            "Estimated duty evasion: $2,100,000 (26,200 kg × $3,050/MT × 374%)"
        ],
        "revenue_impact_usd": 2100000
    }


@pytest.fixture
def mock_firestore(monkeypatch):
    """Mock Firestore client"""
    class MockFirestore:
        async def set(self, *args, **kwargs):
            return None

        async def get(self, *args, **kwargs):
            return None

    return MockFirestore()
