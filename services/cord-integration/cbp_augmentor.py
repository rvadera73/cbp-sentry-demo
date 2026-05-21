"""CBP ISF + Shipment Augmentor - Fetch shipments from data service and index into Senzing."""
import os
import json
import logging
import sqlite3
from typing import Dict, Any, List, Optional
from datetime import datetime

import httpx

logger = logging.getLogger(__name__)


class CBPAugmentor:
    """Fetch CBP shipments and create Senzing records for ISF + shipper augmentation."""

    def __init__(self, data_service_url: str = "http://localhost:8005", db_path: str = "/app/data/senzing.db"):
        """Initialize CBP augmentor.

        Args:
            data_service_url: URL to data service
            db_path: Path to Senzing SQLite database
        """
        self.data_service_url = data_service_url
        self.db_path = db_path
        self.conn = None
        self.cursor = None

    async def augment_shipments(self) -> Dict[str, Any]:
        """Fetch all shipments from data service and index as Senzing records.

        Returns:
            Dict with augmentation statistics
        """
        try:
            # Connect to database
            self.conn = sqlite3.connect(self.db_path)
            self.cursor = self.conn.cursor()

            # Fetch shipments from data service
            logger.info(f"Fetching shipments from {self.data_service_url}...")
            shipments = await self._fetch_shipments()

            if not shipments:
                logger.warning("No shipments fetched")
                return {
                    "status": "success",
                    "shipment_count": 0,
                    "cbp_shipper_records": 0,
                    "cbp_isf_records": 0
                }

            logger.info(f"Fetched {len(shipments)} shipments")

            shipper_count = 0
            isf_count = 0
            relationship_count = 0

            # Process each shipment
            for shipment in shipments:
                try:
                    # Create CBP-SHIPPER record
                    shipper_record = self._create_shipper_record(shipment)
                    if shipper_record:
                        self._insert_cbp_record(shipper_record)
                        shipper_count += 1

                    # Create CBP-ISF record
                    isf_record = self._create_isf_record(shipment)
                    if isf_record:
                        self._insert_cbp_record(isf_record)
                        isf_count += 1

                        # Link ISF to shipper
                        if shipper_record:
                            self._add_isf_shipper_link(shipper_record["entity_id"], isf_record["entity_id"])
                            relationship_count += 1

                except Exception as e:
                    logger.error(f"Error processing shipment {shipment.get('id')}: {e}")
                    continue

            self.conn.commit()
            self.conn.close()

            logger.info(f"✓ Augmentation complete: {shipper_count} shippers, {isf_count} ISF records, {relationship_count} links")

            return {
                "status": "success",
                "shipment_count": len(shipments),
                "cbp_shipper_records": shipper_count,
                "cbp_isf_records": isf_count,
                "relationships_created": relationship_count
            }

        except Exception as e:
            logger.error(f"Augmentation failed: {e}")
            if self.conn:
                self.conn.close()
            return {
                "status": "failed",
                "reason": str(e)
            }

    async def _fetch_shipments(self) -> List[Dict[str, Any]]:
        """Fetch all shipments from data service."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # First get shipment count
                resp = await client.get(f"{self.data_service_url}/shipments?limit=1")
                if resp.status_code != 200:
                    logger.error(f"Failed to fetch shipments: {resp.status_code}")
                    return []

                # Fetch all shipments
                resp = await client.get(f"{self.data_service_url}/shipments?limit=9999")
                if resp.status_code == 200:
                    data = resp.json()
                    return data.get("shipments", []) if isinstance(data, dict) else data

                return []

        except Exception as e:
            logger.error(f"Fetch shipments failed: {e}")
            return []

    def _create_shipper_record(self, shipment: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create CBP-SHIPPER Senzing record from shipment."""
        try:
            shipper_name = shipment.get("shipper_name", "")
            if not shipper_name:
                return None

            entity_id = f"CBP-SHIPPER:{shipment.get('id', 'unknown')}"
            shipper_age_months = shipment.get("shipper_age_months")
            ad_cvd_rate = shipment.get("ad_cvd_rate")
            risk_score = shipment.get("risk_score")
            origin_country = shipment.get("origin_country", "")

            # Calculate confidence based on data completeness
            confidence = 1.0
            if not shipper_age_months:
                confidence -= 0.1
            if not ad_cvd_rate:
                confidence -= 0.05

            return {
                "entity_id": entity_id,
                "data_source": "CBP-SHIPPER",
                "record_id": shipment.get("id"),
                "name": shipper_name,
                "country": origin_country,
                "entity_type": "shipper",
                "confidence": max(0.5, confidence),
                "attributes": {
                    "shipper_name": shipper_name,
                    "shipper_age_months": shipper_age_months,
                    "ad_cvd_rate": ad_cvd_rate,
                    "risk_score": risk_score,
                    "origin_country": origin_country
                }
            }

        except Exception as e:
            logger.error(f"Create shipper record failed: {e}")
            return None

    def _create_isf_record(self, shipment: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create CBP-ISF Senzing record from shipment."""
        try:
            declared_country = shipment.get("element9_declared_country")
            actual_country = shipment.get("element9_actual_country")

            if not declared_country:
                return None

            entity_id = f"CBP-ISF:{shipment.get('id', 'unknown')}"

            # Calculate confidence based on country match
            confidence = 1.0
            if declared_country != actual_country:
                confidence = 0.7  # Lower confidence if countries don't match

            return {
                "entity_id": entity_id,
                "data_source": "CBP-ISF",
                "record_id": f"ISF-{shipment.get('id')}",
                "name": f"ISF {shipment.get('manifest_id', '')}",
                "country": declared_country,
                "entity_type": "isf_record",
                "confidence": confidence,
                "attributes": {
                    "element9_declared_country": declared_country,
                    "element9_actual_country": actual_country,
                    "manifest_id": shipment.get("manifest_id"),
                    "shipment_id": shipment.get("id"),
                    "origin_country": shipment.get("origin_country"),
                    "declared_value_usd": shipment.get("declared_value_usd")
                }
            }

        except Exception as e:
            logger.error(f"Create ISF record failed: {e}")
            return None

    def _insert_cbp_record(self, record: Dict[str, Any]):
        """Insert CBP record into Senzing database."""
        try:
            self.cursor.execute("""
                INSERT OR REPLACE INTO senzing_entities
                (entity_id, data_source, record_id, name_primary, country, entity_type, confidence, raw_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.get("entity_id"),
                record.get("data_source"),
                record.get("record_id"),
                record.get("name"),
                record.get("country"),
                record.get("entity_type"),
                record.get("confidence"),
                json.dumps(record)
            ))

        except Exception as e:
            logger.error(f"Insert CBP record failed: {e}")
            raise

    def _add_isf_shipper_link(self, shipper_entity_id: str, isf_entity_id: str):
        """Create relationship link between shipper and ISF record."""
        try:
            self.cursor.execute("""
                INSERT INTO senzing_relationships
                (entity_id_a, entity_id_b, relationship_type, confidence, evidence)
                VALUES (?, ?, ?, ?, ?)
            """, (
                shipper_entity_id,
                isf_entity_id,
                "ISF_SHIPMENT",
                1.0,
                json.dumps([{"type": "ISF_DECLARATION", "details": "Shipment ISF record"}])
            ))

        except Exception as e:
            logger.error(f"Add ISF shipper link failed: {e}")
            raise


async def augment_cbp_shipments_async(
    data_service_url: str = "http://localhost:8005",
    db_path: str = "/app/data/senzing.db"
) -> Dict[str, Any]:
    """Augment Senzing database with CBP shipment data.

    Args:
        data_service_url: URL to data service
        db_path: Path to Senzing SQLite database

    Returns:
        Dict with augmentation results
    """
    augmentor = CBPAugmentor(data_service_url, db_path)
    return await augmentor.augment_shipments()


if __name__ == "__main__":
    import asyncio

    logging.basicConfig(level=logging.INFO)

    # Run augmentor
    result = asyncio.run(augment_cbp_shipments_async())
    print(json.dumps(result, indent=2))
