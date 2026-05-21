# Sentry Entity Mapping Framework — Architectural Design
**Date:** 2026-05-20  
**Status:** Design Phase (Pre-Implementation)  
**Objective:** Define a multi-source entity resolution system that feeds Senzing with high-confidence data, not raw bulk loads

---

## Problem Statement

**Current approach (static):**
- Load 244K CORD entities once into Senzing → hits 100K eval limit quickly
- No live data → stale shipper registration dates, outdated relationships
- No filtering → Senzing wastes cycles on irrelevant entities

**What we need (dynamic):**
- When a shipment arrives, resolve its entity chain in real-time (~5s latency)
- Only load relevant entities into Senzing (shipper + consignee + likely parents)
- Enrich with live tariff rates, vessel positions, compliance flags
- Confidence-score each relationship so CBP officers know what's high-conviction

---

## Design Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    SHIPMENT INTAKE (ISF Filing)                         │
│                 shipper_name, consignee, HS code, origin                │
└──────────────────────────┬──────────────────────────────────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
        ▼                  ▼                  ▼
    ┌────────────┐   ┌──────────────┐   ┌──────────────┐
    │  FILTER    │   │  ENRICH      │   │   COMPLIANCE │
    │  PIPELINE  │   │  PIPELINE    │   │   CHECK      │
    │            │   │              │   │              │
    │ AI/ML 1:   │   │ Live feeds:  │   │ Real-time:   │
    │ - Entity   │   │ - Tariff API │   │ - OFAC SDN   │
    │   risk     │   │ - AIS        │   │ - Watch list │
    │ - Corridor │   │ - Port auth  │   │ - AD/CVD     │
    │ - Volume   │   │ - ISF        │   │   rates      │
    │   anomaly  │   │ - Company    │   │              │
    │            │   │   registry   │   │              │
    └─────┬──────┘   └──────┬───────┘   └──────┬───────┘
          │                 │                  │
          └─────────────────┼──────────────────┘
                            │
                            ▼
            ┌───────────────────────────────┐
            │  BUILD SENZING SUBSET         │
            │  (≤20 entities, high-signal)  │
            │                               │
            │ • Shipper (from manifest)     │
            │ • Consignee (from manifest)   │
            │ • Top 5 parent matches        │
            │   (OpenCorporates FuzzyMatch) │
            │ • Known freight forwarders    │
            │ • Shared directors           │
            │   (Enterprise registry)       │
            └───────────────┬───────────────┘
                            │
                            ▼
            ┌───────────────────────────────┐
            │  SENZING SDK / REST API       │
            │  (Stateless entity resolution)│
            │                               │
            │ addRecord() ← 20 entities     │
            │ searchByAttributes()          │
            │ → entity chain (5-7 nodes)    │
            │ → relationship types          │
            │ → confidence scores (0-100)   │
            └───────────────┬───────────────┘
                            │
                            ▼
            ┌───────────────────────────────┐
            │  CONFIDENCE FILTERING         │
            │  (Post-Senzing AI/ML 2)       │
            │                               │
            │ Keep if:                      │
            │ • Chain depth ≥ 2             │
            │ • Confidence ≥ 75%            │
            │ • Relationship types linked   │
            │   to prior evasion cases      │
            │                               │
            │ Drop if:                      │
            │ • Confidence < 50%            │
            │ • Disconnected entities       │
            └───────────────┬───────────────┘
                            │
                            ▼
            ┌───────────────────────────────┐
            │  RISK SCORING (H1/H2/H3)      │
            │  Feeds CaseViewerPage         │
            │  (Already implemented)        │
            └───────────────────────────────┘
