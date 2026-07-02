# MLOps Change Management Design
## Risk Model Management V2 - Model Registry & Lifecycle Actions

**Date:** June 25, 2026  
**Status:** Design Review (PRE-IMPLEMENTATION)  
**Scope:** Gate 0 (Rule Engine + XGBoost) → Gate 4 (Production Model)

---

## PART 1: MLOps LIFECYCLE & STATE MACHINE

### 1.1 Model States & Transitions

```
┌─────────────┐
│  REGISTERED │  (Model created, versioned in MLflow)
└──────┬──────┘
       │
       ├──→ [DEVELOP] ─────→ ┌─────────────┐
       │                     │ EXPERIMENTAL│ (Testing, iterating on Gate N)
       │                     └──────┬──────┘
       │                            │
       │                            ├──→ [APPROVE] ──→ ┌──────────┐
       │                            │                  │ APPROVED │ (Pending promotion)
       │                            │                  └────┬─────┘
       │                            │                       │
       │                            └────→ [REJECT] ──→ ┌─────────┐
       │                                              │ REJECTED│ (Blocked, iterate)
       │                                              └─────────┘
       │
       └──→ [PROMOTE] ─────→ ┌──────────────┐
                             │ STAGING      │ (Shadow deploy to 5% traffic)
                             └──────┬───────┘
                                    │
                                    ├──→ [PROMOTE] ─────→ ┌────────────┐
                                    │                     │ PRODUCTION │ (100% traffic)
                                    │                     └──────┬─────┘
                                    │                            │
                                    └──→ [ROLLBACK] ────→ ┌──────────────┐
                                                         │ STAGING→PREV │ (Revert to prior version)
                                                         └──────────────┘

       ┌─────────────────────┐
       │ PRODUCTION (Active) │ ─────→ [DEPRECATE] ─────→ ┌──────────┐
       └─────────────────────┘                           │ ARCHIVED │
                                                         └──────────┘
```

### 1.2 Actions & Their Semantics

| Action | From State | To State | Precondition | Effect | Risk Level |
|--------|-----------|----------|--------------|--------|-----------|
| **Promote** | EXPERIMENTAL | APPROVED | Gate N exit criteria met | Submits to 3-voter approval | LOW |
| **Approve Vote** | APPROVED | APPROVED | 2/3 voters agree | Counts vote, can trigger next action | LOW |
| **Promote to Staging** | APPROVED | STAGING | 3/3 votes collected | Deploys to 5% shadow traffic | MEDIUM |
| **Promote to Prod** | STAGING | PRODUCTION | Monitoring metrics healthy | Rolls out to 100% traffic, becomes active | HIGH |
| **Shadow Deploy** | EXPERIMENTAL | STAGING | Testing complete | Deploys to 5% traffic without affecting production | MEDIUM |
| **Rollback** | PRODUCTION | STAGING+ARCHIVED | Critical issue detected | Reverts to previous production version | HIGH |
| **Deprecate** | PRODUCTION/STAGING | ARCHIVED | Superseded by newer version | Removes from active use, keeps in history | LOW |

---

## PART 2: CHANGE MANAGEMENT WORKFLOW

### 2.1 Parameter & Weight Update Flow

