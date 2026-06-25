# CBP Sentry — Development Guide

**Last Updated:** 2026-06-24  
**Status:** 15% Model Maturity — Active Development  
**Primary Corridor:** VN → US (aluminum extrusions HS 7604, solar panels HS 8541)

---

## Project Overview

**CBP Sentry** is a trade enforcement intelligence platform for CBP officers detecting illegal
transshipment (EAPA cases). It ingests import manifests, scores risk across 7 factors, generates
EAPA referral packages, and provides an investigation workspace.

**Workflow:** Manifest Ingest → Entity Resolution → Risk Scoring → Investigation Workspace → Referral Package

---

## Running Services (Docker Compose)

```bash
cd /home/rahulvadera/cbp-sentry
docker compose up -d

# sentry-ui          → http://localhost:3001   React UI (nginx)
# sentry-api         → http://localhost:8000   FastAPI orchestration
# sentry-data        → http://localhost:8005   FastAPI data service (SQLite)
# cbp-risk-engine    → http://localhost:8010   MLOps MCP service (standalone)
# precise-risk-engine→ http://localhost:8007   Legacy — to be removed
# sentry-cord        → http://localhost:8004   CORD/Senzing entity resolution
```

**cbp-risk-engine is NOT in docker-compose yet** — start manually:
```bash
cd /home/rahulvadera/cbp-risk-engine
MODEL_DIR=/home/rahulvadera/cbp-sentry/models \
SENTRY_SRC=/home/rahulvadera/cbp-sentry/services/api \
nohup .venv/bin/python -m uvicorn api.main:app --host 0.0.0.0 --port 8010 \
  > /tmp/mcp_server.log 2>&1 &
```

---

## Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 19 + TypeScript + Tailwind CSS + Vite (port 3001 via nginx) |
| API | FastAPI + Python 3.12 + Uvicorn |
| Data | SQLite (sentry-data) — `services/api/data/cbp_sentry.db` |
| ML Primary | XGBoost (36 features) + Rule engine — 60/40 blend |
| ML Secondary | LightGBM (legacy 8 features), IsolationForest (AIS anomaly) |
| MLOps | MLflow + DVC — cbp-risk-engine service |
| Entity Resolution | Senzing SDK + CORD (243K entities: GLEIF, ICIJ, OFAC, OpenSanctions) |
| AI | Google Gemini (referral narratives) |
| AIS | VesselFinder API (live vessel tracking) |

---

## Build & Test Commands

```bash
# Frontend
cd ui
npm run lint          # tsc --noEmit
npm test              # Vitest
npm run dev           # Vite dev server :8080
npm run dev:api       # Express proxy :3001

# Backend tests
cd /home/rahulvadera/cbp-sentry && python3 -m pytest tests/ -q

# Rebuild all containers
docker compose build
docker compose up -d

# Rebuild single service
docker compose build sentry-ui && docker compose up -d sentry-ui
```

---

## Architecture

```
sentry-ui (3001)
  └─ nginx proxies /api/* → sentry-api:8000

sentry-api (8000)              ← main orchestration layer
  ├─ /api/shipments            → sentry-data:8005
  ├─ /api/risk-scoring/*       → risk_scoring_engine.py (XGBoost + rule engine)
  ├─ /api/er/*                 → sentry-cord:8004 (entity resolution)
  ├─ /api/referral/*           → referral_comprehensive_v2.py + Gemini
  └─ /api/ask-ai/*             → ask_ai_agent.py + Gemini

sentry-data (8005)             ← SQLite data service
  └─ cbp_sentry.db (1396 shipments, limit 5000/page)

cbp-risk-engine (8010)         ← MLOps MCP service (standalone)
  ├─ POST /api/predict         → XGBoost + SHAP + rule engine blend
  ├─ GET  /api/models          → MLflow model registry
  ├─ POST /api/train           → Training pipeline trigger
  ├─ GET  /api/metrics/gates   → Performance gate status
  └─ POST /api/feedback        → Officer feedback → training signal

sentry-cord (8004)             ← CORD/Senzing entity resolution
  └─ 243K entities: GLEIF LEI + ICIJ (Panama/Pandora) + OFAC + OpenSanctions
     NOTE: Mostly Western entities — SE Asia coverage gap (see data strategy)
```

---

## Risk Scoring Model

**Current maturity: ~15%** (deterministic rules + XGBoost on synthetic data)

### Scoring Formula
```
Final Score = 60% × XGBoost_calibrated + 40% × Rule_engine
```

### 7 Factors (Rule Engine)
| Factor | Weight | Key Signals |
|--------|--------|-------------|
| Documentation | 25% | ISF Element 9 mismatch, manifest amendments |
| Routing | 20% | Vessel dwell anomaly, port selection, flag |
| Commodity | 15% | AD/CVD HS codes, UFLPA, export control |
| Corridor | 15% | Origin country risk, SE Asia transshipment routes |
| Party | 10% | Shipper age, opacity, known bad actors |
| Pattern | 10% | Value/weight anomaly, multidimensional outlier |
| Time Sensitivity | 5% | Pre-tariff filing timing, seasonal anomaly |

### Score Thresholds
- HIGH ≥ 70 → Hold for Examination
- MEDIUM 50-69 → Under Audit / Review
- LOW < 50 → Clear

### XGBoost Model
- **Training data:** Synthetic (10,287 records — 287 EAPA + 10,000 negatives)
- **Features:** 36 clean features (leaky features excluded)
- **AUC:** 0.940 | Precision: 1.000 | Recall: 0.528
- **Calibration:** Percentile anchors (p50/p75/p90/p95)
- **Known issue:** Trained on synthetic data — recall limited by synthetic EAPA pattern

