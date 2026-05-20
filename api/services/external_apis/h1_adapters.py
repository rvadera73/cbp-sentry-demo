"""
Horizon 1 API Adapters — Corridor Risk Data (OpenCorporates, Comtrade, ITC Tariffs)
"""
import logging
from typing import Any, Dict
import json
from pathlib import Path
from services.external_apis.base_adapter import BaseAPIAdapter

logger = logging.getLogger(__name__)

FIXTURES_DIR = Path(__file__).parent / "fixtures"


class OpenCorporatesAdapter(BaseAPIAdapter):
    """OpenCorporates company lookup — shipper/consignee verification"""

    def __init__(self):
        super().__init__("opencorporates")

    async def fetch_live(self, company_name: str, jurisdiction: str = None) -> Dict[str, Any]:
        """Fetch company data from OpenCorporates API (free tier)"""
        # https://api.opencorporates.com/documentation/API-basics
        url = "https://api.opencorporates.com/v0.4/companies/search"
        params = {
            "q": company_name,
            "per_page": 5,
        }
        if jurisdiction:
            params["jurisdiction_code"] = jurisdiction

        try:
            result = await self.http_get(url, params=params)
            companies = result.get("results", {}).get("companies", [])

            if companies:
                company = companies[0]
                return self.add_data_source_metadata({
                    "name": company.get("name"),
                    "jurisdiction": company.get("jurisdiction_code"),
                    "incorporation_date": company.get("incorporation_date"),
                    "company_number": company.get("company_number"),
                    "company_type": company.get("company_type"),
                    "officers_url": company.get("officers_url"),
                    "found": True,
                })
            else:
                return self.add_data_source_metadata({"found": False, "error": "Company not found"})
        except Exception as e:
            logger.error(f"OpenCorporates live fetch failed: {e}")
            raise

    def fetch_fixture(self, company_name: str, jurisdiction: str = None) -> Dict[str, Any]:
        """Return fixture company data for demo"""
        fixtures = {
            "greenfield": {
                "name": "Greenfield Industrial Trading Co., Ltd.",
                "jurisdiction": "VN",
                "incorporation_date": "2018-03-15",
                "company_number": "0313999999",
                "company_type": "Limited Company",
                "found": True,
                "risk_flag": "SHIPPER_AGE_CONCERN",  # Founded 2018, suspicious
            },
            "sunpath": {
                "name": "SunPath Energy Distributors LLC",
                "jurisdiction": "US-NJ",
                "incorporation_date": "2015-06-22",
                "company_number": "123456789",
                "company_type": "LLC",
                "found": True,
                "risk_flag": None,
            },
            "guangdong": {
                "name": "Guangdong Greenfield Aluminum Manufacturing Co., Ltd.",
                "jurisdiction": "CN",
                "incorporation_date": "2010-01-10",
                "company_number": "91440101552999999",
                "company_type": "Limited Company",
                "found": True,
                "risk_flag": None,
            },
        }

        # Match by company name substring
        for key, fixture in fixtures.items():
            if key.lower() in company_name.lower():
                return self.add_data_source_metadata(fixture)

        return self.add_data_source_metadata({"found": False, "error": "Company not in fixture data"})


