#!/usr/bin/env python3
"""
Run database migrations to set up performance metrics schema.

Usage:
    python3 run_migrations.py
"""

import asyncio
import sqlite3
import logging
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

DB_PATH = Path("/home/rahulvadera/cbp-sentry/data/cbp_sentry.db")


def run_migration_v4_1():
    """Run v4.1 migration (performance metrics) as raw SQL"""
    print("\n" + "=" * 70)
    print("🚀 Running Migration v4.1 - Performance Metrics Schema")
    print("=" * 70)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # ========================================================================
        # TABLE 1: performance_metrics_config
        # ========================================================================
        print("\n📝 Creating performance_metrics_config table...")
        cursor.execute("""
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
        """)
        print("✅ performance_metrics_config table created")

        # Create indexes
        print("📝 Creating indexes on performance_metrics_config...")
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_metrics_config_domain ON performance_metrics_config(domain)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_metrics_config_model ON performance_metrics_config(model_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_metrics_config_period ON performance_metrics_config(contract_period_start, contract_period_end)"
        )
        print("✅ Indexes created on performance_metrics_config")

        # ========================================================================
        # TABLE 2: performance_metric_definitions
        # ========================================================================
        print("\n📝 Creating performance_metric_definitions table...")
        cursor.execute("""
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
        """)
        print("✅ performance_metric_definitions table created")

        # Create indexes
        print("📝 Creating indexes on performance_metric_definitions...")
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_metric_defs_type ON performance_metric_definitions(metric_type)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_metric_defs_name ON performance_metric_definitions(metric_name)"
        )
        print("✅ Indexes created on performance_metric_definitions")

        # ========================================================================
        # TABLE 3: performance_gate_results
        # ========================================================================
        print("\n📝 Creating performance_gate_results table...")
        cursor.execute("""
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
        """)
        print("✅ performance_gate_results table created")

        # Create indexes
        print("📝 Creating indexes on performance_gate_results...")
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_gate_results_domain_model ON performance_gate_results(domain, model_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_gate_results_gate ON performance_gate_results(gate_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_gate_results_metric ON performance_gate_results(metric_name)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_gate_results_status ON performance_gate_results(status)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_gate_results_period ON performance_gate_results(period_start_date, period_end_date)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_gate_results_calculated ON performance_gate_results(calculated_at)"
        )
        print("✅ Indexes created on performance_gate_results")

        # ========================================================================
        # Seed initial metric definitions
        # ========================================================================
        print("\n📝 Seeding metric definitions...")

        metrics = [
            ('metric-scalability-001', 'count_per_period', 'scalability', 'count_per_period',
             'reference_packages', 'week', 'packages', 'Number of approved reference packages processed per week'),
            ('metric-accuracy-001', 'threshold', 'accuracy', 'threshold',
             'risk_scores', 'static', 'percentage', 'Model accuracy based on test dataset evaluation'),
            ('metric-latency-001', 'threshold', 'latency', 'threshold',
             'prediction_logs', 'week', 'milliseconds', 'Mean prediction latency (p95) per week'),
            ('metric-auc-001', 'threshold', 'auc', 'threshold',
             'model_evaluation', 'static', 'score', 'Area Under the Curve (AUC) from model evaluation'),
            ('metric-error_rate-001', 'ratio', 'error_rate', 'ratio',
             'prediction_logs', 'day', 'percentage', 'Ratio of failed predictions to total predictions'),
        ]

        for id, mtype, name, plugin, source, period, unit, doc in metrics:
            cursor.execute("""
                INSERT OR IGNORE INTO performance_metric_definitions
                (id, metric_type, metric_name, calculation_plugin, data_source,
                 aggregation_period, unit, documentation)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (id, mtype, name, plugin, source, period, unit, doc))

        print("✅ Metric definitions seeded")

        conn.commit()
        print("\n" + "=" * 70)
        print("✅ Migration v4.1 completed successfully!")
        print("=" * 70)

        # Verify tables were created
        cursor.execute("""
            SELECT name FROM sqlite_master WHERE type='table'
            AND name IN (
                'performance_metrics_config',
                'performance_metric_definitions',
                'performance_gate_results'
            )
        """)
        tables = cursor.fetchall()
        print(f"\n✅ Created {len(tables)} new tables:")
        for table in tables:
            print(f"   - {table[0]}")

    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        conn.rollback()
        raise

    finally:
        conn.close()


if __name__ == "__main__":
    run_migration_v4_1()
    print("\n✅ All migrations completed!")
