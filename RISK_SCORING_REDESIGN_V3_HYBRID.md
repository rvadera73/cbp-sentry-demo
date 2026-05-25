# Risk Scoring Redesign V3 — Hybrid Caching with JSON + Change History

## Core Insight: JSON is Fine, Model Versioning is the Staleness Trigger

**Why JSON Works:**
- ✓ Complete calculation snapshot (immutable point-in-time record)
- ✓ Self-contained (no need to reconstruct from components)
- ✓ Analytics can use JSON functions (PostgreSQL `->`, MongoDB `.`)
- ✓ Change history easy (compare old vs new JSON)
- ✓ NoSQL-ready (can be MongoDB or DynamoDB)

**Staleness Trigger (NOT time, NOT events):**
- Score becomes stale when **ML model version changes**
- If no model tuning → no staleness
- If model retrained → mark all scores with old model version as stale

---

## Schema Design: Simple + Powerful

### Table 1: **risk_scores_cache** (The Cached Score - JSON)
```sql
CREATE TABLE risk_scores_cache (
  id TEXT PRIMARY KEY,
  shipment_id TEXT UNIQUE NOT NULL,
  
  -- CACHED CALCULATION (immutable JSON snapshot)
  final_score REAL NOT NULL,
  risk_level TEXT,
  confidence_interval REAL,
  breakdown_json TEXT NOT NULL,  -- Complete 7-factor breakdown
  
  -- VERSIONING (when was this calculated?)
  model_version TEXT NOT NULL,   -- "7factor-v1.0", "7factor-v1.1", etc.
  calculation_timestamp TIMESTAMP NOT NULL,
  calculated_by_user_id TEXT,
  
  -- FRESHNESS TRACKING
  is_stale BOOLEAN DEFAULT 0,
  staleness_reason TEXT,  -- "model_v1.1_released" or NULL
  
  -- AUDIT
  created_at TIMESTAMP,
  updated_at TIMESTAMP
)
```

### Table 2: **risk_scores_history** (Change Audit Trail)
```sql
CREATE TABLE risk_scores_history (
  id TEXT PRIMARY KEY,
  shipment_id TEXT NOT NULL,
  
  -- BOTH SCORES
  previous_score REAL,
  previous_model_version TEXT,
  previous_breakdown_json TEXT,
  
  new_score REAL NOT NULL,
  new_model_version TEXT NOT NULL,
  new_breakdown_json TEXT NOT NULL,
  
  -- WHY CHANGED?
  change_reason TEXT,  -- "model_tuning_v1.0→v1.1", "manual_recalc", "user_feedback_applied"
  score_delta REAL,    -- new_score - previous_score
  
  created_at TIMESTAMP,
  created_by TEXT
)
```

### Table 3: **model_versions** (ML Model Registry)
```sql
CREATE TABLE model_versions (
  version_id TEXT PRIMARY KEY,  -- "7factor-v1.0", "7factor-v1.1"
  
  -- MODEL METADATA
  model_name TEXT,
  version_number TEXT,
  trained_date TIMESTAMP,
  
  -- COMPONENT CONFIGS
  isolation_forest_n_estimators INT,
  isolation_forest_contamination REAL,
  lightgbm_num_leaves INT,
  lightgbm_learning_rate REAL,
  
  -- STATUS
  is_active BOOLEAN DEFAULT 1,
  released_at TIMESTAMP,
  deprecated_at TIMESTAMP,
  
  -- INVALIDATION
  invalidate_all_scores_on_release BOOLEAN DEFAULT 1,  -- Mark old scores as stale?
  
  created_at TIMESTAMP,
  notes TEXT
)
```

### Table 4: **altana_scenarios** (External API - Only Stored When Called)
```sql
CREATE TABLE altana_scenarios (
  id TEXT PRIMARY KEY,
  shipment_id TEXT NOT NULL,
  risk_score_id TEXT NOT NULL,  -- FK to cache (only if score >= 70)
  
  -- CONDITION FOR INVOCATION
  initial_score REAL NOT NULL,
  score_threshold_met BOOLEAN,   -- Was score >= 70?
  
  -- ALTANA REQUEST
  altana_query_timestamp TIMESTAMP,
  
  -- ALTANA RESPONSE (only if actually called)
  altana_confidence REAL,        -- 0.0-1.0 or NULL if not called
  altana_recommendation TEXT,    -- "HOLD_FOR_EXAMINATION", "CLEAR", "REVIEW"
  altana_risk_factors TEXT,      -- JSON array of factors
  supply_chain_opacity REAL,     -- 0-100 or NULL
  sanctions_exposure BOOLEAN,    -- true/false or NULL
  
  -- ADJUSTMENT LOGIC
  confidence_bracket TEXT,       -- ">85%", "60-85%", "<60%" or "NOT_CALLED"
  adjustment_amount REAL,        -- +5, +2, -8 or 0 if not called
  
  final_score_after_altana REAL, -- initial_score + adjustment
  
  created_at TIMESTAMP,
  notes TEXT
)
```

