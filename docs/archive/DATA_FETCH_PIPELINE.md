# Entity Resolution Data Fetch Pipeline
## Complete API Call Sequence & Data Flow

---

## 1. INITIAL PAGE LOAD — Entity Queue Population

### Step 1.1: Load Sample Entities List (useV2Entities.ts - useEffect)
**File:** `/ui/src/v2/hooks/useV2Entities.ts` (Line 283)
**Trigger:** Component mounts → useEffect fires → calls `loadCORDEntities()`

```typescript
const SAMPLE_ENTITIES = [
  { name: 'Greenfield Industrial Trading Co.', country: 'VN' },
  { name: 'Guangdong Greenfield Aluminum Manufacturing', country: 'CN' },
  { name: 'Bangalore Electronics Trade Group', country: 'IN' },
  // ... more entities
];
```

**Flow:** Hard-coded in hook, no API call needed yet.

---

### Step 1.2: Search CORD for Each Sample Entity
**API Endpoint:** `GET /api/cord/search?name={name}&country={country}&limit=1`

**Called From:** `useV2Entities.ts` → `loadCORDEntities()` (Line 197)

**HTTP Request:**
```bash
GET /api/cord/search?name=Greenfield%20Industrial%20Trading%20Co.&country=VN&limit=1
Accept: application/json
```

**Response Structure:**
```json
{
  "matches": [
    {
      "record_id": "CORD-123456",
      "data_source": "GLEIF",
      "name": "Greenfield Industrial Trading Co., Ltd.",
      "country": "VN",
      "raw_json": {
        "RECORD_ID": "CORD-123456",
        "DATA_SOURCE": "GLEIF",
        "NAMES": [
          {
            "NAME_TYPE": "PRIMARY",
            "NAME_ORG": "Greenfield Industrial Trading Co., Ltd."
          }
        ],
        "COUNTRIES": [
          {
            "REGISTRATION_COUNTRY": "VN"
          }
        ],
        "OFAC_STATUS": "WATCH",
        "ADDRESS": "123 Trade Street, Ho Chi Minh City",
        // ... full CORD record
      }
    }
  ]
}
```

**Data Extracted:**
- `name` → entity_name
- `country` → country code
- `raw_json.OFAC_STATUS` → risk_level determination
- `record_id` → used for further lookups

**Code Location:** `useV2Entities.ts:197-202`
```typescript
const searchResp = await fetch(`/api/cord/search?name=${encodeURIComponent(sample.name)}&country=${encodeURIComponent(sample.country)}&limit=1`);
const searchData = await searchResp.json();
const match = searchData.matches?.[0];
```

---

### Step 1.3: Resolve 3-4 Level Supply Chain for Each Entity
**API Endpoint:** `POST /api/cord/resolve?shipper_name={name}&shipper_country={country}`

**Called From:** `useV2Entities.ts` → `resolveEntityChainFromCORD()` (Line 215)

**HTTP Request:**
```bash
POST /api/cord/resolve?shipper_name=Greenfield%20Industrial%20Trading%20Co.&shipper_country=VN
Content-Type: application/json
```

**Response Structure:**
```json
{
  "status": "success",
  "resolution": {
    "level_1": {
      "entity_id": "ENT-GF-VN-001",
      "name": "Greenfield Industrial Trading Co., Ltd.",
      "entity_type": "shipper",
      "country": "VN",
      "confidence": 0.98,
      "ofac_status": "WATCH"
    },
    "level_1_id": "ENT-GF-VN-001",
    
    "level_2": {
      "entity_id": "ENT-GF-HK-001",
      "name": "Greenfield Global Metals Holdings Ltd.",
      "entity_type": "holding_company",
      "country": "HK",
      "confidence": 0.95,
      "ofac_status": null
    },
    "level_2_relationship": {
      "relationship_type": "OWNED_BY",
      "confidence": 0.95
    },
    "level_2_id": "ENT-GF-HK-001",
    
    "level_3": {
      "entity_id": "ENT-GF-CN-001",
      "name": "Guangdong Greenfield Aluminum Mfg. Co., Ltd.",
      "entity_type": "manufacturer",
      "country": "CN",
      "confidence": 0.92,
      "ofac_status": null
    },
    "level_3_relationship": {
      "relationship_type": "PARENT_COMPANY",
      "confidence": 0.92
    },
    "level_3_id": "ENT-GF-CN-001"
  }
}
```

