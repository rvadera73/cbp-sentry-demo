# 7-Factor Risk Scoring Architecture — Corrected

## Problem Fixed ✗→✓

**Incorrect Pattern (What Was Done):**
```
API routes → directly import from services.data.db → SQLite
```
❌ Code duplication, breaks microservice architecture

**Correct Pattern (Now Fixed):**
```
API routes → HTTP PATCH to sentry-data:8005 → services.data.db → SQLite
```
✓ Clean microservice boundary, single source of database truth

---

## Architecture Overview

### Layer 1: Data Service (sentry-data:8005)
**File:** `services/data/main.py` + `services/data/db.py`

**Responsibilities:**
- SQLite CRUD operations (single source of truth for database)
- Exposes REST endpoints for all data operations
- Handles all migrations and schema management

**Key Endpoints:**
```
PATCH /shipments/{shipment_id}     ← Risk scoring calls this to persist results
GET  /shipments/{shipment_id}
POST /shipments                     ← Create new shipment
GET  /shipments                     ← List all shipments
POST /shipments/batch               ← Bulk operations
```

**Database File:**
```
/app/data/cbp_sentry.db (shared volume: sentry_data_volume)
```

### Layer 2: API Gateway (sentry-api:8000)
**File:** `api/main.py` + `api/services/risk_scoring/routes.py`

**Responsibilities:**
- Risk scoring logic (orchestration)
- Call ML models (Isolation Forest, LightGBM)
- Generate breakdown with 18 components

**Data Access Pattern:**
```python
# ✓ CORRECT: Call sentry-data via HTTP
async def calculate_full_risk_breakdown(shipment_id, shipment_data):
    engine = get_engine()
    breakdown = engine.score_shipment(shipment_data)
    
    # Persist via sentry-data microservice
    await update_shipment_in_data_service(shipment_id, {
        "calculated_risk_score": breakdown.final_score,
        "risk_score_breakdown": json.dumps(breakdown),
        "confidence_interval": "±2.5"
    })
    return breakdown.to_dict()

# ✗ WRONG: Direct import
# from services.data.db import update_shipment  ← NEVER DO THIS
```

**Endpoint:**
```
POST /api/score/full-breakdown/{shipment_id}
  → Calls sentry-data PATCH /shipments/{shipment_id}
```

### Layer 3: UI (sentry-ui:3001)
**Files:** React components in `ui/src/components/risk-scoring/`

**Call Chain:**
```
React Component
  ↓ (POST to /api/score/full-breakdown)
sentry-api:8000
  ↓ (PATCH /shipments/{id})
sentry-data:8005
  ↓ (SQLite write)
/app/data/cbp_sentry.db
```

---

## Data Flow: Risk Scoring Request

```
1. ModernCaseInvestigationPage.tsx
   POST http://localhost:8000/api/score/full-breakdown/SHP-123
   Body: {
     "shipment_id": "SHP-123",
     "shipper_name": "Test Shipper",
     "origin_country": "VN",
     ...
   }

2. api/services/risk_scoring/routes.py :: calculate_full_risk_breakdown()
   • Validate input
   • Load RiskScoringEngine (Isolation Forest + LightGBM)
   • Call engine.score_shipment(shipment_data)
   • Get breakdown: RiskScoreBreakdown (18 components)
   
3. Persist to database via sentry-data:
   PATCH http://sentry-data:8005/shipments/SHP-123
   Body: {
     "calculated_risk_score": 52.3,
     "risk_score_breakdown": "{...full breakdown JSON...}",
     "confidence_interval": "{\"lower\":49.8,\"upper\":54.8,\"text\":\"±2.5\"}"
   }

4. sentry-data:8005 :: services/data/main.py
   • Receive PATCH request
   • Validate ShipmentUpdate model
   • Call update_shipment(shipment_id, updates)
   
5. services/data/db.py :: update_shipment()
   • Open SQLite connection to /app/data/cbp_sentry.db
   • UPDATE shipments SET calculated_risk_score=52.3, ... WHERE id='SHP-123'
   • Return updated shipment
   
6. Response back to React component
   {
     "shipment_id": "SHP-123",
     "components": [...18 components...],
     "subtotal": 44.3,
     "final_score": 52.3,
     "confidence_interval": "±2.5"
   }
```

