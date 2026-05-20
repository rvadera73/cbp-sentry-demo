"""
OpenData.org Registry Service Integration

Checks corporate entities against international business registries
(OpenCorporates, OpenData registries, national business registries).
Validates company registration, director information, and risk flags.
"""

import logging
import httpx
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
from dateutil import parser as dateutil_parser

logger = logging.getLogger(__name__)

@dataclass
class RegistryMatch:
    """Result from corporate registry check"""
    found: bool
    entity_name: str
    country_of_incorporation: str
    registration_number: Optional[str] = None
    incorporation_date: Optional[str] = None
    status: str = "active"  # active, dissolved, suspended
    directors: List[Dict[str, Any]] = None
    company_type: str = "Unknown"
    confidence_pct: float = 0.0
    source: str = "Corporate Registry"
    risk_flags: List[str] = None

    def __post_init__(self):
        if self.directors is None:
            self.directors = []
        if self.risk_flags is None:
            self.risk_flags = []

class RegistryService:
    """Service for checking entities against international corporate registries"""

    def __init__(self):
        self.opencorporates_url = "https://api.opencorporates.com/v0.4"
        self.timeout = 10
        # Mock registry data for demo
        self.mock_entities = {
            "greenfield industrial": {
                "country": "VN",
                "reg_number": "VN0123456789",
                "incorporation_date": "2024-09-15",
                "status": "active",
                "directors": [
                    {"name": "ZHANG Wei", "nationality": "CN", "role": "Director"},
                    {"name": "LI Ming", "nationality": "CN", "role": "Manager"}
                ],
                "company_type": "Limited Liability Company"
            },
            "solaria manufacturing": {
                "country": "MY",
                "reg_number": "MY2024001234",
                "incorporation_date": "2025-04-01",
                "status": "active",
                "directors": [
                    {"name": "TAN Peng", "nationality": "MY", "role": "Director"}
                ],
                "company_type": "Sdn Bhd"
            },
            "guangdong greenfield": {
                "country": "CN",
                "reg_number": "CN441900000000001",
                "incorporation_date": "2015-03-20",
                "status": "active",
                "directors": [
                    {"name": "ZHANG Wei", "nationality": "CN", "role": "Legal Representative"},
                    {"name": "WANG Fang", "nationality": "CN", "role": "Director"}
                ],
                "company_type": "Limited Liability Company"
            }
        }

    async def lookup_entity(
        self,
        entity_name: str,
        country_code: str
    ) -> RegistryMatch:
        """
        Look up entity in corporate registry.

        Args:
            entity_name: Name of company
            country_code: ISO 2-letter country code

        Returns:
            RegistryMatch with company information
        """
        logger.info(f"Looking up entity '{entity_name}' in {country_code} registry")

        # Try mock data first
        entity_lower = entity_name.lower()
        for mock_key, mock_data in self.mock_entities.items():
            if mock_key in entity_lower and mock_data["country"] == country_code:
                risk_flags = self._assess_risk_flags(
                    entity_name,
                    mock_data.get("incorporation_date"),
                    mock_data.get("directors", [])
                )
                return RegistryMatch(
                    found=True,
                    entity_name=entity_name,
                    country_of_incorporation=country_code,
                    registration_number=mock_data.get("reg_number"),
                    incorporation_date=mock_data.get("incorporation_date"),
                    status=mock_data.get("status", "active"),
                    directors=mock_data.get("directors", []),
                    company_type=mock_data.get("company_type"),
                    confidence_pct=95.0,
                    risk_flags=risk_flags
                )

        # Try real API if available
        try:
            result = await self._lookup_opencorporates(entity_name, country_code)
            return result
        except Exception as e:
            logger.warning(f"Registry lookup failed: {e}")
            return RegistryMatch(
                found=False,
                entity_name=entity_name,
                country_of_incorporation=country_code,
                confidence_pct=0.0
            )

    async def check_director(self, director_name: str, countries: List[str]) -> Dict[str, RegistryMatch]:
        """Check director involvement across multiple national registries"""
        results = {}
        for country in countries:
            # Mock cross-registry search
            results[country] = await self.lookup_entity(director_name, country)
        return results

    async def verify_ownership_chain(
        self,
        shipper: str,
        shipper_country: str,
        parent_entity: Optional[str] = None,
        parent_country: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Verify complete ownership chain from shipper to ultimate beneficial owner.
        Returns structured ownership proof.
        """
        results = {
            "shipper": await self.lookup_entity(shipper, shipper_country),
            "chain_valid": False,
            "confidence_pct": 0.0,
            "shared_directors": [],
            "shared_agents": []
        }

        if parent_entity and parent_country:
            parent_match = await self.lookup_entity(parent_entity, parent_country)
            results["parent"] = parent_match

            # Check for director overlap
            if results["shipper"].found and parent_match.found:
                shipper_directors = {d["name"].lower() for d in results["shipper"].directors}
                parent_directors = {d["name"].lower() for d in parent_match.directors}
                results["shared_directors"] = list(shipper_directors & parent_directors)
                results["chain_valid"] = len(results["shared_directors"]) > 0
                if results["chain_valid"]:
                    results["confidence_pct"] = 85.0

        return results

    def _assess_risk_flags(
        self,
        entity_name: str,
        incorporation_date: Optional[str],
        directors: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Assess risk flags based on incorporation date, directors, and other factors
        """
        flags = []

        # Check incorporation recency
        if incorporation_date:
            try:
                incorp_date = dateutil_parser.parse(incorporation_date)
                days_old = (datetime.utcnow() - incorp_date).days
                if days_old < 180:
                    flags.append(f"Recently incorporated ({days_old} days ago)")
            except:
                pass

        # Check for suspicious patterns in company name
        if any(x in entity_name.lower() for x in ["trading", "export", "import", "global", "international"]):
            flags.append("Generic trading company name pattern")

        # Check director countries
        director_countries = {d.get("nationality", "Unknown") for d in directors if d.get("nationality")}
        if "CN" in director_countries and len(director_countries) == 1:
            flags.append("All directors from same high-risk country (CN)")

        return flags

    async def _lookup_opencorporates(
        self,
        entity_name: str,
        country_code: str
    ) -> RegistryMatch:
        """
        Call real OpenCorporates API when available.
        Production: Replace with actual OpenCorporates REST API
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.opencorporates_url}/companies/search",
                    params={
                        "q": entity_name,
                        "country_code": country_code,
                        "per_page": 1
                    },
                    timeout=self.timeout
                )
                if response.status_code == 200:
                    data = response.json()
                    results = data.get("results", {}).get("companies", [])
                    if results:
                        company = results[0]
                        return RegistryMatch(
                            found=True,
                            entity_name=company.get("name"),
                            country_of_incorporation=country_code,
                            registration_number=company.get("company_number"),
                            incorporation_date=company.get("incorporation_date"),
                            status=company.get("status", "active"),
                            company_type=company.get("company_type"),
                            confidence_pct=90.0
                        )
        except Exception as e:
            logger.warning(f"OpenCorporates API error: {e}")

        return RegistryMatch(
            found=False,
            entity_name=entity_name,
            country_of_incorporation=country_code,
            confidence_pct=0.0
        )


# Global service instance
registry_service = RegistryService()
