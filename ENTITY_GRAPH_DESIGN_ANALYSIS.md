# Entity Graph Design Issue Analysis

## Problem Summary

The **Entity tab** in V2InvestigationsPage loads entity data but the **EntityRelationshipGraph component** doesn't render relationships properly because the backend referral service is not including relationship data in the entity chain.

**Current behavior:** "No entity chain data available" or graph renders without relationship arrows
**Expected behavior:** Graph shows 3-level ownership chain with OWNED_BY/PARENT_COMPANY relationship arrows

---

## Architecture Flow (Current vs Expected)

### Current Data Flow (BROKEN)

```
User clicks Entity tab
    ↓
V2InvestigationsPage.EntitiesTab() (line 1083)
    ↓
Fetches selectedReferral from API
    ↓
api.getReferralPackage(shipment_id) → GET /referral/{shipment_id}
    ↓
Backend referral/routes.py → referral/builder.py
    ↓
builder._build_ownership_chain(entities) [Line 206-230]
    ↓
Returns: [
    { level: 1, entity: "Shipper Name", jurisdiction: "VN", relationship: "Root shipper", confidence: 0.98 },
    { level: 2, entity: "Parent HK", jurisdiction: "HK", relationship: "SPV holding", confidence: 0.95 },
    { level: 3, entity: "Manufacturer CN", jurisdiction: "CN", relationship: "Primary mfr", confidence: 0.92 }
]
    ↓
EntitiesTab passes to EntityRelationshipGraph
    ↓
EntityRelationshipGraph component (line 1116)
    ↓
Expects chain: Entity[] with structure:
{
    entity_id: number,
    name: string,
    country: string,
    entity_type: string,          ← MISSING IN CURRENT RESPONSE
    role: string,
    confidence: number,
    relationships?: [              ← MISSING IN CURRENT RESPONSE
        { type: "OWNED_BY", target: "...", confidence: 0.95 }
    ]
}
    ↓
Filter check: validChain.filter(e => e && e.name && e.entity_type)
    ↓
Result: EMPTY because entity_type is missing! 🚫
    ↓
Line 97-101: Renders "No entity chain data available"
```

---

## Root Cause: Missing Fields in Backend Response

### What the Backend Returns (Current)
**File:** `api/services/referral/builder.py` lines 206-230

```python
def _build_ownership_chain(self, entities: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Build Table 3-5: Entity Ownership Chain"""
    chain = []
    
    levels = [
        ("shipper_vn", 1, "Root shipper"),
        ("parent_hk", 2, "SPV holding company" if "parent_hk" in entities else None),
        ("parent_cn", 3, "Primary manufacturer"),
    ]
    
    level = 1
    for entity_key, _, relationship in levels:
        if entity_key in entities:
            entity = entities[entity_key]
            chain.append({
                "level": level,
                "entity": entity.get("entity_name", ""),        # ← WRONG KEY: should be "name"
                "jurisdiction": entity.get("country", ""),      # ← WRONG KEY: should be "country"
                "relationship": relationship,                    # ← WEAK: just a string, not a relationship object
                "confidence": entity.get("match_confidence", 0), 
            })
            level += 1
    
    return chain
```

**Problems:**
1. **Missing `entity_type`** - Graph filter expects this (line 28 in EntityRelationshipGraph.tsx)
2. **Missing `entity_id`** - Graph needs this for SVG node IDs
3. **No relationship array** - Graph expects `.relationships[]` with type/target/confidence
4. **Only partial data** - Doesn't connect to Senzing's 3-level resolution data

### What the Frontend Expects
**File:** `ui/src/v2/components/EntityRelationshipGraph.tsx` lines 4-21

```typescript
interface Entity {
  entity_id: number;                    // ← MISSING
  name: string;                         // ✓ Present (as "entity")
  country: string;                      // ✓ Present (as "jurisdiction")
  entity_type: string;                  // ← MISSING — BLOCKS FILTER
  role: string;
  confidence: number;                   // ✓ Present
  relationships?: Array<{               // ← MISSING
    type: string;       // e.g., "OWNED_BY", "PARENT_COMPANY"
    target: string;     // Target entity name
    confidence: number; // Relationship confidence
  }>;
}
```