---

## Code Organization (Corrected)

```
cbp-sentry/
│
├── services/data/                  ← SINGLE SOURCE OF DB TRUTH
│   ├── main.py                     (FastAPI endpoints)
│   ├── db.py                       (SQLite operations + migrations)
│   ├── models.py                   (Pydantic models)
│   └── Dockerfile
│
├── api/                            ← API GATEWAY
│   ├── main.py                     (Route registration, only imports from api/services)
│   ├── core/
│   │   └── config.py               (Settings, env vars)
│   └── services/
│       ├── risk_scoring/
│       │   ├── routes.py           ✓ FIXED: Uses httpx to call sentry-data:8005
│       │   └── __init__.py
│       ├── scoring/                (Three-level: legacy, optional)
│       ├── ingest/
│       ├── entity_resolution/
│       └── ... (other services)
│
├── ui/                             ← FRONTEND
│   └── src/components/risk-scoring/
│       ├── RiskScoreBreakdown.tsx  (Calls POST /api/score/full-breakdown)
│       ├── types.ts
│       └── ... (other components)
```

### Key Rule
```
✓ api/services/risk_scoring/routes.py → HTTP to sentry-data:8005
✗ api/services/risk_scoring/routes.py → direct import from services.data.db
```

---

## Migrations: Who Owns What

**services/data/db.py:**
```python
migrations = [
    # Original tables
    "CREATE TABLE IF NOT EXISTS shipments (...)",
    "CREATE TABLE IF NOT EXISTS manifests (...)",
    
    # 7-Factor Risk Scoring columns (added via idempotent ALTER)
    "ALTER TABLE shipments ADD COLUMN calculated_risk_score REAL",
    "ALTER TABLE shipments ADD COLUMN risk_score_calculated_at TIMESTAMP",
    "ALTER TABLE shipments ADD COLUMN risk_score_breakdown TEXT",
    "ALTER TABLE shipments ADD COLUMN confidence_interval TEXT",
]
```

- **Only services/data/db.py** can modify the database schema
- **All API services** call sentry-data:8005 to access database
- **No direct imports** of db operations from api/services

---

## Testing the Fix

**Verify routes are using HTTP, not direct imports:**
```bash
grep "from services.data" /home/rahulvadera/cbp-sentry/api/services/risk_scoring/routes.py
# Should return: (nothing — no direct imports!)

grep "import update_shipment\|import get_shipment" /home/rahulvadera/cbp-sentry/api/services/risk_scoring/routes.py
# Should return: (nothing)

grep "httpx\|DATA_SERVICE_URL" /home/rahulvadera/cbp-sentry/api/services/risk_scoring/routes.py
# Should return: imports and usage of httpx, DATA_SERVICE_URL env var
```

**Manual test:**
```bash
# Start services
docker-compose up -d

# Call API
curl -X POST http://localhost:8000/api/score/full-breakdown/test-123 \
  -H "Content-Type: application/json" \
  -d '{
    "shipment_id": "test-123",
    "shipper_name": "Test",
    "shipper_country": "VN",
    "consignee_name": "Cons",
    "consignee_country": "US",
    "hs_code": "6204",
    "declared_value_usd": 50000,
    "declared_weight_kg": 100,
    "vessel_name": "TestVessel"
  }'

# Verify in database (via sentry-data)
curl http://localhost:8005/shipments/test-123
# Should show: calculated_risk_score, risk_score_breakdown, confidence_interval
```

---

## Summary of Fix

| Aspect | Before | After |
|--------|--------|-------|
| **DB Access** | Direct import from services.data.db | HTTP PATCH to sentry-data:8005 |
| **Code Duplication** | Multiple files importing db functions | Single source (services/data/db.py) |
| **Microservice Boundary** | Broken (API imports DB layer directly) | Clean (HTTP API boundary) |
| **Docker Compose** | Would work but violates architecture | Proper inter-container communication |
| **Testability** | Hard to test API in isolation | Easy to mock sentry-data responses |
| **Scalability** | Would require all services to have local db | Data service can be horizontal load-balanced |

**Status:** ✓ FIXED - Risk scoring now properly uses sentry-data microservice
