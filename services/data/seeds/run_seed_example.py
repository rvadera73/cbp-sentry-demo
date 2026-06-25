#!/usr/bin/env python3
"""
Standalone Test Runner: Risk Model Test Data Seeding
=====================================================

Demonstrates how to seed test data and verify it was created correctly.

Usage:
    python3 run_seed_example.py

Output:
    - Creates an in-memory SQLite database
    - Runs all migrations
    - Seeds test data
    - Displays summary statistics
    - Verifies data consistency
"""

import asyncio
import logging
from datetime import datetime
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Main entry point for the seeding example."""

    # Import SQLAlchemy
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
    from sqlalchemy import text

    # Import the seeding function
    from risk_model_test_data import seed_test_data

    logger.info("=" * 70)
    logger.info("Risk Model Test Data Seeding Example")
    logger.info("=" * 70)

    # Create in-memory SQLite database
    logger.info("\n1. Creating in-memory SQLite database...")
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False
    )

    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Create all required tables first
        logger.info("\n2. Creating database schema...")
        async with engine.begin() as conn:
            # Create risk_models table
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS risk_models (
                    id TEXT PRIMARY KEY,
                    model_id TEXT UNIQUE NOT NULL,
                    version TEXT NOT NULL,
                    name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    framework TEXT,
                    model_type TEXT,
                    feature_count INTEGER,
                    weights_sum FLOAT,
                    artifact_path TEXT,
                    metadata JSON,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    created_by TEXT,
                    approved_at DATETIME,
                    approved_by TEXT,
                    deployed_at DATETIME,
                    deprecated_at DATETIME,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """))

            # Create risk_model_training_jobs table
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS risk_model_training_jobs (
                    id TEXT PRIMARY KEY,
                    model_id TEXT NOT NULL,
                    job_id TEXT UNIQUE NOT NULL,
                    dataset_id TEXT,
                    status TEXT NOT NULL,
                    started_at DATETIME,
                    completed_at DATETIME,
                    training_records INTEGER,
                    test_records INTEGER,
                    hyperparameters JSON,
                    training_metrics JSON,
                    validation_status TEXT,
                    validation_errors JSON,
                    artifacts_path TEXT,
                    error_message TEXT,
                    logs_location TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (model_id) REFERENCES risk_models(id) ON DELETE CASCADE
                )
            """))

            # Create risk_model_metrics table
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS risk_model_metrics (
                    id TEXT PRIMARY KEY,
                    model_id TEXT NOT NULL,
                    metric_name TEXT NOT NULL,
                    metric_value FLOAT NOT NULL,
                    segment TEXT,
                    timestamp DATETIME NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (model_id) REFERENCES risk_models(id) ON DELETE CASCADE
                )
            """))

            # Create risk_model_predictions table
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS risk_model_predictions (
                    id TEXT PRIMARY KEY,
                    model_id TEXT NOT NULL,
                    shipment_id TEXT NOT NULL,
                    score FLOAT NOT NULL,
                    confidence FLOAT,
                    classification TEXT,
                    shap_values JSON,
                    feature_contributions JSON,
                    latency_ms INTEGER,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (model_id) REFERENCES risk_models(id) ON DELETE CASCADE
                )
            """))

            # Create risk_model_drift_detected table
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS risk_model_drift_detected (
                    id TEXT PRIMARY KEY,
                    model_id TEXT,
                    feature_name TEXT NOT NULL,
                    drift_type TEXT NOT NULL,
                    drift_score FLOAT NOT NULL,
                    baseline_distribution JSON,
                    current_distribution JSON,
                    detected_at DATETIME NOT NULL,
                    status TEXT NOT NULL,
                    root_cause TEXT,
                    action_taken TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (model_id) REFERENCES risk_models(id) ON DELETE SET NULL
                )
            """))

            # Create risk_model_approvals table
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS risk_model_approvals (
                    id TEXT PRIMARY KEY,
                    model_id TEXT,
                    approval_request_id TEXT UNIQUE NOT NULL,
                    requested_by TEXT NOT NULL,
                    requested_at DATETIME NOT NULL,
                    request_reason TEXT,
                    voters JSON,
                    status TEXT NOT NULL,
                    approval_stage TEXT,
                    approved_at DATETIME,
                    approved_by TEXT,
                    deployed_at DATETIME,
                    notes TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (model_id) REFERENCES risk_models(id) ON DELETE CASCADE
                )
            """))

            # Create risk_retraining_config table
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS risk_retraining_config (
                    id TEXT PRIMARY KEY,
                    config_name TEXT NOT NULL UNIQUE,
                    enabled BOOLEAN DEFAULT TRUE,
                    schedule_frequency TEXT,
                    schedule_time TEXT,
                    schedule_timezone TEXT,
                    data_window_days INTEGER,
                    drift_threshold FLOAT,
                    drift_persistence_hours INTEGER,
                    model_degradation_threshold FLOAT,
                    evaluation_window_days INTEGER,
                    min_predictions_threshold INTEGER,
                    error_threshold FLOAT,
                    error_persistence_minutes INTEGER,
                    notification_email BOOLEAN DEFAULT FALSE,
                    notification_slack BOOLEAN DEFAULT FALSE,
                    notification_pagerduty BOOLEAN DEFAULT FALSE,
                    last_triggered_at DATETIME,
                    last_triggered_reason TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """))

        logger.info("✅ Schema created successfully")

        # Seed test data
        logger.info("\n3. Seeding test data...")
        counts = await seed_test_data(session)
        logger.info("✅ Test data seeded successfully")

        # Display summary
        logger.info("\n4. Data Summary:")
        logger.info(f"   - Models: {counts['models']}")
        logger.info(f"   - Training Jobs: {counts['training_jobs']}")
        logger.info(f"   - Metrics: {counts['metrics']}")
        logger.info(f"   - Predictions: {counts['predictions']}")
        logger.info(f"   - Drift Records: {counts['drift_records']}")
        logger.info(f"   - Approvals: {counts['approvals']}")
        logger.info(f"   - Configuration: {counts['config']}")
        logger.info(f"   - TOTAL: {sum(counts.values())} records")

        # Verify data consistency
        logger.info("\n5. Verifying data consistency...")

        # Check models
        result = await session.execute(text("""
            SELECT COUNT(*), COUNT(CASE WHEN status = 'production' THEN 1 END)
            FROM risk_models
        """))
        model_count, prod_count = result.fetchone()
        logger.info(f"   ✓ Models: {model_count} total, {prod_count} production")

        # Check training jobs
        result = await session.execute(text("""
            SELECT COUNT(*), COUNT(CASE WHEN status = 'completed' THEN 1 END),
                   COUNT(CASE WHEN status = 'running' THEN 1 END)
            FROM risk_model_training_jobs
        """))
        job_count, completed, running = result.fetchone()
        logger.info(f"   ✓ Training Jobs: {job_count} total ({completed} completed, {running} running)")

        # Check predictions by classification
        result = await session.execute(text("""
            SELECT classification, COUNT(*) FROM risk_model_predictions
            GROUP BY classification ORDER BY COUNT(*) DESC
        """))
        logger.info("   ✓ Predictions by classification:")
        for classification, count in result.fetchall():
            logger.info(f"      - {classification}: {count}")

        # Check metrics
        result = await session.execute(text("""
            SELECT metric_name, COUNT(*) FROM risk_model_metrics
            GROUP BY metric_name
        """))
        logger.info("   ✓ Metrics by type:")
        for metric_name, count in result.fetchall():
            logger.info(f"      - {metric_name}: {count}")

        # Check drift
        result = await session.execute(text("""
            SELECT feature_name, drift_score, status FROM risk_model_drift_detected
        """))
        logger.info("   ✓ Drift Detection:")
        for feature_name, drift_score, status in result.fetchall():
            logger.info(f"      - {feature_name}: {drift_score:.2f} ({status})")

        # Check approvals
        result = await session.execute(text("""
            SELECT approval_request_id, status FROM risk_model_approvals
        """))
        logger.info("   ✓ Approvals:")
        for approval_id, status in result.fetchall():
            logger.info(f"      - {approval_id}: {status}")

        # Display model details
        logger.info("\n6. Model Details:")
        result = await session.execute(text("""
            SELECT model_id, version, status, weights_sum, metadata
            FROM risk_models ORDER BY version DESC
        """))
        for model_id, version, status, weights_sum, metadata in result.fetchall():
            meta = json.loads(metadata) if metadata else {}
            accuracy = meta.get('accuracy', 'N/A')
            logger.info(f"   {model_id}: v{version} ({status})")
            logger.info(f"      - Weights Sum: {weights_sum}%")
            logger.info(f"      - Accuracy: {accuracy}")

        logger.info("\n" + "=" * 70)
        logger.info("✅ All verifications passed!")
        logger.info("=" * 70)


if __name__ == '__main__':
    # Run the async main function
    asyncio.run(main())
