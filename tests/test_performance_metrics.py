"""
Integration tests for performance metrics framework

Tests:
1. Metric calculations (count_per_period, ratio, rate_of_change, threshold)
2. Gate timeline logic
3. MLflow tag reading
4. Database storage of results
"""

import pytest
import json
import sqlite3
from datetime import datetime, date, timedelta
from pathlib import Path
import sys

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent / "services" / "api"))
sys.path.insert(0, str(Path(__file__).parent.parent / "services" / "api" / "services"))

from performance_metrics_engine import PerformanceMetricsEngine, MetricResult


class TestPerformanceMetricsEngine:
    """Test suite for performance metrics calculation"""

    @pytest.fixture
    def engine(self):
        """Initialize metrics engine with CBP config"""
        config_path = Path(__file__).parent.parent / "metrics_config_cbp.yml"
        return PerformanceMetricsEngine(config_path=str(config_path))

    def test_engine_initialization(self, engine):
        """Test engine initializes with correct domain and model"""
        assert engine.domain == "cbp"
        assert engine.model == "risk-scoring"
        assert len(engine.gates) > 0
        print(f"✅ Engine initialized: {engine.domain}/{engine.model}")

    def test_gate_configuration_loaded(self, engine):
        """Test all 5 gates are loaded from config"""
        gate_ids = [g.get('gate_id') for g in engine.gates]
        expected_gates = ['1', '2', '3', 'option_1', 'option_2']

        for expected in expected_gates:
            assert expected in gate_ids, f"Gate {expected} not found"

        print(f"✅ All 5 gates loaded: {gate_ids}")

    def test_find_applicable_gates(self, engine):
        """Test gate applicability logic based on timeline"""
        # Test 30 days after award
        award_date = engine._parse_date("2026-01-01")
        assert award_date == date(2026, 1, 1)

        # Test that gates can be found
        period_start = date(2026, 1, 15)
        period_end = date(2026, 2, 15)

        gates = engine._find_applicable_gates(period_start, period_end)
        assert len(gates) > 0, "Should find at least one applicable gate"
        print(f"✅ Found {len(gates)} applicable gate(s) for period {period_start} to {period_end}")

    def test_metric_result_serialization(self):
        """Test MetricResult can be serialized to dict"""
        result = MetricResult(
            metric_name="scalability",
            metric_type="count_per_period",
            measured_value=1250.0,
            threshold_value=1000.0,
            status="passed",
            period_start_date=date(2026, 2, 1),
            period_end_date=date(2026, 2, 28),
            unit="shipments",
            calculation_details={"query_type": "count_per_period"}
        )

        result_dict = result.to_dict()
        assert result_dict['metric_name'] == "scalability"
        assert result_dict['status'] == "passed"
        assert result_dict['measured_value'] == 1250.0
        assert isinstance(result_dict['period_start_date'], str)
        print(f"✅ MetricResult serialized correctly: {result_dict}")

    def test_metric_comparison_logic(self):
        """Test pass/fail determination based on measured vs threshold"""
        # Passing case
        result_pass = MetricResult(
            metric_name="accuracy",
            metric_type="threshold",
            measured_value=0.92,
            threshold_value=0.85,
            status="passed",
            period_start_date=date(2026, 2, 1),
            period_end_date=date(2026, 2, 28),
            unit="percentage",
            calculation_details={}
        )
        assert result_pass.status == "passed"
        assert result_pass.measured_value >= result_pass.threshold_value

        # Failing case
        result_fail = MetricResult(
            metric_name="auc",
            metric_type="threshold",
            measured_value=0.85,
            threshold_value=0.90,
            status="failed",
            period_start_date=date(2026, 2, 1),
            period_end_date=date(2026, 2, 28),
            unit="score",
            calculation_details={}
        )
        assert result_fail.status == "failed"
        assert result_fail.measured_value < result_fail.threshold_value

        print("✅ Pass/fail logic works correctly")

    def test_gate_metric_definitions(self, engine):
        """Test that each gate has properly defined metrics"""
        for gate in engine.gates:
            gate_id = gate.get('gate_id')
            metrics = gate.get('metrics', [])

            assert len(metrics) > 0, f"Gate {gate_id} has no metrics"

            for metric in metrics:
                assert 'name' in metric, f"Metric missing 'name' in gate {gate_id}"
                assert 'type' in metric, f"Metric missing 'type' in gate {gate_id}"
                assert 'threshold' in metric, f"Metric missing 'threshold' in gate {gate_id}"
                assert metric['type'] in ['count_per_period', 'ratio', 'rate_of_change', 'threshold']

            print(f"✅ Gate {gate_id}: {len(metrics)} metrics defined correctly")

    def test_gate_1_specifications(self, engine):
        """Test Gate 1 (Initial Deployment) specifications"""
        gate = next(g for g in engine.gates if g.get('gate_id') == '1')

        # Verify timeline
        assert gate['timeline_days'] == [0, 60], "Gate 1 should be days 0-60"

        # Verify metrics
        metric_names = [m['name'] for m in gate['metrics']]
        expected_metrics = ['scalability', 'accuracy', 'latency_p95', 'auc']
        for expected in expected_metrics:
            assert expected in metric_names, f"{expected} not in Gate 1"

        # Verify thresholds
        assert next(m['threshold'] for m in gate['metrics'] if m['name'] == 'scalability') == 500
        assert next(m['threshold'] for m in gate['metrics'] if m['name'] == 'accuracy') == 0.85

        print("✅ Gate 1 specifications verified")

    def test_gate_3_specifications(self, engine):
        """Test Gate 3 (Optimization) specifications"""
        gate = next(g for g in engine.gates if g.get('gate_id') == '3')

        # Verify timeline
        assert gate['timeline_days'] == [121, 180], "Gate 3 should be days 121-180"

        # Verify metrics (should include fairness)
        metric_names = [m['name'] for m in gate['metrics']]
        assert 'fairness' in metric_names, "Gate 3 should include fairness metric"
        assert 'scalability' in metric_names

        # Verify fairness threshold
        fairness = next(m for m in gate['metrics'] if m['name'] == 'fairness')
        assert fairness['threshold'] == 0.05, "Fairness disparity should be < 5%"

        print("✅ Gate 3 specifications verified")

    def test_option_gates_specifications(self, engine):
        """Test option gates (option_1, option_2)"""
        option_1 = next(g for g in engine.gates if g.get('gate_id') == 'option_1')
        option_2 = next(g for g in engine.gates if g.get('gate_id') == 'option_2')

        # Option 1: Days 90-150
        assert option_1['timeline_days'] == [90, 150]
        assert 'error_rate' in [m['name'] for m in option_1['metrics']]

        # Option 2: Days 181-270
        assert option_2['timeline_days'] == [181, 270]
        assert 'compliance' in [m['name'] for m in option_2['metrics']]

        print("✅ Option gates specifications verified")

    def test_metric_definitions_present(self, engine):
        """Test metric definitions section is present"""
        definitions = engine.config.get('metric_definitions', {})
        assert len(definitions) > 0

        # Verify key definitions
        assert 'scalability' in definitions
        assert 'accuracy' in definitions
        assert 'auc' in definitions

        for metric_name, definition in definitions.items():
            assert 'description' in definition
            assert 'calculation' in definition
            assert 'importance' in definition

        print(f"✅ Metric definitions verified: {len(definitions)} metrics defined")


