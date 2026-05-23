# CBP Sentry — System Architecture

**Version:** 2.0 | **Updated:** 2026-05-23 | **Audience:** Engineers, DevOps, Integration Partners

---

## 1. Overview

CBP Sentry is an AI-powered trade fraud detection system designed to identify transshipment and evasion schemes at the U.S. border. It combines:

- **Real-time manifest analysis** with ML risk scoring (7-factor model)
- **Entity resolution** via CORD 21M-entity database + Senzing SDK
- **External intelligence** from Altana Atlas, OFAC/SDN, AIS vessel tracking
- **Human-in-the-loop AI** generating officer narratives via Gemini Pro
- **CBP-compliant workflows** for investigation and DHS referral

**Core Purpose:** Reduce time-to-investigation from weeks to hours; reduce false positives via calibrated ML + human feedback loops.

**Deployment:** Docker Compose (local), Cloud Run + Cloud Storage (staging), PostgreSQL + Cloud Run (production).

---

## 2. Service Architecture

### Service Topology

```
┌─────────────────────────────────────────────────────────────────┐
│                     BROWSER (Web Client)                        │
│                      Port: 3001 (nginx)                         │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│            sentry-api (Primary API Gateway)                     │
│             FastAPI/uvicorn — Port 8000                         │
│  Health: GET /health                                            │
│  Dependencies: healthy sentry-data + sentry-cord-integration    │
└──────────┬──────────────────┬──────────────────────┬────────────┘
           │                  │                      │
    ┌──────▼────────┐  ┌──────▼────────┐   ┌────────▼──────┐
    │ sentry-data   │  │ sentry-cord   │   │   External    │
    │ Port 8005     │  │ integration   │   │   APIs        │
    │ SQLite DB     │  │ Port 8004     │   │               │
    │               │  │ CORD index    │   │ • Gemini Pro  │
    │ Health: /     │  │               │   │ • Altana      │
    │ health        │  │ Health: /     │   │ • OFAC/SDN    │
    │               │  │ health        │   │ • Vessel API  │
    └───────────────┘  └───────────────┘   │ • OpenCorp    │
                                            │ • Comtrade    │
                                            │ • ITC Tariffs │
                                            └───────────────┘
```

### Service Definitions

| Service | Port | Framework | Role | Database |
|---|---|---|---|---|
| **sentry-api** | 8000 | FastAPI + uvicorn | Request orchestration, risk scoring, Gemini integration, external API proxying | —(queries data service) |
| **sentry-data** | 8005 | FastAPI + uvicorn | CRUD operations, shipment persistence, seed data loading | SQLite 3 |
| **sentry-cord-integration** | 8004 | FastAPI + uvicorn | Entity resolution, CORD search, Senzing SDK wrapper, ownership chain tracing | CORD SQLite index (21M records) |
| **sentry-ui** | 3001 (prod) / 5173 (dev) | React 19 + Vite + nginx | Investigation workspace, case management, officer narrative, PDF export | — (queries sentry-api) |
| **senzing** (optional) | 8250 | Senzing API Server 3.5.2 | Advanced entity resolution sandbox; not used in production | Senzing repository |

### Health Checks

All services expose health check endpoints consumed by Docker Compose startup orchestration:

- **sentry-data:** `GET /health` → returns `{"status": "healthy", "records_in_db": <count>}`
- **sentry-api:** `GET /health` → returns `{"status": "healthy", "mode": "live", "dependencies": {...}}`
- **sentry-cord-integration:** `GET /health` → returns `{"status": "healthy", "entity_count": 21000000, "ready": true}`
- **sentry-ui:** `GET /` → nginx returns 200 + index.html

### Service Startup Dependencies

```
sentry-data
  ├─ Loads seed JSON → SQLite
  └─ Ready (no dependencies)

sentry-cord-integration
  ├─ Waits for sentry-data healthy
  ├─ Fetches shipments from data service
  ├─ Loads CORD SQLite index
  └─ Ready

sentry-api
  ├─ Waits for sentry-data healthy
  ├─ Waits for sentry-cord-integration healthy
  └─ Ready to accept requests

sentry-ui
  ├─ Waits for sentry-api healthy
  └─ Ready to serve browser traffic
```

