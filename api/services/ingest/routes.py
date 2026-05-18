"""
Manifest ingest router — handles file uploads and parsing
"""
import logging
from fastapi import APIRouter, UploadFile, File, HTTPException
from uuid import uuid4

from services.ingest.service import ingest_manifest
from models.schemas import ManifestIngestResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/manifest", response_model=ManifestIngestResponse)
async def upload_manifest(
    file: UploadFile = File(...),
    manifest_id: str = None,
) -> ManifestIngestResponse:
    """
    Upload and ingest manifest Excel file.

    Args:
        file: .xlsx manifest file (multipart/form-data)
        manifest_id: Optional manifest ID (generated if not provided)

    Returns:
        ManifestIngestResponse with row_count, shipment_ids, preview

    Raises:
        400: Invalid file type or parse error
        500: Internal server error
    """

    try:
        # Generate manifest ID if not provided
        if not manifest_id:
            manifest_id = f"manifest-{uuid4()}"

        logger.info(f"Ingesting manifest {manifest_id}: {file.filename}")

        # Call ingest service
        response = await ingest_manifest(file, manifest_id, password="CBPDemo2026")

        logger.info(f"Manifest {manifest_id} ingestion completed")

        return response

    except ValueError as e:
        logger.error(f"Manifest ingest validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        logger.error(f"Manifest ingest error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
