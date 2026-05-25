# Tab Navigation & Workspace Redesign

**Date:** May 25, 2026  
**Status:** ✅ FIXED AND REDESIGNED

---

## Problem Statement

The user reported two critical issues with the Shipping Intelligence page:

1. **Tab Navigation Issues:** Tabs were not responding to clicks and keyboard navigation
2. **Access Workspace Button:** The "Access Workspace" button was not properly navigating to the Investigation Workspace

## Root Cause Analysis

### Issue #1: Tab Override Problem
The page had an inline "Shipment Workspace View" that was overriding the normal tab display:

```typescript
{selectedShipmentId && activeTab === 'compliance' ? (
  // INLINE SHIPMENT WORKSPACE VIEW (this was overriding tabs)
  <ShipmentDetailView ... />
) : (
  // NORMAL TAB NAVIGATION
  <TabNavigation ... />
)}
```

**Problem:** When a shipment was selected, the entire tab navigation was replaced with an inline detail view. This:
- Made tabs invisible/inaccessible
- Created confusing UX (tabs would suddenly disappear)
- Prevented users from switching between tabs while viewing a shipment

### Issue #2: Navigation Problem
The `handleAccessWorkspace` function was just setting local state instead of navigating:

```typescript
// WRONG: Just changes local state on same page
const handleAccessWorkspace = (shipmentId: string) => {
  setSelectedShipmentId(shipmentId);
  setActiveTab('compliance');
  setFromPage('shipping-intelligence');
};
```

**Problem:** This creates a local detail view instead of navigating to the full Investigation Workspace page.

---

## Solution

### 1. Removed State Override
Eliminated the `selectedShipmentId` state and the conditional rendering that was replacing tabs:

```typescript
// BEFORE: Three states managing different views
const [selectedShipmentId, setSelectedShipmentId] = useState<string | null>(null);
const [activeTab, setActiveTab] = useState<TabType>('pre-manifest');
const [fromPage, setFromPage] = useState<'investigations' | 'shipping-intelligence'>('shipping-intelligence');

// With complex conditional logic:
{selectedShipmentId && activeTab === 'compliance' ? (
  <ShipmentWorkspaceView /> // OVERRIDES TABS!
) : (
  <TabNavigation ... /> // NORMAL TABS
)}

// AFTER: Clean state management
const [activeTab, setActiveTab] = useState<TabType>('pre-manifest');

// Tabs always render - no conditional override
<TabNavigation ... />
```

### 2. Implemented Proper Navigation
Changed the access workspace button to navigate to the Investigation page:

```typescript
// BEFORE: Local state change
const handleAccessWorkspace = (shipmentId: string) => {
  setSelectedShipmentId(shipmentId);
  setActiveTab('compliance');
  setFromPage('shipping-intelligence');
};

// AFTER: Navigate to Investigations page
const navigate = useNavigate();

const handleAccessWorkspace = (shipmentId: string) => {
  navigate(`/investigations?shipmentId=${encodeURIComponent(shipmentId)}`);
};
```

### 3. Removed Unused Code
Removed all references to deleted state variables:
- `setSelectedShipmentId` calls
- `selectedShipment` variable and its usages
- `selectedShipmentIntel` variable
- Inline shipment detail views

---

## Changes Made

### File: `ui/src/v2/pages/V2ShippingIntelligencePage.tsx`

1. **Added Navigation:**
   - `import { useNavigate } from 'react-router-dom';`
   - `const navigate = useNavigate();`

2. **Removed State:**
   - Deleted `selectedShipmentId` state
   - Deleted `fromPage` state (no longer needed)
   - Removed `selectedShipment` variable
   - Removed `selectedShipmentIntel` variable

3. **Fixed Navigation Handler:**
   - Changed from state setter to route navigation
   - Passes `shipmentId` as query parameter
   - Users navigate to full Investigation Workspace

4. **Simplified Corridor Selector:**
   - Removed `setSelectedShipmentId(null)` from onChange
   - Only resets `activeTab` to 'pre-manifest'

5. **Removed Tab Override:**
   - Deleted entire ternary condition that was replacing tabs
   - Tabs now always render (never hidden)
   - Content changes based on `activeTab` only

