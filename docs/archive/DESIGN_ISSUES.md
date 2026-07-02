# Design Issues - Requiring Discussion Before Implementation

These issues have been identified but need design discussion before implementation. No fixes should be considered final without team review.

---

## Issue #1: Nginx DNS Resolution in Docker Compose

**Status:** ⚠️ NEEDS DESIGN DISCUSSION  
**Priority:** HIGH (blocking API communication)

### Problem Statement
The nginx container in sentry-ui cannot reliably resolve the `sentry-api` service name for proxying API requests. This causes failed requests when the browser uses the `/api/*` proxy.

### Current Observations
- Docker Compose starts all services on the same network
- Service name resolution should work via Docker's embedded DNS (127.0.0.11)
- But nginx is reporting "could not be resolved (3: Host not found)"
- Attempts to use `resolver 127.0.0.11` with variables failed
- Changed to `upstream` block which appears to work

### Design Questions That Need Discussion
1. **Should we use nginx proxy at all for local dev?**
   - Option A: Keep nginx proxy, fix DNS configuration properly
   - Option B: Skip nginx proxy locally, have React make direct calls to :8000
   - Option C: Hybrid - use proxy for assets, direct calls for API

2. **What's the pattern for local dev vs. staging/prod?**
   - Should local use `/api` relative paths?
   - Should staging/prod use absolute URLs built at compile time?
   - Should we have an environment config file?

3. **DNS resolver approach - what's most reliable?**
   - Upstream block (current attempt)
   - Resolver directive with proper Docker DNS config
   - Service name in environment variables
   - Something else?

### Next Steps
- [ ] Design session: Discuss local dev architecture
- [ ] Design session: Define staging/prod patterns
- [ ] Technical decision: Pick DNS resolution approach
- [ ] Implementation: Apply chosen solution
- [ ] Testing: Verify across all environments

---

## Issue #2: API URL Configuration Across Environments

**Status:** ⚠️ NEEDS DESIGN DISCUSSION  
**Priority:** HIGH (affects deployment)

### Problem Statement
React app needs to know where the API is located, but this varies by environment:
- Local Docker: Should it be `http://localhost:8000`, `/api` proxy, or something else?
- Staging: Unknown host/URL
- Production: Unknown host/URL

### Current Observations
- docker-compose.yml passes `API_URL` as build argument
- Empty API_URL causes React to use `/api` relative paths
- Non-empty values embed absolute URLs in compiled JavaScript
- Dockerfile has comments about "Cloud Run" but no actual Cloud Run config

### Design Questions That Need Discussion
1. **Should API URL be baked in at build time or loaded at runtime?**
   - Option A: Build-time (current VITE_API_URL approach)
   - Option B: Runtime config file (config.json served by nginx)
   - Option C: Window global set by nginx (inject via environment)
   - Option D: Query parameter or header-based discovery

2. **What should local development default to?**
   - `/api` proxy through nginx?
   - Direct to `http://localhost:8000`?
   - Auto-detect based on hostname?

3. **How do we handle staging/production different URLs?**
   - Separate docker-compose files?
   - Environment variable substitution?
   - Build-time configuration?
   - Runtime discovery?

4. **Should different services have different discovery patterns?**
   - UI → API: One pattern
   - API → Data Service: Different pattern (always Docker-internal)?
   - API → External services (OFAC, VesselAPI): Another pattern?

### Next Steps
- [ ] Design session: Decide build-time vs runtime config
- [ ] Design session: Define environment strategy (local/staging/prod)
- [ ] Technical decision: Pick configuration approach
- [ ] Implementation: Apply across all services
- [ ] Documentation: Document for team

---

## Issue #3: Tab Navigation - Keyboard & Click Responsiveness

**Status:** ⚠️ NEEDS DESIGN DISCUSSION  
**Priority:** MEDIUM (UX/accessibility)

### Problem Statement
Investigation workspace tabs are not responding to:
- Mouse clicks
- Keyboard Tab/Arrow navigation
- Proper focus states

### Current Observations
- TabNavigation component exists at `ui/src/v2/components/TabNavigation.tsx`
- Added `type="button"` attribute (but unclear if this alone fixes the issue)
- Added `cursor-pointer` class (visual feedback only)
- Unknown if React state is updating properly on click
- Unknown if keyboard events are being handled

### Design Questions That Need Discussion
1. **Should tabs use native HTML <button> or <a> or custom <div>?**
   - Option A: HTML <button> (semantic, accessible)
   - Option B: HTML <a> with role="tab" (if using routed pages)
   - Option C: Div with role="tab" and custom event handling
   - Option D: Tab library (headless-ui, radix-ui, etc.)

2. **What keyboard interaction pattern should we use?**
   - Option A: Tab key moves focus, Enter/Space activates
   - Option B: Arrow keys to navigate between tabs
   - Option C: Both (Tab for focus, Arrow for navigation)
   - Option D: Custom pattern specific to CBP workflows?

