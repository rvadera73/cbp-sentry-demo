"""
Tests for referral package generation.

Covers:
- Table 3-1 through 3-14 referral JSON structure
- Confidence score calculation (91/100 for Greenfield)
- 6-component breakdown sums to total
- XAI assertions presence and quality
- Revenue impact calculation
- Recommended action field

TDD approach: Tests written first (RED phase). No implementation yet.
Reference: ARCHITECTURE.md referral_packages schema
"""

import pytest
from datetime import datetime


class TestReferralPackageStructure:
    """
    Test that referral package matches expected JSON schema.
    Tables 3-1 through 3-14 from ARCHITECTURE.md
    """

    def test_referral_package_has_all_required_sections(
        self, greenfield_referral_package
    ):
        """
        GIVEN: Greenfield referral package
        WHEN: Package is generated
        THEN: All 13 required sections are present
        """
        package = greenfield_referral_package

        required_sections = [
            "package_id",
            "shipment_id",
            "confidence_level",
            "score",
            "recommended_action",
            "sections",
        ]

        for section in required_sections:
            assert section in package, f"Missing section: {section}"

        # Check nested sections (Tables 3-1 through 3-14)
        nested_sections = [
            "shipment_id",  # Table 3-1
            "line_items",  # Table 3-2
            "routing_history",  # Table 3-3
            "parties",  # Table 3-4
            "ownership_chain",  # Table 3-5
            "import_pattern",  # Table 3-6
            "trade_flow",  # Table 3-7
            "document_review",  # Table 3-8
            "document_consistency",  # Table 3-9
            "manufacturing_verification",  # Table 3-10
            "risk_indicators",  # Table 3-11
            "score_breakdown",  # Table 3-12
            "what_if_scenarios",  # Table 3-13
            "data_sources",  # Table 3-14
        ]

        for nested_section in nested_sections:
            assert nested_section in package["sections"], (
                f"Missing nested section: {nested_section}"
            )

    def test_shipment_id_table_3_1(self, greenfield_referral_package):
        """
        GIVEN: Greenfield referral package
        WHEN: Accessing Table 3-1 (Shipment ID)
        THEN: Contains bill_id, manifest_id, and ETA
        """
        table_3_1 = greenfield_referral_package["sections"]["shipment_id"]

        assert table_3_1["bill_id"] == "SAMPLE-BOL-2026-001"
        assert table_3_1["manifest_id"] == "MF-2026-001"
        assert "eta" in table_3_1
        assert isinstance(table_3_1["eta"], str)

    def test_line_items_table_3_2(self, greenfield_referral_package):
        """
        GIVEN: Greenfield referral package
        WHEN: Accessing Table 3-2 (Line Items)
        THEN: Contains HTS code, weight, value, and duty rate
        """
        table_3_2 = greenfield_referral_package["sections"]["line_items"]

        assert isinstance(table_3_2, list)
        assert len(table_3_2) > 0

        line_item = table_3_2[0]
        assert line_item["hts_code"] == "7604.10.1000"
        assert line_item["weight_mt"] == 26.2
        assert line_item["declared_value_usd"] == 72030
        assert "duty_rate" in line_item
        assert "estimated_duty_usd" in line_item

    def test_routing_history_table_3_3(self, greenfield_referral_package):
        """
        GIVEN: Greenfield referral package
        WHEN: Accessing Table 3-3 (Routing History)
        THEN: Contains location, country, date, and anomaly flags
        """
        table_3_3 = greenfield_referral_package["sections"]["routing_history"]

        assert isinstance(table_3_3, list)
        assert len(table_3_3) > 0

        routing = table_3_3[0]
        assert routing["location"] == "Nansha Terminal, Guangzhou"
        assert routing["country"] == "CN"
        assert "date" in routing
        assert "event" in routing
        assert "ais_anomaly" in routing

    def test_parties_table_3_4(self, greenfield_referral_package):
        """
        GIVEN: Greenfield referral package
        WHEN: Accessing Table 3-4 (Parties)
        THEN: Contains role, name, country, Senzing ID, and risk score
        """
        table_3_4 = greenfield_referral_package["sections"]["parties"]

        assert isinstance(table_3_4, list)
        assert len(table_3_4) > 0

        party = table_3_4[0]
        assert party["role"] == "Shipper"
        assert party["name"] == "Greenfield Industrial Trading Co., Ltd."
        assert party["country"] == "VN"
        assert "senzing_id" in party
        assert "risk_score" in party

    def test_ownership_chain_table_3_5(self, greenfield_referral_package):
        """
        GIVEN: Greenfield referral package
        WHEN: Accessing Table 3-5 (Ownership Chain)
        THEN: Contains 4+ levels linking VN → HK → CN
        """
        table_3_5 = greenfield_referral_package["sections"]["ownership_chain"]

        assert isinstance(table_3_5, list)
        assert len(table_3_5) >= 4, "Expected VN → VN → HK → CN chain"

        # Check chain flow
        assert table_3_5[0]["jurisdiction"] == "VN"  # Root shipper
        assert table_3_5[-1]["jurisdiction"] == "CN"  # Parent manufacturer

        # Each has level, entity, jurisdiction, relationship
        for item in table_3_5:
            assert "level" in item
            assert "entity" in item
            assert "jurisdiction" in item
            assert "relationship" in item

    def test_score_breakdown_table_3_12(
        self, greenfield_referral_package, greenfield_score_breakdown
    ):
        """
        GIVEN: Greenfield referral package and score breakdown
        WHEN: Accessing Table 3-12 (Score Breakdown)
        THEN: Total = 91, components sum to 91, confidence = HIGH
        """
        table_3_12 = greenfield_referral_package["sections"]["score_breakdown"]

        assert table_3_12["total"] == 91
        assert table_3_12["confidence_tier"] == "HIGH"

        # Components must sum to total
        component_sum = sum(c["score"] for c in table_3_12["components"])
        assert component_sum == table_3_12["total"], (
            f"Components sum ({component_sum}) != total ({table_3_12['total']})"
        )

    def test_data_sources_table_3_14(self, greenfield_referral_package):
        """
        GIVEN: Greenfield referral package
        WHEN: Accessing Table 3-14 (Data Sources)
        THEN: Contains ISF, AIS, Senzing with confidence scores
        """
        table_3_14 = greenfield_referral_package["sections"]["data_sources"]

        assert isinstance(table_3_14, list)
        assert len(table_3_14) > 0

        source_names = [s["name"] for s in table_3_14]
        assert "ISF Data Element 9" in source_names
        assert "AIS vessel tracking" in source_names
        assert "Senzing entity resolution" in source_names

        for source in table_3_14:
            assert "name" in source
            assert "confidence" in source
            assert 0 <= source["confidence"] <= 1


