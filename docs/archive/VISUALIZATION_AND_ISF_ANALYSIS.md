# Visualization & ISF Data Analysis

## Alignment with Senzing Documentation & Best Practices

### Senzing Entity Relationship Visualization Standards

Senzing's official documentation recommends **three visualization patterns** for entity relationships:

1. **Entity Relationship Diagram (ERD)** — Graph with nodes and edges
   - Nodes: Entities (shipper, parent, owner)
   - Edges: Relationships (OWNED_BY, PARENT_COMPANY, DIRECTOR_SHARED)
   - Labels: Relationship type + confidence
   - **Use case:** Understanding ownership chains ✅ Our requirement

2. **Senzing Web UI Pattern** — Hierarchical tree layout
   - Top: Source entity (shipper)
   - Middle: Related entities (parents, holding companies)
   - Bottom: Ultimate owner
   - Risk coloring: Green → Amber → Red
   - **Use case:** CBP investigation workflow ✅ Perfect fit

3. **Graph Database (Neo4j)** — Full knowledge graph
   - All entities and relationships
   - Cypher queries for pattern detection
   - Advanced analytics (shortest path, influence, etc.)
   - **Use case:** Research & compliance ⚠️ Overkill for investigation page

### Our Current Implementation Problem

**Current Design.md (lines 215-240):**
```
ENTITY RESOLUTION CHAIN
┌──────────────────┐    ┌──────────────────┐
│ Shipper (L1)     │───▶│ Parent (L2)      │
│ Guangzhou...     │    │ Shanghai Holding │
│ Risk: HIGH       │    │ Risk: MEDIUM     │
└──────────────────┘    └──────────────────┘
         │                      │
         └──────────┬───────────┘
                    ▼
┌──────────────────────────────────────┐
│ Ultimate Owner (Level 3)             │
│ Shenyang Industries Co. Ltd          │
│ Risk: VERIFIED | OFAC: No Match      │
└──────────────────────────────────────┘

INTERACTIVE RELATIONSHIP GRAPH
[This is what's missing]
```

**Problem:** The design spec says "Interactive relationship graph" but:
- ❌ EntityRelationshipGraph is basic SVG (no interactivity)
- ❌ GraphPage is list-only (no visualization)
- ❌ No risk indicators per node
- ❌ No "WHY LINKED" explanation component

### Senzing Best Practice: What We Should Build

**Pattern:** Hierarchical Tree + Interactive Edges

```
                    ┌─────────────────────┐
                    │ Shipper (Level 1)   │
                    │ Greenfield Indust.. │
                    │ Country: VN         │
                    │ Risk: 72 (YELLOW)   │
                    │ Age: 8mo (NEW)      │
                    │ Conf: 95%           │
                    └──────────┬──────────┘
                               │
                        OWNED_BY (0.95)
                               │
                    ┌──────────▼──────────┐
                    │ Parent (Level 2)    │
                    │ Greenfield Global.. │
                    │ Country: HK         │
                    │ Risk: 58 (YELLOW)   │
                    │ Age: 15mo           │
                    │ Conf: 92%           │
                    └──────────┬──────────┘
                               │
                    PARENT_COMPANY (0.93)
                               │
                    ┌──────────▼──────────────────┐
                    │ Manufacturer (Level 3)      │
                    │ Guangdong Greenfield...     │
                    │ Country: CN                 │
                    │ Risk: 85 (RED - CRITICAL)   │
                    │ OFAC: VERIFIED              │
                    │ Conf: 98%                   │
                    └─────────────────────────────┘

WHY LINKED:
→ Greenfield VN owns 75% of Greenfield HK (corporate records)
→ Greenfield HK wholly owns Guangdong Greenfield CN
→ Directors: Li Wei (all three entities), Wang Chen (VN + CN)
→ Risk: Shell company structure with shared directors
```

### React Flow as Senzing-Aligned Solution

**Why React Flow matches Senzing best practices:**

1. **Hierarchical Layout** ✅
   - Automatically arranges levels top-to-bottom
   - Center-aligned (like Senzing examples)

2. **Interactive Edges** ✅
   - Labeled relationship arrows
   - Hover to see confidence/evidence
   - Color-coded by relationship type

3. **Node Risk Indicators** ✅
   - Color (green/yellow/red by risk_score)
   - Border thickness (critical risk)
   - Badge icons (⚠️ OFAC, 🚩 Shell company)

