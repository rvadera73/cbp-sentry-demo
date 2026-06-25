"""
Phase 2 Integration Module
Integrates Precise Risk Model with CBP Sentry API
- Feature flag control
- Dual-model routing (legacy vs. precise-risk-engine-api)
- Fallback mechanism
- Model comparison
"""
import os
import logging
import json
from typing import Dict, Any, Optional
from datetime import datetime
import httpx
import asyncio

logger = logging.getLogger(__name__)

# ============================================================================
# PHASE 2 CONFIGURATION
# ============================================================================

# Feature flag: Controls which model to use
USE_PRECISE_RISK_MODEL = os.getenv('USE_PRECISE_RISK_MODEL', 'false').lower() == 'true'

# Precise Risk Engine URL
PRECISE_RISK_ENGINE_URL = os.getenv(
    'PRECISE_RISK_ENGINE_URL',
    'http://localhost:8004'  # Default for local development
)

# Timeout for API calls
PRECISE_RISK_ENGINE_TIMEOUT = int(os.getenv('PRECISE_RISK_ENGINE_TIMEOUT', 5))

# Traffic ramping percentage (for monitoring)
TRAFFIC_PERCENTAGE = int(os.getenv('TRAFFIC_PERCENTAGE', 0))

# Deployment environment
DEPLOYMENT_ENV = os.getenv('DEPLOYMENT_ENV', 'local')

logger.info(f"""
╔═════════════════════════════════════════════════════════════╗
║        PHASE 2 INTEGRATION INITIALIZED                      ║
╚═════════════════════════════════════════════════════════════╝
USE_PRECISE_RISK_MODEL:      {USE_PRECISE_RISK_MODEL}
PRECISE_RISK_ENGINE_URL:     {PRECISE_RISK_ENGINE_URL}
PRECISE_RISK_ENGINE_TIMEOUT: {PRECISE_RISK_ENGINE_TIMEOUT}s
TRAFFIC_PERCENTAGE:          {TRAFFIC_PERCENTAGE}%
DEPLOYMENT_ENV:              {DEPLOYMENT_ENV}
""")


# ============================================================================
# PRECISE RISK CLIENT
# ============================================================================

