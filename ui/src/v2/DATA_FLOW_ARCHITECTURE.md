# Investigation Workspace — Data Flow Architecture

## Problem: How does updated risk_score cascade across tabs?

When a shipment's risk_score is refined by Altana (82 → 87), the entire investigation workspace must reflect this change:
- Overview tab: risk bar updates, anomaly matrix recalculates
- AI Findings tab: new Altana-discovered signals appear
- Evidence & Referral tab: audit trail shows refinement
- Shipments tab: shipment card updates
- Case-level metrics: case_risk_score recalculates

---

## Current Data Flow (Simplified)

```
API: /api/data/cases → useV2Cases() → V2InvestigationsPage
       ↓
  V2InvestigationsPage.selectedCase
       ├→ Overview tab (displays case.risk_score as number)
       ├→ Entities tab (displays entities linked to case)
       ├→ Shipments tab (displays case shipments)
       ├→ AI Findings tab (displays findings array)
       └→ Evidence & Referral tab (displays referral_package)
```

**Problem**: If a shipment's risk_score updates due to Altana validation, the case doesn't know about it. Tabs don't re-render with new data.

---

## Proposed Data Flow (With Altana Validation)

```
STEP 1: Initial Shipment Scoring
┌─────────────────────────────────────────────────────┐
│ API: GET /api/data/shipments/{id}                   │
│ Returns:                                             │
│ {                                                    │
│   shipment_id: "SHP-000731",                         │
│   manifest_anomalies: ["ELEMENT9_MISMATCH"],         │
│   risk_score: 82,                 ← Model initial    │
│   risk_breakdown: {                                  │
│     components: [                                    │
│       {component: "Documentation", score: 9, ...},  │
│       ...                                            │
│     ],                                               │
│     subtotal: 80.8,                                  │
│     final_score: 82.0                                │
│   }                                                  │
│ }                                                    │
└─────────────────────────────────────────────────────┘
       ↓
STEP 2: Altana Validation (if score >= 80)
┌─────────────────────────────────────────────────────┐
│ API: POST /api/altana/validate                       │
│ Payload: {shipment_id, risk_score: 82, ...}        │
│ Returns:                                             │
│ {                                                    │
│   altana_query: true,                                │
│   altana_response: {                                 │
│     confidence: 92,                                  │
│     risk_factors: [                                  │
│       "sanctioned_supplier_detected",                │
│       "high_transshipment_risk"                      │
│     ],                                               │
│     recommendation: "HOLD_FOR_EXAMINATION"           │
│   },                                                 │
│   model_adjustment: +5,            ← Altana agrees   │
│   final_risk_score: 87.0,          ← Updated score   │
│   audit_trail: {                                     │
│     timestamp: "2025-05-22T14:32:00Z",              │
│     initial_score: 82,                               │
│     altana_confidence: 92,                           │
│     adjustment_reason: "Altana validated...",        │
│     final_score: 87                                  │
│   }                                                  │
│ }                                                    │
└─────────────────────────────────────────────────────┘
       ↓
STEP 3: Case-Level Aggregation
┌─────────────────────────────────────────────────────┐
│ Recalculate Case Risk:                               │
│                                                      │
│ Case has 3 shipments:                                │
│   - SHP-000731: 87 (HIGH)          ← Updated!       │
│   - SHP-000732: 72 (MEDIUM)                          │
│   - SHP-000733: 65 (MEDIUM)                          │
│                                                      │
│ case_risk_score = max(87, 72, 65) = 87              │
│ OR weighted avg: (87×0.5 + 72×0.25 + 65×0.25) = 79  │
│                                                      │
│ → Case priority potentially changes (CRITICAL)      │
│ → Case SLA timer resets if escalated                │
│ → Anomaly matrix recalculates                        │
└─────────────────────────────────────────────────────┘
       ↓
STEP 4: Tab-Specific Updates
┌──────────────────────────────────────────────────────────┐
│ OVERVIEW TAB                                              │
│ ├─ Risk bar: 87/100 (was 82, now RED)                    │
│ ├─ Confidence badge: "87.0±1.5" (Altana refined)        │
│ ├─ Core Anomaly Matrix:                                  │
│ │  ├─ Origination Country Mismatch: 9.0 (was 8.5)        │
│ │  ├─ (recalculated with new Altana factors)             │
│ ├─ Corridor Risk: CN→US with Altana multiplier badge     │
│ └─ Validation badge: "✓ Altana Verified (92% conf.)"    │
│                                                            │
│ AI FINDINGS TAB                                           │
│ ├─ Original findings: ISF_MISMATCH, DWELL_ANOMALY        │
│ ├─ New Altana findings:                                   │
│ │  ├─ "Sanctioned Supplier Detected" [CRITICAL]          │
│ │  ├─ "High Transshipment Risk" [HIGH]                   │
│ │  └─ "Supply Chain Opacity Flagged" [MEDIUM]            │
│ └─ Each finding shows: Accept/Reject buttons + evidence   │
│                                                            │
│ SHIPMENTS TAB                                             │
│ ├─ Shipment list sorted by new risk scores               │
│ ├─ SHP-000731: Risk 87 (was 82) - CRITICAL               │
│ ├─ Each shipment shows:                                   │
│ │  ├─ Risk score with confidence interval                │
│ │  ├─ "Altana Refined" badge if score changed            │
│ │  └─ Audit trail link (shows validation details)        │
│                                                            │
│ EVIDENCE & REFERRAL TAB                                   │
│ ├─ Referral packet shows:                                 │
│ │  ├─ Risk Scoring Breakdown:                             │
│ │  │  ├─ Component scores (Documentation 22.5, etc.)     │
│ │  │  ├─ Subtotal: 80.8                                   │
│ │  │  ├─ Country-of-Origin Adjustment: +3.2              │
│ │  │  ├─ Altana Supply Chain Flag: +2.0                  │
│ │  │  └─ FINAL: 87.0/100                                  │
│ │  ├─ Validation Audit Trail:                             │
│ │  │  ├─ Initial Model Score: 82.0                        │
│ │  │  ├─ Altana Query: Yes (confidence 92%)              │
│ │  │  ├─ Altana Factors: sanctioned_supplier, ...         │
│ │  │  ├─ Adjustment: +5 (Altana agreed)                   │
│ │  │  └─ Final Score: 87.0                                │
│ │  └─ DHS Submission Shows All Details                    │
└──────────────────────────────────────────────────────────┘
```

