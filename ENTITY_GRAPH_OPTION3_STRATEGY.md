# Entity Graph Implementation — Option 3 (CORD Direct Integration)

## Current State vs Target State

### What's Currently In Place (Partial)

✅ **CORD Microservice** (port 8004)
- Runs `/resolve` endpoint with 3-level entity resolution
- Returns full Senzing entity data with relationships
- Loads 244K+ CORD entities into SQLite

✅ **CBP Augmentor** (services/cord-integration/cbp_augmentor.py)
- Fetches shipments from data service
- Creates CBP-SHIPPER and CBP-ISF records
- Links ISF to shipper in Senzing

✅ **Entity Resolution Service** (api/services/entity_resolution/)
- Has routes for loading entities from manifest
- Can call Senzing

❌ **Referral Integration** (api/services/referral/)
- Uses FIXTURES instead of CORD
- Doesn't call microservice
- No real entity resolution data
- Missing entity_type, entity_id, relationships

❌ **Frontend Graph Visualization**
- EntityRelationshipGraph SVG is minimal
- GraphPage is list-only (no visual graph)
- Both expect but don't receive relationship data

---

## Implementation Strategy: Option 3

### Phase 1: Clean Up Fixtures (Mark Deprecated)

**File:** `api/services/referral/routes.py` (lines 30-400)

```python
# REPLACE THIS:
@router.get("/{manifest_id}", response_model=ReferralPackageResponse)
async def get_referral_package(manifest_id: str) -> ReferralPackageResponse:
    """DEPRECATED: Returns fixture data only. Use /entity-graph endpoint instead."""
    # ... current fixture code ...

# WITH THIS:
@router.get("/{manifest_id}", response_model=ReferralPackageResponse)
async def get_referral_package(manifest_id: str) -> ReferralPackageResponse:
    """
    Get referral package for a shipment.
    
    ⚠️ DEPRECATION WARNING: 
    - This endpoint returns FIXTURE DATA only
    - For real entity graphs, use GET /api/referral/{shipment_id}/entity-graph
    - Will be removed in v2.0
    
    Args:
        manifest_id: Manifest identifier
    """
    logger.warning(f"DEPRECATED: get_referral_package() called. Use /entity-graph instead. Returning FIXTURE DATA.")
    
    # Return fixture data with deprecation warning
    return {
        "package_id": f"ref_{manifest_id}",
        "confidence_level": "FIXTURE_DATA",  # ← Mark clearly
        "warning": "This is FIXTURE DATA. Use /entity-graph endpoint for real data.",
        "sections": {
            # ... current fixture ...
        }
    }
```

**Then add deprecation marker to builder.py:**

```python
class ReferralPackageBuilder:
    """
    ⚠️ DEPRECATED: This builder uses static fixture data.
    
    For production use, implement Option 3:
    - Call CORD microservice at http://sentry-cord-integration:8004
    - Fetch entity resolution directly
    - Populate referral package with real data
    
    See ENTITY_GRAPH_OPTION3_STRATEGY.md
    """
```

---

### Phase 2: Implement Option 3 (CORD Direct Integration)

#### Step 1: Add CORD Client Service

**New file:** `api/services/referral/cord_client.py`

```python
"""CORD microservice client for entity resolution."""
import httpx
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class CORDClient:
    """Client for CORD entity resolution microservice."""
    
    def __init__(self, base_url: str = "http://sentry-cord-integration:8004"):
        self.base_url = base_url
        self.timeout = 30.0
    
    async def resolve_shipment_entities(
        self,
        shipper_name: str,
        shipper_country: str,
        consignee_name: str,
        consignee_country: str,
    ) -> Dict[str, Any]:
        """
        Resolve 3-level entity chain via CORD microservice.
        
        Args:
            shipper_name: Shipper entity name
            shipper_country: Shipper country code (e.g., "VN")
            consignee_name: Consignee entity name
            consignee_country: Consignee country code (e.g., "US")
        
        Returns:
            3-level entity chain with relationships from Senzing
            {
                "level_1": { entity details with relationships },
                "level_2": { ... },
                "level_3": { ... },
                "ofac_detected": bool,
                "risk_score": 0-100,
                "confidence_metrics": { ... }
            }
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/resolve",
                    json={
                        "shipper_name": shipper_name,
                        "shipper_country": shipper_country,
                        "consignee_name": consignee_name,
                        "consignee_country": consignee_country,
                    }
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as e:
            logger.error(f"CORD resolution failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error calling CORD: {e}")
            return None
```