**Validation at Line 28:**
```typescript
const validChain = chain.filter(e => e && e.name && e.entity_type);
if (validChain.length === 0) return [];  // ← FAILS because entity_type is missing
```

---

## Data Availability Analysis

### What We Have Available

#### 1. **From CORD Microservice** (`/resolve` endpoint)
When entity resolution runs, the microservice returns:
```json
{
  "level_1": {
    "entity_id": "ENT-GF-VN-001",
    "name": "Greenfield Industrial Trading Co., Ltd.",
    "country": "VN",
    "confidence": 0.98,
    "related_entities": [
      {
        "entity_id": "ENT-GF-HK-001",
        "name": "Greenfield Global Metals Holdings Ltd.",
        "country": "HK",
        "relationship": "OWNED_BY",
        "confidence": 0.95
      }
    ]
  },
  "level_2": { ... },
  "level_3": { ... }
}
```

**Available fields:**
- ✅ `entity_id` (from Senzing)
- ✅ `name` (from Senzing)
- ✅ `country` (from Senzing)
- ✅ `data_source` (GLEIF, OFAC, CBP-SHIPPER, etc.)
- ✅ `related_entities[]` with relationship type & confidence
- ❓ `entity_type` (should be inferred or included)

#### 2. **What ReferralBuilder Receives**
The builder gets `entities` dict with keys like `"shipper_vn"`, `"parent_hk"`, `"parent_cn"` but **doesn't preserve the original Senzing structure**.

---

## Fix Strategy

### Three Complementary Approaches

#### **Approach A: Minimal (Frontend-Only Validation)**
Make the filter accept missing `entity_type` temporarily:
```typescript
// EntityRelationshipGraph.tsx line 28
const validChain = chain.filter(e => e && e.name); // Remove entity_type check
```
**Problem:** Graph won't color-code nodes properly (relies on entity_type)

#### **Approach B: Backend Refactor (RECOMMENDED) ✅**
Modify `builder._build_ownership_chain()` to include full Senzing entity data:
```python
def _build_ownership_chain(self, entities: Dict[str, Any]) -> Dict[str, Any]:
    """Build Table 3-5: Entity Ownership Chain with full relationship data"""
    chain = []
    
    levels = [
        ("shipper_vn", 1),
        ("parent_hk", 2),
        ("parent_cn", 3),
    ]
    
    for entity_key, level in levels:
        if entity_key not in entities:
            continue
            
        entity = entities[entity_key]
        chain_entity = {
            "entity_id": entity.get("senzing_entity_id", 0),
            "name": entity.get("entity_name", ""),
            "country": entity.get("country", ""),
            "entity_type": entity.get("entity_type", "UNKNOWN"),  # ← ADD
            "data_source": entity.get("data_source", "CORD"),     # ← ADD
            "role": self._infer_role(entity_key),                  # ← ADD
            "confidence": entity.get("match_confidence", 0),
            "relationships": entity.get("relationships", [])       # ← ADD (from Senzing)
        }
        chain.append(chain_entity)
    
    return {
        "chain": chain,
        "data_sources": ["CORD", "Senzing", "OFAC"]
    }

def _infer_role(self, entity_key: str) -> str:
    """Map entity key to role for visualization"""
    if "shipper" in entity_key.lower():
        return "Shipper"
    elif "parent" in entity_key.lower() or "holding" in entity_key.lower():
        return "Holding Company"
    elif "mfg" in entity_key.lower() or "mfr" in entity_key.lower():
        return "Manufacturer"
    return "Entity"
```

#### **Approach C: Data Enrichment (BEST LONG-TERM)**
Create a new endpoint that calls CORD microservice directly:
```
GET /referral/{shipment_id}/entity-graph
```
Returns entity chain data directly from Senzing with full relationship traversal.

---

## Implementation Plan

