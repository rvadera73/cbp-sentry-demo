# Entity Graph Fix — Data Structure Mismatch

## The Exact Problem (Line-by-Line)

### What the FIXTURE Returns (api/services/referral/routes.py lines 126-148)

```json
{
  "ownership_chain": [
    {
      "level": 1,
      "entity": "Greenfield Industrial Trading Co., Ltd.",
      "jurisdiction": "VN",
      "relationship": "Direct shipper",
      "confidence": 0.95
    },
    {
      "level": 2,
      "entity": "Guangdong Greenfield Aluminum Mfg. Co., Ltd.",
      "jurisdiction": "CN",
      "relationship": "Parent manufacturer",
      "confidence": 0.98
    },
    {
      "level": 3,
      "entity": "Greenfield Global Metals Holdings Ltd.",
      "jurisdiction": "HK",
      "relationship": "Holding company",
      "confidence": 0.92
    }
  ]
}
```

### What the FRONTEND Expects (EntityRelationshipGraph.tsx lines 4-16)

```typescript
interface Entity {
  entity_id: number;              // ❌ MISSING — Graph uses this for SVG node ID
  name: string;                   // ✅ Present (but keyed as "entity")
  country: string;                // ✅ Present (but keyed as "jurisdiction")
  entity_type: string;            // ❌ MISSING — CRITICAL: Filter requires this
  role: string;                   // ⚠️ Present implicitly ("shipper", "mfg", "holding")
  confidence: number;             // ✅ Present
  relationships?: Array<{         // ❌ MISSING — No relationship arrows between nodes
    type: string;                 // e.g., "OWNED_BY", "PARENT_COMPANY"
    target: string;               // Name of entity this one is related to
    confidence: number;            // Relationship confidence
  }>;
}
```

### The Failing Validation (EntityRelationshipGraph.tsx line 28)

```typescript
const validChain = chain.filter(e => e && e.name && e.entity_type);
//                                        ✅ Has "name"  ❌ NO "entity_type"
//
// Result: validChain = [] (EMPTY!)
//
// Line 97-101: Returns "No entity chain data available"
```

---

## Data Structure Comparison

| Field | Current (BROKEN) | Expected (WORKING) | Source |
|-------|------------------|-------------------|--------|
| **entity_id** | ❌ Missing | ✅ Required | `number` from Senzing |
| **name** | ✅ "entity" | ✅ name | Should use "entity" field |
| **country** | ✅ "jurisdiction" | ✅ country | Should use "jurisdiction" field |
| **entity_type** | ❌ Missing | ✅ Required | Inferred from `relationship` or added field |
| **role** | ⚠️ "relationship" text | ✅ role | Should infer role from level/type |
| **confidence** | ✅ "confidence" | ✅ confidence | Already present |
| **relationships[]** | ❌ Missing | ✅ Required | Connect to next node in chain |

---

## Why the Graph Shows "No Entity Chain Data Available"

### Code Flow That Fails

**File:** `ui/src/v2/pages/V2InvestigationsPage.tsx` line 1115-1120

```typescript
{selectedReferral?.sections?.section_3_5_entity_ownership_chain && (
  <EntityRelationshipGraph
    chain={selectedReferral.sections.section_3_5_entity_ownership_chain.chain}
    parties={selectedReferral.sections.section_3_4_parties_and_roles?.parties}
  />
)}
```

**Expected chain structure:** `section_3_5_entity_ownership_chain.chain`
**Actual structure in fixture:** `ownership_chain` (NOT nested in an object with a `.chain` property)

**Issue 1:** The referral fixture has `ownership_chain` directly, not `section_3_5_entity_ownership_chain: { chain: [...] }`

**Issue 2:** Even if it was nested, the structure has:
- `entity` instead of `name`
- `jurisdiction` instead of `country`
- No `entity_id`
- No `entity_type`
- No `relationships[]` array

### Result: Graph component receives undefined or empty chain

```typescript
chain={selectedReferral.sections.section_3_5_entity_ownership_chain.chain}
// → undefined.chain
// → Graph never initializes
// → Shows empty state message
```

---

## What SHOULD Happen in the Graph

### Expected Rendering with Correct Data

