# Risk Scoring System — Complete Architectural Redesign

## Problem with Current Approach ❌

1. **JSON Blobs**: Storing entire breakdown as TEXT/JSON prevents analytics
2. **No Normalization**: Can't query "which shipments have high Documentation Risk?"
3. **No Cache Invalidation**: When is a score stale? Why?
4. **Poor Separation**: Risk scoring mixed with shipment data
5. **No Audit Trail**: Only latest score, no history
6. **Not Analytics-Ready**: Raw JSON doesn't support dashboards/reports

---

## Redesigned Architecture (Analytics-First)

### Core Principle
```
Shipments = Facts (immutable, what happened)
Risk Scores = Analytical Results (calculated, cached, can go stale)
Staleness = Event-driven (shipper change, entity change, commodity change, corridor risk update)
```

### Schema Design

#### 1. **shipments** (Keep Minimal - No Risk Columns)
```sql
shipments (
  id TEXT PRIMARY KEY,
  manifest_id TEXT,
  shipper_id TEXT,        -- FK to shipper entity
  consignee_id TEXT,      -- FK to consignee entity
  commodity_hs_code TEXT,
  corridor_id TEXT,       -- FK to corridors
  declared_value_usd REAL,
  created_at TIMESTAMP,
  [no risk columns here]
)
```

#### 2. **risk_score_snapshots** (Latest Score - Cached)
```sql
risk_score_snapshots (
  id TEXT PRIMARY KEY,
  shipment_id TEXT UNIQUE FK,
  
  -- Final Score
  final_score REAL,
  risk_level TEXT (LOW|MEDIUM|HIGH|CRITICAL),
  confidence_interval REAL,
  
  -- Metadata
  calculation_timestamp TIMESTAMP,
  model_version TEXT (e.g., "7factor-v1.0"),
  calculation_duration_ms REAL,
  
  -- Staleness Tracking
  is_stale BOOLEAN DEFAULT 0,
  staleness_reason TEXT (NULL|'shipper_profile_changed'|'entity_resolution_updated'|'commodity_class_changed'|'corridor_risk_updated'|'time_based'),
  staleness_detected_at TIMESTAMP,
  
  -- What-If Support
  is_what_if BOOLEAN DEFAULT 0,
  what_if_scenario_id TEXT,
  
  created_at TIMESTAMP,
  updated_at TIMESTAMP
)
```

#### 3. **risk_score_history** (Audit Trail)
```sql
risk_score_history (
  id TEXT PRIMARY KEY,
  shipment_id TEXT FK,
  final_score REAL,
  risk_level TEXT,
  model_version TEXT,
  calculation_timestamp TIMESTAMP,
  reason_for_recalculation TEXT,
  created_at TIMESTAMP
)
```

#### 4. **risk_score_components** (Normalized - Queryable)
```sql
risk_score_components (
  id TEXT PRIMARY KEY,
  shipment_id TEXT FK,
  risk_score_id TEXT FK,  -- Link to snapshot
  
  -- Dimensions
  factor_name TEXT (Documentation|Commodity|Routing|Party|Corridor|Pattern|Time),
  component_name TEXT (Element9Mismatch|ExportControl|AIS Dwell|etc),
  
  -- Values
  raw_score REAL (0-10),
  weight_percentage REAL,
  weighted_contribution REAL,
  
  -- Evidence
  rationale TEXT,
  evidence_items TEXT (JSON array: ["ISF Filing: 2026-05-20", "Element 9 Mismatch"]),
  
  created_at TIMESTAMP
)

-- Enables queries like:
-- SELECT factor_name, AVG(weighted_contribution) 
-- FROM risk_score_components 
-- WHERE factor_name = 'Documentation' 
-- GROUP BY factor_name
```

#### 5. **risk_adjustments** (Multipliers & Flags)
```sql
risk_adjustments (
  id TEXT PRIMARY KEY,
  shipment_id TEXT FK,
  risk_score_id TEXT FK,
  
  adjustment_type TEXT (corridor_multiplier|penalty|bonus),
  adjustment_name TEXT,
  baseline_value REAL,
  multiplier REAL,
  adjustment_points REAL,
  
  reason TEXT,
  created_at TIMESTAMP
)
```

#### 6. **staleness_events** (Analytics - When/Why Scores Go Stale)
```sql
staleness_events (
  id TEXT PRIMARY KEY,
  shipment_id TEXT FK,
  event_type TEXT,  -- shipper_profile_changed, entity_data_updated, commodity_reclassified, corridor_risk_updated, time_based
  event_timestamp TIMESTAMP,
  old_value TEXT,
  new_value TEXT,
  triggered_by_user_id TEXT,
  triggered_by_system TEXT,
  
  -- What should happen
  requires_recalculation BOOLEAN,
  recalculation_priority TEXT (high|medium|low),
  
  created_at TIMESTAMP
)
```

