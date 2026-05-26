"""
Comprehensive Referral Package API Router

Endpoints:
- POST /api/referrals/{shipment_id} - Generate complete 14-section referral
- GET /api/referrals/{referral_id} - Retrieve referral package
- GET /api/shipments/{shipment_id}/referral - Get referral for shipment
- POST /api/referrals/{referral_id}/annotations - Save annotations
"""

import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks
import json
from datetime import datetime
import sqlite3

from referral_comprehensive_v2 import ComprehensiveReferralGenerator
from gemini_referral_narratives import ReferralNarrativeGenerator
from risk_scoring_engine import RiskScoringEngine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/referrals", tags=["referrals"])


class ReferralPackageService:
    """Service to generate and manage comprehensive referral packages"""

    def __init__(self, db_path: str = "/app/data/cbp_sentry.db", google_api_key: str = None, cord_url: str = None):
        self.db_path = db_path
        self.gen = ComprehensiveReferralGenerator(db_path, cord_url)
        self.narrative_gen = ReferralNarrativeGenerator(google_api_key)
        self.risk_engine = RiskScoringEngine()

    def generate_complete_referral(self, shipment_id: str) -> Dict[str, Any]:
        """
        Generate complete 14-section referral with AI narratives.

        Process:
        1. Get shipment data
        2. Calculate risk score & breakdown
        3. Generate data-backed sections (3-1 to 3-10)
        4. Generate AI narratives for sections 3-6, 3-7, 3-11, 3-14
        5. Store in DB
        """
        logger.info(f"Generating referral package for {shipment_id}")

        # Step 1: Get shipment & calculate risk
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM shipments WHERE id = ?", (shipment_id,))
        shipment_row = cursor.fetchone()

        if not shipment_row:
            raise HTTPException(status_code=404, detail=f"Shipment {shipment_id} not found")

        shipment = dict(shipment_row)

        # Calculate risk score
        risk_breakdown = self.risk_engine.score_shipment(shipment)
        breakdown_dict = {
            "final_score": risk_breakdown.final_score,
            "components": [
                {
                    "component": c.component,
                    "factor": c.factor,
                    "score": c.score,
                    "weight": c.weight,
                    "weighted_result": c.weighted_result,
                    "rationale": c.rationale,
                    "evidence": c.evidence,
                }
                for c in risk_breakdown.components
            ],
        }

        # Step 2: Generate base referral package
        package = self.gen.generate_referral_package(shipment_id)
        package["risk_breakdown"] = breakdown_dict

        # Step 3: Enhance with AI narratives
        logger.info(f"Generating AI narratives via Gemini...")

        try:
            # Section 3-6: Historical Import Pattern
            s3_6_narrative = self.narrative_gen.generate_section_3_6(shipment, breakdown_dict)
            if package["sections"].get("section_3_6_historical_import_pattern"):
                package["sections"]["section_3_6_historical_import_pattern"]["pattern_narrative"] = s3_6_narrative
        except Exception as e:
            logger.warning(f"Failed to generate Section 3-6: {e}")

        try:
            # Section 3-7: Trade Flow Intelligence
            s3_7_narrative = self.narrative_gen.generate_section_3_7(shipment, breakdown_dict)
            if package["sections"].get("section_3_7_trade_flow_intelligence"):
                package["sections"]["section_3_7_trade_flow_intelligence"]["trade_flow_narrative"] = s3_7_narrative
        except Exception as e:
            logger.warning(f"Failed to generate Section 3-7: {e}")

        try:
            # Section 3-11: Risk Indicator Summary
            s3_11_narrative = self.narrative_gen.generate_section_3_11_narrative(breakdown_dict, shipment)
            if package["sections"].get("section_3_11_risk_indicators"):
                package["sections"]["section_3_11_risk_indicators"]["summary"] = s3_11_narrative
        except Exception as e:
            logger.warning(f"Failed to generate Section 3-11: {e}")

        try:
            # Section 3-14: Conclusion & Recommendation
            s3_14_narrative = self.narrative_gen.generate_section_3_14_conclusion(breakdown_dict, shipment)
            if package["sections"].get("section_3_14_conclusion_and_recommendation"):
                package["sections"]["section_3_14_conclusion_and_recommendation"]["conclusion_narrative"] = s3_14_narrative
        except Exception as e:
            logger.warning(f"Failed to generate Section 3-14: {e}")

        # Step 4: Store in database
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO referral_packages
                (referral_id, shipment_id, manifest_id, created_at, risk_score, risk_level, package_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                package["referral_id"],
                package["shipment_id"],
                package["manifest_id"],
                package["created_at"],
                package["risk_score"],
                package["risk_level"],
                json.dumps(package["sections"], default=str),
            ))
            conn.commit()
            logger.info(f"✓ Stored referral {package['referral_id']}")
        except Exception as e:
            logger.error(f"Failed to store referral: {e}")
        finally:
            conn.close()

        return package


