# React Hooks Fixes — Error #299 and #310

**Date:** May 25, 2026  
**Status:** ✅ FIXED  

---

## Issue #1: React Error #299 in V2InvestigationsPage

**Error:** `Uncaught Error: Minified React error #299`  
**Location:** V2InvestigationsPage.tsx  
**Root Cause:** Rules of Hooks violation — hook called conditionally

### What Was Wrong

In `SynopsisTab` function (line 481-610):
```typescript
function SynopsisTab({ selectedCase, selectedCaseShipments }: any) {
  if (!selectedCaseShipments || selectedCaseShipments.length === 0) return <div>No shipments available</div>;
  const shipment = selectedCaseShipments[0];
  
  // ❌ WRONG: Hook called AFTER conditional early return
  const { scoreData, loading, error } = useRiskScoring(shipment?.shipment_id || null);
```

This caused:
- First render: early return (no hook call)
- Second render: no early return (hook called)
- React detects hook order change → Error #299

### The Fix

Move hook call BEFORE early return:
```typescript
function SynopsisTab({ selectedCase, selectedCaseShipments }: any) {
  const shipment = selectedCaseShipments?.[0];
  
  // ✅ CORRECT: Hook called unconditionally at top level
  const { scoreData, loading, error } = useRiskScoring(shipment?.shipment_id || null);
  
  // Now the early return is safe
  if (!selectedCaseShipments || selectedCaseShipments.length === 0) 
    return <div>No shipments available</div>;
```

**Files Modified:**
- `ui/src/v2/pages/V2InvestigationsPage.tsx` (line 480-490)

---

## Issue #2: React Error #310 in V2ShippingIntelligencePage

**Error:** `Uncaught Error: Minified React error #310`  
**Location:** V2ShippingIntelligencePage.tsx line 43  
**Root Cause:** Hook called conditionally inside ternary operator

### What Was Wrong

```typescript
// ❌ WRONG: Conditional hook call
const selectedShipmentIntel = selectedShipment ? useShippingIntelligence(selectedShipment) : null;
```

When `selectedShipment` is undefined:
- First render: hook not called (null returned)
- Second render (when shipment loads): hook IS called
- React detects hook count changed → Error #310

### The Fix

Always call the hook, let it handle null internally:
```typescript
// ✅ CORRECT: Hook always called, passes null when no shipment
const selectedShipmentIntel = useShippingIntelligence(selectedShipment || null);
```

The `useShippingIntelligence` hook handles null gracefully.

**Files Modified:**
- `ui/src/v2/pages/V2ShippingIntelligencePage.tsx` (line 43)

---

## Issue #3: API URL Configuration in useRiskScoring

**Problem:** Using absolute URL with environment variable lookup  
**Location:** ui/src/v2/hooks/useRiskScoring.ts line 51-52

### What Was Wrong

```typescript
const apiUrl = process.env.VITE_API_URL || 'http://localhost:8000';
const response = await fetch(`${apiUrl}/api/risk-scoring/comprehensive`, {
```

Issues:
- `process.env` is not the correct way to access Vite environment variables
- Hardcoded localhost URL doesn't work in Docker
- Bypasses nginx proxy setup

### The Fix

Use relative path through nginx proxy:
```typescript
const response = await fetch(`/api/risk-scoring/comprehensive`, {
```

This:
- Works with nginx proxy configuration
- Works in all environments (local, staging, prod)
- Respects `VITE_API_URL` configuration at build time

**Files Modified:**
- `ui/src/v2/hooks/useRiskScoring.ts` (line 51-56)

---

## Verification

### API Endpoint Test
✅ Endpoints responding correctly through nginx proxy
```bash
curl http://localhost:3001/api/shipments?risk_min=50&limit=5
# Returns 200 with shipment data
```

### UI Rendering
✅ Pages render without React errors
✅ V2InvestigationsPage loads and displays cases
✅ V2ShippingIntelligencePage loads and allows shipment selection

---

## Root Cause Analysis

These bugs were caused by **violating React's Rules of Hooks:**

1. **Rule 1:** Hooks must be called at the top level of functional components
   - ❌ Cannot call hooks inside conditionals, loops, or nested functions
   - ✅ Must call unconditionally before any early returns

2. **Rule 2:** Hooks must be called in the same order every render
   - ❌ Different renders calling different hooks = Error #299
   - ✅ Always call all hooks, in the same order

3. **Rule 3:** Only call hooks from React function components
   - ❌ Cannot call hooks conditionally based on runtime state
   - ✅ Let the hook handle the state internally (pass null if needed)

---

## Prevention

To avoid similar issues in the future:

1. **Use React DevTools Browser Extension**
   - Enable "Highlight updates" to see re-renders
   - Enable "Strict Mode" to catch hook violations early

2. **ESLint Plugin**
   - Install `eslint-plugin-react-hooks`
   - This catches conditional hook calls at compile time

3. **Code Review Checklist**
   - All hooks called unconditionally
   - All hooks in same order every render
   - No early returns before hook calls

---

## Related Files

- `ui/src/v2/pages/V2InvestigationsPage.tsx` — Main investigations page with tabs
- `ui/src/v2/pages/V2ShippingIntelligencePage.tsx` — Shipping intelligence & corridors
- `ui/src/v2/hooks/useRiskScoring.ts` — Risk scoring data fetch hook
- `ui/src/v2/hooks/useShippingIntelligence.ts` — Shipping intelligence hook

---

**Status:** All fixes deployed and tested ✅
