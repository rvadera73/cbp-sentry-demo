# Risk Scoring Model - Gap Analysis & Improvement Plan
**Date:** May 25, 2026  
**Status:** Analysis Complete - Ready for Implementation

---

## Executive Summary

The risk scoring system has **three parallel implementations** that are out of sync:
1. **Database Static Scores** (91, 87, 85) - Seeded at initialization
2. **Frontend Calculation** (`riskBreakdown.ts`) - Uses h1/h2/h3 formulas that don't match backend
3. **Backend Three-Level Model** (`three_level_scorer.py`) - Active but incomplete

**Root Issue:** When users view Investigation Page, they see DB score (91) but the "calculated" score shown is different (39-45 range) because:
- UI pulls static `risk_score` from DB 
- UI also calls `three_level_scorer.py` which calculates a separate score
- These two values are **never reconciled**
- The DB score was seeded once and never updated

---

## Current Architecture Problems

### 1. **Multiple Scoring Models (No Single Source of Truth)**

| Model | Location | Used By | Status | Issues |
|-------|----------|---------|--------|--------|
| **7-Factor ML Model** | `risk_scoring_engine.py` | NONE | Dead code | Fully implemented but never called |
| **Three-Level Model** | `three_level_scorer.py` | Investigation Page API | Partial | Used in `/score/three-level/{id}` endpoint but incomplete external data calls |
| **Frontend H1/H2/H3** | `riskBreakdown.ts` | UI calculation | Broken | Uses incorrect formulas: `h1Score/4`, `h2Score/3.5` |
| **Database Static** | Seed data | Fallback display | Stale | Never updated after initial load |

### 2. **Data Flow Inconsistency**

```
User views Investigation Page
    ↓
Fetches shipment from DB (gets risk_score = 91)
    ↓
Calls /score/three-level/{id} API
    ↓
three_level_scorer.py calculates: (0.20*corridor + 0.35*vessel + 0.45*manifest) * 100
    ↓
Returns calculated_score = 39-45
    ↓
UI displays BOTH values (confusion!)
    ├─ Header shows: DB score (91) 
    └─ Scoring cards show: Three-level score (39-45)
```

### 3. **Score Calculation Discrepancy**

#### Example: Greenfield Case
- **DB Score:** 91 (from seed - never recalculated)
- **three_level_scorer.py:** ~42 (0.20×0.85 + 0.35×0.65 + 0.45×0.70 × 100 = ~70... but actual is lower)
- **Frontend riskBreakdown.ts:** ~38-42 (incorrect h1/h2/h3 formulas)
- **Expected (7-factor):** Should be ~85-91 based on element9_mismatch + documentation + commodity + routing + party + corridor + pattern + time

#### Root Causes:
1. **three_level_scorer.py** uses only 3 factors (corridor/vessel/manifest), missing:
   - Documentation risk (Element 9, ISF amendments, manifest completeness)
   - Commodity sensitivity (tariff, export control, UFLPA)
   - Party profile (shipper age, violations, OFAC)
   - Pattern anomalies (pricing, transshipment ML)

2. **Frontend riskBreakdown.ts** uses placeholder formulas instead of actual h1/h2/h3 scoring logic

3. **DB score** is static seed value, no recalculation path

---

## Gap Identification

### Critical Gaps

| Gap | Impact | Severity | Fix Effort |
|-----|--------|----------|------------|
| **No unified scoring engine in use** | User sees conflicting scores | CRITICAL | High |
| **DB never updated with calculated scores** | Stale data, fallback to wrong value | CRITICAL | Medium |
| **three_level_scorer incomplete** | Missing 4 of 7 factors | CRITICAL | High |
| **Frontend calculation broken** | Confuses officers with wrong math | HIGH | Low |
| **No API endpoint to persist scores** | Can't save calculation back to DB | HIGH | Medium |
| **ML models (Isolation Forest, LightGBM) not loaded** | Advanced pattern detection unused | MEDIUM | High |
| **Test-first specs for 4-tier model undefined** | test_scoring.py expects unimplemented code | MEDIUM | Medium |

---

## What Needs to Be Implemented

### Phase 1: Unify the Scoring Model (Foundation)

**Goal:** Make risk_scoring_engine.py the single source of truth

