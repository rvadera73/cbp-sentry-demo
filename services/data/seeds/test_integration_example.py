"""
Integration Test Example: Using Risk Model Test Data
=====================================================

This example demonstrates how to use the risk_model_test_data seeding script
in your integration tests.

Usage:
    pytest services/data/seeds/test_integration_example.py -v

Requirements:
    - Async SQLAlchemy setup
    - pytest-asyncio
    - Test database (SQLite or PostgreSQL)
"""

import pytest
import asyncio
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
import logging

# Import the seeding function
from risk_model_test_data import seed_test_data

logger = logging.getLogger(__name__)


@pytest.fixture
async def db_session():
    """Create an async database session for testing."""
    # Use in-memory SQLite for testing
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False
    )

    # Create all tables first
    async with engine.begin() as conn:
        # Run migrations here if needed
        pass

    async_session_local = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session_local() as session:
        yield session
        await session.close()

    await engine.dispose()


@pytest.mark.asyncio
async def test_seed_test_data_creates_models(db_session):
    """Test that seed_test_data creates model records."""
    counts = await seed_test_data(db_session)

    assert counts['models'] == 4, "Should create 4 models (v3.0, v3.1, v2.1, v3.2)"
    assert counts['training_jobs'] == 3, "Should create 3 training jobs"
    assert counts['metrics'] > 0, "Should create metric records"
    assert counts['predictions'] == 100, "Should create 100 predictions"
    assert counts['drift_records'] == 2, "Should create 2 drift records"
    assert counts['approvals'] == 3, "Should create 3 approval records"
    assert counts['config'] == 1, "Should create 1 config record"


@pytest.mark.asyncio
async def test_v3_0_production_model_exists(db_session):
    """Test that v3.0 production model is properly seeded."""
    await seed_test_data(db_session)

    result = await db_session.execute(text("""
        SELECT id, model_id, version, status, weights_sum, metadata
        FROM risk_models
        WHERE model_id = 'v3.0'
    """))

    model = result.fetchone()
    assert model is not None, "v3.0 model should exist"
    assert model[3] == 'production', "v3.0 should be in production status"
    assert model[4] == 100.0, "v3.0 weights_sum should be 100.0"

    import json
    metadata = json.loads(model[5])
    assert metadata['accuracy'] == 0.924, "v3.0 accuracy should be 0.924"


@pytest.mark.asyncio
async def test_v3_1_candidate_model_exists(db_session):
    """Test that v3.1 candidate model is properly seeded."""
    await seed_test_data(db_session)

    result = await db_session.execute(text("""
        SELECT id, model_id, version, status, weights_sum
        FROM risk_models
        WHERE model_id = 'v3.1'
    """))

    model = result.fetchone()
    assert model is not None, "v3.1 model should exist"
    assert model[3] == 'candidate', "v3.1 should be in candidate status"
    assert model[4] == 100.0, "v3.1 weights_sum should be 100.0"


@pytest.mark.asyncio
async def test_v2_1_deprecated_model_has_legacy_weights(db_session):
    """Test that v2.1 deprecated model has 110% weights (legacy constraint)."""
    await seed_test_data(db_session)

    result = await db_session.execute(text("""
        SELECT id, model_id, version, status, weights_sum
        FROM risk_models
        WHERE model_id = 'v2.1'
    """))

    model = result.fetchone()
    assert model is not None, "v2.1 model should exist"
    assert model[3] == 'deprecated', "v2.1 should be in deprecated status"
    assert model[4] == 110.0, "v2.1 weights_sum should be 110.0 (legacy constraint)"


@pytest.mark.asyncio
async def test_training_jobs_completed(db_session):
    """Test that training jobs are properly recorded."""
    await seed_test_data(db_session)

    result = await db_session.execute(text("""
        SELECT COUNT(*), SUM(training_records), AVG(training_records)
        FROM risk_model_training_jobs
        WHERE status = 'completed'
    """))

    row = result.fetchone()
    assert row[0] == 2, "Should have 2 completed training jobs"
    assert row[1] == 5000000, "Total training records should be 5M"


@pytest.mark.asyncio
async def test_metrics_time_series_data(db_session):
    """Test that metric time-series data is created."""
    await seed_test_data(db_session)

    # Query accuracy metrics
    result = await db_session.execute(text("""
        SELECT COUNT(*), MIN(metric_value), MAX(metric_value)
        FROM risk_model_metrics
        WHERE metric_name = 'accuracy'
    """))

    row = result.fetchone()
    assert row[0] == 24, "Should have 24 hourly accuracy metrics"
    assert 0.920 <= row[1] <= 0.924, "Min accuracy should be in 0.920-0.924 range"
    assert 0.924 <= row[2] <= 0.928, "Max accuracy should be in 0.924-0.928 range"


@pytest.mark.asyncio
async def test_fairness_metrics_by_origin(db_session):
    """Test that fairness metrics are seeded for each origin."""
    await seed_test_data(db_session)

    result = await db_session.execute(text("""
        SELECT DISTINCT segment
        FROM risk_model_metrics
        WHERE metric_name = 'accuracy_by_origin'
    """))

    origins = {row[0] for row in result.fetchall()}
    expected_origins = {'CN', 'VN', 'MX', 'IN', 'HK'}
    assert origins == expected_origins, f"Should have accuracy metrics for {expected_origins}"


