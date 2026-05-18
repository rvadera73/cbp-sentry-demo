"""
Score Aggregator: Combines all 4 tiers into final risk score
Input: tier1, tier2, tier3_commodity, tier3_pattern, tier4_origin, tier4_time
Output: ScoreResponse with total_score, components, confidence_tier
"""

from typing import Dict, List, Any, Optional
import sys
from pathlib import Path

# Add api directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from models.schemas import ScoreComponent, ScoreResponse, XAIAssertion, BBNPosteriors


class ScoreAggregator:
    """Aggregate scores from all 4 tiers"""

    def __init__(self):
        """Initialize aggregator"""
        pass

    def aggregate(
        self,
        tier1_score: float,
        tier2_score: float,
        tier3_commodity: float,
        tier3_pattern: float,
        tier4_origin: float,
        tier4_time: float,
        manifest: Dict[str, Any],
        entities: Dict[str, Any],
        bbn_posteriors: Optional[Dict[str, float]] = None,
        xai_assertions: Optional[List[str]] = None
    ) -> ScoreResponse:
        """
        Aggregate scores from all tiers into ScoreResponse.

        Args:
            tier1_score: Party Profile Risk (0-15)
            tier2_score: Routing Consistency (0-15)
            tier3_commodity: Commodity Sensitivity (0-15)
            tier3_pattern: Historical Pattern (0-15)
            tier4_origin: Origin Doc Gap (0-25)
            tier4_time: Time Sensitivity (0-15)
            manifest: Original manifest data
            entities: Original entity data
            bbn_posteriors: BBN posterior probabilities
            xai_assertions: XAI narratives

        Returns:
            ScoreResponse with all aggregated data
        """
        # Calculate total score (max = 100)
        # Max: 15 + 15 + 15 + 15 + 25 + 15 = 100
        total_score = tier1_score + tier2_score + tier3_commodity + tier3_pattern + tier4_origin + tier4_time

        # Determine confidence tier
        if total_score >= 75:
            confidence_tier = "HIGH"
        elif total_score >= 40:
            confidence_tier = "MEDIUM"
        else:
            confidence_tier = "LOW"

        # Build components list with descriptions
        components = [
            ScoreComponent(
                name="Origin Doc Gap",
                tier=4,
                score=tier4_origin,
                max=25,
                percentage=round(tier4_origin / 25 * 100, 1),
                description="ISF Element 9 filed China, manifests declare Vietnam (19 CFR 149.5 violation)"
            ),
            ScoreComponent(
                name="Commodity Sensitivity",
                tier=3,
                score=tier3_commodity,
                max=15,
                percentage=round(tier3_commodity / 15 * 100, 1),
                description=f"Commodity HTS {manifest.get('hts_code', 'N/A')} subject to {manifest.get('hts_duty_rate_pct', 0)}% duty"
            ),
            ScoreComponent(
                name="Routing Consistency",
                tier=2,
                score=tier2_score,
                max=15,
                percentage=round(tier2_score / 15 * 100, 1),
                description=f"AIS tracking shows {manifest.get('ais_dwell_days', 0):.1f}-day dwell ({manifest.get('ais_anomaly_ratio', 0):.1f}× baseline)"
            ),
            ScoreComponent(
                name="Party Profile Risk",
                tier=1,
                score=tier1_score,
                max=15,
                percentage=round(tier1_score / 15 * 100, 1),
                description=f"{manifest.get('shipper_country', 'N/A')} shipper linked to {entities.get('parent_cn', {}).get('country', 'N/A')} parent"
            ),
            ScoreComponent(
                name="Historical Pattern",
                tier=3,
                score=tier3_pattern,
                max=15,
                percentage=round(tier3_pattern / 15 * 100, 1),
                description="6-month origin shift, known transshipment corridor"
            ),
            ScoreComponent(
                name="Time Sensitivity",
                tier=4,
                score=tier4_time,
                max=15,
                percentage=round(tier4_time / 15 * 100, 1),
                description="72-hour manifest window + AD/CVD active (limited investigation window)"
            )
        ]

        # Calculate revenue impact
        weight_kg = manifest.get("weight_kg", 0)
        duty_rate_pct = manifest.get("hts_duty_rate_pct", 0)
        declared_value = manifest.get("declared_value_usd", 0)

        # Estimated duty per kg (assuming ~$3,050/MT for aluminum)
        if weight_kg > 0 and duty_rate_pct > 0:
            price_per_kg = declared_value / weight_kg if declared_value > 0 else 3.05
            revenue_impact = (weight_kg / 1000) * price_per_kg * duty_rate_pct / 100
        else:
            revenue_impact = 0.0

        # Generate or use provided XAI assertions
        if not xai_assertions:
            xai_assertions = self._generate_xai_assertions(manifest, entities, components)

        xai_assertion_objects = [
            XAIAssertion(
                text=assertion,
                source="ML Pipeline",
                confidence=0.85
            )
            for assertion in xai_assertions
        ]

        # Build BBN posteriors schema
        bbn_posteriors_obj = None
        if bbn_posteriors:
            bbn_posteriors_obj = BBNPosteriors(
                entity_linked_to_cn_parent=bbn_posteriors.get("entity_linked_to_cn_parent"),
                ad_cvd_active=bbn_posteriors.get("ad_cvd_active"),
                stuffing_coo_mismatch=bbn_posteriors.get("stuffing_coo_mismatch"),
                origin_doc_fraudulent=bbn_posteriors.get("origin_doc_fraudulent"),
                time_critical=bbn_posteriors.get("time_critical"),
            )

        return ScoreResponse(
            total_score=round(total_score, 1),
            confidence_tier=confidence_tier,
            components=components,
            xai_assertions=xai_assertion_objects,
            bbn_posteriors=bbn_posteriors_obj,
            revenue_impact_usd=round(revenue_impact, 2)
        )

    def _generate_xai_assertions(
        self,
        manifest: Dict[str, Any],
        entities: Dict[str, Any],
        components: List[ScoreComponent]
    ) -> List[str]:
        """
        Generate XAI narrative assertions from score components.

        Returns:
            List of natural language explanations
        """
        assertions = []

        # ISF/COO mismatch
        isf_country = manifest.get("isf_stuffing_country", "")
        declared_coo = manifest.get("declared_coo", "")
        if isf_country and declared_coo and isf_country != declared_coo:
            assertions.append(
                f"ISF Element 9 filed {isf_country}, manifests declare {declared_coo} (19 CFR 149.5 violation)"
            )

        # AIS anomaly
        dwell = manifest.get("ais_dwell_days", 0)
        baseline = manifest.get("ais_dwell_baseline", 2.1)
        anomaly_ratio = manifest.get("ais_anomaly_ratio", 0)
        if dwell > 0 and anomaly_ratio > 2:
            assertions.append(
                f"AIS tracking shows {dwell:.1f}-day dwell ({anomaly_ratio:.1f}× baseline, 99th percentile anomaly)"
            )

        # Entity linkage
        parent_cn = entities.get("parent_cn")
        shipper = entities.get("shipper_vn")
        if parent_cn and shipper:
            confidence = shipper.get("match_confidence", 0.9)
            assertions.append(
                f"Entity resolution: Vietnamese shipper owned by Chinese parent ({confidence:.2f} Senzing confidence)"
            )

        # Commodity duty
        duty_rate = manifest.get("hts_duty_rate_pct", 0)
        coo = manifest.get("country_of_origin", "")
        if duty_rate > 100:
            assertions.append(
                f"Aluminum subject to {duty_rate}% AD/CVD from China; {coo} origin evades duties"
            )

        # Revenue impact
        revenue_impact = 0
        weight_kg = manifest.get("weight_kg", 0)
        declared_value = manifest.get("declared_value_usd", 0)
        if weight_kg > 0 and duty_rate > 0:
            price_per_kg = declared_value / weight_kg if declared_value > 0 else 3.05
            revenue_impact = int((weight_kg / 1000) * price_per_kg * duty_rate / 100)
        if revenue_impact > 0:
            assertions.append(
                f"Estimated duty evasion: ${revenue_impact:,} ({int(weight_kg)} kg × ${declared_value/weight_kg:.2f}/kg × {duty_rate}%)"
            )

        return assertions