### Step 1: Identify Data Source
Check where `entities` dict comes from in referral route:
```python
# api/services/referral/routes.py
@router.get("/{shipment_id}")
async def get_referral_package(shipment_id: str):
    # Where is entities populated?
    entities = await entity_resolution_service.resolve(...)
    # Does it have entity_type, entity_id, relationships?
```

### Step 2: Trace Senzing Data Through Pipeline
```
CORD Microservice (port 8004)
    ↓ /resolve endpoint returns full entity chain
    ↓
Entity Resolution Service
    ↓ Should cache/preserve Senzing response
    ↓
Referral Builder
    ↓ Currently discards relationship data
    ↓
Frontend
```

### Step 3: Backend Fix
**File to modify:** `api/services/referral/builder.py` lines 206-230

**Changes:**
1. Rename `_build_ownership_chain()` parameter to accept full Senzing response
2. Extract all fields EntityRelationshipGraph needs
3. Preserve `relationships[]` array from Senzing
4. Add `entity_type` inference based on entity data

### Step 4: Update API Response Type
**File:** `ui/src/types/sentry.ts`

Add to ReferralPackage.sections:
```typescript
section_3_5_entity_ownership_chain: {
  chain: Entity[];  // Use proper Entity interface from EntityRelationshipGraph
  data_sources: string[];
  last_updated?: string;
}
```

### Step 5: Frontend Validation
**File:** `ui/src/v2/components/EntityRelationshipGraph.tsx`

Update filter to handle optional fields gracefully:
```typescript
const validChain = chain.filter(e => 
  e && e.name && (e.entity_type || e.role)  // Accept either
);
```

---

## Current Data Flow in Referral Route

To understand where to make changes, check:

1. **Which service populates entities?**
   - `api/services/referral/routes.py` — line where entities dict is created
   - Is it calling CORD microservice or loading from cache?

2. **Does entity_resolution service preserve Senzing output?**
   - `api/services/entity_resolution/service.py`
   - Does it return the full 3-level chain with relationships?

3. **What fields are available at builder time?**
   - Add logging to `_build_ownership_chain()` to inspect incoming data

---

## Validation Checklist

- [ ] **Backend:** `_build_ownership_chain()` includes `entity_id`, `entity_type`, `relationships[]`
- [ ] **Backend:** Response matches Entity interface requirements
- [ ] **Frontend:** EntityRelationshipGraph receives non-empty chain
- [ ] **Frontend:** Graph renders 3 nodes (Shipper → Parent → Manufacturer)
- [ ] **Frontend:** Relationship arrows show OWNED_BY/PARENT_COMPANY labels
- [ ] **Frontend:** Risk coloring works (intermediaries show as amber/orange)
- [ ] **Frontend:** Confidence scores display (% conf badges)

---

## Files to Review & Modify

### Backend
1. `api/services/referral/builder.py` — **PRIMARY FIX**
   - Lines 206-230: `_build_ownership_chain()`
   - Add helper method: `_infer_role()`, `_map_entity_type()`

2. `api/services/referral/routes.py`
   - Verify entities dict has all required fields before builder

3. `api/services/entity_resolution/service.py`
   - Ensure entity response includes relationships from Senzing

### Frontend  
1. `ui/src/v2/components/EntityRelationshipGraph.tsx`
   - Lines 23-66: Update node construction if needed
   - Lines 165-199: Relationship arrow rendering

2. `ui/src/v2/pages/V2InvestigationsPage.tsx` → EntitiesTab
   - Lines 1115-1120: Verify data passing to graph

3. `ui/src/types/sentry.ts`
   - Update ReferralPackage.sections type definition

---

## Next Steps

1. **Read** `api/services/referral/routes.py` to see where entities come from
2. **Trace** entity_resolution_service.resolve() to verify it returns Senzing data
3. **Implement** Approach B (Backend Refactor) in builder.py
4. **Test** with demo entities (Greenfield VN → Greenfield HK → Guangdong Greenfield CN)
5. **Verify** graph renders with relationship arrows

Ready to implement once you confirm the data sources?
