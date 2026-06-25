# Risk Model Test Data Seeding

Comprehensive test data seeding script for CBP Sentry risk model integration tests.

## Overview

The `risk_model_test_data.py` module provides the `seed_test_data()` async function that populates all seven risk model management tables with realistic, consistent test data:

1. **risk_models** — Model registry (v3.0 production, v3.1 candidate, v2.1 deprecated, v3.2 in-training)
2. **risk_model_training_jobs** — Training job history with execution metrics
3. **risk_model_metrics** — 24 hours of time-series performance metrics
4. **risk_model_predictions** — 100 real shipment predictions with SHAP explanations
5. **risk_model_drift_detected** — Data and model drift detection alerts
6. **risk_model_approvals** — Multi-voter approval workflow state
7. **risk_retraining_config** — Automated retraining configuration

## Quick Start

### Basic Usage

```python
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from services.data.seeds import seed_test_data

async def main():
    # Create async engine and session
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async_session = async_sessionmaker(engine, class_=AsyncSession)
    
    async with async_session() as session:
        # Seed test data
        counts = await seed_test_data(session)
        print(f"Seeded {sum(counts.values())} records")
        # Output: Seeded 434 records
```

### In Pytest Fixtures

```python
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from services.data.seeds import seed_test_data

@pytest.fixture
async def seeded_db():
    """Database fixture with test data."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async_session = async_sessionmaker(engine, class_=AsyncSession)
    
    async with async_session() as session:
        await seed_test_data(session)
        yield session

@pytest.mark.asyncio
async def test_model_registry(seeded_db):
    """Test with seeded database."""
    result = await seeded_db.execute(text("""
        SELECT COUNT(*) FROM risk_models WHERE status = 'production'
    """))
    count = result.scalar()
    assert count == 1  # v3.0 is the only production model
```

## Data Structures

### Models (risk_models)

| Version | Status | Weights Sum | Accuracy | Purpose |
|---------|--------|------------|----------|---------|
| v3.0 | production | 100.0% | 0.924 | Current production model |
| v3.1 | candidate | 100.0% | 0.931 | Awaiting approval (1/3 votes) |
| v2.1 | deprecated | 110.0% | 0.891 | Legacy constraint testing |
| v3.2 | training | 100.0% | N/A | In-progress (45% trained) |

### Training Jobs (risk_model_training_jobs)

| Job ID | Model | Status | Records | Duration | Purpose |
|--------|-------|--------|---------|----------|---------|
| job-20260611-093001 | v3.1 | completed | 2.5M | 6.2h | Completed training |
| job-20260612-143501 | v3.0 | completed | 2.5M | 5.5h | Production training |
| job-20260613-020000 | v3.2 | running | 2.5M | in-progress | Current training |

### Metrics (risk_model_metrics)

24 hours of time-series data per v3.0 production model:

- **Accuracy**: 0.920–0.928 range (hourly oscillation)
- **Latency**: 80–90ms range (hourly oscillation)
- **Confidence**: 0.85–0.89 range (hourly oscillation)
- **Fairness by Origin**:
  - China (CN): 0.921 accuracy, 0.89 confidence
  - Vietnam (VN): 0.927 accuracy, 0.91 confidence
  - Mexico (MX): 0.925 accuracy, 0.88 confidence
  - India (IN): 0.920 accuracy, 0.87 confidence
  - Hong Kong (HK): 0.926 accuracy, 0.90 confidence

### Predictions (risk_model_predictions)

100 shipment predictions with realistic risk profiles:

- **Score Distribution**:
  - High-risk (EXAMINE): 70–92 scores
  - Medium-risk (HOLD): 40–70 scores
  - Low-risk (CLEAR): <40 scores

- **SHAP Values Included**:
  - ISF Element 9 mismatch contribution
  - Shipper age (months) contribution
  - Origin country risk contribution
  - Commodity value contribution
  - AIS dwell anomaly contribution
  - Price variance contribution
  - Vessel routing flag contribution

- **Real Shipment Scenarios**:
  - Vietnam aluminum with ISF Element 9 mismatch (high-risk pattern)
  - China electronics with AIS dwell anomaly (medium-risk)
  - India textiles with price variance (medium-risk)
  - Mexico produce with established shipper (low-risk)
  - Canadian machinery (low-risk)

### Drift Detection (risk_model_drift_detected)

Two drift records demonstrating monitoring:

1. **Origin Country Drift** (Data Drift)
   - Drift Score: 0.34 (elevated)
   - Status: acknowledged
   - Baseline: CN=22%, VN=18%, MX=20%, IN=15%, TH=12%, Other=13%
   - Current: CN=28%, VN=16%, MX=19%, IN=14%, TH=11%, Other=12%
   - Interpretation: Increased China shipments, decreased Vietnam

2. **Commodity Value Drift** (Data Drift)
   - Drift Score: 0.08 (normal)
   - Status: resolved
   - Baseline Mean: $52,340.50
   - Current Mean: $51,890.20
   - Interpretation: Minor variation, within normal range

### Approvals (risk_model_approvals)

Three approval records showing workflow states:

1. **v3.1 Promotion** (Pending)
   - Status: pending
   - Votes: 1/3 (Chief Data Officer approved, waiting on Risk Officer and Operations)
   - Reason: Higher accuracy (0.931 vs 0.924), improved fairness metrics
   - Request Time: 18 hours ago

