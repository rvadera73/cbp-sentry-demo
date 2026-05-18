# Greenfield Aluminum Case — Complete Seed Data Specification

## Overview

The **Greenfield Aluminum case** is the canonical example used throughout Sentry's documentation, UI demos, and test suites. It demonstrates a real-world illegal transshipment scheme: goods manufactured in China but falsely declared as Vietnamese origin to evade 374.15% antidumping/countervailing duty (AD/CVD) orders.

This document specifies every data point for reproducibility across:
- Backend unit tests (`api/tests/test_referral_package.py`)
- Integration tests (end-to-end pipeline)
- Frontend demo UI (`ui/src/pages/ReferralPackagePage.tsx`)
- Seed database fixtures (`api/seed_data/greenfield_aluminum.json`)

---

## Shipment Overview

| Field | Value | Notes |
|-------|-------|-------|
| **Shipment ID** | SHP-001 | Internal identifier |
| **Bill of Lading** | SAMPLE-BOL-2026-001 | Master BOL |
| **Manifest ID** | MF-2026-001 | CBP manifest reference |
| **Status** | IN TRANSIT | Within 72-hour pre-arrival window |
| **Estimated Arrival** | 2026-05-01 00:00:00Z | Port of Los Angeles (USLAX) |
| **Created At** | 2026-04-28 14:32:00Z | Manifest received |
| **Confidence Score** | 91/100 | HIGH |
| **Recommended Action** | EXAMINE_ON_ARRIVAL | Enforcement-ready |
| **Revenue Impact (USD)** | 2,100,000 | Estimated duties + penalties |

---

## Shipment Identification (Table 3-1)

### Basic Details

```json
{
  "bill_of_lading": "SAMPLE-BOL-2026-001",
  "shipper_name": "Greenfield Industrial Trading Co., Ltd.",
  "shipper_address": "Unit 402, 21 Tran Hung Dao Street, District 1, Ho Chi Minh City, Vietnam",
  "shipper_registration_number": "VN-0320869823",
  "shipper_phone": "+84 28 3822 4156",
  "shipper_email": "export@greenfield-vn.local",
  
  "consignee_name": "SunPath Energy Distributors LLC",
  "consignee_address": "1234 Industrial Boulevard, Newark, NJ 07102, USA",
  "consignee_ein": "98-7654321",
  "consignee_phone": "+1 973 555 0142",
  
  "manifest_id": "MF-2026-001",
  "port_of_lading": "VNSGN",
  "port_of_lading_name": "Ho Chi Minh City (Saigon Port)",
  "port_of_unlading": "USLAX",
  "port_of_unlading_name": "Port of Los Angeles",
  
  "cargo_description": "Aluminum Extrusions, Various Profiles",
  "hts_code": "7604.10.1000",
  "hts_description": "Aluminum extrusions, not further worked",
  "declared_country_of_origin": "VN",
  "declared_value_usd": 72030,
  "total_weight_kg": 26200,
  "total_weight_mt": 26.2,
  "container_count": 1,
  "container_number": "COSCO2026001",
  "container_seal": "SEAL123456"
}
```

### Commodity Details

- **HTS Code**: 7604.10.1000
  - Description: Aluminum extrusions, not further worked
  - Base duty rate: 6.5%
  - AD/CVD rate from China: 374.15% (combined)
  - Section 232 additional: 10%
  - **Total effective duty**: 390.65%

- **Market Context**:
  - Chinese aluminum billet baseline FOB: $2,500–$2,600/MT
  - Legitimate Vietnamese value-add: $150–$200/MT (anodizing, testing)
  - Expected Vietnamese extrusion FOB: $2,650–$2,800/MT
  - **Declared value**: $2,750/MT ($72,030 ÷ 26.2 MT)
  - **Analysis**: Suspiciously aligned with Chinese billet cost, not Vietnamese value-added cost

---

## Line Items (Table 3-2)

Three SKUs representing distinct extrusion profiles:

```json
{
  "line_items": [
    {
      "line_number": 1,
      "sku": "AE-401",
      "description": "Aluminum extrusion profile, anodized, 25×50mm, 6063-T5",
      "hts_code": "7604.10.1000",
      "quantity_kg": 12400,
      "unit_value_usd": 2.85,
      "line_total_usd": 35340,
      "lot_number": "LOT-2026-401",
      "production_date_declared": null,
      "factory_code_declared": null
    },
    {
      "line_number": 2,
      "sku": "AE-402",
      "description": "Aluminum extrusion profile, mill finish, 40×20mm, 6063-T5",
      "hts_code": "7604.10.1000",
      "quantity_kg": 8700,
      "unit_value_usd": 2.40,
      "line_total_usd": 20880,
      "lot_number": "LOT-2026-402",
      "production_date_declared": null,
      "factory_code_declared": null
    },
    {
      "line_number": 3,
      "sku": "AE-403",
      "description": "Aluminum extrusion frame component, anodized, 50×30mm, 6061-T6",
      "hts_code": "7604.10.1000",
      "quantity_kg": 5100,
      "unit_value_usd": 3.10,
      "line_total_usd": 15810,
      "lot_number": "LOT-2026-403",
      "production_date_declared": null,
      "factory_code_declared": null
    }
  ]
}
```

