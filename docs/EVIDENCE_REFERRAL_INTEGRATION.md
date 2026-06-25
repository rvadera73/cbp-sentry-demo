# Evidence Tab & Referral Package Integration
**Version:** 1.0 (June 2026)  
**Status:** Authoritative Reference  
**Related:** `docs/RISK_SCORING_ARCHITECTURE.md`

---

## 1. Overview: Tabs → Referral Package Flow

Each investigation tab feeds specific sections of the CSOP-BP-GS-26-0001 referral package.
The **Referral (New)** tab is the *assembler* — it pulls pre-built data from all other tabs,
allows investigator annotation, generates AI narratives for sections requiring synthesis,
then produces the final PDF.

```
┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐
│  Risk Analysis  │   │    Evidence     │   │     Entity      │   │    Shipment     │
│  (3-11, 3-12,   │   │  (3-8, 3-9,     │   │  (3-4, 3-5)     │   │  (3-1, 3-2,     │
│   3-13)         │   │   3-10)         │   │                 │   │   3-3)          │
└────────┬────────┘   └────────┬────────┘   └────────┬────────┘   └────────┬────────┘
         │                     │                     │                     │
         └─────────────────────┴─────────────────────┴─────────────────────┘
                                          │
                                          ▼
                              ┌───────────────────────┐
                              │    Referral (New)     │
                              │    ASSEMBLER          │
                              │                       │
                              │  + AI Narratives for: │
                              │    3-6, 3-7, 3-14     │
                              └───────────┬───────────┘
                                          │
                                          ▼
                              ┌───────────────────────┐
                              │  CSOP PDF Package     │
                              │  (14 sections)        │
                              │  + Investigator notes │
                              └───────────────────────┘
```

---

## 2. CSOP Section Mapping

### Sections by Data Source

| Section | Title | Tab | Data Status | Generation |
|---|---|---|---|---|
| **3-1** | Shipment Identification | Shipment | ✅ Live from DB | Auto-populated |
| **3-2** | Line Items & Commodity | Shipment | ✅ Live from DB | Auto-populated |
| **3-3** | AIS Routing History | Evidence/Entity | ✅ Live (dwell, ports) | Auto-populated |
| **3-4** | Parties & Roles | Entity | ✅ Live from DB | Auto-populated |
| **3-5** | Entity Ownership Chain | Entity | ⚠️ Gate 2 (CORD) | Placeholder until CORD migration |
| **3-6** | Historical Import Pattern | — | ⚠️ Partial | Gemini AI narrative |
| **3-7** | Trade Flow Intelligence | — | ⚠️ Partial | Gemini AI narrative |
| **3-8** | Document Review | Evidence | ✅ Live (HS-based checklist) | Auto-populated, investigator edits |
| **3-9** | ISF Document Consistency | Evidence | ✅ Live (element9 data) | Auto-populated |
| **3-10** | Supplier Manufacturing | Evidence | ⚠️ Partial | Shipper age + capacity stub |
| **3-11** | Risk Indicator Summary | Risk Analysis | ✅ Live (rule engine v2) | Auto-populated from critical_indicators |
| **3-12** | Risk Score Breakdown | Risk Analysis | ✅ Live (compound multiplier) | Auto-populated from calculation_table |
| **3-13** | What-If Scenarios | Risk Analysis | ✅ Live (rule engine) | Auto-populated |
| **3-14** | Conclusion & Recommendation | — | ✅ Derived | Gemini AI summary |

**Legend:** ✅ Full data available | ⚠️ Partial/AI-assisted | ❌ Not yet implemented

---

## 3. Evidence Tab — Three Pillars

The Evidence tab serves as the **pre-referral evidence assembly workspace**.

### Pillar 1 — Documentary Evidence (Tables 3-8, 3-9)

**Purpose:** Establish what documents are present, missing, or inconsistent.

**Data sources:**
- `shipment.hs_code` → determines required document list (hardcoded by HS family)
- `shipment.element9_is_mismatch` → flags ISF Element 9 inconsistency
- `shipment.element9_declared_country` / `element9_actual_country` → shows discrepancy
- `shipment.isf_data` (jsonb) → ISF filing details if ingested

**Required document lists by HS code:**

| HS Family | Commodity | Critical Documents |
|---|---|---|
| 7604 | Aluminum extrusions | Invoice, BOL, Packing List, COO, Factory Records, BOM, Raw Material Invoices |
| 8541 | Solar panels | Invoice, BOL, Packing List, COO, Technical Specs, Wafer/Cell Declaration |
| 7210/7225 | Flat-rolled steel | Invoice, BOL, Packing List, COO, Mill Test Certificate, Sourcing Declaration |
| 6203/6204 | Garments | Invoice, BOL, Packing List, COO, Cutting Orders, Fabric Sourcing |
| Default | General | Invoice, BOL, Packing List, COO |

**Auto-received** (from ISF/manifest): Commercial Invoice, BOL, Packing List  
**Must request from importer:** Factory Records, BOM, Test Certificates, Mill Certificates

### Pillar 2 — Risk Indicators (Table 3-11)

**Purpose:** Document the specific risk signals that triggered the case.

**Data sources:**
- `scoreData.critical_indicators` from `/api/risk-scoring/comprehensive` (calculation_table)
- `shipment.dwell_days` → AIS dwell anomaly
- `shipment.ad_cvd_rate` → tariff exposure
- `shipment.shipper_age_months` → new entity risk
- `shipment.unit_price_per_kg` + `price_variance_percent` → pricing anomaly
- `shipment.port_calls` → routing sequence

