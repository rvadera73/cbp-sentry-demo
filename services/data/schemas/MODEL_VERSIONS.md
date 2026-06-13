# Model Versions & Database Snapshots

## Overview

This document tracks the database snapshots and model versions to enable safe switching between v2.1 (legacy) and v3.0 (precise).

---

## v2.1 (Legacy Rule-Based Model)

**Status:** Frozen (baseline snapshot)

**Database Snapshot:**
- Location: `backups/cbp_sentry_v2.1_baseline_*.db`
- Created: 2026-06-13
- Size: 3.0 MB
- Tables: 27
- Model Active: v2.1 (7-factor rule-based, 110% weights)

**Risk Scoring:**
- Factors: corridor, vessel, manifest (fixed weights, overweighted)
- Gates: 3 (H1, H2, H3 horizons)
- Score Range: 0-100
- Latency: ~50ms

**To Restore (Rollback if v3.0 fails):**
```bash
./scripts/restore_to_v2.1.sh backups/cbp_sentry_v2.1_baseline_*.db
```

---

## v3.0 (Precise Risk Model - XGBoost)

**Status:** In Development (applying migrations)

**Database:**
- Location: `data/cbp_sentry.db`
- Tables: 34 (27 existing + 7 new risk model tables)
- New Tables:
  - `risk_models` - Model registry with versions
  - `risk_model_training_jobs` - Training history
  - `risk_model_metrics` - Performance metrics (time-series)
  - `risk_model_predictions` - Individual predictions + SHAP
  - `risk_model_drift_detected` - Data/model drift alerts
  - `risk_model_approvals` - Multi-voter workflow
  - `risk_retraining_config` - Automated triggers

**Risk Scoring:**
- Framework: XGBoost classifier + Isolation Forest anomaly
- Features: 72 CBP fields → 7 weighted factors (100% normalized)
- Gates: 3 (Deterministic rules → ML classifier → Uncertainty)
- Score Range: 0-100
- Confidence: 0-1.0
- Latency: <100ms
- Explainability: SHAP values for every prediction

**Training Data:**
- `/data/training_data.csv` - 10,287 samples (287 positive, 10,000 negative)
- `/data/feature_matrix_72.csv` - 72 engineered features
- Performance: AUC=0.94, Precision=0.92, Recall=0.91

**Deployment Timeline:**
- Phase 1 (NOW): Database migrations, snapshot strategy
- Phase 2 (Today): MLflow integration
- Phase 3 (Today): DVC data versioning
- Phase 4 (Today): Risk Model Management UI ↔ MLflow connection

---

## Switching Between v2.1 and v3.0

### Monitor Current Model Version

```bash
# Check which model is active in deployment
grep MODEL_VERSION_ACTIVE /home/rahulvadera/cbp-sentry/docker-compose.yml
```

### Rollback v3.0 → v2.1 (If Issues Occur)

```bash
# 1. Find the v2.1 snapshot
ls -lh backups/cbp_sentry_v2.1_baseline_*.db

# 2. Restore database
./scripts/restore_to_v2.1.sh backups/cbp_sentry_v2.1_baseline_20260613_*.db

# 3. Restart services (automatic in script)

# 4. Verify
curl http://localhost:8000/api/risk-models/dashboard | jq '.active_model.model_id'
# Should return: "v2.1"
```

### Promote v3.0 → Production

```bash
# 1. Verify model in Risk Model Management UI
#    - Check "Model Approvals" screen
#    - Get 2 approvals for v3.0 promotion

# 2. Promote in database
# UPDATE risk_models SET status='production' WHERE model_id='v3.0'

# 3. Update feature flag
# export MODEL_VERSION_ACTIVE=v3.0

# 4. Restart API
docker compose restart sentry-api
```

---

## Backup Strategy

**Frequency:**
- Automatic snapshots after each retraining job
- Manual snapshots before major deployments

**Retention:**
- v2.1 snapshot: Forever (rollback baseline)
- v3.0 snapshots: Keep last 3 (daily snapshots during validation)

**Storage:**
- Local: `backups/` directory
- Cloud: (TBD - DVC + GCS in Phase 3)

---

## Monitoring

Track model versions and health:
- Risk Model Management dashboard: `http://localhost:3001/risk-models`
- MLflow UI: `http://localhost:5000` (Phase 2)
- Database queries:
  ```sql
  SELECT model_id, status, deployed_at FROM risk_models;
  SELECT * FROM risk_model_approvals WHERE status='pending';
  ```