---

## Implementation: How Tabs Stay Synchronized

### Option A: Unified Case Context (Recommended)

```typescript
// In V2InvestigationsPage.tsx

interface CaseContext {
  case: Case;
  shipments: ShipmentWithScoreBreakdown[];  // ← Includes risk_breakdown + audit_trail
  findings: AIFinding[];                     // ← May include Altana-discovered signals
  riskMetrics: {
    case_risk_score: number;                 // ← Max of shipment risks
    confidence_interval: string;             // ← From Altana
    altana_agreement: boolean;
    adjustment_reason: string;
  };
  auditTrail: AuditEvent[];                  // ← All score changes with timestamps
}

// Each tab reads from CaseContext, re-renders when any property changes
export default function V2InvestigationsPage() {
  const { selectedCaseId } = ...;
  
  // Fetch case + all related data
  const [caseContext, setCaseContext] = useState<CaseContext>(null);
  
  useEffect(() => {
    // When selectedCaseId changes, fetch full context
    fetchCaseContext(selectedCaseId).then(context => {
      setCaseContext(context);
      
      // Trigger real-time updates every 30s (Altana validation in progress?)
      const interval = setInterval(() => {
        checkForUpdates(selectedCaseId).then(updates => {
          if (updates.risk_score_changed) {
            // Shipment risk updated → cascade change
            setCaseContext(prev => ({
              ...prev,
              shipments: prev.shipments.map(s =>
                s.shipment_id === updates.shipment_id
                  ? {...s, ...updates.shipment_data}
                  : s
              ),
              riskMetrics: {
                ...prev.riskMetrics,
                case_risk_score: Math.max(...prev.shipments.map(s => s.risk_score))
              }
            }));
          }
        });
      }, 30000);
      
      return () => clearInterval(interval);
    });
  }, [selectedCaseId]);
  
  // All tabs access caseContext
  return (
    <>
      {activeSubTab === 'Overview' && <OverviewTab caseContext={caseContext} />}
      {activeSubTab === 'Entities' && <EntitiesTab caseContext={caseContext} />}
      {activeSubTab === 'Shipments' && <ShipmentsTab caseContext={caseContext} />}
      {activeSubTab === 'Findings' && <FindingsTab caseContext={caseContext} />}
      {activeSubTab === 'Evidence & Referral' && <EvidenceTab caseContext={caseContext} />}
    </>
  );
}
```

