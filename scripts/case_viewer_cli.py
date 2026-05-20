#!/usr/bin/env python3
"""
Case Viewer CLI - Display manifest data with smart RED case flagging.

Shows:
1. Case list (sorted by risk) with RED/YELLOW/GREEN flags
2. Investigate action for detailed scoring (H1+H2+H3 + ISF + entity chain)
3. Scoring breakdown with evidence

Usage:
  python3 scripts/case_viewer_cli.py list                    # Show all cases
  python3 scripts/case_viewer_cli.py list --red-only          # Show RED cases only
  python3 scripts/case_viewer_cli.py investigate SHP-000015   # Score a specific case
"""

import json
import sys
import asyncio
from pathlib import Path
from typing import Dict, List, Optional
import argparse

# Add services to path
sys.path.insert(0, str(Path(__file__).parent.parent / "services"))

from entity_resolution.cord_rag import CORDRagDatabase


def load_manifests() -> List[Dict]:
    """Load manifest seed data."""
    manifest_file = Path(__file__).parent.parent / "api" / "seed_data" / "manifest_feb_march_2026_with_isf.json"
    with open(manifest_file) as f:
        return json.load(f)


def calculate_risk_flag(risk_score: float) -> tuple[str, str]:
    """
    Determine risk flag and color for display.

    Returns: (flag_emoji, label)
    """
    if risk_score >= 70:
        return "🔴", "RED"
    elif risk_score >= 40:
        return "🟡", "YELLOW"
    else:
        return "🟢", "GREEN"


def display_case_list(manifests: List[Dict], red_only: bool = False):
    """Display case list with risk flags."""

    print("\n" + "=" * 110)
    print("SENTRY CBP — CASE VIEWER  |  Manifest Data (1191 records)")
    print("=" * 110)

    # Sort by risk score (highest first)
    sorted_manifests = sorted(manifests, key=lambda x: x.get("risk_score", 0), reverse=True)

    # Filter RED if requested
    if red_only:
        sorted_manifests = [m for m in sorted_manifests if m.get("risk_score", 0) >= 70]

    print(f"\nShowing {len(sorted_manifests)} cases\n")
    print(
        f"{'Flag':<6} {'ID':<16} {'Shipper':<30} {'Origin':<6} {'Risk':<6} "
        f"{'Corridor':<20} {'ISF Match':<12} {'Action':<40}"
    )
    print("-" * 110)

    for manifest in sorted_manifests[:20]:  # Show first 20
        flag, label = calculate_risk_flag(manifest.get("risk_score", 0))

        shipper = manifest.get("shipper_name", "")[:28]
        origin = manifest.get("shipper_country", "")
        risk = int(manifest.get("risk_score", 0))
        corridor = manifest.get("corridor_label", "")[:18]

        # ISF Element 9 status
        element9 = manifest.get("element_9", {})
        is_mismatch = element9.get("is_mismatch", False)
        isf_status = "⚠️ MISMATCH" if is_mismatch else "✓ Match"

        # Action button
        action_text = f"investigate {manifest.get('id', '')}"

        print(
            f"{flag:<6} {manifest.get('id', ''):<16} {shipper:<30} {origin:<6} "
            f"{risk:<6} {corridor:<20} {isf_status:<12} {action_text:<40}"
        )

    print("\n" + "-" * 110)
    print(f"📌 RED cases (risk >= 70): {len([m for m in sorted_manifests if m.get('risk_score', 0) >= 70])}")
    print(f"🟡 YELLOW cases (40-69): {len([m for m in sorted_manifests if 40 <= m.get('risk_score', 0) < 70])}")
    print(f"🟢 GREEN cases (< 40): {len([m for m in sorted_manifests if m.get('risk_score', 0) < 40])}")
    print("\nUsage: python3 scripts/case_viewer_cli.py investigate <ID>")
    print("=" * 110 + "\n")


