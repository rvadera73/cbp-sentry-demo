#!/usr/bin/env python3
"""
Seed database with shipments having varied risk profiles.
This creates shipments with characteristics that will score 95%+ and 60-70%
when processed through the comprehensive risk scoring API.

Usage:
    python3 seed_varied_risks.py
"""

import sqlite3
from datetime import datetime, timedelta
import random

DB_PATH = "/home/rahulvadera/cbp-sentry/data/cbp_sentry.db"

HIGH_RISK_SHIPPERS = [
    # Origin Concealment
    {
        "name": "Shanghai Trade Co.",
        "origin": "CN",
        "destination": "US",
        "hs_code": "6204.29",
        "value": 185000,
        "element9_mismatch": True,
        "declared_country": "VN",
        "actual_country": "CN",
        "shipper_age_months": 2,
        "dwell_days": 9,
        "ad_cvd": True,
        "ad_cvd_rate": 0.25,
        "ports": "HK,SG,LA",
        "vessel_flag": "HK",
        "profile": "Element 9 Mismatch + China Origin + High Tariff"
    },
    # Circular Invoicing
    {
        "name": "Emirates Trade Hub LLC",
        "origin": "AE",
        "destination": "US",
        "hs_code": "9011.90",
        "value": 45000,
        "element9_mismatch": False,
        "declared_country": "AE",
        "actual_country": "AE",
        "shipper_age_months": 6,
        "dwell_days": 2,
        "ad_cvd": False,
        "ad_cvd_rate": 0,
        "ports": "AE,HK,LA",
        "vessel_flag": "LB",
        "profile": "Tech re-export + Low value/high volume pattern"
    },
    # UFLPA Controlled
    {
        "name": "Xinjiang Cotton Mills Trading",
        "origin": "CN",
        "destination": "US",
        "hs_code": "5208.11",
        "value": 280000,
        "element9_mismatch": False,
        "declared_country": "CN",
        "actual_country": "CN",
        "shipper_age_months": 48,
        "dwell_days": 1,
        "ad_cvd": False,
        "ad_cvd_rate": 0,
        "ports": "CN,LA",
        "vessel_flag": "CN",
        "profile": "UFLPA Cotton + China Origin",
        "ofac_match": True
    },
    # Multiple Red Flags
    {
        "name": "Pacific Logistics Ltd",
        "origin": "CN",
        "destination": "US",
        "hs_code": "2933.99",
        "value": 156000,
        "element9_mismatch": True,
        "declared_country": "MY",
        "actual_country": "CN",
        "shipper_age_months": 1,
        "dwell_days": 8,
        "ad_cvd": True,
        "ad_cvd_rate": 0.30,
        "ports": "CN,SG,HK,LA",
        "vessel_flag": "PA",
        "profile": "New shipper + Element 9 mismatch + High dwell + High AD/CVD"
    },
    # Sanctions Adjacent
    {
        "name": "Tehran Trade Company",
        "origin": "AE",
        "destination": "US",
        "hs_code": "8517.62",
        "value": 125000,
        "element9_mismatch": False,
        "declared_country": "AE",
        "actual_country": "AE",
        "shipper_age_months": 18,
        "dwell_days": 3,
        "ad_cvd": True,
        "ad_cvd_rate": 0.20,
        "ports": "AE,LA",
        "vessel_flag": "AE",
        "profile": "RE-export from OFAC-adjacent country"
    },
]

MEDIUM_RISK_SHIPPERS = [
    # New Shipper
    {
        "name": "Tech Solutions Inc (New)",
        "origin": "CA",
        "destination": "US",
        "hs_code": "8471.30",
        "value": 95000,
        "element9_mismatch": False,
        "declared_country": "CA",
        "actual_country": "CA",
        "shipper_age_months": 1,
        "dwell_days": 2,
        "ad_cvd": False,
        "ad_cvd_rate": 0,
        "ports": "CA,LA",
        "vessel_flag": "CA",
        "profile": "New Shipper < 3 months"
    },
    # Transshipment Dwell
    {
        "name": "Singapore Trade Partners",
        "origin": "MY",
        "destination": "US",
        "hs_code": "3926.30",
        "value": 125000,
        "element9_mismatch": False,
        "declared_country": "MY",
        "actual_country": "MY",
        "shipper_age_months": 36,
        "dwell_days": 7,  # 3.5x normal baseline
        "ad_cvd": True,
        "ad_cvd_rate": 0.05,
        "ports": "MY,SG,LA",
        "vessel_flag": "SG",
        "profile": "Dwell Anomaly at Transshipment + AD/CVD"
    },
    # AD/CVD Corridor Risk
    {
        "name": "Vietnam Aluminum Ltd",
        "origin": "VN",
        "destination": "US",
        "hs_code": "7610.10",
        "value": 156000,
        "element9_mismatch": False,
        "declared_country": "VN",
        "actual_country": "VN",
        "shipper_age_months": 48,
        "dwell_days": 3,
        "ad_cvd": True,
        "ad_cvd_rate": 0.12,  # Active AD/CVD order
        "ports": "VN,SG,LA",
        "vessel_flag": "VN",
        "profile": "AD/CVD Corridor (VN→US) + 12% Duty"
    },
    # New but Compliant
    {
        "name": "Mexican Auto Parts SA",
        "origin": "MX",
        "destination": "US",
        "hs_code": "8708.99",
        "value": 185000,
        "element9_mismatch": False,
        "declared_country": "MX",
        "actual_country": "MX",
        "shipper_age_months": 2,
        "dwell_days": 1,
        "ad_cvd": False,
        "ad_cvd_rate": 0,
        "ports": "MX,LA",
        "vessel_flag": "MX",
        "profile": "New Shipper + Clean Documentation"
    },
    # China with Single Red Flag
    {
        "name": "Beijing Electronics Ltd",
        "origin": "CN",
        "destination": "US",
        "hs_code": "8534.30",
        "value": 105000,
        "element9_mismatch": False,
        "declared_country": "CN",
        "actual_country": "CN",
        "shipper_age_months": 24,
        "dwell_days": 2,
        "ad_cvd": True,
        "ad_cvd_rate": 0.08,
        "ports": "CN,LA",
        "vessel_flag": "CN",
        "profile": "Established China Shipper + Moderate AD/CVD"
    },
    # Low Value High Frequency Pattern
    {
        "name": "Fashion Trade Group",
        "origin": "IN",
        "destination": "US",
        "hs_code": "6204.29",
        "value": 35000,
        "element9_mismatch": False,
        "declared_country": "IN",
        "actual_country": "IN",
        "shipper_age_months": 12,
        "dwell_days": 2,
        "ad_cvd": False,
        "ad_cvd_rate": 0,
        "ports": "IN,SG,LA",
        "vessel_flag": "IN",
        "profile": "Low Value, Potential Structuring Pattern"
    },
]

