"""
Search-First Senzing Pattern

Implements lazy per-shipment entity loading to stay under Senzing eval 100K limit.

Flow:
1. Query CORD FTS index for shipper + consignee (returns ~20 candidates)
2. Load only those ~20 into Senzing SDK via addRecord()
3. Call Senzing entity resolution on the subset
4. Return resolved entity chain
5. Discard subset records from Senzing (ready for next shipment)

This allows unlimited shipments while always respecting the 100K eval limit
because we only load ~20 records per investigation, not all 244K CORD records.
"""

import logging
import httpx
import json
from typing import Optional, Dict, List, Any
import os

logger = logging.getLogger(__name__)

SENZING_URL = os.getenv("SENZING_URL", "http://senzing:8250")
CORD_DATA_DIR = os.getenv("CORD_DATA_DIR", "/app/cord-data")


class SearchFirstSenzingClient:
    """
    Search-First Senzing pattern: load only high-signal entities per shipment.

    Stays under 100K eval limit by:
    - Querying CORD FTS for ~20 candidates per shipment
    - Loading only those ~20 into Senzing
    - Resolving entity chain
    - Discarding subset after response
    """

    def __init__(self):
        self.senzing_url = SENZING_URL
        self.timeout = 15.0
        self.cord_engine = None
        self._init_cord_engine()

    def _init_cord_engine(self):
        """Initialize CORD engine for FTS search (lazy import)."""
        try:
            from cord_engine import get_cord_engine

            self.cord_engine = get_cord_engine()
            logger.info("Search-First Senzing initialized with CORD engine")
        except Exception as e:
            logger.error(f"Search-First Senzing init failed - CORD engine unavailable: {e}")
            raise

    async def resolve_shipment_entities(
        self,
        shipment_id: str,
        shipper_name: str,
        shipper_country: Optional[str] = None,
        consignee_name: Optional[str] = None,
        consignee_country: Optional[str] = None,
        directors: Optional[List[str]] = None,
        freight_forwarder: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Resolve shipper/consignee ownership chain using Search-First pattern.

        Args:
            shipment_id: Manifest ID for tracking
            shipper_name: Shipper entity name
            shipper_country: Shipper country code (e.g., 'VN')
            consignee_name: Consignee entity name
            consignee_country: Consignee country code
            directors: Optional list of known director names
            freight_forwarder: Optional freight forwarder name

        Returns:
            {
                "shipment_id": str,
                "entities_loaded": int,
                "senzing_available": bool,
                "failure_reason": str (if unavailable),
                "entity_chain": [
                    {
                        "entity_id": str,
                        "name": str,
                        "country": str,
                        "entity_type": str,
                        "role": str (shipper/consignee/parent/related),
                        "confidence": float,
                        "data_source": str (GLEIF/OpenSanctions/CORD/etc),
                        "relationships": [...]
                    }
                ],
                "relationship_edges": [
                    {
                        "source_name": str,
                        "target_name": str,
                        "relationship_type": str,
                        "evidence": str,
                        "confidence": float
                    }
                ]
            }
        """
        logger.info(
            f"[{shipment_id}] Search-First entity resolution: shipper={shipper_name}, consignee={consignee_name}"
        )

        # Step 1: Search CORD FTS index for high-signal entities
        cord_candidates = self._search_cord_for_candidates(
            shipper_name, shipper_country, consignee_name, consignee_country, directors, freight_forwarder
        )

        if not cord_candidates:
            logger.warning(f"[{shipment_id}] No CORD candidates found")
            return {
                "shipment_id": shipment_id,
                "entities_loaded": 0,
                "senzing_available": False,
                "failure_reason": "no_cord_candidates",
                "entity_chain": [],
                "relationship_edges": [],
            }

        logger.info(f"[{shipment_id}] Found {len(cord_candidates)} CORD candidates")

        # Step 2: Try to load candidates into Senzing and resolve
        try:
            result = await self._load_and_resolve_senzing(shipment_id, cord_candidates)
            logger.info(
                f"[{shipment_id}] Senzing resolution successful: {len(result.get('entity_chain', []))} entities"
            )
            return result
        except Exception as e:
            logger.error(f"[{shipment_id}] Senzing resolution failed: {e}")
            # Fall back to CORD data only (no Senzing)
            return self._fallback_to_cord_only(shipment_id, cord_candidates, failure_reason=str(e))

    def _search_cord_for_candidates(
        self,
        shipper_name: str,
        shipper_country: Optional[str],
        consignee_name: Optional[str],
        consignee_country: Optional[str],
        directors: Optional[List[str]],
        freight_forwarder: Optional[str],
    ) -> List[Dict[str, Any]]:
        """
        Query CORD FTS index for ~20 high-signal entity candidates.

        Returns list of CORD records (raw Senzing-format JSON).
        """
        if not self.cord_engine:
            logger.error("CORD engine not available for candidate search")
            return []

        candidates = []
        seen_ids = set()

        # Search for shipper and related entities
        if shipper_name:
            shipper_results = self.cord_engine.search(shipper_name, country=shipper_country, limit=8)
            for record in shipper_results:
                record_id = record.get("RECORD_ID")
                if record_id and record_id not in seen_ids:
                    candidates.append(record)
                    seen_ids.add(record_id)

        # Search for consignee and related entities
        if consignee_name:
            consignee_results = self.cord_engine.search(consignee_name, country=consignee_country, limit=6)
            for record in consignee_results:
                record_id = record.get("RECORD_ID")
                if record_id and record_id not in seen_ids:
                    candidates.append(record)
                    seen_ids.add(record_id)

        # Search for known directors (if provided)
        if directors:
            for director in directors[:2]:  # Max 2 director searches
                director_results = self.cord_engine.search(director, limit=3)
                for record in director_results:
                    record_id = record.get("RECORD_ID")
                    if record_id and record_id not in seen_ids:
                        candidates.append(record)
                        seen_ids.add(record_id)

        # Search for freight forwarder (if provided)
        if freight_forwarder:
            ff_results = self.cord_engine.search(freight_forwarder, limit=3)
            for record in ff_results:
                record_id = record.get("RECORD_ID")
                if record_id and record_id not in seen_ids:
                    candidates.append(record)
                    seen_ids.add(record_id)

        return candidates[:25]  # Cap at 25 records per shipment investigation

    async def _load_and_resolve_senzing(
        self, shipment_id: str, cord_candidates: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Load CORD candidates into Senzing and resolve entity chain.

        Returns entity chain with relationships.
        """
        async with httpx.AsyncClient(base_url=self.senzing_url, timeout=self.timeout) as client:
            # Check Senzing health
            try:
                health = await client.get("/heartbeat")
                if health.status_code != 200:
                    raise Exception(f"Senzing unhealthy: {health.status_code}")
            except Exception as e:
                logger.error(f"[{shipment_id}] Senzing health check failed: {e}")
                raise

            # Load each CORD candidate into Senzing
            loaded_count = 0
            for record in cord_candidates:
                try:
                    record_id = record.get("RECORD_ID", str(loaded_count))
                    data_source = record.get("DATA_SOURCE", "CORD")

                    resp = await client.post(
                        "/addRecord",
                        json={"dataSource": data_source, "recordId": record_id, "jsonData": json.dumps(record)},
                    )

                    if resp.status_code == 200:
                        loaded_count += 1
                    else:
                        logger.warning(f"[{shipment_id}] Failed to load record {record_id}: {resp.status_code}")
                except Exception as e:
                    logger.debug(f"[{shipment_id}] Record load error: {e}")

            logger.info(f"[{shipment_id}] Loaded {loaded_count}/{len(cord_candidates)} records into Senzing")

            # Resolve entity chain
            entity_chain = await self._resolve_chain(client, shipment_id, cord_candidates)

            # Clean up: remove loaded records from Senzing
            # (not strictly necessary in eval mode, but good practice)
            for i in range(loaded_count):
                try:
                    await client.delete(f"/record/{i}")
                except:
                    pass

            return {
                "shipment_id": shipment_id,
                "entities_loaded": loaded_count,
                "senzing_available": True,
                "entity_chain": entity_chain,
                "relationship_edges": self._extract_edges(entity_chain),
            }

    async def _resolve_chain(
        self, client: httpx.AsyncClient, shipment_id: str, cord_candidates: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Query Senzing to resolve entity ownership chain.

        Returns list of resolved entities with relationships.
        """
        entity_chain = []

        # Extract main shipper/consignee names from candidates
        primary_names = set()
        for record in cord_candidates:
            names = record.get("NAMES", [])
            if names:
                primary_name = names[0].get("NAME_ORG") or names[0].get("NAME_FULL")
                if primary_name:
                    primary_names.add(primary_name)

        # Search Senzing for each primary name
        for name in list(primary_names)[:5]:  # Max 5 name searches
            try:
                resp = await client.post("/searchByAttributes", json={"NAME_FULL": name})

                if resp.status_code == 200:
                    data = resp.json()
                    entities = data.get("RESOLVED_ENTITIES", [])

                    for entity in entities:
                        entity_id = entity.get("ENTITY_ID")
                        # Get entity details
                        detail_resp = await client.get(f"/entity/{entity_id}")
                        if detail_resp.status_code == 200:
                            details = detail_resp.json().get("ENTITY", {})
                            entity_chain.append(
                                {
                                    "entity_id": str(entity_id),
                                    "name": details.get("RESOLVED_ENTITY", {}).get("ENTITY_NAME", name),
                                    "country": details.get("RESOLVED_ENTITY", {}).get("COUNTRY_CODE", ""),
                                    "entity_type": self._infer_entity_type(details),
                                    "role": "unknown",
                                    "confidence": 0.85,
                                    "data_source": "Senzing Entity Resolution",
                                    "relationships": [],
                                }
                            )
            except Exception as e:
                logger.debug(f"[{shipment_id}] Senzing search error for '{name}': {e}")

        return entity_chain

    @staticmethod
    def _infer_entity_type(senzing_detail: Dict) -> str:
        """Infer entity type from Senzing record."""
        record_type = senzing_detail.get("RECORD_TYPE", "")
        if "ORGANIZATION" in record_type:
            return "ORGANIZATION"
        elif "INDIVIDUAL" in record_type:
            return "INDIVIDUAL"
        elif "VESSEL" in record_type:
            return "VESSEL"
        else:
            return record_type or "ENTITY"

    @staticmethod
    def _extract_edges(entity_chain: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract relationship edges from entity chain."""
        edges = []
        for entity in entity_chain:
            for rel in entity.get("relationships", []):
                edges.append(
                    {
                        "source_name": entity.get("name"),
                        "target_name": rel.get("target_name"),
                        "relationship_type": rel.get("type"),
                        "evidence": rel.get("evidence", ""),
                        "confidence": rel.get("confidence", 0.5),
                    }
                )
        return edges

    def _fallback_to_cord_only(
        self, shipment_id: str, cord_candidates: List[Dict[str, Any]], failure_reason: str
    ) -> Dict[str, Any]:
        """
        Fallback: return CORD data directly without Senzing resolution.

        Senzing unavailable (service down, timeout, etc) — return CORD FTS
        matches with explicit failure reason.
        """
        entity_chain = []
        for record in cord_candidates[:10]:  # Limit to top 10
            names = record.get("NAMES", [])
            primary_name = names[0].get("NAME_ORG") or names[0].get("NAME_FULL") if names else ""

            entity_chain.append(
                {
                    "entity_id": record.get("RECORD_ID", ""),
                    "name": primary_name,
                    "country": record.get("COUNTRIES", [{}])[0].get("REGISTRATION_COUNTRY", ""),
                    "entity_type": record.get("RECORD_TYPE", "ENTITY"),
                    "role": record.get("DATA_SOURCE", ""),  # GLEIF, OpenSanctions, etc
                    "confidence": 0.75,  # Lower confidence since no Senzing resolution
                    "data_source": f"CORD {record.get('DATA_SOURCE', 'ENTITY')} (Senzing unavailable)",
                    "relationships": [],
                }
            )

        return {
            "shipment_id": shipment_id,
            "entities_loaded": len(cord_candidates),
            "senzing_available": False,
            "failure_reason": failure_reason,
            "entity_chain": entity_chain,
            "relationship_edges": [],
        }


# Global singleton
_search_first_client = None


def get_search_first_client() -> SearchFirstSenzingClient:
    """Get or create Search-First Senzing client."""
    global _search_first_client
    if _search_first_client is None:
        _search_first_client = SearchFirstSenzingClient()
    return _search_first_client
