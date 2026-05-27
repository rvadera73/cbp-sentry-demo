# Entity Resolution Architecture Diagram

## Complete System Architecture

```
┌────────────────────────────────────────────────────────────────────────────┐
│                                                                            │
│                          BROWSER (Port 3000)                              │
│                        ┌────────────────────────┐                         │
│                        │  React Single-Spa App  │                         │
│                        │  Entity Resolution Tab │                         │
│                        └────────────────────────┘                         │
│                                  │                                         │
│      ┌───────────────────────────┼───────────────────────────┐            │
│      │                           │                           │            │
│  ┌───▼────────────────┐  ┌──────▼─────────────┐  ┌─────────▼────────┐   │
│  │ V2EntitiesPage.tsx │  │useV2Entities Hook │  │  API Client      │   │
│  │   (Component)      │  │ (Data Logic)       │  │   (fetch calls)  │   │
│  └────────────────────┘  └────────────────────┘  └──────────────────┘   │
│                                  │                           │            │
│                                  └───────────────┬───────────┘            │
│                                                  │                        │
└──────────────────────────────────────────────────┼────────────────────────┘
                                                   │
                        HTTP/JSON Requests         │
                                                   ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                                                                          │
│                API Gateway (FastAPI, Port 8000)                         │
│                         main.py                                         │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │ Routes:                                                            │ │
│  │  • GET  /api/cord/search                                           │ │
│  │  • POST /api/cord/resolve                                          │ │
│  │  • GET  /api/cord/entity/{id}                                      │ │
│  │  • GET  /api/cord/entity/{id}/chain                                │ │
│  │  • GET  /api/cord/entity/{id}/parties                              │ │
│  │  • POST /api/cord/why/{id_a}/{id_b}                                │ │
│  │                                                                    │ │
│  │  (All proxy to CORD microservice at localhost:8004)               │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
│                                                                          │
└────────────────────┬────────────────────────────────────────────────────┘
                     │
         gRPC/HTTP Proxy Request (internal)
                     │
                     ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                                                                          │
│         CORD Microservice (Port 8004, Internal Only)                    │
│         cord-integration/main.py                                        │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │ Endpoints:                                                         │ │
│  │  • GET /search        → Query FTS5 index                           │ │
│  │  • POST /resolve      → Run entity resolution algorithm            │ │
│  │  • GET /entity/{id}   → Fetch full record                          │ │
│  │  • GET /entity/{id}/chain → Get relationship chain                 │ │
│  │  • GET /entity/{id}/parties → Get supply chain parties             │ │
│  │  • POST /why/{id_a}/{id_b} → Why-connected explanation             │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
│                                                                          │
└────────────────────┬────────────────────────────────────────────────────┘
                     │
           SQLite Query (local file)
                     │
                     ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                                                                          │
│            SQLite Database: cord_index.db                               │
│         Full-Text Search (FTS5) Index                                   │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │ Tables:                                                            │ │
│  │                                                                    │ │
│  │  cord_fts (FTS5 Virtual Table)                                     │ │
│  │  ├─ record_id: Unique entity ID                                    │ │
│  │  ├─ data_source: GLEIF, OFAC, etc.                                 │ │
│  │  ├─ record_type: Entity classification                             │ │
│  │  ├─ name_primary: Official name                                    │ │
│  │  ├─ names_aka: Alternative names                                   │ │
│  │  ├─ country: Registration country                                  │ │
│  │  ├─ ofac_program: If OFAC listed                                   │ │
│  │  ├─ sanctions_topic: Sanctions classification                      │ │
│  │  └─ raw_json: Complete entity record (JSON)                        │ │
│  │                                                                    │ │
│  │  ofac_sdn (OFAC-specific table for SDN checks)                      │ │
│  │  ├─ record_id: SDN ID                                              │ │
│  │  ├─ name_primary: SDN name                                         │ │
│  │  ├─ names_aka: AKA names                                           │ │
│  │  ├─ sdn_program: Program type                                      │ │
│  │  ├─ entity_type: Type classification                               │ │
│  │  └─ raw_json: Full SDN record                                      │ │
│  │                                                                    │ │
│  │ Size: 244,000+ entities indexed                                    │ │
│  │ Data Sources: GLEIF, OFAC, OpenCorporates, etc.                    │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow: Entity Queue Load

```
┌─────────────────────────────────────────────────────────────────────────┐
│ 1. Component Mount (useEffect)                                          │
│    loadCORDEntities() called                                            │
└────┬────────────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 2. For Each Sample Entity:                                              │
│    - Greenfield Industrial Trading Co.                                  │
│    - Guangdong Greenfield Aluminum Manufacturing                        │
│    - Bangalore Electronics Trade Group                                  │
│    - (6 total)                                                          │
└────┬────────────────────────────────────────────────────────────────────┘
     │
     ▼ (In parallel batches of 10)
