# Complete Risk Model Service Design

**Purpose:** Design a comprehensive risk model service as part of CBP Sentry (not external)

**Key Principle:** Risk Model Management tab in UI + background microservice (not GitHub Actions)

---

## 1. What We Missed in Initial Design

### **Initial Design (Incomplete)**
```
We designed:
✅ Model training
✅ Model deployment
✅ Feature flag switching
❌ Model validation framework
❌ Feature store
❌ Data drift detection
❌ Model drift detection
❌ Retraining triggers
❌ Model explainability at scale
❌ A/B testing infrastructure
❌ Bias detection
❌ Training data lineage
❌ Hyperparameter tuning history
❌ Prediction confidence tracking
❌ Model performance degradation alerts
```

### **Complete Risk Model Service Should Include**

```
┌─────────────────────────────────────────────────────────┐
│         COMPLETE RISK MODEL SERVICE                     │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ 1. DATA MANAGEMENT LAYER                                │
│    ├─ Feature Store (centralized feature tracking)      │
│    ├─ Training Data Versioning (what data trained it)   │
│    ├─ Data Drift Detection (is input distribution ok?)  │
│    └─ Data Quality Checks (validation rules per feature)│
│                                                         │
│ 2. MODEL DEVELOPMENT LAYER                              │
│    ├─ Hyperparameter Tuning (track all experiments)     │
│    ├─ Feature Engineering History (which features used) │
│    ├─ Model Validation (rigorous testing before deploy) │
│    ├─ Cross-Validation Scores (5-fold, 10-fold, etc)   │
│    └─ Test Set Performance (holdout evaluation)         │
│                                                         │
│ 3. MODEL REGISTRY LAYER                                 │
│    ├─ Model Versioning (v2.1, v3.0, v3.1, etc)         │
│    ├─ Model Artifacts (pkl files, config, metadata)    │
│    ├─ Model Documentation (model card)                  │
│    └─ Model Lineage (which data, which features)        │
│                                                         │
│ 4. MODEL DEPLOYMENT LAYER                               │
│    ├─ Approval Workflow (who signed off on this)        │
│    ├─ Gradual Rollout (traffic ramping: 0→10→50→100%)  │
│    ├─ Shadow Mode (run both models, compare)            │
│    └─ Fallback Strategy (automatic rollback on errors)  │
│                                                         │
│ 5. PREDICTION EXPLANATION LAYER                         │
│    ├─ SHAP Values (why did it score 75?)                │
│    ├─ Feature Attribution (which features mattered)     │
│    ├─ Confidence Intervals (how sure are we?)           │
│    └─ Uncertainty Quantification (epistemic vs aleatoric)
│                                                         │
│ 6. MONITORING & ALERTING LAYER                          │
│    ├─ Model Drift Detection (is model performance ok?)  │
│    ├─ Prediction Drift (are predictions getting weird?) │
│    ├─ Data Distribution Shift (input feature changes)   │
│    ├─ Performance Degradation (accuracy dropping)       │
│    ├─ Fairness Metrics (bias detection by subgroup)     │
│    └─ Latency Monitoring (inference speed)              │
│                                                         │
│ 7. RETRAINING LAYER                                     │
│    ├─ Retraining Triggers (when to retrain)             │
│    ├─ Automated Training (scheduled + on-demand)        │
│    ├─ Automated Validation (pre-deployment testing)     │
│    ├─ Automated Comparison (vs current production)      │
│    └─ Candidate Selection (is new model better?)        │
│                                                         │
│ 8. COMPARISON & ANALYTICS LAYER                         │
│    ├─ A/B Testing (segment-level comparison)            │
│    ├─ Cohort Analysis (how does v3.0 vs v2.1 perform)   │
│    ├─ Score Distribution Analysis (are outputs ok?)     │
│    ├─ Classification Rate Changes (% HOLD/EXAMINE/CLEAR)│
│    └─ Latency Comparison (training time vs inference)   │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 2. Architecture: Risk Model Service (Not GitHub Actions)

```
┌────────────────────────────────────────────────────────┐
│                 CBP SENTRY UI                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │      NEW: Risk Model Management Tab              │  │
│  │  ├─ Model Versions & Status                      │  │
│  │  ├─ Training Job History                         │  │
│  │  ├─ Model Performance Dashboard                  │  │
│  │  ├─ Data Drift Monitoring                        │  │
│  │  ├─ Approval Queue                               │  │
│  │  └─ Retraining Triggers                          │  │
│  └──────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────┘
                          ↓ HTTP/WebSocket
