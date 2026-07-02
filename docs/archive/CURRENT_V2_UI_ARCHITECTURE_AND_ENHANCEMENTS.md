# Current V2 UI Architecture & Enhancement Plan

**Date:** June 12, 2026  
**Status:** V2 is the CURRENT production UI  
**Deployment:** Running on localhost:3001  
**Validated:** Yes - confirmed via local deployment

---

## PART 1: CURRENT V2 UI ARCHITECTURE

### 1.1 Route Structure

```
App.tsx (root)
├─ "/" → RootRedirect()
│  ├─ If not authenticated → /login
│  └─ If authenticated → /dashboard (redirects to V2AppWrapper)
│
├─ "/login" → LoginPage
│
├─ "/dashboard" → V2AppWrapper (MAIN ENTRY)
├─ "/investigations" → V2AppWrapper (same wrapper, different tab)
├─ "/shipping-intelligence" → V2AppWrapper
├─ "/entities" → V2AppWrapper
├─ "/entity-resolution" → V2AppWrapper
├─ "/watchlists" → V2AppWrapper
├─ "/ai-tuning" → V2AITuningPage
│
└─ "*" → NotFoundPage (404)

ALL authenticated users → V2AppWrapper
```

### 1.2 V2AppWrapper Component (Main Container)

**Location:** `ui/src/App.tsx:30-200+`

```typescript
function V2AppWrapper() {
  // Core state management
  const [activeTab, setActiveTab] = useState('dashboard');
  const [selectedCaseId, setSelectedCaseId] = useState<string | null>(null);
  const [selectedEntityId, setSelectedEntityId] = useState<string | null>(null);
  
  // Data fetching
  const { cases, shipments, loading: casesLoading } = useV2Cases();
  const { referrals, createReferral } = useV2Referrals(cases);
  
  // AI-generated findings
  const generateFindings = useCallback((): AIFinding[] => {
    // Generate AI findings from shipment signals
    // Integrated with Gemini LLM for analysis
  }, [cases, selectedCaseId, shipments]);
  
  return (
    <V2Layout>
      <V2DashboardPage />
      <V2InvestigationsPage />
      <V2ShippingIntelligencePage />
      <V2EntitiesPage />
      <V2EntityResolutionPage />
      <V2WatchlistsPage />
      [... routing logic ...]
    </V2Layout>
  );
}
```

**Key Features:**
- Manages all V2 pages
- Centralizes case/shipment/referral state
- Integrates with V2Layout (which includes V2ChatPanel)
- Generates AI findings on-demand

### 1.3 V2Layout Component (Layout Wrapper)

**Location:** `ui/src/v2/layout/V2Layout.tsx`

```
V2Layout
├─ Header (navigation, user menu)
├─ V2SidebarNav (left sidebar with tab buttons)
│  ├─ Dashboard
│  ├─ Investigations (case queue)
│  ├─ Shipping Intelligence
│  ├─ Entities
│  ├─ Entity Resolution
│  ├─ Watchlists
│  └─ [AI Tuning (admin only)]
│
├─ Main Content Area (center)
│  └─ [Current page content]
│
└─ V2ChatPanel (right sidebar, expandable)
   ├─ Session ID (UUID)
   ├─ Message history (20-message window)
   ├─ Streaming Gemini responses (SSE)
   ├─ Source attribution (function calling ready)
   └─ Context awareness (current page, selected case)
```

### 1.4 V2ChatPanel Component (Ask-AI Agent Integration)

**Location:** `ui/src/v2/layout/V2ChatPanel.tsx`

```typescript
interface V2ChatPanelProps {
  caseContext?: {
    id: string;
    name: string;
    target: string;
    riskScore: number;
    officer: string;
    shipmentId?: string;
  };
  isExpanded?: boolean;
  onToggleExpand?: () => void;
  currentPage?: string;
  selectedEntity?: string;
}

export default function V2ChatPanel({
  caseContext,
  isExpanded = true,
  currentPage = 'dashboard',
  selectedEntity
}) {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'assistant',
      text: 'Authorized Sentry Platform Secure Assistant live. Ask me about active cases, entity intelligence, risk scores, corridors, or referral packages.',
      sources: []
    },
  ]);
  
  const sessionIdRef = useRef<string>(generateUUID());
  
  // Stream response from /api/gemini/assistant/stream endpoint
  const handleSendMessage = async (userMessage: string) => {
    const params = new URLSearchParams({
      message: userMessage,
      session_id: sessionIdRef.current,
      page: currentPage,
      ...(caseContext?.shipmentId && { shipment_id: caseContext.shipmentId }),
      ...(selectedEntity && { entity: selectedEntity }),
    });
    
    // Fetch with SSE streaming
    const response = await fetch(`/api/gemini/assistant/stream?${params}`);
    // Stream and parse events...
  }
}
```

