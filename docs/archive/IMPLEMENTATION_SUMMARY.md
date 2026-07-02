# Entity Graph Implementation — Executive Summary

## TL;DR

**The entity graph in Investigation Page doesn't work because:**
1. Backend returns fixture data (hardcoded demo)
2. Fixture has wrong field names and missing required fields
3. Frontend validation fails → shows "No entity chain data available"

**The Fix (Option 3):**
1. Call CORD microservice instead of using fixtures
2. CORD already does 3-level entity resolution with relationships
3. Transform CORD response to match frontend expectations
4. Replace basic SVG graph with interactive React Flow

**Timeline:** 4 weeks (1 week cleanup, 1 integration, 1 visualization, 1 polish)

---

## What's Currently In Place

### ✅ Working Infrastructure
```
CORD Microservice (port 8004)
    ├─ 244K+ CORD entities loaded
    ├─ /resolve endpoint returns 3-level chains
    ├─ Senzing SQLite database ready
    └─ CBP augmentor enriches with shipment data

Entity Resolution Service (api/services/entity_resolution/)
    ├─ Can load manifests to Senzing
    └─ Routes exist but not connected to referral

Investigation Page (V2InvestigationsPage)
    └─ Entity tab exists but shows empty graph
```

### ❌ Missing Pieces
```
Referral Service (api/services/referral/)
    ├─ Uses FIXTURES instead of CORD ← PROBLEM
    ├─ No CORDClient to call microservice
    └─ Wrong data structure for frontend

Frontend Visualization
    ├─ EntityRelationshipGraph is too basic (SVG)
    ├─ GraphPage is list-only (no visualization)
    └─ No interactive features (pan, zoom, search)
```

---

## The Core Issue: Fixture vs Real Data

### Current Behavior (Broken)
```
referral/routes.py:
  "ownership_chain": [
    {
      "entity": "...",           ← Wrong key (should be "name")
      "jurisdiction": "...",     ← Wrong key (should be "country")
      "confidence": 0.95
      // Missing: entity_id, entity_type, relationships[]
    }
  ]

Frontend validation:
  validChain.filter(e => e && e.name && e.entity_type)
  → e.name exists (as "entity")
  → e.entity_type MISSING
  → Result: EMPTY ARRAY
  → Shows "No entity chain data available"
```

### Expected Behavior (Fixed)
```
/referral/{shipment_id}/entity-graph
  "chain": [
    {
      "entity_id": 1001,                           ✅
      "name": "Greenfield Industrial...",         ✅
      "country": "VN",                            ✅
      "entity_type": "SHIPPER",                   ✅
      "role": "Shipper",
      "confidence": 0.95,
      "relationships": [                          ✅
        {"type": "OWNED_BY", "target": "...", "confidence": 0.95}
      ]
    },
    { ... Level 2 ... },
    { ... Level 3 ... }
  ]

Frontend renders:
  ✅ 3 nodes with proper colors
  ✅ Relationship arrows between nodes
  ✅ Risk flags for intermediaries
  ✅ Interactive controls (drag, zoom, pan)
```

---

## Implementation Plan: 4 Weeks

### Week 1: Cleanup & Setup

**Monday-Wednesday: CORD Client**
```python
# Create api/services/referral/cord_client.py
class CORDClient:
    async def resolve_shipment_entities(
        shipper_name, shipper_country,
        consignee_name, consignee_country
    ) -> Dict[str, Any]:
        # Call http://sentry-cord-integration:8004/resolve
        # Return 3-level entity chain with relationships
```

**Thursday-Friday: Data Transformer**
```python
# Create api/services/referral/entity_graph_service.py
class EntityGraphService:
    @staticmethod
    def transform_cord_to_entity_chain(cord_response) -> Dict[str, Any]:
        # Convert CORD format to Entity[] format
        # Handle level_1, level_2, level_3
        # Extract relationships from each level
        # Return { "chain": [...], "data_sources": [...] }
```

**Deliverable:** Both services tested, can call CORD successfully

### Week 2: Integration

**Monday-Wednesday: Backend Endpoint**
```python
# Add to api/services/referral/routes.py
@router.get("/{shipment_id}/entity-graph")
async def get_entity_graph(shipment_id: str):
    shipment = await get_shipment_data(shipment_id)
    cord_response = await cord_client.resolve_shipment_entities(...)
    entity_graph = EntityGraphService.transform_cord_to_entity_chain(cord_response)
    return entity_graph
```

