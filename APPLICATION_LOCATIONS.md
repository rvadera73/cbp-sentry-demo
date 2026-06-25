# CBP Sentry — Application & Service Locations

**Version:** 2.1 | **Updated:** 2026-06-12 | **Audience:** Developers, Architects, DevOps

This document maps all CBP Sentry applications and services to their filesystem locations, entry points, and key files.

---

## Service Directory Structure

```
cbp-sentry/
├── services/                          ← All microservices
│   ├── api/                          ← API Gateway (sentry-api)
│   │   ├── main.py                   ← FastAPI app entry point
│   │   ├── phase2_integration.py     ← Feature flag + routing logic
│   │   ├── routes/                   ← API endpoints
│   │   │   ├── shipments.py
│   │   │   ├── entities.py
│   │   │   ├── scoring.py
│   │   │   └── scoring_phase2.py     ← Phase 2 scoring endpoints
│   │   ├── models/                   ← SQLAlchemy + Pydantic models
│   │   ├── Dockerfile                ← Container definition
│   │   └── requirements.txt           ← Python dependencies
│   │
│   ├── data/                         ← Data Service (sentry-data)
│   │   ├── main.py                   ← FastAPI app entry point
│   │   ├── database.py               ← SQLite connection + schema
│   │   ├── models/                   ← Database models (shipments, manifests, scores)
│   │   ├── routes/                   ← CRUD endpoints
│   │   ├── seed_data/                ← JSON seed files
│   │   │   ├── manifest_demo_cases.json
│   │   │   └── legacy_archived.json
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   │
│   ├── cord-integration/             ← Entity Resolution (sentry-cord-integration)
│   │   ├── main.py                   ← FastAPI app entry point
│   │   ├── cord_client.py            ← CORD index wrapper
│   │   ├── routes/                   ← Entity search/resolution endpoints
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   │
│   └── risk-engine/                  ← ML Risk Scoring (precise-risk-engine)
│       ├── app.py                    ← Flask app entry point
│       ├── models/
│       │   ├── risk_model.py         ← PreciseRiskModel class (XGBoost)
│       │   └── *.pkl                 ← Trained XGBoost, Isolation Forest, SHAP
│       ├── config/
│       │   └── cbp.yaml              ← 7 factors, 3 gates, 8 rules
│       ├── routes/
│       │   └── scoring.py            ← /score, /health endpoints
│       ├── Dockerfile
│       └── requirements.txt
│
├── ui/                               ← Frontend Application (sentry-ui)
│   ├── src/
│   │   ├── index.html                ← HTML entry point
│   │   ├── main.tsx                  ← React root
│   │   ├── App.tsx                   ← Router + providers
│   │   ├── pages/
│   │   │   ├── V2DashboardPage.tsx
│   │   │   ├── V2InvestigationsPage.tsx
│   │   │   ├── V2ShippingIntelligencePage.tsx
│   │   │   ├── V2EntitiesPage.tsx
│   │   │   └── ...
│   │   ├── components/
│   │   │   ├── V2Header.tsx
│   │   │   ├── V2Sidebar.tsx
│   │   │   ├── V2Layout.tsx
│   │   │   └── ...
│   │   ├── api/
│   │   │   └── client.ts             ← API client (calls sentry-api)
│   │   └── styles/
│   │       └── globals.css
│   ├── Dockerfile                    ← Multi-stage build → nginx
│   ├── package.json                  ← Node dependencies
│   ├── tsconfig.json                 ← TypeScript config
│   ├── vite.config.ts                ← Vite build config
│   └── nginx.conf                    ← nginx reverse proxy config
│
├── docker-compose.yml                ← Local multi-service orchestration
├── .github/workflows/
│   ├── deploy.yml                    ← Staging CI/CD (dev/stage branches)
│   ├── deploy-production.yml         ← Production CI/CD (stable branch)
│   ├── deploy-stable.yml
│   ├── test.yml                      ← Tests
│   └── security.yml                  ← Security scanning
│
├── scripts/
│   ├── local_startup.sh              ← Local deployment automation
│   ├── setup_gcp_staging.sh          ← GCP infrastructure setup
│   └── ...
│
└── docs/
    ├── ARCHITECTURE.md               ← System architecture (2.1, includes Phase 2)
    ├── DEPLOYMENT.md                 ← Deployment guide (2.1, includes traffic ramping)
    ├── DESIGN.md                     ← UI/UX design
    └── README.md
```

