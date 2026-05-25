# Risk Scoring Final Schema — Clean Architecture

## Core Principle: Separation of Concerns
```
shipments (facts)
├─ risk_scores_cache (current snapshot)
├─ risk_score_transactions (audit trail - SEPARATE TABLE)
├─ model_versions (ML registry)
└─ altana_scenarios (external API - conditional)
```

---

## Table 1: risk_scores_cache (The Current Score)

```sql
CREATE TABLE risk_scores_cache (
  id TEXT PRIMARY KEY,
  shipment_id TEXT UNIQUE NOT NULL,
  
  -- THE CALCULATION
  final_score REAL NOT NULL,
  risk_level TEXT,                   -- LOW, MEDIUM, HIGH, CRITICAL
  confidence_interval REAL,
  breakdown_json TEXT NOT NULL,      -- Complete 7-factor breakdown
  
  -- METADATA
  current_model_version TEXT NOT NULL,  -- Which model calculated this?
  calculation_timestamp TIMESTAMP NOT NULL,
  is_stale BOOLEAN DEFAULT 0,           -- Is newer model available?
  
  -- AUDIT
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP,
  
  FOREIGN KEY (shipment_id) REFERENCES shipments(id)
)
```

**Purpose:** Single current snapshot for each shipment. Used by list views (fast).

---

## Table 2: risk_score_transactions (Complete Audit Trail - SEPARATE)

```sql
CREATE TABLE risk_score_transactions (
  id TEXT PRIMARY KEY,
  shipment_id TEXT NOT NULL,
  
  -- WHAT CHANGED
  previous_final_score REAL,
  new_final_score REAL NOT NULL,
  score_delta REAL,                    -- new - previous (can be NULL if first)
  
  -- WHAT HAPPENED
  transaction_type TEXT NOT NULL,      -- 'initial_calculation', 'model_update', 'manual_recalc', 'backfill'
  transaction_reason TEXT,             -- 'model_v1.0_released', 'user_requested_refresh', 'backfill_on_schema_migration'
  
  -- DETAILS (for analytics)
  previous_breakdown_json TEXT,        -- Old 7-factor breakdown
  new_breakdown_json TEXT NOT NULL,    -- New 7-factor breakdown
  
  -- WHO DID IT
  triggered_by TEXT,                   -- 'system', 'user_id:123', 'scheduler', 'model_release'
  triggered_by_model_version TEXT,     -- 'model_v1.0', 'model_v1.1', NULL if not model-triggered
  
  -- TIMESTAMP
  transaction_timestamp TIMESTAMP NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  
  FOREIGN KEY (shipment_id) REFERENCES shipments(id)
)

-- INDEXES for fast queries
CREATE INDEX idx_transactions_shipment ON risk_score_transactions(shipment_id);
CREATE INDEX idx_transactions_type ON risk_score_transactions(transaction_type);
CREATE INDEX idx_transactions_timestamp ON risk_score_transactions(transaction_timestamp);
```

**Purpose:** Complete immutable audit trail. Every score change recorded as a transaction. Never deleted, only appended.

---

## Table 3: model_versions (ML Model Registry)

```sql
CREATE TABLE model_versions (
  id TEXT PRIMARY KEY,                           -- "7factor-v1.0", "7factor-v1.1"
  
  -- METADATA
  model_name TEXT NOT NULL,
  version_number TEXT NOT NULL,
  training_date TIMESTAMP,
  released_at TIMESTAMP,
  
  -- ML PARAMETERS
  isolation_forest_n_estimators INT,
  isolation_forest_contamination REAL,
  isolation_forest_random_state INT,
  
  lightgbm_num_leaves INT,
  lightgbm_learning_rate REAL,
  lightgbm_max_depth INT,
  
  -- STATUS
  is_active BOOLEAN DEFAULT 0,
  deprecated_at TIMESTAMP,
  
  -- USAGE
  total_calculations INT DEFAULT 0,    -- How many shipments scored with this model?
  
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  notes TEXT
)
```

**Purpose:** Track every ML model version. Used to detect staleness and trigger recalculations.

---

## Table 4: altana_scenarios (External API - Conditional Only)

