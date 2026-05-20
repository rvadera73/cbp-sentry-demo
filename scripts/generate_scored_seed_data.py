#!/usr/bin/env python3
"""
Generate realistic risk scores for 500 manifest records (fast, data-driven).

Uses rule-based scoring without API calls:
- H1: Corridor risk (15-40 pts) based on origin+destination high-risk pairs
- H2: Vessel anomaly (10-35 pts) based on dwell time, ISF mismatch, port call patterns
- H3: Intelligence (5-25 pts) based on shipper age, importer age, commodity flags

Target distribution:
- 10-15 RED cases (risk >= 70)
- 8-10 GREEN cases (< 40)
- Rest YELLOW (40-69)
"""

import json
import sys
import random
from pathlib import Path
from typing import Dict, List, Any
from collections import defaultdict


# High-risk corridors (more likely to score RED)
HIGH_RISK_CORRIDORS = {
    ("CN", "US"),
    ("CN", "CA"),
    ("CN", "MX"),
    ("VN", "US"),
    ("VN", "CA"),
    ("VN", "MX"),
    ("TH", "US"),
    ("KH", "US"),
    ("MY", "US"),
    ("PK", "US"),
}

# High-risk commodities (more likely to score RED)
HIGH_RISK_HS_PREFIXES = {
    "7604",  # Aluminum (AD/CVD 374%)
    "8541",  # Solar cells (AD/CVD 100%)
    "7210",  # Steel (AD/CVD 200%+)
    "2308",  # Fish meal (AD/CVD)
}

# Low-risk commodities (more likely to score GREEN)
LOW_RISK_HS_PREFIXES = {
    "6203",  # Apparel
    "6204",  # Apparel
    "6205",  # Apparel
    "6206",  # Apparel
    "6207",  # Apparel
    "6208",  # Apparel
    "8517",  # Telecom
    "8518",  # Speakers
}


def load_manifests() -> List[Dict]:
    """Load manifest seed data."""
    manifest_file = Path(__file__).parent.parent / "api" / "seed_data" / "manifest_feb_march_2026_with_isf.json"
    with open(manifest_file) as f:
        return json.load(f)


def select_diverse_records(manifests: List[Dict], count: int = 500) -> List[Dict]:
    """Select 500 records with diverse characteristics."""
    # Group by corridor
    corridors: Dict[str, List[Dict]] = defaultdict(list)
    for m in manifests:
        origin = m.get("origin_country", "")
        destination = m.get("destination_country", "")
        corridor = f"{origin}→{destination}"
        corridors[corridor].append(m)

    # Sample from each corridor proportionally
    selected = []
    for corridor, records in sorted(corridors.items()):
        ratio = len(records) / len(manifests)
        num_to_select = max(1, int(count * ratio))
        selected.extend(random.sample(records, min(num_to_select, len(records))))

    # Pad with random records if needed
    if len(selected) < count:
        remaining_ids = set(m["id"] for m in manifests) - set(m["id"] for m in selected)
        remaining_records = [m for m in manifests if m["id"] in remaining_ids]
        selected.extend(random.sample(remaining_records, min(count - len(selected), len(remaining_records))))

    return selected[:count]


def calculate_h1_corridor_risk(manifest: Dict) -> float:
    """
    H1 Corridor Risk (0-40 pts).
    Based on: origin+destination corridor risk, commodity AD/CVD status.
    """
    base_score = 15  # Default baseline for all shipments

    origin = manifest.get("origin_country", "")
    destination = manifest.get("destination_country", "")
    corridor = (origin, destination)

    # High-risk corridor (add to baseline)
    if corridor in HIGH_RISK_CORRIDORS:
        base_score += 12
    elif origin in ["CN", "IN", "PK"]:
        base_score += 6
    elif origin in ["VN", "TH", "KH", "MY"]:
        base_score += 4
    # else: base stays at 15

    # Commodity risk
    hs_code = manifest.get("hs_code", "")
    if any(hs_code.startswith(prefix) for prefix in HIGH_RISK_HS_PREFIXES):
        base_score += 8
    elif any(hs_code.startswith(prefix) for prefix in LOW_RISK_HS_PREFIXES):
        base_score -= 3
    # else: no adjustment

    # Destination port risk
    port = manifest.get("destination_port", "")
    if port in ["NY", "LA", "HOU", "CHI"]:  # Major ports
        base_score += 2

    # Undervaluation indicator (declared value < typical)
    declared_value = manifest.get("declared_value_usd", 0)
    declared_weight = manifest.get("declared_weight_kg", 1)
    if declared_weight > 0:
        price_per_kg = declared_value / declared_weight
        # Below $5/kg for high-risk commodities is suspicious
        if price_per_kg < 5 and hs_code.startswith(("7604", "8541", "7210")):
            base_score += 4

    return min(40, max(8, base_score))


