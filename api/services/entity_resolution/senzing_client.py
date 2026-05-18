"""
Senzing entity resolution client.

Interfaces with Senzing REST API (or mock for testing) to:
- Load records into Senzing
- Search for entity matches
- Get why-explanations for matches
- Find related entities
"""

import logging
import requests
from typing import Dict, List, Optional
from requests.exceptions import RequestException, Timeout, ConnectionError

logger = logging.getLogger(__name__)


class SenzingClient:
    """Client for Senzing entity resolution service."""

    def __init__(self, base_url: str = "http://localhost:8250"):
        """
        Initialize Senzing client.

        Args:
            base_url: Base URL for Senzing service (default: localhost:8250)
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = 30

    def health_check(self) -> Dict:
        """
        Check Senzing service health.

        Returns:
            Dict with status field
        """
        try:
            response = requests.get(
                f"{self.base_url}/health",
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except (ConnectionError, Timeout) as e:
            logger.error(f"Senzing health check failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during health check: {e}")
            raise

    def load_record(self, record: Dict) -> str:
        """
        Load an entity record into Senzing.

        Args:
            record: Entity record dict with keys: name, country, director, phone, etc.

        Returns:
            Senzing record_id (string)

        Raises:
            ConnectionError: If Senzing service is unreachable
            ValueError: If response is invalid
        """
        try:
            payload = {
                "DATA_SOURCE": "CBP",
                "RECORD_ID": record.get("id", ""),
                "NAME_FULL": record.get("name", ""),
                "COUNTRY_CODE": record.get("country", ""),
                "ADDR_FULL": record.get("address", ""),
                "PHONE_NUMBER": record.get("phone", ""),
            }

            # Add optional fields
            if "director" in record:
                payload["TITLE"] = record["director"]
            if "type" in record:
                payload["ENTITY_TYPE"] = record["type"]
            if "incorporated_date" in record:
                payload["DATE_OF_BIRTH"] = record["incorporated_date"]

            response = requests.post(
                f"{self.base_url}/records",
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()

            # Extract record_id from response
            if "RECORD_ID" in data:
                return str(data["RECORD_ID"])
            elif "record_id" in data:
                return str(data["record_id"])
            else:
                raise ValueError(f"No record_id in response: {data}")

        except (ConnectionError, Timeout) as e:
            logger.error(f"Failed to load record into Senzing: {e}")
            raise
        except Exception as e:
            logger.error(f"Error loading record: {e}")
            raise

    def search_entity(self, entity_data: Dict) -> List[Dict]:
        """
        Search for matching entities in Senzing.

        Args:
            entity_data: Entity data dict with name, country, etc.

        Returns:
            List of matching entities with record_id, name, country, confidence
        """
        try:
            payload = {
                "NAME_FULL": entity_data.get("name", ""),
                "COUNTRY_CODE": entity_data.get("country", ""),
                "ADDR_FULL": entity_data.get("address", ""),
                "PHONE_NUMBER": entity_data.get("phone", ""),
            }

            response = requests.post(
                f"{self.base_url}/search",
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()

            # Handle response format
            if isinstance(data, dict):
                if "ENTITIES" in data:
                    entities = data["ENTITIES"]
                elif "entities" in data:
                    entities = data["entities"]
                else:
                    entities = []
            elif isinstance(data, list):
                entities = data
            else:
                entities = []

            # Normalize results
            results = []
            for entity in entities:
                results.append({
                    "record_id": entity.get("RECORD_ID") or entity.get("record_id"),
                    "name": entity.get("NAME_FULL") or entity.get("name"),
                    "country": entity.get("COUNTRY_CODE") or entity.get("country"),
                    "confidence": float(entity.get("CONFIDENCE", 0) or
                                      entity.get("confidence", 0)),
                    "match_key": entity.get("MATCH_KEY", "").upper()
                })
            return results

        except (ConnectionError, Timeout) as e:
            logger.error(f"Entity search failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Error searching entities: {e}")
            raise

    def why_entities(self, entity_a: str, entity_b: str) -> Dict:
        """
        Get why-explanation for why two entities are matched.

        Args:
            entity_a: First entity record_id
            entity_b: Second entity record_id

        Returns:
            Dict with why_key, confidence, and match_factors list
        """
        try:
            response = requests.get(
                f"{self.base_url}/why/{entity_a}/{entity_b}",
                timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()

            # Normalize response
            return {
                "why_key": data.get("WHY_KEY") or data.get("why_key", ""),
                "entity_a": entity_a,
                "entity_b": entity_b,
                "confidence": float(data.get("CONFIDENCE", 0) or data.get("confidence", 0)),
                "match_factors": data.get("MATCH_FACTORS", data.get("match_factors", []))
            }

        except (ConnectionError, Timeout) as e:
            logger.error(f"Why explanation failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Error getting why explanation: {e}")
            raise

    def related_entities(self, entity_id: str) -> List[Dict]:
        """
        Get entities related to a given entity.

        Args:
            entity_id: Entity record_id

        Returns:
            List of related entity record_ids
        """
        try:
            response = requests.get(
                f"{self.base_url}/entities/{entity_id}/related",
                timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()

            # Handle response format
            if isinstance(data, dict):
                if "ENTITIES" in data:
                    entities = data["ENTITIES"]
                elif "entities" in data:
                    entities = data["entities"]
                else:
                    entities = []
            elif isinstance(data, list):
                entities = data
            else:
                entities = []

            # Return list of entity IDs
            result = []
            for entity in entities:
                entity_id = entity.get("RECORD_ID") or entity.get("record_id")
                if entity_id:
                    result.append(str(entity_id))
            return result

        except (ConnectionError, Timeout) as e:
            logger.error(f"Related entities query failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Error querying related entities: {e}")
            raise