**Data Extracted & Transformed:**
```typescript
// Lines 218-259: Build entity_chain array
const chain = [];

if (resolution.level_1) {
  chain.push({
    entity_id: resolution.level_1.entity_id,
    name: resolution.level_1.name,
    country: resolution.level_1.country,
    entity_type: resolution.level_1.entity_type,
    role: 'Shipper/Direct Entity',
    confidence: 0.98,
    data_source: 'CORD'
  });
}

if (resolution.level_2) {
  chain.push({
    entity_id: resolution.level_2.entity_id,
    name: resolution.level_2.name,
    country: resolution.level_2.country,
    entity_type: resolution.level_2.entity_type,
    role: resolution.level_2_relationship.relationship_type,
    confidence: 0.95,
    relationships: [
      {
        type: 'OWNERSHIP_LINK',
        details: 'Greenfield Global is parent/owner',
        confidence: 0.95
      },
      {
        type: 'SHARED_INFRASTRUCTURE',
        details: 'Operates under common corporate structure',
        confidence: 0.85
      }
    ],
    data_source: 'CORD'
  });
}
// ... level_3 similar
```

**Code Location:** `useV2Entities.ts:88-163`

---

### Step 1.4: Map CORD Data to TradeEntity Format
**Called From:** `useV2Entities.ts` → `mapCordToTradeEntity()` (Line 149)

**Input Data:**
```typescript
{
  name: "Greenfield Industrial Trading Co., Ltd.",
  country: "VN",
  cordEntity: { // from CORD search response
    OFAC_STATUS: "WATCH",
    entity_type: "organization",
    // ...
  }
}
```

**Output (TradeEntity):**
```typescript
{
  entity_id: "greenfield-industrial-trading-co-vn",
  entity_type: "Manufacturer",
  entity_name: "Greenfield Industrial Trading Co., Ltd.",
  country: "VN",
  risk_level: "High",  // Determined from OFAC_STATUS: "WATCH"
  sanctions_status: "Under Investigation",
  known_affiliations: [],
  enforcement_history: "No enforcement actions recorded",
  ownership_indicators: "Data pending from beneficial ownership registry",
  registration_status: "Active",
  watchlist_status: "Flagged",
  address: "Address pending",
  tax_id: "Unverified",
  phone: "Contact pending",
  shared_identifiers: [],
  entity_chain: [ /* 3-4 level chain from step 1.3 */ ]
}
```

**Risk Level Logic:**
```typescript
let riskLevel = 'Low';
const ofacStatus = cordEntity?.raw_data?.OFAC_STATUS || cordEntity?.OFAC_STATUS;

if (ofacStatus === 'BLOCKED') {
  riskLevel = 'Critical';
  watchlistStatus = 'Flagged';
} else if (ofacStatus === 'WATCH') {
  riskLevel = 'High';
  watchlistStatus = 'Flagged';
} else if (ofacStatus === 'CLEAR') {
  riskLevel = 'Verified';
  watchlistStatus = 'Not Flagged';
} else {
  riskLevel = 'Low';
  watchlistStatus = 'Not Flagged';
}
```

**Code Location:** `useV2Entities.ts:47-104`

---

### Step 1.5: Display Entity Queue
**Component:** `V2EntitiesPage.tsx` (Line 84-125)

**Data Source:** From `useV2Entities()` hook:
```typescript
const { entities, selectedEntity, selectEntity, loading } = useV2Entities();
```

**Rendered In Table:**
```tsx
{sortedEntities.map((e) => (
  <tr key={e.entity_id}>
    <td>{e.entity_name} / {e.entity_id}</td>
    <td>{e.entity_type}</td>
    <td>{e.country}</td>
    <td>{e.tax_id || '—'}</td>
    <td>{e.watchlist_status}</td>
    <td>
      <button onClick={() => selectEntity(e.entity_id)}>
        WORKSPACE
      </button>
    </td>
  </tr>
))}
```

**Displayed Fields:**
- `entity_name` — From CORD search
- `entity_id` — Generated from name|country
- `entity_type` — From CORD
- `country` — From CORD
- `tax_id` — From CORD raw_json
- `watchlist_status` — Determined from OFAC status

---

## 2. ENTITY SELECTED — Workspace Detail Load

