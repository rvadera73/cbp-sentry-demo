# Complete Referral Package Generation Feature — Build Guide
**Status:** Core Components Complete, Ready for Final Assembly  
**Completion:** 40% (Types + Hooks + Main Components)  
**Remaining:** 60% (CSS + Additional Components + Backend)

---

## ✅ COMPLETED (Ready to Use)

### TypeScript Types
- ✅ `/ui/src/components/referral-generation/types/ReferralGeneration.types.ts` (470 lines)

### Main Container
- ✅ `/ui/src/components/referral-generation/ReferralPackageGenerationTab.tsx` (180 lines)
- ✅ `/ui/src/components/referral-generation/ReferralPackageGenerationTab.css` (320 lines)

### Hooks (Data Management)
- ✅ `/ui/src/components/referral-generation/hooks/useReferralDisplay.ts` (150 lines)
- ✅ `/ui/src/components/referral-generation/hooks/useOfficerAnalysisForm.ts` (280 lines)

### Display Component
- ✅ `/ui/src/components/referral-generation/ReferralDisplayPanel.tsx` (240 lines)

---

## 📋 REMAINING TO BUILD

### 1. CSS Files (3 files)

#### ReferralDisplayPanel.css (250 lines)
```css
.referral-display-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow-y: auto;
}

.referral-display-panel__content {
  flex: 1;
  padding: var(--space-lg);
}

.display-section {
  margin-bottom: var(--space-xl);
}

.section-group-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--federal-navy);
  margin-bottom: var(--space-lg);
  border-bottom: 2px solid var(--neutral-border);
  padding-bottom: var(--space-md);
}

.sections-container {
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
}

.section-card {
  border: 1px solid var(--neutral-border);
  border-radius: var(--radius-md);
  background: var(--neutral-white);
  overflow: hidden;
  transition: all 0.2s ease;
}

.section-card.edited {
  border-color: var(--status-warning);
  background: linear-gradient(90deg, transparent 0%, var(--risk-l2-bg) 100%);
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-lg);
  cursor: pointer;
  background: var(--neutral-light-bg);
  user-select: none;
  transition: background 0.2s ease;
}

.section-header:hover {
  background: var(--neutral-light-card);
}

.section-title-group {
  display: flex;
  align-items: center;
  gap: var(--space-md);
  flex: 1;
}

.section-title {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: var(--federal-navy);
}

.edited-badge {
  display: inline-block;
  padding: 2px 8px;
  background: var(--status-warning);
  color: white;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 600;
}

.edit-button {
  padding: 6px;
  background: var(--federal-focus);
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  display: flex;
  align-items: center;
  transition: all 0.2s ease;
}

.edit-button:hover {
  background: var(--uswds-blue-hover);
  transform: scale(1.05);
}

.section-content {
  padding: var(--space-lg);
  border-top: 1px solid var(--neutral-border);
}

.data-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-md);
}

.data-row {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: var(--space-sm);
  background: var(--neutral-light-bg);
  border-radius: var(--radius-sm);
}

.data-key {
  font-weight: 600;
  font-size: 12px;
  color: var(--neutral-text-secondary);
  text-transform: capitalize;
}

.data-value {
  font-size: 14px;
  color: var(--neutral-text-primary);
  font-family: var(--font-family-mono);
  word-break: break-word;
}

.risk-breakdown-card {
  border: 2px solid var(--risk-l3-border);
  border-radius: var(--radius-md);
  background: var(--risk-l3-bg);
  padding: var(--space-lg);
  margin-bottom: var(--space-lg);
}

.risk-breakdown-card h3 {
  margin: 0 0 var(--space-lg) 0;
  color: var(--risk-l3-text);
  font-size: 18px;
}

.score-display {
  display: flex;
  align-items: baseline;
  gap: 8px;
  margin-bottom: var(--space-lg);
}

.score-value {
  font-size: 48px;
  font-weight: 700;
  color: var(--risk-l3-border);
  font-family: var(--font-family-mono);
}

.score-label {
  font-size: 18px;
  color: var(--risk-l3-text);
}

.components-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: var(--space-lg);
  margin-bottom: var(--space-lg);
}

.component-item {
  background: white;
  padding: var(--space-md);
  border-radius: var(--radius-sm);
  border: 1px solid var(--neutral-border);
}

.component-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
  font-size: 13px;
}

.component-name {
  font-weight: 600;
  color: var(--federal-navy);
}

.component-weight {
  color: var(--neutral-text-secondary);
}

.progress-bar {
  height: 6px;
  background: var(--neutral-border-light);
  border-radius: 3px;
  overflow: hidden;
  margin-bottom: 6px;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--status-warning), var(--risk-l3-border));
  transition: width 0.3s ease;
}

.component-score {
  font-size: 12px;
  color: var(--neutral-text-secondary);
  font-family: var(--font-family-mono);
}

.evidence-section {
  background: white;
  padding: var(--space-md);
  border-radius: var(--radius-sm);
  border: 1px solid var(--neutral-border);
}

.evidence-section h4 {
  margin: 0 0 var(--space-sm) 0;
  font-size: 14px;
  color: var(--federal-navy);
}

.evidence-section ul {
  margin: 0;
  padding-left: var(--space-lg);
  list-style: disc;
}

.evidence-section li {
  margin-bottom: 4px;
  font-size: 13px;
  color: var(--neutral-text-primary);
}

.data-sources-card {
  border: 1px solid var(--neutral-border);
  border-radius: var(--radius-md);
  padding: var(--space-lg);
  background: var(--neutral-light-bg);
}

.data-sources-card h4 {
  margin: 0 0 var(--space-md) 0;
  color: var(--federal-navy);
  font-size: 16px;
}

.data-sources-card ul {
  margin: 0 0 var(--space-md) 0;
  padding-left: var(--space-lg);
  list-style: disc;
}

.data-sources-card li {
  margin-bottom: 6px;
  font-size: 13px;
  color: var(--neutral-text-primary);
  font-family: var(--font-family-mono);
}

.timestamp {
  margin: 0;
  font-size: 12px;
  color: var(--neutral-text-secondary);
  font-style: italic;
}

@media (max-width: 768px) {
  .data-grid {
    grid-template-columns: 1fr;
  }

  .components-grid {
    grid-template-columns: 1fr;
  }

  .section-title-group {
    gap: var(--space-sm);
  }

  .section-title {
    font-size: 14px;
  }
}
```

