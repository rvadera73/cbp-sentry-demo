"""HTS Industry Segment Classification Engine

Maps 6-digit HTS codes to high-risk industry segments with known evasion origins.
Data source: CBP research on priority trade corridors (pp. 2-3)
"""

import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class HTSIndustryClassifier:
    """Classifies HTS codes into high-risk industry segments.

    Maintains mapping of HTS chapters to industry segments with:
    - AD/CVD countries of interest
    - Known evasion origin shifts (transshipment routes)
    - Baseline annual production capacity
    """

    # HTS Chapter → Industry Segment mapping (CBP priority corridors)
    INDUSTRY_MAP = {
        "8541": {
            "segment": "Solar Infrastructure",
            "chapters": ["8541.40.60", "8541.40.80"],
            "ad_cvd_countries": ["CN", "VN", "TH", "MY"],
            "known_evasion_origin_shifts": [
                ("CN", ["VN", "MY", "TH", "KH"]),  # CN manufacturers divert via ASEAN
            ],
            "baseline_annual_capacity_tons": 2_500_000,
        },
        "7604": {
            "segment": "Industrial Aluminum",
            "chapters": ["7604.10", "7604.29"],
            "ad_cvd_countries": ["CN", "VN", "RU"],
            "known_evasion_origin_shifts": [
                ("CN", ["VN", "MY", "TH"]),  # CN aluminum transships via Vietnam
            ],
            "baseline_annual_capacity_tons": 1_200_000,
        },
        "7210": {
            "segment": "Flat-Rolled Steel & Alloys",
            "chapters": ["7210.70", "7212.30"],
            "ad_cvd_countries": ["CN", "VN", "RU"],
            "known_evasion_origin_shifts": [
                ("CN", ["VN", "MY", "IN"]),  # CN steel transships via Vietnam, Malaysia, India
            ],
            "baseline_annual_capacity_tons": 3_500_000,
        },
        "6204": {
            "segment": "Textiles & Apparel",
            "chapters": ["6204.00"],
            "ad_cvd_countries": ["CN", "IN", "VN", "BD"],
            "known_evasion_origin_shifts": [
                ("CN", ["VN", "KH", "MM"]),  # Textile transshipment via ASEAN
                ("IN", ["BN", "SG"]),
            ],
            "baseline_annual_capacity_tons": 500_000,
        },
        "2714": {
            "segment": "Petroleum Refinery Products",
            "chapters": ["2714.10", "2714.90"],
            "ad_cvd_countries": ["RU", "IR", "VE"],
            "known_evasion_origin_shifts": [
                ("RU", ["SG", "MY", "AE"]),  # Russian oil/products via Singapore transshipment
            ],
            "baseline_annual_capacity_tons": 5_000_000,
        },
    }

    # AD/CVD duty rates by HTS + origin country (source: USITC)
    DUTY_RATES_MAP = {
        ("8541", "CN"): 100.0,
        ("8541", "VN"): 100.0,
        ("8541", "MY"): 100.0,
        ("7604", "CN"): 374.15,
        ("7604", "VN"): 374.15,
        ("7604", "RU"): 374.15,
        ("7210", "CN"): 156.0,
        ("7210", "VN"): 156.0,
        ("7210", "RU"): 156.0,
        ("6204", "CN"): 25.0,
        ("6204", "IN"): 20.0,
        ("6204", "VN"): 25.0,
    }

    def classify_hts_to_segment(self, hts_code: str) -> Dict:
        """Map 6-digit HTS code to industry segment.

        Args:
            hts_code: 6-digit HTS code (string or int)

        Returns:
            Dict with keys:
                - segment: High-risk industry name
                - chapters: Matching chapter codes
                - ad_cvd_countries: Countries under AD/CVD
                - known_evasion_origin_shifts: [(origin, [alternatives])]
                - baseline_annual_capacity_tons: Production capacity
        """
        hts_str = str(hts_code)[:4]  # Take first 4 digits

        if hts_str in self.INDUSTRY_MAP:
            return self.INDUSTRY_MAP[hts_str]

        # Return generic classification for non-priority HTS
        return {
            "segment": "General Merchandise",
            "chapters": [hts_str],
            "ad_cvd_countries": [],
            "known_evasion_origin_shifts": [],
            "baseline_annual_capacity_tons": 10_000_000,
        }

    def get_evasion_origin_shifts(self, hts_code: str, origin_country: str) -> List[str]:
        """Return known transshipment alternatives for HTS + origin pair.

        E.g., if HTS 8541 from CN, returns ["VN", "MY", "TH", "KH"]
        indicating China's typical transshipment routes via ASEAN.

        Args:
            hts_code: 6-digit HTS code
            origin_country: Declared origin country (ISO 2-letter code)

        Returns:
            List of suspect alternative origins
        """
        segment = self.classify_hts_to_segment(hts_code)
        shifts = []

        for primary_origin, suspect_origins in segment.get("known_evasion_origin_shifts", []):
            if origin_country == primary_origin:
                shifts = suspect_origins
                break

        return shifts

    def get_ad_cvd_countries(self, hts_code: str) -> List[str]:
        """Return all countries with active AD/CVD on this HTS code.

        Args:
            hts_code: 6-digit HTS code

        Returns:
            List of country codes under AD/CVD
        """
        segment = self.classify_hts_to_segment(hts_code)
        return segment.get("ad_cvd_countries", [])

    def lookup_ad_cvd_rate(self, hts_code: str, origin_country: str) -> float:
        """Lookup AD/CVD duty rate for HTS + origin pair.

        Args:
            hts_code: 6-digit HTS code
            origin_country: Country code (ISO 2-letter)

        Returns:
            Duty rate as percentage, or 0.0 if no rate found
        """
        hts_4digit = str(hts_code)[:4]
        rate = self.DUTY_RATES_MAP.get((hts_4digit, origin_country), 0.0)
        return rate

    def is_high_risk_hts(self, hts_code: str) -> bool:
        """Determine if HTS code is in high-risk priority list.

        Args:
            hts_code: 6-digit HTS code

        Returns:
            True if in INDUSTRY_MAP, False otherwise
        """
        hts_4digit = str(hts_code)[:4]
        return hts_4digit in self.INDUSTRY_MAP

    def get_baseline_capacity_tons(self, hts_code: str) -> float:
        """Get annual production capacity for HTS code.

        Args:
            hts_code: 6-digit HTS code

        Returns:
            Baseline annual capacity in metric tons
        """
        segment = self.classify_hts_to_segment(hts_code)
        return segment.get("baseline_annual_capacity_tons", 10_000_000)