### Step 2.1: User Clicks "WORKSPACE" Button
**Event Handler:** `V2EntitiesPage.tsx:88` onClick
```tsx
onClick={() => {
  selectEntity(e.entity_id).catch(err => console.error('Error selecting entity:', err));
}}
```

**Entity ID Format:** `"greenfield-industrial-trading-co-vn"`

---

### Step 2.2: Fetch Entity Chain (if not already loaded)
**API Endpoint:** `GET /api/cord/entity/{entity_id}/chain`

**Called From:** `useV2Entities.ts` → `selectEntity()` (Line 270)

**HTTP Request:**
```bash
GET /api/cord/entity/greenfield-industrial-trading-co-vn/chain
Accept: application/json
```

**Response Structure:**
```json
{
  "status": "success",
  "chain": [
    {
      "entity_id": "ENT-GF-VN-001",
      "name": "Greenfield Industrial Trading Co., Ltd.",
      "country": "VN",
      "entity_type": "shipper",
      "role": "Shipper/Direct Entity",
      "confidence": 0.98,
      "data_source": "CORD",
      "relationships": []
    },
    {
      "entity_id": "ENT-GF-HK-001",
      "name": "Greenfield Global Metals Holdings Ltd.",
      "country": "HK",
      "entity_type": "holding_company",
      "role": "Parent/Owner",
      "confidence": 0.95,
      "data_source": "CORD",
      "relationships": [
        {
          "type": "OWNERSHIP_LINK",
          "target": "Greenfield Industrial Trading Co., Ltd.",
          "confidence": 0.95
        }
      ]
    }
  ]
}
```

**Data Extraction:**
```typescript
// useV2Entities.ts:270-280
const chainResponse = await fetch(`/api/cord/entity/${entityId}/chain`);
if (chainResponse.ok) {
  const chainData = await chainResponse.json();
  entityChain = chainData?.chain || chainData?.entity_chain || chainData?.data;
  if (!Array.isArray(entityChain)) {
    entityChain = undefined;
  }
}
```

**Note:** In current implementation, chain is already loaded during initial load in step 1.3, so this may not be needed. But code is there as fallback.

---

### Step 2.3: Fetch Entity Parties (Shipper, Consignee, Bank, etc.)
**API Endpoint:** `GET /api/cord/entity/{entity_id}/parties`

**Called From:** `useV2Entities.ts` → `selectEntity()` (Line 281-290)

**HTTP Request:**
```bash
GET /api/cord/entity/greenfield-industrial-trading-co-vn/parties
Accept: application/json
```

**Response Structure:**
```json
{
  "status": "success",
  "parties": [
    {
      "entity": "DHL Supply Chain Vietnam",
      "role": "Freight Forwarder",
      "country": "VN"
    },
    {
      "entity": "ICBC Vietnam Branch",
      "role": "Bank",
      "country": "VN"
    },
    {
      "entity": "Hung Yen Port Services",
      "role": "Port Authority",
      "country": "VN"
    }
  ]
}
```

**Data Extraction:**
```typescript
// useV2Entities.ts:281-290
const partiesResponse = await fetch(`/api/cord/entity/${entityId}/parties`);
if (partiesResponse.ok) {
  const partiesData = await partiesResponse.json();
  parties = partiesData?.parties || partiesData?.data;
  if (!Array.isArray(parties)) {
    parties = undefined;
  }
}
```

---

### Step 2.4: Merge into selectedEntity
**Code Location:** `useV2Entities.ts:310-320`

```typescript
const enrichedEntity: TradeEntity = {
  ...entity,  // Original entity from queue
  entity_chain: entityChain,  // From step 2.2
  parties: parties,  // From step 2.3
};

setSelectedEntity(enrichedEntity);
```

**State Update:** React re-renders detail panel with merged data.

---

## 3. DISPLAY ENTITY WORKSPACE — Data to UI

### Step 3.1: Render Entity Identity Header
**Component:** `V2EntitiesPage.tsx:149-160`

**Data Source:**
```typescript
selectedEntity = {
  entity_name: "Greenfield Industrial Trading Co., Ltd.",
  entity_id: "greenfield-industrial-trading-co-vn",
  watchlist_status: "Flagged",
  // ...
}
```

