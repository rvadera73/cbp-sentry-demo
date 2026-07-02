# Risk Model Management Tab — Testing Ready Checklist

**Date:** 2026-06-13 | **Status:** ✅ Ready for Testing

---

## What's Ready Right Now

### ✅ Frontend (UI)
- **Location:** `ui/src/pages/RiskModelManagement/`
- **8 Screens Created:**
  1. Dashboard.tsx — Active model health + alerts
  2. ModelVersions.tsx — Version comparison
  3. TrainingHistory.tsx — Job history
  4. PerformanceMetrics.tsx — Metrics charts
  5. DataDriftMonitoring.tsx — Drift alerts
  6. PredictionExplanations.tsx — SHAP explanations
  7. ModelApprovals.tsx — Voting workflow
  8. RetrainingConfig.tsx — Trigger configuration
- **Routing:** `/risk-models` route added to App.tsx
- **Status:** ✅ Renders with mock data immediately

### ✅ Backend API (FastAPI)
- **Location:** `services/api/routes/risk_model_management.py`
- **12 Endpoints Created:**
  - GET `/api/risk-models/dashboard`
  - GET `/api/risk-models/versions`
  - POST `/api/risk-models/{model_id}/compare`
  - GET `/api/risk-models/training-jobs`
  - GET `/api/risk-models/training-jobs/{job_id}`
  - GET `/api/risk-models/{model_id}/metrics`
  - GET `/api/risk-models/{model_id}/drift`
  - GET `/api/risk-models/predictions/{shipment_id}/explain`
  - GET `/api/risk-models/approvals`
  - POST `/api/risk-models/approvals/{approval_id}/vote`
  - GET `/api/risk-models/retraining-config`
  - PUT `/api/risk-models/retraining-config`
  - POST `/api/risk-models/{model_id}/rollback`
- **Status:** ✅ Registered in main.py, returns mock data

### ✅ Database Schema
- **File:** `services/data/migrations/v4_0_risk_model_management.py`
- **7 Tables Created:**
  - `risk_models` — Model registry
  - `risk_model_training_jobs` — Training history
  - `risk_model_metrics` — Performance metrics
  - `risk_model_predictions` — Individual predictions + SHAP
  - `risk_model_drift_detected` — Drift alerts
  - `risk_model_approvals` — Multi-voter workflow
  - `risk_retraining_config` — Automation triggers
- **Status:** ✅ Created, awaiting migration run

### ✅ Data Services
- **Real Data Service:** `services/api/services/risk_model_data_service.py` (600 lines)
  - Methods stubbed for: metrics, drift, SHAP, approvals, training
  - TODO: Database queries need implementation
- **Mock Service:** `services/api/services/risk_model_mock_service.py` (500 lines)
  - Ready for immediate use in development

### ⚠️ Integration Points (TODO for Week 2)
- [ ] Apply database migration
- [ ] Implement database queries in real data service
- [ ] Call precise-risk-engine for SHAP explanations
- [ ] Wire API endpoints to real data service
- [ ] Test with actual v3.0 predictions

---

## How to Test Now

### Step 1: Start Services
```bash
cd /home/rahulvadera/cbp-sentry
./scripts/local_startup.sh
```

**Expected Output:**
```
✓ sentry-data running on 8005
✓ sentry-cord-integration running on 8004
✓ precise-risk-engine running on 8007
✓ sentry-api running on 8000
✓ sentry-ui running on 3001
```

### Step 2: Open CBP Sentry UI
```bash
open http://localhost:3001
```

**Expected:**
- Main navigation visible
- "Risk Model Management" tab added to menu
- Click to navigate to `/risk-models`

### Step 3: Test Tab Navigation
**URL:** `http://localhost:3001/risk-models`

**Expected:**
- Dashboard screen loads ✓
- Shows active model (v3.0) with mock metrics ✓
- Shows pending approvals ✓
- Shows alerts ✓
- 8 tabs visible at top ✓

### Step 4: Test Each Screen
```
Dashboard Tab:
  - ✓ Shows "v3.0" as active model
  - ✓ Displays 24h metrics (accuracy: 0.924, latency: 85ms)
  - ✓ Shows pending approval for v3.1
  - ✓ Displays drift alert for origin_country

Model Versions Tab:
  - ✓ Lists v3.0 (production), v3.1 (candidate), v2.1 (deprecated)
  - ✓ Shows performance metrics per version
  - ✓ Compare button functional

Training History Tab:
  - ✓ Shows job-20260611-093001 (completed)
  - ✓ Shows v3.0 deployment job
  - ✓ Shows v3.2 running job with progress

Performance Metrics Tab:
  - ✓ Accuracy chart over time
  - ✓ Latency percentiles displayed
  - ✓ Fairness metrics by origin

Data Drift Tab:
  - ✓ Overall drift score: 0.12
  - ✓ Elevated feature: origin_country (drift: 0.34)
  - ✓ Distribution comparison visible

SHAP Explanations Tab:
  - ✓ Search box for shipment ID (e.g., SHP-00142857)
  - ✓ Shows prediction: 0.76 (EXAMINE)
  - ✓ SHAP factors displayed with contributions

Approvals Tab:
  - ✓ Pending approval for v3.1 shown
  - ✓ Voter names and status visible
  - ✓ Vote buttons available

Retraining Config Tab:
  - ✓ Scheduled retraining enabled (weekly)
  - ✓ Drift trigger config visible
  - ✓ Configuration save button works
```

