# Risk Scoring Engine Framework - Architecture Diagram

## System Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                         GENERALIZED FRAMEWORK                            │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │ DOMAIN CONFIGURATIONS (Git-Versioned, Immutable)                │   │
│  │                                                                  │   │
│  │  ├─ CBP Illegal Transshipment (v1)                             │   │
│  │  │  ├─ Factors: 7 (DOCUMENTATION_RISK, ROUTING_RISK, ...)    │   │
│  │  │  ├─ Thresholds: 3 gates (30, 60, 80)                       │   │
│  │  │  └─ Rules: W-121, W-822, UFLPA-301                         │   │
│  │  │                                                              │   │
│  │  ├─ FDA Imports Fraud (v1)                                     │   │
│  │  │  ├─ Factors: 5 (IMPORTER_LEGITIMACY, PRODUCT_COMPLIANCE) │   │
│  │  │  ├─ Thresholds: 2 gates (40, 70)                           │   │
│  │  │  └─ Rules: FDA-RECALL-MATCH, FDA-UNREGISTERED-IMPORTER   │   │
│  │  │                                                              │   │
│  │  └─ Opioid Detection (v1)                                      │   │
│  │     ├─ Factors: 5 (PRESCRIPTION_VOLUME, PRESCRIBER_PATTERN) │   │
│  │     ├─ Thresholds: 2 gates (50, 75)                           │   │
│  │     └─ Rules: DEA-FLAGGED-PRESCRIBER, VOLUME-SPIKE-DETECTION│   │
│  │                                                                  │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                    │                                      │
│                                    ↓                                      │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │ RULE EVALUATION ENGINE (Stateless, Language-Agnostic)           │   │
│  │                                                                  │   │
│  │  evaluate_rule(rule_def, entity_data) → risk_points            │   │
│  │                                                                  │   │
│  │  for each rule in active_rules:                                │   │
│  │    if rule.condition(entity_data):                             │   │
│  │      score += rule.base_risk_points * parameter[rule].weight  │   │
│  │                                                                  │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                    │                                      │
│                                    ↓                                      │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │ PARAMETER TUNING LAYER (DuckDB, Multi-Analyst Safe)            │   │
│  │                                                                  │   │
│  │  ┌────────────────────────────────────────────────────────┐   │   │
│  │  │ rule_parameters (SCD Type 2)                           │   │   │
│  │  │                                                         │   │   │
│  │  │ W-121:                                                │   │   │
│  │  │  ├─ weight: 1.0  (v5, valid_from: 2026-03-15)      │   │   │
│  │  │  ├─ enabled: true (v4, valid_from: 2026-03-10)     │   │   │
│  │  │  └─ corridor_override: {...}                         │   │   │
│  │  │                                                         │   │   │
│  │  │ UFLPA-301:                                            │   │   │
│  │  │  └─ weight: 1.2  (v3, valid_from: 2026-03-01)      │   │   │
│  │  │                                                         │   │   │
│  │  │ ✓ Optimistic concurrency: version field prevents       │   │   │
│  │  │   lost updates (analyst A updates v5→v6, analyst B    │   │   │
│  │  │   sees conflict if trying v5→v6)                      │   │   │
│  │  │                                                         │   │   │
│  │  │ ✓ Temporal queries: "what was weight on 2026-03-12?"  │   │   │
│  │  │                                                         │   │   │
│  │  └────────────────────────────────────────────────────────┘   │   │
│  │                                                                  │   │
│  │  ┌────────────────────────────────────────────────────────┐   │   │
│  │  │ rule_change_events (Immutable Audit Log)             │   │   │
│  │  │                                                         │   │   │
│  │  │ event_id | rule_id | old_value | new_value | analyst │   │   │
│  │  │ 1001     | W-121   | 1.0       | 1.2       | alice    │   │   │
│  │  │ 1002     | UFLPA   | 0.8       | 1.2       | bob      │   │   │
│  │  │ 1003     | W-121   | 1.2       | 1.0       | alice    │   │   │
│  │  │                                                         │   │   │
│  │  │ ✓ Append-only: no edits, only new events             │   │   │
│  │  │ ✓ Full audit: who, what, when, why, approval status  │   │   │
│  │  │                                                         │   │   │
│  │  └────────────────────────────────────────────────────────┘   │   │
│  │                                                                  │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                    │                                      │
│                                    ↓                                      │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │ ANALYST UI LAYER (V2AITuningPage Refactored)                   │   │
│  │                                                                  │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │   │
│  │  │ Model        │  │ Screening    │  │ Configuration│         │   │
│  │  │ Weights Tab  │  │ Rules Tab    │  │ Tab          │         │   │
│  │  ├──────────────┤  ├──────────────┤  ├──────────────┤         │   │
│  │  │ DYNAMIC:     │  │ DYNAMIC:     │  │ DYNAMIC:     │         │   │
│  │  │ Load factors │  │ Load rules   │  │ Load config  │         │   │
│  │  │ from active  │  │ from active  │  │ from active  │         │   │
│  │  │ scorecard    │  │ scorecard    │  │ scorecard    │         │   │
│  │  │             │  │             │  │             │         │   │
│  │  │ Analyst      │  │ Analyst      │  │ Analyst      │         │   │
│  │  │ adjusts:     │  │ can:         │  │ adjusts:     │         │   │
│  │  │ • Weights    │  │ • Enable/    │  │ • Thresholds│         │   │
│  │  │ • Sliders    │  │   disable    │  │ • Multiplier│         │   │
│  │  │   → POST to  │  │ • Overrides  │  │ • Triggers  │         │   │
│  │  │   /api/...   │  │   → POST to  │  │   → POST to │         │   │
│  │  │              │  │   /api/...   │  │   /api/...  │         │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘         │   │
│  │                                                                  │   │
│  │  Domain Selector: [CBP ▼] → Refresh all factors                │   │
│  │                                                                  │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                    │                                      │
└────────────────────────────────────┼──────────────────────────────────────┘
                                     │
                    ┌────────────────┼────────────────┐
                    ↓                ↓                ↓
         ┌─────────────────┐ ┌──────────────┐ ┌─────────────┐
         │ LOCAL DEV       │ │ GEMINI       │ │ GOVERNANCE  │
         │ (DuckDB file)   │ │ (Optional)   │ │ (Optional)  │
         │                 │ │              │ │             │
         │ /tmp/risk.db    │ │ "Convert     │ │ Approval    │
         │                 │ │ policy →     │ │ Workflows   │
         │ Schema + data   │ │ rule         │ │             │
         │ in one file     │ │ suggestion"  │ │ Default:    │
         │                 │ │              │ │ Superuser   │
         │ Cost: $0        │ │ Analyst      │ │ bypass      │
         │ Setup: 5 min    │ │ reviews +    │ │             │
         │                 │ │ approves     │ │ Cost: $0    │
         └─────────────────┘ └──────────────┘ └─────────────┘
                    │
         ┌──────────┴──────────┐
         │                     │
         ↓                     ↓
    ┌──────────────────┐ ┌─────────────────┐
    │ PROD: MotherDuck │ │ BACKUP: Firestore
    │ (Starter)        │ │ (If needed)
    │                  │ │
    │ Free tier:       │ │ Free tier:
    │ • 125 GB         │ │ • 1 GB
    │ • Daily snapshot │ │ • 50K reads/day
    │   from local DB  │ │ • CDC sync
    │                  │ │
    │ Cost: $0         │ │ Cost: $0 (light)
    └──────────────────┘ └─────────────────┘
