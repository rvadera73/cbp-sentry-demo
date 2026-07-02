# Risk Model Management Tab — CBP Sentry

**Date:** 2026-06-12 | **Status:** Ready for Implementation | **Scope:** Phase 1 (CBP-only, fully featured)

---

## 1. Tab Overview

### **Location in UI**
```
CBP Sentry Dashboard
├─ Shipments
├─ Entity Graph
├─ AI Tuning
└─ ⭐ Risk Model Management  ← NEW TAB
   ├─ Dashboard (Summary)
   ├─ Model Versions (Active/Staging/Candidate)
   ├─ Training History (Jobs + Results)
   ├─ Performance Metrics (Accuracy, Latency, Fairness)
   ├─ Data Drift Monitoring (Feature distributions)
   ├─ Prediction Explanations (SHAP per shipment)
   ├─ Model Approvals (Voting + Audit trail)
   └─ Retraining Configuration (Triggers + Schedule)
```

### **Tab Purpose**
End-to-end risk model lifecycle management:
- Monitor current model performance (v3.0)
- Review candidate models (v3.1, v4.0)
- Approve model switches with workflow
- View training job status
- Detect data/model drift
- Explain individual predictions
- Configure retraining triggers
- Track approval history

---

## 2. Tab Screens (8 Total)

### **Screen 1: Dashboard (Summary)**

**Purpose:** At-a-glance model health and status

```
┌─────────────────────────────────────────────┐
│ Risk Model Management Dashboard              │
├─────────────────────────────────────────────┤
│                                              │
│  ACTIVE MODEL                                │
│  ┌──────────────────────────────────────┐   │
│  │ Model: CBP Risk v3.0                 │   │
│  │ Status: PRODUCTION                   │   │
│  │ Deployed: 2026-06-12 14:35 UTC       │   │
│  │ Approved By: Sarah Chen (Manager)    │   │
│  │                                      │   │
│  │ Performance (Last 24h):              │   │
│  │ ├─ Accuracy: 92.4%                   │   │
│  │ ├─ AUC-ROC: 0.94                     │   │
│  │ ├─ Latency (p95): 85ms               │   │
│  │ └─ Confidence (avg): 0.87            │   │
│  │                                      │   │
│  │ Predictions Processed: 15,432        │   │
│  │ Data Drift Score: 0.12 (Normal)      │   │
│  │ Model Drift Score: 0.08 (Normal)     │   │
│  └──────────────────────────────────────┘   │
│                                              │
│  PENDING ACTIONS                             │
│  ┌──────────────────────────────────────┐   │
│  │ Candidate Model: v3.1 (Under Review) │   │
│  │ ├─ Requested By: ML Team             │   │
│  │ ├─ Requested: 2026-06-11 10:00 UTC   │   │
│  │ ├─ Approval Status: 1/2 votes (50%)  │   │
│  │ ├─ New Accuracy: 93.1% (+0.7%)       │   │
│  │ └─ [View Details] [Vote]             │   │
│  └──────────────────────────────────────┘   │
│                                              │
│  MONITORING ALERTS                           │
│  ┌──────────────────────────────────────┐   │
│  │ ⚠️  High Data Drift Detected          │   │
│  │   Feature: origin_country             │   │
│  │   Drift Score: 0.34 (Elevated)        │   │
│  │   Detected: 2 hours ago               │   │
│  │   [Investigate] [Run Drift Report]    │   │
│  │                                      │   │
│  │ ✓ All Other Metrics Normal            │   │
│  └──────────────────────────────────────┘   │
│                                              │
│  QUICK ACTIONS                               │
│  [View All Versions] [Compare Models]        │
│  [Run Training Job] [View Metrics]           │
│  [Explain Predictions] [Approval Queue]      │
│                                              │
└─────────────────────────────────────────────┘
```

**Key Metrics:**
- Current model version + status
- 24h performance (accuracy, AUC, latency, confidence)
- Data drift score (0.0-1.0)
- Model drift score (0.0-1.0)
- Pending approvals count
- Active alerts

---

### **Screen 2: Model Versions**

**Purpose:** Compare all available model versions + manage status

