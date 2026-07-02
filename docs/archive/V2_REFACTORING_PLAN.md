# V2AITuningPage Refactoring Plan

**Current State**: Hardcoded 7 factors for CBP  
**Future State**: Dynamic factors loaded from scorecard config  
**Impact**: Same UI works for CBP, FDA, Opioid without code changes

---

## Current Implementation (Lines 40-95)

### Problem 1: Hardcoded Factors

```typescript
// CURRENT: Hardcoded for CBP only
const FACTOR_META: Record<string, { label: string; color: string }> = {
  DOCUMENTATION_RISK: { label: 'Documentation Risk (ISF, Element 9, Manifest Completeness)', color: 'text-[#D83933]' },
  CORRIDOR_RISK: { label: 'Corridor Risk (Country-of-Origin Risk Pair)', color: 'text-amber-600' },
  COMMODITY_RISK: { label: 'Commodity Risk (Tariff Rate, Export Control, UFLPA)', color: 'text-orange-600' },
  ROUTING_RISK: { label: 'Routing Risk (AIS Dwell, Port Selection, Vessel Flag)', color: 'text-blue-600' },
  PARTY_RISK: { label: 'Party Risk (Shipper Age, Prior Violations, OFAC, Ownership)', color: 'text-purple-600' },
  PATTERN_RISK: { label: 'Pattern Anomaly (Pricing Anomaly, Weight Anomaly, Trade Frequency)', color: 'text-[#112E51]' },
  TIME_SENSITIVITY: { label: 'Time Sensitivity (Pre-Tariff Timing, Seasonal Anomaly)', color: 'text-slate-600' },
};

// If you want FDA, you must hardcode new factors
// If you want Opioid, you must hardcode new factors
// = Code bloat + maintenance nightmare
```

### Problem 2: Hardcoded Rules

```typescript
// CURRENT: Hardcoded rule checkboxes
const [rules, setRules] = useState({
  'W-121': true,
  'W-822': true,
  'UFLPA-301': true,
});

// FDA scorecard needs different rules: FDA-RECALL-MATCH, FDA-UNREGISTERED-IMPORTER
// Opioid scorecard needs: DEA-FLAGGED-PRESCRIBER, VOLUME-SPIKE-DETECTION
// = Must add conditional logic per domain
```

### Problem 3: Hardcoded Thresholds

```typescript
// CURRENT: Weights hardcoded in state
const [weights, setWeights] = useState<ModelWeights>({
  DOCUMENTATION_RISK: 25,
  CORRIDOR_RISK: 20,
  COMMODITY_RISK: 15,
  ROUTING_RISK: 15,
  PARTY_RISK: 15,
  PATTERN_RISK: 10,
  TIME_SENSITIVITY: 10,
});

// FDA has different factors, so hardcoded weights are wrong
// Opioid has different factors, so weights must be re-hardcoded
```

---

## Future Implementation (Parameterized)

### Step 1: Add Scorecard Selector

```typescript
// NEW: Add domain selector at top of page
type Scorecard = 'cbp_illegal_transshipment_v1' | 'fda_imports_fraud_v1' | 'opioid_detection_v1';

export default function V2AITuningPage() {
  const [activeScorecard, setActiveScorecard] = useState<Scorecard>('cbp_illegal_transshipment_v1');
  const [scorecardConfig, setScorecardConfig] = useState<ScorecardConfig | null>(null);
  
  // Load scorecard config when domain changes
  useEffect(() => {
    const loadScorecard = async () => {
      const config = await fetch(`/api/scorecards/${activeScorecard}`).then(r => r.json());
      setScorecardConfig(config);
      setWeights(config.factors.reduce((acc, f) => ({ ...acc, [f.id]: f.weight * 100 }), {}));
      setRules(config.rules.reduce((acc, r) => ({ ...acc, [r.ruleId]: true }), {}));
    };
    loadScorecard();
  }, [activeScorecard]);

  return (
    <div>
      {/* Domain Selector */}
      <select value={activeScorecard} onChange={(e) => setActiveScorecard(e.target.value as Scorecard)}>
        <option value="cbp_illegal_transshipment_v1">CBP Illegal Transshipment</option>
        <option value="fda_imports_fraud_v1">FDA Imports Fraud</option>
        <option value="opioid_detection_v1">Opioid Detection</option>
      </select>
      
      {/* Rest of page now uses scorecardConfig */}
    </div>
  );
}
```

### Step 2: Load Factors Dynamically

