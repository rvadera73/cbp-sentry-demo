# Master Implementation Plan: Fix Risk Scoring Model

> ⚠️ **SUPERSEDED** — This document describes a prior consolidation task (completed June 2026).
> The current master plan is in `CLAUDE.md § Known Issues & TODOs` and the session plan file.
> For the full maturity roadmap (15%→90%), see `GATES_DEFINITION_AND_CURRENT_STATE.md`.

**Original Status:** Completed — 7-factor rule engine + XGBoost blend is now the single scorer.  
**Archive Date:** June 24, 2026

---

## Executive Summary

You have **three competing scoring systems**. This plan consolidates to **one**: the 7-factor model that's already built and working.

```
CURRENT STATE (Broken):
├─ risk_scoring_engine.py (7-factor, correct, not used)
├─ three_level_scorer.py (3-factor, incomplete, used)
└─ h3_scorer + ml_scorers (old, causing confusion)

DESIRED STATE (Clean):
└─ risk_scoring_engine.py (7-factor, correct, ONLY ONE USED)
```

---

## Phase 0: Cleanup (Today - 1 hour)

**Goal:** Remove duplicate/conflicting code

### Step 1: Review Code Changes (10 min)
- [ ] Read `EXACT_CODE_CHANGES.md` - See exactly what to delete/modify
- [ ] Open `services/api/main.py` in editor
- [ ] Locate lines 28-29 (old imports)
- [ ] Locate lines 135-137 (old instantiations)
- [ ] Locate lines ~2950-3005 (three-level endpoint)

### Step 2: Make Manual Changes (20 min)
- [ ] Delete lines 28-29: `from ml_scorers...` and `from h3_scorer...`
- [ ] Delete lines 135-137: `h1_scorer`, `h2_scorer`, `h3_scorer` instantiations
- [ ] Delete entire `async def score_shipment_three_level(...)` function (~55 lines)
- [ ] Check `feedback_engine.py` for old references (probably none)

### Step 3: Verify Syntax (10 min)
- [ ] Test main.py compiles: `python -m py_compile services/api/main.py`
- [ ] Check for orphaned imports: 
  ```bash
  grep -r "three_level_scorer\|h3_scorer\|ml_scorers" . --include="*.py" --include="*.ts"
  ```
- [ ] Should return: **No results** (or only in deleted files)

### Step 4: Delete Old Files (5 min)
```bash
bash CLEANUP_SCRIPT.sh --confirm
```

This deletes:
```
✗ services/api/three_level_scorer.py
✗ services/api/h3_scorer.py
✗ services/api/ml_scorers.py
✗ ui/src/utils/risk.ts
✗ ui/src/v2/utils/riskBreakdown.ts
```

**Result:** Only `risk_scoring_engine.py` remains as the scoring system ✓

---

## Phase 1: Implement New Endpoint (Day 1-2, 4-6 hours)

**Goal:** Create the API that Investigation Page will call

### Step 1: Create Routes File (1.5 hours)

**File:** `api/services/risk_scoring/routes.py` (NEW)

Copy code from `PHASE1_IMPLEMENTATION_PLAN.md` → Step 1

### Step 2: Register Routes (15 min)

**File:** `api/main.py` (MODIFY)

Add at top:
```python
from services.risk_scoring import routes as risk_scoring_routes
```

Add in app creation:
```python
app.include_router(risk_scoring_routes.router)
```

### Step 3: Update Database Schema (1 hour)

**File:** `api/core/shipments_db.py` (MODIFY)

Add function:
```python
def update_shipment_risk_score(shipment_id, calculated_risk_score, ...):
    # Updates DB with calculated score
```

Run migration:
```bash
python scripts/add_risk_score_columns.py
```

### Step 4: Update Investigation Page (1.5 hours)

**File:** `ui/src/pages/ModernCaseInvestigationPage.tsx` (MODIFY)

Replace old `threeLevelScore` state with `riskBreakdown` state  
Replace API call to `/score/three-level/{id}` with `/api/score/full-breakdown/{id}`  
Update display to show full 7-factor breakdown

