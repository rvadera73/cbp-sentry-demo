# Model Lifecycle Clarification
## Why v1, v2 in Training vs v3.0, v3.1 in Model Registry

**Date:** June 25, 2026  
**Status:** Architecture Clarification  
**Issue:** Confusion between training runs (v1, v2) and deployed model versions (v3.0, v3.1)

---

## PART 1: THE CONFUSION

**What user is seeing:**
- Training & Data tab: Shows v1 bootstrap, v2 experimental retrain
- Model Registry tab: Shows v3.0 production, v3.1 pending approval
- Question: Why are there two different versioning systems? Why is "v2 current" and "v1 production"?

**Root cause:** These are TWO DIFFERENT CONCEPTS:
1. **Training Runs** (training jobs in database): v1, v2, v3... (how many times we retrained)
2. **Deployed Model Versions** (in production): v3.0, v3.1, v3.2... (which models serve traffic)

The naming is confusing because they use overlapping numbers. Let me clarify the lifecycle.

---

## PART 2: ACTUAL MODEL LIFECYCLE (Detailed Timeline)

```
TRAINING PHASE 1: Gate 0 Rule Engine Bootstrap
═══════════════════════════════════════════════════════════════

Timeline: June 12, 2026

Step 1: TRAINING JOB #1 (v1 - Training Run)
├─ Type: Bootstrap training run (initial rule engine)
├─ Data: 1,396 shipments (287 EAPA, 1,109 negatives)
├─ Model: Rule engine (7 factors) + XGBoost (70/30 ensemble)
├─ Parameters:
│  ├─ element9_weight: +20 pts
│  ├─ dwell_multiplier: 5x baseline
│  ├─ pricing_threshold: 15% below market
│  ├─ referral_score_threshold: 50 pts
│  └─ corroboration_required: 2 sources
├─ Results:
│  ├─ AUC: 0.940 (on synthetic EAPA labels)
│  ├─ Precision: 1.0 (on held-out test)
│  ├─ Recall: 0.528 (misses 47% of cases)
│  └─ Backtest on 287 EAPA: 73% sensitivity
├─ Status: COMPLETED (artifact saved to MLflow)
├─ Duration: 45 minutes
├─ Created: 2026-06-24T08:00:00Z
└─ Artifact location: s3://sentry-ml/models/training/v1/model.pkl

Step 2: VALIDATION & APPROVAL (v1 Training Run)
├─ Owner: Data Scientist (Alex Kim)
├─ Validation:
│  ├─ Unit tests: Rule logic ✓
│  ├─ Integration test: End-to-end scoring ✓
│  ├─ Backtest on EAPA cases: 73% sensitivity ✓
│  └─ Data quality check: 87% completeness ✓
├─ Result: v1 training artifacts APPROVED
└─ Ready for deployment

Step 3: DEPLOY v1 to PRODUCTION (Register as v3.0)
├─ What happens:
│  ├─ Take v1 training artifacts from MLflow
│  ├─ Register as MODEL VERSION: v3.0 (NOT v1, different namespace)
│  ├─ Status: PRODUCTION
│  ├─ Build Docker image: risk-model:v3.0
│  ├─ Deploy to Kubernetes cluster
│  └─ Route 100% traffic to v3.0
├─ Timeline: June 12, 2026 @ 14:35 UTC
├─ Approver: Sarah Chen (ML Manager)
├─ Status: ACTIVE (currently serving all predictions)
├─ Note: v1 training run → v3.0 model version (RENUMBERED for production)
└─ Production status:
    ├─ Serving: 1,399 shipments scored
    ├─ Latency: 89ms p95
    ├─ Accuracy: 92.4%
    └─ Confidence: 87%

═══════════════════════════════════════════════════════════════

TRAINING PHASE 2: Experimental Retrain on Production Data
═══════════════════════════════════════════════════════════════

Timeline: June 24-25, 2026

Step 1: TRAINING JOB #2 (v2 - Experimental Retrain)
├─ Trigger: New requirement identified
│  ├─ "Element9 mismatch penalty too low"
│  ├─ "Want to adjust dwell multiplier from 5x to 4x"
│  └─ "Want to test pure XGBoost without rule engine mix"
├─ Type: Experimental retrain (learning from v3.0 production)
├─ Input:
│  ├─ Training data: SAME 1,396 shipments (v3.0 used this)
│  ├─ Model framework: 100% XGBoost (remove 30% rule engine)
│  ├─ New parameters:
│  │  ├─ element9_weight: 20 → 25 pts (CHANGE)
│  │  ├─ dwell_multiplier: 5x → 4x baseline (CHANGE)
│  │  ├─ xgboost_ensemble_weight: 70% → 100% (CHANGE)
│  │  └─ pricing_threshold: 15% → 12% (CHANGE)
│  │
│  └─ Hypothesis: "XGBoost alone + higher element9 penalty = better precision"
├─ Training:
│  ├─ Duration: 62 minutes (longer because XGBoost tuning)
│  ├─ Cross-validation: 5-fold on 287 EAPA labels
│  ├─ Hyperparameter search: max_depth, learning_rate (Bayesian)
│  └─ Results:
│     ├─ AUC: 0.946 (vs v1: 0.940, +0.6% improvement)
│     ├─ Precision: 1.0 (same as v1)
│     ├─ Recall: 0.562 (vs v1: 0.528, +6.4% improvement)
│     └─ Backtest on 287 EAPA: 76% sensitivity (vs v1: 73%)
├─ Status: COMPLETED (artifact saved)
├─ Created: 2026-06-25T09:00:00Z
├─ Training ID: job-002 / training_v2
└─ Artifact location: s3://sentry-ml/models/training/v2/model.pkl

Step 2: VALIDATION (v2 Experimental Training Run)
├─ Owner: Data Scientist (Alex Kim)
├─ Local validation:
│  ├─ Unit tests: XGBoost model ✓
│  ├─ Integration test: Scoring pipeline ✓
│  ├─ Backtest on EAPA: 76% sensitivity ✓ (improved)
│  ├─ Feature importance check: Top 5 features make sense ✓
│  └─ Data drift check: No significant drift vs baseline ✓
├─ Result: v2 training APPROVED for model registration
└─ Ready for promotion to model version

Step 3: REGISTER v2 as NEW MODEL VERSION (v3.1)
├─ What happens:
│  ├─ Take v2 training artifacts
│  ├─ Register as MODEL VERSION: v3.1 (PRODUCTION-CANDIDATE)
│  ├─ Status: EXPERIMENTAL (not serving traffic yet)
│  ├─ Submit for 3-voter approval
│  └─ Create approval_request record
├─ Timeline: June 25, 2026 @ 10:15 UTC
├─ Submitter: Alex Kim
├─ Status: PENDING_APPROVAL (awaiting votes)
├─ Note: v2 training run → v3.1 model version (RENUMBERED again)
└─ Approval status:
    ├─ Voters: Sarah Chen ✓, John Davis ✓, Patricia Brown ○
    ├─ Votes: 2/3 (majority threshold)
    ├─ Deadline: June 26 @ 10:15 UTC (24h window)
    └─ Decision: AWAITING 3RD VOTER (could proceed with 2/3 if policy allows)

═══════════════════════════════════════════════════════════════
```

