# Risk Model Management API — Implementation Complete

**File:** `/services/api/routes/risk_models.py`  
**Date:** 2026-06-13  
**Status:** Ready for Database Integration  
**Test:** Python syntax validated ✓

---

## Overview

Complete Flask API implementation for the Risk Model Management tab with 15 endpoints providing end-to-end risk model lifecycle management.

### Key Features
- **Model Versioning** — Track production, staging, candidate, and deprecated models
- **Performance Monitoring** — Time-series metrics, fairness analysis, trend detection
- **Data Drift Detection** — Kolmogorov-Smirnov statistical testing per feature
- **Prediction Explanations** — SHAP values + plain-English interpretations
- **Approval Workflow** — Multi-voter approval with audit trail
- **Automated Retraining** — Scheduled runs + drift/degradation triggers
- **Model Rollback** — Emergency downgrade to previous version with logging

---

## API Endpoints (15 Total)

### 1. Dashboard & Summary
```
GET /api/risk-models/dashboard
```
Returns active model health, 24h metrics, pending approvals, alerts, and key statistics.

**Response:** Dashboard summary with model status, metrics, alerts, and action items

---

### 2. Model Versions
```
GET /api/risk-models/versions?status=production&sort=date
```
List all model versions with optional filtering by status and sorting.

**Query Parameters:**
- `status` — Filter: production | staging | candidate | deprecated
- `sort` — Order: date (default) | status

**Response:** Array of model metadata including performance metrics

---

### 3. Model Comparison
```
POST /api/risk-models/{model_id}/compare
```
Compare two models side-by-side with performance deltas and improvement summary.

**Payload:**
```json
{
  "compare_to_model_id": "v2.1"
}
```

**Response:** Metrics comparison with improvements/regressions and overall winner

---

### 4. Training Jobs List
```
GET /api/risk-models/training-jobs?status=completed&limit=20&sort=date
```
Get training job history with filtering, pagination, and sorting.

**Query Parameters:**
- `status` — Filter: completed | running | queued | failed
- `limit` — Pagination (default: 20, max: 100)
- `sort` — Order: date | status

**Response:** Array of training jobs with metrics, hyperparameters, feature importance

---

### 5. Training Job Details
```
GET /api/risk-models/training-jobs/{job_id}
```
Get detailed status of a specific training job including progress, steps, and ETA.

**Response:** Job status with step-by-step progress, current step, ETA, and timing

---

### 6. Trigger Training Job
```
POST /api/risk-models/training-jobs
```
Queue a new training job with specified dataset and hyperparameters.

**Payload:**
```json
{
  "dataset_id": "cbp-shipments-2024",
  "hyperparameters": {
    "max_depth": 8,
    "learning_rate": 0.05,
    "n_estimators": 500
  },
  "model_version_name": "v3.2",
  "description": "Optional description"
}
```

**Response:** Job ID, status, start time, estimated duration (HTTP 201)

---

### 7. Performance Metrics
```
GET /api/risk-models/{model_id}/metrics?time_range=24h&metric=accuracy
```
Get time-series performance metrics with optional filtering.

**Query Parameters:**
- `time_range` — Window: 24h (default) | 7d | 30d
- `metric` — Type: accuracy | auc | latency | confidence | all

**Response:** Chronological array of metric points with timestamp, value, optional segment

---

### 8. Fairness Metrics
```
GET /api/risk-models/{model_id}/metrics/fairness?segment_by=origin
```
Get model performance broken down by demographic/operational segment.

**Query Parameters:**
- `segment_by` — Dimension: origin (default) | commodity | corridor

**Response:** Per-segment accuracy, precision, recall, fairness score, sample count

---

### 9. Data Drift Detection
```
GET /api/risk-models/{model_id}/drift
```
Get current data drift status comparing baseline vs current distributions.

**Response:** Overall drift score, elevated features with KS statistics, normal features, recommendations

---

### 10. Trigger Drift Detection
```
POST /api/risk-models/{model_id}/drift/detect
```
Manually queue an async drift detection analysis job.

**Response:** Job ID, status, start time, estimated completion (HTTP 202)

---

### 11. Prediction Explanation (SHAP)
```
GET /api/risk-models/predictions/{shipment_id}/explain?model_version=v3.0&compare_to=v2.1
```
Get SHAP explanation showing feature contributions to prediction score.

**Query Parameters:**
- `model_version` — Model: v3.0 (default) | v2.1 | etc
- `compare_to` — Optional comparison model

**Response:** Shipment data, prediction, SHAP values (base + positive/negative factors), interpretation, optional comparison

---

### 12. Approval Requests
```
GET /api/risk-models/approvals?status=pending
```
Get model promotion approval requests with voting status.

**Query Parameters:**
- `status` — Filter: pending (default) | approved | rejected

**Response:** Array of approval requests with voters, votes summary, deadline, performance improvements

---

### 13. Cast Approval Vote
```
POST /api/risk-models/approvals/{approval_id}/vote
```
Record an approval vote (approve/reject/abstain) with optional comment.

**Payload:**
```json
{
  "vote": "approve",
  "comment": "FPR reduction is significant"
}
```

**Response:** Vote recorded, updated votes summary, threshold status, deployment readiness

---

### 14. Retraining Configuration
```
GET /api/risk-models/retraining-config
```
Get current automated retraining configuration and trigger history.

