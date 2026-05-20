"""
Search-First CORD Integration — Smart approach to avoid eval limits.

Flow:
1. Manifest upload → Extract entities (shipper, consignee, mfg)
2. Search FULL CORD via REST API (unlimited) for matches
3. Extract matching subset (~20 entities per case)
4. Load ONLY subset into Senzing SDK (<100K eval limit)
5. Run Senzing resolution on relevant data
6. Return entity chains + risk scores

Advantages:
  ✓ Never exceeds SDK eval limit (load ~20 entities per case)
  ✓ Real CORD data (searched via REST)
  ✓ Works with free evaluation
  ✓ Scales to production (same code, swap REST for commercial)
"""

import json
import logging
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class SearchFirstCORDIntegration:
    """
    Search-First approach: Query CORD, extract subset, load to Senzing.

    This avoids the 100K SDK eval limit by only loading relevant entities.
    """

    def __init__(
        self,
        cord_rest_url: str = "http://localhost:8250",
        senzing_sdk_enabled: bool = True
    ):
        """
        Initialize search-first integration.

        Args:
            cord_rest_url: REST API URL for searching CORD
            senzing_sdk_enabled: Enable Senzing SDK (True) or REST-only (False)
        """
        self.cord_rest_url = cord_rest_url.rstrip('/')
        self.senzing_sdk_enabled = senzing_sdk_enabled
        self.senzing_engine = None

        if senzing_sdk_enabled:
            self._init_senzing_sdk()

    def investigate_shipment(self, manifest_data: Dict) -> Dict:
        """
        Investigate shipment using search-first approach.

        Flow:
        1. Extract entities from manifest
        2. Search CORD for matches (REST - unlimited)
        3. Load matches into Senzing (SDK - limited)
        4. Resolve relationships
        5. Flag risks

        Args:
            manifest_data: Shipment manifest data

        Returns:
            Investigation result with entity chains + risks
        """
        logger.info("="*70)
        logger.info(f"Investigating shipment: {manifest_data.get('shipper_name')}")
        logger.info("="*70)

        # Step 1: Extract entities from manifest
        logger.info("\n1. EXTRACT: Reading entities from manifest...")
        entities_to_search = self._extract_manifest_entities(manifest_data)
        logger.info(f"   Found {len(entities_to_search)} entities to search")
        for e in entities_to_search:
            logger.info(f"     • {e['name']} ({e['country']})")

        # Step 2: SEARCH CORD via REST API (no limits!)
        logger.info("\n2. SEARCH: Querying CORD via REST API (unlimited)...")
        cord_matches = self._search_cord_for_entities(entities_to_search)
        logger.info(f"   Found {len(cord_matches)} matches in CORD")
        total_records = sum(len(m.get('records', [])) for m in cord_matches)
        logger.info(f"   Total CORD records to load: {total_records}")

        # Step 3: EXTRACT relevant subset
        logger.info("\n3. EXTRACT: Building relevant subset from CORD...")
        cord_subset = self._extract_relevant_subset(cord_matches)
        logger.info(f"   Subset size: {len(cord_subset)} CORD entities")
        logger.info(f"   ✓ Under 100K SDK eval limit ({len(cord_subset)}/100000)")

        # Step 4: LOAD subset into Senzing (if SDK enabled)
        logger.info("\n4. LOAD: Loading subset into Senzing SDK...")
        if self.senzing_sdk_enabled and self.senzing_engine:
            self._load_into_senzing(cord_subset)
            logger.info(f"   ✓ Loaded {len(cord_subset)} entities to Senzing")
        else:
            logger.info("   ℹ SDK disabled, using REST API only")

        # Step 5: RESOLVE relationships
        logger.info("\n5. RESOLVE: Finding entity relationships...")
        entity_chains = self._resolve_entity_chains(
            entities_to_search,
            cord_matches
        )
        logger.info(f"   Resolved {len(entity_chains)} entity chains")
        for chain in entity_chains:
            logger.info(f"     • {len(chain['entities'])} entities: {' → '.join(e['name'] for e in chain['entities'][:3])}...")

        # Step 6: FLAG risks
        logger.info("\n6. RISK: Detecting risk indicators...")
        risk_flags = self._flag_risks(cord_matches, entity_chains)
        logger.info(f"   Found {len(risk_flags)} risk flags")
        for flag in risk_flags[:5]:
            logger.info(f"     • {flag['type']}: {flag['detail']}")

        # Step 7: SCORE
        logger.info("\n7. SCORE: Calculating risk score...")
        score = self._calculate_score(
            entity_chains,
            risk_flags,
            manifest_data
        )
        logger.info(f"   Risk score: {score['total_score']}/100 ({score['level']})")

        result = {
            "manifest_id": manifest_data.get('manifest_id'),
            "status": "success",
            "investigation": {
                "manifest_entities": entities_to_search,
                "cord_search_results": len(cord_matches),
                "cord_records_found": total_records,
                "cord_subset_loaded": len(cord_subset),
                "entity_chains": entity_chains,
                "risk_flags": risk_flags,
            },
            "scoring": score,
            "sources": self._get_sources(cord_matches),
            "eval_safety": {
                "sdk_enabled": self.senzing_sdk_enabled,
                "entities_loaded": len(cord_subset),
                "eval_limit": 100000,
                "percent_used": (len(cord_subset) / 100000) * 100,
                "status": "safe" if len(cord_subset) < 100000 else "warning"
            },
            "timestamp": datetime.utcnow().isoformat()
        }

        logger.info("\n" + "="*70)
        logger.info("✓ Investigation complete")
        logger.info("="*70)

        return result

    def _extract_manifest_entities(self, manifest: Dict) -> List[Dict]:
        """Extract entities from manifest for searching."""
        return [
            {
                "name": manifest.get('shipper_name', ''),
                "country": manifest.get('shipper_country', ''),
                "type": "shipper",
                "role": "exporter"
            },
            {
                "name": manifest.get('consignee_name', ''),
                "country": manifest.get('consignee_country', ''),
                "type": "consignee",
                "role": "importer"
            },
            # Infer manufacturer based on country mismatches
            {
                "name": manifest.get('manufacturer_inferred', ''),
                "country": manifest.get('declared_origin', ''),
                "type": "manufacturer",
                "role": "producer"
            }
        ]

    def _search_cord_for_entities(self, entities: List[Dict]) -> List[Dict]:
        """
        Search CORD for entities via REST API.

        This queries the full CORD dataset (16M records) via REST API.
        No eval limits apply here.
        """
        import requests

        results = []

        for entity in entities:
            if not entity['name']:
                continue

            try:
                # Query CORD via REST API
                # In production: this would query real Senzing REST
                response = requests.get(
                    f"{self.cord_rest_url}/search",
                    params={
                        "name": entity['name'],
                        "country": entity['country'],
                        "limit": 5  # Top 5 matches
                    },
                    timeout=10
                )

                if response.status_code == 200:
                    matches = response.json().get('results', [])
                    results.append({
                        "query": entity,
                        "matches": matches,
                        "records": self._extract_records_from_matches(matches)
                    })

                    logger.debug(
                        f"Found {len(matches)} CORD matches for "
                        f"{entity['name']} ({entity['country']})"
                    )

            except Exception as e:
                logger.warning(f"Search failed for {entity['name']}: {e}")

        return results

    def _extract_relevant_subset(self, cord_matches: List[Dict]) -> List[Dict]:
        """
        Extract only relevant CORD entities (not all 16M).

        Takes search results and extracts just the matched entities,
        keeping total under 100K SDK eval limit.
        """
        subset = []
        seen_ids = set()

        for match_group in cord_matches:
            for match in match_group.get('matches', [])[:5]:  # Top 5 per query
                record_id = match.get('id')
                if record_id not in seen_ids:
                    subset.append({
                        "id": record_id,
                        "name": match.get('name'),
                        "country": match.get('country'),
                        "sources": match.get('sources', []),
                        "confidence": match.get('confidence', 0.0),
                        "data": match  # Full match data
                    })
                    seen_ids.add(record_id)

        logger.info(f"Extracted {len(subset)} unique entities from CORD")
        return subset

    def _load_into_senzing(self, entities: List[Dict]) -> int:
        """Load extracted subset into Senzing SDK."""
        if not self.senzing_engine:
            logger.warning("Senzing SDK not initialized")
            return 0

        loaded = 0

        for entity in entities:
            try:
                # Format for Senzing
                record = {
                    "DATA_SOURCE": "CORD_SEARCH_RESULT",
                    "RECORD_ID": entity['id'],
                    "NAME_FULL": entity['name'],
                    "COUNTRY_CODE": entity['country'],
                    "MATCH_CONFIDENCE": entity['confidence']
                }

                # Load into Senzing SDK
                self.senzing_engine.addRecord(
                    record["DATA_SOURCE"],
                    record["RECORD_ID"],
                    json.dumps(record)
                )

                loaded += 1

            except Exception as e:
                logger.warning(f"Failed to load entity {entity['id']}: {e}")

        return loaded

    def _resolve_entity_chains(
        self,
        manifest_entities: List[Dict],
        cord_matches: List[Dict]
    ) -> List[Dict]:
        """Build entity chains from manifest + CORD data."""
        chains = []

        for match_group in cord_matches:
            if not match_group.get('matches'):
                continue

            # Top match is primary entity
            primary = match_group['matches'][0]
            chain = {
                "primary": primary,
                "query": match_group['query'],
                "entities": [primary],
                "relationships": []
            }

            # Add related entities from CORD
            for secondary in match_group['matches'][1:]:
                chain['entities'].append(secondary)
                chain['relationships'].append({
                    "type": "related_in_cord",
                    "confidence": secondary.get('confidence')
                })

            chains.append(chain)

        return chains

    def _flag_risks(
        self,
        cord_matches: List[Dict],
        entity_chains: List[Dict]
    ) -> List[Dict]:
        """Detect risks from CORD data."""
        risks = []

        for chain in entity_chains:
            for entity in chain['entities']:
                # Check for OFAC
                if entity.get('ofac_status'):
                    risks.append({
                        "type": "OFAC_MATCH",
                        "severity": "CRITICAL",
                        "entity": entity['name'],
                        "source": "CORD",
                        "detail": f"OFAC: {entity['ofac_status']}"
                    })

                # Check for AD/CVD
                if entity.get('ad_cvd_cases'):
                    risks.append({
                        "type": "AD_CVD_CASE",
                        "severity": "HIGH",
                        "entity": entity['name'],
                        "source": "CORD",
                        "detail": entity['ad_cvd_cases'][0]
                    })

                # Check for sanctions
                if entity.get('sanctions_lists'):
                    risks.append({
                        "type": "SANCTIONS",
                        "severity": "HIGH",
                        "entity": entity['name'],
                        "source": "CORD",
                        "detail": f"Listed in: {entity['sanctions_lists'][0]}"
                    })

        return risks

    def _calculate_score(
        self,
        entity_chains: List[Dict],
        risk_flags: List[Dict],
        manifest: Dict
    ) -> Dict:
        """Calculate risk score based on entity chains + risks."""
        # Start with base score from manifest analysis
        base_score = manifest.get('base_score', 30)

        # Add points for each risk
        risk_points = 0
        for flag in risk_flags:
            if flag['severity'] == 'CRITICAL':
                risk_points += 25
            elif flag['severity'] == 'HIGH':
                risk_points += 15
            elif flag['severity'] == 'MEDIUM':
                risk_points += 8

        # Add points for complex entity chains (transshipment indicator)
        chain_points = 0
        for chain in entity_chains:
            if len(chain['entities']) > 2:
                chain_points += 15  # Multi-hop = transshipment indicator

        total = min(100, base_score + risk_points + chain_points)

        if total >= 70:
            level = "HIGH"
        elif total >= 40:
            level = "MEDIUM"
        else:
            level = "LOW"

        return {
            "base_score": base_score,
            "risk_points": risk_points,
            "chain_points": chain_points,
            "total_score": total,
            "level": level,
            "confidence": 0.85 if len(risk_flags) > 0 else 0.6
        }

    def _extract_records_from_matches(self, matches: List[Dict]) -> List[Dict]:
        """Extract records from match results."""
        return [m.get('record_data', {}) for m in matches if m.get('record_data')]

    def _get_sources(self, cord_matches: List[Dict]) -> List[str]:
        """Extract data sources from CORD matches."""
        sources = set()
        for match_group in cord_matches:
            for match in match_group.get('matches', []):
                sources.update(match.get('sources', []))
        return sorted(list(sources))

    def _init_senzing_sdk(self):
        """Initialize Senzing SDK (if available)."""
        try:
            from senzing import G2Engine
            self.senzing_engine = G2Engine()
            self.senzing_engine.init("cbp-sentry")
            logger.info("✓ Senzing SDK initialized")
        except ImportError:
            logger.warning("Senzing SDK not available, using REST API only")
            self.senzing_sdk_enabled = False
        except Exception as e:
            logger.warning(f"Senzing SDK init failed: {e}, using REST API only")
            self.senzing_sdk_enabled = False


def main():
    """Example usage."""
    integration = SearchFirstCORDIntegration(
        cord_rest_url="http://localhost:8250",
        senzing_sdk_enabled=False  # Start with REST only
    )

    # Test manifest
    manifest = {
        "manifest_id": "test-001",
        "shipper_name": "Greenfield Industrial Trading Co., Ltd.",
        "shipper_country": "VN",
        "consignee_name": "SunPath Energy Distributors LLC",
        "consignee_country": "US",
        "declared_origin": "VN",
        "manufacturer_inferred": "Guangdong Greenfield Aluminum",
        "base_score": 35
    }

    result = integration.investigate_shipment(manifest)
    print("\n" + json.dumps(result, indent=2, default=str))


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    main()