class PreciseRiskClient:
    """Async HTTP client for Precise Risk Engine API"""

    def __init__(self, base_url: str, timeout: int = 5):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        logger.info(f"PreciseRiskClient initialized: {self.base_url}")

    async def health_check(self) -> bool:
        """Check if service is healthy"""
        try:
            async with httpx.AsyncClient(timeout=2) as client:
                response = await client.get(f"{self.base_url}/health")
                is_healthy = response.status_code == 200
                logger.debug(f"Health check: {is_healthy}")
                return is_healthy
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return False

    async def score_entity(self, domain: str, entity_id: str, entity_data: Dict[str, Any]) -> Dict[str, Any]:
        """Score an entity using Precise Risk Engine"""
        try:
            url = f"{self.base_url}/api/v1/scoring/score"

            payload = {
                "entity_id": entity_id,
                "domain": domain,
                "entity_data": entity_data,
                "timestamp": datetime.utcnow().isoformat()
            }

            logger.debug(f"Calling Precise Risk Engine: POST {url}")

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()

                result = response.json()
                logger.debug(f"Precise Risk Engine response: {result}")
                return result

        except httpx.TimeoutException:
            logger.error(f"Timeout calling Precise Risk Engine (>{self.timeout}s)")
            raise
        except httpx.ConnectError:
            logger.error(f"Connection error to Precise Risk Engine: {self.base_url}")
            raise
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error from Precise Risk Engine: {e.response.status_code}")
            raise
        except Exception as e:
            logger.error(f"Error calling Precise Risk Engine: {str(e)}")
            raise

    async def compare_models(self, domain: str, entity_id: str, entity_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get both legacy and new model scores"""
        try:
            url = f"{self.base_url}/api/v1/scoring/compare"

            payload = {
                "entity_id": entity_id,
                "domain": domain,
                "entity_data": entity_data
            }

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                return response.json()

        except Exception as e:
            logger.error(f"Error comparing models: {str(e)}")
            raise


# Global client instance
_precise_risk_client: Optional[PreciseRiskClient] = None


def get_precise_risk_client() -> PreciseRiskClient:
    """Get or create Precise Risk Client"""
    global _precise_risk_client
    if _precise_risk_client is None:
        _precise_risk_client = PreciseRiskClient(PRECISE_RISK_ENGINE_URL, PRECISE_RISK_ENGINE_TIMEOUT)
    return _precise_risk_client


# ============================================================================
# PHASE 2 ROUTING FUNCTIONS
# ============================================================================

async def score_shipment_phase2(shipment_id: str, entity_data: Dict[str, Any],
                               legacy_score_func) -> Dict[str, Any]:
    """
    Route shipment scoring to either Precise Risk Engine or legacy model

    Args:
        shipment_id: Shipment identifier
        entity_data: Entity attributes to score
        legacy_score_func: Fallback function for legacy model

    Returns:
        Risk score result with model version and routing info
    """
    start_time = datetime.utcnow()

    try:
        logger.info(f"Scoring shipment {shipment_id} - Route: {'new' if USE_PRECISE_RISK_MODEL else 'legacy'}")

        # Try new model if flag is enabled
        if USE_PRECISE_RISK_MODEL:
            try:
                client = get_precise_risk_client()

                # Check health first
                is_healthy = await client.health_check()
                if not is_healthy:
                    raise Exception("Precise Risk Engine not healthy")

                # Call new model
                result = await client.score_entity('cbp', shipment_id, entity_data)
                result['model_version'] = 'precise-risk-model-v1'
                result['route'] = 'new'

            except Exception as e:
                logger.warning(f"New model failed, falling back to legacy: {str(e)}")
                # Fallback to legacy
                result = legacy_score_func(shipment_id, entity_data)
                result['model_version'] = 'legacy'
                result['route'] = 'fallback'
                result['fallback_reason'] = str(e)

        else:
            # Use legacy model
            result = legacy_score_func(shipment_id, entity_data)
            result['model_version'] = 'legacy'
            result['route'] = 'legacy'

        # Add metadata
        result['shipment_id'] = shipment_id
        result['scored_at'] = datetime.utcnow().isoformat()
        result['latency_ms'] = (datetime.utcnow() - start_time).total_seconds() * 1000

        logger.info(f"Shipment {shipment_id} scored in {result['latency_ms']:.1f}ms "
                   f"(model={result['route']})")

        return result

    except Exception as e:
        logger.error(f"Fatal error in score_shipment_phase2: {str(e)}")
        # Return error response
        return {
            "error": "Scoring failed",
            "message": str(e),
            "shipment_id": shipment_id,
            "route": "error"
        }


async def compare_shipment_models(shipment_id: str, entity_data: Dict[str, Any],
                                 legacy_score_func) -> Dict[str, Any]:
    """
    Score shipment with both legacy and new models for comparison

    Used during traffic ramping to validate models side-by-side
    """
    try:
        # Score with legacy model
        legacy_result = legacy_score_func(shipment_id, entity_data)

        # Score with new model (if available)
        try:
            client = get_precise_risk_client()
            new_result = await client.score_entity('cbp', shipment_id, entity_data)
        except Exception as e:
            logger.warning(f"New model unavailable for comparison: {str(e)}")
            new_result = {"error": str(e), "available": False}

        # Compare results
        if "error" not in new_result:
            score_difference = abs(new_result.get('risk_score', 0) - legacy_result.get('risk_score', 0))
            agreement = "AGREE" if score_difference < 10 else "DIFFER"
        else:
            score_difference = None
            agreement = "UNAVAILABLE"

        comparison = {
            "shipment_id": shipment_id,
            "legacy_model": legacy_result,
            "new_model": new_result,
            "comparison": {
                "score_difference": score_difference,
                "agreement": agreement,
                "legacy_score": legacy_result.get('risk_score'),
                "new_score": new_result.get('risk_score') if "error" not in new_result else None
            }
        }

        logger.info(f"Model comparison for {shipment_id}: {agreement}")

        return comparison

    except Exception as e:
        logger.error(f"Error in compare_shipment_models: {str(e)}")
        raise


# ============================================================================
# FEATURE FLAG MANAGEMENT
# ============================================================================

class FeatureFlagManager:
    """Manage feature flag state"""

    _state = {
        'enabled': USE_PRECISE_RISK_MODEL,
        'traffic_percentage': TRAFFIC_PERCENTAGE
    }

    @classmethod
    def get_state(cls) -> Dict[str, Any]:
        """Get current feature flag state"""
        return {
            "feature": "USE_PRECISE_RISK_MODEL",
            "enabled": cls._state['enabled'],
            "traffic_percentage": cls._state['traffic_percentage'],
            "timestamp": datetime.utcnow().isoformat()
        }

    @classmethod
    def set_state(cls, enabled: bool, traffic_percentage: int = 0) -> Dict[str, Any]:
        """Set feature flag state"""
        logger.warning(f"Feature flag changed: enabled={enabled}, traffic={traffic_percentage}%")
        cls._state['enabled'] = enabled
        cls._state['traffic_percentage'] = traffic_percentage
        return cls.get_state()

    @classmethod
    def is_enabled(cls) -> bool:
        """Check if feature flag is enabled"""
        return cls._state['enabled']

    @classmethod
    def get_traffic_percentage(cls) -> int:
        """Get traffic percentage for new model"""
        return cls._state['traffic_percentage']


# ============================================================================
# INTEGRATION HEALTH CHECK
# ============================================================================

async def check_phase2_health() -> Dict[str, Any]:
    """Check health of Phase 2 integration"""
    try:
        client = get_precise_risk_client()
        precise_risk_healthy = await client.health_check()
    except Exception as e:
        logger.error(f"Error checking Precise Risk Engine health: {str(e)}")
        precise_risk_healthy = False

    return {
        "phase2_enabled": USE_PRECISE_RISK_MODEL,
        "precise_risk_engine": {
            "url": PRECISE_RISK_ENGINE_URL,
            "healthy": precise_risk_healthy
        },
        "traffic_percentage": TRAFFIC_PERCENTAGE,
        "timestamp": datetime.utcnow().isoformat()
    }