┌─────────────────────────────────────────────────────────────────────────┐
│ 3. SEARCH API CALL                                                      │
│                                                                         │
│    GET /api/cord/search                                                │
│    ?name=Greenfield%20Industrial%20Trading%20Co.                       │
│    &country=VN                                                         │
│    &limit=1                                                            │
│                                                                         │
│    Response:                                                           │
│    {                                                                   │
│      "matches": [{                                                     │
│        "name": "Greenfield Industrial Trading Co., Ltd.",              │
│        "country": "VN",                                                │
│        "raw_json": { OFAC_STATUS: "WATCH", ... }                       │
│      }]                                                                │
│    }                                                                   │
│                                                                         │
│    Time: ~300ms per entity                                             │
└────┬────────────────────────────────────────────────────────────────────┘
     │
     ▼ (Immediately after search)
┌─────────────────────────────────────────────────────────────────────────┐
│ 4. RESOLVE API CALL (3-4 Level Chain)                                   │
│                                                                         │
│    POST /api/cord/resolve                                              │
│    ?shipper_name=Greenfield%20Industrial%20Trading%20Co.               │
│    &shipper_country=VN                                                 │
│                                                                         │
│    Response:                                                           │
│    {                                                                   │
│      "resolution": {                                                   │
│        "level_1": {...},                                               │
│        "level_1_relationship": {...},                                  │
│        "level_2": {...},                                               │
│        "level_2_relationship": {...},                                  │
│        "level_3": {...},                                               │
│        "level_3_relationship": {...}                                   │
│      }                                                                 │
│    }                                                                   │
│                                                                         │
│    Time: ~500ms per entity                                             │
└────┬────────────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 5. TRANSFORM DATA                                                       │
│                                                                         │
│    mapCordToTradeEntity():                                              │
│    ├─ Extract OFAC_STATUS → Determine risk_level                       │
│    ├─ Create entity_chain array from resolution levels                  │
│    ├─ Add relationship evidence                                        │
│    └─ Return TradeEntity object                                        │
│                                                                         │
│    Result:                                                             │
│    {                                                                   │
│      entity_id: "greenfield-industrial-trading-co-vn",                 │
│      entity_name: "Greenfield Industrial Trading Co., Ltd.",           │
│      country: "VN",                                                    │
│      risk_level: "High",      ← From OFAC_STATUS: "WATCH"              │
│      watchlist_status: "Flagged",                                      │
│      entity_chain: [...]      ← 3-4 level array                        │
│    }                                                                   │
└────┬────────────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 6. SORT & RENDER                                                        │
│                                                                         │
│    entities.sort((a, b) => riskOrder[a.risk_level] - ...)              │
│                                                                         │
│    Rendered in table:                                                  │
│    ┌────────────────────────────────────────────────────────────────┐  │
│    │ NAME                      │ TYPE  │ COUNTRY │ TAX ID │ STATUS  │  │
│    ├────────────────────────────────────────────────────────────────┤  │
│    │ Greenfield (VN)           │ Mfg   │ VN      │ N/A    │ Flagged │  │
│    │ Greenfield (CN)           │ Mfg   │ CN      │ N/A    │ OK      │  │
│    │ Bangalore Electronics     │ Mfg   │ IN      │ N/A    │ OK      │  │
│    │ ...                       │ ...   │ ...     │ ...    │ ...     │  │
│    └────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│    Time: ~50ms for 6 entities                                          │
└────┬────────────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ TOTAL TIME: ~2-3 seconds                                                │
│                                                                         │
│ Timeline:                                                              │
│  0-600ms:  Search CORD x6 (parallel in batches)                        │
│  200-1000ms: Resolve chains x6 (parallel in batches)                   │
│  500ms:    Transform & sort                                           │
│  50ms:     Render queue                                               │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow: Entity Selection (Workspace)

