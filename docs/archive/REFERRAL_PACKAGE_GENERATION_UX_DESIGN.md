# Enhanced Referral Package Generation Feature — UX Design Specification
**Date:** May 27, 2026  
**Status:** Design Review Ready  
**Target User:** CBP Analyst (30-minute review cycle)  
**Integration Point:** ModernCaseInvestigationPage (new "Referral Package" tab)

---

## 1. FEATURE OVERVIEW

### User Journey
**CBP Analyst Workflow (30 minutes):**
1. Navigate to case investigation page
2. Click "Referral Package" tab
3. **Tab 1 (8 min):** Review auto-generated referral package with all 14 sections and risk data
4. **Tab 2 (15 min):** Step through structured analysis form (4 guided steps)
5. **Tab 2 (7 min):** Review officer signature and submit analysis
6. **System:** Archive both tabs together as case referral package

### Key Design Principles
- **Fast Scanning:** Tab 1 sections are collapsible; critical info surfaced first
- **Guided Workflow:** Tab 2 is a 4-step form, not blank canvas
- **Auditable:** Every decision captured with timestamp, officer ID, and justification
- **Consistent Styling:** Matches existing ReferralPackage CSS + design tokens
- **No New Dependencies:** Uses existing Lucide icons, established color scheme

---

## 2. OVERALL LAYOUT STRUCTURE

```
┌────────────────────────────────────────────────────────────────┐
│  Investigation Detail Page (ModernCaseInvestigationPage)       │
│                                                                │
│  Tabs: [Overview] [Risk Scoring] [Referral Package] [History]  │
│                                          ↑ NEW                 │
└────────────────────────────────────────────────────────────────┘
         ↓ (when Referral Package tab clicked)
┌────────────────────────────────────────────────────────────────┐
│  REFERRAL PACKAGE CONTAINER                                    │
│                                                                │
│  Sub-tabs: [Tab 1: Package Display] [Tab 2: Officer Analysis]  │
│                                                                │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                                                          │  │
│  │  TAB 1: REFERRAL PACKAGE DISPLAY                        │  │
│  │  (shows auto-generated referral with all 14 sections)   │  │
│  │                                                          │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                │
│  OR                                                            │
│                                                                │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                                                          │  │
│  │  TAB 2: OFFICER ANALYSIS (GUIDED FORM)                  │  │
│  │  - Step 1: Risk Assessment Confirmation                 │  │
│  │  - Step 2: Evidence Review Checklist                    │  │
│  │  - Step 3: Action Recommendation                        │  │
│  │  - Step 4: Officer Notes & Signature                    │  │
│  │                                                          │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

---

## 3. TAB 1 — REFERRAL PACKAGE DISPLAY

### Purpose
Display the auto-generated 14-section referral package with all datasets and risk scores. Officer can expand/collapse sections for fast scanning or deep dive.

### Layout Structure

#### 3.1 Header (Always Visible)
```
┌─────────────────────────────────────────────────────────────┐
│  REFERRAL PACKAGE GENERATED                                │
│  Package ID: REF-2026-05-27-SHP-000211                    │
│  Generated: May 27, 2026 14:32 UTC                         │
│  Shipment: SHP-000211 | Vessel: MSC Madrid                 │
│  Origin: China (Guangzhou) → US (Long Beach)              │
│                                                             │
│  Risk Score: 87/100 [HIGH RISK]  ▲ Confidence: 94%        │
│                                                             │
│  [Export as PDF] [Annotate] [Compare to Related Cases]    │
└─────────────────────────────────────────────────────────────┘
```

**Color Coding:**
- Risk Badge: `--risk-l3-bg` (pale red) + `--risk-l3-border` (vivid red)
- Risk Text: `--risk-l3-text` (crimson)
- Border: `--neutral-border`

---

#### 3.2 Quick Stats Bar (Collapsible)
```
┌─────────────────────────────────────────────────────────────┐
│  📊 QUICK STATS                                             │
│  ┌──────────┬──────────┬──────────┬──────────────────────┐ │
│  │ Critical │ High     │ Medium   │ Documentation Gaps   │ │
│  │ Signals: │ Severity:│ Risk:    │ (ISF Element 9)      │ │
│  │    5     │    12    │    8     │          YES          │ │
│  └──────────┴──────────┴──────────┴──────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