@pytest.mark.asyncio
async def test_predictions_mixed_classifications(db_session):
    """Test that predictions have realistic classification mix."""
    await seed_test_data(db_session)

    result = await db_session.execute(text("""
        SELECT classification, COUNT(*) as count
        FROM risk_model_predictions
        GROUP BY classification
    """))

    classifications = {row[0]: row[1] for row in result.fetchall()}
    assert sum(classifications.values()) == 100, "Should have 100 predictions total"
    assert 'EXAMINE' in classifications, "Should have EXAMINE classifications"
    assert 'HOLD' in classifications, "Should have HOLD classifications"
    assert 'CLEAR' in classifications, "Should have CLEAR classifications"


@pytest.mark.asyncio
async def test_predictions_have_shap_values(db_session):
    """Test that predictions include SHAP values."""
    await seed_test_data(db_session)

    result = await db_session.execute(text("""
        SELECT shap_values
        FROM risk_model_predictions
        LIMIT 1
    """))

    row = result.fetchone()
    assert row is not None, "Should have at least one prediction"

    import json
    shap = json.loads(row[0])
    expected_keys = [
        'isf_element9_mismatch', 'shipper_age_months', 'origin_country_risk',
        'commodity_value', 'ais_dwell_anomaly', 'price_variance_pct', 'vessel_routing_flag'
    ]
    for key in expected_keys:
        assert key in shap, f"SHAP values should include {key}"


@pytest.mark.asyncio
async def test_drift_origin_country_elevated(db_session):
    """Test that origin_country drift is marked as elevated."""
    await seed_test_data(db_session)

    result = await db_session.execute(text("""
        SELECT feature_name, drift_score, status
        FROM risk_model_drift_detected
        WHERE feature_name = 'origin_country'
    """))

    row = result.fetchone()
    assert row is not None, "Should have origin_country drift record"
    assert row[1] == 0.34, "Drift score should be 0.34 (elevated)"
    assert row[2] == 'acknowledged', "Status should be acknowledged"


@pytest.mark.asyncio
async def test_drift_commodity_value_normal(db_session):
    """Test that commodity_value drift is marked as normal."""
    await seed_test_data(db_session)

    result = await db_session.execute(text("""
        SELECT feature_name, drift_score, status
        FROM risk_model_drift_detected
        WHERE feature_name = 'commodity_value_usd'
    """))

    row = result.fetchone()
    assert row is not None, "Should have commodity_value_usd drift record"
    assert row[1] == 0.08, "Drift score should be 0.08 (normal)"
    assert row[2] == 'resolved', "Status should be resolved"


@pytest.mark.asyncio
async def test_v3_1_approval_pending_one_vote(db_session):
    """Test that v3.1 has pending approval with 1/3 votes."""
    await seed_test_data(db_session)

    result = await db_session.execute(text("""
        SELECT status, approval_stage, voters
        FROM risk_model_approvals
        WHERE approval_request_id LIKE '%v3.1%'
    """))

    row = result.fetchone()
    assert row is not None, "Should have v3.1 approval record"
    assert row[0] == 'pending', "Status should be pending"
    assert row[1] == '1/3', "Should show 1/3 votes"

    import json
    voters = json.loads(row[2])
    assert voters['chief_data_officer']['vote'] == 'approve', "CDO should approve"
    assert voters['chief_risk_officer']['vote'] is None, "CRO should not have voted"


@pytest.mark.asyncio
async def test_v3_0_approval_approved_deployed(db_session):
    """Test that v3.0 has approved status and is deployed."""
    await seed_test_data(db_session)

    result = await db_session.execute(text("""
        SELECT status, approval_stage, deployed_at
        FROM risk_model_approvals
        WHERE approval_request_id LIKE '%v3.0%'
    """))

    row = result.fetchone()
    assert row is not None, "Should have v3.0 approval record"
    assert row[0] == 'approved', "Status should be approved"
    assert row[1] == '2/3', "Should show 2/3 votes"
    assert row[2] is not None, "deployed_at should be set"


@pytest.mark.asyncio
async def test_retraining_config_enabled(db_session):
    """Test that retraining config is properly configured."""
    await seed_test_data(db_session)

    result = await db_session.execute(text("""
        SELECT enabled, schedule_frequency, drift_threshold,
               model_degradation_threshold, error_threshold
        FROM risk_retraining_config
        WHERE config_name = 'Default CBP Sentry Retraining Configuration'
    """))

    row = result.fetchone()
    assert row is not None, "Should have retraining config"
    assert row[0] == 1, "Should be enabled"
    assert row[1] == 'weekly', "Should be weekly"
    assert row[2] == 0.30, "Drift threshold should be 0.30"
    assert row[3] == -2.0, "Model degradation threshold should be -2.0%"
    assert row[4] == 5.0, "Error threshold should be 5.0%"


# =====================================================================
# Example: Running a specific test
# =====================================================================
if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
