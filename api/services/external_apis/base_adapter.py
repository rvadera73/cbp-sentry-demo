"""
Base adapter class for external APIs with live/fixture support
"""
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import aiohttp
from services.external_apis.config import get_api_mode, get_api_key

logger = logging.getLogger(__name__)


class BaseAPIAdapter(ABC):
    """Base class for external API adapters"""

    def __init__(self, api_name: str):
        self.api_name = api_name
        self.mode = get_api_mode(api_name)
        self.api_key = get_api_key(api_name)
        logger.info(f"Initialized {api_name} adapter in {self.mode} mode")

    @abstractmethod
    async def fetch_live(self, **kwargs) -> Dict[str, Any]:
        """Fetch from real API - override in subclass"""
        pass

    @abstractmethod
    def fetch_fixture(self, **kwargs) -> Dict[str, Any]:
        """Return fixture data - override in subclass"""
        pass

    async def fetch(self, **kwargs) -> Dict[str, Any]:
        """Main fetch method - routes to live or fixture based on mode"""
        try:
            if self.mode == "live":
                logger.debug(f"Fetching from live {self.api_name}")
                return await self.fetch_live(**kwargs)
            else:
                logger.debug(f"Fetching from fixture {self.api_name}")
                return self.fetch_fixture(**kwargs)
        except Exception as e:
            logger.warning(f"Error fetching from {self.api_name} ({self.mode}): {e}")
            # Fallback to fixture on error
            try:
                logger.info(f"Falling back to fixture for {self.api_name}")
                return self.fetch_fixture(**kwargs)
            except Exception as e2:
                logger.error(f"Fixture fallback also failed: {e2}")
                return {"error": str(e), "data": None}

    async def http_get(self, url: str, params: Optional[Dict] = None, **kwargs) -> Dict[str, Any]:
        """Helper for HTTP GET requests"""
        try:
            headers = kwargs.get("headers", {})
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"

            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    else:
                        raise Exception(f"HTTP {resp.status}: {await resp.text()}")
        except Exception as e:
            logger.error(f"HTTP request failed: {e}")
            raise

    def add_data_source_metadata(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Add metadata about data source and confidence"""
        return {
            **data,
            "_metadata": {
                "source": self.api_name,
                "mode": self.mode,
                "confidence": 0.95 if self.mode == "live" else 0.50,
            },
        }