```

---

## Data Sources (Live Feeds) — From CSOP-BP-GS-26-0001 Proposal

**SOURCE:** Table 1 of the submitted response (April 24, 2026) lists exactly what was promised to CBP.

### Tier 1: Core (Committed in Proposal + CBP-controlled)

| Source | Endpoint | Use Case | Latency | Cost | Notes |
|--------|----------|----------|---------|------|-------|
| **CBP Manifest Feed** | Internal CBP system | Primary shipment identification + trigger | <1s (real-time) | Internal | Encrypted email drop; weekly/daily cycle |
| **ISF 10+2 Element 9** | Altana Atlas API | Container stuffing location (actual origin evidence) | <5s | Altana partnership | **CRITICAL:** ISF filed 14-22 days pre-arrival |
| **OFAC SDN List** | treasury.gov/oac/data | Compliance screening (shippers, consignees, resolved entities) | Daily batch | Free | Treasury; 1,996 U.S. SDN entries |
| **AD/CVD Tariff Orders** | commerce.gov/ACCESS | Active duty/countervailing rates by HTS code | Daily batch | Free | Commerce dataset; linked by HS code + origin |
| **USITC HTS Schedule** | commerce.gov/USITC | Duty rates, tariff classifications, product descriptions | Daily batch | Free | Commodity risk classification |
| **Altana Atlas (ISF + Supply Chain)** | altana-atlas.com/API | Container stuffing verification + supply chain intelligence | <30s | $5-10K/mo | **STRATEGIC:** Pre-arrival intelligence (10-18 days before manifest) |

### Tier 2: Entity Resolution (Committed in Proposal)

| Source | Endpoint | Use Case | Latency | Cost | Notes |
|--------|----------|----------|---------|------|-------|
| **OpenCorporates** | opencorporates.com/API | Shipper aliases, parent companies, officers | <2s | Built into Senzing | 200M+ registered entities globally |
| **Open Ownership** | openownership.org/data | Beneficial ownership links, control structures | <2s | Built into Senzing | Transparency International; 190+ jurisdictions |
| **Panjiva** | panjiva.com/API (or feed) | Historical trade patterns, shipper-consignee history | <5s | Panjiva subscription | 20 years of U.S. trade data; identifies surge patterns |
| **Chamber of Commerce Registries** | Vietnam/Malaysia/China gov APIs | Company incorporation date, registration verification | 24-48h (batch) | $50-200/mo | Shipper age signal; fraud indicator if recently incorporated |

### Tier 3: Vessel & Routing Intelligence (Committed in Proposal)

| Source | Endpoint | Use Case | Latency | Cost | Notes |
|--------|----------|----------|---------|------|-------|
| **AIS Vessel Tracking** | Spire Maritime or MarineTraffic | Port dwell, routing anomalies, vessel history | <5s | $1-2K/mo | Spire preferred (CBP partnership available); MarineTraffic fallback |
| **Bill of Lading Database** | Panjiva or B/L archives | Vessel assignments, port sequences, prior routings | <10s | Panjiva | Detect vessel-based transshipment patterns |
| **CORD JSONL (Reference)** | Local SQLite FTS5 index | 244K entity reference corpus for fuzzy matching | <100ms | Internal | Offline baseline; **not** primary lookup |

### Tier 4: Advanced (Phase 2, not Phase 1)

| Source | Endpoint | Use Case | Latency | Cost | Notes |
|--------|----------|----------|---------|------|-------|
| **OpenSanctions** | opensanctions.org | Non-U.S. sanctions (EU, UN, Swiss, etc.) | Daily batch | Free | Secondary sanctions check after OFAC |
| **Satellite Imagery** | Maxar, Planet Labs | Factory verification, container tracking | 24-48h | $10K+/mo | Phase 2+; not in base commitment |

---

## AI/ML Filtering Framework

### Filter 1: Pre-Senzing (Reduce 244K → ~50 candidates)

**Input:** Manifest shipment fields (shipper_name, consignee, HS code, origin)

**ML Model:** LightGBM + XGBoost trained on prior evasion cases

**Features:**
```
1. Shipper characteristics:
   - Entity age (months since incorporation)
   - New shipper flag (< 6 months)
   - Prior CBP filings (count, dates, outcomes)
   - Consistency of business address
   
2. Corridor signals:
   - Origin-destination pair in known high-risk list (VN→US, MY→US, CN→TH→US)
   - AD/CVD active on HS code
   - Duty rate > 25%
   
3. Volume/Pricing anomalies:
   - Declared value vs market baseline (< 70% = suspicious)
   - Weight-to-value ratio (outlier detection)
   - Frequency surge (3× normal volume from shipper)
   
4. ISF/Vessel signals:
   - ISF Element 9 mismatch (declared ≠ actual stuffing)
   - Port dwell > 5 days (baseline ~2 days)
   - Vessel routing unusual (Beijing → Singapore → Vietnam → US instead of direct)
   - AIS gaps (transponder off for suspicious periods)
