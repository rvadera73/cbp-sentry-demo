#!/usr/bin/env python3
"""
Seed database with three strategic CBP cases for demo:
1. Greenfield Industrial → SunPath (HIGH RISK 91/100) - textbook transshipment
2. Solaria Manufacturing → SunPath (MEDIUM RISK 65/100) - shared consignee alert
3. Decoys (3-4 LOW RISK 15-28/100) - legitimate for discrimination

Creates seed data in Excel format, then ingests via manifest endpoint.
"""

import pandas as pd
import requests
import json
from datetime import datetime, timedelta
from pathlib import Path

# Strategic case profiles
CASES = {
    "greenfield": {
        "shipper": "Greenfield Industrial Trading Co.",
        "shipper_country": "VN",
        "consignee": "SunPath Energy Distributors LLC",
        "consignee_country": "US",
        "manufacturer_origin": "CN",  # ISF Element 9 mismatch
        "hs_code": "7604.29",  # Aluminum extrusions (374% AD/CVD from China)
        "value_usd": 50000,
        "weight_kg": 5000,
        "vessel_name": "MV Pacific Horizon",
        "description": "Aluminum extrusions",
        "shipper_age_months": 8,  # NEW_IMPORTER signal
        "expected_score": 91,
        "expected_tier": "HIGH",
        "triggers": [
            "VN-US corridor (12 pts H1)",
            "374% AD/CVD extreme duty (10 pts H1)",
            "Shipper age 8 months (8 pts H1)",
            "Undervaluation ~40% (10 pts H1)",
            "Dwell 11.2d vs 2.1d baseline (12 pts H2)",
            "ISF CN≠VN mismatch (12 pts H2)",
            "AIS signal gaps (6 pts H2)",
            "Unusual routing (5 pts H2)",
            "New importer high volume (8 pts H3)",
        ]
    },
    "solaria": {
        "shipper": "Solaria Manufacturing Sdn. Bhd.",
        "shipper_country": "MY",
        "consignee": "SunPath Energy Distributors LLC",  # SAME as Greenfield
        "consignee_country": "US",
        "manufacturer_origin": "CN",  # ISF mismatch
        "hs_code": "8541.40.6020",  # Solar modules (100%+ AD/CVD)
        "value_usd": 75000,
        "weight_kg": 2000,
        "vessel_name": "MV Solar Express",
        "description": "Solar modules",
        "shipper_age_months": 1,  # VERY NEW
        "expected_score": 65,
        "expected_tier": "MEDIUM",
        "triggers": [
            "MY-US corridor (12 pts H1)",
            "100% AD/CVD high duty (7 pts H1)",
            "Shipper age 1 month (8 pts H1)",
            "Slight undervaluation (2 pts H1)",
            "Dwell 6.1d vs 2.3d (8 pts H2)",
            "ISF CN≠MY mismatch (8 pts H2)",
            "AIS signal gaps (3 pts H2)",
            "Shared consignee with HIGH case (10 pts H3)",
        ]
    },
    "decoy_legit_old": {
        "shipper": "Vietnam Aluminum Corp",
        "shipper_country": "VN",
        "consignee": "Newark Metals Inc",
        "consignee_country": "US",
        "manufacturer_origin": "VN",  # No ISF mismatch
        "hs_code": "7610",
        "value_usd": 45000,
        "weight_kg": 4500,
        "vessel_name": "MV Hanoi Star",
        "description": "Aluminum bars",
        "shipper_age_months": 180,  # 15 years old - ESTABLISHED
        "expected_score": 18,
        "expected_tier": "LOW",
        "triggers": [
            "VN-US corridor (12 pts H1)",
            "No duties on 7610 (0 pts H1)",
            "Established shipper 15y (0 pts H1)",
            "Fair pricing (0 pts H1)",
            "Normal dwell 3.2d vs 2.8d (4 pts H2)",
            "No ISF mismatch (0 pts H2)",
            "Normal AIS (2 pts H2)",
        ]
    },
    "decoy_legit_thai": {
        "shipper": "Bangkok Metals International",
        "shipper_country": "TH",
        "consignee": "American Industrial Supply",
        "consignee_country": "US",
        "manufacturer_origin": "TH",
        "hs_code": "7611",
        "value_usd": 65000,
        "weight_kg": 3500,
        "vessel_name": "MV Bangkok Pride",
        "description": "Aluminum tubes",
        "shipper_age_months": 60,  # 5 years old
        "expected_score": 22,
        "expected_tier": "LOW",
        "triggers": [
            "TH-US corridor elevated (12 pts H1)",
            "No duties (0 pts H1)",
            "Established shipper (0 pts H1)",
            "Fair pricing (0 pts H1)",
            "Dwell 4.1d elevated (8 pts H2)",
            "No mismatch (0 pts H2)",
            "Normal AIS (2 pts H2)",
        ]
    },
    "decoy_legit_sg": {
        "shipper": "TechExport Ltd",
        "shipper_country": "SG",
        "consignee": "GlobalTech Inc",
        "consignee_country": "CA",
        "manufacturer_origin": "SG",
        "hs_code": "8517.62",
        "value_usd": 30000,
        "weight_kg": 1500,
        "vessel_name": "MV Singapore Link",
        "description": "Router devices",
        "shipper_age_months": 120,  # 10 years old
        "expected_score": 29,
        "expected_tier": "LOW",
        "triggers": [
            "SG-CA low-risk corridor (4 pts H1)",
            "No duties (0 pts H1)",
            "Established shipper (0 pts H1)",
            "Fair pricing (0 pts H1)",
            "Normal dwell (4 pts H2)",
            "No mismatch (0 pts H2)",
            "Normal AIS (2 pts H2)",
        ]
    }
}