Copy code from `PHASE1_IMPLEMENTATION_PLAN.md` → Step 3

### Step 5: Test End-to-End (30 min)

```bash
# Start API
cd api && python -m uvicorn main:app --reload

# Test new endpoint
curl -X POST http://localhost:8000/api/score/full-breakdown/shipment-1 \
  -H "Content-Type: application/json" \
  -d @/tmp/test_shipment.json

# Expected: Full breakdown with final_score, components, calculation_table
```

---

## Success Criteria

After Phase 0 + Phase 1, verify:

### ✅ Code Quality
- [ ] No imports of `three_level_scorer`, `h3_scorer`, `ml_scorers`
- [ ] `risk_scoring_engine` is the only scoring system
- [ ] All tests pass: `pytest api/tests/test_risk_scoring.py -v`

### ✅ Functionality
- [ ] API endpoint `/api/score/full-breakdown/{id}` works
- [ ] Returns full 7-factor breakdown (not 39, not 91, but 85-91)
- [ ] Investigation Page calls new endpoint
- [ ] Score displayed with confidence interval

### ✅ Data
- [ ] Database columns added: `calculated_risk_score`, `risk_score_calculated_at`, etc.
- [ ] Calculated scores persisted after each call
- [ ] No more 97 vs 39 discrepancy

### ✅ Transparency
- [ ] Officer sees all 7 components
- [ ] Each component shows score, weight, weighted result
- [ ] Full calculation table visible
- [ ] Rationale & evidence displayed

---

## Files Involved

### DELETE (Phase 0)
```
services/api/three_level_scorer.py      ✗
services/api/h3_scorer.py               ✗
services/api/ml_scorers.py              ✗
ui/src/utils/risk.ts                    ✗
ui/src/v2/utils/riskBreakdown.ts        ✗
```

### MODIFY (Phase 0)
```
services/api/main.py                    (remove 3 imports, 3 instantiations, 1 function)
services/api/feedback_engine.py         (check for references)
```

### CREATE (Phase 1)
```
api/services/risk_scoring/routes.py     (new endpoint)
api/services/risk_scoring/__init__.py   (package marker)
scripts/add_risk_score_columns.py       (DB migration)
```

### MODIFY (Phase 1)
```
api/main.py                             (register new routes)
api/core/shipments_db.py                (add persistence function)
ui/src/pages/ModernCaseInvestigationPage.tsx   (update UI)
```

### KEEP (Both Phases)
```
services/api/risk_scoring_engine.py     ✓ (THE SOURCE OF TRUTH)
services/api/risk_models.py             ✓ (configuration)
```

---

## Day-by-Day Timeline

### Day 1 (Morning): Cleanup
- [ ] 0:00 - Read `EXACT_CODE_CHANGES.md`
- [ ] 0:15 - Make manual edits to main.py
- [ ] 0:35 - Run syntax checks
- [ ] 0:45 - Run `CLEANUP_SCRIPT.sh --confirm`
- [ ] 1:00 - COMPLETE! Commit changes: "cleanup: remove duplicate scoring models"

### Day 1-2 (Afternoon): Phase 1 Implementation
- [ ] 2:00 - Create `api/services/risk_scoring/routes.py`
- [ ] 3:30 - Register routes in `api/main.py`
- [ ] 4:00 - Add DB columns + run migration
- [ ] 5:30 - Update Investigation Page UI
- [ ] 6:00 - Test end-to-end
- [ ] 6:30 - COMPLETE! Commit changes: "feat: implement 7-factor risk scoring endpoint"

### Day 2 (Optional): Validation
- [ ] Run full test suite
- [ ] Verify scores on known cases (Greenfield, Clean, Transshipment)
- [ ] Officer user testing
- [ ] Tune factor weights based on feedback

---

## Risk Mitigation

### If Phase 0 Breaks Something
- [ ] Revert deleted imports + instantiations from git
- [ ] Keep the cleaned-up main.py
- [ ] Investigation Page will fall back to DB score temporarily