```
┌──────────────────────────────────────────────────────────────────────┐
│                    PARAMETER UPDATE REQUEST FLOW                     │
└──────────────────────────────────────────────────────────────────────┘

STEP 1: IDENTIFY PARAMETER CHANGE
├─ Context: Gate 0 rule weights OR XGBoost hyperparameters OR threshold tuning
├─ Examples:
│  ├─ Rule Engine: Adjust "Element9_mismatch" weight from +20 → +25 pts
│  ├─ Rule Engine: Change "dwell_baseline_multiplier" from 5x → 4x
│  ├─ XGBoost: Tune max_depth from 8 → 10 OR learning_rate 0.1 → 0.05
│  ├─ Threshold: Change referral_score_threshold from 50 → 45
│  └─ Approval: Change voter count from 3/3 → 2/3
│
└─ Owner: Data Scientist, ML Engineer, CBP Officer

STEP 2: CREATE EXPERIMENT VERSION (EXPERIMENTAL state)
├─ Create new model version in MLflow
├─ Record:
│  ├─ model_id: v3.1 (incremental version)
│  ├─ gate_target: Gate 0 (which gate this improvement targets)
│  ├─ parameters_changed: {
│  │    "element9_weight": {old: 20, new: 25},
│  │    "dwell_multiplier": {old: 5, new: 4}
│  │  }
│  ├─ rationale: "Increase precision by penalizing container source mismatches"
│  ├─ expected_impact: "Reduce false positives, +3% precision"
│  ├─ created_by: "Alex Kim"
│  └─ created_at: "2026-06-25T14:30:00Z"
│
├─ Copy training dataset & previous model artifacts
├─ Run backtest on Gate 1 historical data (287 EAPA cases)
│  ├─ If Gate 0 rules: Compute new referral counts & PPV
│  │  ├─ Baseline: 8 confirmed / 47 referred = 17.0% PPV
│  │  ├─ New run: Compute scores with new weights
│  │  └─ Compare: Did PPV improve? FPR improve?
│  │
│  └─ If XGBoost: Train on dataset, evaluate on held-out test
│      ├─ Compare AUC, Precision, Recall
│      └─ Check for data drift (feature distributions changed?)
│
└─ Status: EXPERIMENTAL (not serving traffic yet)

STEP 3: LOCAL VALIDATION (Developer / Data Scientist)
├─ Location: Training & Data tab → "Validation Results" section
├─ Tests run:
│  ├─ Unit tests: Rule logic, edge cases (element9 null, missing fields)
│  ├─ Data quality: Completeness audit on 1,396 shipments
│  │  ├─ element9_is_mismatch: % non-null
│  │  ├─ dwell_days: % non-null (filled from AIS if present)
│  │  ├─ ad_cvd_rate: % non-null (filled from reference data)
│  │  └─ Flagged missing > 10%: Highlight in UI
│  │
│  ├─ Integration test: Score a sample shipment end-to-end
│  │  ├─ Manifest → ISF → AIS → Entity resolution → Score
│  │  ├─ Compare expected vs actual score
│  │  └─ Trace each rule's contribution (SHAP)
│  │
│  └─ Backtest metric: Compute on historical labels (287 EAPA cases)
│     ├─ Sensitivity: % EAPA cases we would have caught
│     ├─ Specificity: % non-EAPA cases we correctly cleared
│     ├─ Precision: Of cases we flagged, % actually EAPA
│     └─ Confidence: min(rule confidence weights) × corroboration count
│
└─ Result: Pass/Fail displayed in UI; if FAIL, stay in EXPERIMENTAL

STEP 4: APPROVAL REQUEST (Model Registry tab)
├─ Owner: Data Scientist (submitter)
├─ Triggers: Manual "Request Approval" button in Model Registry tab
├─ Creates approval_request record:
│  ├─ approval_request_id: apr-20260625-v3.1
│  ├─ model_id: v3.1
│  ├─ requested_by: Alex Kim (Data Scientist)
│  ├─ requested_at: 2026-06-25T14:45:00Z
│  ├─ request_reason: "Increase element9 penalty to improve precision"
│  ├─ supporting_metrics: {backtest PPV, sensitivity, specificity}
│  ├─ status: pending
│  ├─ approval_threshold: "2/3 (majority)"
│  ├─ voters: [
│  │    {name: "Sarah Chen", role: "ML Manager", vote: null, status: "pending", email_sent: true},
│  │    {name: "John Davis", role: "Tech Lead", vote: null, status: "pending", email_sent: true},
│  │    {name: "Patricia Brown", role: "CBP Officer", vote: null, status: "pending", email_sent: true}
│  │  ]
│  └─ deadline: 2026-06-26T14:45:00Z (24h voting window)
│
└─ State: APPROVED (awaiting votes)

STEP 5: 3-VOTER APPROVAL WORKFLOW (Model Registry tab)
├─ Voters receive email with:
│  ├─ Link to approval in Model Registry tab
│  ├─ Summary: "v3.1 proposes element9_weight: 20→25"
│  ├─ Backtest results (PPV, sensitivity, specificity)
│  ├─ Risk assessment: "Low risk (rule engine only, no ML retraining)"
│  └─ Voting options: Approve / Reject / Request Changes
│
├─ Voter 1 (Sarah Chen - ML Manager):
│  ├─ Opens Model Registry tab → finds v3.1 in "Pending Approvals"
│  ├─ Reviews metrics & rationale
│  ├─ Clicks "Approve" button
│  ├─ Optional: Adds comment "Good improvement. Precision gain justified."
│  └─ Vote recorded: voted_at: 2026-06-25T15:30:00Z
│
├─ Voter 2 (John Davis - Tech Lead):
│  ├─ Reviews: "Does this break backward compatibility? Can we rollback?"
│  ├─ Clicks "Approve" button
│  └─ Vote recorded
│
├─ Vote Count: 2/3 → THRESHOLD MET (majority)
│  ├─ Alternative thresholds (governance choice):
│  │  ├─ 2/3 (majority): 2 of 3 needed
│  │  ├─ 3/3 (unanimous): all 3 required
│  │  └─ 1/3 (expedited): 1 of 3 (for low-risk changes only)
│  │
│  └─ Action: Enable "Promote to Staging" button in UI
│
└─ State: APPROVED → STAGING (once promoted)

STEP 6: SHADOW DEPLOY TO 5% TRAFFIC (Staging)
├─ Where: Model Registry tab → Click "Promote to Staging" on approved version
├─ What happens:
│  ├─ Deploy v3.1 model artifact to Kubernetes canary pod
│  ├─ Route 5% of incoming shipments to v3.1, 95% to v3.0 (production)
│  ├─ Both models score same shipment, compare results
│  ├─ Log metrics in real-time:
│  │  ├─ Score distribution (v3.1 vs v3.0)
│  │  ├─ Referral rate (% flagged by v3.1)
│  │  ├─ Latency (p50, p95, p99)
│  │  ├─ Error rate (model failures)
│  │  └─ Disagreement rate (cases where v3.1 differs from v3.0 by >5 points)
│  │
│  ├─ Duration: 7-14 days of data collection
│  ├─ Monitoring dashboard: Training & Data tab → "Staging Metrics"
│  │  ├─ Live graphs of referral rate (v3.1 vs v3.0)
│  │  ├─ Score distributions side-by-side
│  │  ├─ Latency SLA check (must be <500ms p95)
│  │  └─ Alert if error rate > 1%
│  │
│  └─ State: STAGING (dual-serving until manual promotion)

STEP 7: DECISION: PROMOTE TO PRODUCTION OR ROLLBACK
├─ After 7-14 days, review staging metrics:
│
├─ SCENARIO A: Metrics look good (referral rate +5%, precision improved, no errors)
│  ├─ Owner: Sarah Chen (ML Manager)
│  ├─ Action: Click "Promote to Production" in Model Registry tab
│  ├─ Effect:
│  │  ├─ Set v3.1 as new production model
│  │  ├─ Archive v3.0 (keep in history)
│  │  ├─ Route 100% traffic to v3.1
│  │  ├─ Log promotion: promoted_by: Sarah, promoted_at: 2026-07-02T10:00:00Z
│  │  └─ Send notification: "v3.1 promoted to production"
│  │
│  └─ State: PRODUCTION (now active for all new shipments)
│
├─ SCENARIO B: Metrics concerning (high error rate, scores diverged wildly)
│  ├─ Owner: Sarah Chen (ML Manager)
│  ├─ Action: Click "Rollback to v3.0" in Model Registry tab
│  ├─ Effect:
│  │  ├─ Route 100% traffic back to v3.0
│  │  ├─ Archive v3.1 with "FAILED_STAGING" status
│  │  ├─ Log rollback reason: "Error rate 3.2% in staging, exceeded 1% threshold"
│  │  └─ Send notification: "v3.1 rolled back; reverting to v3.0"
│  │
│  └─ State: ARCHIVED (keeps versioned for learning)
│
└─ Result: One model is PRODUCTION, others are ARCHIVED or STAGING

STEP 8: DEPRECATION (Optional, for old versions)
├─ Once v3.1 is stable in production for 30+ days:
│  ├─ Owner: Sarah Chen
│  ├─ Action: Click "Deprecate v3.0" in Model Registry tab
│  ├─ Effect:
│  │  ├─ Mark v3.0 as "DEPRECATED" (not usable for new deployments)
│  │  ├─ Keep in database for audit/rollback history
│  │  ├─ Hide from production candidate list
│  │  └─ Update GATES_DEFINITION_AND_CURRENT_STATE.md with new baseline
│  │
│  └─ State: ARCHIVED (historical reference only)
```

