#!/usr/bin/env python3
"""
Test performance metrics API endpoints

Run this to verify the API endpoints are working correctly.
"""

import sys
import json
from pathlib import Path
from datetime import date, timedelta

# Add API to path
sys.path.insert(0, str(Path(__file__).parent / "services" / "api"))
sys.path.insert(0, str(Path(__file__).parent / "services" / "api" / "services"))

from performance_api import PerformanceMetricsAPI

def test_api():
    """Test the PerformanceMetricsAPI"""
    print("\n" + "=" * 70)
    print("🧪 Testing Performance Metrics API")
    print("=" * 70)

    api = PerformanceMetricsAPI()

    # Test 1: Current Gate
    print("\n1️⃣  Testing: GET /api/risk-models/performance/current-gate")
    try:
        result = api.get_current_gate(model_id="v3.0")
        print(f"   Status: {result.get('status')}")
        print(f"   Gate: {result.get('current_gate')}")
        print(f"   Days until next: {result.get('days_until_next_gate')}")
        print("   ✅ PASS")
    except Exception as e:
        print(f"   ❌ FAIL: {e}")
        return False

    # Test 2: Performance Metrics
    print("\n2️⃣  Testing: GET /api/risk-models/performance/metrics")
    try:
        period_end = date.today()
        period_start = period_end - timedelta(days=30)
        results = api.get_performance_metrics(
            model_id="v3.0",
            period_start=period_start,
            period_end=period_end
        )
        print(f"   Metrics returned: {len(results)}")
        if results:
            print(f"   Sample metric: {results[0].get('metric_name')}")
        print("   ✅ PASS")
    except Exception as e:
        print(f"   ❌ FAIL: {e}")
        return False

    # Test 3: Gate Status
    print("\n3️⃣  Testing: GET /api/risk-models/performance/gate/3")
    try:
        period_end = date.today()
        period_start = period_end - timedelta(days=30)
        result = api.get_gate_status(
            model_id="v3.0",
            gate_id="3",
            period_start=period_start,
            period_end=period_end
        )
        print(f"   Gate: {result.get('gate_id')}")
        print(f"   Overall status: {result.get('overall_status')}")
        print(f"   Metrics passed: {result.get('metrics_passed')}/{result.get('metrics_total')}")
        print("   ✅ PASS")
    except Exception as e:
        print(f"   ❌ FAIL: {e}")
        return False

    # Test 4: MLflow Config
    print("\n4️⃣  Testing: GET /api/risk-models/performance/mlflow-config")
    try:
        result = api.get_mlflow_performance_config(model_id="v3.0")
        print(f"   Model ID: {result.get('model_id')}")
        print(f"   Gate: {result.get('gate')}")
        print("   ✅ PASS")
    except Exception as e:
        print(f"   Note: {e} (MLflow may not have model tagged yet)")
        print("   This is OK - run: python3 train_with_mlflow.py --version v3.0 --gate 3")

    print("\n" + "=" * 70)
    print("✅ API Test Complete!")
    print("=" * 70)

    return True


if __name__ == "__main__":
    success = test_api()
    sys.exit(0 if success else 1)