```sql
CREATE TABLE altana_scenarios (
  id TEXT PRIMARY KEY,
  shipment_id TEXT NOT NULL UNIQUE,
  risk_score_id TEXT NOT NULL,         -- FK to cache (only if score >= 70)
  
  -- INVOCATION CONDITION
  initial_score_before_altana REAL NOT NULL,
  threshold_met BOOLEAN,                -- Was score >= 70?
  
  -- REQUEST
  query_timestamp TIMESTAMP,
  
  -- RESPONSE (only if threshold_met=true)
  altana_confidence REAL,               -- 0.0-1.0, NULL if not called
  altana_recommendation TEXT,           -- "HOLD_FOR_EXAMINATION", "CLEAR", "REVIEW"
  altana_risk_factors TEXT,             -- JSON array
  supply_chain_opacity REAL,            -- 0-100
  sanctions_exposure BOOLEAN,
  
  -- ADJUSTMENT
  confidence_bracket TEXT,              -- ">85%", "60-85%", "<60%", "NOT_CALLED"
  adjustment_points REAL,               -- +5, +2, -8, or 0 if not called
  final_score_after_altana REAL,        -- initial + adjustment
  
  -- AUDIT
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP,
  
  FOREIGN KEY (shipment_id) REFERENCES shipments(id),
  FOREIGN KEY (risk_score_id) REFERENCES risk_scores_cache(id)
)
```

**Purpose:** Store Altana API calls ONLY when score >= 70. Conditional external scenario.

---

## Data Flow with Transactions

### Scenario 1: Initial Backfill (1,191 Shipments)

```
for each of 1,191 shipments:
  1. Calculate 7-factor score
  2. INSERT INTO risk_scores_cache
     {
       shipment_id, 
       final_score,
       breakdown_json,
       current_model_version='7factor-v1.0'
     }
  
  3. INSERT INTO risk_score_transactions
     {
       shipment_id,
       previous_final_score: NULL,
       new_final_score: calculated_score,
       transaction_type: 'backfill',
       transaction_reason: 'backfill_on_schema_migration',
       triggered_by: 'system',
       new_breakdown_json: calculated_breakdown
     }
  
  4. IF score >= 70:
       Call Altana API
       INSERT INTO altana_scenarios
```

### Scenario 2: New Model Released (v1.1)

```
1. INSERT INTO model_versions
   {
     id: 'model_v1.1',
     is_active: 1
   }

2. Mark old scores stale:
   UPDATE risk_scores_cache
   SET is_stale = 1
   WHERE current_model_version != 'model_v1.1'

3. When user clicks investigation detail on SHP-123:
   - Detect: current cache is v1.0, active model is v1.1
   - Recalculate with v1.1 → new_score = 52.3
   
   - INSERT INTO risk_score_transactions
     {
       shipment_id: 'SHP-123',
       previous_final_score: 45.0,
       new_final_score: 52.3,
       score_delta: 7.3,
       transaction_type: 'model_update',
       transaction_reason: 'model_v1.0→v1.1_recalculation',
       triggered_by: 'user:analyst_123',
       triggered_by_model_version: 'model_v1.1',
       previous_breakdown_json: old_breakdown,
       new_breakdown_json: new_breakdown
     }
   
   - UPDATE risk_scores_cache
     {
       final_score: 52.3,
       breakdown_json: new_breakdown,
       current_model_version: 'model_v1.1',
       is_stale: 0,
       updated_at: NOW()
     }

4. Show UI:
   Old: 45.0 (v1.0)
   New: 52.3 (v1.1)
   Delta: +7.3
```

### Scenario 3: Manual Recalculation (User Requests Refresh)

```
User clicks "Recalculate Score" button

1. Use current model (v1.1)
2. Recalculate → 52.0 (still fresh, no new model released)

3. INSERT INTO risk_score_transactions
   {
     transaction_type: 'manual_recalc',
     transaction_reason: 'user_requested_refresh',
     triggered_by: 'user:analyst_123'
   }

4. UPDATE risk_scores_cache (same model, updated timestamp)
```

---

## Querying the Transaction Log (Analytics)

### All Score Changes for a Shipment
```sql
SELECT 
  transaction_timestamp,
  transaction_type,
  previous_final_score,
  new_final_score,
  score_delta,
  triggered_by
FROM risk_score_transactions
WHERE shipment_id = 'SHP-123'
ORDER BY transaction_timestamp;

Result:
2026-05-25 | model_update | 45.0 → 52.3 | +7.3 | system (v1.1 release)
2026-05-10 | backfill     | NULL → 45.0 | N/A  | system (schema migration)
```

### How Many Shipments Changed on Model Release?
```sql
SELECT 
  COUNT(*) as updated_shipments,
  AVG(score_delta) as avg_delta,
  STDDEV(score_delta) as stddev_delta
FROM risk_score_transactions
WHERE transaction_type = 'model_update'
  AND triggered_by_model_version = 'model_v1.1';

Result:
542 shipments affected
Average delta: +4.2 points
Std Dev: 2.1 points
```