---

## PART 3: MODEL REGISTRY TAB DESIGN

### 3.1 Layout & Data Structure

```
┌──────────────────────────────────────────────────────────────────┐
│ RISK MODEL MANAGEMENT → MODEL REGISTRY TAB                      │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  SECTION 1: ACTIVE PRODUCTION MODEL                             │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ ▶ [v3.0] PRODUCTION · Aluminum/Solar · Gate 0 · Active  │   │
│  │ │                                                        │   │
│  │ │ Accuracy: 92.4% | AUC: 0.944 | Latency: 89ms p95     │   │
│  │ │ Deployed: 2026-06-12 | Approved by: Sarah Chen       │   │
│  │ │ Metrics: 1,399 shipments scored, 72 HIGH/CRITICAL    │   │
│  │ │                                                        │   │
│  │ │ [View Details] [View Rules] [View Lineage]           │   │
│  │ │ [Shadow Deploy] [Request Changes]                    │   │
│  │ │                                                        │   │
│  │ │ RULE WEIGHTS (Gate 0):                                │   │
│  │ │  Element9_Mismatch: +20 pts (confidence: 95%)         │   │
│  │ │  Dwell_Anomaly: +18 pts (confidence: 85%)             │   │
│  │ │  Pricing: +12 pts (confidence: 75%)                   │   │
│  │ │  Corridor_Risk: +15 pts (confidence: 90%)             │   │
│  │ │  Transshipment: +14 pts (confidence: 80%)             │   │
│  │ │  New_Shipper: +10 pts (confidence: 70%)               │   │
│  │ │  ISF_Amendments: +12 pts (confidence: 75%)            │   │
│  │ │ [Edit Weights?] (request change)                      │   │
│  │ │                                                        │   │
│  │ └────────────────────────────────────────────────────────┘   │
│                                                                  │
│  SECTION 2: PENDING APPROVALS (Waiting for votes)              │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ ▶ [v3.1] APPROVED · Element9 Penalty Increase           │   │
│  │ │                                                        │   │
│  │ │ Requested: 2026-06-25 by Alex Kim                     │   │
│  │ │ Status: Voting in progress (deadline: 2026-06-26)     │   │
│  │ │                                                        │   │
│  │ │ CHANGES:                                               │   │
│  │ │  • element9_weight: 20 → 25 pts (+5 penalty)          │   │
│  │ │  • dwell_multiplier: 5x → 4x baseline (looser)        │   │
│  │ │                                                        │   │
│  │ │ BACKTEST RESULTS:                                      │   │
│  │ │  • PPV: 17.0% → 18.2% (baseline EAPA cases)           │   │
│  │ │  • Sensitivity: 73% (would catch 73% of EAPA)         │   │
│  │ │  • Specificity: 94% (correctly clears 94% non-EAPA)   │   │
│  │ │  • Risk Level: LOW (rule engine only)                 │   │
│  │ │                                                        │   │
│  │ │ VOTER APPROVAL CHAIN:                                  │   │
│  │ │  ✓ Sarah Chen (ML Manager)       → APPROVED 2026-06-25│   │
│  │ │  ✓ John Davis (Tech Lead)        → APPROVED 2026-06-25│   │
│  │ │  ○ Patricia Brown (CBP Officer)  → PENDING (1 day ago)│   │
│  │ │                                                        │   │
│  │ │  Votes: 2/3 COLLECTED (majority threshold met)         │   │
│  │ │  ✓ Can proceed to staging                             │   │
│  │ │                                                        │   │
│  │ │ [View Full Proposal] [View Backtest] [View Comments]  │   │
│  │ │ [Promote to Staging →] [Request Changes] [Reject]    │   │
│  │ │                                                        │   │
│  │ └────────────────────────────────────────────────────────┘   │
│                                                                  │
│  SECTION 3: STAGING MODELS (5% traffic, testing)               │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ (None currently, or show:)                              │   │
│  │ ▶ [v2.5] STAGING · Corridor Risk Adjustment             │   │
│  │ │ Deployed to staging: 2026-06-20 (5 days ago)          │   │
│  │ │ Metrics: 5% traffic · 70 shipments scored             │   │
│  │ │ Referral rate: 8.6% (vs v3.0: 7.2%, +19% change)      │   │
│  │ │ Latency: 92ms p95 (within SLA)                        │   │
│  │ │ Errors: 0 (0% error rate)                             │   │
│  │ │ Agreement with v3.0: 94% (score diff < 5 pts)         │   │
│  │ │ Monitor duration: 5 days remaining (12 total planned)  │   │
│  │ │                                                        │   │
│  │ │ [Live Staging Dashboard] [Promote to Prod] [Rollback] │   │
│  │ │                                                        │   │
│  │ └────────────────────────────────────────────────────────┘   │
│                                                                  │
│  SECTION 4: VERSION HISTORY (Archived models)                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ ▼ [v2.9] ARCHIVED (Deprecated 2026-05-15)               │   │
│  │ │ Superseded by v3.0. Gate 0 rule baseline.             │   │
│  │ │ [View Details]                                         │   │
│  │ │                                                        │   │
│  │ ▼ [v2.8] ARCHIVED (Rollback from Production)             │   │
│  │ │ Failed in staging: High error rate (2.3%)             │   │
│  │ │ [View Details]                                         │   │
│  │ │                                                        │   │
│  │ ▼ [v2.7] ARCHIVED (Deprecated 2026-04-01)               │   │
│  │ │ Original Gate 0 baseline. [View Details]              │   │
│  │ │                                                        │   │
│  │ └────────────────────────────────────────────────────────┘   │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### 3.2 Actions Visible in Model Cards

```
PRODUCTION MODEL (Active):
├─ View Details          → Expand to show rule weights, metrics, lineage
├─ View Rules            → Detailed breakdown of all 8 rules + scoring logic
├─ View Lineage          → DAG showing previous versions → current
├─ Shadow Deploy         → Deploy current prod to 5% staging traffic
├─ Request Changes       → Create new EXPERIMENTAL version with proposed changes
│  ├─ Opens form to modify rule weights OR hyperparameters
│  ├─ Runs backtest automatically
│  └─ Submits for approval
│
└─ Monitoring            → Link to live metrics dashboard

