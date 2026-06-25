# CBP Sentry — System Architecture

**Version:** 2.2 | **Updated:** 2026-06-24 | **Audience:** Engineers, DevOps, Integration Partners

---

## 1. Overview

CBP Sentry is an AI-powered trade fraud detection system designed to identify transshipment and evasion schemes at the U.S. border. It combines:

- **7-factor risk scoring** — 60% XGBoost + 40% rule engine blend; AUC 0.940 on held-out synthetic data
- **MLOps lifecycle** — `cbp-risk-engine` MCP service (port 8010): model versioning, training, drift detection, officer feedback
- **Entity resolution** via CORD 243K-entity database + Senzing SDK (GLEIF, ICIJ Panama/Pandora, OFAC, OpenSanctions)
- **External intelligence** from VesselFinder AIS, OFAC/SDN, OpenCorporates, UN Comtrade, Federal Register
- **Human-in-the-loop AI** generating officer EAPA referral narratives via Gemini Pro
- **CBP-compliant workflows** for investigation workspace and DHS referral packages

**Core Purpose:** Reduce time-to-investigation from weeks to hours; surface EAPA cases with deterministic
rules + ML scoring; improve model accuracy through closed-loop officer feedback.

**Deployment:** Docker Compose (local). See `docs/DEPLOYMENT.md`.

**Current Maturity (June 24, 2026):** ~15% — XGBoost + rule engine operational on synthetic data;
4 of 7 scoring factors non-zero; score write-back and real reference data pipelines in progress.

### Model Maturity Levels

| Level | Description | Key Gate | ETA |
|-------|-------------|----------|-----|
| **15%** | Deterministic rules + XGBoost on real reference data | In progress | Jun 2026 |
| **30%** | LightGBM on ≥200 Gate 1 outcomes + real EAPA cases | gate1_outcomes ≥ 200 | TBD |
| **50%** | Full ensemble (XGBoost+LGBM+IF) + BBN uncertainty | gate1_outcomes ≥ 500 | TBD |
| **70%** | RL closed-loop retraining, weekly calibration | gate1_outcomes ≥ 1000 | TBD |
| **90%** | 90% PPV @ 5+ referrals/day — SOW end-state | ACE real-time ISF | TBD |

---

## 2. Service Architecture

### Service Topology

```
┌─────────────────────────────────────────────────────────────────┐
│                     BROWSER (Web Client)                        │
│                      Port: 3001 (nginx)                         │
└──────────────────────────┬──────────────────────────────────────┘
                           │  /api/*
┌──────────────────────────▼──────────────────────────────────────┐
│            sentry-api (Primary API Gateway)                     │
│             FastAPI/uvicorn — Port 8000                         │
│  Health: GET /health                                            │
│  Scoring: risk_scoring_engine.py (XGBoost 60% + rules 40%)     │
└───┬──────────────────┬──────────────────┬────────────────┬──────┘
    │                  │                  │                │
┌───▼────────┐  ┌──────▼────────┐  ┌──────▼──────────┐  ┌▼───────────────────┐
│sentry-data │  │sentry-cord    │  │cbp-risk-engine  │  │External APIs       │
│Port 8005   │  │integration    │  │Port 8010        │  │                    │
│SQLite DB   │  │Port 8004      │  │MLOps MCP Svc    │  │• Gemini Pro        │
│1396 ships. │  │243K entities  │  │XGBoost+LGBM     │  │• VesselFinder AIS  │
│limit 5000  │  │GLEIF,ICIJ,    │  │MLflow registry  │  │• OpenCorporates    │
│            │  │OFAC,OpenSanct │  │/api/predict     │  │• UN Comtrade       │
│            │  │NOTE: SE Asia  │  │/api/train       │  │• Federal Register  │
│            │  │coverage sparse│  │/api/models      │  │• USITC             │
│            │  │               │  │/api/metrics     │  │• Altana (disabled) │
└────────────┘  └───────────────┘  │/api/feedback    │  └────────────────────┘
                                    └─────────────────┘

DEPRECATED (pending removal):
  precise-risk-engine (Port 8007) — redundant with cbp-risk-engine, to be removed
```

### Service Definitions

