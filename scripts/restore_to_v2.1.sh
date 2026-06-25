#!/bin/bash
# Restore CBP Sentry database to v2.1 baseline
# Usage: ./restore_to_v2.1.sh

set -e

DB_PATH="/home/rahulvadera/cbp-sentry/data/cbp_sentry.db"
V2_1_BACKUP="$1"

if [ -z "$V2_1_BACKUP" ]; then
    echo "❌ Usage: ./restore_to_v2.1.sh <backup_file>"
    echo "   Example: ./restore_to_v2.1.sh backups/cbp_sentry_v2.1_baseline_20260613_140000.db"
    exit 1
fi

if [ ! -f "$V2_1_BACKUP" ]; then
    echo "❌ Backup file not found: $V2_1_BACKUP"
    exit 1
fi

echo "⚠️  WARNING: This will restore the database to v2.1 state"
echo "   Current database: $DB_PATH"
echo "   Backup source: $V2_1_BACKUP"
read -p "Continue? (yes/no) " -n 3 -r
echo
if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    echo "❌ Restore cancelled"
    exit 1
fi

# Create backup of current state before restoring
CURRENT_BACKUP="$DB_PATH.backup_$(date +%Y%m%d_%H%M%S)"
cp "$DB_PATH" "$CURRENT_BACKUP"
echo "✅ Saved current state to: $CURRENT_BACKUP"

# Restore v2.1
cp "$V2_1_BACKUP" "$DB_PATH"
echo "✅ Restored database to v2.1 from: $V2_1_BACKUP"

echo ""
echo "🔄 Restarting services..."
cd /home/rahulvadera/cbp-sentry
docker compose restart sentry-api sentry-data
echo "✅ Services restarted"
echo ""
echo "✅ RESTORE COMPLETE - Database is now v2.1"