PENDING APPROVAL MODEL (Voting in progress):
├─ View Full Proposal    → Show change summary + rationale
├─ View Backtest         → Detailed metrics from historical evaluation
├─ View Comments         → Voter feedback & questions
├─ Add Comment           → Ask for clarification or suggest tweaks
├─ Your Vote (if voter)  → Approve / Reject / Request Changes
│
└─ If votes met:
   ├─ Promote to Staging → Begin shadow deployment (5% traffic)
   ├─ Request Changes    → Iterate on proposal
   └─ Reject             → Archive and start over

STAGING MODEL (5% traffic):
├─ Live Staging Dashboard → Real-time metrics (referral rate, latency, errors)
├─ View Staging Metrics   → Detailed comparison vs production
├─ Promote to Production  → Route 100% traffic to this version
├─ Rollback               → Revert to previous production version
│
└─ Decision checklist:
   ├─ Latency p95 < 500ms? ✓
   ├─ Error rate < 1%? ✓
   ├─ Score agreement > 90%? ✓
   └─ Ready to promote?

ARCHIVED MODEL (Historical):
├─ View Details    → Why was it archived? (Deprecated / Failed / Replaced)
├─ View Metrics    → Historical performance data
├─ Revert From     → IF critical issue in production, can revert to this
│
└─ Rationale shown:
   ├─ Deprecated after X days in production
   ├─ Rolled back due to: [error rate / performance drop]
   └─ Replaced by: v3.1 (with rationale)