**Key Features:**
- **Session ID Persistence**: UUID stored in ref, persists for 20 messages
- **Context Awareness**: Passes page, shipment_id, entity to Gemini
- **Streaming Responses**: Real-time text via Server-Sent Events (SSE)
- **Source Attribution**: Ready for Phase 2 function calling (10 tools available)
- **Message History**: Keeps last 20 messages for conversation memory

---

## PART 2: V2 PAGES & COMPONENTS

### 2.1 Dashboard Pages

```
V2DashboardPage
├─ Executive KPIs
│  ├─ Referrals this period
│  ├─ PPV (Positive Predictive Value)
│  ├─ Model AUC
│  └─ Data quality score
│
├─ Trend Charts
│  ├─ PPV over time
│  ├─ Referral volume
│  └─ Model performance drift
│
└─ Quick Actions
   ├─ Start new investigation
   ├─ Generate referral package
   └─ Review watchlist

V2InvestigationsPage
├─ Case Queue (sortable, filterable)
│  ├─ Risk score
│  ├─ Shipper name
│  ├─ Commodity
│  └─ Status
│
├─ Case Detail View
│  ├─ 7-factor risk breakdown
│  ├─ Evidence chain
│  ├─ Referral package (14 sections)
│  ├─ What-if scenarios
│  └─ Officer feedback form
│
└─ Actions
   ├─ Generate referral
   ├─ Hold vessel
   ├─ Add to watchlist
   └─ Request Altana verification

V2ShippingIntelligencePage
├─ Trade corridor analysis
├─ Shipping pattern intelligence
└─ Port/vessel tracking

V2EntitiesPage
├─ Entity search (CORD database)
├─ Entity ownership chains (L1-L3)
├─ Historical patterns
└─ Sanctions screening results

V2EntityResolutionPage
├─ Interactive entity network graph (D3/React Flow)
├─ Beneficial ownership visualization
├─ Connection evidence
└─ Risk assessment per entity

V2AITuningPage ⭐ (NEW - Admin Dashboard)
├─ Model Weights (slider controls)
│  ├─ Documentation Risk (25%)
│  ├─ Commodity Sensitivity (15%)
│  ├─ Routing Anomalies (15%)
│  ├─ Party Profile Risk (15%)
│  ├─ Corridor Risk (5%)
│  ├─ Pattern Anomaly (10%)
│  └─ Time Sensitivity (10%)
│
├─ Screening Rules (enable/disable, adjust thresholds)
│  ├─ Element 9 Mismatch
│  ├─ OFAC/SDN Hit
│  ├─ High-Risk Corridor
│  └─ [8 total rules]
│
├─ Configuration
│  ├─ Calibration multiplier
│  ├─ Auto-hold threshold
│  └─ Altana trigger threshold
│
└─ Performance Metrics
   ├─ AUC-ROC
   ├─ Precision/Recall
   ├─ F1 Score
   ├─ Model Version
   └─ Last Training Date
```

### 2.2 Key Components

```
Risk Scoring:
├─ RiskScoreBreakdown.tsx (7-factor visualization)
├─ RiskHeatmap.tsx (commodity/corridor heatmap)
├─ RiskGauge.tsx (radial gauge, 0-100)
└─ ConfidenceBar.tsx (confidence interval display)

Entity Resolution:
├─ EntityRelationshipGraph.tsx (SVG network)
├─ EntityNetworkGraph.tsx (D3 force-directed)
├─ EntityRiskDashboard.tsx (entity-level view)
└─ V2EntityResolutionPanel.tsx (modern entity display)

Referral Generation:
├─ ReferralPackageGenerationTab.tsx (14-section builder)
├─ ReferralPackageGuide.tsx (officer walkthrough)
├─ SectionEditor.tsx (edit individual sections)
└─ NarrativeEditor.tsx (edit LLM narratives)

Data Visualization:
├─ CommodityRiskMatrix.tsx (heatmap)
├─ TradeCorridorMap.tsx (geographical)
├─ InvestigationTimeline.tsx (case history)
├─ DataTable.tsx (generic sortable table)
└─ CorridorSummaryCard.tsx (quick-glance card)
```

