# Risk Model Management — Data Flow & Integration Design

**Status:** Design Phase (Analysis Only)  
**Date:** 2026-06-25  
**Scope:** All 5 UI Tabs + Complete Data Architecture

---

## 1. ARCHITECTURE OVERVIEW

### Current Data Sources

```
┌─────────────────────────────────────────────────────────────┐
│                     CBP Sentry System                        │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────────┐         ┌──────────────────┐           │
│  │  PostgreSQL      │         │  cbp-risk-engine │           │
│  │  (port 5433)     │         │  (port 8010)     │           │
│  ├──────────────────┤         ├──────────────────┤           │
│  │ - shipments      │         │ - MLflow         │           │
│  │ - risk_scores    │         │ - Model versions │           │
│  │ - risk_models    │         │ - Approvals      │           │
│  │ - risk_metrics   │         │ - Training jobs  │           │
│  │ - approvals      │         │ - Metrics        │           │
│  │ - training_jobs  │         │ - Drift data     │           │
│  │ - drift_detected │         └──────────────────┘           │
│  └────────┬─────────┘                  ▲                     │
│           │                            │                     │
│           │        API Routes          │                     │
│           └────────────────────────────┘                     │
│                     (port 8000)                              │
│                           ▲                                  │
│                           │                                  │
│                      ┌────┴────┐                             │
│                      │          │                            │
│               ┌──────▼──┐  ┌───▼──────┐                      │
│               │ Overview │  │ Registry │                     │
│               │  Tab     │  │   Tab    │                     │
│               └──────────┘  └──────────┘                     │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### Three Data Sources

1. **PostgreSQL** — Authoritative registry (shipments, model metadata, approvals)
2. **cbp-risk-engine** — MLOps registry (MLflow model versions, metrics, training)
3. **File-based** — Bootstrap data (metrics_config_cbp.yml, training results JSON)

**KEY DECISION:** UI should pull from **cbp-risk-engine** as primary source, fallback to PostgreSQL for approval workflow.

---

## 2. DATA AUDIT BY TAB

### TAB 1: Overview — Gate Progression & Exit Criteria

**Purpose:** Show which gate we're in, what criteria must be met to exit, blocking items.

#### Data Needs

| Data Point | Source | Status | Notes |
|-----------|--------|--------|-------|
| Current Gate | YAML config (cbp-risk-engine) | ✅ Real | metrics_config_cbp.yml defines gates 0-4 |
| Gate Exit Criteria | YAML config | ✅ Real | Hardcoded in metrics_config_cbp.yml |
| Criteria Met/Not Met | MetricsService | ✅ Real | evaluate_gates() compares measured vs threshold |
| Active Model | cbp-risk-engine MLflow | ✅ Real | Production model from registry |
| Model Maturity % | Metadata in risk_models | ✅ Real | Seeded during registry setup |
| Score Distribution | PostgreSQL shipments | ✅ Real | Query risk_score buckets from shipments table |
| Blocking Items | ? | ❌ Missing | Need analysis |

**Missing Data: "Blocking Items"**
- What prevents gate exit?
- Currently: Hardcoded in OverviewTab.tsx (line 34-35)
- **Question:** Should blocking items be:
  - (A) Tracked in PostgreSQL table? (risk_gate_blockers?)
  - (B) Derived from failed criteria metrics?
  - (C) Manually configured in YAML?

**Recommendation:** (B) — Derive from failed criteria. If a gate's metric doesn't meet threshold → it's a blocker.

---

### TAB 2: Model Registry — Version Management & Lineage

**Purpose:** Show all model versions, lineage, approval votes, status transitions.

#### Data Needs

| Data Point | Source | Status | Notes |
|-----------|--------|--------|-------|
| All Model Versions | cbp-risk-engine MLflow | ✅ Real | ModelRegistry.list_model_versions() |
| Model Name/Version | MLflow | ✅ Real | Registered in MLflow model registry |
| Status (production/staging/candidate/deprecated) | MLflow tags | ✅ Real | Set via aliases and tags |
| Framework | MLflow metadata | ✅ Real | Tag during registration |
| Created Date | MLflow run time | ✅ Real | from run.info.start_time |
| Deployed Date | MLflow tag 'promoted_at' | ✅ Real | Set during promotion |
| Performance Metrics | cbp-risk-engine /metrics | ✅ Real | get_performance() returns accuracy, AUC, etc. |
| Model Lineage | ? | ⚠️ Partial | Progression path defined, transitions tracked |
| Approval Votes | PostgreSQL + cbp-risk-engine | ⚠️ Split | Approvals stored in SQLite (cbp-risk-engine); also in PostgreSQL |
| Approval Status | SQLite (cbp-risk-engine) | ✅ Real | model_approvals table |
| Voters & Votes | SQLite (cbp-risk-engine) | ✅ Real | model_approvals table |

**Data Split Issues:**
- Approvals stored in TWO places:
  - cbp-risk-engine SQLite: for MLflow voting workflow
  - PostgreSQL: risk_model_approvals table (backup)
- **Question:** Single source of truth?
  - (A) Use only cbp-risk-engine SQLite (already has approval logic)
  - (B) Use only PostgreSQL (consolidate)
  - (C) Keep both but sync them?

**Recommendation:** (A) — cbp-risk-engine SQLite is the source of truth for approvals (already integrated with ModelRegistry). Make it the single store. Sync to PostgreSQL for audit trail only.

---

### TAB 3: Performance — Model Metrics & Comparison

**Purpose:** Show accuracy, latency, AUC, fairness, drift for production model and compare vs staging.

#### Data Needs

| Data Point | Source | Status | Notes |
|-----------|--------|--------|-------|
| Production Model Metrics | cbp-risk-engine /metrics/performance | ✅ Real | Loaded from clean_training_results.json |
| Staging Model Metrics | cbp-risk-engine /metrics/performance | ⚠️ Partial | Only if staging model exists in MLflow |
| Metric History (time-series) | PostgreSQL risk_model_metrics | ✅ Real | Table exists, 11 baseline metrics seeded |
| Latency (P50/P95/P99) | cbp-risk-engine predictions | ⚠️ Partial | Stored in recent prediction payloads, not aggregated |
| Fairness (false positive/negative rates) | Drift detection | ⚠️ Partial | Calculated but not persisted |
| Score Distribution | PostgreSQL shipments | ✅ Real | Query risk_score column by bucket |
| Model Comparison (gate0 vs v3.0) | ? | ❌ Missing | Need to compute predictions from both models |

**Missing Data: "Model Comparison"**
- Tab shows v1 (gate0) vs v2 (v3.0) side-by-side
- Currently hardcoded metrics (lines 61-80 in ModelRegistryTab)
- **To get real comparison:**
  - (A) Retrain gate0 and v3.0 on historical shipment data
  - (B) Use existing predictions if available
  - (C) Run batch scoring on test dataset with both models
  - (D) Skip comparison, just show production metrics

**Recommendation:** (C) — Define a test dataset from shipments table, score with both models, log metrics.

**Missing Data: "Latency Aggregation"**
- Individual prediction latency stored, not aggregated
- Need: P50, P95, P99 latency
- **Solution:** Compute from risk_model_predictions.latency_ms

---

### TAB 4: Training & Data — Job History & Retraining Config

**Purpose:** Show training job history, dataset info, automated retraining config.

#### Data Needs

| Data Point | Source | Status | Notes |
|-----------|--------|--------|-------|
| Training Jobs | cbp-risk-engine /jobs | ✅ Real | TrainingPipeline.list_jobs() |
| Job Status | cbp-risk-engine SQLite | ✅ Real | Stored during job execution |
| Job Metrics (accuracy, AUC, time) | cbp-risk-engine runs | ✅ Real | MLflow metrics from training runs |
| Dataset Info (row count, date range) | PostgreSQL shipments | ✅ Real | Query shipments table |
| Training Dataset Size | cbp-risk-engine metrics | ✅ Real | training_samples in performance metrics |
| Test Dataset Size | cbp-risk-engine metrics | ✅ Real | test_samples in performance metrics |
| Feature Engineering History | ? | ❌ Missing | What features were used for each model? |
| Data Quality Metrics | ? | ❌ Missing | Missing value %, outliers %, etc. |
| Retraining Triggers (automated) | PostgreSQL risk_retraining_config | ✅ Real | Table exists, config seeded |
| Retraining Schedule | PostgreSQL risk_retraining_config | ✅ Real | Frequency, thresholds, notifications |
| Last Retraining Run | ? | ❌ Missing | When was the last automated retrain? |

**Missing Data: "Feature Engineering History"**
- Which features used for gate0 vs v3.0?
- **Solution:** Log features during training (MLflow artifact)

**Missing Data: "Data Quality Metrics"**
- Training data health (nulls, outliers, duplication)
- **Solution:** Compute during data prep, log to risk_model_training_jobs.metadata

**Missing Data: "Last Retraining Run"**
- When did automated retraining last trigger?
- **Solution:** Update risk_retraining_config.last_triggered_at during runs

---

### TAB 5: Monitoring — Drift Detection & Alerts

**Purpose:** Show data drift, model drift, error spikes, and actions taken.

#### Data Needs

| Data Point | Source | Status | Notes |
|-----------|--------|--------|-------|
| Drift Alerts | cbp-risk-engine /metrics/drift | ✅ Real | get_drift() compares baseline vs current |
| Drift Type (data/model/error) | PostgreSQL risk_model_drift_detected | ✅ Real | Drift table tracks type |
| Drift Score | cbp-risk-engine | ✅ Real | Computed from KS-statistic |
| Feature Drift | cbp-risk-engine | ✅ Real | Per-field distribution comparison |
| Baseline Distribution | PostgreSQL or files | ✅ Real | Stored in risk_model_drift_detected |
| Current Distribution | cbp-risk-engine predictions | ✅ Real | Computed from recent predictions |
| Drift Detection Timeline | PostgreSQL risk_model_drift_detected | ✅ Real | detected_at timestamp |
| Drift Status (new/acknowledged/resolved) | PostgreSQL | ✅ Real | status column |
| Action Taken | PostgreSQL | ⚠️ Partial | action_taken column exists, rarely filled |
| Monitoring History | PostgreSQL | ✅ Real | Full audit trail in table |
| Alert Channels (Slack/Email/PagerDuty) | ? | ❌ Missing | Are alerts being sent? Which channels? |
| Alert Effectiveness | ? | ❌ Missing | Did alert lead to action? How long to resolve? |

**Missing Data: "Alert Notifications"**
- Does the system actually send alerts?
- **Solution:** Implement alert sender + log notifications to database

**Missing Data: "Alert Effectiveness"**
- How quickly do alerts get resolved?
- **Solution:** Compute from drift_detected.resolved_at - detected_at

---

## 3. DATA SOURCES INVENTORY

### Source 1: PostgreSQL (port 5433)

**Connection:** `postgresql://sentry:sentry-secret@localhost:5433/sentry`