4. **Metadata Display** ✅
   - Node details on hover/click
   - Sidebar with WHY LINKED explanation
   - Data source attribution (CORD, Senzing, OFAC)

5. **Mobile Compatible** ✅
   - Touch controls for pan/zoom
   - Responsive node sizing
   - Readable on investigation officer's phone

6. **Extensible** ✅
   - Easy to add complex networks (>3 nodes)
   - Support for multiple relationship types
   - Custom node templates for different entity types

### Alternative: Mermaid (Simpler, Senzing-Aligned)

If we want simpler implementation:

```typescript
function generateMermaidDiagram(chain: Entity[]): string {
  let diagram = 'graph TD\n';
  
  chain.forEach((entity, idx) => {
    const riskColor = getRiskColor(entity);
    const riskLabel = getRiskLabel(entity.risk_score);
    
    diagram += `
      ${entity.entity_id}["<b>${entity.name}</b><br/>
      ${entity.country}<br/>
      Risk: ${riskLabel}<br/>
      ${entity.confidence * 100}% conf"]:::${riskColor}
    `;
    
    if (idx < chain.length - 1) {
      const rel = entity.relationships?.[0];
      diagram += `${entity.entity_id} -->|${rel?.type}| ${chain[idx + 1].entity_id}\n`;
    }
  });
  
  return diagram;
}
```

**Output:** Senzing-style hierarchical diagram, rendered as SVG via Mermaid

---

## ISF Data Availability & Manifest Enrichment Reality

### Current State: ISF Data IS Available

**What we have:**

✅ **ISFService** (api/services/isf/isf_service.py)
- Element 9 analysis engine
- Dwell time anomaly detection
- Port call history integration

✅ **VesselTrackerClient** (RAG-first pattern)
- Order: 1) Memory cache (24h) → 2) Local archive → 3) VesselFinder API → 4) Fallback fixtures
- Caches VesselFinder API results to archive for future lookups
- No repeated API calls for same vessel

✅ **ISFData Model** (api/services/isf/models.py)
```python
class ISFData(BaseModel):
    manifest_id: str
    shipper_name: str
    shipper_country: str
    consignee_name: str
    consignee_country: str
    manufacturer_name: Optional[str]
    manufacturer_country: Optional[str]
    
    vessel: Optional[VesselInfo]  # ← Full vessel data
    imo: Optional[str]
    vessel_name: Optional[str]
    
    element_9: Element9Data  # ← ISF Element 9 analysis
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

✅ **Demo Manifests** (demo_manifests/*.xlsx)
- manifests_april_2026.xlsx (35K) → April shipments
- manifests_may_2026.xlsx (39K) → May shipments
- manifests_june_2026.xlsx (41K) → June shipments
- test_april_manifest_small.xlsx (6.6K) → Small test file

### The Real Issue: NOT Data Availability — It's Integration

**The problem is NOT missing ISF data.** It's that **the referral service doesn't call the ISF service.**

#### Current Flow (BROKEN)
```
Referral Service (api/services/referral/)
  ├─ Uses FIXTURES (hardcoded demo data)
  ├─ Does NOT call ISFEnrichmentService
  ├─ Does NOT integrate Element 9 analysis
  └─ Does NOT link manifest anomalies to entity chain
```

#### What SHOULD Happen
```
Referral Service (Option 3)
  ├─ Get shipment from database
  │   ├─ shipper_name, origin_country
  │   ├─ consignee_name, destination_country
  │   ├─ vessel_name, imo
  │   └─ declared_origin (COO)
  │
  ├─ Call ISFEnrichmentService.enrich_manifest()
  │   ├─ Fetches Element 9 from VesselFinder (via VesselTrackerClient)
  │   ├─ Analyzes dwell anomalies
  │   ├─ Detects COO mismatches
  │   └─ Returns ISF analysis with risk flags
  │
  ├─ Call CORD /resolve endpoint
  │   ├─ Passes shipper, consignee, manifest context
  │   ├─ Senzing uses context to find ownership chain
  │   └─ Returns 3-level chain with relationships
  │
  ├─ Merge ISF + Entity Resolution
  │   ├─ ISF Element 9 mismatch → Flag on shipper node
  │   ├─ Dwell anomaly → Flag on vessel context
  │   ├─ New shipper → Risk badge on Level 1
  │   └─ OFAC match → Flag on any level
  │
  └─ Return entity_graph with manifest context
     └─ Frontend displays interactive graph
        ├─ 3 nodes colored by risk
        ├─ Relationship arrows with labels
        ├─ WHY LINKED explanation
        ├─ ISF mismatch warnings
        ├─ Dwell anomaly indicators
        └─ OFAC status badges