### Risk Analysis

- **Missing production evidence**: No lot numbers, serial tracking, or factory codes
- **Identical unit value across SKUs**: Suggests bulk pricing (characteristic of Chinese commodity pricing), not differentiated Vietnamese value-add pricing
- **No QC documentation**: Real Vietnamese extrusion facilities include per-lot testing certificates

---

## Routing History (Table 3-3 & AIS Data)

### Bill of Lading Events

```json
{
  "routing_history": [
    {
      "event_sequence": 1,
      "event": "Container stuffed",
      "location": "Binh Duong Province, Vietnam",
      "location_coordinates": "10.8867, 106.8312",
      "date": "2026-04-12",
      "time": "14:30:00Z",
      "location_type": "supplier_facility",
      "notes": "Supplier-provided packing record (address: 247 Nguyen Hue Blvd, Dist. 1, HCMC)",
      "evidence_flag": "LOCATION_MISMATCH — This is a freight forwarding office, not manufacturing facility"
    },
    {
      "event_sequence": 2,
      "event": "Gate out (export)",
      "location": "Ho Chi Minh City (VNSGN)",
      "location_coordinates": "10.3573, 106.6843",
      "date": "2026-04-13",
      "time": "08:15:00Z",
      "location_type": "port",
      "notes": "Export booking confirmed by Saigon Global Logistics JSC",
      "evidence_flag": null
    },
    {
      "event_sequence": 3,
      "event": "Vessel departure",
      "location": "VNSGN",
      "date": "2026-04-14",
      "time": "16:45:00Z",
      "location_type": "port",
      "notes": "MV Pacific Horizon, IMO 9834521, Flag: Panama",
      "vessel_operator": "Pacific Shipping Co. (Hong Kong)",
      "evidence_flag": null
    },
    {
      "event_sequence": 4,
      "event": "Port call (AIS tracking)",
      "location": "Nansha Container Terminal, Guangzhou (CNGGZ)",
      "location_coordinates": "22.8048, 113.9406",
      "date_arrival": "2026-03-25",
      "date_departure": "2026-04-06",
      "dwell_days": 11.2,
      "dwell_hours": 268.8,
      "location_type": "port",
      "notes": "Unscheduled port call; no berthing confirmed in Hong Kong or Shenzhen",
      "evidence_flag": "CRITICAL — Container stuffed in Guangzhou (China), not Vietnam"
    },
    {
      "event_sequence": 5,
      "event": "Estimated arrival",
      "location": "Port of Los Angeles (USLAX)",
      "location_coordinates": "33.7534, -118.2126",
      "date": "2026-05-01",
      "time": "00:00:00Z",
      "location_type": "port",
      "notes": "Vessel ETA: 2026-04-30 18:00:00Z (within 72-hour pre-arrival window)",
      "evidence_flag": null
    }
  ]
}
```

### AIS Anomaly Data

```json
{
  "ais_tracking": {
    "vessel_imo": 9834521,
    "vessel_name": "MV Pacific Horizon",
    "vessel_flag": "PA",
    "vessel_callsign": "3FOC6",
    "vessel_operator": "Pacific Shipping Co. Ltd. (Hong Kong)",
    
    "route_summary": "VNSGN → CNGGZ (unscheduled) → USLAX",
    
    "port_calls": [
      {
        "port_code": "VNSGN",
        "port_name": "Ho Chi Minh City",
        "arrival_date": "2026-04-13",
        "departure_date": "2026-04-14",
        "dwell_days": 1.0,
        "arrival_draft_m": 9.2,
        "departure_draft_m": 9.8,
        "notes": "Standard loading"
      },
      {
        "port_code": "CNGGZ",
        "port_name": "Guangzhou (Nansha)",
        "arrival_date": "2026-03-25",
        "departure_date": "2026-04-06",
        "dwell_days": 11.2,
        "dwell_hours": 268.8,
        "arrival_draft_m": 8.1,
        "departure_draft_m": 9.8,
        "berthing_terminal": "Nansha Container Terminal",
        "berthing_address": "Nansha District, Guangzhou, Guangdong, China",
        "notes": "Unscheduled call; vessel arrived light, departed heavy (draft increase = cargo loaded)"
      },
      {
        "port_code": "USLAX",
        "port_name": "Port of Los Angeles",
        "scheduled_arrival": "2026-05-01",
        "status": "Inbound"
      }
    ],
    
    "anomaly_analysis": {
      "commodity": "Aluminum extrusions (HTS 7604.10)",
      "commodity_baseline_dwell_days": 2.1,
      "commodity_baseline_source": "MarineTraffic 2024 statistics for aluminum into LA",
      "actual_dwell_days": 11.2,
      "anomaly_ratio": 5.33,
      "percentile": 99,
      "interpretation": "5.3× normal dwell time = typical for full vessel loading/unloading, not transshipment"
    }
  }
}
```