**Critical indicator thresholds:**

| Indicator | Threshold | Risk Level |
|---|---|---|
| ISF Element 9 mismatch | = true | CRITICAL |
| AD/CVD exposure | ≥ 100% | HIGH |
| Dwell time | ≥ 10 days | HIGH (≥ 18 days = CRITICAL) |
| Shipper age | < 6 months | CRITICAL |
| Unit price variance | ≤ -40% | CRITICAL |

### Pillar 3 — Entity & Routing Intelligence (Tables 3-3, 3-4)

**Purpose:** Identify all parties and document the routing chain.

**Data sources:**
- `shipment.shipper_name`, `shipper_country`, `shipper_age_months`
- `shipment.consignee_name`, `consignee_country`
- `shipment.vessel_name`, `vessel_imo`, `vessel_flag`
- `shipment.port_calls`
- CORD entity resolution (Gate 2)

### Evidence Readiness Panel

The panel at the bottom of the Evidence tab tracks four conditions:
1. **Risk score computed** — `selectedCase.risk_score > 0`
2. **Critical indicators documented** — scoring endpoint called
3. **Document checklist reviewed** — ≤ 2 critical docs missing
4. **Party registry complete** — shipper + consignee identified

When all 4 are satisfied → **"Generate CSOP Referral Package"** button activates,
switching to Referral (New) tab with pre-populated data.

---

## 4. Referral (New) Tab — Assembly Workflow

### Step-by-Step Flow

```
Step 1: Pre-populated Case Data
├── Pulls from selectedCase + selectedCaseShipments
├── Shows: shipment ID, parties, HS code, risk score, critical indicators
└── Investigator confirms / corrects any auto-populated fields

Step 2: Evidence Review Checklist
├── Shows same critical indicators from Evidence tab
├── Investigator must check each CRITICAL item as "Reviewed"
└── Enables progression when all critical items reviewed

Step 3: Generate Package
├── Calls POST /api/referral/generate with enriched payload
├── Backend calls Gemini for sections 3-6, 3-7, 3-14
├── Returns full 14-section JSON
└── Displays ComprehensiveReferralViewer

Step 4: Review, Annotate & Submit
├── ComprehensiveReferralViewer with all 14 sections
├── Inline annotation on each section
├── PDF export (html2canvas + jsPDF)
└── Submit action → TRLED referral system
```

### What the Referral API Receives (Enriched Payload)

```json
{
  "shipment_id": "SHP-000211",
  "risk_score": 86.1,
  "confidence_interval": "±17",
  "model_maturity": 15,
  "critical_indicators": [
    "ISF Element 9 origin mismatch (VN declared → CN actual)",
    "High AD/CVD tariff exposure (176%)",
    "Excessive dwell time (21 days)",
    "Newly established shipper (2 months)"
  ],
  "compound_multiplier": 1.35,
  "document_gaps": ["Factory Production Records", "Bill of Materials"],
  "investigator_notes": "Confirmed element 9 discrepancy via vessel tracking..."
}
```

---

## 5. AI-Generated Sections (Gemini)

Three sections require AI narrative generation:

| Section | Prompt Input | Output |
|---|---|---|
| **3-6** Historical Import Pattern | HS code, shipper name, origin country, shipment count, timing | 2-3 paragraphs on import frequency and timing anomalies vs industry baseline |
| **3-7** Trade Flow Intelligence | Shipper-consignee relationship, commodity, declared vs actual origin | Analysis of supply chain coherence and red flags |
| **3-14** Conclusion | All critical indicators, risk score, recommendation | Professional CSOP-formatted conclusion with enforcement recommendation |

**Gemini fallback:** If API key unavailable, structured template narratives are used.

---

## 6. Data Gaps — Gate 2 Requirements

The following sections are incomplete until Gate 2 (30% maturity):

| Gap | Needed For | Source at Gate 2 |
|---|---|---|
| Entity ownership chain | Table 3-5 | CORD PostgreSQL migration + entity graph |
| Historical shipment patterns | Table 3-6 | CBP historical manifest data |
| Actual AIS dwell data | Table 3-3 | AIS vessel tracking API integration |
| Factory verification | Table 3-10 | Supplier database or CBP On-Site verification |
| ISF filing details | Table 3-9 | Live ISF data ingest pipeline |

---

## 7. Referral Package Quality Scoring

Before submission, the package should be assessed:

| Quality Gate | Check | Minimum |
|---|---|---|
| Risk Score | ≥ 65 or h1_level = CRITICAL | Required |
| Critical Indicators | ≥ 1 documented | Required |
| Document Review | Table 3-8 completed | Required |
| AI Narratives | 3-6, 3-7, 3-14 generated | Required |
| Investigator Review | All critical evidence checked | Required |
| Annotation | At least 1 investigator note | Recommended |

---

## 8. Key Files

| File | Purpose |
|---|---|
| `ui/src/v2/components/EvidenceTab.tsx` | Three-pillar evidence assembly tab |
| `ui/src/v2/hooks/useRiskScoring.ts` | Risk scoring hook (exposes critical_indicators) |
| `ui/src/components/referral-generation/ReferralPackageGenerationTab.tsx` | 4-step referral wizard |
| `ui/src/v2/components/ComprehensiveReferralViewer.tsx` | 14-section CSOP viewer |
| `services/api/referral_comprehensive.py` | Backend referral generator |
| `services/api/gemini_referral_narratives.py` | Gemini narrative generation |
