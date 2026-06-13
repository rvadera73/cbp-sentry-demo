# Performance Metrics Framework Guide

## Overview

The Performance Metrics Framework is a **multi-tenant, domain-agnostic** system for tracking model performance against contractual gates. It's designed to support CBP, FDA, Commerce, and other domains with minimal configuration changes.

**Key Design Principle:** Configuration files (YAML) are the source of truth for domain structure; MLflow tags track model-specific requirements; the generic calculation engine supports any metric type.

---

## Architecture

### Three Components

1. **Configuration (YAML)** → Domain template (reusable)
2. **MLflow Tags** → Model-specific gate requirements (versioned)
3. **Metrics Engine** → Generic calculation for any metric type

### Database Schema

Three new tables (migration v4.1):

```
performance_metrics_config
├─ id (PRIMARY KEY)
├─ domain (CBP, FDA, Commerce, etc.)
├─ model_id (v3.0, v3.1, etc.)
├─ config_json (full YAML config as JSON)
└─ created_at, updated_at

performance_metric_definitions
├─ id (PRIMARY KEY)
├─ metric_type (count_per_period, ratio, rate_of_change, threshold)
├─ metric_name (scalability, accuracy, latency, auc, error_rate)
├─ calculation_plugin (how to calculate)
├─ data_source (which table to query)
└─ documentation

performance_gate_results
├─ id (PRIMARY KEY)
├─ domain, model_id, gate_id
├─ metric_name
├─ measured_value, threshold_value
├─ status (passed/failed/error)
├─ period_start_date, period_end_date
└─ calculation_details (JSON with query info)
```

---

## Supported Metric Types

### 1. **count_per_period** — Throughput/Volume
Count rows matching a filter in a time period.

```yaml
- name: "scalability"
  type: "count_per_period"
  source: "shipments"
  filter: "status='scored' AND created_at >= date('now', '-7 days')"
  period: "week"
  threshold: 1000
  unit: "shipments"
```

**Example:** Count approved packages processed per week.

---

### 2. **ratio** — Percentage Metrics
Numerator / Denominator × 100.

```yaml
- name: "consistency"
  type: "ratio"
  numerator:
    source: "shipments"
    filter: "status='scored' AND score_variance < 0.1"
  denominator:
    source: "shipments"
    filter: "status='scored'"
  threshold: 95.0
  unit: "percentage"
```

**Example:** % of predictions with low variance.

---

### 3. **rate_of_change** — Trend Analysis
(Current - Baseline) / Baseline × 100.

```yaml
- name: "improvement"
  type: "rate_of_change"
  source: "risk_scores"
  measure: "average score"
  baseline: 0.65
  threshold: 10.0  # improvement target
  unit: "percentage"
```

**Example:** Model improvement vs. baseline accuracy.

---

### 4. **threshold** — Static Metrics
Compare a static value (from MLflow or database) against a threshold.

```yaml
- name: "accuracy"
  type: "threshold"
  source: "model_evaluation"
  measure: "accuracy"
  threshold: 0.85
  unit: "percentage"
```

**Example:** Model accuracy from test dataset.

---

## CBP Configuration (5 Gates)

File: `/home/rahulvadera/cbp-sentry/metrics_config_cbp.yml`

### Gate 1: Days 0-60 (Initial Deployment)
```
Metrics:
  - Scalability: ≥500 shipments/week
  - Accuracy: ≥85%
  - Latency P95: ≤500ms
  - AUC: ≥0.90
```

### Gate 2: Days 61-120 (Stability)
```
Metrics:
  - Scalability: ≥1000 shipments/week
  - Accuracy: ≥87%
  - Consistency: ≥95% low-variance predictions
  - AUC: ≥0.92
```

### Gate 3: Days 121-180 (Optimization)
```
Metrics:
  - Scalability: ≥2000 shipments/week
  - Accuracy: ≥90%
  - Fairness: <5% disparity across groups
  - AUC: ≥0.94
```

### Option 1: Days 90-150 (Early Unlock)
```
Metrics:
  - Scalability: ≥1500 shipments/week
  - Accuracy: ≥89%
  - Error Rate: <1%
  - AUC: ≥0.93
```

### Option 2: Days 181-270 (Extended Evaluation)
```
Metrics:
  - Scalability: ≥1200 shipments/week
  - Accuracy: ≥82%
  - Compliance: ≥95%
  - AUC: ≥0.88
```

---

## Usage Examples

### 1. Initialize Engine with Config File

```python
from services.performance_metrics_engine import PerformanceMetricsEngine
from datetime import date, timedelta

engine = PerformanceMetricsEngine(config_path="metrics_config_cbp.yml")
```