### Option B: Event-Driven Updates (Alternative)

```typescript
// Emit score update event → all tabs listen

const scoreUpdateEvent = new CustomEvent('shipment-score-updated', {
  detail: {
    shipment_id: 'SHP-000731',
    old_score: 82,
    new_score: 87,
    reason: 'Altana validation',
    audit_trail: {...}
  }
});

// Each tab listens:
// OverviewTab.tsx
useEffect(() => {
  window.addEventListener('shipment-score-updated', (e) => {
    // Update local state → re-render risk bar
    updateRiskBar(e.detail.new_score);
  });
}, []);
```

---

## Tab-Specific Rendering Updates

### 1. OVERVIEW TAB

**What changes when shipment risk_score updates?**

```tsx
// Before: case.risk_score = 82
// After: case.risk_score = 87 (recalculated from shipments)

<section className="risk-score-section">
  {/* Risk Bar */}
  <div className="w-32 h-8 bg-gray-200 rounded-full overflow-hidden">
    <div
      className={`h-full transition-all ${
        caseContext.riskMetrics.case_risk_score >= 80 
          ? 'bg-[#D83933]'  // RED
          : 'bg-[#FFBE2E]'  // YELLOW
      }`}
      style={{width: `${caseContext.riskMetrics.case_risk_score}%`}}
    />
  </div>
  
  {/* Score Display */}
  <span className="text-2xl font-black">
    {caseContext.riskMetrics.case_risk_score}
  </span>
  /100
  
  {/* Confidence with Altana badge */}
  <span className="text-xs text-slate-500">
    {caseContext.riskMetrics.confidence_interval}
    {caseContext.riskMetrics.altana_agreement && (
      <span className="ml-2 px-2 py-1 bg-cyan-100 text-cyan-700 rounded text-[9px]">
        ✓ Altana Verified
      </span>
    )}
  </span>
  
  {/* Adjustment Reason */}
  {caseContext.riskMetrics.adjustment_reason && (
    <div className="text-[10px] text-slate-600 mt-1">
      {caseContext.riskMetrics.adjustment_reason}
    </div>
  )}
</section>

{/* Core Anomaly Matrix — recalculated from shipment data */}
<section className="anomaly-matrix">
  {caseContext.shipments[0].manifest_anomalies.map((anomaly, i) => (
    <div key={i} className="flex justify-between">
      <span>{anomalyLabel(anomaly)}</span>
      <span className={`font-bold ${getRiskColor(anomaly)}`}>
        {getComponentScore(anomaly, caseContext)}
      </span>
    </div>
  ))}
</section>

{/* Validation Audit Trail */}
<section className="audit-trail">
  <div className="text-xs font-mono text-slate-600">
    Initial Model Score: {caseContext.auditTrail[0].initial_score}
    <br/>
    Altana Query: {caseContext.shipments[0].audit_trail.altana_query ? 'Yes' : 'No'}
    <br/>
    Altana Confidence: {caseContext.shipments[0].audit_trail.altana_confidence}%
    <br/>
    Final Score: {caseContext.riskMetrics.case_risk_score}
  </div>
</section>
```

