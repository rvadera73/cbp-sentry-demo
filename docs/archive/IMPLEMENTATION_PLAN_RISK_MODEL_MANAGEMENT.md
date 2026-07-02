# Risk Model Management Tab — Complete Implementation Plan

**Status**: Ready to Execute (All 3 Tasks)  
**Date**: 2026-06-25  
**Owner**: Claude Code  

---

## Current State Snapshot

### cbp-risk-engine (Separate Repo, Port 8010)
- **MLflow Model**: `transshipment_classifier`
- **Versions**: 2 (v1: bootstrap, v2: trained)
- **Current Production**: v1 (bootstrap, currently aliased as 'production')
- **Tagging**: Uses MLflow tags for metadata (job_id, model_type, notes, promoted_by, promoted_at)
- **Approvals**: approvals.db tracks 3-voter quorum voting
- **Gap**: No CBP gate metadata (gate_level, cbp_version_id, corridor)

### cbp-sentry (Main Repo, Port 8000)
- **Duplicate Tables**: risk_models, risk_model_approvals, risk_model_training_jobs (empty or mock data)
- **Real Tracking Tables**: model_score_history (6,980 rows), dataset_baselines (1 row), performance_gate_results (6 rows)
- **Current Model**: gate0-rule-engine-v1.0 (registered with baseline)
- **Gap**: Doesn't link to MLflow registry in cbp-risk-engine

---

## TASK A: Verify & Tag Models in cbp-risk-engine

### Goal
Ensure current models are in cbp-risk-engine, add CBP metadata tags, create mapping to Gate 0.

### Steps

#### A1: Map Existing Models to CBP Gate 0

```
Existing MLflow Model v1 (bootstrap)
  → Should become: gate0-rule-engine-v1.0 (CBP reference)
  
Existing MLflow Model v2 (trained)
  → Should become: gate0-xgboost-retrain-v1.0 (experimental, not production)
```

#### A2: Add CBP Gate Tags via MLflow

Create script to tag model versions with:
- `gate`: 0 (CBP Gate level)
- `cbp_model_id`: "gate0-rule-engine-v1.0"
- `cbp_status`: "PRODUCTION" (for v1) or "EXPERIMENTAL" (for v2)
- `corridor_primary`: "VN"
- `maturity_level`: 15 (15% = Gate 0)
- `confidence_interval_pts`: 17

#### A3: Sync to cbp-sentry (One-Way Reference)

Create a sync record in cbp-sentry's risk_models table that references MLflow:
```sql
INSERT INTO risk_models 
  (model_id, version, gate, mlflow_version_id, cbp_status, created_at)
VALUES
  ('gate0-rule-engine-v1.0', '1', 0, '1', 'PRODUCTION', NOW())
```

---

## TASK B: Design Risk Model Management Tab UI

### Architecture: Gates vs. Stages

```
GATES (ops-defined, CBP program maturity)
  Gate 0 [15%] ← Current, Exit criteria not met
  Gate 1 [30%]
  Gate 2 [50%]
  Gate 3 [70%]
  Gate 4 [90%] ← Production end-state

STAGES (ML-defined, deployment lifecycle within a gate)
  Registered → Staging → Production → Deprecated → Archived
```

### Tab Structure (5 Tabs)

#### Tab 1: Overview
- Active model card: gate0-rule-engine-v1.0, v1, Production, 15% maturity
- Gate lifecycle tracker (visual: Gate 0 🔴 → Gate 1 ⚪ → Gate 2 ⚪ → ...)
- Gate 0 exit criteria checklist:
  - ✅ 7-factor rule engine
  - ✅ Referral package generation
  - ❌ Feature write-back (element9_is_mismatch, dwell_days)
  - ❌ Senzing entity chain in Table 3-5
- Quick actions: View Details, Compare Versions, Request Approval
- Active alerts: "2 items blocking Gate 0 closure"

#### Tab 2: Model Registry
- Version list (all stages):
  - gate0-rule-engine-v1.0 (v1) → Production, AUC=0.99, trained=2026-06-24
  - v2.1-rule-based → Deprecated, never deployed
  - (future) gate1-lgbm-v1.0 → Registered (when Gate 1 starts)
- Lineage chain visualization
- Action buttons per version: Promote, Rollback, Shadow Deploy, Deprecate
- Approval workflow status (3-voter quorum tracker)

#### Tab 3: Performance
- Score distribution chart (histogram by risk tier)
- Key metrics table: AUC, Precision, Recall, FPR @ threshold ≥65
- Confidence interval tracker: ±17 pts (tightens as maturity increases)
- Comparison view: Current model vs. previous model on same shipments
- Drift monitoring: Feature distributions over time

#### Tab 4: Training & Data
- Training run history (from cbp-risk-engine)
- Dataset baseline: 1396 shipments, SHA-256 hash, feature completeness %
- Feature audit: Which enriched columns are populated (dwell_days=0%, element9_is_mismatch=0%)
- Reference data freshness: AD/CVD rates (stale: 30d+), Comtrade (stale: 30d+)
- Retraining config: Manual trigger + automated schedule (future)