def create_shipment(conn, shipper_info, quantity=1):
    """Create shipment records with given characteristics."""
    cursor = conn.cursor()

    for i in range(quantity):
        shipment_id = f"SHP-{random.randint(100000, 999999)}"
        manifest_id = f"MNF-2026-{shipment_id}"

        # Vary dates slightly
        days_offset = random.randint(0, 30)
        created_date = (datetime.now() - timedelta(days=days_offset)).isoformat() + "Z"

        try:
            cursor.execute("""
                INSERT INTO shipments (
                    id, manifest_id, shipper_name, consignee_name,
                    origin_country, destination_country,
                    hs_code, declared_value_usd, declared_weight_kg,
                    description, vessel_name, vessel_imo, vessel_flag,
                    dwell_days, ais_stuffing_country, port_calls,
                    element9_is_mismatch, element9_declared_country, element9_actual_country,
                    shipper_age_months, shipper_country, consignee_country,
                    ad_cvd_rate, ad_cvd_applicable,
                    status, risk_score, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                shipment_id,
                manifest_id,
                shipper_info["name"],
                "Import Warehouse Inc",
                shipper_info["origin"],
                shipper_info["destination"],
                shipper_info["hs_code"],
                shipper_info["value"],
                random.randint(100, 5000),
                f"Commodity HS {shipper_info['hs_code']}",
                f"MV {shipper_info['name'].split()[0]}",
                f"{random.randint(9000000, 9999999)}",
                shipper_info["vessel_flag"],
                shipper_info["dwell_days"],
                shipper_info["origin"],
                shipper_info["ports"],
                1 if shipper_info["element9_mismatch"] else 0,
                shipper_info["declared_country"],
                shipper_info["actual_country"],
                shipper_info["shipper_age_months"],
                shipper_info["origin"],
                "US",
                shipper_info["ad_cvd_rate"],
                1 if shipper_info["ad_cvd"] else 0,
                "FILED",
                0,  # Will be calculated dynamically
                created_date
            ))
            print(f"✓ Created: {shipment_id} - {shipper_info['profile']}")
        except Exception as e:
            print(f"✗ Failed: {shipper_info['name']} - {e}")

def seed_database():
    """Populate database with varied risk profiles."""
    conn = sqlite3.connect(DB_PATH)

    print("\n" + "="*70)
    print("SEEDING HIGH-RISK SHIPMENTS (Expected Score: 90-99%)")
    print("="*70)

    for shipper in HIGH_RISK_SHIPPERS:
        create_shipment(conn, shipper, quantity=3)

    print("\n" + "="*70)
    print("SEEDING MEDIUM-RISK SHIPMENTS (Expected Score: 60-70%)")
    print("="*70)

    for shipper in MEDIUM_RISK_SHIPPERS:
        create_shipment(conn, shipper, quantity=4)

    conn.commit()
    conn.close()

    print("\n" + "="*70)
    print("✅ SEEDING COMPLETE")
    print("="*70)
    print("\nNext steps:")
    print("1. Call /api/risk-scoring/comprehensive for each shipment")
    print("2. Verify high-risk shipments score 90%+")
    print("3. Verify medium-risk shipments score 60-70%")
    print("4. Check Altana API calls for risk >= 80%")
    print("\nTest command:")
    print('  curl -X POST http://localhost:8000/api/risk-scoring/comprehensive \\')
    print('    -H "Content-Type: application/json" \\')
    print('    -d \'{"shipment_id": "SHP-XXXXX"}\'')

if __name__ == "__main__":
    seed_database()