### 2. Calculate Metrics for a Period

```python
period_end = date.today()
period_start = period_end - timedelta(days=30)

results = engine.calculate_metrics(period_start, period_end)

for result in results:
    print(f"{result.metric_name}: {result.measured_value} vs {result.threshold_value} ({result.status})")
```

### 3. Query Current Gate via API

```bash
curl http://localhost:8004/api/risk-models/performance/current-gate?model_id=v3.0
```

Response:
```json
{
  "status": "active",
  "current_gate": {
    "gate_id": "3",
    "gate_name": "Optimization & Refinement",
    "timeline_days": [121, 180],
    "description": "Performance optimization and model refinement phase"
  },
  "days_since_award": 145,
  "days_until_next_gate": 35,
  "metrics_count": 4
}
```

### 4. Get Detailed Gate Status

```bash
curl http://localhost:8004/api/risk-models/performance/gate/3?model_id=v3.0&period_days=30
```

Response:
```json
{
  "gate_id": "3",
  "gate_name": "Optimization & Refinement",
  "overall_status": "failed",
  "metrics_passed": 3,
  "metrics_total": 4,
  "pass_percentage": 75.0,
  "metrics": [
    {
      "name": "scalability",
      "measured_value": 2150.0,
      "threshold_value": 2000.0,
      "status": "passed"
    },
    {
      "name": "accuracy",
      "measured_value": 0.89,
      "threshold_value": 0.90,
      "status": "failed"
    }
  ]
}
```

### 5. Train Model for Specific Gate

```bash
python3 train_with_mlflow.py --version v3.1 --gate 2
```

This:
1. Loads Gate 2 metrics config from YAML
2. Registers model v3.1 with MLflow
3. Tags in MLflow: `performance_gate=2`, `performance_config_timeline=[61, 120]`
4. Logs gate requirements as artifact

### 6. Retrieve MLflow Performance Config

```bash
curl http://localhost:8004/api/risk-models/performance/mlflow-config?model_id=v3.0
```

Response:
```json
{
  "model_id": "v3.0",
  "gate": "3",
  "tags": {
    "performance_gate": "3",
    "performance_config_timeline": "[121, 180]"
  }
}
```

---

## Adding a New Domain (FDA, Commerce)

### Step 1: Create Config File

Copy and modify `metrics_config_cbp.yml`:

```yaml
# metrics_config_fda.yml
domain: "fda"
model: "drug-inspection"
award_date: "2026-02-01"

gates:
  - gate_id: "1"
    timeline_days: [0, 90]
    gate_name: "Phase 1: Validation"
    metrics:
      - name: "accuracy"
        type: "threshold"
        source: "model_evaluation"
        measure: "accuracy"
        threshold: 0.92
        unit: "percentage"
      # Add more FDA-specific metrics
```

**Key Differences:**
- Change `domain`, `model`, `award_date`
- Define FDA-specific gates and metrics
- Adjust thresholds for FDA requirements

### Step 2: Initialize Engine for FDA

```python
engine = PerformanceMetricsEngine(config_path="metrics_config_fda.yml")
results = engine.calculate_metrics(start, end)
```

### Step 3: Deploy via MLflow

```bash
python3 train_with_mlflow.py --version fda_v1.0 --gate 1
```

The engine automatically:
- Loads `metrics_config_fda.yml`
- Calculates all metrics
- Tags in MLflow with gate info
- Stores results in `performance_gate_results`

---

## Metric Calculation Details

### count_per_period

**Query Pattern:**
```sql
SELECT COUNT(*) FROM {source}
WHERE created_at BETWEEN ? AND ?
AND ({filter_logic})
```

**Example: Scalability (shipments scored per week)**
```sql
SELECT COUNT(*) FROM shipments
WHERE created_at BETWEEN '2026-02-01' AND '2026-02-08'
AND status='scored'
AND created_at >= date('now', '-7 days')
```

### ratio

**Query Pattern:**
```
(numerator count) / (denominator count) * 100
```

**Example: Consistency (% predictions with low variance)**
```
SELECT COUNT(*) FROM shipments
WHERE status='scored' AND score_variance < 0.1
DIVIDED BY
SELECT COUNT(*) FROM shipments
WHERE status='scored'
```

### threshold

**Query Pattern:**
```sql
SELECT value FROM model_evaluation_metrics
WHERE metric_name = ?
AND model_id = ?
ORDER BY created_at DESC LIMIT 1
```

Compares static value from database or MLflow artifacts.

---

## Testing

Run test suite:

```bash
python3 -m pytest tests/test_performance_metrics.py -v -s
```

Tests verify:
- ✅ Engine initialization with config
- ✅ All 5 gates loaded
- ✅ Gate timeline logic
- ✅ Metric serialization
- ✅ Pass/fail comparison
- ✅ YAML config structure
- ✅ Database tables exist

---

## Troubleshooting

### Issue: "Gate not found"
**Solution:** Check gate_id exists in config file (1, 2, 3, option_1, option_2).

### Issue: "Database query returned no results"
**Solution:** 
- Verify table name in `source` field matches actual table
- Check `filter_logic` syntax is valid SQL
- Ensure data exists in date range

### Issue: "Metric threshold not met"
**Solution:**
- Review measured_value in API response
- Check if calculation is querying correct table
- Verify threshold value in config file

### Issue: "MLflow tags not appearing"
**Solution:**
- Run migration: `python3 run_migrations.py`
- Register model with gate: `python3 train_with_mlflow.py --gate <gate_id>`
- Check MLflow UI: http://localhost:5000

---

## API Reference

### GET /api/risk-models/performance/current-gate
Get active gate for model based on timeline.

**Query Params:**
- `model_id` (default: "v3.0") — Model version

**Returns:**
```json
{
  "status": "active|awaiting_gate",
  "current_gate": { gate info },
  "days_until_next_gate": 35
}
```

---

### GET /api/risk-models/performance/metrics
Calculate all metrics for evaluation period.

**Query Params:**
- `model_id` (default: "v3.0")
- `period_days` (default: 30)

**Returns:**
```json
[
  {
    "metric_name": "scalability",
    "measured_value": 1250.0,
    "threshold_value": 1000.0,
    "status": "passed"
  }
]
```

---

### GET /api/risk-models/performance/gate/{gate_id}
Get detailed status of specific gate.

**Query Params:**
- `gate_id` — Gate number/ID (required in path)
- `model_id` (default: "v3.0")
- `period_days` (default: 30)

**Returns:**
```json
{
  "gate_id": "3",
  "overall_status": "passed|failed",
  "metrics_passed": 3,
  "metrics_total": 4,
  "metrics": [ metric results ]
}
```

---

### GET /api/risk-models/performance/mlflow-config
Retrieve performance config from MLflow tags.

**Query Params:**
- `model_id` (default: "v3.0")

**Returns:**
```json
{
  "model_id": "v3.0",
  "gate": "3",
  "tags": { performance tags from MLflow }
}
```

---

## Design Decisions

### Why YAML + MLflow + Generic Engine?

1. **YAML Config** = Reusable domain template
   - Copy for FDA/Commerce = new domain
   - Version-controlled, readable
   - Single source of truth for structure

2. **MLflow Tags** = Model-specific versioning
   - Each model version can require different gates
   - v3.0 → Gate 3; v4.0 → Gate 2 if needed
   - Audit trail of requirements per model version

3. **Generic Engine** = No hardcoding
   - Add new metric type = one method
   - New domain = one config file
   - Calculation logic reused across all domains

### Why These 5 Gates?

- **Gate 1 (0-60)** — Prove deployment works
- **Gate 2 (61-120)** — Prove stability with volume
- **Gate 3 (121-180)** — Prove optimization complete
- **Option 1** — Early path for high performers
- **Option 2** — Extended path for special cases

---

## Next Steps

1. **Deploy dashboard screen** in React showing:
   - Current gate + days remaining
   - Metric trends (30-day charts)
   - Pass/fail status
   - Alert if approaching deadline

2. **Add more metrics** for specific domains:
   - Latency percentiles (p50, p95, p99)
   - False positive/negative rates
   - Processing cost per transaction
   - Demographic parity metrics

3. **Integrate with feedback loops:**
   - Auto-trigger retraining on gate failure
   - Notify stakeholders on gate transitions
   - Store historical gate results for trend analysis

4. **Support for custom calculations:**
   - Plugin system for domain-specific metric types
   - Custom SQL templates
   - Python calculation functions

---

## Files Reference

| File | Purpose |
|------|---------|
| `metrics_config_cbp.yml` | CBP domain config with 5 gates |
| `services/api/services/performance_metrics_engine.py` | Core calculation engine |
| `services/api/services/performance_api.py` | API endpoints |
| `services/data/migrations/v4_1_performance_metrics.py` | Database schema |
| `tests/test_performance_metrics.py` | Integration tests |
| `run_migrations.py` | Migration runner script |
| `train_with_mlflow.py` | MLflow integration (updated) |
| `services/api/main.py` | FastAPI endpoints (updated) |