#### OfficerAnalysisForm.css (300 lines)
```css
.officer-analysis-form {
  display: flex;
  flex-direction: column;
  gap: var(--space-lg);
  padding: var(--space-lg);
}

.form-progress {
  margin-bottom: var(--space-lg);
}

.progress-bar {
  height: 4px;
  background: var(--neutral-border-light);
  border-radius: 2px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--federal-focus), var(--uswds-primary-blue));
  transition: width 0.3s ease;
}

.progress-label {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: var(--neutral-text-secondary);
  margin-top: 8px;
}

.step-container {
  background: var(--neutral-white);
  border: 1px solid var(--neutral-border);
  border-radius: var(--radius-md);
  padding: var(--space-lg);
  animation: slideIn 0.3s ease;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.step-header {
  margin-bottom: var(--space-lg);
  border-bottom: 2px solid var(--neutral-border);
  padding-bottom: var(--space-md);
}

.step-title {
  margin: 0;
  font-size: 20px;
  font-weight: 700;
  color: var(--federal-navy);
}

.step-description {
  margin: 4px 0 0 0;
  font-size: 13px;
  color: var(--neutral-text-secondary);
}

.form-group {
  margin-bottom: var(--space-lg);
}

.form-label {
  display: block;
  margin-bottom: var(--space-sm);
  font-weight: 600;
  font-size: 14px;
  color: var(--federal-navy);
}

.form-label.required::after {
  content: ' *';
  color: var(--risk-l3-border);
}

.form-input,
.form-select,
.form-textarea {
  width: 100%;
  padding: var(--space-sm);
  border: 1px solid var(--neutral-border);
  border-radius: var(--radius-md);
  font-family: var(--font-family);
  font-size: 14px;
  color: var(--neutral-text-primary);
  transition: all 0.2s ease;
}

.form-input:focus,
.form-select:focus,
.form-textarea:focus {
  outline: none;
  border-color: var(--federal-focus);
  box-shadow: 0 0 0 3px rgba(0, 80, 216, 0.1);
}

.form-textarea {
  resize: vertical;
  min-height: 120px;
}

.radio-group,
.checkbox-group {
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
}

.radio-option,
.checkbox-option {
  display: flex;
  align-items: flex-start;
  gap: var(--space-sm);
}

.radio-option input[type="radio"],
.checkbox-option input[type="checkbox"] {
  margin-top: 4px;
  cursor: pointer;
}

.option-label {
  display: flex;
  flex-direction: column;
  gap: 2px;
  cursor: pointer;
  flex: 1;
}

.option-text {
  font-weight: 500;
  color: var(--neutral-text-primary);
}

.option-hint {
  font-size: 12px;
  color: var(--neutral-text-secondary);
}

.error-message {
  display: block;
  margin-top: 4px;
  padding: 6px 10px;
  background: var(--risk-l3-bg);
  color: var(--risk-l3-text);
  border-left: 3px solid var(--risk-l3-border);
  font-size: 12px;
  border-radius: 2px;
}

.validation-errors {
  padding: var(--space-md);
  background: var(--risk-l3-bg);
  border: 1px solid var(--risk-l3-border);
  border-radius: var(--radius-md);
  margin-bottom: var(--space-lg);
}

.validation-errors h4 {
  margin: 0 0 var(--space-sm) 0;
  color: var(--risk-l3-text);
  font-size: 14px;
}

.validation-errors ul {
  margin: 0;
  padding-left: var(--space-lg);
  color: var(--risk-l3-text);
  font-size: 13px;
}

.form-footer {
  display: flex;
  justify-content: space-between;
  gap: var(--space-lg);
  padding-top: var(--space-lg);
  border-top: 1px solid var(--neutral-border);
  margin-top: var(--space-lg);
}

.button-group {
  display: flex;
  gap: var(--space-md);
}

.btn {
  padding: 10px 20px;
  border: none;
  border-radius: var(--radius-md);
  font-weight: 600;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s ease;
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-primary {
  background: var(--federal-focus);
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: var(--uswds-blue-hover);
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 80, 216, 0.3);
}

.btn-secondary {
  background: var(--neutral-light-bg);
  color: var(--federal-navy);
  border: 1px solid var(--neutral-border);
}

.btn-secondary:hover:not(:disabled) {
  background: var(--neutral-border-light);
}

.btn-danger {
  background: var(--risk-l3-border);
  color: white;
}

.btn-danger:hover:not(:disabled) {
  background: var(--risk-l3-accent);
}

@media (max-width: 768px) {
  .officer-analysis-form {
    padding: var(--space-md);
  }

  .form-footer {
    flex-direction: column;
  }

  .button-group {
    width: 100%;
    flex-direction: column;
  }

  .btn {
    width: 100%;
    justify-content: center;
  }
}
```

