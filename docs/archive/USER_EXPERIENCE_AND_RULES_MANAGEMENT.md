# User Experience & Rules Management System — CBP Sentry

**Date:** June 12, 2026  
**Purpose:** Document current UX implementation, rules management interface, and data management  
**Status:** Partially implemented (UI framework exists, rules management needs admin panel)

---

## PART 1: CURRENT UI IMPLEMENTATION STATUS

### 1.1 What's Built (Pages & Components)

**Implemented Pages (React/TypeScript):**

```
✅ ModernCaseInvestigationPage.tsx (14KB)
├─ Primary interface for CBP officer to review cases
├─ Features:
│  ├─ Case overview (shipper, consignee, HTS code, value)
│  ├─ Risk score breakdown (7-factor visualization)
│  ├─ Collapsible sections (overview, scoring, actions)
│  ├─ Feedback interface (officer confirms/flags outcome)
│  ├─ Altana verification panel (ISF validation)
│  └─ Referral package generation tab
├─ State management: React hooks (useState, useEffect)
├─ API integration: Calls `/api/score/full-breakdown/{shipmentId}` for risk calculation
└─ Current: WORKING for single shipment investigation

✅ ManifestRiskQueuePage.tsx (12KB)
├─ Queue of high-risk shipments for officer review
├─ Features:
│  ├─ Risk queue (sorted by score, highest first)
│  ├─ Quick-view cards (score, shipper, commodity)
│  ├─ Filter by risk level (LOW, MEDIUM, HIGH, CRITICAL)
│  ├─ Bulk actions (mark reviewed, export, etc.)
│  └─ Real-time updates (WebSocket, future)
├─ Current: PARTIALLY IMPLEMENTED (UI ready, live updates pending)

✅ ScoringCalibrationPage.tsx (15KB)
├─ Officer tools to validate and tune scoring
├─ Features:
│  ├─ Historical case analysis (backtest results)
│  ├─ PPV by score bin (e.g., "80-90" → 78% actual)
│  ├─ Confidence calibration chart
│  ├─ Threshold adjustment sliders
│  └─ A/B test runner (compare models)
├─ Current: UI BUILT, backend APIs not wired

✅ CBPOfficerDashboard.tsx (7.2KB)
├─ Executive summary for CBP leadership
├─ Features:
│  ├─ KPIs: Referrals/week, PPV, AUC, data quality
│  ├─ Trend charts (PPV over time, referral volume)
│  ├─ Anomaly alerts (model drift, data quality issues)
│  └─ System health (uptime, latency, error rate)
├─ Current: FRAMEWORK READY, needs real data connection

✅ CommandCenterPage.tsx (7.4KB)
├─ Operations control room
├─ Features:
│  ├─ Live processing status (shipments processed/hour)
│  ├─ Pipeline monitoring (ingest → scoring → referral)
│  ├─ Alert management (data quality, model issues)
│  └─ Manual controls (pause scoring, emergency threshold)
├─ Current: UI READY, backend monitoring APIs pending

✅ IngestPage.tsx (8.2KB)
├─ Upload CBP manifest Excel files
├─ Features:
│  ├─ File picker + drag-and-drop
│  ├─ Progress bar (parsing progress)
│  ├─ Validation feedback (field errors, warnings)
│  └─ Preview of extracted data
├─ Current: WORKING END-TO-END

✅ ReferralPackageGenerationTab (component in ModernCaseInvestigationPage)
├─ Generate 14-section referral package for officer review
├─ Features:
│  ├─ Section-by-section builder (collapsible cards)
│  ├─ Edit narratives (LLM-generated, editable)
│  ├─ Export as PDF
│  ├─ Save to database
│  └─ Email delivery to CBP inbox
├─ Current: WORKING (tested with sample shipments)

✅ ShipmentsHubPage.tsx (15KB)
├─ Search & filter interface for shipments
├─ Features:
│  ├─ Search by shipper, consignee, HTS code
│  ├─ Filter by risk level, date range, status
│  ├─ Column sorting (score, date, value)
│  ├─ Pagination (100 results per page)
│  └─ Bulk select (select multiple, export)
├─ Current: WORKING

✅ V2 Module (Modern UI 2.0)
├─ Alternative modern interface (newer design)
├─ Pages:
│  ├─ V2DashboardPage (exec dashboard, updated design)
│  ├─ V2InvestigationsPage (case queue, modern layout)
│  ├─ V2ReferralsPage (referral package management)
│  ├─ V2EntityResolutionPage (entity network visualization)
│  └─ V2ShippingIntelligencePage (trade intelligence)
├─ Status: UI BUILT, still integrating APIs
```

---

### 1.2 Component Architecture

