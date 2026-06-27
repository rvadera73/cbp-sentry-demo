# Risk Model Management Tab — Design Discussion

**Status**: Pre-Implementation Design Review  
**Date**: 2026-06-25  
**Purpose**: Align design with actual data, styling, and API before implementing

---

## 1. ACTUAL SYSTEM STATE (Database Reality Check)

### What We Have Right Now

**Risk Models Table** (2 models):
```
id: 'risk-model-v3.0'
  - model_id: v3.0
  - name: Precise Risk Model v3.0
  - status: staging
  - framework: xgboost
  - feature_count: 72
  - deployed_at: NULL
  - created_at: 2026-06-13 18:43:10

id: 'model-v2.1-8783ad37'
  - model_id: v2.1
  - name: CBP Risk Model v2.1 (Legacy)
  - status: deprecated
  - framework: rule-based
  - feature_count: 72
  - deprecated_at: 2026-06-13T19:17:14
```

**Shipments & Scoring**:
- shipments: 1,396 rows (actual import records)
- risk_score_components: 9,772 rows (detailed factor breakdowns)
- risk_scores_cache: 1 row (live scoring state)

**What's EMPTY** (0 rows):
- ❌ model_score_history (doesn't exist in this DB)
- ❌ performance_gate_results (0 rows)
- ❌ dataset_baselines (0 rows)
- ❌ model_score_history (we created, but it's not here)

**What ACTUALLY EXISTS**:
- ✅ risk_models (2 versions)
- ✅ shipments (1,396)
- ✅ risk_score_components (scoring breakdown per shipment)
- ✅ risk_scores_cache (current production state)

---

## 2. REFERRAL PACKAGE STYLING REFERENCE

From `ReferralPackageV2.tsx`, the production standard is:

### Color Palette
```
Primary: #005EA2 (CBP Blue)
Dark: #0B1F33 (Navy)
Risk Colors:
  - CRITICAL (≥80): bg:#FEE2E2, text:#991B1B
  - HIGH (65-79): bg:#FEF3C7, text:#92400E
  - MEDIUM (40-65): bg:#FFF7ED, text:#9A3412
  - LOW (<40): bg:#DCFCE7, text:#166534
```

### Typography Pattern
```
Headers: font-bold text-[#0B1F33]
Section titles: text-sm font-bold
Subtitles: text-[11px] text-slate-500
Section numbers: Circles with #005EA2 background, white text
```

### Component Patterns
```
- Section numbers in blue circles (size: w-8 h-8)
- Cards: white background, border-l-2 border-[#005EA2]
- Tables: Headers with stripes, data in rows
- Status badges: Color-coded risk levels
- Info boxes: Icon + text with relevant colors
```

---

## 3. PROPOSED TAB STRUCTURE (FUNCTIONAL with REAL DATA)

### Tab 1: Overview — Model Status & Current Risk Distribution

**What to display**:
- Active model card (v3.0 staging / v2.1 deprecated)
- Score distribution pie chart (1,396 shipments):
  - CRITICAL (≥80): X cases
  - HIGH (65-79): X cases
  - MEDIUM (40-65): X cases
  - LOW (<40): X cases
- Model status timeline
- Quick stats: Feature count, framework, created date

**Styling**: 
- Use ReferralPackageV2 section headers (blue circle numbers)
- Risk color badges for distribution
- Cards with blue left border

**Data source**: 
- risk_models table
- shipments + risk_scores_cache aggregate

---

### Tab 2: Model Registry — Version Management

**What to display**:
- Version cards for v3.0 and v2.1
  - Status: staging / deprecated / production
  - Framework: xgboost / rule-based
  - Created date, created by
  - Feature count
  - Deployment status
- Lineage timeline showing progression
- Action buttons (promote, rollback, deprecate)

**Styling**:
- Cards matching ReferralPackageV2 (blue border-l-2)
- Status badges with appropriate colors
- Timeline showing v2.1 → v3.0 progression

**Data source**:
- risk_models table
- Direct display of version, status, framework

---

### Tab 3: Performance — Scoring Distribution & Model Comparison

**What to display**:
- Histogram of scores across 1,396 shipments
- Score distribution by risk tier
- Feature importance breakdown
- Comparison: v3.0 (staging) vs v2.1 (deprecated)
- Confidence intervals / uncertainty visualization

**Styling**:
- Charts with CBP blue color scheme
- Risk color gradients matching distribution
- Data table with sortable columns

**Data source**:
- shipments + risk_scores_cache (current scores)
- risk_score_components (factor breakdown)

---

### Tab 4: Score Components — Factor Breakdown per Shipment

**What to display**:
- Searchable table of shipments with:
  - Shipment ID
  - Current risk score
  - Top risk factors (from risk_score_components)
  - Score components breakdown
  - Corridor, commodity, shipper info
- Drill-down: Click shipment → see component details

**Styling**:
- Table with Referral Package styling
- Factor names with contribution % shown
- Color-coded risk indicators

**Data source**:
- shipments (1,396)
- risk_score_components (factor details)

---

### Tab 5: Configuration & Retraining

**What to display**:
- Current retraining config (from risk_retraining_config table)
- Feature configuration (72 features)
- Model hyperparameters
- Approval workflow (who can deploy)
- Last updated timestamp

**Styling**:
- Configuration cards
- Approval status badges
- Edit form (for admins only)

**Data source**:
- risk_retraining_config
- risk_models metadata

---

## 4. ALIGNMENT WITH REFERRAL PACKAGE TEMPLATE

### Matching Elements

| Element | Referral Package V2 | Risk Model Mgmt Tab |
|---------|-------------------|-------------------|
| Section Headers | Blue circle numbers + title | ✓ Use same pattern |
| Color Scheme | #005EA2 primary | ✓ Use same colors |
| Risk Badges | CRITICAL/HIGH/MEDIUM/LOW | ✓ Use same colors |
| Cards | White bg, border-l-2 #005EA2 | ✓ Use same style |
| Tables | Striped rows, bold headers | ✓ Use same pattern |
| Typography | font-bold text-[#0B1F33] | ✓ Use same fonts |
| Data Display | Fact/value pairs | ✓ Use same layout |

---

## 5. API ENDPOINTS NEEDED

### Existing Endpoints We Can Use

```
GET  /api/shipments?limit=X&offset=Y&risk_min=Z
     → Returns shipment list with current risk scores

GET  /api/risk-scoring/comprehensive
     → Returns full risk breakdown for one shipment
     
GET  /api/risk-corridors
     → Returns corridor definitions (helpful context)

GET  /api/model/metrics
     → Returns model performance metrics (if available)
```

### New Endpoints We Need to Add

```
GET  /api/models/registry
     → Returns all models (v3.0, v2.1) with full metadata
     
GET  /api/models/{model_id}/statistics
     → Returns score distribution histogram data
     → Count of cases by risk tier
     
GET  /api/models/{model_id}/components
     → Returns feature importance rankings
     
GET  /api/shipments/{shipment_id}/risk-breakdown
     → Returns all 9,772 component scores for a shipment
```

---

## 6. DESIGN QUESTIONS & DECISIONS NEEDED

### Question 1: Data Freshness
**Issue**: risk_scores_cache has 1 row - is this current production state or stale?
- **Option A**: Use risk_scores_cache as the source of truth (fast, simple)
- **Option B**: Recalculate scores in real-time from shipment data (accurate but slow)
- **Decision Needed**: Which source should drive the tabs?

### Question 2: Model Comparison
**Issue**: v3.0 (staging) hasn't been deployed yet. Should we compare against v2.1 (deprecated)?
- **Option A**: Show v3.0 vs v2.1 scoring differences (academic comparison)
- **Option B**: Show v3.0 alongside v2.1 lineage (historical progression)
- **Option C**: Only show v3.0 current state (simplest)
- **Decision Needed**: What should the comparison show?

### Question 3: Time Range
**Issue**: No timestamp data in risk_scores_cache. How far back should we show metrics?
- **Option A**: All-time data (start of project)
- **Option B**: Last 30 days (rolling window)
- **Option C**: Since v3.0 deployment (future-proof)
- **Decision Needed**: What time window makes sense?

### Question 4: Admin Actions
**Issue**: Can we actually promote/rollback models from the UI, or is this read-only?
- **Option A**: Read-only display (safe, no risk)
- **Option B**: Enable promote/rollback buttons (requires approval workflow)
- **Option C**: Show buttons but disable them (aspirational UI)
- **Decision Needed**: What's the scope for this MVP?

### Question 5: Feature Importance Display
**Issue**: How to show 72 features meaningfully in a tab?
- **Option A**: Top 10 features only (summarized)
- **Option B**: Searchable/filterable list (comprehensive)
- **Option C**: Group by category (Documentation, Routing, etc.)
- **Decision Needed**: How detailed should this be?

---

## 7. FONT & CSS ALIGNMENT CHECKLIST

### Fonts (from Referral Package)
- [ ] Headers: `font-bold text-[#0B1F33]`
- [ ] Section titles: `text-sm font-bold`
- [ ] Subtitles: `text-[11px] text-slate-500`
- [ ] Data values: `font-semibold text-slate-900`
- [ ] Section numbers: White text on #005EA2 circular background

### CSS Classes (Reusable from Referral)
```typescript
// Section number badge
className="w-8 h-8 rounded-full bg-[#005EA2] text-white text-[11px] font-bold flex items-center justify-center flex-shrink-0"

// Card with blue border
className="border-l-2 border-[#005EA2] bg-white rounded p-4"

// Risk badge (CRITICAL)
className="inline-block px-2.5 py-1 rounded text-[11px] font-bold text-red-700 bg-red-100"

// Table header
className="bg-[#005EA2] text-white font-bold text-[11px] uppercase"
```

---

## 8. IMPLEMENTATION ROADMAP (If Approved)

### Phase 1: Overview Tab (Easiest)
- Display active model (v3.0)
- Show score distribution pie chart (1,396 shipments)
- Use Referral Package styling

### Phase 2: Model Registry Tab
- Display v3.0 and v2.1 version cards
- Show lineage timeline
- Display metadata (framework, features, dates)

### Phase 3: Performance Tab
- Add score histogram
- Add risk tier distribution
- Add comparison view

### Phase 4: Score Components Tab
- Searchable shipment table
- Factor breakdown per shipment
- Drill-down details

### Phase 5: Configuration Tab
- Display current config
- Show feature count and hyperparameters
- Mock approval workflow UI

---

## 9. CRITICAL QUESTIONS FOR YOU

Before we implement, please clarify:

1. **Data Source**: Should we use `risk_scores_cache` or recalculate from shipment data?
2. **Model Scope**: Focus on v3.0 (staging) or compare v3.0 vs v2.1?
3. **Functionality**: Read-only display or enable promote/rollback?
4. **Time Range**: All-time, last 30 days, or since v3.0?
5. **Feature Display**: Top 10 features or all 72?
6. **API Changes**: Can we add new endpoints, or work with existing ones?

---

## 10. RISKS & CONSTRAINTS

**Risk 1**: Model state inconsistency
- v3.0 is "staging" but no deployed_at date
- Unclear if it's actually running in production
- **Mitigation**: Query the actual scoring endpoint to see what's running

**Risk 2**: Empty performance tables
- performance_gate_results: 0 rows (we tried to create these, but they're gone)
- **Mitigation**: Rebuild this data before tab goes live, or compute on-the-fly

**Risk 3**: Score timestamp issues
- risk_scores_cache has no created_at/updated_at
- Can't show "last updated" info
- **Mitigation**: Batch rescore and log timestamps before deploying

**Risk 4**: API endpoint availability
- Risk model endpoints exist but return limited data
- May need new endpoints
- **Mitigation**: Extend API or work within existing constraints

---

## Next Steps

1. **Review & Approve** this design
2. **Answer the 5 critical questions** above
3. **Design the UI layouts** for each tab (mockups)
4. **Plan API changes** (what endpoints to add/extend)
5. **Then implement** with confidence we're aligned

---

**Document prepared for design discussion before implementation.**  
**Please review and provide feedback on the 5 critical questions.**