---

## Service Locations & Ports

### 1. Frontend Application (sentry-ui)

**Location:** `/home/rahulvadera/cbp-sentry/ui/`

**Port:** 3001 (production) / 5173 (development)

**Framework:** React 19 + TypeScript + Vite

**Entry Points:**
- **Browser:** http://localhost:3001 (local) or https://sentry-ui-{hash}.{region}.run.app (Cloud Run)
- **Source:** `ui/src/index.html` → `ui/src/main.tsx` → `ui/src/App.tsx`
- **Build:** `ui/Dockerfile` (nginx reverse proxy + React SPA)

**Key Files:**
- `ui/src/pages/*.tsx` — Tab pages (Investigations, Shipments, Entities, etc.)
- `ui/src/components/V2*.tsx` — Shared components (Header, Sidebar, Layout)
- `ui/src/api/client.ts` — API client (calls sentry-api:8000)

**Dependencies:**
- React (frontend framework)
- Tailwind CSS (styling)
- Recharts (data visualization)
- API Gateway: `sentry-api:8000` (internal) or https://sentry-api-{hash}.run.app (Cloud)

---

### 2. API Gateway (sentry-api)

**Location:** `/home/rahulvadera/cbp-sentry/services/api/`

**Port:** 8000

**Framework:** FastAPI + uvicorn (Python)

**Entry Points:**
- **API:** http://localhost:8000 (local) or https://sentry-api-{hash}.run.app (Cloud Run)
- **Source:** `services/api/main.py`
- **Docker:** `services/api/Dockerfile`

**Key Files:**
- `services/api/main.py` — FastAPI app initialization, middleware, dependency injection
- `services/api/phase2_integration.py` — Feature flag management, routing logic for Phase 2
- `services/api/routes/` — Endpoint implementations (shipments, entities, scoring)
- `services/api/routes/scoring_phase2.py` — Phase 2 scoring endpoints + feature flag API

**Responsibilities:**
- Orchestrates data, entity resolution, and risk scoring
- Manages feature flag state (USE_PRECISE_RISK_MODEL, TRAFFIC_PERCENTAGE)
- Routes shipment scoring to legacy model OR precise-risk-engine based on flag
- Falls back to legacy if precise-risk-engine unavailable
- Integrates with Google Gemini Pro (AI narratives), Altana Atlas (supply chain verification)

**Dependencies:**
- `sentry-data:8005` — SQLite database
- `sentry-cord-integration:8004` — Entity resolution
- `precise-risk-engine:8004` (internal) — ML risk scoring

---

### 3. Data Service (sentry-data)

**Location:** `/home/rahulvadera/cbp-sentry/services/data/`

**Port:** 8005

**Framework:** FastAPI + uvicorn (Python)

**Entry Points:**
- **API:** http://localhost:8005 (local) or https://sentry-data-{hash}.run.app (Cloud Run)
- **Source:** `services/data/main.py`
- **Docker:** `services/data/Dockerfile`

**Key Files:**
- `services/data/main.py` — FastAPI app, startup (seed data loading)
- `services/data/database.py` — SQLite engine, session factory
- `services/data/models/` — SQLAlchemy table definitions (shipments, manifests, scores, entities)
- `services/data/routes/` — CRUD endpoints (GET/POST shipments, etc.)
- `services/data/seed_data/` — JSON seed files (demo cases, historical data)

**Responsibilities:**
- CRUD operations for shipments, manifests, scores, entities
- Seed data loading on startup (manifest_demo_cases.json → SQLite)
- Provides single source of truth for shipment records

**Database:**
- Local: SQLite at `/app/data/cbp_sentry.db` (persistent volume)
- Cloud: SQLite at GCS FUSE mount `/app/data/cbp_sentry.db`

**Dependencies:** None (no upstream dependencies)

---

### 4. Entity Resolution Service (sentry-cord-integration)

