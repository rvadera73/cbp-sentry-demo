#!/bin/bash
#######################################################################
# Setup Neon Dev Databases — CBP Sentry
#
# Creates schemas in three separate Neon databases (one per service):
#   cbp_sentry schema  →  NEON_DATABASE_URL
#   mlops schema       →  NEON_MLOPS_DATABASE_URL
#   cord schema        →  NEON_CORD_DATABASE_URL
#
# Each Neon DB is an independent Neon project/branch so services are
# fully isolated and can be scaled or branched independently.
#
# Usage:
#   # Set env vars first (or copy from .env.neon):
#   export NEON_DATABASE_URL="postgresql://user:pass@ep-xxx.us-east-2.aws.neon.tech/cbp_sentry?sslmode=require"
#   export NEON_MLOPS_DATABASE_URL="postgresql://user:pass@ep-yyy.us-east-2.aws.neon.tech/mlops?sslmode=require"
#   export NEON_CORD_DATABASE_URL="postgresql://user:pass@ep-zzz.us-east-2.aws.neon.tech/cord?sslmode=require"
#   bash scripts/setup_neon_dev.sh
#
# To also seed with local data after schema creation:
#   bash scripts/setup_neon_dev.sh --seed
#######################################################################

set -e

PROJECT_ROOT="$(dirname "$(dirname "$(readlink -f "$0")")")"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info()    { echo -e "${BLUE}→${NC} $1"; }
log_success() { echo -e "${GREEN}✓${NC} $1"; }
log_warn()    { echo -e "${YELLOW}⚠${NC} $1"; }
log_error()   { echo -e "${RED}✗${NC} $1"; exit 1; }

SEED=false
while [[ $# -gt 0 ]]; do
  case $1 in
    --seed) SEED=true; shift ;;
    *) log_error "Unknown argument: $1" ;;
  esac
done

echo ""
echo "🐘 CBP Sentry — Neon Dev Database Setup"
echo "========================================"
echo ""

# ── Validate URLs ──────────────────────────────────────────────────────────────
if [ -z "$NEON_DATABASE_URL" ]; then
  log_error "NEON_DATABASE_URL is not set. Export it or create .env.neon — see header comments."
fi

log_success "NEON_DATABASE_URL set (cbp_sentry DB)"
[ -n "$NEON_MLOPS_DATABASE_URL" ]  && log_success "NEON_MLOPS_DATABASE_URL set (mlops DB)"  || log_warn "NEON_MLOPS_DATABASE_URL not set — mlops schema will be skipped"
[ -n "$NEON_CORD_DATABASE_URL" ]   && log_success "NEON_CORD_DATABASE_URL set (cord DB)"    || log_warn "NEON_CORD_DATABASE_URL not set — cord schema will be skipped"
echo ""

# ── Helper: run DDL against a Neon URL ────────────────────────────────────────
run_ddl() {
  local url=$1
  local label=$2
  local ddl=$3

  log_info "Creating schema objects in '$label'..."
  echo "$ddl" | psql "$url" --no-psqlrc -q
  log_success "'$label' schema ready"
}

# ── 1. cbp_sentry schema (sentry-data service) ────────────────────────────────
log_info "Setting up cbp_sentry schema..."

CBPSENTRY_DDL=$(cat "$PROJECT_ROOT/services/data/init.sql" 2>/dev/null || echo "")
if [ -z "$CBPSENTRY_DDL" ]; then
  log_error "services/data/init.sql not found. Run from project root."
fi

# Neon uses 'public' schema by default unless we specify otherwise.
# Our init.sql creates the cbp_sentry schema — run it directly.
echo "$CBPSENTRY_DDL" | psql "$NEON_DATABASE_URL" --no-psqlrc -q
log_success "cbp_sentry schema created in Neon"

# ── 2. mlops schema (cbp-risk-engine service) ─────────────────────────────────
if [ -n "$NEON_MLOPS_DATABASE_URL" ]; then
  MLOPS_INIT="$PROJECT_ROOT/services/risk-engine/init_mlops.sql"
  if [ -f "$MLOPS_INIT" ]; then
    log_info "Setting up mlops schema..."
    psql "$NEON_MLOPS_DATABASE_URL" --no-psqlrc -q -f "$MLOPS_INIT"
    log_success "mlops schema created in Neon"
  else
    log_warn "services/risk-engine/init_mlops.sql not found — mlops schema skipped (will be created when pg-mlops-schema migration runs)"
  fi
fi

# ── 3. cord schema (sentry-cord-integration service) ──────────────────────────
if [ -n "$NEON_CORD_DATABASE_URL" ]; then
  CORD_INIT="$PROJECT_ROOT/services/cord-integration/init_cord.sql"
  if [ -f "$CORD_INIT" ]; then
    log_info "Setting up cord schema..."
    psql "$NEON_CORD_DATABASE_URL" --no-psqlrc -q -f "$CORD_INIT"
    log_success "cord schema created in Neon"
  else
    log_warn "services/cord-integration/init_cord.sql not found — cord schema skipped"
  fi
fi

# ── 4. Optional seed from local ───────────────────────────────────────────────
if [ "$SEED" = true ]; then
  echo ""
  log_info "Seeding Neon DBs from local PostgreSQL..."
  NEON_DATABASE_URL="$NEON_DATABASE_URL" \
  NEON_MLOPS_DATABASE_URL="${NEON_MLOPS_DATABASE_URL:-}" \
  NEON_CORD_DATABASE_URL="${NEON_CORD_DATABASE_URL:-}" \
    bash "$PROJECT_ROOT/scripts/export_for_neon.sh" --schema all
fi

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
echo "════════════════════════════════════════════"
log_success "Neon dev databases ready!"
echo ""
echo "Add these to your .env.local (or GitHub Actions secrets for stage):"
echo ""
echo "  # sentry-data service"
echo "  DATABASE_URL=$NEON_DATABASE_URL"
echo ""
if [ -n "$NEON_MLOPS_DATABASE_URL" ]; then
  echo "  # cbp-risk-engine service"
  echo "  MLOPS_DATABASE_URL=$NEON_MLOPS_DATABASE_URL"
  echo ""
fi
if [ -n "$NEON_CORD_DATABASE_URL" ]; then
  echo "  # sentry-cord-integration service"
  echo "  CORD_DATABASE_URL=$NEON_CORD_DATABASE_URL"
  echo ""
fi
echo "To seed from local data at any time:"
echo "  bash scripts/export_for_neon.sh --schema all"
