"""
Referral Package API - Generates and returns PDF for viewer integration
"""

import io
import logging
from typing import Dict, Any
from fastapi import APIRouter, HTTPException
from referral_pdf_generator import CBPReferralPDFGenerator

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/referral", tags=["referral"])


@router.get("/{shipment_id}/package")
async def get_referral_package(shipment_id: str) -> Dict[str, Any]:
    """
    Generate referral package PDF for a shipment.
    Returns PDF as base64 for inline display in viewer.

    This endpoint is called when Evidence & Referral tab loads.
    Returns complete referral data including PDF for viewer integration.
    """
    try:
        logger.info(f"Generating referral package for shipment: {shipment_id}")

        # Comprehensive data for all sections: Shipment, Entity, Risk Score, Referral
        referral_data = {
            "case_id": f"CBP-2026-{shipment_id[-4:]}",
            "shipment_id": shipment_id,
            "risk_score": 97,
            "recommendation": "HOLD FOR EXAMINATION",
            # SHIPMENT TAB DATA
            "shipment": {
                "shipper_name": "Canadian Aluminum Inc.",
                "consignee_name": "Gulf Coast Industrial",
                "commodity_name": "Semiconductor Devices",
                "hs_code": "8541.40",
                "origin_country": "Canada",
                "destination_country": "United States",
                "declared_value": 8177.41,
                "quantity": 1,
                "unit": "shipment",
                "weight_kg": 11624.0,
            },
            "line_items": [
                {
                    "hs_code": "8541.40",
                    "description": "Semiconductor Devices",
                    "quantity": 1,
                    "unit": "shipment",
                    "value": 8177.41,
                }
            ],
            "routing": {
                "vessel_name": "MV Seamless Journey",
                "vessel_imo": "9645123",
                "port_of_lading": "Vancouver, BC",
                "port_of_unlading": "Houston, TX",
                "dwell_days": 5.2,
                "dwell_baseline": 2.5,
                "dwell_anomaly": "HIGH",
                "ais_gaps": 2,
                "transit_days": 14,
            },
            # ENTITY TAB DATA
            "parties": [
                {
                    "name": "Canadian Aluminum Inc.",
                    "role": "SHIPPER",
                    "country": "Canada",
                    "risk_note": "67% entity match confidence",
                },
                {
                    "name": "Gulf Coast Industrial",
                    "role": "CONSIGNEE",
                    "country": "United States",
                    "risk_note": "New importer",
                },
            ],
            "entity_chain": [
                {
                    "tier": 1,
                    "name": "Northamericana Holdings Ltd.",
                    "country": "Canada",
                    "ownership_pct": 100,
                    "match_confidence": 89,
                    "risk_signal": "None",
                },
            ],
            # RISK SCORE TAB DATA
            "risk_scoring": {
                "h1_score": 35,
                "h2_score": 31,
                "h3_score": 31,
                "final_score": 97,
                "h1_level": "HIGH",
                "h2_signals": [
                    "Dwell time anomaly: 5.2 days vs 2.5 baseline",
                    "ISF Element 9 mismatch detected",
                    "AIS gap: 2 days in transit",
                ],
                "h3_recommendation": "INVESTIGATE",
                "components": [
                    {
                        "component": "Trade Corridor Risk",
                        "weight": 40,
                        "score": 8.5,
                        "weighted_result": 34.0,
                    },
                    {
                        "component": "Pre-Manifest Anomaly",
                        "weight": 35,
                        "score": 8.8,
                        "weighted_result": 31.0,
                    },
                    {
                        "component": "Network Intelligence",
                        "weight": 25,
                        "score": 12.4,
                        "weighted_result": 31.0,
                    },
                ],
                "adjustments": [
                    {
                        "type": "Corridor Risk Multiplier",
                        "multiplier": 1.0,
                        "adjustment_points": 0,
                    },
                ],
                "subtotal": 96.0,
                "confidence_interval": "High (±3 points)",
            },
            # WHAT-IF SCENARIOS
            "what_if_scenarios": [
                {
                    "name": "What-If: Shipper has 10+ years history",
                    "scenario": True,
                    "base_score": 97,
                    "adjusted_score": 78,
                    "recommendation": "RELEASE - Risk reduced below examination threshold",
                    "impact": "-19 points",
                },
                {
                    "name": "What-If: Dwell time normalized to baseline",
                    "scenario": True,
                    "base_score": 97,
                    "adjusted_score": 82,
                    "recommendation": "EXAMINE - Risk remains in critical category",
                    "impact": "-15 points",
                },
                {
                    "name": "What-If: Additional AIS gaps detected (4 total)",
                    "scenario": False,
                    "base_score": 97,
                    "adjusted_score": 103,
                    "recommendation": "REFER TO NATIONAL TARGETING CENTER - Escalate investigation",
                    "impact": "+6 points (capped at 100)",
                },
            ],
            # REFERRAL DATA
            "narrative": "",
        }

        # Generate PDF
        generator = CBPReferralPDFGenerator()
        pdf_buffer = generator.generate_pdf(referral_data)
        pdf_bytes = pdf_buffer.getvalue()

        # Convert to base64 for inline display
        import base64

        pdf_base64 = base64.b64encode(pdf_bytes).decode("utf-8")

        logger.info(f"Referral package generated successfully: {len(pdf_bytes)} bytes")

        return {
            "status": "success",
            "shipment_id": shipment_id,
            "case_id": referral_data["case_id"],
            "risk_score": referral_data["risk_score"],
            "pdf_base64": pdf_base64,
            "pdf_bytes": len(pdf_bytes),
            "referral_data": referral_data,
        }

    except Exception as e:
        logger.error(f"Error generating referral package: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate referral package: {str(e)}")