class ComtradeAdapter(BaseAPIAdapter):
    """UN Comtrade trade statistics — historical volumes and benchmarks"""

    def __init__(self):
        super().__init__("comtrade")

    async def fetch_live(self, hs_code: str, reporter: str, partner: str, year: int = 2024) -> Dict[str, Any]:
        """Fetch trade data from UN Comtrade API"""
        # https://comtradeplus.un.org/api
        url = "https://comtrade.un.org/api/get"
        params = {
            "type": "C",  # Classification
            "freq": "A",  # Annual
            "px": "HS",  # HS codes
            "ps": str(year),
            "r": reporter,
            "p": partner,
            "rg": "all",  # Import and export
            "cc": hs_code,
            "fmt": "json",
            "max": 50000,
        }

        try:
            result = await self.http_get(url, params=params)
            if result.get("data"):
                data = result["data"][0]
                return self.add_data_source_metadata({
                    "hs_code": hs_code,
                    "reporter": data.get("rtTitle"),
                    "partner": data.get("ptTitle"),
                    "trade_value_usd": data.get("TradeValue"),
                    "quantity": data.get("Qty"),
                    "unit": data.get("Unit"),
                    "year": year,
                    "found": True,
                })
            else:
                return self.add_data_source_metadata({"found": False})
        except Exception as e:
            logger.error(f"Comtrade live fetch failed: {e}")
            raise

    def fetch_fixture(self, hs_code: str, reporter: str, partner: str, year: int = 2024) -> Dict[str, Any]:
        """Return fixture trade data"""
        # Benchmark prices for common HS codes
        benchmarks = {
            "7604": {  # Aluminum extrusions
                "unit_price_per_kg": 3.50,
                "avg_shipment_kg": 15000,
                "annual_volume": 5000000,
                "flag": "PRICE_BELOW_MARKET" if reporter == "VN" and partner == "US" else None,
            },
            "8541": {  # Electronic components
                "unit_price_per_kg": 8.00,
                "avg_shipment_kg": 10000,
                "annual_volume": 3000000,
                "flag": None,
            },
        }

        hs_base = hs_code[:4] if hs_code else ""
        benchmark = benchmarks.get(hs_base, {"unit_price_per_kg": 5.00, "flag": None})

        return self.add_data_source_metadata({
            "hs_code": hs_code,
            "reporter": reporter,
            "partner": partner,
            "benchmark_unit_price_usd_per_kg": benchmark["unit_price_per_kg"],
            "avg_shipment_weight_kg": benchmark["avg_shipment_kg"],
            "annual_volume_kg": benchmark["annual_volume"],
            "pricing_flag": benchmark["flag"],
            "year": year,
            "found": True,
        })


class ITCTariffsAdapter(BaseAPIAdapter):
    """ITC Harmonized Tariff Schedule — AD/CVD duties and rates"""

    def __init__(self):
        super().__init__("itc_tariffs")

    async def fetch_live(self, hs_code: str, origin_country: str = None) -> Dict[str, Any]:
        """Fetch tariff rates from USITC DataWeb"""
        # USITC publishes HTS duty rates freely
        # https://dataweb.usitc.gov/
        # For now, we use fixture data as live access requires registration

        logger.warning("ITC live API requires registration - using fixture mode")
        return self.fetch_fixture(hs_code, origin_country)

    def fetch_fixture(self, hs_code: str, origin_country: str = None) -> Dict[str, Any]:
        """Return fixture tariff data with AD/CVD rates"""
        # Real AD/CVD cases from CBP
        duty_fixtures = {
            "7604": {  # Aluminum extrusions from China
                "CN": {"base_rate": 0.06, "ad_cv_rate": 3.7415, "total": 3.8015, "case": "AD/CVD from China"},
                "VN": {"base_rate": 0.06, "ad_cv_rate": 0.00, "total": 0.06, "case": "No duties"},
            },
            "8541": {  # Electronics
                "CN": {"base_rate": 0.00, "ad_cv_rate": 0.15, "total": 0.15, "case": "CVD only"},
                "VN": {"base_rate": 0.00, "ad_cv_rate": 0.00, "total": 0.00, "case": "No duties"},
            },
        }

        hs_base = hs_code[:4] if hs_code else ""
        duties = duty_fixtures.get(hs_base, {})
        duty_info = duties.get(origin_country, {"base_rate": 0.00, "ad_cv_rate": 0.00, "total": 0.00, "case": "Unknown"})

        return self.add_data_source_metadata({
            "hs_code": hs_code,
            "origin_country": origin_country,
            "base_rate": duty_info["base_rate"],
            "ad_cv_rate": duty_info["ad_cv_rate"],
            "total_effective_rate": duty_info["total"],
            "case_description": duty_info["case"],
            "found": True,
        })