---

#### 3.3 The 14 Sections (Expandable Cards)

Each section follows this pattern. **Narrative sections (3-6, 3-7, 3-11, 3-14) include an edit button:**

```
Narrative sections have [Edit] button in header:
┌─────────────────────────────────────────────────────────────┐
│ ▼ [SECTION 3-6: Historical Import Pattern]    [Edit] [✏️]   │
│   (Officer can edit narrative; regenerate via Gemini)       │
│                                                             │
│ Current Narrative:                                          │
│ [LLM-generated 2-3 paragraphs of analysis]                │
│                                                             │
│ [Edit] button opens modal:                                 │
│ ┌────────────────────────────────────────────────────────┐ │
│ │ Edit Historical Import Pattern Narrative               │ │
│ │                                                        │ │
│ │ [Large text area with current content editable]       │ │
│ │                                                        │ │
│ │ [Save Changes] [Regenerate via Gemini] [Discard]    │ │
│ └────────────────────────────────────────────────────────┘ │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

Other sections follow this pattern:

```
┌─────────────────────────────────────────────────────────────┐
│ ▶ [SECTION 3-1: Shipment Identification]        [Status: ✓] │
│   MBL: US123456789 | HBL: HK123456 | ETA: Jun 02           │
│   Last Updated: 2 hours ago | Data Quality: Complete       │
│                                                             │
│ ▼ [SECTION 3-2: Line Items]                    [Status: ⚠]  │
│   ┌────────────────────────────────────────────────────┐   │
│   │ HTS Code: 7610.10.00 (Aluminum Extrusions)        │   │
│   │ Declared Qty: 250 MT                               │   │
│   │ Declared Value: $187,500 (0.75/kg)                │   │
│   │ Market Range: $0.85-$1.20/kg     ⚠ LOW PRICING   │   │
│   │                                                    │   │
│   │ Price Variance: -12% below market (Risk Flag)     │   │
│   │ [View Full Line Item Details]                     │   │
│   └────────────────────────────────────────────────────┘   │
│                                                             │
│ ▶ [SECTION 3-3: AIS Routing History]                       │
│   Port Calls: Guangzhou → Kaohsiung → Singapore → LA      │
│   Dwell in Singapore: 11 days (3x normal for commodity)   │
│   Last Updated: Real-time                                 │
│                                                             │
│ ... (10 more sections follow same pattern)                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Section Card Anatomy:**
- **Header Row:**
  - Status icon (✓ = complete, ⚠ = partial, ✗ = critical gap)
  - Section number + title
  - Right-aligned: data freshness ("2 hours ago") + data quality badge
  
- **Collapsed View:** 1-2 line summary of key facts
- **Expanded View:** Full details with color-coded flags

---

### 3.4 Risk Score Breakdown (Integrated Section)

Appears as special **"Section 3-12: Risk Score Breakdown"** with visualization:

