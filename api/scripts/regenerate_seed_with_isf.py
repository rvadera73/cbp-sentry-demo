"""Regenerate seed manifest data with ISF Element 9 enrichment."""

import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path
import random


# Mock vessel data database
VESSEL_DATABASE = {
    "MV_PACIFIC_HORIZON": {
        "imo": "9710399",
        "vessel_name": "MV Pacific Horizon",
        "flag_country": "PA",
        "vessel_type": "Container Ship",
        "capacity_teu": 8063,
        "port_calls": [
            {"port": "CNSHA", "country": "CN", "dwell": 11},
            {"port": "SGSIN", "country": "SG", "dwell": 2},
            {"port": "USNYC", "country": "US", "dwell": None},
        ]
    },
    "MV_SOLAR_EXPRESS": {
        "imo": "9387456",
        "vessel_name": "MV Solar Express",
        "flag_country": "LR",
        "vessel_type": "General Cargo",
        "capacity_teu": 4000,
        "port_calls": [
            {"port": "MYKL", "country": "MY", "dwell": 6},
            {"port": "SGSIN", "country": "SG", "dwell": 3},
            {"port": "USPHL", "country": "US", "dwell": None},
        ]
    },
    "MV_HANOI_STAR": {
        "imo": "9642187",
        "vessel_name": "MV Hanoi Star",
        "flag_country": "VN",
        "vessel_type": "Container Ship",
        "capacity_teu": 5000,
        "port_calls": [
            {"port": "VNSGN", "country": "VN", "dwell": 3},
            {"port": "USNYC", "country": "US", "dwell": None},
        ]
    },
    "MV_BANGKOK_PRIDE": {
        "imo": "9715823",
        "vessel_name": "MV Bangkok Pride",
        "flag_country": "SG",
        "vessel_type": "Container Ship",
        "capacity_teu": 9200,
        "port_calls": [
            {"port": "THBKK", "country": "TH", "dwell": 2},
            {"port": "SGSIN", "country": "SG", "dwell": 2},
            {"port": "USLB", "country": "US", "dwell": None},
        ]
    },
    "MV_SINGAPORE_LINK": {
        "imo": "9845921",
        "vessel_name": "MV Singapore Link",
        "flag_country": "SG",
        "vessel_type": "Container Ship",
        "capacity_teu": 7000,
        "port_calls": [
            {"port": "SGSIN", "country": "SG", "dwell": 1},
            {"port": "CATOR", "country": "CA", "dwell": None},
        ]
    }
}

# Element 9 analysis logic
def analyze_element_9(shipper_country, consignee_country, declared_origin, vessel_data):
    """Analyze Element 9 based on declared vs actual origin."""

    actual_stuffing_country = None
    dwell_days = 0

    # Get loading port from vessel routing
    if vessel_data and "port_calls" in vessel_data:
        first_port = vessel_data["port_calls"][0]
        actual_stuffing_country = first_port.get("country")
        dwell_days = first_port.get("dwell", 0)

    is_mismatch = False
    risk_level = "LOW"
    mismatch_confidence = 0.0
    evidence = []

    # Check declared vs actual
    if actual_stuffing_country and declared_origin:
        if actual_stuffing_country != declared_origin:
            is_mismatch = True
            evidence.append(
                f"Declared origin {declared_origin} but loaded from {actual_stuffing_country}"
            )

            # High-risk corridors
            corridor = (actual_stuffing_country, consignee_country)
            if corridor in [("CN", "MY"), ("CN", "VN"), ("CN", "TH"), ("CN", "KH")]:
                risk_level = "HIGH"
                mismatch_confidence = 0.95
                evidence.append(f"Known transshipment corridor: {corridor[0]}→{corridor[1]}")
            else:
                risk_level = "MEDIUM"
                mismatch_confidence = 0.75
                evidence.append("Potential transshipment detected")

    # Check for dwell anomalies
    if dwell_days and dwell_days > 10:
        evidence.append(f"Extended dwell: {dwell_days} days (baseline 2-5)")
        if risk_level == "LOW":
            risk_level = "MEDIUM"
            mismatch_confidence = 0.60
        elif risk_level == "MEDIUM":
            mismatch_confidence = min(mismatch_confidence + 0.15, 1.0)

    # Direct shipper country mismatch
    if shipper_country != declared_origin and declared_origin != "CN":
        evidence.append(f"Shipper {shipper_country} differs from declared {declared_origin}")
        if not is_mismatch and risk_level == "LOW":
            risk_level = "MEDIUM"
            mismatch_confidence = 0.6

    return {
        "declared_country": declared_origin,
        "actual_stuffing_country": actual_stuffing_country,
        "is_mismatch": is_mismatch,
        "risk_level": risk_level,
        "mismatch_confidence": mismatch_confidence,
        "dwell_days": dwell_days,
        "evidence": evidence,
        "data_sources": ["VesselFinder", "Port Authority Records"]
    }