| Service | Port | Framework | Role | Database |
|---|---|---|---|---|
| **sentry-api** | 8000 | FastAPI + uvicorn | Request orchestration, risk scoring (XGBoost + rule engine blend), Gemini integration, external API proxying | —(queries data service) |
| **sentry-data** | 8005 | FastAPI + uvicorn | CRUD operations, shipment persistence, seed data loading. Limit: 5000/page | SQLite 3 (cbp_sentry.db, 1396 shipments) |
| **sentry-cord-integration** | 8004 | FastAPI + uvicorn | Entity resolution, CORD search, Senzing SDK wrapper, ownership chain tracing | CORD SQLite (243K records: GLEIF, ICIJ, OFAC, OpenSanctions) |
| **cbp-risk-engine** | 8010 | FastAPI + uvicorn | MLOps MCP service: model inference, training pipeline, MLflow registry, drift detection, officer feedback | MLflow tracking DB + DVC reference data |
| **sentry-ui** | 3001 (prod) / 5173 (dev) | React 19 + Vite + nginx | Investigation workspace, case management, officer narrative, PDF export | — (queries sentry-api) |
| **precise-risk-engine** (deprecated) | 8007 | Flask + Python | Legacy ML scoring — REDUNDANT with cbp-risk-engine, scheduled for removal | — |

### Health Checks

All services expose health check endpoints consumed by Docker Compose startup orchestration:

- **sentry-data:** `GET /health` → returns `{"status": "healthy", "records_in_db": <count>}`
- **sentry-api:** `GET /health` → returns `{"status": "healthy", "mode": "live", "dependencies": {...}}`
- **sentry-cord-integration:** `GET /health` → returns `{"status": "healthy", "entity_count": 21000000, "ready": true}`
- **precise-risk-engine:** `GET /health` → returns `{"status": "healthy", "model_loaded": true, "ready": true}`
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

precise-risk-engine
  ├─ Loads trained XGBoost model from disk
  ├─ Loads configuration (7 factors, 3 gates, rules)
  ├─ Waits for sentry-data healthy (optional, for enrichment)
  └─ Ready to accept scoring requests

sentry-api
  ├─ Waits for sentry-data healthy
  ├─ Waits for sentry-cord-integration healthy
  ├─ Waits for precise-risk-engine healthy (required)
  ├─ Loads feature flag state (USE_PRECISE_RISK_MODEL)
  └─ Ready to accept requests (routes to legacy or precise-risk-engine)

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

### Model Architecture

CBP Sentry uses a blended model: **60% XGBoost (calibrated probability) + 40% 7-factor rule engine**.

```
INPUT: Manifest data (36 normalized features)
  ├─ XGBoost Classifier (60% weight)
  │   ├─ Trained on 10,287 records (287 EAPA + 10,000 negatives) — SYNTHETIC
  │   ├─ 36 clean features (leaky features removed, see models/score_calibration.json)
  │   ├─ Returns raw probability → calibrate via percentile anchors
  │   └─ AUC: 0.940 | Precision: 1.0 | Recall: 0.528
  │
  ├─ Rule Engine (40% weight)
  │   ├─ 7 factors with hardcoded weights (see factor table below)
  │   ├─ Uses live lookups: CORD entity match, VesselFinder dwell, AD/CVD table
  │   └─ Returns 0-100 rule score
  │
  └─ Blend → Final Score = 0.6×XGBoost_calibrated + 0.4×Rule_score
               → Constrain to 0-100

OUTPUT: {
  risk_score: 0-100,
  risk_level: HIGH|MEDIUM|LOW,
  calculated_risk_score: (same, model-computed),
  model_version: "xgb-v1.0-YYYYMMDD",
  model_maturity: 15,   ← current level (scale: 15/30/50/70/90)
  scored_at: ISO timestamp,
  scoring_method: "xgb_blend",
  factor_breakdown: {...},
  shap_values: {...}    ← top 5 features
}
```

> **⚠️ Current limitation:** scoring endpoint computes live scores but does NOT write back to DB.
> All `calculated_risk_score`, `scored_at`, `model_version` fields in DB are NULL.
> Score write-back is a 15% maturity task (in progress).

### 7 Scoring Factors

| Factor | Weight | Key Signals | Data Source | Status |
|--------|--------|-------------|-------------|--------|
| **Documentation** | 25% | ISF Element 9 mismatch, manifest amendments | ISF data (synthetic) | ⚠️ Synthetic |
| **Corridor** | 20% | Origin country risk, SE Asia routes | Corridor risk table | ⚠️ Synthetic baselines |
| **Commodity** | 15% | AD/CVD HS codes, UFLPA, export control | Federal Register (TODO) | ⬜ Zero factor |
| **Routing** | 15% | AIS dwell anomaly, port selection, vessel flag | VesselFinder API (live) | ✅ Real |
| **Party** | 10% | Shipper age, prior violations, OFAC match | CORD + OpenCorporates (TODO) | ⬜ Zero factor |
| **Pattern** | 10% | Price anomaly (declared vs corridor norm), weight | UN Comtrade (TODO) | ⬜ Zero factor |
| **Time Sensitivity** | 5% | Pre-tariff filing, seasonal anomaly | Derived from manifest dates | ✅ Real |

