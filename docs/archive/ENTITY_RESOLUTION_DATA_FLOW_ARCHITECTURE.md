# Entity Resolution Tab - Data Flow & User Journey Architecture
## Clarification Document for Discussion

**Status:** Architecture Planning - Awaiting CBP Officer Workflow Input  
**Date:** May 27, 2026

---

## CRITICAL DESIGN QUESTION: Entry Points into Entity Resolution

### Question: How do CBP Officers Access Entity Resolution Tab?

There are three potential user journeys. **Which one(s) should we support?**

---

## OPTION 1: FROM SHIPMENT CONTEXT (Most Likely?)

### User Flow
```
Officer is reviewing Active Shipments in Shipping Intelligence
    │
    └─→ Clicks on HIGH RISK shipment
         │
         └─→ Views Shipment Detail
             │
             ├─→ Sees Shipper: "Greenfield Industrial Trading Co., Ltd." | VN
             ├─→ Sees Consignee: "SunPath Energy Distributors LLC" | US
             ├─→ Sees Risk Score: 87/100 (HIGH)
             │
             └─→ [INVESTIGATE ENTITIES] button
                 │
                 └─→ Entity Resolution Tab Opens
                     │
                     ├─→ Pre-populated with:
                     │   • Shipper name
                     │   • Consignee name
                     │   • Shipment ID (for case reference)
                     │
                     └─→ Shows:
                         • Full 4-level supply chain for shipper
                         • Full 4-level supply chain for consignee
                         • Why-connected evidence for each level
                         • Risk assessment (individual + aggregated)
                         • Prior CBP enforcement on these entities
                         • Option to drill down on any entity
```

**Data Flow:**
```
Shipment Data (Sentry API)
    ├─ shipper_name
    ├─ consignee_name
    ├─ shipper_country
    ├─ consignee_country
    └─ shipment_id
         │
         └─→ Entity Resolution Service (Backend)
             │
             ├─→ CORD API: Search shipper + consignee
             ├─→ Senzing API: Resolve entity chains
             ├─→ CORD API: Get entity details (OFAC, SDN)
             ├─→ CORD API: Get entity chains (3-4 levels)
             ├─→ Senzing API: Why-connected evidence
             ├─→ CBP Enforcement DB: Prior filings
             │
             └─→ Response: Complete entity intelligence
                 │
                 └─→ Frontend: Display in Entity Resolution Tab
```

**Pros:**
- Officer has context (shipment being reviewed)
- Natural workflow (shipment → entities → investigation)
- Can directly compare shipper/consignee relationship
- Case file integration (link entities to shipment ID)

**Cons:**
- Only works when reviewing shipments
- Can't do independent entity research
- Limited to entities in current shipment

---

## OPTION 2: STANDALONE ENTITY RESEARCH (Also Needed?)

### User Flow
```
Officer wants to proactively investigate an entity (not tied to shipment)
    │
    └─→ Opens Entity Resolution Tab (standalone)
         │
         └─→ [Search Entity] dialog
             │
             └─→ Officer enters:
                 • Entity name: "Greenfield Industrial Trading Co., Ltd."
                 • Country (optional): Vietnam
                 • Entity type (optional): Shipper
                 │
                 └─→ Returns CORD search results:
                     • Top 10 matches from 244K entities in CORD
                     • Confidence scores
                     • Risk levels
                     │
                     └─→ Officer clicks entity
                         │
                         └─→ Shows full entity intelligence:
                             • All details (4-level chains, why-connected, etc.)
```

**Data Flow:**
```
Officer Search Query
    │
    └─→ Entity Resolution Service
         │
         ├─→ CORD API: Full-text search (244K entities)
         │   └─→ Returns: [entities with name match, confidence, country]
         │
         └─→ [Officer selects entity]
             │
             ├─→ CORD API: Get entity details
             ├─→ Senzing API: Resolve entity chains
             ├─→ CORD API: Get OFAC/SDN status
             ├─→ Senzing API: Why-connected evidence
             ├─→ CBP Enforcement DB: Prior filings
             │
             └─→ Response: Complete entity intelligence
                 │
                 └─→ Frontend: Display full entity detail
```