---

## Data Flow: The Two-View Pattern

### View 1: List View (Shows Cached Score - Fast)
```
ModernCaseInvestigationPage.tsx :: List of Shipments
  ↓
SELECT final_score, risk_level, is_stale 
FROM risk_scores_cache 
WHERE shipment_id IN (...)

Response:
{
  "id": "SHP-123",
  "final_score": 45.0,
  "risk_level": "MEDIUM",
  "is_stale": false,      ← Green indicator
  "model_version": "7factor-v1.0"
}
```

### View 2: Investigation Detail View (Recalculates + Shows Change)
```
ModernCaseInvestigationPage.tsx :: Detail View
  ↓ Click on SHP-123

Request 1: Get Current Model Version
  GET /api/score/current-model-version
  Response: "7factor-v1.1"

Request 2: Get Cached Score
  GET /api/score/cache/SHP-123
  Response: {
    "final_score": 45.0,
    "model_version": "7factor-v1.0",  ← OLD MODEL
    "is_stale": true
  }

Request 3: Recalculate with Current Model
  POST /api/score/full-breakdown/SHP-123
  Response: {
    "final_score": 52.3,              ← NEW MODEL
    "model_version": "7factor-v1.1"
  }

Request 4: Get Change History
  GET /api/score/history/SHP-123
  Response: [
    {
      "timestamp": "2026-05-20T10:00Z",
      "previous_score": 45.0,
      "new_score": 52.3,
      "change_reason": "model_tuning_v1.0→v1.1",
      "delta": +7.3
    }
  ]

UI Shows:
┌─────────────────────────────────────┐
│ CACHED SCORE (from v1.0)            │
│ Final Score: 45.0  🟡 STALE         │
│ Model: 7factor-v1.0                 │
│ Calculated: 2026-05-10              │
│                                     │
│ ─────────────────────────────────── │
│ CURRENT SCORE (recalculated v1.1)   │
│ Final Score: 52.3  🟢 FRESH         │
│ Model: 7factor-v1.1                 │
│ Delta: +7.3 (documentation improved)│
│                                     │
│ ─────────────────────────────────── │
│ CHANGE HISTORY                      │
│ • 2026-05-20: 45.0 → 52.3 (+7.3)   │
│   Reason: Model tuning v1.0→v1.1   │
│ • 2026-04-15: 40.2 → 45.0 (+4.8)   │
│   Reason: ISF Dwell detected       │
└─────────────────────────────────────┘
```

---

## When Scores Become Stale (ML Versioning Only)

### Scenario 1: Model Training Complete
```
Step 1: New Model Released
  INSERT INTO model_versions (version_id='7factor-v1.1', ...)
  SET is_active=1

Step 2: Mark Old Scores Stale (if invalidate_on_release=true)
  UPDATE risk_scores_cache 
  SET is_stale=1, 
      staleness_reason='model_v1.0→v1.1_released'
  WHERE model_version='7factor-v1.0'
  AND is_stale=0

Step 3: User Clicks Investigation
  ├─ Detect: Current model v1.1, cached score v1.0
  ├─ Recalculate with v1.1
  ├─ Show both scores + delta
  ├─ Record in history
  └─ Optional: Auto-update cache or keep old?
```

### Scenario 2: No Model Change
```
Old model: 7factor-v1.0 (still active)
Score calculated: 45.0 (v1.0)
New data arrives about shipment
User clicks investigation

Action: 
  ├─ is_stale=false (same model version)
  ├─ Return cached 45.0
  ├─ NO recalculation needed
  ├─ NO history entry
  └─ Show as FRESH (green)
```

### Scenario 3: Model Tuned (Parameters Updated, Same Version)
```
BEFORE: 
  7factor-v1.0 (isolation_forest_contamination=0.1)

AFTER:
  7factor-v1.0 (isolation_forest_contamination=0.15)

Decision Point:
  A. Don't increment version → Cached scores stay valid
  B. Increment to v1.1 → Cached scores marked stale

Usually: Increment version (safer) → Scores marked stale on user request
```

---

## The JSON Breakdown (What Gets Cached)