```

**Output:** Risk score (0-100) → if ≥ 40, include in Senzing candidate pool

**Expected reduction:** 244K CORD entities → ~50-100 relevant candidates

---

### Filter 2: Post-Senzing (Keep high-confidence chains only)

**Input:** Senzing entity resolution output

**Senzing output shape:**
```json
{
  "entity_id": 12345,
  "entity_name": "Guangdong Greenfield Aluminum Co.",
  "match_key": "+NAME+DIRECTOR",
  "confidence": 0.87,
  "relationships": [
    {
      "related_entity_id": 12346,
      "related_name": "Greenfield Global Holdings (Hong Kong)",
      "relationship_type": "OWNS",
      "evidence": ["Shared director WANG Lei", "Same address block"]
    }
  ]
}
```

**Filtering rules:**
```
Keep chain if:
  ✓ Entity confidence ≥ 75%
  ✓ Relationship confidence ≥ 60%
  ✓ Relationship type in high-evasion patterns:
      - OWNS (equity control)
      - SHARED_DIRECTOR (control signal)
      - FREIGHT_FORWARDER (direct access to falsify docs)
  ✓ Chain depth ≥ 2 (shipper + 1 parent minimum)
  
Drop entity if:
  ✗ Confidence < 50% (noise)
  ✗ Only shallow matches (name only, no structural link)
  ✗ Relationship type = SUPPLIER (too many false positives)
```

**Post-filter output:** 5-7 node entity chain with confidence scores + relationship types

---

## Integration Points

### With Existing Code

**Already implemented:**
- H1/H2/H3 scoring (uses manifest + CORD lookups)
- OFAC service (reads CORD OFAC subset)
- Referral package builder (14 tables)

**Needs update:**
- **H1 scorer:** Replace corridor lookup with live AD/CVD API
- **H2 scorer:** Replace fixture AIS data with VesselFinder API
- **Senzing client:** Add Search-First pattern (filter → load subset → resolve)
- **Database schema:** Add fields for live data (tariff rate, dwell days, confidence scores)

### Senzing Configuration

**Current state:** Senzing container running, REST API at port 8250

**Proposed pattern:**
```python
# Pseudo-code: entity resolution flow

async def resolve_entity_chain(shipment):
    # 1. Pre-filter: which entities matter?
    candidates = ml_filter_pre_senzing(shipment)  # 244K → 50
    
    # 2. Load candidates into Senzing (stateless, fresh each query)
    senzing = SenzingClient()
    for candidate in candidates:
        senzing.addRecord(candidate["DATA_SOURCE"], candidate["RECORD_ID"], candidate)
    
    # 3. Resolve entity chain
    entity_chain = senzing.searchByAttributes({
        "NAME_FULL": shipment["shipper_name"],
        "COUNTRY_CODE": shipment["shipper_country"]
    })
    
    # 4. Post-filter: confidence >= threshold?
    high_confidence_chain = ml_filter_post_senzing(entity_chain)
    
    # 5. Store in DB for referral package
    return high_confidence_chain
```

**Key benefit:** Each shipment loads ~20 entities into Senzing, not 244K globally. Avoids eval limit entirely.

---

## Cost & Resource Model

| Component | Annual Cost | Notes |
|-----------|------------|-------|
| **VesselFinder API** | $1,500 | ~100K vessel lookups/year |
| **OpenCorporates API** | $500 | Shipper parent resolution |
| **Trade.gov API** | $0 | Free; rate-limited |
| **Senzing SDK** | $15,000 | Entity resolution engine; enterprise license |
| **Infra (Cloud Run)** | $2,000 | API services, CORD index caching |
| **Total Year 1** | ~$19,000 | Excludes labor |

---

## Design Decisions & Trade-offs

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Senzing frequency** | Per-shipment (not batch) | Real-time detection vs overnight processing |
| **Dataset for Senzing** | Filter to ~20 candidates | Eval limit + latency (5s vs 30s for full load) |
| **OFAC source** | Treasury daily export (CORD) | Free + no API rate limits vs paid OFAC API |
| **Live vs cached** | Mixture: AIS/Tariff live, company registry cached | AIS/tariff change hourly; company data stable |
| **Confidence threshold** | ≥75% post-resolution | CBP officers' comfort with "high-conviction" evidence |

---

## Open Questions

**1. Should we batch-load CORD entities at startup, or query on-demand?**
- Current: FTS5 index (~375MB) built once, queried per-shipment
- Alternative: Query CORD API (if it exists) or cloud index
- **Recommendation:** Keep FTS5 index (fast, no external dependency)

**2. How much does Senzing eval license cost vs enterprise?**
- Eval: ~$5-10K/year, 100K records
- Enterprise: ~$50K+/year, unlimited
- **Recommendation:** Phase 1 use eval license (free tier exists). Move to enterprise if 1000+ shipments/day

**3. Should we include Altana Atlas for supply chain intelligence?**
- Altana knows "normal" supply chains; flags unusual routing
- Cost: $5-10K/month
- **Recommendation:** Phase 2 (not Phase 1). Proof-of-concept with free sources first

**4. How do we handle non-English shipper names?**
- CORD JSONL has transliterated names (绿田 = Lü Tian = Greenfield)
- Senzing handles phonetic matching natively
- **Recommendation:** Ensure CORD JSONL is fully loaded (it is: 244K entities)

---

---

## AI/LLM Integration (Context Extraction + Evidence Synthesis)

### Where LLM Fits

**Problem:** Manifest documents (invoices, C/Os, packing lists, purchase orders) are **unstructured text**. Traditional regex/rules-based extraction misses context, aliases, and transshipment signals hidden in free-form fields.

**Solution:** LLM as context layer (not core scorer):

```
Raw manifests (Excel, PDF, scanned docs)
    ↓