async def display_case_investigation(shipment_id: str, manifests: List[Dict]):
    """Investigate and display full case details with scoring."""

    # Find shipment
    shipment = next((m for m in manifests if m.get("id") == shipment_id), None)
    if not shipment:
        print(f"❌ Shipment {shipment_id} not found")
        return

    print("\n" + "=" * 110)
    print(f"CASE INVESTIGATION: {shipment_id}")
    print("=" * 110)

    # ═══════════════════════════════════════════════════════════════════════
    # SECTION 1: MANIFEST BASICS
    # ═══════════════════════════════════════════════════════════════════════

    print("\n📋 MANIFEST DETAILS")
    print("-" * 110)
    print(f"  Shipment ID:        {shipment.get('id')}")
    print(f"  Manifest ID:        {shipment.get('manifest_id')}")
    print(f"  Filing Date:        {shipment.get('filing_date')}")
    print(f"  Status:             {shipment.get('status')}")
    print()
    print(f"  Shipper:            {shipment.get('shipper_name')} ({shipment.get('shipper_country')})")
    print(f"  Shipper Age:        {shipment.get('shipper_age_months')} months")
    print(f"  Consignee:          {shipment.get('consignee_name')} ({shipment.get('consignee_country')})")
    print(f"  Importer Age:       {shipment.get('importer_age_months')} months")
    print()
    print(f"  HS Code:            {shipment.get('hs_code')} ({shipment.get('commodity_description')})")
    print(f"  Declared Value:     ${shipment.get('declared_value_usd'):,.2f}")
    print(f"  Declared Weight:    {shipment.get('declared_weight_kg'):,} kg")
    print(f"  Port of Entry:      {shipment.get('destination_port_name')} ({shipment.get('destination_port')})")

    # ═══════════════════════════════════════════════════════════════════════
    # SECTION 2: ISF ELEMENT 9 DATA
    # ═══════════════════════════════════════════════════════════════════════

    print("\n📑 ISF ELEMENT 9 (Country of Origin Pre-Arrival)")
    print("-" * 110)

    element9 = shipment.get("element_9", {})
    declared_country = element9.get("declared_country", "?")
    actual_country = element9.get("actual_stuffing_country", "?")
    is_mismatch = element9.get("is_mismatch", False)
    dwell_days = element9.get("dwell_days", 0)

    if is_mismatch:
        print(f"  ⚠️  COUNTRY MISMATCH DETECTED")
        print(f"      Declared Origin: {declared_country}")
        print(f"      Actual Stuffing: {actual_country}")
        print(f"      Confidence: {element9.get('mismatch_confidence', 0):.0%}")
    else:
        print(f"  ✓ Origin Match OK")
        print(f"      Declared: {declared_country}")
        print(f"      Actual:   {actual_country}")

    print(f"\n  Port Calls:         {' → '.join(shipment.get('port_calls', []))}")
    print(f"  Dwell Days:         {dwell_days} days")
    if dwell_days > 5:
        print(f"    ⚠️  Extended dwell (baseline: 2-5 days)")

    print(f"  ISF Risk Level:     {element9.get('risk_level', 'UNKNOWN')}")
    print(f"  Evidence:")
    for evidence in element9.get("evidence", []):
        print(f"    • {evidence}")

    # ═══════════════════════════════════════════════════════════════════════
    # SECTION 3: CORRIDOR & COMMODITY RISK
    # ═══════════════════════════════════════════════════════════════════════

    print("\n🌐 CORRIDOR & COMMODITY RISK")
    print("-" * 110)
    print(f"  Corridor:           {shipment.get('corridor_label')}")
    print(f"  Corridor Risk:      {shipment.get('corridor_risk', 0):.2f}")
    print(f"  Commodity Risk:     {shipment.get('commodity_risk_level', 'UNKNOWN')}")
    print(f"  AD/CVD Applicable:  {shipment.get('ad_cvd_applicable', 'No')}")

    if shipment.get("ad_cvd_cases"):
        print(f"  AD/CVD Cases:       {len(shipment.get('ad_cvd_cases', []))} active")
        for case in shipment.get("ad_cvd_cases", [])[:3]:
            print(f"    • {case}")
    else:
        print(f"  AD/CVD Cases:       None")

    # ═══════════════════════════════════════════════════════════════════════
    # SECTION 4: VESSEL INFORMATION
    # ═══════════════════════════════════════════════════════════════════════

    print("\n⛴️  VESSEL INFORMATION")
    print("-" * 110)
    print(f"  Vessel Name:        {shipment.get('vessel_name')}")
    print(f"  IMO Number:         {shipment.get('vessel_imo')}")
    print(f"  Flag:               {shipment.get('vessel_flag')}")
    print(f"  Type:               {shipment.get('vessel_type')}")
    print(f"  Capacity:           {shipment.get('vessel_capacity_teu')} TEU")

    # ═══════════════════════════════════════════════════════════════════════
    # SECTION 5: ENTITY RESOLUTION (CORD RAG)
    # ═══════════════════════════════════════════════════════════════════════

    print("\n🔍 ENTITY RESOLUTION (CORD RAG + Senzing)")
    print("-" * 110)

    try:
        cord_rag = CORDRagDatabase(
            str(Path(__file__).parent.parent / "data" / "cord_rag.db")
        )

        # Resolve shipper
        shipper_match = await cord_rag.resolve_entity(
            shipment.get("shipper_name", ""),
            shipment.get("shipper_country", "")
        )

        if shipper_match["found"]:
            print(f"  ✓ Shipper FOUND in CORD")
            print(f"    Name:      {shipper_match['entity_name']}")
            print(f"    Country:   {shipper_match['country']}")
            print(f"    Source:    {shipper_match['data_source']}")
            print(f"    Confidence: {shipper_match['confidence']:.0%}")

            # Trace beneficial owner
            chain = await cord_rag.trace_beneficial_owner(
                shipper_match["entity_name"],
                shipper_match["country"],
                depth=3
            )
            if chain and len(chain) > 1:
                print(f"    Beneficial Owner Chain:")
                for i, entity in enumerate(chain):
                    indent = "      "
                    print(f"{indent}{'└─' if i == len(chain)-1 else '├─'} {entity['entity_name']} ({entity['country']})")
        else:
            print(f"  ❌ Shipper NOT found in CORD")

        # Resolve consignee
        consignee_match = await cord_rag.resolve_entity(
            shipment.get("consignee_name", ""),
            shipment.get("consignee_country", "")
        )

        if consignee_match["found"]:
            print(f"\n  ✓ Consignee FOUND in CORD")
            print(f"    Name:      {consignee_match['entity_name']}")
            print(f"    Country:   {consignee_match['country']}")
            print(f"    Source:    {consignee_match['data_source']}")
            print(f"    Confidence: {consignee_match['confidence']:.0%}")
        else:
            print(f"\n  ❌ Consignee NOT found in CORD")

        # Sanctions check
        shipper_sanctions = await cord_rag.search_sanctions(
            shipment.get("shipper_name", ""),
            shipment.get("shipper_country", "")
        )
        if shipper_sanctions["status"] != "CLEAR":
            print(f"\n  ⛔ SANCTIONS HIT: {shipper_sanctions['status']}")
        else:
            print(f"\n  ✓ Sanctions: CLEAR")

    except FileNotFoundError:
        print("  ⚠️  CORD RAG database not available (run build_cord_rag_db_from_sources.py)")

    # ═══════════════════════════════════════════════════════════════════════
    # SECTION 6: RISK SCORE
    # ═══════════════════════════════════════════════════════════════════════

    print("\n📊 OVERALL RISK SCORE")
    print("-" * 110)

    risk_score = shipment.get("risk_score", 0)
    flag, label = calculate_risk_flag(risk_score)

    print(f"  {flag} {label} RISK")
    print(f"  Score: {risk_score}/100")
    print()

    # Score breakdown (placeholder - actual H1+H2+H3 would go here)
    print(f"  Components (from seed data):")
    print(f"    • Corridor Risk:      {shipment.get('corridor_risk', 0):.0f}")
    print(f"    • Commodity Risk:     {shipment.get('commodity_risk_level', 'UNKNOWN')}")
    print(f"    • ISF Anomaly:        {'⚠️  MISMATCH' if shipment.get('element_9', {}).get('is_mismatch') else '✓ OK'}")
    print()
    print(f"  Recommended Action:")
    if risk_score >= 70:
        print(f"    🔴 EXAMINE ON ARRIVAL / REFER TO TRLED")
    elif risk_score >= 40:
        print(f"    🟡 ENHANCED SCREENING / CF-28 EXAMINATION")
    else:
        print(f"    🟢 STANDARD PROCESSING")

    print("\n" + "=" * 110 + "\n")


def main():
    parser = argparse.ArgumentParser(description="SENTRY CBP Case Viewer")
    parser.add_argument("action", choices=["list", "investigate"], help="Action to perform")
    parser.add_argument("--red-only", action="store_true", help="Show only RED cases")
    parser.add_argument("shipment_id", nargs="?", help="Shipment ID for investigate action")

    args = parser.parse_args()

    # Load manifests
    manifests = load_manifests()

    if args.action == "list":
        display_case_list(manifests, red_only=args.red_only)
    elif args.action == "investigate":
        if not args.shipment_id:
            print("❌ Shipment ID required for investigate action")
            sys.exit(1)
        asyncio.run(display_case_investigation(args.shipment_id, manifests))


if __name__ == "__main__":
    main()