```
┌─────────────────────────────────────────────────────────────────────────┐
│ 1. User clicks "WORKSPACE" button in queue                             │
│                                                                         │
│    onClick={() => selectEntity(entity.entity_id)}                      │
│    entity.entity_id = "greenfield-industrial-trading-co-vn"            │
└────┬────────────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 2. selectEntity() async function called                                 │
│                                                                         │
│    const entity = entities.find(e => e.entity_id === entityId)         │
│    ✓ Found in queue (already has entity_chain from step 4)             │
└────┬────────────────────────────────────────────────────────────────────┘
     │
     ├──────────────────────┬──────────────────────┐
     │                      │                      │
     ▼                      ▼                      ▼
┌──────────────────┐  ┌──────────────────┐  ┌────────────────┐
│ 3a. CHAIN API    │  │ 3b. PARTIES API  │  │ 3c. DATA       │
│ (Fallback only)  │  │ (Fallback only)  │  │ TRANSFORM      │
│                  │  │                  │  │                │
│ GET /api/cord/   │  │ GET /api/cord/   │  │ mapCordTo      │
│ entity/{id}/     │  │ entity/{id}/     │  │ TradeEntity()  │
│ chain            │  │ parties          │  │                │
│                  │  │                  │  │ Enrich with    │
│ (Already in      │  │ (Already in      │  │ chain & parties│
│  state from      │  │  state from      │  │                │
│  queue load)     │  │  queue load)     │  │ Build final    │
│                  │  │                  │  │ entity object  │
└──────────────────┘  └──────────────────┘  └────────────────┘
     │                      │                      │
     └──────────────────────┼──────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 4. MERGE ENTITY DATA                                                    │
│                                                                         │
│    const enrichedEntity: TradeEntity = {                                │
│      ...entity,  ← From queue                                           │
│      entity_chain: entityChain,  ← From API or queue                    │
│      parties: parties,  ← From API or queue                             │
│    }                                                                    │
│                                                                         │
│    Result:                                                             │
│    {                                                                   │
│      entity_id: "greenfield-industrial-trading-co-vn",                 │
│      entity_name: "Greenfield Industrial Trading Co., Ltd.",           │
│      country: "VN",                                                    │
│      risk_level: "High",                                               │
│      watchlist_status: "Flagged",                                      │
│      entity_chain: [                                                   │
│        { name: "Greenfield VN", country: "VN", role: "Direct", ... }, │
│        { name: "Greenfield HK", country: "HK", role: "Parent", ... }, │
│        { name: "Guangdong Greenfield CN", country: "CN", ... }        │
│      ],                                                                │
│      parties: [                                                        │
│        { entity: "DHL", role: "Freight Forwarder", country: "VN" },    │
│        { entity: "ICBC", role: "Bank", country: "VN" }                 │
│      ]                                                                 │
│    }                                                                   │
└────┬────────────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 5. SET SELECTED ENTITY STATE                                            │
│                                                                         │
│    setSelectedEntity(enrichedEntity)                                    │
│    ↓ React re-renders with selectedEntity !== null                     │
└────┬────────────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 6. RENDER WORKSPACE                                                     │
│                                                                         │
│    V2EntitiesPage.tsx (Line 132-282):                                   │
│    ├─ Entity Header (name, ID, status badge)                           │
│    ├─ Entity Details Grid (Type, Country, Tax ID, Source)              │
│    ├─ Entity Relationship Chain (3-4 levels with WHY CONNECTED)         │
│    ├─ Risk Assessment (if High/Critical)                               │
│    └─ Supply Chain Parties Table                                       │
│                                                                         │
│    Time: ~50ms render                                                  │
└────┬────────────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ TOTAL TIME: 200-800ms                                                   │
│                                                                         │
│ (If chain/parties already cached from queue load: ~50ms)               │
│ (If need to fetch from API: ~500ms for both calls)                     │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Component Structure

```
V2EntitiesPage.tsx (Main Component)
│
├─ Header Section
│  └─ "Entity Resolution" title
│
├─ List View (Left Side)
│  ├─ Search Bar
│  └─ Entity Queue Table
│     ├─ ENTITY NAME / ID (from entity_name, entity_id)
│     ├─ TYPE (from entity_type)
│     ├─ COUNTRY (from country)
│     ├─ TAX ID (from tax_id)
│     ├─ STATUS (from watchlist_status)
│     └─ ACTIONS → onClick: selectEntity(entity_id)
│
└─ Detail Panel (Right Side) ← Shown when selectedEntity !== null
   │
   ├─ Back Button
   │
   ├─ Entity Identity Header
   │  ├─ entity_name
   │  ├─ entity_id
   │  └─ watchlist_status (badge)
   │
   ├─ Entity Details Grid (4-column)
   │  ├─ Type (entity_type)
   │  ├─ Country (country)
   │  ├─ Tax ID (tax_id)
   │  └─ Source ("CORD")
   │
   ├─ Entity Relationship Chain
   │  └─ For each level in entity_chain:
   │     ├─ Entity Name (name)
   │     ├─ Country (country)
   │     ├─ Role (role)
   │     ├─ Confidence (confidence)
   │     ├─ Level Label (1=DIRECT, 2-4=LEVEL N)
   │     └─ WHY CONNECTED (relationships[])
   │        └─ For each relationship:
   │           ├─ Relationship type (type)
   │           └─ Details (details)
   │
   ├─ Risk Assessment (if High/Critical risk)
   │  └─ OFAC status & warning
   │
   └─ Supply Chain Parties Table (if parties exist)
      ├─ ROLE (party.role)
      ├─ ENTITY (party.entity)
      └─ COUNTRY (party.country)
