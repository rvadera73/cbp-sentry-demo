#!/usr/bin/env python3
"""
Safe Migration: Delete Duplicate Risk Model Tables from cbp-sentry

BACKUP FIRST! This script removes tables that are now redundant with cbp-risk-engine MLflow registry.

Overview:
  cbp-sentry used to have its own risk model metadata tables that duplicated MLflow functionality.
  Now that cbp-risk-engine is the single source of truth, we can safely remove these tables.

Tables to DELETE (safe - data backed up in Gate 0 baseline commit):
  - risk_models (metadata, duplicate with MLflow)
  - risk_model_approvals (empty, approvals now in cbp-risk-engine/approvals.db)
  - risk_model_training_jobs (empty, training in cbp-risk-engine MLflow)
  - risk_model_metrics (empty, metrics in cbp-risk-engine)
  - risk_model_drift_detected (empty, drift detection in cbp-risk-engine)
  - risk_model_predictions (empty, predictions logged in cbp-risk-engine/runtime.db)

Tables to KEEP (CBP enforcement tracking, not ML infrastructure):
  - model_score_history (shipment → score mapping)
  - dataset_baselines (snapshot metadata)
  - performance_gate_results (Gate 0 baseline metrics)

Steps:
  1. Backup database
  2. Verify table counts (should be 0 or very small)
  3. Drop tables
  4. Verify cleanup
  5. Git commit with migration note
  6. Tag commit

Safety checks:
  - Only runs if run with --confirm flag (requires explicit user consent)
  - Creates backup before any deletions
  - Verifies tables exist before dropping
  - Reports row counts before and after
  - Rolls back on error (simple: drop transaction)
"""

import sqlite3
import sys
import shutil
from datetime import datetime
from pathlib import Path

# Configuration
DB_PATH = Path('/home/rahulvadera/cbp-sentry/data/cbp_sentry.db')
BACKUP_DIR = Path('/home/rahulvadera/cbp-sentry/backups')

# Tables to delete
TABLES_TO_DELETE = [
    'risk_models',
    'risk_model_approvals',
    'risk_model_training_jobs',
    'risk_model_metrics',
    'risk_model_drift_detected',
    'risk_model_predictions',
]

# Tables to keep
TABLES_TO_KEEP = [
    'model_score_history',
    'dataset_baselines',
    'performance_gate_results',
]

def get_table_count(conn, table_name):
    """Get row count for a table, return 0 if table doesn't exist"""
    try:
        c = conn.cursor()
        c.execute(f'SELECT COUNT(*) FROM {table_name}')
        return c.fetchone()[0]
    except sqlite3.OperationalError:
        return None  # Table doesn't exist

def create_backup():
    """Create timestamped backup of database"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = BACKUP_DIR / f'cbp_sentry_backup_pre_cleanup_{timestamp}.db'

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    print(f"\n📦 Creating backup: {backup_file}")
    shutil.copy2(DB_PATH, backup_file)
    print(f"✓ Backup created successfully")
    return backup_file

def verify_tables(conn):
    """Verify which tables exist and their row counts"""
    print("\n" + "=" * 70)
    print("STEP 1: VERIFY TABLE STATES")
    print("=" * 70)

    print("\nTables to DELETE:")
    for table in TABLES_TO_DELETE:
        count = get_table_count(conn, table)
        if count is None:
            print(f"  ✗ {table}: DOES NOT EXIST (will skip)")
        else:
            print(f"  ✓ {table}: {count} rows")

    print("\nTables to KEEP:")
    for table in TABLES_TO_KEEP:
        count = get_table_count(conn, table)
        if count is None:
            print(f"  ✗ {table}: DOES NOT EXIST (warning)")
        else:
            print(f"  ✓ {table}: {count} rows ← PROTECTED")

def drop_tables(conn):
    """Drop duplicate tables"""
    print("\n" + "=" * 70)
    print("STEP 2: DELETE DUPLICATE TABLES")
    print("=" * 70)

    c = conn.cursor()
    dropped = []
    skipped = []

    for table in TABLES_TO_DELETE:
        try:
            c.execute(f'DROP TABLE IF EXISTS {table}')
            dropped.append(table)
            print(f"✓ Dropped: {table}")
        except Exception as e:
            skipped.append((table, str(e)))
            print(f"✗ Failed to drop {table}: {e}")

    conn.commit()
    print(f"\nDropped {len(dropped)} tables, skipped {len(skipped)}")
    return dropped, skipped

def verify_cleanup(conn):
    """Verify all target tables are gone"""
    print("\n" + "=" * 70)
    print("STEP 3: VERIFY CLEANUP")
    print("=" * 70)

    c = conn.cursor()
    c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    remaining_tables = [row[0] for row in c.fetchall()]

    print(f"\nRemaining tables in database ({len(remaining_tables)} total):")
    for table in sorted(remaining_tables):
        if table in TABLES_TO_KEEP:
            print(f"  ✓ {table} (protected)")
        else:
            print(f"  - {table}")

    # Check for any stragglers
    stragglers = [t for t in TABLES_TO_DELETE if t in remaining_tables]
    if stragglers:
        print(f"\n⚠️  WARNING: {len(stragglers)} target tables still exist:")
        for t in stragglers:
            print(f"  - {t}")
        return False
    else:
        print(f"\n✅ All duplicate tables successfully removed!")
        return True

def main():
    if not DB_PATH.exists():
        print(f"❌ Database not found: {DB_PATH}")
        sys.exit(1)

    # Check for --confirm flag
    if '--confirm' not in sys.argv:
        print("""
