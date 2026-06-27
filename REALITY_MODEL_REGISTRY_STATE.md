# REALITY CHECK: Model Registry & Versioning Actual State
## What Actually Exists vs. What We Designed

**Date:** June 25, 2026  
**Status:** Honest Assessment  
**Finding:** We've been designing theory. The actual system doesn't have what we described.

---

## PART 1: WHAT WE DESIGNED (Theory)

We created designs for:
- ✗ Model versioning system (v3.0, v3.1, v3.2...)
- ✗ Staging models (5% traffic, shadow deploy)
- ✗ Rollback capability
- ✗ 3-voter approval workflow
- ✗ Change management (weights, parameters)
- ✗ Training & Data pipeline integration

**Status:** Beautiful design documents. None of it actually exists in the code.

---

## PART 2: WHAT ACTUALLY EXISTS (Reality)

### Database
```
cbp_sentry.db:
└─ Tables: (ONLY 1)
   └─ shipments
      ├─ id, manifest_id
      ├─ shipper_name, consignee_name
      ├─ origin_country, destination_country
      ├─ risk_score (the score), hs_code, vessel_name, dwell_days
      ├─ element9_is_mismatch, element9_declared_country
      ├─ ad_cvd_applicable, ad_cvd_rate
      └─ NO model_id, NO model_version, NO version_history
         NO approval_workflow, NO staging_flag, NO rollback_flag

Missing tables:
├─ risk_models (no model registry)
├─ risk_model_versions (no versioning)
├─ risk_model_approvals (no voting)
├─ risk_model_training_jobs (no training history)
├─ risk_model_weights (no parameter tracking)
├─ risk_model_rollback_history (no rollback history)
└─ risk_model_staging (no staging records)
```

### Scoring Engine
```
services/api/risk_scoring_engine.py:
└─ RiskScoringEngine class
   ├─ score_shipment(shipment) → RiskScoreBreakdown
   ├─ 7-factor rule engine (Documentation, Commodity, Routing, Party, Corridor, Pattern, Time)
   ├─ XGBoost integration (36 features)
   ├─ Isolation Forest for AIS anomalies
   ├─ LightGBM for legacy patterns
   └─ NO versioning, NO model switching, NO staging
      One engine. One model. No alternatives.
```

### API Endpoints (Main)
```
services/api/main.py:
└─ Endpoints that exist:
   ├─ POST /api/risk-scoring/comprehensive → Score a shipment
   │  └─ Uses: RiskScoringEngine (hardcoded, no version parameter)
   ├─ GET /api/risk-models/performance/current-gate
   │  └─ Default model_id: "v3.0" (hardcoded query default)
   ├─ GET /api/risk-models/performance/metrics
   │  └─ Default model_id: "v3.0" (hardcoded)
   ├─ GET /api/risk-models/performance/gate/{gate_id}
   │  └─ Default model_id: "v3.0" (hardcoded)
   └─ GET /api/risk-models/performance/mlflow-config
      └─ Default model_id: "v3.0" (hardcoded)
```

### Risk Models Routes (Mock Data)
```
services/api/routes/risk_models.py:
└─ Endpoints that EXIST (but return MOCK/HARDCODED data):
   ├─ GET /api/risk-models/dashboard
   │  └─ Returns hardcoded:
   │     ├─ active_model: {model_id: "v3.0", version: "v3.0", status: "production"}
   │     ├─ pending_approvals: [{model_id: "v3.1", status: "under_review"}]
   │     └─ alerts: [{type: "data_drift", drift_score: 0.34}]
   │
   ├─ GET /api/risk-models/versions
   │  └─ Returns empty list (no actual versions stored)
   │
   ├─ GET /api/risk-models/training-jobs
   │  └─ Returns empty list (no training jobs stored)
   │
   └─ [Other endpoints exist in routes file but return mock data]

Key point: The data in the API IS MOCKED.
The shipments table has NO column to track which model scored it.
```

---

## PART 3: WHAT THIS MEANS

