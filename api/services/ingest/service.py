"""
Manifest ingestion service — orchestrates parsing, normalization, validation, and storage
"""
import logging
import uuid
import tempfile
import os
from datetime import datetime
from typing import List, Dict, Any, Tuple
from fastapi import UploadFile

from services.ingest.parser import parse_excel_manifest
from models.schemas import ManifestIngestResponse, ManifestRow
from core.db import get_db

logger = logging.getLogger(__name__)

# Market floor prices (price/kg) for suspicious entry detection
MARKET_FLOOR_PRICES = {
    "7604": 2.00,  # Aluminum extrusions
}


async def ingest_manifest(
    file: UploadFile, manifest_id: str, password: str = "CBPDemo2026"
) -> ManifestIngestResponse:
    """
    Ingest manifest Excel file: parse, normalize, flag suspicious, store.

    Args:
        file: Uploaded Excel file
        manifest_id: Unique manifest ID
        password: Password for protected sheet (default: CBPDemo2026)

    Returns:
        ManifestIngestResponse with row_count, shipment_ids, preview

    Raises:
        ValueError: If file invalid or parse fails
    """

    # Validate file type
    if not file.filename.endswith(".xlsx"):
        raise ValueError("File must be .xlsx")

    # Save file temporarily
    temp_file = None
    try:
        # Create temp file
        with tempfile.NamedTemporaryFile(
            mode="wb", suffix=".xlsx", delete=False
        ) as tmp:
            content = await file.read()
            tmp.write(content)
            temp_file = tmp.name

        logger.info(f"Temporary file saved: {temp_file}")

        # Parse Excel
        rows = parse_excel_manifest(temp_file, password=password)

        if not rows:
            raise ValueError("No data rows found in manifest")

        # Normalize and flag each row
        manifest_rows = []
        shipment_ids = []

        for row in rows:
            normalized_row = _normalize_row(row)
            flag_suspicious = _check_suspicious(normalized_row)
            normalized_row["flag_suspicious"] = flag_suspicious

            manifest_rows.append(normalized_row)

            # Generate shipment ID
            shipment_id = str(uuid.uuid4())
            shipment_ids.append(shipment_id)

        # Store in database
        db = await get_db()
        await _store_manifest(db, manifest_id, manifest_rows, shipment_ids)

        # Prepare response with preview
        preview = [
            ManifestRow(
                shipper=row["shipper"],
                consignee=row["consignee"],
                hts_code=row["hts_code"],
                quantity_kg=row["quantity_kg"],
                value_usd=row["value_usd"],
                description=row["description"],
                flag_suspicious=row["flag_suspicious"],
            )
            for row in manifest_rows[:5]  # First 5 rows
        ]

        logger.info(f"Manifest {manifest_id}: {len(manifest_rows)} rows ingested")

        return ManifestIngestResponse(
            success=True,
            manifest_id=manifest_id,
            record_count=len(manifest_rows),
            row_count=len(manifest_rows),
            status="completed",
            message=f"Successfully ingested {len(manifest_rows)} rows",
            shipment_ids=shipment_ids,
            preview=preview,
        )

    except Exception as e:
        logger.error(f"Manifest ingest failed: {e}")
        raise

    finally:
        # Clean up temp file
        if temp_file and os.path.exists(temp_file):
            try:
                os.unlink(temp_file)
                logger.debug(f"Cleaned up temp file: {temp_file}")
            except Exception as e:
                logger.warning(f"Failed to clean up temp file: {e}")


def _normalize_row(row: Dict[str, Any]) -> Dict[str, Any]:
    """Apply field normalization to row"""
    return {
        "shipper": row.get("shipper", "").strip(),
        "consignee": row.get("consignee", "").strip(),
        "hts_code": row.get("hts_code", ""),
        "quantity_kg": float(row.get("quantity_kg", 0)),
        "value_usd": float(row.get("value_usd", 0)),
        "description": row.get("description", "").strip(),
    }


def _check_suspicious(row: Dict[str, Any]) -> bool:
    """
    Flag suspicious entries based on business rules.

    Rules:
    - Price < market floor for commodity
    """
    hts_base = row["hts_code"][:4]
    floor_price = MARKET_FLOOR_PRICES.get(hts_base, 0)

    if floor_price > 0:
        unit_price = row["value_usd"] / row["quantity_kg"] if row["quantity_kg"] > 0 else 0
        if unit_price < floor_price:
            logger.warning(
                f"Suspicious: {row['hts_code']} unit price ${unit_price:.2f} < floor ${floor_price:.2f}"
            )
            return True

    return False


async def _store_manifest(
    db, manifest_id: str, rows: List[Dict[str, Any]], shipment_ids: List[str]
) -> None:
    """Store manifest and rows in database"""

    created_at = datetime.utcnow().isoformat() + "Z"

    # Insert manifest header
    try:
        await db.execute(
            """
            INSERT INTO manifests (id, uploaded_at, shipper, consignee, hts_code, total_weight_kg, total_value_usd, row_count, flag_suspicious)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                manifest_id,
                created_at,
                rows[0]["shipper"] if rows else "",
                rows[0]["consignee"] if rows else "",
                rows[0]["hts_code"] if rows else "",
                sum(r["quantity_kg"] for r in rows),
                sum(r["value_usd"] for r in rows),
                len(rows),
                any(r.get("flag_suspicious") for r in rows),
            ),
        )

        # Insert manifest rows
        for idx, (row, shipment_id) in enumerate(zip(rows, shipment_ids)):
            await db.execute(
                """
                INSERT INTO manifest_rows (id, manifest_id, shipper, consignee, hts_code, quantity_kg, value_usd, description, flag_suspicious)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    shipment_id,
                    manifest_id,
                    row["shipper"],
                    row["consignee"],
                    row["hts_code"],
                    row["quantity_kg"],
                    row["value_usd"],
                    row["description"],
                    row.get("flag_suspicious", False),
                ),
            )

        await db.commit()
        logger.info(f"Stored {len(rows)} rows for manifest {manifest_id}")

    except Exception as e:
        logger.error(f"Failed to store manifest: {e}")
        raise