**Pros:**
- Flexible - any entity can be researched
- Support for proactive screening
- Good for building watchlists
- Officers can explore related entities

**Cons:**
- Requires more UI work (search dialog, results)
- No shipment context
- Need to validate/confirm entity match

---

## OPTION 3: HIGH-RISK ENTITY WATCHLIST (Monitoring?)

### User Flow
```
System continuously monitors high-risk entities from CORD
    │
    └─→ Flags entities that:
         • Are new additions to OFAC SDN list
         • Have new enforcement actions
         • Are repeat violators
         • Have shared directors with flagged entities
         │
         └─→ Entity Resolution Tab shows:
             • High-Risk Entity Queue (sorted by risk)
             • Officer reviews each for pattern recognition
             • Can dismiss, investigate, or refer to enforcement
```

**Data Flow:**
```
Scheduled Job (Daily/Hourly)
    │
    ├─→ CORD: Check for new OFAC/SDN additions
    ├─→ CBP DB: Check for new enforcement actions
    ├─→ Senzing: Check for new relationship patterns
    │
    └─→ Build High-Risk Entity Queue
         │
         └─→ Entity Resolution Tab:
             • Display watchlist
             • Officer can drill into any entity
             • Mark as investigated/cleared/escalated
```

**Pros:**
- Proactive threat detection
- Automated monitoring
- Pattern recognition across network

**Cons:**
- Requires significant backend work
- High false positive potential
- Requires tuning/calibration

---

## CURRENT SYSTEM STATE: What Data Do We Have NOW?

### ✅ Data Currently Available

**CORD Database (244K entities):**
- Entity name, country, tax ID
- Entity type (shipper, consignee, manufacturer, intermediary)
- OFAC status (SDN, WATCH, CLEAR)
- OFAC program (if listed)
- Sanctions topic (if applicable)
- Basic company registration data
- Located in: SQLite DB at `data/cbp_sentry.db`

**Manifest Data:**
- Shipper name + country
- Consignee name + country
- Manufacturer name + country
- Commodity, quantity, value
- Trade lane (origin → destination)
- Located in: SQLite DB (already populated)

**ISF (Import Security Filing) Data:**
- Pre-import security filing details
- ISF filer information
- More detailed shipment data
- Located in: SQLite DB (already populated)

**Senzing APIs (Available):**
- Entity resolution (shipper/consignee matching)
- Why-connected evidence (shared directors, agents, etc.)
- Confidence scoring (0-1)
- Prior filings (CBP enforcement history)
- Located in: `services/api/senzing_client.py`

**CORD APIs (Available):**
- Entity search (full-text search on 244K entities)
- Entity resolve (3-level supply chain)
- Entity details (full record)
- Entity chain (ownership hierarchy)
- Located in: `services/api/cord_integration/` or similar

**CBP Enforcement Data:**
- Prior EAPA cases
- Prior AD/CVD cases
- Settlement agreements
- Located in: SQLite DB or CBP case management system

### ❌ Data Currently NOT Integrated

**CORD/Senzing Service:**
- Need to confirm: What endpoints are actually available?
- Need to confirm: Response data structure for each endpoint?
- Need to confirm: Do APIs return why-connected evidence?
- Need to confirm: Do APIs return prior filings?

**Backend Entity Resolution Service:**
- Location: `services/api/` (main API)
- Current: Not clear if there's a dedicated entity resolution service
- Needed: New endpoints for Entity Resolution tab

---

## PROPOSED UNIFIED ARCHITECTURE

### Backend Service Structure

