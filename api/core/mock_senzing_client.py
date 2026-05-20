"""Mock Senzing client for when license unavailable — returns pre-baked fixture responses"""

import logging
from typing import Dict, Any, List
import json

logger = logging.getLogger(__name__)


class MockSenzingClient:
    """Returns fixture responses matching real Senzing API contract"""

    def __init__(self):
        self.entities = self._load_fixture_entities()
        self.logger = logger

    def _load_fixture_entities(self) -> Dict[int, Dict[str, Any]]:
        """Load and map fixture entities to entity IDs"""
        return {
            1: {
                "entity_id": 1,
                "entity_name": "Greenfield Industrial Trading Co., Ltd.",
                "entity_type": "SHIPPER",
                "country": "VN",
                "jurisdiction": "Vietnam",
                "senzing_confidence": 0.95,
                "risk_level": "HIGH",
                "director_name": "Tran Van Minh",
                "freight_forwarder_id": "FF_GF_001",
                "prior_cbp_filings": 3,
                "matching_evidence": ["NAME_MATCH", "DIRECTOR_MATCH", "FREIGHT_FORWARDER_MATCH"]
            },
            2: {
                "entity_id": 2,
                "entity_name": "Guangdong Greenfield Aluminum Mfg. Co., Ltd.",
                "entity_type": "MANUFACTURER",
                "country": "CN",
                "jurisdiction": "China",
                "senzing_confidence": 0.98,
                "risk_level": "CRITICAL",
                "director_name": "Tran Van Minh",
                "freight_forwarder_id": "FF_GF_001",
                "prior_cbp_filings": 12,
                "matching_evidence": ["DIRECTOR_MATCH", "FREIGHT_FORWARDER_MATCH", "BUSINESS_REG_MATCH"]
            },
            3: {
                "entity_id": 3,
                "entity_name": "Greenfield Global Metals Holdings Ltd.",
                "entity_type": "HOLDING_COMPANY",
                "country": "HK",
                "jurisdiction": "Hong Kong",
                "senzing_confidence": 0.91,
                "risk_level": "HIGH",
                "freight_forwarder_id": "FF_GF_001",
                "prior_cbp_filings": 2,
                "matching_evidence": ["FREIGHT_FORWARDER_MATCH", "REGISTERED_AGENT_MATCH"]
            },
            4: {
                "entity_id": 4,
                "entity_name": "SunPath Energy Distributors LLC",
                "entity_type": "CONSIGNEE",
                "country": "US",
                "jurisdiction": "New Jersey",
                "senzing_confidence": 0.88,
                "risk_level": "MEDIUM",
                "prior_cbp_filings": 7,
                "matching_evidence": ["ADDRESS_MATCH", "PHONE_MATCH"]
            },
            5: {
                "entity_id": 5,
                "entity_name": "MV Pacific Horizon",
                "entity_type": "VESSEL",
                "country": "SG",
                "jurisdiction": "Singapore",
                "senzing_confidence": 1.0,
                "risk_level": "LOW",
                "imo": "9432110",
                "prior_cbp_filings": 8,
                "matching_evidence": ["IMO_MATCH"]
            },
            6: {
                "entity_id": 6,
                "entity_name": "Global Cargo Logistics (Guangzhou) Co., Ltd.",
                "entity_type": "FREIGHT_FORWARDER",
                "country": "CN",
                "jurisdiction": "China",
                "senzing_confidence": 0.92,
                "risk_level": "MEDIUM",
                "freight_forwarder_id": "FF_GF_001",
                "prior_cbp_filings": 4,
                "matching_evidence": ["FREIGHT_FORWARDER_ID_MATCH"]
            },
            7: {
                "entity_id": 7,
                "entity_name": "Established Vietnam Aluminum Co.",
                "entity_type": "SHIPPER",
                "country": "VN",
                "jurisdiction": "Vietnam",
                "senzing_confidence": 0.85,
                "risk_level": "LOW",
                "director_name": "Nguyen Hoang Anh",
                "prior_cbp_filings": 1,
                "matching_evidence": ["NAME_MATCH"]
            },
        }

    async def health(self) -> bool:
        """Mock is always healthy"""
        return True

    async def add_record(
        self,
        data_source: str,
        record_id: str,
        record: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Mock add_record — logs and returns success"""
        logger.info(f"[MOCK] Added record {record_id} from {data_source}")
        return {"status": "MOCK", "record_id": record_id}

    async def search_by_attributes(self, attributes: Dict[str, str]) -> Dict[str, Any]:
        """Mock search — returns fixture entity if name matches"""
        query_name = attributes.get("NAME", "").upper()

        for entity in self.entities.values():
            if query_name in entity["entity_name"].upper():
                return {
                    "status": "MOCK",
                    "entities": [entity]
                }

        return {"status": "MOCK", "entities": []}

    async def get_entity(self, entity_id: int) -> Dict[str, Any]:
        """Mock get_entity — returns fixture entity"""
        if entity_id in self.entities:
            return {"status": "MOCK", "entity": self.entities[entity_id]}

        return {"status": "MOCK", "entity": None}

    async def why_entities(self, entity_id_a: int, entity_id_b: int) -> Dict[str, Any]:
        """Mock why_entities — returns pre-baked connection explanations"""

        # Greenfield VN → CN (primary demo case)
        if (entity_id_a, entity_id_b) == (1, 2) or (entity_id_a, entity_id_b) == (2, 1):
            return {
                "status": "MOCK",
                "why_result": {
                    "why_type": "RELATIONSHIPS",
                    "entity_paths": [
                        {
                            "start_entity_id": 1,
                            "end_entity_id": 2,
                            "path_length": 1,
                            "matching_criteria": [
                                {"criterion": "DIRECTOR_NAME", "value": "Tran Van Minh"},
                                {"criterion": "FREIGHT_FORWARDER_ID", "value": "FF_GF_001"},
                            ]
                        }
                    ]
                }
            }

        # Greenfield CN → HK
        if (entity_id_a, entity_id_b) == (2, 3) or (entity_id_a, entity_id_b) == (3, 2):
            return {
                "status": "MOCK",
                "why_result": {
                    "why_type": "RELATIONSHIPS",
                    "entity_paths": [
                        {
                            "start_entity_id": 2,
                            "end_entity_id": 3,
                            "path_length": 1,
                            "matching_criteria": [
                                {"criterion": "FREIGHT_FORWARDER_ID", "value": "FF_GF_001"},
                                {"criterion": "COMPANY_NAME_ROOT", "value": "GREENFIELD"},
                            ]
                        }
                    ]
                }
            }

        # HK → US (Greenfield consignee)
        if (entity_id_a, entity_id_b) == (3, 4) or (entity_id_a, entity_id_b) == (4, 3):
            return {
                "status": "MOCK",
                "why_result": {
                    "why_type": "RELATIONSHIPS",
                    "entity_paths": [
                        {
                            "start_entity_id": 3,
                            "end_entity_id": 4,
                            "path_length": 2,
                            "matching_criteria": [
                                {"criterion": "SHARED_CONSIGNEE", "value": "SunPath Energy Distributors LLC"},
                            ]
                        }
                    ]
                }
            }

        # Default: no direct relationship
        return {
            "status": "MOCK",
            "why_result": {
                "why_type": "NO_MATCH",
                "entity_paths": []
            }
        }

    async def close(self):
        """No-op for mock client"""
        pass
