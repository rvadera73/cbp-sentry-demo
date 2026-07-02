# Runtime Issues - Investigation Required

**Issue Type:** React Runtime Error  
**Status:** 🔴 BLOCKING - Page crashes during render  
**Severity:** CRITICAL

---

## Problem

### What's Working
- ✅ API calls returning 200 status
- ✅ Data fetching (100 items, 479 total)
- ✅ Data mapping (58 cases successfully mapped)
- ✅ Nginx proxy routing (DNS resolved)

### What's Failing  
- ❌ React render crashes with "Uncaught Error: Minified React error #299"
- ❌ Page won't display even though data is loaded
- ❌ Multiple renders happening (data mapped 3 times in logs)

---

## Error Details

**React Error #299** indicates:
1. Violation of Rules of Hooks
2. Conditional hook usage
3. Hook called outside component
4. Multiple React instances
5. Improper createRoot usage

**Additional Error:**
```
Uncaught (in promise) Error: No Listener: tabs:outgoing.message.ready
```
This is likely a browser extension issue (can be ignored)

---

## Observations from Console

```
[useV2Cases] Starting fetch...
[useV2Cases] Fetching from: /api/shipments?risk_min=50&limit=100&offset=0
[useV2Cases] Response status: 200
[useV2Cases] Data received: 100 items, count: 479
[useV2Cases] Successfully mapped 58 cases
[useV2Cases] Successfully mapped 58 cases  ← logged 3 times
[useV2Cases] Successfully mapped 58 cases
Uncaught Error: Minified React error #299
```

The data mapping log appearing 3 times suggests:
- Component re-rendering multiple times
- Possible infinite re-render loop
- Hook order changing between renders

---

## Likely Root Causes

### 1. **useRiskScoring Hook Issue** (Line 5 of V2InvestigationsPage.tsx)
```typescript
const { scoreData, loading, error } = useRiskScoring(shipment?.shipment_id || null);
```
If `useRiskScoring` hook is called conditionally or has dependency issues.

### 2. **useEffect Dependencies** 
In useV2Cases hook - the dependency array might be causing re-renders:
```typescript
const [cases, setCases] = useState<Case[]>([]);
const [shipments, setShipments] = useState<Shipment[]>([]);
```
If useEffect runs infinitely, re-renders happen constantly.

### 3. **Hook Call Order Changes**
If on first render all hooks are called, but on second render some are skipped due to conditions.

### 4. **Multiple Component Instances**
Possible that both `ReferralPackageViewer` and `ReferralPackageViewerNew` are being imported and used, causing React confusion.

---

## How to Debug

### In Chrome DevTools (F12)

1. **Console Tab**
   - Disable minification: Use un-minified React (dev mode)
   - Check for full error message

2. **Sources Tab**
   - Set breakpoint in useV2Cases hook
   - Step through execution
   - Watch for hook order changes

3. **React DevTools Extension**
   - Install React DevTools browser extension
   - Check component tree
   - Look for duplicate components
   - Check hook dependencies

### Steps to Get Full Error

1. Open http://localhost:3001
2. F12 → Console
3. Look for full error message (not minified)
4. Check "Sources" tab → search for "useV2Cases"
5. Set breakpoint at line 225 (Successfully mapped log)
6. Step through code to see what happens next

---

## Suspected Fix Areas

### Check 1: useRiskScoring Hook
Look at `/home/rahulvadera/cbp-sentry/ui/src/v2/hooks/useRiskScoring.ts`
- Is it calling hooks conditionally?
- Are dependencies correct?
- Does it handle null shipmentId properly?

### Check 2: useV2Cases useEffect
Look for useEffect in `/home/rahulvadera/cbp-sentry/ui/src/v2/hooks/useV2Cases.ts`
- Is dependency array correct?
- Could it be running repeatedly?
- Is state update causing re-renders?

### Check 3: Duplicate Components
Check V2InvestigationsPage imports:
```typescript
import { ReferralPackageViewer } from '../components/ReferralPackageViewer';
import { ReferralPackageViewerNew } from '../components/ReferralPackageViewer_NEW';
```
Both are imported - could be conflicting.

### Check 4: Tab Component
Check if TabNavigation component has hook issues in render path.

---

## Investigation Checklist

- [ ] Enable React dev mode (non-minified React library)
- [ ] Get full error message from Console
- [ ] Install React DevTools extension
- [ ] Check hook call order in DevTools
- [ ] Look for infinite loops in useEffect
- [ ] Check component re-render count
- [ ] Verify hook dependency arrays
- [ ] Check for duplicate component renders
- [ ] Run with browser extensions disabled (in incognito window)

---

## Next Steps

1. **Immediate:** Follow debugging checklist above
2. **Identify:** Which hook is violating Rules of Hooks
3. **Fix:** Correct the hook or component structure
4. **Verify:** Data displays correctly
5. **Test:** Ensure no further re-render loops

---

## Related Files to Check

- `/ui/src/v2/pages/V2InvestigationsPage.tsx` (main component)
- `/ui/src/v2/hooks/useV2Cases.ts` (data fetch hook)
- `/ui/src/v2/hooks/useRiskScoring.ts` (risk data hook)
- `/ui/src/v2/components/TabNavigation.tsx` (tab component)
- `/ui/src/v2/components/ReferralPackageViewer_NEW.tsx` (referral display)

---

**This is NOT a design issue - it's a React runtime bug that needs code-level debugging.**
