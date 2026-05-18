# Sentry Architecture — Three Horizon Design

## Overview

Sentry implements a **three-horizon intelligence pipeline** that begins detecting illegal transshipment **months before** cargo arrives, completing ~80% of investigative analysis by the time the CBP 72-hour manifest is received.

```
TIME AXIS:
6 months back ◄───────────────── TODAY ────────────────► 72 hours future
     │                              │                          │
     H1                            H2                          H3
  Horizon 1               Horizon 2                     Horizon 3
  Structural              Pre-Manifest                  72-Hour
  Corridor               ISF + AIS                      Manifest
  Intelligence          Intelligence                    Trigger
                                                              │
                                                    80% done ─┘
```

## Three Horizons

### H1 — Structural Corridor Intelligence (Days/Weeks Before)

**Timing**: Runs daily in background (Cloud Scheduler → Cloud Run Job)

**What it does**: Cross-references UN Comtrade bilateral trade statistics, China's General Administration of Customs (GACC) export data, and USITC import statistics to **pre-classify** high-risk corridors before any specific shipment is identified.

**Example**: 
- Chinese billet (HTS 7604.10) exports to Vietnam: $180M (2017) → $1.2B (2023) [6.7× spike]
- Vietnamese finished aluminum exports to U.S.: $42M → $380M [correlated]
- Vietnam has no domestic smelting capacity — import dependency on China
- **Conclusion**: CRITICAL STRUCTURAL RISK corridor
- U.S. AD/CVD duties on Chinese aluminum: 374.15% → evasion incentive is massive

**Data Sources**:
- UN Comtrade (bilateral trade flows)
- GACC (Chinese export data)
- USITC (U.S. import statistics)
- Commerce Department (AD/CVD case history)

**Storage**: Firestore `corridors/{hts6}_{origin}_{destination}` document

**Demo moment**: When a user uploads a manifest, the UI shows: "This aluminum extrusion route (China→Vietnam→US) was classified CRITICAL STRUCTURAL RISK 7 years ago based on macro trade pattern analysis — before this specific shipment was booked."

---

### H2 — Pre-Manifest ISF & Maritime Intelligence (14-22 Days Before)

**Timing**: Triggered when ISF 10+2 filing is received (24 hours before container is loaded at foreign port)

**What it does**: Processes ISF Data Element 9 (container stuffing location) and AIS vessel tracking. Flags direct evidence of origin fraud weeks before the manifest arrives.

**Key Insight**: ISF is filed 24 hours BEFORE the cargo is loaded — not after it's already on the ship. This is a 14-22 day advance warning compared to the 72-hour manifest window.

**Example (Greenfield case)**:
- ISF filed: "Container stuffed at Nansha, Guangzhou, China"
- Declared origin: "Vietnam"
- **This is direct legal evidence of origin fraud** (19 CFR 149.5)
- AIS data confirms MV Pacific Horizon berthed at Guangzhou for 11.2 days (5.3× baseline)
- **Stuffing at Chinese facility + Vietnamese declaration = provable falsification**

**Data Sources**:
- ISF Data Element 9 (via Altana Atlas API, mocked for demo)
- AIS vessel tracking (Spire, MarineTraffic, mocked for demo)
- Commercial BOL history (Panjiva, mocked for demo)

**Storage**: Firestore `shipments/{bill_id}/h2_intelligence` document + Neo4j nodes for vessel/carrier

**Demo moment**: "The ISF filing 18 days ago already placed this cargo in China, contradicting the declared Vietnamese origin. The investigation was already underway."

---

### H3 — 72-Hour Manifest Trigger (When Manifest Received)

**Timing**: Triggered when CBP manifest is received (72 hours before vessel arrival)

**What it does**: Activates full Senzing entity resolution + 4-tier risk scoring + LLM-narrated referral package. **Incorporates H1 and H2 intelligence already gathered.**

**Data Flow**:

```
CBP Manifest (Excel)
    │
    ├─→ Parse manifest: shipper, consignee, HTS, COO, weight, value
    │
    ├─→ Look up H1 corridor risk from Firestore
    │   └─→ "This corridor = CRITICAL STRUCTURAL RISK"
    │
    ├─→ Look up H2 pre-intelligence from Firestore
    │   └─→ "ISF Element 9 contradiction already flagged"
    │
    ├─→ Senzing entity resolution
    │   └─→ Link Vietnam shipper to Chinese parent via shared director
    │
    ├─→ 4-Tier ML Scoring
    │   ├─→ Tier 1: Senzing entity chain depth (Senzing confidence)
    │   ├─→ Tier 2: Isolation Forest (AIS anomaly)
    │   ├─→ Tier 3: LightGBM (supervised classification on EAPA cases)
    │   └─→ Tier 4: Bayesian Belief Network (origin doc fraud + time criticality)
    │
    ├─→ Vertex AI Gemini
    │   ├─→ Generate XAI assertions (why each score component)
    │   └─→ Narrate referral package sections
    │
    └─→ Referral Package (JSON)
        ├─→ Confidence score: 91/100
        ├─→ Risk factors: 6 components with evidence
        ├─→ Entity ownership chain: VN → HK → CN
        ├─→ Recommended action: EXAMINE_ON_ARRIVAL
        └─→ Revenue impact: ~$2.1M duties
```