### Score Provenance
Every score should include:
- `calculated_risk_score` — engine-computed value
- `model_version` — e.g. "xgb-v1.0-20260624"
- `model_maturity` — 15 (scale: 15/30/50/70/90)
- `scored_at` — timestamp
- `scoring_method` — "xgb_blend" | "rule_engine"

**Current state:** Scoring endpoint computes but does NOT yet write back to DB.  
**TODO:** Wire write-back + batch rescore all 1396 shipments.

---

## Model Maturity Ladder

| Level | Description | Trigger | Data Required |
|-------|-------------|---------|---------------|
| **15%** | Deterministic rules + entity graph, low FP referrals | In progress | AD/CVD VN orders, Comtrade VN→US baselines, VN company registry |
| **30%** | LightGBM on Gate 1 outcomes + EAPA history | gate1_outcomes ≥ 200 | Real feedback + public EAPA cases (~150-200) |
| **50%** | Full ensemble + dynamic thresholding + BBN | gate1_outcomes ≥ 500 | Altana API active, ISF amendment data |
| **70%** | RL agent closed-loop retraining, weekly calibration | gate1_outcomes ≥ 1000 | Real ISF data feed (ACE or agreement) |
| **90%** | 90% PPV @ 5+ referrals/day — SOW end-state | 36+ months operation | Full ACE integration, commercial manifest data |

---

## Data Status

### Real Data (active)
- VesselFinder API — live AIS vessel tracking (key configured in .env)
- Google Gemini API — referral narrative generation
- CORD 243K entities — GLEIF, ICIJ, OFAC, OpenSanctions, OpenOwnership
- Senzing entity resolution SDK

### Synthetic Data (being replaced)
- All 1396 DB shipments — risk_scores are pre-seeded fiction (not model-computed)
- Training EAPA cases — EAPA-001052 style fake IDs
- AD/CVD rates — seeded table, not from Federal Register
- Corridor baselines — synthetic JSON seeds
- Altana integration — DISABLED (ALTANA_ENABLED=false, demo key)

### Data Pipelines (15% maturity — in progress)
```
fetch_adcvd.py   --region VN  → reference/adcvd/vn_v1.0.csv    (Federal Register API)
fetch_comtrade.py --region VN → reference/corridors/vn_v1.0.csv (UN Comtrade API)
fetch_entities.py --region VN → reference/entities/vn_v1.0.csv  (OpenCorporates API)
```
All pipelines accept `--region` and `--version` params — scale to new corridors at 30%.

---

## Key Files

| File | Purpose |
|------|---------|
| `services/api/risk_scoring_engine.py` | Primary scorer — 7-factor rules + XGBoost 60/40 blend |
| `services/api/inference_features.py` | Single-shipment 36-feature extractor |
| `services/api/main.py` | API routes (4200+ lines) |
| `services/data/main.py` | Data service routes |
| `train_models_phase1.py` | XGBoost training pipeline |
| `models/xgboost_model.json` | Primary model (36 features) |
| `models/score_calibration.json` | Percentile anchors + clean_features list |
| `models/inference_ref_stats.json` | Normalization stats for single-shipment scoring |
| `cbp-risk-engine/api/main.py` | MLOps MCP service entry point |
| `ui/src/v2/hooks/useV2Cases.ts` | Canonical shipment data hook (all tabs use this) |
| `ui/src/App.tsx` | V2AppWrapper — URL→tab sync, all page routing |

---

## UI Architecture

```
App.tsx → V2AppWrapper
  ├─ useV2Cases()         ← ALL tabs share this hook (GET /api/shipments?risk_min=50&limit=500)
  ├─ /dashboard           → V2DashboardPage
  ├─ /investigations      → V2InvestigationsPage (case workspace, Risk Score tab)
  ├─ /shipments           → V2ActiveShipmentsPage (now uses useV2Cases, not duplicate hook)
  ├─ /entities            → V2EntityResolutionPage
  ├─ /risk-models         → RiskModelManagement (8 stub components — Phase 3 pending)
  └─ /referrals           → V2ReferralsPage
```

**Score display:** Case card shows `calculated_risk_score` (fallback: `risk_score`).  
Risk Score tab calls `POST /api/risk-scoring/comprehensive` for live breakdown.

---

## Known Issues & TODOs

### Immediate (15% maturity execution)
- [ ] Score write-back: scoring endpoint must persist `calculated_risk_score` + provenance
- [ ] DB migration: add `model_version`, `model_maturity`, `scored_at` columns
- [ ] score_history table for audit trail across model versions
- [ ] Batch rescore all 1396 shipments
- [ ] Build 3 data pipelines (AD/CVD, Comtrade, OpenCorporates VN)
- [ ] Wire 4 zero-scoring factors with real reference data

### Short term
- [ ] Add cbp-risk-engine to docker-compose.yml
- [ ] Remove precise-risk-engine (redundant)
- [ ] Wire Risk Model Management tab (8 components → MCP endpoints)
- [ ] Officer feedback loop: Hold/Examine/Clear → gate1_outcomes table

### Architecture debt
- `precise-risk-engine` container is redundant with `cbp-risk-engine` — remove
- Senzing runs in fixture mode by default — enable live resolution for VN entities
- CORD entity coverage sparse for SE Asia — needs OpenCorporates expansion at 30%