```
COMPONENT HIERARCHY:

App.tsx (entry point)
├─ Router (React Router v6)
│  ├─ /dashboard → CBPOfficerDashboard
│  ├─ /queue → ManifestRiskQueuePage
│  ├─ /cases/:shipmentId → ModernCaseInvestigationPage
│  ├─ /shipments → ShipmentsHubPage
│  ├─ /calibration → ScoringCalibrationPage
│  ├─ /command-center → CommandCenterPage
│  └─ /ingest → IngestPage
│
├─ RoleContext (authentication, user role)
│  ├─ Role: OFFICER, ANALYST, ADMIN
│  ├─ Permissions: view, edit, approve referrals
│  └─ Status: FRAMEWORK EXISTS (auth backend not implemented)
│
└─ Components (Reusable)
   ├─ Layout
   │  ├─ USWDSLayout (U.S. Web Design System layout)
   │  ├─ Header (navigation, user menu)
   │  └─ Sidebar (nav menu, collapsible)
   │
   ├─ Shared
   │  ├─ RiskGauge (visual risk score gauge)
   │  ├─ ConfidenceBar (confidence interval visualization)
   │  ├─ CollapsibleSection (expand/collapse detail)
   │  └─ LoadingSpinner, ErrorMessage
   │
   ├─ Risk Scoring
   │  ├─ RiskScoreBreakdown (7-factor component visualization)
   │  ├─ RiskHeatmap (visual matrix of scores)
   │  ├─ AnomalyChecklist (flags anomalies with checkboxes)
   │  └─ FeedbackInterface (confirm/flag outcome)
   │
   ├─ Referral Generation
   │  ├─ ReferralPackageGenerationTab (14-section builder)
   │  ├─ ReferralPackageGuide (walkthrough for officers)
   │  ├─ SectionEditor (edit individual sections)
   │  └─ NarrativeEditor (edit LLM narratives)
   │
   ├─ Entity Resolution
   │  ├─ EntityRelationshipGraph (SVG network diagram)
   │  ├─ EntityNetworkGraph (interactive force-directed)
   │  ├─ EntityRiskDashboard (entity-level risk view)
   │  └─ V2EntityResolutionPanel (modern entity display)
   │
   └─ Data Visualization
      ├─ CommodityRiskMatrix (heatmap by commodity)
      ├─ TradeCorridorMap (geographical corridor display)
      ├─ InvestigationTimeline (case history timeline)
      ├─ DataTable (generic sortable table)
      └─ CorridorSummaryCard (quick-glance corridor info)

STYLING:
├─ Tailwind CSS (utility-first)
├─ USWDS Design Tokens (government standard colors)
│  ├─ Navy: #013060
│  ├─ Teal: #4AC4D3
│  ├─ Orange: #E6800C
│  └─ [6+ more official colors]
├─ Custom CSS (CompactDashboard.css, etc.)
└─ Responsive (mobile, tablet, desktop breakpoints)
```

---

### 1.3 Current Data Flow (Officer Workflow)

```
WORKFLOW: Manifest Received → Investigation → Referral → Outcome

DAY 0: MANIFEST ARRIVES
├─ CBP manifest (Excel) uploaded via secure email
├─ IngestPage processes file (validation, parsing)
├─ Data stored in SQLite/PostgreSQL (shipments table)
└─ Officer gets notification: "3 new high-risk shipments"

DAY 1: OFFICER REVIEWS QUEUE
├─ Officer opens ManifestRiskQueuePage
├─ Sees 3 shipments sorted by score:
│  ├─ SHP-001: 87/100 [HIGH RISK]
│  ├─ SHP-002: 62/100 [MEDIUM RISK]
│  └─ SHP-003: 45/100 [LOW RISK]
│
├─ Officer clicks SHP-001 → Navigates to ModernCaseInvestigationPage

DAY 1-2: DETAILED INVESTIGATION
├─ Officer sees case overview (shipper: "Greenfield", origin: "China", HTS: "7604.10")
├─ Risk score breakdown displayed:
│  ├─ Documentation Risk: 40/40 (Element 9 mismatch!)
│  ├─ Commodity Risk: 30/35 (aluminum, AD rate 14.5%)
│  ├─ Routing Anomalies: 25/25 (dwell 11 days, 3.5x baseline)
│  ├─ Party Profile: 10/15 (shipper 1.8yr old, opacity concerns)
│  ├─ Corridor Risk: 10/10 (China→US aluminum, high-risk)
│  ├─ Pattern Anomaly: 15/15 (pricing 12% below market)
│  └─ Time Sensitivity: 12/15 (pre-tariff timing)
│
├─ Officer clicks "Generate Referral Package"
│  └─ System calls /api/referral/{shipmentId}
│  └─ Returns 14-section package (in ~3 seconds)
│
├─ Officer reviews package in ReferralPackageGenerationTab
│  ├─ Sections 3-1 to 3-14 displayed as collapsible cards
│  ├─ Officer can edit narratives (e.g., 3-6: Historical Pattern)
│  ├─ Officer adds notes ("Entity relationship confirms shell company")
│  └─ Officer clicks "Submit for Referral"

DAY 2-5: REFERRAL TO CBP ENFORCEMENT
├─ Referral package sent to CBP analyst (secure email + dashboard)
├─ Analyst reviews package, initiates investigation
├─ Investigation outcomes reported back (API callback or manual input)

OUTCOME FEEDBACK:
├─ CBP investigation confirms transshipment → Label: "CONFIRMED"
├─ CBP clears shipment after exam → Label: "CLEARED"
├─ CBP still investigating → Label: "IN_PROGRESS"
│
├─ Officer submits feedback via FeedbackInterface
│  ├─ Outcome: Select from [CONFIRMED, CLEARED, IN_PROGRESS]
│  ├─ Notes: Free text explanation
│  └─ Confidence: "How confident were you in the referral?"
│
├─ Feedback stored in database (investigation_outcomes table)
└─ Used for model retraining (Gate 2, 3, Option Period)
```

---

## PART 2: RULES MANAGEMENT IMPLEMENTATION

### 2.1 Current Rules Engine Code Location

**Rules Encoded In:**

