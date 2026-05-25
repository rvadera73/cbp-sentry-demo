# Risk Scoring Model - Complete Documentation Index
**Last Updated:** May 25, 2026  
**Status:** ✅ Ready for Implementation

---

## 📋 Quick Navigation

### 🚀 START HERE (Pick One)

| Need | Document | Time |
|------|----------|------|
| **Just want the fix?** | `MASTER_IMPLEMENTATION_PLAN.md` | 5 min |
| **Want the full story?** | `SESSION_SUMMARY.md` | 10 min |
| **Visual learner?** | `QUICKSTART.md` | 2 min |
| **Need exact code changes?** | `EXACT_CODE_CHANGES.md` | 5 min |

---

## 📚 Complete Document Guide

### Analysis & Understanding (Read These First)

1. **QUICKSTART.md** ⚡ (2 min)
   - TL;DR version
   - What's broken in 30 seconds
   - Where to find help for specific needs
   - **For:** Anyone who wants the summary

2. **SESSION_SUMMARY.md** 📋 (10 min)
   - What we discovered in this session
   - Root causes
   - What's working vs. broken
   - Next steps
   - **For:** Someone joining the project midstream

3. **RISK_SCORING_SUMMARY.txt** 👀 (ASCII diagrams, 3 min)
   - Visual representation of the problem
   - Data flow diagram
   - Architecture comparison
   - **For:** Visual learners

4. **RISK_SCORING_ANALYSIS.md** 📊 (15 min, comprehensive)
   - Complete gap analysis
   - All 5 phases of the solution
   - Specific implementation requirements
   - Success criteria
   - **For:** Architects, those needing full context

---

### Implementation Guides (Use These During Coding)

5. **MASTER_IMPLEMENTATION_PLAN.md** 🎯 (READ THIS, 5 min)
   - Executive summary of the whole project
   - Timeline: Day 1 cleanup + Day 2 implementation
   - Phase 0 (cleanup) checklist
   - Phase 1 (implementation) checklist
   - Success criteria
   - **For:** Project lead, development team

6. **EXACT_CODE_CHANGES.md** 💻 (Copy/paste reference)
   - Line-by-line changes to `services/api/main.py`
   - What to delete (with line numbers)
   - What to keep
   - What to modify
   - **For:** During Phase 0 cleanup

7. **PHASE1_IMPLEMENTATION_PLAN.md** 🔧 (Step-by-step)
   - 4 detailed implementation steps
   - Complete code snippets ready to use
   - Database schema updates
   - Frontend UI changes
   - Testing procedures
   - **For:** During Phase 1 coding

---

### Automation & Cleanup

8. **CLEANUP_AND_CONSOLIDATION_PLAN.md** 📋 (Reference)
   - What files to delete (old/duplicate)
   - What files to keep (correct ones)
   - What files to modify
   - Verification checklist
   - **For:** Understanding the cleanup strategy

9. **CLEANUP_SCRIPT.sh** 🗑️ (Bash script)
   - Automated file deletion
   - Orphaned import detection
   - Pre-deletion safety checks
   - Usage: `bash CLEANUP_SCRIPT.sh --confirm`
   - **For:** Actually deleting old files

---

## 🎯 The Problem (Quick Version)

```
3 Different Scoring Systems Creating Confusion:
├─ Database: 91 (static seed, never updated)
├─ API three_level_scorer: 39 (incomplete, missing 4 factors)
├─ Frontend riskBreakdown.ts: 38 (wrong formulas)
└─ CORRECT: risk_scoring_engine.py: 85-91 (NEVER CALLED)

Solution: Use the correct one (it's already built!)
```

---

## ✅ The Solution (Quick Version)

### Phase 0: Cleanup (1 hour today)
1. Remove old scorer imports from `main.py` (lines 28-29)
2. Remove old scorer instantiations from `main.py` (lines 135-137)
3. Remove old three-level endpoint from `main.py` (lines ~2950-3005)
4. Delete 5 duplicate scoring files
5. **Result:** Only `risk_scoring_engine.py` remains ✓

### Phase 1: Implement (4-6 hours day 1-2)
1. Create new API endpoint `/api/score/full-breakdown/{id}`
2. Update Investigation Page to call it
3. Add DB columns + migration
4. Test end-to-end
5. **Result:** Score now 85-91 with full 7-factor breakdown ✓

---

## 📊 7-Factor Model (What's Being Used)

```
risk_scoring_engine.py (32K - CORRECT & COMPLETE):
├─ Documentation Risk (25%)  ← Element 9, ISF amendments, manifest
├─ Commodity Sensitivity (15%) ← Tariff rate, export control, UFLPA
├─ Routing Risk (15%)        ← AIS dwell, port selection, vessel flag
├─ Party Profile Risk (15%)  ← Shipper age, violations, OFAC, opacity
├─ Corridor Risk (20%)       ← Country pair + tariff evasion incentive
├─ Pattern Anomaly (10%)     ← Pricing, transshipment ML
└─ Time Sensitivity (10%)    ← Pre-tariff timing, seasonality
= FINAL SCORE (0-100)
```

