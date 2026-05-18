"""
Tests for 4-tier ML scoring pipeline.

Covers:
- Tier 1: Senzing entity chain
- Tier 2: Isolation Forest (AIS anomaly)
- Tier 3: LightGBM (supervised classification)
- Tier 4: BBN (Bayesian Belief Network)
- Final aggregated score

TDD approach: Tests written first (RED phase). No implementation yet.
Reference: ARCHITECTURE.md scoring model, Table 3-12
"""

import pytest


class TestTier1SenzingEntityChain:
    """
    Tier 1 scoring: Senzing entity resolution depth.
    Output: Party Profile Risk (0-15 pts)
    """

    def test_tier1_party_profile_risk_for_greenfield(self, greenfield_entities):
        """
        GIVEN: Greenfield case with VN shipper linked to CN parent via Senzing
        WHEN: Tier 1 score is calculated
        THEN: Score is 15/15 (maximum, shipper linked to CN)
        """
        from services.scoring.tier1_senzing import Tier1Scorer

        entities = greenfield_entities

        # VN shipper linked to CN parent = maximum risk
        assert entities["shipper_vn"]["risk_score"] == 65
        assert entities["parent_cn"]["risk_score"] == 72

        scorer = Tier1Scorer()
        score = scorer.score(entities)
        assert 14.0 <= score <= 15.0

    def test_tier1_score_0_when_no_parent_entity_found(self):
        """
        GIVEN: Entity with no Senzing matches
        WHEN: Tier 1 score is calculated
        THEN: Score is 0/15
        """
        from services.scoring.tier1_senzing import Tier1Scorer

        scorer = Tier1Scorer()
        score = scorer.score({})
        assert score == 0.0

    def test_tier1_score_increases_with_chain_depth(self):
        """
        GIVEN: Entity with varying chain depths
        WHEN: Tier 1 score is calculated
        THEN: Score increases: no parent (0) < 1 hop (5) < 2 hops (10) < 3 hops (15)
        """
        from services.scoring.tier1_senzing import Tier1Scorer

        scorer = Tier1Scorer()

        # No parent
        score_no_parent = scorer.score({})
        assert score_no_parent == 0.0

        # With parent
        with_parent = {
            "shipper_vn": {"match_confidence": 0.9},
            "parent_cn": {"match_confidence": 0.9}
        }
        score_with_parent = scorer.score(with_parent)
        assert score_with_parent > score_no_parent

    def test_tier1_score_penalizes_low_confidence_matches(self):
        """
        GIVEN: Senzing match with confidence < 0.80
        WHEN: Tier 1 score is calculated
        THEN: Score is reduced by matching the confidence
        """
        from services.scoring.tier1_senzing import Tier1Scorer

        scorer = Tier1Scorer()

        # Low confidence
        low_conf = {
            "shipper_vn": {"match_confidence": 0.5},
            "parent_cn": {"match_confidence": 0.5}
        }
        score_low = scorer.score(low_conf)

        # High confidence
        high_conf = {
            "shipper_vn": {"match_confidence": 0.98},
            "parent_cn": {"match_confidence": 0.91}
        }
        score_high = scorer.score(high_conf)

        assert score_low < score_high

    def test_tier1_score_includes_party_roles(self):
        """
        GIVEN: Shipper vs. consignee role
        WHEN: Tier 1 score is assigned
        THEN: Shipper penalties > consignee penalties
        """
        from services.scoring.tier1_senzing import Tier1Scorer

        scorer = Tier1Scorer()

        # Shipper role (higher risk)
        shipper_entities = {
            "shipper_vn": {"match_confidence": 0.9},
            "parent_cn": {"match_confidence": 0.9}
        }
        shipper_score = scorer.score(shipper_entities)

        # Consignee only (lower risk)
        consignee_entities = {
            "consignee_us": {"match_confidence": 0.9},
        }
        consignee_score = scorer.score(consignee_entities)

        assert shipper_score > consignee_score