### ISF Element 9 Contradiction

**ISF Data Element 9** (Container Stuffing Location) — filed 24 hours before container loading:

```json
{
  "isf_filing": {
    "bill_of_lading": "SAMPLE-BOL-2026-001",
    "isf_filing_date": "2026-04-13T08:00:00Z",
    "element_9_container_stuffing_location": "Nansha Container Terminal, Guangzhou, China",
    "element_9_stuffing_coordinates": "22.8048, 113.9406",
    "element_9_date": "2026-03-25 to 2026-04-06",
    
    "declared_country_of_origin": "VN",
    "declared_shipper": "Greenfield Industrial Trading Co., Ltd.",
    
    "isf_contradiction": true,
    "contradiction_summary": "ISF Element 9 places container stuffing in Guangzhou, China, but manifest declares Vietnamese origin.",
    "legal_violation": "19 CFR 149.5 — False origin declaration",
    "regulatory_authority": "U.S. CBP ISF Regulations"
  }
}
```

---

## Entity Ownership Chain (Table 3-5 & Senzing Matching)

### Tier 1 — Vietnamese Shipper (Exporter)

```json
{
  "tier": 1,
  "entity_name": "Greenfield Industrial Trading Co., Ltd.",
  "entity_name_vietnamese": "Công ty Cổ phần Thương mại Công nghiệp Greenfield",
  "legal_structure": "Limited Liability Company (LLC equivalent)",
  "jurisdiction": "Binh Duong Province, Vietnam",
  "registered_address": "Unit 402, 21 Tran Hung Dao Street, District 1, Ho Chi Minh City, Vietnam",
  "registration_number": "VN-0320869823",
  "registration_date": "2025-01-15",
  "registration_source": "Vietnam Department of Planning & Investment",
  
  "business_scope": "International trading; freight forwarding; import/export",
  "tax_id": "VN-123456789",
  
  "beneficial_owners": [
    {
      "name": "Nguyen Van Hung",
      "title": "Director",
      "nationality": "Vietnamese",
      "identification_number": "VN-ID-098765432"
    }
  ],
  
  "senzing_entity_id": 1001,
  "senzing_confidence": 0.91,
  "senzing_match_keys": [
    {
      "match_key_type": "NAME_ORG",
      "match_description": "Greenfield (transliteration match to Chinese 绿田)",
      "confidence": 0.88
    },
    {
      "match_key_type": "REGISTERED_ADDRESS",
      "match_description": "Address is Saigon Global Logistics office, not manufacturing facility",
      "confidence": 0.95,
      "risk_flag": "TRADING COMPANY SHIPPER — Common transshipment schema"
    }
  ],
  
  "prior_filings": 0,
  "entity_age_days": 104,
  "entity_age_months": 3.4,
  "risk_flag": "Recently registered; no manufacturing history; operates as freight forwarder"
}
```

### Tier 2 — Hong Kong Holding Company

```json
{
  "tier": 2,
  "entity_name": "Greenfield Global Metals Holdings Ltd.",
  "legal_structure": "Private Limited Company",
  "jurisdiction": "Hong Kong SAR",
  "registered_address": "Suite 2501, Admiralty Tower, 18 Harcourt Road, Hong Kong",
  "registration_number": "HK-1234567",
  "registration_date": "2024-10-15",
  "registration_source": "Hong Kong Registrar of Companies",
  
  "beneficial_owners": [
    {
      "name": "Wang Haohui (王浩辉)",
      "title": "Director",
      "nationality": "Chinese",
      "identification_number": "CN-ID-370102198605032345"
    }
  ],
  
  "senzing_entity_id": 1002,
  "senzing_confidence": 0.87,
  "senzing_match_keys": [
    {
      "match_key_type": "BENEFICIAL_OWNER",
      "match_description": "Shared with Vietnamese entity (Nguyen Van Hung ≈ Wang Haohui per corporate filings)",
      "confidence": 0.82,
      "notes": "Name appears in multiple tiers; likely proxy arrangement"
    },
    {
      "match_key_type": "FREIGHT_FORWARDER",
      "match_description": "Saigon Global Logistics JSC used by both Vietnamese and HK entities",
      "confidence": 0.91,
      "risk_flag": "SHARED LOGISTICS PROVIDER — Evidence of coordinated scheme"
    }
  ],
  
  "connected_entities": [1001, 1003],
  "ownership_chain_direction": "Intermediate holding company",
  "risk_flag": "Hong Kong registration; recent (Oct 2024); uses shared beneficial owner across tiers"
}
```