```
┌─────────────────────────────────────────────────────────────┐
│ ▼ [SECTION 3-12: Risk Score Breakdown & Contributing Factors]│
│                                                              │
│   OVERALL SCORE: 87/100 [HIGH RISK - CRITICAL ACTION]      │
│                                                              │
│   Component Breakdown:                                       │
│   ┌──────────────────────────────────────────────────────┐  │
│   │ Documentation Risk       ████████░░  28/40  (Weight:35%)│ │
│   │ Commodity Risk          ███████░░░  25/35  (Weight:30%)│ │
│   │ Routing Anomalies       █████░░░░░  18/25  (Weight:20%)│ │
│   │ Party Risk Profile      ██████░░░░  10/15  (Weight:10%)│ │
│   │ Corridor Risk           ██░░░░░░░░   6/10  (Weight: 5%)│ │
│   └──────────────────────────────────────────────────────┘  │
│                                                              │
│   🔴 Top 3 Contributing Factors:                           │
│      1. ISF Element 9 Mismatch (declared: MY, actual: CN) │
│      2. Abnormal Dwell in Singapore (11 days vs 3 avg)    │
│      3. Pricing 12% below market baseline                 │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**Styling:**
- Progress bars use `--risk-l3-border` (red) for critical factors
- Percentages in monospace font
- Top 3 factors highlighted with 🔴 icon

---

### 3.5 Data Sources Footer (Always Visible)

```
┌─────────────────────────────────────────────────────────────┐
│ 📚 Data Sources & Attribution                              │
│                                                             │
│ • ISF 10+2 Data: CBP Automated Manifest System (100%)     │
│ • AIS Tracking: MarineTraffic API (Real-time, 98% uptime) │
│ • Entity Resolution: Senzing CORD Index (Confidence: 92%) │
│ • Price Benchmarking: USITC Trade Data (Jan-May 2026)     │
│ • Risk Scoring: CBP Sentry 7-Factor Engine (v2.1)         │
│                                                             │
│ Last Updated: May 27, 2026 14:35 UTC                      │
│ (Data refreshes automatically every 15 minutes)            │
│                                                             │
│ [Export Section Data]                                      │
└─────────────────────────────────────────────────────────────┘
```

**Note:** Data refreshes silently in background. No manual refresh UI needed.

---

## 4. TAB 2 — OFFICER ANALYSIS (STRUCTURED FORM)

### Purpose
Guide CBP Analyst through a 4-step workflow to capture their risk assessment, evidence review, and recommended action.

### 4.1 Overall Form Layout

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  OFFICER ANALYSIS FORM                                      │
│                                                             │
│  Progress: ████░░░░░░  Step 1/4 (25%)                      │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ STEP 1: RISK ASSESSMENT CONFIRMATION                │   │
│  │ (Agree/disagree with Sentry's 87/100 score)         │   │
│  │                                                     │   │
│  │ Your Assessment:                                    │   │
│  │ ◯ Agree (87/100 is appropriate)                    │   │
│  │ ◯ Adjust (I assess differently)                    │   │
│  │   └─ Your Score: [____] / 100                      │   │
│  │   └─ Reason for Adjustment:                        │   │
│  │       [Large text area - min 50 chars]              │   │
│  │                                                     │   │
│  │ Confidence in Your Assessment:                      │   │
│  │ ◯ Low (40-60% confident)  ◯ Medium (60-80%)        │   │
│  │ ◯ High (80%+)                                       │   │
│  │                                                     │   │
│  │ [Next Step] [Save Progress]                         │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

### 4.2 Step 1: Risk Assessment Confirmation

**Input Type:** Radio buttons + conditional score input + confidence selector

**Fields:**
1. **Agree/Adjust Radio:**
   - Agree: Accept Sentry's 87/100 score as final
   - Adjust: Override with officer's own assessment

2. **Conditional Score Input** (shows only if Adjust selected):
   - Number field: 0-100
   - Slider alternative (with visual risk color indicator)
   - Live risk level badge update (LOW/MEDIUM/HIGH/CRITICAL)

3. **Reason Text Area** (required if score adjusted):
   - Minimum 50 characters
   - Placeholder: "e.g., 'Reduced from 87 to 72 because vendor has 5-year compliant history despite current documentation gaps'"
   - Character count visible

4. **Confidence Level** (radio buttons):
   - Low (40-60%)
   - Medium (60-80%)
   - High (80%+)

**Navigation:**
- [Next Step] button (enabled after all required fields filled)
- [Save Progress] button (saves draft, allows return later)
- [Cancel] button (discard form)

**Validation:**
- If Adjust: score must be 0-100
- If score adjusted: reason is required
- Confidence must be selected
- Visual error messages in red (`--risk-l3-text`)

---

### 4.3 Step 2: Evidence Review Checklist

**Input Type:** Checkboxes + optional notes per item

```
┌─────────────────────────────────────────────────────────────┐
│ STEP 2: EVIDENCE REVIEW CHECKLIST                           │
│ (Verify which critical evidence items support the risk)     │
│                                                             │
│ Please confirm you've reviewed the following evidence:      │
│                                                             │
│ Critical Evidence (Must Review):                            │
│ ☑ ISF Element 9 Mismatch Report                            │
│   └─ Officer Notes: ________________ [Optional]            │
│                                                             │
│ ☑ Vessel Dwell Time Analysis                               │
│   └─ Officer Notes: ________________ [Optional]            │
│                                                             │
│ ☑ Price Variance Analysis (12% below market)               │
│   └─ Officer Notes: ________________ [Optional]            │
│                                                             │
│ ☑ Entity Resolution Report (Senzing Output)                │
│   └─ Officer Notes: ________________ [Optional]            │
│                                                             │
│ ☐ AIS Routing Pattern Analysis                             │
│   └─ Officer Notes: ________________ [Optional]            │
│                                                             │
│ ☐ Historical Import Patterns (Shipper Profile)             │
│   └─ Officer Notes: ________________ [Optional]            │
│                                                             │
│ ☐ Related Cases & Precedents (if applicable)               │
│   └─ Officer Notes: ________________ [Optional]            │
│                                                             │
│ Summary:                                                    │
│ You've reviewed: 4/7 evidence items                        │
│ Critical items: 4/4 ✓ (all required items reviewed)        │
│                                                             │
│ [Back] [Next Step] [Save Progress]                        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Logic:**
- **Critical Evidence (must have ☑):** 
  - ISF Element 9 Mismatch
  - Vessel Dwell Time
  - Price Variance
  - Entity Resolution
  