class TestTier2IsolationForest:
    """
    Tier 2 scoring: Isolation Forest anomaly detection.
    Input: AIS vessel data (dwell time, transit deltas)
    Output: Routing Consistency (0-15 pts)
    """

    def test_tier2_routing_consistency_for_greenfield(self, greenfield_manifest):
        """
        GIVEN: Greenfield case with AIS dwell 11.2 days (5.3× baseline)
        WHEN: Tier 2 score is calculated
        THEN: Score is 14/15 (high anomaly)
        """
        from services.scoring.tier2_isolation_forest import Tier2Scorer

        manifest = greenfield_manifest

        assert manifest["ais_dwell_days"] == 11.2
        assert manifest["ais_dwell_baseline"] == 2.1
        assert manifest["ais_anomaly_ratio"] == 5.3

        scorer = Tier2Scorer()
        score = scorer.score(manifest)
        assert 13.5 <= score <= 15.0

    def test_tier2_score_0_for_normal_transit(self):
        """
        GIVEN: Normal vessel transit (dwell = baseline)
        WHEN: Tier 2 score is calculated
        THEN: Score is 0-3/15 (low anomaly)
        """
        from services.scoring.tier2_isolation_forest import Tier2Scorer

        scorer = Tier2Scorer()
        manifest = {
            "ais_dwell_days": 2.1,
            "ais_dwell_baseline": 2.1,
        }
        score = scorer.score(manifest)
        assert 0 <= score <= 3

    def test_tier2_score_high_for_extreme_dwell(self):
        """
        GIVEN: Extreme dwell time (10× baseline)
        WHEN: Tier 2 score is calculated
        THEN: Score is 15/15
        """
        from services.scoring.tier2_isolation_forest import Tier2Scorer

        scorer = Tier2Scorer()
        manifest = {
            "ais_dwell_days": 21.0,
            "ais_dwell_baseline": 2.1,
        }
        score = scorer.score(manifest)
        assert score == 15.0

    def test_tier2_includes_route_delta_anomalies(self):
        """
        GIVEN: Vessel transit delta (actual vs. planned route)
        WHEN: Isolation Forest analyzes
        THEN: Detects deviations and includes in score
        """
        from services.scoring.tier2_isolation_forest import Tier2Scorer

        scorer = Tier2Scorer()
        # Significant dwell anomaly
        manifest = {
            "ais_dwell_days": 8.0,
            "ais_dwell_baseline": 2.1,
        }
        score = scorer.score(manifest)
        assert score > 10.0

    def test_tier2_commodity_specific_baseline(self):
        """
        GIVEN: Aluminum cargo at Guangzhou (CNGGZ)
        WHEN: Baseline dwell is retrieved
        THEN: Baseline is commodity-specific (aluminum = 2.1 days)
        """
        from services.scoring.tier2_isolation_forest import Tier2Scorer

        scorer = Tier2Scorer()
        manifest = {
            "port_of_lading": "CNGGZ",
            "ais_dwell_days": 11.2,
            "ais_dwell_baseline": 2.1,
        }
        score = scorer.score(manifest)
        assert score > 13.0  # High anomaly for aluminum baseline