**Response:** Scheduled settings, drift trigger settings, degradation trigger settings, error trigger settings, with last trigger timestamps

---

### 15. Update Retraining Configuration
```
PUT /api/risk-models/retraining-config
```
Update automated retraining settings including frequencies, thresholds, and notifications.

**Payload:**
```json
{
  "scheduled": {
    "enabled": true,
    "frequency": "weekly",
    "day": "monday",
    "time": "02:00",
    "timezone": "UTC",
    "data_window_days": 7
  },
  "drift_triggered": {
    "enabled": true,
    "drift_threshold": 0.30,
    "persistence_hours": 24,
    "affected_features_min": 3
  },
  "model_drift_triggered": {...},
  "error_triggered": {...}
}
```

**Response:** Updated configuration with success status and timestamp

---

### 16. Model Rollback
```
POST /api/risk-models/{model_id}/rollback
```
Emergency operation to rollback from current model to a previous version.

**Payload:**
```json
{
  "reason": "Performance degradation detected",
  "notify_team": true
}
```

**Response:** Rollback status, timestamp, audit entry ID, notifications sent, action messages

---

## Error Handling

All endpoints implement comprehensive error handling:

**HTTP Status Codes:**
- `200` — Success (GET, PUT)
- `201` — Created (POST for new resources)
- `202` — Accepted (async operations like drift detection)
- `400` — Invalid parameters (validation errors)
- `404` — Resource not found
- `409` — Conflict (validation failed, e.g., model already rolled back)
- `500` — Internal server error

**Error Response Format:**
```json
{
  "error": "Error type",
  "detail": "Detailed explanation",
  "timestamp": "2026-06-13T10:20:30Z"
}
```

---

## Code Patterns

### 1. Logging
- INFO: Normal operations (request received, data retrieved)
- ERROR: Exceptions with full traceback via `exc_info=True`
- All responses logged for audit trail

### 2. Validation
- Query parameter validation with helpful error messages
- Request body validation (required vs optional fields)
- HTTP status code selection based on error type

### 3. Docstrings
- Comprehensive endpoint descriptions
- Parameter documentation with types and constraints
- Response schema with examples
- Status code reference

### 4. Database Integration Points (TODO)
All endpoints include TODO comments indicating where database queries belong:
- Query statements from risk model tables
- Filtering, aggregation, sorting logic
- Transaction creation for audit trail

---

## Integration Checklist

### Phase 1: Database Queries
- [ ] Implement `get_dashboard()` — Query risk_models, risk_model_approvals, risk_model_drift_detected
- [ ] Implement `get_model_versions()` — Query and filter risk_models table
- [ ] Implement `compare_models()` — Calculate metrics deltas between two versions
- [ ] Implement `get_training_jobs()` — Query risk_model_training_jobs with filters
- [ ] Implement `get_training_job_details()` — Query specific job progress
- [ ] Implement `get_model_metrics()` — Query risk_model_metrics time-series
- [ ] Implement `get_fairness_metrics()` — Group metrics by segment
- [ ] Implement `get_data_drift()` — Calculate KS statistics from feature distributions
- [ ] Implement `explain_prediction()` — Query risk_model_predictions + SHAP values
- [ ] Implement `get_approvals()` — Query risk_model_approvals with voting status
- [ ] Implement `vote_approval()` — Update approval votes, check threshold
- [ ] Implement `get_retraining_config()` — Query risk_retraining_config
- [ ] Implement `update_retraining_config()` — Update configuration with validation
- [ ] Implement `rollback_model()` — Update active model, create audit log

### Phase 2: External Service Integration
- [ ] Integrate precise-risk-engine service for SHAP explanations
- [ ] Implement async job queuing (training, drift detection)
- [ ] Implement notifications (Slack, email) for approval deadlines, rollbacks
- [ ] Implement audit logging to immutable audit table

### Phase 3: Testing
- [ ] Unit tests for parameter validation
- [ ] Integration tests with mock database
- [ ] End-to-end tests with real data
- [ ] Performance tests for time-series queries

---

## File Location

`/home/rahulvadera/cbp-sentry/services/api/routes/risk_models.py`

**Total Lines:** ~1,600  
**Endpoints:** 15 (12 required + 3 supporting)  
**Error Handlers:** Comprehensive try-catch on all endpoints  
**Docstrings:** Full documentation per endpoint  
**Syntax:** Validated ✓

---

## Next Steps

1. **Import in main.py** — Add router to FastAPI app
2. **Run database migrations** — Create risk model tables (schema in RISK_MODEL_MANAGEMENT_TAB_DESIGN.md)
3. **Implement TODO queries** — Connect endpoints to actual database
4. **Integration testing** — Validate with sample data
5. **Frontend integration** — Connect React UI to API endpoints

---

## Documentation References

- **Tab Design:** `RISK_MODEL_MANAGEMENT_TAB_DESIGN.md` (sections 1-5)
- **Database Schema:** `RISK_MODEL_MANAGEMENT_TAB_DESIGN.md` (section 3)
- **Data Service:** `/services/api/services/risk_model_data_service.py`
- **Mock Service:** `/services/api/services/risk_model_mock_service.py`

---

## Success Criteria

✅ All 15 endpoints implemented  
✅ Comprehensive error handling  
✅ Full docstrings with examples  
✅ Parameter validation  
✅ Logging on all operations  
✅ Python syntax validated  
✅ Matches CBP Sentry API patterns  
✅ Ready for database integration
