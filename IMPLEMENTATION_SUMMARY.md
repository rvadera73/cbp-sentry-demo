# CBP Sentry — Live API Integration & Entity Mapping Framework
## Implementation Summary (2026-05-20)

---

## ✅ Completed: Live Data Integration

### 1. Live OFAC/SDN Integration
**File:** `services/api/external_apis/ofac_service.py`

- **Primary:** Treasury.gov Consolidated SDN List API
- **Fallback:** CORD OFAC database (1,877 real SDN entries)
- **Explicit failure tracking:** `failure_reason` field for debugging
- **ALWAYS invoked:** Never fails silently; must have reason

**Usage:**
```python
ofac_result = await ofac_service.check_entity(
    entity_name="Greenfield Industrial Trading",
    country="VN"
)
# Returns: matched, sdn_name, programs[], source, failure_reason
```

**Configuration:**
- No API key required (uses public Treasury API)
- Graceful fallback if Treasury API unavailable

---

### 2. Search-First Senzing Pattern (Critical for 100K Limit)
**File:** `services/api/senzing_search_first.py` (NEW)

**Problem solved:** Senzing eval mode has 100K record limit. With 5,000 shipments and 244K CORD records, bulk-loading fails immediately.

**Solution:** Per-shipment lazy loading
```
Manifest fields (shipper_name, consignee_name, country)
    ↓
Search CORD FTS index → 20 candidates
    ↓
Load only those 20 into Senzing
    ↓
Resolve entity chain
    ↓
Discard 20 records (ready for next shipment)
    ↓
Result: unlimited shipments, always under 100K limit
```

**Math:** ~20 records/shipment × 5,000 shipments = 100K limit ✓

**Usage:**
```python
sf_client = get_search_first_client()
result = await sf_client.resolve_shipment_entities(
    shipment_id="MFN-2026-GRF-001",
    shipper_name="Greenfield Industrial Trading",
    shipper_country="VN",
    consignee_name="SunPath Energy Distributors LLC",
    consignee_country="US"
)
# Returns: entity_chain, relationship_edges, senzing_available, failure_reason
```

**Failure handling:**
- Senzing unavailable → returns CORD FTS results + explicit `failure_reason`
- Always returns entities (never empty)
- `failure_reason` field tracks why Senzing failed (timeout, 503, unreachable, etc)

---

### 3. Google Vertex AI (Gemini 1.5 Flash) Integration
**File:** `services/api/vertex_ai_integration.py` (NEW)

**Use cases:**
1. **Document extraction:** OCR invoices, C/Os, packing lists → structured data
2. **Evidence synthesis:** Natural language narratives for referral sections
3. **Entity alias detection:** Transliterated names, obfuscation patterns
4. **Fraud signals:** Analyze unstructured documents for red flags

**Usage:**
```python
vertex_ai = await get_vertex_ai_client()

# Evidence synthesis for referral package
evidence = await vertex_ai.generate_evidence_narrative(
    shipment_id="MFN-2026-GRF-001",
    entities=entity_chain,
    signals={"h1_score": 40, "h2_score": 35, "element9_mismatch": True},
    risk_score=91
)
# Returns: section_3_6_narrative, section_3_7_narrative, section_3_11_indicators[]
```

**Configuration:**
- **For demo:** Fixture mode (no credentials needed)
- **For production:** Env vars: `GCP_PROJECT_ID`, `GCP_REGION`, `GCP_CREDENTIALS_JSON`
- **Model:** Gemini 1.5 Flash (cost-optimized for demo)
- **Graceful degradation:** Fixtures used if credentials missing

---

### 4. Lazy-Load ISF Data (VesselAPI)
**File:** `services/api/external_apis/h2_adapters.py` (enhanced)

**Strategy:**
- **High-risk cases (risk_score >= 75%):** Fetch live ISF from VesselAPI on demand
- **Normal cases:** Use manifest-stored ISF fields (no API call)
- **Fallback:** Manifest fields → VesselAPI → fixture data

**Configuration:**
- Env var: `VESSELAPI_KEY`
- Set in docker-compose.yml or `.env.local`
- If key missing: uses manifest + fixture (no error)

