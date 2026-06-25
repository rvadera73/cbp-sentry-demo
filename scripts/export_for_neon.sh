#!/bin/bash

#######################################################################
# Export Local PostgreSQL Schemas to Neon Dev/Stage
#
# Dumps cbp_sentry (and optionally mlops, cord) schemas from the
# local sentry-db container and imports them into the target Neon DB.
#
# Usage:
#   ./scripts/export_for_neon.sh [--target-url <NEON_URL>] [--schema cbp_sentry|mlops|cord|all]
#   ./scripts/export_for_neon.sh --schema all   # dump all schemas to backups/
#
# Environment variables (alternative to flags):
#   NEON_DATABASE_URL      - Neon connection string for cbp_sentry schema
#   NEON_MLOPS_DATABASE_URL  - Neon connection string for mlops schema
#   NEON_CORD_DATABASE_URL   - Neon connection string for cord schema
#######################################################################

set -e

PROJECT_ROOT="$(dirname "$(dirname "$(readlink -f "$0")")")"
BACKUP_DIR="$PROJECT_ROOT/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Colors
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info()    { echo -e "${BLUE}→${NC} $1"; }
log_success() { echo -e "${GREEN}✓${NC} $1"; }
log_warn()    { echo -e "${YELLOW}⚠${NC} $1"; }
log_error()   { echo -e "${RED}✗${NC} $1"; exit 1; }

# Parse arguments
TARGET_URL=""
SCHEMA="cbp_sentry"

while [[ $# -gt 0 ]]; do
  case $1 in
    --target-url) TARGET_URL="$2"; shift 2 ;;
    --schema)     SCHEMA="$2"; shift 2 ;;
    *) log_error "Unknown argument: $1. Usage: $0 [--target-url URL] [--schema cbp_sentry|mlops|cord|all]" ;;
  esac
done

mkdir -p "$BACKUP_DIR"

# Verify sentry-db is running
if ! docker compose -f "$PROJECT_ROOT/docker-compose.yml" exec -T sentry-db pg_isready -U sentry -d sentry > /dev/null 2>&1; then
  log_error "sentry-db is not running. Start it with: ./scripts/deploy-local.sh quick"
fi

# Dump a single schema from local PostgreSQL
dump_schema() {
  local schema=$1
  local dump_file="$BACKUP_DIR/${schema}_${TIMESTAMP}.sql"

  log_info "Dumping schema '$schema' from local sentry-db..."

  # pg_dump inside the sentry-db container — no pg_dump install needed on host
  docker compose -f "$PROJECT_ROOT/docker-compose.yml" exec -T sentry-db \
    pg_dump -U sentry -d sentry \
    --schema="$schema" \
    --no-owner --no-privileges \
    --clean --if-exists \
    > "$dump_file"

  local count
  count=$(grep -c "^INSERT INTO\|^COPY " "$dump_file" 2>/dev/null || echo 0)
  log_success "Dumped schema '$schema' → $dump_file ($count data statements)"
  echo "$dump_file"
}

# Import a dump file into target Neon DB
import_to_neon() {
  local dump_file=$1
  local target_url=$2
  local schema=$3

  if [ -z "$target_url" ]; then
    log_warn "No target URL for schema '$schema' — skipping import (dump saved to $dump_file)"
    return 0
  fi

  log_info "Importing '$schema' into Neon ($target_url)..."
  psql "$target_url" < "$dump_file"
  log_success "Imported '$schema' into Neon successfully"
}

# Process schemas
process_schema() {
  local schema=$1
  local target_url=$2

  local dump_file
  dump_file=$(dump_schema "$schema")
  import_to_neon "$dump_file" "$target_url" "$schema"
}

echo ""
log_info "CBP Sentry → Neon Export"
echo ""

if [ "$SCHEMA" = "all" ]; then
  process_schema "cbp_sentry" "${TARGET_URL:-${NEON_DATABASE_URL:-}}"
  process_schema "mlops"      "${NEON_MLOPS_DATABASE_URL:-}"
  process_schema "cord"       "${NEON_CORD_DATABASE_URL:-}"
else
  process_schema "$SCHEMA" "${TARGET_URL:-${NEON_DATABASE_URL:-}}"
fi

echo ""
log_success "Export complete. Dumps saved to: $BACKUP_DIR/"
echo ""
echo "To manually import a dump into Neon:"
echo "  psql \$NEON_DATABASE_URL < $BACKUP_DIR/<file>.sql"
echo ""
echo "To run all schemas at once with env vars:"
echo "  NEON_DATABASE_URL=<url> NEON_MLOPS_DATABASE_URL=<url> NEON_CORD_DATABASE_URL=<url> \\"
echo "    ./scripts/export_for_neon.sh --schema all"