3. **How should active/focus states be styled?**
   - Option A: Separate colors for focus vs active
   - Option B: Single active color with outline for focus
   - Option C: Underline for active, highlight for focus
   - Option D: Something else matching CBP design system?

4. **Should the active tab be controlled by URL or state?**
   - Option A: URL params (e.g., /investigations?tab=shipment)
   - Option B: React state only (loses on refresh)
   - Option C: localStorage + state (persists across sessions)
   - Option D: Server-side session

### Next Steps
- [ ] Accessibility audit: Test with actual keyboard navigation
- [ ] Design session: Choose tab implementation approach
- [ ] Design session: Define keyboard interaction patterns
- [ ] Implementation: Rewrite TabNavigation component
- [ ] Testing: Verify with screen readers and keyboard-only users

---

## Issue #4: Referral Package Component Display

**Status:** ⚠️ NEEDS DESIGN DISCUSSION  
**Priority:** MEDIUM (feature display)

### Problem Statement
ReferralPackageViewer_NEW component is trying to display a PDF that doesn't exist. The actual data is a complex JSON structure with 14 tables from CSOP-BP-GS-26-0001 specification.

### Current Observations
- Component tries to fetch `/api/referral/{id}/package` (endpoint doesn't exist)
- Actual endpoint is `/api/referral/{id}` (returns JSON)
- Attempted to convert to HTML display but design unclear
- Unknown if this matches user expectations

### Design Questions That Need Discussion
1. **Should referral package be displayed or exported?**
   - Option A: Interactive HTML view in browser
   - Option B: PDF export (requires PDF generation service)
   - Option C: Print-to-PDF (browser native)
   - Option D: Both (view + export)

2. **What data should be shown and in what order?**
   - Show all 14 tables?
   - Show summary only?
   - Show selectable sections?
   - Expand/collapse sections?
   - Print-optimized layout?

3. **How should the 14 tables be organized?**
   - Tabs (like investigation workspace)?
   - Sections with headers?
   - Accordion/collapsible sections?
   - Progressive disclosure?

4. **Is the JSON structure from `/api/referral/{id}` complete and correct?**
   - Does it have all required fields?
   - Are data types correct?
   - Are any fields missing?
   - Should the API be modified?

5. **What's the user workflow?**
   - View referral package in UI?
   - Export for external use?
   - Submit to authorities?
   - Archive/print?

### Next Steps
- [ ] Requirements discussion: What should referral display be?
- [ ] Design session: Choose display approach
- [ ] Design session: Plan information hierarchy
- [ ] Technical decision: PDF generation vs HTML view vs both
- [ ] API review: Verify `/api/referral/{id}` returns all needed data
- [ ] Implementation: Build component matching design

---

## Issue #5: Active Shipments to Investigation Navigation

**Status:** ⚠️ NEEDS DESIGN DISCUSSION  
**Priority:** MEDIUM (user workflow)

### Problem Statement
No clear path from "Active Shipments" page to create/access an investigation for a specific shipment.

### Current Observations
- Added "Access Investigation Workspace" button
- Navigates to `/investigations?shipmentId={id}`
- Unknown if investigations page expects this parameter
- Unknown if clicking should create new investigation or open existing

### Design Questions That Need Discussion
1. **What should happen when user clicks "Access Investigation"?**
   - Option A: Create a new investigation for this shipment
   - Option B: Search for existing investigation with this shipment
   - Option C: Open investigation creation form with shipment pre-filled
   - Option D: Show list of related investigations

2. **Should investigations always be tied to specific shipments?**
   - Option A: One shipment per investigation
   - Option B: Multiple shipments per investigation (collection)
   - Option C: Either (flexible)
   - Option D: Neither (independent of shipments)

3. **What should be pre-filled in the investigation?**
   - Risk score, commodity, route
   - All shipment details
   - Nothing (user chooses case details)
   - Something else?

4. **What's the actual user workflow?**
   - Officer sees shipment → Creates case
   - Officer has open case → Finds related shipments
   - Officer has high-risk list → Triages into cases
   - Officer has referral → Reviews shipments
   - Other?

5. **Should the button say "Access Investigation" or something else?**
   - "Create Investigation"
   - "Start Case"
   - "Open Workspace"
   - "View/Create Case"
   - "New Investigation for This Shipment"

### Next Steps
- [ ] Requirements discussion: What's the user workflow?
- [ ] Requirements discussion: Can investigation have multiple shipments?
- [ ] Design session: Plan the navigation/creation flow
- [ ] Design session: Define what pre-fills the investigation form
- [ ] Design session: Finalize button label and behavior
- [ ] Implementation: Build the complete workflow

---

## Issue #6: Risk Scores and Demo Data

**Status:** ⚠️ NEEDS DESIGN DISCUSSION  
**Priority:** LOW (data quality)

### Problem Statement
Database has data (1,471 shipments) but unclear if risk scores are calculated correctly or if data is realistic for testing/demo purposes.

### Current Observations
- 26 high-risk (≥80)
- 453 medium-risk (50-79)
- 992 low-risk (<50)
- Distribution appears reasonable (2% high, 31% medium, 67% low)
- Unknown if risk scores are calculated with current engine
- Unknown if test data matches real CBP patterns

### Design Questions That Need Discussion
1. **Should demo data match real CBP patterns?**
   - Option A: Use real or realistic data distributions
   - Option B: Use synthetic data with diverse patterns
   - Option C: Use real data (if available)
   - Option D: Vary distribution for different scenarios

2. **Should we validate risk scoring engine against test data?**
   - Option A: Re-score all shipments with current engine
   - Option B: Compare with expected risk patterns
   - Option C: Audit a sample of high-risk shipments
   - Option D: No validation needed

3. **What's the acceptable distribution of risk scores?**
   - Should it match real CBP statistics?
   - Should it have more high-risk for demo impact?
   - Should it vary by commodity type?
   - Should it vary by route/corridor?

4. **Do we need different datasets for different purposes?**
   - Demo dataset (impressive, diverse)
   - Test dataset (edge cases, coverage)
   - Performance dataset (large volume)
   - Training dataset (for ML models)

### Next Steps
- [ ] Requirements discussion: What should demo data look like?
- [ ] Requirements discussion: Is current distribution acceptable?
- [ ] Risk engine review: Are scores being calculated correctly?
- [ ] Data audit: Sample check of high-risk shipments
- [ ] Decision: Regenerate data or keep current?
- [ ] Implementation: If needed, regenerate with proper distribution

---

## Issue #7: Login Screen - Authentication Architecture

**Status:** ⚠️ NEEDS DESIGN DISCUSSION  
**Priority:** HIGH (security/access control)

### Problem Statement
Created LoginPage.tsx but no backend authentication implemented. Need complete design for:
- Google OAuth flow
- Session management
- User profiles
- Access control

### Current Observations
- Created UI component for Google Sign-In
- No backend endpoint (`/api/auth/google`)
- No session/token management
- No user profile storage
- No route protection

### Design Questions That Need Discussion
1. **What's the authentication flow?**
   - Option A: Google OAuth → Backend validates → JWT token
   - Option B: Google OAuth → Store token in localStorage → Include in requests
   - Option C: Google OAuth → Backend creates session cookie
   - Option D: Passwordless email link → Custom session
   - Option E: Something else?

2. **Where should tokens/sessions be stored?**
   - Option A: localStorage (XSS risk)
   - Option B: sessionStorage (clears on browser close)
   - Option C: httpOnly cookie (secure, CSRF risk)
   - Option D: In-memory only (lost on refresh)

3. **What user info do we need to store?**
   - Google ID
   - Email
   - Name
   - CBP officer role/department
   - Custom attributes

4. **How should we handle user profiles?**
   - Option A: Store in database
   - Option B: Get from Google only
   - Option C: Hybrid (Google → convert to local profile)
   - Option D: LDAP/Active Directory integration

5. **What routes should require authentication?**
   - Option A: Everything except /login
   - Option B: Only /investigations and admin endpoints
   - Option C: Tiered based on role
   - Option D: Configurable per route

6. **Should we have user roles?**
   - Option A: Just authenticated vs not
   - Option B: Officer, Supervisor, Admin
   - Option C: Role-based access control (RBAC)
   - Option D: Attribute-based access control (ABAC)

### Next Steps
- [ ] Security review: Define authentication requirements
- [ ] Design session: Choose OAuth flow approach
- [ ] Design session: Plan token/session storage
- [ ] Design session: Plan user profile structure
- [ ] Design session: Define role/permission model
- [ ] Technical decision: Pick implementation approach
- [ ] Implementation: Build complete auth system
- [ ] Security audit: Review for vulnerabilities

---

## Summary of Needs

All issues above require design discussion before implementation:

| Issue | Type | Blocking | Discussion Needed |
|-------|------|----------|-------------------|
| Nginx DNS | Architecture | YES | Local dev strategy, DNS approach |
| API URLs | Configuration | YES | Build vs runtime, environments |
| Tab Navigation | UX | MEDIUM | HTML approach, keyboard handling |
| Referral Package | Display | MEDIUM | Format, structure, export |
| Navigation Flow | Workflow | MEDIUM | User workflow, investigation model |
| Demo Data | Quality | NO | Distribution, realism, testing |
| Authentication | Security | YES | OAuth flow, session storage, roles |

**Recommended order for design discussions:**
1. API URL configuration (affects everything)
2. Nginx DNS / local dev architecture (enables testing)
3. Authentication (gates access)
4. Navigation workflow (affects multiple pages)
5. Tab navigation (accessibility)
6. Referral package display (feature)
7. Demo data (testing)

---

**Note:** Do not implement any of these without team agreement on design.
Each needs documented decision before code changes.
