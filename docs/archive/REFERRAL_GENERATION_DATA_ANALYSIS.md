# Referral Package Generation — Complete Data Analysis & Implementation Plan
**Date:** May 27, 2026  
**Scope:** Single Integrated Implementation (No Phases)  
**Data Source:** Live APIs + Existing Database  

---

## 1. DATA SOURCES & AVAILABILITY

### 1.1 Shipment Data (Source: SQLite Database)
**Table:** `shipments`
```python
{
  "id": str,                           # Shipment ID (PK)
  "manifest_id": str,                  # Manifest reference
  "shipper_name": str,                 # Shipper entity
  "shipper_country": str,              # Shipper origin
  "shipper_age_months": int,           # Company age (months)
  "consignee_name": str,               # Consignee entity
  "consignee_country": str,            # Consignee destination
  "origin_country": str,               # Declared origin
  "destination_country": str,          # Declared destination
  "hs_code": str,                      # HTS commodity code
  "commodity_name": str,               # Commodity description
  "declared_value_usd": float,         # Declared value ($)
  "declared_weight_kg": float,         # Declared weight (kg)
  "unit_price_per_kg": float,          # Price per unit
  "price_variance_percent": float,     # Price variance vs market (%)
  "dwell_days": int,                   # Port dwell time (days)
  "port_calls": list,                  # Port sequence
  "vessel_name": str,                  # Vessel name
  "vessel_imo": str,                   # Vessel IMO
  "vessel_flag": str,                  # Flag state
  "ais_stuffing_country": str,         # AIS origin (if available)
  "element9_is_mismatch": bool,        # ISF Element 9 mismatch flag
  "element9_declared_country": str,    # Declared country (ISF)
  "element9_actual_country": str,      # Actual country (ISF)
  "ad_cvd_rate": float,                # Anti-dumping/CVD rate (%)
  "prior_violations": int,             # Historical violations
  "ofac_status": str,                  # OFAC check status
  "ownership_opacity": bool,           # Ownership clarity flag
  "risk_score": float,                 # Calculated risk score (0-100)
  "status": str,                       # Case status
  "created_at": timestamp              # Entry timestamp
}
```
**Availability:** ✅ Complete  
**Records:** 11+ high-risk test cases prepared

---

### 1.2 Line Items (Source: SQLite)
**Table:** `shipment_line_items`
```python
{
  "shipment_id": str,
  "line_number": int,
  "hs_code": str,
  "product_description": str,
  "quantity": float,
  "unit": str,
  "total_value_usd": float
}
```
**Availability:** ✅ Complete  
**Fallback:** If missing, creates from shipment commodity

---

### 1.3 Routing Events (Source: SQLite + AIS APIs)
**Table:** `routing_events`
```python
{
  "shipment_id": str,
  "location": str,
  "event_date": timestamp,
  "event_type": str,  # "loading", "transshipment", "unloading", "dwell"
  "dwell_hours": int
}
```
**API Integration:**
- MarineTraffic API (real-time AIS)
- Spire Maritime (historical tracking)

**Availability:** ✅ Can query via referral_comprehensive_v2.py

---

### 1.4 Parties & Roles (Source: SQLite)
**Table:** `parties_involved`
```python
{
  "shipment_id": str,
  "party_name": str,
  "party_role": str,  # "SHIPPER", "CONSIGNEE", "MANUFACTURER", "BROKER", etc.
  "party_country": str
}
```
**Availability:** ✅ Complete  
**Fallback:** Uses shipper/consignee from shipment table

---

### 1.5 Entity Ownership Chain (Source: CORD Microservice)
**Service:** CORD (Port 8004)
```python
{
  "level": int,                    # 1=L1 (direct), 2=L2 (parent), 3=L3 (UBO)
  "entities": [
    {
      "entity_id": str,
      "name": str,
      "country": str,
      "entity_type": str,          # "Manufacturer", "Trader", "Shell", etc.
      "risk_level": str,           # "low", "medium", "high", "critical"
      "confidence_score": float,   # 0-1
      "data_source": str           # "GLEIF", "OFAC", "OpenCorporates", etc.
    }
  ]
}
```
**API Endpoint:** 
```
POST http://sentry-cord-integration:8004/resolve
Body: { "name": "shipper_name", "country": "shipper_country" }
```
**Availability:** ✅ Live via `_resolve_entities_from_cord()` in referral_comprehensive_v2.py

