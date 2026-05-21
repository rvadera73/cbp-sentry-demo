#!/usr/bin/env python3
"""
Standalone test script for Risk Corridors API
"""
import sys
sys.path.insert(0, 'api')

from fastapi.testclient import TestClient
from datetime import datetime
from api.main import app
from api.services.risk_corridors.db import init_risk_corridor_tables

def test_all():
    init_risk_corridor_tables()
    client = TestClient(app)

    print("\n" + "="*60)
    print("RISK CORRIDORS API TEST SUITE")
    print("="*60)

    # Test 1: List risk corridors
    print("\nTest 1: GET /api/risk-corridors")
    response = client.get("/api/risk-corridors")
    print(f"  Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"  ✓ Got response with {len(data['corridors'])} corridors")
        if data['corridors']:
            corridor = data['corridors'][0]
            print(f"    First corridor: {corridor['corridor_id']}")
            print(f"    Risk level: {corridor['risk_level']}")
            print(f"    Shipments: {corridor['shipment_count']}")
            print(f"    Value: ${corridor['aggregate_value_usd']:,}")
    else:
        print(f"  ✗ Error: {response.text}")
        return False

    # Test 2: Get corridor detail
    print("\nTest 2: GET /api/risk-corridors/{corridor_id}")
    response = client.get("/api/risk-corridors")
    if response.status_code == 200:
        data = response.json()
        if len(data['corridors']) > 0:
            corridor_id = data['corridors'][0]['corridor_id']
            print(f"  Using corridor: {corridor_id}")
            response = client.get(f"/api/risk-corridors/{corridor_id}")
            print(f"  Status: {response.status_code}")
            if response.status_code == 200:
                detail = response.json()
                print(f"  ✓ Got corridor detail")
                print(f"    Active vessels: {len(detail['corridor']['active_vessels'])}")
                print(f"    Entity chain levels: {len([k for k in detail['entity_chain'].keys() if k.startswith('level')])}")
            else:
                print(f"  ✗ Error: {response.text}")
                return False
        else:
            print("  No corridors found in database")

    # Test 3: Vessels by port
    print("\nTest 3: GET /api/ports/{port_code}/vessels-of-interest")
    response = client.get("/api/ports/USLA/vessels-of-interest")
    print(f"  Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"  ✓ Got response with {len(data['vessels_of_interest'])} vessels of interest")
        print(f"    Total vessels at port: {data['summary']['total_vessels_at_port']}")
        print(f"    High risk count: {data['summary']['high_risk_count']}")
    else:
        print(f"  ✗ Error: {response.text}")
        return False

    # Test 4: Timeline
    print("\nTest 4: GET /api/risk-corridors/{corridor_id}/timeline")
    response = client.get("/api/risk-corridors")
    if response.status_code == 200:
        data = response.json()
        if len(data['corridors']) > 0:
            corridor_id = data['corridors'][0]['corridor_id']
            response = client.get(f"/api/risk-corridors/{corridor_id}/timeline?start_date=2026-05-13&end_date=2026-05-20")
            print(f"  Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"  ✓ Got timeline with {len(data['timeline_snapshots'])} snapshots")
                print(f"    Entity formations: {data['entity_evolution']['entities_formed']}")
            else:
                print(f"  ✗ Error: {response.text}")
                return False

    # Test 5: Feedback override
    print("\nTest 5: POST /api/feedback/override")
    payload = {
        "shipment_id": "MANIFEST-TEST-001",
        "corridor_id": "HC-7604-VNUS-GDF",
        "risk_score_original": 91.0,
        "override_action": "MARK_FALSE_POSITIVE",
        "justification_category": "VERIFIED_LABOR_STRIKE_PORT_DELAY",
        "justification_detail": "Port delay test",
        "officer_id": "CBP-12345",
        "override_timestamp": datetime.now().isoformat(),
    }
    response = client.post("/api/feedback/override", json=payload)
    print(f"  Status: {response.status_code}")
    if response.status_code == 201:
        data = response.json()
        print(f"  ✓ Override logged: {data['override_id']}")
        print(f"    Status: {data['status']}")
        print(f"    Next training window: {data['next_model_training_window']}")
    else:
        print(f"  ✗ Error: {response.text}")
        return False

    # Test 6: Filter by industry
    print("\nTest 6: GET /api/risk-corridors?industry_filter=7604,8541")
    response = client.get("/api/risk-corridors?industry_filter=7604,8541")
    print(f"  Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"  ✓ Got {len(data['corridors'])} filtered corridors")
    else:
        print(f"  ✗ Error: {response.text}")
        return False

    # Test 7: Different time periods
    print("\nTest 7: GET /api/risk-corridors with different time periods")
    for period in ["7d", "14d", "30d"]:
        response = client.get(f"/api/risk-corridors?time_period={period}")
        print(f"  {period}: Status {response.status_code}")
        if response.status_code != 200:
            print(f"    ✗ Error: {response.text}")
            return False
    print("  ✓ All time periods work")

    # Test 8: Different port codes
    print("\nTest 8: GET /api/ports/{port_code}/vessels-of-interest (different ports)")
    for port in ["USLA", "USLB", "USNJ"]:
        response = client.get(f"/api/ports/{port}/vessels-of-interest")
        print(f"  {port}: Status {response.status_code}")
        if response.status_code != 200:
            print(f"    ✗ Error: {response.text}")
            return False
    print("  ✓ All port codes work")

    print("\n" + "="*60)
    print("✓ ALL TESTS PASSED")
    print("="*60)
    return True

if __name__ == "__main__":
    success = test_all()
    sys.exit(0 if success else 1)
