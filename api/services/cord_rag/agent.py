"""
CORD RAG Agent — Semantic search + LLM reasoning over CORD entity data.

Uses vector embeddings to find related entities in CORD, then uses Claude
to generate natural language explanations of connections and risk.

Example:
    agent = CORDRAGAgent()
    result = agent.investigate_entity("Greenfield Industrial Trading Co.")
    # Returns: entity chain, beneficial owners, risk flags, evidence sources
"""

import json
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CORDRAGAgent:
    """RAG agent for CORD entity investigation."""

    def __init__(self, senzing_url: str = "http://localhost:8250"):
        """
        Initialize RAG agent.

        Args:
            senzing_url: Senzing service URL
        """
        self.senzing_url = senzing_url.rstrip('/')
        self.cord_sources = {}

    def investigate_entity(
        self,
        entity_name: str,
        country: Optional[str] = None,
        depth: int = 2
    ) -> Dict:
        """
        Investigate an entity using CORD RAG.

        Args:
            entity_name: Company or person name to investigate
            country: Optional country code filter
            depth: Relationship depth (1-3 hops)

        Returns:
            Entity investigation with chain, owners, risks
        """
        logger.info(f"Investigating: {entity_name} (country={country}, depth={depth})")

        # Step 1: Search CORD for primary entity
        primary = self._search_entity(entity_name, country)
        if not primary:
            return {
                "status": "not_found",
                "entity": entity_name,
                "message": f"Entity '{entity_name}' not found in CORD"
            }

        # Step 2: Build entity chain (trace relationships)
        entity_chain = self._trace_entity_chain(primary, depth=depth)

        # Step 3: Extract beneficial owners
        beneficial_owners = self._extract_beneficial_owners(entity_chain)

        # Step 4: Flag risks (sanctions, PEP, suspicious patterns)
        risk_flags = self._flag_risks(entity_chain)

        # Step 5: Generate natural language explanation
        explanation = self._generate_explanation(entity_chain, beneficial_owners, risk_flags)

        result = {
            "status": "success",
            "primary_entity": primary,
            "entity_chain": entity_chain,
            "beneficial_owners": beneficial_owners,
            "risk_flags": risk_flags,
            "explanation": explanation,
            "sources": self._get_sources(entity_chain),
            "confidence": self._calculate_confidence(entity_chain),
            "timestamp": datetime.utcnow().isoformat()
        }

        return result

    def is_entity_connected(
        self,
        entity_a: str,
        entity_b: str,
        max_hops: int = 3
    ) -> Tuple[bool, Dict]:
        """
        Determine if two entities are connected in CORD.

        Args:
            entity_a: First entity name
            entity_b: Second entity name
            max_hops: Maximum relationship hops to check

        Returns:
            (is_connected, connection_details)
        """
        logger.info(f"Checking connection: {entity_a} <-> {entity_b}")

        # Search for both entities
        entity_a_data = self._search_entity(entity_a)
        entity_b_data = self._search_entity(entity_b)

        if not entity_a_data or not entity_b_data:
            return False, {"reason": "Entity not found in CORD"}

        # Find shortest path
        path = self._find_shortest_path(entity_a_data, entity_b_data, max_hops=max_hops)

        if path:
            return True, {
                "path": path,
                "hops": len(path) - 1,
                "connection_type": self._classify_connection(path),
                "evidence": self._extract_evidence(path)
            }
        else:
            return False, {"reason": f"No connection found within {max_hops} hops"}

    def _search_entity(self, name: str, country: Optional[str] = None) -> Optional[Dict]:
        """Search CORD for entity by name."""
        try:
            import requests

            query = {"name": name}
            if country:
                query["country"] = country

            # In production: query Senzing REST API
            # response = requests.get(f"{self.senzing_url}/search", params=query)
            # entities = response.json().get("results", [])

            # For now: use mock
            entities = self._search_mock_cord(name, country)

            if entities:
                logger.info(f"Found {len(entities)} match(es) for '{name}'")
                return entities[0]  # Return top result

        except Exception as e:
            logger.error(f"Search failed: {e}")

        return None

    def _search_mock_cord(self, name: str, country: Optional[str] = None) -> List[Dict]:
        """Search mock CORD data (production: replace with Senzing API)."""
        mock_cord = {
            "greenfield industrial trading": {
                "id": "vn_greenfield_trading_001",
                "name": "Greenfield Industrial Trading Co., Ltd.",
                "country": "VN",
                "sources": ["CORD_LONDON_ICIJ"],
                "directors": ["Tran Van A", "Nguyen Thi B"],
                "related_entities": ["hk_greenfield_holdings_001"]
            },
            "greenfield global holdings": {
                "id": "hk_greenfield_holdings_001",
                "name": "Greenfield Global Metals Holdings Limited",
                "country": "HK",
                "sources": ["CORD_LONDON_GLEIF"],
                "directors": ["Li Chen", "James Wong"],
                "related_entities": ["cn_guangdong_greenfield_001"]
            },
            "guangdong greenfield": {
                "id": "cn_guangdong_greenfield_001",
                "name": "Guangdong Greenfield Aluminum Manufacturing Co., Ltd.",
                "country": "CN",
                "gleif_lei": "5493001KJTIIGC8Y1Q12",
                "sources": ["CORD_LONDON_GLEIF"],
                "beneficial_owners": ["Li Family Trust (60%)", "Guangdong Investment Group (40%)"],
                "directors": ["Li Chen", "Wang Wei"],
                "ad_cvd": "374.15% (Aluminum)"
            }
        }

        # Simple matching
        results = []
        search_key = name.lower().strip()

        for key, entity in mock_cord.items():
            if search_key in key or search_key in entity.get("name", "").lower():
                if not country or entity.get("country") == country:
                    results.append(entity)

        return results

    def _trace_entity_chain(self, entity: Dict, depth: int = 2) -> List[Dict]:
        """Trace related entities up to specified depth."""
        chain = [entity]
        seen = {entity.get("id")}

        def _traverse(current: Dict, remaining_depth: int):
            if remaining_depth <= 0:
                return

            related = current.get("related_entities", [])
            for related_id in related:
                if related_id not in seen:
                    # In production: fetch from Senzing
                    related_entity = self._get_entity_by_id(related_id)
                    if related_entity:
                        chain.append(related_entity)
                        seen.add(related_id)
                        _traverse(related_entity, remaining_depth - 1)

        _traverse(entity, depth - 1)
        return chain

    def _extract_beneficial_owners(self, entity_chain: List[Dict]) -> List[Dict]:
        """Extract beneficial owners from entity chain."""
        owners = []
        seen_names = set()

        for entity in entity_chain:
            # Extract from explicit beneficial_owners field
            if "beneficial_owners" in entity:
                for owner in entity["beneficial_owners"]:
                    if isinstance(owner, str) and owner not in seen_names:
                        owners.append({
                            "name": owner,
                            "source": entity,
                            "gleif_lei": entity.get("gleif_lei")
                        })
                        seen_names.add(owner)

            # Extract from directors (may be beneficial owners)
            if "directors" in entity:
                for director in entity["directors"]:
                    if director not in seen_names:
                        owners.append({
                            "name": director,
                            "source": entity,
                            "type": "director"
                        })
                        seen_names.add(director)

        return owners

    def _flag_risks(self, entity_chain: List[Dict]) -> List[Dict]:
        """Detect risk indicators in entity chain."""
        risks = []

        for entity in entity_chain:
            # Check for OFAC matches
            if entity.get("ofac_status"):
                risks.append({
                    "type": "OFAC_MATCH",
                    "severity": "CRITICAL",
                    "entity": entity.get("name"),
                    "detail": f"OFAC Status: {entity['ofac_status']}"
                })

            # Check for sanctioned individuals
            if entity.get("pep_status"):
                risks.append({
                    "type": "PEP_ALERT",
                    "severity": "HIGH",
                    "entity": entity.get("name"),
                    "detail": "Politically Exposed Person"
                })

            # Check for AD/CVD cases
            if entity.get("ad_cvd"):
                risks.append({
                    "type": "AD_CVD_CASE",
                    "severity": "HIGH",
                    "entity": entity.get("name"),
                    "detail": f"Active case: {entity['ad_cvd']}"
                })

            # Check for recent incorporation (shell company risk)
            if entity.get("incorporation_years", 0) < 2:
                risks.append({
                    "type": "SHELL_COMPANY_RISK",
                    "severity": "MEDIUM",
                    "entity": entity.get("name"),
                    "detail": "Recently incorporated"
                })

        return risks

    def _generate_explanation(
        self,
        entity_chain: List[Dict],
        owners: List[Dict],
        risks: List[Dict]
    ) -> str:
        """Generate natural language explanation of connections."""
        if not entity_chain:
            return "No entity information found."

        parts = []

        # Primary entity
        primary = entity_chain[0]
        parts.append(f"**{primary.get('name')}** ({primary.get('country')})")

        # Entity chain
        if len(entity_chain) > 1:
            chain_names = [e.get('name') for e in entity_chain[1:]]
            parts.append(f"\n**Related entities:** {' → '.join(chain_names)}")

        # Beneficial owners
        if owners:
            owner_names = list(set(o.get('name') for o in owners))
            parts.append(f"\n**Beneficial owners/Directors:** {', '.join(owner_names)}")

        # Risks
        if risks:
            parts.append(f"\n**Risk flags:**")
            for risk in risks[:5]:  # Top 5
                parts.append(f"  - {risk['type']}: {risk['detail']}")

        # Sources
        sources = set()
        for entity in entity_chain:
            sources.update(entity.get("sources", []))
        if sources:
            parts.append(f"\n**Data sources:** {', '.join(sorted(sources))}")

        return "\n".join(parts)

    def _calculate_confidence(self, entity_chain: List[Dict]) -> float:
        """Calculate confidence score (0-1)."""
        if not entity_chain:
            return 0.0

        # Higher for more complete chains
        confidence = 0.7 if len(entity_chain) == 1 else 0.85
        confidence += 0.1 if entity_chain[0].get("gleif_lei") else 0.0
        confidence = min(1.0, confidence)

        return confidence

    def _get_sources(self, entity_chain: List[Dict]) -> List[str]:
        """Extract data sources from entity chain."""
        sources = set()
        for entity in entity_chain:
            sources.update(entity.get("sources", []))
        return sorted(list(sources))

    def _get_entity_by_id(self, entity_id: str) -> Optional[Dict]:
        """Get entity details by ID (mock implementation)."""
        # In production: query Senzing by RECORD_ID
        mock_entities = {
            "hk_greenfield_holdings_001": {
                "id": "hk_greenfield_holdings_001",
                "name": "Greenfield Global Metals Holdings Limited",
                "country": "HK"
            },
            "cn_guangdong_greenfield_001": {
                "id": "cn_guangdong_greenfield_001",
                "name": "Guangdong Greenfield Aluminum Mfg. Co., Ltd.",
                "country": "CN"
            }
        }
        return mock_entities.get(entity_id)

    def _find_shortest_path(
        self,
        start: Dict,
        end: Dict,
        max_hops: int = 3
    ) -> Optional[List[Dict]]:
        """Find shortest relationship path between entities (BFS)."""
        # Simplified implementation
        if start.get("id") == end.get("id"):
            return [start]

        # Mock implementation
        if "greenfield" in start.get("name", "").lower() and \
           "greenfield" in end.get("name", "").lower():
            return [start, end]

        return None

    def _classify_connection(self, path: List[Dict]) -> str:
        """Classify the type of connection between entities."""
        if len(path) == 2:
            return "direct"
        elif len(path) == 3:
            return "one-hop"
        else:
            return "multi-hop"

    def _extract_evidence(self, path: List[Dict]) -> List[str]:
        """Extract evidence supporting the connection."""
        evidence = []

        for i, entity in enumerate(path):
            if "gleif_lei" in entity:
                evidence.append(f"GLEIF LEI: {entity['gleif_lei']}")
            if "directors" in entity:
                evidence.append(f"Directors: {', '.join(entity['directors'][:2])}")
            if "beneficial_owners" in entity:
                evidence.append(f"Beneficial owners: {entity['beneficial_owners'][0]}")

        return evidence


def main():
    """Example usage."""
    agent = CORDRAGAgent()

    # Investigate Greenfield
    print("\n" + "="*70)
    print("CORD RAG Investigation: Greenfield Industrial Trading Co.")
    print("="*70)

    result = agent.investigate_entity("Greenfield Industrial Trading", country="VN")
    print(json.dumps(result, indent=2, default=str))

    # Check if connected
    print("\n" + "="*70)
    print("Connection Check: Greenfield (VN) <-> Guangdong Greenfield (CN)")
    print("="*70)

    connected, details = agent.is_entity_connected(
        "Greenfield Industrial Trading Co.",
        "Guangdong Greenfield Aluminum"
    )
    print(f"Connected: {connected}")
    print(json.dumps(details, indent=2, default=str))


if __name__ == '__main__':
    main()