```

---

## PART 4: TRAINING & DATA TAB PERSPECTIVE

### 4.1 How Parameter Changes Affect Training Pipeline

```
PARAMETER CHANGE FLOW → TRAINING & DATA TAB:

Step 1: Parameter Change Created in Model Registry
├─ v3.1: element9_weight 20 → 25
├─ v3.1: dwell_multiplier 5x → 4x
└─ Status: EXPERIMENTAL

Step 2: Training & Data Tab Shows:
├─ Training Runs section:
│  ├─ v3.0 (production baseline):
│  │  ├─ Training data: 1,396 shipments (287 EAPA, 1,109 negatives)
│  │  ├─ Feature count: 36 features (XGBoost)
│  │  ├─ Gate target: Gate 0
│  │  ├─ Model type: Rule engine + XGBoost (60/40 blend)
│  │  ├─ Rule weights: [Element9: 20, Dwell: 18, Pricing: 12, ...]
│  │  ├─ Trained: 2026-06-12 by Alex Kim
│  │  ├─ Backtest AUC: 0.944 (on 287 EAPA cases)
│  │  └─ [View Training Artifacts] [Compare Against v3.1]
│  │
│  └─ v3.1 (experimental, pending approval):
│     ├─ Training data: SAME (1,396 shipments)
│     ├─ Feature count: 36 features (SAME)
│     ├─ Gate target: Gate 0 (SAME)
│     ├─ Model type: Rule engine + XGBoost (SAME)
│     ├─ Rule weights: [Element9: 25 ↑, Dwell: 18, Pricing: 12, ...]
│     ├─ Trained: 2026-06-25 by Alex Kim
│     ├─ Backtest AUC: 0.946 ↑ (on 287 EAPA cases, +0.2 improvement)
│     └─ [View Training Artifacts] [View Weight Differences]
│
├─ Dataset Baseline section:
│  ├─ v3.1 uses SAME dataset as v3.0
│  ├─ Shipments: 1,396 total
│  ├─ EAPA labels: 287 confirmed cases
│  ├─ Negatives: 1,109 (non-EAPA, cleared cases)
│  ├─ Data hash: sha256(...)
│  ├─ Last updated: 2026-06-20
│  ├─ [View Dataset] [View Changes Since v3.0]
│  │
│  └─ Feature Completeness Audit:
│     ├─ element9_is_mismatch: 100% non-null ✓ (critical for v3.1)
│     ├─ dwell_days: 87% non-null ✓ (important for dwell_multiplier change)
│     ├─ ad_cvd_rate: 92% non-null ✓
│     ├─ shipper_age_months: 95% non-null ✓
│     └─ [Detailed audit...]
│
└─ Data Drift Detection:
   ├─ Gate 0 baseline (v3.0): Captured June 20
   ├─ Current shipments (June 25): Compared against baseline
   ├─ Drift detected:
   │  ├─ element9_is_mismatch: 5% flagged (baseline: 4%) → +1% drift
   │  ├─ shipper_age_months: mean 18mo (baseline: 17mo) → normal
   │  ├─ dwell_days: KS-stat 0.06 (threshold: 0.10) → no significant drift
   │  └─ [View detailed drift analysis]
   │
   └─ Implication for v3.1:
      ├─ element9 change is JUSTIFIED (slight drift in this feature)
      ├─ dwell_multiplier relaxation (5x→4x) is RISKY (could over-flag)
      └─ Recommend: Monitor closely during staging