#### Step 2: Create Entity Graph Endpoint

**New file:** `api/services/referral/entity_graph_service.py`

```python
"""Transform CORD resolution into entity graph format."""
from typing import Dict, Any, List, Optional

class EntityGraphService:
    """Transform CORD 3-level resolution to Entity[] format for frontend."""
    
    @staticmethod
    def transform_cord_to_entity_chain(cord_response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform CORD /resolve response into Entity interface format.
        
        Input (from CORD):
        {
            "level_1": {
                "entity_id": "ENT-GF-VN-001",
                "name": "Greenfield Industrial...",
                "country": "VN",
                "confidence": 0.98,
                "related_entities": [
                    {
                        "entity_id": "ENT-GF-HK-001",
                        "name": "Greenfield Global...",
                        "relationship": "OWNED_BY",
                        "confidence": 0.95
                    }
                ]
            }
        }
        
        Output (for frontend):
        {
            "chain": [
                {
                    "entity_id": "ENT-GF-VN-001",
                    "name": "Greenfield Industrial...",
                    "country": "VN",
                    "entity_type": "SHIPPER",
                    "role": "Shipper",
                    "data_source": "CORD",
                    "confidence": 0.98,
                    "relationships": [
                        {
                            "type": "OWNED_BY",
                            "target": "Greenfield Global...",
                            "confidence": 0.95
                        }
                    ]
                },
                ...
            ],
            "data_sources": ["CORD", "Senzing", "OFAC"],
            "ofac_detected": false,
            "risk_score": 72,
            "confidence_metrics": { ... }
        }
        """
        if not cord_response:
            return {"chain": [], "data_sources": []}
        
        chain = []
        entity_type_map = {
            "level_1": "SHIPPER",
            "level_2": "INTERMEDIARY",  # Often a holding company
            "level_3": "MANUFACTURER",
        }
        
        for level_key in ["level_1", "level_2", "level_3"]:
            if level_key not in cord_response or not cord_response[level_key]:
                continue
            
            entity_data = cord_response[level_key]
            relationships = []
            
            # Extract relationships
            for related in entity_data.get("related_entities", []):
                relationships.append({
                    "type": related.get("relationship", "UNKNOWN"),
                    "target": related.get("name", ""),
                    "confidence": related.get("confidence", 0)
                })
            
            chain.append({
                "entity_id": entity_data.get("entity_id", f"ENT-{level_key}"),
                "name": entity_data.get("name", ""),
                "country": entity_data.get("country", ""),
                "entity_type": entity_type_map.get(level_key, "UNKNOWN"),
                "role": EntityGraphService._infer_role(level_key),
                "data_source": entity_data.get("data_source", "CORD"),
                "confidence": entity_data.get("confidence", 0),
                "relationships": relationships
            })
        
        return {
            "chain": chain,
            "data_sources": [
                entity.get("data_source", "CORD")
                for entity in [cord_response.get(f"level_{i}") for i in [1, 2, 3]]
                if entity
            ],
            "ofac_detected": cord_response.get("ofac_detected", False),
            "risk_score": cord_response.get("risk_score", 0),
            "confidence_metrics": cord_response.get("confidence_metrics", {})
        }
    
    @staticmethod
    def _infer_role(level_key: str) -> str:
        """Infer role from level position in ownership chain."""
        roles = {
            "level_1": "Shipper",
            "level_2": "Holding Company",
            "level_3": "Manufacturer"
        }
        return roles.get(level_key, "Entity")
```

#### Step 3: New Endpoint in Referral Routes

**File:** `api/services/referral/routes.py` — Add new endpoint:

```python
from .cord_client import CORDClient
from .entity_graph_service import EntityGraphService

cord_client = CORDClient()

@router.get("/{shipment_id}/entity-graph")
async def get_entity_graph(shipment_id: str) -> Dict[str, Any]:
    """
    Get entity ownership chain directly from CORD microservice.
    
    This is the PRODUCTION endpoint for entity graph data.
    Fetches fresh data from CORD, not fixtures.
    
    Args:
        shipment_id: Shipment identifier (can be manifest_id, SHP-*, etc)
    
    Returns:
        Entity graph data ready for frontend visualization:
        {
            "chain": Entity[],
            "data_sources": ["CORD", "Senzing"],
            "ofac_detected": bool,
            "risk_score": 0-100,
            "confidence_metrics": { ... }
        }
    """
    try:
        # Fetch shipment details
        shipment = await get_shipment_data(shipment_id)  # ← Implementation depends on your DB
        
        if not shipment:
            raise HTTPException(status_code=404, detail=f"Shipment not found: {shipment_id}")
        
        # Call CORD to resolve entities
        cord_response = await cord_client.resolve_shipment_entities(
            shipper_name=shipment.get("shipper_name", ""),
            shipper_country=shipment.get("origin_country", ""),
            consignee_name=shipment.get("consignee_name", ""),
            consignee_country=shipment.get("destination_country", ""),
        )
        
        if not cord_response:
            return {
                "chain": [],
                "data_sources": [],
                "error": "CORD entity resolution failed or microservice unavailable"
            }
        
        # Transform CORD response to Entity format
        entity_graph = EntityGraphService.transform_cord_to_entity_chain(cord_response)
        
        return {
            "shipment_id": shipment_id,
            **entity_graph
        }
        
    except Exception as e:
        logger.error(f"Error fetching entity graph for {shipment_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

---

### Phase 3: Update Referral Package Builder

**File:** `api/services/referral/builder.py` — Update ownership chain building:

```python
async def build_package_with_cord(
    self,
    manifest_id: str,
    manifest_data: Dict[str, Any],
    shipment_id: str,
) -> Dict[str, Any]:
    """
    Build referral package using CORD entity data (PRODUCTION).
    
    Args:
        manifest_id: Manifest identifier
        manifest_data: Raw manifest data
        shipment_id: Shipment ID for entity resolution
    
    Returns:
        Complete referral package with real entity data
    """
    # Fetch entity graph from CORD
    entity_graph = await EntityGraphService.get_entity_graph(shipment_id)
    
    # Build sections using real data
    sections = {
        "shipment_id": self._build_shipment_id(manifest_data),
        "line_items": self._build_line_items(manifest_data),
        "routing_history": self._build_routing_history(manifest_data),
        "section_3_4_parties_and_roles": self._build_parties_from_entity_graph(entity_graph),
        "section_3_5_entity_ownership_chain": entity_graph,  # ← Direct from CORD
        # ... other sections ...
    }
    
    return {
        "package_id": self._generate_package_id(),
        "shipment_id": shipment_id,
        "confidence_level": entity_graph.get("confidence_metrics", {}).get("level", "MEDIUM"),
        "sections": sections
    }
```

---

## Manifest + Senzing Integration

### How Manifest Data Enriches Senzing

**Current Flow:**

```
Manifest → CBPAugmentor → Senzing
  ↓           ↓             ↓
  ├─ Shipper name          Creates CBP-SHIPPER record
  ├─ Origin country        Indexes shipper in DB
  ├─ ISF Element 9         Creates CBP-ISF record
  ├─ Weight/value          Links ISF to shipper
  └─ Consignee             Creates consignee record
                           ↓
                        3-Level Resolution
                           ↓
                        CORD lookup
                        (GLEIF, OFAC, etc.)
                           ↓
                        Ownership chain
```

### Enhanced Approach: Manifest as Senzing Context

To make Senzing aware of manifest details:

**File:** `services/cord-integration/cbp_augmentor.py` — Enhance record creation:

```python
def _create_shipper_record(self, shipment: Dict[str, Any]) -> Dict[str, Any]:
    """Create enhanced CBP-SHIPPER record with manifest context."""
    return {
        "entity_id": f"CBP-SHIP-{shipment['id']}",
        "data_source": "CBP-SHIPPER",
        "name_primary": shipment.get("shipper_name", ""),
        "country": shipment.get("origin_country", ""),
        "confidence": 1.0,  # Direct from manifest
        "raw_data": {
            # ← Add manifest details as context
            "shipment_id": shipment.get("id"),
            "hs_code": shipment.get("hs_code"),
            "commodity": shipment.get("commodity_name"),
            "weight_kg": shipment.get("weight_kg"),
            "isf_element_9": shipment.get("isf_stuffing_country"),
            "declared_coo": shipment.get("declared_coo"),
            "vessel_name": shipment.get("vessel_name"),
            "dwell_days": shipment.get("dwell_days"),
            "risk_flags": shipment.get("manifest_anomalies", [])
        }
    }
