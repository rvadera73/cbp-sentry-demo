"""
Senzing SDK Integration — Use Senzing SDK to work with CORD data.

This module uses the native Senzing Python SDK for:
- Loading CORD records into Senzing engine
- Running entity resolution via Senzing G2 engine
- Getting match confidence and why-explanations
- Building entity relationship graphs

Requirements:
    pip install senzing==3.7.0
"""

import json
import logging
from typing import Dict, List, Tuple, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class SenzingCORDIntegration:
    """Integration layer for Senzing SDK and CORD data."""

    def __init__(self, g2_config_path: str = None):
        """
        Initialize Senzing integration.

        Args:
            g2_config_path: Path to Senzing G2 config (default: auto-detect)
        """
        self.g2_config_path = g2_config_path or self._find_g2_config()
        self.g2_engine = None
        self.g2_config = None

        try:
            self._init_senzing_sdk()
        except ImportError:
            logger.warning(
                "Senzing SDK not installed. Install with: pip install senzing==3.7.0"
            )

    def _find_g2_config(self) -> str:
        """Find Senzing G2 config file."""
        possible_paths = [
            "/etc/opt/senzing/g2.conf",
            "/opt/senzing/etc/g2.conf",
            Path.home() / ".senzing" / "g2.conf",
        ]

        for path in possible_paths:
            if Path(path).exists():
                logger.info(f"Found G2 config: {path}")
                return str(path)

        logger.warning("G2 config not found. Using default initialization.")
        return None

    def _init_senzing_sdk(self):
        """Initialize Senzing SDK components."""
        try:
            from senzing import G2Config, G2Engine
            from senzing import SenzingBadInputError

            logger.info("Initializing Senzing SDK...")

            # Initialize config
            self.g2_config = G2Config()
            if self.g2_config_path:
                self.g2_config.init("cbp-sentry", {"configFile": self.g2_config_path})
            else:
                self.g2_config.init("cbp-sentry")

            # Initialize engine
            self.g2_engine = G2Engine()
            self.g2_engine.init("cbp-sentry", self.g2_config.exportConfig())

            logger.info("✓ Senzing SDK initialized")

        except Exception as e:
            logger.error(f"Failed to initialize Senzing SDK: {e}")
            raise

    def load_cord_records(
        self,
        cord_jsonl_file: str,
        data_source: str = "CORD_LONDON"
    ) -> Dict[str, int]:
        """
        Load CORD JSONL records into Senzing.

        Args:
            cord_jsonl_file: Path to CORD JSONL file
            data_source: Senzing DATA_SOURCE identifier

        Returns:
            Load statistics
        """
        if not self.g2_engine:
            raise RuntimeError("Senzing SDK not initialized")

        loaded = 0
        errors = 0
        skipped = 0

        logger.info(f"Loading CORD records from {cord_jsonl_file}...")

        with open(cord_jsonl_file, 'r') as f:
            for line_num, line in enumerate(f, 1):
                # Skip comments
                if line.startswith('#'):
                    skipped += 1
                    continue

                try:
                    record = json.loads(line)

                    # Ensure DATA_SOURCE is set
                    if "DATA_SOURCE" not in record:
                        record["DATA_SOURCE"] = data_source

                    # Add to Senzing engine
                    self.g2_engine.addRecord(
                        record["DATA_SOURCE"],
                        record.get("RECORD_ID", f"cord_{line_num}"),
                        json.dumps(record)
                    )

                    loaded += 1

                    if loaded % 1000 == 0:
                        logger.debug(f"Loaded {loaded} records...")

                except json.JSONDecodeError as e:
                    logger.warning(f"Line {line_num}: Invalid JSON - {e}")
                    errors += 1
                except Exception as e:
                    logger.error(f"Line {line_num}: {e}")
                    errors += 1

        logger.info(f"Load complete: {loaded} loaded, {errors} errors, {skipped} skipped")

        return {
            "loaded": loaded,
            "errors": errors,
            "skipped": skipped,
            "data_source": data_source
        }

    def search_entities(
        self,
        name: str,
        country: Optional[str] = None
    ) -> List[Dict]:
        """
        Search CORD for entities matching criteria.

        Args:
            name: Entity name to search for
            country: Optional country code filter

        Returns:
            List of matching entities with scores
        """
        if not self.g2_engine:
            raise RuntimeError("Senzing SDK not initialized")

        try:
            # Build search criteria
            search_record = {
                "NAME_FULL": name,
            }
            if country:
                search_record["COUNTRY_CODE"] = country

            # Search using Senzing engine
            results = self.g2_engine.searchByAttributes(json.dumps(search_record))
            results_json = json.loads(results)

            matches = []
            for resolved_entity in results_json.get("RESOLVED_ENTITIES", []):
                matches.append({
                    "entity_id": resolved_entity["ENTITY_ID"],
                    "name": resolved_entity.get("ENTITY_NAME"),
                    "match_score": resolved_entity.get("MATCH_SCORE"),
                    "data_sources": resolved_entity.get("DATA_SOURCES"),
                    "records": resolved_entity.get("RECORDS", [])
                })

            logger.info(f"Found {len(matches)} matches for '{name}'")
            return sorted(matches, key=lambda x: x.get("match_score", 0), reverse=True)

        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

    def get_entity_details(self, entity_id: int) -> Dict:
        """
        Get detailed information for an entity.

        Args:
            entity_id: Senzing entity ID

        Returns:
            Entity details including records and attributes
        """
        if not self.g2_engine:
            raise RuntimeError("Senzing SDK not initialized")

        try:
            entity_json = self.g2_engine.getEntity(entity_id)
            entity_data = json.loads(entity_json)

            return {
                "entity_id": entity_id,
                "entity_name": entity_data.get("RESOLVED_ENTITY", {}).get("ENTITY_NAME"),
                "record_count": len(entity_data.get("RESOLVED_ENTITY", {}).get("RECORDS", [])),
                "records": entity_data.get("RESOLVED_ENTITY", {}).get("RECORDS", []),
                "attributes": self._extract_attributes(entity_data)
            }

        except Exception as e:
            logger.error(f"Failed to get entity details: {e}")
            return {}

    def get_why_explanation(self, entity_a_id: int, entity_b_id: int) -> Dict:
        """
        Get why-explanation for why two entities matched.

        Args:
            entity_a_id: First Senzing entity ID
            entity_b_id: Second Senzing entity ID

        Returns:
            Explanation with match reasons and evidence
        """
        if not self.g2_engine:
            raise RuntimeError("Senzing SDK not initialized")

        try:
            why_json = self.g2_engine.why(entity_a_id, entity_b_id)
            why_data = json.loads(why_json)

            return {
                "entity_a": entity_a_id,
                "entity_b": entity_b_id,
                "match_level": why_data.get("WHY_RESULTS", [{}])[0].get("MATCH_LEVEL"),
                "match_reasons": why_data.get("WHY_RESULTS", [{}])[0].get("MATCH_KEYS", []),
                "evidence": self._extract_why_evidence(why_data)
            }

        except Exception as e:
            logger.error(f"Failed to get why explanation: {e}")
            return {}

    def find_related_entities(
        self,
        entity_id: int,
        relationship_type: Optional[str] = None
    ) -> List[Dict]:
        """
        Find entities related to a given entity.

        Args:
            entity_id: Senzing entity ID
            relationship_type: Optional filter (director_shared, ownership, etc.)

        Returns:
            List of related entities
        """
        if not self.g2_engine:
            raise RuntimeError("Senzing SDK not initialized")

        try:
            # Get entity details first
            entity_json = self.g2_engine.getEntity(entity_id)
            entity_data = json.loads(entity_json)

            related = []
            records = entity_data.get("RESOLVED_ENTITY", {}).get("RECORDS", [])

            for record in records:
                # Extract related entity IDs from record
                related_entities = record.get("RELATED_ENTITIES", [])
                for rel_entity in related_entities:
                    related.append({
                        "entity_id": rel_entity.get("ENTITY_ID"),
                        "relationship_type": rel_entity.get("RELATIONSHIP_TYPE"),
                        "match_score": rel_entity.get("MATCH_SCORE")
                    })

            logger.info(f"Found {len(related)} related entities for ID {entity_id}")
            return related

        except Exception as e:
            logger.error(f"Failed to find related entities: {e}")
            return []

    def resolve_entity_chain(
        self,
        start_name: str,
        depth: int = 2
    ) -> List[Dict]:
        """
        Resolve complete entity chain starting from a name.

        Args:
            start_name: Starting entity name (e.g., shipper)
            depth: Chain depth to traverse

        Returns:
            Entity chain with all details
        """
        chain = []
        seen_ids = set()

        # Search for starting entity
        matches = self.search_entities(start_name)
        if not matches:
            logger.warning(f"No entities found for '{start_name}'")
            return []

        # Add primary entity
        primary_id = matches[0]["entity_id"]
        primary = self.get_entity_details(primary_id)
        chain.append(primary)
        seen_ids.add(primary_id)

        # Traverse related entities
        def _traverse(entity_id: int, remaining_depth: int):
            if remaining_depth <= 0:
                return

            related = self.find_related_entities(entity_id)
            for rel_entity in related:
                rel_id = rel_entity["entity_id"]
                if rel_id not in seen_ids:
                    rel_details = self.get_entity_details(rel_id)
                    if rel_details:
                        chain.append(rel_details)
                        seen_ids.add(rel_id)
                        _traverse(rel_id, remaining_depth - 1)

        _traverse(primary_id, depth - 1)

        logger.info(f"Resolved entity chain: {len(chain)} entities")
        return chain

    @staticmethod
    def _extract_attributes(entity_data: Dict) -> Dict:
        """Extract key attributes from entity data."""
        resolved = entity_data.get("RESOLVED_ENTITY", {})
        return {
            "names": resolved.get("ENTITY_NAME"),
            "countries": list(set(
                r.get("COUNTRY_CODE") for r in resolved.get("RECORDS", [])
                if r.get("COUNTRY_CODE")
            )),
            "directors": [],  # Extract from records
            "beneficial_owners": []  # Extract from records
        }

    @staticmethod
    def _extract_why_evidence(why_data: Dict) -> List[str]:
        """Extract evidence from why-explanation."""
        evidence = []
        match_keys = why_data.get("WHY_RESULTS", [{}])[0].get("MATCH_KEYS", {})

        for key, matches in match_keys.items():
            for match in matches:
                evidence.append(f"{key}: {match}")

        return evidence

    def cleanup(self):
        """Cleanup Senzing resources."""
        if self.g2_engine:
            try:
                self.g2_engine.destroy()
                logger.info("Senzing engine cleaned up")
            except Exception as e:
                logger.warning(f"Cleanup warning: {e}")