Step 3: Monitoring During Staging (Training & Data Tab)
├─ Staging Metrics section:
│  ├─ v3.1 on 5% traffic (production baseline: v3.0 on 95% traffic)
│  ├─ Real-time comparison:
│  │  ├─ v3.0 referral rate: 7.2% (on its 95% traffic)
│  │  ├─ v3.1 referral rate: 8.6% (on its 5% traffic)
│  │  ├─ Difference: +1.4% absolute (19% relative increase)
│  │  ├─ Latency: v3.0 89ms p95 vs v3.1 92ms p95 (within SLA)
│  │  ├─ Error rate: v3.0 0.1% vs v3.1 0.0% (both healthy)
│  │  └─ Score agreement: 94% of cases score within 5 pts of each other
│  │
│  └─ Data quality in staging:
│     ├─ Feature completeness: 98% non-null (healthy)
│     ├─ Drift from baseline: 0.08 KS-stat (normal)
│     └─ No anomalies detected
│
└─ Decision checkpoint:
   ├─ Is v3.1 ready for production?
   ├─ Metrics look good (latency OK, error rate OK, modest referral increase)
   ├─ Data quality stable
   └─ Proceed to production OR monitor longer?

Step 4: Production Promotion (Training & Data Tab)
├─ v3.1 promoted to 100% production traffic
├─ v3.0 archived (kept in history)
├─ New baseline established: v3.1
├─ Training & Data tab now shows:
│  ├─ Active production model: v3.1
│  ├─ Production metrics (real, not staged):
│  │  ├─ Daily referral rate: 8.4% (slightly lower than staging, normal variation)
│  │  ├─ Daily error rate: 0.08%
│  │  ├─ Daily latency p95: 91ms
│  │  └─ Daily data drift: 0.07 KS-stat (stable)
│  │
│  └─ Next phase: Gate 0→1 transition (collect officer feedback)
│     ├─ Officer Hold/Examine/Clear outcomes on v3.1 referrals
│     ├─ Sensitivity target: 70% of real EAPA cases caught
│     ├─ Specificity target: 90% of non-EAPA correctly cleared
│     └─ Gate 1 exit: 200 officer outcomes collected
└─ State: Production stable, ready for gate progression

Step 5: (Future) Gate 1 Model Development
├─ Once 200 officer outcomes collected:
│  ├─ Use as training labels for Gate 1 ML model
│  ├─ Train supervised model (XGBoost, LightGBM, etc.)
│  ├─ Compare Gate 1 model AUC vs Gate 0 rules
│  └─ If Gate 1 model better: promote to EXPERIMENTAL
│
└─ Cycle repeats: Experiment → Approve → Stage → Promote
```

---

## PART 5: WEIGHTS & PARAMETERS THAT CAN BE UPDATED

### 5.1 Rule Engine Parameters (Gate 0)

```
RULE WEIGHTS (Rule Engine):

