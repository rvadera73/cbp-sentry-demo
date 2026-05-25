# Risk Scoring Calculation Flow - Complete Transparency

## Executive Summary

This document details **every step** in the risk scoring calculation, including:
- Component-level calculations
- Factor-level aggregation
- Adjustment logic
- **When and how Altana API is invoked**
- How Altana findings adjust the final score

---

## STEP 1: Component Scoring (7 Factors, 20+ Components)

### INPUT: Shipment Data
```
Example: Shanghai Trade Co. shipment (SHP-163679)
├─ element9_is_mismatch: TRUE (VN declared, but CN actual)
├─ dwell_days: 9.0 (vs 2.5 baseline = 3.6× anomaly)
├─ shipper_age_months: 2 (NEW SHIPPER)
├─ ad_cvd_applicable: TRUE (25% tariff)
├─ ad_cvd_rate: 0.25
├─ hs_code: 6204.29 (textiles)
└─ vessel_flag: HK (transshipment hub)
```

### STEP 1A: Calculate Each Component Score

**TABLE 1: Component-Level Calculation**

| Factor | Component | Score (0-10) | Weight | Calculation | Weighted Result |
|--------|-----------|--------------|---------|-------------|-----------------|
| **Documentation** | Element 9 Mismatch | 9.5 | 11.4% | 9.5 × 0.114 ÷ 10 | **1.08** |
| | ISF Amendments | 2.0 | 6.8% | 2.0 × 0.068 ÷ 10 | **0.14** |
| | Manifest Completeness | 6.0 | 4.5% | 6.0 × 0.045 ÷ 10 | **0.27** |
| **Commodity** | Tariff Rate (AD/CVD 25%) | 5.0 | 6.8% | 5.0 × 0.068 ÷ 10 | **0.34** |
| | Export Control | 2.0 | 4.1% | 2.0 × 0.041 ÷ 10 | **0.08** |
| | UFLPA Risk | 3.0 | 2.7% | 3.0 × 0.027 ÷ 10 | **0.08** |
| **Routing** | **AIS Dwell (ML)** | **9.0** | **9.9%** | **9.0 × 0.099 ÷ 10** | **0.89** |
| | Port Selection | 6.5 | 7.5% | 6.5 × 0.075 ÷ 10 | **0.49** |
| | Vessel Flag | 6.0 | 5.0% | 6.0 × 0.050 ÷ 10 | **0.30** |
| **Party** | Shipper Age (2mo) | **9.0** | **8.8%** | **9.0 × 0.088 ÷ 10** | **0.79** |
| | Prior Violations | 0.0 | 7.5% | 0.0 × 0.075 ÷ 10 | **0.00** |
| | OFAC/Sanctions | 1.5 | 5.0% | 1.5 × 0.050 ÷ 10 | **0.08** |
| **Corridor** | CN→US Baseline | 8.5 | 10.0% | 8.5 × 0.100 ÷ 10 | **0.85** |
| **Pattern (ML)** | **Transshipment (LGB)** | **0.0** | **5.0%** | **0.0 × 0.050 ÷ 10** | **0.00** |
| **Time Sensitivity** | Pre-Tariff Timing | 3.0 | 5.0% | 3.0 × 0.050 ÷ 10 | **0.15** |
| | | | | **SUBTOTAL** | **6.52** |

---

## STEP 2: Factor-Level Summary

**TABLE 2: Factor Aggregation**

| Factor | Components | Subtotal | % of Score | Status |
|--------|-----------|----------|-----------|--------|
| Documentation | 3 | 1.49 | 22.8% | ⚠️ HIGH (Element 9) |
| Commodity | 3 | 0.50 | 7.7% | 🟢 LOW (no exotic goods) |
| Routing | 3 | 1.68 | 25.7% | 🔴 CRITICAL (dwell anomaly) |
| Party | 3 | 0.87 | 13.3% | 🔴 CRITICAL (new shipper) |
| Corridor | 1 | 0.85 | 13.0% | ⚠️ HIGH (CN→US) |
| Pattern | 1 | 0.00 | 0.0% | 🟢 LOW (direct routing pattern) |
| Time Sensitivity | 1 | 0.15 | 2.3% | 🟢 LOW |
| | **TOTAL** | **6.52** | **100%** | |

---

## STEP 3: Apply Adjustments (Corroboration)

**TABLE 3: Adjustment Logic**