---

### 2. React Components (5 files)

#### OfficerAnalysisForm.tsx (400 lines)
```typescript
// Core form container managing 4 steps
// Integrates Step1-4 components
// Handles form submission and progress tracking
// (See template below)
```

#### Step1RiskAssessment.tsx (200 lines)
```typescript
// Risk score confirmation/adjustment
// Confidence level selection
// Form validation
```

#### Step2EvidenceReview.tsx (250 lines)
```typescript
// Evidence checklist (7 items)
// Critical items mandatory
// Optional officer notes per item
```

#### Step3ActionRecommendation.tsx (300 lines)
```typescript
// Action selection (TRLED/Hold/Release)
// Conditional fields based on action
// Details per action type
```

#### Step4OfficeSignature.tsx (250 lines)
```typescript
// Case narrative text area
// Certification acceptance
// Officer information display
// Signature capture
// Form submission
```

#### NarrativeEditModal.tsx (250 lines)
```typescript
// Modal dialog for editing narratives
// Current content display
// [Save Changes] button
// [Regenerate via Gemini] button
// [Discard] button
```

---

### 3. Backend API (Python)

#### services/api/routers/officer_analysis_router.py (250 lines)
```python
"""
Officer Analysis API Router

Endpoints:
  POST /api/officer-analysis - Save analysis form
  GET /api/officer-analysis/{analysis_id} - Retrieve
  POST /api/referral-packages/{referral_id}/finalize - Archive
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import sqlite3
import json
import uuid
from datetime import datetime

router = APIRouter(prefix="/api/officer-analysis", tags=["analysis"])

@router.post("")
async def save_officer_analysis(data: Dict[str, Any]) -> Dict[str, Any]:
    """Save 4-step analysis form"""
    analysis_id = str(uuid.uuid4())
    
    # Insert into database
    conn = sqlite3.connect("/app/data/cbp_sentry.db")
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO officer_analyses
        (analysis_id, referral_id, officer_id, step1, step2, step3, step4, submitted_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        analysis_id,
        data['referral_id'],
        data['step4']['officerId'],
        json.dumps(data['step1']),
        json.dumps(data['step2']),
        json.dumps(data['step3']),
        json.dumps(data['step4']),
        datetime.utcnow().isoformat()
    ))
    
    conn.commit()
    conn.close()
    
    return {
        "status": "success",
        "analysis_id": analysis_id
    }

@router.get("/{analysis_id}")
async def get_officer_analysis(analysis_id: str) -> Dict[str, Any]:
    """Retrieve saved analysis"""
    conn = sqlite3.connect("/app/data/cbp_sentry.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM officer_analyses WHERE analysis_id = ?", (analysis_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    return dict(row)
```

