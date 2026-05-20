# Integration Status: External Services

Last Updated: 2026-05-19

## Current State Summary

| Service | Status | Location | Notes |
|---|---|---|---|
| **Senzing** | Partially ready | Docker service (optional profile) | Container defined, license required, not fully wired to API |
| **VesselAPI** | Fixture data only | services/api/external_apis/h2_adapters.py | Real API integration not implemented |
| **CORD RAG** | Local data loaded | Manifest JSON seeding | 1,191 records with ISF fields; RAG query endpoints not implemented |
| **OFAC SDN** | Fixture data only | services/api/external_apis/ofac_service.py | Real API integration not implemented |

---

## What's Implemented

### 1. Manifest JSON → Database Seeding ✅
**Status**: COMPLETE (May 19, 2026)

Manifest JSON at `services/data/seed_data/manifest_feb_march_2026_with_isf.json` is loaded into database on startup:
- **1,191 shipment records** with SHP-* IDs
- **ISF Element 9 fields**: `element_9`, `ais_stuffing_country`, `dwell_days`
- **Risk scores**: Pre-computed H1+H2 from manifest
- **Endpoint**: `GET /api/shipments` returns all 1,191 records

### 2. Three-Horizon Scoring Pipeline ✅
**Status**: COMPLETE (May 19, 2026)

- **H1 Corridor Risk (40pts)**: Implemented via `H1CorridorRiskScorer`
  - Origin-destination corridor detection
  - AD/CVD lookup (fixture data from `adcvd_hts_*.json`)
  - Shipper age analysis
  
- **H2 Vessel Anomaly (35pts)**: Implemented via `H2AnomalyScorer`
  - ISF Element 9 mismatch detection (using manifest fields directly)
  - AIS dwell time anomalies (using manifest `dwell_days` field)
  - Port call analysis
  
- **H3 Intelligence (25pts)**: Placeholder
  - Currently returns hardcoded value pending OFAC/watch-list integration

### 3. ISF Element 9 Detection ✅
**Status**: COMPLETE (May 19, 2026)

Direct from manifest JSON:
```python
element_9 = shipment.get("element_9") or shipment.get("ais_stuffing_country")
if element_9 and element_9 != origin_country:
    # ISF mismatch confidence = 0.95
```

Enables transshipment detection for high-risk corridors (CN→MY→US, CN→VN→US, etc.)

---

## What's NOT Fully Implemented

### 1. Senzing Entity Resolution ❌
**Current State**: Service defined but not wired to API

**What exists**:
- Docker service in `docker-compose.yml` (profile: `senzing`)
- Expected to listen on port 8250
- Requires `senzing/senzing.license` file (user must obtain from senzing.com)

**What's missing**:
- HTTP client to call Senzing REST API from services/api/main.py
- Entity loading script to populate Senzing with 1,191 shipment parties
- Why-explanation endpoints for entity relationships
- Integration with entity chain visualization in frontend

**To implement**:
1. Create `services/api/senzing_client.py`:
   ```python
   async def resolve_entities(manifest_id, shipment_id):
       """Call Senzing REST API to resolve shipper/consignee ownership chains."""
       resp = await httpx.get(f"{SENZING_URL}/data?...")
       return entities, confidence_scores
   ```

2. Add endpoint: `POST /api/entities/resolve`
   - Input: manifest_id, shipment_id
   - Output: entity graph with ownership chains, confidence scores

3. Wire into scoring: Use Senzing confidence as input to H1 entity risk score

**Effort**: ~3 hours for basic integration, +2 hours for why-explanation chain

---

### 2. VesselAPI (Real AIS Data) ❌
**Current State**: Fixture data only

**What exists**:
- `services/api/external_apis/h2_adapters.py` with `AISSampleAdapter`
- Returns fixture vessel data (dwell time, port calls) for hardcoded vessel names
- H2 anomaly scorer consumes this data

**What's missing**:
- Real VesselAPI integration (vesselapi.com, AISStream, etc.)
- Actual historical vessel tracking data
- Live port call information
- Cost: VesselAPI subscription required (~$500/month for production)

**To implement**:
1. Create `services/api/external_apis/vessel_live_adapter.py`:
   ```python
   async def fetch_vessel_ais(vessel_name: str, imo: str):
       """Fetch real AIS data from VesselAPI."""
       headers = {"Authorization": f"Bearer {VESSELAPI_KEY}"}
       resp = await httpx.get(f"https://api.vesselapi.com/ais/{imo}", headers=headers)
       return {
           "current_port": resp.json()["last_port"],
           "dwell_days": calculate_dwell(resp.json()["timestamps"]),
           "port_calls": [...]
       }
   ```

2. Update `config.py` API mode:
   - `API_MODE=fixture` → use hardcoded data (demo/testing)
   - `API_MODE=live` → call real VesselAPI (staging/production)

3. Add Dockerfile env var: `VESSELAPI_KEY` (from Secret Manager in Cloud Run)

**Effort**: ~2 hours to implement, +1 hour to test with real data

