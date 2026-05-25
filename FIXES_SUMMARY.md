# Complete Fixes Summary — React Hooks & Tab Navigation

**Date:** May 25, 2026  
**Status:** ✅ ALL ISSUES RESOLVED  

---

## Overview

Fixed 3 critical React issues preventing the application from working:
1. React error #299 (Rules of Hooks violation)
2. React error #310 (Conditional hook call)
3. Tab navigation not working + broken Access Workspace flow

---

## Issue #1: React Error #299 (V2InvestigationsPage)

### Problem
`useRiskScoring` hook was called AFTER an early return, violating React's Rules of Hooks.

### Root Cause
```typescript
function SynopsisTab({ selectedCase, selectedCaseShipments }: any) {
  // ❌ EARLY RETURN
  if (!selectedCaseShipments || selectedCaseShipments.length === 0) 
    return <div>No shipments available</div>;
  
  // ❌ HOOK CALLED AFTER EARLY RETURN
  const { scoreData, loading, error } = useRiskScoring(shipment?.shipment_id || null);
```

When `selectedCaseShipments` changes:
- First render: condition false → hook gets called
- Second render: condition true → hook NOT called
- React detects hook count changed → Error #299

### Solution
```typescript
function SynopsisTab({ selectedCase, selectedCaseShipments }: any) {
  const shipment = selectedCaseShipments?.[0];
  
  // ✅ HOOK CALLED UNCONDITIONALLY (at top level)
  const { scoreData, loading, error } = useRiskScoring(shipment?.shipment_id || null);
  
  // ✅ EARLY RETURN AFTER HOOK
  if (!selectedCaseShipments || selectedCaseShipments.length === 0) 
    return <div>No shipments available</div>;
```

**File:** `ui/src/v2/pages/V2InvestigationsPage.tsx` (lines 480-490)

---

## Issue #2: React Error #310 (V2ShippingIntelligencePage)

### Problem
`useShippingIntelligence` hook was called conditionally inside a ternary operator.

### Root Cause
```typescript
// ❌ CONDITIONAL HOOK CALL (inside ternary)
const selectedShipmentIntel = selectedShipment 
  ? useShippingIntelligence(selectedShipment) 
  : null;
```

When `selectedShipment` changes:
- First render: undefined → hook NOT called
- Second render: has value → hook called
- React detects hook called conditionally → Error #310

### Solution
```typescript
// ✅ HOOK ALWAYS CALLED (let it handle null internally)
const selectedShipmentIntel = useShippingIntelligence(selectedShipment || null);
```

**File:** `ui/src/v2/pages/V2ShippingIntelligencePage.tsx` (line 43)

---

## Issue #3: Tab Navigation & Access Workspace Broken

### Problems

#### 3A: Tabs Not Working
The page had conditional rendering that was REPLACING tabs with an inline detail view.

```typescript
{selectedShipmentId && activeTab === 'compliance' ? (
  // TABS COMPLETELY HIDDEN - replaced with this view
  <ShipmentDetailView /> 
) : (
  // TABS ONLY SHOW WHEN NO SHIPMENT SELECTED
  <TabNavigation /> 
)}
```

**Effect:** Tabs disappear when you select a shipment.

#### 3B: Access Workspace Button Not Working
The button was just setting local state instead of navigating.

```typescript
// ❌ WRONG: Just changes UI on same page
const handleAccessWorkspace = (shipmentId: string) => {
  setSelectedShipmentId(shipmentId);  // Triggers tab override ↑
  setActiveTab('compliance');
  setFromPage('shipping-intelligence');
};
```

**Effect:** Button doesn't navigate to Investigation Workspace.

#### 3C: Investigation Workspace Doesn't Read Query Parameter
The page didn't use the `shipmentId` query parameter from the URL.

```typescript
// No useSearchParams, no useEffect to read ?shipmentId=...
// Page just shows empty case list instead of the selected case
```

**Effect:** Navigation to `/investigations?shipmentId=XYZ` shows case list, not the selected case.

### Solution

#### 3A: Remove Tab Override
Completely removed the conditional that was replacing tabs:

```typescript
// ❌ REMOVED THIS:
{selectedShipmentId && activeTab === 'compliance' ? ( ... ) : ( ... )}

// ✅ NOW: Tabs always render, never get hidden
<TabNavigation ... />
```

**Result:** Tabs always visible and clickable.

#### 3B: Proper Navigation
Changed to use React Router for navigation:

```typescript
import { useNavigate } from 'react-router-dom';

const navigate = useNavigate();

const handleAccessWorkspace = (shipmentId: string) => {
  // ✅ CORRECT: Navigate to Investigation Workspace
  navigate(`/investigations?shipmentId=${encodeURIComponent(shipmentId)}`);
};
```

**Result:** Button properly navigates to Investigation Workspace page.

#### 3C: Read Query Parameter
Added query parameter handling to Investigation Workspace:

```typescript
import { useSearchParams } from 'react-router-dom';

const [searchParams] = useSearchParams();

// Auto-select case when shipmentId is in URL
useEffect(() => {
  const shipmentId = searchParams.get('shipmentId');
  if (shipmentId && cases.length > 0 && !selectedCaseId) {
    // Find shipment in data
    const shipment = shipments.find(s => s.shipment_id === shipmentId);
    if (shipment) {
      // Find matching case
      const matchingCase = cases.find(c =>
        c.origin_country === shipment.origin_country &&
        c.destination_country === shipment.destination_country &&
        c.target_entity === shipment.shipper_name
      );
      if (matchingCase) {
        // Auto-select the case
        setSelectedCaseId(matchingCase.case_id);
        setActiveSubTab('Shipment');
      }
    }
  }
}, [searchParams, cases, shipments, selectedCaseId, setSelectedCaseId, setActiveSubTab]);
```

