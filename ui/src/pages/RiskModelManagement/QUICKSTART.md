# Risk Model Management Tab — Quick Start Guide

**For:** Developers integrating components with backend API  
**Time to Read:** 5 minutes  
**Version:** 1.0

---

## 1. Import Components

```typescript
// In your main router or dashboard component
import {
  Dashboard,
  ModelVersions,
  TrainingHistory,
  PerformanceMetrics,
  DataDriftMonitoring,
  PredictionExplanations,
  ModelApprovals,
  RetrainingConfig,
} from '@/pages/RiskModelManagement'
```

## 2. Set Up Tab Navigation

```typescript
// App.tsx or DashboardPage.tsx
import { useState } from 'react'
import * as RiskModelManagement from '@/pages/RiskModelManagement'

export default function CBPSentryDashboard() {
  const [activeScreen, setActiveScreen] = useState<
    'dashboard' | 'versions' | 'training' | 'metrics' | 'drift' | 'explanations' | 'approvals' | 'config'
  >('dashboard')

  return (
    <div className="space-y-6">
      {/* Tab Navigation */}
      <div className="bg-white border-b border-gray-200">
        <div className="flex gap-1 px-6">
          {[
            { key: 'dashboard', label: 'Dashboard' },
            { key: 'versions', label: 'Model Versions' },
            { key: 'training', label: 'Training History' },
            { key: 'metrics', label: 'Performance Metrics' },
            { key: 'drift', label: 'Data Drift' },
            { key: 'explanations', label: 'Explanations' },
            { key: 'approvals', label: 'Approvals' },
            { key: 'config', label: 'Retraining Config' },
          ].map(tab => (
            <button
              key={tab.key}
              onClick={() => setActiveScreen(tab.key as any)}
              className={`px-4 py-3 border-b-2 font-medium transition-colors ${
                activeScreen === tab.key
                  ? 'border-sentry-navy text-sentry-navy'
                  : 'border-transparent text-gray-600 hover:text-sentry-navy'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Active Screen */}
      <div className="px-6 py-6">
        {activeScreen === 'dashboard' && (
          <RiskModelManagement.Dashboard
            onNavigate={(screen) => setActiveScreen(screen as any)}
          />
        )}
        {activeScreen === 'versions' && (
          <RiskModelManagement.ModelVersions
            onCompare={(m1, m2) => console.log(`Compare ${m1} vs ${m2}`)}
            onVote={(id) => console.log(`Vote on ${id}`)}
          />
        )}
        {activeScreen === 'training' && (
          <RiskModelManagement.TrainingHistory
            onViewDetails={(id) => console.log(`View job ${id}`)}
            onRetry={(id) => console.log(`Retry job ${id}`)}
          />
        )}
        {activeScreen === 'metrics' && (
          <RiskModelManagement.PerformanceMetrics
            onExport={() => console.log('Export metrics')}
          />
        )}
        {activeScreen === 'drift' && (
          <RiskModelManagement.DataDriftMonitoring
            onInvestigate={(feature) => console.log(`Investigate ${feature}`)}
          />
        )}
        {activeScreen === 'explanations' && (
          <RiskModelManagement.PredictionExplanations
            onCompare={(ship, model) => console.log(`Compare ${ship} in ${model}`)}
          />
        )}
        {activeScreen === 'approvals' && (
          <RiskModelManagement.ModelApprovals
            onVote={(id, vote) => console.log(`Vote ${vote} on ${id}`)}
            onCompare={(m1, m2) => console.log(`Compare ${m1} vs ${m2}`)}
          />
        )}
        {activeScreen === 'config' && (
          <RiskModelManagement.RetrainingConfig
            onSave={(config) => console.log('Save config', config)}
            onReset={() => console.log('Reset config')}
          />
        )}
      </div>
    </div>
  )
}
```

## 3. Replace Mock Data with API Calls

Each component has a `TODO` comment where data is loaded. Example for Dashboard:

**Before (Mock Data):**
```typescript
const loadDashboardData = async () => {
  setLoading(true)
  setError(null)
  try {
    // TODO: Replace with actual API calls
    setActiveModel({
      version: 'CBP Risk v3.0',
      status: 'PRODUCTION',
      // ...more mock data
    })
  } catch (err) {
    setError(err instanceof Error ? err.message : 'Failed to load dashboard data')
  } finally {
    setLoading(false)
  }
}
```

**After (Real API):**
```typescript
const loadDashboardData = async () => {
  setLoading(true)
  setError(null)
  try {
    const response = await fetch('/api/risk-models/dashboard')
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    const data = await response.json()
    
    setActiveModel(data.active_model)
    setPendingApproval(data.pending_approval)
    setAlerts(data.alerts)
  } catch (err) {
    setError(err instanceof Error ? err.message : 'Failed to load dashboard data')
  } finally {
    setLoading(false)
  }
}
```

## 4. API Endpoint Reference

```bash
# Dashboard data
GET /api/risk-models/dashboard
# Response: {active_model, pending_approval, alerts, ...}

# List models
GET /api/risk-models/versions?status=production&sort=date
# Response: [{id, version, status, performance, ...}, ...]

# Compare models
POST /api/risk-models/{model_id}/compare
# Body: {compare_to_model_id: "v2.1"}
# Response: {metrics_comparison, performance_diff, ...}

# Training jobs
GET /api/risk-models/training-jobs?status=completed&limit=20
# Response: [{id, jobId, status, timing, results, ...}, ...]

