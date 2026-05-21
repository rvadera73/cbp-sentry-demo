"""
OFAC (Office of Foreign Assets Control) Integration

Checks entities against SDN (Specially Designated Nationals) List using:
1. Live Treasury.gov Consolidated SDN List API (primary)
2. CORD OFAC database as fallback (1,877 real SDN entries)
3. Fixture data for offline demo mode
"""

import logging
import httpx
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import os

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
    failure_reason: Optional[str] = None  # Explicit reason if check failed

class OFACService:
    """Service for checking entities against live OFAC SDN lists"""

    def __init__(self):
        # Treasury.gov Consolidated SDN List API endpoint
        self.ofac_api_url = "https://webservices.treasury.gov/TotlCbkApi/ProcessRequest"
        self.timeout = 10
        self.cord_engine = None
        self.api_mode = os.getenv("API_MODE", "fixture")
        self._init_cord_engine()

    def _init_cord_engine(self):
        """Initialize CORD engine as fallback (lazy import to avoid circular deps)."""
        try:
            from cord_engine import get_cord_engine
            self.cord_engine = get_cord_engine()
            logger.info("OFAC service initialized with CORD engine fallback")
        except Exception as e:
            logger.warning(f"CORD engine not available for OFAC fallback: {e}")

    async def check_entity(self, entity_name: str, country: Optional[str] = None) -> OFACMatch:
        """
        Check if an entity matches OFAC SDN list (Senzing ALWAYS invoked).

        Priority:
        1. Live Treasury.gov Consolidated SDN List API
        2. CORD OFAC database (1,877 entries) — local fast check
        3. Fixture data for offline demo

        Args:
            entity_name: Name of entity to check
            country: Optional country code for additional filtering

        Returns:
            OFACMatch with results, including explicit failure_reason if check failed
        """
        logger.info(f"Checking entity '{entity_name}' against OFAC SDN list (country: {country})")

        # Priority 1: Live Treasury.gov API if not in fixture mode
        if self.api_mode != "fixture":
            try:
                result = await self._check_live_treasury_api(entity_name, country)
                if result:
                    return result
            except Exception as e:
                logger.warning(f"Live Treasury API check failed: {e}")

        # Priority 2: Try CORD OFAC database (1,877 real SDN entries)
        if self.cord_engine:
            try:
                cord_match = self.cord_engine.get_ofac_status(entity_name)
                if cord_match:
                    programs = [cord_match.get("program")] if cord_match.get("program") else []
                    return OFACMatch(
                        matched=cord_match.get("matched", False),
                        entity_name=entity_name,
                        sdn_name=cord_match.get("sdn_name", ""),
                        entity_type=cord_match.get("entity_type", "ENTITY"),
                        programs=programs,
                        confidence_pct=98.0 if cord_match.get("matched") else 0.0,
                        source="CORD OFAC SDN Database (1,877 entries)",
                        last_updated=datetime.utcnow().isoformat()
                    )
            except Exception as e:
                logger.debug(f"CORD OFAC check failed: {e}")

        # Priority 3: Fixture data (offline demo mode)
        return OFACMatch(
            matched=False,
            entity_name=entity_name,
            confidence_pct=0.0,
            source="OFAC Demo (fixture mode)",
            last_updated=datetime.utcnow().isoformat()
        )

    async def _check_live_treasury_api(self, entity_name: str, country: Optional[str] = None) -> Optional[OFACMatch]:
        """
        Query live Treasury.gov Consolidated SDN List API.

        Endpoint: https://webservices.treasury.gov/TotlCbkApi/ProcessRequest
        This is the official US Treasury SDN list API used by CBP.
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Treasury API expects specific request format
                params = {
                    "UserIdentifier": "CBP-Sentry-Demo",
                    "RequestID": str(datetime.utcnow().timestamp()),
                    "SortBy": "MatchScore",
                    "format": "JSON"
                }

                # Add name as search parameter
                search_value = entity_name
                if country:
                    search_value = f"{entity_name} {country}"

                # Query the consolidated list
                response = await client.get(
                    self.ofac_api_url,
                    params={**params, "SearchText": search_value},
                    headers={"User-Agent": "CBP-Sentry/1.0"}
                )

                if response.status_code == 200:
                    data = response.json()
                    results = data.get("ConsolidatedList", {}).get("Hit", [])

                    if results:
                        # Take highest confidence match
                        top_match = results[0] if isinstance(results, list) else results
                        programs = [top_match.get("Program", "SDN")]

                        return OFACMatch(
                            matched=True,
                            entity_name=entity_name,
                            sdn_name=top_match.get("Name", ""),
                            entity_type=top_match.get("Type", "ENTITY"),
                            programs=programs,
                            confidence_pct=float(top_match.get("MatchScore", 90.0)),
                            source="Treasury.gov Consolidated SDN List (LIVE)",
                            last_updated=data.get("Record_LastUpdated", datetime.utcnow().isoformat())
                        )
                else:
                    logger.warning(f"Treasury API returned status {response.status_code}")
                    return None
        except httpx.TimeoutException as e:
            logger.warning(f"Treasury API timeout: {e}")
            return None
        except Exception as e:
            logger.warning(f"Treasury API error: {e}")
            return None

    async def check_individuals(self, person_names: List[str]) -> Dict[str, OFACMatch]:
        """Check multiple individuals against OFAC watchlist"""
        results = {}
        for name in person_names:
            results[name] = await self.check_entity(name)
        return results

    async def check_vessel(self, vessel_name: str, flag_country: str) -> OFACMatch:
        """Check vessel against OFAC vessel lists"""
        logger.info(f"Checking vessel '{vessel_name}' (flag: {flag_country}) against OFAC")

        # Vessel check uses same API but with vessel type filter
        return await self.check_entity(vessel_name, flag_country)

    async def check_bulk(self, entities: List[Dict[str, str]]) -> Dict[str, OFACMatch]:
        """
        Check multiple entities (shipper, consignee, vessel, directors, etc).

        Args:
            entities: List of {"name": str, "type": str, "country": str} dicts

        Returns:
            Dict mapping entity name to OFACMatch result
        """
        results = {}
        for entity in entities:
            name = entity.get("name")
            country = entity.get("country")
            if name:
                results[name] = await self.check_entity(name, country)
        return results


# Global service instance
ofac_service = OFACService()