**Rendered As:**
```tsx
<div className="flex justify-between items-start">
  <div className="flex-1">
    <p className="text-xs font-bold text-[#0B1F33] uppercase">
      {selectedEntity.entity_name}
    </p>
    <p className="text-[9px] text-slate-600 mt-1">
      ID: {selectedEntity.entity_id}
    </p>
  </div>
  <span className={`px-2.5 py-1 rounded font-extrabold text-xs text-white ${
    selectedEntity.watchlist_status === 'Flagged' ? 'bg-[#D83933]' : 'bg-green-600'
  }`}>
    {selectedEntity.watchlist_status}
  </span>
</div>
```

**Output (on screen):**
```
Greenfield Industrial Trading Co., Ltd.          [Flagged]
ID: greenfield-industrial-trading-co-vn
```

---

### Step 3.2: Render Entity Details Grid (4 columns)
**Component:** `V2EntitiesPage.tsx:163-182`

**Data Source:**
```typescript
selectedEntity = {
  entity_type: "Manufacturer",
  country: "VN",
  tax_id: "Unverified",
  // ... (using hardcoded "CORD" for Source)
}
```

**Rendered As:**
```tsx
<div className="grid grid-cols-4 gap-3 text-[9px]">
  <div>
    <p className="text-slate-600 font-bold uppercase">Type</p>
    <p className="text-[#0B1F33] font-medium mt-0.5">
      {selectedEntity.entity_type}
    </p>
  </div>
  <div>
    <p className="text-slate-600 font-bold uppercase">Country</p>
    <p className="text-[#0B1F33] font-medium mt-0.5">
      {selectedEntity.country}
    </p>
  </div>
  <div>
    <p className="text-slate-600 font-bold uppercase">Tax ID</p>
    <p className="text-[#0B1F33] font-medium mt-0.5">
      {selectedEntity.tax_id || 'N/A'}
    </p>
  </div>
  <div>
    <p className="text-slate-600 font-bold uppercase">Source</p>
    <p className="text-[#0B1F33] font-medium mt-0.5">CORD</p>
  </div>
</div>
```

**Output (on screen):**
```
TYPE          COUNTRY       TAX ID         SOURCE
Manufacturer  VN            Unverified     CORD
```

---

### Step 3.3: Render Entity Relationship Chain (3-4 Levels)
**Component:** `V2EntitiesPage.tsx:185-239`

**Data Source:**
```typescript
selectedEntity.entity_chain = [
  {
    level: 1,
    name: "Greenfield Industrial Trading Co., Ltd.",
    country: "VN",
    role: "Shipper/Direct Entity",
    confidence: 0.98,
    relationships: []
  },
  {
    level: 2,
    name: "Greenfield Global Metals Holdings Ltd.",
    country: "HK",
    role: "Parent/Owner",
    confidence: 0.95,
    relationships: [
      {
        type: "OWNERSHIP_LINK",
        details: "Greenfield Global is parent/owner",
        confidence: 0.95
      },
      {
        type: "SHARED_INFRASTRUCTURE",
        details: "Operates under common corporate structure",
        confidence: 0.85
      }
    ]
  },
  {
    level: 3,
    name: "Guangdong Greenfield Aluminum Mfg. Co., Ltd.",
    country: "CN",
    role: "Ultimate manufacturer",
    confidence: 0.92,
    relationships: [
      {
        type: "PARENT_MANUFACTURER",
        details: "Ultimate manufacturer/beneficial owner",
        confidence: 0.9
      }
    ]
  }
]
```

**Rendered As Loop (Lines 207-232):**
```tsx
{selectedEntity.entity_chain.slice(0, 4).map((entity: any, idx: number) => (
  <div key={idx} className="p-3 bg-white border border-slate-200 rounded">
    {/* Entity Header */}
    <div className="flex items-start justify-between mb-2">
      <div className="flex-1">
        <p className="font-bold text-[9px] text-[#0B1F33]">
          {entity.name}
        </p>
        <p className="text-[8px] text-slate-500 mt-0.5">
          {entity.country} • {entity.role} • Confidence: {entity.confidence.toFixed(2)}
        </p>
      </div>
      <span className={`px-2 py-0.5 rounded text-[7px] font-bold whitespace-nowrap ml-2 ${
        idx === 0 ? 'bg-blue-100 text-blue-700' : 'bg-amber-100 text-amber-700'
      }`}>
        LEVEL {idx + 1} {idx === 0 ? '(DIRECT)' : ''}
      </span>
    </div>

    {/* Why Connected Evidence */}
    {entity.relationships && entity.relationships.length > 0 && (
      <div className="mt-2 pt-2 border-t border-slate-200">
        <p className="text-[7px] font-bold text-slate-600 uppercase mb-1">
          WHY CONNECTED:
        </p>
        {entity.relationships.map((rel: any, ridx: number) => (
          <div key={ridx} className="text-[8px] text-slate-700 mb-1 flex items-start">
            <span className="text-amber-600 font-bold mr-1">•</span>
            <span>{rel.type}: {rel.details}</span>
          </div>
        ))}
      </div>
    )}

    {/* Connector Arrow */}
    {idx < selectedEntity.entity_chain.length - 1 && (
      <div className="mt-2 text-center text-slate-400 text-[10px] font-bold">
        ↓
      </div>
    )}
  </div>
))}
```