### Current Situation
```
When a shipment is scored:
1. API receives shipment data
2. RiskScoringEngine.score_shipment(shipment) is called
3. Risk score is computed using CURRENT weights/rules (whatever is in the code)
4. Score stored in shipments.risk_score (database column)
5. NO TRACKING OF:
   ├─ Which version of the model computed this?
   ├─ What were the weights at that moment?
   ├─ Can we compare to previous model version?
   └─ Can we rollback if this version is bad?

Answer: NO. There is no tracking, no versioning, no way to rollback.
```

### Production Model
```
What is "production"?
├─ The hardcoded RiskScoringEngine.py in the code
├─ Whatever weights are defined in RiskModelConfig
├─ Currently: 7-factor rule engine + XGBoost (60/40 or 70/30, unclear)
├─ Deployed by: Rebuilding the Docker image and restarting services
└─ Rollback by: Reverting git commit and rebuilding Docker image

That's it. No sophisticated model switching, no staging, no approval workflow.
```

### Staging & Versioning
```
Does "staging" exist?
├─ NO database concept of staging
├─ NO ability to route 5% traffic to v3.1 and 95% to v3.0
├─ NO parallel model serving infrastructure
└─ NO shadow deployment capability

Can we A/B test models?
├─ NO, only one model runs at a time
├─ To test new model, must deploy to production (scary)
└─ Or manually score test data offline (tedious)
```

### Rollback
```
How to rollback if a model breaks?
├─ Option 1: Manually find the git commit before the change
├─ Option 2: Revert the code, rebuild Docker, restart services
├─ Option 3: Hope you have a database backup with old scores
└─ There is NO automated rollback mechanism

Timeline: 10-30 minutes (depending on Docker build time)
```

---

## PART 4: CURRENT ACTUAL WORKFLOW (Not Theory)

```
REALITY: How Model Changes Actually Happen Today

Step 1: DATA SCIENTIST WANTS TO TEST WEIGHT CHANGE
├─ Change element9_weight from 20 → 25
├─ Location: services/api/risk_models.py (hardcoded)
├─ Or: RiskModelConfig in risk_models.py

Step 2: TEST LOCALLY
├─ Run: python test_risk_scoring.py
├─ Check: Do scores improve on test shipments?
├─ Manual inspection of results

Step 3: COMMIT TO GIT
├─ git add services/api/risk_models.py
├─ git commit -m "Increase element9_weight: 20→25"
├─ git push origin main

Step 4: CI/CD PIPELINE
├─ GitHub Actions runs (if configured)
├─ Builds Docker image: sentry-api:latest
├─ Pushes to Docker registry
├─ (Or wait for manual deployment)

Step 5: DEPLOY TO PRODUCTION
├─ Manual: docker pull sentry-api:latest && docker-compose up -d sentry-api
├─ Or: Kubernetes deployment (if using K8s)
├─ OR: Run script: bash ./scripts/deploy-local.sh api

Step 6: MONITOR
├─ Watch logs: docker logs sentry-api | grep risk_score
├─ Check database: SELECT COUNT(*) WHERE risk_score > 50 (daily referral rate)
├─ Manual check: Is new weight causing problems?

Step 7: IF BAD → ROLLBACK
├─ git revert <commit>
├─ Rebuild Docker image
├─ Redeploy
├─ 10-30 minutes of broken predictions in between

Step 8: IF GOOD → CELEBRATE
├─ Keep it deployed
└─ Hope no other changes break it
```

**No:**
- Approval workflow (votes, voters, comments)
- Staging environment (5% traffic testing)
- A/B testing capability
- Automated rollback
- Parameter audit trail
- Training job versioning
- Model comparison metrics

---

## PART 5: WHAT THE DESIGN ASSUMES (But Doesn't Exist)