class TestConfidenceScoreCalculation:
    """
    Test confidence score calculation logic.
    Greenfield case: 91/100
    """

    def test_greenfield_confidence_score_is_91(self, greenfield_referral_package):
        """
        GIVEN: Greenfield case data
        WHEN: Confidence score is calculated
        THEN: Score is 91/100 (HIGH confidence)
        """
        package = greenfield_referral_package

        assert package["score"] == 91, "Greenfield score must be 91"
        assert package["confidence_level"] == "HIGH"

    def test_confidence_score_range_is_0_to_100(
        self, greenfield_referral_package
    ):
        """
        GIVEN: Referral package
        WHEN: Confidence score is accessed
        THEN: Score is between 0 and 100 inclusive
        """
        score = greenfield_referral_package["score"]

        assert isinstance(score, int)
        assert 0 <= score <= 100

    def test_confidence_tier_matches_score_range(self, greenfield_referral_package):
        """
        GIVEN: Referral package
        WHEN: Accessing confidence_level field
        THEN: Tier matches score (LOW/MEDIUM/HIGH)
        """
        package = greenfield_referral_package
        score = package["score"]
        tier = package["confidence_level"]

        if score >= 75:
            assert tier == "HIGH"
        elif score >= 40:
            assert tier == "MEDIUM"
        else:
            assert tier == "LOW"


