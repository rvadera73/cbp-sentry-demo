# Generalized Risk Scoring Engine Framework

**Status**: Architecture Design (Ready for Implementation)  
**Date**: June 12, 2026  
**For**: CBP Sentry (CBP Illegal Transshipment, FDA Imports Fraud, Opioid Detection)

---

## Executive Summary

A **single extensible framework** supporting multiple risk domains via configurable scorecards. Rules are versioned, parameters are tunable by analysts, Gemini suggests regulatory translations, and governance is optional.

**Storage**: DuckDB (local) + MotherDuck (managed free tier fallback)  
**Multi-Analyst**: Optimistic concurrency (no locks, conflict detection)  
**Governance**: Default superuser, optional approval workflows

---

## 1. Core Architecture

### 1.1 Data Model (Three-Table Pattern)

```sql
-- Table 1: SCORECARD DEFINITIONS (Git-versioned, rarely changes)
CREATE TABLE scorecards (
  scorecard_id STRING PRIMARY KEY,          -- "cbp_illegal_transshipment_v1", "fda_imports_fraud_v1"
  domain STRING,                            -- "cbp", "fda", "opioid_detection"
  version INT,                              -- Semantic: 1, 2, 3 (changed via code review)
  factors JSON,                             -- [{id: "DOCUMENTATION_RISK", weight: 0.25, sources: [...], horizon: "H1"}, ...]
  thresholds JSON,                          -- {gate1: {score: 30, action: "auto_review"}, ...}
  rules JSON,                               -- [{ruleId: "W-121", priority: 1, appliesToGates: ["gate1", "gate2"]}, ...]
  activated_at TIMESTAMP,
  description STRING,
  created_by STRING,
  git_commit_sha STRING                     -- Links to code repo for audit
);

-- Table 2: RULE PARAMETERS (Analysts tune these daily)
CREATE TABLE rule_parameters (
  rule_id STRING NOT NULL,                  -- "W-121", "UFLPA-301", etc.
  parameter_name STRING NOT NULL,           -- "weight", "enabled", "threshold"
  parameter_value DECIMAL/STRING,           -- 1.0, true, 75
  version INT NOT NULL,                     -- Incremented on each change
  valid_from TIMESTAMP NOT NULL,            -- SCD Type 2: when this version became active
  valid_to TIMESTAMP,                       -- SCD Type 2: when it was superseded
  is_current BOOLEAN DEFAULT true,          -- Fast query for active parameters
  analyst_id STRING,                        -- Who made the change
  reason STRING,                            -- Why (e.g., "Q1 fraud spike adjustment")
  PRIMARY KEY (rule_id, parameter_name, valid_from)
);

-- Table 3: RULE_CHANGE_EVENTS (Immutable audit log, append-only)
CREATE TABLE rule_change_events (
  event_id INT GENERATED ALWAYS AS IDENTITY,
  rule_id STRING NOT NULL,
  parameter_name STRING NOT NULL,
  old_value ANY,
  new_value ANY,
  analyst_id STRING NOT NULL,
  reason STRING,
  approval_status STRING,                   -- "pending", "approved", "rejected"
  approved_by STRING,
  approval_timestamp TIMESTAMP,
  created_at TIMESTAMP DEFAULT NOW(),
  environment STRING                        -- "DEV", "STAGING", "PROD"
);
```

### 1.2 Key Separation: Rules vs Parameters

**RULES** (Stored in Git, Quarterly Changes):
```yaml
# v2.rules.yaml (in code repo)
rules:
  W-121:
    name: "UNVERIFIED_RELEGATED_IMPORTER"
    condition: "importer_shipper_relationship == 'unverified' AND shipper_age_days < 90"
    base_risk_points: 25
    horizon: "H1"  # Proven, stable
    domain: "cbp"

  UFLPA-301:
    name: "UFLPA_RECLASSIFICATION"
    condition: "commodity_origin IN ['CN', 'VN'] AND hs_code LIKE '6204%'"
    base_risk_points: 35
    horizon: "H1"
    domain: "cbp"

  PATTERN_ANOMALY:
    name: "ML_PATTERN_DETECTION"
    condition: "ml_score > threshold AND confidence > 0.85"
    base_risk_points: 0  # ML score itself is the input
    horizon: "H3"  # Experimental, shadow mode only
    domain: "cbp"
```

