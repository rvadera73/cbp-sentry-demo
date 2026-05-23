"""Comprehensive test suite for Risk Corridor Business Logic Engine

Tests all four modules and the factory orchestration.
"""

import unittest
from datetime import datetime, timedelta
from typing import Dict, List

from hts_classifier import HTSIndustryClassifier
from volumetric_analyzer import VolumetricAnalyzer
from temporal_analyzer import TemporalAnalyzer
from transshipment_detector import TransshipmentDetector
from corridor_factory import RiskCorridorFactory


class TestHTSIndustryClassifier(unittest.TestCase):
    """Test HTS classification logic."""

    def setUp(self):
        self.classifier = HTSIndustryClassifier()

    def test_classify_solar_infrastructure(self):
        """Test classification of solar panel HTS codes."""
        result = self.classifier.classify_hts_to_segment("8541.40.60")
        self.assertEqual(result["segment"], "Solar Infrastructure")
        self.assertIn("CN", result["ad_cvd_countries"])

    def test_classify_aluminum(self):
        """Test aluminum extrusions."""
        result = self.classifier.classify_hts_to_segment("7604.10")
        self.assertEqual(result["segment"], "Industrial Aluminum")

    def test_classify_steel(self):
        """Test flat-rolled steel."""
        result = self.classifier.classify_hts_to_segment("7210.70")
        self.assertEqual(result["segment"], "Flat-Rolled Steel & Alloys")

    def test_get_evasion_origin_shifts(self):
        """Test retrieval of known transshipment routes."""
        shifts = self.classifier.get_evasion_origin_shifts("8541.40", "CN")
        self.assertIn("VN", shifts)  # Vietnam is known CN transshipment route
        self.assertIn("MY", shifts)  # Malaysia

    def test_lookup_ad_cvd_rate(self):
        """Test duty rate lookup."""
        rate = self.classifier.lookup_ad_cvd_rate("8541", "CN")
        self.assertEqual(rate, 100.0)

    def test_generic_hts_fallback(self):
        """Test non-priority HTS code returns generic classification."""
        result = self.classifier.classify_hts_to_segment("9999.99")
        self.assertEqual(result["segment"], "General Merchandise")
        self.assertEqual(result["baseline_annual_capacity_tons"], 10_000_000)

    def test_is_high_risk_hts(self):
        """Test high-risk flag."""
        self.assertTrue(self.classifier.is_high_risk_hts("8541"))
        self.assertTrue(self.classifier.is_high_risk_hts("7604"))
        self.assertFalse(self.classifier.is_high_risk_hts("9999"))


class TestVolumetricAnalyzer(unittest.TestCase):
    """Test volumetric delta calculations."""

    def setUp(self):
        self.classifier = HTSIndustryClassifier()
        self.analyzer = VolumetricAnalyzer(self.classifier)

    def test_normal_volume(self):
        """Test normal shipment volume (within capacity)."""
        manifest = [
            {"weight_tons": 50.0, "declared_value": 100000},
            {"weight_tons": 45.0, "declared_value": 90000},
            {"weight_tons": 55.0, "declared_value": 110000},
        ]
        result = self.analyzer.calculate_macro_volumetric_delta(
            hts_code="8541",
            origin_country="CN",
            destination_country="US",
            manifest_rows=manifest,
            time_period_days=7,
        )
        self.assertEqual(result["status"], "NORMAL")
        self.assertEqual(result["outbound_volume_manifest_tons"], 150.0)

    def test_flagged_volume_surge(self):
        """Test volume exceeding capacity (4× ratio = CRITICAL)."""
        # Solar baseline is 2.5M tons/year = 6849 tons/day = 47,940 tons/week
        # Create 150,000 tons = 3.1× weekly capacity
        manifest = [
            {"weight_tons": 1000.0, "declared_value": 1000000} for _ in range(150)
        ]
        result = self.analyzer.calculate_macro_volumetric_delta(
            hts_code="8541",
            origin_country="CN",
            destination_country="US",
            manifest_rows=manifest,
            time_period_days=7,
        )
        self.assertEqual(result["status"], "FLAGGED")
        self.assertGreater(result["ratio"], 3.0)
        self.assertEqual(result["severity"], "CRITICAL")

    def test_price_anomaly_detection(self):
        """Test unit price outlier detection."""
        manifest = [
            {"weight_tons": 10.0, "declared_value": 100000},  # $10k/ton (normal)
            {"weight_tons": 10.0, "declared_value": 105000},  # $10.5k/ton
            {"weight_tons": 10.0, "declared_value": 15000},   # $1.5k/ton (OUTLIER)
            {"weight_tons": 10.0, "declared_value": 102000},  # $10.2k/ton
        ]
        result = self.analyzer.detect_weight_value_mismatch(manifest, "8541")
        self.assertTrue(result["anomaly_detected"])
        self.assertEqual(len(result["suspect_rows"]), 1)

    def test_frequency_spike(self):
        """Test shipping frequency anomaly."""
        manifest = [
            {"filing_date": "2026-05-20", "weight_tons": 100},
            {"filing_date": "2026-05-20", "weight_tons": 100},
            {"filing_date": "2026-05-20", "weight_tons": 100},
            {"filing_date": "2026-05-21", "weight_tons": 100},
        ]
        result = self.analyzer.detect_frequency_spike(manifest, baseline_shipments_per_week=2)
        self.assertTrue(result["spike_detected"])