6. **Cleaned Up Table Props:**
   - Removed `onRowClick` handler (users click "Access Workspace" instead)
   - Added no-op `onRowClick={() => {}}` (required by component)
   - Focus is on `onAccessWorkspace` for navigation

---

## User Experience Impact

### Before (Broken)
- ❌ User selects shipment → tabs disappear
- ❌ User clicks "Access Workspace" → inline view on same page
- ❌ Cannot switch tabs while viewing shipment details
- ❌ Tab state gets confused

### After (Fixed)
- ✅ Tabs always visible and clickable
- ✅ Clicking "Access Workspace" navigates to Investigation Workspace
- ✅ Full Investigation page loads with shipment context
- ✅ Tab navigation works independently
- ✅ Clean separation of concerns

---

## Tab Navigation Behavior (After Fix)

### Shipping Intelligence Page - 3 Tabs
1. **Pre-Manifest Tab:** Shows inbound vessels arriving in corridor
2. **Active Shipments Tab:** Shows high-risk shipments (with "Access Workspace" button)
3. **Duties & Enforcement Tab:** Shows AD/CVD duties and EAPA cases

Each tab:
- ✅ Displays independently without interference
- ✅ Content updates on click
- ✅ Can be accessed via keyboard (Tab/Arrow navigation)
- ✅ Maintains state when switching between tabs
- ✅ Never overridden by other components

### Investigation Workspace Page
- When user clicks "Access Workspace" from a shipment:
  - Navigates to `/investigations?shipmentId=<ID>`
  - Full Investigation Workspace loads
  - Can view case details, referral package, etc.
  - Different interface optimized for investigation

---

## Files Modified

| File | Changes |
|------|---------|
| `ui/src/v2/pages/V2ShippingIntelligencePage.tsx` | Removed state override, added navigation, cleaned up code |
| `ui/src/v2/hooks/useRiskScoring.ts` | Fixed API URL to use relative proxy path |
| `ui/src/v2/pages/V2InvestigationsPage.tsx` | Moved hook call before early return |
| `ui/src/v2/pages/V2ShippingIntelligencePage.tsx` (same file) | Fixed conditional hook call |

---

## Testing Checklist

- [x] Build completes successfully (TypeScript + Vite)
- [x] UI renders without React errors
- [x] Tab navigation component receives correct props
- [x] Tabs switch content on click
- [x] "Access Workspace" button navigates to /investigations page
- [x] Query parameter (shipmentId) passed correctly
- [x] No state interference between tabs and detail views
- [x] API endpoints respond through proxy

---

## Technical Details

### Why Tabs Were Breaking

The original design pattern tried to mix two concerns:
1. **Tab Navigation** (horizontal tabs at top)
2. **Detail View** (inline shipment workspace)

Using a conditional ternary operator to switch between them caused:
- State conflicts (which view should be active?)
- UI flashing (tabs appear/disappear)
- Navigation confusion (clicking what goes where?)

### Why Navigation Fix Works Better

React Router handles page navigation cleanly:
- Route change handled by router (`/investigations?shipmentId=...`)
- New page component (V2InvestigationsPage) loads
- Old state in ShippingIntelligencePage doesn't interfere
- User can easily navigate back
- Full browser history support
- Bookmarkable URLs

### Why Removing State Override Works

By removing the conditional that replaced tabs:
- TabNavigation component always renders
- State management is simpler (one concern per component)
- Each tab is independent
- No hidden/visible conflicts
- React re-renders are predictable

---

## Design Principle Applied

**Separation of Concerns:**
- Shipping Intelligence page: Shows vessels and shipments in a corridor
- Investigation Workspace page: Shows detailed investigation for a shipment
- Each page has its own navigation model
- No page tries to be two different things

---

## Verification

**API Test:**
```bash
curl http://localhost:3001/api/shipments?risk_min=50&limit=5
# Returns shipment data ✓
```

**Build Test:**
```bash
docker compose build sentry-ui
# Compiles successfully ✓
# TypeScript validation passes ✓
```

**Navigation Test:**
- User navigates to Shipping Intelligence page ✓
- Selects a corridor ✓
- Tabs switch content on click ✓
- Clicks "Access Workspace" ✓
- Navigates to Investigation Workspace with shipmentId param ✓

---

**Status:** All issues resolved. Tabs work correctly. Navigation is proper. Ready for testing. ✅
