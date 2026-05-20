"""
Generate large-scale US manifest seed data for Feb-March 2026
1000+ shipments representing realistic monthly customs volume
"""

import json
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any

# High-risk corridors
HIGH_RISK_CORRIDORS = [
    {"origin": "CN", "destination": "US", "risk": 0.75, "label": "China → USA", "monthly_volume": 280},
    {"origin": "VN", "destination": "US", "risk": 0.68, "label": "Vietnam → USA", "monthly_volume": 150},
    {"origin": "MY", "destination": "US", "risk": 0.62, "label": "Malaysia → USA", "monthly_volume": 120},
]

# Medium-risk corridors
MEDIUM_RISK_CORRIDORS = [
    {"origin": "IN", "destination": "US", "risk": 0.45, "label": "India → USA", "monthly_volume": 95},
    {"origin": "TH", "destination": "US", "risk": 0.40, "label": "Thailand → USA", "monthly_volume": 85},
    {"origin": "ID", "destination": "US", "risk": 0.35, "label": "Indonesia → USA", "monthly_volume": 70},
    {"origin": "PH", "destination": "US", "risk": 0.38, "label": "Philippines → USA", "monthly_volume": 65},
    {"origin": "KH", "destination": "US", "risk": 0.42, "label": "Cambodia → USA", "monthly_volume": 45},
]

# Low-risk corridors
LOW_RISK_CORRIDORS = [
    {"origin": "CA", "destination": "US", "risk": 0.15, "label": "Canada → USA", "monthly_volume": 320},
    {"origin": "MX", "destination": "US", "risk": 0.20, "label": "Mexico → USA", "monthly_volume": 280},
    {"origin": "SG", "destination": "US", "risk": 0.25, "label": "Singapore → USA", "monthly_volume": 110},
    {"origin": "JP", "destination": "US", "risk": 0.18, "label": "Japan → USA", "monthly_volume": 140},
    {"origin": "KR", "destination": "US", "risk": 0.22, "label": "South Korea → USA", "monthly_volume": 125},
    {"origin": "TW", "destination": "US", "risk": 0.20, "label": "Taiwan → USA", "monthly_volume": 95},
]

# US Ports of Entry (by volume)
US_PORTS = [
    {"code": "LA", "name": "Los Angeles", "state": "CA", "type": "seaport", "share": 0.35},
    {"code": "LB", "name": "Long Beach", "state": "CA", "type": "seaport", "share": 0.20},
    {"code": "HT", "name": "Houston", "state": "TX", "type": "seaport", "share": 0.18},
    {"code": "SV", "name": "Savannah", "state": "GA", "type": "seaport", "share": 0.15},
    {"code": "NY", "name": "New York/Newark", "state": "NY", "type": "seaport", "share": 0.12},
]

# High-susceptibility commodities
SUSCEPTIBLE_COMMODITIES = [
    {
        "hs_code": "7604.29",
        "description": "Aluminum extrusions",
        "ad_cvd_rate": 3.7415,
        "risk_level": "CRITICAL",
        "cases": ["C-570-841", "A-570-070"],
        "base_price_usd_per_kg": 4.50,
        "volume_pct": 0.12
    },
    {
        "hs_code": "8541.40",
        "description": "Solar modules and cells",
        "ad_cvd_rate": 1.75,
        "risk_level": "CRITICAL",
        "cases": ["C-357-809", "A-357-808"],
        "base_price_usd_per_kg": 0.85,
        "volume_pct": 0.14
    },
    {
        "hs_code": "7210.70",
        "description": "Flat-rolled steel (cold-rolled)",
        "ad_cvd_rate": 0.35,
        "risk_level": "HIGH",
        "cases": ["C-489-817"],
        "base_price_usd_per_kg": 0.65,
        "volume_pct": 0.10
    },
    {
        "hs_code": "7225.30",
        "description": "Stainless steel sheets",
        "ad_cvd_rate": 0.18,
        "risk_level": "HIGH",
        "cases": ["C-533-901"],
        "base_price_usd_per_kg": 0.88,
        "volume_pct": 0.08
    },
    {
        "hs_code": "8517.62",
        "description": "Telephone switching equipment",
        "ad_cvd_rate": 0.08,
        "risk_level": "MEDIUM",
        "cases": [],
        "base_price_usd_per_kg": 15.00,
        "volume_pct": 0.06
    },
    {
        "hs_code": "6204.62",
        "description": "Women's trousers (cotton)",
        "ad_cvd_rate": 0.0,
        "risk_level": "LOW",
        "cases": [],
        "base_price_usd_per_kg": 3.20,
        "volume_pct": 0.15
    },
    {
        "hs_code": "6203.42",
        "description": "Men's trousers (cotton)",
        "ad_cvd_rate": 0.0,
        "risk_level": "LOW",
        "cases": [],
        "base_price_usd_per_kg": 3.50,
        "volume_pct": 0.12
    },
    {
        "hs_code": "8471.30",
        "description": "Computer processors",
        "ad_cvd_rate": 0.0,
        "risk_level": "MEDIUM",
        "cases": [],
        "base_price_usd_per_kg": 45.00,
        "volume_pct": 0.11
    },
    {
        "hs_code": "3004.90",
        "description": "Pharmaceutical products",
        "ad_cvd_rate": 0.0,
        "risk_level": "LOW",
        "cases": [],
        "base_price_usd_per_kg": 25.00,
        "volume_pct": 0.07
    },
    {
        "hs_code": "2709.00",
        "description": "Petroleum oils",
        "ad_cvd_rate": 0.0,
        "risk_level": "LOW",
        "cases": [],
        "base_price_usd_per_kg": 0.45,
        "volume_pct": 0.05
    },
]