```
sentry-api (services/api/)
    │
    ├─→ routers/
    │   └─→ entity_resolution_router.py [NEW]
    │       │
    │       ├─→ GET /api/entity/search
    │       │   Input: entity_name, country, entity_type
    │       │   Uses: CORD full-text search
    │       │   Returns: [entities with match confidence]
    │       │
    │       ├─→ GET /api/entity/{entity_id}
    │       │   Input: entity_id (from CORD)
    │       │   Uses: CORD + Senzing APIs
    │       │   Returns: Full entity intelligence
    │       │
    │       ├─→ POST /api/entity/resolve-shipment
    │       │   Input: shipment_id
    │       │   Extracts: shipper, consignee from manifest
    │       │   Returns: Full intelligence for both entities
    │       │
    │       ├─→ GET /api/entity/{entity_id}/chain
    │       │   Returns: 4-level supply chain with why-connected
    │       │
    │       ├─→ GET /api/entity/{entity_a}/{entity_b}/why-connected
    │       │   Returns: Evidence linking two entities
    │       │
    │       └─→ GET /api/entity/{entity_id}/enforcement-history
    │           Returns: Prior CBP cases, pattern analysis
    │
    ├─→ services/
    │   ├─→ entity_resolution_service.py [NEW]
    │   │   • Orchestrate CORD + Senzing calls
    │   │   • Build complete entity intelligence
    │   │   • Cache frequently accessed entities
    │   │   • Risk aggregation logic
    │   │
    │   ├─→ cord_service.py [ENHANCE]
    │   │   • Search entities
    │   │   • Get entity details
    │   │   • Get entity chains
    │   │   • Get OFAC/SDN status
    │   │
    │   └─→ senzing_service.py [ENHANCE]
    │       • Resolve entities (confidence)
    │       • Why-connected evidence
    │       • Prior filings
    │       • Confidence scoring
    │
    └─→ core/
        └─→ senzing_client.py [EXISTING]
        └─→ cord_client.py [EXISTING or NEW?]
```

### Frontend Component Structure

```
ui/src/v2/pages/V2EntitiesPage.tsx [ENHANCE]
    │
    ├─→ Entry Point Detection:
    │   ├─→ If called from Shipment → Pre-populate shipper/consignee
    │   └─→ If called standalone → Show search dialog
    │
    ├─→ Entity Search Component
    │   ├─→ Search input
    │   ├─→ Results list
    │   └─→ Selection handling
    │
    ├─→ Entity Intelligence Dashboard [NEW]
    │   │
    │   ├─→ EntityCardEnhanced [NEW]
    │   │   • Entity details
    │   │   • OFAC/SDN status
    │   │   • Prior filings
    │   │   • Risk assessment
    │   │
    │   ├─→ SupplyChainVisualization [NEW]
    │   │   • 4-level chain display
    │   │   • Why-connected evidence
    │   │   • Relationship types
    │   │   • Confidence scores
    │   │
    │   ├─→ RelationshipGraph [NEW]
    │   │   • Interactive D3.js/React Flow network
    │   │   • Node = entity, Edge = relationship
    │   │   • Color by risk level
    │   │   • Hover for evidence
    │   │
    │   ├─→ RiskAggregationPanel [NEW]
    │   │   • Chain-level risk score
    │   │   • Flagged entities count
    │   │   • Recommendation
    │   │
    │   ├─→ SharedIdentifiersPanel [NEW]
    │   │   • Shared directors
    │   │   • Shared agents
    │   │   • Shared locations
    │   │
    │   └─→ EnforcementHistoryPanel [NEW]
    │       • Prior CBP cases
    │       • Case details
    │       • Pattern analysis
    │
    └─→ Actions:
        ├─→ [Drill Down] - Explore entity relationships
        ├─→ [View Network] - See full relationship graph
        ├─→ [Export] - Save entity intelligence to case file
        └─→ [Refer to Enforcement] - Send to investigation team
```

---

## DATA FLOW: WHICH SCENARIO?

### **I Need YOU to Clarify:**

**1. PRIMARY ENTRY POINT:**
- **A)** Officer reviews shipment in Shipping Intelligence, clicks [Investigate Entities] → Goes to Entity Resolution
- **B)** Officer opens Entity Resolution tab directly, searches for entity by name
- **C)** Both A and B (two different workflows)

**2. INITIAL DISPLAY:**
When officer clicks into Entity Resolution, should it show:
- **A)** Empty search dialog (officer must search)
- **B)** Pre-populated with entity from shipment context (if coming from shipment)
- **C)** High-risk entity queue (system-generated watchlist)
- **D)** List of recently viewed entities (history)

