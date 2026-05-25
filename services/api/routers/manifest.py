"""Manifest ingestion and processing endpoints"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
from services.manifest_service import ManifestService
from httpx import AsyncClient

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/manifest", tags=["manifest"])

manifest_service = ManifestService()


class ConfirmDedupsRequest(BaseModel):
    """Request to confirm which duplicate rows to keep/skip"""

    keep: List[str]  # manifest_source_ids to insert
    skip: List[str]  # manifest_source_ids to skip


@router.post("/upload")
async def upload_manifest(file: UploadFile = File(...)) -> Dict[str, Any]:
    """
    Upload and parse a manifest file, detect duplicates.

    Returns: {manifest_id, filename, total_rows, new_rows[], duplicate_rows[], status}
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    if not file.filename.lower().endswith((".xlsx", ".xls", ".csv")):
        raise HTTPException(status_code=400, detail="Only Excel (.xlsx/.xls) and CSV files supported")

    try:
        content = await file.read()

        async with AsyncClient() as client:
            result = await manifest_service.parse_and_detect_duplicates(
                file_content=content,
                filename=file.filename,
                data_service_client=client,
            )

        return result

    except Exception as e:
        logger.error(f"Upload manifest error: {e}")
        raise HTTPException(status_code=500, detail=f"Error uploading manifest: {str(e)}")


@router.post("/{manifest_id}/confirm")
async def confirm_manifest(
    manifest_id: str,
    request: ConfirmDedupsRequest,
) -> Dict[str, Any]:
    """
    Confirm which duplicate rows to insert after dedup review.

    User selects which rows to keep, rest are skipped.
    """
    try:
        logger.info(f"Confirming manifest {manifest_id}: keep={len(request.keep)}, skip={len(request.skip)}")

        # This endpoint is a placeholder for the flow.
        # Actual implementation would re-fetch the parsed rows and filter by keep list,
        # then call confirm_and_insert with the filtered rows.
        # For now, return a structure that indicates the next step.

        return {
            "status": "confirmed",
            "manifest_id": manifest_id,
            "keep_count": len(request.keep),
            "skip_count": len(request.skip),
            "next_step": "scoring_pipeline",
        }

    except Exception as e:
        logger.error(f"Confirm manifest error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export")
async def export_data(source: str = "uploaded") -> Dict[str, Any]:
    """
    Export current database state as JSON.

    Args:
        source: "uploaded" (user-imported only) or "all" (including seed data)

    Returns: JSON array of shipments
    """
    try:
        from httpx import AsyncClient
        import os

        data_service_url = os.getenv("DATA_SERVICE_URL", "http://localhost:8005")

        async with AsyncClient() as client:
            if source == "uploaded":
                # Query for user-uploaded rows (have manifest_source_id)
                resp = await client.get(
                    f"{data_service_url}/shipments",
                    params={"has_manifest_source_id": "true", "limit": 10000},
                )
            else:
                # Query all rows
                resp = await client.get(
                    f"{data_service_url}/shipments",
                    params={"limit": 10000},
                )

            if resp.status_code != 200:
                raise HTTPException(status_code=resp.status_code, detail=resp.text)

            shipments = resp.json().get("data", [])

            logger.info(f"Exported {len(shipments)} shipments (source={source})")

            return {
                "status": "success",
                "source": source,
                "count": len(shipments),
                "data": shipments,
                "exported_at": datetime.utcnow().isoformat(),
            }

    except Exception as e:
        logger.error(f"Export data error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