---

## 3. Data Flow

### Request Lifecycle: Get a Shipment with Risk Breakdown

```
Browser (React)
  │
  └─► GET /api/data/shipments/SHP-001?include_breakdown=true
      │
      └─► sentry-api:8000/api/data/shipments/SHP-001?include_breakdown=true
          │
          ├─ [Lookup] GET http://sentry-data:8005/shipments/SHP-001
          │   └─ Returns raw manifest + H1/H2/H3 scores
          │
          ├─ [Enrich] POST internal _calculate_comprehensive_risk()
          │   ├─ Load 7-factor weights
          │   ├─ Fetch entity details from sentry-cord-integration:8004
          │   ├─ If risk_score ≥ 80: call Altana Atlas API
          │   └─ Return shipment + risk_breakdown object
          │
          └─ Returns to browser
              {
                "id": "SHP-001",
                "shipper_name": "...",
                "risk_score": 92,
                "risk_breakdown": {
                  "factors": [
                    {"name": "Documentation", "weight": 0.25, "score": 95, "rationale": "..."},
                    {"name": "Corridor", "weight": 0.20, "score": 85, ...},
                    ...
                  ],
                  "altana_validation": {...}
                }
              }
```

### Entity Resolution Flow

```
Officer searches for shipper "Guangzhou Trading Ltd"
  │
  └─► POST /api/cord/resolve
      │
      ├─ GET /search (name + country) → top 5 CORD matches
      │
      ├─ For each match: GET /entity/{id}
      │   └─ Extract entity_id, name, country, risk_level
      │
      ├─ FOR TOP MATCH: 3-level resolution chain
      │   ├─ Query Senzing: shipper → parent company → ultimate owner
      │   ├─ Check each level against OFAC/SDN list
      │   └─ Return [shipper, parent, owner] with sanctions status
      │
      └─ Returns to browser: TradeEntity[] with why_linked relationships
```

### External API Integration

| API | Service | Trigger | Use Case |
|---|---|---|---|
| **Google Gemini Pro** | sentry-api | User clicks "Generate Synopsis" or "Draft Referral" | AI-generated case narratives, chat assistance |
| **Altana Atlas** | sentry-api | risk_score ≥ 80 (automatic) | Supply chain opacity scoring, sanctions exposure |
| **OFAC/SDN List** | sentry-cord-integration | Entity resolution lookup | Sanctions screening, blocking at shipment level |
| **VesselFinder / AIS** | (future enhancement) | Vessel tracking | Port dwell anomalies, route verification |
| **OpenCorporates** | (pre-loaded H1 model) | Corridor risk calculation | Company registration, beneficial ownership |
| **Comtrade** | (pre-loaded H1 model) | Corridor risk calculation | Historical trade patterns, volume benchmarks |
| **ITC Tariffs** | (pre-loaded H1 model) | Commodity risk calculation | HS code duty rates, trade agreements |

---

## 4. Data Layer Architecture

### SQLite Database (sentry-data)

**Location:** `/app/data/cbp_sentry.db` (persistent volume in Docker Compose)

**Schema:**

