"""
HTTP Client for Precise Risk Engine Microservice Integration
Phase 2: Communication layer between cbp-sentry-api and precise-risk-engine-api
"""
import requests
import logging
import json
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class PreciseRiskClient:
    """HTTP client for communicating with precise-risk-engine-api microservice"""

    def __init__(self, base_url: str, timeout: int = 5):
        """
        Initialize Precise Risk Client

        Args:
            base_url: Base URL of precise-risk-engine-api (e.g., http://localhost:8004)
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'CBPSentry-Phase2/1.0'
        })
        logger.info(f"PreciseRiskClient initialized: {self.base_url}")

    def health_check(self) -> bool:
        """
        Check if precise-risk-engine-api is available

        Returns:
            True if service is healthy, False otherwise
        """
        try:
            url = f"{self.base_url}/health"
            response = self.session.get(url, timeout=2)
            is_healthy = response.status_code == 200
            if not is_healthy:
                logger.warning(f"Precise Risk Engine health check failed: {response.status_code}")
            return is_healthy
        except requests.exceptions.RequestException as e:
            logger.error(f"Precise Risk Engine health check error: {str(e)}")
            return False

    def score_entity(self, domain: str, entity_id: str, entity_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Score an entity using precise-risk-engine-api

        Args:
            domain: Risk domain (cbp, fda, opioid)
            entity_id: Unique entity identifier
            entity_data: Entity attributes for scoring

        Returns:
            Dictionary with risk score, confidence, explanation

        Raises:
            requests.exceptions.RequestException: If API call fails
        """
        try:
            url = f"{self.base_url}/api/v1/scoring/score"

            payload = {
                "entity_id": entity_id,
                "domain": domain,
                "entity_data": entity_data,
                "timestamp": datetime.utcnow().isoformat()
            }

            logger.debug(f"Calling Precise Risk Engine: {url} (domain={domain}, entity={entity_id})")

            response = self.session.post(
                url,
                json=payload,
                timeout=self.timeout
            )

            response.raise_for_status()

            result = response.json()
            logger.debug(f"Precise Risk Engine response: {result}")

            return result

        except requests.exceptions.Timeout:
            logger.error(f"Precise Risk Engine timeout (>{self.timeout}s)")
            raise
        except requests.exceptions.ConnectionError:
            logger.error(f"Precise Risk Engine connection error: {self.base_url}")
            raise
        except requests.exceptions.HTTPError as e:
            logger.error(f"Precise Risk Engine HTTP error: {e.response.status_code}")
            raise
        except Exception as e:
            logger.error(f"Precise Risk Engine error: {str(e)}")
            raise

    def get_rules(self, domain: str) -> Dict[str, Any]:
        """Get active rules for a domain"""
        try:
            url = f"{self.base_url}/api/v1/rules/{domain}"
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching rules for domain {domain}: {str(e)}")
            raise

    def get_metrics(self, domain: str) -> Dict[str, Any]:
        """Get model performance metrics for a domain"""
        try:
            url = f"{self.base_url}/api/v1/metrics/{domain}"
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching metrics for domain {domain}: {str(e)}")
            raise

    def submit_feedback(self, domain: str, entity_id: str, analyst_label: int, confidence: float) -> bool:
        """Submit analyst feedback for active learning"""
        try:
            url = f"{self.base_url}/api/v1/feedback/{domain}/{entity_id}"
            payload = {
                "analyst_label": analyst_label,  # 0 or 1
                "confidence": confidence
            }
            response = self.session.post(url, json=payload, timeout=self.timeout)
            response.raise_for_status()
            logger.info(f"Feedback submitted for {entity_id}")
            return True
        except Exception as e:
            logger.error(f"Error submitting feedback: {str(e)}")
            return False

    def close(self):
        """Close the session"""
        self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def create_precise_risk_client(base_url: str, timeout: int = 5) -> PreciseRiskClient:
    """Factory function to create a PreciseRiskClient instance"""
    return PreciseRiskClient(base_url, timeout)