---

## PART 3: TWO VERSIONING SYSTEMS (Side by Side)

### System 1: TRAINING RUNS (Internal development)

Used in **Training & Data Tab**:

```
Training Run Version Space:
├─ v1: "Bootstrap from rule engine + XGBoost 70/30 ensemble"
│  ├─ Created: 2026-06-24
│  ├─ Status: COMPLETED
│  ├─ Purpose: Initial Gate 0 rule engine verification
│  ├─ Framework: XGBoost 70% + Rule Engine 30%
│  └─ Next action: Deploy to production
│
├─ v2: "Experimental retrain on v1 outcomes"
│  ├─ Created: 2026-06-25
│  ├─ Status: COMPLETED
│  ├─ Purpose: Test pure XGBoost + higher element9 penalty
│  ├─ Framework: XGBoost 100%
│  └─ Next action: Submit for approval
│
└─ v3 (future): "Gate 1 ML model trained on officer feedback"
   ├─ Created: (future, after 200 officer outcomes)
   ├─ Status: NOT YET
   ├─ Purpose: Supervised learning on real EAPA labels
   ├─ Framework: XGBoost + deep learning ensemble
   └─ Next action: Compare vs v2 backtest
```

**Training Run Properties:**
- Incremented sequentially (v1, v2, v3...)
- Tied to a specific training job/run
- Can have multiple training runs for same gate (iterating)
- Stored in MLflow artifact repo
- Used for research/experimentation