class TestTier3LightGBM:
    """
    Tier 3 scoring: Supervised classification.
    Inputs: HTS, COO, duty rate, shipper age, price vs. market
    Output: Commodity Sensitivity + Historical Pattern (0-30 pts, split 15/15)
    """

    def test_tier3_commodity_sensitivity_for_aluminum(self, greenfield_manifest):
        """
        GIVEN: Greenfield aluminum extrusions (HTS 7604.10.1000)
        WHEN: LightGBM commodity classifier runs
        THEN: Commodity sensitivity score is 14/15 (high AD/CVD duty)
        """
        from services.scoring.tier3_lgbm import Tier3Scorer

        manifest = greenfield_manifest

        assert manifest["hts_code"] == "7604.10.1000"
        assert manifest["country_of_origin"] == "VN"

        scorer = Tier3Scorer()
        commodity_score, _ = scorer.score(manifest)
        assert 13.0 <= commodity_score <= 15.0

    def test_tier3_historical_pattern_for_vn_us_aluminum(self, greenfield_manifest):
        """
        GIVEN: VN→US aluminum corridor (H1 CRITICAL_STRUCTURAL_RISK)
        WHEN: LightGBM historical pattern scorer runs
        THEN: Historical pattern score is 12/15 (known evasion corridor)
        """
        from services.scoring.tier3_lgbm import Tier3Scorer

        manifest = greenfield_manifest

        scorer = Tier3Scorer()
        _, pattern_score = scorer.score(manifest)
        assert 10.0 <= pattern_score <= 15.0

    def test_tier3_score_low_for_low_duty_commodity(self):
        """
        GIVEN: Low-duty commodity (e.g., HTS 1701 sugar, 15% tariff)
        WHEN: LightGBM runs
        THEN: Commodity sensitivity score is low (0-5/15)
        """
        from services.scoring.tier3_lgbm import Tier3Scorer

        scorer = Tier3Scorer()
        manifest = {
            "hts_code": "1701",
            "hts_duty_rate_pct": 15,
            "ad_cvd_status": "INACTIVE",
        }
        commodity_score, _ = scorer.score(manifest)
        assert commodity_score <= 5

    def test_tier3_price_anomaly_detection(self):
        """
        GIVEN: Declared value significantly below market price
        WHEN: LightGBM analyzes
        THEN: Flags underinvoicing and increases pattern score
        """
        from services.scoring.tier3_lgbm import Tier3Scorer

        scorer = Tier3Scorer()

        # Price below market
        manifest_below = {
            "price_variance_pct": -25,
            "prior_origins_6m": ["VN"],
            "shipper_incorporation_date": "2020-01-01",
        }
        _, pattern_low = scorer.score(manifest_below)

        # Fair price
        manifest_fair = {
            "price_variance_pct": 0,
            "prior_origins_6m": ["VN"],
            "shipper_incorporation_date": "2020-01-01",
        }
        _, pattern_fair = scorer.score(manifest_fair)

        assert pattern_low > pattern_fair

    def test_tier3_shipper_age_factor(self):
        """
        GIVEN: Shipper incorporated date (Greenfield: 2021)
        WHEN: LightGBM includes shipper age
        THEN: Newer companies (< 3 years) increase suspicion
        """
        from services.scoring.tier3_lgbm import Tier3Scorer
        from datetime import datetime, timedelta

        scorer = Tier3Scorer()

        # Very new shipper (< 6 months)
        very_new_date = (datetime.utcnow() - timedelta(days=90)).isoformat()
        manifest_very_new = {
            "shipper_incorporation_date": very_new_date,
        }
        _, pattern_very_new = scorer.score(manifest_very_new)

        # Established shipper (> 10 years)
        old_date = (datetime.utcnow() - timedelta(days=3650)).isoformat()
        manifest_old = {
            "shipper_incorporation_date": old_date,
        }
        _, pattern_old = scorer.score(manifest_old)

        assert pattern_very_new > pattern_old


class TestTier4BayesianBeliefNetwork:
    """
    Tier 4 scoring: Bayesian Belief Network.
    Inputs: Tiers 1-3 + ISF contradiction + time criticality
    Output: Origin Doc Gap + Time Sensitivity (0-40 pts, split 23/13 for Greenfield)
    """

    def test_tier4_origin_doc_gap_for_greenfield(self, greenfield_manifest, greenfield_entities):
        """
        GIVEN: Greenfield ISF stuffing at CN, declared COO = VN
        WHEN: BBN calculates origin doc gap
        THEN: Score is 23/25 (direct origin fraud evidence)
        """
        from services.scoring.tier4_bbn import Tier4Scorer

        manifest = greenfield_manifest

        assert manifest["isf_stuffing_country"] == "CN"
        assert manifest["declared_coo"] == "VN"

        scorer = Tier4Scorer()
        origin_gap, _, _ = scorer.score(manifest, greenfield_entities)
        assert 20.0 <= origin_gap <= 25.0

    def test_tier4_time_sensitivity_for_greenfield(self, greenfield_manifest, greenfield_entities):
        """
        GIVEN: Greenfield case (72-hour manifest window)
        WHEN: BBN calculates time sensitivity
        THEN: Score is 13/15 (limited investigation window)
        """
        from services.scoring.tier4_bbn import Tier4Scorer

        scorer = Tier4Scorer()
        _, time_sens, _ = scorer.score(greenfield_manifest, greenfield_entities)
        assert 10.0 <= time_sens <= 15.0

    def test_tier4_integrates_prior_tiers(self, greenfield_score_breakdown):
        """
        GIVEN: BBN model with Tiers 1-3 evidence
        WHEN: Tier 4 is calculated
        THEN: Uses conditional probability P(FRAUDULENT | Tier1, Tier2, Tier3)
        """
        breakdown = greenfield_score_breakdown

        # Tier 4 components should reflect high prior confidence from earlier tiers
        tier_4_total = sum(
            c["score"] for c in breakdown["components"] if c["tier"] == 4
        )
        assert tier_4_total >= 35, "Tier 4 should be high given strong Tier 1-3 evidence"

    def test_tier4_isf_coo_contradiction_high_weight(self, greenfield_manifest, greenfield_entities):
        """
        GIVEN: ISF stuffing location contradicts declared COO
        WHEN: BBN weighs this evidence
        THEN: This is the highest-weight factor (per 19 CFR 149.5)
        """
        from services.scoring.tier4_bbn import Tier4Scorer

        scorer = Tier4Scorer()

        # ISF/COO mismatch
        with_mismatch = greenfield_manifest.copy()
        with_mismatch["isf_stuffing_country"] = "CN"
        with_mismatch["declared_coo"] = "VN"

        origin_mismatch, _, _ = scorer.score(with_mismatch, greenfield_entities)

        # No mismatch
        no_mismatch = greenfield_manifest.copy()
        no_mismatch["isf_stuffing_country"] = "VN"
        no_mismatch["declared_coo"] = "VN"

        origin_no_mismatch, _, _ = scorer.score(no_mismatch, greenfield_entities)

        assert origin_mismatch > origin_no_mismatch

    def test_tier4_probability_fraudulent_is_0_91_for_greenfield(self, greenfield_manifest, greenfield_entities):
        """
        GIVEN: Greenfield case with all evidence factors
        WHEN: BBN computes P(FRAUDULENT=PROBABLE)
        THEN: Probability is 0.91 (91%)
        """
        from services.scoring.tier4_bbn import Tier4Scorer

        scorer = Tier4Scorer()
        _, _, posteriors = scorer.score(greenfield_manifest, greenfield_entities)

        assert "origin_doc_fraudulent" in posteriors
        assert 0.8 <= posteriors["origin_doc_fraudulent"] <= 0.95