- **Supporting Evidence (optional ☐):**
  - AIS Routing
  - Historical Patterns
  - Related Cases

- **Validation Rule:** At least all "Critical" items must be checked
- If unchecked critical item: warning message on Next button
- Optional notes per item: free-text field (no char limit)

---

### 4.4 Step 3: Action Recommendation

**Input Type:** Dropdown selection + conditional fields

```
┌─────────────────────────────────────────────────────────────┐
│ STEP 3: ACTION RECOMMENDATION                               │
│ (What action should CBP take on this shipment?)             │
│                                                             │
│ Recommended Action: [▼ Select Action]                      │
│                                                             │
│ When user selects "Execute TRLED Referral":                │
│ ┌─────────────────────────────────────────────────────┐   │
│ │ Referral Type:    [▼ EAPA Investigation]            │   │
│ │ Priority Level:   [▼ High Priority]                 │   │
│ │ Holding Period:   [___] days (default: 30)         │   │
│ │ Assigned To:      [▼ Select District/Officer]      │   │
│ │ Notes for Examiner: [Large text area]              │   │
│ └─────────────────────────────────────────────────────┘   │
│                                                             │
│ OR                                                          │
│                                                             │
│ When user selects "Hold for Examination":                  │
│ ┌─────────────────────────────────────────────────────┐   │
│ │ Hold Duration: [___] days (default: 5)             │   │
│ │ Examination Type: [▼ Documentary / Physical]       │   │
│ │ Examination Scope: [Large text area]               │   │
│ │ Notify Importer: [☑] Yes / [☐] No                │   │
│ └─────────────────────────────────────────────────────┘   │
│                                                             │
│ OR                                                          │
│                                                             │
│ When user selects "Release with Monitoring":               │
│ ┌─────────────────────────────────────────────────────┐   │
│ │ Monitoring Type: [▼ Standard / Enhanced / Real-time]│   │
│ │ Duration: [___] days (default: 60)                 │   │
│ │ Conditions: [Large text area]                      │   │
│ │ Audit Trail Flag: [☑] Yes / [☐] No               │   │
│ └─────────────────────────────────────────────────────┘   │
│                                                             │
│ [Back] [Next Step] [Save Progress]                        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Actions Available:**
1. **Execute TRLED Referral**
   - Referral Type dropdown (EAPA, Duty Evasion, Fraud, etc.)
   - Priority (Low/Medium/High)
   - Holding Period (days, default 30)
   - Assigned District/Officer
   - Free-form notes for examiner

2. **Hold for Examination**
   - Hold Duration (days, default 5)
   - Exam Type (Documentary / Physical / Hybrid)
   - Scope details (free-text)
   - Notify Importer? (Y/N)

3. **Release with Monitoring**
   - Monitoring Type (Standard/Enhanced/Real-time)
   - Duration (days, default 60)
   - Conditions (free-text)
   - Audit Trail Flag (Y/N)

**Validation:**
- Action selection is required
- All conditional fields (if action selected) are required
- Text fields: min 10 characters for notes

---

### 4.5 Step 4: Officer Notes & Signature

**Input Type:** Large text area + signature capture + metadata

```
┌─────────────────────────────────────────────────────────────┐
│ STEP 4: OFFICER NOTES & SIGNATURE                           │
│                                                             │
│ Final Case Summary / Notes:                                │
│ (Required: min 50 characters; max 2000 characters)         │
│                                                             │
│ [Large text area with formatting toolbar]                 │
│ - Placeholder: "Summarize your investigation findings..." │
│ - Char count: 0/2000                                       │
│                                                             │
│ Officer Certification:                                     │
│ □ I certify that I have reviewed all relevant evidence     │
│   and my assessment above is accurate and complete.        │
│   (Must be checked before submission)                      │
│                                                             │
│ Officer Information (Pre-filled):                          │
│ Name: [John Smith] (Read-only, from session)              │
│ Title: [CBP Supervisory Officer] (Read-only)              │
│ Badge #: [45821] (Read-only)                              │
│ District: [Los Angeles Field Office] (Read-only)          │
│ Date/Time: May 27, 2026 14:47 UTC (Auto-filled)          │
│                                                             │
│ Digital Signature:                                         │
│ [I sign this document using my PIV/CAC credentials]       │
│ [Authenticate with PIV Card] [Use e-signature]            │
│                                                             │
│ [Back] [Submit Analysis] [Save as Draft]                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Fields:**
1. **Final Notes Text Area:**
   - Min 50 chars, max 2000
   - Optional markdown formatting (bold, italic, bullet lists)
   - Auto-save every 30 seconds (draft)

