# Direct Answers to Your Questions

## Question 1: Is Visualization Aligned with Senzing Examples/Documentation?

### Answer: PARTIALLY

**The design spec (DESIGN.md) is aligned with Senzing best practices.** But the implementation is NOT.

### What Senzing Documentation Recommends

Senzing examples show **three standard patterns:**

1. **Hierarchical Tree** (most common for entity chains)
   ```
   Level 1 (Shipper)
      ↓ OWNED_BY
   Level 2 (Parent)
      ↓ PARENT_COMPANY
   Level 3 (Owner)
   ```
   - Vertical or horizontal layout
   - Top-to-bottom (root to leaves)
   - Risk coloring on nodes
   - Relationship labels on edges
   - **THIS IS WHAT WE NEED**

2. **Entity Relationship Diagram (ERD)**
   - Used for complex networks (>5 entities)
   - All relationships visible at once
   - Pattern detection emphasis

3. **Graph Database (Neo4j)**
   - For research/analytics, not operational workflows

### Current CBP Sentry Design Spec Says (DESIGN.md:215-240)

```
ENTITY RESOLUTION CHAIN (hierarchical tree — ✅ CORRECT)
┌──────────────────┐    ┌──────────────────┐
│ Shipper (L1)     │───▶│ Parent (L2)      │
│ Risk: HIGH       │    │ Risk: MEDIUM     │
└──────────────────┘    └──────────────────┘
         │                      │
         └──────────┬───────────┘
                    ▼
         ┌──────────────────────┐
         │ Owner (Level 3)      │
         │ Risk: VERIFIED       │
         └──────────────────────┘

WHY LINKED (Explanation)
[Interactive relationship graph]
```

### Current Implementation (BROKEN)

❌ **EntityRelationshipGraph** — Basic SVG, not Senzing-style
- Manual node positioning (fragile)
- No interactivity
- Limited to 3 nodes
- No risk indicators

❌ **GraphPage** — List-only, no visualization at all

### What We Need to Match Senzing Standards

✅ **React Flow Implementation**
```
Characteristics that match Senzing docs:
✅ Hierarchical auto-layout (top-to-bottom)
✅ Senzing-style coloring (green/yellow/red by risk)
✅ Interactive edges (hover for confidence)
✅ Relationship labels (OWNED_BY, PARENT_COMPANY)
✅ Node metadata (country, age, confidence)
✅ WHY LINKED sidebar (explanation + evidence)
✅ Extensible to complex networks
✅ Mobile responsive
```

### Bottom Line

**Design spec:** ✅ Aligned with Senzing best practices
**Current code:** ❌ Not aligned (too basic, no interactivity)
**React Flow fix:** ✅ Will align with Senzing documentation

---

## Question 2: What Manifest Enrichment Issue Do You See with ISF Dataset?

### Answer: NO ISSUE WITH DATA — Issue is Integration

**There is NO missing manifest data.** All ISF data is available and integrated. The issue is that **the referral service doesn't USE it.**

### What ISF Data Exists (ALL AVAILABLE)

✅ **ISFService** (`api/services/isf/isf_service.py`)
- Element 9 (Country of Origin Pre-Arrival) analysis
- Dwell time anomaly detection (>2.5x baseline)
- Port call history integration
- Risk scoring per ISF element

✅ **VesselTrackerClient** (RAG-first integration)
- Fetches vessel data from VesselFinder API
- Caches in local archive (SQLite)
- Memory cache (24h TTL)
- Fall-back to fixtures if API unavailable
- **No repeated API calls** — all data is cached

✅ **ISFData Model** (Complete)
```python
class ISFData(BaseModel):
    manifest_id: str
    shipper_name: str
    shipper_country: str
    consignee_name: str
    consignee_country: str
    
    element_9: Element9Data  # ← Full Element 9 analysis
    vessel: Optional[VesselInfo]  # ← Full vessel info from VesselFinder
    imo: Optional[str]
    vessel_name: Optional[str]
    
    port_of_loading: Optional[str]
    port_of_unlading: Optional[str]
    estimated_arrival: Optional[datetime]
    
    hs_code: Optional[str]
    commodity_description: Optional[str]
    declared_value_usd: Optional[float]
    weight_kg: Optional[float]
    
    data_completeness_pct: float  # 0-100
    confidence_score: float  # 0-1
```

✅ **Demo Manifests** (Ready to use)
- `demo_manifests/manifests_april_2026.xlsx` (35K)
- `demo_manifests/manifests_may_2026.xlsx` (39K)
- `demo_manifests/manifests_june_2026.xlsx` (41K)
- `demo_manifests/test_april_manifest_small.xlsx` (6.6K)