### Tier 3 — Chinese Manufacturer (True Origin)

```json
{
  "tier": 3,
  "entity_name": "Guangdong Greenfield Aluminum Mfg. Co., Ltd.",
  "entity_name_chinese": "广东绿田铝业制造有限公司",
  "legal_structure": "Limited Liability Company",
  "jurisdiction": "Nanhai District, Foshan, Guangdong, China",
  "registered_address": "Building 5, Industrial Zone A, Nanhai District, Foshan, Guangdong 528200, China",
  "registration_number": "CN-GD-2015-000456789",
  "registration_date": "2015-06-20",
  "registration_source": "Guangdong SAMR (State Administration for Market Regulation)",
  "unified_social_credit_code": "91440605MA51D4HM3F",
  
  "business_scope": "Aluminum extrusion manufacturing; primary and fabricated metal products",
  "tax_id": "CN-442006000123456",
  
  "beneficial_owners": [
    {
      "name": "Wang Haohui (王浩辉)",
      "title": "Legal Representative",
      "nationality": "Chinese",
      "identification_number": "CN-ID-370102198605032345"
    }
  ],
  
  "senzing_entity_id": 1003,
  "senzing_confidence": 0.98,
  "senzing_match_keys": [
    {
      "match_key_type": "DIRECTOR_NAME",
      "match_description": "Shared across all tiers: Wang Haohui (CN), Nguyen Van Hung (VN pseudo-translation)",
      "confidence": 0.96,
      "risk_flag": "DIRECTOR LINKAGE — Primary evidence of ownership chain"
    },
    {
      "match_key_type": "PHONE_NUMBER",
      "match_description": "Foshan area code (0757) matching registered agent",
      "confidence": 0.93
    },
    {
      "match_key_type": "COMMERCIAL_RECORDS",
      "match_description": "Aluminum extrusion producer; 18 prior shipments HTS 7604.10.1000 to U.S.",
      "confidence": 0.98
    }
  ],
  
  "prior_cbp_filings": 18,
  "prior_filing_years": "2020-2025",
  "prior_filing_hts_codes": ["7604.10.1000", "7604.21.0000"],
  "prior_filing_declared_origins": ["CN"],
  "prior_filing_quantities_mt": "482.4",
  
  "facilities": [
    {
      "facility_name": "Nanhai Extrusion Plant",
      "address": "Building 5, Industrial Zone A, Foshan",
      "facility_type": "Manufacturing",
      "equipment": "6 extrusion presses (500-1200 tons), 2 anodizing lines",
      "annual_capacity_mt": "3500",
      "employees": "220"
    }
  ],
  
  "risk_flag": "ORIGINAL MANUFACTURER — 18 prior direct U.S. filings under Chinese origin; incentive for transshipment to avoid AD/CVD"
}
```

### Entity Relationship Summary

```
Guangdong Greenfield Aluminum Mfg. (China) ──┐
                                              ├─→ Director: Wang Haohui
                                              │   Shared Address: Foshan area
                    Ownership Chain           │   Prior Filings: 18 (HTS 7604.10)
                         │                    │
                    [Via HK Holding]          │
                         │                    │
                         ▼                    │
Greenfield Global Metals Holdings (Hong Kong)┤─→ Director: Wang Haohui / Proxy
                                              │   Shared Forwarder: Saigon Global
                                              │
                    [Via Beneficial Ownership]│
                         │                    │
                         ▼                    │
Greenfield Industrial Trading (Vietnam) ─────┘─→ Director: Nguyen Van Hung (proxy)
                                                  Address: Forwarder Office (not factory)
                                                  Registered: Jan 2025 (5 months post-AD/CVD)
```

---

## Historical Import Pattern Analysis (Table 3-6)

Six-month pattern showing systematic **origin-shifting**: Malaysia → Thailand → Vietnam