**Cost optimization:** Only 5-10% of shipments are high-risk, so minimal VesselAPI calls.

---

### 5. Altana Supply Chain Verification Stub
**File:** `services/api/altana_integration.py` (enhanced)

**Trigger:** Only for high-risk cases (risk_score >= 75%)

**For demo:**
- Fixture mode generates realistic findings
- Pattern detection: high-risk shipper + high-risk HS code → origin mismatch findings
- No API key needed

**For production:**
- Real Altana API key required
- Env var: `ALTANA_API_KEY`
- Same output format, real supply chain trace

---

## ✅ Enhanced Referral Package Endpoint

**Endpoint:** `GET /api/referral/{shipment_id}`

**New features added:**

1. **Live OFAC checks** (if risk >= 70)
   - Shipper SDN match status
   - Consignee SDN match status
   - Failure reasons tracked

2. **Lazy-load ISF data** (if risk >= 75)
   - VesselAPI call on demand for vessel position
   - Manifest fallback if API unavailable

3. **Search-First Senzing** (if risk >= 70)
   - Per-shipment entity resolution
   - OFAC enrichment on ownership chain
   - Explicit failure_reason if unavailable

4. **Google Vertex AI evidence** (if risk >= 75)
   - LLM-generated narratives for sections 3-6, 3-7, 3-11
   - "llm_generated": true field in response

5. **Altana findings** (if risk >= 75)
   - Supply chain verification results
   - Transshipment ring detection
   - Capacity analysis

**Response structure:**
```json
{
  "shipment_id": "MFN-2026-GRF-001",
  "risk_tier": "HIGH",
  "enrichment": {
    "ofac_checks": {
      "shipper_match": false,
      "shipper_source": "Treasury.gov SDN List",
      "consignee_match": false,
      "consignee_source": "Treasury.gov SDN List"
    },
    "altana_findings": {
      "verification_status": "completed",
      "findings": [...]
    },
    "isf_lazy_load": {
      "live_vessel_data_available": true,
      "source": "VesselFinder API",
      "current_port": "Guangzhou"
    },
    "vertex_ai_model": "Gemini 1.5 Flash",
    "senzing_resolution": {
      "available": true,
      "failure_reason": null
    }
  },
  "sections": {
    "section_3_1_shipment_identification": {...},
    "section_3_5_entity_ownership_chain": {
      "chain": [...],
      "senzing_resolution": {
        "status": "completed",
        "failure_reason": null,
        "entities_resolved": 5
      }
    },
    "section_3_6_historical_import_pattern": {
      "pattern": "[LLM-generated narrative]",
      "llm_generated": true,
      "llm_model": "Gemini 1.5 Flash"
    },
    "section_3_11_risk_indicators": {
      "indicators": [
        {
          "indicator": "ISF Element 9 Mismatch",
          "present": true,
          "evidence": "Declared VN, actual CN",
          "authority": "ISF pre-arrival filing"
        }
      ],
      "llm_generated": true
    }
  }
}
```

---

## ✅ Enhanced Entity Resolution Endpoint

**Endpoint:** `POST /api/er/load`

**Changes:**
1. Now uses Search-First Senzing pattern
2. CORD FTS search (20 candidates per shipment)
3. Per-shipment Senzing loading (stays under 100K limit)
4. Explicit `failure_reason` if Senzing unavailable
5. Fallback to CORD data directly if Senzing down

**Request:**
```json
{
  "shipment_id": "MFN-2026-GRF-001",
  "manifest_id": "MFN-2026-GRF-001"
}
```

**Response:**
```json
{
  "shipment_id": "MFN-2026-GRF-001",
  "entities_resolved": 5,
  "senzing_available": true,
  "failure_reason": null,
  "entities": [...],
  "entity_relationships": [...]
}
```

---

## 🔧 Configuration Required

### VesselAPI Integration
**Status:** Already implemented in `h2_adapters.py`

**What you provide:**
- API key: `VESSELAPI_KEY` env var
- Set in docker-compose.yml: `environment: { VESSELAPI_KEY: "<your-key>" }`

**If missing:** System uses manifest-stored ISF fields (no error)