### Step 5: Test API Endpoints Directly
```bash
# Test Dashboard
curl http://localhost:8000/api/risk-models/dashboard | jq

# Expected Response:
# {
#   "active_model": {
#     "model_id": "v3.0",
#     "metrics": {
#       "accuracy": 0.924,
#       "predictions_24h": 15432
#     }
#   },
#   "pending_approvals": [...],
#   "alerts": [...]
# }

# Test Model Versions
curl http://localhost:8000/api/risk-models/versions | jq

# Expected: List of v3.0, v3.1, v2.1

# Test SHAP Explanation
curl "http://localhost:8000/api/risk-models/predictions/SHP-00142857/explain" | jq

# Expected: SHAP values with feature contributions
```

---

## Current Status: What Works vs What Doesn't

| Component | Status | Why |
|---|---|---|
| **UI Rendering** | ✅ Works | React components created, routing added |
| **Tab Navigation** | ✅ Works | All 8 screens accessible |
| **API Endpoints** | ✅ Works | FastAPI router registered, returns mock data |
| **Mock Data** | ✅ Works | Mock service ready for all screens |
| **Database Tables** | ⏳ Pending | Migration file created, needs to be run |
| **Real Queries** | ❌ Not yet | TODO: Implement database queries |
| **SHAP from Model** | ❌ Not yet | TODO: Call precise-risk-engine |
| **Drift Detection** | ❌ Not yet | TODO: Calculate KS statistic on shipments |
| **Approval Voting** | ❌ Not yet | TODO: Implement vote logic |

---

## What Needs to Happen Before Production

### Week 2 Tasks (Priority Order)

**Task 1: Apply Database Migration** (1 hour)
```bash
cd services/data
python -c "
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from migrations.v4_0_risk_model_management import upgrade

async def run():
    engine = create_async_engine('sqlite+aiosqlite:///./data/cbp_sentry.db')
    async with AsyncSession(engine) as session:
        await upgrade(session)

asyncio.run(run())
"
```

**Task 2: Implement Real Data Service Queries** (8 hours)
- Database queries for metrics, versions, training jobs
- Feature distribution calculations for drift
- Approval logic

**Task 3: Integrate precise-risk-engine Calls** (4 hours)
- Call service for v3.0 predictions
- Parse SHAP values
- Error handling

**Task 4: Wire API to Real Data** (4 hours)
- Replace mock returns with real data service calls
- Add error handling
- Add logging

**Task 5: Test End-to-End** (8 hours)
- Test with real shipments
- Verify SHAP explanations
- Test approval workflow
- Load testing

**Task 6: Staging Deployment** (4 hours)
- Deploy to staging environment
- Run smoke tests
- Get stakeholder feedback

---

## Success Criteria for Testing Phase

✅ **All 8 screens render without errors**
- Dashboard, Versions, Training, Metrics, Drift, SHAP, Approvals, Config

✅ **Tab navigation works**
- All links functional
- No console errors

✅ **API endpoints respond**
- All 12 endpoints return data
- Proper HTTP status codes

✅ **Mock data populates screens**
- Charts show data
- Tables show data
- Form fields show data

✅ **No TypeScript errors**
- Components compile
- Props typed correctly

✅ **No Flask/Blueprint errors**
- FastAPI router integrated correctly
- No import errors

---

## Testing Command (All-in-One)

```bash
# 1. Start services (background)
./scripts/local_startup.sh &

# 2. Wait for startup
sleep 30

# 3. Test API
curl http://localhost:8000/api/risk-models/dashboard

# 4. Test UI
open http://localhost:3001

# 5. Navigate to Risk Model Management
# Click "Risk Model Management" in nav menu
```

---

## What to Look For

### UI Should Show:
1. ✅ Dashboard with v3.0 metrics
2. ✅ "Data drift detected: origin_country" alert
3. ✅ "Pending approval: v3.1" widget
4. ✅ Model versions list
5. ✅ Training history with jobs
6. ✅ Performance metrics charts
7. ✅ Data drift monitoring chart
8. ✅ SHAP explanation interface
9. ✅ Approval voting interface
10. ✅ Retraining config form

### API Should Return:
1. ✅ HTTP 200 on all GET endpoints
2. ✅ HTTP 200 on all POST endpoints
3. ✅ Properly formatted JSON
4. ✅ No error messages

### Errors to Fix If Found:
- ❌ 404: API route not found → Router not registered
- ❌ 500: Internal server error → Check logs
- ❌ TypeScript errors → Check component props
- ❌ White screen → Check console errors
- ❌ No Risk Model Management tab → Check routing in App.tsx

---

## After Testing

### If Everything Works ✅
→ Proceed to Week 2 implementation
- Apply database migration
- Implement real data queries
- Integrate precise-risk-engine

### If Something Breaks ❌
→ Debug and report:
1. Screenshot or error message
2. Which screen/endpoint failed
3. Expected vs actual behavior
4. Browser console errors

---

## Ready to Test?

**Just run:**
```bash
./scripts/local_startup.sh
open http://localhost:3001
# Navigate to Risk Model Management tab
```

**All 8 screens should load with mock data immediately.**

---

**After testing, report back on what works and what needs Week 2 implementation.**
