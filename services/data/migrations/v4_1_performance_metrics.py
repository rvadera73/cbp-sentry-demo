"""
Migration: Performance Metrics Framework (v4.1)
Date: 2026-06-13
Status: Production-ready

This migration creates the multi-tenant performance metrics infrastructure:

1. performance_metrics_config — Domain-level configuration for metrics templates
2. performance_metric_definitions — Reusable metric definitions (scalability, accuracy, etc.)
3. performance_gate_results — Results of gate evaluations with measured vs. threshold values

All tables include:
- Proper primary keys and foreign keys
- Production-ready indexes for query performance
- Constraints for data integrity
- Audit columns (created_at, updated_at)
- JSON fields for flexible metadata storage

This framework supports multiple domains (CBP, FDA, Commerce) with:
- YAML config files as source of truth for domain structure
- MLflow tags for model-specific gate requirements
- Generic calculation engine for any metric type
"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


async def upgrade(session: AsyncSession):
    """Apply migration: create performance metrics infrastructure"""

    try:
        # ========================================================================
        # TABLE 1: performance_metrics_config
        # Domain-level configuration: templates for metrics (reusable across models)
        # ========================================================================
        print("📝 Creating performance_metrics_config table...")
        await session.execute(text("""
            CREATE TABLE IF NOT EXISTS performance_metrics_config (
                id TEXT PRIMARY KEY,
                domain TEXT NOT NULL,
                model_id TEXT,
                contract_period_start DATE,
                contract_period_end DATE,
                config_json JSON NOT NULL,
                config_source TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(domain, model_id)
            )
        """))
        print("✅ performance_metrics_config table created")

        # Create indexes on performance_metrics_config
        print("📝 Creating indexes on performance_metrics_config...")
        await session.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_metrics_config_domain ON performance_metrics_config(domain)"
        ))
        await session.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_metrics_config_model ON performance_metrics_config(model_id)"
        ))
        await session.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_metrics_config_period ON performance_metrics_config(contract_period_start, contract_period_end)"
        ))
        print("✅ Indexes created on performance_metrics_config")

        # ========================================================================
        # TABLE 2: performance_metric_definitions
        # Reusable metric definitions (scalability, accuracy, latency, etc.)
        # ========================================================================
        print("📝 Creating performance_metric_definitions table...")
        await session.execute(text("""
            CREATE TABLE IF NOT EXISTS performance_metric_definitions (
                id TEXT PRIMARY KEY,
                metric_type TEXT NOT NULL CHECK(metric_type IN (
                    'count_per_period',
                    'ratio',
                    'rate_of_change',
                    'threshold',
                    'custom'
                )),
                metric_name TEXT NOT NULL UNIQUE,
                calculation_plugin TEXT NOT NULL,
                data_source TEXT NOT NULL,
                filter_logic TEXT,
                aggregation_period TEXT,
                unit TEXT,
                documentation TEXT,
                example_config JSON,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """))
        print("✅ performance_metric_definitions table created")

        # Create indexes on metric definitions
        print("📝 Creating indexes on performance_metric_definitions...")
        await session.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_metric_defs_type ON performance_metric_definitions(metric_type)"
        ))
        await session.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_metric_defs_name ON performance_metric_definitions(metric_name)"
        ))
        print("✅ Indexes created on performance_metric_definitions")

        # ========================================================================
        # TABLE 3: performance_gate_results
        # Results of gate evaluations (measured value vs. threshold)
        # ========================================================================
        print("📝 Creating performance_gate_results table...")
        await session.execute(text("""
            CREATE TABLE IF NOT EXISTS performance_gate_results (
                id TEXT PRIMARY KEY,
                domain TEXT NOT NULL,
                model_id TEXT NOT NULL,
                gate_id TEXT NOT NULL,
                metric_name TEXT NOT NULL,
                measured_value FLOAT NOT NULL,
                threshold_value FLOAT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('passed', 'failed', 'pending', 'error')),
                period_start_date DATE NOT NULL,
                period_end_date DATE NOT NULL,
                calculated_at DATETIME NOT NULL,
                calculation_details JSON,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(domain, model_id, gate_id, metric_name, period_start_date, period_end_date)
            )
        """))
        print("✅ performance_gate_results table created")

        # Create indexes on gate results for fast queries
        print("📝 Creating indexes on performance_gate_results...")
        await session.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_gate_results_domain_model ON performance_gate_results(domain, model_id)"
        ))
        await session.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_gate_results_gate ON performance_gate_results(gate_id)"
        ))
        await session.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_gate_results_metric ON performance_gate_results(metric_name)"
        ))
        await session.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_gate_results_status ON performance_gate_results(status)"
        ))
        await session.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_gate_results_period ON performance_gate_results(period_start_date, period_end_date)"
        ))
        await session.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_gate_results_calculated ON performance_gate_results(calculated_at)"
        ))
        print("✅ Indexes created on performance_gate_results")

        # ========================================================================
        # Seed initial metric definitions
        # ========================================================================
        print("\n📝 Seeding metric definitions...")

        # Scalability metric
        await session.execute(text("""
            INSERT OR IGNORE INTO performance_metric_definitions
            (id, metric_type, metric_name, calculation_plugin, data_source,
             aggregation_period, unit, documentation)
            VALUES
            (
                'metric-scalability-001',
                'count_per_period',
                'scalability',
                'count_per_period',
                'reference_packages',
                'week',
                'packages',
                'Number of approved reference packages processed per week'
            )
        """))

        # Accuracy metric
        await session.execute(text("""
            INSERT OR IGNORE INTO performance_metric_definitions
            (id, metric_type, metric_name, calculation_plugin, data_source,
             aggregation_period, unit, documentation)
            VALUES
            (
                'metric-accuracy-001',
                'threshold',
                'accuracy',
                'threshold',
                'risk_scores',
                'static',
                'percentage',
                'Model accuracy based on test dataset evaluation'
            )
        """))

        # Latency metric
        await session.execute(text("""
            INSERT OR IGNORE INTO performance_metric_definitions
            (id, metric_type, metric_name, calculation_plugin, data_source,
             aggregation_period, unit, documentation)
            VALUES
            (
                'metric-latency-001',
                'threshold',
                'latency',
                'threshold',
                'prediction_logs',
                'week',
                'milliseconds',
                'Mean prediction latency (p95) per week'
            )
        """))

        # AUC metric
        await session.execute(text("""
            INSERT OR IGNORE INTO performance_metric_definitions
            (id, metric_type, metric_name, calculation_plugin, data_source,
             aggregation_period, unit, documentation)
            VALUES
            (
                'metric-auc-001',
                'threshold',
                'auc',
                'threshold',
                'model_evaluation',
                'static',
                'score',
                'Area Under the Curve (AUC) from model evaluation'
            )
        """))

        # Error rate metric
        await session.execute(text("""
            INSERT OR IGNORE INTO performance_metric_definitions
            (id, metric_type, metric_name, calculation_plugin, data_source,
             aggregation_period, unit, documentation)
            VALUES
            (
                'metric-error_rate-001',
                'ratio',
                'error_rate',
                'ratio',
                'prediction_logs',
                'day',
                'percentage',
                'Ratio of failed predictions to total predictions'
            )
        """))

        print("✅ Metric definitions seeded")

        await session.commit()
        print("\n✅ Migration v4.1 completed successfully!")

    except Exception as e:
        logger.error(f"Migration v4.1 failed: {e}")
        await session.rollback()
        raise


async def downgrade(session: AsyncSession):
    """Rollback migration: drop performance metrics tables"""
    try:
        print("⏮️  Rolling back migration v4.1...")

        # Drop tables in reverse order
        await session.execute(text("DROP TABLE IF EXISTS performance_gate_results"))
        await session.execute(text("DROP TABLE IF EXISTS performance_metric_definitions"))
        await session.execute(text("DROP TABLE IF EXISTS performance_metrics_config"))

        await session.commit()
        print("✅ Migration v4.1 rolled back successfully!")

    except Exception as e:
        logger.error(f"Rollback of migration v4.1 failed: {e}")
        await session.rollback()
        raise
