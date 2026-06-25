#!/usr/bin/env python3
"""
Test v2.1 scoring on sample shipments
"""

import sys
sys.path.insert(0, '/home/rahulvadera/cbp-sentry/services/api/services')

from risk_model_v2_1_scoring import RiskModelV21Scorer, score_with_v2_1
import json

def test_v2_1_scoring():
    """Test v2.1 scoring on 3 sample shipments"""

    print("\n" + "="*80)
    print("CBP SENTRY v2.1 RISK MODEL SCORING TEST")
    print("="*80)

    # Sample Shipment 1: China to US with high-risk indicators
    print("\n\n📦 TEST SHIPMENT 1: High-Risk China to US")
    print("-" * 80)
    sample1 = {
        "shipment_id": "SHP-00142857",
        "origin": "CN",
        "destination": "US",
        "commodity_type": "semiconductors",
        "vessel_flag": "PA",  # High-risk Panama flag
        "port_of_call": "SG",  # Transshipment hub
        "dwell_hours": 280,  # High dwell time
        "has_isf": True,
        "element_9_match": False,  # Mismatch!
        "manifest_complete": False,  # Incomplete!
        "declared_value": 45200,
        "unit_price": 8.50,
    }

    result1 = score_with_v2_1(sample1)
    print(json.dumps(result1, indent=2))
    print(f"\n✅ Final Score: {result1['score']}/100")

    # Sample Shipment 2: Vietnam to US with tariff evasion indicators
    print("\n\n📦 TEST SHIPMENT 2: Vietnam to US (Tariff Evasion)")
    print("-" * 80)
    sample2 = {
        "shipment_id": "SHP-00142858",
        "origin": "VN",
        "destination": "US",
        "commodity_type": "aluminum_extrusions",
        "vessel_flag": "KR",  # Standard flag
        "port_of_call": "LA",  # Transshipment hub
        "dwell_hours": 72,  # Standard dwell
        "has_isf": True,
        "element_9_match": True,
        "manifest_complete": True,
        "declared_value": 125000,
        "unit_price": 120.00,
    }

    result2 = score_with_v2_1(sample2)
    print(json.dumps(result2, indent=2))
    print(f"\n✅ Final Score: {result2['score']}/100")

    # Sample Shipment 3: Japan to US with low-risk profile
    print("\n\n📦 TEST SHIPMENT 3: Japan to US (Low Risk)")
    print("-" * 80)
    sample3 = {
        "shipment_id": "SHP-00142859",
        "origin": "JP",
        "destination": "US",
        "commodity_type": "precision_instruments",
        "vessel_flag": "JP",  # Low-risk Japan flag
        "port_of_call": "LA",  # Standard port
        "dwell_hours": 48,  # Standard dwell
        "has_isf": True,
        "element_9_match": True,
        "manifest_complete": True,
        "declared_value": 85000,
        "unit_price": 425.00,
    }

    result3 = score_with_v2_1(sample3)
    print(json.dumps(result3, indent=2))
    print(f"\n✅ Final Score: {result3['score']}/100")

    # Summary comparison
    print("\n\n" + "="*80)
    print("SUMMARY COMPARISON")
    print("="*80)
    print(f"\nShipment 1 (CN→US, high-risk): {result1['score']}/100")
    print(f"  - Origin: CN (baseline 8.5)")
    print(f"  - Flag: PA (high-risk, +3.0)")
    print(f"  - Port: SG (hub, +2.5)")
    print(f"  - Dwell: {sample1['dwell_hours']}h (anomaly, +1.5)")
    print(f"  - Commodity: semiconductors (8.5)")
    print(f"  - Element 9: Mismatch (+4.0)")
    print(f"  - Manifest: Incomplete (+2.0)")

    print(f"\nShipment 2 (VN→US, tariff evasion): {result2['score']}/100")
    print(f"  - Origin: VN (baseline 7.0)")
    print(f"  - Flag: KR (standard)")
    print(f"  - Port: LA (hub, +2.5)")
    print(f"  - Dwell: {sample2['dwell_hours']}h (normal)")
    print(f"  - Commodity: aluminum_extrusions (7.0)")
    print(f"  - Element 9: Match")
    print(f"  - Manifest: Complete")

    print(f"\nShipment 3 (JP→US, low-risk): {result3['score']}/100")
    print(f"  - Origin: JP (baseline 3.0)")
    print(f"  - Flag: JP (standard)")
    print(f"  - Port: LA (standard)")
    print(f"  - Dwell: {sample3['dwell_hours']}h (normal)")
    print(f"  - Commodity: precision_instruments (6.5)")
    print(f"  - Element 9: Match")
    print(f"  - Manifest: Complete")

    print("\n✅ V2.1 SCORING TEST COMPLETE\n")


if __name__ == "__main__":
    test_v2_1_scoring()