# Performance metrics
GET /api/risk-models/{model_id}/metrics?time_range=24h&metric=accuracy
# Response: [{timestamp, accuracy, latency, ...}, ...]

# Data drift
GET /api/risk-models/{model_id}/drift
# Response: {drift_score, elevated_features, distributions, ...}

# Prediction explanation
GET /api/risk-models/predictions/{shipment_id}/explain?model_version=v3.0
# Response: {shipment, prediction, shap_values, interpretation, ...}

# Approvals
GET /api/risk-models/approvals?status=pending
# Response: [{id, model, requestedBy, voters, status, ...}, ...]

# Vote on approval
POST /api/risk-models/approvals/{approval_id}/vote
# Body: {vote: "approve"|"reject"|"abstain", comment: "..."}
# Response: {updated_approval, remaining_votes}

# Retraining config
GET /api/risk-models/retraining-config
# Response: {scheduled, drift_triggered, model_drift_triggered, ...}

PUT /api/risk-models/retraining-config
# Body: {schedule_frequency, drift_threshold, ...}
# Response: {updated_config}
```

## 5. Error Handling

All components have built-in error handling. Make sure your API returns proper error messages:

```typescript
// Good error response
{
  "status": 400,
  "error": "Invalid model version",
  "message": "Model v5.0 does not exist"
}

// Component will show:
// "Invalid model version" or "Failed to load dashboard data"
```

## 6. TypeScript Integration

If using TypeScript, define API response types:

```typescript
// types/riskModel.ts
export interface ActiveModel {
  version: string
  status: 'production' | 'staging' | 'candidate' | 'deprecated'
  deployedAt: string
  accuracy: number
  aucRoc: number
  latencyP95: number
  confidenceAvg: number
}

export interface DashboardResponse {
  active_model: ActiveModel
  pending_approval: PendingApproval | null
  alerts: Alert[]
}

// Usage in Dashboard.tsx
const data = (await response.json()) as DashboardResponse
setActiveModel(data.active_model)
```

## 7. State Management (Optional)

If using Redux or Zustand, create slices for risk model state:

```typescript
// Redux example
const riskModelSlice = createSlice({
  name: 'riskModel',
  initialState: {
    activeModel: null,
    pendingApproval: null,
    alerts: [],
    loading: false,
  },
  reducers: {
    setActiveModel: (state, action) => {
      state.activeModel = action.payload
    },
    // ...more reducers
  },
})
```

## 8. Testing Mock Components

For testing before backend is ready, use mock server:

```typescript
// Using MSW (Mock Service Worker)
import { setupServer } from 'msw/node'
import { http, HttpResponse } from 'msw'

const server = setupServer(
  http.get('/api/risk-models/dashboard', () => {
    return HttpResponse.json({
      active_model: { version: 'v3.0', status: 'PRODUCTION', ... },
      // ...
    })
  })
)

// In test setup
beforeAll(() => server.listen())
afterEach(() => server.resetHandlers())
afterAll(() => server.close())
```

## 9. Common Patterns

### Loading Data on Mount
```typescript
useEffect(() => {
  loadData()
}, [])
```

### Filtering/Sorting
```typescript
const filtered = items.filter(item => 
  filter === 'all' || item.status === filter
)
```

### Form Submission
```typescript
const handleSave = async () => {
  setLoading(true)
  try {
    await fetch('/api/endpoint', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config),
    })
    setSuccess('Saved!')
  } catch (err) {
    setError(err.message)
  } finally {
    setLoading(false)
  }
}
```

### Navigation
```typescript
const handleNavigate = (screen: string) => {
  setActiveScreen(screen as any)
  // Or use React Router:
  // navigate(`/risk-models/${screen}`)
}
```

## 10. Debugging Tips

### Check Console
All components log async state changes:
```javascript
// Open DevTools → Console
// You'll see loading/error messages as data fetches
```

### Mock Data Inspection
All mock data is in component `useState` blocks. Add this to inspect:
```typescript
useEffect(() => {
  console.log('ActiveModel:', activeModel)
  console.log('Alerts:', alerts)
}, [activeModel, alerts])
```

### Network Inspector
Use DevTools → Network tab to monitor API calls:
```
GET /api/risk-models/dashboard
200 OK, 145ms
```

### Performance
Use React DevTools Profiler to check render times:
- Components should render < 16ms for 60fps
- Large lists (ModelApprovals) may need virtualizing

---

## Checklist for Deployment

- [ ] All API endpoints implemented and tested
- [ ] Components connected to real API calls
- [ ] Error handling verified with network failures
- [ ] Loading states show while fetching
- [ ] Mock data removed or behind feature flag
- [ ] TypeScript types for all API responses
- [ ] Unit tests for each component (filter, sort, form logic)
- [ ] E2E tests for workflows (approve, retrain)
- [ ] Performance baseline established (all screens < 1s initial load)
- [ ] Accessibility audit passed (keyboard nav, screen readers)
- [ ] User acceptance testing completed

---

## Support Resources

| Resource | Link |
|----------|------|
| Full Design Doc | `RISK_MODEL_MANAGEMENT_TAB_DESIGN.md` |
| Component Guide | `README.md` in each component |
| Implementation Notes | `IMPLEMENTATION_NOTES.md` |
| Tailwind Docs | https://tailwindcss.com |
| Lucide Icons | https://lucide.dev |
| React Docs | https://react.dev |

---

**Need help?** Check the design document first, then see IMPLEMENTATION_NOTES.md for detailed guidance.
