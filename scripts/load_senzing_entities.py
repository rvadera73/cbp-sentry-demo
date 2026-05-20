"""
Load seed entities into Senzing via REST API.

This script:
1. Waits for Senzing service to be healthy (/heartbeat)
2. Reads senzing_entities.jsonl (one JSON per line)
3. POSTs each record to Senzing /v3/records endpoint
4. Logs success/failure for each entity

Run from docker-compose senzing-init service after senzing is healthy.
"""

import asyncio
import json
import logging
import httpx
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Senzing service URL
SENZING_URL = "http://senzing:8250"
SEED_DATA_PATH = Path("/app/seed_data/senzing_entities.jsonl")


async def wait_for_senzing(max_retries: int = 30, interval: float = 2.0) -> bool:
    """
    Wait for Senzing service to be healthy.

    Args:
        max_retries: Maximum number of retry attempts
        interval: Seconds between retries

    Returns:
        True if healthy, False if timeout
    """
    async with httpx.AsyncClient(timeout=5.0) as client:
        for attempt in range(max_retries):
            try:
                response = await client.get(f"{SENZING_URL}/heartbeat")
                if response.status_code == 200:
                    logger.info("Senzing service is healthy")
                    return True
            except Exception as e:
                logger.debug(f"Health check attempt {attempt + 1} failed: {e}")

            if attempt < max_retries - 1:
                await asyncio.sleep(interval)

    logger.error(f"Senzing service did not become healthy after {max_retries} attempts")
    return False


async def load_entities() -> None:
    """
    Load all entities from senzing_entities.jsonl into Senzing.
    """
    # Wait for Senzing to be healthy
    if not await wait_for_senzing():
        logger.error("Cannot proceed; Senzing is not healthy")
        sys.exit(1)

    if not SEED_DATA_PATH.exists():
        logger.error(f"Seed data file not found: {SEED_DATA_PATH}")
        sys.exit(1)

    success_count = 0
    failure_count = 0

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            with open(SEED_DATA_PATH, "r") as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        record = json.loads(line)

                        # Extract required fields
                        data_source = record.pop("DATA_SOURCE", f"DEMO_CASE_{line_num}")
                        record_id = record.pop("RECORD_ID", f"record_{line_num}")

                        # POST to Senzing
                        payload = {
                            "data_source": data_source,
                            "record_id": record_id,
                            **record
                        }

                        response = await client.post(
                            f"{SENZING_URL}/v3/records",
                            json=payload
                        )

                        if response.status_code in (200, 201, 204):
                            logger.info(f"✓ Loaded {data_source}/{record_id}")
                            success_count += 1
                        else:
                            logger.error(
                                f"✗ Failed to load {data_source}/{record_id}: "
                                f"HTTP {response.status_code} - {response.text}"
                            )
                            failure_count += 1

                    except json.JSONDecodeError as e:
                        logger.error(f"✗ Line {line_num} is invalid JSON: {e}")
                        failure_count += 1
                    except Exception as e:
                        logger.error(f"✗ Error processing line {line_num}: {e}")
                        failure_count += 1

        except Exception as e:
            logger.error(f"Failed to read seed data: {e}")
            sys.exit(1)

    logger.info(f"\n=== Entity Load Summary ===")
    logger.info(f"Successfully loaded: {success_count}")
    logger.info(f"Failed: {failure_count}")

    if failure_count > 0:
        logger.warning("Some entities failed to load; see above for details")
        sys.exit(1)
    else:
        logger.info("All entities loaded successfully")
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(load_entities())