| Adjustment Type | Condition | Points | Trigger | Reason |
|-----------------|-----------|--------|---------|--------|
| **Corroboration Bonus** | ISF Mismatch AND Dwell Anomaly detected | +10 | ✅ TRUE | Multiple red flags align |
| **AIS Corroboration** | Dwell Anomaly AND Documentary Risk (ISF) | +15 | ✅ TRUE | Vessel tracking confirms concealment |
| **Party Escalation** | New Shipper (< 12mo) AND High Corridor Risk | +5 | ✅ TRUE | Elevated risk due to unknown entity |
| **Corridor Adjustment** | AD/CVD Applicable × 1.15 multiplier | +0.98 | ✅ TRUE | Tariff evasion incentive |
| | | | **TOTAL ADJUSTMENTS** | **+30.98** |

---

## STEP 4: Initial Score Calculation

```
Subtotal (from TABLE 2):           6.52
Adjustments (from TABLE 3):       +30.98
────────────────────────────────────────
PRELIMINARY SCORE:                37.50

Apply Calibration Multiplier (×1.2): 45.00
Apply Ceiling (cap at 100):          45.00
────────────────────────────────────────
INITIAL RISK SCORE:               45.00
```

---

## STEP 5: ALTANA API INVOCATION LOGIC

**Decision Point: Is Initial Score >= 70?**

```
45.00 >= 70? NO → Altana NOT invoked (stub response = CLEAR)
```

### IF Score >= 70: Altana Validation Flow

```
┌──────────────────────────────────────┐
│  INITIAL_SCORE >= 70?                │
└──────────────────────────────────────┘
            │
            ├─ YES → INVOKE ALTANA
            │         │
            │         ├─ Input: shipment_id, shipper, origin_country, hs_code, declared_value, model_score
            │         │
            │         └─ Output (STUB):
            │             {
            │               "confidence": 0.92,
            │               "recommendation": "HOLD_FOR_EXAMINATION",
            │               "risk_factors": ["supply_chain_opacity", "sanctions_exposure"],
            │               "supply_chain_opacity": 65,
            │               "sanctions_exposure": false
            │             }
            │
            └─ NO → Skip Altana (confidence = 0)
```

### Example: If Score WAS 85 (Shanghai with all corroboration bonuses)

**TABLE 4: Altana Decision Logic**

| Scenario | Initial Score | Altana Confidence | Recommendation | Adjustment | Final Score |
|----------|--------------|-------------------|-----------------|------------|------------|
| **Scenario A** | 85 | 92% (HIGH) | HOLD_FOR_EXAMINATION | +5 points | **90** |
| | | | *Altana strongly agrees supply chain is risky* | | |
| **Scenario B** | 85 | 75% (MEDIUM) | REVIEW | +2 points | **87** |
| | | | *Altana partially validates risk* | | |
| **Scenario C** | 85 | 62% (LOW) | CLEAR | -8 points | **77** |
| | | | *Altana disputes - supply chain verified* | | |

### Current Case (SHP-163679): Altana Not Invoked

```
INITIAL SCORE: 45.00
├─ Is >= 70? NO
├─ Altana Query: FALSE
├─ Altana Confidence: 0%
├─ Model Adjustment: 0 points
└─ FINAL RISK SCORE: 45.00
```

---

## STEP 6: FINAL SCORE DERIVATION

**TABLE 5: Complete Calculation Ledger**

| Step | Calculation | Value | Notes |
|------|-----------|-------|-------|
| 1 | Documentation (3 components) | 1.49 | Element 9 mismatch = 1.08 |
| 2 | Commodity (3 components) | 0.50 | Low exposure, no export control |
| 3 | Routing (3 components + ML) | 1.68 | **Isolation Forest: dwell = 9/10** |
| 4 | Party (3 components) | 0.87 | **Shipper age 2 months = HIGH** |
| 5 | Corridor (baseline) | 0.85 | CN→US multiplier 1.30x |
| 6 | Pattern (ML) | 0.00 | LightGBM: direct routing |
| 7 | Time Sensitivity | 0.15 | No pre-tariff timing pressure |
| | **Component Subtotal** | **6.52** | Sum of all weighted components |
| 8 | Corroboration Bonuses | +30.98 | ISF + Dwell + Party alignment |
| 9 | Corridor Adjustment | +0.98 | AD/CVD tariff incentive |
| | **Pre-Calibration Total** | **38.48** | |
| 10 | Calibration Multiplier (×1.2) | 46.18 | ML model calibration |
| 11 | Ceiling (max 100) | 46.18 | Capped at 100 |
| 12 | **Altana Adjustment** | **0** | Score < 70, Altana skipped |
| | | **FINAL RISK SCORE** | **46.2/100** | |

---

## STEP 7: Audit Trail for Transparency

**TABLE 6: Complete Audit Trail**