```
services/api/risk_scoring_engine.py (32KB)
├─ Class: RiskScoringEngine
├─ Method: score_shipment(shipment) → RiskScoreBreakdown
├─ 7 Factor calculations:
│  ├─ _score_documentation_risk() → Rules for Element 9, ISF, manifest
│  ├─ _score_commodity_risk() → Rules for tariff rates, export control
│  ├─ _score_routing_risk() → Rules for AIS dwell, port selection
│  ├─ _score_party_risk() → Rules for shipper age, OFAC, opacity
│  ├─ _score_corridor_risk() → Rules for country pairs, duty rates
│  ├─ _score_pattern_risk() → Rules for pricing, anomalies
│  └─ _score_time_sensitivity() → Rules for tariff timing, seasonality
│
└─ Current: HARDCODED in Python, not configurable

services/api/risk_models.py (15KB)
├─ Class: RiskModelConfig
├─ Contains all factor definitions and weights:
│  ├─ DOCUMENTATION_RISK (weight: 0.25)
│  ├─ COMMODITY_RISK (weight: 0.15)
│  ├─ ROUTING_RISK (weight: 0.15)
│  ├─ PARTY_RISK (weight: 0.15)
│  ├─ CORRIDOR_RISK (weight: 0.05)
│  ├─ PATTERN_RISK (weight: 0.10)
│  └─ TIME_SENSITIVITY (weight: 0.10)
│
├─ Each factor has sub-factors with thresholds
└─ Current: CONFIG FILE (YAML-like in Python), modifiable but requires code restart

services/api/scoring_orchestrator.py (24KB)
├─ Orchestrates the scoring pipeline
├─ Calls risk_scoring_engine for each shipment
├─ Handles caching, versioning, feedback loop
└─ Current: PARTIALLY IMPLEMENTED (caching framework exists)
```

**How Rules Are Currently Implemented:**

Example from `risk_models.py`:
```python
DOCUMENTATION_RISK = {
    "name": "Origin Documentation Gap",
    "weight": 0.25,  # 25% of final score
    "sub_factors": {
        "element_9_mismatch": {
            "name": "Element 9 Origin Mismatch",
            "weight": 0.50,  # 50% of documentation score
            "severity_multiplier": 2.5,  # Critical factor
            "description": "Declared origin vs actual origin discrepancy",
        },
        "isf_amendments": {
            "name": "ISF Amendments/Corrections",
            "weight": 0.30,
            "base_score": 2,  # 2 pts per amendment
            "description": "Number of filed amendments post-transmission",
        },
        "manifest_completeness": {
            "name": "Manifest Field Completeness",
            "weight": 0.20,
            "description": "Missing or vague descriptions, inconsistent formatting",
        },
    },
}
```

Example from `risk_scoring_engine.py`:
```python
def _score_documentation_risk(self, shipment: Dict) -> List[RiskComponentScore]:
    """Score documentation compliance and ISF filing completeness"""
    components = []
    
    # Rule 1: Element 9 Mismatch
    element9_mismatch = shipment.get("element9_is_mismatch", False)
    if element9_mismatch:
        components.append(RiskComponentScore(
            component="Documentation Risk",
            factor="Element 9 Mismatch",
            score=10.0,  # 10 out of 10
            weight=0.50,
            weighted_result=5.0,  # 10 * 0.50
            rationale="Declared origin does not match AIS stuffing location",
            evidence=["ISF Element 9: Guangzhou, China",
                      "Manifest: Vietnam",
                      "AIS confirms ship at Guangzhou port"]
        ))
    
    # Rule 2: ISF Amendments
    isf_amendments = shipment.get("isf_amendments", 0)
    if isf_amendments > 3:
        components.append(RiskComponentScore(
            component="Documentation Risk",
            factor="ISF Amendments",
            score=min(8.0, isf_amendments * 2),  # 2 pts per amendment, capped at 8
            weight=0.30,
            weighted_result=min(2.4, (isf_amendments * 2 * 0.30)),
            rationale=f"{isf_amendments} amendments filed after ISF transmission",
            evidence=[f"Amendment {i}: {date}" for i, date in enumerate(...)]
        ))
    
    # ... more rules
    return components
```

---

### 2.2 What's MISSING: Rules Management Interface

```
❌ NO ADMIN PANEL FOR RULES
├─ Can't change thresholds without code edit
├─ Can't adjust weights without code restart
├─ Can't enable/disable rules without deployment
├─ Can't A/B test threshold changes
└─ Impact: Hard to tune in production (Gate 2-3)

❌ NO RULE VERSION CONTROL
├─ No history of rule changes
├─ No ability to rollback rule changes
├─ No audit trail (who changed what, when)
└─ Impact: Can't diagnose why PPV changed

❌ NO RULES DATABASE
├─ Rules hardcoded in Python (not in DB)
├─ Can't query rule effectiveness
├─ Can't correlate rule firings to outcomes
└─ Impact: Hard to optimize rules based on data

❌ NO DYNAMIC THRESHOLD ADJUSTMENT (for Gate 3)
├─ Need to adjust thresholds weekly based on PPV
├─ Currently manual + requires code deployment
└─ Impact: Can't reach 50%+ PPV targets

❌ NO RULE IMPACT ANALYSIS
├─ Can't see "which rules caught this case?"
├─ Can't identify "if we removed rule X, would PPV improve?"
└─ Impact: Can't optimize rule set
```

---

## PART 3: PROPOSED RULES MANAGEMENT INTERFACE

### 3.1 Admin Panel for Rules (To Build in Gate 1-2)