**Steps:**
1. ✅ `risk_scoring_engine.py` exists and is fully implemented
2. ⚠️ **Need:** Create API endpoint `/api/score/full-breakdown/{shipment_id}`
   - Takes shipment data
   - Calls `RiskScoringEngine.score_shipment()`
   - Returns: `RiskScoreBreakdown` with all 7 components, subtotal, adjustments, final_score
3. ⚠️ **Need:** Create database migration to add `calculated_risk_score` column to shipments table
4. ⚠️ **Need:** Create background job to recalculate all existing shipments with new engine
5. ⚠️ **Need:** Update Investigation Page to call new endpoint and display calculated_score instead of DB score

### Phase 2: Fix Data Persistence (DB Sync)

**Goal:** Calculated scores flow back to database

**Steps:**
1. ⚠️ **Need:** Add `UPDATE shipments SET calculated_risk_score = {score} WHERE id = {id}` after calculation
2. ⚠️ **Need:** Track calculation timestamp: `risk_score_calculated_at`
3. ⚠️ **Need:** Add API endpoint to override risk score with officer feedback: `PATCH /api/shipments/{id}/risk-score`
4. ⚠️ **Need:** Log all override events for audit trail

### Phase 3: Fix Frontend Display (UI Consistency)

**Goal:** UI shows correct calculated score with full breakdown

**Steps:**
1. 🔴 **Fix:** `riskBreakdown.ts` - Remove h1/h2/h3 formulas, use API response directly
2. ⚠️ **Need:** Create new component `RiskScoreBreakdownCard.tsx` to display:
   - Factor summary (Documentation, Commodity, Routing, Party, Corridor, Pattern, Time)
   - Component details with weights and calculations
   - Corridor adjustment explanation
   - Additional adjustments (OFAC, dwell anomalies)
   - Confidence interval
3. ⚠️ **Need:** Update Investigation Page to show calculated score prominently

### Phase 4: Train & Validate the Model (Quality)

**Goal:** Score accuracy matches expectations

**Steps:**
1. ⚠️ **Need:** Implement feedback loop: Officer marks score as "Correct" or "Incorrect" + reason
2. ⚠️ **Need:** Run validation on 100 known cases (greenfield, transshipment, clean)
3. ⚠️ **Need:** Tune factor weights based on feedback
4. ⚠️ **Need:** Document baseline expectations (Greenfield = 85-91, Clean = 15-30, Transshipment = 70-90)

### Phase 5: Enable ML Models (Advanced)

**Goal:** Isolation Forest and LightGBM active for pattern detection

**Steps:**
1. ⚠️ **Need:** Train Isolation Forest on AIS dwell data
2. ⚠️ **Need:** Train LightGBM on transshipment classification
3. ⚠️ **Need:** Integrate outputs into `risk_scoring_engine.py`
4. ⚠️ **Need:** Add model versioning (track which version scored which shipment)

---

## Specific Implementation Requirements

### 1. Fix the Inconsistency (97 vs 39)

**For a shipment with DB score = 91:**

| Calculation Path | Current | Expected | Gap |
|------------------|---------|----------|-----|
| DB lookup | 91 | 91 | ✓ Correct |
| three_level_scorer | 42 | 70-75 | -33 points (missing factors) |
| Frontend riskBreakdown | 38 | 70-75 | -37 points (broken formulas) |
| **Correct (7-factor)** | None | **85-91** | Need to implement |

**Action:** Replace three_level_scorer with risk_scoring_engine in Investigation Page

### 2. Update Database Schema

```sql
-- Add new columns to shipments table
ALTER TABLE shipments ADD COLUMN IF NOT EXISTS calculated_risk_score REAL;
ALTER TABLE shipments ADD COLUMN IF NOT EXISTS risk_score_calculated_at TIMESTAMP;
ALTER TABLE shipments ADD COLUMN IF NOT EXISTS risk_score_breakdown JSON;  -- Store full component details
ALTER TABLE shipments ADD COLUMN IF NOT EXISTS confidence_interval TEXT;

-- Index for queries
CREATE INDEX IF NOT EXISTS idx_calculated_risk_score ON shipments(calculated_risk_score DESC);
```

### 3. New API Endpoint

