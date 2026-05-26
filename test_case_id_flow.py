#!/usr/bin/env python3
"""
Trace the flow of CBP-2026-9000 case ID through the system
"""
import sqlite3
import json
import sys

print("=" * 70)
print("🧪 TRACING: CBP-2026-9000 → Referral API Flow")
print("=" * 70)

db_path = "/home/rahulvadera/cbp-sentry/data/cbp_sentry.db"

try:
    # Step 1: Check database
    print("\n1️⃣  Checking database...")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) as count FROM shipments")
    total_shipments = cursor.fetchone()['count']
    print(f"   Total shipments in DB: {total_shipments}")

    if total_shipments == 0:
        print("   ❌ ERROR: No shipments in database!")
        print("   Run: docker-compose up to load seed data")
        sys.exit(1)

    # Step 2: Show how cases are grouped
    print("\n2️⃣  Case grouping (shipper / origin → destination):")
    cursor.execute("""
        SELECT
            COUNT(*) as count,
            shipper_name,
            origin_country,
            destination_country
        FROM shipments
        GROUP BY shipper_name, origin_country, destination_country
        ORDER BY count DESC
        LIMIT 5
    """)

    cases = cursor.fetchall()
    for idx, case in enumerate(cases):
        case_id = f"CBP-2026-{9000 + idx}"
        print(f"\n   Case ID: {case_id}")
        print(f"     Shipper: {case['shipper_name']}")
        print(f"     Route: {case['origin_country']} → {case['destination_country']}")
        print(f"     Shipments: {case['count']}")

    # Step 3: Show first shipment that would be used
    print("\n3️⃣  When API gets CBP-2026-9000, it does:")
    print("   a) Fetch /shipments?limit=1000&offset=0 from data service")
    print("   b) Take first shipment from results")

    cursor.execute("""
        SELECT
            id, manifest_id, shipper_name, consignee_name,
            origin_country, destination_country, risk_score,
            h1_score, h2_score, vessel_name, hs_code
        FROM shipments
        LIMIT 1
    """)

    first_shipment = cursor.fetchone()
    if first_shipment:
        print(f"\n   ✅ First shipment found:")
        print(f"      ID: {first_shipment['id']}")
        print(f"      Shipper: {first_shipment['shipper_name']}")
        print(f"      Consignee: {first_shipment['consignee_name']}")
        print(f"      Route: {first_shipment['origin_country']} → {first_shipment['destination_country']}")
        print(f"      Risk Score: {first_shipment['risk_score']}")
        print(f"      H1/H2 Scores: {first_shipment['h1_score']}/{first_shipment['h2_score']}")
        print(f"      Vessel: {first_shipment['vessel_name']}")
        print(f"      HS Code: {first_shipment['hs_code']}")

        # Step 4: Check required fields
        print("\n4️⃣  Required fields for referral (from API code):")
        required_fields = {
            'shipper_name': 'Shipper',
            'consignee_name': 'Consignee',
            'origin_country': 'Origin',
            'destination_country': 'Destination',
            'hs_code': 'HS Code',
            'declared_value_usd': 'Declared Value',
            'declared_weight_kg': 'Weight',
            'vessel_name': 'Vessel',
            'manifest_id': 'Manifest ID',
            'risk_score': 'Risk Score',
        }

        missing = []
        for field, label in required_fields.items():
            val = first_shipment[field]
            status = "✅" if val else "❌"
            print(f"   {status} {label}: {val}")
            if not val:
                missing.append(field)

        if missing:
            print(f"\n   ⚠️  Missing fields: {missing}")
            print(f"   The referral will use defaults for missing fields")

        # Step 5: Test the API endpoint
        print("\n5️⃣  To test the API endpoint:")
        print(f"\n   curl -X GET http://localhost:8000/api/referral/CBP-2026-9000")
        print(f"\n   Or with shipment UUID:")
        print(f"   curl -X GET http://localhost:8000/api/referral/{first_shipment['id']}")

    else:
        print("   ❌ ERROR: No shipments found to use as first")

    conn.close()
    print("\n" + "=" * 70)
    print("✅ Diagnostic complete")
    print("=" * 70)

except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