---

### System 2: DEPLOYED MODEL VERSIONS (Production)

Used in **Model Registry Tab**:

```
Production Model Version Space:
├─ v3.0: "Gate 0 Rule Engine + XGBoost (70/30 ensemble)"
│  ├─ Created: 2026-06-12
│  ├─ Deployed: 2026-06-12 @ 14:35 UTC
│  ├─ Status: PRODUCTION (active, 100% traffic)
│  ├─ Approver: Sarah Chen
│  ├─ Derived from: Training Run v1
│  ├─ Metrics:
│  │  ├─ Accuracy: 92.4%
│  │  ├─ AUC: 0.944
│  │  ├─ Latency: 89ms p95
│  │  └─ Predictions/day: 15,432
│  └─ Serving: All new shipments scored since June 12
│
├─ v3.1: "Gate 0 XGBoost + Higher Element9 Penalty"
│  ├─ Created: 2026-06-25
│  ├─ Status: EXPERIMENTAL (pending approval, 0% traffic)
│  ├─ Approver: PENDING (awaiting 3/3 votes)
│  ├─ Derived from: Training Run v2
│  ├─ Projected metrics:
│  │  ├─ Accuracy: 93.1% (+0.7%)
│  │  ├─ AUC: 0.951 (+0.7%)
│  │  ├─ Latency: 87ms p95 (-2ms)
│  │  └─ Expected improvement: Higher recall, lower FPR
│  └─ Next action: Approve → Shadow deploy 5% → Monitor → Promote
│
└─ v4.0 (future): "Gate 1 ML Model"
   ├─ Created: (future)
   ├─ Status: NOT YET
   ├─ Will be derived from: Training Run v3
   ├─ After: 200+ officer outcomes collected
   └─ Target: Gate 1 exit criteria
```

**Model Version Properties:**
- Format: v{MAJOR}.{MINOR} (v3.0, v3.1, v4.0...)
- One model can serve production traffic at a time
- Others are in staging/candidate/deprecated states
- Directly serve predictions in Kubernetes
- Immutable once deployed (for audit trail)

---

## PART 4: THE MAPPING

```
Why the numbering is confusing:

Training Run v1  ──────→  Deployed Model v3.0
                          (renumbered for major version)
                          │
                          ├─ Serving production since June 12
                          ├─ Processing all shipments
                          └─ Status: ACTIVE

Training Run v2  ──────→  Deployed Model v3.1
                          (renumbered, incremented minor version)
                          │
                          ├─ Not yet serving (pending approval)
                          ├─ Will serve 5% traffic in staging
                          └─ Status: EXPERIMENTAL (awaiting votes)

Training Run v3  ──────→  Deployed Model v4.0
(not yet)                 (future, after officer feedback collection)
```

**Key insight:** 
- Training run numbers increment from first training (v1, v2, v3...)
- Model version numbers jump to v3.0 when deployed (because v1, v2 might have been earlier attempts)
- Then increment minor version for variations (v3.0, v3.1, v3.2...)
- Never go backwards (no v2.9 after v3.0, always forward to v4.0+)

---

## PART 5: CURRENT STATE IN YOUR ENVIRONMENT (June 25, 2026)