**PARAMETERS** (Tunable via UI, versioned in DuckDB):
```json
{
  "rule_id": "W-121",
  "parameters": {
    "weight": 1.0,              // Multiply base_risk_points by this
    "enabled": true,            // Can disable rule without code change
    "threshold": null,          // Only apply if total_score > X
    "corridor_override": {      // Domain-specific adjustment
      "CN→US": 1.5,
      "VN→US": 1.2,
      "CA→US": 0.9
    }
  },
  "version": 3,
  "valid_from": "2026-03-15T16:00:00Z",
  "valid_to": null,
  "is_current": true
}
```

---

## 2. Three Use Cases (Scorecards)

### 2.1 CBP Illegal Transshipment (Existing)

```json
{
  "scorecard_id": "cbp_illegal_transshipment_v1",
  "domain": "cbp",
  "factors": [
    {
      "id": "DOCUMENTATION_RISK",
      "weight": 0.25,
      "sources": ["manifest_completeness", "isf_validation"],
      "horizon": "H1"
    },
    {
      "id": "ROUTING_RISK",
      "weight": 0.15,
      "sources": ["ais_patterns", "port_anomalies"],
      "horizon": "H1"
    },
    {
      "id": "COMMODITY_RISK",
      "weight": 0.15,
      "sources": ["hs_code_validation", "tariff_history"],
      "horizon": "H1"
    },
    {
      "id": "CORRIDOR_RISK",
      "weight": 0.20,
      "sources": ["country_pair_risk", "corridor_history"],
      "horizon": "H2"  // Emerging, monthly review
    },
    {
      "id": "PARTY_RISK",
      "weight": 0.15,
      "sources": ["ofac_screening", "shipper_age", "violation_history"],
      "horizon": "H1"
    },
    {
      "id": "PATTERN_RISK",
      "weight": 0.10,
      "sources": ["ml_anomaly_detection"],
      "horizon": "H3"  // Experimental, shadow only
    },
    {
      "id": "TIME_SENSITIVITY",
      "weight": 0.10,
      "sources": ["tariff_timing", "seasonal_anomaly"],
      "horizon": "H2"
    }
  ],
  "thresholds": {
    "gate1": { "score": 30, "action": "auto_review", "horizon": "H1" },
    "gate2": { "score": 60, "action": "escalate_to_analyst", "horizon": "H1" },
    "gate3": { "score": 80, "action": "hold_shipment", "horizon": "H1" }
  },
  "rules": [
    { "ruleId": "W-121", "priority": 1, "appliesToGates": ["gate1", "gate2"] },
    { "ruleId": "W-822", "priority": 2, "appliesToGates": ["gate2", "gate3"] },
    { "ruleId": "UFLPA-301", "priority": 3, "appliesToGates": ["gate3"] }
  ]
}
```

### 2.2 FDA Imports Fraud (New)

```json
{
  "scorecard_id": "fda_imports_fraud_v1",
  "domain": "fda",
  "factors": [
    {
      "id": "IMPORTER_LEGITIMACY",
      "weight": 0.30,
      "sources": ["fda_registrations", "prior_violations", "facility_inspection_history"],
      "horizon": "H1"
    },
    {
      "id": "PRODUCT_COMPLIANCE",
      "weight": 0.25,
      "sources": ["labeling_analysis", "ingredient_verification", "microbial_testing"],
      "horizon": "H1"
    },
    {
      "id": "SUPPLY_CHAIN_INTEGRITY",
      "weight": 0.20,
      "sources": ["supplier_verification", "traceability_data"],
      "horizon": "H2"
    },
    {
      "id": "COUNTERFEITING_RISK",
      "weight": 0.15,
      "sources": ["packaging_analysis", "serial_number_validation"],
      "horizon": "H2"
    },
    {
      "id": "SELLER_REPUTATION",
      "weight": 0.10,
      "sources": ["complaints", "recalls", "market_data"],
      "horizon": "H1"
    }
  ],
  "thresholds": {
    "gate1": { "score": 40, "action": "enhanced_inspection", "horizon": "H1" },
    "gate2": { "score": 70, "action": "escalate_to_compliance_officer", "horizon": "H1" }
  },
  "rules": [
    { "ruleId": "FDA-RECALL-MATCH", "priority": 1, "appliesToGates": ["gate2"] },
    { "ruleId": "FDA-UNREGISTERED-IMPORTER", "priority": 2, "appliesToGates": ["gate1"] }
  ]
}
```

### 2.3 Opioid Detection (New)