### 2. AI FINDINGS TAB

**New findings appear after Altana validation:**

```tsx
// Original findings (from H2 signals)
const originalFindings = caseContext.findings.filter(f => f.source === 'h2_signals');

// Altana-discovered findings (from Altana API response)
const altanaFindings = caseContext.findings.filter(f => f.source === 'altana_validation');

return (
  <>
    {/* H2 Signal Findings */}
    <div className="space-y-4">
      <h3 className="font-bold text-sm">Detected Anomalies</h3>
      {originalFindings.map(finding => (
        <FindingCard
          finding={finding}
          onStatusChange={(status) => updateFinding(finding.id, status)}
        />
      ))}
    </div>
    
    {/* Altana-Validated Findings */}
    {altanaFindings.length > 0 && (
      <div className="space-y-4 border-t pt-4 mt-4">
        <div className="flex items-center gap-2">
          <span className="text-xs font-bold text-cyan-600">
            ALTANA SUPPLY CHAIN VALIDATION
          </span>
          <span className="px-2 py-0.5 bg-cyan-100 text-cyan-700 rounded text-[9px]">
            {caseContext.shipments[0].audit_trail.altana_confidence}% confidence
          </span>
        </div>
        
        {altanaFindings.map(finding => (
          <FindingCard
            finding={finding}
            badge="VERIFIED"
            badgeColor="bg-cyan-100 text-cyan-700"
            onStatusChange={(status) => updateFinding(finding.id, status)}
          />
        ))}
      </div>
    )}
  </>
);
```

### 3. SHIPMENTS TAB

**Shipments re-sort and show audit trail:**

```tsx
// Sort by updated risk scores (highest first)
const sortedShipments = [...caseContext.shipments].sort(
  (a, b) => b.risk_score - a.risk_score
);

return (
  <div className="space-y-2">
    {sortedShipments.map(shipment => (
      <div
        key={shipment.shipment_id}
        className="border p-3 rounded hover:bg-blue-50 cursor-pointer"
      >
        <div className="flex justify-between items-center">
          <span className="font-bold">{shipment.shipper_name}</span>
          
          {/* Risk score with change indicator */}
          <div className="flex items-center gap-2">
            <span className="text-xl font-black">
              {shipment.risk_score}
            </span>
            
            {shipment.audit_trail?.initial_score !== shipment.risk_score && (
              <span className="text-[9px] font-mono text-slate-600">
                was {shipment.audit_trail.initial_score} → Altana refined
              </span>
            )}
          </div>
        </div>
        
        {/* Audit trail preview */}
        {shipment.audit_trail && (
          <div className="text-[10px] text-slate-600 mt-1">
            <span className="bg-cyan-50 px-1 rounded">
              {shipment.audit_trail.altana_confidence}% Altana confidence
            </span>
          </div>
        )}
      </div>
    ))}
  </div>
);
```

### 4. EVIDENCE & REFERRAL TAB

**Referral package displays full scoring breakdown with Altana refinement:**