---

### 1.6 Risk Score & Breakdown (Source: Risk Scoring Engine)
**Service:** `RiskScoringEngine` (Python service)
```python
{
  "final_score": float,            # 0-100
  "risk_level": str,               # "LOW", "MEDIUM", "HIGH", "CRITICAL"
  "components": [
    {
      "component": str,            # "Documentation", "Commodity", "Routing", etc.
      "factor": str,               # Factor name
      "score": float,              # Component score
      "weight": float,             # Weight %
      "weighted_result": float,    # Weighted contribution
      "rationale": str,            # Why this score
      "evidence": [str]            # Evidence items
    }
  ]
}
```
**7 Components:**
1. **Documentation Risk** (35%) - ISF completeness, manifests, compliance
2. **Commodity Risk** (30%) - HS code, AD/CVD status, restrictions
3. **Routing Anomalies** (20%) - AIS dwell, transshipment patterns, rerouting
4. **Party Risk** (10%) - Shipper age, OFAC status, prior violations
5. **Corridor Risk** (5%) - Bilateral trade patterns, origin-destination mismatch

**Availability:** ✅ Live via `risk_engine.score_shipment(shipment)` in referral_router.py

---

### 1.7 AI-Generated Narratives (Source: Gemini 1.5 Flash)
**Service:** `ReferralNarrativeGenerator`
**Sections Generated:**
- **3-6:** Historical Import Pattern (narrative)
- **3-7:** Trade Flow Intelligence (narrative)
- **3-11:** Risk Indicator Summary (narrative)
- **3-14:** Conclusion & Recommendation (narrative)

**Prompts:** Located in `gemini_referral_narratives.py`

**Fallback:** Template narratives if Gemini fails

**Availability:** ✅ Live via API endpoints

---

## 2. COMPLETE API ENDPOINTS

### Generate Full Referral Package
```
POST /api/referrals/{shipment_id}

Response:
{
  "status": "success",
  "referral": {
    "referral_id": "uuid",
    "shipment_id": "SHP-000211",
    "created_at": "2026-05-27T14:35:00Z",
    "risk_score": 87,
    "risk_level": "HIGH",
    "risk_breakdown": {
      "final_score": 87,
      "components": [...]  # 7-factor breakdown
    },
    "sections": {
      "section_3_1_shipment_identification": {...},
      "section_3_2_line_items": {...},
      "section_3_3_routing_history": {...},
      "section_3_4_parties_and_roles": {...},
      "section_3_5_entity_ownership_chain": {...},
      "section_3_6_historical_import_pattern": {
        "pattern_narrative": "AI-generated narrative"
      },
      "section_3_7_trade_flow_intelligence": {
        "trade_flow_narrative": "AI-generated narrative"
      },
      "section_3_8_document_review": {...},
      "section_3_9_document_consistency": {...},
      "section_3_10_supplier_verification": {...},
      "section_3_11_risk_indicators": {
        "summary": "AI-generated summary"
      },
      "section_3_12_pattern_analysis": {...},
      "section_3_13_enforcement_analysis": {...},
      "section_3_14_conclusion_and_recommendation": {
        "conclusion_narrative": "AI-generated conclusion"
      }
    }
  }
}
```

### Retrieve Referral
```
GET /api/referrals/{referral_id}

Response: Same as above
```

### Get Referral for Shipment
```
GET /api/referrals/shipment/{shipment_id}

Response: Same as above
```

### Save Annotations
```
POST /api/referrals/{referral_id}/annotations

Body:
{
  "annotations": [
    {
      "sectionId": "section_3_6_historical_import_pattern",
      "text": "Officer note here",
      "timestamp": "2026-05-27T14:40:00Z",
      "author": "Officer Name"
    }
  ]
}
```

### List Referrals
```
GET /api/referrals?skip=0&limit=20

Response:
{
  "referrals": [...],
  "total": 42
}
```

---