```
┌─────────────────────────────────────────────────────────────┐
│                    CURRENT PRODUCTION STATE                 │
└─────────────────────────────────────────────────────────────┘

DEPLOYED IN PRODUCTION (100% Traffic):
├─ Active Model: v3.0
├─ Framework: Rule Engine (30%) + XGBoost (70%)
├─ Rules: 7 factors with original weights
├─ Deployed: June 12, 2026 @ 14:35 UTC
├─ Approver: Sarah Chen
├─ Performance:
│  ├─ Accuracy: 92.4%
│  ├─ Latency: 89ms p95
│  └─ Daily predictions: 15,432
└─ Status: ✓ HEALTHY, SERVING ALL TRAFFIC

═══════════════════════════════════════════════════════════════

AWAITING APPROVAL (0% Traffic, NOT YET SERVING):
├─ Candidate Model: v3.1
├─ Framework: XGBoost (100%, no rule engine)
├─ Parameters: element9 +25, dwell 4x, pricing -12%
├─ Submitted: June 25, 2026 @ 10:15 UTC
├─ Derived from: Training Run v2
├─ Expected performance:
│  ├─ Accuracy: 93.1% (+0.7%)
│  ├─ Latency: 87ms p95 (-2ms)
│  └─ Expected PPV: 18.2% (vs v3.0: 17.0%)
├─ Approval status:
│  ├─ Sarah Chen (ML Manager): ✓ APPROVED
│  ├─ John Davis (Tech Lead): ✓ APPROVED
│  ├─ Patricia Brown (CBP Officer): ○ PENDING
│  └─ Votes needed: 2/3 (have 2, can proceed) OR 3/3 (wait)
└─ Next steps:
   ├─ Once approved: Shadow deploy to 5% traffic
   ├─ Monitor 7-14 days: Latency, error rate, score drift
   └─ If healthy: Promote to 100% production (becomes new v3.0)

═══════════════════════════════════════════════════════════════

HISTORICAL/ARCHIVED (Not Serving):
├─ Previous versions (if any exist from before June 12)
├─ Would show deprecation reason
└─ Keep for rollback capability
```

---

## PART 6: WHAT HAPPENS WHEN v3.1 IS PROMOTED

```
PROMOTION SCENARIO (June 26, 2026 - After Approval):

Step 1: v3.1 APPROVED by voters
├─ Votes: 2/3 or 3/3 collected
├─ Status changed: EXPERIMENTAL → APPROVED
└─ Action: Click "Promote to Staging" button

Step 2: v3.1 SHADOW DEPLOYED (5% Canary)
├─ What: Deploy to 5% of traffic, v3.0 still serving 95%
├─ Where: Model Registry tab → click "Promote to Staging"
├─ Duration: 7-14 days (collect real metrics)
├─ Monitoring: Training & Data tab shows side-by-side comparison
│  ├─ v3.0 metrics (95% traffic, baseline)
│  ├─ v3.1 metrics (5% traffic, experimental)
│  ├─ Score agreement: Do they agree >90%?
│  ├─ Latency: Both < 500ms p95?
│  ├─ Error rate: Both < 1%?
│  └─ Drift: Is v3.1 seeing different data patterns?
└─ Status: STAGING

Step 3a: v3.1 HEALTH CHECK PASSES → PROMOTE TO PRODUCTION
├─ Scenario: All metrics healthy, no issues detected
├─ Action: Click "Promote to Production" in Model Registry
├─ What happens:
│  ├─ v3.1 becomes PRODUCTION (100% traffic)
│  ├─ v3.0 becomes ARCHIVED (can still rollback)
│  ├─ Update active_model in database
│  ├─ Route all future predictions through v3.1
│  └─ Log: "Promoted v3.1 to production 2026-06-30"
├─ Result: v3.1 is now the active model
└─ Status: PRODUCTION

Step 3b: v3.1 HEALTH CHECK FAILS → ROLLBACK
├─ Scenario: Error rate spiked to 3%, latency > 500ms p95
├─ Action: Click "Rollback to v3.0" in Model Registry
├─ What happens:
│  ├─ v3.1 deployment stopped (halts 5% traffic routing)
│  ├─ v3.0 remains 100% production
│  ├─ v3.1 marked ARCHIVED (failed staging)
│  ├─ Failure reason logged: "Error rate exceeded threshold"
│  └─ Create incident ticket: Debug why v3.1 failed
├─ Result: Back to v3.0 as only production model
├─ Next steps: Investigate v3.1 failure, create v3.2 fix
└─ Status: EXPERIMENTAL → ARCHIVED (FAILED)

═══════════════════════════════════════════════════════════════

FINAL STATE (If v3.1 Promoted Successfully):

PRODUCTION (100% Traffic):
├─ Active Model: v3.1 (formerly candidate, now active)
├─ Framework: XGBoost (100%)
├─ Rules: Updated weights (element9 +25, dwell 4x, pricing -12%)
├─ Promoted: June 30, 2026 @ 15:00 UTC
├─ Performance:
│  ├─ Accuracy: 93.1%
│  ├─ Latency: 87ms p95
│  └─ Daily predictions: 15,500 (slightly more referrals)
└─ Status: ✓ HEALTHY

ARCHIVED (Historical Reference):
├─ Previous Model: v3.0
├─ Status: DEPRECATED (replaced by v3.1)
├─ Can rollback if critical issue found
└─ Kept for 90 days, then deleted
```

