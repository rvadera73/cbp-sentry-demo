#!/usr/bin/env python3
"""
Initialize CORD (Senzing Ready Data Collections) for CBP entity resolution.

This script:
1. Waits for Senzing to be healthy
2. Loads curated CORD entities for CBP testing
3. Primes Senzing for high-accuracy entity matching

Run at startup: python init_cord_data.py
"""

import sys
import time
import json
import logging
from pathlib import Path
from typing import Dict
import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

SENZING_URL = "http://localhost:8250"
CORD_FILE = Path(__file__).parent.parent / "seed_data" / "cord_cbp_entities.jsonl"
MAX_RETRIES = 30
RETRY_DELAY = 2


def wait_for_senzing(url: str, max_retries: int = MAX_RETRIES) -> bool:
    """Wait for Senzing service to be healthy."""
    for attempt in range(max_retries):
        try:
            response = requests.get(f"{url}/health", timeout=5)
            if response.status_code == 200:
                logger.info(f"✓ Senzing service healthy at {url}")
                return True
        except requests.exceptions.RequestException:
            pass

        if attempt < max_retries - 1:
            logger.info(
                f"Waiting for Senzing... (attempt {attempt + 1}/{max_retries})"
            )
            time.sleep(RETRY_DELAY)

    logger.error(f"✗ Senzing service did not respond after {max_retries * RETRY_DELAY}s")
    return False


def load_cord_entities(cord_file: Path, senzing_url: str) -> Dict:
    """Load CORD entities from JSONL file into Senzing."""
    if not cord_file.exists():
        logger.error(f"CORD file not found: {cord_file}")
        return {"loaded": 0, "errors": 0}

    loaded = 0
    errors = 0

    logger.info(f"Loading CORD entities from {cord_file}")

    with open(cord_file, 'r') as f:
        for line_num, line in enumerate(f, 1):
            # Skip comments
            if line.startswith('#'):
                continue

            try:
                record = json.loads(line)

                # Post to Senzing
                response = requests.post(
                    f"{senzing_url}/load-record",
                    json=record,
                    timeout=10
                )

                if response.status_code in [200, 201]:
                    loaded += 1
                    if loaded % 5 == 0:
                        logger.debug(f"Loaded {loaded} CORD entities...")
                else:
                    logger.warning(
                        f"Line {line_num}: Senzing returned {response.status_code}"
                    )
                    errors += 1

            except json.JSONDecodeError:
                logger.warning(f"Line {line_num}: Invalid JSON")
                errors += 1
            except requests.exceptions.RequestException as e:
                logger.error(f"Line {line_num}: Request failed: {e}")
                errors += 1
            except Exception as e:
                logger.error(f"Line {line_num}: Unexpected error: {e}")
                errors += 1

    logger.info(f"✓ CORD load complete: {loaded} loaded, {errors} errors")
    return {"loaded": loaded, "errors": errors}


def verify_cord_entities(senzing_url: str) -> bool:
    """Verify that key CORD entities were loaded."""
    test_cases = [
        {
            "name": "Greenfield Aluminum CN",
            "search_term": "Guangdong Greenfield"
        },
        {
            "name": "Greenfield Holdings HK",
            "search_term": "Greenfield Global"
        },
        {
            "name": "Greenfield Trading VN",
            "search_term": "Greenfield Industrial Trading"
        },
    ]

    logger.info("Verifying CORD entity loading...")

    for test in test_cases:
        try:
            # Search for entity by name
            response = requests.get(
                f"{senzing_url}/search",
                params={"name": test["search_term"]},
                timeout=10
            )

            if response.status_code == 200:
                results = response.json().get('results', [])
                if results:
                    logger.info(f"  ✓ {test['name']}: Found in Senzing")
                else:
                    logger.warning(f"  ? {test['name']}: No search results")
            else:
                logger.warning(f"  ✗ {test['name']}: Search failed")

        except Exception as e:
            logger.warning(f"  ✗ {test['name']}: {e}")

    return True


def main():
    """Main initialization sequence."""
    logger.info("=" * 70)
    logger.info("Senzing CORD Initialization")
    logger.info("=" * 70)

    # Step 1: Wait for Senzing
    logger.info("\n1. Waiting for Senzing service...")
    if not wait_for_senzing(SENZING_URL):
        logger.error("Failed to connect to Senzing. Exiting.")
        return 1

    # Step 2: Load CORD data
    logger.info("\n2. Loading CORD entities...")
    result = load_cord_entities(CORD_FILE, SENZING_URL)

    if result["errors"] > 0:
        logger.warning(f"   Loaded with {result['errors']} errors")

    # Step 3: Verify
    logger.info("\n3. Verifying CORD entities...")
    verify_cord_entities(SENZING_URL)

    logger.info("\n" + "=" * 70)
    logger.info("✓ CORD initialization complete")
    logger.info("=" * 70)
    logger.info("\nEntity Resolution is now ready with CORD reference data.")
    logger.info("Senzing will match manifest entities against loaded CORD entities.")

    return 0


if __name__ == '__main__':
    sys.exit(main())
