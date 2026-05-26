#!/usr/bin/env python3
"""Test the referral API endpoint with case IDs"""
import requests
import json

# Test with local API (assuming it's running)
API_URL = "http://localhost:8000"

print("🧪 Testing Referral API Endpoint\n")
print("=" * 60)

# Test 1: Try with case ID
case_id = "CBP-2026-9000"
print(f"\n1️⃣  Testing with Case ID: {case_id}")
print(f"   Endpoint: GET {API_URL}/api/referral/{case_id}")

try:
    response = requests.get(f"{API_URL}/api/referral/{case_id}", timeout=10)
    print(f"   Status Code: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ SUCCESS - Got referral data")
        print(f"   Response keys: {list(data.keys())}")
        if 'sections' in data:
            print(f"   Sections available: {list(data['sections'].keys())[:3]}...")
        if 'error' not in data:
            print(f"   Shipment ID: {data.get('shipment_id')}")
            print(f"   Risk Score: {data.get('risk_score')}")
            print(f"   Risk Tier: {data.get('risk_tier')}")
        else:
            print(f"   ❌ Error in response: {data.get('error')}")
    else:
        print(f"   ❌ FAILED")
        try:
            print(f"   Response: {response.json()}")
        except:
            print(f"   Response: {response.text[:200]}")

except requests.exceptions.ConnectionError:
    print(f"   ❌ Connection failed - API not running at {API_URL}")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Test 2: Try with actual shipment UUID (if we can get one)
print(f"\n2️⃣  To get a real shipment UUID, check the database:")
print(f"   sqlite3 /home/rahulvadera/cbp-sentry/data/cbp_sentry.db")
print(f"   SELECT id FROM shipments LIMIT 1;")
print(f"\n   Then test with:")
print(f"   curl http://localhost:8000/api/referral/<UUID>")

print("\n" + "=" * 60)
print("\n📝 Expected successful response format:")
print("""
{
  "shipment_id": "uuid-here",
  "referral_id": "uuid-here",
  "created_at": "2026-05-26T...",
  "risk_score": 75.5,
  "risk_tier": "HIGH",
  "sections": {
    "section_3_1_shipment_identification": {...},
    "section_3_2_line_items": {...},
    ...
  }
}
""")