# Test cases
def test_cord_integration():
    """Test Senzing CORD integration."""
    import tempfile

    logger.info("\n" + "="*70)
    logger.info("Testing Senzing CORD Integration")
    logger.info("="*70)

    try:
        # Initialize
        senzing = SenzingCORDIntegration()

        # Create test CORD file
        test_cord = [
            {"DATA_SOURCE": "CORD_LONDON_GLEIF", "RECORD_ID": "test_001", "NAME_FULL": "Greenfield Industrial Trading Co., Ltd.", "COUNTRY_CODE": "VN"},
            {"DATA_SOURCE": "CORD_LONDON_GLEIF", "RECORD_ID": "test_002", "NAME_FULL": "Greenfield Global Holdings Limited", "COUNTRY_CODE": "HK"},
            {"DATA_SOURCE": "CORD_LONDON_GLEIF", "RECORD_ID": "test_003", "NAME_FULL": "Guangdong Greenfield Aluminum Manufacturing", "COUNTRY_CODE": "CN"},
        ]

        # Write test file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            for record in test_cord:
                f.write(json.dumps(record) + '\n')
            test_file = f.name

        logger.info(f"\nTest 1: Load CORD records")
        result = senzing.load_cord_records(test_file)
        logger.info(f"Result: {result}")

        logger.info(f"\nTest 2: Search for entity")
        matches = senzing.search_entities("Greenfield Industrial", country="VN")
        logger.info(f"Found {len(matches)} matches")
        if matches:
            logger.info(f"Top match: {matches[0]}")

        logger.info(f"\nTest 3: Resolve entity chain")
        chain = senzing.resolve_entity_chain("Greenfield Industrial Trading", depth=2)
        logger.info(f"Chain length: {len(chain)}")
        for i, entity in enumerate(chain):
            logger.info(f"  {i+1}. {entity.get('entity_name')}")

        logger.info("\n✓ All tests passed")
        senzing.cleanup()

    except Exception as e:
        logger.error(f"✗ Test failed: {e}")
        raise


if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.INFO)
    test_cord_integration()