# Shippers by corridor
SHIPPERS = {
    "CN": [
        "Guangdong Greenfield Aluminum Co., Ltd.",
        "Xiamen Solar Technology Co., Ltd.",
        "Shanghai Steel International Trading",
        "Ningbo Manufacturing Group",
        "Beijing Electronics Ltd.",
        "Wuhan Industrial Corp",
        "Chongqing Export Trading",
        "Suzhou Precision Mfg",
        "Hangzhou Commercial Ltd",
        "Dalian Shipping Corp",
    ],
    "VN": [
        "Vietnam Aluminum Trading Co.",
        "Hanoi Solar Enterprises",
        "Ho Chi Minh Export Corp",
        "Mekong Industrial Trading Ltd.",
        "Saigon Manufacturing",
        "Hanoi Textile Export",
        "Da Nang Industrial",
    ],
    "MY": [
        "Kuala Lumpur Solar Mfg Sdn Bhd",
        "Penang Electronics Trading",
        "Malaysia Industrial Corp",
        "Selangor Manufacturing",
        "Johor Exports Ltd",
    ],
    "IN": [
        "Mumbai Import Export Ltd.",
        "Delhi Trading Corporation",
        "Bangalore Industrial Co.",
        "Chennai Exports",
        "Hyderabad Manufacturing",
    ],
    "TH": [
        "Bangkok Manufacturing Co.",
        "Chiang Mai Trading Ltd.",
        "Phuket Industrial Export",
    ],
    "ID": [
        "Jakarta Industrial Export",
        "Surabaya Trading Co.",
        "Bandung Manufacturing",
    ],
    "PH": [
        "Manila Export Corp",
        "Cebu Trading Ltd",
    ],
    "KH": [
        "Phnom Penh Manufacturing",
        "Sihanoukville Industrial",
    ],
    "CA": [
        "Canadian Aluminum Inc.",
        "Toronto Trading Ltd.",
        "Vancouver Export Corp",
        "Montreal Manufacturing",
    ],
    "MX": [
        "Mexico City Export Corp",
        "Monterrey Trading Ltd.",
        "Guadalajara Manufacturing",
        "Cancun Industrial",
    ],
    "SG": [
        "Singapore Electronics Ltd.",
        "Singapore Trading Hub",
        "Singapore Port Authority",
    ],
    "JP": [
        "Tokyo Manufacturing Corp",
        "Osaka Trading Ltd.",
        "Yokohama Industrial",
    ],
    "KR": [
        "Seoul Electronics Ltd",
        "Busan Trading Corp",
    ],
    "TW": [
        "Taipei Manufacturing",
        "Kaohsiung Trading",
    ],
}

# US Consignees
CONSIGNEES = [
    "SunPath Energy Distributors LLC",
    "Newark Metals Inc.",
    "American Industrial Supply Corp",
    "California Solar Solutions",
    "Texas Manufacturing LLC",
    "Georgia Steel Imports",
    "New York Trading Group",
    "Global Imports USA",
    "Pacific Coast Traders",
    "Great Lakes Import Co",
    "Midwest Industrial Supply",
    "Southeast Trading Corp",
    "Northeast Manufacturing",
    "Southwest Imports Ltd",
    "Central US Distributors",
    "Atlantic Trading Partners",
    "Gulf Coast Industrial",
    "West Coast Supply",
]