```tsx
return (
  <div className="grid grid-cols-3 gap-6">
    {/* Left: Checkbox sections */}
    <div className="space-y-3">
      <h3 className="text-xs font-bold uppercase">Statutory Sections</h3>
      {/* checkboxes */}
    </div>
    
    {/* Right: Dark narrative editor */}
    <div className="col-span-2 bg-[#0B1F33] text-slate-100 rounded p-4">
      <div className="text-[10px] font-mono text-cyan-400 uppercase mb-4">
        OFFICIAL DHS GENERAL COUNSEL TRADE FRAUD COMPLIANCE DRAFT
      </div>
      
      {/* SCORING BREAKDOWN SECTION (NEW) */}
      <div className="mb-6 p-3 border border-cyan-900 rounded">
        <div className="text-[10px] font-bold text-cyan-400 mb-2">
          RISK SCORING METHODOLOGY
        </div>
        
        {/* Component breakdown */}
        <table className="w-full text-[9px] font-mono mb-3">
          <thead className="border-b border-cyan-900">
            <tr className="text-cyan-400">
              <th className="text-left">Category</th>
              <th className="text-right">Weight</th>
              <th className="text-right">Score</th>
              <th className="text-right">Result</th>
            </tr>
          </thead>
          <tbody className="text-slate-300">
            {caseContext.shipments[0].risk_breakdown.components.map((comp, i) => (
              <tr key={i} className="border-b border-cyan-950">
                <td>{comp.component}</td>
                <td className="text-right">{comp.weight}%</td>
                <td className="text-right">{comp.score.toFixed(1)}</td>
                <td className="text-right text-cyan-400">
                  {comp.weighted_result.toFixed(1)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        
        <div className="border-t border-cyan-900 pt-2 text-[9px] text-slate-300">
          <div className="flex justify-between">
            <span>Subtotal (Pre-Adjustment)</span>
            <span className="text-cyan-400">
              {caseContext.shipments[0].risk_breakdown.subtotal.toFixed(1)}
            </span>
          </div>
          
          {/* Corridor adjustment */}
          {caseContext.shipments[0].risk_breakdown.corridor_risk_adjustment && (
            <div className="flex justify-between mt-1">
              <span>Country-of-Origin Multiplier</span>
              <span className="text-cyan-400">
                +{caseContext.shipments[0].risk_breakdown.corridor_risk_adjustment.adjustment_points.toFixed(1)}
              </span>
            </div>
          )}
          
          {/* Altana adjustment */}
          {caseContext.shipments[0].audit_trail?.altana_query && (
            <div className="flex justify-between mt-1">
              <span>Altana Supply Chain Validation</span>
              <span className="text-cyan-400">
                {caseContext.shipments[0].audit_trail.model_adjustment > 0 ? '+' : ''}
                {caseContext.shipments[0].audit_trail.model_adjustment}
              </span>
            </div>
          )}
          
          {/* Final score */}
          <div className="flex justify-between mt-2 pt-2 border-t border-cyan-900 font-bold text-cyan-400">
            <span>FINAL RISK SCORE</span>
            <span>{caseContext.riskMetrics.case_risk_score.toFixed(1)}/100</span>
          </div>
        </div>
      </div>
      
      {/* VALIDATION AUDIT TRAIL SECTION (NEW) */}
      {caseContext.shipments[0].audit_trail && (
        <div className="mb-6 p-3 border border-cyan-900 rounded">
          <div className="text-[10px] font-bold text-cyan-400 mb-2">
            ALTANA VALIDATION AUDIT TRAIL
          </div>
          
          <div className="text-[9px] text-slate-300 space-y-1 font-mono">
            <div>
              Model Initial Assessment: {caseContext.shipments[0].audit_trail.initial_score}/100
            </div>
            <div>
              Altana Query Triggered: {caseContext.shipments[0].audit_trail.altana_query ? 'YES' : 'NO'}
            </div>
            {caseContext.shipments[0].audit_trail.altana_confidence && (
              <div>
                Altana Confidence Level: {caseContext.shipments[0].audit_trail.altana_confidence}%
              </div>
            )}
            {caseContext.shipments[0].audit_trail.altana_response?.risk_factors && (
              <div>
                Altana Risk Factors:
                <ul className="ml-4">
                  {caseContext.shipments[0].audit_trail.altana_response.risk_factors.map((f, i) => (
                    <li key={i}>• {f}</li>
                  ))}
                </ul>
              </div>
            )}
            <div className="text-cyan-400">
              Final Assessment: {caseContext.riskMetrics.case_risk_score}/100
              ({caseContext.shipments[0].audit_trail.adjustment_reason})
            </div>
          </div>
        </div>
      )}
      
      {/* Narrative editor below */}
      <textarea
        className="w-full bg-transparent border border-cyan-900 text-xs text-slate-100 font-mono p-2 rounded mt-4"
        value={narrative}
        onChange={(e) => setNarrative(e.target.value)}
        placeholder="Draft your findings here..."
      />
    </div>
  </div>
);
```