#### Database Schema Updates
```sql
-- Create officer_analyses table
CREATE TABLE IF NOT EXISTS officer_analyses (
  analysis_id TEXT PRIMARY KEY,
  referral_id TEXT NOT NULL,
  officer_id TEXT NOT NULL,
  officer_name TEXT,
  badge_number TEXT,
  district TEXT,
  step1 JSON NOT NULL,
  step2 JSON NOT NULL,
  step3 JSON NOT NULL,
  step4 JSON NOT NULL,
  submitted_at TIMESTAMP NOT NULL,
  signed_at TIMESTAMP,
  FOREIGN KEY (referral_id) REFERENCES referral_packages(referral_id)
);

-- Update referral_packages table
ALTER TABLE referral_packages ADD COLUMN (
  edited_sections JSON,
  analysis_id TEXT,
  final_package_status TEXT DEFAULT 'draft'
);

-- Create audit_log table
CREATE TABLE IF NOT EXISTS audit_log (
  log_id TEXT PRIMARY KEY,
  officer_id TEXT,
  action TEXT,
  referral_id TEXT,
  analysis_id TEXT,
  timestamp TIMESTAMP,
  details JSON
);
```

---

## 🔗 INTEGRATION CHECKLIST

### 1. Add Tab to Investigation Page
```typescript
// In ModernCaseInvestigationPage.tsx
import ReferralPackageGenerationTab from './referral-generation/ReferralPackageGenerationTab';

// In tab navigation:
tabs: [
  { id: 'overview', label: 'Overview' },
  { id: 'scoring', label: 'Risk Scoring' },
  { id: 'referral', label: 'Referral Package', component: ReferralPackageGenerationTab }, // NEW
  { id: 'history', label: 'History' }
]
```

### 2. Database Migration
```bash
sqlite3 /app/data/cbp_sentry.db < schema_updates.sql
```

### 3. API Integration
```python
# In services/api/main.py
from routers.officer_analysis_router import router as analysis_router
app.include_router(analysis_router)
```

### 4. Docker Rebuild
```bash
./scripts/deploy-local.sh full
```

---

## 📊 TESTING WORKFLOW

### Manual Test Case
```
Shipment: shipment-greenfield-001
Risk Score: 90+
Expected: All 14 sections display
Officer: Review + Adjust + Submit Analysis
```

### Test Scenarios
1. ✅ Load referral package with all 14 sections
2. ✅ Edit narrative section (3-6, 3-7, 3-11, 3-14)
3. ✅ Complete 4-step form
4. ✅ Submit analysis + verify persistence
5. ✅ Export as PDF (federal format)
6. ✅ Retrieve saved analysis

---

## 🎯 NEXT STEPS

1. **Create remaining React components** (2 hours)
   - OfficerAnalysisForm.tsx
   - Step1-4 components
   - NarrativeEditModal.tsx

2. **Add CSS styling** (1 hour)
   - OfficerAnalysisForm.css
   - ReferralDisplayPanel.css

3. **Create backend API endpoints** (1.5 hours)
   - officer_analysis_router.py
   - Database migrations
   - Audit logging

4. **Integration & Testing** (2 hours)
   - Wire into ModernCaseInvestigationPage
   - End-to-end testing
   - PDF export testing

5. **Deploy** (0.5 hours)
   - Docker rebuild
   - Verification

**Total Estimated Time:** 7 hours for complete implementation

---

**READY TO BUILD** ✅

All types, hooks, and core components are in place. Remaining work is straightforward component creation following the established patterns.
