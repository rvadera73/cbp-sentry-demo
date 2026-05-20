# Single Source of Truth: Architecture Decision

## Problem We Solved

**Before (Broken):**
```
Manifest JSON (1,191 records, IDs: SHP-000001)
    ↓ (shown in dashboard)
    ✓ User sees case "SHP-000001"
    ✓ Clicks to view it
    ↓
Database (5 hardcoded records, IDs: shipment-greenfield-001)
    ✓ API queries for "SHP-000001"
    ✗ Not found! → "case not found" error
```

**Root cause:** Two different data sources with incompatible IDs. The system was trying to maintain two separate datasets:
1. **Manifest JSON** — the "real" data (1,191 CBP cases)
2. **Hardcoded demo records** — emergency fallback data (5 sample shipments)

This created an impossible situation:
- If manifest JSON is used: database is empty, API returns 404
- If fallback data is used: dashboard shows wrong IDs, API can't find them

---

## Solution: Single Source of Truth

**After (Fixed):**
```
Manifest JSON (1,191 records, IDs: SHP-000001, etc.)
    ↓
    LOAD INTO DATABASE (once at startup)
    ↓
Database (1,191 records, IDs: SHP-000001, etc.)
    ↓
API queries DB
    ↓ (finds it!)
Dashboard shows results
```

**One data source**, one set of IDs, no confusion.

---

## Architecture Principle

| Aspect | Before (Wrong) | After (Right) |
|--------|---|---|
| **Data Sources** | 2 (JSON + hardcoded) | 1 (JSON only) |
| **Source of Truth** | Ambiguous | Manifest JSON |
| **Fallback Data** | 5 hardcoded shipments | None — fail loudly if JSON missing |
| **ID Format** | Inconsistent (SHP-* vs shipment-*) | Consistent (SHP-* from manifest) |
| **Startup** | Silent fallback if JSON missing | Fail with clear error if JSON missing |
| **Dashboard/API** | Query different sources | Query same database |

---

## How It Works Now

### 1. On Container Startup
```
services/data/main.py → seed_demo_data() function
    ↓
    Check if database empty
    ↓ Yes → look for manifest JSON
    ↓
    File exists? 
    ├─ Yes  → Load 1,191 records into database ✅
    └─ No   → Fail with clear error message 🛑
```

### 2. Dashboard
```
User opens http://localhost:3001
    ↓
DashboardPage queries /api/shipments
    ↓
API queries database
    ↓
Returns 1,191 records with IDs: SHP-000001, SHP-000002, ...
```

### 3. Case View
```
User clicks case "SHP-000001"
    ↓
CaseViewerPage calls /api/data/shipments/SHP-000001
    ↓
API queries database for SHP-000001
    ↓
Found! ✅ Returns full shipment details
```

---

## Why This Is Better

### Before
- **Data duplication:** Same data in two places (JSON + hardcoded)
- **Sync problems:** Change one, forget to update the other
- **ID confusion:** Dashboard shows SHP-*, database has shipment-*
- **Silent failures:** JSON missing? Quietly use wrong data
- **Hard to debug:** Which data is actually being used?

### After
- **Single source:** Manifest JSON is authoritative
- **No duplication:** Database is just an indexed copy
- **Consistent IDs:** Everything uses SHP-* from manifest
- **Loud failures:** Missing JSON = clear error, not silent fallback
- **Easy to debug:** Everything traces back to manifest JSON

---

## Manifest JSON Structure

The `services/data/seed_data/manifest_feb_march_2026_with_isf.json` file contains:
```json
[
  {
    "id": "SHP-000001",              ← Authoritative ID
    "manifest_id": "MNF-2026-001",
    "shipper_name": "...",
    "consignee_name": "...",
    "origin_country": "VN",
    "destination_country": "US",
    "hs_code": "7604.29",
    "declared_value_usd": 50000,
    "declared_weight_kg": 5000,
    "vessel_name": "...",
    "element_9": "CN",                ← ISF field
    "ais_stuffing_country": "CN",     ← AIS field
    "dwell_days": 11.2,               ← Vessel metric
    "risk_score": 91                  ← Pre-computed risk
  },
  ... 1,190 more records
]
```

All 1,191 records are loaded into the database as-is, preserving:
- Original ID (SHP-*)
- All manifest fields
- Risk scores (used for dashboard sorting)
- ISF and AIS fields (used for H2 scoring)

---

## Moving Forward

### Local Development
```bash
cp .env.local.template .env.local
bash scripts/unified-setup.sh local
```
→ Automatically loads manifest JSON into database ✅

### Staging/Production
```
GitHub Actions workflow
    ↓
    Loads manifest JSON from services/data/seed_data/
    ↓
    Creates database with 1,191 SHP-* IDs
    ↓
    Cloud Run service starts with full dataset
```

### If Manifest Changes
```
1. Update services/data/seed_data/manifest_feb_march_2026_with_isf.json
2. Delete local database: rm data/cbp_sentry.db
3. Rebuild: bash scripts/unified-setup.sh local
   → Automatically reloads new manifest data ✅
```

---

## Never Add Hardcoded Data Again

✅ **DO THIS:**
- Store all data in manifest JSON
- Load manifest JSON into database on startup
- Query the indexed database

❌ **DON'T DO THIS:**
- Hardcoded shipments in code
- Multiple data sources
- Fallback data as a "safety net"
- Different ID formats

The manifest JSON is the source of truth. Everything else is a derived index.