class TestTemporalAnalyzer(unittest.TestCase):
    """Test temporal anomaly detection."""

    def setUp(self):
        self.analyzer = TemporalAnalyzer()

    def test_yoy_surge_critical(self):
        """Test critical year-over-year surge."""
        current = {"shipment_count": 100, "aggregate_value": 500000}
        prior = {"shipment_count": 20, "aggregate_value": 100000}
        result = self.analyzer.calculate_yoy_surge(current, prior)
        self.assertEqual(result["surge_status"], "CRITICAL")
        self.assertEqual(result["volume_surge_pct"], 400.0)

    def test_yoy_surge_normal(self):
        """Test normal variation."""
        current = {"shipment_count": 50, "aggregate_value": 250000}
        prior = {"shipment_count": 48, "aggregate_value": 240000}
        result = self.analyzer.calculate_yoy_surge(current, prior)
        self.assertEqual(result["surge_status"], "NORMAL")

    def test_seasonal_anomaly(self):
        """Test seasonal deviation."""
        current = 200000  # Current period value
        historical = {
            "Jan-2024": 50000,
            "Jan-2025": 48000,
            "Feb-2024": 49000,
            "Feb-2025": 51000,
        }
        result = self.analyzer.detect_seasonal_anomaly(current, historical)
        self.assertTrue(result["anomaly_detected"])
        self.assertGreater(result["current_deviation_pct"], 300)

    def test_trend_calculation(self):
        """Test trend direction."""
        time_series = [
            ("2026-05-01", 1000),
            ("2026-05-02", 1100),
            ("2026-05-03", 1200),
            ("2026-05-04", 1300),
            ("2026-05-05", 1400),
        ]
        result = self.analyzer.calculate_trend(time_series)
        self.assertEqual(result["trend"], "UP")
        self.assertGreater(result["r_squared"], 0.9)

    def test_cyclical_pattern_regular(self):
        """Test detection of regular shipping cycles."""
        dates = [
            ("2026-05-01", 1000),
            ("2026-05-08", 1000),
            ("2026-05-15", 1000),
            ("2026-05-22", 1000),
            ("2026-05-29", 1000),
        ]
        result = self.analyzer.detect_cyclical_pattern(dates)
        self.assertTrue(result["pattern_detected"])
        self.assertEqual(result["regularity"], "VERY_REGULAR")
        self.assertEqual(result["cycle_length_days"], 7)


class TestTransshipmentDetector(unittest.TestCase):
    """Test transshipment pattern detection."""

    def setUp(self):
        self.detector = TransshipmentDetector()

    def test_ftz_dwell_normal(self):
        """Test normal FTZ dwell."""
        result = self.detector.detect_ftz_dwell_anomaly("FTZ-80", actual_dwell_days=1.5)
        self.assertEqual(result["status"], "NORMAL")
        self.assertFalse(result["flag"])

    def test_ftz_dwell_anomaly(self):
        """Test excessive FTZ dwell (transshipment indicator)."""
        result = self.detector.detect_ftz_dwell_anomaly("FTZ-80", actual_dwell_days=6.0)
        self.assertEqual(result["status"], "HIGH_RISK_DWELL")
        self.assertTrue(result["flag"])
        self.assertEqual(result["ratio"], 4.0)

    def test_port_routing_return_visit(self):
        """Test detection of return visits."""
        routing = [
            {"port_code": "SGSIN", "country": "SG", "dwell_hours": 24},
            {"port_code": "HKHKG", "country": "HK", "dwell_hours": 36},
            {"port_code": "SGSIN", "country": "SG", "dwell_hours": 12},  # Return to SG
            {"port_code": "LAUS", "country": "US", "dwell_hours": 48},
        ]
        result = self.detector.detect_port_routing_anomaly(routing)
        self.assertTrue(result["anomaly_detected"])
        self.assertIn("SG", result["return_visits"])

    def test_port_routing_transshipment_hub(self):
        """Test detection of known transshipment hubs."""
        routing = [
            {"port_code": "CNSHA", "country": "CN", "dwell_hours": 12},
            {"port_code": "SGSIN", "country": "SG", "dwell_hours": 24},  # Hub
            {"port_code": "LAUS", "country": "US", "dwell_hours": 48},
        ]
        result = self.detector.detect_port_routing_anomaly(routing)
        self.assertGreater(len(result["transshipment_hubs"]), 0)

    def test_consolidation_pattern(self):
        """Test detection of consolidation centers."""
        shipments_by_ftz = {
            "FTZ-80": [
                {"origin_country": "CN", "weight_tons": 100},
                {"origin_country": "VN", "weight_tons": 100},
                {"origin_country": "TH", "weight_tons": 100},
                {"origin_country": "MY", "weight_tons": 100},
                {"origin_country": "KH", "weight_tons": 100},
                {"origin_country": "IN", "weight_tons": 100},
                {"origin_country": "BD", "weight_tons": 100},
            ]
        }
        result = self.detector.detect_consolidation_pattern(shipments_by_ftz)
        self.assertTrue(result["consolidation_detected"])
        self.assertEqual(result["origin_country_count"], 7)