**Location:** `/home/rahulvadera/cbp-sentry/services/cord-integration/`

**Port:** 8004

**Framework:** FastAPI + uvicorn (Python)

**Entry Points:**
- **API:** http://localhost:8004 (local) or https://sentry-cord-integration-{hash}.run.app (Cloud Run)
- **Source:** `services/cord-integration/main.py`
- **Docker:** `services/cord-integration/Dockerfile`

**Key Files:**
- `services/cord-integration/main.py` — FastAPI app, startup (CORD index loading)
- `services/cord-integration/cord_client.py` — CORD database wrapper (21M entity search)
- `services/cord-integration/routes/` — Entity search/resolution endpoints
- `services/cord-integration/senzing_wrapper.py` — Mock Senzing SDK (3-level ownership resolution)

**Responsibilities:**
- Entity search (fuzzy name matching on 21M CORD records)
- 3-level ownership resolution (shipper → parent → owner)
- OFAC/SDN screening (sanctions list matching)
- Why-linked explanations (relationship tracing)

**Database:**
- CORD SQLite Index: `/app/data/cord_index.db` (21M entity records)
- GCS FUSE Mount: `gs://cbp-sentry-appdata/cord_index.db`

**Dependencies:**
- `sentry-data:8005` — Fetches shipments on startup

---

### 5. ML Risk Scoring Service (precise-risk-engine)

**Location:** `/home/rahulvadera/cbp-sentry/services/risk-engine/`

**Port:** 8007 (external, maps to 8004 internal in Docker)

**Framework:** Flask (Python)

**Entry Points:**
- **API:** http://localhost:8007 (local Docker) or https://precise-risk-engine-{hash}.run.app (Cloud Run)
- **Source:** `services/risk-engine/app.py`
- **Docker:** `services/risk-engine/Dockerfile`

**Key Files:**
- `services/risk-engine/app.py` — Flask app initialization, routes
- `services/risk-engine/models/risk_model.py` — PreciseRiskModel class (XGBoost wrapper)
- `services/risk-engine/models/` — Trained ML models
  - `xgboost_model.pkl` — Trained XGBoost classifier
  - `isolation_forest.pkl` — Anomaly detector
  - `shap_explainer.pkl` — Model explainability
- `services/risk-engine/config/cbp.yaml` — Configuration (7 factors, 3 gates, 8 rules)
- `services/risk-engine/routes/scoring.py` — `/score` and `/health` endpoints

**Responsibilities:**
- Feature engineering (72 CBP features → 7 weighted factors)
- 3-gate processing:
  1. Deterministic rules (OFAC, high-risk commodities/corridors)
  2. XGBoost classification (trained on historical data)
  3. Uncertainty quantification (Isolation Forest, SHAP)
- Returns risk score (0-100) with confidence, factors, explanations

**Model Specs:**
- Training Data: ~10,000 labeled shipments
- Features: 72 CBP manifest fields
- Feature Factors: 7 (Documentation, Routing, Commodity, Corridor, Party, Pattern, Time-Sensitivity)
- Architecture: 3 gates (rules → XGBoost → uncertainty)
- Performance: AUC 1.0, latency <100ms

**Dependencies:** None (read-only access to sentry-data optional for enrichment)

---

## Deployment Pipelines

### Local Development (`docker-compose.yml`)

**File:** `/home/rahulvadera/cbp-sentry/docker-compose.yml`

**Services:**
- `sentry-data` (port 8005)
- `sentry-cord-integration` (port 8004)
- `precise-risk-engine` (port 8007 → 8004 internal)
- `sentry-api` (port 8000)
- `sentry-ui` (port 3001)
- `senzing` (port 8250, optional profile)

**Orchestration Script:**
```bash
./scripts/local_startup.sh [clean]
```

**Features:**
- Single docker-compose command starts all 5-6 services
- All services on `sentry-network` (bridge)
- Health checks for startup ordering
- Smoke tests after deployment
- Feature flag OFF by default (legacy model only)

---

### Staging Deployment (develop/dev/stage branches)

**GitHub Actions:** `.github/workflows/deploy.yml`

**Services Deployed:** sentry-api, sentry-data, sentry-cord-integration, precise-risk-engine, sentry-ui

