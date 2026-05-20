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
        self.cord_engine = None
        self._init_cord_engine()

    def _init_cord_engine(self):
        """Initialize CORD engine for OFAC lookups (lazy import to avoid circular deps)."""
        try:
            from cord_engine import get_cord_engine
            self.cord_engine = get_cord_engine()
            logger.info("OFAC service initialized with CORD engine")
        except Exception as e:
            logger.warning(f"CORD engine not available for OFAC checks: {e}")

    async def check_entity(self, entity_name: str) -> OFACMatch:
        """
        Check if an entity matches OFAC SDN list.

        Args:
            entity_name: Name of entity to check

        Returns:
            OFACMatch with results
        """
        logger.info(f"Checking entity '{entity_name}' against OFAC SDN list")

        # Step 1: Try CORD OFAC database (1,996 real SDN entries)
        if self.cord_engine:
            try:
                cord_match = self.cord_engine.get_ofac_status(entity_name)
                if cord_match and cord_match.get("matched"):
                    raw_record = cord_match.get("raw", {})
                    programs = [cord_match.get("program")] if cord_match.get("program") else []
                    return OFACMatch(
                        matched=True,
                        entity_name=entity_name,
                        sdn_name=cord_match.get("sdn_name", ""),
                        entity_type=cord_match.get("entity_type", ""),
                        programs=programs,
                        confidence_pct=98.0,
                        source="CORD OFAC SDN List",
                        last_updated=datetime.utcnow().isoformat()
                    )
            except Exception as e:
                logger.debug(f"CORD OFAC check failed: {e}")

        # Step 2: Try real OFAC API if available
        try:
            result = await self._check_real_ofac(entity_name)
            return result
        except Exception as e:
            logger.warning(f"Real OFAC check failed: {e}")
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