| Feature | Assumed | Actual |
|---------|---------|--------|
| Model Registry DB | Table with versions, status, metrics | ❌ DOESN'T EXIST |
| Approval Workflow | 3-voter voting system | ❌ DOESN'T EXIST |
| Staging Infrastructure | 5% traffic routing to v3.1, 95% to v3.0 | ❌ DOESN'T EXIST |
| Weight Tracking | DB table: model_version, parameters, changed_at | ❌ DOESN'T EXIST |
| Training History | Job logs, artifacts, backtest metrics | ❌ MINIMAL (MLflow exists but not integrated) |
| Rollback Mechanism | Click button → revert to previous | ❌ DOESN'T EXIST |
| Score Attribution | Each score tagged with model_id, version_id | ❌ DOESN'T EXIST |
| Data Drift Monitoring | Live alerting, staging metrics dashboard | ❌ PARTIALLY (alerts in mock API) |
| Approval Voting | 3-voter quorum, voting deadline, comments | ❌ DOESN'T EXIST |

---

## PART 6: WHAT WE NEED TO ACTUALLY BUILD

If we want the MLOps workflow we designed, we need to implement:

```
LAYER 1: Database Layer (NEW)
├─ Create tables:
│  ├─ risk_models (model_id, version, status, deployed_at, deployed_by)
│  ├─ risk_model_versions (version_id, framework, parameters_json, metrics_json)
│  ├─ risk_model_approvals (approval_id, model_id, voters, votes_json, deadline)
│  ├─ risk_model_staging (staging_id, model_id, traffic_percent, deployed_at)
│  ├─ risk_model_rollback_history (rollback_id, from_version, to_version, reason)
│  └─ shipment_model_attribution (shipment_id, model_version, scored_at)
└─ Data migrations (Alembic or raw SQL)

LAYER 2: Model Serving Layer (MAJOR CHANGE)
├─ Load multiple models into memory or Kubernetes pods
├─ Route traffic based on shipment_id hash or shadow deployment rules
├─ Support parallel model serving (e.g., Seldon Core, BentoML, or custom)
└─ Track which model scored which prediction

LAYER 3: API Layer (NEW ENDPOINTS)
├─ POST /api/risk-models/register → Register new model version
├─ POST /api/risk-models/{model_id}/approve → Submit for approval
├─ POST /api/risk-models/{model_id}/votes → Cast approval vote
├─ POST /api/risk-models/{model_id}/stage → Deploy to 5% staging
├─ POST /api/risk-models/{model_id}/promote → Promote to 100% production
├─ POST /api/risk-models/{model_id}/rollback → Revert to previous
├─ GET /api/risk-models/{model_id}/staging-metrics → Live comparison metrics
└─ GET /api/risk-models/audit → Full change audit trail

LAYER 4: UI Layer (Model Registry Tab)
├─ Show all 4 sections (Active | Pending | Staging | Archive)
├─ Show rule weights, metrics, deployment status
├─ Voting interface (for voters)
├─ Action buttons (Promote, Rollback, etc.)
└─ Staging metrics dashboard (real-time comparison)

LAYER 5: MLOps Workflow (Training Integration)
├─ Capture training runs in database
├─ Auto-backtest on historical data
├─ Compare against current production model
├─ Submit for approval with metrics
└─ Gate approval on backtest results

LAYER 6: Monitoring & Alerting (NEW)
├─ Track model performance over time
├─ Detect data drift (KS-stat, population shift)
├─ Alert if scores diverge from expected distribution
├─ Monitor staging metrics continuously
└─ Auto-rollback if critical thresholds exceeded (optional)
```

---

## PART 7: HONEST ASSESSMENT

**What we've accomplished (in code):**
- ✅ Risk scoring engine (works, computes scores)
- ✅ 7-factor rule engine (implemented)
- ✅ XGBoost integration (exists)
- ✅ Mock API endpoints (exist, return fake data)
- ✅ UI tabs (exist, show mock data)

**What's missing (needed for MLOps workflow):**
- ❌ Database model registry
- ❌ Approval workflow tables
- ❌ Staging infrastructure
- ❌ Model versioning in scoring logic
- ❌ Rollback mechanism
- ❌ Change audit trail
- ❌ 3-voter voting system
- ❌ A/B testing infrastructure

**Current reality:**
- One model at a time
- Changed by editing code
- Deployed by rebuilding Docker
- No voting, no staging, no rollback
- No way to track which model scored which prediction

---

## PART 8: OPTIONS FOR MOVING FORWARD