```
┌─────────────────────────────────────────────────────────────────┐
│          ENTITY SUPPLY CHAIN TOPOLOGY                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  Shipper (VN)          Parent (HK)          Manufacturer (CN)    │
│  ┌──────────────┐      ┌──────────────┐      ┌──────────────┐   │
│  │ Greenfield   │      │ Greenfield   │      │ Guangdong    │   │
│  │ Industrial   │      │ Global       │      │ Greenfield   │   │
│  │ Trading      │ ──→  │ Metals       │ ──→  │ Aluminum     │   │
│  │              │      │ Holdings     │      │ Mfg.         │   │
│  │ 95% conf     │      │ 92% conf     │      │ 98% conf     │   │
│  └──────────────┘      └──────────────┘      └──────────────┘   │
│                                                                   │
│  Relationship: OWNED_BY    Relationship: PARENT_COMPANY         │
│  (shown as arrow labels)   (shown as arrow labels)              │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

**To render this graph, EntityRelationshipGraph needs:**

1. **Three entity nodes** with proper coloring:
   - Shipper: Blue (#3B82F6)
   - Holding: Amber (#F59E0B) — flagged as risky
   - Manufacturer: Green (#10B981)

2. **Entity types** to determine color:
   ```typescript
   const getEntityColor = (type: string) => {
     if (type.includes('SHIPPER')) return '#3B82F6';
     if (type.includes('HOLDING')) return '#F59E0B';
     if (type.includes('MANUFACTURER')) return '#10B981';
   }
   ```

3. **Relationship arrows** between nodes:
   ```typescript
   {nodes.map((node, idx) => {
     if (idx >= nodes.length - 1) return null;
     const nextNode = nodes[idx + 1];
     const relationships = node.relationships || [];  // ← NEEDS THIS
     return (
       <line x1={...} y1={...} x2={...} y2={...} 
             markerEnd="url(#arrowhead)" />
     );
   })}
   ```

---

## How to Fix This (Three Options)

### **OPTION 1: Frontend Data Mapping (Quick Fix)**

**In EntitiesTab component, transform the data before passing to graph:**

```typescript
// ui/src/v2/pages/V2InvestigationsPage.tsx line 1115-1120

// Map fixture structure to expected Entity[] structure
const transformedChain = selectedReferral?.sections?.ownership_chain?.map(
  (entity, idx) => ({
    entity_id: idx + 1,  // Generate ID from position
    name: entity.entity,  // Rename "entity" to "name"
    country: entity.jurisdiction,  // Rename "jurisdiction" to "country"
    entity_type: inferEntityType(entity.relationship),  // Infer from relationship string
    role: entity.relationship,  // Keep relationship as role for now
    confidence: entity.confidence,
    relationships: idx < (selectedReferral.sections.ownership_chain.length - 1)
      ? [{
          type: 'OWNED_BY',  // Hardcoded for now
          target: selectedReferral.sections.ownership_chain[idx + 1].entity,
          confidence: entity.confidence
        }]
      : []
  })
) || [];

const inferEntityType = (relationship: string) => {
  if (relationship.includes('shipper')) return 'SHIPPER';
  if (relationship.includes('manufacturer')) return 'MANUFACTURER';
  if (relationship.includes('holding')) return 'HOLDING_COMPANY';
  return 'UNKNOWN';
};

// Then pass transformed data:
<EntityRelationshipGraph
  chain={transformedChain}  // ← Transformed data
  parties={...}
/>
```

**Pros:** Quick, no backend changes
**Cons:** Hacky, breaks if fixture changes, hardcoded relationships

---

### **OPTION 2: Backend Fixture Update (Proper Data Structure)**

**In api/services/referral/routes.py, change ownership_chain structure:**

```python
# BEFORE (BROKEN)
"ownership_chain": [
    {
        "level": 1,
        "entity": "Greenfield Industrial Trading Co., Ltd.",
        "jurisdiction": "VN",
        "relationship": "Direct shipper",
        "confidence": 0.95
    },
    ...
]

# AFTER (FIXED)
"section_3_5_entity_ownership_chain": {
    "chain": [
        {
            "entity_id": 1001,
            "name": "Greenfield Industrial Trading Co., Ltd.",
            "country": "VN",
            "entity_type": "SHIPPER",
            "role": "Shipper",
            "data_source": "CORD",
            "confidence": 0.95,
            "relationships": [
                {
                    "type": "OWNED_BY",
                    "target": "Greenfield Global Metals Holdings Ltd.",
                    "confidence": 0.92
                }
            ]
        },
        {
            "entity_id": 1003,  # Out of order to show the chain
            "name": "Greenfield Global Metals Holdings Ltd.",
            "country": "HK",
            "entity_type": "HOLDING_COMPANY",
            "role": "Holding Company",
            "data_source": "CORD",
            "confidence": 0.92,
            "relationships": [
                {
                    "type": "PARENT_COMPANY",
                    "target": "Guangdong Greenfield Aluminum Mfg. Co., Ltd.",
                    "confidence": 0.98
                }
            ]
        },
        {
            "entity_id": 1002,
            "name": "Guangdong Greenfield Aluminum Mfg. Co., Ltd.",
            "country": "CN",
            "entity_type": "MANUFACTURER",
            "role": "Manufacturer",
            "data_source": "CORD",
            "confidence": 0.98,
            "relationships": []
        }
    ],
    "data_sources": ["CORD", "Senzing", "OFAC"],
    "last_updated": "2026-05-25T12:00:00Z"
}
```

**Pros:** Proper structure, frontend code unchanged, correct semantics
**Cons:** Need to change fixture and builder.py

---

### **OPTION 3: Direct CORD Integration (Best Long-Term)**

Create a new endpoint that calls CORD microservice directly:

```python
# api/services/referral/routes.py