# Vessels
VESSELS = [
    "MV Pacific Horizon", "MV Global Trade", "MV Ocean Express",
    "MV Cargo Star", "MV International Flow", "MV Trade Wind",
    "MV Seamless Journey", "MV Atlantic Bridge", "MV Asia Explorer",
    "MV Container Master", "MV Voyage Star", "MV Golden Gate",
    "MV Northern Lights", "MV Eastern Promise", "MV Western Sun",
    "MV Pacific Bridge", "MV Global Gateway", "MV Ocean Master",
]

def generate_manifest_data(
    num_shipments: int = 1200,
    start_date: str = "2026-02-01",
    end_date: str = "2026-03-31"
) -> List[Dict[str, Any]]:
    """Generate large-scale manifest data"""
    manifests = []
    
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    date_range = (end - start).days
    
    shipment_id = 1
    
    # Calculate shipments per corridor based on realistic volumes
    all_corridors = HIGH_RISK_CORRIDORS + MEDIUM_RISK_CORRIDORS + LOW_RISK_CORRIDORS
    total_volume = sum(c["monthly_volume"] for c in all_corridors) * 2  # 2 months
    
    for corridor in all_corridors:
        corridor_shipments = int((corridor["monthly_volume"] / (total_volume / 2)) * num_shipments)
        
        for _ in range(corridor_shipments):
            commodity = random.choices(
                SUSCEPTIBLE_COMMODITIES,
                weights=[c["volume_pct"] for c in SUSCEPTIBLE_COMMODITIES],
                k=1
            )[0]
            
            manifest = _create_manifest(
                shipment_id=f"SHP-{shipment_id:06d}",
                corridor=corridor,
                commodity=commodity,
                start_date=start,
                days_range=date_range
            )
            manifests.append(manifest)
            shipment_id += 1
    
    return manifests[:num_shipments]


def _create_manifest(
    shipment_id: str,
    corridor: Dict,
    commodity: Dict,
    start_date: datetime,
    days_range: int
) -> Dict[str, Any]:
    """Create a single manifest record"""
    
    filing_date = start_date + timedelta(days=random.randint(0, days_range))
    
    shipper = random.choice(SHIPPERS.get(corridor["origin"], ["Unknown Shipper"]))
    consignee = random.choice(CONSIGNEES)
    port = random.choices(US_PORTS, weights=[p["share"] for p in US_PORTS], k=1)[0]
    
    weight_kg = random.randint(500, 100000)
    unit_price = commodity["base_price_usd_per_kg"] * random.uniform(0.7, 1.4)
    total_value = weight_kg * unit_price
    
    # Dwell time varies by risk
    if corridor["risk"] > 0.6:
        dwell_days = random.uniform(4, 16)
    elif corridor["risk"] > 0.35:
        dwell_days = random.uniform(2, 6)
    else:
        dwell_days = random.uniform(0.5, 3)
    
    vessel = random.choice(VESSELS)
    
    declared_origin = corridor["origin"]
    if random.random() < (0.20 if corridor["risk"] > 0.6 else 0.08):
        isf_origin = random.choice(["CN", "VN", "MY"])
    else:
        isf_origin = declared_origin
    
    # Calculate risk score
    corridor_score = corridor["risk"] * 50
    commodity_score = (40 if commodity["risk_level"] == "CRITICAL" else 
                      25 if commodity["risk_level"] == "HIGH" else
                      15 if commodity["risk_level"] == "MEDIUM" else 5)
    base_score = min(100, int(corridor_score + commodity_score * 0.5))
    
    return {
        "id": shipment_id,
        "manifest_id": f"MNF-2026-{shipment_id}",
        "filing_date": filing_date.isoformat(),
        "shipper_name": shipper,
        "shipper_country": corridor["origin"],
        "consignee_name": consignee,
        "consignee_country": "US",
        "hs_code": commodity["hs_code"],
        "commodity_description": commodity["description"],
        "declared_value_usd": round(total_value, 2),
        "declared_weight_kg": weight_kg,
        "origin_country": corridor["origin"],
        "destination_country": "US",
        "destination_port": port["code"],
        "destination_port_name": port["name"],
        "destination_state": port["state"],
        "vessel_name": vessel,
        "dwell_days": round(dwell_days, 1),
        "declared_origin": declared_origin,
        "ais_stuffing_country": isf_origin,
        "port_calls": [corridor["origin"], "SG", "US"],
        "shipper_age_months": random.randint(2, 180),
        "importer_age_months": random.randint(6, 300),
        "ad_cvd_applicable": "Yes" if commodity["ad_cvd_rate"] > 0 else "No",
        "ad_cvd_rate": round(commodity["ad_cvd_rate"], 2),
        "ad_cvd_cases": commodity["cases"],
        "commodity_risk_level": commodity["risk_level"],
        "corridor_risk": corridor["risk"],
        "corridor_label": corridor["label"],
        "risk_score": base_score,
        "status": "FILED",
        "created_at": filing_date.isoformat(),
    }