├─ element9_weight: Currently +20 pts
│  ├─ Tunable range: 15-30 pts (rule is high confidence)
│  ├─ Change impact: Direct effect on referral threshold
│  ├─ Example change: 20 → 25 (increase penalty, reduce false negatives)
│  ├─ Backtest required: Yes (affects referral count & PPV)
│  └─ Risk: LOW (deterministic rule, easily reversible)
│
├─ dwell_multiplier: Currently 5x baseline
│  ├─ Tunable range: 3x-7x (allows shorter dwell anomalies to flag)
│  ├─ Change impact: More/fewer dwell-based referrals
│  ├─ Example change: 5x → 4x (more aggressive, lower threshold)
│  ├─ Backtest required: Yes
│  └─ Risk: MEDIUM (affects many shipments with dwell data)
│
├─ pricing_threshold: Currently 15% below market
│  ├─ Tunable range: 10%-20% (allow some variance)
│  ├─ Change impact: More/fewer pricing-anomaly referrals
│  ├─ Example change: 15% → 12% (stricter, more sensitive)
│  ├─ Backtest required: Yes
│  └─ Risk: MEDIUM (market data may be incomplete)
│
├─ referral_score_threshold: Currently 50 pts (normalized 0-100)
│  ├─ Tunable range: 30-70 (controls decision boundary)
│  ├─ Change impact: Global referral rate change
│  ├─ Example change: 50 → 45 (more referrals, lower precision)
│  ├─ Backtest required: Yes (critical parameter)
│  └─ Risk: HIGH (affects all shipments, operational burden)
│
├─ ad_cvd_duty_threshold: Currently 15%
│  ├─ Tunable range: 10%-25%
│  ├─ Change impact: Which tariff rates trigger corridor risk
│  ├─ Example change: 15% → 10% (more aggressive on duties)
│  ├─ Backtest required: Yes
│  └─ Risk: MEDIUM (commodity-specific, economic context)
│
└─ new_shipper_age_threshold: Currently 24 months
   ├─ Tunable range: 12-36 months
   ├─ Change impact: Who counts as "new" for risk assessment
   ├─ Example change: 24 → 12 (more aggressive on new entrants)
   ├─ Backtest required: Yes
   └─ Risk: LOW (simple demographic threshold)

RULE COMBINATION WEIGHTS (Corroboration):

├─ minimum_corroboration_count: Currently 2 sources required
│  ├─ Examples:
│  │  ├─ Element 9 mismatch ALONE: Can it trigger referral? (Currently NO)
│  │  ├─ Element 9 + dwell anomaly: YES, 2 sources
│  │  └─ Element 9 + pricing + dwell: YES, 3 sources (overkill)
│  │
│  ├─ Tunable range: 1-3 sources
│  ├─ Change impact: Stringency of referral decision
│  ├─ Example change: 2 → 1 (more aggressive, more referrals)
│  ├─ Backtest required: Yes (major change to decision logic)
│  └─ Risk: HIGH (affects fundamental corroboration requirement)
│
└─ voter_approval_threshold: Currently 2/3 (majority)
   ├─ Alternative thresholds:
   │  ├─ 1/3 (expedited for low-risk changes only)
   │  ├─ 2/3 (current, democratic)
   │  └─ 3/3 (unanimous, conservative)
   │
   ├─ Tunable range: 1/3 to 3/3
   ├─ Change impact: Approval speed vs consensus
   ├─ Example change: 2/3 → 3/3 (slower, more conservative)
   ├─ Backtest required: No (governance only)
   └─ Risk: LOW (internal process)
```

### 5.2 XGBoost Hyperparameters (IF we move to Gate 1 ML model)

```
NOT YET TUNED (Gate 0 is rule-based only), but will be for Gate 1:

├─ max_depth: Currently 8 (tree depth)
│  ├─ Tunable range: 3-15
│  ├─ Lower = simpler model, less overfitting
│  ├─ Higher = more complex, captures patterns but may overfit
│  ├─ Change impact: Model complexity, variance/bias trade-off
│  ├─ Backtest required: Yes (retrain on same dataset)
│  └─ Risk: MEDIUM (affects generalization)
│
├─ learning_rate: Currently 0.1 (gradient boosting step size)
│  ├─ Tunable range: 0.01-0.5
│  ├─ Lower = slower learning, more regularization
│  ├─ Higher = faster learning, risk of overfitting
│  ├─ Change impact: Training time & convergence
│  ├─ Backtest required: Yes
│  └─ Risk: MEDIUM
│
├─ n_estimators: Currently 100 (num trees)
│  ├─ Tunable range: 50-500
│  ├─ More trees = ensemble effect, but also more time
│  ├─ Change impact: Model accuracy & training time
│  ├─ Backtest required: Yes
│  └─ Risk: LOW (mostly affects performance, not decision logic)
│
├─ subsample: Currently 0.8 (row sampling)
│  ├─ Tunable range: 0.5-1.0
│  ├─ Controls variability across trees
│  ├─ Change impact: Regularization, variance reduction
│  ├─ Backtest required: Yes
│  └─ Risk: MEDIUM
│
└─ colsample_bytree: Currently 0.8 (feature sampling)
   ├─ Tunable range: 0.5-1.0
   ├─ Controls feature diversity across trees
   ├─ Change impact: Regularization, feature importance
   ├─ Backtest required: Yes
   └─ Risk: MEDIUM