┌────────────────────────────────────────────────────────┐
│          RISK MODEL SERVICE (NEW MICROSERVICE)         │
│  Runs as part of CBP Sentry (not GitHub Actions)       │
├────────────────────────────────────────────────────────┤
│                                                        │
│  API ENDPOINTS:                                        │
│  POST /api/model/train                                 │
│  GET  /api/model/jobs/{job_id}                         │
│  GET  /api/model/metrics/{version}                     │
│  POST /api/model/validate/{version}                    │
│  POST /api/model/approve/{version}                     │
│  POST /api/model/deploy/{version}                      │
│  GET  /api/model/predictions/{shipment_id}/explain     │
│  GET  /api/model/monitoring/drift                      │
│                                                        │
│  BACKGROUND JOBS:                                      │
│  ├─ Training Scheduler (daily 2am)                     │
│  ├─ Validation Runner (post-training)                  │
│  ├─ Drift Monitor (every 1 hour)                       │
│  ├─ Performance Monitor (continuous)                   │
│  └─ Retraining Trigger Evaluator (hourly)              │
│                                                        │
│  DATABASE TABLES:                                      │
│  ├─ model_versions                                     │
│  ├─ training_jobs                                      │
│  ├─ model_metrics                                      │
│  ├─ feature_store                                      │
│  ├─ training_data_lineage                              │
│  ├─ prediction_explanations                            │
│  ├─ drift_detected                                     │
│  ├─ model_approvals                                    │
│  └─ retraining_history                                 │
│                                                        │
└────────────────────────────────────────────────────────┘
                          ↓
┌────────────────────────────────────────────────────────┐
│        SUPPORTING SERVICES                             │
├────────────────────────────────────────────────────────┤
│  Precise Risk Engine (model inference)                 │
│  Monitoring Service (metrics collection)               │
│  PostgreSQL (model metadata + metrics)                 │
│  Feature Store (BigQuery or Feast)                     │
└────────────────────────────────────────────────────────┘
```

---

## 3. Data Models Missing from Initial Design

### **Core Tables Needed**

```sql
-- 1. MODEL VERSIONS (which models exist)
CREATE TABLE model_versions (
    id TEXT PRIMARY KEY,
    version TEXT UNIQUE,
    name TEXT,
    status TEXT,  -- 'training', 'candidate', 'staging', 'production', 'deprecated'
    model_type TEXT,  -- 'xgboost', 'neural_net', 'ensemble'
    features_count INT,
    training_data_size INT,
    created_at DATETIME,
    trained_by TEXT,
    approved_by TEXT,
    approved_at DATETIME,
    deployment_status TEXT,
    traffic_percentage INT,
    metadata JSON
);

-- 2. TRAINING JOBS (audit trail of all training)
CREATE TABLE training_jobs (
    id TEXT PRIMARY KEY,
    model_version TEXT,
    job_status TEXT,  -- 'queued', 'running', 'completed', 'failed'
    started_at DATETIME,
    completed_at DATETIME,
    training_data_size INT,
    training_data_hash TEXT,  -- For reproducibility
    features_used JSON,
    hyperparameters JSON,
    training_time_seconds INT,
    validation_error TEXT,
    metrics JSON,
    artifacts_location TEXT,
    FOREIGN KEY (model_version) REFERENCES model_versions(id)
);