**Tables Used by UI:**

```sql
-- Model Registry (authoritative for metadata)
risk_models                    -- 4 models (v2.1, v3.0, gate0-v1.0, gate1-lgbm-v1.0)
risk_model_approvals          -- Transition records (v2.1 → gate0)
risk_model_training_jobs      -- Training history
risk_model_metrics            -- 11 baseline metrics for gate0
risk_model_predictions        -- Individual prediction records
risk_model_drift_detected     -- Drift alerts
risk_retraining_config        -- Automated retraining config

-- Operational Data
shipments                      -- 1,399 records; columns: risk_score, created_at, ...
```

**Data Status:** ✅ Schema exists, ⚠️ Minimal seed data (11 metrics, 1 config)

---

### Source 2: cbp-risk-engine (port 8010)

**Connection:** Built from `/home/rahulvadera/cbp-risk-engine`

**API Endpoints:**

```
GET /api/models                          → List all MLflow model versions
GET /api/models/production               → Get production model info
GET /api/models/{version_id}             → Get specific version
POST /api/models/{version_id}/approve    → Submit approval vote
POST /api/models/{version_id}/promote    → Promote to production

GET /api/metrics/performance             → Accuracy, AUC, precision, recall
GET /api/metrics/gates                   → Gate evaluation (passed/failed)
GET /api/metrics/history                 → MLflow run history
GET /api/metrics/drift                   → Data/model drift detection

GET /api/jobs                            → List training jobs
GET /api/jobs/{job_id}                   → Get job details
POST /api/train                          → Trigger training

GET /api/feedback                        → Officer feedback/outcomes (if exists)
```