```json
{
  "shipment_id": "SHP-163679",
  "final_score": 45.0,
  "risk_level": "MEDIUM",
  "confidence_interval": "±2.5",
  
  "calculation_summary": {
    "subtotal": 6.52,
    "corroboration_bonuses": 30.98,
    "calibration_multiplier": 1.2,
    "altana_adjustment": 0
  },
  
  "factors": {
    "documentation": {
      "total": 1.49,
      "percentage": 22.8,
      "components": [
        {
          "name": "Element9Mismatch",
          "raw_score": 9.5,
          "weight": 11.4,
          "weighted_result": 1.08,
          "rationale": "Declared VN, actual CN",
          "evidence": ["ISF Filing: 2026-05-20", "Element 9 Mismatch"]
        }
      ]
    },
    "commodity": { ... },
    "routing": { ... },
    "party": { ... },
    "corridor": { ... },
    "pattern": { ... },
    "time": { ... }
  },
  
  "adjustments": [
    {
      "type": "corroboration_bonus",
      "amount": 10.0,
      "reason": "Element9 + Dwell Anomaly align"
    }
  ],
  
  "altana": {
    "queried": false,           -- Was score >= 70?
    "threshold_met": false,
    "initial_score_before_altana": 45.0,
    "confidence": null,         -- NULL if not called
    "adjustment": 0,            -- 0 if not called
    "final_score_after_altana": 45.0
    -- If score was >= 70, this would include:
    -- "queried": true,
    -- "confidence": 0.92,
    -- "recommendation": "HOLD_FOR_EXAMINATION",
    -- "adjustment": +5,
    -- "final_score_after_altana": 75.0
  },
  
  "metadata": {
    "model_version": "7factor-v1.0",
    "calculation_timestamp": "2026-05-10T14:30:00Z",
    "calculation_duration_ms": 245
  }
}
```

---

## Benefits of This Design

| Aspect | Benefit |
|--------|---------|
| **JSON Caching** | Fast list views, self-contained snapshots |
| **Model Versioning as Staleness** | Clear trigger (no ambiguity about when to recalc) |
| **Two-Score Display** | Shows cached (what was decided) + current (what would decide now) |
| **Change History** | Full audit trail: when did score change, why, by how much |
| **No Real-time Recalc Pressure** | Scores don't go stale from shipment changes, only from model updates |
| **Analytics Ready** | Can query JSON in most databases, or export for Tableau/PowerBI |
| **What-If Ready** | Store hypothetical scenarios as separate cache entries |

---

## API Endpoints

```python
# CACHING ENDPOINTS
GET /api/score/cache/{shipment_id}          # Get cached score
GET /api/score/cache/{shipment_id}?format=json  # Get as JSON

# RECALCULATION ENDPOINTS  
POST /api/score/full-breakdown/{shipment_id}    # Recalc + cache
POST /api/score/full-breakdown/{shipment_id}?force=true  # Force recalc

# HISTORY & VERSIONING
GET /api/score/history/{shipment_id}        # Get all changes
GET /api/score/current-model-version        # Current model version
GET /api/score/model-versions               # All versions

# STALENESS MANAGEMENT
POST /api/score/mark-stale (on model release)
PATCH /api/score/cache/{shipment_id} (user recalc)

# ANALYTICS (if SQL backend)
GET /api/analytics/risk-by-factor
GET /api/analytics/model-comparison  
GET /api/analytics/staleness-report
```

---

## Altana API: Conditional External Scenario

### Key Principle: **Altana Only in Scenario When Score >= 70**

```
Risk Score Calculation
  ↓
Is final_score >= 70?
  ├─ NO (e.g., 45.0)
  │  └─ altana_scenarios entry = NULL
  │     (no API call, no Altana data stored)
  │
  └─ YES (e.g., 85.0)
     ├─ Call Altana API
     ├─ INSERT altana_scenarios row
     ├─ Store: confidence, recommendation, risk_factors
     ├─ Calculate: confidence_bracket + adjustment
     ├─ Update: final_score_after_altana
     └─ Include in cache JSON
```

### Example: Two Scenarios

**Scenario A: Score 45.0 (Below Altana Threshold)**
```json
{
  "shipment_id": "SHP-163679",
  "final_score": 45.0,
  "altana": {
    "queried": false,
    "reason": "score < 70 threshold",
    "confidence": null,
    "adjustment": 0,
    "final_score_after_altana": 45.0
  }
}

Database: altana_scenarios table is NOT used for this shipment
```