-- 3. MODEL METRICS (performance tracking)
CREATE TABLE model_metrics (
    id TEXT PRIMARY KEY,
    model_version TEXT,
    metric_name TEXT,  -- 'accuracy', 'auc_roc', 'precision', 'recall', etc
    metric_value FLOAT,
    metric_type TEXT,  -- 'training', 'validation', 'test', 'production'
    timestamp DATETIME,
    segment TEXT,  -- Optional: 'CN_origin', 'high_value', etc
    FOREIGN KEY (model_version) REFERENCES model_versions(id)
);

-- 4. FEATURE STORE (centralized features)
CREATE TABLE feature_store (
    id TEXT PRIMARY KEY,
    feature_name TEXT,
    feature_type TEXT,  -- 'numeric', 'categorical', 'temporal'
    source_table TEXT,
    source_column TEXT,
    description TEXT,
    validation_rules JSON,  -- Min, max, allowed values
    created_at DATETIME,
    last_updated DATETIME,
    used_in_versions JSON  -- ['v2.1', 'v3.0', 'v3.1']
);

-- 5. TRAINING DATA LINEAGE (reproducibility)
CREATE TABLE training_data_lineage (
    id TEXT PRIMARY KEY,
    model_version TEXT,
    data_source TEXT,  -- 'production_db', 'backup_db', 'synthetic'
    date_range_start DATE,
    date_range_end DATE,
    total_records INT,
    record_hash TEXT,  -- Hash of actual data for reproducibility
    preprocessing_steps JSON,
    train_test_split TEXT,  -- '80/20', '70/15/15'
    FOREIGN KEY (model_version) REFERENCES model_versions(id)
);

-- 6. PREDICTION EXPLANATIONS (SHAP values per prediction)
CREATE TABLE prediction_explanations (
    id TEXT PRIMARY KEY,
    shipment_id TEXT,
    model_version TEXT,
    predicted_score FLOAT,
    feature_contributions JSON,  -- [{name: 'field9_mismatch', value: 15.3, contribution: +8.2}, ...]
    base_value FLOAT,  -- SHAP base value
    top_features JSON,  -- Top 5 features for this prediction
    confidence_interval JSON,  -- {lower: 72.1, upper: 74.5}
    created_at DATETIME,
    FOREIGN KEY (model_version) REFERENCES model_versions(id)
);

-- 7. DRIFT DETECTION (when data/model quality changes)
CREATE TABLE drift_detected (
    id TEXT PRIMARY KEY,
    drift_type TEXT,  -- 'data_drift', 'model_drift', 'prediction_drift'
    model_version TEXT,
    feature_name TEXT,  -- Optional, if specific feature drifted
    drift_score FLOAT,  -- 0-1 severity
    baseline_value FLOAT,
    current_value FLOAT,
    detected_at DATETIME,
    status TEXT,  -- 'new', 'acknowledged', 'resolved'
    action_taken TEXT,
    FOREIGN KEY (model_version) REFERENCES model_versions(id)
);

-- 8. MODEL APPROVALS (approval workflow)
CREATE TABLE model_approvals (
    id TEXT PRIMARY KEY,
    model_version TEXT,
    approval_stage TEXT,  -- 'staging', 'production'
    requested_by TEXT,
    requested_at DATETIME,
    approved_by TEXT,
    approved_at DATETIME,
    rejected_by TEXT,
    rejected_at DATETIME,
    rejection_reason TEXT,
    approval_criteria JSON,  -- What must be true to approve
    approval_votes JSON,  -- [{user: 'alice', vote: 'yes'}, ...]
    FOREIGN KEY (model_version) REFERENCES model_versions(id)
);

-- 9. RETRAINING HISTORY (when & why models were retrained)
CREATE TABLE retraining_history (
    id TEXT PRIMARY KEY,
    trigger_reason TEXT,  -- 'scheduled', 'performance_degradation', 'data_drift', 'manual'
    triggered_at DATETIME,
    training_started DATETIME,
    training_completed DATETIME,
    new_model_version TEXT,
    improvement_vs_current FLOAT,  -- % improvement if any
    decision TEXT,  -- 'approved_for_deployment', 'rejected', 'pending_review'
    FOREIGN KEY (new_model_version) REFERENCES model_versions(id)
);