```

---

## Data Transformation Pipeline

```
CORD Raw JSON
    ↓
┌───────────────────────────────────────────────┐
│ mapCordToTradeEntity()                        │
│                                               │
│ Input:                                        │
│  cordEntity: {                                │
│    name: string                               │
│    country: string                            │
│    OFAC_STATUS: "BLOCKED"|"WATCH"|"CLEAR"    │
│    entity_type: string                        │
│    ...                                        │
│  }                                            │
│                                               │
│ Processing:                                   │
│  ├─ Extract OFAC_STATUS                       │
│  │  ├─ "BLOCKED" → risk_level = "Critical"   │
│  │  ├─ "WATCH" → risk_level = "High"         │
│  │  ├─ "CLEAR" → risk_level = "Verified"     │
│  │  └─ null → risk_level = "Low"             │
│  │                                            │
│  ├─ Determine watchlist_status                │
│  │  └─ "Critical" or "High" → "Flagged"      │
│  │                                            │
│  ├─ Generate entity_id                        │
│  │  └─ `${name}|${country}` lowercase        │
│  │                                            │
│  └─ Build entity_chain (if available)         │
│     └─ From resolveEntityChainFromCORD()     │
│                                               │
│ Output:                                       │
│  TradeEntity: {                               │
│    entity_id: string                          │
│    entity_name: string                        │
│    country: string                            │
│    entity_type: string                        │
│    risk_level: "Critical"|"High"|"Medium"...  │
│    watchlist_status: "Flagged"|"Not Flagged"  │
│    entity_chain: Entity[]                     │
│    parties: Party[]                           │
│  }                                            │
└───────────────────────────────────────────────┘
    ↓
TradeEntity[] Array (stored in React state)
    ↓
Displayed in UI Components
```

---

## API Call Summary Table

| Endpoint | Method | Purpose | Called When | Response Time |
|----------|--------|---------|-------------|---|
| `/api/cord/search` | GET | Find entity in CORD | Queue load, search | 200-500ms |
| `/api/cord/resolve` | POST | Get 3-4 level chain | Queue load | 300-800ms |
| `/api/cord/entity/{id}/chain` | GET | Get entity chain | Entity selection (fallback) | 150-300ms |
| `/api/cord/entity/{id}/parties` | GET | Get supply chain parties | Entity selection (fallback) | 150-300ms |
| `/api/cord/entity/{id}` | GET | Get full entity details | Not currently used | 200-400ms |
| `/api/cord/why/{a}/{b}` | POST | Why are entities connected | Not currently used | 300-600ms |

---

## State Management (React)

```
useV2Entities Hook:
│
├─ entities: TradeEntity[]
│  └─ All entities in current queue
│     Populated by: loadCORDEntities() or searchEntities()
│
├─ selectedEntity: TradeEntity | null
│  └─ Currently selected entity for detail panel
│     Set by: selectEntity(entityId)
│
├─ loading: boolean
│  └─ True while API calls in progress
│     Used for: Loading spinners
│
└─ error: string | null
   └─ Error message if API call fails
      Used for: Error display
```

---

## Caching Strategy

**Current Implementation:**
- Queue entities are fetched once and cached in React state
- Entity details (chain, parties) are fetched on selection
- No explicit cache invalidation

**What Could Be Improved:**
- Cache entity lookups with TTL (5-10 min)
- Use React Query or SWR for automatic cache management
- Add manual refresh button for force-update