#### 7. **risk_score_cache_config** (Configuration)
```sql
risk_score_cache_config (
  id TEXT PRIMARY KEY,
  
  -- Staleness Thresholds
  max_age_days INTEGER DEFAULT 7,
  
  -- Events that trigger staleness
  trigger_shipper_profile_change BOOLEAN DEFAULT 1,
  trigger_entity_resolution_change BOOLEAN DEFAULT 1,
  trigger_commodity_reclassification BOOLEAN DEFAULT 1,
  trigger_corridor_risk_update BOOLEAN DEFAULT 1,
  
  -- Recalculation rules
  auto_recalculate BOOLEAN DEFAULT 0,
  recalculate_on_stale_detection BOOLEAN DEFAULT 1,
  batch_recalculation_schedule TEXT (cron: "0 2 * * *"),
  
  created_at TIMESTAMP,
  updated_at TIMESTAMP
)
```

---

## Data Flow Redesign

### A. Initial Score Calculation
```
1. POST /api/score/full-breakdown/{shipment_id}
   ├─ Risk Scoring Engine calculates 18 components
   ├─ Normalize: Store in risk_score_components (one row per component)
   ├─ Persist: risk_score_snapshots (final score, metadata)
   ├─ Audit: risk_score_history (for replay/audit)
   └─ Return: Assembled response to UI

2. sentry-data service calls:
   ├─ create_or_update_risk_snapshot()
   ├─ insert_risk_components() [bulk insert]
   ├─ insert_risk_adjustments()
   └─ get_7factor_score() [return latest]
```

### B. Staleness Detection (Event-Driven)
```
1. Shipper profile changes → Event fires
2. Entity resolution updates → Event fires
3. Commodity classification changes → Event fires
4. Corridor risk level changes → Event fires
5. Time-based: 7 days passed → Event fires

Each event:
├─ INSERT INTO staleness_events
├─ UPDATE risk_score_snapshots SET is_stale=1, staleness_reason=?
├─ Emit webhook/event if auto_recalculate enabled
└─ Optional: Trigger async batch recalculation
```

### C. What-If Analysis
```
1. User asks: "What if origin country changed?"
2. Alternative flow:
   ├─ Mark is_what_if=1
   ├─ Create separate what_if_scenario_id
   ├─ Calculate with hypothetical values
   ├─ Store in risk_score_snapshots with what_if markers
   └─ Return: Current vs What-If comparison
```

---

## Analytics Capabilities (Why This Design)

### 1. Risk Factor Trends
```sql
SELECT 
  factor_name,
  DATE(created_at) as date,
  AVG(weighted_contribution) as avg_contribution,
  COUNT(*) as shipment_count
FROM risk_score_components
WHERE created_at > DATE('now', '-30 days')
GROUP BY factor_name, DATE(created_at)
ORDER BY date;
```
**Output**: Dashboard showing Documentation Risk trending up over past month

### 2. Staleness Analysis
```sql
SELECT 
  staleness_reason,
  COUNT(*) as stale_count,
  AVG(JULIANDAY('now') - JULIANDAY(staleness_detected_at)) as days_stale_avg
FROM risk_score_snapshots
WHERE is_stale = 1
GROUP BY staleness_reason;
```
**Output**: "47 scores are stale due to shipper profile changes, avg 3.2 days old"

### 3. Component Impact
```sql
SELECT 
  component_name,
  factor_name,
  AVG(weighted_contribution) as impact,
  COUNT(DISTINCT shipment_id) as frequency
FROM risk_score_components
WHERE factor_name = 'Documentation'
GROUP BY component_name
ORDER BY impact DESC;
```
**Output**: "Element 9 Mismatch has highest impact on Documentation Risk"

### 4. Corridor Risk Patterns
```sql
SELECT 
  s.corridor_id,
  AVG(rs.final_score) as avg_risk_score,
  COUNT(rs.shipment_id) as shipment_count,
  SUM(CASE WHEN rs.risk_level = 'CRITICAL' THEN 1 ELSE 0 END) as critical_count
FROM shipments s
JOIN risk_score_snapshots rs ON s.id = rs.shipment_id
WHERE rs.created_at > DATE('now', '-30 days')
GROUP BY s.corridor_id
ORDER BY avg_risk_score DESC;
```
**Output**: "Vietnam→US corridor has 8 critical shipments this month"

