# Cleanup & Consolidation Plan
**Objective:** Remove duplicate/incomplete scorers, consolidate to single 7-factor model  
**Status:** Ready to execute

---

## Files to DELETE (Old/Incomplete Models)

### ❌ Delete These Files

```bash
# OLD PARTIAL MODELS - CONFLICTING & INCOMPLETE
rm /home/rahulvadera/cbp-sentry/services/api/three_level_scorer.py      # 19K - incomplete (3 factors)
rm /home/rahulvadera/cbp-sentry/services/api/h3_scorer.py               # 4.2K - old H3 component
rm /home/rahulvadera/cbp-sentry/services/api/ml_scorers.py              # 9.1K - old H1/H2 scorers

# OLD FRONTEND CALCULATIONS - BROKEN FORMULAS
rm /home/rahulvadera/cbp-sentry/ui/src/utils/risk.ts                    # Old calculation utility
rm /home/rahulvadera/cbp-sentry/ui/src/v2/utils/riskBreakdown.ts        # Broken h1/h2/h3 formulas
```

### ✅ Keep These Files

```bash
# CORRECT MODEL & SUPPORTING FILES
/home/rahulvadera/cbp-sentry/services/api/risk_scoring_engine.py        # 32K - THE CORRECT 7-FACTOR MODEL
/home/rahulvadera/cbp-sentry/services/api/risk_models.py                # 15K - Configuration & schemas
```

---

## Files to UPDATE (Remove Old References)

### 1. `/services/api/main.py` - Remove Old Imports

**Find these lines:**
```python
# Line 28-29: OLD IMPORTS
from ml_scorers import H1CorridorRiskScorer, H2AnomalyScorer
from h3_scorer import H3IntelligenceScorer

# Line 137: OLD INSTANTIATION  
h3_scorer = H3IntelligenceScorer()

# Line 2962: OLD ENDPOINT
from three_level_scorer import scorer
```

**Replace with:**
```python
# NEW IMPORT - Single source of truth
from risk_scoring_engine import RiskScoringEngine

# NEW INSTANTIATION
risk_scoring_engine = RiskScoringEngine()
```

### 2. `/services/api/feedback_engine.py` - Check for Old References

Run:
```bash
grep -n "three_level_scorer\|h3_scorer\|ml_scorers" /home/rahulvadera/cbp-sentry/services/api/feedback_engine.py
```

Update any references to use `RiskScoringEngine` instead.

---

## Frontend Cleanup

### `/ui/src/pages/ModernCaseInvestigationPage.tsx`

**Remove these API calls:**
```typescript
// REMOVE: This calls old three_level_scorer
const scoreResponse = await fetch(
  `${API_BASE_URL}/score/three-level/${shipment.id}...`
);

// REPLACE WITH: New unified endpoint
const scoreResponse = await fetch(
  `${API_BASE_URL}/score/full-breakdown/${shipment.id}`,
  { method: 'POST', body: JSON.stringify(shipment) }
);
```

### Delete Old Files
```bash
rm /home/rahulvadera/cbp-sentry/ui/src/utils/risk.ts
rm /home/rahulvadera/cbp-sentry/ui/src/v2/utils/riskBreakdown.ts
```

---

## API Endpoint Consolidation

### Current (Conflicting)
```
GET  /score/three-level/{id}         → uses three_level_scorer (incomplete)
GET  /score/h3/{id}                  → uses h3_scorer (old)
GET  /score/h1/{id}                  → uses ml_scorers (old)
```

### After Cleanup (Single Source of Truth)
```
POST /api/score/full-breakdown/{id}  → uses risk_scoring_engine (7-factor, correct)
```

---

## Step-by-Step Execution

### Phase 1: Code Cleanup (30 minutes)

```bash
# Step 1: Update main.py
# - Remove imports: ml_scorers, h3_scorer, three_level_scorer
# - Add import: risk_scoring_engine.RiskScoringEngine
# - Replace h3_scorer instantiation with RiskScoringEngine

# Step 2: Update feedback_engine.py
# - Search for old scorer references
# - Replace with risk_scoring_engine

# Step 3: Update Investigation Page (ModernCaseInvestigationPage.tsx)
# - Remove /score/three-level/{id} calls
# - Add /api/score/full-breakdown/{id} calls (from Phase 1 implementation)

# Step 4: Delete old files
rm services/api/three_level_scorer.py
rm services/api/h3_scorer.py
rm services/api/ml_scorers.py
rm ui/src/utils/risk.ts
rm ui/src/v2/utils/riskBreakdown.ts
```

### Phase 2: Test (15 minutes)

```bash
# Verify imports work
python -m py_compile services/api/main.py

# Test the engine works
cd api && pytest tests/test_risk_scoring.py -v
```

### Phase 3: Cleanup Analysis Docs (Optional)

Keep only:
```bash
# KEEP - Implementation reference
PHASE1_IMPLEMENTATION_PLAN.md
RISK_SCORING_ANALYSIS.md

# DELETE - Old analysis (now obsolete)
RISK_SCORING_SUMMARY.txt        # Showed the "three systems" problem - no longer true
```

---

## Verification Checklist

After cleanup, verify:

- [ ] No imports of `three_level_scorer`, `h3_scorer`, or `ml_scorers` exist
- [ ] No API endpoints for old scorers remain
- [ ] `risk_scoring_engine.py` is the only scoring implementation
- [ ] `risk_models.py` contains all configuration
- [ ] All tests pass
- [ ] Phase 1 implementation deploys successfully
- [ ] Investigation Page shows calculated score (85-91 range, not 39)

---

## Files Affected

```
DELETIONS (5 files):
├─ services/api/three_level_scorer.py
├─ services/api/h3_scorer.py
├─ services/api/ml_scorers.py
├─ ui/src/utils/risk.ts
└─ ui/src/v2/utils/riskBreakdown.ts

MODIFICATIONS (2 files):
├─ services/api/main.py
└─ services/api/feedback_engine.py

STAYS (2 files):
├─ services/api/risk_scoring_engine.py    ← THE SOURCE OF TRUTH
└─ services/api/risk_models.py

IMPLEMENTATION (NEW):
├─ api/services/risk_scoring/routes.py    ← Create this (Phase 1)
```

---

## Why This Cleanup Matters

**Before (Confusing):**
```
Multiple scoring endpoints → Different results → Officer confusion
├─ /score/three-level/{id} → 39
├─ /score/h3/{id} → different value
└─ /score/h1/{id} → different value
```

**After (Clear):**
```
Single endpoint → Single result → Officer confidence
└─ /api/score/full-breakdown/{id} → 85-91 (with full breakdown)
```

---

## Safety Notes

1. **Keep risk_models.py** - Contains critical factor weights and configurations
2. **Backup main.py before editing** - It's 182K and central to the app
3. **Run tests after each change** - Verify nothing broke
4. **Keep Phase1_IMPLEMENTATION_PLAN.md** - It guides the new endpoint creation

---

## Next Command

Once ready, run:
```bash
# Stage 1: Update references in code
# (manually, following PHASE1_IMPLEMENTATION_PLAN.md)

# Stage 2: Delete old files
bash -c 'rm -v services/api/three_level_scorer.py services/api/h3_scorer.py services/api/ml_scorers.py ui/src/utils/risk.ts ui/src/v2/utils/riskBreakdown.ts'

# Verify no orphaned imports
grep -r "three_level_scorer\|h3_scorer\|ml_scorers" . --include="*.py" --include="*.ts" --include="*.tsx"
```