### The Real Problem: Integration Gap

**Referral service doesn't call ISFEnrichmentService:**

```python
# Current (BROKEN)
@router.get("/{manifest_id}")
async def get_referral_package(manifest_id: str):
    return FIXTURES  # ← Returns hardcoded demo data
    # Never calls: ISFEnrichmentService
    # Never calls: VesselTrackerClient
    # Never calls: CORD /resolve endpoint
```

**What should happen:**

```python
# Fixed (Option 3)
@router.get("/{shipment_id}/entity-graph")
async def get_entity_graph(shipment_id: str):
    shipment = await get_shipment_data(shipment_id)
    
    # Step 1: Get ISF enrichment (Element 9 analysis)
    isf_data = await isf_service.enrich_manifest(
        ISFEnrichmentRequest(
            manifest_id=shipment['manifest_id'],
            shipper_name=shipment['shipper_name'],
            vessel_name=shipment['vessel_name'],
            imo=shipment.get('imo'),
            declared_origin=shipment['declared_coo'],
        )
    )
    # → Returns Element 9 mismatch, dwell anomalies, vessel data
    
    # Step 2: Get entity resolution (CORD + Senzing)
    cord_response = await cord_client.resolve_shipment_entities(
        shipper_name=shipment['shipper_name'],
        shipper_country=shipment['origin_country'],
        consignee_name=shipment['consignee_name'],
        consignee_country=shipment['destination_country'],
        # Plus ISF context for better matching
        element_9_mismatch=isf_data.element_9.is_mismatch,
        stuffing_country=isf_data.element_9.actual_stuffing_country,
    )
    # → Returns 3-level ownership chain
    
    # Step 3: Transform to Entity[]
    entity_graph = EntityGraphService.transform_cord_to_entity_chain(cord_response)
    
    # Step 4: Merge ISF warnings into graph
    if isf_data.element_9.is_mismatch:
        entity_graph['chain'][0]['warnings'] = [{
            "type": "ISF_ELEMENT_9_MISMATCH",
            "declared": isf_data.element_9.declared_country,
            "actual": isf_data.element_9.actual_stuffing_country,
            "severity": "HIGH"
        }]
    
    return entity_graph
```

### What ISF Data Reveals in Entity Graphs

**Element 9 is the key to understanding ownership:**

| Scenario | Declared COO | Actual Stuffing (Element 9) | What It Means |
|----------|--------------|---------------------------|--------------|
| **Clean** | VN | VN | Direct shipper in Vietnam ✅ |
| **Red Flag** | VN | CN | Goods packed in China, declared as VN → indicates parent company in different country |
| **Shell Co.** | VN | HK | Stuffing in Hong Kong (holding co. jurisdiction) → 3-level chain |
| **Evasion** | VN | TH | Multi-hop transshipment → complex ownership |

**Example:** Greenfield Industrial (VN shipper) declares COO=VN, but Element 9 filed as CN:
1. Officer sees: ⚠️ ISF_MISMATCH on shipper node
2. CORD resolves: Shipper (VN) → Parent (HK) → Manufacturer (CN)
3. Graph shows: Why the mismatch — shipper is agent, real manufacturer is in CN
4. Risk score increases (layered ownership = higher risk)

### Timeline Change: No Separate Enrichment Phase Needed

**Original plan had 4 phases. NEW plan:**

| Week | Task | Why |
|------|------|-----|
| 1 | Cleanup + CORD client | Same |
| 2 | **ISF integration + /entity-graph endpoint** | CHANGED: ISF service call included |
| 3 | React Flow visualization | Same |
| 4 | Polish + testing | Same — no separate manifest work needed |

**The data is already there.** We just need to wire it up in Phase 2.

---

## Summary

### Q1: Visualization Alignment
- **Design spec:** ✅ Aligned with Senzing best practices (hierarchical tree)
- **Current code:** ❌ Not aligned (too basic)
- **React Flow fix:** ✅ Matches Senzing documentation patterns

### Q2: ISF Data & Manifest Enrichment
- **ISF data:** ✅ All available (ISFService, VesselTrackerClient, demo manifests)
- **Integration:** ❌ Referral service doesn't call ISFEnrichmentService
- **Fix in Phase 2:** Call ISFEnrichmentService + CORD together in `/entity-graph` endpoint

### Bottom Line: You Were Right

Your questions revealed that I was overthinking the "manifest enrichment" issue. **The data pipeline is complete.** We just need to:

1. ✅ Use React Flow for Senzing-aligned visualization
2. ✅ Integrate ISFService + CORD in Phase 2 (no separate enrichment work)

Ready to start Phase 1 (CORD client + deprecation markers)?

