"""
Implementation tests for 4-tier ML scoring pipeline (GREEN phase).

These tests verify that the scoring implementation produces expected results
for the Greenfield test case fixture.
"""

import pytest
from services.scoring.tier1_senzing import Tier1Scorer
from services.scoring.tier2_isolation_forest import Tier2Scorer
from services.scoring.tier3_lgbm import Tier3Scorer
from services.scoring.tier4_bbn import Tier4Scorer
from services.scoring.service import ScoringService
from services.scoring.aggregator import ScoreAggregator


class TestTier1Implementation:
    """Test Tier 1 Senzing entity chain scorer"""

    def test_tier1_party_profile_risk_for_greenfield(self, greenfield_entities):
        """Greenfield case should score 15/15"""
        scorer = Tier1Scorer()
        score = scorer.score(greenfield_entities)

        assert isinstance(score, float)
        assert 14.0 <= score <= 15.0, f"Expected 14-15, got {score}"

    def test_tier1_score_0_when_no_entities(self):
        """Empty entities should score 0"""
        scorer = Tier1Scorer()
        score = scorer.score({})
        assert score == 0.0

    def test_tier1_score_no_parent(self):
        """Shipper with no parent should score lower"""
        scorer = Tier1Scorer()
        entities = {
            "shipper_vn": {
                "match_confidence": 0.85,
            }
        }
        score = scorer.score(entities)
        assert 0 < score < 10  # Lower than Greenfield's 15


class TestTier2Implementation:
    """Test Tier 2 Isolation Forest anomaly scorer"""

    def test_tier2_routing_consistency_for_greenfield(self, greenfield_manifest):
        """Greenfield case should score 14/15"""
        scorer = Tier2Scorer()
        score = scorer.score(greenfield_manifest)

        assert isinstance(score, float)
        assert 13.5 <= score <= 15.0, f"Expected 13.5-15, got {score}"

    def test_tier2_score_0_for_no_dwell_data(self):
        """No dwell data should score 0"""
        scorer = Tier2Scorer()
        manifest = {}
        score = scorer.score(manifest)
        assert score == 0.0

    def test_tier2_score_low_for_normal_dwell(self):
        """Normal dwell (1.5x baseline) should score low"""
        scorer = Tier2Scorer()
        manifest = {
            "ais_dwell_days": 3.0,
            "ais_dwell_baseline": 2.1,
        }
        score = scorer.score(manifest)
        assert 0 < score <= 2.0


class TestTier3Implementation:
    """Test Tier 3 LightGBM commodity + pattern scorer"""

    def test_tier3_commodity_sensitivity_for_greenfield(self, greenfield_manifest):
        """Greenfield aluminum should score 14/15"""
        scorer = Tier3Scorer()
        commodity_score, _ = scorer.score(greenfield_manifest)

        assert isinstance(commodity_score, float)
        assert 13.0 <= commodity_score <= 15.0, f"Expected 13-15, got {commodity_score}"

    def test_tier3_historical_pattern_for_greenfield(self, greenfield_manifest):
        """Greenfield origin shift should score 12/15"""
        scorer = Tier3Scorer()
        _, pattern_score = scorer.score(greenfield_manifest)

        assert isinstance(pattern_score, float)
        assert 10.0 <= pattern_score <= 15.0, f"Expected 10-15, got {pattern_score}"

    def test_tier3_low_duty_commodity(self):
        """Low-duty commodity should score low"""
        scorer = Tier3Scorer()
        manifest = {
            "hts_code": "1701",
            "hts_duty_rate_pct": 15,
            "ad_cvd_status": "INACTIVE",
        }
        commodity_score, _ = scorer.score(manifest)
        assert commodity_score <= 5


class TestTier4Implementation:
    """Test Tier 4 BBN origin fraud + time sensitivity"""

    def test_tier4_origin_doc_gap_for_greenfield(self, greenfield_manifest, greenfield_entities):
        """Greenfield ISF mismatch should score 23/25"""
        scorer = Tier4Scorer()
        origin_gap, _, _ = scorer.score(greenfield_manifest, greenfield_entities)

        assert isinstance(origin_gap, float)
        assert 20.0 <= origin_gap <= 25.0, f"Expected 20-25, got {origin_gap}"

    def test_tier4_time_sensitivity_for_greenfield(self, greenfield_manifest, greenfield_entities):
        """Greenfield time window should score 13/15"""
        scorer = Tier4Scorer()
        _, time_sens, _ = scorer.score(greenfield_manifest, greenfield_entities)

        assert isinstance(time_sens, float)
        assert 10.0 <= time_sens <= 15.0, f"Expected 10-15, got {time_sens}"

    def test_tier4_returns_posteriors(self, greenfield_manifest, greenfield_entities):
        """BBN should return posterior probabilities"""
        scorer = Tier4Scorer()
        _, _, posteriors = scorer.score(greenfield_manifest, greenfield_entities)

        assert isinstance(posteriors, dict)
        assert "origin_doc_fraudulent" in posteriors
        assert "time_critical" in posteriors
        assert 0 <= posteriors["origin_doc_fraudulent"] <= 1