```
┌─────────────────────────────────────────────┐
│ Model Versions                               │
├─────────────────────────────────────────────┤
│                                              │
│ Filter: [All] [Production] [Staging] [Candidate]│
│                                              │
│ MODEL v3.0 (PRODUCTION) ✓ ACTIVE             │
│ ├─ Status: ACTIVE IN PRODUCTION              │
│ ├─ Deployed: 2026-06-12 14:35 UTC            │
│ ├─ Trained On: 2,500,000 shipments           │
│ ├─ Features: 47                              │
│ ├─ Weights Sum: 100.0% ✓                     │
│ ├─ Performance:                              │
│ │  ├─ Accuracy: 92.4%                        │
│ │  ├─ AUC-ROC: 0.944                         │
│ │  ├─ Latency (p95): 85ms                    │
│ │  └─ False Positive Rate: 3.2%              │
│ ├─ Approved By: Sarah Chen                   │
│ ├─ Approval Date: 2026-06-12 12:00 UTC       │
│ └─ [View Details] [Compare] [Rollback]       │
│                                              │
│ MODEL v3.1 (CANDIDATE) ⏳ UNDER REVIEW        │
│ ├─ Status: AWAITING APPROVAL                 │
│ ├─ Trained: 2026-06-11 09:30 UTC             │
│ ├─ Trained On: 2,500,000 shipments           │
│ ├─ Features: 47                              │
│ ├─ Weights Sum: 100.0% ✓                     │
│ ├─ Performance vs v3.0:                      │
│ │  ├─ Accuracy: 93.1% (+0.7%) ↑              │
│ │  ├─ AUC-ROC: 0.951 (+0.007) ↑              │
│ │  ├─ Latency (p95): 87ms (+2ms) ↓           │
│ │  └─ False Positive Rate: 2.8% (-0.4%) ↑    │
│ ├─ Approval Votes: 1/2 (50%)                 │
│ │  ├─ Sarah Chen: ✓ APPROVE                  │
│ │  └─ John Davis: ⏳ PENDING                  │
│ └─ [View Details] [Compare] [Vote]           │
│                                              │
│ MODEL v2.1 (DEPRECATED) ✓ ARCHIVED           │
│ ├─ Status: ARCHIVED (Legacy)                 │
│ ├─ Deprecated: 2026-06-12 14:35 UTC          │
│ ├─ Features: 47                              │
│ ├─ Weights Sum: 110.0% ✗ (Invalid)           │
│ ├─ Note: Replaced by v3.0                    │
│ └─ [View Details] [Restore] (Admin Only)     │
│                                              │
└─────────────────────────────────────────────┘
```

**Features:**
- List all model versions (production, staging, candidate, deprecated)
- Show status + deployment date
- Compare performance metrics
- Display approval status with voter names
- Quick actions: View Details, Compare, Vote, Rollback

---

### **Screen 3: Training History**

**Purpose:** Track all training jobs + view results

```
┌─────────────────────────────────────────────┐
│ Training History & Jobs                      │
├─────────────────────────────────────────────┤
│                                              │
│ Filter: [All] [Completed] [In Progress] [Failed]│
│ Sort: [Date] [Status]                        │
│                                              │
│ TRAINING JOB v3.1 (COMPLETED) ✓              │
│ ├─ Model: v3.1                               │
│ ├─ Job ID: job-20260611-093001               │
│ ├─ Started: 2026-06-11 09:30 UTC             │
│ ├─ Completed: 2026-06-11 11:45 UTC (2h 15m) │
│ ├─ Dataset: cbp-shipments-2024               │
│ │  ├─ Records: 2,500,000                     │
│ │  ├─ Features: 47                           │
│ │  └─ Train/Test: 80/20                      │
│ ├─ Hyperparameters:                          │
│ │  ├─ max_depth: 8                           │
│ │  ├─ learning_rate: 0.05                    │
│ │  └─ n_estimators: 500                      │
│ ├─ Training Results:                         │
│ │  ├─ Training Accuracy: 93.8%               │
│ │  ├─ Test Accuracy: 93.1%                   │
│ │  ├─ AUC-ROC: 0.951                         │
│ │  ├─ Validation: PASSED ✓                   │
│ │  └─ Approval Status: UNDER_REVIEW          │
│ ├─ Top Features by Importance:               │
│ │  ├─ 1. documentation_risk (25.3%)          │
│ │  ├─ 2. corridor_risk (19.8%)               │
│ │  └─ 3. routing_risk (14.9%)                │
│ └─ [View Full Report] [Create Comparison]    │
│                                              │
│ TRAINING JOB v3.0 (COMPLETED) ✓              │
│ ├─ Model: v3.0 (DEPLOYED)                    │
│ ├─ Job ID: job-20260612-143501               │
│ ├─ Started: 2026-06-12 14:35 UTC             │
│ ├─ Completed: 2026-06-12 16:50 UTC           │
│ ├─ Dataset: cbp-shipments-2024               │
│ ├─ Results: All Metrics ✓ Passed             │
│ └─ [View Full Report]                        │
│                                              │
│ TRAINING JOB v3.2 (IN PROGRESS) ⏳            │
│ ├─ Model: v3.2                               │
│ ├─ Job ID: job-20260613-020000               │
│ ├─ Started: 2026-06-13 02:00 UTC             │
│ ├─ Progress: 45% (Step 3/6)                  │
│ │  ├─ Data Prep: ✓ Complete                  │
│ │  ├─ Feature Engineering: ✓ Complete        │
│ │  ├─ Model Training: ⏳ In Progress...       │
│ │  ├─ Validation: ⏜ Queued                   │
│ │  ├─ Artifact Storage: ⏜ Queued             │
│ │  └─ Notification: ⏜ Queued                 │
│ ├─ ETA: ~1 hour 15 minutes                   │
│ └─ [View Logs] [Cancel] [View Real-Time]     │
│                                              │
│ TRAINING JOB v2.2 (FAILED) ✗                 │
│ ├─ Model: v2.2                               │
│ ├─ Job ID: job-20260610-140000               │
│ ├─ Started: 2026-06-10 14:00 UTC             │
│ ├─ Failed: 2026-06-10 14:30 UTC              │
│ ├─ Error: ValidationError                    │
│ ├─ Reason: Test accuracy < 0.90 threshold    │
│ └─ [View Error Log] [Retry] [View Report]    │
│                                              │
└─────────────────────────────────────────────┘
```