**Scenario B: Score 85.0 (Above Altana Threshold)**
```json
{
  "shipment_id": "SHP-999",
  "final_score_before_altana": 85.0,
  "altana": {
    "queried": true,
    "query_timestamp": "2026-05-20T14:35:00Z",
    "confidence": 0.92,
    "recommendation": "HOLD_FOR_EXAMINATION",
    "risk_factors": ["supply_chain_opacity", "new_trade_route"],
    "supply_chain_opacity": 70,
    "sanctions_exposure": false,
    "confidence_bracket": ">85%",
    "adjustment": +5,
    "final_score_after_altana": 90.0
  }
}

Database: altana_scenarios row created with all Altana response data
```

### API Flow (Conditional)

```python
def calculate_risk_score(shipment_data):
    # Step 1: Calculate 7-factor score
    initial_score = engine.score_shipment(shipment_data)
    
    # Step 2: Store in cache
    save_to_risk_scores_cache(initial_score)
    
    # Step 3: CONDITIONAL - Check Altana threshold
    if initial_score >= 70:
        # Call external Altana API
        altana_response = await call_altana_api(
            shipment_id=shipment_data['id'],
            shipper=shipment_data['shipper_name'],
            origin=shipment_data['origin_country'],
            hs_code=shipment_data['hs_code'],
            model_score=initial_score
        )
        
        # Store Altana scenario
        create_altana_scenario(
            shipment_id=shipment_data['id'],
            initial_score=initial_score,
            altana_response=altana_response
        )
        
        # Calculate adjustment
        adjustment = compute_altana_adjustment(altana_response['confidence'])
        final_score = initial_score + adjustment
    else:
        # Altana not called
        final_score = initial_score
        # altana_scenarios table NOT touched
    
    return {
        "final_score": final_score,
        "has_altana_scenario": initial_score >= 70,
        "altana_adjustment": adjustment if initial_score >= 70 else 0
    }
```

### UI Display Logic

```
Investigation View: Display Final Score
  ↓
if shipment.altana_scenarios exists:
  ├─ Show: "Score with Altana Verification"
  ├─ Show: Altana Confidence (92%)
  ├─ Show: Altana Recommendation
  ├─ Show: Adjustment Applied (+5 points)
  └─ Show: Final = 85 + 5 = 90
else:
  ├─ Show: "Model Score (Altana threshold not met)"
  └─ Show: Final = 45.0
```

---

## When to Recalculate (Decision Tree)

```
User clicks Investigation Detail View
  ↓
Is cached score from current model version?
  ├─ YES → is_stale=false
  │        ├─ Display cached score
  │        ├─ Show: "FRESH (v1.1)"
  │        └─ No recalc
  │
  └─ NO → is_stale=true
           ├─ Recalculate with current model
           ├─ Show both: cached (v1.0) vs new (v1.1)
           ├─ Show delta: +7.3 points
           ├─ Show history: why it changed
           ├─ Optional: Update cache or keep old?
           └─ User can accept new or keep investigating old
```

---

## Implementation Checklist

### Phase 1: Core Caching + History (No Altana Yet)
- [ ] Create `risk_scores_cache` table (JSON breakdown)
- [ ] Create `risk_scores_history` table (change audit)
- [ ] Create `model_versions` table (ML registry)
- [ ] Endpoint: POST /api/score/full-breakdown/{id} → cache + history
- [ ] Endpoint: GET /api/score/cache/{id}
- [ ] Endpoint: GET /api/score/history/{id}
- [ ] Generate 7-factor score (complete calculation)
- [ ] Store in cache as JSON (self-contained snapshot)

### Phase 2: Model Versioning + Staleness Detection
- [ ] Track model version in calculation
- [ ] Endpoint: GET /api/score/current-model-version
- [ ] Mark scores stale on model release
- [ ] UI: Show cached vs current with delta
- [ ] Display change history (when score changed, why)

### Phase 3: Altana Integration (Conditional, External)
- [ ] Create `altana_scenarios` table
- [ ] Add threshold check: if initial_score >= 70 → call Altana
- [ ] Endpoint: Call Altana API (only when >= 70)
- [ ] Store Altana response (confidence, recommendation, adjustment)
- [ ] Calculate final_score = initial_score + altana_adjustment
- [ ] UI: Show "Altana Verified" badge when scenario exists

### Phase 4: Advanced (Optional)
- [ ] What-if scenarios (separate cache entries)
- [ ] Batch recalculation (on model release)
- [ ] Analytics queries (risk by factor, staleness report)
- [ ] Comparison view (old model vs new model)
- [ ] Altana response caching (retry logic if API fails)

---

## Example: What User Sees

### Scenario: Model Update Released (v1.0 → v1.1)

**Before Clicking Investigation:**
```
List View:
SHP-163679 | Score: 45.0 | Status: 🟡 STALE | Last Calc: 5 days ago
```