def create_strategic_manifest():
    """Create Excel manifest with strategic cases."""
    rows = []

    for case_key, case in CASES.items():
        # Calculate incorporation date based on shipper_age_months
        incorporation_date = (datetime.now() - timedelta(days=case["shipper_age_months"]*30)).strftime("%Y-%m-%d")

        row = {
            "shipper": case["shipper"],
            "consignee": case["consignee"],
            "origin_country": case["shipper_country"],
            "destination_country": case["consignee_country"],
            "hs_code": case["hs_code"],
            "value_usd": case["value_usd"],
            "weight_kg": case["weight_kg"],
            "vessel_name": case["vessel_name"],
            "description": case["description"],
            # Extra fields for fixture matching
            "shipper_incorporation_date": incorporation_date,
            "manufacturer_origin": case["manufacturer_origin"],
        }
        rows.append(row)

    df = pd.DataFrame(rows)

    # Save Excel
    output_path = Path("/tmp/strategic_demo_manifest.xlsx")
    df.to_excel(output_path, index=False)
    print(f"✓ Created strategic manifest: {output_path}")
    print(f"  Cases: {len(CASES)} (Greenfield + Solaria + 3 Decoys)")

    return output_path, df

def ingest_manifest(manifest_path):
    """Upload manifest via API."""
    print(f"\nIngesting manifest...")

    with open(manifest_path, "rb") as f:
        files = {"file": f}
        response = requests.post("http://localhost:8000/api/ingest/manifest", files=files)

    if response.status_code == 200:
        result = response.json()
        print(f"✓ Ingested {result['row_count']} shipments")
        return result.get("shipment_ids", [])
    else:
        print(f"✗ Ingest failed: {response.status_code}")
        print(f"  {response.text}")
        return []

def print_summary():
    """Print expected scoring summary."""
    print("\n" + "=" * 70)
    print("STRATEGIC CASES — EXPECTED SCORES")
    print("=" * 70)

    for case_key, case in CASES.items():
        print(f"\n{case['shipper']} → {case['consignee']}")
        print(f"  HTS: {case['hs_code']}")
        print(f"  Corridor: {case['shipper_country']}→{case['consignee_country']}")
        print(f"  Shipper age: {case['shipper_age_months']} months")
        print(f"  Expected Score: {case['expected_score']}/100 ({case['expected_tier']})")
        print(f"  Key Triggers:")
        for trigger in case["triggers"]:
            print(f"    • {trigger}")

if __name__ == "__main__":
    print("🎯 SENTRY CBP — STRATEGIC DEMO CASES")
    print("=" * 70)

    # Create manifest
    manifest_path, df = create_strategic_manifest()
    print_summary()

    # Ingest via API
    print(f"\n" + "=" * 70)
    shipment_ids = ingest_manifest(manifest_path)

    if shipment_ids:
        print(f"\n✓ Ready for scoring!")
        print(f"  Shipment IDs:")
        for i, sid in enumerate(shipment_ids, 1):
            print(f"    {i}. {sid}")
        print(f"\n  Next: POST /api/score/{{shipment_id}} to trigger scoring")

    print("=" * 70)