**Features:**
- List training jobs with status (completed, in progress, failed)
- Show timing + dataset info
- Display hyperparameters
- Show training/test results
- Feature importance ranking
- Progress indicators for running jobs
- Links to detailed reports

---

### **Screen 4: Performance Metrics**

**Purpose:** Time-series monitoring of model performance

```
┌─────────────────────────────────────────────┐
│ Performance Metrics Dashboard                │
├─────────────────────────────────────────────┤
│                                              │
│ Time Range: [Last 24h] [7d] [30d] [Custom]  │
│ Model: [v3.0 (Active)] vs [v3.1 (Compare)]  │
│                                              │
│ ACCURACY TREND                               │
│ 94% ┌─────────────────────────────────┐     │
│     │           v3.0 ─────────        │     │
│ 92% │          /      \               │     │
│     │        /          \             │     │
│ 90% │      /              \───────────│     │
│     │ v3.1 ─────────────               │     │
│     └─────────────────────────────────┘     │
│     00:00  06:00  12:00  18:00  23:59       │
│                                              │
│ Model v3.0 Accuracy: 92.4%                   │
│ Model v3.1 Accuracy: 93.1% (+0.7%)           │
│                                              │
│ ─────────────────────────────────────────── │
│                                              │
│ LATENCY DISTRIBUTION (p95)                   │
│ 200ms ┌─────────────────────────────────┐   │
│       │                                 │   │
│ 100ms │  v3.0 ███████████ 85ms          │   │
│       │  v3.1 ███████████ 87ms          │   │
│ 0ms   └─────────────────────────────────┘   │
│                                              │
│ ─────────────────────────────────────────── │
│                                              │
│ CONFUSION MATRIX (v3.0, Last 24h)            │
│                Predicted                     │
│              CLEAR  EXAMINE  HOLD            │
│ Actual CLEAR  8,234    156      10           │
│        EXAMINE  245   3,421     89           │
│        HOLD      32     78     443           │
│                                              │
│ Recall (HOLD): 79.2%                        │
│ Precision (HOLD): 83.1%                     │
│                                              │
│ ─────────────────────────────────────────── │
│                                              │
│ FAIRNESS METRICS (v3.0)                      │
│ By Origin:                                   │
│ ├─ CN (China):     Accuracy 91.8%, N=4,532  │
│ ├─ MX (Mexico):    Accuracy 93.2%, N=3,124  │
│ ├─ IN (India):     Accuracy 92.5%, N=2,891  │
│ └─ Other:         Accuracy 92.3%, N=4,885  │
│ Fairness Score: 0.94 (Good) ✓               │
│                                              │
│ EXPORT / REPORT                              │
│ [Download CSV] [Generate Report] [Alert Setup]│
│                                              │
└─────────────────────────────────────────────┘
```

**Metrics Tracked:**
- Accuracy trend (time series)
- Latency percentiles (p50, p95, p99)
- Confusion matrix + recall/precision
- Fairness metrics by segment (origin, commodity, etc.)
- AUC-ROC curves
- False positive/negative rates
- Confidence distribution

---

### **Screen 5: Data Drift Monitoring**

**Purpose:** Detect feature distribution changes