```json
{
  "historical_import_patterns": [
    {
      "month": "2025-11",
      "period_start": "2025-11-01",
      "period_end": "2025-11-30",
      "shipments": 1,
      "total_weight_kg": 18500,
      "total_weight_mt": 18.5,
      "declared_origin": "MY",
      "declared_origin_name": "Malaysia",
      "average_unit_value_usd": 2.15,
      "total_value_usd": 39775,
      "vessel_ports": ["MYPKG", "USLAX"],
      "transit_days": 18,
      "consignee": "SunPath Energy Distributors LLC",
      "pattern_notes": "Initial entry; Malaysia origin (lowest AD/CVD exposure)",
      "pattern_risk": "INITIAL_ENTRY"
    },
    {
      "month": "2025-12",
      "period_start": "2025-12-01",
      "period_end": "2025-12-31",
      "shipments": 2,
      "total_weight_kg": 41200,
      "total_weight_mt": 41.2,
      "declared_origin": "TH",
      "declared_origin_name": "Thailand",
      "average_unit_value_usd": 2.22,
      "total_value_usd": 91464,
      "vessel_ports": ["THLCH", "USLAX"],
      "transit_days": 19,
      "consignee": "SunPath Energy Distributors LLC",
      "pattern_notes": "Origin shifted to Thailand; doubling of volume post-Nov tariff notices",
      "pattern_risk": "ORIGIN_SHIFT_EARLY_EVASION"
    },
    {
      "month": "2026-01",
      "period_start": "2026-01-01",
      "period_end": "2026-01-31",
      "shipments": 2,
      "total_weight_kg": 39800,
      "total_weight_mt": 39.8,
      "declared_origin": "VN",
      "declared_origin_name": "Vietnam",
      "average_unit_value_usd": 2.35,
      "total_value_usd": 93580,
      "vessel_ports": ["VNSGN", "USLAX"],
      "transit_days": 20,
      "consignee": "SunPath Energy Distributors LLC",
      "pattern_notes": "Origin shifted to Vietnam; highest AD/CVD avoidance benefit",
      "pattern_risk": "ORIGIN_SHIFT_ESCALATION"
    },
    {
      "month": "2026-02",
      "period_start": "2026-02-01",
      "period_end": "2026-02-28",
      "shipments": 3,
      "total_weight_kg": 62900,
      "total_weight_mt": 62.9,
      "declared_origin": "VN",
      "declared_origin_name": "Vietnam",
      "average_unit_value_usd": 2.41,
      "total_value_usd": 151669,
      "vessel_ports": ["VNSGN", "USLAX"],
      "transit_days": 21,
      "consignee": "SunPath Energy Distributors LLC",
      "pattern_notes": "Volume increased sharply post-AD/CVD expansion (Feb 5, 2025)",
      "pattern_risk": "VOLUME_SPIKE_POST_DUTY"
    },
    {
      "month": "2026-03",
      "period_start": "2026-03-01",
      "period_end": "2026-03-31",
      "shipments": 4,
      "total_weight_kg": 88100,
      "total_weight_mt": 88.1,
      "declared_origin": "VN",
      "declared_origin_name": "Vietnam",
      "average_unit_value_usd": 2.37,
      "total_value_usd": 208837,
      "vessel_ports": ["VNSGN", "USLAX"],
      "transit_days": 20,
      "consignee": "SunPath Energy Distributors LLC",
      "pattern_notes": "Sustained high volume; evasion scheme in full effect",
      "pattern_risk": "SUSTAINED_EVASION"
    },
    {
      "month": "2026-04",
      "period_start": "2026-04-01",
      "period_end": "2026-04-30",
      "shipments": 1,
      "total_weight_kg": 26200,
      "total_weight_mt": 26.2,
      "declared_origin": "VN",
      "declared_origin_name": "Vietnam",
      "average_unit_value_usd": 2.48,
      "total_value_usd": 72030,
      "vessel_ports": ["VNSGN", "USLAX"],
      "transit_days": 20,
      "consignee": "SunPath Energy Distributors LLC",
      "pattern_notes": "Current shipment (in transit); consistent with established pattern",
      "pattern_risk": "IN_TRANSIT_PATTERN_MATCH",
      "is_current_shipment": true
    }
  ],
  
  "pattern_summary": {
    "origin_shift_sequence": "MY → TH → VN",
    "origin_shift_interpretation": "Systematic routing to minimize AD/CVD exposure",
    "total_shipments": 13,
    "total_weight_mt": 256.8,
    "total_value_usd": 657955,
    "duration_months": 6,
    "volume_trend": "Upward after AD/CVD action (Feb 2025)",
    "tariff_evasion_incentive": "374.15% duty on Chinese aluminum → VN circumvention attractive"
  }
}
```

