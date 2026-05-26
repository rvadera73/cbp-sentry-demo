#!/usr/bin/env python3
"""Test referral endpoint with case ID"""
import sqlite3
import json

db_path = "/home/rahulvadera/cbp-sentry/data/cbp_sentry.db"

try:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Check shipment count
    cursor.execute("SELECT COUNT(*) as count FROM shipments")
    total = cursor.fetchone()['count']
    print(f"✅ Total shipments in database: {total}")

    if total == 0:
        print("❌ No shipments found in database!")
        conn.close()
        exit(1)

    # Get first shipment
    cursor.execute("""
        SELECT id, manifest_id, shipper_name, consignee_name,
               origin_country, destination_country, risk_score,
               h1_score, h2_score
        FROM shipments LIMIT 1
    """)

    shipment = cursor.fetchone()
    print(f"\n📋 First shipment:")
    print(f"  ID: {shipment['id']}")
    print(f"  Shipper: {shipment['shipper_name']}")
    print(f"  Consignee: {shipment['consignee_name']}")
    print(f"  Route: {shipment['origin_country']} → {shipment['destination_country']}")
    print(f"  Risk Score: {shipment['risk_score']}")
    print(f"  H1/H2 Scores: {shipment['h1_score']}/{shipment['h2_score']}")

    # Show sample shipments grouped by route (simulating case grouping)
    cursor.execute("""
        SELECT
            COUNT(*) as count,
            shipper_name,
            origin_country,
            destination_country
        FROM shipments
        GROUP BY shipper_name, origin_country, destination_country
        LIMIT 5
    """)

    print(f"\n🗂️  Sample case groups (shipper/route combinations):")
    groups = cursor.fetchall()
    for idx, group in enumerate(groups):
        case_id = f"CBP-2026-{9000 + idx}"
        print(f"  {case_id}: {group['shipper_name']} ({group['origin_country']}→{group['destination_country']}) - {group['count']} shipments")

    conn.close()
    print(f"\n✅ Database test complete!")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
