"""Cache service utilities for risk scoring."""
import logging
import json
from typing import Any, Optional
from . import cache

logger = logging.getLogger(__name__)


def test_redis_connection() -> bool:
    """Test Redis connection."""
    try:
        cache.cache._client.ping()
        logger.info("Redis connection successful")
        return True
    except Exception as e:
        logger.error(f"Redis connection failed: {e}")
        return False


def cache_risk_score(entity_id: str, score: dict, ttl: int = 3600) -> bool:
    """
    Cache a risk score result.

    Args:
        entity_id: Entity identifier
        score: Risk score data
        ttl: Time to live in seconds (default 1 hour)

    Returns:
        Success flag
    """
    try:
        key = f"risk_score:{entity_id}"
        cache.set(key, json.dumps(score), timeout=ttl)
        logger.debug(f"Cached risk score for entity {entity_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to cache risk score: {e}")
        return False


def get_cached_risk_score(entity_id: str) -> Optional[dict]:
    """
    Retrieve a cached risk score.

    Args:
        entity_id: Entity identifier

    Returns:
        Cached score data or None if not found
    """
    try:
        key = f"risk_score:{entity_id}"
        cached = cache.get(key)
        if cached:
            logger.debug(f"Retrieved cached risk score for entity {entity_id}")
            return json.loads(cached)
        return None
    except Exception as e:
        logger.error(f"Failed to retrieve cached risk score: {e}")
        return None


def invalidate_risk_cache(entity_id: Optional[str] = None) -> bool:
    """
    Invalidate risk score cache.

    Args:
        entity_id: Specific entity to invalidate, or None for all

    Returns:
        Success flag
    """
    try:
        if entity_id:
            key = f"risk_score:{entity_id}"
            cache.delete(key)
            logger.debug(f"Invalidated cache for entity {entity_id}")
        else:
            cache.clear()
            logger.info("Cleared all risk score cache")
        return True
    except Exception as e:
        logger.error(f"Failed to invalidate cache: {e}")
        return False