#### Tab 5: Monitoring & Feedback
- Officer feedback summary: Hold/Examine/Clear outcomes collected (7 total towards Gate 1 requirement of 200)
- Prediction log: Recent cases scored, officer Hold/Examine/Clear outcomes
- Score trend: Moving average score over 7 days (detect drift)
- Model drift detection: KS test per feature (elevated features in red)

### Styling
- Match Referral Package V2: CBP blue borders (#005EA2), white backgrounds, zebra table rows
- Header: "RISK MODEL MANAGEMENT" with active model badge and gate indicator
- Tab bar: Active = blue underline, inactive = gray text

### API Endpoints Needed

From cbp-risk-engine (via `/api/mcp/*` proxy):
```
GET  /api/mcp/models                          → List all versions
GET  /api/mcp/models/production                → Get active model
GET  /api/mcp/models/{version}/metrics        → Performance metrics
GET  /api/mcp/metrics/performance             → Detailed metrics
GET  /api/mcp/metrics/gates                   → Gate status + exit criteria
GET  /api/mcp/metrics/history                 → Historical metrics
GET  /api/mcp/metrics/drift                   → Drift detection results
POST /api/mcp/models/{version}/approve        → Submit approval vote
POST /api/mcp/models/{version}/promote        → Promote to production
GET  /api/mcp/jobs                            → Training job history
GET  /api/mcp/jobs/{job_id}                   → Job details
```

From cbp-sentry (local):
```
GET  /api/risk-models/gate/{gate_id}/exit-criteria   → Gate 0 exit criteria
GET  /api/risk-models/dataset-baseline                → Dataset snapshot info
GET  /api/risk-models/feedback/summary                → Officer feedback stats
GET  /api/risk-models/predictions/{shipment_id}      → Recent predictions
```

---

## TASK C: Safe Migration Script

### Goal
Delete duplicate tables from cbp-sentry, keep operational tracking tables.

### Delete List (SAFE - Data backed up in Gate 0 commit)
```sql
DROP TABLE IF EXISTS risk_models;              -- Metadata (duplicate with MLflow)
DROP TABLE IF EXISTS risk_model_approvals;     -- Approvals (use approvals.db instead)
DROP TABLE IF EXISTS risk_model_training_jobs; -- Training (use MLflow instead)
DROP TABLE IF EXISTS risk_model_metrics;       -- Metrics (use MLflow instead)
DROP TABLE IF EXISTS risk_model_drift_detected;-- Drift (use MLflow instead)
DROP TABLE IF EXISTS risk_model_predictions;   -- Predictions (use runtime.db instead)
```

### Keep (Operational)
```sql
-- These track CBP enforcement outcomes, not ML infrastructure
KEEP: model_score_history       -- Shipment ID → calculated risk score
KEEP: dataset_baselines         -- Dataset snapshot (hash, row count)
KEEP: performance_gate_results  -- Gate 0 baseline metrics (PPV, recall)
```

### Steps
1. Backup cbp_sentry.db locally
2. Remove duplicate tables
3. Remove `/api/risk-models/dashboard` endpoint (hardcoded mock data)
4. Verify UI still works (calls `/api/mcp/*` instead)
5. Git commit with safe deletion note

---

## Implementation Sequence

### Phase 1: Tag Models in cbp-risk-engine (30 min)
1. Add CBP metadata tags to MLflow versions (A1-A2)
2. Verify tags appear in `/api/mcp/models` response
3. Test that UI can read gate metadata

### Phase 2: Design & Build Risk Model Management Tab (4 hours)
1. Create component structure (5 tabs)
2. Wire up to `/api/mcp/*` endpoints
3. Build Overview tab (gate tracker, exit criteria)
4. Build Model Registry tab (version list, approval workflow)
5. Build remaining tabs (Performance, Training, Monitoring)
6. Style with CBP design system

### Phase 3: Safe Cleanup (1 hour)
1. Backup database
2. Run migration script to delete duplicates
3. Remove hardcoded dashboard endpoint
4. Update API router registration
5. Test end-to-end

### Phase 4: Verify & Document (1 hour)
1. Test full workflow: View models → Approve → Promote
2. Verify no data loss
3. Document gate definitions in Git
4. Tag commit: v0.15-risk-model-management-redesigned

---

## Rollback Plan

If something breaks:
1. Restore cbp_sentry.db from backup
2. Revert API changes in sentry-api
3. Re-enable `/api/risk-models/dashboard` endpoint temporarily

---

## Success Criteria

- [ ] cbp-risk-engine models tagged with CBP gate metadata
- [ ] Risk Model Management tab displays gate progression (Gate 0 → 1 → 2 ...)
- [ ] Tab shows Gate 0 exit criteria (2 items blocking, clear action items)
- [ ] Approval workflow visible (3-voter quorum, voting history)
- [ ] No orphaned data in cbp-sentry (duplicate tables deleted)
- [ ] UI calls cbp-risk-engine only (no hardcoded mock data)
- [ ] Styling matches Referral Package V2

