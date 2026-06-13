"""
Migration: Risk Model Management Tab (v4.0)
Date: 2026-06-12
Status: Production-ready

This migration creates the complete Risk Model Management infrastructure:

1. risk_models — Core model registry with versioning, status, and approval tracking
2. risk_model_training_jobs — Training job history with hyperparameters and metrics
3. risk_model_metrics — Time-series performance metrics (accuracy, latency, fairness)
4. risk_model_predictions — Individual prediction records with SHAP explanations
5. risk_model_drift_detected — Data/model drift detection alerts and tracking
6. risk_model_approvals — Multi-voter approval workflow with audit trail
7. risk_retraining_config — Automated retraining triggers and schedules

All tables include:
- Proper primary keys and foreign keys
- Production-ready indexes for query performance
- Constraints for data integrity
- Audit columns (created_at, created_by, updated_at, etc.)
- JSON fields for flexible metadata storage
"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


async def upgrade(session: AsyncSession):
    """Apply migration: create risk model management infrastructure"""

    try:
        # ========================================================================
        # TABLE 1: risk_models
        # Core registry for all model versions (v2.1, v3.0, v3.1, etc.)
        # ========================================================================
        print("📝 Creating risk_models table...")
        await session.execute(text("""
            CREATE TABLE IF NOT EXISTS risk_models (
                id TEXT PRIMARY KEY,
                model_id TEXT UNIQUE NOT NULL,
                version TEXT NOT NULL,
                name TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN (
                    'training', 'staging', 'candidate', 'production', 'deprecated'
                )),
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
        print("✅ risk_models table created")

        # Create indexes on risk_models
        print("📝 Creating indexes on risk_models...")
        await session.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_risk_models_status ON risk_models(status)"
        ))
        await session.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_risk_models_deployed ON risk_models(deployed_at)"
        ))
        await session.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_risk_models_created ON risk_models(created_at)"
        ))
        print("✅ Indexes created on risk_models")

        # ========================================================================
        # TABLE 2: risk_model_training_jobs
        # Execution history: when models are trained, what data, results
        # ========================================================================
        print("📝 Creating risk_model_training_jobs table...")
        await session.execute(text("""
            CREATE TABLE IF NOT EXISTS risk_model_training_jobs (
                id TEXT PRIMARY KEY,
                model_id TEXT NOT NULL,
                job_id TEXT UNIQUE NOT NULL,
                dataset_id TEXT,
                status TEXT NOT NULL CHECK(status IN (
                    'queued', 'running', 'completed', 'failed'
                )),
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
        print("✅ risk_model_training_jobs table created")

        # Create indexes on training_jobs
        print("📝 Creating indexes on risk_model_training_jobs...")
        await session.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_training_jobs_model ON risk_model_training_jobs(model_id)"
        ))
        await session.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_training_jobs_status ON risk_model_training_jobs(status)"
        ))
        await session.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_training_jobs_started ON risk_model_training_jobs(started_at)"
        ))
        await session.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_training_jobs_completed ON risk_model_training_jobs(completed_at)"
        ))
        print("✅ Indexes created on risk_model_training_jobs")

        # ========================================================================
        # TABLE 3: risk_model_metrics
        # Time-series metrics: accuracy, latency, AUC, fairness, etc.
        # ========================================================================
        print("📝 Creating risk_model_metrics table...")
        await session.execute(text("""
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
        print("✅ risk_model_metrics table created")

        # Create composite index for fast time-series queries
        print("📝 Creating indexes on risk_model_metrics...")
        await session.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_metrics_model_time ON risk_model_metrics(model_id, timestamp)"
        ))
        await session.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_metrics_name ON risk_model_metrics(metric_name)"
        ))
        await session.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_metrics_segment ON risk_model_metrics(segment)"
        ))
        print("✅ Indexes created on risk_model_metrics")

        # ========================================================================
        # TABLE 4: risk_model_predictions
        # Individual prediction records with SHAP explanations
        # ========================================================================
        print("📝 Creating risk_model_predictions table...")
        await session.execute(text("""
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
        print("✅ risk_model_predictions table created")

        # Create indexes for prediction lookups
        print("📝 Creating indexes on risk_model_predictions...")
        await session.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_predictions_shipment ON risk_model_predictions(shipment_id)"
        ))
        await session.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_predictions_model ON risk_model_predictions(model_id)"
        ))
        await session.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_predictions_created ON risk_model_predictions(created_at)"
        ))
        await session.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_predictions_score ON risk_model_predictions(score)"
        ))
        print("✅ Indexes created on risk_model_predictions")

        # ========================================================================
        # TABLE 5: risk_model_drift_detected
        # Drift detection alerts: data drift, model drift
        # ========================================================================
        print("📝 Creating risk_model_drift_detected table...")
        await session.execute(text("""
            CREATE TABLE IF NOT EXISTS risk_model_drift_detected (
                id TEXT PRIMARY KEY,
                model_id TEXT,
                feature_name TEXT NOT NULL,
                drift_type TEXT NOT NULL CHECK(drift_type IN (
                    'data_drift', 'model_drift', 'error_spike'
                )),
                drift_score FLOAT NOT NULL,
                baseline_distribution JSON,
                current_distribution JSON,
                detected_at DATETIME NOT NULL,
                status TEXT NOT NULL CHECK(status IN (
                    'new', 'acknowledged', 'resolved'
                )),
                root_cause TEXT,
                action_taken TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (model_id) REFERENCES risk_models(id) ON DELETE SET NULL
            )
        """))
        print("✅ risk_model_drift_detected table created")

        # Create indexes for drift monitoring
        print("📝 Creating indexes on risk_model_drift_detected...")
        await session.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_drift_model ON risk_model_drift_detected(model_id)"
        ))
        await session.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_drift_detected ON risk_model_drift_detected(detected_at)"
        ))
        await session.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_drift_status ON risk_model_drift_detected(status)"
        ))
        await session.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_drift_type ON risk_model_drift_detected(drift_type)"
        ))
        print("✅ Indexes created on risk_model_drift_detected")

        # ========================================================================
        # TABLE 6: risk_model_approvals
        # Multi-voter approval workflow for model deployments
        # ========================================================================
        print("📝 Creating risk_model_approvals table...")
        await session.execute(text("""
            CREATE TABLE IF NOT EXISTS risk_model_approvals (
                id TEXT PRIMARY KEY,
                model_id TEXT NOT NULL,
                approval_request_id TEXT UNIQUE NOT NULL,
                requested_by TEXT NOT NULL,
                requested_at DATETIME NOT NULL,
                request_reason TEXT,
                voters JSON,
                status TEXT NOT NULL CHECK(status IN (
                    'pending', 'approved', 'rejected', 'expired'
                )),
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
        print("✅ risk_model_approvals table created")

        # Create indexes for approval workflow
        print("📝 Creating indexes on risk_model_approvals...")
        await session.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_approvals_model ON risk_model_approvals(model_id)"
        ))
        await session.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_approvals_status ON risk_model_approvals(status)"
        ))
        await session.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_approvals_requested ON risk_model_approvals(requested_at)"
        ))
        await session.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_approvals_requested_by ON risk_model_approvals(requested_by)"
        ))
        print("✅ Indexes created on risk_model_approvals")

        # ========================================================================
        # TABLE 7: risk_retraining_config
        # Configuration for automated retraining triggers
        # ========================================================================
        print("📝 Creating risk_retraining_config table...")
        await session.execute(text("""
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
        print("✅ risk_retraining_config table created")

        # Create indexes on config
        print("📝 Creating indexes on risk_retraining_config...")
        await session.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_retraining_config_enabled ON risk_retraining_config(enabled)"
        ))
        await session.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_retraining_config_triggered ON risk_retraining_config(last_triggered_at)"
        ))
        print("✅ Indexes created on risk_retraining_config")

        # ========================================================================
        # Seed initial data
        # ========================================================================
        print("\n📝 Seeding initial data...")

        # Insert v3.0 as initial production model
        await session.execute(text("""
            INSERT OR IGNORE INTO risk_models
            (id, model_id, version, name, status, framework, model_type, feature_count, weights_sum, created_by, approved_by, deployed_at)
            VALUES
            (
                'model-v3.0-prod',
                'v3.0',
                '3.0',
                'CBP Risk Model v3.0',
                'production',
                'xgboost',
                'classification',
                47,
                100.0,
                'system',
                'system',
                CURRENT_TIMESTAMP
            )
        """))
        print("✅ Initial model metadata seeded")

        # Insert default retraining configuration
        await session.execute(text("""
            INSERT OR IGNORE INTO risk_retraining_config
            (id, config_name, enabled, schedule_frequency, schedule_time, schedule_timezone,
             data_window_days, drift_threshold, drift_persistence_hours,
             model_degradation_threshold, evaluation_window_days, min_predictions_threshold,
             error_threshold, error_persistence_minutes, notification_email, notification_slack)
            VALUES
            (
                'config-default',
                'Default Retraining Config',
                1,
                'weekly',
                '02:00',
                'UTC',
                7,
                0.30,
                24,
                -2.0,
                7,
                10000,
                5.0,
                30,
                1,
                1
            )
        """))
        print("✅ Default retraining configuration seeded")

        await session.commit()
        print("\n✅ Migration completed successfully!")
        print("   - Created 7 tables for Risk Model Management")
        print("   - Added 20+ production-ready indexes")
        print("   - Configured foreign key constraints")
        print("   - Seeded initial model and configuration data")
        print("\nTables created:")
        print("   1. risk_models (model registry)")
        print("   2. risk_model_training_jobs (training history)")
        print("   3. risk_model_metrics (time-series metrics)")
        print("   4. risk_model_predictions (individual predictions)")
        print("   5. risk_model_drift_detected (drift alerts)")
        print("   6. risk_model_approvals (approval workflow)")
        print("   7. risk_retraining_config (automated triggers)")

    except Exception as e:
        await session.rollback()
        logger.error(f"❌ Migration failed: {e}")
        raise


async def downgrade(session: AsyncSession):
    """Rollback migration: remove risk model management infrastructure"""

    try:
        print("🔄 Rolling back Risk Model Management migration...")

        # Drop tables in reverse dependency order
        tables_to_drop = [
            'risk_retraining_config',
            'risk_model_approvals',
            'risk_model_drift_detected',
            'risk_model_predictions',
            'risk_model_metrics',
            'risk_model_training_jobs',
            'risk_models'
        ]

        for table in tables_to_drop:
            print(f"   Dropping {table}...")
            await session.execute(text(f"DROP TABLE IF EXISTS {table}"))

        await session.commit()
        print("✅ Rollback completed")
        print("   All risk model management tables removed")

    except Exception as e:
        await session.rollback()
        logger.error(f"❌ Rollback failed: {e}")
        raise


# ============================================================================
# SQLAlchemy ORM Models (for reference in application code)
# ============================================================================
# These models can be imported in your application to interact with the tables

"""
from sqlalchemy import Column, String, Float, Integer, DateTime, Boolean, JSON, ForeignKey, Text, CheckConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class RiskModel(Base):
    __tablename__ = "risk_models"

    id = Column(String, primary_key=True)
    model_id = Column(String, unique=True, nullable=False)
    version = Column(String, nullable=False)
    name = Column(String, nullable=False)
    status = Column(String, nullable=False)  # training, staging, candidate, production, deprecated
    framework = Column(String)
    model_type = Column(String)
    feature_count = Column(Integer)
    weights_sum = Column(Float)
    artifact_path = Column(String)
    metadata = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String)
    approved_at = Column(DateTime)
    approved_by = Column(String)
    deployed_at = Column(DateTime)
    deprecated_at = Column(DateTime)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    training_jobs = relationship("RiskModelTrainingJob", back_populates="model", cascade="all, delete-orphan")
    metrics = relationship("RiskModelMetric", back_populates="model", cascade="all, delete-orphan")
    predictions = relationship("RiskModelPrediction", back_populates="model", cascade="all, delete-orphan")
    approvals = relationship("RiskModelApproval", back_populates="model", cascade="all, delete-orphan")


class RiskModelTrainingJob(Base):
    __tablename__ = "risk_model_training_jobs"

    id = Column(String, primary_key=True)
    model_id = Column(String, ForeignKey("risk_models.id", ondelete="CASCADE"), nullable=False)
    job_id = Column(String, unique=True, nullable=False)
    dataset_id = Column(String)
    status = Column(String, nullable=False)  # queued, running, completed, failed
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    training_records = Column(Integer)
    test_records = Column(Integer)
    hyperparameters = Column(JSON)
    training_metrics = Column(JSON)
    validation_status = Column(String)
    validation_errors = Column(JSON)
    artifacts_path = Column(String)
    error_message = Column(String)
    logs_location = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    model = relationship("RiskModel", back_populates="training_jobs")


class RiskModelMetric(Base):
    __tablename__ = "risk_model_metrics"

    id = Column(String, primary_key=True)
    model_id = Column(String, ForeignKey("risk_models.id", ondelete="CASCADE"), nullable=False)
    metric_name = Column(String, nullable=False)
    metric_value = Column(Float, nullable=False)
    segment = Column(String)
    timestamp = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    model = relationship("RiskModel", back_populates="metrics")


class RiskModelPrediction(Base):
    __tablename__ = "risk_model_predictions"

    id = Column(String, primary_key=True)
    model_id = Column(String, ForeignKey("risk_models.id", ondelete="CASCADE"), nullable=False)
    shipment_id = Column(String, nullable=False)
    score = Column(Float, nullable=False)
    confidence = Column(Float)
    classification = Column(String)
    shap_values = Column(JSON)
    feature_contributions = Column(JSON)
    latency_ms = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)

    model = relationship("RiskModel", back_populates="predictions")


