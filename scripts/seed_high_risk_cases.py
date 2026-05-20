#!/usr/bin/env python3
"""
Generate comprehensive high-risk transshipment cases for demo
"""
import requests
import json
from datetime import datetime, timedelta
import random

API_BASE = "http://localhost:8000/api"

# Rich case profiles with all details needed for scoring
CASES = [
    {
        "shipper_name": "Greenfield Industrial Trading Co.",
        "shipper_country": "VN",
        "shipper_city": "Hanoi",
        "consignee_name": "SunPath Energy Distributors LLC",
        "consignee_country": "US",
        "consignee_city": "Newark",
        "commodity_code": "7604.29",
        "commodity_name": "Aluminum Extrusions",
        "declared_value": 50000,
        "declared_weight_kg": 5000,
        "vessel_name": "MV Pacific Horizon",
        "port_of_origin": "Guangzhou, China",
        "port_of_destination": "Newark, NJ",
        "shipper_age_months": 8,
        "shipper_confidence": 0.87,
        "risk_indicators": {
            "h1": {
                "corridor_risk": "HIGH",
                "corridor_score": 40,
                "ad_cvd_rate": 374.15,
                "shipper_age_risk": "NEW_ENTITY",
                "undervaluation": 42.5,
                "factors": [
                    "Vietnam-US corridor flagged for aluminum transshipment",
                    "374.15% AD/CVD rate from China - tariff avoidance signal",
                    "Shipper established 8 months ago - suspiciously timed",
                    "Declared value $50k for 5 tons = $10/kg (42.5% below market $17.50/kg)",
                ]
            },
            "h2": {
                "vessel_score": 35,
                "ais_dwell_days": 11.2,
                "ais_baseline_days": 2.1,
                "dwell_anomaly_pct": 433,
                "isf_stuffing_location": "China",
                "isf_declared_origin": "Vietnam",
                "routing_flags": ["Unusual dwell", "ISF mismatch", "Port call gaps"],
                "factors": [
                    "AIS dwell: 11.2 days vs 2.1 day baseline (5.3x anomaly)",
                    "ISF Element 9: Stuffing in China, declared as Vietnam origin",
                    "4 port calls skipped in normal route pattern",
                    "Vessel MV Pacific Horizon flagged in prior EAPA cases"
                ]
            },
            "h3": {
                "intelligence_score": 16,
                "ofac_hit": False,
                "watch_list_entity": True,
                "new_importer_high_vol": True,
                "surge_volume": True,
                "factors": [
                    "Shipper shares directors with 3 other new VN entities",
                    "SunPath consignee also linked to Solaria case (Solaria MEDIUM 65)",
                    "Volume surge: first shipment 5x larger than typical startup",
                    "Senzing: director overlap with known transshipment facilitator (confidence 92%)"
                ]
            }
        }
    },
    {
        "shipper_name": "Solaria Manufacturing Sdn. Bhd.",
        "shipper_country": "MY",
        "shipper_city": "Kuala Lumpur",
        "consignee_name": "SunPath Energy Distributors LLC",
        "consignee_country": "US",
        "consignee_city": "Newark",
        "commodity_code": "8541.40.6020",
        "commodity_name": "Solar Modules",
        "declared_value": 75000,
        "declared_weight_kg": 2000,
        "vessel_name": "MV Solar Express",
        "port_of_origin": "Port Klang, Malaysia",
        "port_of_destination": "Los Angeles, CA",
        "shipper_age_months": 1,
        "shipper_confidence": 0.76,
        "risk_indicators": {
            "h1": {
                "corridor_risk": "MEDIUM",
                "corridor_score": 32,
                "ad_cvd_rate": 100.0,
                "shipper_age_risk": "BRAND_NEW",
                "undervaluation": 18.2,
                "factors": [
                    "Malaysia-US solar corridor flagged - known transshipment route",
                    "100% CVD from China on solar modules",
                    "Shipper incorporated 33 DAYS before filing - extreme timing",
                    "Declared value $75k for 2 tons = $37.50/kg (18.2% undervalued)"
                ]
            },
            "h2": {
                "vessel_score": 24,
                "ais_dwell_days": 6.1,
                "ais_baseline_days": 2.3,
                "dwell_anomaly_pct": 165,
                "isf_stuffing_location": "China",
                "isf_declared_origin": "Malaysia",
                "routing_flags": ["Extended dwell", "ISF country mismatch"],
                "factors": [
                    "AIS dwell: 6.1 days vs 2.3 baseline (2.7x anomaly)",
                    "ISF Element 9: Stuffed in China, declared as Malaysia origin",
                    "2 port call delays vs standard schedule",
                    "Vessel MV Solar Express in port call pattern change"
                ]
            },
            "h3": {
                "intelligence_score": 10,
                "ofac_hit": False,
                "watch_list_entity": False,
                "new_importer_high_vol": True,
                "surge_volume": False,
                "factors": [
                    "**CRITICAL**: Same consignee as Greenfield case (SunPath)",
                    "Fraud ring indicator: 2 high-risk shippers → same consignee",
                    "Parent company Guangdong Solaria (China) - same as Greenfield parent",
                    "Senzing: director overlap with Greenfield parent entities (confidence 88%)"
                ]
            }
        }
    },
    {
        "shipper_name": "Vietnam Aluminum Corp",
        "shipper_country": "VN",
        "shipper_city": "Ho Chi Minh",
        "consignee_name": "Newark Metals Inc",
        "consignee_country": "US",
        "consignee_city": "Newark",
        "commodity_code": "7610",
        "commodity_name": "Aluminum Plates",
        "declared_value": 45000,
        "declared_weight_kg": 4500,
        "vessel_name": "MV Hanoi Star",
        "port_of_origin": "Ho Chi Minh City, Vietnam",
        "port_of_destination": "Charleston, SC",
        "shipper_age_months": 192,
        "shipper_confidence": 0.98,
        "risk_indicators": {
            "h1": {
                "corridor_risk": "LOW",
                "corridor_score": 12,
                "ad_cvd_rate": 0.0,
                "shipper_age_risk": "ESTABLISHED",
                "undervaluation": 0.0,
                "factors": [
                    "Vietnam-US aluminum corridor - established shipper profile",
                    "No AD/CVD for HTS 7610 - legitimate product code",
                    "Vietnam Aluminum established 16 years ago - credible history",
                    "Declared value $45k for 4.5 tons = $10/kg (fair market pricing)"
                ]
            },
            "h2": {
                "vessel_score": 2,
                "ais_dwell_days": 3.2,
                "ais_baseline_days": 2.8,
                "dwell_anomaly_pct": 14,
                "isf_stuffing_location": "Vietnam",
                "isf_declared_origin": "Vietnam",
                "routing_flags": [],
                "factors": [
                    "AIS dwell: 3.2 days vs 2.8 baseline (normal variation)",
                    "ISF Element 9: Stuffed in Vietnam, declared as Vietnam (match)",
                    "Standard port call sequence - no anomalies",
                    "Vessel MV Hanoi Star: clean history, regular schedule"
                ]
            },
            "h3": {
                "intelligence_score": 0,
                "ofac_hit": False,
                "watch_list_entity": False,
                "new_importer_high_vol": False,
                "surge_volume": False,
                "factors": [
                    "Shipper: 16 years operating, established reputation",
                    "No watch list hits, no prior EAPA involvement",
                    "Consignee (Newark Metals): legitimate industrial buyer, 22 years",
                    "No Senzing director overlaps with known risk entities"
                ]
            }
        }
    },
    {
        "shipper_name": "Bangkok Metals International",
        "shipper_country": "TH",
        "shipper_city": "Bangkok",
        "consignee_name": "American Industrial Supply",
        "consignee_country": "US",
        "consignee_city": "Chicago",
        "commodity_code": "7611",
        "commodity_name": "Aluminum Tubes",
        "declared_value": 65000,
        "declared_weight_kg": 3500,
        "vessel_name": "MV Bangkok Pride",
        "port_of_origin": "Laem Chabang, Thailand",
        "port_of_destination": "Long Beach, CA",
        "shipper_age_months": 60,
        "shipper_confidence": 0.93,
        "risk_indicators": {
            "h1": {
                "corridor_risk": "LOW",
                "corridor_score": 12,
                "ad_cvd_rate": 0.0,
                "shipper_age_risk": "ESTABLISHED",
                "undervaluation": 0.0,
                "factors": [
                    "Thailand-US aluminum corridor - normal trade flow",
                    "No AD/CVD on HTS 7611 - standard product",
                    "Bangkok Metals: 5 years operating, solid track record",
                    "Pricing $18.57/kg - matches market baseline"
                ]
            },
            "h2": {
                "vessel_score": 3,
                "ais_dwell_days": 2.8,
                "ais_baseline_days": 2.5,
                "dwell_anomaly_pct": 12,
                "isf_stuffing_location": "Thailand",
                "isf_declared_origin": "Thailand",
                "routing_flags": [],
                "factors": [
                    "AIS dwell: 2.8 days vs 2.5 baseline (normal)",
                    "ISF Element 9: Stuffed and declared as Thailand (no mismatch)",
                    "Standard routing, no unusual port calls",
                    "Vessel MV Bangkok Pride: clean AIS history"
                ]
            },
            "h3": {
                "intelligence_score": 0,
                "ofac_hit": False,
                "watch_list_entity": False,
                "new_importer_high_vol": False,
                "surge_volume": False,
                "factors": [
                    "No watch list or prior EAPA involvement",
                    "Consignee: American Industrial Supply, 18 years operating",
                    "No director overlaps or suspicious entity links",
                    "Senzing confidence 93% - clean entity resolution"
                ]
            }
        }
    },
    {
        "shipper_name": "TechExport Ltd",
        "shipper_country": "SG",
        "shipper_city": "Singapore",
        "consignee_name": "GlobalTech Inc",
        "consignee_country": "CA",
        "consignee_city": "Toronto",
        "commodity_code": "8517.62",
        "commodity_name": "Telecom Equipment",
        "declared_value": 30000,
        "declared_weight_kg": 1500,
        "vessel_name": "MV Singapore Link",
        "port_of_origin": "Port of Singapore",
        "port_of_destination": "Port of Vancouver",
        "shipper_age_months": 120,
        "shipper_confidence": 0.95,
        "risk_indicators": {
            "h1": {
                "corridor_risk": "LOW",
                "corridor_score": 7,
                "ad_cvd_rate": 0.0,
                "shipper_age_risk": "ESTABLISHED",
                "undervaluation": 0.0,
                "factors": [
                    "Singapore-Canada tech corridor - normal trade",
                    "No AD/CVD on telecom equipment HTS 8517",
                    "TechExport: 10 years established, known exporter",
                    "Pricing $20/kg - fair market value"
                ]
            },
            "h2": {
                "vessel_score": 1,
                "ais_dwell_days": 2.1,
                "ais_baseline_days": 2.0,
                "dwell_anomaly_pct": 5,
                "isf_stuffing_location": "Singapore",
                "isf_declared_origin": "Singapore",
                "routing_flags": [],
                "factors": [
                    "AIS dwell: 2.1 days vs 2.0 baseline (minimal variance)",
                    "ISF Element 9: Consistent - Singapore → Singapore",
                    "No routing anomalies, standard schedule",
                    "Vessel: regular Asia-North America service"
                ]
            },
            "h3": {
                "intelligence_score": 0,
                "ofac_hit": False,
                "watch_list_entity": False,
                "new_importer_high_vol": False,
                "surge_volume": False,
                "factors": [
                    "Clean OFAC check, no watch list flags",
                    "No prior EAPA filings or enforcement actions",
                    "Consignee GlobalTech: 15 years, electronics import specialist",
                    "Senzing: no suspicious director or entity overlaps"
                ]
            }
        }
    }
]