def calculate_h2_vessel_anomaly(manifest: Dict) -> float:
    """
    H2 Vessel Anomaly (0-35 pts).
    Based on: dwell time, ISF Element 9 mismatch, port call patterns.
    """
    base_score = 12  # Default baseline for all shipments

    # Dwell time anomaly (baseline ~2.1 days)
    dwell_days = manifest.get("element_9", {}).get("dwell_days", 2.1)
    if dwell_days > 10:
        base_score += 12
    elif dwell_days > 7:
        base_score += 8
    elif dwell_days > 4:
        base_score += 4
    # else: stays at baseline

    # ISF Element 9 country mismatch
    declared_origin = manifest.get("element_9", {}).get("declared_country", manifest.get("origin_country", ""))
    stuffing_country = manifest.get("element_9", {}).get("actual_stuffing_country", manifest.get("origin_country", ""))
    if declared_origin and stuffing_country and declared_origin != stuffing_country:
        if stuffing_country == "CN" and declared_origin != "CN":
            base_score += 12  # China transshipment red flag
        else:
            base_score += 6

    # Port calls (unusual routing)
    port_calls = manifest.get("port_calls", [])
    if len(port_calls) > 3:
        base_score += 3
    elif len(port_calls) > 1:
        base_score += 1

    # AIS gaps/unusual vessel
    if manifest.get("vessel_type") in ["container", "general_cargo"]:
        base_score += 0  # Normal
    elif manifest.get("vessel_type") in ["break_bulk", "multipurpose"]:
        base_score += 1  # Slightly unusual

    return min(35, max(6, base_score))


def calculate_h3_intelligence(manifest: Dict) -> float:
    """
    H3 Intelligence (0-25 pts).
    Based on: shipper age, importer age, entity chain, sanctions flags.
    """
    base_score = 8  # Default baseline for all shipments

    # Shipper age risk
    shipper_age = manifest.get("shipper_age_months", 24)
    if shipper_age < 6:
        base_score += 7
    elif shipper_age < 12:
        base_score += 4
    elif shipper_age < 24:
        base_score += 2
    # else: stays at baseline

    # Importer age risk
    importer_age = manifest.get("importer_age_months", 24)
    if importer_age < 6:
        base_score += 6
    elif importer_age < 12:
        base_score += 3
    # else: stays at baseline

    # Volume surge indicator
    ytd_volume = manifest.get("importer_ytd_volume", 0)
    if ytd_volume > 500000:  # Over $500k YTD
        base_score += 2

    # Sanctions/watchlist flags
    if manifest.get("ofac_match", False):
        base_score -= 25  # Automatic disqualification (goes negative, clamped to 0)
    elif manifest.get("watchlist_match", False):
        base_score += 4

    # CORD entity resolution confidence
    senzing_confidence = manifest.get("senzing_confidence", 0.85)
    if senzing_confidence < 0.70:
        base_score += 2  # Unverified entity

    return min(25, max(0, base_score))


def calculate_total_score(manifest: Dict) -> tuple:
    """Calculate H1+H2+H3 scores and total."""
    h1 = calculate_h1_corridor_risk(manifest)
    h2 = calculate_h2_vessel_anomaly(manifest)
    h3 = calculate_h3_intelligence(manifest)
    total = h1 + h2 + h3
    return total, h1, h2, h3


def adjust_scores_for_distribution(manifests: List[Dict]) -> List[Dict]:
    """
    Adjust a subset of scores to ensure target distribution.
    Target: 10-15 RED (>=70), 8-10 GREEN (<40), rest YELLOW.
    """
    # Calculate initial scores
    for m in manifests:
        total, h1, h2, h3 = calculate_total_score(m)
        m["risk_score"] = round(total, 2)
        m["h1_score"] = round(h1, 2)
        m["h2_score"] = round(h2, 2)
        m["h3_score"] = round(h3, 2)

    target_red = 12  # Mid-range of 10-15
    target_green = 9  # Mid-range of 8-10

    # Pass 1: Demote RED cases to YELLOW if too many
    red_cases = [m for m in manifests if m.get("risk_score", 0) >= 70]
    if len(red_cases) > target_red:
        candidates = sorted(red_cases, key=lambda x: x.get("risk_score", 0))
        num_to_demote = len(red_cases) - target_red
        for m in candidates[:num_to_demote]:
            # Lower to high YELLOW
            m["risk_score"] = 60 + random.randint(0, 8)

    # Pass 2: Promote YELLOW cases to RED if too few
    red_cases = [m for m in manifests if m.get("risk_score", 0) >= 70]
    yellow_cases = [m for m in manifests if 40 <= m.get("risk_score", 0) < 70]
    if len(red_cases) < target_red:
        candidates = sorted(yellow_cases, key=lambda x: x.get("risk_score", 0), reverse=True)
        num_to_promote = target_red - len(red_cases)
        for m in candidates[:num_to_promote]:
            # Raise to low RED
            m["risk_score"] = 70 + random.randint(0, 15)

    # Pass 3: Demote GREEN cases to YELLOW if too few GREEN
    green_cases = [m for m in manifests if m.get("risk_score", 0) < 40]
    yellow_cases = [m for m in manifests if 40 <= m.get("risk_score", 0) < 70]
    if len(green_cases) < target_green and yellow_cases:
        candidates = sorted(yellow_cases, key=lambda x: x.get("risk_score", 0))
        num_to_demote = min(target_green - len(green_cases), len(candidates))
        for m in candidates[:num_to_demote]:
            # Lower to low GREEN
            m["risk_score"] = 20 + random.randint(0, 18)

    return manifests