LLM: Extract + Normalize (Claude 3.5 or GPT-4)
    ↓ 
Structured extraction:
  - Shipper name (detect aliases: "YYY Corp" vs "YYY Ltd" vs "益益有限公司")
  - Manufacturing location (OCR handwritten notes)
  - Declared vs. actual origin (from invoice footnotes)
  - Unusual phrasing (red flags: "transited through", "transit only")
    ↓
Feed to H1/H2/H3 scorers
```

### Specific LLM Use Cases

| Use Case | Input | LLM Task | Output | Cost |
|----------|-------|----------|--------|------|
| **Document OCR + Extraction** | Scanned invoices, packing lists, COOs | Extract structured fields + free-text anomalies | JSON: {shipper, origin_stated, origin_evidence, confidence} | $0.01-0.05/doc (Claude API) |
| **Entity Name Normalization** | Raw shipper names from manifest | Detect aliases, transliterations, shell companies | Canonical name + alias variants | $0.005/query |
| **Evidence Synthesis** | Senzing entity chain + manifest docs | Summarize "why this entity chain matters" in CBP language | Plain-English risk narrative (for referral package) | $0.01-0.02/narrative |
| **Fraud Pattern Detection** | Document text (invoices, emails) | Find suspicious phrasing: delays, missing details, generic templates | Pattern flagging + confidence | $0.01/doc |

### LLM Guard Rails

**What LLM does NOT do (stays with symbolic AI):**
- Make final enforcement decisions (CBP officer decides)
- Replace tariff lookups (use APIs; LLM hallucination risk too high)
- Resolve entity relationships (Senzing does this; ground truth)

**LLM only used for:**
- Unstructured → structured conversion
- Free-text anomaly flags (narrative, not scoring)
- Referral package prose (summary, not evidence)

**Cost Model:**
- Base: 10,000 shipments/month × $0.02/doc = $200/mo
- Peak: 50,000/month = $1,000/mo
- API: Claude Haiku ($0.50/$1.50 per million tokens) for cost efficiency

---

## Grounding Principles (Making This Real, Not Smoke)

### 1. **Data Actually Exists**
- ✓ OFAC SDN: Real 1,996-entity list, updated daily by Treasury (treasury.gov/oac)
- ✓ ISF Element 9: Real CBP filing requirement (19 CFR 149); Altana integrates it
- ✓ AD/CVD: Real Commerce Department orders (search.trade.gov); 400+ active orders
- ✓ AIS: Real vessel tracking from Spire/MarineTraffic; 10,000+ vessels tracked globally
- ✓ Panjiva: Real trade database (100M+ shipments); used by Customs brokers
- ✓ OpenCorporates: Real company registry data (200M+ entities)
- ✗ **NOT assumed:** No synthetic data, no "we'll collect it later," no proprietary sources

### 2. **Latency is Realistic**
- Real-time (<5s): AIS, API lookups, LLM extraction
- Near-real-time (<30s): Altana supply chain context, Senzing entity resolution
- Batch (24-48h): Daily tariff updates, OFAC list refreshes, Chamber registry checks
- **Principle:** If CBP needs a decision within 72 hours pre-arrival, all data must be ≤30 minutes stale

### 3. **Costs Are Honest**
| Component | Annual Cost | Notes |
|-----------|-----------|-------|
| Altana Atlas | $60,000-120,000 | Strategic; pre-arrival intelligence |
| AIS (Spire/MarineTraffic) | $12,000-24,000 | ~1,000 vessels/month lookup |
| Senzing (enterprise license) | $50,000-100,000 | Entity resolution at CBP scale |
| LLM (Claude/GPT-4) | $2,400-12,000 | 10K-50K manifests/month |
| Panjiva trade data | $10,000-20,000 | Historical pattern lookups |
| Infrastructure (Cloud Run) | $5,000 | CORD index caching + API services |
| **TOTAL YEAR 1** | ~$150K-300K | Not free; reflects enterprise-grade system |

### 4. **Senzing is Used Correctly (Search-First)**
- **NOT:** Load all 244K CORD entities globally into Senzing (wastes $50K license)
- **YES:** Per-shipment, load ~20 high-signal candidates, resolve, discard after response
- **Benefit:** Stays under 100K eval limit; $50K/year not $500K+

### 5. **No Hybrid Mode Cheating**
- All data sources must be **real API calls or live feeds**, not "fixture fallback mode"
- If Altana API is down, Sentry waits (doesn't use 2-year-old CORD data as "it's close enough")
- If AIS is unavailable, ISF Element 9 carries the signal alone (don't invent dwell data)
- **Principle:** CBP makes decisions based on what was **actually queried**, logged with timestamp

### 6. **Audit Trail is Built-In**
Every referral package records:
- Which data sources queried (+ timestamp)
- Confidence scores per source
- How LLM interpreted unstructured docs
- Which Senzing relationships matched
- Which ML filters triggered

**Requirement for CBP:**  Officer must see "97% confident shipper owns manufacturer" with evidence (Senzing match + director name + registration dates), not just "HIGH RISK."

### 7. **Fail Safes Are Explicit**
If any **Tier 1 data source** fails:
- **Altana (ISF Element 9):** Fall back to manifest origin declaration + port metadata
- **OFAC:** Fall back to local CORD SDN check (stale but complete)
- **AIS:** Fall back to manifest route + port call estimates
- **Senzing:** If no match at ≥60% confidence, return flat entity list (no chain)

If **multiple sources fail**, referral is generated but flagged "INCOMPLETE DATA" and officer must manually verify before enforcement action.

---

## Design Validation Checklist

Before implementation, confirm:

- [ ] **Altana Atlas API access confirmed?** (ISF Element 9 is core; without it, half the signal is gone)
- [ ] **Senzing enterprise license budget approved?** (Can't work without it; free tier won't scale)
- [ ] **Cloud infrastructure ready?** (FIPS 140-2/FedRAMP; CORD index persistence)
- [ ] **LLM choice settled?** (Claude Haiku for cost, GPT-4 for capability? Commit.)
- [ ] **Panjiva data feed configured?** (Trade pattern lookups; must be real-time or end-of-day batch)
- [ ] **AIS provider contract signed?** (Spire Maritime or MarineTraffic; lead time 2-4 weeks)
- [ ] **CBP data governance confirmed?** (Manifest feed cadence, ISF ingest schedule, data quality SLA)

---

## Next Steps

**If this design is approved:**

1. **Spike:** Build Filter 1 (LightGBM pre-Senzing) with synthetic data — 2 days
2. **Spike:** Test Senzing Search-First pattern (load 20, resolve, post-filter) — 1 day
3. **Integration:** Wire live APIs (VesselFinder, OpenCorporates, AD/CVD trade.gov) — 3 days
4. **Testing:** End-to-end on 3 demo cases (Greenfield, Solaria, decoy) — 1 day
5. **Deployment:** Cloud Run with persistent CORD index + Senzing container — 2 days

**Total: ~9 days for full enterprise entity mapping system**

---

## Questions for User Validation

- [ ] Are the 5 data sources (OFAC, ISF, AIS, Port Auth, AD/CVD) the right set to start?
- [ ] Should we add or remove any Tier 2/3 sources?
- [ ] Is 75% confidence threshold right for "high-conviction" CBP referrals?
- [ ] Should Senzing be refreshed per-shipment or cached (stale-but-fast)?
- [ ] Any concerns about licensing costs ($19K/year) for Phase 1?