**Data Status:** ✅ APIs exist, ⚠️ Some rely on bootstrap/synthetic data

---

### Source 3: File-Based Configuration

**Location:** `/home/rahulvadera/cbp-risk-engine/`

```
metrics_config_cbp.yml                   → Gate definitions, thresholds, timeline
api/core/training_pipeline.py            → Training job execution
api/core/model_registry.py               → MLflow integration
api/core/monitoring.py                   → Gate evaluation logic
services/api/models/gate0_rule_engine_weights_v1.0.json  → Model configuration
```

**Data Status:** ✅ Real gate configuration

---

## 4. DATA FLOW ARCHITECTURE

### From Database → API → UI

```
PostgreSQL                          cbp-risk-engine API
(source of truth)                   (aggregator)
    ↓                                    ↓
┌─────────────────────────────────┐
│ 1. Overview Tab                 │
│   - Query gates from YAML       │
│   - Get performance metrics     │ → /api/metrics/performance
│   - Evaluate criteria           │ → /api/metrics/gates
│   - Score distribution          │ → Query shipments for buckets
└─────────────────────────────────┘

┌─────────────────────────────────┐
│ 2. Model Registry Tab           │
│   - List model versions         │ → /api/models
│   - Get approval status         │ → /api/models + SQLite approvals
│   - Show lineage/progression    │ → risk_models table + lineage rules
│   - Performance metrics         │ → /api/metrics/performance per version
└─────────────────────────────────┘

┌─────────────────────────────────┐
│ 3. Performance Tab              │
│   - Production metrics          │ → /api/metrics/performance
│   - Staging metrics             │ → /api/models/{staging_id} + /api/metrics
│   - Metric history (time-series)│ → risk_model_metrics table
│   - Latency aggregation         │ → Compute from risk_model_predictions
└─────────────────────────────────┘

┌─────────────────────────────────┐
│ 4. Training & Data Tab          │
│   - Training job history        │ → /api/jobs
│   - Dataset info                │ → /api/metrics/performance
│   - Retraining config           │ → risk_retraining_config table
│   - Last triggered              │ → risk_retraining_config.last_triggered_at
└─────────────────────────────────┘

┌─────────────────────────────────┐
│ 5. Monitoring Tab               │
│   - Drift detection results     │ → /api/metrics/drift
│   - Drift alerts history        │ → risk_model_drift_detected table
│   - Drift status & actions      │ → risk_model_drift_detected table
│   - Monitoring timeline         │ → risk_model_drift_detected.detected_at
└─────────────────────────────────┘
```