```
┌─────────────────────────────────────────────┐
│ Data Drift Monitoring                        │
├─────────────────────────────────────────────┤
│                                              │
│ Baseline Period: [Last 7d Baseline]          │
│ Current Period: [Last 24h]                   │
│ Drift Detection Method: Kolmogorov-Smirnov  │
│                                              │
│ ⚠️  ELEVATED DRIFT DETECTED                  │
│                                              │
│ ORIGIN_COUNTRY (Drift Score: 0.34) ⚠️       │
│ ├─ Drift Type: Categorical shift             │
│ ├─ Baseline Distribution (7d avg):           │
│ │  ├─ CN: 32.4%  ├─ MX: 22.1%  ├─ IN: 20.5% │
│ │  ├─ HK: 8.2%   └─ Other: 16.8%             │
│ ├─ Current Distribution (24h):               │
│ │  ├─ CN: 28.9%  ├─ MX: 24.3%  ├─ IN: 22.8% │
│ │  ├─ HK: 9.1%   └─ Other: 14.9%             │
│ ├─ Change: China -3.5%, Mexico +2.2%, ...    │
│ ├─ Root Cause: Likely holiday season shift   │
│ ├─ Recommendation: Monitor for 48h           │
│ └─ [Investigate] [Run Detailed Analysis]     │
│                                              │
│ ─────────────────────────────────────────── │
│                                              │
│ COMMODITY_VALUE (Drift Score: 0.08) ✓       │
│ ├─ Drift Type: Numeric distribution          │
│ ├─ Baseline Mean: $2,145                     │
│ ├─ Current Mean: $2,168 (+1.1%)              │
│ ├─ Baseline Std Dev: $1,240                  │
│ ├─ Current Std Dev: $1,255 (+1.2%)           │
│ ├─ Status: NORMAL (within 5% threshold)      │
│ └─ [View Distribution Plot]                  │
│                                              │
│ ─────────────────────────────────────────── │
│                                              │
│ DOCUMENTATION_RISK (Drift Score: 0.06) ✓    │
│ ├─ Baseline: Avg 2.34, Std 1.12              │
│ ├─ Current: Avg 2.31, Std 1.09               │
│ ├─ Status: NORMAL                            │
│ └─ [View Distribution Plot]                  │
│                                              │
│ ALL OTHER FEATURES                           │
│ ├─ 44 features checked                       │
│ ├─ 44 features NORMAL ✓                      │
│ └─ [View All Features]                       │
│                                              │
│ DRIFT SUMMARY                                │
│ Elevated Drift: 1 feature                    │
│ Normal Drift: 46 features                    │
│ Overall Drift Score: 0.12 (Acceptable)       │
│                                              │
│ ACTIONS                                      │
│ [ ] Schedule retraining (if drift continues)│
│ [ ] Investigate root cause                  │
│ [ ] Monitor closely for 48 hours             │
│ [Acknowledge Alert] [Dismiss] [More Details] │
│                                              │
└─────────────────────────────────────────────┘
```

**Features:**
- Baseline vs current distribution comparison
- Drift score per feature (0.0-1.0)
- Categorical vs numeric shift detection
- Root cause suggestions
- Alert thresholds configurable
- Links to detailed analysis

---

### **Screen 6: Prediction Explanations (SHAP)**

**Purpose:** Understand individual predictions

```
┌─────────────────────────────────────────────┐
│ Prediction Explanations                      │
├─────────────────────────────────────────────┤
│                                              │
│ Search Shipment: [SHP-00142857]             │
│                                              │
│ ─────────────────────────────────────────── │
│                                              │
│ SHIPMENT SUMMARY                             │
│ Shipment ID: SHP-00142857                    │
│ Origin: China (Beijing)                      │
│ Destination: New York                        │
│ Commodity: Electronics                       │
│ Declared Value: $45,200                      │
│ Container Type: 40ft FCL                     │
│                                              │
│ ─────────────────────────────────────────── │
│                                              │
│ PREDICTION                                   │
│ Model: v3.0                                  │
│ Score: 0.76 (EXAMINE)                        │
│ Confidence: 0.91                             │
│ Processing Time: 82ms                        │
│                                              │
│ ─────────────────────────────────────────── │
│                                              │
│ SHAP EXPLANATION (Why v3.0 predicted 0.76?)  │
│                                              │
│ Base Score: 0.35                             │
│                                              │
│ Factors Increasing Risk (Pushing up):        │
│ ┌──────────────────────────────────────┐    │
│ │ documentation_risk: 0.85              │    │
│ │ ███████████████████  +0.16            │    │
│ │                                      │    │
│ │ routing_risk: HIGH                   │    │
│ │ ████████████████     +0.14            │    │
│ │                                      │    │
│ │ pattern_risk: UNUSUAL                │    │
│ │ ██████████            +0.07           │    │
│ │                                      │    │
│ │ corridor_risk: ELEVATED              │    │
│ │ ███████████           +0.06           │    │
│ └──────────────────────────────────────┘    │
│                                              │
│ Factors Decreasing Risk (Pushing down):      │
│ ┌──────────────────────────────────────┐    │
│ │ party_risk: LOW (Known exporter)     │    │
│ │ ████                  -0.04           │    │
│ │                                      │    │
│ │ commodity_risk: NORMAL               │    │
│ │ ██                    -0.02           │    │
│ └──────────────────────────────────────┘    │
│                                              │
│ Final Score: 0.35 + 0.43 - 0.06 = 0.76 ✓   │
│                                              │
│ ─────────────────────────────────────────── │
│                                              │
│ INTERPRETATION                               │
│ This shipment is flagged for EXAMINE due to:│
│ 1. Missing/suspicious documentation         │
│ 2. Routing through high-risk ports           │
│ 3. Unusual trade pattern for this party      │
│ 4. Elevated corridor risk (CN→US ports)      │
│                                              │
│ Combined, these factors exceed threshold.    │
│ Recommend: Standard examination protocol.    │
│                                              │
│ COMPARISON                                   │
│ v2.1 Score: 0.71 (EXAMINE)                  │
│ v3.0 Score: 0.76 (EXAMINE)                  │
│ Difference: +0.05 (v3.0 more conservative)  │
│                                              │
│ [Compare v2.1 Explanation] [Export Report]   │
│                                              │
└─────────────────────────────────────────────┘
```

