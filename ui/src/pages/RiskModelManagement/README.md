# Risk Model Management Tab — React Components

**Phase 1 Implementation** | CBP Risk Model (v2.1 → v3.0)  
**Status:** Stub Components Ready for Integration  
**Created:** 2026-06-12

---

## Overview

This directory contains 8 functional React components for the Risk Model Management tab in CBP Sentry. All components are TypeScript-based with stub implementations ready for API integration.

### Component Structure

```
RiskModelManagement/
├── Dashboard.tsx                 # At-a-glance model health summary
├── ModelVersions.tsx             # Compare all model versions
├── TrainingHistory.tsx           # Training job history and logs
├── PerformanceMetrics.tsx        # Time-series performance monitoring
├── DataDriftMonitoring.tsx       # Feature distribution change detection
├── PredictionExplanations.tsx    # SHAP-based prediction explanations
├── ModelApprovals.tsx            # Multi-voter approval workflow
├── RetrainingConfig.tsx          # Schedule triggers and automation
├── index.ts                      # Barrel export file
└── README.md                     # This file
```

---

## Component Details

### 1. Dashboard.tsx

**Purpose:** At-a-glance model health and status  
**Key Features:**
- Active model summary (v3.0)
- 24h performance metrics (accuracy, AUC-ROC, latency, confidence)
- Pending approvals counter
- Monitoring alerts (data/model drift)
- Quick action buttons to other screens

**Props:**
```typescript
interface DashboardProps {
  onNavigate?: (screen: string) => void
}
```

**State Shape:**
- `activeModel`: Model version, deployment date, approval info, metrics
- `pendingApproval`: Candidate model details, approval status
- `alerts`: Array of monitoring alerts (warning/success)
- `loading`, `error`: Standard async state

---

### 2. ModelVersions.tsx

**Purpose:** Compare all available model versions  
**Key Features:**
- Filter by status (production, staging, candidate, deprecated)
- Display all model info (training data, features, weights validation)
- Performance comparison (accuracy, AUC-ROC, latency, FPR)
- Approval voting status per voter
- Actions: View Details, Compare, Vote, Rollback

**Props:**
```typescript
interface ModelVersionsProps {
  onCompare?: (model1: string, model2: string) => void
  onVote?: (versionId: string) => void
}
```

**State Shape:**
- `models`: Array of model versions with metrics and approval data
- `filter`: Status filter (all/production/staging/candidate/deprecated)
- `loading`, `error`: Standard async state

---

### 3. TrainingHistory.tsx

**Purpose:** Track all training jobs and results  
**Key Features:**
- Filter by status (completed, in progress, failed)
- Sort by date or status
- Job details: dataset info, hyperparameters, timing
- Results: accuracy, AUC-ROC, validation status, feature importance
- Progress indicator for running jobs
- Error details for failed jobs

**Props:**
```typescript
interface TrainingHistoryProps {
  onViewDetails?: (jobId: string) => void
  onRetry?: (jobId: string) => void
}
```

**State Shape:**
- `jobs`: Array of training jobs with full metadata
- `filter`: Status filter (all/completed/in_progress/failed)
- `sort`: Sort option (date/status)
- `loading`, `error`: Standard async state

---

### 4. PerformanceMetrics.tsx

**Purpose:** Time-series monitoring of model performance  
**Key Features:**
- Time range selector (24h, 7d, 30d, custom)
- Model comparison dropdown
- Accuracy trend chart (placeholder for Chart.js integration)
- Latency distribution (p95 percentile)
- Confusion matrix with recall/precision
- Fairness metrics by origin/commodity
- Export to CSV, generate reports

**Props:**
```typescript
interface PerformanceMetricsProps {
  onExport?: () => void
}
```

**State Shape:**
- `accuracyTrend`: Time-series accuracy and latency points
- `confusionMatrix`: 3x3 matrix (CLEAR/EXAMINE/HOLD)
- `fairnessMetrics`: Array of segment-wise accuracy scores
- `timeRange`, `compareModel`: Filter controls
- `loading`: Async state