```

---

## PART 6: GOVERNANCE & DECISION MATRIX

### 6.1 What Changes Require Full Approval Workflow?

| Change Type | Risk Level | Voters Required | Backtest | Staging | Decision Maker |
|------------|-----------|-----------------|----------|---------|----------------|
| Rule weight ±10 pts | LOW | 2/3 | Yes | Optional | Data Scientist |
| Referral threshold ±10 pts | HIGH | 3/3 | Yes | Required | ML Manager |
| Corroboration requirement change | HIGH | 3/3 | Yes | Required | ML Manager + CBP Officer |
| XGBoost hyperparameter tune | MEDIUM | 2/3 | Yes | Required | Data Scientist |
| Voter threshold change | LOW | N/A | No | N/A | Governance |
| Data source addition | MEDIUM | 2/3 | Yes | Required | Data Scientist |
| New feature engineering | MEDIUM | 2/3 | Yes | Required | Data Scientist |

### 6.2 Approval Workflow Variations

```
EXPEDITED (Low-risk changes):
├─ Changes: Rule weight ±5 pts, minor hyperparameter tuning
├─ Voters: 1/3 (any 1 of 3 experts)
├─ Timeline: 24h voting window
└─ No staging required, promote directly after approval

STANDARD (Medium-risk changes):
├─ Changes: Rule weight ±10 pts, threshold ±10 pts
├─ Voters: 2/3 (majority)
├─ Timeline: 24h voting window
├─ Staging required: 7 days monitoring
└─ Promotion after staging metrics reviewed

STRICT (High-risk changes):
├─ Changes: Corroboration logic, major threshold changes
├─ Voters: 3/3 (unanimous)
├─ Timeline: 48h voting window
├─ Staging required: 14 days monitoring
├─ Post-promotion review: Daily for first 7 days
└─ Requires ML Manager + CBP Officer sign-off
```

---

## PART 7: NEXT STEPS FOR DESIGN REVIEW

**Questions for user approval before implementation:**

1. **MLOps Actions**: Is the 8-step workflow (STEP 1-8 above) aligned with your vision?
   - Do Promote/Rollback/Shadow Deploy/Deprecate map correctly to states?
   - Is 5% staging traffic for shadow deployment reasonable?
   - Are monitoring metrics (latency, error rate, agreement %) sufficient?

2. **Model Registry Tab**: Does the 4-section layout work?
   - SECTION 1: Active production model with rule weights
   - SECTION 2: Pending approvals with voter status
   - SECTION 3: Staging models with live metrics
   - SECTION 4: Version history (archived)
   - Does this reduce white space and make actions visible?

3. **Change Management**: Are the parameter categories complete?
   - Rule weights (7 tunable parameters)
   - Corroboration logic (2 thresholds)
   - Governance (voter counts, approval thresholds)
   - Missing anything?

4. **Training & Data Tab Integration**: Does the flow make sense?
   - Parameters change in Model Registry → backtest automatically
   - Staging → real-time metrics in Training & Data tab
   - Data drift detection informs deployment decisions
   - Feedback loop to next model version training

5. **Governance**: Do approval thresholds (1/3, 2/3, 3/3) fit your needs?
   - Who should be the 3 voters? (Currently: ML Manager, Tech Lead, CBP Officer)
   - Should some changes bypass voting (e.g., rollback in emergency)?
   - Timeline acceptable (24h standard, 48h strict)?

**Once you agree on design, we'll:**
1. Implement Model Registry tab redesign (remove white space, show actions)
2. Wire MLOps action buttons to API endpoints
3. Add change management UI (request weight changes, approval voting)
4. Integrate Training & Data tab with staging metrics
5. Test full workflow end-to-end