---

## 🗂️ File Structure After Cleanup

```
KEEP (Source of Truth):
├─ services/api/risk_scoring_engine.py      ✓ The correct model
├─ services/api/risk_models.py              ✓ Configuration
└─ api/services/risk_scoring/routes.py      ✓ New (Phase 1)

DELETE (Duplicates/Incomplete):
├─ services/api/three_level_scorer.py       ✗
├─ services/api/h3_scorer.py                ✗
├─ services/api/ml_scorers.py               ✗
├─ ui/src/utils/risk.ts                     ✗
└─ ui/src/v2/utils/riskBreakdown.ts         ✗
```

---

## 🎬 Getting Started

### Step 1: Understand (15 min)
- [ ] Read `QUICKSTART.md` (2 min)
- [ ] Read `MASTER_IMPLEMENTATION_PLAN.md` (5 min)
- [ ] Skim `EXACT_CODE_CHANGES.md` (8 min)

### Step 2: Phase 0 - Cleanup (1 hour)
- [ ] Follow `EXACT_CODE_CHANGES.md` for manual edits
- [ ] Test compiles: `python -m py_compile services/api/main.py`
- [ ] Run: `bash CLEANUP_SCRIPT.sh --confirm`

### Step 3: Phase 1 - Implement (4-6 hours)
- [ ] Follow `PHASE1_IMPLEMENTATION_PLAN.md` → Step 1 (create routes)
- [ ] Follow `PHASE1_IMPLEMENTATION_PLAN.md` → Step 2 (register routes)
- [ ] Follow `PHASE1_IMPLEMENTATION_PLAN.md` → Step 3 (update UI)
- [ ] Follow `PHASE1_IMPLEMENTATION_PLAN.md` → Step 4 (test)

### Step 4: Verify
- [ ] Run tests: `pytest api/tests/test_risk_scoring.py -v`
- [ ] Manual test: `curl -X POST localhost:8000/api/score/full-breakdown/test ...`
- [ ] UI test: Open Investigation Page, verify score displays correctly

---

## 🔍 How to Find What You Need

| Question | Answer In |
|----------|-----------|
| What's the problem? | `QUICKSTART.md` or `SESSION_SUMMARY.md` |
| What's the solution? | `MASTER_IMPLEMENTATION_PLAN.md` |
| What exact code changes? | `EXACT_CODE_CHANGES.md` |
| How do I implement Phase 1? | `PHASE1_IMPLEMENTATION_PLAN.md` |
| What gets deleted? | `CLEANUP_AND_CONSOLIDATION_PLAN.md` |
| How do I automate cleanup? | `CLEANUP_SCRIPT.sh` |
| Full technical analysis? | `RISK_SCORING_ANALYSIS.md` |
| Full context? | `SESSION_SUMMARY.md` |

---

## 📅 Timeline

- **Today (1 hour):** Phase 0 cleanup
- **Day 1-2 (4-6 hours):** Phase 1 implementation
- **Day 2 (optional, 1-2 hours):** Validation & testing
- **Weeks 2-4 (optional):** Phases 2-5 (data quality, feedback loop, ML training)

---

## ✨ Success Looks Like This

### Before Cleanup
```
❌ Multiple scoring endpoints with different results
❌ Officer sees 91 in header, 39 in breakdown (confused)
❌ Dead code, incomplete models, broken formulas
❌ No source of truth
```

### After Phase 0
```
✅ Only risk_scoring_engine.py exists
✅ Old files deleted
✅ Code compiles
✅ No orphaned imports
```

### After Phase 1
```
✅ Single API endpoint: /api/score/full-breakdown/{id}
✅ Investigation Page shows: 85-91 (consistent)
✅ Full 7-factor breakdown displayed
✅ Calculation table shows all components
✅ Officer confidence: "Why 87? I can see each factor and why."
```

---

## 🎯 Success Criteria

- [ ] No duplicate scoring models
- [ ] Single API endpoint
- [ ] Score consistent across DB, API, UI
- [ ] Full transparency (see all 7 components)
- [ ] Performance < 2 seconds
- [ ] Tests pass
- [ ] Officer user testing successful

---

## 📞 Questions?

**"What's broken?"** → `QUICKSTART.md`  
**"Why is this happening?"** → `SESSION_SUMMARY.md`  
**"What do I do?"** → `MASTER_IMPLEMENTATION_PLAN.md`  
**"Show me the code changes"** → `EXACT_CODE_CHANGES.md`  
**"Walk me through Phase 1"** → `PHASE1_IMPLEMENTATION_PLAN.md`  
**"I need full context"** → `RISK_SCORING_ANALYSIS.md`  

---

## 🚀 Ready?

1. **Read:** `MASTER_IMPLEMENTATION_PLAN.md` (5 min)
2. **Do:** Phase 0 cleanup (1 hour)
3. **Do:** Phase 1 implementation (4-6 hours)
4. **Verify:** Tests pass + UI works correctly
5. **Celebrate:** You've consolidated the scoring system! 🎉

Let's go! 💪