### If Phase 1 Breaks Something
- [ ] Keep `three_level_scorer.py` as fallback
- [ ] Investigation Page calls old endpoint until new one stabilizes
- [ ] Allows gradual rollout

### If Scores Look Wrong
- [ ] Check shipment input data (is hs_code, ad_cvd_rate populated?)
- [ ] Check ML models are loaded (Isolation Forest, LightGBM)
- [ ] Review calculation_table in response (shows exactly which components contribute what)

---

## Documentation to Keep

After cleanup, these analysis docs are **reference only** (archive if needed):
```
RISK_SCORING_ANALYSIS.md           ← Explains the 3-system problem (solved now)
RISK_SCORING_SUMMARY.txt           ← Visual of the problem (solved now)
EXACT_CODE_CHANGES.md              ← Keep (reference for what changed)
PHASE1_IMPLEMENTATION_PLAN.md      ← Keep (implementation guide)
CLEANUP_AND_CONSOLIDATION_PLAN.md  ← Keep (what was deleted and why)
CLEANUP_SCRIPT.sh                  ← Keep (automated cleanup)
SESSION_SUMMARY.md                 ← Keep (context)
```

---

## Command Quick Reference

### Phase 0: Cleanup
```bash
# Check for changes needed
grep -n "from ml_scorers\|from h3_scorer" services/api/main.py

# Check if change compiles
python -m py_compile services/api/main.py

# Verify no orphaned imports
grep -r "three_level_scorer\|h3_scorer\|ml_scorers" . --include="*.py"

# Run automated deletion (after manual edits)
bash CLEANUP_SCRIPT.sh --confirm
```

### Phase 1: Implementation
```bash
# Create new routes file
# (follow PHASE1_IMPLEMENTATION_PLAN.md)

# Run migrations
python scripts/add_risk_score_columns.py

# Start API for testing
cd api && python -m uvicorn main:app --reload

# Test the endpoint
curl -X POST http://localhost:8000/api/score/full-breakdown/test \
  -H "Content-Type: application/json" \
  -d '{"id":"test","element9_is_mismatch":true, ...}'
```

---

## What You'll Get After Phase 0 + Phase 1

### For the User (Officer)
```
Investigation Page now shows:
├─ Risk Score: 87 (single number, no confusion)
├─ Confidence: ±2.5%
└─ 7-Factor Breakdown:
    ├─ Documentation: 8.2/10 (Element 9 critical)
    ├─ Commodity: 6.5/10 (Tariff)
    ├─ Routing: 7.3/10 (AIS dwell)
    ├─ Party: 6.1/10 (Shipper age)
    ├─ Corridor: 7.8/10 (CN→US)
    ├─ Pattern: 6.9/10 (Transshipment ML)
    └─ Time: 3.2/10 (Timing)

Why 87? [Full calculation table with every number explained]
```

### For the System
- Single source of truth: `risk_scoring_engine.py`
- Full data persistence: calculated scores saved to DB
- Complete transparency: every component visible with evidence
- Ready for Phase 2-5: feedback loops, ML training, audit trails

---

## Next Steps After This Phase

### Phase 2: Data Quality (1-2 weeks)
- Ensure all shipment fields populated (hs_code, ad_cvd_rate, prior_violations)
- Load ML models (Isolation Forest, LightGBM)
- Connect to live external data (tariffs, pricing benchmarks)

### Phase 3: Officer Feedback Loop (2 weeks)
- UI button: "Correct/incorrect score?"
- Reason dropdown (too high, too low, missing factor, etc.)
- Retrain factor weights monthly

### Phase 4: Advanced ML (4 weeks)
- Train models on known cases
- A/B test new weights
- Production deployment

---

**Ready to start? Begin with Phase 0.**

Questions? Refer to:
- Exact changes needed: `EXACT_CODE_CHANGES.md`
- Implementation details: `PHASE1_IMPLEMENTATION_PLAN.md`
- Cleanup automation: `CLEANUP_SCRIPT.sh`

Let's consolidate and get one system working correctly! 🚀
