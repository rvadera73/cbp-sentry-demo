# MVC Component Architecture Guide

## Overview

This document describes the Model-View-Controller (MVC) architecture implemented for the Sentry CBP UI. This architecture eliminates component duplication and enables reusable, composable UI elements.

## Architecture Layers

### 1. Model Layer (`/src/types/`)

**Purpose:** Define data structures that flow through the application.

**Files:**
- `types/models.ts` — Core domain types (Case, Score, Entity, ReferralPackage, etc.)
- `types/sentry.ts` — API response types (legacy, being phased out)

**Key Types:**
```typescript
- Case — shipment/case data
- ScoreResult — risk score and components
- ReferralPackage — 14-section CBP referral structure
- Entity — shipper/consignee/manufacturer nodes
- GraphData — entity relationships for visualization
- InvestigationNote — officer notes tied to cases
```

**Rule:** All components must use types from `models.ts`, not define their own `interface Case` locally.

---

### 2. Controller Layer (`/src/hooks/`)

**Purpose:** Manage data fetching, state, and business logic.

**Files:**
- `hooks/useCases.ts` — Load, filter, sort cases
- `hooks/useScore.ts` — Fetch score for a shipment
- `hooks/useReferralPackage.ts` — Fetch 14-table referral structure
- `hooks/useEntityGraph.ts` — Fetch entity relationship graph
- `hooks/index.ts` — Barrel export for easy importing

**Usage Pattern:**
```typescript
// In a page or complex component:
const { cases, loading, error, fetchCases, filterCases } = useCases();
const { score, loading: scoreLoading } = useScore(shipmentId);

// Hook automatically handles:
// - API calls via fetch()
// - Loading states
// - Error handling
// - State management (useState internally)
```

**Adding a New Hook:**
1. Create `hooks/useNewFeature.ts`
2. Define state: `const [data, setData] = useState(null)`
3. Create fetch function that calls `${API_BASE_URL}/endpoint`
4. Return: `{ data, loading, error, refetch }`
5. Export from `hooks/index.ts`

---

### 3. View Layer (`/src/components/`)

#### 3a. Common Reusable Components (`/src/components/common/`)

**Purpose:** Atomic, presentation-only components that accept props and render UI. No data fetching.

**Available Components:**

| Component | Purpose | Example |
|---|---|---|
| `ExpandableCard` | Accordion card for grouped content | Referral package sections |
| `RiskBadge` | Risk score badge (HIGH/MEDIUM/LOW) | Case queue items, entity cards |
| `DataTable` | Reusable table for any data | Historical patterns, AIS routes |
| `AlertBanner` | Alert/status message | Error states, warnings |
| `SearchBar` | Search input with clear button | Case queue filtering |
| `FilterSelect` | Dropdown filter | Risk level selection |
| `ScoreComponentChart` | Score breakdown visualization | H1/H2/H3 score components |
| `EntityCard` | Entity display (shipper/consignee/etc) | Entity chain visualization |
| `SectionHeader` | Consistent section title + badge | Tab content headers |

**Usage Example:**
```typescript
import { ExpandableCard, RiskBadge, DataTable } from '@/components/common';

// In a page or container component:
<ExpandableCard
  title="Referral Section 3-1"
  badge="HIGH"
  badgeColor="red"
>
  <RiskBadge score={91} size="lg" />
  <DataTable columns={cols} data={rows} />
</ExpandableCard>
```

**Adding a New Common Component:**
1. Create `components/common/MyComponent.tsx`
2. Define props interface: `interface MyComponentProps { ... }`
3. No hooks or API calls — accept all data via props
4. Export from `components/common/index.ts`
5. Use with `import { MyComponent } from '@/components/common'`

#### 3b. Feature Components (`/src/components/cases/`, `/src/components/monitoring/`)

**Purpose:** Components that fetch data (use hooks) and orchestrate UI.

