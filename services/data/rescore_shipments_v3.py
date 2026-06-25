#!/usr/bin/env python3
"""
Rescore All Shipments with v3.0 Model

This script:
1. Fetches all shipments from database
2. Calls precise-risk-engine for each shipment
3. Updates database with v3.0 scores
4. Preserves legacy (v2.1) scores for comparison
5. Creates audit trail in score_history table

Usage:
    python rescore_shipments_v3.py [--dry-run] [--limit 10]

Options:
    --dry-run       Show what would be changed without modifying database
    --limit N       Only rescore first N shipments
"""

import asyncio
import json
import logging
import sys
from datetime import datetime
from typing import Optional
from argparse import ArgumentParser
import httpx

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base
from sqlalchemy import select, update, insert, Column, String, Float, DateTime, JSON, Integer
from uuid import uuid4

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Database setup
DATABASE_URL = "sqlite+aiosqlite:///./data/cbp_sentry.db"
engine = create_async_engine(DATABASE_URL, echo=False)
Base = declarative_base()

# Import models
# Note: In production, import from services/data/database.py
# For now, we define minimal models for this migration


class Shipment:
    """Minimal shipment model for migration"""
    id: str
    shipper_name: str
    origin_country: str
    destination_country: str
    declared_value_usd: float
    dwell_days: Optional[float]
    hs_code: str
    h1_h2_score: Optional[float]
    model_version: Optional[str]
    element9_is_mismatch: Optional[bool]

    def to_dict(self):
        """Convert to dict for API call"""
        return {
            'shipment_id': self.id,
            'shipper_name': self.shipper_name,
            'origin_country': self.origin_country,
            'destination_country': self.destination_country,
            'declared_value_usd': self.declared_value_usd,
            'dwell_days': self.dwell_days or 0,
            'hs_code': self.hs_code,
            'element9_is_mismatch': self.element9_is_mismatch or False
        }


class ScoreHistory:
    """Score history for audit trail"""
    id: str
    shipment_id: str
    model_version: str
    legacy_score: Optional[float]
    precise_score: Optional[float]
    precise_confidence: Optional[float]
    scored_at: datetime


async def fetch_all_shipments(session: AsyncSession, limit: Optional[int] = None) -> list:
    """Fetch all shipments from database"""
    logger.info(f"📦 Fetching shipments{f' (limit: {limit})' if limit else ''}...")

    query = select(Shipment)
    if limit:
        query = query.limit(limit)

    result = await session.execute(query)
    shipments = result.scalars().all()
    logger.info(f"✅ Fetched {len(shipments)} shipments")
    return shipments


async def call_precise_risk_engine(shipment_data: dict, timeout: int = 10) -> dict:
    """Call precise-risk-engine API"""
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                "http://precise-risk-engine:8004/score",
                json=shipment_data
            )
            response.raise_for_status()
            return response.json()
    except httpx.TimeoutException:
        logger.warning(f"⏱️  Timeout scoring {shipment_data.get('shipment_id')}")
        raise
    except httpx.HTTPError as e:
        logger.warning(f"⚠️  API error scoring {shipment_data.get('shipment_id')}: {e}")
        raise


async def rescore_shipment(
    session: AsyncSession,
    shipment: Shipment,
    dry_run: bool = False
) -> dict:
    """Rescore a single shipment with v3.0 model"""

    try:
        # Call precise-risk-engine
        v3_result = await call_precise_risk_engine(shipment.to_dict())

        # Extract scores
        v3_score = v3_result.get('risk_score', 0)
        v3_confidence = v3_result.get('confidence', 0.0)
        v3_factors = v3_result.get('factors', {})
        v2_legacy_score = shipment.h1_h2_score

        if not dry_run:
            # Update shipment with v3.0 scores
            await session.execute(
                update(Shipment)
                .where(Shipment.id == shipment.id)
                .values(
                    model_version='v3.0',
                    precise_score=v3_score,
                    model_confidence=v3_confidence,
                    model_factors=json.dumps(v3_factors)
                )
            )

            # Create score_history entry
            await session.execute(
                insert(ScoreHistory).values(
                    id=str(uuid4()),
                    shipment_id=shipment.id,
                    model_version='v3.0',
                    legacy_score=v2_legacy_score,
                    precise_score=v3_score,
                    precise_confidence=v3_confidence,
                    scored_at=datetime.now()
                )
            )

        return {
            'shipment_id': shipment.id,
            'v2_legacy_score': v2_legacy_score,
            'v3_precise_score': v3_score,
            'v3_confidence': v3_confidence,
            'score_change': v3_score - (v2_legacy_score or 0),
            'percent_change': ((v3_score - (v2_legacy_score or 0)) / (v2_legacy_score or 1) * 100) if v2_legacy_score else 0
        }

    except Exception as e:
        logger.error(f"❌ Failed to rescore {shipment.id}: {e}")
        return {
            'shipment_id': shipment.id,
            'error': str(e)
        }