```

### Why ISF Data Matters for Entity Graphs

**ISF Element 9 reveals the ownership chain:**

| Scenario | ISF Element 9 (Actual Stuffing Country) | Declared COO | What It Tells Us |
|----------|----------------------------------------|--------------|-----------------|
| **Legitimate** | VN | VN | Direct shipment from Vietnam shipper ✅ |
| **Transshipment Red Flag** | CN | VN | Goods actually stuffed in China, declared as Vietnam → Parent company detected |
| **Shell Company** | HK | VN | Stuffing in Hong Kong (holding company jurisdiction) → 3-level chain likely |
| **Multi-Hop Evasion** | TH | VN | Transshipment through Thailand → Complex ownership chain |

**Example:** Greenfield Industrial Trading (VN shipper) declares COO=VN, but:
- ISF Element 9 filed as CN (actual stuffing in Guangzhou)
- This mismatch + shipper_age (8mo) + shared directors → indicates layered ownership
- CORD resolves: Shipper (VN) → Parent (HK) → Manufacturer (CN)
- Graph shows: COO mismatch badge on shipper, dashed lines to parents

---

## What Needs to Change: NOT a Data Problem

### Root Cause: Referral Service Doesn't Integrate Existing Services

**Files already exist and work:**
- ✅ `api/services/isf/` — Complete ISF enrichment + Element 9 analysis
- ✅ `api/services/isf/vessel_tracker.py` — VesselFinder API integration (RAG-first)
- ✅ `services/cord-integration/` — 244K CORD entities, 3-level resolution
- ✅ Demo manifests with actual vessel/ISF data

**What's missing:**
- ❌ Referral service does NOT call ISFEnrichmentService
- ❌ Referral service does NOT call CORD /resolve endpoint
- ❌ No integration between ISF analysis and entity chain

### Implementation Path (Revised)

**Phase 1: ISF Integration** (NEW — insert before CORD integration)
```python
# Update api/services/referral/routes.py

@router.get("/{shipment_id}/enriched-manifest")
async def get_enriched_manifest(shipment_id: str):
    """Get manifest with ISF Element 9 enrichment."""
    shipment = await get_shipment_data(shipment_id)
    
    # Call ISFEnrichmentService
    isf_data = await isf_service.enrich_manifest(
        ISFEnrichmentRequest(
            manifest_id=shipment['manifest_id'],
            shipper_name=shipment['shipper_name'],
            shipper_country=shipment['origin_country'],
            vessel_name=shipment['vessel_name'],
            imo=shipment.get('vessel_imo'),
            declared_origin=shipment['declared_coo'],
        )
    )
    
    return {
        "manifest": shipment,
        "isf_enrichment": isf_data,  # Element 9 analysis + dwell anomalies
        "data_completeness": isf_data.data_completeness_pct,
        "confidence": isf_data.confidence_score
    }
```

**Phase 2: CORD + ISF Integration** (Then call CORD with ISF context)
```python
@router.get("/{shipment_id}/entity-graph")
async def get_entity_graph(shipment_id: str):
    """Get entity graph with ISF context."""
    shipment = await get_shipment_data(shipment_id)
    
    # Step 1: Get ISF enrichment
    isf_data = await isf_service.enrich_manifest(...)
    
    # Step 2: Call CORD with ISF context
    cord_response = await cord_client.resolve_shipment_entities(
        shipper_name=shipment['shipper_name'],
        shipper_country=shipment['origin_country'],
        consignee_name=shipment['consignee_name'],
        consignee_country=shipment['destination_country'],
        context={  # ← Pass ISF data as context
            "element_9_mismatch": isf_data.element_9.is_mismatch,
            "stuffing_country": isf_data.element_9.actual_stuffing_country,
            "dwell_anomaly": isf_data.dwell_anomaly,
            "new_shipper": shipment.get('shipper_age_months', 100) < 24
        }
    )
    
    # Step 3: Transform and enrich entity graph
    entity_graph = EntityGraphService.transform_cord_to_entity_chain(cord_response)
    
    # Step 4: Add ISF warnings to shipper node
    if isf_data.element_9.is_mismatch:
        entity_graph['chain'][0]['warnings'] = [
            {
                "type": "ISF_MISMATCH",
                "message": f"Declared COO: {isf_data.element_9.declared_country} | Actual stuffing: {isf_data.element_9.actual_stuffing_country}",
                "severity": "HIGH"
            }
        ]
    
    return entity_graph
