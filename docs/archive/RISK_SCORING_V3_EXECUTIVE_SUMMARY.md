# Risk Scoring Redesign V3 — Executive Summary

## The Vision (What User Understands)

**JSON is fine. Model versioning is the staleness trigger. Two views. Change history.**

---

## Three Key Decisions

### 1. JSON Caching (Why This Works)
```
❌ Don't normalize every component into separate rows
✓ Cache the complete 7-factor calculation as immutable JSON snapshot

Why:
- Self-contained (don't need to reconstruct from components)
- Fast (single SELECT from cache table)
- Flexible (works with SQL or NoSQL)
- Audit-ready (snapshots for replay)
```

### 2. Model Version = Staleness Trigger (Not Time, Not Events)
```
❌ Don't mark stale on shipment changes (shipper age, commodity class change)
❌ Don't mark stale on time (7 days passed)
✓ Mark stale ONLY when ML model version changes

When:
├─ Model v1.0 active, score calculated with v1.0 → FRESH
├─ Model v1.1 released → Mark all v1.0 scores as STALE
├─ User clicks detail on STALE score → Auto-recalc with v1.1
└─ Show both: v1.0 (45.0) vs v1.1 (52.3) with delta

Why:
- Clear trigger (no ambiguity)
- No real-time pressure (only happens when team retrains model)
- Lazy calculation (only on user demand)
- Full transparency (shows what changed and why)
```

### 3. Two-View Pattern (List vs Detail)
```
LIST VIEW (Fast, Cached):
SHP-123 | Score: 45.0 | 🟡 STALE (v1.0) | Last calc: May 10

DETAIL VIEW (Lazy, Recalculated):
┌─ CACHED SCORE (v1.0)      ┐
│  Final: 45.0              │
│  Calculated: May 10       │
└─────────────────────────────┘
         ↓
┌─ CURRENT SCORE (v1.1)     ┐
│  Final: 52.3              │ ← Recalculated on-demand
│  Calculated: May 20       │
│  Delta: +7.3              │
└─────────────────────────────┘
         ↓
┌─ CHANGE HISTORY          ┐
│ May 20 | 45.0 → 52.3    │
│ Reason: v1.0 → v1.1     │
│ Why: AIS Dwell improved  │
└─────────────────────────────┘

Why:
- List view fast (no recalculation)
- Detail view transparent (shows old vs new)
- Change history captured (for investigation)
- No hidden recalculations (user sees both scores)
```

---

## Database Schema (3 Tables)

### risk_scores_cache (The Immutable JSON Snapshot)
```
id          | PK
shipment_id | FK (UNIQUE)
final_score | The number (0-100)
breakdown_json | Complete 7-factor calculation (self-contained)
model_version | "7factor-v1.0", "7factor-v1.1"
is_stale    | Boolean (true if newer model released)
created_at  | When calculated
```

### risk_scores_history (The Audit Trail)
```
id                  | PK
shipment_id         | FK
previous_score      | What it was
new_score           | What it is now
change_reason       | "model_v1.0→v1.1", "manual_recalc"
score_delta         | new - previous
created_at          | When changed
```

### altana_scenarios (External API, Conditional)
```
id                      | PK
shipment_id             | FK
initial_score           | Before Altana
score_threshold_met     | Was >= 70?

[Only if threshold met:]
altana_confidence       | 0.92 (from API)
altana_recommendation   | "HOLD_FOR_EXAMINATION"
adjustment_amount       | +5 points
final_score_after_altana| initial + adjustment

[If not called:]
All fields above = NULL
```

---

## Data Flow

```
1. CALCULATE
   POST /api/score/full-breakdown/SHP-123
   ├─ Engine scores all 18 components
   ├─ Generate 7-factor breakdown
   └─ Calculate final_score = 45.0

2. CACHE
   INSERT INTO risk_scores_cache
   ├─ breakdown_json = {complete 18-component breakdown}
   ├─ model_version = "7factor-v1.0"
   ├─ is_stale = false
   └─ Return to UI

3. OPTIONAL: ALTANA (Only if >= 70)
   IF initial_score >= 70:
   ├─ POST to Altana API
   ├─ INSERT into altana_scenarios
   ├─ Calculate: final = 45 + altana_adjustment
   └─ Store in cache.breakdown_json.altana section

4. HISTORY
   On recalculation:
   ├─ Get old cache.final_score = 45.0
   ├─ Get new cache.final_score = 52.3
   ├─ INSERT into risk_scores_history
   │  previous_score: 45.0
   │  new_score: 52.3
   │  change_reason: "model_v1.0→v1.1"
   └─ Update cache.is_stale = false (now fresh with new model)
```