**Scoring: Four Tiers**

| Tier | Component | Input | Output | Example |
|---|---|---|---|---|
| 1 | Entity Resolution | Senzing graph | Party Profile Risk (0-15 pts) | Shipper linked to CN parent = 15 |
| 2 | Anomaly Detection | AIS dwell time, transit delta | Routing Consistency (0-15 pts) | 11.2-day dwell at Guangzhou = 14 |
| 3 | Supervised Classification | HTS, COO, duty rate, shipper age, price vs. market | Commodity Sens. + Historical Pattern (0-30 pts) | LightGBM outputs prob → split 15/15 |
| 4 | Bayesian Belief Network | All prior tiers + ISF mismatch, price below market | Origin Doc Gap + Time Sensitivity (0-40 pts) | `P(FRAUDULENT=PROBABLE)=0.91` → 23 pts |

**Final Score (Greenfield example)**: 91/100

---

## Data Models

### Firestore Collections

#### `corridors/{corridor_id}`
```json
{
  "hts_6": "760410",
  "origin": "VN",
  "destination": "US",
  "risk_level": "CRITICAL_STRUCTURAL_RISK",
  "created_at": "2018-01-01T00:00:00Z",
  "h1_evidence": {
    "billet_export_spike": "6.7× (2017-2023)",
    "finished_product_correlation": "correlated with AD/CVD tariff action",
    "domestic_capacity": "Vietnam has no commercial primary smelting"
  },
  "ad_cvd_cases": ["A-552-813", "A-570-967"],
  "enforcement_history": "1.8M MT seized 2019; Zhongwang determination 2019"
}
```

#### `shipments/{bill_id}`
```json
{
  "bill_id": "SAMPLE-BOL-2026-001",
  "manifest_id": "MF-2026-001",
  "shipper": "Greenfield Industrial Trading Co., Ltd.",
  "consignee": "SunPath Energy Distributors LLC",
  "hts_code": "7604.10.1000",
  "country_of_origin": "VN",
  "declared_value_usd": 72030,
  "weight_mt": 26.2,
  "h1_intelligence": {
    "corridor_id": "760410_VN_US",
    "risk_level": "CRITICAL_STRUCTURAL_RISK"
  },
  "h2_intelligence": {
    "isf_stuffing_country": "CN",
    "isf_stuffing_location": "Nansha Terminal, Guangzhou",
    "declared_coo": "VN",
    "isf_contradiction_flag": true,
    "ais_dwell_days": 11.2,
    "ais_dwell_baseline": 2.1,
    "ais_anomaly_ratio": 5.3
  },
  "h3_score": {
    "total": 91,
    "confidence_tier": "HIGH",
    "components": [
      { "name": "origin_doc_gap", "score": 23, "max": 25 },
      { "name": "commodity_sensitivity", "score": 14, "max": 15 },
      { "name": "routing_consistency", "score": 14, "max": 15 },
      { "name": "party_profile_risk", "score": 15, "max": 15 },
      { "name": "historical_pattern", "score": 12, "max": 15 },
      { "name": "time_sensitivity", "score": 13, "max": 15 }
    ]
  },
  "referral_package_id": "SENTRY-2026-001"
}
```

#### `referral_packages/{package_id}`
```json
{
  "package_id": "SENTRY-2026-001",
  "shipment_id": "SHP-001",
  "confidence_level": "HIGH",
  "score": 91,
  "recommended_action": "EXAMINE_ON_ARRIVAL",
  "sections": {
    "shipment_id": { /* Table 3-1 */ },
    "line_items": [ /* Table 3-2 */ ],
    "routing_history": [ /* Table 3-3 */ ],
    "parties": [ /* Table 3-4 */ ],
    "ownership_chain": [ /* Table 3-5 */ ],
    "import_pattern": [ /* Table 3-6 */ ],
    "trade_flow": [ /* Table 3-7 */ ],
    "document_review": [ /* Table 3-8 */ ],
    "document_consistency": [ /* Table 3-9 */ ],
    "manufacturing_verification": [ /* Table 3-10 */ ],
    "risk_indicators": [ /* Table 3-11 */ ],
    "score_breakdown": { /* Table 3-12 */ },
    "what_if_scenarios": [ /* Table 3-13 */ ],
    "data_sources": [ /* Table 3-14 */ ]
  }
}
```

