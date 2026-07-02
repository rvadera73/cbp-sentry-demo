# CBP Scoring Model Explained (Concrete Example)

**The confusion**: What do "7 factors", "3 horizons", and "3 rules" actually DO when you score a shipment?

---

## Simple Answer

When a shipment arrives at CBP, we ask: **"What's the risk score (0-100)?"**

To answer, we use:

1. **7 Factors** = Seven different risk perspectives we calculate
2. **3 Horizons** = How proven/stable each factor is (affects governance, not calculation)
3. **3 Rules** = Three hard gates that block/escalate before we even calculate factors

---

## Live Example: Scoring a Real Shipment

### Shipment Details
```
Shipment ID: SHP-20260612-001
Origin: China (CN)
Destination: Los Angeles (US)
Importer: ABC Trading LLC (age: 45 days)
Commodities: Textiles (HS Code 6204.62200)
Value: $45,000 USD
Vessel: MSC Algeciras (Flag: Panama)
AIS Status: Silent for 3 days
```

---

## STEP 1: Check Hard Rules (3 Rules)

Before we calculate anything, check if any of these **hard stop rules** apply:

### Rule 1: W-121 "UNVERIFIED RELEGATED IMPORTER"
```
Condition: importer_shipper_relationship == 'unverified' AND shipper_age_days < 90

Check: Is ABC Trading unverified? YES
       Is their age < 90 days? YES (45 days)
       
Result: RULE TRIGGERED ✓
        Add base risk points: 25 (from rule definition)
        Apply parameter: weight = 1.2 (analyst tuned this)
        Final contribution: 25 × 1.2 = 30 points
```

### Rule 2: W-822 "AIS SILENT PATTERN ANOMALY"
```
Condition: vessel_ais_silent_days > 2 AND last_known_location NOT IN standard_routes

Check: AIS silent > 2 days? YES (3 days)
       Last known location normal? NO (unusual routing)
       
Result: RULE TRIGGERED ✓
        Add base risk points: 20
        Apply parameter: weight = 1.0 (default)
        Final contribution: 20 × 1.0 = 20 points
```

### Rule 3: UFLPA-301 "AD/CVD RECLASSIFICATION"
```
Condition: commodity_origin IN ['CN', 'VN'] AND hs_code LIKE '6204%'

Check: Origin is CN? YES
       HS code starts with 6204? YES
       
Result: RULE TRIGGERED ✓
        Add base risk points: 35
        Apply parameter: weight = 0.8 (analyst lowered this)
        Final contribution: 35 × 0.8 = 28 points
```

**Hard Rules Total: 30 + 20 + 28 = 78 points from rules alone**

---

## STEP 2: Calculate 7 Factors (Weighted Score)

The hard rules give us a baseline. Now we calculate the 7 risk factors independently:

### Factor 1: DOCUMENTATION_RISK (Weight: 25%)

```
Question: How complete is the shipment documentation?

Sub-checks:
  ├─ Manifest complete? YES (100%)
  ├─ ISF filed? YES (100%)
  ├─ All elements present? NO (Element 9 missing: 80%)
  └─ Average: (100 + 100 + 80) / 3 = 93%

Calculated Factor Score: 93 / 100 = 0.93 (on 0-1 scale)
                         → 93 (on 0-100 scale)

Contribution to final score: 0.93 × 25% = 23.25 points
```

### Factor 2: ROUTING_RISK (Weight: 15%)

```
Question: Is the shipping route normal or anomalous?

Sub-checks:
  ├─ Port selection normal? Partially (Los Angeles is high-risk port: 60%)
  ├─ Vessel flag suspicious? YES (Panama flag, often linked to evasion: 40%)
  ├─ AIS dwell time? Unusual (silent 3 days: 30%)
  └─ Average: (60 + 40 + 30) / 3 = 43%

Calculated Factor Score: 43 / 100 = 0.43 (low = risky)

Contribution to final score: 0.43 × 15% = 6.45 points
```

### Factor 3: COMMODITY_RISK (Weight: 15%)