if __name__ == "__main__":
    manifests = generate_manifest_data(num_shipments=1200)
    
    output_file = "/home/rahulvadera/cbp-sentry/api/seed_data/manifest_feb_march_2026.json"
    with open(output_file, "w") as f:
        json.dump(manifests, f, indent=2)
    
    print(f"✅ Generated {len(manifests)} manifest records")
    print(f"📁 Saved to {output_file}")
    print(f"💾 File size: {len(json.dumps(manifests)) / (1024*1024):.2f} MB\n")
    
    # Print summary statistics
    print("=" * 80)
    print("📊 DATA DISTRIBUTION SUMMARY")
    print("=" * 80)
    
    # By corridor
    corridors = {}
    for m in manifests:
        corridor = m["corridor_label"]
        corridors[corridor] = corridors.get(corridor, 0) + 1
    
    print("\n📍 BY CORRIDOR (Origin → Destination):")
    print("-" * 60)
    for corridor, count in sorted(corridors.items(), key=lambda x: x[1], reverse=True):
        pct = count/len(manifests)*100
        bar = "█" * int(pct/2)
        print(f"  {corridor:25s} {count:3d} shipments ({pct:5.1f}%) {bar}")
    
    # By port
    ports = {}
    for m in manifests:
        port = m["destination_port_name"]
        ports[port] = ports.get(port, 0) + 1
    
    print("\n🏭 BY US PORT OF ENTRY:")
    print("-" * 60)
    for port, count in sorted(ports.items(), key=lambda x: x[1], reverse=True):
        pct = count/len(manifests)*100
        bar = "█" * int(pct/2)
        print(f"  {port:25s} {count:3d} shipments ({pct:5.1f}%) {bar}")
    
    # By commodity
    commodities = {}
    for m in manifests:
        hs = m["hs_code"]
        desc = m["commodity_description"]
        key = f"{hs} - {desc}"
        commodities[key] = commodities.get(key, 0) + 1
    
    print("\n📦 BY COMMODITY (HS Code):")
    print("-" * 60)
    for commodity, count in sorted(commodities.items(), key=lambda x: x[1], reverse=True):
        pct = count/len(manifests)*100
        bar = "█" * int(pct/2)
        print(f"  {commodity:40s} {count:3d} ({pct:5.1f}%) {bar}")
    
    # By risk level
    risk_levels = {}
    for m in manifests:
        risk = m["commodity_risk_level"]
        risk_levels[risk] = risk_levels.get(risk, 0) + 1
    
    print("\n⚠️  BY RISK LEVEL:")
    print("-" * 60)
    for risk in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
        if risk in risk_levels:
            count = risk_levels[risk]
            pct = count/len(manifests)*100
            bar = "█" * int(pct/2)
            print(f"  {risk:15s} {count:3d} shipments ({pct:5.1f}%) {bar}")
    
    # Value summary
    total_value = sum(m["declared_value_usd"] for m in manifests)
    total_weight = sum(m["declared_weight_kg"] for m in manifests)
    
    print("\n💰 VALUE & WEIGHT SUMMARY:")
    print("-" * 60)
    print(f"  Total Declared Value: ${total_value:,.0f}")
    print(f"  Total Weight: {total_weight:,.0f} kg ({total_weight/1000:,.0f} metric tonnes)")
    print(f"  Average Shipment Value: ${total_value/len(manifests):,.0f}")
    print(f"  Average Shipment Weight: {total_weight/len(manifests):,.0f} kg")
    
    # Risk score distribution
    high_risk = sum(1 for m in manifests if m["risk_score"] >= 70)
    medium_risk = sum(1 for m in manifests if 40 <= m["risk_score"] < 70)
    low_risk = sum(1 for m in manifests if m["risk_score"] < 40)
    
    print("\n🎯 RISK SCORE DISTRIBUTION:")
    print("-" * 60)
    print(f"  HIGH (≥70):    {high_risk:3d} shipments ({high_risk/len(manifests)*100:5.1f}%)")
    print(f"  MEDIUM (40-70): {medium_risk:3d} shipments ({medium_risk/len(manifests)*100:5.1f}%)")
    print(f"  LOW (<40):     {low_risk:3d} shipments ({low_risk/len(manifests)*100:5.1f}%)")
    
    print("\n" + "=" * 80)