---

## Trade Flow Intelligence (Table 3-7)

```json
{
  "trade_flow_intelligence": [
    {
      "shipment_id": "SHP-11201",
      "month": "2025-11",
      "declared_origin": "MY",
      "export_port": "Port Klang (MYPKG)",
      "export_port_country": "Malaysia",
      "import_port": "USLAX",
      "transit_days": 18,
      "weight_kg": 18500,
      "value_usd": 39775,
      "unit_value": 2.15,
      "status": "Delivered",
      "consignee": "SunPath Energy Distributors LLC",
      "shipper": "Unknown (first consignment)",
      "hts_code": "7604.10.1000"
    },
    {
      "shipment_id": "SHP-11844",
      "month": "2025-12",
      "declared_origin": "TH",
      "export_port": "Laem Chabang (THLCH)",
      "export_port_country": "Thailand",
      "import_port": "USLAX",
      "transit_days": 19,
      "weight_kg": 20400,
      "value_usd": 45288,
      "unit_value": 2.22,
      "status": "Delivered",
      "consignee": "SunPath Energy Distributors LLC",
      "shipper": "TBD Thailand Traders Co., Ltd.",
      "hts_code": "7604.10.1000"
    },
    {
      "shipment_id": "SHP-12201",
      "month": "2026-01",
      "declared_origin": "VN",
      "export_port": "VNSGN",
      "export_port_country": "Vietnam",
      "import_port": "USLAX",
      "transit_days": 20,
      "weight_kg": 19900,
      "value_usd": 46765,
      "unit_value": 2.35,
      "status": "Delivered",
      "consignee": "SunPath Energy Distributors LLC",
      "shipper": "Greenfield Industrial Trading Co., Ltd.",
      "hts_code": "7604.10.1000"
    },
    {
      "shipment_id": "SHP-12456",
      "month": "2026-01",
      "declared_origin": "VN",
      "export_port": "VNSGN",
      "export_port_country": "Vietnam",
      "import_port": "USLAX",
      "transit_days": 20,
      "weight_kg": 19900,
      "value_usd": 46815,
      "unit_value": 2.35,
      "status": "Delivered",
      "consignee": "SunPath Energy Distributors LLC",
      "shipper": "Greenfield Industrial Trading Co., Ltd.",
      "hts_code": "7604.10.1000"
    },
    {
      "shipment_id": "SHP-13088",
      "month": "2026-04",
      "declared_origin": "VN",
      "export_port": "VNSGN",
      "export_port_country": "Vietnam",
      "import_port": "USLAX",
      "transit_days": 20,
      "weight_kg": 26200,
      "value_usd": 72030,
      "unit_value": 2.48,
      "status": "In Transit",
      "consignee": "SunPath Energy Distributors LLC",
      "shipper": "Greenfield Industrial Trading Co., Ltd.",
      "hts_code": "7604.10.1000",
      "is_current_shipment": true
    }
  ]
}
```

---

## Risk Indicator Summary (Table 3-11)

Six risk factors, each with evidence and legal basis:

```json
{
  "risk_indicators": [
    {
      "rank": 1,
      "indicator": "Origin claim not supported by factory records",
      "indicator_type": "DOCUMENT_GAP",
      "risk_level": "HIGH",
      "evidence": "No production records, QC documents, serial lot numbers, or factory verification provided",
      "evidence_sources": ["Commercial Invoice", "Packing List", "Certificate of Origin"],
      "why_matters": "Origin determinations under 19 USC 1481 require substantive proof of manufacturing; absence shifts burden to CBP",
      "legal_authority": "19 USC 1481; 19 CFR 134.1 (country of origin marking)",
      "impact_on_score": 23
    },
    {
      "rank": 2,
      "indicator": "Trading company shipper profile",
      "indicator_type": "PARTY_PROFILE",
      "risk_level": "HIGH",
      "evidence": "Shipper (VN-0320869823) shows no manufacturing facility; registered address is freight forwarder office; no prior manufacturing history",
      "evidence_sources": ["Senzing entity resolution", "Vietnam corporate registry", "Address verification"],
      "why_matters": "Trading entities frequently used as intermediaries to obscure true manufacturing source; high-risk transshipment schema",
      "legal_authority": "19 USC 1484 (entry by importer of record); EAPA authority",
      "impact_on_score": 15
    },
    {
      "rank": 3,
      "indicator": "Sudden origin shifting (Malaysia → Thailand → Vietnam)",
      "indicator_type": "PATTERN_ANOMALY",
      "risk_level": "MEDIUM-HIGH",
      "evidence": "6-month pattern: MY (Nov 2025) → TH (Dec 2025) → VN (Jan+ 2026); volume increases post-AD/CVD action (Feb 5, 2025)",
      "evidence_sources": ["Historical import records", "CBP manifest database", "Panjiva trade flow data"],
      "why_matters": "Systematic routing changes suggest deliberate evasion to minimize AD/CVD exposure; indicates knowledge of prohibited scheme",
      "legal_authority": "19 USC 1517 (EAPA), 19 USC 1593(c) (penalties)",
      "impact_on_score": 12
    },
    {
      "rank": 4,
      "indicator": "Container stuffing location mismatch (ISF Element 9)",
      "indicator_type": "DIRECT_FRAUD_EVIDENCE",
      "risk_level": "CRITICAL",
      "evidence": "ISF Element 9 filed April 13: Container stuffed at Guangzhou, China (Nansha Terminal). Manifest declares Vietnam origin.",
      "evidence_sources": ["ISF 10+2 Element 9", "AIS vessel tracking"],
      "why_matters": "Direct violation of 19 CFR 149.5 (ISF filing accuracy); direct evidence of origin fraud",
      "legal_authority": "19 CFR 149.5; 19 USC 1484 (false entry); EAPA authority",
      "impact_on_score": 14
    },
    {
      "rank": 5,
      "indicator": "Vessel dwell time anomaly (11.2 days at Guangzhou)",
      "indicator_type": "LOGISTICS_ANOMALY",
      "risk_level": "HIGH",
      "evidence": "MV Pacific Horizon dwell at Guangzhou (March 25 – April 6) = 11.2 days. Commodity baseline for aluminum at CNGGZ = 2.1 days (99th percentile). Anomaly ratio: 5.3×.",
      "evidence_sources": ["AIS tracking (Spire/MarineTraffic)", "MarineTraffic historical baselines"],
      "why_matters": "Dwell time consistent with full cargo loading/unloading at Chinese manufacturing facility, not transshipment pass-through",
      "legal_authority": "Circumstantial evidence supporting ISF stuffing location",
      "impact_on_score": 14
    },
    {
      "rank": 6,
      "indicator": "Declared value below legitimate Vietnamese manufacturing cost",
      "indicator_type": "PRICE_ANOMALY",
      "risk_level": "MEDIUM-HIGH",
      "evidence": "AE-402 at $2.40/kg; Chinese billet FOB baseline $2.50-$2.60/kg; legitimate VN value-add $150-$200/MT would yield $2.65-$2.80/kg FOB. Declared price = Chinese billet cost, not VN finished extrusion.",
      "evidence_sources": ["Commercial Invoice", "Market intelligence (LME, industry pricing)"],
      "why_matters": "Price reflects Chinese FOB cost + freight, not Vietnamese value-added extrusion; indicates false value declaration or misattribution of origin",
      "legal_authority": "19 USC 1481 (accurate entry value); 19 CFR 134.1 (appraisement)",
      "impact_on_score": 14
    }
  ]
}
```

---

## Decoy Shipments (Legitimate Consignees for Discrimination Test)

To avoid discrimination allegations, the referral package must demonstrate that Sentry flags **all** similar-risk shipments, not just this one. Three legitimate (low-risk) control shipments:

```json
{
  "control_shipments": [
    {
      "shipment_id": "CTRL-001",
      "consignee": "Alpine Aluminum USA",
      "shipper": "Hanoi Extrusion Industries",
      "origin": "VN",
      "weight_mt": 18.5,
      "hts_code": "7604.10.1000",
      "score": 22,
      "confidence": "LOW",
      "reason_for_low_score": "Shipper has 12-year operating history; factory verified in Hanoi; production records provided; consistent pricing (VN value-add tier)"
    },
    {
      "shipment_id": "CTRL-002",
      "consignee": "West Coast Metal Supply",
      "shipper": "Thai National Extrusion Co.",
      "origin": "TH",
      "weight_mt": 22.0,
      "hts_code": "7604.10.1000",
      "score": 18,
      "confidence": "LOW",
      "reason_for_low_score": "Shipper established 2008; factory in Bangkok verified; direct production contracts provided; price aligned with Thai labor cost"
    },
    {
      "shipment_id": "CTRL-003",
      "consignee": "Premium Metals LLC",
      "shipper": "Greenfield Extrusions (Malaysia)",
      "origin": "MY",
      "weight_mt": 15.3,
      "hts_code": "7604.10.1000",
      "score": 19,
      "confidence": "LOW",
      "reason_for_low_score": "Different Greenfield entity (registered MY-9876543, 2010); no shared directors; independent freight forwarder; factory visits documented"
    }
  ]
}
```