---

## When Things Happen

### FRESH Score (Same Model Version)
```
User clicks detail on SHP-123
Score from v1.0, current model is v1.0
├─ is_stale = false
├─ Display cached 45.0
├─ Show: "FRESH (calculated 5 days ago)"
└─ No recalculation needed
```

### STALE Score (Older Model Version)
```
Model v1.1 released today
Existing scores from v1.0 marked is_stale = true

User clicks detail on SHP-123
Score from v1.0, current model is v1.1
├─ is_stale = true
├─ Recalculate with v1.1 → 52.3
├─ Show both: 45.0 (v1.0) vs 52.3 (v1.1)
├─ Show delta: +7.3
├─ Show history: "Model tuning improved AIS detection"
└─ Update cache to v1.1 (optional or keep both?)
```

### ALTANA SCENARIO (Only >= 70)
```
Score calculated: 85.0 (high risk)

Is 85.0 >= 70? YES
├─ Call Altana API
├─ Get confidence: 92%
├─ Get recommendation: "HOLD_FOR_EXAMINATION"
├─ Calculate adjustment: +5
├─ Final score: 85 + 5 = 90
└─ Store in altana_scenarios + cache.breakdown_json.altana

Score calculated: 45.0 (medium risk)

Is 45.0 >= 70? NO
├─ Skip Altana (no API call)
├─ altana_scenarios = NULL for this shipment
└─ Final score: 45.0 (no adjustment)
```

---

## Key Principles

1. **JSON is the cache format** (immutable, self-contained)
2. **Model version is the staleness trigger** (only reason to recalc)
3. **Lazy recalculation** (only on user demand)
4. **Two scores in detail view** (transparency: old vs new)
5. **Complete history** (audit trail of all changes)
6. **Altana is conditional** (only when score >= 70)
7. **No hidden recalculations** (user always aware of score sources)

---

## Implementation Order

```
Phase 1 (Core):
  ✓ risk_scores_cache table + CRUD
  ✓ risk_scores_history table + CRUD
  ✓ Full 7-factor calculation
  ✓ Cache JSON on POST /api/score/full-breakdown
  ✓ Show cached score on GET /api/score/cache/{id}

Phase 2 (Versioning + Staleness):
  ✓ model_versions table
  ✓ Track model_version in cache
  ✓ Mark stale on new model release
  ✓ Auto-recalc on detail view
  ✓ Show both scores + delta + history

Phase 3 (Altana):
  ✓ altana_scenarios table
  ✓ Conditional call (>= 70 only)
  ✓ Store response + adjustment
  ✓ Show "Altana Verified" badge

Phase 4 (Polish):
  ✓ What-if scenarios
  ✓ Batch recalc on model release
  ✓ Analytics dashboards
```

---

## Why This Design

| Question | Answer |
|----------|--------|
| Why JSON? | It's an immutable snapshot. Fast. Self-contained. Works with any DB. |
| Why model version for staleness? | Clear trigger. No ambiguity. Aligns with ML ops reality. |
| Why two views? | List is fast. Detail is transparent. User sees both old and new. |
| Why history table? | Audit trail. Compliance. Replay capability. Investigation support. |
| Why conditional Altana? | External API = scenario-based. Only call when needed (>= 70). |
| Why lazy recalc? | Performant. Transparent. User-driven (not hidden in background). |

---

## Ready to Build?

Once approved, we'll:
1. Revert all previous code changes
2. Create 3 clean tables (cache, history, altana_scenarios)
3. Implement Phase 1 fully (7-factor calculation + caching)
4. Deploy locally and test end-to-end
5. Then Phase 2 (versioning + staleness)

**Awaiting confirmation on:**
- ✓ JSON caching approach?
- ✓ Model version = staleness trigger?
- ✓ Two-view pattern (list cached, detail recalc)?
- ✓ Altana as conditional (>= 70 only)?