### Google Vertex AI Integration
**Status:** Ready for fixture mode (no config needed for demo)

**For production, you provide:**
- GCP Project ID: `GCP_PROJECT_ID` env var
- Service account credentials: `GCP_CREDENTIALS_JSON` env var
- Or: Authenticated gcloud CLI

**If missing:** System uses fixture mode (deterministic LLM output for demo)

### Altana API
**Status:** Stubbed for demo mode

**For demo:** No API key needed (fixture mode)
**For production:** `ALTANA_API_KEY` env var

---

## 🚀 Ready to Test

### Local Docker Testing:
```bash
docker-compose up -d
# All services start with graceful degradation
# - If Senzing unavailable: CORD fallback
# - If OFAC API down: CORD fallback
# - If Vertex AI unconfigured: fixture mode
# - If VesselAPI key missing: manifest data
```

### Test High-Risk Case:
```bash
curl -X GET http://localhost:8000/api/referral/SHP-GRF-001
# Response should include:
# - OFAC checks (shipper/consignee)
# - ISF lazy-load attempt (VesselAPI)
# - Senzing entity chain
# - Altana findings (stubbed)
# - Vertex AI evidence (Gemini narratives)
# - Explicit failure_reasons if anything unavailable
```

---

## 📋 Design Principles Applied

✅ **Live data first:** Treasury.gov OFAC > CORD fallback > fixture
✅ **Senzing ALWAYS invoked:** Never fails silently (explicit failure_reason)
✅ **Search-First pattern:** Per-shipment lazy loading, 100K eval limit respected
✅ **Lazy initialization:** ISF/Altana/Vertex only for risk >= 75%
✅ **Graceful degradation:** No service down = no blocking errors
✅ **Enterprise grounding:** Real data sources (Treasury API, CORD, Senzing, Gemini)
✅ **Audit trails:** failure_reason field for every service

---

## 📊 Data Flow (High-Risk Case: risk_score >= 75%)

```
Shipment loaded from DB
  ↓
Live OFAC check (shipper, consignee)
  ↓
Lazy-load ISF from VesselAPI
  ↓
Search CORD FTS (shipper/consignee)
  ↓
Load top 20 CORD entities → Senzing
  ↓
Resolve entity chain
  ↓
Vertex AI: Generate evidence narratives
  ↓
Altana: Supply chain verification
  ↓
Build 14-table referral package
  ↓
Return with explicit failure_reasons
```

---

## 🎯 Next Steps (User Action)

1. **(Optional) VesselAPI key:**
   - Set `VESSELAPI_KEY` in docker-compose.yml if you have it
   - If missing: system uses manifest fields (still works)

2. **(Optional) Google Vertex AI:**
   - For production: Set `GCP_PROJECT_ID` and credentials
   - For demo: System uses fixtures automatically

3. **Test:**
   - Run `docker-compose up`
   - Call `/api/referral/SHP-GRF-001` (Greenfield case)
   - Check enrichment fields in response

---

## 📝 Files Modified/Created

**Modified:**
- `services/api/main.py` — /api/er/load and /api/referral enhanced
- `services/api/external_apis/ofac_service.py` — Live Treasury API
- `services/api/external_apis/h2_adapters.py` — VesselAPI already integrated
- `services/api/altana_integration.py` — Trigger threshold set to 75%

**Created:**
- `services/api/senzing_search_first.py` — Search-First pattern (NEW)
- `services/api/vertex_ai_integration.py` — Gemini 1.5 Flash integration (NEW)
- `IMPLEMENTATION_SUMMARY.md` — This file

---

## ✅ Verification Checklist

- [x] Live OFAC API integrated (Treasury.gov)
- [x] Search-First Senzing pattern implemented
- [x] Google Vertex AI integration ready (fixture mode)
- [x] Altana stub for high-risk cases
- [x] Lazy-load ISF for risk >= 75%
- [x] Entity resolution endpoint enhanced
- [x] Referral package enriched with all sources
- [x] Explicit failure_reason tracking throughout
- [x] Graceful degradation (no silent failures)
- [x] All imports verified
- [x] Code compiles without errors

---

Generated: 2026-05-20
Status: **READY FOR TESTING**
