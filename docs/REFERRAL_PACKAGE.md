# Referral Package Specification

## Overview

The **Referral Package** is Sentry's primary deliverable — the enforcement-ready document CBP officers use to examine and seize goods suspected of illegal transshipment.

It maps directly to **Tables 3-1 through 3-14** from the CBP proposal and includes:
- **Confidence score** (0-100)
- **Risk factors** (6 components with evidence)
- **Entity ownership chain** (Senzing-resolved)
- **Recommended action** (EXAMINE_ON_ARRIVAL, REFER_TO_LAW_ENFORCEMENT, etc.)
- **Revenue impact** (estimated duties owed)

---

## JSON Structure

```json
{
  "package_id": "SENTRY-2026-001",
  "created_at": "2026-05-18T14:32:00Z",
  "shipment_id": "SHP-001",
  "manifest_id": "MF-2026-001",
  "in_transit": true,
  "estimated_arrival": "2026-05-01T00:00:00Z",
  
  "confidence_level": "HIGH",
  "total_score": 91,
  "recommended_action": "EXAMINE_ON_ARRIVAL",
  
  "sections": {
    "shipment_identification": {
      "bill_of_lading": "SAMPLE-BOL-2026-001",
      "shipper_name": "Greenfield Industrial Trading Co., Ltd.",
      "shipper_country": "VN",
      "consignee_name": "SunPath Energy Distributors LLC",
      "consignee_address": "1234 Industrial Blvd, Newark, NJ 07102",
      "port_of_lading": "VNSGN",
      "port_of_unlading": "USLAX",
      "cargo_description": "Aluminum Extrusions, Various Profiles",
      "hts_code": "7604.10.1000",
      "declared_country_of_origin": "VN",
      "declared_value_usd": 72030,
      "total_weight_kg": 26200
    },
    
    "line_items": [
      {
        "line_number": 1,
        "sku": "AE-401",
        "description": "Aluminum extrusion profile, anodized",
        "quantity_kg": 12400,
        "unit_value_usd": 2.85,
        "line_total_usd": 35340
      },
      {
        "line_number": 2,
        "sku": "AE-402",
        "description": "Aluminum extrusion profile, mill finish",
        "quantity_kg": 8700,
        "unit_value_usd": 2.40,
        "line_total_usd": 20880
      },
      {
        "line_number": 3,
        "sku": "AE-403",
        "description": "Aluminum extrusion frame component",
        "quantity_kg": 5100,
        "unit_value_usd": 3.10,
        "line_total_usd": 15810
      }
    ],
    
    "routing_history": [
      {
        "event": "Container stuffed",
        "location": "Binh Duong Province, Vietnam",
        "date": "2026-04-12",
        "notes": "Supplier-provided packing record (DISCREPANCY: ISF filed China)"
      },
      {
        "event": "Gate out (export)",
        "location": "Ho Chi Minh City (VNSGN)",
        "date": "2026-04-13",
        "notes": "Export booking confirmed"
      },
      {
        "event": "Vessel departure",
        "location": "VNSGN",
        "date": "2026-04-14",
        "notes": "MV Pacific Horizon, IMO 9834521"
      },
      {
        "event": "Port call (AIS tracking)",
        "location": "Nansha Container Terminal, Guangzhou (CNGGZ)",
        "date": "2026-03-25 to 2026-04-06",
        "notes": "Dwell: 11.2 days (5.3× baseline = ANOMALY)"
      },
      {
        "event": "Estimated arrival",
        "location": "Port of Los Angeles (USLAX)",
        "date": "2026-05-01",
        "notes": "Within 72-hour pre-arrival window"
      }
    ],
    
    "parties_and_roles": [
      {
        "party_name": "Greenfield Industrial Trading Co., Ltd.",
        "role": "Shipper (Exporter)",
        "country": "VN",
        "risk_flag": "Trading company with no confirmed manufacturing facility",
        "risk_level": "HIGH"
      },
      {
        "party_name": "Guangdong Greenfield Aluminum Mfg. Co., Ltd.",
        "role": "Senzing-resolved Parent Entity",
        "country": "CN",
        "risk_flag": "18 prior direct China-origin CBP filings; aluminum extrusion producer",
        "risk_level": "CRITICAL"
      },
      {
        "party_name": "Greenfield Global Metals Holdings Ltd.",
        "role": "Intermediate Holding Company",
        "country": "HK",
        "risk_flag": "Shared beneficial owner; Hong Kong registration (Oct 2024)",
        "risk_level": "HIGH"
      },
      {
        "party_name": "SunPath Energy Distributors LLC",
        "role": "Consignee (U.S. Importer)",
        "country": "US",
        "risk_flag": "No prior trade history before Nov 2025",
        "risk_level": "MEDIUM"
      },
      {
        "party_name": "Saigon Global Logistics JSC",
        "role": "Freight Forwarder",
        "country": "VN",
        "risk_flag": "Shared forwarder across all three entity tiers",
        "risk_level": "MEDIUM"
      },
      {
        "party_name": "West Coast Customs Services",
        "role": "Licensed Customs Broker (U.S.)",
        "country": "US",
        "risk_flag": "Broker coordination with forwarder warrants review",
        "risk_level": "LOW"
      }
    ],
    
    "entity_ownership_chain_senzing": [
      {
        "tier": 1,
        "entity_name": "Greenfield Industrial Trading Co., Ltd.",
        "jurisdiction": "Binh Duong Province, Vietnam",
        "registration_date": "2025-01-15",
        "senzing_entity_id": 1001,
        "senzing_confidence": 0.91,
        "matching_evidence": [
          "NAME_ORG: Greenfield (transliteration match to Chinese 绿田)",
          "REGISTERED_ADDRESS: Freight forwarding office (not manufacturing)"
        ]
      },
      {
        "tier": 2,
        "entity_name": "Greenfield Global Metals Holdings Ltd.",
        "jurisdiction": "Hong Kong SAR",
        "registration_date": "2024-10-15",
        "senzing_entity_id": 1002,
        "senzing_confidence": 0.87,
        "matching_evidence": [
          "BENEFICIAL_OWNER: Shared with Vietnamese entity",
          "FREIGHT_FORWARDER: Same LSP across all tiers"
        ]
      },
      {
        "tier": 3,
        "entity_name": "Guangdong Greenfield Aluminum Mfg. Co., Ltd. (广东绿田铝业制造有限公司)",
        "jurisdiction": "Nanhai District, Foshan, Guangdong, China",
        "registration_date": "2015-06-20",
        "senzing_entity_id": 1003,
        "senzing_confidence": 0.98,
        "prior_cbp_filings": 18,
        "matching_evidence": [
          "DIRECTOR_NAME: Shared (Wang Haohui, registered in multiple entities)",
          "PHONE_NUMBER: Foshan area code (0757) matching registered agent",
          "COMMERCIAL_RECORDS: Aluminum extrusion producer (18 prior shipments HTS 7604.10.1000)"
        ]
      }
    ],
    
    "historical_import_pattern_analysis": [
      {
        "month": "2025-11",
        "shipments": 1,
        "total_weight_kg": 18500,
        "declared_origin": "MY",
        "average_unit_value_usd": 2.15,
        "notes": "Initial entry, Malaysia origin"
      },
      {
        "month": "2025-12",
        "shipments": 2,
        "total_weight_kg": 41200,
        "declared_origin": "TH",
        "average_unit_value_usd": 2.22,
        "notes": "Origin shifted to Thailand (avoidance pattern?)"
      },
      {
        "month": "2026-01",
        "shipments": 2,
        "total_weight_kg": 39800,
        "declared_origin": "VN",
        "average_unit_value_usd": 2.35,
        "notes": "Origin shifted to Vietnam (avoidance escalation)"
      },
      {
        "month": "2026-02",
        "shipments": 3,
        "total_weight_kg": 62900,
        "declared_origin": "VN",
        "average_unit_value_usd": 2.41,
        "notes": "Volume increased sharply post-AD/CVD expansion"
      },
      {
        "month": "2026-03",
        "shipments": 4,
        "total_weight_kg": 88100,
        "declared_origin": "VN",
        "average_unit_value_usd": 2.37,
        "notes": "Sustained high volume (evasion scheme in full effect)"
      },
      {
        "month": "2026-04",
        "shipments": 1,
        "total_weight_kg": 26200,
        "declared_origin": "VN",
        "average_unit_value_usd": 2.48,
        "notes": "Current shipment (in transit)"
      }
    ],
    
    "trade_flow_intelligence": [
      {
        "shipment_id": "SHP-11201",
        "month": "2025-11",
        "declared_origin": "MY",
        "export_port": "Port Klang",
        "transit_days": 18,
        "weight_kg": 18500,
        "unit_value": 2.15,
        "status": "Delivered",
        "consignee": "SunPath Energy Distributors LLC"
      },
      {
        "shipment_id": "SHP-11844",
        "month": "2025-12",
        "declared_origin": "TH",
        "export_port": "Laem Chabang",
        "transit_days": 19,
        "weight_kg": 20400,
        "unit_value": 2.18,
        "status": "Delivered",
        "consignee": "SunPath Energy Distributors LLC"
      },
      {
        "shipment_id": "SHP-13088",
        "month": "2026-04",
        "declared_origin": "VN",
        "export_port": "VNSGN",
        "transit_days": 20,
        "weight_kg": 26200,
        "unit_value": 2.48,
        "status": "In Transit",
        "consignee": "SunPath Energy Distributors LLC"
      }
    ],
    
    "document_review": [
      {
        "document_type": "Commercial Invoice",
        "received": true,
        "key_data": "Origin stated as Vietnam",
        "match_to_shipment": "Partial",
        "concern": "Generic invoice, lacking production details"
      },
      {
        "document_type": "Packing List",
        "received": true,
        "key_data": "3 line items, 26,200 kg total",
        "match_to_shipment": "Yes",
        "concern": "No factory lot numbers or serial tracking"
      },
      {
        "document_type": "Bill of Lading",
        "received": true,
        "key_data": "SAMPLE-BOL-2026-001",
        "match_to_shipment": "Yes",
        "concern": "No contradiction but insufficient alone"
      },
      {
        "document_type": "Certificate of Origin",
        "received": true,
        "key_data": "Vietnam origin checked",
        "match_to_shipment": "Partial",
        "concern": "Template-like, limited production evidence"
      },
      {
        "document_type": "Purchase Order",
        "received": true,
        "key_data": "U.S. consignee order dated 2026-03-28",
        "match_to_shipment": "Yes",
        "concern": "Does not identify source factory"
      },
      {
        "document_type": "Factory Production Record",
        "received": false,
        "key_data": "Not provided",
        "match_to_shipment": "No",
        "concern": "MAJOR GAP — Origin verification requires production proof"
      },
      {
        "document_type": "Bill of Materials",
        "received": false,
        "key_data": "Not provided",
        "match_to_shipment": "No",
        "concern": "MAJOR GAP — No raw material traceability"
      }
    ],
    
    "document_consistency_analysis": [
      {
        "data_element": "Shipper name",
        "invoice": "Greenfield Industrial Trading Co., Ltd.",
        "packing_list": "Greenfield Industrial Trading Co., Ltd.",
        "bol": "Greenfield Industrial Trading Co., Ltd.",
        "certificate_of_origin": "Greenfield Industrial Trading Co., Ltd.",
        "consistency": "CONSISTENT",
        "risk_flag": "Name consistent but identity unverified"
      },
      {
        "data_element": "Country of origin",
        "invoice": "Vietnam",
        "packing_list": "Vietnam",
        "bol": "Vietnam",
        "certificate_of_origin": "Vietnam",
        "consistency": "CONSISTENT",
        "risk_flag": "Consistent declaration but contradicted by ISF Element 9"
      },
      {
        "data_element": "Manufacturing details",
        "invoice": "Not included",
        "packing_list": "Not included",
        "bol": "Not included",
        "certificate_of_origin": "Not included",
        "consistency": "CONSISTENTLY ABSENT",
        "risk_flag": "CRITICAL — No documentation of actual production"
      }
    ],
    
    "supplier_manufacturing_verification": [
      {
        "item": "Factory address",
        "supplier_response": "Industrial Zone, Binh Duong",
        "evidence_provided": "No specific street address or GPS",
        "assessment": "WEAK — Address is freight forwarding office, not factory"
      },
      {
        "item": "Number of extrusion presses",
        "supplier_response": "Multiple presses available",
        "evidence_provided": "No equipment list or capacity report",
        "assessment": "WEAK — Unverified capacity claim"
      },
      {
        "item": "Annual production capacity",
        "supplier_response": "Sufficient for export demand",
        "evidence_provided": "No capacity report or technical specs",
        "assessment": "WEAK — Vague; capacity unverified"
      },
      {
        "item": "Raw aluminum source",
        "supplier_response": "Regional sources (China, Middle East)",
        "evidence_provided": "No supplier invoices or bills of material",
        "assessment": "WEAK — Admits Chinese source but claims Vietnamese transformation"
      },
      {
        "item": "Quality control records",
        "supplier_response": "Available upon request (not provided)",
        "evidence_provided": "None",
        "assessment": "MISSING — No testing or QC documentation"
      }
    ],
    
    "risk_indicator_summary": [
      {
        "indicator": "Origin claim not supported by factory records",
        "evidence": "No production records, QC documents, or lot numbers provided",
        "risk_level": "HIGH",
        "why_matters": "Origin determinations depend on proof of manufacturing"
      },
      {
        "indicator": "Trading company shipper profile",
        "evidence": "Shipper shows no manufacturing facility; address is freight forwarder office",
        "risk_level": "HIGH",
        "why_matters": "Trading entities frequently used to obscure true source"
      },
      {
        "indicator": "Sudden origin shifting (Malaysia → Thailand → Vietnam)",
        "evidence": "3-month pattern: MY (Nov) → TH (Dec) → VN (Jan+)",
        "risk_level": "MEDIUM-HIGH",
        "why_matters": "Systematic routing changes suggest evasion attempt"
      },
      {
        "indicator": "Container stuffing location mismatch (ISF Element 9)",
        "evidence": "ISF filed: Guangzhou, China | Declared: Vietnam",
        "risk_level": "CRITICAL",
        "why_matters": "Direct violation of 19 CFR 149.5; evidence of origin fraud"
      },
      {
        "indicator": "Vessel dwell time anomaly (11.2 days at Guangzhou)",
        "evidence": "5.3× commodity-specific baseline (99th percentile)",
        "risk_level": "HIGH",
        "why_matters": "Dwell time consistent with cargo loading, not transshipment"
      },
      {
        "indicator": "Declared value below market (Vietnam production)",
        "evidence": "AE-402 at $2.40/kg; Chinese billet baseline $2.50-2.60/kg",
        "risk_level": "MEDIUM-HIGH",
        "why_matters": "Price reflects Chinese FOB, not Vietnamese value-added processing"
      }
    ],
    
    "risk_score_breakdown": {
      "components": [
        {
          "component": "Origin Documentation Gap",
          "weight": 25,
          "score": 23,
          "max": 25,
          "percentage": 0.92,
          "basis": "No production records, QC documents, or factory verification"
        },
        {
          "component": "Commodity Sensitivity",
          "weight": 15,
          "score": 14,
          "max": 15,
          "percentage": 0.93,
          "basis": "HTS 7604.10 subject to 374.15% AD/CVD duty from China"
        },
        {
          "component": "Routing Consistency",
          "weight": 15,
          "score": 14,
          "max": 15,
          "percentage": 0.93,
          "basis": "Guangzhou dwell 11.2 days (5.3× baseline) + origin mismatch"
        },
        {
          "component": "Party Profile Risk",
          "weight": 15,
          "score": 15,
          "max": 15,
          "percentage": 1.00,
          "basis": "Shipper resolved to Chinese parent (Senzing, 0.91 confidence)"
        },
        {
          "component": "Historical Pattern Anomaly",
          "weight": 15,
          "score": 12,
          "max": 15,
          "percentage": 0.80,
          "basis": "3-month origin shift (MY→TH→VN); volume spike post-AD/CVD"
        },
        {
          "component": "Time Sensitivity",
          "weight": 15,
          "score": 13,
          "max": 15,
          "percentage": 0.87,
          "basis": "In-transit within 72-hour enforcement window; immediate action possible"
        }
      ],
      "total_score": 91,
      "confidence_tier": "HIGH",
      "composite_formula": "Weighted average of 6 components (25+15+15+15+15+15 = 100 pts)"
    },
    
    "what_if_scenarios": [
      {
        "scenario": "Vietnam is actual country of origin",
        "condition_if_true": "Production records, lot numbers, and source materials all substantiate Vietnamese manufacturing",
        "condition_if_false": "Documents are generic or recycled across shipments; shipper cannot explain production process",
        "impact_on_score": "Score would drop to 15-20 if substantiated; remains 91 if not"
      },
      {
        "scenario": "Shipment only transits Vietnam (not produced)",
        "condition_if_true": "Goods were imported into Vietnam, re-labeled, and exported to U.S. (circumvention)",
        "condition_if_false": "Vietnam conducted legitimate manufacturing (value-add >15%, per Rules of Origin)",
        "impact_on_score": "Score increases to 98 if transit-only confirmed; validates CRITICAL RISK"
      },
      {
        "scenario": "Trading company is legitimate exporter",
        "condition_if_true": "Shipper can show direct production contracts, subcontracting records, and capacity statements",
        "condition_if_false": "Shipper is paper entity with no verifiable manufacturing role",
        "impact_on_score": "Score drops to 35-40 if manufacturing verified; remains 91 if shipper is intermediary only"
      }
    ],
    
    "data_sources_and_uses": [
      {
        "source": "CBP Manifest Feed (manual upload)",
        "data_provided": "Primary shipment ID, shipper/consignee, HTS code, declared COO, weight, value",
        "use_in_assessment": "Primary input for entity resolution and baseline risk scoring"
      },
      {
        "source": "ISF 10+2 Data Element 9 (Altana Atlas API)",
        "data_provided": "Container stuffing location; declared vs. actual port of lading",
        "use_in_assessment": "Direct evidence of origin fraud; pre-arrival signal (18+ days before manifest)"
      },
      {
        "source": "AIS Vessel Tracking (Spire Maritime, MarineTraffic)",
        "data_provided": "Port call history, dwell time, route deviations, vessel operator",
        "use_in_assessment": "Anomaly detection (11.2-day Guangzhou dwell vs. 2.1-day baseline)"
      },
      {
        "source": "Senzing Entity Resolution",
        "data_provided": "Resolved entity IDs, ownership chains, beneficial owners, match confidence",
        "use_in_assessment": "Identifies hidden ownership (Vietnam shipper → Chinese parent); confidence: 0.91"
      },
      {
        "source": "Commercial Bill of Lading Database (Panjiva)",
        "data_provided": "Shipper-consignee trade history, prior routes, historical patterns",
        "use_in_assessment": "Pattern analysis (origin-shifting: MY→TH→VN over 6 months)"
      },
      {
        "source": "AD/CVD Proceedings (Commerce ACCESS)",
        "data_provided": "Active antidumping/countervailing duty orders by HTS code",
        "use_in_assessment": "Tariff evasion incentive quantified (HTS 7604.10: 374.15% duty from China)"
      },
      {
        "source": "Harmonized Tariff Schedule (USITC)",
        "data_provided": "HTS code description, duty rates, classification rules",
        "use_in_assessment": "Confirmed HTS 7604.10.1000 = aluminum extrusions; duty rate lookup"
      },
      {
        "source": "Global Corporate Registry Data (OpenCorporates)",
        "data_provided": "Entity registration date, beneficial owners, directors, addresses",
        "use_in_assessment": "Shipper registered 2025-01-15 (5 months post-AD/CVD expansion); suspicious timing"
      },
      {
        "source": "Neo4j Entity Graph (internal)",
        "data_provided": "Resolved entity relationships: ownership, shared directors, shared addresses",
        "use_in_assessment": "Graph traversal shows Vietnam Co. owned by China Co. via HK holding; 18 prior CN filings"
      }
    ]
  },
  
  "recommended_cbp_action": {
    "primary_action": "EXAMINE_ON_ARRIVAL",
    "focus_areas": [
      "Verification of country-of-origin documentation (production records, factory location verification)",
      "Inspection of cargo markings for consistency with declared Vietnamese origin",
      "Review of Senzing-identified corporate ownership relationship (Greenfield Vietnam → Guangdong China)",
      "Assessment of consignee network in context of prior enforcement actions"
    ],
    "legal_authority": "19 CFR 149.5 (false ISF filing); 19 USC 1481 (entry declaration); EAPA authority",
    "estimated_revenue_impact_usd": 2100000,
    "revenue_basis": "26,200 kg × $3,050/MT (legitimate Vietnamese extrusion value) × (374.15% AD/CVD + 10% Section 232) = $2.1M",
    "timeline_note": "Evidence chain complete; ready for enforcement within 72-hour pre-arrival window"
  },
  
  "investigative_quality_metrics": {
    "evidence_sources": 11,
    "independent_evidence_chains": 4,
    "senzing_confidence": 0.91,
    "data_completeness": 0.94,
    "legal_defensibility": "HIGH"
  }
}
```