**3. DATA TRIGGER:**
Which entities should be shown in Entity Resolution?
- **A)** Only entities that are in current shipments (filtered from manifest)
- **B)** All 244K entities from CORD (full database searchable)
- **C)** High-risk subset of CORD (OFAC, new shippers, repeat violators)
- **D)** Officer-configured watchlist

**4. USE CASE PRIORITY:**
Which use case is most critical for CBP officers?
- **A)** "I'm reviewing a shipment - show me shipper/consignee risk" (Option 1)
- **B)** "I want to research a specific entity I heard about" (Option 2)
- **C)** "Show me new high-risk entities I should be aware of" (Option 3)
- **D)** All equally important

---

## PROPOSED MVP DESIGN (Based on Assumptions)

**ASSUMPTION:** Officers primarily use Entity Resolution **in context of shipment review** (Option 1 + Option 2 combined)

### User Journey
```
┌─────────────────────────────────────────────────────────────────┐
│ WORKFLOW 1: From Shipping Intelligence                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ 1. Officer views Shipping Intelligence page                    │
│    └─→ Sees high-risk shipment: Risk 87/100                   │
│                                                                 │
│ 2. Clicks [INVESTIGATE ENTITIES] button                        │
│    └─→ Entity Resolution tab opens with shipment data:         │
│        • Shipper: Greenfield Industrial (VN)                  │
│        • Consignee: SunPath Energy (US)                       │
│        • Shipment ID: SHP-20260527-001                         │
│                                                                 │
│ 3. Entity Resolution shows:                                    │
│    ├─→ Shipper Chain (4 levels):                              │
│    │   ├─ Greenfield Industrial (VN) - Shipper                │
│    │   ├─ Greenfield Holdings (HK) - Parent                   │
│    │   ├─ Greenfield Mfg (CN) - Beneficial Owner              │
│    │   └─ [Ultimate Owner - if available]                     │
│    │                                                           │
│    ├─→ Consignee Status:                                       │
│    │   └─ SunPath Energy (US) - Importer                      │
│    │                                                           │
│    ├─→ Each entity shows:                                      │
│    │   ├─ Risk level (CRITICAL/HIGH/MEDIUM/LOW)              │
│    │   ├─ OFAC status (if listed)                            │
│    │   ├─ Prior CBP enforcement                               │
│    │   ├─ Why connected (to parent):                          │
│    │   │  ├─ Director Li Wei (0.94 confidence)               │
│    │   │  └─ Shared registered agent (0.91 confidence)        │
│    │   └─ Relationship type (OWNS, PARENT_OF, etc.)          │
│    │                                                           │
│    ├─→ Chain Risk Assessment:                                 │
│    │   ├─ Overall: CRITICAL                                   │
│    │   ├─ Reason: Level 1 is OFAC listed                     │
│    │   └─ Recommendation: ESCALATE to enforcement             │
│    │                                                           │
│    └─→ Actions:                                                │
│        ├─ [View Network Graph] - See visual relationships     │
│        ├─ [Drill Down] - Explore specific entity              │
│        ├─ [Generate Referral] - Start enforcement case        │
│        └─ [Return to Shipment] - Back to shipping intelligence │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│ WORKFLOW 2: Standalone Entity Search                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ 1. Officer opens Entity Resolution tab (no shipment context)  │
│    └─→ Shows search dialog:                                    │
│        "Search entity by name, country..."                    │
│                                                                 │
│ 2. Officer enters: "Greenfield" + filters                     │
│    └─→ Returns top 10 matches from CORD:                      │
│        • Greenfield Industrial (VN) - 0.98 match              │
│        • Greenfield Holdings (HK) - 0.95 match                │
│        • Green Field Industries (SG) - 0.87 match             │
│        [... more results]                                      │
│                                                                 │
│ 3. Officer clicks entity                                       │
│    └─→ Shows same full intelligence as Workflow 1              │
│        But WITHOUT shipment context                            │
│                                                                 │
│ 4. Officer can:                                                │
│    ├─ [Link to Shipment] - If this entity is in manifest      │
│    ├─ [Add to Watchlist] - Mark for monitoring                │
│    ├─ [Export Profile] - Save for reference                   │
│    └─ [Search Related] - Explore connected entities           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## API ENDPOINTS NEEDED (Backend)

### For Workflow 1: Shipment Context
```
POST /api/entity/resolve-shipment
  Input: {
    shipment_id: "SHP-20260527-001"
  }
  
  Backend:
    1. Get shipment from manifest DB
    2. Extract shipper_name, shipper_country, consignee_name, consignee_country
    3. Call CORD search for each
    4. Call Senzing resolve for chains
    5. Call why-connected for each pair
    6. Call enforcement history for each entity
    7. Aggregate risk
    
  Output: {
    shipment_id,
    shipper_entity: { full intelligence },
    consignee_entity: { full intelligence },
    chain_risk: { aggregated score },
    recommendation: "ESCALATE" | "INVESTIGATE" | "CLEAR"
  }