## 3. DATA FLOW ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────────────┐
│                        BROWSER (React)                              │
│                                                                     │
│  ModernCaseInvestigationPage                                       │
│  └─ ReferralPackageGenerationTab (NEW)                             │
│     ├─ Tab 1: ReferralDisplayPanel (displays referral)             │
│     │   ├─ Fetches: GET /api/referrals/{referral_id}              │
│     │   ├─ Data: All 14 sections                                   │
│     │   └─ Edit: Narrative sections with [Edit] + [Regenerate]   │
│     │                                                               │
│     └─ Tab 2: OfficerAnalysisForm (4-step form)                   │
│         ├─ Step 1: Risk Assessment (agree/adjust/confidence)     │
│         ├─ Step 2: Evidence Checklist (7 items to verify)        │
│         ├─ Step 3: Action Recommendation (TRLED/Hold/Release)    │
│         └─ Step 4: Officer Signature (certification + sign)      │
│             └─ Submits: POST /api/officer-analysis                │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
         │
         │ HTTP/REST
         │
┌────────▼──────────────────────────────────────────────────────────────┐
│                    API Gateway (FastAPI, Port 8000)                   │
│                                                                        │
│  Endpoints:                                                            │
│  POST   /api/referrals/{shipment_id}              [Generate]         │
│  GET    /api/referrals/{referral_id}              [Retrieve]         │
│  GET    /api/referrals/shipment/{shipment_id}     [By Shipment]      │
│  POST   /api/referrals/{referral_id}/annotations  [Save Notes]       │
│  GET    /api/referrals                            [List]             │
│  POST   /api/officer-analysis                     [NEW - Save Form]  │
│  GET    /api/officer-analysis/{analysis_id}      [NEW - Retrieve]   │
│                                                                        │
└────────┬──────────────────────────────────────────────────────────────┘
         │
         ├────────────────────┬──────────────────────┬──────────────────┐
         │                    │                      │                  │
         │                    │                      │                  │
    ┌────▼────────┐   ┌──────▼────────┐  ┌─────────▼────┐   ┌────────▼────┐
    │   SQLite     │   │  CORD Service │  │   Gemini API │   │ Risk Engine │
    │  Database    │   │  (Port 8004)  │  │ (Google)     │   │  (Python)   │
    │              │   │               │  │              │   │             │
    │ Tables:      │   │ • Entity      │  │ • Generate   │   │ • Score     │
    │ • shipments  │   │   resolution  │  │   narratives │   │   shipment  │
    │ • line_items │   │ • Ownership   │  │ • Sections   │   │ • Breakdown │
    │ • routing    │   │   chain       │  │   3-6, 3-7,  │   │ • 7-factors │
    │ • parties    │   │ • CORD index  │  │   3-11, 3-14 │   │             │
    │ • entities   │   │   (244K)      │  │              │   │             │
    │              │   │               │  │              │   │             │
    └──────────────┘   └───────────────┘  └──────────────┘   └─────────────┘
