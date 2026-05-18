"""Senzing entity resolution client"""

import httpx
import logging
from typing import Optional, Dict, Any
from core.config import settings

logger = logging.getLogger(__name__)

class SenzingClient:
    """Thin HTTP client for Senzing REST API"""

    def __init__(self, base_url: str = settings.senzing_url):
        self.base_url = base_url.rstrip("/")
        self.client = httpx.AsyncClient(base_url=self.base_url, timeout=30.0)

    async def health(self) -> bool:
        """Check Senzing service health"""
        try:
            response = await self.client.get("/heartbeat")
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Senzing health check failed: {e}")
            return False

    async def add_record(
        self,
        data_source: str,
        record_id: str,
        record: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Add a record to Senzing for entity resolution"""
        try:
            response = await self.client.post(
                "/v3/records",
                json={
                    "data_source": data_source,
                    "record_id": record_id,
                    **record
                }
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to add record to Senzing: {e}")
            raise

    async def search_by_attributes(self, attributes: Dict[str, str]) -> Dict[str, Any]:
        """Search for entities by attributes"""
        try:
            response = await self.client.post(
                "/v3/entities/search",
                json={"attributes": attributes}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Senzing search failed: {e}")
            raise

    async def get_entity(self, entity_id: int) -> Dict[str, Any]:
        """Get entity details by ID"""
        try:
            response = await self.client.get(f"/v3/entities/{entity_id}")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get entity {entity_id}: {e}")
            raise

    async def why_entities(self, entity_id_a: int, entity_id_b: int) -> Dict[str, Any]:
        """Get explanation for why two entities were linked"""
        try:
            response = await self.client.post(
                "/v3/why/entities",
                json={"entity_ids": [entity_id_a, entity_id_b]}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get why explanation: {e}")
            raise

    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()

# Global client instance
_senzing_client: Optional[SenzingClient] = None

async def init_senzing():
    """Initialize Senzing client"""
    global _senzing_client
    _senzing_client = SenzingClient()
    health = await _senzing_client.health()
    if not health:
        logger.warning("Senzing service not available — using mock responses")
    return _senzing_client

def get_senzing_client() -> SenzingClient:
    """Get the Senzing client instance"""
    global _senzing_client
    if _senzing_client is None:
        # Initialize synchronously if needed
        raise RuntimeError("Senzing client not initialized")
    return _senzing_client