```json
{
  "scorecard_id": "opioid_detection_v1",
  "domain": "opioid",
  "factors": [
    {
      "id": "PRESCRIPTION_VOLUME",
      "weight": 0.25,
      "sources": ["pill_count", "ndc_code", "patient_demographics"],
      "horizon": "H1"
    },
    {
      "id": "PRESCRIBER_PATTERN",
      "weight": 0.25,
      "sources": ["prescriber_license_verification", "specialty_mismatch"],
      "horizon": "H1"
    },
    {
      "id": "PATIENT_BEHAVIOR",
      "weight": 0.20,
      "sources": ["multiple_prescriber_visits", "pharmacy_hopping"],
      "horizon": "H1"
    },
    {
      "id": "PHARMACY_NETWORK",
      "weight": 0.15,
      "sources": ["chain_vs_independent", "inspection_history"],
      "horizon": "H2"
    },
    {
      "id": "DIVERSION_SIGNALS",
      "weight": 0.15,
      "sources": ["dea_watch_list", "lost_theft_reports"],
      "horizon": "H1"
    }
  ],
  "thresholds": {
    "gate1": { "score": 50, "action": "report_to_dea", "horizon": "H1" },
    "gate2": { "score": 75, "action": "block_prescription", "horizon": "H1" }
  },
  "rules": [
    { "ruleId": "DEA-FLAGGED-PRESCRIBER", "priority": 1, "appliesToGates": ["gate2"] },
    { "ruleId": "VOLUME-SPIKE-DETECTION", "priority": 2, "appliesToGates": ["gate1"] }
  ]
}
```

---

## 3. Multi-Analyst Parameter Tuning (No Locks)

### 3.1 Optimistic Concurrency Pattern

Analysts work simultaneously without blocking each other:

```
Analyst A                          Analyst B
├─ Fetch W-121 (version: 5)
│  weight: 1.0
│
├─ Adjust weight: 1.0 → 1.2
│  (thinks about margin impact)
│
├─ Submit update with version: 5
│  
└─ SUCCESS
   version incremented to 6
                                   ├─ Fetch W-121 (version: 5)
                                   │  weight: 1.0
                                   │
                                   ├─ Adjust weight: 1.0 → 0.9
                                   │  (thinks about false positive rate)
                                   │
                                   ├─ Submit update with version: 5
                                   │
                                   └─ CONFLICT DETECTED
                                      Expected version: 5
                                      Found version: 6
                                      → "Rule was modified by Analyst A 2 min ago"
                                      → Analyst B refreshes and retries
```

**Implementation (DuckDB)**:

```sql
-- Update with version check (prevents lost updates)
UPDATE rule_parameters
SET parameter_value = 1.2,
    version = 6,
    valid_to = NOW(),
    is_current = false
WHERE rule_id = 'W-121'
  AND parameter_name = 'weight'
  AND version = 5              -- ← This check prevents conflicts
RETURNING *;

-- If version != 5, UPDATE returns 0 rows → conflict
-- Analyst refreshes and sees version=6 (Analyst A's change)
```

### 3.2 SCD Type 2 History (Temporal Queries)

"What was W-121's weight on March 15?"

```sql
SELECT parameter_value
FROM rule_parameters
WHERE rule_id = 'W-121'
  AND parameter_name = 'weight'
  AND valid_from <= '2026-03-15'::timestamp
  AND (valid_to IS NULL OR valid_to > '2026-03-15'::timestamp);
```

---

## 4. Gemini Rule Suggestion Flow

### 4.1 Analyst → Regulatory Document → Gemini → Suggested Rule

**Workflow**:

```
Analyst uploads PDF (e.g., "49 CFR 19.html")
    ↓
Gemini extracts policy sections with context
    ↓
"Generate rule for: 'Importers must verify shipper age >= 90 days'"
    ↓
Gemini suggests:
  {
    "rule_id": "W-121-AUTO",
    "name": "UNVERIFIED_RELEGATED_IMPORTER",
    "condition": "shipper_age_days < 90 AND shipper_shipper_relationship_type == 'unverified'",
    "base_risk_points": 25,
    "horizon": "H1",
    "confidence": 0.92,
    "policy_reference": "49 CFR 19.2(a)",
    "requires_manual_validation": true
  }
    ↓
Analyst reviews, adjusts condition if needed
    ↓
Analyst approves → Rule goes to rule_parameters table
    ↓
Next analyst tuning session: can adjust weight/threshold/corridor_override
```

### 4.2 Implementation (UI Component)