-- 10. FAIRNESS METRICS (bias detection by segment)
CREATE TABLE fairness_metrics (
    id TEXT PRIMARY KEY,
    model_version TEXT,
    segment_name TEXT,  -- 'origin_country=CN', 'commodity=Electronics', etc
    total_predictions INT,
    avg_score FLOAT,
    hold_rate FLOAT,
    examine_rate FLOAT,
    clear_rate FLOAT,
    disparity_ratio FLOAT,  -- vs overall population
    flag_if_disparity_high BOOLEAN,
    FOREIGN KEY (model_version) REFERENCES model_versions(id)
);
```

---

## 4. Risk Model Management UI Tab

### **Layout & Screens**

```
RISK MODEL MANAGEMENT TAB
├── 1. DASHBOARD (Overview)
│   ├─ Active Model: v3.0 (Precise Risk XGBoost)
│   │  ├─ Status: Production
│   │  ├─ Traffic: 100%
│   │  ├─ Accuracy (7-day): 0.92
│   │  ├─ Latency (P95): 85ms
│   │  └─ Last retrained: 6 days ago
│   │
│   ├─ Next Model: v3.1 (staging)
│   │  ├─ Status: Under Review
│   │  ├─ Accuracy: 0.93 (↑ 1.1% better)
│   │  ├─ [Approve] [Reject] buttons
│   │  └─ Review by: Alice, Bob (waiting: Charlie)
│   │
│   ├─ Data Health
│   │  ├─ Data Quality: 99.2%
│   │  ├─ Drift Detected: NO ✅
│   │  └─ Last check: 1 hour ago
│   │
│   └─ Recent Alerts
│       ├─ ⚠️ Latency increased 5% (P95: 85ms → 89ms)
│       ├─ ⚠️ Fairness: Origin=VN disparity 1.3x (vs 1.0x baseline)
│       └─ ✅ No data quality issues
│
├── 2. MODEL VERSIONS (Compare all versions)
│   ├─ v2.1 (Legacy)
│   │  ├─ Status: Deprecated
│   │  ├─ Accuracy: 0.85
│   │  ├─ AUC-ROC: 0.88
│   │  ├─ Latency: 50ms
│   │  ├─ Features: 72
│   │  └─ [View Details] [Download] [Restore]
│   │
│   ├─ v3.0 (Current Production)
│   │  ├─ Status: Production
│   │  ├─ Accuracy: 0.92
│   │  ├─ AUC-ROC: 0.94
│   │  ├─ Latency: 85ms
│   │  ├─ Features: 72
│   │  ├─ Deployed: 15 days ago
│   │  ├─ Traffic: 100%
│   │  └─ [View Details] [View Metrics] [Rollback]
│   │
│   └─ v3.1 (Staging)
│       ├─ Status: Candidate
│       ├─ Accuracy: 0.93
│       ├─ Improvement: +1.1%
│       ├─ Trained: 2 days ago
│       └─ [View Details] [Approve for Prod] [Reject]
│
├── 3. TRAINING JOBS (History of all training)
│   ├─ Job ID | Model | Status | Started | Completed | Accuracy
│   ├─ job-101 | v3.1 | ✅ Completed | 2d ago | 2d ago | 0.93
│   ├─ job-100 | v3.0 | ✅ Completed | 15d ago | 15d ago | 0.92
│   ├─ job-99 | v3.0-exp2 | ❌ Failed | 20d ago | 20d ago | N/A
│   ├─ job-98 | v2.1 | ✅ Completed | 45d ago | 45d ago | 0.85
│   └─ [View Logs] [Retry] buttons per job
│
├── 4. PERFORMANCE METRICS (Track over time)
│   ├─ Accuracy (by version)
│   │  ├─ v2.1: 0.85 (at deployment)
│   │  ├─ v3.0: 0.92 (current)
│   │  └─ v3.1: 0.93 (candidate)
│   │
│   ├─ Score Distribution (live)
│   │  ├─ Histogram of all scores (last 24h)
│   │  ├─ HOLD (80+): 28%
│   │  ├─ EXAMINE (50-79): 38%
│   │  └─ CLEAR (0-49): 34%
│   │
│   ├─ Latency Percentiles
│   │  ├─ P50: 75ms
│   │  ├─ P95: 85ms
│   │  ├─ P99: 120ms
│   │  └─ Max: 250ms
│   │
│   └─ Charts over time (30/90/365 day views)
│
├── 5. DATA DRIFT MONITORING
│   ├─ Current Status: NO DRIFT ✅
│   ├─ Last Check: 1 hour ago
│   │
│   ├─ Feature Distributions (samples)
│   │  ├─ origin_country: baseline vs current
│   │  ├─ declared_value: baseline vs current
│   │  ├─ dwell_days: baseline vs current
│   │  └─ [View All Features]
│   │
│   └─ Historical Drift (detected in past)
│       ├─ 2026-05-15: Drift detected in vessel_flag
│       ├─ 2026-04-20: Drift detected in hs_code
│       └─ Action taken: Model retrained
│
├── 6. MODEL EXPLANATIONS (Per Shipment)
│   ├─ Select shipment: [SHP-12345]
│   │
│   ├─ Prediction Details
│   │  ├─ Score: 75.3
│   │  ├─ Confidence: 89%
│   │  ├─ Recommendation: EXAMINE
│   │  └─ Why: ▼
│   │
│   ├─ Top Contributing Factors (SHAP)
│   │  ├─ 1. element9_mismatch=true: +15.3
│   │  ├─ 2. origin_country=CN: +12.1
│   │  ├─ 3. declared_value=80000: +8.5
│   │  ├─ 4. dwell_days=6.5: +5.2
│   │  └─ 5. shipper_age_months=8: +3.1
│   │  ├─ Base value: 50.0
│   │  └─ = Final score: 75.3
│   │
│   └─ Similar Shipments (with this pattern)
│       ├─ SHP-12344: score=73.1, prediction=correct
│       ├─ SHP-12342: score=76.5, prediction=correct
│       └─ Pattern success rate: 92%
│
├── 7. FAIRNESS & BIAS DETECTION
│   ├─ Segmented Performance
│   │  ├─ Origin Country
│   │  │  ├─ CN: 2,100 predictions, HOLD rate: 30%, disparity: 1.1x
│   │  │  ├─ VN: 800 predictions, HOLD rate: 29%, disparity: 1.0x
│   │  │  ├─ SG: 450 predictions, HOLD rate: 25%, disparity: 0.9x
│   │  │  └─ ⚠️ Flag: CN disparity > 1.2x threshold
│   │  │
│   │  ├─ Shipment Value
│   │  │  ├─ <$10K: 300 predictions, HOLD rate: 15%
│   │  │  ├─ $10K-$50K: 1,500 predictions, HOLD rate: 28%
│   │  │  └─ >$50K: 2,000 predictions, HOLD rate: 32%
│   │  │
│   │  └─ Commodity Type
│   │     ├─ Electronics: HOLD rate: 32%
│   │     ├─ Textiles: HOLD rate: 25%
│   │     └─ Chemicals: HOLD rate: 28%
│   │
│   └─ Action: Review if disparities acceptable
│
├── 8. RETRAINING CONFIGURATION
│   ├─ Current Schedule: Daily at 2:00 AM
│   ├─ Retraining Triggers:
│   │  ├─ ☑ Scheduled (daily)
│   │  ├─ ☑ Performance degradation (accuracy < 0.91)
│   │  ├─ ☑ Data drift detected (KL-divergence > 0.05)
│   │  ├─ ☑ Prediction drift (score distribution changes > 10%)
│   │  └─ ☑ Manual request
│   │
│   ├─ Validation Before Deploy
│   │  ├─ ☑ Must improve accuracy by > 0.5%
│   │  ├─ ☑ Must pass fairness checks
│   │  ├─ ☑ Must have < 2% latency increase
│   │  └─ ☑ Must be approved by manager
│   │
│   └─ [Trigger Training Now] [Edit Config]
│
├── 9. APPROVAL QUEUE (For new models)
│   ├─ v3.1 Staging Review
│   │  ├─ Submitted by: Data Scientist Alice
│   │  ├─ Submitted at: 2026-06-11 10:30 AM
│   │  ├─ Improvement vs v3.0: +1.1% accuracy
│   │  ├─ Staging test duration: 5 days ✅
│   │  ├─ No data drift detected ✅
│   │  ├─ No fairness issues ✅
│   │  │
│   │  ├─ Approvals Needed:
│   │  │  ├─ ☑ Alice (submitted)
│   │  │  ├─ ☐ Bob (manager) - Waiting
│   │  │  ├─ ☐ Charlie (domain expert) - Waiting
│   │  │  └─ Decision: 2/3 needed to approve
│   │  │
│   │  ├─ [Approve] [Request Changes] [Reject] buttons
│   │  └─ Comment box: "Looks good, but need Charlie's sign-off"
│   │
│   └─ v3.0-exp1 Rejected
│       ├─ Submitted: 20d ago
│       ├─ Rejected by: Bob
│       └─ Reason: "Latency increased too much (85ms → 120ms)"
│
└── 10. RETRAINING HISTORY
    ├─ Last 10 retrained models
    ├─ job-101 | v3.1 | 2d ago | Scheduled | Approved ✅
    ├─ job-100 | v3.0 | 15d ago | Scheduled | Approved ✅
    ├─ job-99 | v3.0-exp2 | 20d ago | Performance | Rejected ❌
    ├─ job-98 | v2.1 | 45d ago | Scheduled | Approved ✅
    └─ [Show more history]