---

## Score Breakdown (Table 3-12)

Weighted 6-component scoring system resulting in **91/100**:

```json
{
  "risk_score_breakdown": {
    "total_score": 91,
    "max_score": 100,
    "confidence_level": "HIGH",
    "confidence_threshold": "80-100",
    
    "components": [
      {
        "rank": 1,
        "component_name": "Origin Documentation Gap",
        "component_code": "ORIGIN_DOC_GAP",
        "weight_pct": 25,
        "max_points": 25,
        "earned_points": 23,
        "component_score": 0.92,
        "basis": "No production records, QC documents, factory verification, or lot-level traceability provided"
      },
      {
        "rank": 2,
        "component_name": "Commodity Sensitivity",
        "component_code": "COMMODITY_SENSITIVITY",
        "weight_pct": 15,
        "max_points": 15,
        "earned_points": 14,
        "component_score": 0.93,
        "basis": "HTS 7604.10 subject to 374.15% AD/CVD from China; Section 232 adds 10%; total 390.65% duty incentive"
      },
      {
        "rank": 3,
        "component_name": "Routing Consistency",
        "component_code": "ROUTING_CONSISTENCY",
        "weight_pct": 15,
        "max_points": 15,
        "earned_points": 14,
        "component_score": 0.93,
        "basis": "Guangzhou dwell 11.2 days (5.3× baseline) + ISF Element 9 stuffing location contradiction"
      },
      {
        "rank": 4,
        "component_name": "Party Profile Risk",
        "component_code": "PARTY_PROFILE_RISK",
        "weight_pct": 15,
        "max_points": 15,
        "earned_points": 15,
        "component_score": 1.00,
        "basis": "Shipper (Senzing ID 1001) resolved to Chinese manufacturer (ID 1003) via shared director; 18 prior CN filings"
      },
      {
        "rank": 5,
        "component_name": "Historical Pattern Anomaly",
        "component_code": "HISTORICAL_PATTERN",
        "weight_pct": 15,
        "max_points": 15,
        "earned_points": 12,
        "component_score": 0.80,
        "basis": "6-month origin shift (MY→TH→VN); volume spike post-AD/CVD expansion (Feb 5, 2025); 13 shipments in 6 months"
      },
      {
        "rank": 6,
        "component_name": "Time Sensitivity",
        "component_code": "TIME_SENSITIVITY",
        "weight_pct": 15,
        "max_points": 15,
        "earned_points": 13,
        "component_score": 0.87,
        "basis": "In-transit within 72-hour enforcement window; vessel ETA 2026-05-01; evidence chain complete for immediate action"
      }
    ],
    
    "composite_calculation": "Weighted average = (23×0.25 + 14×0.15 + 14×0.15 + 15×0.15 + 12×0.15 + 13×0.15) ÷ 1.00 = 91/100"
  }
}
```

---

## Test Fixture (api/seed_data/greenfield_aluminum.json)

The complete seed data is stored in JSON format for reproducible testing:

```json
{
  "greenfield_aluminum": {
    "shipment_id": "SHP-001",
    "bill_of_lading": "SAMPLE-BOL-2026-001",
    "manifest_id": "MF-2026-001",
    "shipper": {
      "name": "Greenfield Industrial Trading Co., Ltd.",
      "address": "Unit 402, 21 Tran Hung Dao Street, District 1, Ho Chi Minh City, Vietnam",
      "registration_number": "VN-0320869823"
    },
    "consignee": {
      "name": "SunPath Energy Distributors LLC",
      "address": "1234 Industrial Boulevard, Newark, NJ 07102, USA",
      "ein": "98-7654321"
    },
    "cargo": {
      "hts_code": "7604.10.1000",
      "declared_origin": "VN",
      "weight_kg": 26200,
      "value_usd": 72030
    },
    "expected_score": 91,
    "expected_confidence": "HIGH",
    "expected_action": "EXAMINE_ON_ARRIVAL"
  }
}
```

---

## References

- **CLAUDE.md**: Project architecture, tech stack, deployment
- **REFERRAL_PACKAGE.md**: Output format (Tables 3-1 to 3-14)
- **ARCHITECTURE.md**: Three-horizon pipeline, scoring tiers
- **API_CONTRACT.md**: `/api/score/{shipment_id}` endpoint
- **DATABASE_SCHEMA.md**: PostgreSQL + Neo4j storage
- **Testing**: `api/tests/test_referral_package.py`, `api/tests/test_greenfield.py`