```typescript
// GeminiRuleSuggestion.tsx
const SuggestRuleFromPolicy = async (policyFile: File) => {
  const text = await policyFile.text();
  
  const suggestion = await fetch('/api/gemini/suggest-rule', {
    method: 'POST',
    body: JSON.stringify({
      policy_text: text,
      domain: 'cbp',
      existing_rules: await fetchExistingRules()
    })
  });

  // Show suggestion to analyst for approval
  return suggestion.json();
};
```

---

## 5. Governance (Optional, Default Superuser)

### 5.1 Default Mode: Superuser Bypass

```
Analyst submits parameter change
    ↓
If analyst is SUPERUSER:
  ├─ Change applied immediately
  ├─ Event logged to audit trail
  └─ Done (no approval needed)
```

### 5.2 Optional Approval Workflow

```
Analyst submits parameter change
    ↓
If governance_enabled for this rule/domain:
  ├─ Change goes to "pending" approval_status
  ├─ Notifies approvers (manager, compliance officer)
  ├─ If approved:
  │  ├─ approved_by = approver_id
  │  └─ approval_timestamp = NOW()
  ├─ If rejected:
  │  └─ Change reverted, reason logged
  └─ Governance audit trail maintained
```

**Configuration** (per domain/rule):

```json
{
  "rule_id": "UFLPA-301",
  "governance": {
    "enabled": true,
    "required_approvers": ["compliance_officer", "manager"],
    "approval_sla_hours": 4,
    "escalation_on_timeout": "cpo@cbp.gov"
  }
}
```

---

## 6. Implementation Roadmap

### Phase 1: Foundation (Weeks 1-3)

**Goal**: Single analyst can tune parameters for CBP

- [ ] DuckDB schema + SCD Type 2 setup
- [ ] Flask API: GET/POST `/api/rules/{rule_id}/parameters`
- [ ] V2AITuningPage refactored: load factors from scorecard config instead of hardcoded
- [ ] Optimistic concurrency validation
- [ ] Audit trail: all changes logged to rule_change_events
- [ ] Local testing: DuckDB file-based

**Deliverable**: Analyst can adjust W-121 weight, refresh V2AITuningPage, see history

### Phase 2: Multi-Analyst + Gemini (Weeks 4-6)

**Goal**: Multiple analysts work simultaneously; Gemini suggests rules

- [ ] Conflict detection + UI feedback ("modified by another analyst")
- [ ] Temporal query: "show me parameters on date X"
- [ ] Gemini integration: `/api/gemini/suggest-rule`
- [ ] Rule suggestion UI component
- [ ] Audit trail with analyst_id, reason, approval status
- [ ] Test concurrent edits (analyst A updates, analyst B gets conflict)

**Deliverable**: 2-3 analysts can tune rules; Gemini can convert "49 CFR 19 says X" → rule suggestion

### Phase 3: Three Domains (Weeks 7-9)

**Goal**: FDA Imports Fraud, Opioid Detection scorecards active

- [ ] Create scorecard configs for FDA, Opioid
- [ ] V2AITuningPage dynamically load factors from active scorecard
- [ ] Test: switch between CBP, FDA, Opioid scorecards
- [ ] Each domain has independent rule set, weight history

**Deliverable**: Superuser can select domain, analysts tune domain-specific parameters

### Phase 4: Governance + Managed DB (Weeks 10-12)

**Goal**: Optional governance workflows; production deployment

- [ ] Governance approval workflow (optional)
- [ ] MotherDuck Starter (free tier) setup
- [ ] Daily snapshot: DuckDB local → MotherDuck
- [ ] Blue-green deployment (zero-downtime rule rollback)
- [ ] Dashboard: rule change history, audit trail, concurrent edit metrics

**Deliverable**: Governance optional but available; rules can be rolled back in <1 second

---

## 7. V2AITuningPage Integration

### Current State (Hardcoded)

```typescript
// V2AITuningPage.tsx (line 40-48)
const FACTOR_META: Record<string, { label: string; color: string }> = {
  DOCUMENTATION_RISK: { ... },
  CORRIDOR_RISK: { ... },
  // ... all 7 hardcoded
};
```

### New State (Parameterized)