---

## PART 3: BACKEND INTEGRATION (API LAYER)

### 3.1 Ask-AI Agent Backend

**Location:** `services/api/ask_ai_agent.py`

```python
class AskAIAgent:
  """Gemini-powered intelligence analyst with function calling"""
  
  def __init__(self, api_key: str = None):
    self.model = genai.GenerativeModel(model_name="gemini-2.5-flash")
    self.sessions = {}  # session_id → message history
    self.MAX_HISTORY = 20
  
  async def stream_response(
    self,
    session_id: str,
    user_message: str,
    context: Dict[str, Any] = None
  ) -> AsyncGenerator[str, None]:
    """Stream response with function calling (Phase 2)"""
    # Build system prompt
    # Add user message to session history
    # Stream from Gemini API
    # Yield SSE events: text, source (function call), done
```

**FastAPI Endpoint:**

```python
@app.get("/api/gemini/assistant/stream")
async def gemini_assistant_stream(
    message: str,
    session_id: str = None,
    page: str = None,
    shipment_id: str = None,
    entity: str = None
) -> StreamingResponse:
  """Stream Gemini response with context awareness"""
```

### 3.2 Ask-AI Tools (Phase 2 - Function Calling)

**Location:** `services/api/ask_ai_tools.py`

10 tools ready for function calling:

```python
1. search_shipments(query, risk_min, risk_max, limit)
   └─ Find shipments by keyword, risk range

2. get_shipment_risk_breakdown(shipment_id)
   └─ Full 7-factor breakdown + audit trail

3. investigate_entity(entity_name, country)
   └─ CORD entity resolution + beneficial ownership

4. get_ownership_chain(entity_name, depth=3)
   └─ Trace L1-L3 beneficial owners

5. check_sanctions_screening(entity_name, country)
   └─ OFAC + OpenSanctions screening

6. get_corridor_risk(origin_country, destination_country)
   └─ Trade corridor risk + AD/CVD rates

7. get_case_statistics()
   └─ Aggregate workload metrics

8. get_what_if_scenarios(shipment_id)
   └─ Risk scenario analysis (change price, origin, etc.)

9. get_historical_patterns(entity_name)
   └─ Shipper/entity history + import frequency

10. get_referral_summary(shipment_id)
    └─ Referral packages + officer analysis
```

### 3.3 V2AITuningPage Backend APIs

**Location:** `services/api/main.py:3899-4200+`

```python
GET /api/model/weights
└─ Returns: {"weights": {...}, "config": {...}}

POST /api/model/weights
└─ Input: {"weights": {...}, "config": {...}}
└─ Updates factor weights, calibration multiplier

GET /api/model/metrics
└─ Returns: {"auc_roc": ..., "precision": ..., "f1_score": ..., "model_version": ...}

POST /api/rules/save
└─ Input: {"h1_weight": ..., "h2_weight": ..., "rules": {...}}
└─ Saves rules configuration with audit trail

GET /api/rule-analytics/{rule_id}
└─ Returns: {"times_fired": ..., "ppv": ..., "correlation": ...}
```

---

## PART 4: ENHANCEMENT PLAN FOR GATES 1-3

### 4.1 Gate 1 Enhancements (Weeks 1-8)

**Priority: Wire up backend APIs for V2AITuningPage**