```

---

## 5. Background Jobs in Risk Model Service

### **What Runs Automatically**

```python
# Location: services/risk-engine/background_jobs.py

class RiskModelBackgroundJobs:
    """Background tasks for complete model lifecycle"""
    
    async def scheduled_training_job(self):
        """
        Runs daily at 2:00 AM
        - Collect fresh training data (last 24 hours of new shipments)
        - Train new model version
        - Validate against test set
        - If better: candidate for approval
        """
        
    async def data_drift_detection_job(self):
        """
        Runs every 1 hour
        - Calculate distribution of features vs baseline
        - Detect statistical drift (Kolmogorov-Smirnov test)
        - If drift detected: alert + consider retraining
        """
        
    async def model_performance_monitoring_job(self):
        """
        Runs continuously (every 5 minutes)
        - Track prediction latency (P50, P95, P99)
        - Track error rate
        - Track score distribution (are outputs normal?)
        - Alert if any metric goes out of bounds
        """
        
    async def fairness_monitoring_job(self):
        """
        Runs every 4 hours
        - Calculate HOLD rate by segment (country, value, commodity)
        - Calculate disparity ratio vs population
        - Alert if disparity > threshold
        """
        
    async def retraining_trigger_evaluation_job(self):
        """
        Runs every 30 minutes
        - Check if any trigger condition met:
          * Accuracy degradation > threshold
          * Data drift detected
          * Prediction distribution changed
          * Manual request
        - If yes: queue training job
        """
        
    async def model_comparison_job(self):
        """
        Runs after each new model trained
        - Score same sample of shipments with both models
        - Calculate accuracy improvement
        - Calculate latency impact
        - Generate comparison report for approval
        """
        
    async def prediction_explanation_job(self):
        """
        Runs on every prediction (async)
        - Calculate SHAP values
        - Store feature contributions
        - Store confidence intervals
        - Available for UI query
        """