**New Page: `/admin/rules-editor` (React component)**

```
┌─────────────────────────────────────────────────────────────┐
│ RULES MANAGEMENT DASHBOARD                                  │
│ (Admin/Lead Analyst access only)                            │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ TABS:                                                        │
│ [Rules Editor] [Version History] [A/B Testing] [Analytics]  │
│                                                              │
├─────────────────────────────────────────────────────────────┤
│ TAB 1: RULES EDITOR                                         │
│                                                              │
│ Factor Weights (Slider Controls):                           │
│ ┌──────────────────────────────────────────────────────┐   │
│ │ Documentation Risk        [========●=====] 25%       │   │
│ │ Commodity Sensitivity     [======●======] 15%        │   │
│ │ Routing Anomalies         [======●======] 15%        │   │
│ │ Party Profile Risk        [===●=========] 10%        │   │
│ │ Corridor Risk             [●===========] 5%          │   │
│ │ Pattern Anomaly           [======●======] 10%        │   │
│ │ Time Sensitivity          [======●======] 10%        │   │
│ │                                                      │   │
│ │ [Reset to Defaults] [Preview Impact]                │   │
│ └──────────────────────────────────────────────────────┘   │
│                                                              │
│ Individual Rules:                                           │
│ ┌──────────────────────────────────────────────────────┐   │
│ │ Filter: [Documentation ▼] [Enabled ▼]               │   │
│ ├──────────────────────────────────────────────────────┤   │
│ │ ✅ Element 9 Exact Mismatch                          │   │
│ │    ├─ Confidence: 95%                               │   │
│ │    ├─ Points: 20 (editable)                         │   │
│ │    ├─ Corroboration Required: 1 (editable)          │   │
│ │    └─ [Edit] [Test] [Disable]                       │   │
│ │                                                      │   │
│ │ ✅ OFAC/SDN Hit                                      │   │
│ │    ├─ Confidence: 100% (locked)                     │   │
│ │    ├─ Points: 25                                     │   │
│ │    ├─ Corroboration Required: 0                     │   │
│ │    └─ [Edit] [Test] [Disable]                       │   │
│ │                                                      │   │
│ │ ✅ High-Risk Corridor + Duty >15%                    │   │
│ │    ├─ Confidence: 90%                               │   │
│ │    ├─ Points: 15                                     │   │
│ │    ├─ Duty Threshold: 15% (editable)                │   │
│ │    ├─ Corridor List: [CN, VN, MY, TH, ID ▼]         │   │
│ │    └─ [Edit] [Test] [Disable]                       │   │
│ │                                                      │   │
│ │ [+ Add New Rule]                                     │   │
│ └──────────────────────────────────────────────────────┘   │
│                                                              │
│ [Save Changes] [Preview] [Deploy to Staging] [Deploy Live] │
└─────────────────────────────────────────────────────────────┘
```

**Implementation:**

Backend needs:
```python
# New API endpoints for rules management:

GET /api/admin/rules
├─ Returns all rules (configuration, weights, thresholds)
├─ Response:
│  {
│    "rules": [
│      {
│        "id": "element9_mismatch",
│        "name": "Element 9 Mismatch",
│        "component": "documentation",
│        "confidence": 0.95,
│        "points": 20,
│        "corroboration_required": 1,
│        "enabled": true,
│        "version": 1,
│        "created_at": "2026-06-01",
│        "last_modified": "2026-06-12"
│      },
│      ...
│    ]
│  }
└─ Status: NEEDS TO BE BUILT

POST /api/admin/rules/{rule_id}
├─ Update individual rule (threshold, points, enabled)
├─ Request:
│  {
│    "points": 22,
│    "corroboration_required": 2,
│    "enabled": true
│  }
├─ Response: Updated rule + version number
└─ Status: NEEDS TO BE BUILT

GET /api/admin/rules/versions
├─ Returns version history (who changed what, when)
├─ Response: List of historical rule sets
└─ Status: NEEDS TO BE BUILT

POST /api/admin/rules/preview
├─ Preview impact of rule changes (dry run)
├─ Request: New rule set
├─ Returns: "Would affect X shipments, PPV would change ±Y%"
└─ Status: NEEDS TO BE BUILT

GET /api/admin/rules/analytics/{rule_id}
├─ Analytics: How often does this rule fire?
├─ Response:
│  {
│    "rule_id": "element9_mismatch",
│    "times_fired_30d": 23,
│    "times_confirmed": 22,
│    "ppv": 0.956,
│    "correlation_to_outcome": 0.94
│  }
└─ Status: NEEDS TO BE BUILT
```