---

### 5. DataDriftMonitoring.tsx

**Purpose:** Detect and alert on feature distribution changes  
**Key Features:**
- Baseline vs. current period configuration
- Drift detection method (Kolmogorov-Smirnov)
- Feature-level drift scores (0.0-1.0)
- Categorical shift visualization
- Numeric distribution comparison
- Root cause suggestions
- Alert acknowledgement/dismissal
- Recommended actions checklist

**Props:**
```typescript
interface DataDriftMonitoringProps {
  onInvestigate?: (featureName: string) => void
}
```

**State Shape:**
- `features`: Array of feature drift data with baseline/current distributions
- `baselinePeriod`, `currentPeriod`: Time range config
- `loading`, `error`: Standard async state

---

### 6. PredictionExplanations.tsx

**Purpose:** Understand individual predictions via SHAP analysis  
**Key Features:**
- Shipment search by ID
- Shipment summary (origin, destination, commodity, value)
- Prediction details (score, classification, confidence, latency)
- SHAP force plot simulation
- Positive factors (pushing risk up)
- Negative factors (pushing risk down)
- Plain English interpretation
- Model comparison (v2.1 vs v3.0)

**Props:**
```typescript
interface PredictionExplanationsProps {
  onCompare?: (shipmentId: string, model: string) => void
}
```

**State Shape:**
- `explanation`: Full SHAP explanation with contributions
- `searchTerm`: Shipment ID search input
- `loading`, `error`: Standard async state

---

### 7. ModelApprovals.tsx

**Purpose:** Multi-voter approval workflow  
**Key Features:**
- Filter by approval status (pending, approved, rejected)
- Request details: submitter, reason, deadline
- Performance improvement comparison
- Training data validation
- Fairness analysis summary
- Per-voter approval card
- Vote collection with comments
- Historical approvals/rejections
- Audit trail tracking

**Props:**
```typescript
interface ModelApprovalsProps {
  onVote?: (approvalId: string, vote: 'approve' | 'reject' | 'abstain') => void
  onCompare?: (model1: string, model2: string) => void
}
```

**State Shape:**
- `approvals`: Array of approval requests with voter details
- `filter`: Status filter (all/pending/approved/rejected)
- `votingComments`: Map of approval ID to voter comment
- `loading`, `error`: Standard async state

---

### 8. RetrainingConfig.tsx

**Purpose:** Automated retraining triggers and scheduling  
**Key Features:**
- Scheduled retraining setup (frequency, day, time, data window)
- Data drift trigger (threshold, persistence, affected features)
- Model drift trigger (degradation %, evaluation window, min predictions)
- Error spike trigger (error threshold, duration)
- Notification settings (email, Slack, alerts)
- Trigger history per type
- Save/reset configuration buttons

**Props:**
```typescript
interface RetrainingConfigProps {
  onSave?: (config: RetrainingConfigData) => void
  onReset?: () => void
}
```

**State Shape:**
- `config`: All retraining configuration settings
- `loading`: Async state for save operation
- `success`, `error`: Feedback messages

---

## Code Style & Patterns

### TypeScript
- All components use TypeScript with proper prop typing
- Interface definitions at top of file
- State management via `useState` hooks
- Type safety enforced

### Tailwind CSS
- Color palette:
  - Navy: `text-sentry-navy`, `bg-sentry-navy`
  - Slate: `text-sentry-slate`
  - Orange: `text-sentry-orange` (accent)
  - Status colors: `bg-green-50`, `bg-yellow-50`, `bg-red-50`
- Spacing: Standard Tailwind grid (`gap-4`, `mb-6`, etc.)
- Responsive: `grid-cols-1 md:grid-cols-2 lg:grid-cols-4`

### Lucide React Icons
- Used for status indicators, alerts, actions
- Standard sizes: `size={18}`, `size={20}`, `size={32}`
- Import examples: `AlertTriangle`, `CheckCircle`, `Clock`, `Download`