### Audit Trail: Who/When/Why
```sql
SELECT 
  shipment_id,
  transaction_timestamp,
  triggered_by,
  transaction_reason,
  new_final_score
FROM risk_score_transactions
WHERE transaction_type = 'manual_recalc'
  AND DATE(transaction_timestamp) = '2026-05-25'
ORDER BY transaction_timestamp DESC;
```

---

## UI: What Investigator Sees

### List View (Fast, Cached)
```
SHP-123     | Score: 45.0/100  | 🟡 STALE   | Last: May 10
SHP-124     | Score: 52.3/100  | 🟢 FRESH   | Last: May 25
SHP-125     | Score: 38.5/100  | 🟢 FRESH   | Last: May 25
```

### Detail View (Transparent)
```
╔═════════════════════════════════════════════════╗
║ SHIPMENT: SHP-123 (Shanghai Trade Co.)          ║
╠═════════════════════════════════════════════════╣
║                                                 ║
║ CURRENT CACHED SCORE (v1.0)                    ║
║ ┌─────────────────────────────────────────┐    ║
║ │ Final Score: 45.0/100 🟡 STALE         │    ║
║ │ Model: 7factor-v1.0                    │    ║
║ │ Calculated: May 10, 2026                │    ║
║ │ [Details...]                           │    ║
║ └─────────────────────────────────────────┘    ║
║                                                 ║
║ RECALCULATED WITH CURRENT MODEL (v1.1)        ║
║ ┌─────────────────────────────────────────┐    ║
║ │ Final Score: 52.3/100 🔴 HIGH          │    ║
║ │ Model: 7factor-v1.1                    │    ║
║ │ Calculated: Now (May 25)                │    ║
║ │ [Details...]                           │    ║
║ └─────────────────────────────────────────┘    ║
║                                                 ║
║ CHANGE ANALYSIS                                ║
║ ┌─────────────────────────────────────────┐    ║
║ │ Score Delta: +7.3 points                │    ║
║ │ Reason: Model v1.0 → v1.1               │    ║
║ │ What Changed: AIS Dwell detection       │    ║
║ │              (9.0/10 → 9.8/10)          │    ║
║ └─────────────────────────────────────────┘    ║
║                                                 ║
║ TRANSACTION HISTORY                            ║
║ ┌─────────────────────────────────────────┐    ║
║ │ May 25 | v1.0→v1.1 | 45.0→52.3 | +7.3  │    ║
║ │ May 10 | Backfill  | —→45.0   | N/A    │    ║
║ └─────────────────────────────────────────┘    ║
║                                                 ║
║ [Accept Score] [Keep Investigating]            ║
║ [What-If: Change Data] [Export Report]         ║
║                                                 ║
╚═════════════════════════════════════════════════╝
```

---

## Implementation Plan

### Phase 1: Core Schema + Backfill (Week 1)
```
□ Create 4 tables (cache, transactions, model_versions, altana_scenarios)
□ Backfill 1,191 shipments with initial scores
□ All backfill entries recorded in transactions table
□ Set current_model_version = '7factor-v1.0' (no versioning yet)
□ Deploy locally + test
```

### Phase 2: Model Versioning (Week 2)
```
□ Track model version in every calculation
□ Auto-detect staleness on model change
□ Auto-recalc on detail view
□ Show old vs new scores + delta
□ Record as transaction_type='model_update'
```

### Phase 3: Altana Integration (Week 3)
```
□ Conditional invocation (>= 70 only)
□ Store responses in altana_scenarios
□ Calculate adjustment
□ Include in breakdown JSON
```

### Phase 4: Analytics + Dashboards (Week 4+)
```
□ Transaction queries (who changed what when)
□ Model comparison (v1.0 vs v1.1 impact)
□ Staleness analysis
□ Audit reports
```

---

## Why This Design is Clean

| Aspect | Benefit |
|--------|---------|
| **Separate transaction table** | Immutable audit log, never mixed with shipments |
| **No version markers in cache** | Clean current state, versioning is separate concern |
| **Auto-recalc on model update** | Lazy evaluation, transparent |
| **Complete transaction history** | Full compliance, investigation-ready |
| **Conditional Altana** | External API only when needed |
| **Separation of concerns** | Cache (current) vs Transactions (history) |

---

## Ready to Build?

Shall I now:
1. Delete all experimental code from previous attempts
2. Build these 4 clean tables from scratch
3. Implement backfill script (1,191 shipments)
4. Deploy locally and test end-to-end
5. Then Phase 2 (model versioning)

Approval to proceed?