---

## Backend API Changes Required

### 1. Enhanced Shipment Response

```json
GET /api/data/shipments/{shipment_id}

{
  "shipment_id": "SHP-000731",
  "manifest_anomalies": ["ELEMENT9_MISMATCH", "DWELL_ANOMALY"],
  
  "risk_score": 87,
  "risk_breakdown": {
    "components": [
      {
        "component": "Documentation Risk",
        "factor": "documentation",
        "score": 9.0,
        "weight": 25.0,
        "weighted_result": 22.5,
        "rationale": "Element 9 mismatch detected"
      },
      ...
    ],
    "subtotal": 80.8,
    "corridor_risk_adjustment": {
      "baseline": 8.5,
      "multiplier": 1.3,
      "adjustment_points": 3.2,
      "reason": "CN→US origin concealment corridor"
    },
    "final_score": 87.0,
    "confidence_interval": "87.0±1.5"
  },
  
  "audit_trail": {
    "initial_score": 82.0,
    "altana_query": true,
    "altana_confidence": 92,
    "altana_response": {
      "risk_factors": ["sanctioned_supplier_detected", "high_transshipment_risk"],
      "recommendation": "HOLD_FOR_EXAMINATION"
    },
    "model_adjustment": +5,
    "final_risk_score": 87.0,
    "adjustment_reason": "Altana validated supply chain risks",
    "timestamp": "2025-05-22T14:32:00Z"
  }
}
```

### 2. Enhanced Case Response

```json
GET /api/data/cases/{case_id}

{
  "case_id": "CASE-2025-001",
  "case_name": "Aluminum Tariff Evasion - Greenfield Industrial",
  
  "risk_score": 87,  // ← Max of shipment risks
  "risk_metrics": {
    "case_risk_score": 87,
    "confidence_interval": "87.0±1.5",
    "altana_agreement": true,
    "adjustment_reason": "Shipment SHP-000731 validated by Altana supply chain analysis"
  },
  
  "shipments": [
    { ...shipment_data_with_breakdown_and_audit_trail },
    ...
  ],
  
  "findings": [
    {
      "id": "FINDING-001",
      "title": "Element 9 Declaration Violation",
      "source": "h2_signals",
      "severity": "CRITICAL",
      ...
    },
    {
      "id": "FINDING-002",
      "title": "Sanctioned Supplier Detected",
      "source": "altana_validation",  // ← New source
      "severity": "CRITICAL",
      "altana_confidence": 92,
      "evidence": ["Altana supply chain API"]
      ...
    }
  ],
  
  "auditTrail": [
    {
      "timestamp": "2025-05-22T14:15:00Z",
      "event": "case_created",
      "initial_risk_score": 82
    },
    {
      "timestamp": "2025-05-22T14:32:00Z",
      "event": "shipment_score_updated",
      "shipment_id": "SHP-000731",
      "old_score": 82,
      "new_score": 87,
      "reason": "Altana validation",
      "altana_confidence": 92
    }
  ]
}
```

---

## Summary: Tab Update Flow

| Tab | Triggers Re-render On | What Updates |
|-----|----------------------|--------------|
| **Overview** | shipment risk_score changes | Risk bar color/width, confidence badge, anomaly matrix scores, audit trail |
| **Entities** | new findings from Altana | Entity risk levels, connected entities with new risk factors |
| **Shipments** | shipment audit_trail updates | Sort order (by new risk), display "was X → now Y", Altana confidence badges |
| **Findings** | new Altana findings added | New "ALTANA SUPPLY CHAIN VALIDATION" section with verified findings |
| **Evidence & Referral** | risk_breakdown + audit_trail | Detailed scoring breakdown table, Altana adjustment line items, final score |

**All triggered by**: `shipment.audit_trail.altana_query = true` and `shipment.audit_trail.model_adjustment != 0`