```typescript
// BEFORE: Hardcoded FACTOR_META
const FACTOR_META: Record<string, { label: string; color: string }> = {
  DOCUMENTATION_RISK: { ... },
  // ... 6 more hardcoded
};

// AFTER: Build from scorecard config
const FACTOR_META = useMemo(() => {
  if (!scorecardConfig) return {};
  
  return Object.fromEntries(
    scorecardConfig.factors.map(factor => [
      factor.id,
      {
        label: factor.id,
        sources: factor.sources,
        horizon: factor.horizon,
        color: getColorByHorizon(factor.horizon) // H1=red, H2=yellow, H3=gray
      }
    ])
  );
}, [scorecardConfig]);

// Function to color-code by horizon
const getColorByHorizon = (horizon: string) => {
  switch (horizon) {
    case 'H1': return 'text-[#D83933]';  // Red: Proven
    case 'H2': return 'text-amber-600';  // Yellow: Emerging
    case 'H3': return 'text-slate-600';  // Gray: Experimental
    default: return 'text-gray-600';
  }
};
```

### Step 3: Load Rules Dynamically

```typescript
// BEFORE: Hardcoded rules
const [rules, setRules] = useState({
  'W-121': true,
  'W-822': true,
  'UFLPA-301': true,
});

// AFTER: Load from scorecard config
useEffect(() => {
  if (!scorecardConfig) return;
  
  const initialRules = Object.fromEntries(
    scorecardConfig.rules.map(rule => [rule.ruleId, true])
  );
  setRules(initialRules);
}, [scorecardConfig]);

// In ScreeningRulesTab, dynamically render:
function ScreeningRulesTab({ rules, setRules, scorecardConfig }: any) {
  return (
    <div className="space-y-6">
      {/* Mandatory Rules */}
      <div className="bg-white rounded-sm border border-[#D0D7DE] shadow-sm overflow-hidden">
        <table className="w-full">
          <thead>...</thead>
          <tbody className="divide-y divide-[#E0E3E8]">
            {scorecardConfig.rules.map((rule) => (
              <tr key={rule.ruleId}>
                <td className="p-3 text-center">
                  <input
                    type="checkbox"
                    checked={rules[rule.ruleId]}
                    onChange={(e) => setRules({ ...rules, [rule.ruleId]: e.target.checked })}
                  />
                </td>
                <td className="p-3">
                  <span className="text-sm font-bold">{rule.ruleId}</span>
                </td>
                <td className="p-3">
                  <span className="text-xs text-gray-600">{rule.description || rule.ruleId}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
```

### Step 4: Load Thresholds Dynamically

```typescript
// BEFORE: Hardcoded gates in ModelMetrics display
{
  label: 'AUC-ROC', value: metrics.auc_roc, target: 0.75
}

// AFTER: Load from scorecard thresholds
<div className="space-y-3">
  {Object.entries(scorecardConfig.thresholds).map(([gateId, gateConfig]) => (
    <div key={gateId} className="flex justify-between items-center p-2 bg-[#F7F9FC] rounded-sm border border-[#E0E3E8]">
      <div>
        <p className="text-[10px] font-bold uppercase font-mono">
          {gateId.toUpperCase()}: {gateConfig.action}
        </p>
        <p className="text-[9px] text-gray-600">
          Score ≥ {gateConfig.score}
        </p>
      </div>
      <span className="text-lg font-bold font-mono">
        {gateConfig.score}
      </span>
    </div>
  ))}
</div>
```

---

## API Changes Required

### Current API

```typescript
// Current V2AITuningPage calls:
GET  /api/model/weights       // Returns {weights, config}
POST /api/model/weights       // Saves weights + config
GET  /api/model/metrics       // Returns model metrics
POST /api/rules/save          // Saves rule toggles
```

### New API

```typescript
// Scorecard endpoint (new)
GET /api/scorecards/{scorecard_id}
    Returns: {
      scorecard_id: "cbp_illegal_transshipment_v1",
      factors: [...],
      thresholds: {...},
      rules: [...]
    }

// Rule parameters endpoint (new)
GET    /api/rules/{rule_id}/parameters
       Returns: {
         rule_id: "W-121",
         parameters: {weight: 1.0, enabled: true, ...},
         version: 5,
         valid_from: "2026-03-15T16:00:00Z",
         valid_to: null,
         history: [...]
       }

POST   /api/rules/{rule_id}/parameters
       Body: {
         parameter_name: "weight",
         new_value: 1.2,
         version: 5,              // Optimistic concurrency
         analyst_id: "alice@cbp.gov",
         reason: "Q1 adjustment"
       }
       Returns: 200 OK or 409 Conflict

// Keep existing endpoints for backward compatibility
GET  /api/model/weights       // Now calls /api/rules/*/parameters
POST /api/model/weights       // Now calls /api/rules/*/parameters
GET  /api/model/metrics       // Unchanged
POST /api/rules/save          // Deprecated, but still works
```