```

### For Workflow 2: Standalone Search
```
GET /api/entity/search?name=Greenfield&country=VN&limit=10
  Uses: CORD full-text search
  
  Output: [{
    entity_id,
    name,
    country,
    entity_type,
    risk_level,
    watchlist_status,
    match_confidence
  }]
```

```
GET /api/entity/{entity_id}/intelligence
  Uses: CORD + Senzing APIs
  
  Output: {
    entity_details: { full record },
    entity_chains: [ 4-level chains ],
    why_connected: [ evidence for each level ],
    enforcement_history: [ prior cases ],
    risk_assessment: { aggregated },
    shared_identifiers: { directors, agents, locations }
  }
```

---

## DATABASE: What's Needed?

### ✅ EXISTING
- `cbp_sentry.db` - Contains manifest, ISF, entity data
- Tables: shipments, shippers, consignees, commodities, etc.

### NEEDED (New or Enhancement)
```
1. entity_relationships (Cache why-connected evidence)
   - entity_a_id
   - entity_b_id
   - relationship_type (OWNS, PARENT_OF, etc.)
   - evidence (JSON: why_connected from Senzing)
   - confidence
   - last_updated

2. entity_enforcement_history (Cache prior filings)
   - entity_id
   - case_id (CBP case)
   - case_type (EAPA, AD/CVD, etc.)
   - determination
   - settlement_amount_usd
   - date_filed
   - date_closed

3. entity_risk_cache (Cache risk scores)
   - entity_id
   - risk_level (CRITICAL/HIGH/MEDIUM/LOW)
   - risk_score (0-100)
   - flags (JSON: NEW_SHIPPER, OFAC_WATCH, etc.)
   - calculated_at
```

---

## SUMMARY: Architecture vs. Actual Implementation

| Component | Current Status | Needed |
|-----------|---|---|
| CORD DB (244K entities) | ✅ Exists | Use as-is |
| Manifest/Shipment data | ✅ Exists | Extract shipper/consignee |
| CORD APIs | ❓ Unknown | Confirm endpoints, response format |
| Senzing APIs | ❓ Unknown | Confirm endpoints, response format |
| Entity Resolution Service | ❌ Missing | Build new (`entity_resolution_router.py`) |
| Entity Intelligence UI | ❌ Missing | Build new components |
| Entity Relationship Cache | ❌ Missing | Add DB tables |
| Entity Enforcement Cache | ❌ Missing | Add DB tables |

---

## NEXT STEPS FOR DISCUSSION

**Please clarify:**

1. ✅ **Primary user workflow** - Option 1, 2, or both?
2. ✅ **Entry point** - From shipment or standalone search?
3. ✅ **CORD/Senzing APIs** - What endpoints are actually available?
4. ✅ **Data freshness** - How often should entity data be refreshed?
5. ✅ **Officer workflow** - What actions should be possible from Entity Resolution?

**Once clarified, I can:**
- Finalize backend API design
- Design database schema
- Create detailed component specifications
- Build implementation plan with timeline

