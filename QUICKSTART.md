# Risk Scoring Analysis - Quick Start Guide

## TL;DR

**Problem:** Risk score shows different values (97 in DB, 39 in UI)  
**Cause:** Three different scoring systems, none synchronized  
**Solution:** Activate the correct 7-factor model that already exists  
**Time:** 4-6 hours for Phase 1  
**Impact:** High (fixes user confusion immediately)

---

## Where to Start (Pick One)

### 👀 Visual Learner?
**Read:** `RISK_SCORING_SUMMARY.txt` (2 min)
- ASCII diagrams of current vs. correct architecture
- Data flow visualization
- Root causes at a glance

### 📊 Need Full Context?
**Read:** `RISK_SCORING_ANALYSIS.md` (15 min)
- Complete gap identification
- 5-phase implementation roadmap
- Why each gap matters

### 💻 Ready to Code?
**Read:** `PHASE1_IMPLEMENTATION_PLAN.md` (30 min)
- Step-by-step code changes
- Exact file paths and code snippets
- Deployment checklist

### 📋 Just Want the Summary?
**Read:** `SESSION_SUMMARY.md` (5 min)
- What we found
- What's working/broken
- Next steps

---

## The Fix in 30 Seconds

```
CURRENT STATE:
└─ DB: risk_score = 91 (static seed, never updated)
└─ API three_level_scorer: calculates 39 (missing 4 factors)
└─ Frontend riskBreakdown: calculates 38 (wrong formulas)
└─ risk_scoring_engine.py: exists but UNUSED ❌

SOLUTION:
1. Create API endpoint → /api/score/full-breakdown/{id}
2. Use risk_scoring_engine.py (the correct one!)
3. Update Investigation Page to call new endpoint
4. Done! Score is now 85-91 (with full transparency)
```

---

## The Three Scoring Systems

| System | Location | Result | Problem |
|--------|----------|--------|---------|
| **Dead Code** | `risk_scoring_engine.py` | 85-91 ✅ | Never called |
| **Incomplete** | `three_level_scorer.py` | 39-45 ❌ | Missing 4 factors |
| **Broken** | `riskBreakdown.ts` | 38-42 ❌ | Wrong math |
| **Stale** | Database seed | 91 ❌ | Never updated |

---

## Implementation Phases

### Phase 1: Activate Correct Model (4-6 hrs) — START HERE
- [ ] Create `/api/services/risk_scoring/routes.py`
- [ ] Update `/api/main.py`
- [ ] Modify Investigation Page UI
- [ ] Add DB columns + migration
- [ ] Result: 85-91 score with full transparency

### Phase 2: Persist Scores (3-4 hrs) — LATER
- [ ] Save calculated scores to DB
- [ ] Track calculation timestamps
- [ ] Officer override endpoint

### Phase 3: UI Polish (2-3 hrs) — LATER
- [ ] Component breakdown card
- [ ] Calculation table display
- [ ] Confidence interval UI

### Phase 4: Validate (ongoing) — LATER
- [ ] Officer feedback loop
- [ ] Retrain weights
- [ ] Test on known cases

### Phase 5: ML Models (future) — LATER
- [ ] Train Isolation Forest
- [ ] Train LightGBM
- [ ] Integrate into engine

---

## Files Created for You

Located in `/home/rahulvadera/cbp-sentry/`:

```
├─ RISK_SCORING_SUMMARY.txt          👈 Start here (visual)
├─ RISK_SCORING_ANALYSIS.md          📖 Full analysis
├─ PHASE1_IMPLEMENTATION_PLAN.md      💻 Code walkthrough
├─ SESSION_SUMMARY.md                📋 This session recap
└─ QUICKSTART.md                     ⚡ You are here
```

---

## Key Insights

### What's Actually Happening

Officer opens Investigation Page for Greenfield case:

```
UI fetches DB → gets risk_score = 91
UI calls /score/three-level/{id} → gets 42
UI displays both → officer confused 😕
```

### The Right Way (After Phase 1)

Officer opens same page:

```
UI calls /score/full-breakdown/{id}
Backend uses risk_scoring_engine.py
Returns: 87 with full 7-factor breakdown
Officer sees: "Why 87? Here's each component..."
```

---

## Quick Facts

- ✅ Correct model **already implemented** (`risk_scoring_engine.py`)
- ❌ Just **not connected to API**
- 📊 7 factors evaluated (Documentation, Commodity, Routing, Party, Corridor, Pattern, Time)
- 🎯 Expected Greenfield score: 85-91 (not 97 or 39!)
- ⏱️ Phase 1: 4-6 hours to fix
- 📈 High impact on user clarity

---

## What Needs to Happen

```
1. Create API endpoint (use existing risk_scoring_engine)
   ↓
2. Investigation Page calls new endpoint
   ↓
3. Display calculated score + breakdown
   ↓
4. Save to DB
   ↓
5. Problem solved ✓
```

---

## Success Looks Like This

**Before:**
```
Risk Score: 91 (in header)
Three-Level Score: 42 (in breakdown cards)
Officer: "What?!"
```

**After Phase 1:**
```
Risk Score: 87
Confidence: ±2.5%

7-Factor Breakdown:
├─ Documentation: 8.2/10 ✓
├─ Commodity: 6.5/10 ✓
├─ Routing: 7.3/10 ✓
├─ Party: 6.1/10 ✓
├─ Corridor: 7.8/10 ✓
├─ Pattern: 6.9/10 ✓
└─ Time: 3.2/10 ✓

Why 87? [Full calculation table...]
Officer: "Makes sense."
```

---

## Next Steps

1. **Read** `RISK_SCORING_SUMMARY.txt` (visualize the problem)
2. **Understand** `RISK_SCORING_ANALYSIS.md` (why it matters)
3. **Plan** `PHASE1_IMPLEMENTATION_PLAN.md` (what to code)
4. **Implement** Phase 1 (4-6 hours)
5. **Test** & verify scores are consistent

---

## Questions?

- **"What's the problem?"** → Read `RISK_SCORING_SUMMARY.txt`
- **"What are the gaps?"** → Read `RISK_SCORING_ANALYSIS.md`
- **"How do I code Phase 1?"** → Read `PHASE1_IMPLEMENTATION_PLAN.md`
- **"What happened in this session?"** → Read `SESSION_SUMMARY.md`

---

**Status:** Analysis Complete ✅  
**Ready for:** Implementation  
**Estimated Effort:** 4-6 hours (Phase 1)  
**Value:** High (fixes user confusion immediately)  

🚀 **Let's fix this!**