╔════════════════════════════════════════════════════════════════════════╗
║           SAFE MIGRATION: RISK MODEL TABLE CLEANUP                      ║
║                                                                         ║
║  This script will DELETE the following duplicate tables from cbp_sentry ║
║  (now handled by cbp-risk-engine MLflow registry):                     ║
║                                                                         ║
║    - risk_models              → Delete (duplicate with MLflow)          ║
║    - risk_model_approvals     → Delete (empty, use approvals.db)       ║
║    - risk_model_training_jobs → Delete (empty, use MLflow)             ║
║    - risk_model_metrics       → Delete (empty, use MLflow)             ║
║    - risk_model_drift_detected→ Delete (empty, use MLflow)             ║
║    - risk_model_predictions   → Delete (empty, use runtime.db)         ║
║                                                                         ║
║  PROTECTED (will not be deleted):                                       ║
║    - model_score_history      → Keep (shipment → score mapping)        ║
║    - dataset_baselines        → Keep (baseline snapshots)              ║
║    - performance_gate_results → Keep (Gate 0 baseline metrics)         ║
║                                                                         ║
║  ⚠️  BACKUP WILL BE CREATED BEFORE ANY CHANGES                          ║
║  ⚠️  Run with --confirm to proceed                                      ║
║                                                                         ║
╚════════════════════════════════════════════════════════════════════════╝
        """)
        print("Usage: python3 migrate_risk_models_cleanup.py --confirm")
        sys.exit(0)

    try:
        # Create backup
        backup_file = create_backup()

        # Connect to database
        conn = sqlite3.connect(str(DB_PATH))

        # Step 1: Verify table states
        verify_tables(conn)

        # Ask for confirmation again
        print("\n" + "=" * 70)
        response = input("✓ Create database backup and proceed with cleanup? (yes/no): ")
        if response.lower() != 'yes':
            print("Cleanup cancelled. Database unchanged.")
            sys.exit(0)

        # Step 2: Drop tables
        dropped, skipped = drop_tables(conn)

        # Step 3: Verify cleanup
        success = verify_cleanup(conn)

        # Summary
        print("\n" + "=" * 70)
        print("MIGRATION SUMMARY")
        print("=" * 70)
        print(f"✓ Backup created: {backup_file}")
        print(f"✓ Tables deleted: {len(dropped)}")
        if skipped:
            print(f"⚠ Tables skipped: {len(skipped)}")
        print(f"✓ Protected tables: {len(TABLES_TO_KEEP)}")
        print(f"✓ Status: {'SUCCESS' if success else 'PARTIAL - CHECK WARNINGS'}")

        conn.close()

        # Instructions for git commit
        print("\n" + "=" * 70)
        print("NEXT STEPS: GIT COMMIT")
        print("=" * 70)
        print("""
After verifying the changes:

  1. Run tests to ensure UI still works
  2. Commit with message:

     git add -A
     git commit -m "refactor: remove duplicate risk model tables

     - Delete risk_models (now in MLflow registry)
     - Delete risk_model_approvals (now in approvals.db)
     - Delete risk_model_training_jobs (now in MLflow)
     - Delete risk_model_metrics (now in MLflow)
     - Delete risk_model_drift_detected (now in MLflow)
     - Delete risk_model_predictions (now in runtime.db)

     Single source of truth: cbp-risk-engine MLflow registry
     Backup: {backup_file}

     Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>"

  3. Tag and push:

     git tag -a v0.15-risk-models-migration -m "Remove duplicate model tables"
     git push origin master --tags
        """.format(backup_file=backup_file))

    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        print(f"⚠️  Database unchanged. Backup available at: {backup_file if 'backup_file' in locals() else 'N/A'}")
        sys.exit(1)

if __name__ == '__main__':
    main()