#### Table: `shipments`
```
id (PRIMARY KEY)               TEXT      SHP-2026-00001
manifest_id                    TEXT
filing_date                    DATETIME
shipper_name                   TEXT
shipper_country                TEXT      2-letter country code
consignee_name                 TEXT
consignee_country              TEXT
hs_code                        TEXT      HS commodity code (6+ digits)
commodity_description          TEXT
declared_value_usd             FLOAT
declared_weight_kg             FLOAT
origin_country                 TEXT      True country of origin
destination_country            TEXT      US
vessel_name                    TEXT
vessel_flag                    TEXT      PA, LR, MH, etc.
vessel_imo                     TEXT
dwell_days                     FLOAT     Port dwell time
declared_origin                TEXT      ISF Element 9
ais_stuffing_country           TEXT      Actual stuffing (AIS data)
port_calls                     JSON      ["CN", "SG", "US"]
shipper_age_months             INT
importer_age_months            INT
ad_cvd_applicable              BOOLEAN
ad_cvd_rate                    FLOAT
ad_cvd_cases                   JSON      ["A-570-070"]
commodity_risk_level           TEXT      CRITICAL | HIGH | MEDIUM | LOW
corridor_risk                  FLOAT     0.0 - 1.0
corridor_label                 TEXT      "VN → USA"
risk_score                     FLOAT     0.0 - 100.0
status                         TEXT      FILED | HELD | EXAMINED | CLEARED
created_at                     DATETIME
updated_at                     DATETIME
element_9 (JSON)               JSON      {is_mismatch, actual_stuffing, dwell_anomaly...}
element9_risk_level            TEXT      HIGH | LOW
h1_score                       FLOAT     Corridor risk
h2_score                       FLOAT     AIS/Vessel risk
h3_score                       FLOAT     Manifest/Document risk
```

#### Table: `manifests`
```
id                             TEXT      MNF-2026-00001
filing_date                    DATETIME
source_file                    TEXT      filename.xlsx
row_count                      INT
status                         TEXT      INGESTED | PROCESSED | ERROR
created_at                     DATETIME
```

#### Table: `scores`
```
id                             TEXT
shipment_id                    TEXT
score_version                  TEXT      v2.1
score_timestamp                DATETIME
h1_score                       FLOAT
h2_score                       FLOAT
h3_score                       FLOAT
final_risk_score               FLOAT
breakdown_json                 JSON      7-factor breakdown
created_at                     DATETIME
```

### Seed Data Pipeline

On service startup (`sentry-data` entrypoint):

```python
async def startup():
  1. Initialize AsyncSession with SQLite engine
  2. Create all tables if not exist
  3. For each JSON file in seed_data/:
     a. Load manifest JSON (array of objects)
     b. For each record:
        - CREATE OR IGNORE shipment (prevents duplicates)
        - Ensure element_9 is parsed as JSON
        - Calculate H3 score if missing
  4. Commit transaction
  5. Return /health with record count
```

**Seed Files:**
- `seed_data/manifest_demo_cases.json` — 30 showcase cases (5 original + 25 new CRITICAL/HIGH/ELEVATED bands)
- `seed_data/legacy_archived.json` — (optional) historical data for testing

---

## 5. Risk Scoring Engine

### 7-Factor ML Model

```
Final Risk Score = (calibration_multiplier × weighted_factors) + altana_adjustment
Calibration Multiplier = 1.2x (post-score to match synthetic data distribution)
Altana Adjustment = +5 (if sanctions match) or -8 (if verified clean)
```

**Factor Breakdown:**

| Factor | Weight | Sub-factors | Description |
|---|---|---|---|
| **Documentation Risk** | 25% | Element 9 mismatch (50%), ISF amendments (30%), manifest completeness (20%) | ISF Element 9 (country of origin) vs AIS stuffing location; amendment frequency; missing fields |
| **Corridor Risk** | 20% | Route baseline scores | Pre-computed per corridor: CN→US (8.5), VN→US (7.0), MY→US (6.5), SG→US (5.0), CA→US (4.5) |
| **Commodity Risk** | 15% | Tariff rate (50%), export control (30%), UFLPA (20%) | Duty rate from ITC tariffs; EAR/ITAR status; forced labor indicators |
| **Routing Consistency** | 15% | AIS dwell anomaly (40%), port selection (30%), vessel flag (20%) | Port dwell vs baseline (e.g., >10 days flags); port selection logic; Panama-flagged vessels |
| **Party Profile Risk** | 15% | Shipper age (35%), prior violations (30%), OFAC/sanctions (20%), beneficial ownership opacity (15%) | Company registration age; enforcement history; OFAC SDN list match; opacity score |
| **Pattern Anomaly** | 10% | Pricing vs benchmark (50%), weight anomaly (25%), trade frequency (25%) | Price per kg deviation; declared weight variance; shipment frequency spikes |
| **Time Sensitivity** | 10% | Pre-tariff timing (50%), seasonal anomaly (50%) | Filings 30+ days before tariff changes; seasonal import pattern breaks |