| Field | Value | Explanation |
|-------|-------|-------------|
| shipment_id | SHP-163679 | Shanghai Trade Co. |
| initial_score | 46.2 | After calibration |
| altana_query | FALSE | Score < 70 threshold |
| altana_confidence | 0% | N/A - not queried |
| altana_response | STUB: CLEAR | Mock response (score too low) |
| model_adjustment | 0 points | Altana did not adjust |
| final_risk_score | **46.2/100** | **MEDIUM-ELEVATED RISK** |
| adjustment_reason | "Initial model assessment" | No Altana adjustment |
| confidence_interval | ±2.5 | ML model uncertainty |
| recommended_action | REVIEW | For further investigation |
| timestamp | 2026-05-24T22:45:32Z | Calculation timestamp |

---

## RISK LEVEL CLASSIFICATION

```
Final Score: 46.2/100
├─ 0-40:   LOW RISK           🟢 (Allow clear)
├─ 40-70:  MEDIUM-ELEVATED    🟡 (Review & EXAMINE if > 60)
├─ 70-85:  CRITICAL           🔴 (HOLD - invoke Altana validation)
└─ 85-100: EXTREME            🔴🔴 (SEIZE - with Altana verification)

Current Case: 🟡 MEDIUM-ELEVATED → Recommend: REVIEW
```

---

## TRANSPARENCY FEATURES FOR REFERRAL PACKAGE

All tables above (1-6) should appear in the referral package PDF/view with:

✅ **TABLE 3-12A: Component Scoring**
✅ **TABLE 3-12B: Factor Summary**  
✅ **TABLE 3-12C: Adjustment Logic**
✅ **TABLE 3-12D: Altana Decision Flow**
✅ **TABLE 3-12E: Calculation Ledger**
✅ **TABLE 3-12F: Audit Trail**

Each table shows:
- Individual component scores and how they're calculated
- Weights and weighted results
- Adjustments and bonuses
- **When Altana is invoked (>= 70 threshold)**
- **How Altana adjustments modify the score**
- Final score with full reasoning

---

## Example: If Shanghai Trade Co. HAD Score >= 70

**Hypothetical High-Risk Scenario:**

```
If ALL corroboration bonuses applied:
Subtotal:                6.52
Corroboration (+10):    +10.00
AIS-Doc Corroboration (+15): +15.00
Party Escalation (+5):   +5.00
Corridor Adj (+0.98):    +0.98
────────────────────────────
Pre-Calibration:        37.48
Calibration ×1.2:       44.98
────────────────────────────
INITIAL SCORE:          44.98

[IF this were 80+ instead...]

ALTANA INVOCATION:
├─ POST /altana/validate_shipment
├─ Payload: {shipment_id, shipper, origin_country, hs_code, declared_value, model_score: 80+}
├─ Response (STUB):
│  {
│    "confidence": 0.92,
│    "recommendation": "HOLD_FOR_EXAMINATION",
│    "risk_factors": ["supply_chain_opacity"],
│    "supply_chain_opacity": 70,
│    "sanctions_exposure": false
│  }
│
├─ Confidence > 85%? YES
├─ Recommendation = HOLD_FOR_EXAMINATION? YES
│
└─ ADJUSTMENT: +5 points (Altana validates high-risk assessment)
   FINAL SCORE: 80 + 5 = 85/100 🔴 CRITICAL

│ AUDIT TRAIL:
│ ├─ altana_query: TRUE
│ ├─ altana_confidence: 92%
│ ├─ model_adjustment: +5
│ └─ adjustment_reason: "Altana validated high supply chain risk"
```

---

## KEY TAKEAWAYS

1. **ML Models Integrated**:
   - ✅ Isolation Forest: Detects AIS anomalies (dwell, cost spikes)
   - ✅ LightGBM: Classifies transshipment patterns
   - ✅ Scoring engine uses ML predictions as component inputs

2. **Transparency in Action**:
   - Every component score is visible and explained
   - Weights are explicit (e.g., Element 9 = 11.4% of doc risk)
   - Adjustments are labeled with triggers and reasons
   - Calculation steps shown in full ledger

3. **Altana Integration**:
   - **Threshold**: Invoked only when initial_score >= 70
   - **Input**: Shipment details + model score
   - **Output**: Confidence, recommendation, risk factors
   - **Impact**: Adjusts final score by ±5 to ±15 points based on confidence
   - **Current Case**: Score 46 → Altana not needed (stub = CLEAR)

4. **Referral Package**:
   - Displays all 6 tables with full calculations
   - Shows when Altana was/would be invoked
   - Explains every point adjustment
   - Officer can trace reasoning from shipment → final recommendation