class TestComponentBreakdown:
    """
    Test 6-component breakdown sums to total.
    From ARCHITECTURE.md Table 3-12
    """

    def test_six_components_sum_to_91(self, greenfield_score_breakdown):
        """
        GIVEN: Greenfield score breakdown with 6 components
        WHEN: Components are summed
        THEN: Total equals 91
        """
        breakdown = greenfield_score_breakdown

        assert len(breakdown["components"]) == 6

        component_sum = sum(c["score"] for c in breakdown["components"])
        assert component_sum == 91

    def test_each_component_has_tier_and_source(self, greenfield_score_breakdown):
        """
        GIVEN: Score breakdown
        WHEN: Iterating components
        THEN: Each has tier (1-4), name, score, max, and source
        """
        for component in greenfield_score_breakdown["components"]:
            assert "tier" in component
            assert 1 <= component["tier"] <= 4

            assert "name" in component
            assert "score" in component
            assert "max" in component
            assert "source" in component

            # Score must not exceed max
            assert component["score"] <= component["max"]

    def test_tier_4_components_dominate_score(self, greenfield_score_breakdown):
        """
        GIVEN: 4-tier scoring model
        WHEN: Reviewing Greenfield breakdown
        THEN: Tier 4 (origin_doc_gap + time_sensitivity) accounts for ~39 pts
        """
        tier_4_components = [
            c for c in greenfield_score_breakdown["components"]
            if c["tier"] == 4
        ]

        tier_4_sum = sum(c["score"] for c in tier_4_components)
        assert tier_4_sum > 30, "Tier 4 must dominate scoring"

        # Verify tier 4 includes origin_doc_gap and time_sensitivity
        tier_4_names = [c["name"] for c in tier_4_components]
        assert "origin_doc_gap" in tier_4_names
        assert "time_sensitivity" in tier_4_names

    def test_component_scores_never_exceed_max(self, greenfield_score_breakdown):
        """
        GIVEN: Score breakdown
        WHEN: Checking each component
        THEN: score <= max for all components
        """
        for component in greenfield_score_breakdown["components"]:
            assert component["score"] <= component["max"], (
                f"{component['name']}: {component['score']} > {component['max']}"
            )


class TestXAIAssertions:
    """
    Test XAI (Explainable AI) assertions are present and meaningful.
    """

    def test_referral_package_contains_xai_narratives(
        self, greenfield_referral_package
    ):
        """
        GIVEN: Greenfield referral package
        WHEN: Checking for XAI content
        THEN: Score breakdown includes plain-English descriptions
        """
        breakdown = greenfield_referral_package["sections"]["score_breakdown"]

        # Each component must have a description (XAI narrative)
        for component in breakdown["components"]:
            assert "description" in component
            assert len(component["description"]) > 10, (
                "Description must be meaningful, not empty"
            )

    def test_xai_assertion_explains_why_not_just_number(
        self, greenfield_score_breakdown
    ):
        """
        GIVEN: Score breakdown
        WHEN: Accessing origin_doc_gap component
        THEN: Description explains WHY (ISF contradiction) not just score
        """
        origin_doc_gap = next(
            c for c in greenfield_score_breakdown["components"]
            if c["name"] == "origin_doc_gap"
        )

        description = origin_doc_gap["description"]

        # Must explain the evidence, not just the score
        assert "ISF" in description or "stuffing" in description.lower()
        assert "COO" in description or "country of origin" in description.lower()