**Triggers:**
- `git push origin dev`
- `git push origin stage`

**Environment:**
- Google Cloud Run (us-central1)
- Cloud Storage FUSE for data persistence
- Workload Identity for service-to-service auth

**Phase 2 Configuration:**
- `USE_PRECISE_RISK_MODEL=true`
- `TRAFFIC_PERCENTAGE=10` (gradual rollout: 90% legacy, 10% precise-risk-engine)

**Workflow Steps:**
1. Detect changed services (only build changed)
2. Run tests (pytest + TypeScript check)
3. Build Docker images
4. Push to Artifact Registry
5. Deploy to Cloud Run
6. Run smoke tests
7. Send Slack notification

---

### Production Deployment (stable branch)

**GitHub Actions:** `.github/workflows/deploy-production.yml`

**Services Deployed:** sentry-api, sentry-data, sentry-cord-integration, precise-risk-engine, sentry-ui

**Triggers:**
- `git push origin stable`

**Environment:**
- Google Cloud Run (us-central1)
- Cloud SQL PostgreSQL (production database)
- Cloud Storage FUSE for data persistence

**Phase 2 Configuration:**
- `USE_PRECISE_RISK_MODEL=true`
- `TRAFFIC_PERCENTAGE=0` (OFF initially, manual increase via API)

**Workflow Steps:**
1. Run tests (pytest + TypeScript check)
2. Build all Docker images (always, for safety)
3. Push to Artifact Registry
4. Deploy all services to Cloud Run (in order)
5. Run smoke tests
6. Send Slack notification

**Manual Traffic Ramping (Post-Deployment):**
```bash
# Day 1: 10% traffic
curl -X POST https://sentry-api-prod.{hash}.run.app/api/feature-flag \
  -d '{"enabled": true, "traffic_percentage": 10}'

# Day 2: 50% traffic (if Day 1 clean)
# Day 3: 90% traffic (if Day 2 clean)
# Day 4: 100% traffic (if Day 3 clean)

# Rollback anytime
curl -X POST https://sentry-api-prod.{hash}.run.app/api/feature-flag \
  -d '{"enabled": false, "traffic_percentage": 0}'
```

---

## File Locations Summary

### Source Code

| Component | Location | Language | Entry Point |
|---|---|---|---|
| **Frontend** | `ui/` | TypeScript/React | `ui/src/main.tsx` |
| **API Gateway** | `services/api/` | Python/FastAPI | `services/api/main.py` |
| **Data Service** | `services/data/` | Python/FastAPI | `services/data/main.py` |
| **Entity Service** | `services/cord-integration/` | Python/FastAPI | `services/cord-integration/main.py` |
| **Risk Engine** | `services/risk-engine/` | Python/Flask | `services/risk-engine/app.py` |

### Configuration

| Item | Location | Type |
|---|---|---|
| **Docker Compose** | `docker-compose.yml` | YAML |
| **Local Startup** | `scripts/local_startup.sh` | Bash |
| **Staging CI/CD** | `.github/workflows/deploy.yml` | YAML (GitHub Actions) |
| **Production CI/CD** | `.github/workflows/deploy-production.yml` | YAML (GitHub Actions) |
| **Risk Engine Config** | `services/risk-engine/config/cbp.yaml` | YAML |

### Documentation

| Document | Location |
|---|---|
| **Architecture** | `docs/ARCHITECTURE.md` |
| **Deployment** | `docs/DEPLOYMENT.md` |
| **Design** | `docs/DESIGN.md` |
| **Quick Start** | `QUICK_START_DEPLOYMENT.md` |

---

## Next Steps

- **Local Testing:** Run `./scripts/local_startup.sh` and navigate to http://localhost:3001
- **Staging Deploy:** `git push origin dev` and watch GitHub Actions
- **Production Deploy:** `git push origin stable` and follow traffic ramping guide
- **Phase 2 Validation:** Use feature flag API to control traffic percentage
- **Monitoring:** Check Cloud Logging, service health, and error rates during ramping

For detailed deployment instructions, see `docs/DEPLOYMENT.md`.
For architecture details, see `docs/ARCHITECTURE.md`.