```

---

## Data Flow: Analyst Tuning a Rule

```
Analyst opens V2AITuningPage
    │
    ├─ Selects domain: "CBP Illegal Transshipment"
    │
    ├─ API call: GET /api/scorecards/cbp_illegal_transshipment_v1
    │  ├─ Returns factors: [DOCUMENTATION_RISK (25%), ROUTING_RISK (15%), ...]
    │  └─ Returns rules: [W-121 (enabled), W-822 (enabled), ...]
    │
    ├─ V2AITuningPage renders:
    │  ├─ Model Weights Tab: Shows 7 sliders (factors dynamically loaded)
    │  ├─ Screening Rules Tab: Shows W-121, W-822, UFLPA-301 (dynamic)
    │  └─ Configuration Tab: Thresholds for gate1, gate2, gate3
    │
    ├─ Analyst adjusts: W-121 weight 1.0 → 1.2
    │
    ├─ Analyst clicks "Apply Changes"
    │
    ├─ API call: POST /api/rules/W-121/parameters
    │  {
    │    "parameter_name": "weight",
    │    "new_value": 1.2,
    │    "version": 5,                    // ← Optimistic concurrency check
    │    "analyst_id": "analyst@cbp.gov",
    │    "reason": "Q1 fraud spike adjustment"
    │  }
    │
    ├─ Backend:
    │  ├─ Checks: IF current version == 5 THEN proceed, ELSE conflict
    │  │
    │  ├─ If SUCCESS:
    │  │  ├─ Insert new row in rule_parameters
    │  │  │  (version: 6, valid_from: NOW(), valid_to: null, is_current: true)
    │  │  │
    │  │  ├─ Update old row
    │  │  │  (version: 5, valid_to: NOW(), is_current: false)
    │  │  │
    │  │  └─ Insert event in rule_change_events
    │  │     (rule_id: W-121, old_value: 1.0, new_value: 1.2, analyst: ...)
    │  │
    │  └─ If CONFLICT:
    │     ├─ Return 409 Conflict
    │     └─ Tell analyst: "Rule modified by analyst@cbp.gov at 14:22"
    │
    ├─ UI:
    │  ├─ If success: Show "✓ Saved" + reload factors
    │  └─ If conflict: Show "Refresh and retry" button
    │
    └─ Done
        └─ Change is live immediately
           (No approval needed, superuser mode)
           (If governance enabled: goes to pending until approved)
```

---

## Concurrent Edit Scenario (No Locks)

```
                    Analyst A                  Analyst B
                    (CBP Expert)               (FDA Expert)

                                               