---

### 3. CORD RAG Entity Resolution ❌
**Current State**: Local CORD data in `/cord-data/` (244K entities), not queryable

**What exists**:
- 17 JSONL files in `/cord-data/` with structured entity records
- Fields: entity_id, entity_name, jurisdiction, entity_type, parent_entities, etc.
- Could be indexed for fast lookup

**What's missing**:
- Entity lookup endpoints (by name, jurisdiction, ID)
- Shipper/consignee lookup against CORD database
- Corporate registry matching (OFAC, OpenCorporates fallback)
- RAG (Retrieval-Augmented Generation) for open-ended queries

**To implement**:
1. Index CORD data:
   ```python
   # Load at startup
   cord_db = sqlite3.connect("/app/cord_entities.db")
   for jsonl_file in glob("/cord-data/*.jsonl"):
       for entity in load_jsonl(jsonl_file):
           insert_cord_entity(entity)  # indexed by name, jurisdiction
   ```

2. Add entity lookup endpoints:
   ```python
   GET /api/entities/search?name=greenfield&country=CN
   → Returns: entity_id, parent_entities, risk_indicators
   ```

3. Wire into scoring: Use CORD match confidence for entity ownership chain verification

**Effort**: ~4 hours for indexing + lookup, +2 hours for RAG query endpoint

---

### 4. OFAC SDN Live List ❌
**Current State**: Fixture data only

**What exists**:
- `services/api/external_apis/ofac_service.py` with hardcoded SDN records
- H3 scorer checks for hits

**What's missing**:
- Real Treasury OFAC SDN list (updated weekly)
- Fuzzy name matching against list
- Sanctions screening integration

**To implement**:
1. Create `services/api/external_apis/ofac_live_adapter.py`:
   ```python
   async def check_ofac(entity_name: str, country: str):
       """Query Treasury SDN list."""
       resp = await httpx.get(
           "https://www.treasury.gov/ofac/downloads/sdn.csv",
           headers={"timeout": 10}
       )
       return check_fuzzy_match(entity_name, sdn_list)
   ```

2. Update `ofac_service.py` to use live adapter in `API_MODE=live`

**Effort**: ~1.5 hours

---

## What Users See Today

### Dashboard (`/`)
- ✅ Case list with 1,191 shipments from manifest
- ✅ Risk scores (H1+H2 only, H3 hardcoded)
- ✅ Sort by risk, filter by status
- ❌ Senzing entity chains (hardcoded fixture responses)
- ❌ VesselAPI vessel tracking (fixture data)

### Case Detail (`/case/{id}`)
- ✅ H1 corridor analysis (from manifest corridor)
- ✅ H2 ISF mismatch detection (from manifest fields)
- ❌ Full entity ownership chain (needs Senzing)
- ❌ Live vessel AIS routing (needs VesselAPI)
- ❌ CORD entity matching (needs CORD lookup)
- ❌ OFAC hit confirmation (needs OFAC SDN)

---

## Implementation Priority

For **demonstration** (May 30 deadline):
1. **Senzing basics** (~3 hrs) — entity resolution sufficient for demo
2. Fix any remaining test failures

For **staging/production** (post-demo):
1. Senzing production setup (custom license)
2. VesselAPI subscription + integration
3. CORD indexing + search endpoints
4. OFAC live list feeds

For **future enhancement**:
1. OpenCorporates integration for shipper verification
2. Comtrade trade flow analysis
3. Satellite imagery for facility verification

---

## How to Enable Each Integration

### Senzing (Already in docker-compose, needs license)
```bash
# User action required:
1. Register at senzing.com/get-started
2. Download senzing.license
3. Place at senzing/senzing.license
4. Run: docker-compose --profile senzing up

# API will auto-detect and use Senzing at http://senzing:8250
```

### VesselAPI (Fixture now, live later)
```bash
# For local demo (fixture mode):
API_MODE=fixture docker-compose up
# → Uses hardcoded vessel data

# For staging (live mode):
API_MODE=live VESSELAPI_KEY=xxx docker-compose up
# → Requires VesselAPI subscription key
```

### CORD (Local indexing needed)
```bash
# Create indexed lookup:
python scripts/index_cord_data.py
# → Generates cord_entities.db from /cord-data/

# API will auto-detect and use local index
```

### OFAC (Fixture now, live list later)
```bash
# Download latest SDN list:
python scripts/update_ofac_sdn_list.py
# → Fetches from treasury.gov, caches locally

# API uses for fuzzy matching in H3 scorer
```

---

## Next Steps

**Phase 4 (Current)**: Cloud Run staging deployment
- Implement Senzing client and entity resolution endpoints
- Validate all three horizons with real data
- Test staging integration suite

**Phase 5**: Production readiness
- Enable live VesselAPI integration
- Enable live OFAC feeds
- Index and deploy CORD RAG
- Performance optimization

**Phase 6**: Enhancement
- OpenCorporates integration
- Comtrade trade flow analysis
- Satellite facility verification
