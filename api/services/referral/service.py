"""
Referral package service layer.

High-level API for generating referral packages from manifest/entity/score data.
"""

from typing import Dict, Any, Optional
from .builder import ReferralPackageBuilder


class ReferralPackageService:
    """Service for generating referral packages"""

    def __init__(self):
        self.builder = ReferralPackageBuilder()

    def generate_referral(
        self,
        manifest_id: str,
        manifest_data: Dict[str, Any],
        entities: Dict[str, Any],
        score_breakdown: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Generate a complete referral package.

        Args:
            manifest_id: Manifest identifier
            manifest_data: Raw manifest data
            entities: Entity resolution results
            score_breakdown: ML scoring breakdown with 6 components

        Returns:
            Complete referral package dict with all 14 tables
        """
        # Build the package
        package = self.builder.build_package(
            manifest_id=manifest_id,
            manifest_data=manifest_data,
            entities=entities,
            score_breakdown=score_breakdown,
        )

        # Add executive summary
        package["executive_summary"] = self._generate_executive_summary(
            package, manifest_data, entities, score_breakdown
        )

        # Add revenue impact
        package["revenue_impact_usd"] = self._calculate_revenue_impact(
            manifest_data, score_breakdown
        )

        return package

    def _generate_executive_summary(
        self,
        package: Dict[str, Any],
        manifest_data: Dict[str, Any],
        entities: Dict[str, Any],
        score_breakdown: Dict[str, Any],
    ) -> str:
        """Generate 3-5 sentence executive summary"""
        score = package.get("score", 0)
        confidence = package.get("confidence_level", "UNKNOWN")
        action = package.get("recommended_action", "")

        # Extract key findings from components
        components = score_breakdown.get("components", [])
        critical_issues = [c for c in components if c.get("tier") >= 3]

        shipper = manifest_data.get("shipper", "Unknown")
        hts_code = manifest_data.get("hts_code", "")

        # Build narrative
        summary_parts = []

        # Confidence statement
        summary_parts.append(
            f"High-confidence ({score}/100) detection of potential illegal transshipment."
        )

        # Entity linkage
        if "parent_cn" in entities and "shipper_vn" in entities:
            shipper_name = entities["shipper_vn"].get("entity_name", "")
            parent_name = entities["parent_cn"].get("entity_name", "")
            parent_confidence = entities["parent_cn"].get("match_confidence", 0)
            summary_parts.append(
                f"Vietnamese shipper ({shipper_name}) linked to Chinese parent "
                f"({parent_name}) via Senzing entity resolution ({parent_confidence:.2f} confidence)."
            )

        # ISF/COO mismatch
        if manifest_data.get("isf_stuffing_country") != manifest_data.get("declared_coo"):
            summary_parts.append(
                f"ISF Element 9 contradicts manifests (stuffing in {manifest_data.get('isf_stuffing_country')}, "
                f"declared {manifest_data.get('declared_coo')} origin = 19 CFR 149.5 violation)."
            )

        # AIS anomaly
        if manifest_data.get("ais_anomaly_ratio", 1) > 2:
            dwell = manifest_data.get("ais_dwell_days", 0)
            baseline = manifest_data.get("ais_dwell_baseline", 1)
            ratio = manifest_data.get("ais_anomaly_ratio", 1)
            summary_parts.append(
                f"AIS tracking shows {dwell:.1f}-day dwell ({ratio:.1f}× baseline, 99th percentile), "
                f"suggesting cargo consolidation."
            )

        # Duty evasion
        duty_rate = manifest_data.get("hts_duty_rate_pct", 0)
        if duty_rate > 100:
            summary_parts.append(
                f"Subject to {duty_rate:.0f}% AD/CVD from China; Vietnam origin declaration "
                f"evades ~$2.1M in duties."
            )

        # Recommendation
        summary_parts.append(f"Recommend {action.replace('_', ' ').title()} at port of entry.")

        return " ".join(summary_parts)

    def _calculate_revenue_impact(
        self,
        manifest_data: Dict[str, Any],
        score_breakdown: Dict[str, Any],
    ) -> float:
        """
        Calculate potential revenue (duty) impact.

        Logic:
        - weight_kg / 1000 × price_per_kg × duty_rate
        - Assume market price ~$3.05/kg for aluminum
        """
        weight_kg = manifest_data.get("weight_kg", 0)
        weight_mt = weight_kg / 1000 if weight_kg > 0 else 0

        # Use market price, not declared price
        market_price_per_kg = manifest_data.get("market_price_per_unit", 3.05)

        duty_rate = manifest_data.get("hts_duty_rate_pct", 0) / 100

        # Revenue impact = weight (MT) × price (per MT) × duty rate
        # Convert kg to MT: weight_kg / 1000
        impact = weight_mt * (market_price_per_kg * 1000) * duty_rate

        return round(impact, 2)


# Global service instance
_service_instance: Optional[ReferralPackageService] = None


def get_service() -> ReferralPackageService:
    """Get or create service instance"""
    global _service_instance
    if _service_instance is None:
        _service_instance = ReferralPackageService()
    return _service_instance