def create_shipment(case_data):
    """Create a shipment with all enriched data"""
    payload = {
        "shipper_name": case_data["shipper_name"],
        "shipper_country": case_data["shipper_country"],
        "shipper_city": case_data.get("shipper_city", ""),
        "consignee_name": case_data["consignee_name"],
        "consignee_country": case_data["consignee_country"],
        "consignee_city": case_data.get("consignee_city", ""),
        "commodity_code": case_data["commodity_code"],
        "commodity_name": case_data.get("commodity_name", ""),
        "declared_value": case_data["declared_value"],
        "declared_weight_kg": case_data["declared_weight_kg"],
        "vessel_name": case_data.get("vessel_name", ""),
        "port_of_origin": case_data.get("port_of_origin", ""),
        "port_of_destination": case_data.get("port_of_destination", ""),
        "shipper_age_months": case_data.get("shipper_age_months", 60),
        "risk_indicators": case_data.get("risk_indicators", {})
    }

    try:
        response = requests.post(f"{API_BASE}/ingest/create-shipment", json=payload, timeout=10)
        if response.status_code == 201:
            print(f"✓ Created: {case_data['shipper_name']}")
            return response.json()
        else:
            print(f"✗ Failed to create {case_data['shipper_name']}: {response.status_code}")
            # Fallback: just insert directly to DB if ingest endpoint not available
            return None
    except Exception as e:
        print(f"✗ Error creating {case_data['shipper_name']}: {e}")
        return None

def main():
    print("=" * 70)
    print("SENTRY CBP - High Risk Transshipment Case Generation")
    print("=" * 70)

    for case in CASES:
        print(f"\nProcessing: {case['shipper_name']}")
        result = create_shipment(case)
        if result:
            print(f"  Shipment ID: {result.get('id', 'N/A')}")

    print("\n" + "=" * 70)
    print("Case generation complete!")
    print("=" * 70)

if __name__ == "__main__":
    main()