```
Frontend (V2AITuningPage):
├─ [ ] Load model weights from GET /api/model/weights
├─ [ ] Save weight changes via POST /api/model/weights
├─ [ ] Load metrics from GET /api/model/metrics
├─ [ ] Display rule effectiveness (times fired, PPV)
├─ [ ] Preview impact before saving (dry-run)
└─ [ ] Show audit trail of weight changes

Backend:
├─ [ ] Create rules database (rules, rule_versions, rule_change_log tables)
├─ [ ] Implement POST /api/model/weights (persist to DB)
├─ [ ] Implement GET /api/model/metrics (compute from feedback data)
├─ [ ] Implement GET /api/rule-analytics/{rule_id} (calculate PPV per rule)
└─ [ ] Add role-based access control (admin only)
```

### 4.2 Gate 2 Enhancements (Weeks 9-16)

**Priority: Activate Ask-AI function calling + dynamic threshold tuning UI**

```
Frontend (V2ChatPanel):
├─ [ ] Enable function calling in Ask-AI (display source cards)
├─ [ ] Show "Analyzing shipment: SHP-001" while tools run
├─ [ ] Display evidence from tools (CORD results, risk breakdown, etc.)
└─ [ ] Add suggested questions ("Explain this score", "Check entity chain")

Frontend (New Page: Threshold Tuning):
├─ [ ] Create /threshold-tuning page (admin only)
├─ [ ] Build threshold slider (0.40-0.80)
├─ [ ] Show PPV/Sensitivity curves for different thresholds
├─ [ ] Display week-over-week PPV trend
├─ [ ] Implement auto-threshold suggestion (AI recommends best threshold)
└─ [ ] Display threshold adjustment history

Backend:
├─ [ ] Enable function calling in AskAIAgent (wire up ask_ai_tools.py)
├─ [ ] Implement GET /api/threshold-tuning (PPV curve data)
├─ [ ] Implement POST /api/threshold-tuning (update threshold)
├─ [ ] Add weekly cron: auto-adjust threshold based on observed PPV
└─ [ ] Create threshold_history table (audit trail)
```

### 4.3 Gate 3 Enhancements (Weeks 17-24)

**Priority: Advanced rule analytics + RL vulnerability viewer**

```
Frontend (New Page: Rule Analytics):
├─ [ ] Create /admin/rule-analytics page (admin only)
├─ [ ] Build PPV heatmap (rules × score bins)
├─ [ ] Show top rule combinations (which rules work best together?)
├─ [ ] Display false positive analysis (why did Rule X miss this case?)
├─ [ ] Recommend rule adjustments ("Lower pricing threshold by 5%")
└─ [ ] Show RL-discovered vulnerabilities (evasion patterns found)

Frontend (Enhanced V2ChatPanel):
├─ [ ] Add "Ask about scoring logic" context menu
├─ [ ] Example: "Why is this score 87? What would make it 70?"
├─ [ ] Function calling returns detailed explanations
├─ [ ] What-if scenarios: "If I change price by 10%, new score = X"
└─ [ ] Suggest improvements: "Based on outcomes, consider adjusting Rule 3"

Backend:
├─ [ ] Implement GET /api/rule-analytics (PPV by rule, correlation data)
├─ [ ] Implement RL agent: simulate evasion, find vulnerabilities
├─ [ ] Implement GET /api/rl-vulnerabilities (discovered evasion patterns)
├─ [ ] Auto-suggest rule updates from RL findings
└─ [ ] Create rule_vulnerability_history table
```

---

## PART 5: CURRENT STATE SUMMARY

```
✅ BUILT & WORKING (V2 UI)
├─ V2 layout framework (sidebar, header, main content)
├─ V2ChatPanel (Ask-AI sidebar, session memory, streaming)
├─ V2AITuningPage (UI for weight/rule tuning)
├─ Dashboard, Investigations, Shipping Intelligence pages
├─ Entity resolution visualization
├─ Risk score breakdown components
└─ Referral package generation (14 sections)

✅ BACKEND READY (Ask-AI)
├─ AskAIAgent class (Gemini 2.5 Flash integration)
├─ 10 tools defined in ask_ai_tools.py (not yet wired)
├─ SSE streaming endpoint (/api/gemini/assistant/stream)
└─ Function calling infrastructure ready

⚠️ PARTIALLY WIRED (V2AITuningPage)
├─ UI looks good, shows sliders and rule controls
├─ Backend APIs partially stubbed (GET /api/model/weights, etc.)
├─ No database persistence yet
├─ No rule version control / audit trail
└─ No A/B testing or dry-run preview

❌ NOT YET IMPLEMENTED
├─ Rules database (rules, versions, changelog)
├─ Rule analytics (PPV per rule, correlation)
├─ Dynamic threshold tuning UI
├─ Ask-AI function calling (10 tools not yet callable from UI)
├─ RL agent vulnerabilityanalysis
├─ A/B testing interface
└─ Advanced rule recommendation engine
```