**Features:**
- Search/filter shipments
- Show prediction + confidence
- SHAP force plot (base + pushes)
- Feature contributions ranked
- Plain English interpretation
- Compare with v2.1 (legacy)

---

### **Screen 7: Model Approvals**

**Purpose:** Workflow for approving/rejecting model changes

```
┌─────────────────────────────────────────────┐
│ Model Approvals & Voting                     │
├─────────────────────────────────────────────┤
│                                              │
│ Filter: [All] [Pending] [Approved] [Rejected]│
│                                              │
│ APPROVAL REQUEST: v3.1 (PENDING)             │
│ ┌──────────────────────────────────────────┐│
│ │ Model: CBP Risk v3.1                     ││
│ │ Requested By: Alex Kim (ML Engineer)     ││
│ │ Requested Date: 2026-06-11 10:30 UTC     ││
│ │ Request Reason: +0.7% accuracy, lower FPR││
│ │                                          ││
│ │ Performance Improvement:                 ││
│ │ ├─ Accuracy: 92.4% → 93.1% (+0.7%) ✓    ││
│ │ ├─ AUC-ROC: 0.944 → 0.951 (+0.007) ✓    ││
│ │ ├─ Latency: 85ms → 87ms (-0.2%) ✓       ││
│ │ └─ False Positive Rate: 3.2% → 2.8% ✓   ││
│ │                                          ││
│ │ Training Data:                           ││
│ │ ├─ Records: 2,500,000 shipments          ││
│ │ ├─ Date Range: 2024 full year            ││
│ │ └─ Validation: PASSED ✓                  ││
│ │                                          ││
│ │ Fairness Analysis:                       ││
│ │ ├─ By Origin: All segments within ±1% ✓ ││
│ │ ├─ By Commodity: All segments ✓         ││
│ │ └─ Overall Fairness Score: 0.94 ✓       ││
│ │                                          ││
│ │ APPROVAL VOTES (2/2 required)            ││
│ │ ┌─────────────────────────────────────┐ ││
│ │ │ Voter 1: Sarah Chen (Manager)      │ ││
│ │ │ Vote: ✓ APPROVE                    │ ││
│ │ │ Comment: "Solid improvement. FPR   │ ││
│ │ │           reduction is significant"│ ││
│ │ │ Voted: 2026-06-11 14:22 UTC        │ ││
│ │ │                                    │ ││
│ │ │ Voter 2: John Davis (Tech Lead)    │ ││
│ │ │ Vote: ⏳ PENDING                    │ ││
│ │ │ Email Sent: 2026-06-11 10:35 UTC   │ ││
│ │ │ Reminder Sent: 2026-06-12 10:35 UTC│ ││
│ │ │                                    │ ││
│ │ │ [ ] I agree this model is better   │ ││
│ │ │ [ ] Risk is within acceptable range│ ││
│ │ │ [ ] I recommend approval           │ ││
│ │ │ Comment: [_________________]       │ ││
│ │ │ [APPROVE] [REJECT] [ABSTAIN]       │ ││
│ │ └─────────────────────────────────────┘ ││
│ │                                          ││
│ │ Status: 50% voted, 1 approval remaining  ││
│ │ Voting Deadline: 2026-06-14 10:30 UTC    ││
│ │                                          ││
│ │ [View Full Training Report]              ││
│ │ [Compare Metrics] [Notify Reviewers]     ││
│ └──────────────────────────────────────────┘│
│                                              │
│ ─────────────────────────────────────────── │
│                                              │
│ APPROVAL HISTORY                             │
│                                              │
│ ✓ APPROVED: v3.0 (2026-06-12)                │
│   ├─ Requested: 2026-06-12 12:00 UTC         │
│   ├─ Approved: 2026-06-12 14:35 UTC          │
│   ├─ Votes: Sarah Chen ✓, John Davis ✓      │
│   ├─ Deployed: 2026-06-12 14:35 UTC          │
│   └─ [View Details]                          │
│                                              │
│ ✗ REJECTED: v2.2 (2026-06-10)                │
│   ├─ Requested: 2026-06-10 14:00 UTC         │
│   ├─ Rejected: 2026-06-10 16:30 UTC          │
│   ├─ Reason: Test accuracy < 0.90 threshold  │
│   ├─ Rejector: Sarah Chen                    │
│   └─ [View Details]                          │
│                                              │
└─────────────────────────────────────────────┘
```