### Three-Horizon Pipeline

```
INPUT: Manifest data (shipper, commodity, route, vessel, declared value)

┌─────────────────────────────────────────────────────────┐
│ Horizon 1 (H1): Corridor Risk                           │
│ ─────────────────────────────────────────────────────   │
│ Analyzes trade corridor patterns                        │
│ - Country pair, commodity, industry history             │
│ - Baseline risk (CN→US = 8.5 / 10)                      │
│ - Result: H1_score (0-100)                              │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│ Horizon 2 (H2): Pre-Intelligence Anomalies              │
│ ─────────────────────────────────────────────────────   │
│ Analyzes ISF filings + AIS vessel tracking              │
│ - Element 9 mismatch (declared vs actual stuffing)      │
│ - Port dwell anomalies                                  │
│ - Vessel flag / IMO history                             │
│ - Result: H2_score (0-100)                              │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│ Horizon 3 (H3): Manifest-Level Signals                  │
│ ─────────────────────────────────────────────────────   │
│ Analyzes shipper/consignee profiles + pricing           │
│ - Party age, prior violations, OFAC match               │
│ - Price anomaly (declared vs benchmark)                 │
│ - Weight anomaly                                        │
│ - Result: H3_score (0-100)                              │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│ FINAL: Comprehensive Risk Score                         │
│ ─────────────────────────────────────────────────────   │
│ Weighted formula: 0.25×H1 + 0.20×H2 + ... (7 factors)   │
│ Apply calibration: 1.2x multiplier                      │
│ Add Altana adjustment: ±5/8                             │
│ Constrain: 0-100 range                                  │
│ Result: risk_score (integer 0-100)                      │
│ Map to recommendation: HOLD / EXAMINE / CLEAR           │
└─────────────────────────────────────────────────────────┘
```

### Risk Score Interpretation

```
Risk Score Range        Recommendation        Color       Action
─────────────────────────────────────────────────────────────────
80 - 100               HOLD FOR EXAMINATION   Red         Automatic referral to DHS
50 - 79                EXAMINE                Amber       Officer discretion, further review
0 - 49                 CLEAR                  Green       Normal processing
```

### Calibration & Feedback Loop

- **Analyst feedback:** Officer accepts/rejects a score → stored in `scores.feedback_override` table
- **Weight recalibration:** Monthly job aggregates feedback → suggests weight adjustments
- **Recalibration endpoint:** POST `/api/weight-suggestions/{id}/approve` immediately applies new weights to all future scores
- **Audit trail:** All weight changes logged with timestamp, approval user, reason

---

## 6. Entity Resolution Architecture

### CORD Index (21M Records)

- **Source:** CORD database (public entity records from 195 countries)
- **Storage:** SQLite at `/app/data/cord_index.db` (sentry-cord-integration service)
- **Indexing:** Fuzzy match on company name + country code; exact match on LEI/tax ID
- **Usage:** `GET /search?name={query}&country={code}` returns top-K matches with confidence scores

### Senzing SDK Integration

The `SenzingSDKWrapper` class (mock of real Senzing SDK) implements:

- **Entity loading:** `add_record()` → add a company record to Senzing repository
- **Entity linking:** `search_by_attributes()` → find similar entities in repository
- **Relationship extraction:** `get_match_info()` → explain why two entities were linked
- **Ownership tracing:** 3-level chain — shipper → parent company → ultimate beneficial owner

### Resolution Chain (3 Levels)

```
INPUT: Shipper name, country

LEVEL 1 (Shipper):
  └─ Search CORD + Senzing for exact/fuzzy match
  └─ Return shipper entity_id, name, registration date, address

LEVEL 2 (Parent Company):
  └─ Query shipper's declared parent from corporate registry
  └─ Search CORD for parent entity
  └─ Return parent entity_id, name, country

LEVEL 3 (Ultimate Beneficial Owner):
  └─ Query parent's ownership structure
  └─ Trace to ultimate owner (non-shell entity with real operations)
  └─ Check against OFAC SDN list
  └─ Return owner entity_id, sanctions status

OUTPUT: [shipper, parent, owner] with confidence scores and why_linked explanations
```