**Output (on screen):**
```
┌─────────────────────────────────────────────────────────────┐
│ Greenfield Industrial Trading Co., Ltd.           [LEVEL 1] │
│ VN • Shipper/Direct Entity • Confidence: 0.98    (DIRECT)   │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Greenfield Global Metals Holdings Ltd.            [LEVEL 2] │
│ HK • Parent/Owner • Confidence: 0.95                        │
│                                                             │
│ WHY CONNECTED:                                              │
│ • OWNERSHIP_LINK: Greenfield Global is parent/owner        │
│ • SHARED_INFRASTRUCTURE: Common corporate structure        │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Guangdong Greenfield Aluminum Mfg. Co., Ltd.     [LEVEL 3] │
│ CN • Ultimate manufacturer • Confidence: 0.92              │
│                                                             │
│ WHY CONNECTED:                                              │
│ • PARENT_MANUFACTURER: Ultimate manufacturer/owner         │
└─────────────────────────────────────────────────────────────┘
```

---

### Step 3.4: Render Risk Assessment (for Critical/High Risk)
**Component:** `V2EntitiesPage.tsx:241-257`

**Data Source:**
```typescript
selectedEntity = {
  risk_level: "High",  // From OFAC status
  watchlist_status: "Flagged"
}
```

**Condition Check:**
```typescript
{(selectedEntity.risk_level === 'Critical' || selectedEntity.watchlist_status === 'Flagged') && (
  <div className={`${DESIGN.bgWhite} border border-[#D83933] rounded-sm p-4`}>
    <h3 className="text-xs font-bold text-[#D83933] uppercase mb-3">
      ⚠️ RISK ASSESSMENT
    </h3>
    {selectedEntity.risk_level === 'Critical' && (
      <div className="p-2 bg-red-50 border border-red-200 rounded">
        <p className="font-bold text-red-700">
          🚩 OFAC SDN MATCH - CRITICAL
        </p>
        <p className="text-red-600 mt-0.5">
          Entity is on OFAC Specially Designated Nationals List
        </p>
      </div>
    )}
    {selectedEntity.risk_level === 'High' && (
      <div className="p-2 bg-orange-50 border border-orange-200 rounded">
        <p className="font-bold text-orange-700">
          ⚠️ SANCTIONS WATCH LIST - HIGH RISK
        </p>
        <p className="text-orange-600 mt-0.5">
          Entity is under sanctions monitoring
        </p>
      </div>
    )}
  </div>
)}
```

**Output (on screen) - if risk_level = 'High':**
```
⚠️ RISK ASSESSMENT