```

---

## 6. API Endpoints (Risk Model Service)

```python
# Location: services/api/routes/risk_model_service.py

@router.post("/api/model/train")
async def trigger_training(request: TrainingRequest):
    """
    Manually trigger model training
    Request: {data_source, date_range, features, hyperparameters}
    Response: {job_id, status, eta}
    """

@router.get("/api/model/jobs/{job_id}")
async def get_training_job_status(job_id: str):
    """
    Get status of a training job
    Response: {status, progress, accuracy, started_at, completed_at}
    """

@router.get("/api/model/metrics/{version}")
async def get_model_metrics(version: str):
    """
    Get all metrics for a model version
    Response: {accuracy, auc_roc, precision, recall, f1, latency}
    """

@router.post("/api/model/validate/{version}")
async def validate_model(version: str):
    """
    Run validation suite on model before deployment
    Response: {all_checks_passed, detailed_results, recommendations}
    """

@router.post("/api/model/approve/{version}")
async def request_approval(version: str, request: ApprovalRequest):
    """
    Request approval to deploy model
    Request: {stage, approvers, comment}
    Response: {approval_id, status, approvers}
    """

@router.post("/api/model/approve/{version}/vote")
async def vote_on_approval(version: str, vote: ApprovalVote):
    """
    Cast vote on model approval (requires auth)
    Request: {approver_id, vote, comment}
    Response: {approval_status, votes_received, approval_percentage}
    """