class TestRevenueImpactCalculation:
    """
    Test revenue (duty) impact calculations.
    """

    def test_line_item_includes_estimated_duty(self, greenfield_referral_package):
        """
        GIVEN: Greenfield line item
        WHEN: Accessing estimated_duty_usd
        THEN: Duty is calculated: declared_value_usd × duty_rate
        """
        line_item = greenfield_referral_package["sections"]["line_items"][0]

        declared_value = line_item["declared_value_usd"]
        duty_rate = line_item["duty_rate"]
        estimated_duty = line_item["estimated_duty_usd"]

        # Duty should be ≈ value × rate (with rounding)
        calculated_duty = declared_value * duty_rate
        assert abs(estimated_duty - calculated_duty) < 1, (
            f"Duty mismatch: {estimated_duty} vs {calculated_duty}"
        )

    def test_greenfield_duty_impact_is_26k(self, greenfield_referral_package):
        """
        GIVEN: Greenfield case (aluminum, 374% AD/CVD rate)
        WHEN: Calculating duty impact
        THEN: Impact is ~$26.9k (372% rate typical for aluminum)
        """
        line_item = greenfield_referral_package["sections"]["line_items"][0]

        estimated_duty = line_item["estimated_duty_usd"]

        # From ARCHITECTURE.md: 374% AD/CVD rate
        # 72030 × 0.374 ≈ 26938
        assert 25000 < estimated_duty < 28000, (
            f"Greenfield duty impact should be ~$26.9k, got ${estimated_duty}"
        )

    def test_revenue_impact_displayed_in_recommended_action(
        self, greenfield_referral_package
    ):
        """
        GIVEN: Referral package
        WHEN: User sees recommended action
        THEN: Revenue impact is visible (e.g., "~$2.1M duties")
        """
        package = greenfield_referral_package

        # This test is a placeholder for when the referral includes
        # a revenue_impact field in the recommended_action narrative
        # For now, we assert the structure supports it
        assert "recommended_action" in package


class TestRecommendedActionField:
    """
    Test recommended action field and action logic.
    """

    def test_recommended_action_is_examine_on_arrival(
        self, greenfield_referral_package
    ):
        """
        GIVEN: Greenfield case (score 91/100)
        WHEN: Recommended action is determined
        THEN: Action is EXAMINE_ON_ARRIVAL
        """
        package = greenfield_referral_package

        assert package["recommended_action"] == "EXAMINE_ON_ARRIVAL"

    def test_recommended_action_is_one_of_valid_values(
        self, greenfield_referral_package
    ):
        """
        GIVEN: Referral package
        WHEN: Accessing recommended_action
        THEN: Value is one of: EXAMINE_ON_ARRIVAL, HOLD_FOR_INVESTIGATION, CLEAR, AUDIT
        """
        valid_actions = [
            "EXAMINE_ON_ARRIVAL",
            "HOLD_FOR_INVESTIGATION",
            "CLEAR",
            "AUDIT",
        ]

        action = greenfield_referral_package["recommended_action"]
        assert action in valid_actions, (
            f"Invalid action: {action}"
        )

    def test_high_confidence_recommends_action(self, greenfield_referral_package):
        """
        GIVEN: Referral with score 91 (HIGH confidence)
        WHEN: Recommended action is determined
        THEN: Action is not CLEAR
        """
        package = greenfield_referral_package

        if package["confidence_level"] == "HIGH" and package["score"] >= 75:
            assert package["recommended_action"] != "CLEAR"


class TestReferralPackageIntegration:
    """
    Integration tests for full referral package generation flow.
    """

    def test_referral_package_is_json_serializable(
        self, greenfield_referral_package
    ):
        """
        GIVEN: Referral package
        WHEN: Attempting to serialize to JSON
        THEN: No serialization errors occur
        """
        import json

        # Should not raise JSONDecodeError
        json_str = json.dumps(greenfield_referral_package)
        assert json_str is not None
        assert len(json_str) > 0

    def test_greenfield_package_is_complete_for_presentation(
        self, greenfield_referral_package
    ):
        """
        GIVEN: Greenfield referral package
        WHEN: Preparing for CBP officer presentation
        THEN: All 14 tables (3-1 through 3-14) are populated
        """
        package = greenfield_referral_package
        sections = package["sections"]

        # 14 tables as per ARCHITECTURE.md
        required_tables = [
            "shipment_id",  # 3-1
            "line_items",  # 3-2
            "routing_history",  # 3-3
            "parties",  # 3-4
            "ownership_chain",  # 3-5
            "import_pattern",  # 3-6
            "trade_flow",  # 3-7
            "document_review",  # 3-8
            "document_consistency",  # 3-9
            "manufacturing_verification",  # 3-10
            "risk_indicators",  # 3-11
            "score_breakdown",  # 3-12
            "what_if_scenarios",  # 3-13
            "data_sources",  # 3-14
        ]

        for table in required_tables:
            assert table in sections, f"Missing Table: {table}"
            # Each table should have content (not None or empty)
            assert sections[table] is not None, f"Table {table} is None"