### OFAC/SDN Screening

- **Trigger:** After 3-level resolution chain completes
- **Check:** Each entity (shipper, parent, owner) against OFAC SDN list (annual updates)
- **Result:** `sanctions_status` ∈ {None, Match Found, Under Investigation, Blocked list}
- **Action:** If `Blocked list`, reject shipment automatically (cannot be cleared by officer)

---

## 7. External Integrations

### Google Gemini Pro (AI Narratives)

- **Endpoint:** `POST /api/gemini/synopsis` — auto-generate case synopsis from shipment data
- **Endpoint:** `POST /api/gemini/draft-referral` — auto-draft DHS-compliant officer narrative
- **Prompt:** Structured, CBP-compliant formatting; includes Element 9, OFAC, commodity risk
- **Fallback:** Template-based narrative if API key missing or quota exceeded
- **Auth:** `GOOGLE_API_KEY` environment variable (Secret Manager in Cloud Run)

### Altana Atlas (Supply Chain Verification)

- **Trigger:** Automatic when risk_score ≥ 80 (CRITICAL band)
- **API Call:** POST `https://api.altanafinance.com/supply-chain-verification`
- **Input:** Shipper, consignee, commodity, route, declared value
- **Output:** Opacity score (0-100), sanctions exposure, capacity check, verification confidence
- **Action:** If Altana confirms risk, +5 adjustment; if verified clean, -8 adjustment
- **Auth:** `ALTANA_API_KEY` environment variable

### OFAC SDN List

- **Source:** OFAC .csv download (annual updates + dynamic feeds)
- **Refresh:** On sentry-cord-integration startup; daily refresh job (optional)
- **Check:** Shipper name, parent company, ultimate owner against SDN consolidated list
- **Result:** `sanctions_match` boolean + confidence score
- **Action:** If match found, set `ofac_flag: true` on shipment; DHS mandatory referral

### VesselFinder / AIS Data

- **Use:** Port dwell anomaly detection (H2 factor)
- **API:** VesselFinder or MarineTraffic AIS feed
- **Query:** Vessel IMO + port code → port call history, dwell times
- **Output:** Actual dwell vs baseline; port sequence verification
- **Current:** Hardcoded in manifest (future: live API integration)

### OpenCorporates / Comtrade / ITC (Pre-loaded Models)

These are not real-time API calls; they're baked into the H1 corridor risk model:

- **OpenCorporates:** Company registration age, beneficial ownership transparency scores
- **Comtrade:** Historical bilateral trade flows, tariff product codes, volume benchmarks
- **ITC Tariffs:** HS code duty rates, trade agreement preferences, anti-dumping cases

---

## 8. Security Architecture

### Authentication & Authorization

- **Auth Method:** JWT tokens (OAuth 2.0 with client credentials flow)
- **Roles:** `cbp_officer` (full workflow), `analyst` (tuning + calibration), `admin` (user management)
- **Route Guards:** All `/api/*` endpoints check JWT + role in middleware

### Data Protection

- **Encryption at Rest:** SQLite database file on encrypted volume (Docker named volumes + Cloud Storage)
- **Encryption in Transit:** HTTPS only (nginx termination on port 80 → 443 in production)
- **PII Handling:** No PII logged; sanitize error messages; mask entity names in logs

### External API Security

- **Secret Management:** All API keys stored in Secret Manager (Cloud Run), environment variables (local dev)
- **Rate Limiting:** Gemini API: 60 req/min (Google quota); Altana: 100 req/day (custom contract)
- **Timeout:** 30s default; 60s for Gemini (slow model)

---

## 9. Network & Communication

### Docker Compose Network

- **Network Name:** `sentry-network` (bridge)
- **Service Discovery:** Docker internal DNS — `sentry-api:8000` resolves from within containers
- **External Access:** Host port mapping (localhost:3001 for UI, localhost:8000 for API)