---

## PART 6: ENHANCEMENT ROADMAP

### Phase 1: Gate 1 (Weeks 1-8)
**Focus:** Rules database + V2AITuningPage backend

```
Week 1-2: Rules Database
├─ Create tables: rules, rule_versions, rule_change_log
├─ Implement CRUD endpoints
├─ Add audit trail logging

Week 3-4: V2AITuningPage Backend
├─ Wire GET /api/model/weights (read from DB)
├─ Wire POST /api/model/weights (write to DB)
├─ Display rule effectiveness metrics
└─ Add dry-run preview

Week 5-6: Monitoring Dashboard
├─ Data quality metrics (ISF, AIS, ER completeness)
├─ Rule effectiveness heatmap
├─ Performance drift alerts

Week 7-8: Testing & Launch
├─ Test weight changes persist across restarts
├─ Test audit trail captures all changes
└─ Verify Gate 1 accuracy targets (≥10% PPV)
```

### Phase 2: Gate 2 (Weeks 9-16)
**Focus:** Ask-AI function calling + dynamic thresholding

```
Week 9-10: Function Calling
├─ Wire up 10 ask_ai_tools in AskAIAgent
├─ Display source cards in V2ChatPanel
├─ Show "Analyzing..." indicators

Week 11-12: Threshold Tuning UI
├─ Build /threshold-tuning page
├─ Display PPV curves
├─ Implement auto-threshold recommendation

Week 13-14: Weekly Retraining
├─ Create scheduler: weekly LGB retrain
├─ Implement threshold auto-adjust
└─ Track PPV trends

Week 15-16: Testing & Launch
├─ Verify Ask-AI accuracy (use 10 tools correctly)
├─ Verify threshold tuning improves PPV to 30%+
└─ Test dynamic thresholding algorithm
```

### Phase 3: Gate 3 (Weeks 17-24)
**Focus:** Advanced analytics + RL integration

```
Week 17-18: Rule Analytics
├─ Implement /admin/rule-analytics endpoint
├─ Build PPV heatmap visualization
├─ Show rule combination analysis

Week 19-20: RL Agent
├─ Implement adversarial evasion simulator
├─ Find vulnerabilities in current rules
├─ Suggest improvements

Week 21-22: Enhanced Ask-AI
├─ Add "explain scoring logic" intent
├─ Implement what-if analysis via function calls
└─ Suggest rule improvements

Week 23-24: Testing & Launch
├─ Verify RL vulnerabilities found match real evasion
├─ Verify rule suggestions improve PPV to 50%+
└─ End-to-end testing of full system
```

---

## DEPLOYMENT INSTRUCTIONS

**Current Status:** V2 running on localhost:3001

```bash
# Check status
./scripts/deploy-local.sh status

# Rebuild UI only (after frontend changes)
./scripts/deploy-local.sh ui

# Full clean rebuild
./scripts/deploy-local.sh full

# View logs
./scripts/deploy-local.sh logs

# Access UI
# Dashboard: http://localhost:3001/dashboard
# Investigations: http://localhost:3001/investigations
# AI Tuning: http://localhost:3001/ai-tuning
# API: http://localhost:8000
```

---

## SUMMARY

**V2 is the current production UI.** It provides:
- Modern, responsive dashboard (React + Tailwind CSS)
- Ask-AI intelligent assistant (V2ChatPanel sidebar)
- AI Tuning & Rules dashboard (V2AITuningPage)
- Full integration with backend API

**To move from Rules-Manual to Rules-AI-Driven:**
1. Gate 1: Complete rules database + backend APIs
2. Gate 2: Enable Ask-AI function calling + threshold tuning UI
3. Gate 3: Add RL vulnerabilityanalysis + advanced rules recommendations

**Estimated effort:** 8-13 weeks for full enhancement (can be parallelized with model development)