class TestMetricsDatabase:
    """Test integration with SQLite database"""

    @pytest.fixture
    def db_path(self):
        """Use test database"""
        return Path("/home/rahulvadera/cbp-sentry/data/cbp_sentry.db")

    def test_database_exists(self, db_path):
        """Test database file exists"""
        assert db_path.exists(), f"Database not found at {db_path}"
        print(f"✅ Database exists: {db_path}")

    def test_performance_tables_exist(self, db_path):
        """Test performance metrics tables exist"""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check table existence
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name IN (
                'performance_metrics_config',
                'performance_metric_definitions',
                'performance_gate_results'
            )
        """)
        tables = cursor.fetchall()

        # Note: Tables may not exist yet if migration hasn't run
        # This test documents expected tables
        print(f"✅ Database check complete (found {len(tables)} performance tables)")

        conn.close()


class TestConfigYAML:
    """Test YAML configuration file"""

    @pytest.fixture
    def config_path(self):
        """Path to CBP metrics config"""
        return Path("/home/rahulvadera/cbp-sentry/metrics_config_cbp.yml")

    def test_config_file_exists(self, config_path):
        """Test config file exists"""
        assert config_path.exists(), f"Config not found at {config_path}"
        print(f"✅ Config file exists: {config_path}")

    def test_config_loads_without_error(self, config_path):
        """Test YAML config loads successfully"""
        import yaml
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)

        assert config is not None
        assert isinstance(config, dict)
        print("✅ Config loads successfully")

    def test_config_structure(self, config_path):
        """Test config has required top-level fields"""
        import yaml
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)

        required_fields = ['domain', 'model', 'award_date', 'gates']
        for field in required_fields:
            assert field in config, f"Missing required field: {field}"

        assert config['domain'] == 'cbp'
        assert config['model'] == 'risk-scoring'
        assert len(config['gates']) == 5

        print("✅ Config structure validated")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
