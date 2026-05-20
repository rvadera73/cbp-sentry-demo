"""Test fixtures"""
import sys
from pathlib import Path

# Add parent directory (services/api) to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

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
        "bill_id": "SAMPLE-BOL-2026-001",
        "manifest_id": "MF-2026-001",
        "shipper": "Greenfield Industrial Trading Co., Ltd.",
        "shipper_country": "VN",
        "consignee": "SunPath Energy Distributors LLC",
        "consignee_country": "US",
        "hts_code": "7604.10.1000",
        "country_of_origin": "VN",
        "declared_value_usd": 72030,
        "weight_mt": 26.2,
        "weight_kg": 26200,
        "description": "Aluminum extrusions",
        "created_at": datetime.utcnow().isoformat() + "Z",
        "isf_stuffing_location": "Nansha Terminal, Guangzhou",
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
                "name": "origin_doc_gap",
                "tier": 4,
                "score": 23,
                "max": 25,
                "percentage": 92,
                "description": "ISF Element 9 filed China, manifests declare Vietnam (19 CFR 149.5 violation)"
            },
            {
                "name": "commodity_sensitivity",
                "tier": 3,
                "score": 14,
                "max": 15,
                "percentage": 93,
                "description": "Aluminum extrusions subject to 374% AD/CVD from China; Vietnam origin evades duties"
            },
            {
                "name": "routing_consistency",
                "tier": 2,
                "score": 14,
                "max": 15,
                "percentage": 93,
                "description": "AIS tracking shows 11.2-day Guangzhou dwell (5.3× commodity baseline, 99th percentile anomaly)"
            },
            {
                "name": "party_profile_risk",
                "tier": 1,
                "score": 15,
                "max": 15,
                "percentage": 100,
                "description": "Vietnamese shipper owned by Chinese parent (0.98 Senzing confidence, high-risk linkage)"
            },
            {
                "name": "historical_pattern",
                "tier": 3,
                "score": 12,
                "max": 15,
                "percentage": 80,
                "description": "6-month origin shift VN→TH→VN, known aluminum transshipment corridor, CRITICAL_STRUCTURAL_RISK"
            },
            {
                "name": "time_sensitivity",
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


@pytest.fixture
def greenfield_referral_package(greenfield_manifest, greenfield_entities, greenfield_score_breakdown):
    """
    Complete Greenfield referral package fixture.
    Combines manifest data, entity resolution, and ML scoring into full referral structure.
    """
    from datetime import datetime

    return {
        "package_id": "SENTRY-2026-001",
        "shipment_id": "SHP-001",
        "confidence_level": "HIGH",
        "score": 91,
        "recommended_action": "EXAMINE_ON_ARRIVAL",
        "sections": {
            "shipment_id": {
                "bill_id": "SAMPLE-BOL-2026-001",
                "manifest_id": "MF-2026-001",
                "shipper": "Greenfield Industrial Trading Co., Ltd.",
                "shipper_country": "VN",
                "consignee": "SunPath Energy Distributors LLC",
                "consignee_country": "US",
                "hts_code": "7604.10.1000",
                "hts_description": "Aluminum extrusions, other than tubes",
                "declared_value_usd": 72030,
                "total_weight_kg": 26200,
                "weight_mt": 26.2,
                "vessel_name": "EVER GIVEN",
                "port_of_lading": "CNGGZ",
                "port_of_discharge": "USHOU",
                "eta": "2026-05-27T00:00:00Z"
            },
            "line_items": [
                {
                    "sku": "AE-401",
                    "description": "Aluminum extrusion anodized T6",
                    "quantity_kg": 26200,
                    "hts_code": "7604.10.1000",
                    "weight_mt": 26.2,
                    "declared_value_usd": 72030,
                    "duty_rate": 3.74,
                    "estimated_duty_usd": 26938
                }
            ],
            "routing_history": [
                {
                    "location": "Nansha Terminal, Guangzhou",
                    "country": "CN",
                    "date": "2026-04-12",
                    "event": "Stuffed",
                    "ais_anomaly": True,
                    "dwell_days": 11.2,
                    "baseline_days": 2.1,
                    "anomaly_ratio": 5.3
                }
            ],
            "parties": [
                {
                    "role": "Shipper",
                    "name": "Greenfield Industrial Trading Co., Ltd.",
                    "country": "VN",
                    "senzing_id": 12345,
                    "risk_score": 65,
                    "confidence": 0.98
                },
                {
                    "role": "Consignee",
                    "name": "SunPath Energy Distributors LLC",
                    "country": "US",
                    "senzing_id": 11111,
                    "risk_score": 15,
                    "confidence": 0.87
                },
                {
                    "role": "True Manufacturer",
                    "name": "Guangdong Greenfield Aluminum Mfg. Co., Ltd.",
                    "country": "CN",
                    "senzing_id": 67890,
                    "risk_score": 72,
                    "confidence": 0.98
                }
            ],
            "ownership_chain": [
                {
                    "level": 1,
                    "entity": "Greenfield Industrial Trading Co., Ltd.",
                    "jurisdiction": "VN",
                    "relationship": "Root shipper",
                    "confidence": 0.95
                },
                {
                    "level": 2,
                    "entity": "Greenfield Global Metals Holdings Ltd.",
                    "jurisdiction": "HK",
                    "relationship": "SPV structure",
                    "confidence": 0.92
                },
                {
                    "level": 3,
                    "entity": "Guangdong Greenfield Aluminum Mfg. Co., Ltd.",
                    "jurisdiction": "CN",
                    "relationship": "Primary manufacturer",
                    "confidence": 0.98
                }
            ],
            "import_pattern": [
                {
                    "month": "2025-11",
                    "shipments": 1,
                    "weight_kg": 18500,
                    "declared_origin": "MY",
                    "unit_value": 2.15
                },
                {
                    "month": "2025-12",
                    "shipments": 2,
                    "weight_kg": 41200,
                    "declared_origin": "TH",
                    "unit_value": 2.22
                },
                {
                    "month": "2026-01",
                    "shipments": 2,
                    "weight_kg": 39800,
                    "declared_origin": "VN",
                    "unit_value": 2.35
                },
                {
                    "month": "2026-02",
                    "shipments": 3,
                    "weight_kg": 62900,
                    "declared_origin": "VN",
                    "unit_value": 2.41
                },
                {
                    "month": "2026-03",
                    "shipments": 4,
                    "weight_kg": 88100,
                    "declared_origin": "VN",
                    "unit_value": 2.37
                },
                {
                    "month": "2026-04",
                    "shipments": 1,
                    "weight_kg": 26200,
                    "declared_origin": "VN",
                    "unit_value": 2.48
                }
            ],
            "trade_flow": {
                "hts_code": "7604.10.1000",
                "ad_cvd_status": "ACTIVE",
                "china_rate": 3.74,
                "vietnam_rate": 0.425,
                "duty_evasion_incentive": "HIGH",
                "trade_corridor_risk": "HIGH"
            },
            "document_review": [
                {
                    "type": "Bill of Lading",
                    "filed_date": "2026-04-14",
                    "shipper_declared": "Greenfield Industrial Trading Co., Ltd."
                },
                {
                    "type": "Commercial Invoice",
                    "filed_date": "2026-04-14",
                    "origin_declared": "Vietnam"
                },
                {
                    "type": "ISF Filing",
                    "filed_date": "2026-05-23",
                    "element_9": "China",
                    "status": "MISMATCH"
                }
            ],
            "document_consistency": [
                {
                    "issue": "ISF Element 9 vs manifests",
                    "type": "CRITICAL",
                    "evidence": "ISF filed: China | Manifests declare: Vietnam"
                },
                {
                    "issue": "Price below market",
                    "type": "HIGH",
                    "evidence": "Declared $2.48/kg vs market $3.05/kg"
                },
                {
                    "issue": "Shipper has no factory",
                    "type": "HIGH",
                    "evidence": "VN address is freight forwarder office"
                }
            ],
            "manufacturing_verification": {
                "true_manufacturer": "Guangdong Greenfield Aluminum Mfg. Co., Ltd.",
                "factory_location": "Foshan, Guangdong, China",
                "facility_confirmed": False,
                "production_records": "Not provided",
                "certificates": "Not provided",
                "prior_filings": 18
            },
            "risk_indicators": [
                {
                    "indicator": "ISF/COO mismatch",
                    "severity": "CRITICAL",
                    "evidence": "19 CFR 149.5 violation",
                    "confidence": 0.99
                },
                {
                    "indicator": "Entity linkage to China parent",
                    "severity": "CRITICAL",
                    "evidence": "Senzing resolved VN→CN",
                    "confidence": 0.98
                },
                {
                    "indicator": "AIS dwell anomaly",
                    "severity": "HIGH",
                    "evidence": "11.2-day Guangzhou dwell",
                    "confidence": 0.92
                },
                {
                    "indicator": "Price anomaly",
                    "severity": "HIGH",
                    "evidence": "$2.48 vs $3.05 market",
                    "confidence": 0.87
                },
                {
                    "indicator": "Origin shift pattern",
                    "severity": "HIGH",
                    "evidence": "MY→TH→VN shift",
                    "confidence": 0.85
                },
                {
                    "indicator": "AD/CVD incentive",
                    "severity": "HIGH",
                    "evidence": "374% duty evasion motive",
                    "confidence": 0.99
                }
            ],
            "score_breakdown": {
                "total": 91,
                "confidence_tier": "HIGH",
                "components": [
                    {
                        "name": "origin_doc_gap",
                        "tier": 4,
                        "score": 23,
                        "max": 25,
                        "percentage": 92,
                        "description": "ISF Element 9 filed China, manifests declare Vietnam (19 CFR 149.5 violation)"
                    },
                    {
                        "name": "commodity_sensitivity",
                        "tier": 3,
                        "score": 14,
                        "max": 15,
                        "percentage": 93,
                        "description": "Aluminum extrusions subject to 374% AD/CVD from China; Vietnam origin evades duties"
                    },
                    {
                        "name": "routing_consistency",
                        "tier": 2,
                        "score": 14,
                        "max": 15,
                        "percentage": 93,
                        "description": "AIS tracking shows 11.2-day Guangzhou dwell (5.3× commodity baseline, 99th percentile anomaly)"
                    },
                    {
                        "name": "party_profile_risk",
                        "tier": 1,
                        "score": 15,
                        "max": 15,
                        "percentage": 100,
                        "description": "Vietnamese shipper owned by Chinese parent (0.98 Senzing confidence, high-risk linkage)"
                    },
                    {
                        "name": "historical_pattern",
                        "tier": 3,
                        "score": 12,
                        "max": 15,
                        "percentage": 80,
                        "description": "6-month origin shift VN→TH→VN, known aluminum transshipment corridor, CRITICAL_STRUCTURAL_RISK"
                    },
                    {
                        "name": "time_sensitivity",
                        "tier": 4,
                        "score": 13,
                        "max": 15,
                        "percentage": 87,
                        "description": "72-hour manifest window + AD/CVD active (limited investigation window)"
                    }
                ]
            },
            "what_if_scenarios": [
                {
                    "scenario": "Legitimate Vietnamese aluminum",
                    "assumption": "Shipper owns factory in Vietnam",
                    "expected_score": 22,
                    "key_differences": "No China linkage"
                },
                {
                    "scenario": "Legitimate transshipment",
                    "assumption": "ISF Element 9 China filed correctly",
                    "expected_score": 35,
                    "key_differences": "COO still Vietnam"
                },
                {
                    "scenario": "Chinese goods, Vietnam label only",
                    "assumption": "Only shipper changed",
                    "expected_score": 98,
                    "key_differences": "All red flags present"
                }
            ],
            "data_sources": [
                {
                    "name": "CBP Manifest Filing",
                    "confidence": 0.95,
                    "data_element": "Shipper, consignee, HTS, value"
                },
                {
                    "name": "ISF Data Element 9",
                    "confidence": 0.99,
                    "data_element": "Container stuffing location"
                },
                {
                    "name": "AIS vessel tracking",
                    "confidence": 0.92,
                    "data_element": "Port dwell times"
                },
                {
                    "name": "Senzing entity resolution",
                    "confidence": 0.98,
                    "data_element": "Entity linkage"
                },
                {
                    "name": "AD/CVD Proceedings",
                    "confidence": 0.99,
                    "data_element": "Tariff rates"
                },
                {
                    "name": "Corporate Registry (Vietnam)",
                    "confidence": 0.94,
                    "data_element": "Shipper registration"
                },
                {
                    "name": "Corporate Registry (Hong Kong)",
                    "confidence": 0.91,
                    "data_element": "Holding company"
                },
                {
                    "name": "Corporate Registry (China SAMR)",
                    "confidence": 0.98,
                    "data_element": "Manufacturer details"
                },
                {
                    "name": "Trade History (Panjiva)",
                    "confidence": 0.87,
                    "data_element": "Prior patterns"
                }
            ]
        }
    }