```
Question: Is the commodity high-risk?

Sub-checks:
  ├─ HS code high-risk? YES (6204 = women's clothing, high tariff evasion: 80%)
  ├─ Tariff applicability? YES (Section 301 tariffs apply: 75%)
  ├─ Export control status? NO (not controlled: 10%)
  └─ Average: (80 + 75 + 10) / 3 = 55%

Calculated Factor Score: 55 / 100 = 0.55

Contribution to final score: 0.55 × 15% = 8.25 points
```

### Factor 4: CORRIDOR_RISK (Weight: 20%)

```
Question: Is the CN→US corridor high-risk?

Base corridor risk: 1.5x multiplier (from analyst-tuned corridor overrides)

Sub-checks:
  ├─ Country pair (CN→US)? High risk: 85%
  ├─ Trade history? No prior violations: 50%
  ├─ Route frequency? Unusual: 70%
  └─ Average: (85 + 50 + 70) / 3 = 68%

Calculated Factor Score: 68 / 100 = 0.68
Apply corridor multiplier: 0.68 × 1.5 = 1.02 (capped at 1.0)

Contribution to final score: 1.0 × 20% = 20 points
```

### Factor 5: PARTY_RISK (Weight: 15%)

```
Question: How risky are the parties (importer, shipper, etc.)?

Sub-checks:
  ├─ Importer age? Young (45 days: 85% risk)
  ├─ Prior violations? None: 20%
  ├─ OFAC match? NO: 0%
  ├─ Ownership transparency? Unclear: 60%
  └─ Average: (85 + 20 + 0 + 60) / 4 = 41%

Calculated Factor Score: 41 / 100 = 0.41

Contribution to final score: 0.41 × 15% = 6.15 points
```

### Factor 6: PATTERN_RISK (Weight: 10%)

```
Question: Are there ML-detected anomalies?

Sub-checks (ML model):
  ├─ Pricing anomaly? YES (price/unit unusually low: 75%)
  ├─ Weight anomaly? NO (weight normal: 20%)
  ├─ Trade frequency anomaly? YES (unusual pattern for new importer: 80%)
  └─ Average: (75 + 20 + 80) / 3 = 58%

Calculated Factor Score: 58 / 100 = 0.58

Contribution to final score: 0.58 × 10% = 5.8 points
```

### Factor 7: TIME_SENSITIVITY (Weight: 10%)

```
Question: Is the timing suspicious?

Sub-checks:
  ├─ Pre-tariff timing? YES (submitted just before tariff increase: 90%)
  ├─ Seasonal anomaly? NO (normal for season: 30%)
  └─ Average: (90 + 30) / 2 = 60%

Calculated Factor Score: 60 / 100 = 0.60

Contribution to final score: 0.60 × 10% = 6 points
```

**7 Factors Total: 23.25 + 6.45 + 8.25 + 20 + 6.15 + 5.8 + 6 = 75.9 points**

---

## STEP 3: Combine Scores

```
Hard Rules:     78 points (W-121 + W-822 + UFLPA-301)
7 Factors:      75.9 points (weighted sum)
---

METHOD A: Rules OR Factors (take max):
Final Score = MAX(78, 75.9) = 78

METHOD B: Rules THEN Factors (sequential):
Final Score = 78 (rules triggered, factors are secondary validation)

METHOD C: Rules + Factors (additive, capped at 100):
Final Score = MIN(78 + 75.9, 100) = 100 (capped)

CBP uses METHOD B (rules first, decisive)
```

**Using METHOD B (Rules-First):**

```
Final Risk Score = 78 (from hard rules, factors are supporting evidence)
```

---

## STEP 4: Apply Thresholds (3 Gates)

Now we have a score. Where does it fall?

```
Gate 1 (Score ≥ 30):  "Auto-Review"      ✓ TRIGGERED (78 ≥ 30)
Gate 2 (Score ≥ 60):  "Escalate to Analyst" ✓ TRIGGERED (78 ≥ 60)
Gate 3 (Score ≥ 80):  "Hold Shipment"    ✗ NOT triggered (78 < 80)

ACTION: Escalate to analyst for manual review
        (Because score passed gates 1 and 2, but not gate 3)
```