---

## Display in UI (ReferralPackagePage.tsx)

The referral package is displayed as an **expandable document view**:

```
┌─────────────────────────────────────────────────────────────┐
│ SENTRY ILLEGAL TRANSSHIPMENT REFERRAL PACKAGE               │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│ Package ID: SENTRY-2026-001                                 │
│ Shipment ID: SHP-001                                        │
│ Status: IN TRANSIT (Arrival: 2026-05-01)                   │
│                                                               │
│ ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓ │
│ ┃ CONFIDENCE: 91/100 — HIGH                                ┃ │
│ ┃ ACTION: EXAMINE_ON_ARRIVAL                               ┃ │
│ ┃ REVENUE IMPACT: $2.1M                                    ┃ │
│ ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛ │
│                                                               │
│ ✓ Shipment Identification  [▼]                              │
│   Bill of Lading: SAMPLE-BOL-2026-001                       │
│   Shipper: Greenfield Industrial Trading Co., Ltd. (Vietnam)│
│   Consignee: SunPath Energy Distributors LLC (Newark, NJ)   │
│   HTS Code: 7604.10.1000 (Aluminum Extrusions)              │
│   Declared COO: Vietnam                                      │
│   Weight: 26,200 kg | Value: $72,030                        │
│                                                               │
│ ✓ Risk Factors  [▼]                                         │
│   🔴 Origin Doc Gap (23/25) — No production records        │
│   🔴 Party Profile Risk (15/15) — Shipper owned by China   │
│   🟠 Routing Anomaly (14/15) — 11.2-day Guangzhou dwell    │
│   🟠 Historical Pattern (12/15) — Origin shift MY→TH→VN    │
│   🟡 Price Anomaly (14/15) — Below Vietnamese manufacturing │
│   🟡 Time Sensitivity (13/15) — In 72-hour window          │
│                                                               │
│ ✓ Entity Ownership Chain (Senzing)  [▼]                    │
│   Tier 1: Greenfield Industrial Trading Co., Ltd. (Vietnam)│
│           └─ Registered Address: Freight Forwarder Office   │
│           └─ Confidence: 0.91                               │
│                                                               │
│   Tier 2: Greenfield Global Metals Holdings Ltd. (Hong Kong)│
│           └─ Shared Beneficial Owner                         │
│                                                               │
│   Tier 3: Guangdong Greenfield Aluminum Mfg. (China)       │
│           └─ Manufacturing Facility (18 Prior CBP Filings) │
│                                                               │
│ ✓ Evidence Chain (Expandable)  [▼]                          │
│   • ISF Element 9: Container in China, declared as Vietnam  │
│   • AIS Data: Guangzhou dwell 11.2 days (99th percentile)   │
│   • Price Analysis: Below Chinese billet cost               │
│   • Document Gap: No factory production records             │
│   • Pattern Analysis: 6-month origin shift                  │
│                                                               │
│ ✓ Recommended Actions  [▼]                                  │
│   □ Examine cargo upon arrival (focus on origin proof)      │
│   □ Review ownership documentation (Greenfield chain)       │
│   □ Inspect cargo markings against declared origin          │
│   □ Assess consignee network (prior enforcement contacts)   │
│                                                               │
│ [📄 Download PDF]  [🔗 Share]  [✓ Accept]  [✎ Modify]      │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

---

## Testing (TDD)

**Test file**: `api/tests/test_referral_package.py`

```python
@pytest.mark.asyncio
async def test_referral_package_greenfield_format():
    """Test referral package structure matches Tables 3-1 to 3-14"""
    
    package = await generate_referral_package(greenfield_shipment)
    
    # Assert structure
    assert 'package_id' in package
    assert 'sections' in package
    assert 'shipment_identification' in package['sections']
    assert 'line_items' in package['sections']
    assert 'ownership_chain_senzing' in package['sections']
    assert 'risk_score_breakdown' in package['sections']
    assert 'recommended_cbp_action' in package
    
    # Assert score
    assert package['total_score'] == 91
    assert package['confidence_level'] == 'HIGH'
    
    # Assert evidence completeness
    assert len(package['sections']['risk_indicator_summary']) == 6
    assert package['sections']['risk_score_breakdown']['total_score'] == 91
```

---

## Export Formats

1. **JSON** — For API/database storage
2. **PDF** — For printing and enforcement handoff
3. **CSV** — For bulk analysis/trending

**PDF generated by**: `api/services/referral/pdf_builder.py` (jinja2 template + weasyprint)

---

## Key: This is THE Deliverable

The referral package is what makes Sentry valuable. It's not just a score—it's an **enforcement-ready case file** that CBP officers can immediately act on.

Everything else (entity resolution, ML scoring, graph visualization) exists to build this package.