async def regenerate_seed_data():
    """Regenerate seed data with ISF Element 9 enrichment."""

    print("=" * 80)
    print("REGENERATING SEED DATA WITH ISF ELEMENT 9 ENRICHMENT")
    print("=" * 80)

    # Load existing seed data
    seed_path = Path("/home/rahulvadera/cbp-sentry/api/seed_data/manifest_feb_march_2026.json")
    with open(seed_path) as f:
        records = json.load(f)

    print(f"\nLoaded {len(records)} existing manifest records")

    # Map vessel names to database
    vessel_key_map = {
        "MV Seamless Journey": "MV_PACIFIC_HORIZON",
        "MV Pacific Horizon": "MV_PACIFIC_HORIZON",
        "MV Solar Express": "MV_SOLAR_EXPRESS",
        "MV Hanoi Star": "MV_HANOI_STAR",
        "MV Bangkok Pride": "MV_BANGKOK_PRIDE",
        "MV Singapore Link": "MV_SINGAPORE_LINK",
    }

    # Enhance each record with ISF data
    enriched_count = 0
    element9_mismatches = 0
    high_risk_count = 0

    for i, record in enumerate(records):
        # Find vessel in database
        vessel_name = record.get("vessel_name", "")
        vessel_key = vessel_key_map.get(vessel_name)
        vessel_data = VESSEL_DATABASE.get(vessel_key)

        # Add ISF fields
        if vessel_data:
            record["vessel_imo"] = vessel_data["imo"]
            record["vessel_flag"] = vessel_data["flag_country"]
            record["vessel_type"] = vessel_data["vessel_type"]
            record["vessel_capacity_teu"] = vessel_data["capacity_teu"]

            # Analyze Element 9
            e9 = analyze_element_9(
                record.get("shipper_country", "XX"),
                record.get("consignee_country", "XX"),
                record.get("declared_origin", "XX"),
                vessel_data
            )

            # Add Element 9 to record
            record["element_9"] = e9
            record["element9_declared_country"] = e9["declared_country"]
            record["element9_actual_country"] = e9["actual_stuffing_country"]
            record["element9_is_mismatch"] = e9["is_mismatch"]
            record["element9_risk_level"] = e9["risk_level"]
            record["element9_confidence"] = e9["mismatch_confidence"]
            record["element9_dwell_days"] = e9["dwell_days"]
            record["element9_evidence"] = e9["evidence"]

            # Track statistics
            if e9["is_mismatch"]:
                element9_mismatches += 1
            if e9["risk_level"] == "HIGH":
                high_risk_count += 1

            enriched_count += 1
        else:
            # Add default Element 9 if vessel not found
            record["element_9"] = {
                "declared_country": record.get("declared_origin", "XX"),
                "actual_stuffing_country": None,
                "is_mismatch": False,
                "risk_level": "LOW",
                "mismatch_confidence": 0.0,
                "dwell_days": record.get("dwell_days", 0),
                "evidence": ["Vessel data not available"],
                "data_sources": []
            }
            record["element9_risk_level"] = "LOW"

    # Save enriched data
    output_path = Path("/home/rahulvadera/cbp-sentry/api/seed_data/manifest_feb_march_2026_with_isf.json")
    with open(output_path, "w") as f:
        json.dump(records, f, indent=2, default=str)

    print(f"\n✓ Enriched {enriched_count}/{len(records)} records with ISF data")
    print(f"✓ Element 9 mismatches detected: {element9_mismatches}")
    print(f"✓ High-risk Element 9 cases: {high_risk_count}")
    print(f"✓ Saved to: {output_path}")

    # Show sample enriched record
    sample_idx = random.randint(0, len(records) - 1)
    sample = records[sample_idx]

    print("\n" + "=" * 80)
    print("SAMPLE ENRICHED RECORD")
    print("=" * 80)
    print(f"Manifest ID: {sample.get('manifest_id')}")
    print(f"Shipper: {sample.get('shipper_name')} ({sample.get('shipper_country')})")
    print(f"Consignee: {sample.get('consignee_name')} ({sample.get('consignee_country')})")
    print(f"Vessel: {sample.get('vessel_name')} (IMO: {sample.get('vessel_imo')})")
    if "element_9" in sample:
        e9 = sample["element_9"]
        print(f"\nElement 9 Analysis:")
        print(f"  Declared: {e9['declared_country']}")
        print(f"  Actual: {e9['actual_stuffing_country']}")
        print(f"  Is Mismatch: {e9['is_mismatch']}")
        print(f"  Risk Level: {e9['risk_level']}")
        print(f"  Confidence: {e9['mismatch_confidence']:.2f}")
        if e9['evidence']:
            print(f"  Evidence:")
            for ev in e9['evidence']:
                print(f"    - {ev}")

    # Show Element 9 statistics
    print("\n" + "=" * 80)
    print("ELEMENT 9 STATISTICS")
    print("=" * 80)

    risk_distribution = {}
    mismatch_distribution = {}

    for record in records:
        if "element_9" in record:
            e9 = record["element_9"]
            risk_level = e9.get("risk_level", "LOW")
            risk_distribution[risk_level] = risk_distribution.get(risk_level, 0) + 1

            is_mismatch = e9.get("is_mismatch", False)
            key = "Mismatch" if is_mismatch else "No Mismatch"
            mismatch_distribution[key] = mismatch_distribution.get(key, 0) + 1

    print("\nRisk Level Distribution:")
    for risk_level in ["HIGH", "MEDIUM", "LOW"]:
        count = risk_distribution.get(risk_level, 0)
        pct = (count / len(records)) * 100 if records else 0
        print(f"  {risk_level}: {count} ({pct:.1f}%)")

    print("\nElement 9 Mismatch Distribution:")
    for status in ["Mismatch", "No Mismatch"]:
        count = mismatch_distribution.get(status, 0)
        pct = (count / len(records)) * 100 if records else 0
        print(f"  {status}: {count} ({pct:.1f}%)")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    asyncio.run(regenerate_seed_data())