@router.get("/{shipment_id}/entity-graph")
async def get_entity_graph(shipment_id: str):
    """Get entity ownership chain directly from CORD microservice"""
    # Call CORD /resolve endpoint
    response = await cord_client.resolve(
        shipper_name=shipment.shipper_name,
        shipper_country=shipment.origin_country,
        consignee_name=shipment.consignee_name,
        consignee_country=shipment.destination_country
    )
    
    # Transform CORD response to Entity[] format
    return {
        "chain": transform_cord_response(response),
        "data_sources": ["CORD", "Senzing"],
        "confidence": response.get("confidence_metrics", {})
    }

def transform_cord_response(cord_response):
    """Transform CORD 3-level resolution to Entity[] format"""
    chain = []
    
    if cord_response.get("level_1"):
        chain.append({
            "entity_id": cord_response["level_1"]["entity_id"],
            "name": cord_response["level_1"]["name"],
            "country": cord_response["level_1"]["country"],
            "entity_type": "SHIPPER",
            "role": "Shipper",
            "confidence": cord_response["level_1"]["confidence"],
            "relationships": [
                {
                    "type": rel["relationship"],
                    "target": rel["name"],
                    "confidence": rel["confidence"]
                }
                for rel in cord_response["level_1"].get("related_entities", [])
            ]
        })
    
    # Similar for level_2, level_3...
    
    return chain
```

**Pros:** Real data from Senzing, relationships from actual entity resolution
**Cons:** Requires CORD integration, more API calls

---

## Recommended Fix Path

**For IMMEDIATE FIX (5 min):**
Use **OPTION 1** (Frontend Mapping) to unblock visualization while backend gets fixed

**For PROPER FIX (30 min):**
Use **OPTION 2** (Backend Fixture) to update the fixture and match frontend expectations

**For LONG-TERM (next sprint):**
Implement **OPTION 3** (CORD Integration) to get real Senzing data with actual relationships

---

## Test Cases

After implementing any fix, test with these scenarios:

### Test 1: Graph Renders with Data
```
1. Navigate to Entity tab with shipment selected
2. Verify 3 nodes appear (not "No entity chain data available")
3. Nodes should show names: Greenfield, Greenfield Global, Guangdong Greenfield
```

### Test 2: Entity Types Display Correctly
```
1. First node (shipper): Blue color
2. Second node (holding): Amber color (risky)
3. Third node (manufacturer): Green color
```

### Test 3: Relationships Render
```
1. Arrow between Shipper → Holding (labeled "OWNED_BY")
2. Arrow between Holding → Manufacturer (labeled "PARENT_COMPANY")
3. Arrows should be solid (not dashed for non-risky relationships)
```

### Test 4: Confidence Badges
```
1. Each node shows "95% conf", "92% conf", "98% conf"
2. Risk flags for holding company (⚠️ HIGH or 🚩 CRITICAL)
```

### Test 5: Risk Analysis Box
```
1. Text under graph identifies holding company as risky
2. Shows reason: "Intermediary/holding entity without manufacturing capacity"
3. Shows if shared directors detected (if relationships include DIRECTOR_SHARED)
```

---

## Files Modified Summary

| File | Change | Line(s) |
|------|--------|---------|
| **api/services/referral/routes.py** | Update fixture ownership_chain structure | 126-148 |
| **api/services/referral/builder.py** | Update `_build_ownership_chain()` | 206-230 |
| **ui/src/v2/pages/V2InvestigationsPage.tsx** | Pass transformed data to graph | 1115-1120 |
| **ui/src/v2/components/EntityRelationshipGraph.tsx** | (No change if data correct) | — |
| **ui/src/types/sentry.ts** | Update ReferralPackage type | — |