```python
@router.post("/api/score/full-breakdown/{shipment_id}")
async def calculate_full_risk_breakdown(
    shipment_id: str,
    shipment_data: ShipmentRequest
) -> RiskScoreBreakdownResponse:
    """
    Calculate comprehensive risk score with full component breakdown.
    
    Returns: RiskScoreBreakdown with:
    - 7 component scores
    - Calculation table (transparency)
    - Final score (0-100)
    - Confidence interval
    """
    engine = RiskScoringEngine()
    breakdown = engine.score_shipment(shipment_data.dict())
    
    # Persist to DB
    db.shipments.update(
        id=shipment_id,
        calculated_risk_score=breakdown.final_score,
        risk_score_calculated_at=datetime.utcnow(),
        risk_score_breakdown=breakdown.to_dict()
    )
    
    return RiskScoreBreakdownResponse(**breakdown.to_dict())
```

### 4. Update Investigation Page

```typescript
// ModernCaseInvestigationPage.tsx - Changes
async function fetchRiskScoreBreakdown() {
    const response = await fetch(
        `${API_BASE_URL}/score/full-breakdown/${shipmentId}`,
        { 
            method: 'POST',
            body: JSON.stringify(caseData)
        }
    );
    
    const breakdown = await response.json();
    
    // USE this instead of threeLevelScore
    setRiskBreakdown(breakdown);
}

// Display calculated score, not DB score
<div className="score-display">
    <div className="score-number">
        {Math.round(riskBreakdown?.final_score || 0)}  {/* Calculated */}
    </div>
    <div className="score-note">
        (DB: {caseData.risk_score}) {/* Show DB for reference */}
    </div>
</div>
```

### 5. Data Migration Script

```python
# scripts/recalculate_all_risks.py
import asyncio
from api.services.risk_scoring_engine import RiskScoringEngine
from api.core.shipments_db import get_all_shipments, update_shipment

async def recalculate():
    engine = RiskScoringEngine()
    shipments = get_all_shipments(limit=10000)
    
    for shipment in shipments['shipments']:
        breakdown = engine.score_shipment(shipment)
        update_shipment(
            shipment['id'],
            calculated_risk_score=breakdown.final_score,
            risk_score_breakdown=breakdown.to_dict()
        )
        print(f"✓ {shipment['id']}: {breakdown.final_score}/100")

# Run: python -m scripts.recalculate_all_risks
```

---

## Success Criteria

After implementation, verify:

1. ✅ **Consistency:** Same shipment always returns same score across DB, API, UI
2. ✅ **Accuracy:** 
   - Greenfield test case: 85-91 (not 39 or 97)
   - Clean case: 15-30
   - Transshipment: 70-90
3. ✅ **Transparency:** Officer can see why score is X (all components, weights, calculations)
4. ✅ **Persistence:** Calculated score saved to DB with timestamp
5. ✅ **Auditability:** All score changes logged with reason
6. ✅ **Performance:** Score calculation < 2 seconds

---

## Recommendation

**Start with Phase 1:** Implement the unified API endpoint using existing `risk_scoring_engine.py`

This will:
- Fix the 97 vs 39 discrepancy immediately
- Provide single source of truth
- Enable transparency (calculation table)
- Cost: ~4-6 hours
- Impact: Critical (eliminates user confusion)

Then proceed to Phases 2-5 for full integration.

---

## Files to Create/Modify

### Create:
- `/api/services/risk_scoring/routes.py` - New risk scoring endpoints
- `/api/services/risk_scoring/models.py` - Request/response schemas
- `/scripts/recalculate_all_risks.py` - Migration script
- `/ui/src/components/scoring/RiskScoreBreakdownCard.tsx` - New UI component

### Modify:
- `/api/core/shipments_db.py` - Add calculated_risk_score columns
- `/ui/src/pages/ModernCaseInvestigationPage.tsx` - Call new endpoint, display new score
- `/ui/src/v2/utils/riskBreakdown.ts` - Remove broken formulas
- `/api/main.py` - Register new routes

### Delete:
- `/services/api/three_level_scorer.py` - Replace with risk_scoring_engine
- `/ui/src/utils/risk.ts` - Old calculation utility (if unused)

---

## Questions for Clarification

1. **Baseline Expectations:** What should the score be for different case types?
   - Greenfield (provable origin fraud): 85-95?
   - Clean shipper (low-risk): 10-30?
   - Transshipment (route anomaly): 60-80?

2. **External Data:** Are OFAC, price benchmarks, HS duty rates available?
   - Currently hardcoded in config
   - Should they pull from live APIs?

3. **Officer Feedback:** How should officers correct incorrect scores?
   - UI button to "Override score to X because..."?
   - Retraining feedback loop?

4. **Audit Trail:** Should all score changes be logged forever?
   - Full history needed for compliance?