T=0                 Fetch W-121                (working on FDA rules)
                    └─ current version: 5
                    └─ weight: 1.0
                    
                                               
T=30s               Thinking about margin       Thinking about coverage
                    impact...                   rates...
                    
                                               
T=45s               Still adjusting in UI       Fetch UFLPA-301
                    └─ weight slider:           └─ current version: 3
                    1.0 → 1.1 → 1.2             └─ weight: 1.0
                                               
T=60s               Submit: W-121               Still adjusting
                    {version: 5, value: 1.2}   
                    
                    ✓ Success
                    ├─ version incremented: 5 → 6
                    └─ valid_from: T=60s
                    
                                               
T=65s               Reload dashboard            Submit: UFLPA-301
                    └─ See W-121 now            {version: 3, value: 1.1}
                       version 6, weight 1.2
                                               ✓ Success
                                               ├─ version incremented: 3 → 4
                                               └─ valid_from: T=65s
                    
                    
T=90s               Analyst A submits another   Analyst B re-tries old
                    rule: W-822                 submission (cached version 3)
                    {version: 2, value: 0.9}   {version: 3, value: 1.1}
                    
                    ✓ Success                   ✗ CONFLICT
                    └─ version 2 → 3            └─ Expected version: 3
                                                └─ Found version: 4
                    
                                               ├─ UI shows:
                                               │  "Rule modified by Analyst A"
                                               │  "Refresh and retry"
                                               │
                                               └─ Analyst B clicks refresh
                                                  └─ Fetches current state
                                                     (version: 4, value: 1.1)
                                                  └─ Retries submit
                                                     {version: 4, value: 1.15}
                                                  └─ ✓ Success
```

**Key**: No locks, no waiting, **conflict detected and resolved by analyst**. Fast concurrent tuning.

---

## Gemini Suggestion Flow

```
Analyst uploads: "49_CFR_19_ImporterRequirements.pdf"
    │
    ├─ API: POST /api/gemini/suggest-rule
    │  {
    │    "policy_text": "...[extracted from PDF]...",
    │    "domain": "cbp",
    │    "existing_rules": [W-121, W-822, UFLPA-301]
    │  }
    │
    ├─ Gemini Prompt:
    │  "Convert this policy into a rule definition.
    │   Domain: CBP. Existing rules: W-121, W-822, UFLPA-301.
    │   Return JSON with:
    │   - rule_id (unique)
    │   - condition (executable logic)
    │   - base_risk_points (0-100)
    │   - horizon (H1/H2/H3)
    │   - confidence (0.0-1.0)"
    │
    ├─ Gemini returns:
    │  {
    │    "rule_id": "W-124-SUGGESTED",
    │    "name": "REPEATED_DIVERSION_INDICATOR",
    │    "condition": "shipment_origin IN ['CN','VN'] AND 
    │                  vessel_registration_country != shipment_origin AND
    │                  port_of_discharge NOT IN standard_ports",
    │    "base_risk_points": 30,
    │    "horizon": "H2",
    │    "confidence": 0.87,
    │    "policy_reference": "49 CFR 19.3(b)",
    │    "requires_manual_validation": true
    │  }
    │
    ├─ UI shows suggestion card:
    │  ┌─────────────────────────────────────────┐
    │  │ GEMINI SUGGESTION (Confidence: 87%)     │
    │  │                                         │
    │  │ Rule: REPEATED_DIVERSION_INDICATOR      │
    │  │ Condition: shipment_origin IN ['CN'... │
    │  │ Risk Points: 30                         │
    │  │ Horizon: H2 (Emerging)                  │
    │  │ Policy Ref: 49 CFR 19.3(b)             │
    │  │                                         │
    │  │ [✓ Approve] [✗ Reject] [Edit Condition]│
    │  └─────────────────────────────────────────┘
    │
    ├─ Analyst reviews, possibly edits condition
    │
    ├─ Analyst clicks [✓ Approve]
    │
    ├─ Rule added to v2.rules.yaml (in Git)
    │  └─ Requires code review before merge
    │
    ├─ Once merged, rule appears in V2AITuningPage:
    │  └─ Screening Rules Tab → W-124 (new)
    │
    └─ Analyst can now tune parameters:
       └─ W-124 weight, enabled/disabled, corridor overrides
```

---

## Storage Timeline

```
Week 1: Local DuckDB setup
├─ Create schema
├─ Test concurrent edits locally
└─ Cost: $0

Week 2-4: Single analyst tuning
├─ Flask API for parameter CRUD
├─ V2AITuningPage refactored
├─ Gemini integration
└─ Cost: $0

Week 5-8: Multi-analyst production
├─ Deploy to MotherDuck Starter (free)
├─ Daily backup to Firestore (optional)
├─ Governance workflows (optional)
└─ Cost: $0-50/month

Month 2+: Scaling (if needed)
├─ MotherDuck scales to $250+/month
├─ Or switch to Firestore ($500+/month)
├─ Three domains live (CBP, FDA, Opioid)
└─ Cost: $0 (free tier covers 12K+ daily requests)
```