**Result:** Navigating to `/investigations?shipmentId=XYZ` automatically selects and displays that case.

**File:** `ui/src/v2/pages/V2InvestigationsPage.tsx` (lines 1-75)

---

## API & Environment Fixes

### Issue: useRiskScoring Using Wrong API URL

**Problem:**
```typescript
const apiUrl = process.env.VITE_API_URL || 'http://localhost:8000';
const response = await fetch(`${apiUrl}/api/risk-scoring/comprehensive`, {...});
```

- `process.env` is not the right way to access Vite env vars
- Hardcoded localhost doesn't work in Docker
- Bypasses nginx proxy

**Solution:**
```typescript
const response = await fetch(`/api/risk-scoring/comprehensive`, {...});
```

- Uses relative path through nginx proxy
- Works in all environments (local/staging/prod)
- Respects build-time API URL configuration

**File:** `ui/src/v2/hooks/useRiskScoring.ts` (lines 47-52)

---

## Files Changed

| File | Changes | Lines |
|------|---------|-------|
| `V2InvestigationsPage.tsx` | Added React Router imports; Added query param handling; Fixed hook violation | 1-75, 480-490 |
| `V2ShippingIntelligencePage.tsx` | Removed state override; Added navigation; Fixed hook violation | 1, 43, 112, 145, 243-250 |
| `useRiskScoring.ts` | Fixed API URL to use proxy | 47-52 |

---

## Complete User Journey (After Fixes)

### 1. Shipping Intelligence Page
```
✅ User selects corridor (e.g., VN→US)
✅ Pre-Manifest tab shows vessels
✅ Active Shipments tab shows shipments
✅ Tabs are clickable and switch content
✅ "Access Workspace" button appears on each shipment
```

### 2. Click "Access Workspace"
```
✅ Navigates to /investigations?shipmentId=SHP-000731
✅ URL is bookmarkable
✅ Browser back button works
```

### 3. Investigation Workspace Page
```
✅ Page reads shipmentId from query parameter
✅ Finds matching case automatically
✅ Auto-selects and displays that case
✅ Shows case workspace with 4 tabs:
   - Shipment: Details of the shipment
   - Entity: Parties involved
   - Risk Score: Risk breakdown
   - Evidence & Referral: Referral package
✅ All tabs are clickable and work properly
```

### 4. Tab Navigation
```
✅ Shipment tab: Click → view shipment details
✅ Entity tab: Click → view party information
✅ Risk Score tab: Click → view risk breakdown (with API call)
✅ Evidence & Referral tab: Click → view referral package
✅ Tab switching is instantaneous
✅ No data loss when switching tabs
```

---

## Technical Improvements

### Before
- ❌ Two different views fighting for control
- ❌ State complexity (multiple UI states)
- ❌ Navigation bypass (local state instead of routing)
- ❌ Hook violations (React errors)
- ❌ Non-bookmarkable URLs
- ❌ No browser history support

### After
- ✅ Single responsibility per page
- ✅ Clean state management
- ✅ Proper routing with React Router
- ✅ All hooks called unconditionally
- ✅ Bookmarkable URLs with query parameters
- ✅ Full browser history support
- ✅ Tabs always work
- ✅ Proper async data loading

---

## Testing Checklist

- [x] Build succeeds without TypeScript errors
- [x] UI loads at localhost:3001
- [x] API endpoints respond through proxy
- [x] Shipping Intelligence page tabs work
- [x] Active Shipments tab displays shipments
- [x] "Access Workspace" button navigates to /investigations?shipmentId=...
- [x] Investigation Workspace page loads
- [x] Query parameter auto-selects correct case
- [x] Case details display correctly
- [x] All 4 tabs (Shipment, Entity, Risk Score, Evidence & Referral) clickable
- [x] Tab switching shows correct content
- [x] No React errors in console
- [x] Keyboard navigation works (Tab key)
- [x] Mouse clicks work on tab buttons
- [x] Risk Score tab API call succeeds
- [x] Referral Package displays
- [x] Back button in Investigation workspace goes back to case list
- [x] Browser back button navigates correctly

---

## Root Cause Summary

These bugs stemmed from mixing two architectural patterns:

1. **Local State UI Pattern:** Managing which detail to show with boolean flags
2. **React Router Pattern:** Managing which page to show with routes

When both are active on the same page, they conflict:
- State says "show detail view"
- Router says "show page with tabs"
- Result: Broken UI

**The Fix:** Use only one pattern per page:
- Shipping Intelligence: Uses local state for tabs (same page)
- Investigation Workspace: Uses React Router for navigation (different pages)
- Each page manages its own tabs cleanly

---

## Prevention

To avoid similar issues in the future:

1. **One Pattern Per Page**
   - Don't mix local state UI toggles with React Router
   - Use Router for page navigation, state for in-page UI

2. **Test Hooks**
   - ESLint plugin: `eslint-plugin-react-hooks`
   - Always called at top level
   - Same order every render
   - Never conditional

3. **Tab Navigation Pattern**
   - Tabs always render (never conditional)
   - Content based on state/route
   - No "tab replacement" logic

4. **Navigation Pattern**
   - Use React Router for page changes
   - Use state for in-page UI changes
   - Never mix the two

---

**Deployment Status:** Ready for user testing ✅  
**Build Status:** Passing ✅  
**All Tests:** Passing ✅  
**Code Quality:** No TypeScript errors ✅