```

---

## 4. OFFICER ANALYSIS FORM DATA MODEL

### Step 1: Risk Assessment
```typescript
{
  agreeWithScore: boolean,           // true = accept 87/100, false = adjust
  officerScore?: number,             // 0-100 if officer adjusts
  adjustmentReason?: string,         // required if adjusted
  confidence: 'low' | 'medium' | 'high'  // confidence level
}
```

### Step 2: Evidence Review
```typescript
{
  reviewedItems: {
    "isf_element9_mismatch": {
      reviewed: boolean,
      notes?: string
    },
    "vessel_dwell_anomaly": {
      reviewed: boolean,
      notes?: string
    },
    "price_variance": {
      reviewed: boolean,
      notes?: string
    },
    "entity_resolution": {
      reviewed: boolean,
      notes?: string
    },
    "ais_routing_pattern": {
      reviewed: boolean,
      notes?: string
    },
    "historical_imports": {
      reviewed: boolean,
      notes?: string
    },
    "related_cases": {
      reviewed: boolean,
      notes?: string
    }
  }
}
```

### Step 3: Action Recommendation
```typescript
{
  action: 'execute_trled' | 'hold_examine' | 'release_monitor',
  
  // If execute_trled:
  referralType?: 'EAPA' | 'Duty_Evasion' | 'Fraud' | 'Other',
  priority?: 'low' | 'medium' | 'high',
  holdingPeriodDays?: number,
  assignedDistrict?: string,
  examinerNotes?: string,
  
  // If hold_examine:
  holdDurationDays?: number,
  examinationType?: 'documentary' | 'physical' | 'hybrid',
  examinationScope?: string,
  notifyImporter?: boolean,
  
  // If release_monitor:
  monitoringType?: 'standard' | 'enhanced' | 'realtime',
  monitoringDurationDays?: number,
  conditions?: string,
  auditTrailFlag?: boolean
}
```

### Step 4: Officer Signature
```typescript
{
  caseNarrative: string,           // Min 50 chars, max 2000
  certificationAccepted: boolean,  // Must be true
  officerId: string,               // From session
  officerName: string,
  badgeNumber: string,
  district: string,
  signature: string,               // PIV/CAC or e-signature
  signedAt: timestamp
}
```

---

## 5. COMPLETE IMPLEMENTATION STRUCTURE

### React Components to Create

```
ui/src/components/referral-generation/
├── ReferralPackageGenerationTab.tsx          [Main container, Tab routing]
├── ReferralPackageGenerationTab.css
├── ReferralDisplayPanel.tsx                  [Tab 1 - all 14 sections]
├── ReferralDisplayPanel.css
├── OfficerAnalysisForm.tsx                   [Tab 2 - 4-step form]
├── OfficerAnalysisForm.css
├── sections/
│   ├── ReferralSection.tsx                   [Section card component]
│   ├── ReferralSection.css
│   ├── NarrativeEditModal.tsx               [Edit modal for 3-6, 3-7, 3-11, 3-14]
│   └── NarrativeEditModal.css
├── steps/
│   ├── Step1RiskAssessment.tsx
│   ├── Step1RiskAssessment.css
│   ├── Step2EvidenceReview.tsx
│   ├── Step2EvidenceReview.css
│   ├── Step3ActionRecommendation.tsx
│   ├── Step3ActionRecommendation.css
│   ├── Step4OfficeSignature.tsx
│   ├── Step4OfficeSignature.css
│   └── FormProgress.tsx
├── types/
│   └── ReferralGeneration.types.ts
├── hooks/
│   ├── useReferralDisplay.ts                 [Tab 1 data + edit state]
│   ├── useOfficerAnalysisForm.ts             [Tab 2 form state]
│   ├── usePDFExport.ts                       [PDF generation]
│   └── useNarrativeEdit.ts                   [Edit + regenerate logic]
└── utils/
    ├── pdfFormatter.ts                       [Federal document formatting]
    └── formValidation.ts                     [Step validation]
```

### Backend Endpoints to Create

```
services/api/routers/
└── officer_analysis_router.py

Endpoints:
  POST /api/officer-analysis/{referral_id}
  GET  /api/officer-analysis/{analysis_id}
  GET  /api/officer-analysis/referral/{referral_id}
  POST /api/referral-packages/{referral_id}/finalize
  GET  /api/referral-packages/{package_id}/pdf-export
```

### Database Schema Updates

```sql
-- Officer Analysis Table
CREATE TABLE IF NOT EXISTS officer_analyses (
  analysis_id TEXT PRIMARY KEY,
  referral_id TEXT NOT NULL,
  officer_id TEXT NOT NULL,
  officer_name TEXT,
  badge_number TEXT,
  district TEXT,
  step1_risk_assessment JSON,       -- Risk assessment data
  step2_evidence_checklist JSON,    -- Evidence review data
  step3_action_recommendation JSON, -- Action selected + details
  step4_signature JSON,              -- Signature + certification
  overall_notes TEXT,                -- Officer narrative summary
  submitted_at TIMESTAMP,
  signed_at TIMESTAMP,
  FOREIGN KEY (referral_id) REFERENCES referral_packages(referral_id)
);

-- Referral Packages (enhancement)
ALTER TABLE referral_packages ADD COLUMN (
  edited_sections JSON,             -- Officer-edited narrative sections
  analysis_id TEXT,                 -- Link to officer analysis
  final_package_status TEXT,        -- Draft, Under Review, Finalized, Submitted
  pdf_export_ready BOOLEAN
);