@router.get("/api/model/predictions/{shipment_id}/explain")
async def explain_prediction(shipment_id: str):
    """
    Get SHAP explanation for a shipment's prediction
    Response: {prediction, shap_values, feature_contributions, confidence}
    """

@router.get("/api/model/monitoring/drift")
async def get_drift_status():
    """
    Get current data/model drift status
    Response: {status, detected_drifts, last_check, affected_features}
    """

@router.get("/api/model/monitoring/fairness")
async def get_fairness_metrics():
    """
    Get fairness metrics by segment
    Response: {segments: [{name, predictions, hold_rate, disparity}]}
    """

@router.get("/api/model/compare/{version1}/{version2}")
async def compare_models(version1: str, version2: str):
    """
    Compare two model versions side-by-side
    Response: {accuracy_diff, latency_diff, score_distribution_diff}
    """
```

---

## 7. Complete Data Flow (Not GitHub Actions)

```
┌─────────────────────────────────────────────────────────┐
│ 1. SCHEDULED TRAINING (Daily at 2:00 AM)                │
└─────────────────────────────────────────────────────────┘
                          ↓
    Risk Model Service Scheduler wakes up
    ├─ Collect training data (last 24h)
    ├─ Train new model
    ├─ Validate on test set
    ├─ Calculate metrics (accuracy, AUC, latency)
    ├─ Create model artifact
    ├─ Store in model registry
    └─ If better: mark as candidate
                          ↓
┌─────────────────────────────────────────────────────────┐
│ 2. ANALYST REVIEWS IN UI                                │
│    Risk Model Management Tab → Model Versions           │
└─────────────────────────────────────────────────────────┘
    Analyst sees:
    ├─ v3.1 candidate (0.93 accuracy, +1.1% improvement)
    ├─ Comparison vs v3.0
    ├─ SHAP explanations on sample predictions
    ├─ Fairness metrics by segment
    └─ [Approve] button
                          ↓
┌─────────────────────────────────────────────────────────┐
│ 3. APPROVAL WORKFLOW (In UI)                            │
└─────────────────────────────────────────────────────────┘
    ├─ Analyst clicks [Approve for Staging]
    ├─ Model moves to staging (shadow mode)
    ├─ Runs alongside v3.0 for 5 days
    ├─ Tracks: accuracy, latency, fairness
    ├─ System compares: is v3.1 consistently better?
    ├─ Analyst reviews staging results
    └─ Clicks [Approve for Production]
                          ↓
┌─────────────────────────────────────────────────────────┐
│ 4. GRADUAL ROLLOUT (via UI or API)                      │
└─────────────────────────────────────────────────────────┘
    ├─ v3.1 starts at 0% traffic (only v3.0 scores shipments)
    ├─ UI shows: "Candidate ready for rollout"
    ├─ Analyst can set traffic: 0% → 10% → 50% → 100%
    ├─ Each level: monitor for 24h before increasing
    ├─ At 100%: v3.1 is now production
    └─ v3.0 demoted to "previous"
                          ↓