```

### When Senzing Calls CORD for Resolution

The enhanced record helps CORD:
1. **Match entities** — Shipper name + country + ISF data
2. **Validate chain** — Cross-check manifest COO claim vs entity jurisdiction
3. **Flag anomalies** — ISF Element 9 mismatch signals ownership chain issues
4. **Risk score** — Incorporate manifest signals (new shipper, dwell anomaly, etc.)

**Example:** If manifest says COO=VN but ISF Element 9=CN:
- CORD finds shipper in VN
- But detects relationship to Chinese manufacturer
- Flags this as **mismatch** in entity graph
- Frontend graph shows **dashed relationship arrows** (risky)

---

## Better Visualization Alternatives

### Current Problem with SVG Graph

❌ **EntityRelationshipGraph** (ui/src/v2/components/EntityRelationshipGraph.tsx):
- Manual SVG node positioning (fragile)
- Limited to linear chains (can't show complex networks)
- No interactive features (pan, zoom, search)
- Hard to extend for more than 3 nodes
- Mobile-unfriendly

❌ **GraphPage** (ui/src/pages/GraphPage.tsx):
- Just a list of nodes
- Sidebar shows relationships
- No visual graph at all

### Option A: React Flow (Recommended for Investigation)

**Pros:**
- Purpose-built for entity/relationship graphs
- Drag-and-drop, pan, zoom out-of-box
- Customizable node styling
- Handles complex networks

**Cons:**
- New dependency (but lightweight)

**Implementation:**

```bash
npm install reactflow
```

**New component:** `ui/src/v2/components/InteractiveEntityGraph.tsx`

```typescript
import ReactFlow, {
  Node, Edge, Background, Controls, MiniMap
} from 'reactflow';
import 'reactflow/dist/style.css';

export function InteractiveEntityGraph({ chain, parties }: EntityGraphProps) {
  // Convert chain to ReactFlow nodes
  const nodes: Node[] = chain.map((entity, idx) => ({
    id: entity.entity_id.toString(),
    data: {
      label: entity.name,
      type: entity.entity_type,
      country: entity.country,
      confidence: entity.confidence
    },
    position: { x: idx * 250, y: 0 },
    style: {
      background: getEntityColor(entity.entity_type),
      border: getRiskBorder(entity),
      borderRadius: 8,
      padding: 12,
      width: 150,
    }
  }));
  
  // Convert relationships to ReactFlow edges
  const edges: Edge[] = [];
  for (let i = 0; i < chain.length - 1; i++) {
    const rels = chain[i].relationships || [];
    for (const rel of rels) {
      edges.push({
        id: `${chain[i].entity_id}-${rel.target}`,
        source: chain[i].entity_id.toString(),
        target: findEntityByName(chain, rel.target).entity_id.toString(),
        label: rel.type,
        style: { stroke: getRiskColor(rel.type) }
      });
    }
  }
  
  return (
    <ReactFlow nodes={nodes} edges={edges}>
      <Background />
      <Controls />
      <MiniMap />
    </ReactFlow>
  );
}
```

### Option B: Mermaid (Lightweight, SVG-based)

**Pros:**
- No new dependencies (already used elsewhere)
- Markdown-like syntax
- Auto-layouts chains perfectly
- Easy to render

**Cons:**
- Less interactive than React Flow
- Limited customization

**Implementation:**

```typescript
import mermaid from 'mermaid';

export function MermaidEntityGraph({ chain }: EntityGraphProps) {
  const diagram = generateMermaidDiagram(chain);
  
  useEffect(() => {
    mermaid.contentLoaded();
  }, [diagram]);
  
  return <div className="mermaid">{diagram}</div>;
}