**After Clicking Investigation:**
```
┌─────────────────────────────────────────────────────────┐
│  SHIPMENT: SHP-163679 (Shanghai Trade Co.)              │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  CACHED SCORE (Model v1.0 - from May 10)              │
│  ┌───────────────────────────────────────┐             │
│  │ Final Score: 45.0/100  🟡 MEDIUM      │             │
│  │ Risk Level: MEDIUM-ELEVATED           │             │
│  │ Element 9 Mismatch: HIGH (9.5/10)     │             │
│  │ Routing Dwell: HIGH (9.0/10)          │             │
│  │ Shipper Age: NEW (2 months)           │             │
│  └───────────────────────────────────────┘             │
│                                                         │
│  ────────────── MODEL UPDATE ──────────────             │
│  New Model v1.1 Released (Better AIS Detection)        │
│                                                         │
│  CURRENT SCORE (Model v1.1 - Recalculated)            │
│  ┌───────────────────────────────────────┐             │
│  │ Final Score: 52.3/100  🔴 HIGH        │             │
│  │ Risk Level: HIGH (Changed!)           │             │
│  │ Element 9 Mismatch: HIGH (9.5/10)     │             │
│  │ Routing Dwell: CRITICAL (9.8/10)  ↑   │ ← Model now │
│  │ Shipper Age: NEW (2 months)           │   catches   │
│  └───────────────────────────────────────┘   more      │
│                                                         │
│  ────────────── CHANGE ANALYSIS ──────────────          │
│  Score Delta: +7.3 points                              │
│  Why: Model v1.1 Isolation Forest detected sustained    │
│       dwell anomaly (previously: 9.0, now: 9.8)        │
│                                                         │
│  ────────────── HISTORY ──────────────                  │
│  May 20 | v1.0 → v1.1 | 45.0 → 52.3 | +7.3 points     │
│  May 10 | v1.0 (initial) | Score: 45.0 | ISF dwell    │
│                                                         │
│  [Buttons]                                              │
│  [ Accept New Score ]  [ Keep Investigating ]           │
│  [ What-If: Change Data ]  [ Full Calculation ]         │
└─────────────────────────────────────────────────────────┘
```

This gives investigators:
- ✓ Old decision (45.0 - what was flagged)
- ✓ New decision (52.3 - what would flag today)
- ✓ Reason for change (model tuning)
- ✓ Change history (audit trail)
- ✓ Transparency into why it changed (routing, not doc risk)

---

## Why This Hybrid Design is Better

| Aspect | V1 (Normalized) | V2 (Rejected) | V3 (Hybrid - Current) |
|--------|---|---|---|
| **Staleness Trigger** | Time + Events | Events only | Model Version Only ✓ |
| **Data Format** | Broken across tables | JSON blobs | JSON with history ✓ |
| **Cache Invalidation** | Complex logic | No strategy | Clear: new model → mark stale ✓ |
| **List View Speed** | Slow (joins) | Fast | Fast (single row) ✓ |
| **Detail View Transparency** | Limited | No changes shown | Shows old vs new + history ✓ |
| **Altana Handling** | Always stored | Not addressed | Conditional only >= 70 ✓ |
| **Change Audit Trail** | Generic history | No history | Complete history table ✓ |
| **Analytics Ready** | ✓ Normalizable | ✗ JSON only | ✓ JSON + can denormalize |
| **What-If Support** | Complex logic | Not addressed | Separate cache entries ✓ |

**Key Insight:** JSON is fine for caching. The real architecture is about:
1. **Staleness = Model Version Change** (not time, not events)
2. **Lazy Recalculation** (only when user clicks detail)
3. **Transparency = Show Both Scores** (what was vs what is)
4. **Altana as Conditional External** (only >= 70 threshold)

---

## Database Schema Summary

```
Tables:
├─ risk_scores_cache         (JSON + metadata, one per shipment)
├─ risk_scores_history       (audit trail, one row per change)
├─ model_versions            (ML model registry)
└─ altana_scenarios          (external API data, only if score >= 70)

Data Flow:
Calculation → Cache (JSON) → History (audit) → Optional Altana (if >= 70)

Staleness Trigger:
New Model Released
  ├─ Model version incremented in DB
  ├─ Old scores marked is_stale=true
  ├─ List view shows stale indicator (🟡)
  └─ Detail view auto-recalc + shows delta

User Experience:
List:   "SHP-123 | Score: 45 | 🟡 STALE (v1.0) | Calculated 5 days ago"
Detail: Shows old (45) vs new (52.3) + why (+7.3: Routing Dwell improved)
```