-- Audit Log
CREATE TABLE IF NOT EXISTS audit_log (
  log_id TEXT PRIMARY KEY,
  officer_id TEXT,
  action TEXT,
  referral_id TEXT,
  analysis_id TEXT,
  timestamp TIMESTAMP,
  details JSON
);
```

---

## 6. INTEGRATION WITH EXISTING SYSTEMS

### Use Existing Endpoints
✅ `POST /api/referrals/{shipment_id}` — Generate referral (already works)
✅ `GET /api/referrals/{referral_id}` — Retrieve referral
✅ Risk scoring engine — Already integrated
✅ Gemini narratives — Already integrated
✅ CORD entity resolution — Already integrated

### Extend Existing Components
- Integrate into `ModernCaseInvestigationPage.tsx` as new tab
- Reuse existing `design-tokens.css`
- Reuse `ComprehensiveReferralViewer` logic for Tab 1 display

### Add New Endpoints
- `POST /api/officer-analysis` — Save 4-step form
- `GET /api/officer-analysis/{analysis_id}` — Retrieve form
- `GET /api/referral-packages/{id}/export-pdf` — Export as federal doc

---

## 7. REAL DATA VALIDATION

### Test Shipment Available
```
shipment_id: "shipment-greenfield-001"
- Risk Score: 90+ (CRITICAL)
- Origin: China (Guangzhou)
- Destination: USA (Long Beach)
- Commodity: Aluminum extrusions
- Multiple risk flags: Element 9 mismatch, dwell anomaly, price variance
```

**Confirmed Data Points:**
✅ Complete shipment data in DB
✅ 11+ high-risk test cases prepared
✅ All 14 sections can be generated
✅ Risk engine integration confirmed
✅ Gemini narratives confirmed
✅ CORD entity resolution confirmed
✅ AIS routing data available

---

## 8. IMPLEMENTATION CHECKLIST

### Phase A: UI Components (Real Data, No Mocks)
- [ ] ReferralPackageGenerationTab.tsx - Main container
- [ ] ReferralDisplayPanel.tsx - Tab 1 (14 sections display)
- [ ] ReferralSection.tsx - Collapsible section card
- [ ] NarrativeEditModal.tsx - Edit 3-6, 3-7, 3-11, 3-14
- [ ] OfficerAnalysisForm.tsx - Tab 2 container
- [ ] Step1-4 components - 4-step guided form
- [ ] FormProgress.tsx - Step indicator
- [ ] Integration into ModernCaseInvestigationPage.tsx

### Phase B: Hooks & State Management
- [ ] useReferralDisplay.ts - Fetch + manage Tab 1 data
- [ ] useOfficerAnalysisForm.ts - Manage 4-step form state
- [ ] useNarrativeEdit.ts - Edit + regenerate logic
- [ ] usePDFExport.ts - PDF generation

### Phase C: Styling & Accessibility
- [ ] ReferralDisplayPanel.css - Tab 1 styling
- [ ] OfficerAnalysisForm.css - Form styling
- [ ] Design token integration (colors, spacing, fonts)
- [ ] WCAG 2.1 AA accessibility compliance

### Phase D: Backend APIs
- [ ] officer_analysis_router.py - API endpoints
- [ ] Database schema updates
- [ ] Audit logging
- [ ] Integration with existing referral system

### Phase E: PDF Export
- [ ] pdfFormatter.ts - Federal document formatting
- [ ] PDF generation (using html2pdf + jsPDF)
- [ ] Section 3 referral package style matching

### Phase F: Testing & Deployment
- [ ] Unit tests (components, hooks, validation)
- [ ] Integration tests (API endpoints)
- [ ] E2E testing (complete workflow)
- [ ] Performance testing (large datasets)
- [ ] Accessibility testing

---

## 9. SINGLE INTEGRATED BUILD APPROACH

**No phases — build everything at once:**

1. Create all React components simultaneously
2. Wire complete data flow (API → component → display)
3. Implement 4-step form with full validation
4. Create narrative edit modal with regenerate
5. Build PDF export with federal formatting
6. Create backend API endpoints
7. Database schema updates
8. Test complete end-to-end workflow

**Timeline:** 1-2 weeks for complete implementation with real data

---

**READY TO BUILD** ✅
