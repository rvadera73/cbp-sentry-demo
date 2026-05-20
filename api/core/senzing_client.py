"""Senzing entity resolution client with mock fallback"""

import httpx
import logging
from typing import Optional, Dict, Any, Union
from core.config import settings
from core.mock_senzing_client import MockSenzingClient

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

# Global client instance (can be SenzingClient or MockSenzingClient)
_senzing_client: Optional[Union[SenzingClient, MockSenzingClient]] = None
_use_mock: bool = False


async def init_senzing():
    """Initialize Senzing client with automatic fallback to mock"""
    global _senzing_client, _use_mock

    # Check if mock mode is explicitly requested
    if settings.use_mock_senzing:
        logger.info("Using MOCK Senzing client (license unavailable or disabled)")
        _senzing_client = MockSenzingClient()
        _use_mock = True
        return _senzing_client

    # Try real Senzing first
    _senzing_client = SenzingClient()
    health = await _senzing_client.health()

    if health:
        logger.info("Senzing service is healthy — using real client")
        _use_mock = False
        return _senzing_client

    # Fall back to mock
    logger.warning("Senzing service unavailable — falling back to MOCK client")
    logger.warning("To use real Senzing: place license at ./senzing/senzing.license and run: docker-compose up")
    _senzing_client = MockSenzingClient()
    _use_mock = True
    return _senzing_client


def get_senzing_client() -> Union[SenzingClient, MockSenzingClient]:
    """Get the Senzing client instance"""
    global _senzing_client
    if _senzing_client is None:
        raise RuntimeError("Senzing client not initialized — call init_senzing() first")
    return _senzing_client


def is_using_mock() -> bool:
    """Check if using mock client"""
    return _use_mock