```typescript
// V2AITuningPage.tsx (refactored)
const [activeScorecard, setActiveScorecard] = useState<Scorecard>('cbp_illegal_transshipment_v1');
const [factorMetadata, setFactorMetadata] = useState<Record<string, any>>({});

useEffect(() => {
  // Load scorecard config from API
  const scorecard = await fetch(`/api/scorecards/${activeScorecard}`).then(r => r.json());
  
  // Dynamically build FACTOR_META from scorecard.factors
  setFactorMetadata(
    Object.fromEntries(
      scorecard.factors.map(f => [
        f.id,
        { label: f.id, sources: f.sources, horizon: f.horizon }
      ])
    )
  );
}, [activeScorecard]);

// ModelWeights tab now gets factors from scorecard, not hardcoded
```

**Change**: V2AITuningPage becomes **domain-agnostic**. Same UI works for CBP, FDA, Opioid by switching scorecard.

---

## 8. Storage Comparison

### Local Development (Free)

```bash
# DuckDB file-based (no server needed)
$ duckdb /tmp/risk_engine.duckdb

# Load schema
$ duckdb < schema.sql

# Test concurrent edits locally
$ python test_concurrent_updates.py
```

**Cost**: $0  
**Setup**: 5 minutes  
**Backup**: `cp /tmp/risk_engine.duckdb /backup/`

### Production (Free/Cheap)

**Option A: MotherDuck Starter (Free)**
```bash
$ export MOTHERDUCK_TOKEN=your_token
$ python -c "import duckdb; db = duckdb.sql('SELECT * FROM memory.my_table')"
```
- Free tier: 125 GB storage, included compute
- If usage exceeds: ~$0.50 per GB/month
- For 12 months of audit trail (1.8 MB): negligible cost

**Option B: Firestore Fallback (Free if light usage)**
- Free tier: 1 GB storage, 50K reads/day
- For rule parameters (likely <10K reads/day): $0
- Audit trail stored separately (append-only, cheaper)

---

## 9. Key Design Decisions

| Decision | Why | Trade-off |
|----------|-----|-----------|
| **DuckDB (not SQLite)** | SCD Type 2 versioning, columnar compression, temporal queries | Single writer (safe for 2-10 analysts) |
| **Scorecard config in Git** | Immutable rule definitions, code review, version control | Rules changes require code PR; parameters tuning is fast |
| **Parameters in DuckDB** | Fast versioning, ACID, multi-analyst safe, no deployment needed | Requires separate storage from rules |
| **Gemini suggestions (not generation)** | Suggests based on policy, analyst approves | Still manual; not fully automated |
| **Optimistic concurrency** | No locks, fast response, explicit conflict feedback | Analyst must refresh if conflict detected |
| **Governance optional** | Default is fast (superuser deploys), can add approval layer | Requires discipline to not abuse superuser |
| **Three scorecards (not three schemas)** | Single engine scales to any number of domains | Must ensure factors/thresholds design is generic |

---

## 10. Execution Checklist

- [ ] Create DuckDB schema (scorecards, rule_parameters, rule_change_events)
- [ ] Write Flask API routes for parameter CRUD + conflict detection
- [ ] Refactor V2AITuningPage to load factors from scorecard config
- [ ] Implement Gemini suggestion endpoint
- [ ] Add SCD Type 2 versioning (valid_from, valid_to, is_current)
- [ ] Test concurrent edits: 2+ analysts updating same rule simultaneously
- [ ] Create FDA Imports Fraud scorecard config
- [ ] Create Opioid Detection scorecard config
- [ ] Document temporal queries ("show parameters on date X")
- [ ] Set up MotherDuck Starter account
- [ ] Create rollback procedure (<1 second revert)

---

## Questions to Confirm

1. **Rule definitions**: Should analysts define new rules via UI (UI builder), or only tune parameters of existing rules (git-defined)?
2. **Governance approval**: Should approval be per-domain (CBP requires approval, FDA doesn't), or per-rule (W-121 requires approval, W-822 doesn't)?
3. **Corridors**: In CBP scorecard, CORRIDOR_RISK has corridor_override multipliers. Should other domains have similar overrides?
4. **Audit retention**: How long to keep rule history? (12 months, 3 years, indefinite?)
5. **Rollback scope**: If a rule change causes high false-positive rate, should rollback be instant (revert parameters) or require analyst confirmation?

---

## Next Steps

1. **This week**: Set up DuckDB schema + basic API
2. **Next week**: Refactor V2AITuningPage + test concurrent edits
3. **Week 3**: Integrate Gemini for rule suggestions
4. **Week 4**: Add FDA/Opioid scorecards
5. **Week 5**: Production deployment to MotherDuck Starter