class RiskModelDriftDetected(Base):
    __tablename__ = "risk_model_drift_detected"

    id = Column(String, primary_key=True)
    model_id = Column(String, ForeignKey("risk_models.id", ondelete="SET NULL"))
    feature_name = Column(String, nullable=False)
    drift_type = Column(String, nullable=False)  # data_drift, model_drift, error_spike
    drift_score = Column(Float, nullable=False)
    baseline_distribution = Column(JSON)
    current_distribution = Column(JSON)
    detected_at = Column(DateTime, nullable=False)
    status = Column(String, nullable=False)  # new, acknowledged, resolved
    root_cause = Column(String)
    action_taken = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class RiskModelApproval(Base):
    __tablename__ = "risk_model_approvals"

    id = Column(String, primary_key=True)
    model_id = Column(String, ForeignKey("risk_models.id", ondelete="CASCADE"), nullable=False)
    approval_request_id = Column(String, unique=True, nullable=False)
    requested_by = Column(String, nullable=False)
    requested_at = Column(DateTime, nullable=False)
    request_reason = Column(String)
    voters = Column(JSON)  # [{user, vote, comment, voted_at, status}]
    status = Column(String, nullable=False)  # pending, approved, rejected, expired
    approval_stage = Column(String)
    approved_at = Column(DateTime)
    approved_by = Column(String)
    deployed_at = Column(DateTime)
    notes = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    model = relationship("RiskModel", back_populates="approvals")