Frontend (React component):
```typescript
// ui/src/pages/RulesEditorPage.tsx (needs to be created)

import { useState, useEffect } from 'react';
import RuleWeightEditor from '../components/admin/RuleWeightEditor';
import RuleDetailEditor from '../components/admin/RuleDetailEditor';
import RuleVersionHistory from '../components/admin/RuleVersionHistory';
import RuleAnalytics from '../components/admin/RuleAnalytics';

export default function RulesEditorPage() {
  const [tab, setTab] = useState('editor'); // editor | history | ab-test | analytics
  const [rules, setRules] = useState([]);
  const [weights, setWeights] = useState({});
  const [changes, setChanges] = useState({});
  const [previewResult, setPreviewResult] = useState(null);
  
  useEffect(() => {
    fetchRules();
  }, []);
  
  const fetchRules = async () => {
    const response = await fetch('/api/admin/rules');
    const data = await response.json();
    setRules(data.rules);
  };
  
  const handleRuleChange = (ruleId, field, value) => {
    setChanges(prev => ({
      ...prev,
      [ruleId]: { ...prev[ruleId], [field]: value }
    }));
  };
  
  const handlePreview = async () => {
    const response = await fetch('/api/admin/rules/preview', {
      method: 'POST',
      body: JSON.stringify(changes)
    });
    const preview = await response.json();
    setPreviewResult(preview);
  };
  
  const handleDeploy = async () => {
    // Deploy to staging/production
  };
  
  return (
    <div className="rules-editor-page">
      <Tabs>
        <Tab name="Rules Editor">
          <RuleWeightEditor weights={weights} onChange={handleWeights} />
          <RuleDetailEditor rules={rules} changes={changes} onChange={handleRuleChange} />
          <button onClick={handlePreview}>Preview Impact</button>
          {previewResult && <PreviewPanel result={previewResult} />}
        </Tab>
        
        <Tab name="Version History">
          <RuleVersionHistory />
        </Tab>
        
        <Tab name="A/B Testing">
          <ABTestRunner />
        </Tab>
        
        <Tab name="Analytics">
          <RuleAnalytics rules={rules} />
        </Tab>
      </Tabs>
    </div>
  );
}
```

---

### 3.2 Rules Database Schema (To Build in Gate 1)

```sql
-- Rules registry (version control)
CREATE TABLE rules (
  id TEXT PRIMARY KEY,           -- e.g., "element9_mismatch"
  name TEXT NOT NULL,            -- "Element 9 Mismatch"
  component TEXT NOT NULL,       -- "documentation", "routing", etc.
  description TEXT,
  created_at TIMESTAMP,
  is_active BOOLEAN DEFAULT 1
);

-- Rule versions (history)
CREATE TABLE rule_versions (
  id TEXT PRIMARY KEY,
  rule_id TEXT NOT NULL,
  version INT,                   -- 1, 2, 3, ...
  
  -- Configuration
  confidence REAL,               -- 0.0-1.0
  points INT,                    -- 0-25
  corroboration_required INT,    -- 0, 1, 2, 3+
  enabled BOOLEAN,
  
  -- Thresholds (varies by rule type)
  threshold_numeric REAL,        -- e.g., 15 for "duty > 15%"
  threshold_list TEXT,           -- JSON array for "corridor IN [...]"
  
  -- Metadata
  changed_by TEXT,               -- User ID
  change_reason TEXT,            -- "Gate 2 calibration: lower false positives"
  created_at TIMESTAMP,
  
  FOREIGN KEY (rule_id) REFERENCES rules(id)
);

-- Rule effectiveness tracking
CREATE TABLE rule_effectiveness (
  id TEXT PRIMARY KEY,
  rule_id TEXT NOT NULL,
  version INT,
  
  -- Analytics (30-day rolling)
  times_fired_30d INT,           -- How many shipments triggered this?
  times_confirmed_30d INT,       -- Of those, how many were confirmed?
  ppv REAL,                      -- times_confirmed / times_fired
  
  -- Correlation
  signal_strength REAL,          -- 0.0-1.0 (correlation to outcome)
  false_positive_rate REAL,      -- % of firings that were false alarms
  false_negative_rate REAL,      -- % of real cases missed by this rule
  
  -- Trend
  ppv_7d REAL,                   -- PPV for last 7 days
  ppv_trend TEXT,                -- "increasing", "decreasing", "stable"
  
  calculated_at TIMESTAMP,
  FOREIGN KEY (rule_id) REFERENCES rules(id)
);

-- Rule changes audit trail
CREATE TABLE rule_change_log (
  id TEXT PRIMARY KEY,
  rule_id TEXT NOT NULL,
  old_version INT,
  new_version INT,
  
  changes TEXT,                  -- JSON of what changed
  changed_by TEXT,               -- User ID
  reason TEXT,
  
  deployed_at TIMESTAMP,         -- When did this go live?
  reverted_at TIMESTAMP NULL,    -- If rolled back
  
  created_at TIMESTAMP
);

-- A/B test experiments (compare rule versions)
CREATE TABLE rule_ab_tests (
  id TEXT PRIMARY KEY,
  rule_id TEXT NOT NULL,
  
  variant_a_version INT,         -- Current rule version
  variant_b_version INT,         -- Proposed rule version
  
  variant_a_traffic_pct REAL,    -- % of shipments on variant A
  variant_b_traffic_pct REAL,    -- % of shipments on variant B
  
  start_at TIMESTAMP,
  end_at TIMESTAMP,
  
  -- Results
  variant_a_ppv REAL,
  variant_b_ppv REAL,
  winner TEXT,                   -- "A", "B", or "inconclusive"
  
  created_at TIMESTAMP
);
```

---

## PART 4: DATA MANAGEMENT INTERFACE

### 4.1 Current Data Views (Working)

**Shipments List (ShipmentsHubPage):**

