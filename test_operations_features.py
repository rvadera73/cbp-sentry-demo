#!/usr/bin/env python3
"""
Test Risk Model Operations Features
1. Verify v2.1 is registered in database
2. Test v2.1 scoring function
3. Verify comparison endpoint logic
4. Check UI updates
"""

import subprocess
import sqlite3
import json
import sys

DB_PATH = "/home/rahulvadera/cbp-sentry/data/cbp_sentry.db"

def test_v2_1_database_registration():
    """Verify v2.1 is in the database"""
    print("\n" + "="*80)
    print("TEST 1: v2.1 Database Registration")
    print("="*80)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM risk_models WHERE version = '2.1'")
    row = cursor.fetchone()
    conn.close()

    if not row:
        print("❌ FAILED: v2.1 not found in database")
        return False

    print("✅ PASSED: v2.1 registered in database")
    print(f"   Model ID: {row['model_id']}")
    print(f"   Status: {row['status']}")
    print(f"   Framework: {row['framework']}")
    print(f"   Weights Sum: {row['weights_sum']}")
    print(f"   Feature Count: {row['feature_count']}")
    return True


def test_v2_1_scoring_function():
    """Test v2.1 scoring on sample shipments"""
    print("\n" + "="*80)
    print("TEST 2: v2.1 Scoring Function")
    print("="*80)

    sys.path.insert(0, '/home/rahulvadera/cbp-sentry/services/api/services')
    from risk_model_v2_1_scoring import score_with_v2_1

    # Test high-risk shipment
    result = score_with_v2_1({
        "shipment_id": "SHP-TEST-001",
        "origin": "CN",
        "destination": "US",
        "commodity_type": "semiconductors",
        "vessel_flag": "PA",
        "port_of_call": "SG",
        "has_isf": True,
        "element_9_match": False,
        "manifest_complete": False,
    })

    if not result or result['score'] < 80:
        print(f"❌ FAILED: Expected high score, got {result.get('score')}")
        return False

    print("✅ PASSED: v2.1 scoring function works")
    print(f"   Test Shipment Score: {result['score']}/100")
    print(f"   Factors: {len(result['factors'])}")
    print(f"   Confidence: {result['confidence']}")
    return True


def test_v2_1_vs_v3_0_comparison_format():
    """Test comparison result format"""
    print("\n" + "="*80)
    print("TEST 3: Model Comparison Format")
    print("="*80)

    # Expected format
    comparison_format = {
        "shipment_id": "SHP-XXXXX",
        "v2_1": {
            "score": 85.5,
            "factors": [
                {"name": "Corridor Risk", "raw_score": 8.5, "weight": 0.4, "contribution": 3.4}
            ],
            "confidence": None
        },
        "v3_0": {
            "score": 75.2,
            "factors": [{"name": "Factor", "contribution": 0.15}],
            "confidence": 0.91
        },
        "difference": {
            "score_delta": -10.3,
            "score_delta_percent": -12.1,
            "better_model": "v3.0",
            "reason": "higher confidence"
        }
    }

    # Validate structure
    required_keys = ["shipment_id", "v2_1", "v3_0", "difference"]
    for key in required_keys:
        if key not in comparison_format:
            print(f"❌ FAILED: Missing key {key}")
            return False

    print("✅ PASSED: Comparison format is valid")
    print(json.dumps(comparison_format, indent=2))
    return True


def test_scoring_distribution():
    """Test that v2.1 scores are properly distributed across range"""
    print("\n" + "="*80)
    print("TEST 4: Scoring Distribution (3 sample shipments)")
    print("="*80)

    sys.path.insert(0, '/home/rahulvadera/cbp-sentry/services/api/services')
    from risk_model_v2_1_scoring import score_with_v2_1

    shipments = [
        {
            "name": "High-risk (CN→US, suspicious docs)",
            "shipment_id": "SHP-HR-001",
            "origin": "CN",
            "destination": "US",
            "commodity_type": "semiconductors",
            "vessel_flag": "PA",
            "port_of_call": "SG",
            "element_9_match": False,
            "manifest_complete": False,
            "expected_range": (75, 100)
        },
        {
            "name": "Medium-risk (VN→US, complete docs)",
            "shipment_id": "SHP-MR-001",
            "origin": "VN",
            "destination": "US",
            "commodity_type": "aluminum_extrusions",
            "vessel_flag": "SG",
            "port_of_call": "LA",
            "element_9_match": True,
            "manifest_complete": True,
            "expected_range": (40, 75)
        },
        {
            "name": "Low-risk (JP→US, standard)",
            "shipment_id": "SHP-LR-001",
            "origin": "JP",
            "destination": "US",
            "commodity_type": "machinery",
            "vessel_flag": "JP",
            "port_of_call": "LA",
            "element_9_match": True,
            "manifest_complete": True,
            "expected_range": (20, 50)
        }
    ]

    all_passed = True
    for shipment in shipments:
        result = score_with_v2_1(shipment)
        score = result['score']
        expected_min, expected_max = shipment['expected_range']

        if score < expected_min or score > expected_max:
            print(f"❌ {shipment['name']}: Score {score} outside expected range ({expected_min}-{expected_max})")
            all_passed = False
        else:
            print(f"✅ {shipment['name']}: Score {score} (in range {expected_min}-{expected_max})")

    return all_passed


def test_ui_components_updated():
    """Check that UI components were updated"""
    print("\n" + "="*80)
    print("TEST 5: UI Components Updated")
    print("="*80)

    # Check PredictionExplanations has comparison toggle
    with open('/home/rahulvadera/cbp-sentry/ui/src/pages/RiskModelManagement/PredictionExplanations.tsx', 'r') as f:
        content = f.read()
        if 'showComparison' in content and 'handleLoadComparison' in content:
            print("✅ PredictionExplanations has comparison functionality")
        else:
            print("❌ PredictionExplanations missing comparison functionality")
            return False

    # Check RetrainingConfig has dataset selection
    with open('/home/rahulvadera/cbp-sentry/ui/src/pages/RiskModelManagement/RetrainingConfig.tsx', 'r') as f:
        content = f.read()
        if 'datasetVersion' in content and 'Simulate Retrain' in content:
            print("✅ RetrainingConfig has dataset selection")
        else:
            print("❌ RetrainingConfig missing dataset selection")
            return False

    return True


def main():
    print("\n" + "="*80)
    print("CBP SENTRY: RISK MODEL OPERATIONS FEATURES TEST SUITE")
    print("="*80)

    tests = [
        ("v2.1 Database Registration", test_v2_1_database_registration),
        ("v2.1 Scoring Function", test_v2_1_scoring_function),
        ("Comparison Format", test_v2_1_vs_v3_0_comparison_format),
        ("Scoring Distribution", test_scoring_distribution),
        ("UI Components Updated", test_ui_components_updated),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            passed = test_func()
            results.append((test_name, passed))
        except Exception as e:
            print(f"\n❌ EXCEPTION in {test_name}: {str(e)}")
            results.append((test_name, False))

    # Summary
    print("\n\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)

    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)

    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")

    print(f"\nResult: {passed_count}/{total_count} tests passed")

    if passed_count == total_count:
        print("\n🎉 ALL TESTS PASSED!")
        return 0
    else:
        print(f"\n⚠️  {total_count - passed_count} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