class RiskRetrainingConfig(Base):
    __tablename__ = "risk_retraining_config"

    id = Column(String, primary_key=True)
    config_name = Column(String, unique=True, nullable=False)
    enabled = Column(Boolean, default=True)
    schedule_frequency = Column(String)  # daily, weekly, monthly
    schedule_time = Column(String)  # HH:MM
    schedule_timezone = Column(String)  # UTC
    data_window_days = Column(Integer)
    drift_threshold = Column(Float)
    drift_persistence_hours = Column(Integer)
    model_degradation_threshold = Column(Float)
    evaluation_window_days = Column(Integer)
    min_predictions_threshold = Column(Integer)
    error_threshold = Column(Float)
    error_persistence_minutes = Column(Integer)
    notification_email = Column(Boolean, default=False)
    notification_slack = Column(Boolean, default=False)
    notification_pagerduty = Column(Boolean, default=False)
    last_triggered_at = Column(DateTime)
    last_triggered_reason = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
"""


# ============================================================================
# Usage Instructions
# ============================================================================
# To apply this migration:
#
# python -c "
# import asyncio
# from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
# from migrations.v4_0_risk_model_management import upgrade
#
# async def run():
#     engine = create_async_engine('sqlite+aiosqlite:///./data/cbp_sentry.db')
#     async with AsyncSession(engine) as session:
#         await upgrade(session)
#
# asyncio.run(run())
# "
#
# To rollback:
#
# python -c "
# import asyncio
# from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
# from migrations.v4_0_risk_model_management import downgrade
#
# async def run():
#     engine = create_async_engine('sqlite+aiosqlite:///./data/cbp_sentry.db')
#     async with AsyncSession(engine) as session:
#         await downgrade(session)
#
# asyncio.run(run())
# "