def update_manifests_with_scores(all_manifests: List[Dict], selected: List[Dict]) -> List[Dict]:
    """Update all manifests, replacing selected ones with new scores."""
    selected_ids = set(m["id"] for m in selected)
    updated = [m for m in all_manifests if m["id"] not in selected_ids] + selected
    return updated


def verify_distribution(manifests: List[Dict]) -> None:
    """Verify RED/YELLOW/GREEN distribution."""
    red = [m for m in manifests if m.get("risk_score", 0) >= 70]
    yellow = [m for m in manifests if 40 <= m.get("risk_score", 0) < 70]
    green = [m for m in manifests if m.get("risk_score", 0) < 40]

    print("=" * 80)
    print("DISTRIBUTION VERIFICATION")
    print("=" * 80)
    print(f"📌 RED (risk >= 70):        {len(red):3d} cases  {len(red)*100//len(manifests):2d}%")
    print(f"🟡 YELLOW (40-69):          {len(yellow):3d} cases  {len(yellow)*100//len(manifests):2d}%")
    print(f"🟢 GREEN (< 40):            {len(green):3d} cases  {len(green)*100//len(manifests):2d}%")
    print("=" * 80)

    if 10 <= len(red) <= 15:
        print("✅ RED count in target range (10-15)")
    else:
        print(f"⚠️  RED count {len(red)} outside target range (10-15)")

    if 8 <= len(green) <= 10:
        print("✅ GREEN count in target range (8-10)")
    else:
        print(f"⚠️  GREEN count {len(green)} outside target range (8-10)")

    print()


def main():
    """Main workflow."""
    print("=" * 80)
    print("SEED DATA SCORER (Fast, Data-Driven)")
    print("=" * 80)

    # Load all manifests
    all_manifests = load_manifests()
    print(f"\n📂 Loaded {len(all_manifests)} manifest records")

    # Select 500 diverse records
    print(f"\n🎲 Selecting 500 diverse records...")
    selected_manifests = select_diverse_records(all_manifests, count=500)
    print(f"✅ Selected {len(selected_manifests)} records")

    # Show sample before scoring
    print(f"\nSample records before scoring:")
    for m in selected_manifests[:3]:
        print(f"  {m.get('id'):12s} | {m.get('shipper_name', '')[:30]:30s} | {m.get('origin_country', '')}→{m.get('destination_country', '')}")

    # Calculate scores
    print(f"\n📊 Calculating risk scores...")
    selected_manifests = adjust_scores_for_distribution(selected_manifests)
    print(f"✅ Scores calculated")

    # Show sample after scoring
    print(f"\nSample records after scoring:")
    for m in selected_manifests[:5]:
        flag = "🔴" if m.get("risk_score", 0) >= 70 else "🟡" if m.get("risk_score", 0) >= 40 else "🟢"
        print(f"  {flag} {m.get('id'):12s} | {m.get('shipper_name', '')[:30]:30s} | {m.get('risk_score', 0):6.1f}")

    # Verify distribution
    verify_distribution(selected_manifests)

    # Update all manifests
    print("📝 Merging with unselected records...")
    updated_full = update_manifests_with_scores(all_manifests, selected_manifests)
    print(f"✅ Merged {len(updated_full)} total records")

    # Save updated manifests
    output_file = Path(__file__).parent.parent / "api" / "seed_data" / "manifest_feb_march_2026_with_isf.json"
    with open(output_file, "w") as f:
        json.dump(updated_full, f, indent=2)

    print(f"\n✅ Saved {len(updated_full)} records to {output_file}")

    # Final distribution check
    verify_distribution(selected_manifests)
    print("=" * 80)


if __name__ == "__main__":
    main()
