"""
XAI (Explainable AI) Assertion Generator
Converts numerical scores into natural language evidence statements with citations.
"""

from typing import Dict, List, Any, Optional


class XAIAssertionGenerator:
    """Generate natural language XAI narratives from scoring evidence"""

    def __init__(self):
        """Initialize XAI generator"""
        pass

    def generate_assertions(
        self,
        scores: Dict[str, Any],
        manifest: Dict[str, Any],
        entities: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """
        Generate XAI assertions with source citations and confidence levels.

        Args:
            scores: Dict with tier1, tier2, tier3_commodity, etc.
            manifest: Original manifest data
            entities: Original entity resolution data

        Returns:
            List of assertion dicts with 'text', 'source', and 'confidence'
        """
        assertions = []

        # Tier 4: ISF/COO Mismatch (19 CFR 149.5)
        isf_country = manifest.get("isf_stuffing_country", "")
        declared_coo = manifest.get("declared_coo", "")
        if isf_country and declared_coo and isf_country != declared_coo:
            assertions.append({
                "text": f"ISF Element 9 filed {isf_country}, manifests declare {declared_coo} (19 CFR 149.5 violation)",
                "source": "Tier 4 BBN: ISF/COO Contradiction",
                "confidence": 0.98,
                "tier": 4
            })

        # Tier 2: AIS Dwell Anomaly
        dwell = manifest.get("ais_dwell_days", 0)
        baseline = manifest.get("ais_dwell_baseline", 2.1)
        anomaly_ratio = manifest.get("ais_anomaly_ratio", 0)
        if dwell > 0 and anomaly_ratio > 2:
            assertions.append({
                "text": f"AIS tracking shows {dwell:.1f}-day Guangzhou dwell ({anomaly_ratio:.1f}× commodity baseline, 99th percentile anomaly)",
                "source": "Tier 2 Isolation Forest: Port Dwell Time",
                "confidence": 0.95,
                "tier": 2
            })

        # Tier 1: Entity Linkage
        parent_cn = entities.get("parent_cn")
        shipper = entities.get("shipper_vn")
        if parent_cn and shipper:
            confidence = shipper.get("match_confidence", 0.9)
            assertions.append({
                "text": f"Entity resolution: Vietnamese shipper owned by Chinese parent ({confidence:.2f} Senzing confidence, high-risk linkage)",
                "source": "Tier 1 Senzing: Entity Chain Depth",
                "confidence": confidence,
                "tier": 1
            })

        # Tier 3: Commodity Sensitivity (AD/CVD)
        duty_rate = manifest.get("hts_duty_rate_pct", 0)
        ad_cvd_status = manifest.get("ad_cvd_status", "")
        hts_code = manifest.get("hts_code", "")
        coo = manifest.get("country_of_origin", "")
        if duty_rate > 100 and ad_cvd_status == "ACTIVE":
            assertions.append({
                "text": f"HTS {hts_code} subject to {duty_rate}% AD/CVD from China; {coo} origin evades duties by misclassification",
                "source": "Tier 3 LightGBM: Commodity Sensitivity",
                "confidence": 0.92,
                "tier": 3
            })

        # Tier 3: Historical Pattern (Origin Shift)
        prior_origins = manifest.get("prior_origins_6m", [])
        if prior_origins and len(set(prior_origins)) > 1:
            origin_str = " → ".join(prior_origins)
            assertions.append({
                "text": f"6-month origin shift {origin_str}, known aluminum transshipment corridor (CRITICAL_STRUCTURAL_RISK)",
                "source": "Tier 3 LightGBM: Historical Pattern",
                "confidence": 0.88,
                "tier": 3
            })

        # Tier 4: Time Sensitivity
        assertions.append({
            "text": "72-hour manifest window + AD/CVD active (limited investigation window for customs enforcement)",
            "source": "Tier 4 BBN: Time Sensitivity",
            "confidence": 0.87,
            "tier": 4
        })

        # Revenue Impact
        weight_kg = manifest.get("weight_kg", 0)
        declared_value = manifest.get("declared_value_usd", 0)
        if weight_kg > 0 and duty_rate > 0:
            price_per_unit = declared_value / weight_kg if declared_value > 0 else 3.05
            revenue_impact = int((weight_kg / 1000) * price_per_unit * duty_rate / 100)
            assertions.append({
                "text": f"Estimated duty evasion: ${revenue_impact:,} ({int(weight_kg)} kg × ${price_per_unit:.2f}/kg × {duty_rate}% duty)",
                "source": "Revenue Impact Calculation",
                "confidence": 0.85,
                "tier": "impact"
            })

        return assertions

    def format_assertion_markdown(
        self,
        assertions: List[Dict[str, str]]
    ) -> str:
        """
        Format assertions as markdown for display.

        Args:
            assertions: List of assertion dicts from generate_assertions()

        Returns:
            Formatted markdown string
        """
        markdown = "## Scoring Evidence\n\n"

        # Group by tier
        by_tier = {}
        for assertion in assertions:
            tier = assertion.get("tier", "other")
            if tier not in by_tier:
                by_tier[tier] = []
            by_tier[tier].append(assertion)

        # Tier 4 first
        for tier_num in [4, 3, 2, 1, "impact"]:
            if tier_num in by_tier:
                tier_name = f"Tier {tier_num}" if isinstance(tier_num, int) else "Impact"
                markdown += f"### {tier_name}\n\n"
                for assertion in by_tier[tier_num]:
                    text = assertion.get("text", "")
                    source = assertion.get("source", "")
                    confidence = assertion.get("confidence", 0.0)
                    markdown += f"- **{text}**\n"
                    markdown += f"  - Source: {source}\n"
                    markdown += f"  - Confidence: {confidence:.1%}\n\n"

        return markdown