2. **Certification Checkbox:**
   - Required before submission
   - Text: "I certify that I have reviewed all relevant evidence and my assessment above is accurate and complete."

3. **Officer Info (Pre-filled, Read-only):**
   - Name (from authenticated session)
   - Title
   - Badge Number
   - District
   - Current date/time (auto-populated)

4. **Digital Signature:**
   - Option 1: PIV/CAC authentication (button)
   - Option 2: E-signature via system (alternative)
   - On success: signature timestamp + verified badge shown

---

### 4.6 Form Submission & Result

**On Submit:**
```
Success Message:
┌─────────────────────────────────────────────────────────────┐
│ ✓ ANALYSIS SUBMITTED SUCCESSFULLY                           │
│                                                             │
│ Package ID:    REF-2026-05-27-SHP-000211                  │
│ Analysis ID:   ANA-2026-05-27-001                          │
│ Officer:       John Smith (Badge #45821)                   │
│ Submitted:     May 27, 2026 14:51 UTC                      │
│                                                             │
│ Recommended Action: Execute TRLED Referral                │
│ Risk Score (Officer): 85/100 (Adjusted from 87)           │
│ Confidence: High (85%+)                                    │
│                                                             │
│ Next Steps:                                                │
│ • Referral forwarded to LA EAPA Unit                       │
│ • Hold period: 30 days                                     │
│ • Tracking Number: TRACK-2026-0527-001                     │
│                                                             │
│ [View Complete Package] [Print Analysis] [Return to Cases] │
│ [Email to Supervisor] [Add to Investigation File]          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 5. STYLING & DESIGN CONSISTENCY

### 5.1 Color Scheme

| Element | CSS Variable | Purpose |
|---------|--------------|---------|
| Primary Headers | `--federal-navy` (#003366) | Section titles, step headers |
| Risk Badge (HIGH) | `--risk-l3-bg` (#fcf2f2) | Background |
| Risk Border (HIGH) | `--risk-l3-border` (#d9381e) | Borders, accent |
| Risk Text (HIGH) | `--risk-l3-text` (#b50909) | Text on risk items |
| Success Checkmark | `--status-success` (#2E8540) | Data quality badges |
| Warning Icons | `--status-warning` (#E6A100) | Flags, anomalies |
| Button Primary | `--uswds-primary-blue` (#0050D8) | [Next Step], [Submit] |
| Button Secondary | `--uswds-navy` (#003366) | [Back], [Save Draft] |
| Border | `--neutral-border` (#D0D0D0) | Card borders, dividers |
| Background | `--neutral-white` (#FFFFFF) | Card backgrounds |
| Section Bg | `--neutral-light-card` (#F5F5F5) | Collapsible section BG |

### 5.2 Typography

| Element | Font | Size | Weight |
|---------|------|------|--------|
| Page Title | Public Sans | 24px | 700 (bold) |
| Section Headers | Public Sans | 18px | 600 |
| Form Labels | Public Sans | 14px | 600 |
| Body Text | Public Sans | 14px | 400 |
| Monospace (Data) | Roboto Mono | 13px | 400 |
| Data Values | Roboto Mono | 14px | 500 |

### 5.3 Spacing

Using design token `--space-*` scale:
- `--space-sm` (8px): Within form inputs
- `--space-md` (16px): Between form fields
- `--space-lg` (24px): Between sections
- `--space-xl` (32px): Between major containers

### 5.4 Icons

**Use Lucide React icons:**
- `ChevronDown` / `ChevronUp` — Section expand/collapse
- `Check` — Completed items
- `AlertTriangle` — Critical flags
- `AlertCircle` — Medium warnings
- `Info` — Info messages
- `Download` — Export/PDF
- `Share` — Send analysis
- `Clock` — Timestamps
- `User` — Officer info
- `Zap` — Critical signals

---

## 6. RESPONSIVE DESIGN

### Desktop (≥1024px)
- Two-column layout where possible
- Form fields side-by-side (label + input)
- All sections expanded by default
- Full data tables visible

### Tablet (768px–1023px)
- Single column layout
- Form fields stacked
- Sections collapsed by default (officer expands as needed)
- Responsive tables (reduce padding)

### Mobile (<768px)
- Single column throughout
- Collapsed sections mandatory
- Form fields full-width
- Buttons full-width
- Reduced font sizes (12px min for readability)

---

## 7. ACCESSIBILITY (WCAG 2.1 AA)

### Focus Management
- Tab order follows visual flow (top-to-bottom, left-to-right)
- Focus ring: 3px solid `--federal-focus` (#0050D8)
- All buttons, links, form inputs keyboard accessible

### Semantic HTML
- Form: `<form>` element with `<fieldset>` per step
- Labels: All inputs have `<label>` with `for` attribute
- Buttons: `<button>` elements with clear text ("Next Step", not "Next")
- Radio/Checkbox: Native `<input type="radio/checkbox">` + `<label>`

### Screen Reader Support
- Page structure: `<h1>` (page title), `<h2>` (step title), `<h3>` (subsections)
- Form legend per step
- ARIA live region for form validation errors (`aria-live="polite"`)
- Tab indicator: `role="tablist"`, `role="tab"`, `role="tabpanel"`
- Progress bar: `aria-valuenow`, `aria-valuemin`, `aria-valuemax`

### Color Contrast (WCAG AA = 4.5:1 minimum)
- All text on backgrounds: verify 4.5:1 ratio
- Icon colors: ensure sufficient contrast
- Form error text (`--risk-l3-text` on white): 11.3:1 ✓

---

## 8. IMPLEMENTATION ROADMAP

### Phase 1: UI Component & Layout (Week 1)
- [ ] Create `ReferralPackageGenerationTab.tsx` (main container)
- [ ] Create `ReferralDisplayPanel.tsx` (Tab 1 layout)
- [ ] Create `OfficerAnalysisForm.tsx` (Tab 2 container)
- [ ] Implement 4-step form logic with state management
- [ ] Add styling (CSS module or inline via design tokens)
- [ ] Wire up Tab 1 ↔ Tab 2 navigation

### Phase 2: Data Integration (Week 2)
- [ ] Connect Tab 1 to real API data (CORD, Senzing, AIS, risk engine)
- [ ] Implement data fetching with loading states
- [ ] Add error boundaries and fallback UI
- [ ] Populate mock data for 14 sections

### Phase 3: Officer Analysis Workflow (Week 3)
- [ ] Implement Step 1 logic (score adjustment, validation)
- [ ] Implement Step 2 checklist (evidence review)
- [ ] Implement Step 3 action selection + conditional fields
- [ ] Implement Step 4 signature capture (PIV/CAC or e-signature)
- [ ] Add form validation across all steps

### Phase 4: Backend Integration (Week 4)
- [ ] Create endpoint: `POST /api/officer-analysis` (save analysis)
- [ ] Create endpoint: `GET /api/officer-analysis/{analysis_id}` (retrieve)
- [ ] Create endpoint: `POST /api/referral-packages` (archive package)
- [ ] Implement audit logging (officer ID, timestamp, actions)
- [ ] Add notification system (supervisor email on submission)

### Phase 5: Testing & QA (Week 5)
- [ ] Unit tests for form validation
- [ ] Integration tests for data flow
- [ ] Accessibility testing (WCAG 2.1 AA)
- [ ] User testing with CBP analyst (30-minute workflow)
- [ ] Performance testing (large datasets)

---

## 9. FILE STRUCTURE

```
ui/src/
├── components/
│   └── referral-generation/
│       ├── ReferralPackageGenerationTab.tsx        (main container)
│       ├── ReferralPackageGenerationTab.css        (styling)
│       ├── ReferralDisplayPanel.tsx                (Tab 1)
│       ├── ReferralDisplayPanel.css
│       ├── OfficerAnalysisForm.tsx                 (Tab 2 container)
│       ├── OfficerAnalysisForm.css
│       ├── steps/
│       │   ├── Step1RiskAssessment.tsx
│       │   ├── Step2EvidenceReview.tsx
│       │   ├── Step3ActionRecommendation.tsx
│       │   ├── Step4OfficeSignature.tsx
│       │   └── StepStyles.css
│       ├── types/
│       │   └── ReferralGeneration.types.ts         (TypeScript interfaces)
│       └── hooks/
│           ├── useReferralDisplay.ts               (Tab 1 logic)
│           └── useOfficerAnalysisForm.ts           (Tab 2 logic)
│
└── pages/
    └── ModernCaseInvestigationPage.tsx             (UPDATED: add new tab)