class TestScoringAggregation:
    """Test final score aggregation"""

    def test_aggregation_sums_correctly(self):
        """Aggregator should sum components correctly"""
        aggregator = ScoreAggregator()

        response = aggregator.aggregate(
            tier1_score=15.0,
            tier2_score=14.0,
            tier3_commodity=14.0,
            tier3_pattern=12.0,
            tier4_origin=23.0,
            tier4_time=13.0,
            manifest={},
            entities={},
        )

        assert response.total_score == 91.0

    def test_aggregation_confidence_tier_high(self):
        """Score 91 should be HIGH confidence"""
        aggregator = ScoreAggregator()

        response = aggregator.aggregate(
            tier1_score=15.0,
            tier2_score=14.0,
            tier3_commodity=14.0,
            tier3_pattern=12.0,
            tier4_origin=23.0,
            tier4_time=13.0,
            manifest={},
            entities={},
        )

        assert response.confidence_tier == "HIGH"

    def test_aggregation_confidence_tier_medium(self):
        """Score 50 should be MEDIUM confidence"""
        aggregator = ScoreAggregator()

        response = aggregator.aggregate(
            tier1_score=10.0,
            tier2_score=10.0,
            tier3_commodity=8.0,
            tier3_pattern=7.0,
            tier4_origin=8.0,
            tier4_time=7.0,
            manifest={},
            entities={},
        )

        assert response.confidence_tier == "MEDIUM"

    def test_aggregation_confidence_tier_low(self):
        """Score 20 should be LOW confidence"""
        aggregator = ScoreAggregator()

        response = aggregator.aggregate(
            tier1_score=3.0,
            tier2_score=3.0,
            tier3_commodity=3.0,
            tier3_pattern=3.0,
            tier4_origin=4.0,
            tier4_time=1.0,
            manifest={},
            entities={},
        )

        assert response.confidence_tier == "LOW"

    def test_aggregation_generates_components(self):
        """Aggregator should generate component list"""
        aggregator = ScoreAggregator()

        response = aggregator.aggregate(
            tier1_score=15.0,
            tier2_score=14.0,
            tier3_commodity=14.0,
            tier3_pattern=12.0,
            tier4_origin=23.0,
            tier4_time=13.0,
            manifest={},
            entities={},
        )

        assert len(response.components) == 6
        assert response.components[0].name == "Origin Doc Gap"
        assert response.components[1].name == "Commodity Sensitivity"
        assert response.components[2].name == "Routing Consistency"
        assert response.components[3].name == "Party Profile Risk"
        assert response.components[4].name == "Historical Pattern"
        assert response.components[5].name == "Time Sensitivity"


class TestEndToEndScoring:
    """End-to-end scoring pipeline tests"""

    def test_score_greenfield_manifest_end_to_end(
        self, greenfield_manifest, greenfield_entities, greenfield_score_breakdown
    ):
        """Full pipeline should score Greenfield at 91/100"""
        service = ScoringService()
        response = service.score_shipment(greenfield_manifest, greenfield_entities)

        assert response.total_score == 91.0
        assert response.confidence_tier == "HIGH"
        assert len(response.components) == 6

    def test_score_includes_all_component_narratives(
        self, greenfield_manifest, greenfield_entities
    ):
        """Each component should include description"""
        service = ScoringService()
        response = service.score_shipment(greenfield_manifest, greenfield_entities)

        for component in response.components:
            assert component.description
            assert len(component.description) > 0

    def test_score_includes_xai_assertions(
        self, greenfield_manifest, greenfield_entities
    ):
        """Response should include XAI assertions"""
        service = ScoringService()
        response = service.score_shipment(greenfield_manifest, greenfield_entities)

        assert len(response.xai_assertions) >= 4
        for assertion in response.xai_assertions:
            assert assertion.text
            assert assertion.source

    def test_revenue_impact_calculation(
        self, greenfield_manifest, greenfield_entities
    ):
        """Should calculate estimated duty evasion amount"""
        service = ScoringService()
        response = service.score_shipment(greenfield_manifest, greenfield_entities)

        # Greenfield: 26,200 kg × ~$2.48/kg × 374% ≈ $2.1M
        assert response.revenue_impact_usd > 1500000
        assert response.revenue_impact_usd < 3000000


class TestScoringBoundaries:
    """Test score boundaries and edge cases"""

    def test_maximum_possible_score_is_100(self):
        """Max of all tiers should be 100"""
        aggregator = ScoreAggregator()

        response = aggregator.aggregate(
            tier1_score=15.0,
            tier2_score=15.0,
            tier3_commodity=15.0,
            tier3_pattern=15.0,
            tier4_origin=25.0,
            tier4_time=15.0,
            manifest={},
            entities={},
        )

        assert response.total_score == 100.0

    def test_minimum_possible_score_is_0(self):
        """Min of all tiers should be 0"""
        aggregator = ScoreAggregator()

        response = aggregator.aggregate(
            tier1_score=0.0,
            tier2_score=0.0,
            tier3_commodity=0.0,
            tier3_pattern=0.0,
            tier4_origin=0.0,
            tier4_time=0.0,
            manifest={},
            entities={},
        )

        assert response.total_score == 0.0

    def test_score_never_exceeds_100(self):
        """Score should be capped at 100"""
        aggregator = ScoreAggregator()

        response = aggregator.aggregate(
            tier1_score=20.0,  # Over max
            tier2_score=20.0,  # Over max
            tier3_commodity=20.0,  # Over max
            tier3_pattern=20.0,  # Over max
            tier4_origin=30.0,  # Over max
            tier4_time=20.0,  # Over max
            manifest={},
            entities={},
        )

        assert response.total_score <= 100.0