┌─────────────────────────────────────────────────┐
│ ⚠️ SANCTIONS WATCH LIST - HIGH RISK              │
│ Entity is under sanctions monitoring             │
└─────────────────────────────────────────────────┘
```

---

### Step 3.5: Render Supply Chain Parties Table (if available)
**Component:** `V2EntitiesPage.tsx:258-282`

**Data Source:**
```typescript
selectedEntity.parties = [
  {
    entity: "DHL Supply Chain Vietnam",
    role: "Freight Forwarder",
    country: "VN"
  },
  {
    entity: "ICBC Vietnam Branch",
    role: "Bank",
    country: "VN"
  }
]
```

**Rendered As:**
```tsx
{selectedEntity.parties && selectedEntity.parties.length > 0 && (
  <section>
    <h3 className={`text-xs font-bold text-[#5C5C5C] uppercase mb-3 tracking-wider`}>
      Supply Chain Parties
    </h3>
    <div className={`overflow-x-auto border ${DESIGN.borderColor} rounded`}>
      <table className="w-full text-left text-[9px]">
        <thead className="bg-[#F0F4F8] border-b border-[#D0D7DE]">
          <tr>
            <th className="p-2 font-bold text-[#0B1F33]">ROLE</th>
            <th className="p-2 font-bold text-[#0B1F33]">ENTITY</th>
            <th className="p-2 font-bold text-[#0B1F33]">COUNTRY</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-[#E0E3E8]">
          {selectedEntity.parties.slice(0, 5).map((party, idx) => (
            <tr key={idx} className="hover:bg-[#F7F9FC]">
              <td className="p-2 font-bold text-[#0B1F33]">{party.role}</td>
              <td className="p-2 text-[#0B1F33]">{party.entity}</td>
              <td className="p-2 font-mono text-[#5C5C5C]">{party.country}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  </section>
)}
```

**Output (on screen):**
```
Supply Chain Parties

ROLE                 ENTITY                      COUNTRY
Freight Forwarder    DHL Supply Chain Vietnam    VN
Bank                 ICBC Vietnam Branch         VN
```

---

## 4. BACKEND API IMPLEMENTATION

### Backend Stack
- **Framework:** FastAPI (Python)
- **CORD Service:** Separate microservice at port 8004
- **Data Storage:** SQLite FTS5 index (244K CORD entities)

### API Gateway (Port 8000)
**File:** `/services/api/main.py`

#### Endpoint: GET /api/cord/search
**Lines:** 3444-3468

```python
@app.get("/api/cord/search")
async def cord_search(
    name: str = Query(...),
    country: Optional[str] = Query(None),
    limit: int = Query(10)
) -> Dict[str, Any]:
    """Search CORD FTS index by name + country."""
    try:
        async with await get_cord_service_client() as client:
            params = {"name": name, "limit": limit}
            if country:
                params["country"] = country
            
            resp = await client.get("/search", params=params)
            if resp.status_code == 200:
                return {"status": "success", "matches": resp.json()}
            else:
                return {"status": "error", "matches": []}
    except Exception as e:
        logger.error(f"CORD search error: {e}")
        return {"status": "error", "matches": []}
```

**Data Flow:**
1. UI calls `/api/cord/search?name=...&country=...`
2. API gateway proxies to CORD microservice at `http://sentry-cord-integration:8004`
3. CORD service queries SQLite FTS5 index
4. Returns matching records with raw JSON
5. API gateway returns results to UI

#### Endpoint: POST /api/cord/resolve
**Lines:** 3469-3495

```python
@app.post("/api/cord/resolve")
async def cord_resolve(
    shipper_name: str = Query(...),
    shipper_country: Optional[str] = Query(None),
    consignee_name: Optional[str] = Query(None),
    consignee_country: Optional[str] = Query(None),
) -> Dict[str, Any]:
    """Resolve 3-level supply chain for shipper."""
    try:
        async with await get_cord_service_client() as client:
            payload = {
                "shipper_name": shipper_name,
                "shipper_country": shipper_country,
                "consignee_name": consignee_name,
                "consignee_country": consignee_country,
            }
            
            resp = await client.post("/resolve", json=payload)
            if resp.status_code == 200:
                return {"status": "success", "resolution": resp.json()}
            raise HTTPException(status_code=resp.status_code)
    except Exception as e:
        logger.error(f"CORD resolve error: {e}")
        raise HTTPException(status_code=503)
```

**Data Flow:**
1. UI calls `/api/cord/resolve?shipper_name=...&shipper_country=...`
2. API gateway proxies to CORD microservice
3. CORD service runs entity resolution algorithm (3-level)
4. Returns chain with confidence scores
5. API gateway returns to UI

#### Endpoint: GET /api/cord/entity/{entity_id}/chain
**Lines:** 3520-3540

```python
@app.get("/api/cord/entity/{entity_id}/chain")
async def cord_get_entity_chain(entity_id: str) -> Dict[str, Any]:
    """Get entity relationship chain from CORD."""
    try:
        async with await get_cord_service_client() as client:
            resp = await client.get(f"/entity/{entity_id}/chain")
            if resp.status_code == 200:
                return {"status": "success", "chain": resp.json()}
            elif resp.status_code == 404:
                return {"status": "success", "chain": []}
            else:
                logger.warning(f"CORD returned {resp.status_code}")
                return {"status": "success", "chain": []}
    except Exception as e:
        logger.warning(f"CORD chain error: {e}")
        return {"status": "success", "chain": []}
```

**Data Flow:**
1. UI calls `/api/cord/entity/{id}/chain`
2. API proxies to CORD microservice
3. CORD returns entity's relationship chain
4. API returns to UI

#### Endpoint: GET /api/cord/entity/{entity_id}/parties
**Lines:** 3542-3562

```python
@app.get("/api/cord/entity/{entity_id}/parties")
async def cord_get_entity_parties(entity_id: str) -> Dict[str, Any]:
    """Get supply chain parties from CORD."""
    try:
        async with await get_cord_service_client() as client:
            resp = await client.get(f"/entity/{entity_id}/parties")
            if resp.status_code == 200:
                return {"status": "success", "parties": resp.json()}
            elif resp.status_code == 404:
                return {"status": "success", "parties": []}
            else:
                logger.warning(f"CORD returned {resp.status_code}")
                return {"status": "success", "parties": []}
    except Exception as e:
        logger.warning(f"CORD parties error: {e}")
        return {"status": "success", "parties": []}
```

---

### CORD Microservice (Port 8004)
**File:** `/services/cord-integration/main.py` (separate service)

**Endpoints:**
- `GET /search` — Search CORD FTS index
- `POST /resolve` — Resolve 3-level chain
- `GET /entity/{id}/chain` — Get entity chain
- `GET /entity/{id}/parties` — Get parties
- `GET /entity/{id}` — Get full entity
- `POST /why/{id_a}/{id_b}` — Why connected

**Data Source:**
- SQLite FTS5 index at `/app/data/cord_index.db`
- 244K CORD entities indexed
- Sources: GLEIF (Legal Entity Identifiers), OFAC (Sanctions)

---

## 5. DATA FLOW DIAGRAM

```
USER INTERACTION
    ↓
┌─────────────────────────────────────────────────────────────┐
│  React Component: V2EntitiesPage.tsx                         │
│  - Displays entity queue & workspace                         │
│  - Handles clicks, state updates                             │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│  Custom Hook: useV2Entities.ts                              │
│  - loadCORDEntities() → Load initial queue                  │
│  - resolveEntityChainFromCORD() → Fetch 3-4 level chain    │
│  - selectEntity() → Load detail data                        │
│  - mapCordToTradeEntity() → Transform CORD → TradeEntity   │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│  API Client Fetch Calls                                     │
│  - GET /api/cord/search                                     │
│  - POST /api/cord/resolve                                   │
│  - GET /api/cord/entity/{id}/chain                          │
│  - GET /api/cord/entity/{id}/parties                        │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│  API Gateway (Port 8000) - main.py                          │
│  - Receives HTTP requests                                   │
│  - Validates parameters                                     │
│  - Proxies to CORD service                                  │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│  CORD Microservice (Port 8004)                              │
│  - Queries SQLite FTS5 index                                │
│  - Runs entity resolution algorithm                         │
│  - Returns structured JSON                                  │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│  SQLite Database: cord_index.db                             │
│  - 244K CORD entities                                       │
│  - FTS5 full-text index on names                            │
│  - OFAC SDN table for sanctions lookup                      │
└─────────────────────────────────────────────────────────────┘
```

---

## 6. SAMPLE REQUEST/RESPONSE TRACE

### Request 1: Search Entity
```bash
curl -X GET "http://localhost:8000/api/cord/search?name=Greenfield&country=VN&limit=1"
```

**Response (200 OK):**
```json
{
  "status": "success",
  "matches": [
    {
      "record_id": "CORD-VN-123456",
      "data_source": "GLEIF",
      "name": "Greenfield Industrial Trading Co., Ltd.",
      "country": "VN",
      "raw_json": {
        "RECORD_ID": "CORD-VN-123456",
        "DATA_SOURCE": "GLEIF",
        "NAMES": [{"NAME_TYPE": "PRIMARY", "NAME_ORG": "Greenfield..."}],
        "OFAC_STATUS": "WATCH",
        "ADDRESSES": [{"ADDR_FULL": "123 Trade Street..."}],
        ...full entity record...
      }
    }
  ]
}
```

**Time:** ~200-500ms

---

### Request 2: Resolve Chain
```bash
curl -X POST "http://localhost:8000/api/cord/resolve?shipper_name=Greenfield%20Industrial%20Trading%20Co.&shipper_country=VN"
```

**Response (200 OK):**
```json
{
  "status": "success",
  "resolution": {
    "level_1": {
      "entity_id": "ENT-GF-VN-001",
      "name": "Greenfield Industrial Trading Co., Ltd.",
      "confidence": 0.98,
      "ofac_status": "WATCH"
    },
    "level_1_id": "ENT-GF-VN-001",
    "level_2": {
      "entity_id": "ENT-GF-HK-001",
      "name": "Greenfield Global Metals Holdings Ltd.",
      "confidence": 0.95
    },
    "level_2_relationship": {
      "relationship_type": "OWNED_BY",
      "confidence": 0.95
    },
    "level_2_id": "ENT-GF-HK-001",
    "level_3": {
      "entity_id": "ENT-GF-CN-001",
      "name": "Guangdong Greenfield Aluminum Mfg. Co., Ltd.",
      "confidence": 0.92
    },
    "level_3_relationship": {
      "relationship_type": "PARENT_COMPANY",
      "confidence": 0.92
    },
    "level_3_id": "ENT-GF-CN-001"
  }
}
```

**Time:** ~300-800ms (entity resolution can be slower)

---

### Request 3: Get Entity Parties
```bash
curl -X GET "http://localhost:8000/api/cord/entity/ENT-GF-VN-001/parties"
```

**Response (200 OK):**
```json
{
  "status": "success",
  "parties": [
    {
      "entity": "DHL Supply Chain Vietnam",
      "role": "Freight Forwarder",
      "country": "VN"
    },
    {
      "entity": "ICBC Vietnam Branch",
      "role": "Bank",
      "country": "VN"
    }
  ]
}
```

**Time:** ~150-300ms

---

## 7. PERFORMANCE METRICS

### Initial Page Load
```
Task 1: Load entity queue (6 entities)
  - Search CORD x6: 6 × 300ms = 1,800ms
  - Resolve chain x6: 6 × 500ms = 3,000ms
  - Total sequential: 4,800ms (done in parallel batches)
  - Actual with batching: ~2,000ms
  
Task 2: Render queue
  - React render: ~50ms

Total Initial Load: ~2-3 seconds
```

### Entity Selection
```
Task 1: Fetch chain (if not cached): 300ms
Task 2: Fetch parties: 200ms
Task 3: Render detail panel: 50ms

Total: ~600ms
```

### Search (User types in search box)
```
Task 1: Search CORD: 300-500ms
Task 2: Resolve chains for results: 300-800ms per result
Task 3: Render results: 50ms

Total: ~1-2 seconds (depending on result count)
```

---

## 8. CURRENT LIMITATIONS & FUTURE ENHANCEMENTS

### What's Currently Fetched:
✅ Entity search results (name, country, OFAC status)
✅ 3-level relationship chain (via /resolve)
✅ Entity confidence scores
✅ OFAC status (BLOCKED, WATCH, CLEAR)
✅ Supply chain parties

### What Could Be Added:
🔲 Why-connected evidence (API exists but not called)
🔲 Prior CBP enforcement filings
🔲 Incorporation date & entity details
🔲 Alternative names (AKA)
🔲 Sanctions programs (SDN program type)
🔲 Beneficial owner chains (4+ levels)
🔲 Network graph visualization

### Required API Calls for Enhancements:
```typescript
// Why-connected evidence
GET /api/entities/why/{entity_a}/{entity_b}

// Prior enforcement filings
GET /api/entities/{entity_id}

// OFAC program details
GET /api/cord/entity/{entity_id}  (extract program field)

// Full chain with beneficial owner
POST /api/cord/resolve (with more parameters)
```

---

## 9. DEBUG LOGGING

### Console Logs to Monitor:
```
[Entity Resolution] Loading CORD entities...
[Entity Resolution] Resolved entity: {name}
[Entity Resolution] Search found X entities
[Entity Resolution] Fetching chain data...
[Entity Resolution] Chain response status: 200
[Entity Resolution] Raw chain data: {...}
[Entity Resolution] Extracted chain (isArray=true): [...]
[Entity Resolution] Setting selected entity
[CORD] Resolved {name}: OFAC: {status}
[Map] Entity: {name}, OFAC: {status}
```

### Check in Browser:
1. Open DevTools (F12)
2. Go to Console tab
3. Filter for `[Entity Resolution]` or `[CORD]` or `[Map]`
4. Look at Network tab to see actual API calls
5. Click on request → Response to see raw JSON