**Current Components:**
- `CaseQueue.tsx` — List of cases with search/filter (uses useCases hook)
- `CaseHeader.tsx` — Risk gauge and basic case info
- `ReferralPackageViewer.tsx` — All 14 referral sections (uses useReferralPackage hook)
- `H1CorridorPanel.tsx` — H1 corridor analysis
- `H2VesselPanel.tsx` — H2 vessel/AIS analysis
- `H3IntelPanel.tsx` — H3 intelligence indicators
- `EntityChainViewer.tsx` — Entity relationship visualization (uses useEntityGraph hook)

**Pattern for Feature Components:**
```typescript
import { useScore } from '../../hooks';
import { ExpandableCard, DataTable } from '../common';

interface Props {
  case: Case;
}

export default function MyFeaturePanel({ case: c }: Props) {
  const { score, loading } = useScore(c.id);

  if (loading) return <AlertBanner type="info" title="Loading..." />;

  return (
    <ExpandableCard title="Section Title">
      <DataTable columns={...} data={score.components} />
    </ExpandableCard>
  );
}
```

**Rule:** Feature components ONLY use hooks for their own data. They compose common components but do NOT duplicate UI code.

#### 3c. Page Components (`/src/pages/`)

**Purpose:** Top-level route containers that orchestrate multiple feature components.

**Current Pages:**
- `CaseViewerPage.tsx` — Primary case investigation UI (6 tabs)
- `LiveMonitoringPage.tsx` — Real-time monitoring dashboard
- `DashboardPage.tsx` — Three Horizons H1/H2/H3 overview

**Pattern for Page Components:**
```typescript
import { useCases } from '../hooks';
import { AlertBanner } from '../components/common';
import CaseQueue from '../components/cases/CaseQueue';
import CaseHeader from '../components/cases/CaseHeader';

export default function CaseViewerPage() {
  const { cases, loading, error } = useCases();
  const [selectedCase, setSelectedCase] = useState<Case | null>(null);

  // ... tab management, error handling, layout orchestration ...

  return (
    <div>
      <CaseQueue cases={cases} onSelectCase={setSelectedCase} />
      {selectedCase && (
        <>
          <CaseHeader case={selectedCase} />
          <TabContent case={selectedCase} />
        </>
      )}
    </div>
  );
}
```

---

## Import Organization

### Correct Imports
```typescript
// Common components
import { ExpandableCard, RiskBadge, DataTable } from '@/components/common';

// Hooks (data layer)
import { useCases, useScore } from '@/hooks';

// Types
import { Case, ScoreResult } from '@/types/models';

// Feature components
import CaseQueue from '@/components/cases/CaseQueue';
```

### Incorrect Imports (Avoid)
```typescript
// ❌ Don't import as default when they're in an index
import { ExpandableCard } from '@/components/common/ExpandableCard';

// ❌ Don't define local interfaces when types exist
interface Case { /* ... */ }  // Use: import { Case } from '@/types/models'

// ❌ Don't fetch data directly in a common component
// This breaks reusability. Move to a hook instead.
fetch(`/api/data`).then(...)
```

---

## Workflow: Adding a New Feature

### Example: Add a Fraud Ring Detector Tab

**Step 1: Check if data hook exists**
```typescript
// Do we have a hook for fraud ring data? If not:
// Create: hooks/useFraudRings.ts
```

**Step 2: Design the layout**
```
FraudRingPanel (feature component, uses useFraudRings hook)
  ├─ SectionHeader (common component)
  ├─ RiskBadge (common component, 3x for red entities)
  ├─ ExpandableCard (common component)
  │  └─ DataTable (common component, list of linked cases)
  └─ EntityCard (common component, fraud ring members)
```

**Step 3: Build the hook (data layer)**
```typescript
// hooks/useFraudRings.ts
import { useState, useEffect } from 'react';
import { API_BASE_URL } from '../services/api';

export function useFraudRings(shipmentId: string | null) {
  const [rings, setRings] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!shipmentId) return;
    fetch(`${API_BASE_URL}/fraud-rings/${shipmentId}`)
      .then(r => r.json())
      .then(setRings);
  }, [shipmentId]);

  return { rings, loading };
}
```

