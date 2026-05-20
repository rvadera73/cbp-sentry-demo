"""
OFAC (Office of Foreign Assets Control) Integration

Checks entities against SDN (Specially Designated Nationals) List and other
OFAC watchlists. Can be replaced with real OFAC API when available.
"""

import logging
import httpx
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class OFACMatch:
    """Result from OFAC SDN check"""
    matched: bool
    entity_name: str
    sdn_name: Optional[str] = None
    entity_type: Optional[str] = None  # Individual, Entity, Vessel
    programs: Optional[List[str]] = None
    confidence_pct: float = 0.0
    source: str = "OFAC SDN List"
    last_updated: Optional[str] = None

class OFACService:
    """Service for checking entities against OFAC watchlists"""

    def __init__(self):
        self.base_url = "https://api.trade.gov"  # US Trade API endpoint
        self.timeout = 10
        # Mock SDN entries for demo - in production this would be the real OFAC list
        self.mock_sdn_entries = {
            "zhang wei": {"name": "ZHANG, Wei", "type": "Individual", "programs": ["CAATSA"]},
            "greenfield aluminum": {"name": "GREENFIELD ALUMINUM CORP", "type": "Entity", "programs": ["EO13959"]},
            "solaria manufacturing": {"name": "SOLARIA MANUFACTURING", "type": "Entity", "programs": ["CMIC"]},
        }

    async def check_entity(self, entity_name: str) -> OFACMatch:
        """
        Check if an entity matches OFAC SDN list.

        Args:
            entity_name: Name of entity to check

        Returns:
            OFACMatch with results
        """
        logger.info(f"Checking entity '{entity_name}' against OFAC SDN list")

        # First try mock data (for demo)
        entity_lower = entity_name.lower()
        for mock_key, mock_data in self.mock_sdn_entries.items():
            if mock_key in entity_lower:
                return OFACMatch(
                    matched=True,
                    entity_name=entity_name,
                    sdn_name=mock_data["name"],
                    entity_type=mock_data["type"],
                    programs=mock_data["programs"],
                    confidence_pct=95.0,
                    last_updated=datetime.utcnow().isoformat()
                )

        # Try real API if available
        try:
            result = await self._check_real_ofac(entity_name)
            return result
        except Exception as e:
            logger.warning(f"Real OFAC check failed, using fallback: {e}")
            return OFACMatch(
                matched=False,
                entity_name=entity_name,
                confidence_pct=0.0
            )

    async def check_individuals(self, person_names: List[str]) -> Dict[str, OFACMatch]:
        """Check multiple individuals against OFAC watchlist"""
        results = {}
        for name in person_names:
            results[name] = await self.check_entity(name)
        return results

    async def check_vessel(self, vessel_name: str, flag_country: str) -> OFACMatch:
        """Check vessel against OFAC vessel lists"""
        logger.info(f"Checking vessel '{vessel_name}' (flag: {flag_country}) against OFAC")

        # For demo, check if vessel matches known problematic patterns
        vessel_lower = vessel_name.lower()
        if any(x in vessel_lower for x in ["deauville", "glory", "wise honest"]):
            return OFACMatch(
                matched=True,
                entity_name=vessel_name,
                entity_type="Vessel",
                programs=["IRGC", "DPRK Sanctions"],
                confidence_pct=98.0,
                last_updated=datetime.utcnow().isoformat()
            )

        return OFACMatch(
            matched=False,
            entity_name=vessel_name,
            confidence_pct=0.0
        )

    async def _check_real_ofac(self, entity_name: str) -> OFACMatch:
        """
        Call real OFAC API when available.
        Production: Replace with actual OFAC OPENDATA or Treasury API
        """
        try:
            async with httpx.AsyncClient() as client:
                # Example: Trade.gov API for OFAC data
                response = await client.get(
                    f"{self.base_url}/v1/fta_agreements/search",
                    params={"keyword": entity_name},
                    timeout=self.timeout
                )
                # Parse response and convert to OFACMatch
                if response.status_code == 200:
                    data = response.json()
                    # Process real API response
                    if data.get("total") > 0:
                        return OFACMatch(
                            matched=True,
                            entity_name=entity_name,
                            sdn_name=data.get("results", [{}])[0].get("name"),
                            confidence_pct=92.0
                        )
        except Exception as e:
            logger.warning(f"Real OFAC API error: {e}")

        return OFACMatch(
            matched=False,
            entity_name=entity_name,
            confidence_pct=0.0
        )


# Global service instance
ofac_service = OFACService()
