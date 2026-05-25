"""Transform CORD entity resolution to Entity[] format for frontend visualization.

Converts CORD /resolve endpoint response (3-level ownership chain from Senzing)
into the Entity interface format expected by EntityRelationshipGraph and
InteractiveEntityGraph (React Flow) components.

Used by: /api/referral/{shipment_id}/entity-graph endpoint
"""

from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


class EntityGraphService:
    """Transform CORD resolution data to Entity[] format for visualization."""

    ENTITY_TYPE_MAP = {
        "level_1": "SHIPPER",
        "level_2": "INTERMEDIARY",
        "level_3": "MANUFACTURER",
    }

    ROLE_MAP = {
        "level_1": "Shipper",
        "level_2": "Parent Company",
        "level_3": "Manufacturer",
    }

    @staticmethod
    def transform_cord_to_entity_chain(
        cord_response: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Transform CORD 3-level resolution to Entity[] format.

        Input (from CORD /resolve):
        {
            "level_1": {
                "entity_id": "ENT-GF-VN-001",
                "name": "Greenfield Industrial Trading Co., Ltd.",
                "country": "VN",
                "confidence": 0.98,
                "data_source": "CORD",
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
            "risk_score": 72
        }

        Output (for frontend Entity interface):
        {
            "chain": [
                {
                    "entity_id": "ENT-GF-VN-001",
                    "name": "Greenfield Industrial Trading Co., Ltd.",
                    "country": "VN",
                    "entity_type": "SHIPPER",
                    "role": "Shipper",
                    "data_source": "CORD",
                    "confidence": 0.98,
                    "relationships": [
                        {
                            "type": "OWNED_BY",
                            "target": "Greenfield Global Metals Holdings Ltd.",
                            "confidence": 0.95
                        }
                    ]
                },
                { ... Level 2 ... },
                { ... Level 3 ... }
            ],
            "data_sources": ["CORD", "Senzing", "OFAC"],
            "ofac_detected": false,
            "risk_score": 72,
            "confidence_metrics": { ... }
        }

        Args:
            cord_response: Response from CORD /resolve endpoint

        Returns:
            Dict with "chain" (Entity[]) and metadata for frontend
        """
        if not cord_response:
            logger.warning("CORD response is null, returning empty chain")
            return {"chain": [], "data_sources": []}

        chain: List[Dict[str, Any]] = []
        data_sources: set = set()

        for level_key in ["level_1", "level_2", "level_3"]:
            entity_data = cord_response.get(level_key)
            if not entity_data:
                continue

            # Extract relationships from entity_data
            relationships = []
            related_entities = entity_data.get("related_entities", [])
            for related in related_entities:
                relationships.append({
                    "type": related.get("relationship", "UNKNOWN"),
                    "target": related.get("name", ""),
                    "confidence": related.get("confidence", 0),
                })

            # Extract data source
            data_source = entity_data.get("data_source", "CORD")
            data_sources.add(data_source)

            # Build Entity object
            entity: Dict[str, Any] = {
                "entity_id": entity_data.get("entity_id", f"ENT-{level_key}"),
                "name": entity_data.get("name", ""),
                "country": entity_data.get("country", ""),
                "entity_type": EntityGraphService.ENTITY_TYPE_MAP.get(
                    level_key, "UNKNOWN"
                ),
                "role": EntityGraphService.ROLE_MAP.get(level_key, "Entity"),
                "data_source": data_source,
                "confidence": entity_data.get("confidence", 0),
                "relationships": relationships,
            }

            # Add optional fields if present
            if "risk_score" in entity_data:
                entity["risk_score"] = entity_data["risk_score"]
            if "risk_flags" in entity_data:
                entity["risk_flags"] = entity_data["risk_flags"]

            chain.append(entity)

            logger.info(
                f"Transformed {level_key}: {entity['name']} ({entity['entity_type']})"
            )

        # Build result with metadata
        result = {
            "chain": chain,
            "data_sources": sorted(list(data_sources)) or ["CORD"],
            "ofac_detected": cord_response.get("ofac_detected", False),
            "risk_score": cord_response.get("risk_score", 0),
            "confidence_metrics": cord_response.get("confidence_metrics", {}),
        }

        logger.info(f"✅ Transformed entity chain with {len(chain)} levels")

        return result

    @staticmethod
    def add_isf_warnings(
        entity_graph: Dict[str, Any],
        isf_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Add ISF Element 9 mismatch warnings to shipper node.

        Args:
            entity_graph: Result from transform_cord_to_entity_chain()
            isf_data: ISFData from ISFEnrichmentService.enrich_manifest()

        Returns:
            entity_graph with ISF warnings merged into shipper node
        """
        if not entity_graph.get("chain"):
            return entity_graph

        # Add warnings to first node (shipper)
        shipper_node = entity_graph["chain"][0]

        warnings: List[Dict[str, Any]] = shipper_node.get("warnings", [])

        # Check for Element 9 mismatch
        if isf_data.get("element_9", {}).get("is_mismatch"):
            element_9 = isf_data["element_9"]
            warnings.append({
                "type": "ISF_ELEMENT_9_MISMATCH",
                "severity": "HIGH",
                "message": f"Declared COO: {element_9.get('declared_country', 'N/A')} | "
                f"Actual stuffing: {element_9.get('actual_stuffing_country', 'N/A')}",
                "confidence": element_9.get("mismatch_confidence", 0),
            })
            logger.warning(
                f"ISF Element 9 mismatch detected for {shipper_node['name']}"
            )

        # Check for dwell anomaly
        if isf_data.get("dwell_anomaly"):
            dwell_data = isf_data.get("dwell_anomaly", {})
            warnings.append({
                "type": "DWELL_ANOMALY",
                "severity": "MEDIUM",
                "message": f"Dwell: {dwell_data.get('dwell_days', 0):.1f}d "
                f"vs baseline {dwell_data.get('baseline_days', 0):.1f}d "
                f"({dwell_data.get('anomaly_ratio', 1):.1f}x multiplier)",
            })

        # Check for new shipper flag
        if isf_data.get("new_shipper"):
            warnings.append({
                "type": "NEW_SHIPPER",
                "severity": "MEDIUM",
                "message": f"Shipper age: {isf_data.get('shipper_age_months', 0)} months (< 24mo)",
            })

        if warnings:
            shipper_node["warnings"] = warnings
            logger.info(f"Added {len(warnings)} ISF warnings to shipper node")

        return entity_graph
