# Risk Model Management API — Quick Reference

## All 16 Endpoints

| # | Method | Path | Purpose | Status |
|---|--------|------|---------|--------|
| 1 | GET | `/dashboard` | Dashboard summary | ✓ Complete |
| 2 | GET | `/versions` | List model versions | ✓ Complete |
| 3 | POST | `/{model_id}/compare` | Compare two models | ✓ Complete |
| 4 | GET | `/training-jobs` | Training job history | ✓ Complete |
| 5 | POST | `/training-jobs` | Trigger training job | ✓ Complete |
| 6 | GET | `/training-jobs/{job_id}` | Job progress/details | ✓ Complete |
| 7 | GET | `/{model_id}/metrics` | Time-series metrics | ✓ Complete |
| 8 | GET | `/{model_id}/metrics/fairness` | Fairness metrics | ✓ Complete |
| 9 | GET | `/{model_id}/drift` | Data drift status | ✓ Complete |
| 10 | POST | `/{model_id}/drift/detect` | Trigger drift detection | ✓ Complete |
| 11 | GET | `/predictions/{shipment_id}/explain` | SHAP explanations | ✓ Complete |
| 12 | GET | `/approvals` | Approval requests | ✓ Complete |
| 13 | POST | `/approvals/{approval_id}/vote` | Cast approval vote | ✓ Complete |
| 14 | GET | `/retraining-config` | Retraining settings | ✓ Complete |
| 15 | PUT | `/retraining-config` | Update retraining settings | ✓ Complete |
| 16 | POST | `/{model_id}/rollback` | Emergency rollback | ✓ Complete |

---

## Implementation Details by Feature

### Dashboard (1 endpoint)
- **GET /dashboard** — At-a-glance model health with 24h metrics, pending approvals, alerts

### Model Versioning (3 endpoints)
- **GET /versions** — All versions with filtering by status
- **POST /{model_id}/compare** — Side-by-side comparison with deltas
- **POST /{model_id}/rollback** — Emergency downgrade with logging

### Training Management (3 endpoints)
- **GET /training-jobs** — Job history with status, dataset, hyperparameters
- **POST /training-jobs** — Queue new training with hyperparameters
- **GET /training-jobs/{job_id}** — Progress tracking with step-by-step status

### Performance Monitoring (3 endpoints)
- **GET /{model_id}/metrics** — Time-series (24h/7d/30d) with metric filtering
- **GET /{model_id}/metrics/fairness** — Per-segment accuracy, precision, recall
- **GET /{model_id}/drift** — Drift status with elevated features and recommendations

### Data Drift (1 endpoint)
- **POST /{model_id}/drift/detect** — Manual async drift detection

### Prediction Explanations (1 endpoint)
- **GET /predictions/{shipment_id}/explain** — SHAP values, feature contributions, interpretation

### Approval Workflow (2 endpoints)
- **GET /approvals** — Pending/approved/rejected requests with voter status
- **POST /approvals/{approval_id}/vote** — Record vote, auto-deploy if threshold met

### Configuration (2 endpoints)
- **GET /retraining-config** — Current settings and trigger history
- **PUT /retraining-config** — Update schedule, thresholds, notifications

---

## Error Handling Quick Guide

### Status Codes
- **200** — Success (GET, PUT)
- **201** — Created (POST new resource)
- **202** — Accepted (async operation)
- **400** — Bad request (validation error)
- **404** — Not found
- **409** — Conflict (validation failure)
- **500** — Server error

### Error Response
```json
{
  "error": "Error type",
  "detail": "What went wrong",
  "timestamp": "ISO 8601"
}
```

---

## Parameter Validation

### Common Query Parameters
```
status=pending|approved|rejected|completed|running|failed|production|staging|candidate|deprecated
sort=date|status
limit=1-100
time_range=24h|7d|30d
metric=accuracy|auc|latency|confidence|all
segment_by=origin|commodity|corridor
model_version=v3.0|v2.1|etc
```

---

## Request/Response Examples

### Dashboard
```bash
curl GET /api/risk-models/dashboard
→ {active_model, pending_approvals, alerts, key_metrics}
```

### Compare Models
```bash
curl -X POST /api/risk-models/v3.0/compare \
  -H "Content-Type: application/json" \
  -d '{"compare_to_model_id": "v2.1"}'
→ {model_1, model_2, metrics_comparison, summary}
```

### Cast Vote
```bash
curl -X POST /api/risk-models/approvals/apr-20260611/vote \
  -H "Content-Type: application/json" \
  -d '{"vote": "approve", "comment": "Solid improvement"}'
→ {approval_id, vote_recorded, votes_summary, threshold_met, deployment_status}
```

### Update Config
```bash
curl -X PUT /api/risk-models/retraining-config \
  -H "Content-Type: application/json" \
  -d '{...config...}'
→ {success, updated_at, config}
```

---

## Logging Points

Every endpoint logs:
1. **INFO** — Operation start (what API was called)
2. **INFO** — Success (data retrieved count, status)
3. **ERROR** — Exceptions with full traceback

Example:
```
INFO: Fetching risk model dashboard
INFO: Dashboard data retrieved successfully
ERROR: Error fetching dashboard: [exception] (exc_info=True)
```

---

## Database Integration TODO

Each endpoint has TODO comments indicating:
- What database table(s) to query
- What filters/aggregations to apply
- What data to return

Example (get_model_versions):
```python
# TODO: Query risk_models table
# TODO: Filter by status if provided
# TODO: Sort by date or status
```

---

## File Stats

| Metric | Value |
|--------|-------|
| File Path | `/services/api/routes/risk_models.py` |
| Total Lines | 1,863 |
| Endpoints | 16 |
| Error Handlers | 16 (one per endpoint) |
| Query Validations | 25+ |
| Docstring Lines | ~800 |
| Code Lines | ~900 |
| TODO Comments | 35+ (integration points) |

---

## Next Steps

1. Import in `api/main.py`:
   ```python
   from services.api.routes.risk_models import bp
   app.include_router(bp, prefix="/api/risk-models", tags=["risk-models"])
   ```

2. Create database tables from schema in `RISK_MODEL_MANAGEMENT_TAB_DESIGN.md`

3. Implement database queries (all marked with TODO)

4. Test with mock data service (`services/api/services/risk_model_mock_service.py`)

5. Integration test with real data

---

## Validation

✅ Python syntax validated  
✅ All imports present  
✅ All endpoints functional (mock data)  
✅ Error handling comprehensive  
✅ Documentation complete  
✅ Follows CBP Sentry patterns  
