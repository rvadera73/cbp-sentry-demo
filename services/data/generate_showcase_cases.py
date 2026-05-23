#!/usr/bin/env python3
"""
Generate 25 showcase investigation cases across 3 risk bands for demo/training.
- 10 CRITICAL (90-97%) cases
- 5 HIGH (80-87%) cases
- 10 ELEVATED (62-69%) cases

Appends to manifest_demo_cases.json in the correct format.
"""

import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path

def generate_showcase_cases():
    """Generate 25 realistic trade fraud cases."""
    cases = []

    # Base date for variety
    base_date = datetime(2026, 2, 15)

    # ==================== CRITICAL (90-97%) ====================
    # These are clear-cut illegal transshipment with all red flags
    critical_specs = [
        {
            "shipper": "Guangzhou Electronics Trading Ltd.",
            "origin": "CN", "declared": "VN",
            "hs": "8542.31", "commodity": "Semiconductor Components",
            "dwell": 12.5, "age_months": 7,
            "ad_cvd": 3.95, "risk_score": 95,
            "h1": 40, "h2": 35, "h3": 18,
        },
        {
            "shipper": "Hanoi Industrial Aluminum Co.",
            "origin": "CN", "declared": "VN",
            "hs": "7604.29", "commodity": "Aluminum Extrusions",
            "dwell": 11.8, "age_months": 9,
            "ad_cvd": 3.74, "risk_score": 94,
            "h1": 40, "h2": 35, "h3": 17,
        },
        {
            "shipper": "Bangkok Manufacturing Solutions",
            "origin": "CN", "declared": "TH",
            "hs": "8541.40", "commodity": "Solar Panel Cells",
            "dwell": 13.2, "age_months": 5,
            "ad_cvd": 2.45, "risk_score": 92,
            "h1": 40, "h2": 35, "h3": 16,
        },
        {
            "shipper": "Malaysian Steel Trading Corporation",
            "origin": "CN", "declared": "MY",
            "hs": "7306.30", "commodity": "Steel Tubes & Pipes",
            "dwell": 10.9, "age_months": 8,
            "ad_cvd": 3.12, "risk_score": 91,
            "h1": 40, "h2": 34, "h3": 15,
        },
        {
            "shipper": "Phnom Penh Import-Export Ltd.",
            "origin": "CN", "declared": "KH",
            "hs": "6203.42", "commodity": "Men's Cotton Apparel",
            "dwell": 11.5, "age_months": 6,
            "ad_cvd": 2.89, "risk_score": 90,
            "h1": 40, "h2": 34, "h3": 15,
        },
        {
            "shipper": "Shenyang Trade & Logistics Co.",
            "origin": "CN", "declared": "VN",
            "hs": "8504.40", "commodity": "Electronic Power Converters",
            "dwell": 12.1, "age_months": 4,
            "ad_cvd": 4.12, "risk_score": 96,
            "h1": 40, "h2": 35, "h3": 19,
        },
        {
            "shipper": "Ho Chi Minh Agricultural Products",
            "origin": "CN", "declared": "VN",
            "hs": "2304.90", "commodity": "Soya Flour & Meal",
            "dwell": 11.2, "age_months": 10,
            "ad_cvd": 1.85, "risk_score": 93,
            "h1": 40, "h2": 35, "h3": 17,
        },
        {
            "shipper": "Jakarta Chemical Import Corporation",
            "origin": "CN", "declared": "ID",
            "hs": "2817.00", "commodity": "Zinc Chloride",
            "dwell": 10.6, "age_months": 11,
            "ad_cvd": 2.34, "risk_score": 91,
            "h1": 40, "h2": 34, "h3": 16,
        },
        {
            "shipper": "Singapore Precision Manufacturing",
            "origin": "CN", "declared": "SG",
            "hs": "8471.30", "commodity": "Computer Processors",
            "dwell": 12.8, "age_months": 3,
            "ad_cvd": 3.56, "risk_score": 94,
            "h1": 40, "h2": 35, "h3": 18,
        },
        {
            "shipper": "Myanmar Trade Development Ltd.",
            "origin": "CN", "declared": "MM",
            "hs": "7225.40", "commodity": "Flat-Rolled Iron Products",
            "dwell": 11.3, "age_months": 12,
            "ad_cvd": 3.45, "risk_score": 92,
            "h1": 40, "h2": 34, "h3": 16,
        },
    ]

    # ==================== HIGH (80-87%) ====================
    # Element 9 mismatch + AD/CVD but more established
    high_specs = [
        {
            "shipper": "Vietnam Ceramics Trading House",
            "origin": "CN", "declared": "VN",
            "hs": "6907.90", "commodity": "Ceramic Wall Tiles",
            "dwell": 7.2, "age_months": 22,
            "ad_cvd": 2.15, "risk_score": 85,
            "h1": 38, "h2": 30, "h3": 14,
        },
        {
            "shipper": "Thai Industrial Metals Corporation",
            "origin": "CN", "declared": "TH",
            "hs": "7408.11", "commodity": "Copper Wire",
            "dwell": 6.8, "age_months": 19,
            "ad_cvd": 1.92, "risk_score": 83,
            "h1": 37, "h2": 29, "h3": 13,
        },
        {
            "shipper": "Malaysian Chemical Products Ltd.",
            "origin": "CN", "declared": "MY",
            "hs": "2905.11", "commodity": "Methanol",
            "dwell": 5.5, "age_months": 26,
            "ad_cvd": 1.45, "risk_score": 82,
            "h1": 36, "h2": 28, "h3": 13,
        },
        {
            "shipper": "Cambodian Garment Manufacturing",
            "origin": "CN", "declared": "KH",
            "hs": "6110.30", "commodity": "Knit Apparel",
            "dwell": 6.1, "age_months": 24,
            "ad_cvd": 1.65, "risk_score": 84,
            "h1": 37, "h2": 29, "h3": 14,
        },
        {
            "shipper": "Indonesian Glass Products Exporter",
            "origin": "CN", "declared": "ID",
            "hs": "7007.19", "commodity": "Tempered Glass Sheets",
            "dwell": 7.9, "age_months": 18,
            "ad_cvd": 2.08, "risk_score": 86,
            "h1": 39, "h2": 30, "h3": 14,
        },
    ]

    # ==================== ELEVATED (62-69%) ====================
    # Suspicious routing/pricing but no direct element 9 mismatch
    elevated_specs = [
        {
            "shipper": "Vietnam Trade Partners LLC",
            "origin": "VN", "declared": "VN",
            "hs": "7604.29", "commodity": "Aluminum Extrusions",
            "dwell": 3.2, "age_months": 45,
            "ad_cvd": 1.12, "risk_score": 65,
            "h1": 22, "h2": 25, "h3": 10,
        },
        {
            "shipper": "Thailand Textile Exporters Association",
            "origin": "TH", "declared": "TH",
            "hs": "6203.42", "commodity": "Cotton Apparel",
            "dwell": 2.8, "age_months": 38,
            "ad_cvd": 1.35, "risk_score": 67,
            "h1": 24, "h2": 26, "h3": 11,
        },
        {
            "shipper": "Malaysian Petrochemical Industries",
            "origin": "MY", "declared": "MY",
            "hs": "2710.19", "commodity": "Petroleum Products",
            "dwell": 3.9, "age_months": 52,
            "ad_cvd": 0.95, "risk_score": 62,
            "h1": 20, "h2": 23, "h3": 10,
        },
        {
            "shipper": "Indonesia Natural Rubber Exporters",
            "origin": "ID", "declared": "ID",
            "hs": "4001.29", "commodity": "Natural Rubber",
            "dwell": 2.1, "age_months": 60,
            "ad_cvd": 1.05, "risk_score": 63,
            "h1": 21, "h2": 24, "h3": 10,
        },
        {
            "shipper": "Cambodia Garment Workers Union",
            "origin": "KH", "declared": "KH",
            "hs": "6110.30", "commodity": "Knit Apparel",
            "dwell": 3.5, "age_months": 35,
            "ad_cvd": 1.28, "risk_score": 66,
            "h1": 23, "h2": 26, "h3": 11,
        },
        {
            "shipper": "Philippines Agricultural Cooperative",
            "origin": "PH", "declared": "PH",
            "hs": "0803.00", "commodity": "Bananas",
            "dwell": 4.2, "age_months": 48,
            "ad_cvd": 0.65, "risk_score": 64,
            "h1": 21, "h2": 25, "h3": 10,
        },
        {
            "shipper": "Vietnam Footwear Manufacturers",
            "origin": "VN", "declared": "VN",
            "hs": "6404.11", "commodity": "Sports Footwear",
            "dwell": 3.1, "age_months": 42,
            "ad_cvd": 1.42, "risk_score": 68,
            "h1": 25, "h2": 27, "h3": 11,
        },
        {
            "shipper": "Singapore Trade & Logistics Hub",
            "origin": "SG", "declared": "SG",
            "hs": "8708.99", "commodity": "Auto Parts",
            "dwell": 2.7, "age_months": 55,
            "ad_cvd": 1.18, "risk_score": 65,
            "h1": 22, "h2": 25, "h3": 10,
        },
        {
            "shipper": "Bangladesh Textile Export Council",
            "origin": "BD", "declared": "BD",
            "hs": "5208.49", "commodity": "Cotton Fabrics",
            "dwell": 3.8, "age_months": 40,
            "ad_cvd": 1.55, "risk_score": 67,
            "h1": 24, "h2": 26, "h3": 11,
        },
        {
            "shipper": "Sri Lanka Coconut Products Ltd.",
            "origin": "LK", "declared": "LK",
            "hs": "1204.00", "commodity": "Coconut Seeds",
            "dwell": 4.1, "age_months": 50,
            "ad_cvd": 0.78, "risk_score": 62,
            "h1": 20, "h2": 24, "h3": 10,
        },
    ]

    # Generate all three bands
    counter = 1
    for specs in [critical_specs, high_specs, elevated_specs]:
        for spec in specs:
            filing_date = base_date + timedelta(days=counter * 3)
            is_mismatch = spec["origin"] != spec["declared"]

            record = {
                "id": f"SHP-DEMO-{counter:04d}",
                "manifest_id": f"MNF-2026-DEMO-{counter:04d}",
                "filing_date": filing_date.isoformat() + "T00:00:00",
                "shipper_name": spec["shipper"],
                "shipper_country": spec["declared"],
                "consignee_name": "American Trade Corporation",
                "consignee_country": "US",
                "hs_code": spec["hs"],
                "commodity_description": spec["commodity"],
                "declared_value_usd": round(50000 + counter * 1000, 2),
                "declared_weight_kg": round(5000 + counter * 500, 1),
                "origin_country": spec["declared"],
                "destination_country": "US",
                "destination_port": "NJ",
                "destination_port_name": "Newark",
                "destination_state": "NJ",
                "vessel_name": f"MV Trader {counter}",
                "vessel_imo": f"98765{counter:02d}",
                "vessel_flag": "PA",
                "vessel_type": "Container Ship",
                "vessel_capacity_teu": 8063,
                "dwell_days": spec["dwell"],
                "declared_origin": spec["declared"],
                "ais_stuffing_country": spec["origin"],
                "port_calls": [spec["origin"], "SG", "US"] if is_mismatch else [spec["declared"], "US"],
                "shipper_age_months": spec["age_months"],
                "importer_age_months": 45,
                "ad_cvd_applicable": True,
                "ad_cvd_rate": spec["ad_cvd"],
                "ad_cvd_cases": ["A-570-070"] if spec["ad_cvd"] > 2.0 else [],
                "commodity_risk_level": "CRITICAL" if spec["risk_score"] >= 90 else "HIGH" if spec["risk_score"] >= 80 else "MEDIUM",
                "corridor_risk": 0.95 if spec["declared"] in ["VN", "TH", "MY", "KH", "ID"] else 1.0,
                "corridor_label": f"{spec['declared']} → USA",
                "risk_score": spec["risk_score"],
                "status": "FILED",
                "created_at": filing_date.isoformat() + "T00:00:00",
                "element_9": {
                    "declared_country": spec["declared"],
                    "actual_stuffing_country": spec["origin"],
                    "is_mismatch": is_mismatch,
                    "risk_level": "HIGH" if is_mismatch else "LOW",
                    "mismatch_confidence": 0.98 if is_mismatch else 0.0,
                    "dwell_days": spec["dwell"],
                    "baseline_dwell_days": 2.1,
                    "dwell_anomaly_percentile": 95 if spec["dwell"] > 10 else 50,
                    "evidence": [
                        f"AIS {'stuffing' if is_mismatch else 'transit'} in {spec['origin']}: {spec['dwell']} days",
                        f"ISF Element 9: {'mismatch detected' if is_mismatch else 'consistent'}",
                        f"Port authority manifests confirm {spec['origin']}",
                    ] if is_mismatch else [],
                    "data_sources": ["AIS archive", "Port authority manifests", "Vessel tracking"],
                },
                "element9_risk_level": "HIGH" if is_mismatch else "LOW",
                "h1_score": spec["h1"],
                "h2_score": spec["h2"],
                "h3_score": spec["h3"],
            }
            cases.append(record)
            counter += 1

    return cases

def main():
    """Generate cases and append to manifest_demo_cases.json."""
    script_dir = Path(__file__).parent
    manifest_path = script_dir / "seed_data" / "manifest_demo_cases.json"

    # Load existing manifest
    with open(manifest_path, "r") as f:
        existing = json.load(f)

    # Generate new cases
    new_cases = generate_showcase_cases()

    # Append
    existing.extend(new_cases)

    # Write back
    with open(manifest_path, "w") as f:
        json.dump(existing, f, indent=2)

    print(f"✓ Generated {len(new_cases)} showcase cases")
    print(f"✓ Appended to {manifest_path}")
    print(f"✓ Total records now: {len(existing)}")
    print(f"\nBreakdown:")
    print(f"  - 10 CRITICAL (90-97%)")
    print(f"  - 5 HIGH (80-87%)")
    print(f"  - 10 ELEVATED (62-69%)")

if __name__ == "__main__":
    main()