> **Zero factors:** Commodity, Party, and Pattern default to 0 when reference data is missing.
> This is fixed at 15% maturity by loading AD/CVD, Comtrade, and OpenCorporates data.

### Score Calibration

```
Raw XGBoost probability → percentile mapping (from score_calibration.json):
  p50 = 0.000327  → score 50
  p75 = 0.00328   → score 75
  p90 = 0.01863   → score 90
  p95 = 0.42177   → score 95
  p99 = 1.0       → score 99
Top 25% of any scored population achieves score ≥ 70.
```

### Score Thresholds

```
Score Range  Recommendation         Action
───────────────────────────────────────────────
70 - 100     HIGH — Hold/Examine    Automatic referral flag; officer investigation
50 - 69      MEDIUM — Under Audit   Officer discretion; targeted review
0  - 49      LOW — Clear            Normal processing
```

### Score Provenance (15% implementation target)

Every scored shipment must carry:
- `calculated_risk_score` — engine-computed (replaces synthetic `risk_score`)
- `model_version` — e.g. "xgb-v1.0-20260624"
- `model_maturity` — integer 15 (scale: 15/30/50/70/90)
- `scored_at` — ISO 8601 timestamp
- `scoring_method` — "xgb_blend" | "rule_engine" | "legacy"
- History preserved in `score_history` table on model promotion

### Reference Data Architecture

```
15-29% Maturity:
  cbp-risk-engine/reference/           (DVC-versioned artifacts)
    adcvd/vn_v1.0.csv                  ← Federal Register AD/CVD orders (VN)
    corridors/vn_us_v1.0.csv           ← UN Comtrade VN→US baselines
    entities/vn_v1.0.csv               ← OpenCorporates VN company registry

30%+ Maturity:
  Reference Data Service (port 8011)   ← extracted from cbp-risk-engine
  Versioned API: GET /api/reference/{dataset}/{version}

50%+ Maturity:
  Feature Store                        ← evolved from Reference Data Service
```

Pipeline pattern:
```
fetch_adcvd.py --region VN --version 1.0
  → ELT (extract from Federal Register, transform to canonical schema)
  → DVC commit reference/adcvd/vn_v1.0.csv
  → model card records: adcvd_version=v1.0
  → both training pipeline AND scoring engine read from same artifact
```

---

## 6. Entity Resolution Architecture

### CORD Index (243K Records)

- **Source:** Public entity records from: GLEIF (LEI registry), ICIJ Panama/Pandora Papers, OFAC SDN, Open Sanctions, Open Ownership, US Labor Violations
- **Storage:** SQLite at `/app/data/cord_index.db` (sentry-cord-integration service)
- **Indexing:** Fuzzy match on company name + country code; exact match on LEI/tax ID
- **Usage:** `GET /search?name={query}&country={code}` returns top-K matches with confidence scores
- **⚠️ Coverage gap:** Mostly Western-focused — search for "Guangzhou" or VN/MY manufacturers returns []. Needs OpenCorporates expansion for SE Asia at 30% maturity.
- **Senzing mode:** Runs in `API_MODE=fixture` by default — live entity resolution not active.

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

- **Status:** DISABLED — `ALTANA_ENABLED=false`, `ALTANA_API_KEY=demo-key-12345` (demo)
- **Enable at 50% maturity** when real Altana subscription is in place
- **Trigger:** Automatic when risk_score ≥ 75
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

- **Status:** ACTIVE — real API key configured (`VESSELAPI_KEY` in .env)
- **Use:** Port dwell anomaly detection (Routing factor)
- **API:** VesselFinder AIS feed — fires when `dwell_days=NULL` in manifest
- **Query:** Vessel IMO + port code → port call history, dwell times
- **Output:** Actual dwell vs baseline; port sequence verification; vessel flag, IMO data

### OpenCorporates / Comtrade / Federal Register (Reference Data Pipelines)

These are **ELT pipelines** producing DVC-versioned artifacts consumed by the scoring engine:

- **fetch_adcvd.py `--region VN`** — Federal Register API + USITC: VN AD/CVD orders for HS 7604/8541
  - Output: `cbp-risk-engine/reference/adcvd/vn_v1.0.csv`
  - Fixes: Commodity factor (real duty rates, active EAPA orders)