**Features:**
- Show pending approval requests
- Display performance improvements
- Fairness analysis
- Multi-voter approval workflow
- Vote tracking + audit trail
- Voter comments
- Historical approvals/rejections
- Approval deadline tracking

---

### **Screen 8: Retraining Configuration**

**Purpose:** Set up automated retraining triggers

```
┌─────────────────────────────────────────────┐
│ Retraining Configuration                     │
├─────────────────────────────────────────────┤
│                                              │
│ SCHEDULED RETRAINING                         │
│ ┌──────────────────────────────────────────┐│
│ │ [✓] Enable Scheduled Retraining          ││
│ │                                          ││
│ │ Frequency: [Weekly] (Every Monday)       ││
│ │ Schedule Time: [02:00 UTC] (2 AM UTC)    ││
│ │ Data Window: [Last 7 days]               ││
│ │                                          ││
│ │ Next Scheduled Run: 2026-06-16 02:00 UTC││
│ │ Last Run: 2026-06-09 02:15 UTC (PASSED) ││
│ │                                          ││
│ │ Notification:                            ││
│ │ [ ] Email on training start              ││
│ │ [✓] Email on training completion         ││
│ │ [✓] Slack notification                   ││
│ │ [✓] Alert on failure                     ││
│ │                                          ││
│ └──────────────────────────────────────────┘│
│                                              │
│ AUTOMATIC TRIGGER: DATA DRIFT               │
│ ┌──────────────────────────────────────────┐│
│ │ [✓] Retrain if data drift detected       ││
│ │                                          ││
│ │ Drift Threshold: [0.30] (30%)            ││
│ │ Duration: Must persist for [24 hours]    ││
│ │ Affected Features: [≥ 3 features]        ││
│ │                                          ││
│ │ When triggered:                          ││
│ │ ├─ Collect fresh data from drift period  ││
│ │ ├─ Train new model immediately           ││
│ │ ├─ Create as STAGING version             ││
│ │ ├─ Notify ML team for review             ││
│ │ └─ Await manual approval before deploy    ││
│ │                                          ││
│ │ Last Trigger: 2026-06-05 (Data drift)    ││
│ │ Resulting Model: v3.0 (Now PRODUCTION)   ││
│ │                                          ││
│ └──────────────────────────────────────────┘│
│                                              │
│ AUTOMATIC TRIGGER: MODEL DRIFT              │
│ ┌──────────────────────────────────────────┐│
│ │ [✓] Retrain if accuracy degrades         ││
│ │                                          ││
│ │ Degradation Threshold: [-2.0%]           ││
│ │ Evaluation Window: [7 days]              ││
│ │ Min Predictions: [10,000]                ││
│ │                                          ││
│ │ When triggered:                          ││
│ │ ├─ Flag alert in dashboard               ││
│ │ ├─ Collect training data                 ││
│ │ ├─ Queue retraining job                  ││
│ │ ├─ Notify ML team + managers             ││
│ │ └─ Consider auto-rollback if critical    ││
│ │                                          ││
│ │ Last Trigger: 2026-06-02 (Model drift)   ││
│ │ Resulting Model: v3.0 (Now PRODUCTION)   ││
│ │                                          ││
│ └──────────────────────────────────────────┘│
│                                              │
│ AUTOMATIC TRIGGER: ERROR SPIKE              │
│ ┌──────────────────────────────────────────┐│
│ │ [ ] Retrain if error rate spikes         ││
│ │ (Currently disabled)                     ││
│ │                                          ││
│ │ Error Threshold: [5.0%] (5% errors)      ││
│ │ Duration: Must persist for [30 minutes]  ││
│ │                                          ││
│ │ When triggered:                          ││
│ │ ├─ Alert to on-call engineer             ││
│ │ ├─ Potentially auto-rollback              ││
│ │ ├─ Post-incident review                  ││
│ │ └─ Trigger retraining                    ││
│ │                                          ││
│ │ [Enable] [Configure] [View History]      ││
│ │                                          ││
│ └──────────────────────────────────────────┘│
│                                              │
│ SETTINGS                                     │
│ Default Data Source: [Production Database]  │
│ Training Framework: [XGBoost v1.7]          │
│ Hyperparameter Strategy: [Use Last Params]  │
│ Max Concurrent Jobs: [1]                    │
│ Model Auto-Deprecation: [After 90 days]     │
│                                              │
│ [Save Configuration] [Reset to Default]     │
│                                              │
└─────────────────────────────────────────────┘
```

