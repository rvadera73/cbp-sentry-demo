# Phase 1 Week 1 — Quick Reference Card

**Print this card for your desk. Everything you need on one page.**

---

## Startup Commands (Copy & Paste)

### Terminal 1: Backend API
```bash
cd /home/rahulvadera/cbp-sentry
source venv/bin/activate
cd services/api && python main.py --port 8000
```

### Terminal 2: Frontend Dev Server
```bash
cd /home/rahulvadera/cbp-sentry/ui
npm install
npm run dev
```

### Browser
```
http://localhost:3001
→ Log in
→ Click "Risk Model Management" in sidebar
```

---

## Database Migration (One Command)

```bash
cd /home/rahulvadera/cbp-sentry/services/data
python -c "
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from migrations.v4_0_risk_model_management import upgrade
async def run():
    engine = create_async_engine('sqlite+aiosqlite:///./data/cbp_sentry.db')
    async with AsyncSession(engine) as session:
        await upgrade(session)
        print('✓ Migration complete')
asyncio.run(run())
"
```

**Verify:** `sqlite3 services/data/data/cbp_sentry.db ".tables" | grep risk_model`

---

## Test API Endpoints (cURL)

```bash
# Dashboard
curl http://localhost:8000/api/risk-models/dashboard

# Versions
curl "http://localhost:8000/api/risk-models/versions?status=production"

# Training jobs
curl "http://localhost:8000/api/risk-models/training-jobs?status=completed"

# Metrics
curl "http://localhost:8000/api/risk-models/v3.0/metrics?hours=24"

# Drift
curl "http://localhost:8000/api/risk-models/v3.0/drift"

# Approvals
curl "http://localhost:8000/api/risk-models/approvals?status=pending"

# Vote
curl -X POST http://localhost:8000/api/risk-models/approvals/appr-v3.1-20260611/vote \
  -H "Content-Type: application/json" \
  -d '{"voter_name":"Sarah Chen","vote":"approve"}'
```

---

## UI Checklist (What to Test)

Visit http://localhost:3001 and verify:

- [ ] **Dashboard** — Shows v3.0 production, 92.4% accuracy, alerts
- [ ] **Model Versions** — Shows v3.0, v3.1, v2.1 with metrics
- [ ] **Training History** — Shows jobs with hyperparameters
- [ ] **Performance Metrics** — Shows 24h accuracy trend chart
- [ ] **Data Drift** — Shows feature drift scores
- [ ] **SHAP Explanations** — Shows feature contributions
- [ ] **Approvals** — Shows pending votes interface
- [ ] **Retraining Config** — Shows trigger settings

---

## File Locations

| What | Where |
|------|-------|
| Database migration | `services/data/migrations/v4_0_risk_model_management.py` |
| React components | `ui/src/pages/RiskModelManagement/` (8 files) |
| API endpoints | `services/api/routes/risk_models.py` |
| Mock data | `services/api/services/risk_model_mock_service.py` |
| Routing | `ui/src/App.tsx` (Line 21, 33-34) |
| Full guide | `PHASE1_WEEK1_IMPLEMENTATION.md` (this repo root) |

---

## Week 1 Deliverables Summary

| Component | Status | Lines | Files |
|-----------|--------|-------|-------|
| Database | ✅ | 634 | 1 |
| React UI | ✅ | 2,630 | 9 |
| API Routes | ✅ | 800 | 1 |
| Mock Service | ✅ | 500 | 1 |
| **TOTAL** | **✅** | **4,584** | **13** |

---

## Common Issues & Fixes

**Issue: API returns 404**
```bash
# Add blueprint to services/api/main.py:
# from routes.risk_models import bp as risk_models_bp
# app.register_blueprint(risk_models_bp)
# Then restart API
```

**Issue: React not showing Risk Model Management**
```bash
# Clear cache and restart
cd ui && rm -rf .next node_modules/.cache && npm run dev
```

**Issue: Database migration fails**
```bash
# Check lock
fuser services/data/data/cbp_sentry.db
# Start fresh if needed
rm -f services/data/data/cbp_sentry.db
# Re-run migration
```

**Issue: Console errors in browser**
```bash
# Check browser DevTools (F12)
# Look for import errors or missing components
# Verify path: ui/src/pages/RiskModelManagement/index.tsx exists
```

---

## Week 2 Preview

1. Apply database migration → Verify 7 tables created
2. Register API blueprint → Test endpoints return real data
3. Connect UI to API → Replace mock with database queries
4. Implement approval workflow → Multi-voter voting
5. Add drift detection → Feature distribution analysis
6. Integrate SHAP explanations → Feature importance
7. Write tests → Unit + integration coverage
8. Deploy to staging → Get stakeholder feedback

---

## Key Endpoints (12 Total)

```
GET    /api/risk-models/dashboard
GET    /api/risk-models/versions
GET    /api/risk-models/training-jobs
GET    /api/risk-models/{model_id}/metrics
GET    /api/risk-models/{model_id}/drift
GET    /api/risk-models/predictions/{shipment_id}/explain
GET    /api/risk-models/approvals
POST   /api/risk-models/approvals/{approval_id}/vote
POST   /api/risk-models/training-jobs
POST   /api/risk-models/{model_id}/compare
POST   /api/risk-models/{model_id}/drift/detect
PUT    /api/risk-models/retraining-config
```

---

## Key React Components (8 Total)

1. Dashboard — Active model summary + alerts
2. ModelVersions — Version list + approval voting
3. TrainingHistory — Job history + metrics
4. PerformanceMetrics — Time-series charts
5. DataDriftMonitoring — Feature drift analysis
6. PredictionExplanations — SHAP force plots
7. ModelApprovals — Multi-voter approval workflow
8. RetrainingConfig — Trigger configuration

---

## Database Tables (7 Total)

1. `risk_models` — Model registry
2. `risk_model_training_jobs` — Training history
3. `risk_model_metrics` — Time-series metrics
4. `risk_model_predictions` — Predictions + SHAP
5. `risk_model_drift_detected` — Drift alerts
6. `risk_model_approvals` — Approval workflow
7. `risk_retraining_config` — Retraining triggers

---

**Last updated:** June 13, 2026  
**Phase 1 Week 1:** ✅ Complete  
**Next:** Week 2 Integration (Start applying migration immediately)