### Neo4j Graph Model

**Nodes**:
```
(:Entity {id, name, type, jurisdiction, risk_score, incorporated_date, senzing_confidence})
(:Vessel  {imo, name, flag, operator})
(:HTS     {code, description, ad_rate, cvd_rate})
(:Shipment{bill_id, manifest_id, h1_risk, h2_flag, h3_score})
(:Port    {unlocode, name, country})
```

**Relationships**:
```
(:Entity)-[:OWNED_BY {confidence, match_key}]->(:Entity)
(:Entity)-[:SHARES_DIRECTOR {name}]->(:Entity)
(:Entity)-[:SHIPPED_VIA {shipment_id}]->(:Vessel)
(:Shipment)-[:DECLARED_UNDER]->(:HTS)
(:Entity)-[:CONSIGNED_TO]->(:Entity)
(:Vessel)-[:CALLED_AT {dwell_days, anomaly_ratio}]->(:Port)
(:Entity)-[:PRIOR_ENFORCEMENT {case_id}]->(:Entity)
```

---

## LLM Role (Vertex AI Gemini)

### Point 1 — Manifest Contextualization
Processes manifest fields before entity resolution:
- HTS code disambiguation (e.g., "extruded aluminum" → 7604.10 vs. 7604.21)
- Shipper name transliteration normalization (e.g., "Green Field" vs. "Greenfield")
- Cargo description validation against declared HTS code
- Value anomaly detection (declared $/MT vs. market baseline)

### Point 2 — XAI Assertion Generation
Generates each risk factor as a plain-English evidentiary statement:
- "Senzing resolved Greenfield Industrial Trading Co. to Guangdong Greenfield Aluminum Mfg. Co., Ltd. via shared director Nguyen Van Hung / Wang Haohui and transliterated name match across Vietnamese enterprise registry and Chinese SAMR filings."
- "AIS tracking for MV Pacific Horizon shows 11.2-day dwell at Nansha Container Terminal, Guangzhou — 5.3× the 2.1-day commodity-specific baseline for aluminum at CNGGZ (99th percentile)."

### Point 3 — AI Transparency Panel
When a CBP officer asks "Why did this shipment score 91?", Gemini returns:
- Conversational explanation (not technical jargon)
- Evidence citations with source data
- Impact of each tier on the final score
- Alternative interpretations (what would need to change to lower the score)

---

## Deployment Architecture

### Local Development (Docker Compose)
```
docker-compose up -d
├── sentry-api     (localhost:8000)  | FastAPI + Senzing
├── sentry-ui      (localhost:3000)  | React SPA
└── services       (localhost:xxxx)  | Supporting services
```

### Cloud Deployment (GCP)
```
GitHub push
    ↓
Cloud Build trigger
    ↓
Build sentry-api image (FastAPI + models + Senzing)
Build sentry-ui image (React build + Nginx)
    ↓
Artifact Registry
    ↓
Cloud Run deploy
├── sentry-api service   (us-central1)
└── sentry-ui service    (us-central1)

Backing services:
├── Firestore (default database for all documents)
├── Neo4j Aura Free (entity graph)
├── Cloud Storage (manifests, PDFs)
└── Vertex AI Gemini (LLM inference)

Background jobs:
├── Cloud Scheduler → sentry-h1-job (daily corridor analysis)
└── Cloud Scheduler → sentry-h2-job (triggered on ISF receipt)
```

---

## Security & Compliance

- **FedRAMP High**: Vertex AI Gemini + Cloud Run services are FedRAMP High authorized
- **DHS 4300A**: All CUI handled per DHS requirements
- **FIPS 140-2/140-3**: Cloud KMS encryption for all data at rest
- **PIV/CAC**: Cloud Identity & Access Management for auth
- **Zero Trust**: No data stored in user-accessible paths; all via Firestore/Cloud Storage

---

## Performance Targets

| Operation | Target | Notes |
|---|---|---|
| H1 corridor scoring | < 60s | Cloud Run Job, daily background |
| H2 ISF processing | < 30s | Real-time, sub-minute response |
| H3 manifest ingest + scoring | < 10s | Sub-tier1-second latency target |
| Referral package generation | < 5s | Gemini LLM call + document build |
| Neo4j graph query (Why Connected) | < 1s | Shortest path algorithm |

---

## Testing Strategy

- **Unit tests**: FastAPI routes, ML tier logic, Firestore schema
- **Integration tests**: Senzing + Neo4j + Firestore end-to-end
- **E2E tests**: Full demo flow (ingest → ER → score → graph)
- **Load testing**: Cloud Run auto-scaling under concurrent manifest uploads
