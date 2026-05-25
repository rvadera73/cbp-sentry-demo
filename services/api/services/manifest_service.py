"""Manifest ingestion and processing business logic"""

import uuid
import logging
import hashlib
from datetime import datetime
from typing import Dict, List, Any, Tuple, Optional
from ingest_parser import parse_excel_manifest

logger = logging.getLogger(__name__)


class ManifestService:
    """Handle manifest upload, dedup detection, and pipeline orchestration"""

    def __init__(self, data_service_url: str = "http://localhost:8005"):
        self.data_service_url = data_service_url

    async def parse_and_detect_duplicates(
        self,
        file_content: bytes,
        filename: str,
        data_service_client,
    ) -> Dict[str, Any]:
        """
        Parse manifest file and detect duplicate rows.

        Returns:
        {
            manifest_id: str,
            filename: str,
            total_rows: int,
            new_rows: [],
            duplicate_rows: [{manifest_source_id, shipper, existing_shipment_id, existing_risk_score}],
            status: "needs_review" | "ready"
        }
        """
        try:
            # Parse file
            rows, parse_errors = parse_excel_manifest(file_content)
            if not rows:
                return {
                    "status": "error",
                    "message": f"Failed to parse manifest: {'; '.join(parse_errors)}",
                }

            manifest_id = str(uuid.uuid4())
            manifest_source_ids = [row.get("manifest_id") for row in rows if row.get("manifest_id")]

            # Query data service for existing manifest source IDs
            existing_map = {}
            if manifest_source_ids:
                resp = await data_service_client.get(
                    f"{self.data_service_url}/shipments",
                    params={"manifest_source_id__in": ",".join(manifest_source_ids)},
                )
                if resp.status_code == 200:
                    existing_rows = resp.json().get("data", [])
                    for row in existing_rows:
                        existing_map[row.get("manifest_source_id")] = {
                            "shipment_id": row.get("id"),
                            "shipper": row.get("shipper_name"),
                            "risk_score": row.get("risk_score"),
                        }

            # Classify rows
            new_rows = []
            duplicate_rows = []

            for row in rows:
                manifest_source_id = row.get("manifest_id")
                if manifest_source_id and manifest_source_id in existing_map:
                    duplicate_rows.append(
                        {
                            "manifest_source_id": manifest_source_id,
                            "row_number": row.get("rowNumber"),
                            "shipper": row.get("shipper"),
                            "consignee": row.get("consignee"),
                            "origin": row.get("origin_country"),
                            "existing_shipment_id": existing_map[manifest_source_id]["shipment_id"],
                            "existing_risk_score": existing_map[manifest_source_id]["risk_score"],
                        }
                    )
                else:
                    new_rows.append(row)

            logger.info(f"Manifest parse: {filename} → {len(new_rows)} new, {len(duplicate_rows)} duplicate")

            return {
                "status": "needs_review" if duplicate_rows else "ready",
                "manifest_id": manifest_id,
                "filename": filename,
                "total_rows": len(rows),
                "new_rows": new_rows,
                "duplicate_rows": duplicate_rows,
                "parse_errors": parse_errors if parse_errors else None,
            }

        except Exception as e:
            logger.error(f"Parse and dedup error: {e}")
            return {"status": "error", "message": str(e)}

    async def confirm_and_insert(
        self,
        manifest_id: str,
        rows_to_insert: List[Dict[str, Any]],
        data_service_client,
    ) -> Dict[str, Any]:
        """
        Create manifest record and insert confirmed rows as shipments.

        Returns: {manifest_id, shipment_ids, row_count}
        """
        try:
            # Create manifest record
            manifest_payload = {
                "filename": f"imported-{manifest_id}.xlsx",
                "row_count": len(rows_to_insert),
                "extracted_at": datetime.utcnow().isoformat(),
            }
            resp = await data_service_client.post(
                f"{self.data_service_url}/manifests",
                json=manifest_payload,
            )
            if resp.status_code != 200:
                return {
                    "status": "error",
                    "message": f"Failed to create manifest: {resp.text}",
                }

            # Insert shipments
            shipment_ids = []
            for row in rows_to_insert:
                shipment_payload = {
                    "manifest_id": manifest_id,
                    "manifest_source_id": row.get("manifest_id"),
                    "shipper_name": row.get("shipper"),
                    "consignee_name": row.get("consignee"),
                    "origin_country": row.get("origin_country"),
                    "destination_country": row.get("destination_country"),
                    "hs_code": row.get("hs_code"),
                    "declared_value_usd": row.get("declared_value_usd"),
                    "declared_weight_kg": row.get("declared_weight_kg"),
                    "description": row.get("description"),
                    "vessel_name": row.get("vessel_name"),
                }
                resp = await data_service_client.post(
                    f"{self.data_service_url}/shipments",
                    json=shipment_payload,
                )
                if resp.status_code == 200:
                    shipment_data = resp.json()
                    shipment_ids.append(shipment_data.get("id"))
                else:
                    logger.error(f"Failed to create shipment: {resp.text}")

            logger.info(f"Manifest {manifest_id} inserted {len(shipment_ids)} shipments")

            return {
                "status": "success",
                "manifest_id": manifest_id,
                "shipment_ids": shipment_ids,
                "row_count": len(shipment_ids),
            }

        except Exception as e:
            logger.error(f"Confirm and insert error: {e}")
            return {"status": "error", "message": str(e)}
