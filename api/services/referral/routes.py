"""
Referral package API routes.

Endpoints:
- GET /api/referral/{manifest_id}
- GET /api/referral/{manifest_id}/summary
"""

import logging
from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from models.schemas import ReferralPackageResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/{manifest_id}", response_model=ReferralPackageResponse)
async def get_referral_package(manifest_id: str) -> ReferralPackageResponse:
    """
    Get referral package for a shipment.

    Args:
        manifest_id: Manifest identifier

    Returns:
        Complete referral package with all 14 sections
    """
    try:
        # TODO: Load referral package from database using manifest_id
        # For now, return fixture for Greenfield case
        if manifest_id == "greenfield" or manifest_id.startswith("mani_"):
            return {
                "package_id": f"ref_{manifest_id}",
                "shipment_id": manifest_id,
                "confidence_level": "HIGH",
                "score": 91,
                "recommended_action": "EXAMINE",
                "sections": {
                    "shipment_id": {
                        "bill_id": "BL123456789",
                        "manifest_id": manifest_id,
                        "shipper": "Greenfield Industrial Trading Co., Ltd.",
                        "shipper_country": "VN",
                        "consignee": "SunPath Energy Distributors LLC",
                        "consignee_country": "US",
                        "hts_code": "7604.10.1000",
                        "hts_description": "Aluminum extrusions",
                        "declared_value_usd": 450000.0,
                        "total_weight_kg": 22500.0,
                        "weight_mt": 22.5,
                        "vessel_name": "MV Pacific Horizon",
                        "port_of_lading": "Guangzhou",
                        "port_of_discharge": "Los Angeles",
                        "eta": "2026-06-15"
                    },
                    "line_items": [
                        {
                            "sku": "GF-EXT-001",
                            "description": "Aluminum extrusion profile, 6063-T5",
                            "quantity_kg": 22500.0,
                            "hts_code": "7604.10.1000",
                            "weight_mt": 22.5,
                            "declared_value_usd": 450000.0,
                            "duty_rate": 0.0,
                            "estimated_duty_usd": 0.0
                        }
                    ],
                    "routing_history": [
                        {
                            "location": "Guangzhou",
                            "country": "CN",
                            "date": "2026-05-18",
                            "event": "Loaded on vessel",
                            "ais_anomaly": True,
                            "dwell_days": 11.2,
                            "baseline_days": 2.1,
                            "anomaly_ratio": 5.3
                        },
                        {
                            "location": "Los Angeles",
                            "country": "US",
                            "date": "2026-06-15",
                            "event": "ETA",
                            "ais_anomaly": False
                        }
                    ],
                    "parties": [
                        {
                            "role": "SHIPPER",
                            "name": "Greenfield Industrial Trading Co., Ltd.",
                            "country": "VN",
                            "senzing_id": 1001,
                            "risk_score": 65.0,
                            "confidence": 0.95
                        },
                        {
                            "role": "MANUFACTURER",
                            "name": "Guangdong Greenfield Aluminum Mfg. Co., Ltd.",
                            "country": "CN",
                            "senzing_id": 1002,
                            "risk_score": 78.0,
                            "confidence": 0.98
                        },
                        {
                            "role": "CONSIGNEE",
                            "name": "SunPath Energy Distributors LLC",
                            "country": "US",
                            "senzing_id": 1003,
                            "risk_score": 42.0,
                            "confidence": 0.87
                        }
                    ],
                    "ownership_chain": [
                        {
                            "level": 1,
                            "entity": "Greenfield Industrial Trading Co., Ltd.",
                            "jurisdiction": "VN",
                            "relationship": "Direct shipper",
                            "confidence": 0.95
                        },
                        {
                            "level": 2,
                            "entity": "Guangdong Greenfield Aluminum Mfg. Co., Ltd.",
                            "jurisdiction": "CN",
                            "relationship": "Parent manufacturer",
                            "confidence": 0.98
                        },
                        {
                            "level": 3,
                            "entity": "Greenfield Global Metals Holdings Ltd.",
                            "jurisdiction": "HK",
                            "relationship": "Holding company",
                            "confidence": 0.92
                        }
                    ],
                    "import_pattern": [
                        {
                            "month": "2026-05",
                            "shipments": 1,
                            "weight_kg": 22500.0,
                            "declared_origin": "VN",
                            "unit_value": 20.0
                        }
                    ],
                    "trade_flow": {
                        "hts_code": "7604.10.1000",
                        "ad_cvd_status": "ACTIVE",
                        "china_rate": 374.15,
                        "vietnam_rate": 0.0,
                        "duty_evasion_incentive": "HIGH",
                        "trade_corridor_risk": "HIGH"
                    },
                    "document_review": [
                        {
                            "type": "ISF",
                            "filed_date": "2026-05-18",
                            "shipper_declared": "Greenfield Industrial Trading Co., Ltd.",
                            "origin_declared": "VN",
                            "element_9": "CN",
                            "status": "MISMATCH"
                        }
                    ],
                    "document_consistency": [
                        {
                            "issue": "ISF Element 9 mismatch",
                            "type": "CRITICAL",
                            "evidence": "Filed as CN, declared as VN"
                        }
                    ],
                    "manufacturing_verification": {
                        "true_manufacturer": "Guangdong Greenfield Aluminum Mfg. Co., Ltd.",
                        "factory_location": "Guangzhou, China",
                        "facility_confirmed": False,
                        "production_records": "Not provided",
                        "certificates": "Missing",
                        "prior_filings": 9
                    },
                    "risk_indicators": [
                        {
                            "indicator": "Shipper age",
                            "severity": "MEDIUM",
                            "evidence": "14 months old",
                            "confidence": 0.92
                        },
                        {
                            "indicator": "AIS dwell anomaly",
                            "severity": "HIGH",
                            "evidence": "11.2 days vs. 2.1-day baseline",
                            "confidence": 0.95
                        },
                        {
                            "indicator": "China parent company",
                            "severity": "HIGH",
                            "evidence": "Parent in AD/CVD jurisdiction",
                            "confidence": 0.98
                        }
                    ],
                    "score_breakdown": {
                        "total": 91,
                        "confidence_tier": "HIGH",
                        "components": [
                            {
                                "name": "Origin Doc Gap",
                                "tier": 4,
                                "score": 25,
                                "max": 25,
                                "percentage": 100.0,
                                "description": "Probable fraudulent origin documentation"
                            },
                            {
                                "name": "Commodity Sensitivity",
                                "tier": 3,
                                "score": 15,
                                "max": 15,
                                "percentage": 100.0,
                                "description": "AD/CVD-sensitive aluminum extrusions"
                            },
                            {
                                "name": "Routing Consistency",
                                "tier": 2,
                                "score": 15,
                                "max": 15,
                                "percentage": 100.0,
                                "description": "Anomalous port dwell time"
                            },
                            {
                                "name": "Party Profile Risk",
                                "tier": 1,
                                "score": 15,
                                "max": 15,
                                "percentage": 100.0,
                                "description": "China parent, Vietnam intermediary"
                            },
                            {
                                "name": "Historical Pattern",
                                "tier": 3,
                                "score": 15,
                                "max": 15,
                                "percentage": 100.0,
                                "description": "High-risk commodity with price below market"
                            },
                            {
                                "name": "Time Sensitivity",
                                "tier": 4,
                                "score": 11,
                                "max": 15,
                                "percentage": 73.3,
                                "description": "Time-critical shipment during high-scrutiny period"
                            }
                        ]
                    },
                    "what_if_scenarios": [
                        {
                            "scenario": "If shipper were 36+ months old",
                            "assumption": "Company age risk decreased",
                            "expected_score": 85,
                            "key_differences": "Party Profile Risk: 15 → 10 (-5 points)"
                        },
                        {
                            "scenario": "If no China parent company",
                            "assumption": "No direct AD/CVD connection",
                            "expected_score": 72,
                            "key_differences": "Origin Doc Gap: 25 → 15 (-10 points)"
                        }
                    ],
                    "data_sources": [
                        {
                            "name": "Senzing Entity Resolution",
                            "confidence": 0.95,
                            "data_element": "Party relationships"
                        },
                        {
                            "name": "ISF Manifest",
                            "confidence": 0.99,
                            "data_element": "Element 9, declared origin"
                        },
                        {
                            "name": "AIS Vessel Tracking",
                            "confidence": 0.99,
                            "data_element": "Port dwell times"
                        },
                        {
                            "name": "AD/CVD Orders",
                            "confidence": 1.0,
                            "data_element": "Commodity rate information"
                        }
                    ]
                }
            }

        # Default for unknown manifest
        raise HTTPException(status_code=404, detail=f"Referral package not found for {manifest_id}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Referral package lookup failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{manifest_id}/summary")
async def get_referral_summary(manifest_id: str) -> Dict[str, Any]:
    """
    Get summary of referral package.

    Args:
        manifest_id: Manifest identifier

    Returns:
        Summary with key metrics
    """
    try:
        if manifest_id == "greenfield" or manifest_id.startswith("mani_"):
            return {
                "manifest_id": manifest_id,
                "score": 91,
                "confidence_tier": "HIGH",
                "recommended_action": "EXAMINE",
                "top_risks": [
                    "China parent company (manufacturer resolves to AD/CVD jurisdiction)",
                    "ISF Element 9 mismatch (CN filed, VN declared)",
                    "Anomalous port dwell (11.2d vs. 2.1d baseline)"
                ],
                "referral_justification": "High-confidence transshipment indicators warrant port examination and manufacturer verification."
            }

        raise HTTPException(status_code=404, detail=f"Referral summary not found for {manifest_id}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Referral summary lookup failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