---

## 5. MISSING DATA ANALYSIS

### Category A: Data That Exists But Not Connected

| Data | Where | Missing Link | Fix |
|------|-------|--------------|-----|
| Training metrics | cbp-risk-engine MLflow | API returns raw MLflow, UI needs formatted | Transform in API layer |
| Latency P95/P99 | risk_model_predictions table | Not aggregated | Add aggregation query |
| Gate blocking items | Metrics evaluation logic | Not surfaced | Add endpoint /api/metrics/gates/blockers |
| Feature engineering | Not logged | Should be in MLflow artifacts | Log during training |

**Effort:** 2-3 hours each

---

### Category B: Data That Needs Computation

| Data | Requires | Implementation |
|------|----------|-----------------|
| Model comparison (gate0 vs v3.0) | Batch scoring both models | Run inference.py on test dataset, log metrics |
| Data quality (missing %, outliers) | Feature engineering pipeline | Compute during data prep, log to risk_model_training_jobs |
| Alert effectiveness (resolution time) | Post-incident review | Query: AVG(resolved_at - detected_at) |

**Effort:** 4-6 hours each

---

### Category C: Data That Needs Infrastructure

| Data | Gap | Solution |
|------|-----|----------|
| Alert notifications | Not sent anywhere | Implement AlertService (Slack/Email/PagerDuty) |
| Last retraining run | Not tracked | Add trigger logger in training pipeline |
| Officer feedback/outcomes | Not in system | Integrate with CBP outcome recording |

**Effort:** 4-8 hours each (depends on integrations)

---

## 6. INTEGRATION REQUIREMENTS

### A. Backend Changes (cbp-risk-engine)

```python
# NEW ENDPOINTS NEEDED

GET /api/metrics/gates/blockers
  → Returns: [{"criterion": "...", "status": "not_met", "blocking": true}]

GET /api/metrics/performance/comparison?model_a=gate0-v1.0&model_b=v3.0
  → Returns: Side-by-side metrics comparison

GET /api/training/features
  → Returns: Features used in each training run

GET /api/monitoring/alerts/summary
  → Returns: Alert count, resolution time, channels active
```