```
┌──────────────────────────────────────────────────────────────┐
│ SHIPMENTS HUB                                                │
├──────────────────────────────────────────────────────────────┤
│ Search: [shipper name_________] Filter: [Risk ▼] [Date ▼]   │
│                                                              │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ ID    │ Shipper        │ Consignee  │ HTS    │ Score     │ │
│ ├─────────────────────────────────────────────────────────┤ │
│ │ SHP-1 │ Greenfield     │ LA Dist.   │ 7604   │ 87 ●●●   │ │
│ │ SHP-2 │ China Metals   │ Houston    │ 7610   │ 62 ●●    │ │
│ │ SHP-3 │ Vietnam Solar  │ Phoenix    │ 8541   │ 45 ●     │ │
│ │ SHP-4 │ Malaysia Mfg   │ Cleveland  │ 6100   │ 38 ○     │ │
│ │ [Show more...]                                          │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                              │
│ Columns: [ID, Shipper, Consignee, HTS, Score, Status ▼]    │
│ Display: [100 per page] [Sort by: Score ▼]                  │
│ Export: [CSV] [Excel]                                        │
└──────────────────────────────────────────────────────────────┘
```

**Case Investigation Detail (ModernCaseInvestigationPage):**

```
┌──────────────────────────────────────────────────────────────┐
│ CASE INVESTIGATION: SHP-000211                              │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│ OVERVIEW (Expandable)                                       │
│ ├─ Shipper: Guangdong Greenfield Aluminum Ltd.             │
│ ├─ Consignee: LA Distribution Co.                          │
│ ├─ Origin: China (Guangzhou)                               │
│ ├─ Destination: US (Long Beach)                            │
│ ├─ HTS Code: 7604.10.00 (Aluminum Extrusions)              │
│ ├─ Declared Value: $187,500                                │
│ ├─ Declared Weight: 250 MT                                 │
│ ├─ Unit Price: $750/MT (vs market $850-1200)              │
│ └─ Vessel: MSC Madrid (IMO 9438450)                        │
│                                                              │
│ RISK SCORE BREAKDOWN (Expandable)                          │
│ ├─ Final Score: 87/100 [HIGH RISK]                        │
│ ├─ Confidence: 87% (95% CI: [82-92])                       │
│ │                                                          │
│ ├─ Factor Breakdown:                                        │
│ │  ├─ Documentation Risk: 40/40 (100%)                    │
│ │  ├─ Commodity Risk: 30/35 (86%)                         │
│ │  ├─ Routing Anomalies: 25/25 (100%)                     │
│ │  ├─ Party Profile: 10/15 (67%)                          │
│ │  ├─ Corridor Risk: 10/10 (100%)                         │
│ │  ├─ Pattern Anomaly: 15/15 (100%)                       │
│ │  └─ Time Sensitivity: 12/15 (80%)                       │
│ │                                                          │
│ └─ Top 3 Contributing Factors:                              │
│    1. ISF Element 9 Mismatch (declared: VN, actual: CN)   │
│    2. Abnormal Dwell (11d vs 3.2d avg)                    │
│    3. Pricing 12% below market baseline                    │
│                                                              │
│ ACTIONS                                                     │
│ ├─ [Generate Referral Package]                            │
│ ├─ [Export as PDF]                                         │
│ ├─ [Add to Batch Hold]                                     │
│ └─ [Mark for Follow-up Investigation]                      │
└──────────────────────────────────────────────────────────────┘
```

---

### 4.2 What's MISSING: Admin Data Views

```
❌ NO DATA QUALITY DASHBOARD
├─ Need to see: ISF completeness, AIS coverage, entity resolution success
├─ Missing graphs: Distribution of missing fields, data freshness
└─ Impact: Can't diagnose data issues affecting scoring

❌ NO RULE IMPACT ANALYSIS VIEW
├─ Need to see: "How many shipments does Rule X affect?"
├─ Need to see: "What's the PPV for each rule individually?"
├─ Missing: Correlation matrix (rule X correlation to outcome Y)
└─ Impact: Can't optimize rules

❌ NO MODEL PERFORMANCE DASHBOARD
├─ Need to see: AUC trends, calibration over time
├─ Need to see: Drift detection alerts (data quality, prediction shift)
├─ Missing: Detailed metrics by score bin, by commodity, by origin
└─ Impact: Can't detect model degradation in time

❌ NO FEEDBACK MANAGEMENT INTERFACE
├─ Need to see: All investigation outcomes (confirmed, cleared, pending)
├─ Need to manage: Map outcomes to shipments, track timing
├─ Missing: Bulk feedback upload (CBP sends batch CSV)
└─ Impact: Can't efficiently update training data

❌ NO THRESHOLD TUNING DASHBOARD
├─ Need to see: PPV by threshold (what threshold gives 50%?)
├─ Need to see: Sensitivity/Specificity trade-off curves
├─ Missing: Live threshold adjustment (slider to test effect)
└─ Impact: Can't dynamically optimize thresholds (Gate 3 requirement)
```

---

## PART 5: DATA MANAGEMENT WORKFLOW (Officers & Admins)

### 5.1 Officer Workflow (Day-to-Day)