**Thursday-Friday: Frontend Integration**
```typescript
// Update ui/src/services/api.ts
async getEntityGraph(shipmentId: string): Promise<EntityGraph | null>

// Update V2InvestigationsPage.tsx EntitiesTab
const entityGraph = await api.getEntityGraph(shipment_id)
```

**Deliverable:** End-to-end data flow working, frontend receives correct structure

### Week 3: Visualization

**Monday-Tuesday: React Flow Setup**
```bash
npm install reactflow
# Create ui/src/v2/components/InteractiveEntityGraph.tsx
```

**Wednesday-Friday: Implementation & Testing**
```typescript
export function InteractiveEntityGraph({ chain }: { chain: Entity[] }) {
  // Convert chain to ReactFlow nodes with proper coloring
  // Extract relationships as edges
  // Add pan, zoom, minimap, search
  // Test with real CORD data
}
```

**Replace in Investigation Page:**
```typescript
// Before:
<EntityRelationshipGraph chain={...} />

// After:
<InteractiveEntityGraph chain={entityGraph.chain} />
```

**Deliverable:** Interactive, working graph visualization

### Week 4: Polish & Manifest Enrichment

**Monday-Tuesday: Manifest Enhancement**
```python
# Update services/cord-integration/cbp_augmentor.py
def _create_shipper_record(shipment):
    return {
        "entity_id": f"CBP-SHIP-{shipment['id']}",
        "data_source": "CBP-SHIPPER",
        "name_primary": shipment.get("shipper_name"),
        "country": shipment.get("origin_country"),
        "raw_data": {
            "shipment_id": shipment.get("id"),
            "hs_code": shipment.get("hs_code"),
            "isf_element_9": shipment.get("isf_stuffing_country"),
            "declared_coo": shipment.get("declared_coo"),
            "dwell_days": shipment.get("dwell_days"),
            "risk_flags": shipment.get("manifest_anomalies", [])
        }
    }
```

**Wednesday-Friday: Testing & Optimization**
- Test ISF mismatch detection (declared COO ≠ ISF Element 9)
- Verify risk scoring includes manifest signals
- Performance test with large entity chains
- Cache CORD results for 24h

**Deliverable:** Full integration with manifest context + caching

---

## Visualization Options Comparison

| Feature | React Flow | Mermaid | D3.js |
|---------|-----------|---------|-------|
| **Interactive** | ✅ Drag, zoom, pan | ⚠️ Zoom only | ✅ Full control |
| **Setup Time** | Fast (30 min) | Fast (15 min) | Slow (2-3 days) |
| **Dependencies** | 1 lightweight | 0 (built-in) | 1 heavy |
| **Mobile** | ✅ Touch support | ✅ Responsive | ❌ Complex |
| **Complex Networks** | ✅ Excellent | ⚠️ Limited | ✅ Perfect |
| **Learning Curve** | Easy | Very easy | Very steep |
| **Code Maintenance** | Easy | Very easy | Hard |
| **Recommended For** | Investigation page | Simple chains | Advanced analytics |

**Recommendation:** **React Flow** — Perfect balance of interactivity, ease, and extensibility

---

## File Changes Checklist

### Create (140 lines)
- [ ] `api/services/referral/cord_client.py` — CORD HTTP client
- [ ] `api/services/referral/entity_graph_service.py` — CORD transformer
- [ ] `ui/src/v2/components/InteractiveEntityGraph.tsx` — React Flow component

### Modify (200 lines)
- [ ] `api/services/referral/routes.py` — Add `/entity-graph`, deprecate old endpoint
- [ ] `api/services/referral/builder.py` — Add deprecation warnings
- [ ] `services/cord-integration/cbp_augmentor.py` — Enhance manifest enrichment
- [ ] `ui/src/v2/pages/V2InvestigationsPage.tsx` — Call new endpoint, use new component
- [ ] `ui/src/services/api.ts` — Add getEntityGraph() method
- [ ] `ui/src/types/sentry.ts` — Update Entity interface

### Cleanup
- [ ] Archive or move fixture code to `_fixtures.legacy.py`
- [ ] Remove old `_build_ownership_chain()` implementation
- [ ] Update/remove references to deprecated endpoints

---

## Testing & Validation

### Phase 1: CORD Connectivity ✅
```bash
# Verify CORD is running
curl http://localhost:8004/health
# Should return: {"status": "ready", "entity_count": 245000+, "initialized": true}
```

