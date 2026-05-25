#!/bin/bash
# Consolidation Script: Keep only 7-factor risk_scoring_engine
# Removes old/incomplete scoring models

set -e  # Exit on error

REPO_ROOT="/home/rahulvadera/cbp-sentry"
cd "$REPO_ROOT"

echo "╔════════════════════════════════════════════════════════════╗"
echo "║  CLEANUP & CONSOLIDATION: Remove Duplicate Scoring Models  ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Step 1: Check for orphaned imports
echo "📋 STEP 1: Checking for old scorer references..."
echo ""

OLD_REFS=$(grep -r "three_level_scorer\|h3_scorer\|ml_scorers" . \
  --include="*.py" --include="*.ts" --include="*.tsx" 2>/dev/null | grep -v "^Binary" | grep -v ".git/" || true)

if [ -n "$OLD_REFS" ]; then
  echo "⚠️  Found references to old scorers:"
  echo "$OLD_REFS" | head -10
  echo ""
  echo "These need to be updated manually before deletion!"
  echo ""
else
  echo "✓ No old scorer references found (or already cleaned)"
  echo ""
fi

# Step 2: List files to delete
echo "🗑️  STEP 2: Files to DELETE (old/incomplete models)..."
echo ""

FILES_TO_DELETE=(
  "services/api/three_level_scorer.py"
  "services/api/h3_scorer.py"
  "services/api/ml_scorers.py"
  "ui/src/utils/risk.ts"
  "ui/src/v2/utils/riskBreakdown.ts"
)

for file in "${FILES_TO_DELETE[@]}"; do
  if [ -f "$file" ]; then
    SIZE=$(du -h "$file" | cut -f1)
    echo "  ❌ DELETE: $file ($SIZE)"
  fi
done

echo ""

# Step 3: List files to keep
echo "✅ STEP 3: Files to KEEP (correct implementation)..."
echo ""

FILES_TO_KEEP=(
  "services/api/risk_scoring_engine.py"
  "services/api/risk_models.py"
)

for file in "${FILES_TO_KEEP[@]}"; do
  if [ -f "$file" ]; then
    SIZE=$(du -h "$file" | cut -f1)
    echo "  ✓ KEEP: $file ($SIZE)"
  fi
done

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║               MANUAL STEPS REQUIRED                        ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

echo "1️⃣  UPDATE services/api/main.py:"
echo "   Line 28-29: REMOVE these imports:"
echo "     from ml_scorers import H1CorridorRiskScorer, H2AnomalyScorer"
echo "     from h3_scorer import H3IntelligenceScorer"
echo ""
echo "   Line 135-137: REMOVE these instantiations:"
echo "     h1_scorer = H1CorridorRiskScorer()"
echo "     h2_scorer = H2AnomalyScorer()"
echo "     h3_scorer = H3IntelligenceScorer()  ← ALREADY PRESENT at line 137"
echo ""
echo "   NOTE: Keep line 140 (risk_scoring_engine instantiation) ✓"
echo ""
echo "   Line 2962: REMOVE endpoint using three_level_scorer"
echo "     Search for: async def score_shipment_three_level"
echo "     Replace with call to risk_scoring_engine"
echo ""

echo "2️⃣  CHECK services/api/feedback_engine.py:"
echo "   Run: grep -n three_level_scorer services/api/feedback_engine.py"
echo "   Update any references to use RiskScoringEngine"
echo ""

echo "3️⃣  UPDATE ui/src/pages/ModernCaseInvestigationPage.tsx:"
echo "   Replace: /score/three-level/{id} → /api/score/full-breakdown/{id}"
echo "   (Implementation details in PHASE1_IMPLEMENTATION_PLAN.md)"
echo ""

echo "4️⃣  AFTER manual updates, run this deletion:"
echo ""
echo "   bash -c 'rm -v \\"
echo "     services/api/three_level_scorer.py \\"
echo "     services/api/h3_scorer.py \\"
echo "     services/api/ml_scorers.py \\"
echo "     ui/src/utils/risk.ts \\"
echo "     ui/src/v2/utils/riskBreakdown.ts'"
echo ""

echo "5️⃣  VERIFY cleanup:"
echo ""
echo "   # Should show NO results"
echo "   grep -r 'three_level_scorer\|h3_scorer\|ml_scorers' . \\"
echo "     --include='*.py' --include='*.ts' --include='*.tsx'"
echo ""

echo "6️⃣  TEST the changes:"
echo ""
echo "   cd api && pytest tests/test_risk_scoring.py -v"
echo ""

echo "╔════════════════════════════════════════════════════════════╗"
echo "║                    BEFORE YOU DELETE                       ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "✋ STOP! Manual edits required before deletion."
echo ""
echo "Files changed:"
echo "  1. services/api/main.py (remove 3 imports, 3 instantiations, 1 endpoint)"
echo "  2. services/api/feedback_engine.py (check for old references)"
echo "  3. ui/src/pages/ModernCaseInvestigationPage.tsx (API endpoint update)"
echo ""
echo "After making these changes, re-run this script with --confirm flag"
echo ""
echo "Usage: bash CLEANUP_SCRIPT.sh --confirm"
echo ""

# If --confirm flag provided, proceed with deletion
if [ "$1" = "--confirm" ]; then
  echo ""
  echo "⚠️  PROCEEDING WITH FILE DELETION..."
  echo ""

  for file in "${FILES_TO_DELETE[@]}"; do
    if [ -f "$file" ]; then
      echo "Deleting: $file"
      rm -f "$file"
      echo "  ✓ Deleted"
    fi
  done

  echo ""
  echo "✅ Cleanup complete!"
  echo ""
  echo "Verify no orphaned imports:"
  grep -r "three_level_scorer\|h3_scorer\|ml_scorers" . \
    --include="*.py" --include="*.ts" --include="*.tsx" 2>/dev/null || echo "✓ No old references found"

  echo ""
  echo "Next: Implement Phase 1 (new API endpoint) per PHASE1_IMPLEMENTATION_PLAN.md"
else
  echo ""
  echo "📋 Ready for cleanup. Follow the manual steps above, then run:"
  echo "   bash CLEANUP_SCRIPT.sh --confirm"
  echo ""
fi