```
MORNING:
├─ Officer logs in (role: OFFICER)
├─ Sees dashboard: "5 high-risk cases pending review"
├─ Opens ManifestRiskQueuePage
│  └─ Sees 5 cases sorted by score (highest first)
│
├─ Case 1: SHP-001 (87/100)
│  ├─ Clicks to open ModernCaseInvestigationPage
│  ├─ Reviews 7-factor breakdown
│  ├─ Sees top contributing factors
│  ├─ Reads referral package sections
│  ├─ Decides: "This is high-confidence transshipment"
│  ├─ Clicks [Generate Referral Package]
│  ├─ Reviews generated 14-section package
│  ├─ Edits section 3-6 (Historical Pattern narrative)
│  ├─ Adds notes: "Entity network confirms shell company structure"
│  ├─ Clicks [Submit Referral]
│  └─ Notification: "Package sent to CBP Enforcement"
│
├─ Case 2: SHP-002 (62/100)
│  ├─ Reviews, decides: "Borderline, need more intel"
│  ├─ Clicks [Hold for Further Analysis]
│  ├─ Adds note: "Wait for additional Altana data"
│  └─ Case stays in queue, tagged "PENDING_DATA"
│
└─ Case 3-5: Similar workflow (refer, hold, or clear)

AFTERNOON (After CBP Investigation Outcomes Arrive):
├─ Officer gets notification: "SHP-001 confirmed transshipment!"
├─ Clicks notification → Opens case detail
├─ In FeedbackInterface, selects:
│  ├─ Outcome: "CONFIRMED"
│  ├─ Confidence: "Very high (90%+)"
│  ├─ Notes: "CBP seizure completed, duties recovered"
│  └─ Clicks [Submit Feedback]
│
├─ Feedback stored in database
├─ System notification: "Feedback received for model training"
└─ Officer can track stats: "My referrals: 4 confirmed, 1 cleared, 0 pending"
```

### 5.2 Admin/Lead Analyst Workflow (Weekly Tuning)

```
MONDAY MORNING (Weekly Review):
├─ Admin logs in (role: ADMIN or ANALYST)
├─ Goes to /admin/dashboard
│  └─ Sees KPIs:
│     ├─ Referrals this week: 12
│     ├─ Confirmed: 3 (PPV: 25%)
│     ├─ Cleared: 9
│     ├─ Model AUC: 0.84
│     └─ Data quality: 94% (ISF completeness)
│
├─ Opens /admin/rules-editor
│  ├─ Sees factor weights (current: 0.25 doc, 0.15 commodity, ...)
│  ├─ Sees individual rules (8 rules, all enabled)
│  ├─ Checks rule effectiveness:
│  │  ├─ Rule "Element 9 Mismatch" → Times fired: 23, Confirmed: 22, PPV: 96%
│  │  ├─ Rule "AIS Dwell >5x" → Times fired: 15, Confirmed: 11, PPV: 73%
│  │  └─ Rule "Pricing anomaly" → Times fired: 8, Confirmed: 4, PPV: 50%
│  │
│  ├─ Analysis: "PPV is 25%, target is 30%, need to increase precision"
│  │
│  ├─ Decision 1: Lower "Pricing anomaly" rule points (too noisy)
│  │  ├─ Current: 12 points
│  │  ├─ Change to: 8 points
│  │  ├─ Clicks [Preview] → "Would reduce referrals by 3, improve PPV to 28%"
│  │  └─ Clicks [Deploy to Staging] (test for 1 day before prod)
│  │
│  ├─ Decision 2: Raise corroboration requirement
│  │  ├─ Currently: ≥1 additional signal required
│  │  ├─ Change to: ≥2 additional signals
│  │  ├─ Clicks [Preview] → "Would reduce referrals by 5, improve PPV to 31%"
│  │  └─ Clicks [Deploy to Staging]
│  │
│  └─ Clicks [Save Changes & Deploy to Production]
│     └─ Notification: "Rules updated (v2.1), deployment in progress"
│
├─ Goes to /admin/rule-analytics
│  ├─ Sees graphs:
│  │  ├─ PPV over time (trend: increasing, good)
│  │  ├─ Rule effectiveness heatmap (which rules work best?)
│  │  ├─ Data quality metrics (ISF: 94%, AIS: 96%, ER: 99%)
│  │  └─ Drift detection (any warnings?)
│  │
│  └─ Alert: "Data quality warning: ISF completeness dropped from 96% to 94%"
│     └─ Clicks to investigate, finds: "Spire API had 2-hour outage Saturday"
│
└─ Prepares weekly report for CBP:
   ├─ Metrics: 12 referrals, 3 confirmed (25% PPV), 1 confirmed rate
   ├─ Rules changes: Adjusted pricing rule & corroboration threshold
   ├─ Alert: ISF data quality dip (resolved)
   └─ Outlook: "Expect PPV to reach 30% by next week with rule changes"
```

---

## PART 6: IMPLEMENTATION ROADMAP FOR UX & RULES MANAGEMENT

### 6.1 Gate 1 (Weeks 1-8): UI + Rules Database

**Week 1-2: Rules Database & API**
```
Backend:
├─ [ ] Create rules table, rule_versions table, rule_change_log
├─ [ ] Implement GET /api/admin/rules (fetch current rules)
├─ [ ] Implement POST /api/admin/rules/{rule_id} (update individual rule)
├─ [ ] Implement GET /api/admin/rules/versions (version history)
├─ [ ] Seed database with current 8 Gate 1 rules
└─ [ ] Test CRUD operations

Frontend:
├─ [ ] Create /admin/rules-editor page (stub)
├─ [ ] Wire up GET /api/admin/rules
├─ [ ] Display current rules in table format
└─ [ ] Add [Edit] button (handler not yet wired)

Testing:
├─ [ ] Manual test: Can retrieve all rules?
├─ [ ] Manual test: Can update rule points?
└─ [ ] Verify changes persist in database
```