---

## PART 7: ANSWERING YOUR QUESTION

**"Why is v2 showing as current and v1 as production?"**

Answer: This is actually showing correctly, but the terminology is confusing:

1. **v2 is "current"** = Latest training run completed (v2 experimental retrain)
   - Location: Training & Data tab (training run history)
   - Status: Completed, awaiting registration as model version
   - Purpose: Shows evolution of training (tried new parameters)

2. **v1 is "production"** = Represents what's deployed in production (but shown in training history)
   - Location: Training & Data tab (shows v1 was the base for v3.0 production)
   - Actually deployed as: v3.0 (different versioning namespace)
   - Status: Serving 100% traffic since June 12

3. **What should be clear:**
   - Training runs (v1, v2) = How many times we trained/experimented
   - Model versions (v3.0, v3.1) = Which model serves production traffic
   - v1 training → deployed as v3.0 production model
   - v2 training → waiting to deploy as v3.1 candidate model

---

## PART 8: FIXING THE CONFUSION IN UI

**To make this less confusing, the UI should:**

### Training & Data Tab:
```
Show:
├─ Training Run History
│  ├─ Training Run v1: "Bootstrap (2026-06-24)" 
│  │  └─ Deployed as: v3.0 PRODUCTION (June 12)
│  │
│  ├─ Training Run v2: "Experimental Retrain (2026-06-25)"
│  │  └─ Pending registration as: v3.1 CANDIDATE
│  │
│  └─ [View how training runs map to deployed models]

This shows the relationship clearly.
```

### Model Registry Tab:
```
Show:
├─ PRODUCTION: v3.0 (derived from training v1)
├─ CANDIDATE: v3.1 (derived from training v2, awaiting approval)
├─ STAGED: (none currently)
└─ ARCHIVED: (previous versions if any)

Clear separation of "training" vs "production" versions.
```

---

## PART 9: DESIGN DECISION: SHOULD WE CHANGE THE VERSIONING?

**Current approach (confusing but accurate):**
- Training run v1 → Deploy as v3.0 (major version jump)
- Training run v2 → Deploy as v3.1 (minor increment)

**Option A (Keep current):** 
- Pros: Maintains major/minor version scheme, easier rollback tracking
- Cons: Confusing for users (v1 training ≠ v1 deployment)

**Option B (Align training with deployment):**
- Training run v1 → Deploy as v1.0 (same name, add ".0")
- Training run v2 → Deploy as v2.0
- Then candidates: v2.1, v2.2, etc.
- Pros: Intuitive (v2 training = v2 deployment)
- Cons: Loses major/minor version semantics

**Option C (Rename training runs):**
- Call them "Iteration 1", "Iteration 2" instead of v1, v2
- Deployed models stay v3.0, v3.1, v3.2
- Pros: No numeric confusion
- Cons: Extra terminology to learn

**My recommendation:** **Option B** (Align training with deployment)
- It's the least confusing for end users
- You lose some version semantics, but gain clarity
- Rationale: "v2 model" should mean the same thing everywhere

Would you like me to update the design to use Option B versioning?

