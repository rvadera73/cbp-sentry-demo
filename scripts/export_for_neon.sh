#!/bin/bash

#######################################################################
# Export Local SQLite Database to Neon PostgreSQL Format
# Creates SQL insert statements that can be imported into staging
#######################################################################

set -e

PROJECT_ROOT="$(dirname "$(dirname "$(readlink -f "$0")")")"
BACKUP_DIR="$PROJECT_ROOT/backups"
EXPORT_FILE="$BACKUP_DIR/cbp_sentry_neon_seed_$(date +%Y%m%d_%H%M%S).sql"

# Colors
BLUE='\033[0;34m'
GREEN='\033[0;32m'
NC='\033[0m'

log_info() { echo -e "${BLUE}→${NC} $1"; }
log_success() { echo -e "${GREEN}✓${NC} $1"; }

log_info "Exporting local database to Neon PostgreSQL format"

mkdir -p "$BACKUP_DIR"

# Get shipment data from local container
log_info "Extracting shipment records from local SQLite..."

# Use docker compose to execute sqlite3 query and convert to SQL
# Suppress docker warnings by redirecting stderr and filtering output
docker compose exec -T sentry-data python3 << 'PYSCRIPT' 2>/dev/null | grep -v "^time=" | grep -v "warning msg" > /tmp/shipments_export.json
import sqlite3
import json

# Connect to local SQLite
conn = sqlite3.connect('/app/data/cbp_sentry.db')
cursor = conn.cursor()

# Query all shipments
cursor.execute('SELECT * FROM shipments ORDER BY id')
rows = cursor.fetchall()

# Get column names
cursor.execute('PRAGMA table_info(shipments)')
columns = [col[1] for col in cursor.fetchall()]

# Write as JSON (easier to parse and convert)
shipments = []
for row in rows:
    shipment = {}
    for i, col in enumerate(columns):
        shipment[col] = row[i]
    shipments.append(shipment)

print(json.dumps(shipments, indent=2, default=str))
PYSCRIPT

log_success "Extracted $(grep -c '\"id\"' /tmp/shipments_export.json || echo 0) shipments"

# Generate PostgreSQL INSERT statements
log_info "Converting to PostgreSQL INSERT statements..."

cat > "$EXPORT_FILE" << 'EOF'
-- CBP Sentry Database Seed Data for Neon PostgreSQL
-- Generated from local SQLite export
-- Table: public.shipments

BEGIN TRANSACTION;

-- Clear existing data (optional - comment out if you want to preserve existing records)
-- TRUNCATE TABLE shipments CASCADE;

-- Insert shipment records
EOF

# Parse JSON and generate SQL INSERTs
python3 << 'PYSCRIPT' >> "$EXPORT_FILE"
import json
import sys

try:
    with open('/tmp/shipments_export.json', 'r') as f:
        shipments = json.load(f)

    if not isinstance(shipments, list):
        print("Warning: Expected list of shipments", file=sys.stderr)
        sys.exit(1)

    for shipment in shipments:
        columns = []
        values = []

        for key, value in shipment.items():
            columns.append(key)
            if value is None:
                values.append("NULL")
            elif isinstance(value, str):
                # Escape single quotes
                escaped = value.replace("'", "''")
                values.append(f"'{escaped}'")
            elif isinstance(value, bool):
                values.append("TRUE" if value else "FALSE")
            else:
                values.append(str(value))

        col_str = ", ".join(columns)
        val_str = ", ".join(values)

        print(f"INSERT INTO shipments ({col_str}) VALUES ({val_str});")

except json.JSONDecodeError as e:
    print(f"Error parsing JSON: {e}", file=sys.stderr)
    sys.exit(1)
except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
    sys.exit(1)
PYSCRIPT

# Add completion statement
cat >> "$EXPORT_FILE" << 'EOF'

COMMIT;

-- Verify import
SELECT COUNT(*) as total_shipments FROM shipments;
SELECT
    COUNT(CASE WHEN risk_score >= 70 THEN 1 END) as high_risk,
    COUNT(CASE WHEN risk_score >= 50 AND risk_score < 70 THEN 1 END) as medium_risk,
    COUNT(CASE WHEN risk_score < 50 THEN 1 END) as low_risk
FROM shipments;

-- Show sample records
SELECT id, shipper_name, origin_country, destination_country, risk_score
FROM shipments
ORDER BY risk_score DESC
LIMIT 5;
EOF

log_success "SQL export created: $EXPORT_FILE"

# Show statistics
RECORD_COUNT=$(grep -c "INSERT INTO shipments" "$EXPORT_FILE" || echo "0")
FILE_SIZE=$(du -h "$EXPORT_FILE" | cut -f1)

echo ""
echo "Export Summary:"
echo "  Records: $RECORD_COUNT"
echo "  File: $EXPORT_FILE"
echo "  Size: $FILE_SIZE"
echo ""
echo "To import into Neon staging:"
echo "  1. Connect to Neon: psql \$DATABASE_URL < $EXPORT_FILE"
echo "  2. Or copy/paste SQL statements into Neon console"
echo "  3. Verify: SELECT COUNT(*) FROM shipments;"
echo ""
