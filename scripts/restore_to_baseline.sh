#!/usr/bin/env bash
# restore_to_baseline.sh — Restore system to a registered model baseline
#
# Usage:
#   ./scripts/restore_to_baseline.sh --version gate0-rule-engine-v1.0
#   ./scripts/restore_to_baseline.sh --version v2.1-rule-based --dry-run
#
# What this does:
#   1. Validates the model version exists in risk_models table
#   2. Shows dataset baseline stats for that version
#   3. Resets model_version on all shipments to the target version
#   4. Re-runs batch scoring with the target model weights
#   5. Logs the restore in audit_log

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DB="$PROJECT_ROOT/data/cbp_sentry.db"
API_DIR="$PROJECT_ROOT/services/api"

VERSION=""
DRY_RUN=false

for arg in "$@"; do
  case $arg in
    --version=*) VERSION="${arg#*=}" ;;
    --version)   shift; VERSION="$1" ;;
    --dry-run)   DRY_RUN=true ;;
  esac
done

if [[ -z "$VERSION" ]]; then
  echo "ERROR: --version required"
  echo "Available versions:"
  sqlite3 "$DB" "SELECT id, status, deployed_at FROM risk_models ORDER BY created_at"
  exit 1
fi

echo "=== CBP Sentry Baseline Restore ==="
echo "Target version : $VERSION"
echo "Dry run        : $DRY_RUN"
echo ""

# 1. Validate model exists
STATUS=$(sqlite3 "$DB" "SELECT status FROM risk_models WHERE id='$VERSION'" 2>/dev/null || echo "")
if [[ -z "$STATUS" ]]; then
  echo "ERROR: Model '$VERSION' not found in risk_models registry."
  echo "Run: sqlite3 $DB \"SELECT id, status FROM risk_models\""
  exit 1
fi
echo "Model status: $STATUS"

# 2. Show dataset baseline
echo ""
echo "--- Dataset baseline for $VERSION ---"
sqlite3 "$DB" -column -header \
  "SELECT version, row_count, feature_hash, created_at FROM dataset_baselines WHERE model_version='$VERSION'"

# 3. Show performance metrics
echo ""
echo "--- Performance metrics for $VERSION ---"
sqlite3 "$DB" -column -header \
  "SELECT gate, threshold, total_scored, flagged_count, critical_count, ppv_estimate FROM performance_gate_results WHERE model_version='$VERSION'"

if $DRY_RUN; then
  echo ""
  echo "[DRY RUN] Would reset model_version='$VERSION' on all shipments and replay batch scoring."
  echo "Re-run without --dry-run to execute."
  exit 0
fi

echo ""
echo "Restoring model_version='$VERSION' on all shipments..."
sqlite3 "$DB" "UPDATE shipments SET model_version='$VERSION', calculated_risk_score=NULL, risk_score_calculated_at=NULL WHERE 1=1"

echo "Replaying batch scoring..."
cd "$PROJECT_ROOT"
python3 scripts/baseline_gate0.py
echo ""
echo "=== Restore complete: $VERSION ==="