2. **v3.0 Production** (Approved & Deployed)
   - Status: approved
   - Votes: 2/3 (CDO and CRO approved, Operations didn't vote)
   - Deployed: 2 days ago
   - Traffic: 10% initially, monitoring for issues

3. **v2.2 Rejection** (Rejected)
   - Status: rejected
   - Reason: Validation failures on fairness tests (MX, IN origins), precision drop
   - Vote: Chief Data Officer rejected
   - Test Failures: 8 fairness test failures

### Configuration (risk_retraining_config)

Single configuration record for automated retraining:

```json
{
  "enabled": true,
  "schedule_frequency": "weekly",
  "schedule_time": "02:00 UTC",
  "data_window_days": 7,
  "drift_threshold": 0.30,
  "drift_persistence_hours": 24,
  "model_degradation_threshold": -2.0,  // Trigger if accuracy drops 2%
  "evaluation_window_days": 7,
  "min_predictions_threshold": 10000,
  "error_threshold": 5.0,
  "error_persistence_minutes": 30,
  "notification_email": true,
  "notification_slack": true,
  "last_triggered_at": "6 days ago",
  "last_triggered_reason": "Weekly scheduled retraining completed successfully"
}
```

## Record Counts

The `seed_test_data()` function returns a dictionary with counts:

```python
counts = await seed_test_data(session)
# {
#     'models': 4,            # v3.0, v3.1, v2.1, v3.2
#     'training_jobs': 3,     # v3.1 (completed), v3.0 (completed), v3.2 (running)
#     'metrics': 145,         # 24 × 3 (accuracy, latency, confidence) + 10 fairness metrics × 2 types
#     'predictions': 100,     # 100 shipment predictions
#     'drift_records': 2,     # origin_country, commodity_value
#     'approvals': 3,         # v3.1 pending, v3.0 approved, v2.2 rejected
#     'config': 1             # Default retraining configuration
# }
# Total: 434 records
```

## Testing Patterns

### Test a Specific Model Status

```python
@pytest.mark.asyncio
async def test_production_model_accuracy(seeded_db):
    from sqlalchemy import text
    result = await seeded_db.execute(text("""
        SELECT metadata FROM risk_models WHERE model_id = 'v3.0'
    """))
    row = result.fetchone()
    import json
    metadata = json.loads(row[0])
    assert metadata['accuracy'] == 0.924
```

### Test Approval Workflow

```python
@pytest.mark.asyncio
async def test_approval_voting(seeded_db):
    result = await seeded_db.execute(text("""
        SELECT approval_request_id, voters FROM risk_model_approvals
        WHERE approval_request_id LIKE '%v3.1%'
    """))
    row = result.fetchone()
    import json
    voters = json.loads(row[1])
    # Verify vote states
    assert voters['chief_data_officer']['vote'] == 'approve'
    assert voters['chief_risk_officer']['vote'] is None
```

### Test Metrics Time Series

```python
@pytest.mark.asyncio
async def test_24h_accuracy_trend(seeded_db):
    result = await seeded_db.execute(text("""
        SELECT COUNT(*) FROM risk_model_metrics
        WHERE metric_name = 'accuracy'
    """))
    count = result.scalar()
    assert count == 24, "Should have hourly accuracy metrics"
```

### Test Drift Detection

```python
@pytest.mark.asyncio
async def test_drift_monitoring(seeded_db):
    result = await seeded_db.execute(text("""
        SELECT feature_name, drift_score, status
        FROM risk_model_drift_detected
        WHERE drift_score > 0.30
    """))
    rows = result.fetchall()
    assert len(rows) == 1, "Should have one elevated drift alert"
    assert rows[0][0] == 'origin_country'
```

## Integration with Migrations

The seed data is designed to work with the v4.0 risk model management migration:

```bash
# Run migration to create tables
alembic upgrade head

# Then seed test data
python -c "
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from services.data.seeds import seed_test_data

async def main():
    engine = create_async_engine('postgresql+asyncpg://user:pwd@localhost/dbname')
    async_session = async_sessionmaker(engine, class_=AsyncSession)
    async with async_session() as session:
        await seed_test_data(session)

asyncio.run(main())
"
```

## Data Consistency

The test data maintains realistic relationships:

1. **Model Status Progression**: v2.1 (deprecated) → v3.0 (production) → v3.1 (candidate) → v3.2 (training)
2. **Training Job Alignment**: Each job is linked to its model version
3. **Metrics Temporal Consistency**: All metrics use realistic timestamps
4. **Predictions Linked to Active Model**: All 100 predictions use v3.0 (production model)
5. **Approval Records**: Match their respective model IDs
6. **Drift Detection**: Features are realistic for CBP operations (origin country, commodity value)

## Performance Characteristics

- **Seed Time**: ~500ms for 434 records (on modern hardware)
- **Memory Usage**: Minimal; all operations are async
- **Database Size**: ~2MB for SQLite in-memory test database

## Troubleshooting

### Error: "Can't resolve foreign key"

Ensure tables are created before seeding:

```python
async with engine.begin() as conn:
    # Run migrations first
    from services.data.migrations.v4_0_risk_model_management import upgrade
    await upgrade(session)

# Then seed
await seed_test_data(session)
```

### Error: "Column not found"

Verify that all migration tables exist:

```sql
SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'risk_%';
```

### Missing time-series data

The script generates 24 hours of historical metrics. If queries only show recent data, adjust the time window:

```python
result = await session.execute(text("""
    SELECT * FROM risk_model_metrics
    WHERE timestamp >= datetime('now', '-24 hours')
"""))
```

## References

- [Migration v4.0 — Risk Model Management](../migrations/v4_0_risk_model_management.py)
- [Async SQLAlchemy Documentation](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [Pytest Async Testing](https://pytest-asyncio.readthedocs.io/)