**Week 3-4: Rules Editor UI**
```
Frontend:
├─ [ ] Build RuleWeightEditor component (sliders for factor weights)
├─ [ ] Build RuleDetailEditor component (per-rule settings)
├─ [ ] Implement [Save Changes] (POST to /api/admin/rules)
├─ [ ] Implement [Preview Impact] (POST /api/admin/rules/preview - backend stub)
├─ [ ] Add version history view (show who changed what, when)
└─ [ ] Test: Can user change rule and see preview?

Backend:
├─ [ ] Implement POST /api/admin/rules/preview (dry-run, return impact estimate)
├─ [ ] Implement version tracking (save to rule_change_log)
├─ [ ] Implement role-based access control (admin only)
└─ [ ] Test: Preview gives reasonable estimates?
```

**Week 5-8: Monitoring & Feedback Integration**
```
Frontend:
├─ [ ] Build /admin/data-quality-dashboard (ISF, AIS, ER metrics)
├─ [ ] Build /admin/rule-analytics (PPV per rule, correlation)
├─ [ ] Build FeedbackInterface (officer confirms outcome: CONFIRMED/CLEARED)
├─ [ ] Wire feedback form to POST /api/feedback/{shipmentId}
└─ [ ] Test: Officer can submit feedback from case detail?

Backend:
├─ [ ] Create investigation_outcomes table
├─ [ ] Implement POST /api/feedback/{shipmentId} (store outcome)
├─ [ ] Implement GET /api/admin/rule-analytics/{rule_id} (PPV metrics)
├─ [ ] Implement GET /api/admin/data-quality (data quality metrics)
├─ [ ] Batch calculate rule analytics (daily cron job)
└─ [ ] Test: Analytics reflect real data?
```

### 6.2 Gate 2 (Weeks 9-16): Dynamic Thresholding & A/B Testing

**Week 11-12: Dynamic Threshold UI**
```
Frontend:
├─ [ ] Create /admin/threshold-tuning page
├─ [ ] Build threshold slider (0.40 to 0.80)
├─ [ ] Show PPV/Sensitivity curves for different thresholds
├─ [ ] Implement [Apply New Threshold]
└─ [ ] Test: Threshold changes affect referral volume as expected?

Backend:
├─ [ ] Add threshold to rule_versions table
├─ [ ] Implement GET /api/admin/threshold-tuning (PPV curve data)
├─ [ ] Implement weekly cron: auto-adjust threshold to target PPV
│  └─ Algorithm: If observed_ppv < 30%, lower threshold by 0.01
└─ [ ] Test: Auto-adjustment works correctly?
```

**Week 13-14: A/B Testing**
```
Frontend:
├─ [ ] Create /admin/ab-testing page
├─ [ ] Build experiment launcher (select variant A & B, set traffic split)
├─ [ ] Show experiment results (variant A PPV vs B PPV, winner)
└─ [ ] Test: Can run experiment and see results?

Backend:
├─ [ ] Create rule_ab_tests table
├─ [ ] Implement POST /api/admin/ab-tests (create experiment)
├─ [ ] Implement traffic splitting logic (route % to variant A vs B)
├─ [ ] Implement GET /api/admin/ab-tests/{test_id} (results)
└─ [ ] Test: Traffic splits correctly, results accurate?
```

### 6.3 Gate 3 (Weeks 17-24): Advanced Analytics & RL Integration

```
Frontend:
├─ [ ] Enhance rule analytics (show evasion patterns RL agent finds)
├─ [ ] Create /admin/rl-vulnerabilities page (show exploited signals)
├─ [ ] Build recommendation engine ("RL suggests: increase weight on X signal")
└─ [ ] Test: RL recommendations improve PPV?

Backend:
├─ [ ] Implement RL agent vulnerability detection
├─ [ ] Implement GET /api/admin/rl-vulnerabilities (found vulnerabilities)
├─ [ ] Auto-suggest rule updates based on RL findings
└─ [ ] Test: RL findings correlate with actual false alarms?
```

---

## SUMMARY: CURRENT STATE & GAPS

```
✅ BUILT (Officer Workflow)
├─ Case investigation page (review cases, see 7-factor breakdown)
├─ Referral package generation (14 sections, editable narratives)
├─ Feedback interface (confirm outcome: CONFIRMED/CLEARED)
├─ Shipments hub (search, filter, list all cases)
└─ Modern UI components (risk gauge, confidence bars, etc.)

✅ PARTIALLY BUILT (Rules & Data Management)
├─ Rules encoded in Python (hardcoded, not configurable)
├─ Rules config file (weights, sub-factors editable but requires restart)
├─ Risk model outputs (breakdown scores visible to officer)
└─ Feedback collection (framework, not fully wired)

❌ NOT BUILT (Admin Rules Management)
├─ Rules database (version control, history, audit trail)
├─ Rules editor UI (sliders to change weights, thresholds)
├─ Rules preview/impact tool (dry-run before deployment)
├─ Rule analytics (PPV per rule, correlation to outcome)
├─ Data quality dashboard (ISF, AIS, ER completeness)
├─ Dynamic thresholding (weekly auto-adjust for target PPV)
├─ A/B testing interface (compare rule versions)
└─ RL vulnerability viewer (show evasion patterns)

EFFORT ESTIMATE:
├─ Gate 1 (Rules DB + Editor): 4-6 weeks
├─ Gate 2 (Dynamic thresholding + A/B): 2-4 weeks
├─ Gate 3 (Advanced analytics + RL): 2-3 weeks
└─ Total: 8-13 weeks (can be parallelized with model development)
```

**What should we build next?** Officer UI is solid. The missing piece is the **rules management backend** so admins can tune thresholds and track rule effectiveness.