### Component Patterns
- Functional components with React FC
- Props passed as first argument
- `useEffect` for initial data loads
- Error states always displayed
- Loading states with spinner text
- Action buttons with `onClick` callbacks

---

## API Integration (TODO)

All components have `TODO` comments where API calls should be implemented:

```typescript
// Example pattern - replace with actual API calls
// TODO: Replace with actual API calls to /api/risk-models/dashboard
const loadDashboardData = async () => {
  // Fetch from backend
}
```

### Backend Endpoints (from design doc)

```
GET  /api/risk-models/dashboard
GET  /api/risk-models/versions?status=production
POST /api/risk-models/{model_id}/compare
GET  /api/risk-models/training-jobs?status=completed
GET  /api/risk-models/{model_id}/metrics?time_range=24h
GET  /api/risk-models/{model_id}/drift
GET  /api/risk-models/predictions/{shipment_id}/explain
GET  /api/risk-models/approvals?status=pending
POST /api/risk-models/approvals/{approval_id}/vote
GET  /api/risk-models/retraining-config
PUT  /api/risk-models/retraining-config
```

---

## Integration Checklist

### Phase 1B: Backend Foundations
- [ ] Create database schema (7 tables)
- [ ] Implement API endpoints (15 total)
- [ ] Set up data collection (metrics, drift, predictions)
- [ ] Build model version management

### Phase 1C: Integration
- [ ] Replace mock data with API calls
- [ ] Connect components to Redux/Context for state management
- [ ] Populate with v3.0 model data
- [ ] Test approval workflow end-to-end
- [ ] Test retraining triggers

### Phase 1D: Polish & Testing
- [ ] Add chart libraries (Chart.js or Recharts for PerformanceMetrics)
- [ ] Implement SHAP visualization (PredictionExplanations)
- [ ] UI refinements and accessibility
- [ ] Performance optimization
- [ ] End-to-end testing
- [ ] User acceptance testing

---

## Chart Library Integration

For `PerformanceMetrics.tsx`, you will need to add a charting library:

**Recommended: Recharts**
```bash
npm install recharts
```

Replace the placeholder at line ~85:
```typescript
// FROM: Placeholder chart box
// TO: Recharts LineChart component
```

---

## Future Enhancements

### Phase 2: MLOps Tooling
- MLflow integration for experiment tracking
- DVC for data versioning
- Prometheus metrics export
- GitHub Actions environment approval

### Phase 3+: Multi-Domain Extensibility
- Refactor to generic MCP server
- Add FDA adverse event models
- Add Commerce fraud models
- Expose via MCP protocol

---

## File Statistics

| Component | Lines | Interfaces | Props |
|-----------|-------|-----------|-------|
| Dashboard | ~240 | 3 | 1 |
| ModelVersions | ~310 | 3 | 2 |
| TrainingHistory | ~370 | 3 | 2 |
| PerformanceMetrics | ~260 | 3 | 1 |
| DataDriftMonitoring | ~280 | 3 | 1 |
| PredictionExplanations | ~340 | 4 | 1 |
| ModelApprovals | ~450 | 4 | 2 |
| RetrainingConfig | ~380 | 2 | 2 |
| **Total** | **~2,630** | **~25** | **~12** |

---

## Testing Recommendations

### Unit Tests (Vitest)
- Test each component renders without error
- Test prop validation
- Test button click handlers
- Test filter/sort logic

### Integration Tests
- Test navigation between screens via `onNavigate`
- Test voting workflow (approve/reject/abstain)
- Test form submission (RetrainingConfig save)
- Test search/filter combinations

### End-to-End Tests (Cypress)
- Complete approval workflow: request → votes → deployment
- Complete retraining flow: trigger detection → config update → job queue
- Navigation between all 8 screens
- Error handling and recovery

---

## Support & Questions

For questions about:
- **Design**: See `RISK_MODEL_MANAGEMENT_TAB_DESIGN.md`
- **API Integration**: See backend implementation plan
- **Styling**: See CBP Sentry Tailwind configuration
- **State Management**: See parent container implementation

All components are ready for immediate integration and development.