```

---

## Visualization Strategy: React Flow + Senzing Patterns

### Recommended Implementation

**Component:** `ui/src/v2/components/InteractiveEntityGraph.tsx`

Features:
1. **Senzing-aligned hierarchy** — Automatic 3-level layout
2. **Risk-based coloring** — Green/Yellow/Red by entity.risk_score
3. **Interactive edges** — Hover to see relationship confidence + evidence
4. **ISF warnings** — Visual indicators (⚠️) on shipper node
5. **WHY LINKED sidebar** — Shows relationship evidence + manifest context
6. **Mobile-ready** — Touch controls for pan/zoom

### Migration Path

**Phase 1:** Build React Flow component (parallel with ISF integration)
**Phase 2:** Deploy new endpoint + visualization together
**Phase 3:** Keep EntityRelationshipGraph as fallback (no breaking changes)
**Phase 4:** Deprecate EntityRelationshipGraph after 2 weeks in production

---

## ISF Data Flow (Now That We Understand It)

### Complete End-to-End Flow

```
Officer uploads manifest Excel → API ingests
    ↓
Extract: shipper, consignee, vessel, declared_coo
    ↓
ISFEnrichmentService:
    ├─ VesselTrackerClient.get_vessel_info() 
    │   ├─ Check memory cache (24h TTL)
    │   ├─ Check local archive (RAG)
    │   ├─ Call VesselFinder API if miss
    │   └─ Archive API response
    │
    └─ Analyze Element 9
        ├─ Compare declared_coo vs actual_stuffing_country
        ├─ Detect dwell anomalies (>2.5x baseline)
        ├─ Flag ISF mismatches
        └─ Return ISFData with confidence score
    ↓
CORD Entity Resolution:
    ├─ Receive: shipper_name, shipper_country, consignee_name, consignee_country
    ├─ Plus context: element_9_mismatch, stuffing_country, new_shipper
    ├─ Senzing searches CORD database
    ├─ Detects ownership chain: L1 → L2 → L3
    └─ Return: 3-level entities with relationships
    ↓
Entity Graph Service:
    ├─ Transform CORD → Entity[] interface
    ├─ Merge ISF warnings into entity graph
    ├─ Add OFAC status (from OFAC service)
    └─ Return: complete entity_graph
    ↓
Frontend:
    ├─ Call api.getEntityGraph(shipment_id)
    ├─ Render InteractiveEntityGraph (React Flow)
    │   ├─ 3 nodes with risk colors
    │   ├─ Relationship edges with labels
    │   ├─ ISF warning badges
    │   └─ Interactive pan/zoom/drag
    │
    └─ Sidebar shows:
        ├─ Shipper details + age + ISF status
        ├─ WHY LINKED explanation (Senzing evidence)
        ├─ Manifest context (Element 9 mismatch, dwell)
        └─ OFAC status for each entity
```

---

## Summary: ISF Data IS Available

**What was the misconception?**

I initially thought manifest enrichment was a gap because the referral service wasn't integrating ISF data. But the data pipeline is actually complete:

✅ ISFService exists and works
✅ VesselTrackerClient exists (RAG-first with API fallback)
✅ Element 9 analysis engine built
✅ Demo manifests available
✅ ISFData model complete

**The real issue:** Referral service doesn't USE these services. It returns fixtures instead.

**The fix:** Call ISFEnrichmentService + CORD microservice in Option 3, not separate enrichment work.

---

## Recommendation: Proceed with React Flow + Option 3

**Timeline remains 4 weeks:**

| Week | Task | Change |
|------|------|--------|
| 1 | Cleanup + CORD client | Same |
| 2 | `/entity-graph` endpoint + ISF integration | ADD: ISF service call |
| 3 | React Flow visualization | Aligned with Senzing patterns |
| 4 | Polish + testing | No manifest enrichment work (data already available) |

**No need for separate "manifest enrichment" phase.** ISF data flows through the entity graph when we integrate both services.