### 5. Model Performance
```sql
SELECT 
  model_version,
  COUNT(*) as calculations,
  AVG(final_score) as avg_score,
  AVG(calculation_duration_ms) as avg_duration_ms
FROM risk_score_snapshots
GROUP BY model_version;
```
**Output**: "v1.0 is faster but v2.0 catches more edge cases"

---

## Staleness Strategy (Business Rules)

### Time-Based Staleness
```
Score is STALE if:
  - Age > 7 days (configurable in risk_score_cache_config)
  - OR no recalculation event has occurred
```

### Event-Based Staleness
```
Immediately mark STALE if any of these change:
1. Shipper profile (age, violations, ofac, network)
2. Entity resolution (Senzing matches updated)
3. Commodity classification (HS code reclassified)
4. Corridor risk baseline (corridor risk level updated)
```

### Recalculation Strategy
```
Three modes (configurable):

Mode 1: Lazy (Default)
  - Detection: score marked stale
  - Action: nothing (return as-is but flag stale)
  - Recalc: On-demand (UI "Recalculate" button)

Mode 2: Semi-Async
  - Detection: score marked stale
  - Action: emit to queue
  - Recalc: Background job batch processes at 2am

Mode 3: Real-Time
  - Detection: score marked stale
  - Action: synchronous recalculation
  - Recalc: Immediate (expensive, use sparingly)
```

---

## Implementation Priority (Architect's View)

### Phase 1: Core Analytics (Weeks 1-2)
- ✓ Create risk_score_snapshots table (cached scores)
- ✓ Create risk_score_components table (normalized)
- ✓ Create staleness_events table
- ✓ Implement sentry-data endpoints for CRUD
- ✓ API routes call sentry-data (already fixed)

### Phase 2: Staleness Detection (Weeks 3-4)
- Webhook listeners for shipper/entity/commodity/corridor changes
- Mark snapshots as stale
- Staleness_events logging
- UI flag: "Score is stale, refresh recommended"

### Phase 3: Smart Recalculation (Weeks 5-6)
- Batch recalculation job (scheduler)
- On-demand recalculation endpoint
- Model versioning (track which v1.0 vs v2.0)
- History tracking for audit

### Phase 4: Analytics Dashboards (Weeks 7-8)
- Risk factor trends
- Staleness analytics
- Component impact
- Corridor patterns
- Model performance comparison

---

## Code Structure

```
services/data/
├── db.py
│   ├── create_or_update_risk_snapshot()    [NEW]
│   ├── get_risk_snapshot()                 [NEW]
│   ├── insert_risk_components()            [NEW]
│   ├── insert_risk_adjustments()           [NEW]
│   ├── mark_score_stale()                  [NEW]
│   ├── get_staleness_report()              [NEW]
│   └── [existing functions]
├── models.py
│   ├── RiskScoreSnapshot [NEW]
│   ├── RiskScoreComponent [NEW]
│   ├── RiskAdjustment [NEW]
│   ├── StalenessEvent [NEW]
│   └── [existing models]
└── main.py
    ├── POST /risk-scores/snapshots/{shipment_id}    [NEW]
    ├── GET /risk-scores/snapshots/{shipment_id}     [NEW]
    ├── GET /risk-scores/components/{shipment_id}    [NEW]
    ├── GET /analytics/risk-factors                  [NEW - Phase 4]
    ├── POST /risk-scores/mark-stale/{shipment_id}   [NEW]
    └── [existing endpoints]

api/services/risk_scoring/
├── routes.py
│   ├─ calculate_full_risk_breakdown()
│   └─ Call sentry-data POST /risk-scores/snapshots/
└── [engine stays same]

ui/src/
├── components/risk-scoring/
│   ├─ RiskScoreBreakdown.tsx (unchanged)
│   └─ StalenessIndicator.tsx [NEW]
└── pages/
    └─ AnalyticsRiskDashboard.tsx [NEW - Phase 4]
```

---

## Next Steps

1. **Validate Schema**: Does this support your analytics requirements?
2. **Confirm Staleness Rules**: Are 7 days + 4 events correct?
3. **Confirm Recalc Strategy**: Lazy, Semi-Async, or Real-Time?
4. **Confirm Phase 1 Scope**: Should we build history + staleness in Phase 1?

**Once approved, I will:**
1. Revert all current changes
2. Build schema from scratch (clean)
3. Implement Phase 1 properly
4. Clean architecture, normalized data, analytics-ready