**Step 4: Build feature component (view layer)**
```typescript
// components/cases/FraudRingPanel.tsx
import { Case } from '../../types/models';
import { useFraudRings } from '../../hooks';
import { ExpandableCard, RiskBadge, EntityCard, SectionHeader } from '../common';

interface Props {
  case: Case;
}

export default function FraudRingPanel({ case: c }: Props) {
  const { rings, loading } = useFraudRings(c.id);

  return (
    <div className="p-6">
      <SectionHeader title="Fraud Ring Detection" />
      {rings.map((ring) => (
        <ExpandableCard key={ring.id} title={`Ring ${ring.id}`}>
          {ring.entities.map((entity) => (
            <EntityCard key={entity.id} entity={entity} riskScore={ring.score} />
          ))}
        </ExpandableCard>
      ))}
    </div>
  );
}
```

**Step 5: Integrate into page**
```typescript
// pages/CaseViewerPage.tsx
import FraudRingPanel from '../components/cases/FraudRingPanel';

// Add tab:
const tabOptions = [
  // ... existing tabs ...
  { id: 'fraud-rings', label: 'Fraud Rings', icon: '🚨' }
];

// Add tab content:
{activeTab === 'fraud-rings' && <FraudRingPanel case={selectedCase} />}
```

---

## Benefits of This Architecture

| Benefit | How |
|---|---|
| **No Duplication** | ExpandableCard used 14+ times (referral, H1, H2, H3) instead of reimplemented |
| **Consistent UI** | All risk badges use same color logic; all tables have same sorting/pagination |
| **Easier Testing** | Common components are pure functions; hooks are testable independently |
| **Scalability** | Adding H3 Intelligence tab = 1 hook + 1 feature component, reusing 6 common components |
| **Type Safety** | Shared types in models.ts prevent Case/Score type mismatches across codebase |
| **Separation of Concerns** | UI code (common) separate from data loading (hooks) separate from business logic (hooks) |

---

## Component Count

### Common Components (Reusable, 8)
- ExpandableCard
- RiskBadge
- DataTable
- AlertBanner
- SearchBar
- FilterSelect
- ScoreComponentChart
- EntityCard
- SectionHeader

### Feature Components (Domain-specific, 8+)
- CaseQueue
- CaseHeader
- ReferralPackageViewer
- H1CorridorPanel
- H2VesselPanel
- H3IntelPanel
- EntityChainViewer
- UploadPipelineModal
- (+ future: FraudRingPanel, Corridor TrendPanel, etc.)

### Hooks (Data Layer, 5+)
- useCases
- useScore
- useReferralPackage
- useEntityGraph
- (+ future: useFraudRings, useCorridor Analysis, etc.)

**Principle:** Each new feature should add ≤2 new hooks and ≤3 new feature components, reusing 4-6 common components.

---

## Refactoring Checklist for Old Components

When retrofitting existing components to follow MVC:

- [ ] Create/update types in `types/models.ts`
- [ ] Extract data fetching into new hook in `hooks/`
- [ ] Break UI into common + feature components
- [ ] Remove duplicate styling (use common components)
- [ ] Update imports to use barrel exports (`from '@/components/common'`)
- [ ] Export from `hooks/index.ts`
- [ ] Add to this guide if a new pattern emerges

---

## Future: Analytics AI Module Components

As the architecture matures:

**Planned Common Components (v2):**
- CorridorRiskChart — animated corridor flow with AD/CVD overlay
- AnomalyTimeline — dwell time anomalies on timeline
- PredictionCard — "What if origin is X?" scenario
- RelationshipFlow — SVG entity relationships

**Planned Feature Components (v2):**
- CorridorAnalysisPanel — H1 corridor detail + ML predictions
- VesselAnomalyDetector — H2 ISF/dwell/routing anomalies
- IntelligencePortal — H3 watch list + OFAC + fraud ring correlations

**Planned Hooks (v2):**
- useCorridorTrends — historical import patterns
- useVesselBaseline — port dwell baselines by vessel class
- useFraudRingDetection — graph-based transshipment ring detection
- useWatchListMatches — OFAC, prior EAPA, other watch lists

All will follow this same MVC pattern.
