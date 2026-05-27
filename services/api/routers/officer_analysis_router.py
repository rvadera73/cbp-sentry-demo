"""
Officer Analysis API Router
Handles saving and retrieving officer analysis forms from 4-step workflow
"""

import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException
import json
import uuid
from datetime import datetime
import sqlite3

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/officer-analysis", tags=["officer-analysis"])

DB_PATH = "/app/data/cbp_sentry.db"


@router.post("")
async def save_officer_analysis(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Save completed 4-step officer analysis form

    Expected structure:
    {
      "referral_id": str,
      "step1": {...risk assessment...},
      "step2": {...evidence review...},
      "step3": {...action recommendation...},
      "step4": {...officer signature...}
    }
    """
    try:
        analysis_id = str(uuid.uuid4())
        referral_id = data.get("referral_id")
        step4 = data.get("step4", {})

        if not referral_id:
            raise ValueError("referral_id is required")

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Insert officer analysis
        cursor.execute("""
            INSERT INTO officer_analyses
            (analysis_id, referral_id, officer_id, officer_name, badge_number, district,
             step1, step2, step3, step4, submitted_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            analysis_id,
            referral_id,
            step4.get("officerId", "UNKNOWN"),
            step4.get("officerName", "Unknown Officer"),
            step4.get("badgeNumber", ""),
            step4.get("district", ""),
            json.dumps(data.get("step1", {})),
            json.dumps(data.get("step2", {})),
            json.dumps(data.get("step3", {})),
            json.dumps(step4),
            datetime.utcnow().isoformat()
        ))

        # Update referral_packages with analysis ID
        cursor.execute("""
            UPDATE referral_packages
            SET analysis_id = ?, final_package_status = 'Under Review'
            WHERE referral_id = ?
        """, (analysis_id, referral_id))

        # Log to audit trail
        cursor.execute("""
            INSERT INTO audit_log
            (log_id, officer_id, action, referral_id, analysis_id, timestamp, details)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            str(uuid.uuid4()),
            step4.get("officerId", "UNKNOWN"),
            "ANALYSIS_SUBMITTED",
            referral_id,
            analysis_id,
            datetime.utcnow().isoformat(),
            json.dumps({
                "action_selected": data.get("step3", {}).get("action"),
                "risk_assessment": data.get("step1", {}).get("officerScore") or "AGREED"
            })
        ))

        conn.commit()
        conn.close()

        logger.info(f"✓ Officer analysis {analysis_id} saved for referral {referral_id}")

        return {
            "status": "success",
            "analysis_id": analysis_id,
            "message": "Analysis submitted successfully",
            "referral_id": referral_id
        }

    except Exception as e:
        logger.error(f"Failed to save officer analysis: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{analysis_id}")
async def get_officer_analysis(analysis_id: str) -> Dict[str, Any]:
    """
    Retrieve saved officer analysis by analysis ID
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM officer_analyses WHERE analysis_id = ?", (analysis_id,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            raise HTTPException(status_code=404, detail=f"Analysis {analysis_id} not found")

        # Parse JSON fields
        result = dict(row)
        for field in ["step1", "step2", "step3", "step4", "details"]:
            if field in result and result[field]:
                try:
                    result[field] = json.loads(result[field])
                except:
                    pass

        return {
            "status": "success",
            "analysis": result
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/referral/{referral_id}")
async def get_analysis_by_referral(referral_id: str) -> Dict[str, Any]:
    """
    Retrieve officer analysis linked to a referral
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM officer_analyses WHERE referral_id = ? ORDER BY submitted_at DESC LIMIT 1",
                      (referral_id,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return {
                "status": "not_found",
                "message": f"No analysis found for referral {referral_id}"
            }

        # Parse JSON fields
        result = dict(row)
        for field in ["step1", "step2", "step3", "step4"]:
            if field in result and result[field]:
                try:
                    result[field] = json.loads(result[field])
                except:
                    pass

        return {
            "status": "success",
            "analysis": result
        }

    except Exception as e:
        logger.error(f"Failed to retrieve analysis by referral: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/referral/{referral_id}/finalize")
async def finalize_referral_package(referral_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Finalize and archive a referral package with its analysis
    Marks as ready for submission to enforcement
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Update referral status
        cursor.execute("""
            UPDATE referral_packages
            SET final_package_status = 'Finalized',
                edited_sections = ?,
                pdf_export_ready = 1
            WHERE referral_id = ?
        """, (json.dumps(data.get("edited_sections", {})), referral_id))

        # Log action
        cursor.execute("""
            INSERT INTO audit_log
            (log_id, officer_id, action, referral_id, timestamp, details)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            str(uuid.uuid4()),
            data.get("officer_id", "UNKNOWN"),
            "REFERRAL_FINALIZED",
            referral_id,
            datetime.utcnow().isoformat(),
            json.dumps({"edited_section_count": len(data.get("edited_sections", {}))})
        ))

        conn.commit()
        conn.close()

        logger.info(f"✓ Referral package {referral_id} finalized")

        return {
            "status": "success",
            "message": "Referral package finalized",
            "referral_id": referral_id
        }

    except Exception as e:
        logger.error(f"Failed to finalize referral: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def init_officer_analysis_service(db_path: str = DB_PATH):
    """Initialize officer analysis tables if they don't exist"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Create officer_analyses table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS officer_analyses (
                analysis_id TEXT PRIMARY KEY,
                referral_id TEXT NOT NULL,
                officer_id TEXT NOT NULL,
                officer_name TEXT,
                badge_number TEXT,
                district TEXT,
                step1 JSON NOT NULL,
                step2 JSON NOT NULL,
                step3 JSON NOT NULL,
                step4 JSON NOT NULL,
                submitted_at TIMESTAMP NOT NULL,
                signed_at TIMESTAMP,
                FOREIGN KEY (referral_id) REFERENCES referral_packages(referral_id)
            )
        """)

        # Create audit_log table if not exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                log_id TEXT PRIMARY KEY,
                officer_id TEXT,
                action TEXT,
                referral_id TEXT,
                analysis_id TEXT,
                timestamp TIMESTAMP,
                details JSON
            )
        """)

        conn.commit()
        conn.close()
        logger.info("✓ Officer analysis tables initialized")

    except Exception as e:
        logger.warning(f"Could not initialize officer analysis tables: {e}")