- **fetch_comtrade.py `--region VN`** — UN Comtrade API: VN→US bilateral trade baselines (3yr)
  - Output: `cbp-risk-engine/reference/corridors/vn_us_v1.0.csv`
  - Fixes: Pattern + Corridor factors (real weight/value norms per HS code)
- **fetch_entities.py `--region VN`** — OpenCorporates API: VN company registry (~500 exporters)
  - Output: `cbp-risk-engine/reference/entities/vn_v1.0.csv`
  - Fixes: Party factor (real shipper incorporation dates, registration status)

**Pipeline scale plan:** Add `--region CN`, `--region MY` at 30% maturity.

---

## 8. MLOps Architecture (cbp-risk-engine)

### Service Overview

`cbp-risk-engine` (port 8010) is the MLOps MCP service — a standalone FastAPI service
managing model lifecycle separately from the main `sentry-api`. It exposes 6 route groups:

```
POST /api/predict           → XGBoost + SHAP inference
POST /api/train             → Trigger training pipeline (uses reference/ data + DB snapshots)
GET  /api/models            → MLflow model registry listing
GET  /api/models/{id}       → Model card (features, training data, maturity level)
POST /api/models/{id}/approve → 3-voter approval workflow (Lead Analyst, DS Lead, Compliance)
GET  /api/metrics/performance → AUC, precision, recall per model version
GET  /api/metrics/gates     → Gate status (gate1/2/3/4 thresholds)
GET  /api/metrics/drift     → KS test on feature distributions (vs training baseline)
GET  /api/jobs              → Training job history
POST /api/feedback          → Officer feedback → gate1_outcomes (training signal for 30%)
GET  /api/explain/{id}      → SHAP explanation for a specific shipment
```

### Start Command (manual, not yet in docker-compose)

```bash
cd /home/rahulvadera/cbp-risk-engine
MODEL_DIR=/home/rahulvadera/cbp-sentry/models \
SENTRY_SRC=/home/rahulvadera/cbp-sentry/services/api \
nohup .venv/bin/python -m uvicorn api.main:app --host 0.0.0.0 --port 8010 \
  > /tmp/mcp_server.log 2>&1 &
```

> **TODO:** Add to docker-compose.yml at 15% maturity completion.

### Model Approval Workflow (3-voter quorum)

1. Training job completes → model staged with status "pending_review"
2. Lead Analyst reviews performance metrics → approves or rejects
3. DS Lead reviews drift report → approves or rejects
4. Compliance reviews model card + data provenance → approves or rejects
5. All 3 approve → model promoted → `score_history` backup triggered → batch rescore starts

### Officer Feedback Loop (gate1_outcomes table)

Officer actions in the UI feed into the training pipeline at 30%+:
```
Hold/Examine/Clear button → POST /api/feedback → gate1_outcomes table
gate1_outcomes ≥ 200 → enables LightGBM retraining (30% maturity gate)
gate1_outcomes ≥ 500 → enables full ensemble (50% maturity gate)
gate1_outcomes ≥ 1000 → enables RL closed-loop (70% maturity gate)
```

---

## 9. Security Architecture

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
| **Backend Risk Engine** | Flask | 3.0+ |
| **Backend Async** | asyncio + aiohttp | stdlib + 3.9 |
| **ML Framework** | XGBoost | 2.0+ |
| **ML Anomaly Detection** | Isolation Forest (scikit-learn) | 1.5+ |
| **ML Explainability** | SHAP | 0.45+ |
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

**Services:**
- sentry-ui (port 3001)
- sentry-api (port 8000)
- sentry-data (port 8005)
- sentry-cord-integration (port 8004)
- precise-risk-engine (port 8007 → 8004 internal)
- senzing (port 8250, optional profile)

**Risk Scoring:** Feature flag `USE_PRECISE_RISK_MODEL=false` (safe default, uses legacy model)

### Cloud Run Staging (SQLite)

5 separate Cloud Run services; Cloud Storage FUSE bucket for `/app/data`; Workload Identity for service-to-service auth; Secret Manager for API keys.

**Risk Scoring:** Feature flag `USE_PRECISE_RISK_MODEL=true` with `TRAFFIC_PERCENTAGE=10` (gradual rollout, 90% legacy / 10% precise-risk)

### Cloud Run Production (PostgreSQL)

5 separate Cloud Run services; Cloud SQL PostgreSQL; Cloud VPC Connector for SQL connectivity; Secret Manager for all credentials.

**Risk Scoring:** Feature flag `USE_PRECISE_RISK_MODEL=true` with `TRAFFIC_PERCENTAGE=0` initially (100% legacy). Manual traffic increase via API after validation/monitoring period.

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