async def rescore_all_shipments(
    dry_run: bool = False,
    limit: Optional[int] = None
) -> None:
    """Main rescoring function"""

    async with AsyncSession(engine) as session:
        # Fetch all shipments
        shipments = await fetch_all_shipments(session, limit=limit)

        if not shipments:
            logger.warning("⚠️  No shipments found to rescore")
            return

        logger.info(f"🔄 Rescoring {len(shipments)} shipments with v3.0 model...")
        if dry_run:
            logger.info("   (DRY RUN - no changes will be saved)")

        # Track results
        results = {
            'total': len(shipments),
            'success': 0,
            'failed': 0,
            'scores': []
        }

        # Rescore each shipment
        for i, shipment in enumerate(shipments, 1):
            logger.info(f"   [{i}/{len(shipments)}] {shipment.id}...", end=' ')

            result = await rescore_shipment(session, shipment, dry_run=dry_run)

            if 'error' in result:
                logger.info(f"❌ {result['error']}")
                results['failed'] += 1
            else:
                logger.info(f"✅ {result['v3_precise_score']:.1f} (was {result['v2_legacy_score']:.1f}, {result['percent_change']:+.1f}%)")
                results['success'] += 1
                results['scores'].append(result)

        # Commit all changes
        if not dry_run:
            try:
                await session.commit()
                logger.info(f"\n✅ Successfully rescored {results['success']} shipments")
            except Exception as e:
                await session.rollback()
                logger.error(f"❌ Database commit failed: {e}")
                return
        else:
            logger.info(f"\n✅ DRY RUN: Would have rescored {results['success']} shipments")

        # Print summary statistics
        if results['scores']:
            scores = [r['v3_precise_score'] for r in results['scores']]
            changes = [r['score_change'] for r in results['scores']]
            percent_changes = [r['percent_change'] for r in results['scores']]

            logger.info("\n📊 Score Summary:")
            logger.info(f"   Success: {results['success']}/{results['total']}")
            logger.info(f"   Failed: {results['failed']}/{results['total']}")
            logger.info(f"\n   v3.0 Scores:")
            logger.info(f"   - Min: {min(scores):.1f}")
            logger.info(f"   - Max: {max(scores):.1f}")
            logger.info(f"   - Mean: {sum(scores)/len(scores):.1f}")
            logger.info(f"\n   Score Changes:")
            logger.info(f"   - Min: {min(changes):+.1f}")
            logger.info(f"   - Max: {max(changes):+.1f}")
            logger.info(f"   - Mean: {sum(changes)/len(changes):+.1f}")
            logger.info(f"   - Avg % Change: {sum(percent_changes)/len(percent_changes):+.1f}%")


async def main():
    """Entry point"""
    parser = ArgumentParser(description='Rescore all shipments with v3.0 model')
    parser.add_argument('--dry-run', action='store_true', help='Show changes without saving')
    parser.add_argument('--limit', type=int, help='Only rescore first N shipments')
    args = parser.parse_args()

    logger.info("=" * 70)
    logger.info("CBP Sentry v3.0 Rescoring Migration")
    logger.info("=" * 70)

    try:
        await rescore_all_shipments(dry_run=args.dry_run, limit=args.limit)
    except KeyboardInterrupt:
        logger.info("\n⚠️  Rescoring interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n❌ Rescoring failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    asyncio.run(main())
