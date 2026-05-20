"""Seed database with realistic CBP shipment data"""
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

SAMPLE_SHIPMENTS = [
    {
        "id": "SHIP-2026-001",
        "manifest_id": "MANIFEST-2026-001",
        "shipper_name": "Greenfield Industrial Trading Co., Ltd",
        "origin_country": "VN",
        "consignee_name": "SunPath Energy Distributors LLC",
        "destination_country": "US",
        "hs_code": "7604.29",
        "declared_value_usd": 50000,
        "declared_weight_kg": 5000,
        "risk_score": 91,
        "h1_score": 40,
        "h2_score": 35,
        "vessel_name": "MV Pacific Horizon",
        "status": "received",
    },
    {
        "id": "SHIP-2026-002",
        "manifest_id": "MANIFEST-2026-002",
        "shipper_name": "Solaria Manufacturing Sdn. Bhd.",
        "origin_country": "MY",
        "consignee_name": "SunPath Energy Distributors LLC",
        "destination_country": "US",
        "hs_code": "8541.40",
        "declared_value_usd": 75000,
        "declared_weight_kg": 2000,
        "risk_score": 65,
        "h1_score": 32,
        "h2_score": 24,
        "vessel_name": "MV Solar Express",
        "status": "received",
    },
    {
        "id": "SHIP-2026-003",
        "manifest_id": "MANIFEST-2026-003",
        "shipper_name": "Vietnam Aluminum Corp",
        "origin_country": "VN",
        "consignee_name": "Newark Metals Inc",
        "destination_country": "US",
        "hs_code": "7610",
        "declared_value_usd": 45000,
        "declared_weight_kg": 4500,
        "risk_score": 18,
        "h1_score": 12,
        "h2_score": 4,
        "vessel_name": "MV Hanoi Star",
        "status": "received",
    },
    {
        "id": "SHIP-2026-004",
        "manifest_id": "MANIFEST-2026-004",
        "shipper_name": "Bangkok Metals International",
        "origin_country": "TH",
        "consignee_name": "American Industrial Supply",
        "destination_country": "US",
        "hs_code": "7611",
        "declared_value_usd": 65000,
        "declared_weight_kg": 3500,
        "risk_score": 22,
        "h1_score": 14,
        "h2_score": 6,
        "vessel_name": "MV Bangkok Pride",
        "status": "received",
    },
    {
        "id": "SHIP-2026-005",
        "manifest_id": "MANIFEST-2026-005",
        "shipper_name": "TechExport Ltd",
        "origin_country": "SG",
        "consignee_name": "GlobalTech Inc",
        "destination_country": "CA",
        "hs_code": "8517.62",
        "declared_value_usd": 30000,
        "declared_weight_kg": 1500,
        "risk_score": 29,
        "h1_score": 16,
        "h2_score": 8,
        "vessel_name": "MV Singapore Link",
        "status": "received",
    },
]

def seed_database():
    """Insert sample shipments into database"""
    db_path = Path("/app/data/cbp_sentry.db")
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Insert sample data
    for shipment in SAMPLE_SHIPMENTS:
        cursor.execute("""
            INSERT OR REPLACE INTO shipments
            (id, manifest_id, shipper_name, origin_country, consignee_name, destination_country,
             hs_code, declared_value_usd, declared_weight_kg, risk_score, h1_score, h2_score,
             vessel_name, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, tuple(shipment.values()))

    conn.commit()
    conn.close()
    print(f"✓ Seeded database with {len(SAMPLE_SHIPMENTS)} shipments")

if __name__ == "__main__":
    seed_database()