**Features:**
- Schedule automatic retraining (daily/weekly)
- Set drift detection triggers
- Set model performance degradation triggers
- Configure error spike alerts
- Notification settings
- Show training history per trigger
- Enable/disable individual triggers

---

## 3. Backend: Database Schema

```sql
-- Risk Model Management Tab Tables

CREATE TABLE risk_models (
    id TEXT PRIMARY KEY,
    model_id TEXT UNIQUE NOT NULL,        -- v3.0, v3.1, etc
    version TEXT NOT NULL,
    name TEXT NOT NULL,
    status TEXT NOT NULL,                 -- training, staging, candidate, production, deprecated
    framework TEXT,                       -- xgboost, neural_net, etc
    model_type TEXT,                      -- classification, regression
    feature_count INT,
    weights_sum FLOAT,                    -- 100.0 or 110.0 (for validation)
    artifact_path TEXT,                   -- Path to model file
    metadata JSON,                        -- Training dataset info, hyperparams, etc
    created_at DATETIME,
    created_by TEXT,
    approved_at DATETIME,
    approved_by TEXT,
    deployed_at DATETIME,
    deprecated_at DATETIME
);

CREATE TABLE risk_model_training_jobs (
    id TEXT PRIMARY KEY,
    model_id TEXT,
    job_id TEXT UNIQUE NOT NULL,          -- job-20260611-093001
    dataset_id TEXT,
    status TEXT,                          -- queued, running, completed, failed
    started_at DATETIME,
    completed_at DATETIME,
    training_records INT,
    test_records INT,
    hyperparameters JSON,
    training_metrics JSON,                -- {accuracy, auc_roc, etc}
    validation_status TEXT,               -- passed, failed
    validation_errors JSON,
    artifacts_path TEXT,
    error_message TEXT,
    logs_location TEXT,
    FOREIGN KEY (model_id) REFERENCES risk_models(id)
);

CREATE TABLE risk_model_metrics (
    id TEXT PRIMARY KEY,
    model_id TEXT NOT NULL,
    metric_name TEXT NOT NULL,            -- accuracy, auc_roc, latency, etc
    metric_value FLOAT,
    segment TEXT,                         -- optional: origin=CN, commodity=ELEC
    timestamp DATETIME,
    FOREIGN KEY (model_id) REFERENCES risk_models(id),
    INDEX idx_model_time (model_id, timestamp)
);

CREATE TABLE risk_model_predictions (
    id TEXT PRIMARY KEY,
    model_id TEXT NOT NULL,
    shipment_id TEXT NOT NULL,
    score FLOAT,
    confidence FLOAT,
    classification TEXT,                  -- CLEAR, EXAMINE, HOLD
    shap_values JSON,                     -- SHAP explanation
    feature_contributions JSON,
    latency_ms INT,
    created_at DATETIME,
    FOREIGN KEY (model_id) REFERENCES risk_models(id),
    INDEX idx_shipment (shipment_id),
    INDEX idx_created (created_at)
);

CREATE TABLE risk_model_drift_detected (
    id TEXT PRIMARY KEY,
    model_id TEXT,
    feature_name TEXT,
    drift_type TEXT,                      -- data_drift, model_drift
    drift_score FLOAT,
    baseline_distribution JSON,
    current_distribution JSON,
    detected_at DATETIME,
    status TEXT,                          -- new, acknowledged, resolved
    root_cause TEXT,
    action_taken TEXT,
    FOREIGN KEY (model_id) REFERENCES risk_models(id)
);

CREATE TABLE risk_model_approvals (
    id TEXT PRIMARY KEY,
    model_id TEXT NOT NULL,
    approval_request_id TEXT UNIQUE,
    requested_by TEXT,
    requested_at DATETIME,
    request_reason TEXT,
    voters JSON,                          -- [{user, vote, comment, voted_at, status}]
    status TEXT,                          -- pending, approved, rejected
    approval_stage TEXT,                  -- staging, production
    approved_at DATETIME,
    approved_by TEXT,
    deployed_at DATETIME,
    notes TEXT,
    FOREIGN KEY (model_id) REFERENCES risk_models(id)
);

CREATE TABLE risk_retraining_config (
    id TEXT PRIMARY KEY,
    config_name TEXT,
    enabled BOOLEAN,
    schedule_frequency TEXT,              -- daily, weekly, monthly
    schedule_time TEXT,                   -- 02:00
    schedule_timezone TEXT,               -- UTC
    data_window_days INT,                 -- last N days
    drift_threshold FLOAT,                -- 0.0-1.0
    drift_persistence_hours INT,          -- must persist for N hours
    model_degradation_threshold FLOAT,    -- -2% (percentage)
    evaluation_window_days INT,
    min_predictions_threshold INT,
    error_threshold FLOAT,                -- 5.0%
    error_persistence_minutes INT,
    notification_email BOOLEAN,
    notification_slack BOOLEAN,
    notification_pagerduty BOOLEAN,
    last_triggered_at DATETIME,
    last_triggered_reason TEXT,
    created_at DATETIME,
    updated_at DATETIME
);
```