### Service-to-Service Communication

```
sentry-api → sentry-data
  Base URL: http://sentry-data:8005
  Example: GET http://sentry-data:8005/shipments/SHP-001

sentry-api → sentry-cord-integration
  Base URL: http://sentry-cord-integration:8004
  Example: POST http://sentry-cord-integration:8004/resolve

sentry-cord-integration → sentry-data
  Base URL: http://sentry-data:8005
  Usage: Fetch shipments for CBP augmentation on startup
```

### Cloud Run Network (Staging / Production)

Service-to-service calls are authenticated via Workload Identity:

```
sentry-api (Cloud Run)
  ├─ Calls sentry-data (Cloud Run)
  │  URL: https://sentry-data-{hash}.{region}.run.app
  │  Auth: Service account token (OIDC)
  │
  └─ Calls sentry-cord-integration (Cloud Run)
     URL: https://sentry-cord-integration-{hash}.{region}.run.app
     Auth: Service account token (OIDC)

Browser
  └─ Calls sentry-ui (Cloud Run, nginx reverse proxy)
     URL: https://sentry-ui-{hash}.{region}.run.app
     Reverse proxy routes /api/* to sentry-api Cloud Run service
```

---

## 10. Technology Stack Summary

| Layer | Technology | Version |
|---|---|---|
| **Frontend** | React + TypeScript | 19 + 5.6 |
| **Frontend Build** | Vite + npm | 5.4 + 10.x |
| **Frontend Styling** | Tailwind CSS + USWDS | 3.4 + 2.14 |
| **Frontend Charts** | Recharts | 2.15 |
| **Backend API** | FastAPI + uvicorn | 0.115 + 0.30 |
| **Backend Async** | asyncio + aiohttp | stdlib + 3.9 |
| **Database (Dev)** | SQLite 3 | 3.x |
| **Database (Prod)** | PostgreSQL | 15+ |
| **Entity DB** | CORD SQLite | 21M records |
| **Entity Resolution** | Senzing SDK | 3.x (mock) |
| **AI Models** | Google Gemini Pro | Latest |
| **Containerization** | Docker | 24+ |
| **Orchestration (Dev)** | Docker Compose | 2.20+ |
| **Orchestration (Prod)** | Cloud Run + Cloud Storage | Latest |
| **CI/CD** | Cloud Build + GitHub Actions | — |

---

## 11. Deployment Modes

### Local Development (`docker-compose.yml`)

All services in one network; SQLite persistent volume; optional Senzing profile.

### Cloud Run Staging (SQLite)

4 separate Cloud Run services; Cloud Storage FUSE bucket for `/app/data`; Workload Identity for service-to-service auth; Secret Manager for API keys.

### Cloud Run Production (PostgreSQL)

4 separate Cloud Run services; Cloud SQL PostgreSQL; Cloud VPC Connector for SQL connectivity; Secret Manager for all credentials.

---

## 12. Health & Observability

### Health Check Pattern

All services implement `GET /health`:

```json
{
  "status": "healthy",
  "timestamp": "2026-05-23T14:30:45Z",
  "version": "2.0",
  "dependencies": {
    "database": "connected",
    "cord_index": "loaded",
    "external_apis": "ready"
  }
}
```

### Logging

- **Format:** JSON (structured logs for log aggregation)
- **Level:** INFO (local), WARN (staging), ERROR (production)
- **Transport:** stdout (Docker logs) → Cloud Logging (Cloud Run)

### Metrics

- **Request latency:** Per-endpoint P50/P95/P99 in milliseconds
- **Risk scoring:** Avg score, distribution, Altana call count/latency
- **Entity resolution:** Search latency, match accuracy, OFAC hit rate
- **Uptime:** Service availability per endpoint

---

## Next Steps

For deployment instructions, see [`DEPLOYMENT.md`](DEPLOYMENT.md).

For UI/UX design and feature details, see [`DESIGN.md`](DESIGN.md).