function generateMermaidDiagram(chain: Entity[]): string {
  let diagram = 'graph LR\n';
  
  chain.forEach((entity, idx) => {
    const color = getEntityColor(entity.entity_type);
    diagram += `  ${entity.entity_id}["${entity.name}<br/>${entity.country}"]:::${color}\n`;
    
    if (idx < chain.length - 1) {
      const rel = entity.relationships?.[0];
      diagram += `  ${entity.entity_id} -->|${rel?.type || 'OWNED_BY'}| ${chain[idx + 1].entity_id}\n`;
    }
  });
  
  return diagram;
}
```

### Option C: D3.js (Most Powerful, Steepest Learning Curve)

**Pros:**
- Maximum flexibility
- Professional-grade visualizations
- Handles complex networks
- Force-directed layouts

**Cons:**
- Steep learning curve
- More code to maintain
- Overkill for 3-entity chains

---

## Recommended Implementation Plan

### Timeline

**Week 1: Cleanup + Setup**
- [x] Mark fixtures as deprecated
- [ ] Implement CORDClient service
- [ ] Add EntityGraphService transformer
- [ ] Test CORD connectivity

**Week 2: Integration**
- [ ] Implement `/entity-graph` endpoint
- [ ] Update referral builder to use CORD
- [ ] Update frontend API client
- [ ] Test end-to-end data flow

**Week 3: Visualization**
- [ ] Choose visualization (React Flow recommended)
- [ ] Implement new entity graph component
- [ ] Replace EntityRelationshipGraph in Investigation page
- [ ] Test visualization with real data

**Week 4: Polish + Manifest Enhancement**
- [ ] Enhance manifest augmentation
- [ ] Add manifest context to Senzing records
- [ ] Test ISF mismatch detection in entity graph
- [ ] Performance optimization

---

## Testing Checklist

### Phase 1: CORD Integration
- [ ] CORD service returns 3-level chain with relationships
- [ ] EntityGraphService transforms response correctly
- [ ] All required fields present (entity_id, entity_type, relationships[])
- [ ] Frontend receives non-null chain data

### Phase 2: Visualization
- [ ] 3 nodes render correctly
- [ ] Relationship arrows display with labels
- [ ] Risk colors apply (shipper=blue, holding=amber, mfg=green)
- [ ] Confidence badges show (95%, 92%, 98%)
- [ ] Mobile responsive

### Phase 3: Manifest Integration
- [ ] ISF Element 9 mismatch detected in entity chain
- [ ] New shipper flag reflected in relationships
- [ ] Dwell anomaly visible in shipper node
- [ ] Risk scoring incorporates manifest signals

---

## Files to Create/Modify

### Create New
- `api/services/referral/cord_client.py` — CORD microservice client
- `api/services/referral/entity_graph_service.py` — CORD transformer
- `ui/src/v2/components/InteractiveEntityGraph.tsx` — React Flow visualization

### Modify
- `api/services/referral/routes.py` — Add `/entity-graph` endpoint, mark old endpoint deprecated
- `api/services/referral/builder.py` — Update ownership chain logic
- `services/cord-integration/cbp_augmentor.py` — Enhance manifest enrichment
- `ui/src/v2/pages/V2InvestigationsPage.tsx` — Call new entity-graph endpoint, use new visualization

### Delete/Archive
- Remove fixture data from `routes.py` (or move to `_legacy_fixtures.py`)
- Remove unused `_build_ownership_chain()` from builder

---

## Questions to Address

**Q: How do we validate Senzing has CORD data loaded?**
A: Check `/health` endpoint on sentry-cord-integration:8004 — should show `"entity_count": 245000+`

**Q: What if CORD microservice is down?**
A: Fallback to fixtures with warning log. Update frontend to show degraded data state.

**Q: How do we handle ISF mismatches in the graph?**
A: Manifest data enriches shipper record → Senzing detects manufacturer in different country → Entity graph shows PARENT_COMPANY relationship with dashed arrow in UI

**Q: Should we pre-cache entity resolution results?**
A: Yes, cache CORD results in PostgreSQL for 24h to avoid repeated microservice calls for same shipper.