┌─────────────────────────────────────────────────────────┐
│ 5. CONTINUOUS MONITORING (Background)                   │
└─────────────────────────────────────────────────────────┘
    ├─ Every 5 min: track latency, error rate
    ├─ Every 1 hour: detect data drift
    ├─ Every 4 hours: calculate fairness metrics
    ├─ Every 24 hours: measure accuracy degradation
    ├─ If anomaly: alert analyst in UI
    └─ If critical: auto-rollback to previous version
                          ↓
┌─────────────────────────────────────────────────────────┐
│ 6. RETRAINING TRIGGER                                   │
│    (if monitoring detects problems)                     │
└─────────────────────────────────────────────────────────┘
    ├─ Accuracy < 0.91: trigger immediate retraining
    ├─ Data drift > threshold: trigger retraining
    ├─ Fairness disparity > threshold: trigger retraining
    └─ System queues training job
                          ↓
    Back to Step 1: New model trained and candidate ready
```

---

## 8. What's Now Self-Contained in CBP Sentry

```
❌ NO MORE:
- GitHub Actions workflow
- External training pipelines
- External approval processes
- Manual snapshot management

✅ NOW IN CBP SENTRY:
- Risk Model Management tab (UI)
- Training scheduler (background job)
- Approval workflow (in-app)
- Monitoring dashboards (UI)
- Drift detection (background job)
- Fairness metrics (background job)
- SHAP explanations (real-time)
- Model comparison (UI)
- Gradual rollout (feature flag)
- Auto-retraining triggers (background job)
```

---

## 9. Why This is Better Than GitHub Actions

| Aspect | GitHub Actions | Risk Model Service |
|---|---|---|
| **Approval** | Email-based, hard to track | In-app UI, integrated with team workflow |
| **Monitoring** | Separate dashboard | Integrated in CBP Sentry tab |
| **Data access** | Requires API calls | Direct database queries |
| **Retraining** | Manual trigger via PR | Automatic on degradation |
| **Rollback** | Code deploy (risky) | Feature flag in UI (instant) |
| **Explanations** | Batch job | Real-time per prediction |
| **Drift detection** | Email alerts | UI dashboard + notifications |
| **History** | Git log (hard to parse) | Dedicated audit tables |

---

## 10. Implementation Roadmap

### **Phase 1 (Week 1-2): Core Infrastructure**
```
- Create model versioning tables
- Create training_jobs table
- Build training scheduler
- Build background job framework
```

### **Phase 2 (Week 3): Monitoring**
```
- Create drift_detected table
- Build drift detection job
- Create fairness_metrics table
- Build fairness monitoring job
```

### **Phase 3 (Week 4): UI Tab**
```
- Build Risk Model Management tab
- Dashboard screen (overview)
- Model versions screen
- Metrics & monitoring screen
```

### **Phase 4 (Week 5): Approval & Rollout**
```
- Create model_approvals table
- Build approval voting system
- Integrate with gradual rollout
- Build notifications
```

### **Phase 5 (Week 6): SHAP & Explanations**
```
- Integrate SHAP library
- Store prediction explanations
- Build explainability UI
- Add per-shipment explanation view
```

---

## Summary: What Was Missing

| Component | Initial Design | Complete Design |
|---|---|---|
| Model training | ✅ Designed | ✅ + scheduled + triggers |
| Deployment | ✅ Designed | ✅ + approval workflow + gradual rollout |
| Monitoring | ❌ Missing | ✅ Drift + fairness + performance |
| Explanations | ❌ Missing | ✅ SHAP + feature attribution |
| Approval | ❌ Missing | ✅ Multi-person voting + audit trail |
| Retraining triggers | ❌ Missing | ✅ Auto on degradation + drift |
| Feature store | ❌ Missing | ✅ Centralized feature management |
| Data lineage | ❌ Missing | ✅ Track all training data used |
| UI | ❌ Missing | ✅ Complete Risk Model Management tab |
| Background jobs | ❌ Missing | ✅ Continuous monitoring + alerts |

**The initial design was 40% complete. A complete risk model service needs all 10 components.**
