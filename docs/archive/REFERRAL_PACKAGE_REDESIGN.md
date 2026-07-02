# Professional Referral Package Redesign - Design Document

## Executive Summary

**Goal:** Transform raw referral API data into professional analytical presentations matching the Precise Software "Illegal Transshipment Referral Package" format.

**Approach:** 
- Map 14 sections (3-1 through 3-14) from API response to professional Table format
- Use Gemini LLM to analyze raw data and generate professional narratives
- Display with professional styling and visual analysis
- Include risk factor analysis, confidence scores, and enforcement recommendations

**Feasibility:** ✅ YES - Medium complexity, 3-4 hour implementation

---

## Current State Analysis

### What the API Provides:
```
{
  "referral_id": "...",
  "shipment_id": "SHP-000211",
  "risk_tier": "LOW",
  "risk_score": 32.36,
  "sections": {
    "section_3_1_shipment_identification": {...},
    "section_3_2_line_items": {...},
    "section_3_3_routing_history": {...},
    ...14 sections total
  },
  "risk_breakdown": {
    "final_score": 32.36,
    "components": [...]
  }
}
```

### What We Need to Generate:

Professional referral sections with:
1. **Professional table format** (matching Table 3-X in Precise document)
2. **Risk factor narratives** (AI-generated analysis)
3. **Visual analysis** (charts, gauges, patterns)
4. **Confidence scores** (overall and per-factor)
5. **Evidence chains** (structured reasoning)
6. **Enforcement recommendations** (actionable next steps)

---

## Section-by-Section Mapping

### Table 3-1: Shipment Identification ✅
**Current Data:** Shipper, consignee, commodity, HTS code, BOL, origin
**Transformation:**
- Extract fields into professional table format
- Gemini: Analyze if origin claim is supported by commodity profile
- Output: Professional table + Risk assessment narrative

**Feasible?** ✅ YES - Data available in API

---

### Table 3-2: Line-Item Detail ✅
**Current Data:** SKU, product description, quantity, unit value
**Transformation:**
- Format as professional line-item table
- Gemini: Analyze unit values for price anomalies vs market baselines
- Calculate total value, identify suspicious pricing

**Feasible?** ✅ YES - Data available in API

---

### Table 3-3: Routing History ✅
**Current Data:** Port of lading, port of unlading, transit dates
**Transformation:**
- Create timeline with event dates and locations
- Gemini: Analyze AIS data for dwell time anomalies
- Flag routing inconsistencies vs commodity baselines

**Feasible?** ✅ YES - Data available; AIS analysis can be added

---

### Table 3-4: Parties and Roles ✅
**Current Data:** Shipper, consignee, freight forwarder, carrier, broker
**Transformation:**
- Format as professional party registry table
- Gemini: Flag parties with prior enforcement history
- Note network connections and broker relationships

**Feasible?** ✅ YES - Data available in API

---

### Table 3-5: Entity Ownership Chain Analysis ⚠️
**Current Data:** Limited - only shipper/consignee names
**Transformation:**
- Gemini: Analyze corporate names for evidence of shell companies
- Cross-reference against enforcement history
- Map ownership chains if identifiable from name patterns
- Identify beneficial owner concerns

**Feasible?** ⚠️ PARTIAL - Requires Senzing integration for full entity resolution
**Workaround:** Use Gemini to infer ownership patterns from name analysis

---

### Table 3-6: Historical Import Pattern Analysis ⚠️
**Current Data:** Single shipment record, no historical data
**Transformation:**
- Gemini: Analyze commodity code for tariff evasion patterns
- Identify if origin country changed recently (from other shipments)
- Flag if timing correlates with new AD/CVD orders

**Feasible?** ⚠️ PARTIAL - Would need historical shipment data from CBP
**Workaround:** Gemini can generate risk assessment based on commodity + origin combination

---

### Table 3-7: Trade Flow Intelligence ⚠️
**Current Data:** Shipper/consignee pair, commodity, declared origin
**Transformation:**
- Gemini: Analyze shipper-consignee relationship for consistency
- Flag if relationship is new or atypical
- Assess supply chain coherence

**Feasible?** ⚠️ PARTIAL - Limited historical data available
**Workaround:** Gemini can generate analysis of supply chain plausibility

---

### Table 3-8: Document Review ⚠️
**Current Data:** None in API (would need to be ingested)
**Transformation:**
- Gemini: Prompt to assess what documents SHOULD be present
- Flag missing documents (Factory records, BOM, etc.)
- Assess document completeness

**Feasible?** ⚠️ NO DATA - But Gemini can generate framework
**Workaround:** Display checklist of required documents and risk assessment

---

### Table 3-9: Document Consistency Analysis ⚠️
**Current Data:** None in API
**Transformation:**
- Gemini: Generate framework for consistency checks
- Flag missing data fields across documents

**Feasible?** ⚠️ NO DATA - Gemini can generate template

---

### Table 3-10: Supplier Manufacturing Verification ⚠️
**Current Data:** Commodity, declared origin, shipper profile
**Transformation:**
- Gemini: Assess plausibility of manufacturing in declared country
- Flag if commodity requires facilities beyond stated capacity
- Identify missing verification evidence

**Feasible?** ⚠️ PARTIAL - Gemini can generate risk assessment framework

---

### Table 3-11: Risk Indicator Summary ✅
**Current Data:** Risk breakdown components (7-factor model)
**Transformation:**
- Extract risk components from risk_breakdown
- Format as professional summary table
- Gemini: Generate narrative explaining each indicator

**Feasible?** ✅ YES - Full data available

---