### OPTION A: Build Full MLOps System (Big Effort)
**Scope:**
- 3-4 weeks of development
- Database migrations (new tables)
- Model serving infrastructure (Kubernetes or custom)
- Full approval workflow
- Staging environment with traffic splitting
- Comprehensive testing

**Benefit:** Full MLOps capabilities as designed
**Cost:** High (dev time, infrastructure complexity, testing)

### OPTION B: Simplified MLOps (Medium Effort)
**Scope:**
- 1-2 weeks of development
- Add model registry database table (simple)
- Git-based versioning (use git tags/commits as versions)
- Manual approval (in Slack or email, logged in database)
- No staging, no traffic splitting
- Deploy to prod via docker rebuild (as is now)
- Can track which model scored which shipment

**Benefit:** Basic versioning + audit trail, much simpler than full system
**Cost:** Medium (dev time, but less infrastructure)

### OPTION C: No MLOps For Now (Minimal Effort)
**Scope:**
- Just improve the UI to show truth
- "Current Model: RiskScoringEngine.py (commit abc1234)"
- "Last changed: 2026-06-25 by Alex Kim"
- "Changes: element9_weight 20→25"
- Link to git commit for details

**Benefit:** Honest about actual state, low dev cost
**Cost:** Low, but no sophisticated versioning

### OPTION D: Phased Approach (Recommend)
**Phase 1 (Week 1-2):** Honest UI + Git-based tracking
├─ Show actual model (RiskScoringEngine)
├─ Show git history (changes made)
├─ Track deployment events (who deployed when)
└─ Database table: model_deployments (model_hash, deployed_by, deployed_at, changes)

**Phase 2 (Week 3-4):** Simple Approval Workflow
├─ Database table: model_approvals (model_hash, voters, votes, status)
├─ Slack bot: Ask for approvals before deploy
├─ Manual deployment (same Docker rebuild as now)
└─ Tracked approval in database

**Phase 3 (Week 5+):** Staging Infrastructure
├─ Model serving layer (Seldon/BentoML or custom)
├─ Traffic routing (5% to new, 95% to current)
├─ Live metrics comparison (latency, error rate, score agreement)
└─ One-click promotion

**Phase 4 (Week 8+):** Full MLOps
├─ Complete as designed in MLOPS_CHANGE_MANAGEMENT_DESIGN.md
└─ All features (voting, staging, rollback, etc.)

---

## PART 9: MY RECOMMENDATION

**Given your situation (no existing MLOps), I recommend OPTION D - Phased Approach:**

**Phase 1 (NOW):** Make the UI honest
1. Show what model is actually running (RiskScoringEngine.py)
2. Show git history of changes to that file
3. Create `model_deployments` table with audit trail
4. Model Registry tab shows:
   - Current model: "Gate 0 Rule Engine (v1.0)" deployed 2026-06-12 by Sarah Chen
   - Changes since then: element9_weight 20→25 (pending approval)
   - Previous versions: (git history)

**Phase 1 can be done in 3-5 days**, no infrastructure changes needed.

Then decide:
- Do you actually need staging (traffic splitting)?
- Do you actually need 3-voter approval?
- Can you accept manual approval (Slack/email)?

Based on answers, move to Phase 2, 3, or 4.

---

## QUESTIONS FOR YOU

Before we move forward, please clarify:

1. **What's your actual workflow today?**
   - Who makes decisions about model changes?
   - How are changes approved (or are they)?
   - How do you handle bad deployments?

2. **What's the minimum MLOps capability you need?**
   - Just track what changed? (Phase 1)
   - Track + approval workflow? (Phase 2)
   - Track + approval + staging? (Phase 3)
   - Full capabilities? (Phase 4)

3. **Do you have infrastructure for staging?**
   - Can you run 2+ model instances in parallel?
   - Do you have traffic routing capability (Kubernetes, load balancer)?
   - Or is one model at a time sufficient?

4. **What's your risk tolerance?**
   - Can you deploy breaking changes and roll back in 10 minutes?
   - Or do you need 7-14 days of staging before production?

Once you answer, I'll design Phase 1 implementation in detail.