---

## Implementation Checklist

### Phase 1: Foundation (Week 1)

- [ ] Create `ScorecardConfig` TypeScript interface
- [ ] Create `/api/scorecards/{scorecard_id}` endpoint
- [ ] Create `/api/rules/{rule_id}/parameters` GET/POST endpoints
- [ ] Add DuckDB schema for rule_parameters + rule_change_events
- [ ] Test: Fetch CBP scorecard, verify factors match hardcoded values
- [ ] Test: POST parameter change, verify optimistic concurrency rejection

### Phase 2: UI Refactoring (Week 2)

- [ ] Add scorecard selector dropdown
- [ ] Replace hardcoded FACTOR_META with dynamic loading
- [ ] Replace hardcoded rules with dynamic rendering
- [ ] Replace hardcoded thresholds with dynamic display
- [ ] Test: Switch between CBP and FDA, verify factors change
- [ ] Test: Concurrent edits from 2 analysts

### Phase 3: Gemini Integration (Week 3)

- [ ] Create `/api/gemini/suggest-rule` endpoint
- [ ] Add "Suggest Rule from Policy" button to V2AITuningPage
- [ ] UI shows suggestion card + analyst can approve/reject
- [ ] Approved rule added to v2.rules.yaml (requires code review)
- [ ] Test: Upload PDF, get suggestion, approve, see in V2AITuningPage

### Phase 4: Three Domains (Week 4)

- [ ] Create FDA Imports Fraud scorecard config
- [ ] Create Opioid Detection scorecard config
- [ ] Test each domain independently
- [ ] Test switching between domains
- [ ] Verify rules/weights/thresholds load correctly

---

## Code Diff Summary

### Files to Create

```
services/api/
├── routes/
│  ├── scorecards.py           (new)
│  ├── rule_parameters.py      (new)
│  └── gemini_suggestions.py   (new)
├── models/
│  ├── scorecard.py            (new)
│  ├── rule_parameter.py       (new)
│  └── rule_change_event.py    (new)
└── schema/
   ├── v2.rules.yaml           (new: define rule logic)
   ├── cbp_scorecard.json       (new: define factors/thresholds/rules)
   ├── fda_scorecard.json       (new)
   └── opioid_scorecard.json    (new)

ui/src/v2/
├── pages/
│  └── V2AITuningPage.tsx       (refactor: ~30 line changes)
└── components/
   └── GeminiRuleSuggestion.tsx (new)
```

### Files to Modify

```
ui/src/v2/pages/V2AITuningPage.tsx
├─ Line 1-10:   Add imports for ScorecardConfig, useEffect
├─ Line 25-50:  Replace hardcoded FACTOR_META with dynamic
├─ Line 69-95:  Add scorecard selector + state management
├─ Line 99-125: Replace hardcoded weights with dynamic loading
├─ Line 285-286:Replace hardcoded rules with dynamic rendering
└─ Total impact: ~50 lines changed (not rewrite)
```

---

## Backward Compatibility

### Keep Existing API Routes

```python
# services/api/routes/risk_models.py (existing)
@app.post('/api/model/weights')
def save_weights(body):
    # Translate to new format
    for rule_id in body.rules:
        update_rule_parameter(rule_id, 'enabled', body.rules[rule_id])
    # Still works, just routes to new endpoints
```

### Prevent Breaking V2 Tests

- Old API: `POST /api/model/weights` still works
- New API: `POST /api/rules/{rule_id}/parameters` is the source of truth
- Migration: Tests gradually move to new endpoints

---

## Horizon-Based Coloring

With three horizons (H1/H2/H3), factors should be visually distinguished:

```typescript
// ModelWeightsTab shows factors by horizon
<div className="grid grid-cols-3 gap-4">
  <div>
    <h4 className="font-bold text-red-600">H1 - Proven (Fixed)</h4>
    {/* DOCUMENTATION_RISK, ROUTING_RISK, PARTY_RISK */}
    <p className="text-xs text-gray-600">Quarterly review only</p>
  </div>
  <div>
    <h4 className="font-bold text-amber-600">H2 - Emerging (Monitored)</h4>
    {/* CORRIDOR_RISK, TIME_SENSITIVITY */}
    <p className="text-xs text-gray-600">Monthly tuning allowed</p>
  </div>
  <div>
    <h4 className="font-bold text-slate-600">H3 - Experimental (Shadow)</h4>
    {/* PATTERN_RISK */}
    <p className="text-xs text-gray-600">Not in production decision</p>
  </div>
</div>
```

---

## Example: Switching from CBP to FDA

```
User clicks: Domain selector [CBP ▼]
    ↓ Choose "FDA Imports Fraud"
    ↓
GET /api/scorecards/fda_imports_fraud_v1
    ↓ Returns:
    {
      factors: [
        {id: "IMPORTER_LEGITIMACY", weight: 0.30, horizon: "H1", ...},
        {id: "PRODUCT_COMPLIANCE", weight: 0.25, horizon: "H1", ...},
        ...
      ],
      rules: [
        {ruleId: "FDA-RECALL-MATCH", priority: 1, ...},
        {ruleId: "FDA-UNREGISTERED-IMPORTER", priority: 2, ...}
      ],
      thresholds: {
        gate1: {score: 40, action: "enhanced_inspection"},
        gate2: {score: 70, action: "escalate_to_compliance_officer"}
      }
    }
    ↓
V2AITuningPage re-renders:
  ├─ Model Weights Tab: Now shows 5 factors instead of 7
  │  └─ Sliders: IMPORTER_LEGITIMACY (30%), PRODUCT_COMPLIANCE (25%), ...
  ├─ Screening Rules Tab: Now shows FDA-RECALL-MATCH, FDA-UNREGISTERED-IMPORTER
  └─ Configuration Tab: Thresholds are 40 and 70 (not 30, 60, 80)

All done in <500ms, no code deployment needed.
```

---

## Test Scenarios

### Scenario 1: Single Analyst Tuning CBP

```
1. Open V2AITuningPage
2. Domain selector defaults to "CBP Illegal Transshipment"
3. See 7 factors with weights summing to 100%
4. Adjust W-121 weight: 1.0 → 1.2
5. Click "Apply Changes"
6. Verify: rule_parameters updated, version incremented, event logged
7. Refresh page
8. Verify: new weight persists
```

### Scenario 2: Concurrent Edits (Analyst A & B)

```
1. Both fetch CBP scorecard (v1)
2. Analyst A adjusts W-121: 1.0 → 1.2, submits
   ├─ Backend: version 5 → 6
   └─ Success
3. Analyst B adjusts W-121: 1.0 → 0.9, submits
   ├─ Backend: expects version 5, finds 6
   └─ 409 Conflict
4. Analyst B sees: "Rule modified by Analyst A at 14:22"
5. Analyst B clicks "Refresh & Retry"
6. Analyst B re-fetches (version now 6, weight now 1.2)
7. Analyst B adjusts: 1.2 → 1.0, submits
   ├─ Backend: version 6 → 7
   └─ Success
```

### Scenario 3: Domain Switch

```
1. Open V2AITuningPage (CBP loaded)
2. Select "FDA Imports Fraud" from dropdown
3. Page re-renders:
   ├─ Factors change: 7 → 5
   ├─ Rules change: W-121, W-822, UFLPA-301 → FDA-RECALL-MATCH, FDA-UNREGISTERED-IMPORTER
   ├─ Thresholds change: 30/60/80 → 40/70
   └─ Weights reset to FDA defaults (30%, 25%, 20%, 15%, 10%)
4. Analyst adjusts FDA weights
5. Switch back to CBP
   ├─ See CBP factors again
   ├─ Weights are what analyst set before (not lost)
   └─ FDA changes are saved independently
```

### Scenario 4: Gemini Suggestion

```
1. Click "Suggest Rule from Policy"
2. Upload "49_CFR_19_ImporterRequirements.pdf"
3. Gemini processes, suggests:
   {
     rule_id: "W-124-SUGGESTED",
     condition: "shipment_origin IN ['CN','VN'] AND ...",
     base_risk_points: 30,
     horizon: "H2",
     confidence: 0.87
   }
4. Analyst reviews, edits condition if needed
5. Analyst clicks "Approve"
6. System:
   ├─ Adds rule to v2.rules.yaml
   ├─ Creates GitHub PR (requires code review)
   ├─ Once merged, rule appears in V2AITuningPage
   └─ Analyst can now tune W-124 weight/threshold
```