### Table 3-12: Risk Score Breakdown ✅
**Current Data:** risk_score, risk_breakdown with components and weights
**Transformation:**
- Create weighted scoring table
- Display component scores, weights, and weighted results
- Visualize with bar chart

**Feasible?** ✅ YES - Full data available

---

### Table 3-13: What-If Scenario Analysis ✅
**Current Data:** Risk score, commodity data
**Transformation:**
- Gemini: Generate scenario analysis
  - "What if origin is legitimate?"
  - "What if goods transited only?"
  - "What if pricing is accurate?"
- Assess impact on risk score for each scenario

**Feasible?** ✅ YES - Gemini can generate dynamically

---

### Table 3-14: Data Sources and Uses ✅
**Current Data:** API metadata
**Transformation:**
- Document all data sources used in analysis
- Gemini: Generate description of methodology for each data source

**Feasible?** ✅ YES - Gemini can generate

---

## Design Architecture

### Backend Changes Required

```
1. GEMINI ANALYSIS SERVICE
   ├─ Input: Raw referral data from API
   ├─ Process: Call Gemini for section-by-section analysis
   │  ├─ Prompt: Template for analyzing each section
   │  ├─ Context: Commodity data, risk factors, enforcement history
   │  └─ Output: Structured JSON with narratives, risk factors, confidence
   └─ Output: Enriched referral data with AI analysis

2. DATA TRANSFORMATION PIPELINE
   ├─ Extract API data into section-specific structures
   ├─ Apply Gemini analysis
   ├─ Calculate confidence scores
   ├─ Generate enforcement recommendations
   └─ Format for professional display

3. API ENDPOINT (New)
   POST /api/referrals/{shipment_id}/analyze
   └─ Returns referral + Gemini analysis
```

### Frontend Changes Required

```
1. ProfessionalReferralDisplay v2
   ├─ Section 3-1 through 3-14 with professional tables
   ├─ Gemini-generated narratives below each table
   ├─ Risk factor callouts (HIGH/MEDIUM/LOW indicators)
   ├─ Visual charts (risk breakdown, scoring model)
   └─ Confidence score display

2. Officer Analysis Form
   └─ Already designed - no changes needed
```

---

## Feasibility Summary

| Section | Data Status | Gemini Need | Feasibility |
|---------|------------|-------------|------------|
| 3-1: Shipment ID | ✅ Available | ✅ Optional | ✅ **FULL** |
| 3-2: Line Items | ✅ Available | ✅ Optional | ✅ **FULL** |
| 3-3: Routing | ✅ Available | ✅ Optional | ✅ **FULL** |
| 3-4: Parties | ✅ Available | ✅ Optional | ✅ **FULL** |
| 3-5: Entity Chain | ⚠️ Limited | ✅ Required | ⚠️ **PARTIAL** |
| 3-6: Import History | ❌ Missing | ✅ Can Generate | ⚠️ **PARTIAL** |
| 3-7: Trade Flow | ⚠️ Limited | ✅ Required | ⚠️ **PARTIAL** |
| 3-8: Doc Review | ❌ Missing | ✅ Can Generate | ⚠️ **PARTIAL** |
| 3-9: Doc Consistency | ❌ Missing | ✅ Can Generate | ⚠️ **PARTIAL** |
| 3-10: Supplier Verify | ⚠️ Limited | ✅ Required | ⚠️ **PARTIAL** |
| 3-11: Risk Summary | ✅ Available | ✅ Optional | ✅ **FULL** |
| 3-12: Risk Breakdown | ✅ Available | ❌ Not needed | ✅ **FULL** |
| 3-13: What-If Analysis | ✅ Available | ✅ Required | ✅ **FULL** |
| 3-14: Data Sources | ✅ Available | ✅ Required | ✅ **FULL** |

**Overall Assessment:** ✅ **FEASIBLE**
- 7 sections with full data available
- 7 sections with partial data but Gemini can provide analysis
- All sections can display professional format and risk narratives

---

## Implementation Roadmap

### Phase 1: Gemini Integration (1.5 hours)
```
1. Create ReferralAnalysisService
2. Define Gemini prompts for each section type
3. Implement caching to avoid redundant API calls
4. Test with sample referral data
```

### Phase 2: Professional Display v2 (1.5 hours)
```
1. Create ProfessionalReferralDisplay v2 component
2. Implement professional table layouts for all 14 sections
3. Add risk factor narratives from Gemini
4. Add visual charts and visualizations
5. Implement confidence score display
```

### Phase 3: Polish & Testing (1 hour)
```
1. Match styling to Evidence tab exactly
2. Test all sections with real data
3. Verify Gemini outputs are professional quality
4. Performance optimization
```

**Total Estimated Time:** 4 hours

---

## Next Steps

1. ✅ Design complete - this document
2. ⏳ **Approval needed:** Does this approach match your vision?
3. 🔧 Implementation: Create Gemini integration + Professional display v2
4. 🧪 Testing: Validate all 14 sections render professionally
5. 🚀 Deployment: Update container and test end-to-end

---

## Questions to Answer Before Implementation

1. **Gemini Integration:** Should we use the existing Gemini API key configured in .env.local?
2. **Caching:** Cache Gemini analyses per referral_id to avoid repeated API calls?
3. **Priority Sections:** Should we focus on sections with full data first (3-1, 3-2, 3-3, 3-4, 3-11, 3-12, 3-13, 3-14)?
4. **Missing Data:** For sections missing data (3-5 through 3-10), should Gemini generate risk assessment frameworks?
5. **Confidence Scoring:** Calculate per-section confidence based on data availability?

