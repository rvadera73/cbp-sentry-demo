# Critical Finding: ALL Risk Model Management Tabs Use SYNTHETIC DATA

**Date:** June 25, 2026  
**Status:** URGENT - Design Fundamentally Flawed  
**Issue:** Everything we see in the UI is hardcoded mock data, not real data

---

## PROOF: The Endpoints Are Entirely Synthetic

### File: `services/api/routes/risk_models.py`

Every single endpoint follows this pattern:

```python
# TODO: Query database for X
# TODO: Query database for Y
# TODO: Calculate real metrics from database table Z

# But then just return hardcoded synthetic data:
dashboard_data = {
    'active_model': {'model_id': 'v3.0', 'status': 'production', ...},
    'pending_approvals': [{'model_id': 'v3.1', ...}],
    'alerts': [{'type': 'data_drift', ...}]
}
return jsonify(dashboard_data), 200
```

---

## Line-by-Line Evidence

### Endpoint 1: GET /api/risk-models/dashboard
```python
Line 122-125: # TODO: Query database for current active model
            # TODO: Fetch pending approvals
            # TODO: Check recent drift detections
            # TODO: Calculate 24h metrics from risk_model_metrics table

Line 127-173: dashboard_data = {
                'active_model': {
                    'model_id': 'v3.0',        # ← HARDCODED
                    'version': 'v3.0',         # ← HARDCODED
                    'status': 'production',    # ← HARDCODED
                    'deployed_at': '2026-06-12T14:35:00Z',  # ← HARDCODED
                    ...
                },
                'pending_approvals': [
                    {
                        'model_id': 'v3.1',    # ← HARDCODED
                        'status': 'under_review',  # ← HARDCODED
                        ...
                    }
                ],
                'alerts': [
                    {
                        'type': 'data_drift',  # ← HARDCODED
                        'drift_score': 0.34,   # ← HARDCODED
                        ...
                    }
                ]
            }

Result: Returns fake v3.0, fake v3.1, fake alerts ALWAYS
```

### Endpoint 2: GET /api/risk-models/versions
```python
Line 275-277: # TODO: Query risk_models table
            # TODO: Filter by status if provided
            # TODO: Sort by date or status

Line 281-327: models = [
                {
                    'model_id': 'v3.0',        # ← HARDCODED
                    'status': 'production',    # ← HARDCODED
                    'accuracy': 0.924,         # ← HARDCODED
                    ...
                },
                {
                    'model_id': 'v3.1',        # ← HARDCODED
                    'status': 'candidate',     # ← HARDCODED
                    'accuracy': 0.931,         # ← HARDCODED
                    ...
                }
            ]

Result: Always returns same 2 fake models regardless of query
```

### Endpoint 3: POST /api/risk-models/{model_id}/compare
```python
Line 419-421: # TODO: Query both models from risk_models table
            # TODO: Get performance metrics for both models
            # TODO: Calculate deltas and improvements

Then hardcodes comparison between fake v3.0 and fake v3.1
```

### Endpoint 4: GET /api/risk-models/training-jobs
```python
Line 564-566: # TODO: Query risk_model_training_jobs table
            # TODO: Filter by status if provided
            # TODO: Sort and limit results

Then returns hardcoded list of fake training jobs
```

### Endpoint 5: GET /api/risk-models/training-jobs/{job_id}
```python
Line 669-671: # TODO: Query risk_model_training_jobs table WHERE job_id=job_id
            # TODO: Get current progress and step status
            # TODO: Calculate ETA based on step pace

Then returns hardcoded job progress (data_prep: completed, feature_engineering: completed, etc.)
```

---

## What Each Tab Actually Shows

| Tab | Endpoint | Data Source | Reality |
|-----|----------|-------------|---------|
| **Overview** | `/api/risk-models/dashboard` | Hardcoded dict | Always shows fake v3.0 production |
| **Model Registry** | `/api/risk-models/versions` | Hardcoded list | Always shows fake v3.0 + v3.1 |
| **Performance** | `/api/risk-models/dashboard` (reused) | Hardcoded dict | Always shows fake metrics (92.4% accuracy) |
| **Training & Data** | `/api/risk-models/training-jobs` | Hardcoded list | Always shows fake v1 bootstrap, v2 retrain |
| **Monitoring** | Various endpoints | Hardcoded | Always shows fake officer feedback (4 holds, 2 examines) |