class TestRiskCorridorFactory(unittest.TestCase):
    """Test factory orchestration and corridor creation."""

    def setUp(self):
        self.factory = RiskCorridorFactory()

    def test_create_corridor_from_shipment(self):
        """Test basic corridor creation."""
        shipment = {
            "hts_code": "8541.40.60",
            "origin_country": "CN",
            "destination_country": "US",
            "shipper_name": "Beijing Solar Co",
            "declared_value_usd": 100000,
            "declared_weight_kg": 5000,
            "vessel_name": "Ever Given",
        }
        corridor = self.factory.create_corridor_from_shipment(shipment)
        self.assertEqual(corridor["industry_segment"], "Solar Infrastructure")
        self.assertEqual(corridor["origin_country"], "CN")
        self.assertGreater(corridor["risk_score_baseline"], 0)
        self.assertTrue(corridor["corridor_id"].startswith("HC-"))

    def test_aggregate_corridor_metrics(self):
        """Test full corridor aggregation."""
        shipments = [
            {
                "hts_code": "8541.40.60",
                "origin_country": "CN",
                "destination_country": "US",
                "shipper_name": "Beijing Solar Co",
                "declared_value_usd": 100000,
                "declared_weight_kg": 5000,
                "weight_tons": 5.0,
            }
            for _ in range(10)
        ]
        result = self.factory.aggregate_corridor_metrics(
            corridor_id="HC-8541-CNUS-ABCD",
            shipment_rows=shipments,
            time_period_days=7,
        )
        self.assertEqual(result["shipment_count"], 10)
        self.assertEqual(result["aggregate_value_usd"], 1000000)
        self.assertIn("macro_volumetric_delta", result)
        self.assertIn("yoy_surge", result)
        self.assertIn("risk_level", result)
        self.assertGreater(result["composite_risk_score"], 0)

    def test_group_shipments_by_corridor(self):
        """Test shipment grouping."""
        shipments = [
            {
                "hts_code": "8541.40.60",
                "origin_country": "CN",
                "destination_country": "US",
                "shipper_name": "Beijing Solar Co",
                "declared_value_usd": 100000,
                "declared_weight_kg": 5000,
            },
            {
                "hts_code": "8541.40.60",
                "origin_country": "CN",
                "destination_country": "US",
                "shipper_name": "Shanghai Solar Ltd",
                "declared_value_usd": 100000,
                "declared_weight_kg": 5000,
            },
        ]
        corridors = self.factory.group_shipments_by_corridor(shipments)
        self.assertEqual(len(corridors), 2)

    def test_composite_risk_score_calculation(self):
        """Test composite risk score synthesis."""
        shipments = [
            {"weight_tons": 1000, "declared_value": 1000000}
            for _ in range(150)  # High volume
        ]
        shipments[0]["hts_code"] = "8541"
        shipments[0]["origin_country"] = "CN"
        shipments[0]["destination_country"] = "US"
        shipments[0]["shipper_name"] = "Test Shipper"

        for s in shipments:
            s.setdefault("hts_code", "8541")
            s.setdefault("origin_country", "CN")
            s.setdefault("destination_country", "US")
            s.setdefault("shipper_name", "Test Shipper")

        result = self.factory.aggregate_corridor_metrics(
            corridor_id="HC-8541-CNUS-TEST",
            shipment_rows=shipments,
            time_period_days=7,
        )
        self.assertGreaterEqual(result["composite_risk_score"], 50)


if __name__ == "__main__":
    unittest.main()