```

---

## 10. DESIGN DECISIONS — APPROVED ✅

### Data Refresh
- ✅ Auto-refreshes silently every 15 minutes
- No manual "Refresh Now" button needed
- No UI indicator required

### Tab 1 Editing
- ✅ Narrative sections (3-6, 3-7, 3-11, 3-14) have full-blown LLM edit capability
- Each narrative has [Edit] button opening text editor
- "[Regenerate via Gemini]" button to re-prompt AI
- Data sections (3-1 through 3-5, 3-8 through 3-10) are read-only
- Officer can verify/correct narratives before Tab 2

### Related Cases
- ✅ Deferred to Phase 2 (enhancement feature)
- Not included in MVP

### PDF Export Format
- ✅ Formal federal referral document (matching Section 3 of White GLOVE)
- Header: "Referral Package — CBP CSOP-BP-GS-26-0001"
- All 14 sections in professional format
- Officer's analysis (Tab 2) appended after sections
- Legal footer with officer signature & timestamp
- Color-coded risk indicators throughout
- File naming: `Referral-{referral_id}-{date}.pdf`

### Supervisor Escalation
- ✅ Deferred to Phase 2 (enhancement feature)
- Direct submission in Phase 1; supervisor notification can be added later

---

## 11. READY FOR PHASE 1 IMPLEMENTATION