# Global service instance
referral_service = None


def init_referral_service(db_path: str = "/app/data/cbp_sentry.db", google_api_key: str = None, cord_url: str = None):
    """Initialize referral service"""
    global referral_service
    import os
    cord_url = cord_url or os.getenv("CORD_SERVICE_URL", "http://sentry-cord-integration:8004")
    referral_service = ReferralPackageService(db_path, google_api_key, cord_url)


@router.post("/{shipment_id}")
async def generate_referral(
    shipment_id: str,
    background_tasks: BackgroundTasks = None
) -> Dict[str, Any]:
    """
    Generate comprehensive 14-section referral package for a shipment.

    Includes:
    - Data-backed sections (3-1 through 3-10)
    - AI-generated narratives (3-6, 3-7, 3-11, 3-14)
    - Risk scoring & breakdown
    - Inline annotation capability
    """
    if not referral_service:
        init_referral_service()

    try:
        package = referral_service.generate_complete_referral(shipment_id)
        return {
            "status": "success",
            "referral": package,
        }
    except Exception as e:
        logger.error(f"Referral generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{referral_id}")
async def get_referral(referral_id: str) -> Dict[str, Any]:
    """Retrieve a stored referral package"""
    conn = sqlite3.connect("/app/data/cbp_sentry.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT referral_id, shipment_id, manifest_id, created_at, risk_score, risk_level, package_json
            FROM referral_packages
            WHERE referral_id = ?
        """, (referral_id,))

        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"Referral {referral_id} not found")

        row_dict = dict(row)
        row_dict["sections"] = json.loads(row_dict["package_json"])
        del row_dict["package_json"]

        return {
            "status": "success",
            "referral": row_dict,
        }
    finally:
        conn.close()


@router.get("/shipment/{shipment_id}")
async def get_shipment_referral(shipment_id: str) -> Dict[str, Any]:
    """Get referral for a shipment (returns most recent)"""
    conn = sqlite3.connect("/app/data/cbp_sentry.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT referral_id, shipment_id, manifest_id, created_at, risk_score, risk_level, package_json
            FROM referral_packages
            WHERE shipment_id = ?
            ORDER BY created_at DESC
            LIMIT 1
        """, (shipment_id,))

        row = cursor.fetchone()
        if not row:
            # Generate new referral if not found
            if not referral_service:
                init_referral_service()
            package = referral_service.generate_complete_referral(shipment_id)
            return {"status": "success", "referral": package}

        row_dict = dict(row)
        row_dict["sections"] = json.loads(row_dict["package_json"])
        del row_dict["package_json"]

        return {
            "status": "success",
            "referral": row_dict,
        }
    finally:
        conn.close()


@router.post("/{referral_id}/annotations")
async def save_annotations(
    referral_id: str,
    annotations: list = None
) -> Dict[str, Any]:
    """Save inline annotations to a referral package"""
    conn = sqlite3.connect("/app/data/cbp_sentry.db")
    cursor = conn.cursor()

    try:
        # Store annotations as JSON in a new column (or separate table)
        cursor.execute("""
            UPDATE referral_packages
            SET package_json = json_set(
                package_json,
                '$.annotations',
                ?
            )
            WHERE referral_id = ?
        """, (json.dumps(annotations or []), referral_id))

        conn.commit()

        return {
            "status": "success",
            "referral_id": referral_id,
            "annotations_saved": len(annotations or []),
        }
    except Exception as e:
        logger.error(f"Failed to save annotations: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


@router.get("")
async def list_referrals(skip: int = 0, limit: int = 20) -> Dict[str, Any]:
    """List all referral packages"""
    conn = sqlite3.connect("/app/data/cbp_sentry.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT referral_id, shipment_id, manifest_id, created_at, risk_score, risk_level
            FROM referral_packages
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """, (limit, skip))

        referrals = [dict(row) for row in cursor.fetchall()]

        cursor.execute("SELECT COUNT(*) FROM referral_packages")
        total = cursor.fetchone()[0]

        return {
            "status": "success",
            "total": total,
            "skip": skip,
            "limit": limit,
            "referrals": referrals,
        }
    finally:
        conn.close()