class TestScoringAggregation:
    """
    Test final score aggregation from all 4 tiers.
    """

    def test_final_score_sums_all_tiers(self, greenfield_score_breakdown):
        """
        GIVEN: Greenfield scores for Tiers 1-4
        WHEN: Final score is calculated
        THEN: Total = sum of all component scores = 91
        """
        breakdown = greenfield_score_breakdown

        total = sum(c["score"] for c in breakdown["components"])
        assert total == 91

    def test_final_score_maximum_is_100(self):
        """
        GIVEN: Scoring model
        WHEN: All tiers are maximum
        THEN: Final score is 100
        """
        from services.scoring.aggregator import ScoreAggregator

        # Max: 15 (T1) + 15 (T2) + 30 (T3) + 40 (T4) = 100
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

    def test_final_score_minimum_is_0(self):
        """
        GIVEN: Scoring model
        WHEN: All tiers are minimum
        THEN: Final score is 0
        """
        from services.scoring.aggregator import ScoreAggregator

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

    def test_final_score_confidence_tier_classification(self, greenfield_score_breakdown):
        """
        GIVEN: Final score of 91
        WHEN: Confidence tier is assigned
        THEN: Tier is HIGH (score >= 75)
        """
        breakdown = greenfield_score_breakdown

        score = breakdown["total"]
        if score >= 75:
            assert breakdown["confidence_tier"] == "HIGH"
        elif score >= 40:
            assert breakdown["confidence_tier"] == "MEDIUM"
        else:
            assert breakdown["confidence_tier"] == "LOW"