---

### B. PostgreSQL Changes

```sql
-- NEW FIELDS/TABLES

ALTER TABLE risk_model_training_jobs
  ADD COLUMN features_used JSONB,          -- Which features in this training
  ADD COLUMN data_quality JSONB,           -- Missing %, outliers %, duplication %
  ADD COLUMN dataset_characteristics JSONB; -- Row count, date range, etc.

ALTER TABLE risk_retraining_config
  ADD COLUMN last_triggered_at TIMESTAMP,
  ADD COLUMN last_triggered_reason TEXT;

CREATE TABLE risk_model_alerts (          -- NEW: Alert notification log
  id TEXT PRIMARY KEY,
  drift_id TEXT REFERENCES risk_model_drift_detected(id),
  channel TEXT,  -- 'slack', 'email', 'pagerduty'
  sent_at TIMESTAMP,
  resolved_at TIMESTAMP,
  resolved_by TEXT
);
```

---

### C. UI Changes (React)

```typescript
// TAB COMPONENTS — All data from real sources

1. OverviewTab
   - Load gates from /api/metrics/gates
   - Load blockers from /api/metrics/gates/blockers
   - Load score distribution from /api/metrics/performance
   - Compute: Gate status = all criteria met?

2. ModelRegistryTab
   - Load versions from /api/models
   - Load approvals from /api/models/approvals (NEW endpoint)
   - Load lineage from /api/models (add lineage field)
   - Show: All 4 models (gate0 prod, v3.0 staging, gate1 candidate, v2.1 deprecated)

3. PerformanceTab
   - Load production metrics from /api/metrics/performance
   - Load staging metrics from /api/models + /api/metrics/performance
   - Load history from /api/metrics/history
   - Load comparison from /api/metrics/performance/comparison
   - Compute: Latency aggregation from /api/metrics/performance (add P95/P99)

4. TrainingDataTab
   - Load jobs from /api/jobs
   - Load dataset info from /api/metrics/performance (training_samples, test_samples)
   - Load retraining config from /api/training/config
   - Load quality metrics from /api/training/data-quality

5. MonitoringTab
   - Load drift alerts from /api/metrics/drift
   - Load drift history from /api/monitoring/drift-history
   - Load alert summary from /api/monitoring/alerts/summary
   - Show: Timeline of drift, actions taken, resolution status
```

---

## 7. HIGH-LEVEL IMPLEMENTATION PLAN (Sections)

### Phase 1: Data Connectivity (0-2 hours)
- Ensure cbp-risk-engine is running and accessible
- Test all /api endpoints
- Verify PostgreSQL queries work
- Log what data is available vs missing

### Phase 2: Missing Data Synthesis (2-4 hours)
- Compute blocking items from gate metrics
- Aggregate latency percentiles
- Create model comparison dataset
- Add data quality calculation

### Phase 3: Backend Enhancements (4-8 hours)
- Add new endpoints (/blockers, /comparison, /features, /alerts)
- Implement data aggregations
- Add database fields for missing data
- Wire up alert notification system

### Phase 4: Frontend Integration (6-10 hours)
- Connect each tab to real API endpoints
- Remove hardcoded mock data
- Implement data refresh/polling
- Add error handling and loading states

### Phase 5: Validation & Testing (2-4 hours)
- Verify all tabs show real data
- Test data consistency across tabs
- Performance profiling (query performance)
- End-to-end validation with live system

---

## 8. CRITICAL DECISIONS FOR USER INPUT

**Before implementation, need answers to:**

1. **Approval Workflow Storage**
   - Keep approvals ONLY in cbp-risk-engine SQLite?
   - Or sync to PostgreSQL for audit trail?
   - Or dual-write?

2. **Missing Data Priority**
   - Which missing data is blocking (must have before launch)?
   - Which is nice-to-have (can be computed later)?

3. **Real Training Data**
   - Use actual shipments (1,399 records) for training model comparison?
   - Or need more data before comparison is meaningful?

4. **Alert Notification Integration**
   - Will alerts be sent to Slack/Email in production?
   - Or is monitoring tab display-only for now?

5. **Data Refresh Strategy**
   - How often should UI poll /api endpoints?
   - Real-time (WebSocket) or periodic (every 30s)?

---

**Status:** Design phase complete. Ready for user input on critical decisions, then implementation planning.
