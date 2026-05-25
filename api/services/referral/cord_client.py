"""CORD microservice client for entity resolution.

Calls the CORD microservice (http://sentry-cord-integration:8004) to resolve
3-level entity chains via Senzing entity resolution engine.

Used by: EntityGraphService to get real entity data instead of fixtures.
"""

import httpx
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class CORDClient:
    """Client for CORD entity resolution microservice."""

    def __init__(self, base_url: str = "http://sentry-cord-integration:8004"):
        """Initialize CORD client.

        Args:
            base_url: Base URL of CORD microservice (default: localhost:8004)
        """
        self.base_url = base_url
        self.timeout = 30.0
        self.logger = logger

    async def resolve_shipment_entities(
        self,
        shipper_name: str,
        shipper_country: str,
        consignee_name: str,
        consignee_country: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Resolve 3-level entity chain via CORD microservice.

        Calls CORD /resolve endpoint to get entity resolution:
        - Level 1: Direct shipper entity
        - Level 2: Parent company/intermediary
        - Level 3: Ultimate owner
        - Plus OFAC detection and risk scoring

        Args:
            shipper_name: Shipper entity name (required)
            shipper_country: Shipper country code (e.g., "VN", "CN")
            consignee_name: Consignee entity name (required)
            consignee_country: Consignee country code (e.g., "US")
            context: Optional context dict with manifest data:
                - element_9_mismatch: bool
                - stuffing_country: str
                - dwell_anomaly: bool
                - new_shipper: bool
                - declared_origin: str

        Returns:
            3-level entity chain with relationships:
            {
                "level_1": {
                    "entity_id": "ENT-GF-VN-001",
                    "name": "Greenfield Industrial...",
                    "country": "VN",
                    "confidence": 0.98,
                    "data_source": "CORD",
                    "entity_type": "SHIPPER",
                    "related_entities": [
                        {
                            "entity_id": "ENT-GF-HK-001",
                            "name": "Greenfield Global Metals Holdings Ltd.",
                            "relationship": "OWNED_BY",
                            "confidence": 0.95
                        }
                    ]
                },
                "level_2": { ... },
                "level_3": { ... },
                "ofac_detected": false,
                "risk_score": 72,
                "confidence_metrics": { ... }
            }

            Returns None if CORD is unavailable or request fails.
        """
        try:
            payload = {
                "shipper_name": shipper_name,
                "shipper_country": shipper_country,
                "consignee_name": consignee_name,
                "consignee_country": consignee_country,
            }

            if context:
                payload["context"] = context

            self.logger.info(
                f"Resolving entities: {shipper_name} ({shipper_country}) "
                f"→ {consignee_name} ({consignee_country})"
            )

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/resolve",
                    json=payload,
                    headers={"Content-Type": "application/json"},
                )

                if response.status_code == 200:
                    data = response.json()
                    self.logger.info(
                        f"✅ CORD resolved entities for {shipper_name}: "
                        f"L1={data.get('level_1', {}).get('name')} "
                        f"→ L2={data.get('level_2', {}).get('name')} "
                        f"→ L3={data.get('level_3', {}).get('name')}"
                    )
                    return data
                else:
                    self.logger.error(
                        f"CORD returned {response.status_code}: {response.text}"
                    )
                    return None

        except httpx.TimeoutException:
            self.logger.error(
                f"CORD timeout ({self.timeout}s). Is microservice running at {self.base_url}?"
            )
            return None
        except httpx.ConnectError as e:
            self.logger.error(
                f"Cannot connect to CORD at {self.base_url}. "
                f"Error: {e}. Is sentry-cord-integration:8004 running?"
            )
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error calling CORD: {e}")
            return None

    async def get_health(self) -> Optional[Dict[str, Any]]:
        """Check CORD microservice health.

        Returns health status, entity count, and initialization state.

        Returns:
            {
                "status": "ready",
                "entity_count": 245000,
                "initialized": true
            }

            Returns None if service is unavailable.
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/health")
                if response.status_code == 200:
                    return response.json()
                return None
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return None