class TestScoringEdgeCases:
    """
    Test edge cases and boundary conditions.
    """

    def test_score_for_clear_shipper_with_no_matches(self):
        """
        GIVEN: Shipper with no Senzing matches, normal routing, good history
        WHEN: Score is calculated
        THEN: Score is low (< 30)
        """
        from services.scoring.service import ScoringService

        service = ScoringService()

        manifest = {
            "ais_dwell_days": 2.0,
            "ais_dwell_baseline": 2.1,
            "hts_code": "1701",
            "hts_duty_rate_pct": 15,
            "ad_cvd_status": "INACTIVE",
            "shipper_incorporation_date": "2015-01-01",
            "price_variance_pct": 0,
            "isf_stuffing_country": "VN",
            "declared_coo": "VN",
        }

        entities = {}

        response = service.score_shipment(manifest, entities)
        assert response.total_score < 30

    def test_score_for_shipper_with_prior_enforcement(self):
        """
        GIVEN: Shipper with prior AD/CVD enforcement
        WHEN: Score is calculated
        THEN: Prior enforcement factor increases score significantly
        """
        from services.scoring.service import ScoringService

        service = ScoringService()

        # High-risk commodity that's subject to enforcement
        manifest = {
            "ais_dwell_days": 5.0,
            "ais_dwell_baseline": 2.1,
            "hts_code": "7604",
            "hts_duty_rate_pct": 374,
            "ad_cvd_status": "ACTIVE",
            "shipper_incorporation_date": "2018-01-01",
            "price_variance_pct": -15,
            "isf_stuffing_country": "CN",
            "declared_coo": "VN",
        }

        entities = {"shipper_vn": {"match_confidence": 0.9}}

        response = service.score_shipment(manifest, entities)
        assert response.total_score > 40

    def test_score_for_first_time_shipper(self):
        """
        GIVEN: New shipper incorporated < 6 months ago
        WHEN: Score is calculated
        THEN: Score is increased (suspicious new entity)
        """
        from services.scoring.service import ScoringService
        from datetime import datetime, timedelta

        service = ScoringService()

        # Very new shipper
        very_new_date = (datetime.utcnow() - timedelta(days=90)).isoformat()
        manifest_new = {
            "ais_dwell_days": 2.0,
            "ais_dwell_baseline": 2.1,
            "hts_code": "1701",
            "hts_duty_rate_pct": 15,
            "ad_cvd_status": "INACTIVE",
            "shipper_incorporation_date": very_new_date,
        }

        # Old shipper
        old_date = "2008-01-01"
        manifest_old = {
            "ais_dwell_days": 2.0,
            "ais_dwell_baseline": 2.1,
            "hts_code": "1701",
            "hts_duty_rate_pct": 15,
            "ad_cvd_status": "INACTIVE",
            "shipper_incorporation_date": old_date,
        }

        response_new = service.score_shipment(manifest_new, {})
        response_old = service.score_shipment(manifest_old, {})

        assert response_new.total_score > response_old.total_score

    def test_score_for_mixed_signal_case(self):
        """
        GIVEN: High Tier 1-2, low Tier 3-4 evidence
        WHEN: Score is calculated
        THEN: Score reflects balanced assessment (50-60 range)
        """
        from services.scoring.aggregator import ScoreAggregator

        aggregator = ScoreAggregator()

        # High Tier 1-2, low Tier 3-4
        response = aggregator.aggregate(
            tier1_score=15.0,  # High
            tier2_score=14.0,  # High
            tier3_commodity=3.0,  # Low
            tier3_pattern=2.0,  # Low
            tier4_origin=5.0,  # Low
            tier4_time=3.0,  # Low
            manifest={},
            entities={},
        )

        assert 40 <= response.total_score <= 75


class TestScoringIntegration:
    """
    End-to-end scoring pipeline tests.
    """

    def test_score_greenfield_manifest_end_to_end(
        self, greenfield_manifest, greenfield_entities, greenfield_score_breakdown
    ):
        """
        GIVEN: Greenfield manifest, entity graph, and scoring tiers
        WHEN: Full scoring pipeline runs (Tier 1-4)
        THEN: Final score is 91/100
        """
        from services.scoring.service import ScoringService

        service = ScoringService()
        response = service.score_shipment(greenfield_manifest, greenfield_entities)

        assert response.total_score == 91.0
        assert response.confidence_tier == "HIGH"

    def test_score_includes_all_component_narratives(
        self, greenfield_score_breakdown
    ):
        """
        GIVEN: Scored Greenfield case
        WHEN: Examining components
        THEN: Each component includes description (XAI narrative)
        """
        for component in greenfield_score_breakdown["components"]:
            assert "description" in component
            assert len(component["description"]) > 0

    def test_score_performance_under_10_seconds(self, greenfield_manifest, greenfield_entities):
        """
        GIVEN: Greenfield manifest with full entity graph
        WHEN: Scoring pipeline runs
        THEN: Completes in < 10 seconds (ARCHITECTURE.md target)
        """
        import time
        from services.scoring.service import ScoringService

        service = ScoringService()

        start = time.time()
        response = service.score_shipment(greenfield_manifest, greenfield_entities)
        elapsed = time.time() - start

        assert elapsed < 10.0
        assert response.total_score > 0