---

## Now: What Are the 3 Horizons?

The 7 factors are grouped by maturity (governance level):

### Horizon 1 (H1): Proven, Stable - Quarterly Review Only
```
├─ DOCUMENTATION_RISK (Weight 25%)
│  └─ Historical data: ✓ Reliable for 3+ years
│     Analyst tuning: Only quarterly reviews allowed
│
├─ ROUTING_RISK (Weight 15%)
│  └─ Historical data: ✓ Reliable for 3+ years
│     Analyst tuning: Only quarterly reviews allowed
│
└─ PARTY_RISK (Weight 15%)
   └─ Historical data: ✓ Reliable for 3+ years
      Analyst tuning: Only quarterly reviews allowed
```

**Impact**: Analysts cannot change these weights freely. Manager approval required.

### Horizon 2 (H2): Emerging, Monitored - Monthly Review
```
├─ CORRIDOR_RISK (Weight 20%)
│  └─ Historical data: ~ 18 months validated
│     Analyst tuning: Can adjust weight/multipliers monthly
│     Governance: Supervisor approval recommended
│
└─ TIME_SENSITIVITY (Weight 10%)
   └─ Historical data: ~ 12 months, depends on tariff changes
      Analyst tuning: Can adjust thresholds monthly
      Governance: Supervisor approval recommended
```

**Impact**: Analysts can experiment more, but with oversight.

### Horizon 3 (H3): Experimental, Shadow - Research Only
```
└─ PATTERN_RISK (Weight 10%)
   └─ Historical data: ~ ML model (untested on new types of fraud)
      Analyst tuning: NOT in production decision yet
      Current use: Shadow scoring only (for research)
      Governance: Senior data scientist approval for any changes
```

**Impact**: Highest governance bar. Not used in actual gate decisions yet.

---

## Putting It All Together

### What Each Number Means

```
"CBP 7 Factor 3 Horizon 3 Rule Framework"

↓ Means ↓

7 FACTORS
├─ DOCUMENTATION_RISK (H1, Weight 25%, score contribution 23 pts)
├─ ROUTING_RISK (H1, Weight 15%, score contribution 6 pts)
├─ COMMODITY_RISK (H1, Weight 15%, score contribution 8 pts)
├─ CORRIDOR_RISK (H2, Weight 20%, score contribution 20 pts)
├─ PARTY_RISK (H1, Weight 15%, score contribution 6 pts)
├─ PATTERN_RISK (H3, Weight 10%, score contribution 6 pts - shadow only)
└─ TIME_SENSITIVITY (H2, Weight 10%, score contribution 6 pts)

3 HORIZONS (Governance levels)
├─ H1: Proven (DOCUMENTATION, ROUTING, PARTY, COMMODITY)
│      └─ Quarterly review, manager approval needed
├─ H2: Emerging (CORRIDOR, TIME_SENSITIVITY)
│      └─ Monthly review, supervisor approval recommended
└─ H3: Experimental (PATTERN_RISK)
       └─ Shadow mode only, no production impact, data scientist approval

3 RULES (Hard gates, checked first)
├─ W-121: UNVERIFIED RELEGATED IMPORTER
│         └─ Condition: age < 90 days AND unverified
│         └─ Adds 25 base points × weight parameter
├─ W-822: AIS SILENT PATTERN ANOMALY
│         └─ Condition: AIS silent > 2 days
│         └─ Adds 20 base points × weight parameter
└─ UFLPA-301: AD/CVD RECLASSIFICATION
              └─ Condition: CN/VN + certain HS codes
              └─ Adds 35 base points × weight parameter

RESULT FOR OUR EXAMPLE:
├─ Hard rules triggered: 3/3 (78 points total)
├─ 7 factors calculated: 75.9 points (supporting evidence)
├─ Final score: 78 (rules are decisive)
├─ Gates passed: Gate1 ✓, Gate2 ✓, Gate3 ✗
└─ Action: Escalate to analyst
```