---

## The Actual Truth About Each Tab

### Overview Tab
Shows:
- Active Model: **FAKE** v3.0 (doesn't exist in database)
- Gate Progression: **FAKE** timeline (hardcoded)
- Score Distribution: **FAKE** counts (hardcoded)

What it SHOULD show:
- Actual model currently scoring shipments (RiskScoringEngine.py)
- Gate progress based on actual officer feedback collected
- Real score distribution from actual shipments in database

### Model Registry Tab
Shows:
- v3.0 PRODUCTION: **FAKE** (doesn't exist, no model registry)
- v3.1 PENDING APPROVAL: **FAKE** (doesn't exist, no approval workflow)
- Approval voters: **FAKE** (Sarah Chen ✓, John Davis ✓, Patricia Brown ○)

What it SHOULD show:
- Current model: RiskScoringEngine.py (git commit abc1234)
- Last deployed: June 12, 2026 by Sarah Chen
- Pending changes: None (unless there are staged code changes)

### Performance Tab
Shows:
- Accuracy: **FAKE** 92.4%
- AUC: **FAKE** 0.944
- Latency: **FAKE** 85ms
- Feature importance: **FAKE** 7 factors

What it SHOULD show:
- Actual metrics computed from real shipments
- Actually measured latency from request logs
- Real feature contribution from XGBoost SHAP values

### Training & Data Tab
Shows:
- Training Run v1: **FAKE** "Bootstrap from rule engine" (2026-06-24)
- Training Run v2: **FAKE** "Experimental retrain" (2026-06-25)
- Dataset: **FAKE** "1,396 shipments, SHA-256..."
- Feature completeness: **FAKE** (shows 0% for critical features)

What it SHOULD show:
- No training runs yet (never trained models)
- Dataset: actual 1,396 shipments in database
- Feature completeness: actual percentages from database

### Monitoring Tab
Shows:
- Officer feedback: **FAKE** (4 holds, 2 examines, 1 clear - total 7)
- Recent predictions: **FAKE** (SHP-001245 score 78, SHP-001234 score 71)
- Data drift: **FAKE** (origin_country KS-stat 0.34)

What it SHOULD show:
- Nothing yet (no officer feedback collected, no Gate 1 started)
- Actual scoring results from recent predictions
- Real data drift if any (need to compute)

---

## Why This Happened

Looking at the file header:

```python
"""Risk Model Management API Endpoints

Provides endpoints for the Risk Model Management tab with REAL v3.0 model data:
- Model versioning and metadata from database
- Training job history from risk_model_training_jobs table
- Performance metrics from actual predictions (risk_model_metrics)
- Data drift detection on real feature distributions
...
All data comes from real sources:
  - Shipments database
  - Risk model tables (v4_0_risk_model_management.py)
  - precise-risk-engine service (http://localhost:8004)
"""
```

**The intention was good.** The code was MEANT to pull real data from:
- `risk_models` table (doesn't exist)
- `risk_model_training_jobs` table (doesn't exist)
- `risk_model_metrics` table (doesn't exist)
- `risk_model_drift_detected` table (doesn't exist)

But these tables were never created, so the developer left TODOs and hardcoded synthetic data as placeholders.

---

## Current Reality Summary

```
┌─────────────────────────────────────────────────┐
│        RISK MODEL MANAGEMENT TAB V2             │
├─────────────────────────────────────────────────┤
│                                                 │
│  Everything you see is FICTIONAL.               │
│                                                 │
│  v3.0, v3.1, approval workflow, staging,       │
│  training runs, data drift - ALL HARDCODED.    │
│                                                 │
│  The actual model is:                          │
│  ├─ RiskScoringEngine.py (one class)          │
│  ├─ Whatever weights are in code               │
│  ├─ No versioning, no switching                │
│  └─ Changed by editing code + rebuilding       │
│                                                 │
│  Database has:                                  │
│  └─ One table: shipments (with risk_score)    │
│                                                 │
│  To fix this, we must:                         │
│  1. Create actual model registry in database   │
│  2. Implement real approval workflow           │
│  3. Add training job tracking                  │
│  4. Wire UI to real data instead of fake      │
│  5. Build staging/rollback infrastructure      │
│                                                 │
└─────────────────────────────────────────────────┘
```

---

## What We Should Do Now

**Option 1: Replace with HONEST UI**
- Show actual model: "RiskScoringEngine (commit abc123)"
- Show actual deployment: "Deployed June 12, 2026 by Sarah Chen"
- Show git history of changes
- Show actual shipments scored (count from database)
- Remove fake v3.0, v3.1, approval workflow

**Option 2: Build REAL Model Registry**
- Create database tables (models, versions, approvals, training)
- Implement model switching (can run 2 models simultaneously)
- Build approval workflow (voting, staging, rollback)
- Wire all endpoints to real data
- Requires: 2-3 weeks development + infrastructure changes

**Option 3: Phased Honest Approach**
- Phase 1 (Week 1): Replace fake data with honest current-state UI
- Phase 2 (Week 2-3): Add simple approval workflow (Slack voting)
- Phase 3 (Week 4-5): Add staging infrastructure
- Phase 4 (Week 6+): Full MLOps as designed

---

## My Recommendation

**Right now, we should DELETE the fake data and build an HONEST UI that shows:**

1. **Current Model Section:**
   ```
   Active Model
   ├─ Name: Gate 0 Rule Engine + XGBoost
   ├─ Location: services/api/risk_scoring_engine.py
   ├─ Last modified: 2026-06-25 by Alex Kim
   ├─ Changes since deploy:
   │  ├─ element9_weight: 20 → 25 (not deployed yet)
   │  └─ dwell_multiplier: 5x → 4x (not deployed yet)
   ├─ Deployed: June 12, 2026 @ 14:35 UTC by Sarah Chen
   ├─ Shipments scored: 1,399 (from database count)
   └─ [View Code] [View Git History] [View Scoring Details]
   ```

2. **Pending Changes Section:**
   ```
   Changes not yet deployed:
   ├─ element9_weight: 20 → 25
   │  ├─ Reason: Increase penalty for container source mismatch
   │  ├─ Backtest: +0.7% accuracy on historical EAPA cases
   │  ├─ Status: PENDING APPROVAL
   │  └─ [View Backtest] [Approve] [Reject]
   └─ [Deploy All Changes] [Reset Changes]
   ```

3. **Deployment History Section:**
   ```
   Recent deployments:
   ├─ June 12, 2026 @ 14:35: Initial Gate 0 rule engine (Sarah Chen)
   │  └─ Changes: 7 rules, referral_threshold=50
   ├─ June 05, 2026: Previous version (archived)
   │  └─ Changes: 6 rules, referral_threshold=45
   └─ [View Full History]
   ```

4. **Scoring Statistics Section:**
   ```
   From database (real metrics):
   ├─ Total shipments scored: 1,399
   ├─ Score distribution:
   │  ├─ CRITICAL (≥80): 25 shipments
   │  ├─ HIGH (65-79): 47 shipments
   │  ├─ MEDIUM (50-64): 109 shipments
   │  └─ LOW (<50): 1,218 shipments
   ├─ Last batch scored: 2026-06-25 @ 14:32 UTC
   └─ [View Recent Scores] [Rescore All] [Rescore Range]
   ```

**This approach:**
- ✅ Is HONEST about actual state
- ✅ Can be built in 2-3 days
- ✅ Sets foundation for real MLOps later
- ✅ Uses real data from database
- ✅ Removes confusing fake v3.0/v3.1

Then, based on your actual workflow needs, we can build real model versioning, staging, approval workflow, etc.

---

## What Do YOU Want To Do?

1. **Delete the fake data and build honest UI?** (Recommended)
2. **Build full MLOps system from scratch?** (Big effort)
3. **Leave it as is and just use it for demo?** (Status quo)

Let me know and I'll implement Phase 1 properly.

