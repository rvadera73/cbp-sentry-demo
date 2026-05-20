"""Senzing entity resolution client.

Wraps Senzing REST API for entity matching and why-explanation queries.
Supports both live Senzing service and fixture mode for offline demo.
"""
import httpx
import os
import json
from typing import Optional, Dict, List
import logging

logger = logging.getLogger(__name__)

SENZING_URL = os.getenv("SENZING_URL", "http://senzing:8250")
API_MODE = os.getenv("API_MODE", "fixture")


class SenzingClient:
    """Client for Senzing entity resolution."""

    def __init__(self):
        self.base_url = SENZING_URL
        self.timeout = 10.0
        self.fixtures = self._load_fixtures()

    def _load_fixtures(self) -> Dict:
        """Load fixture entity data for offline demo mode."""
        return {
            "greenfield_vn": {
                "entity_id": "ENT-GF-VN-001",
                "name": "Greenfield Industrial Trading Co., Ltd.",
                "country": "VN",
                "incorporation_date": "2025-09-15",
                "entity_type": "shipper",
                "confidence": 0.98,
                "related_entities": [
                    {
                        "entity_id": "ENT-GF-HK-001",
                        "name": "Greenfield Global Metals Holdings Ltd.",
                        "country": "HK",
                        "relationship": "OWNED_BY",
                        "confidence": 0.95
                    },
                    {
                        "entity_id": "ENT-GF-CN-001",
                        "name": "Guangdong Greenfield Aluminum Mfg. Co., Ltd.",
                        "country": "CN",
                        "relationship": "PARENT_COMPANY",
                        "confidence": 0.92
                    }
                ]
            },
            "sunpath_us": {
                "entity_id": "ENT-SP-US-001",
                "name": "SunPath Energy Distributors LLC",
                "country": "US",
                "incorporation_date": "2021-03-20",
                "entity_type": "consignee",
                "confidence": 0.99,
                "prior_filings": [
                    {"case_id": "2023-EAPA-001", "determination": "evasion"},
                    {"case_id": "2023-AD-CV-002", "determination": "duty"}
                ]
            },
            "solaria_my": {
                "entity_id": "ENT-SOL-MY-001",
                "name": "Solaria Manufacturing Sdn. Bhd.",
                "country": "MY",
                "incorporation_date": "2026-04-02",
                "entity_type": "shipper",
                "confidence": 0.89,
                "risk_flags": ["NEW_SHIPPER", "TRANSSHIPMENT_CORRIDOR"],
                "related_entities": [
                    {
                        "entity_id": "ENT-SOL-CN-001",
                        "name": "Guangdong Solaria New Energy Technology Co.",
                        "country": "CN",
                        "relationship": "PARENT_COMPANY",
                        "confidence": 0.87
                    }
                ]
            }
        }

    async def resolve_entities(self, manifest_id: str, shipper_name: Optional[str] = None, consignee_name: Optional[str] = None) -> Dict:
        """Resolve shipper/consignee entities and return entity chain.

        Returns entity objects with ownership relationships and confidence scores.
        """
        if API_MODE == "fixture":
            return await self._resolve_entities_fixture(shipper_name, consignee_name)
        else:
            return await self._resolve_entities_live(shipper_name, consignee_name)

    async def _resolve_entities_fixture(self, shipper_name: Optional[str] = None, consignee_name: Optional[str] = None) -> Dict:
        """Fixture implementation for offline demo."""
        entities = []

        # Greenfield case
        if shipper_name and "greenfield" in shipper_name.lower():
            entities.append(self.fixtures["greenfield_vn"])
        if consignee_name and "sunpath" in consignee_name.lower():
            entities.append(self.fixtures["sunpath_us"])

        # Solaria case
        if shipper_name and "solaria" in shipper_name.lower():
            entities.append(self.fixtures["solaria_my"])
        if consignee_name and "sunpath" in consignee_name.lower() and "solaria" in str(shipper_name or "").lower():
            entities.append(self.fixtures["sunpath_us"])

        return {
            "entities": entities,
            "graph_edges": self._build_edges_from_entities(entities),
            "total_confidence": self._avg_confidence(entities),
            "source": "fixture"
        }

    async def _resolve_entities_live(self, shipper_name: Optional[str] = None, consignee_name: Optional[str] = None) -> Dict:
        """Live Senzing API implementation."""
        try:
            async with httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout) as client:
                # Check Senzing health first
                health = await client.get("/heartbeat")
                if health.status_code != 200:
                    logger.warning(f"Senzing service unhealthy: {health.status_code}, falling back to fixtures")
                    return await self._resolve_entities_fixture(shipper_name, consignee_name)

                # Query entity resolution
                entities = []
                if shipper_name:
                    resp = await client.post("/entity-search", json={"name": shipper_name, "role": "shipper"})
                    if resp.status_code == 200:
                        entities.extend(resp.json().get("entities", []))

                if consignee_name:
                    resp = await client.post("/entity-search", json={"name": consignee_name, "role": "consignee"})
                    if resp.status_code == 200:
                        entities.extend(resp.json().get("entities", []))

                return {
                    "entities": entities,
                    "graph_edges": self._build_edges_from_entities(entities),
                    "total_confidence": self._avg_confidence(entities),
                    "source": "senzing"
                }
        except Exception as e:
            logger.warning(f"Senzing connection failed: {e}, falling back to fixtures")
            return await self._resolve_entities_fixture(shipper_name, consignee_name)

    def _build_edges_from_entities(self, entities: List[Dict]) -> List[Dict]:
        """Extract relationship edges from entity data."""
        edges = []
        for entity in entities:
            for related in entity.get("related_entities", []):
                edges.append({
                    "source_id": entity.get("entity_id"),
                    "target_id": related.get("entity_id"),
                    "source_name": entity.get("name"),
                    "target_name": related.get("name"),
                    "relationship": related.get("relationship"),
                    "confidence": related.get("confidence")
                })
        return edges

    def _avg_confidence(self, entities: List[Dict]) -> float:
        """Calculate average confidence across entities."""
        if not entities:
            return 0.0
        confidences = [e.get("confidence", 0.5) for e in entities]
        return sum(confidences) / len(confidences)

    async def get_why_connected(self, entity_id_a: str, entity_id_b: str) -> Dict:
        """Get explanation of why two entities are connected.

        Returns evidence linking the two entities (shared directors, freight forwarder, etc.)
        """
        if API_MODE == "fixture":
            return await self._get_why_connected_fixture(entity_id_a, entity_id_b)
        else:
            return await self._get_why_connected_live(entity_id_a, entity_id_b)

    async def _get_why_connected_fixture(self, entity_id_a: str, entity_id_b: str) -> Dict:
        """Fixture why-explanation for Greenfield case."""
        # Greenfield VN → Greenfield HK → Greenfield CN chain
        if ("GF-VN" in entity_id_a and "GF-HK" in entity_id_b) or ("GF-HK" in entity_id_a and "GF-VN" in entity_id_b):
            return {
                "entity_a": "Greenfield Industrial Trading Co., Ltd.",
                "entity_b": "Greenfield Global Metals Holdings Ltd.",
                "why_key": "OWNERSHIP_CHAIN",
                "explanation": "Greenfield VN is owned by Greenfield HK holding company",
                "evidence": [
                    {
                        "type": "DIRECTOR_SHARED",
                        "details": "Director Li Wei appears in both corporate registries",
                        "confidence": 0.94
                    },
                    {
                        "type": "FREIGHT_FORWARDER_SHARED",
                        "details": "Both entities use Pan-Pacific Logistics, Inc. (freight forwarder ID: FRW-98765)",
                        "confidence": 0.87
                    },
                    {
                        "type": "REGISTERED_AGENT",
                        "details": "Both entities list same registered agent: China Trade Services, Room 1204, Lippo Centre",
                        "confidence": 0.91
                    }
                ],
                "confidence": 0.91,
                "relationship": "OWNED_BY"
            }
        elif ("GF-HK" in entity_id_a and "GF-CN" in entity_id_b) or ("GF-CN" in entity_id_a and "GF-HK" in entity_id_b):
            return {
                "entity_a": "Greenfield Global Metals Holdings Ltd.",
                "entity_b": "Guangdong Greenfield Aluminum Mfg. Co., Ltd.",
                "why_key": "PARENT_SUBSIDIARY",
                "explanation": "Guangdong Greenfield is parent manufacturer of Greenfield HK holding company",
                "evidence": [
                    {
                        "type": "OWNERSHIP_STAKE",
                        "details": "Greenfield HK owns 88% of Guangdong Greenfield per SAMR registry",
                        "confidence": 0.96
                    },
                    {
                        "type": "BOARD_OVERLAP",
                        "details": "Chairman Zhang appears on boards of both entities",
                        "confidence": 0.89
                    },
                    {
                        "type": "FACILITY_LOCATION",
                        "details": "Both entities operate from Guangzhou Industrial Zone, Nansha District",
                        "confidence": 0.93
                    }
                ],
                "confidence": 0.93,
                "relationship": "PARENT_COMPANY"
            }
        else:
            return {
                "entity_a": entity_id_a,
                "entity_b": entity_id_b,
                "why_key": "NOT_CONNECTED",
                "explanation": "No direct connection found between these entities",
                "evidence": [],
                "confidence": 0.0
            }

    async def _get_why_connected_live(self, entity_id_a: str, entity_id_b: str) -> Dict:
        """Live Senzing why-explanation."""
        try:
            async with httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout) as client:
                resp = await client.get(f"/why/{entity_id_a}/{entity_id_b}")
                if resp.status_code == 200:
                    return resp.json()
                else:
                    return await self._get_why_connected_fixture(entity_id_a, entity_id_b)
        except Exception as e:
            logger.warning(f"Senzing why-connection failed: {e}, falling back to fixtures")
            return await self._get_why_connected_fixture(entity_id_a, entity_id_b)

    async def load_entities(self, entities_jsonl_path: str) -> Dict:
        """Load entity records into Senzing.

        Called at startup to populate Senzing with shipment party data.
        """
        if API_MODE == "fixture":
            logger.info("API_MODE=fixture: skipping entity load to Senzing")
            return {"status": "skipped", "mode": "fixture"}

        try:
            async with httpx.AsyncClient(base_url=self.base_url, timeout=30.0) as client:
                # Check if Senzing is available
                health = await client.get("/heartbeat")
                if health.status_code != 200:
                    logger.warning("Senzing service not available, entity load skipped")
                    return {"status": "failed", "reason": "service_unavailable"}

                # Load entities from JSONL file
                with open(entities_jsonl_path) as f:
                    loaded_count = 0
                    for line in f:
                        entity = json.loads(line)
                        resp = await client.post("/entity-add", json=entity)
                        if resp.status_code == 200:
                            loaded_count += 1

                logger.info(f"Loaded {loaded_count} entities into Senzing")
                return {"status": "success", "loaded_count": loaded_count}
        except FileNotFoundError:
            logger.warning(f"Entity file not found: {entities_jsonl_path}")
            return {"status": "failed", "reason": "file_not_found"}
        except Exception as e:
            logger.error(f"Entity load failed: {e}")
            return {"status": "failed", "reason": str(e)}


# Singleton instance
_client = None


def get_senzing_client() -> SenzingClient:
    """Get or create Senzing client singleton."""
    global _client
    if _client is None:
        _client = SenzingClient()
    return _client