---

## 4. Backend: API Endpoints

```
Risk Model Management API Endpoints

GET /api/risk-models/dashboard
  Returns: {
    active_model, performance_metrics, pending_approvals,
    alerts, drift_score, key_metrics
  }

GET /api/risk-models/versions
  Query: ?status=production&sort=date
  Returns: [model, model, ...]

POST /api/risk-models/{model_id}/compare
  Payload: {compare_to_model_id: "v2.1"}
  Returns: {metrics_comparison, performance_diff, ...}

GET /api/risk-models/training-jobs
  Query: ?status=completed&limit=20&sort=date
  Returns: [training_job, ...]

GET /api/risk-models/training-jobs/{job_id}
  Returns: {status, progress, timing, results, logs}

GET /api/risk-models/{model_id}/metrics
  Query: ?time_range=24h&metric=accuracy
  Returns: [metrics_point, ...]

GET /api/risk-models/{model_id}/drift
  Returns: {
    drift_score, elevated_features, baseline_distribution,
    current_distribution, recommendations
  }

GET /api/risk-models/predictions/{shipment_id}/explain
  Query: ?model_version=v3.0&compare_to=v2.1
  Returns: {shap_values, interpretation, comparison}

GET /api/risk-models/approvals
  Query: ?status=pending
  Returns: [approval_request, ...]

POST /api/risk-models/approvals/{approval_id}/vote
  Payload: {vote: "approve"|"reject", comment: "..."}
  Returns: {updated_approval, remaining_votes}

GET /api/risk-models/retraining-config
  Returns: {scheduled, drift_triggered, model_drift_triggered, ...}

PUT /api/risk-models/retraining-config
  Payload: {schedule_frequency, drift_threshold, ...}
  Returns: {updated_config}

POST /api/risk-models/{model_id}/rollback
  Payload: {reason: "..."}
  Returns: {success, previous_model, rollback_time}
```

---

## 5. Implementation Phases (Phase 1: CBP-Focused)

### **Phase 1A: UI Scaffolding (Week 1)**
- [ ] Create React component structure for 8 screens
- [ ] Stub out routing (Risk Model Management tab)
- [ ] Build mock data service
- [ ] Get UI designs approved

### **Phase 1B: Backend Foundations (Week 1-2)**
- [ ] Create database schema (7 tables)
- [ ] Implement API endpoints (15 total)
- [ ] Set up data collection (metrics, drift, predictions)
- [ ] Build model version management

### **Phase 1C: Integration (Week 2-3)**
- [ ] Connect UI to REST APIs
- [ ] Populate with v3.0 model data
- [ ] Test approval workflow
- [ ] Test retraining triggers

### **Phase 1D: Polish & Testing (Week 3-4)**
- [ ] UI refinements
- [ ] Performance optimization
- [ ] End-to-end testing
- [ ] User acceptance testing

### **Phase 2: MLOps Tooling (Later)**
- Add MLflow integration
- Add DVC for data versioning
- Add Prometheus monitoring
- Add GitHub Actions Environments for approval

### **Phase 3+: Multi-Domain Extensibility (Future)**
- Refactor to generic MCP server
- Add FDA adverse event model
- Add Commerce fraud model
- Expose via MCP protocol

---

## 6. Success Criteria for Phase 1

```
✓ Dashboard shows current v3.0 model health
✓ Approval workflow works end-to-end
✓ Performance metrics auto-populate
✓ SHAP explanations load for any shipment
✓ Data drift detection alerts trigger
✓ Training history displays correctly
✓ Retraining configuration saves
✓ All 8 screens render without errors
✓ Users can approve/reject model changes
✓ Audit trail tracks all actions
```

---

## Summary: Risk Model Management Tab

| Aspect | Details |
|---|---|
| **Location** | New tab in CBP Sentry dashboard |
| **Screens** | 8 (Dashboard, Versions, Training, Metrics, Drift, Explanations, Approvals, Config) |
| **Users** | Analysts, Managers, ML Team, Admins |
| **Phase 1 Focus** | CBP risk model only (v2.1 → v3.0) |
| **Phase 2+** | Extensible to other models/domains |
| **MCP Ready** | Designed with generic abstractions for future MCP exposure |
| **Implementation** | 4 weeks (scaffolding → integration → testing) |
| **Database Tables** | 7 core tables for complete lifecycle |
| **API Endpoints** | 12+ endpoints covering all operations |

This becomes the central hub for all risk model operations at CBP Sentry.