### Phase 2: Data Flow
```
shipment_id → api.getEntityGraph()
  → GET /api/referral/{shipment_id}/entity-graph
    → CORDClient.resolve_shipment_entities()
      → POST http://sentry-cord-integration:8004/resolve
        → Returns 3-level chain
      → EntityGraphService.transform_cord_to_entity_chain()
        → Returns Entity[]
    → Frontend receives entity graph
      → InteractiveEntityGraph renders
```

### Phase 3: Visual Validation
- [ ] 3 nodes render (shipper, holding, manufacturer)
- [ ] Nodes are color-coded (blue, amber, green)
- [ ] Relationship arrows show with labels
- [ ] Confidence badges display
- [ ] Risk flags appear for intermediaries
- [ ] Pan, zoom, drag work on desktop
- [ ] Works on mobile with touch

### Phase 4: Data Accuracy
- [ ] Entity names match CORD output
- [ ] Relationships show correct type (OWNED_BY, PARENT_COMPANY)
- [ ] ISF mismatches detected and flagged
- [ ] Manifest anomalies reflected in risk indicators
- [ ] Confidence scores accurate (95%, 92%, 98%)

---

## Manifest Enrichment Flow

```
Shipment Manifest
  ├─ shipper_name: "Greenfield Industrial..."
  ├─ origin_country: "VN"
  ├─ consignee_name: "SunPath Energy..."
  ├─ destination_country: "US"
  ├─ hs_code: "7604.10.1000"
  ├─ declared_coo: "VN"
  ├─ isf_element_9: "CN"  ← MISMATCH!
  ├─ dwell_days: 11.2
  └─ weight_kg: 22500
         ↓
  CBPAugmentor.augment_shipments()
         ↓
  Creates CBP-SHIPPER record with raw_data context
         ↓
  Senzing indexes record + enriches with GLEIF/OFAC
         ↓
  CORD resolves entities
         ↓
  Detects: Shipper (VN) → Parent Company (HK) → Manufacturer (CN)
           with ISF mismatch flag
         ↓
  Frontend shows: Dashed relationship arrows = risky ownership chain
```

---

## Success Criteria

By end of Week 4:
1. ✅ `/entity-graph` endpoint returns valid Entity[] with all required fields
2. ✅ Graph renders 3 nodes with relationship arrows in Investigation page
3. ✅ Nodes color-coded by entity_type (shipper=blue, intermediary=amber, mfg=green)
4. ✅ Interactive features work (drag, zoom, pan)
5. ✅ ISF mismatches detected and visualized
6. ✅ Manifest anomalies reflected in risk scoring
7. ✅ Performance: graph renders in <500ms
8. ✅ Mobile responsive

---

## Key Decision: Deprecate Fixtures

All fixture data should be **clearly marked as deprecated** and eventually removed:

```python
# In routes.py, routes.py, and builder.py
class ReferralPackageBuilder:
    """
    ⚠️ DEPRECATED: This builder uses static fixture data.
    
    Production implementation uses CORD microservice.
    See ENTITY_GRAPH_OPTION3_STRATEGY.md for migration path.
    
    Fixture mode will be removed in v2.0 (target: Q3 2026)
    """
```

This prevents future confusion and encourages migration to real data.

---

## References

- **ENTITY_GRAPH_DESIGN_ANALYSIS.md** — Problem analysis (data mismatch, missing fields)
- **ENTITY_GRAPH_FIX_REFERENCE.md** — Detailed code examples for each option
- **ENTITY_GRAPH_OPTION3_STRATEGY.md** — Complete implementation roadmap
- **Memory:** [CBP Sentry — Entity Graph Implementation Plan](../../../memory/project_cbp_sentry_entity_graph.md)

---

## Questions?

**Q: Can we run this in parallel with other development?**
A: Yes! Entity graph is isolated to referral service + investigation UI. Other features unaffected.

**Q: What if CORD microservice is down?**
A: Add fallback to fixtures with warning log. Update UI to show degraded state.

**Q: Timeline realistic?**
A: Yes. Weeks 1-3 are straightforward. Week 4 testing can be accelerated if manifest enrichment already partially works.

**Q: Do we need database changes?**
A: No. CORD data already in Senzing SQLite. Optional: add PostgreSQL caching layer for performance.

---

## Next Action

1. **Confirm timeline** — Do we proceed with Week 1 (cleanup + CORD client)?
2. **Confirm visualization** — React Flow, Mermaid, or other?
3. **Confirm manifest enrichment scope** — Include or defer to Week 5?
4. **Start Phase 1** — Create cord_client.py and entity_graph_service.py

Ready to begin implementation? 🚀