---

## What V2AITuningPage Controls

```
V2AITuningPage (UI) = Parameter Tuning for Analysts

Tab 1: Model Weights
├─ Slider for DOCUMENTATION_RISK: 25% (locked to H1)
├─ Slider for ROUTING_RISK: 15% (locked to H1)
├─ Slider for COMMODITY_RISK: 15% (locked to H1)
├─ Slider for CORRIDOR_RISK: 20% (H2, can change ±5%)
├─ Slider for PARTY_RISK: 15% (locked to H1)
├─ Slider for PATTERN_RISK: 10% (H3, shadow only, read-only)
└─ Slider for TIME_SENSITIVITY: 10% (H2, can change ±3%)

Tab 2: Screening Rules
├─ Checkbox: W-121 enabled/disabled (default: enabled)
├─ Checkbox: W-822 enabled/disabled (default: enabled)
└─ Checkbox: UFLPA-301 enabled/disabled (default: enabled)

Tab 3: Configuration
├─ Threshold for Gate1: 30 (default)
├─ Threshold for Gate2: 60 (default)
├─ Threshold for Gate3: 80 (default)
├─ Corridor multiplier overrides: CN→US: 1.5x, VN→US: 1.2x, etc.
└─ Calibration multiplier: 1.2x (applied to all scores)

Tab 4: Performance Metrics
└─ Read-only: Shows model accuracy (AUC, precision, recall, F1)
```

**What analysts CAN change:**
- H2 factor weights (monthly)
- Rule toggles (enable/disable rules)
- Corridor multipliers
- Gate thresholds
- Calibration multiplier

**What analysts CANNOT change:**
- H1 factor weights (locked to quarterly review)
- H3 factor (shadow mode, not in decision)
- Rule definitions (must change via Git/code review)
- Factor definitions themselves

---

## The FDA and Opioid Examples

### FDA Imports Fraud
```
5 FACTORS (different from CBP)
├─ IMPORTER_LEGITIMACY (H1, Weight 30%)
├─ PRODUCT_COMPLIANCE (H1, Weight 25%)
├─ SUPPLY_CHAIN_INTEGRITY (H2, Weight 20%)
├─ COUNTERFEITING_RISK (H2, Weight 15%)
└─ SELLER_REPUTATION (H1, Weight 10%)

2 HORIZONS
├─ H1: Proven
└─ H2: Emerging

2 RULES
├─ FDA-RECALL-MATCH: If product in recall database
└─ FDA-UNREGISTERED-IMPORTER: If importer not registered with FDA

2 GATES
├─ Gate1 (≥40): Enhanced inspection
└─ Gate2 (≥70): Escalate to compliance officer
```

### Opioid Detection
```
5 FACTORS (completely different domain)
├─ PRESCRIPTION_VOLUME (H1, Weight 25%)
├─ PRESCRIBER_PATTERN (H1, Weight 25%)
├─ PATIENT_BEHAVIOR (H1, Weight 20%)
├─ PHARMACY_NETWORK (H2, Weight 15%)
└─ DIVERSION_SIGNALS (H1, Weight 15%)

2 HORIZONS
├─ H1: Proven
└─ H2: Emerging

2 RULES
├─ DEA-FLAGGED-PRESCRIBER: If prescriber on DEA watch list
└─ VOLUME-SPIKE-DETECTION: If prescription volume spikes >200%

2 GATES
├─ Gate1 (≥50): Report to DEA
└─ Gate2 (≥75): Block prescription
```

---

## The Key Point

**The framework is generalized because:**

1. **Factors** = Domain-specific (CBP has 7, FDA has 5, Opioid has 5)
2. **Horizons** = Governance maturity (H1/H2/H3 apply to any domain)
3. **Rules** = Domain-specific (CBP has W-121, FDA has FDA-RECALL-MATCH)
4. **Weights + Thresholds + Gates** = Tunable via V2AITuningPage (same UI for all domains)

**One engine, three scorecards.**

