"""
Migration: Add Model Versioning Support (v2.1 → v3.0)
Date: 2026-06-12

This migration adds:
1. model_version column to shipments (v2.1 default)
2. precise_score, model_confidence, model_factors columns
3. model_metadata table (tracks model versions)
4. score_history table (audit trail of all scores)
"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


async def upgrade(session: AsyncSession):
    """Apply migration: add model versioning tables and columns"""

    try:
        # 1. Add columns to shipments table
        print("📝 Adding model versioning columns to shipments...")
        await session.execute(text("""
            ALTER TABLE shipments ADD COLUMN IF NOT EXISTS model_version VARCHAR(50);
            ALTER TABLE shipments ADD COLUMN IF NOT EXISTS precise_score FLOAT;
            ALTER TABLE shipments ADD COLUMN IF NOT EXISTS model_confidence FLOAT;
            ALTER TABLE shipments ADD COLUMN IF NOT EXISTS model_factors JSON;
        """))
        print("✅ Columns added to shipments")

        # 2. Create model_metadata table
        print("📝 Creating model_metadata table...")
        await session.execute(text("""
            CREATE TABLE IF NOT EXISTS model_metadata (
                id TEXT PRIMARY KEY,
                version TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                features_count INTEGER,
                gates_count INTEGER,
                rules_count INTEGER,
                weight_sum FLOAT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                description TEXT
            )
        """))
        print("✅ model_metadata table created")

        # 3. Create score_history table
        print("📝 Creating score_history table...")
        await session.execute(text("""
            CREATE TABLE IF NOT EXISTS score_history (
                id TEXT PRIMARY KEY,
                shipment_id TEXT NOT NULL,
                model_version TEXT NOT NULL,
                legacy_score FLOAT,
                legacy_factors JSON,
                precise_score FLOAT,
                precise_factors JSON,
                precise_confidence FLOAT,
                scored_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (shipment_id) REFERENCES shipments(id)
            )
        """))
        print("✅ score_history table created")

        # 4. Insert model metadata
        print("📝 Inserting model metadata...")
        await session.execute(text("""
            INSERT OR IGNORE INTO model_metadata
            (id, version, name, type, features_count, gates_count, rules_count, weight_sum, description)
            VALUES
            (
                'model-v2.1',
                'v2.1',
                'Legacy Rule-Based Model',
                'legacy',
                72,
                3,
                8,
                1.10,
                'Original 7-factor rule-based model with H1/H2/H3 horizons. Over-weighted (110% total).'
            ),
            (
                'model-v3.0',
                'v3.0',
                'Precise Risk Model (XGBoost)',
                'precise',
                72,
                3,
                8,
                1.00,
                'New ML-based model using XGBoost classifier with proper 100% weight normalization. 3-gate architecture: deterministic rules → ML → uncertainty quantification.'
            )
        """))
        print("✅ Model metadata inserted")

        # 5. Set default model_version to v2.1 for existing shipments
        print("📝 Setting default model version for existing shipments...")
        await session.execute(text("""
            UPDATE shipments
            SET model_version = 'v2.1'
            WHERE model_version IS NULL
        """))
        print("✅ Default model version set")

        await session.commit()
        print("\n✅ Migration completed successfully!")
        print("   - Shipments now track model_version")
        print("   - model_metadata table created")
        print("   - score_history table created for audit trail")

    except Exception as e:
        await session.rollback()
        logger.error(f"❌ Migration failed: {e}")
        raise


async def downgrade(session: AsyncSession):
    """Rollback migration: remove model versioning"""

    try:
        print("🔄 Rolling back model versioning migration...")

        # Drop tables
        await session.execute(text("DROP TABLE IF EXISTS score_history"))
        await session.execute(text("DROP TABLE IF EXISTS model_metadata"))

        # Remove columns
        await session.execute(text("""
            ALTER TABLE shipments DROP COLUMN IF EXISTS model_version;
            ALTER TABLE shipments DROP COLUMN IF EXISTS precise_score;
            ALTER TABLE shipments DROP COLUMN IF EXISTS model_confidence;
            ALTER TABLE shipments DROP COLUMN IF EXISTS model_factors;
        """))

        await session.commit()
        print("✅ Rollback completed")

    except Exception as e:
        await session.rollback()
        logger.error(f"❌ Rollback failed: {e}")
        raise


# Usage:
# python -c "
# import asyncio
# from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
# from migrations.v3_0_add_model_versioning import upgrade
#
# async def run():
#     engine = create_async_engine('sqlite+aiosqlite:///./data/cbp_sentry.db')
#     async with AsyncSession(engine) as session:
#         await upgrade(session)
#
# asyncio.run(run())
# "
