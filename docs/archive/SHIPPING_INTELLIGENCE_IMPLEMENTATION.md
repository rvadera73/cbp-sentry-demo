# Shipping Intelligence Implementation - Complete

## 🎯 Overview

The Shipping Intelligence feature has been completely redesigned with a **backend-first, database-driven architecture**. All corridor definitions, duty rates, enforcement actions, and pattern indicators are now in the database and refreshable via API — no static frontend data.

## ✅ What Was Completed

### 1. Backend Architecture (Sentry-Data Service)

#### New Database Tables
- **corridors** — corridor definitions with risk profiles
- **corridor_duties** — AD/CVD rates linked to USITC case numbers (source URLs included)
- **corridor_enforcement_actions** — EAPA cases from CBP public records
- **pre_manifest_vessels** — AIS vessel tracking (destination, ETA, position, speed)

#### Seed Data
Created `corridors_seed.json` with 7 corridors covering major trade routes:
- VN→US (TARIFF_EVASION, aluminum extrusions)
- MY→US (FORCED_LABOR, semiconductors, solar equipment)
- CN→US (ORIGIN_CONCEALMENT, critical risk, semiconductor controls)
- HK→US (TRANSSHIPMENT_HUB, high risk)
- TH→US (SOURCING_RISK)
- SG→US (COMPLIANT_TRADE, low risk)
- IN→US (PHARMA_IP_RISK)

Each includes:
- Real USITC case numbers and AD/CVD rates
- CBP EAPA enforcement actions with duty evasion amounts
- Source URLs for CBP press releases (public record traceability)

#### API Endpoints (Sentry-Data)
- `GET /corridors` — list all corridors with computed stats from shipments
  - Returns: shipment_count, avg_risk_score, element9_mismatch_rate_pct, avg_shipper_age_months, unique_shippers
- `GET /corridors/{id}` — single corridor detail (duties, enforcement actions, pattern indicators)
- `POST /corridors` — create or update corridor
- `GET /pre-manifest/vessels` — list inbound vessels to US
- `POST /pre-manifest/vessels` — create/update pre-manifest vessel
- `GET /corridors/refresh/status` — last refresh timestamps

### 2. Background Scheduler (Sentry-API Service)

#### APScheduler Integration
- **30-minute job**: refresh pre-manifest vessels from VesselFinder API
  - Queries VesselFinder for inbound vessels to US ports
  - Derives corridor_id from origin/destination countries
  - Skips vessels already in shipments table (matching by vessel_imo)
  - Upserts into pre_manifest_vessels
  
- **Daily job**: refresh corridor duty rates from trade.gov API
  - Syncs AD/CVD rates, effective dates, case status
  - Fallback to existing data if API fails

#### refresh_jobs.py
- `refresh_pre_manifest_vessels()` — placeholder ready for VesselFinder API key
- `refresh_corridor_duties()` — placeholder ready for trade.gov integration
- Structured for easy integration of external APIs

### 3. API Gateway (Sentry-API Service)

#### Proxy Routes
- `GET /api/corridors` → `sentry-data:8005/corridors`
- `GET /api/corridors/{id}` → `sentry-data:8005/corridors/{id}`
- `POST /api/corridors` → `sentry-data:8005/corridors`
- `GET /api/pre-manifest/vessels` → `sentry-data:8005/pre-manifest/vessels`
- `POST /api/pre-manifest/vessels` → `sentry-data:8005/pre-manifest/vessels`

All routes authenticated via inter-service OIDC (Cloud Run) or direct HTTP (local dev).

### 4. Frontend Architecture

#### Bug Fix: Hook-in-Loop
- Extracted `computeShippingIntelligence()` as pure function
- Fixed React hook violation in shipment list rendering
- `useShippingIntelligence` now properly memoizes

#### New Hooks
- **useCorridorIntelligence.ts**
  - `useCorridorIntelligence()` — fetches all corridors with computed stats
  - `useCorridorDetail(corridorId)` — fetches single corridor with duties/enforcement
  - Returns: corridors[], count, isLoading, error, timestamp

- **usePreManifestVessels.ts**
  - `usePreManifestVessels(autoRefresh)` — fetches inbound vessels
  - `usePreManifestVesselsWithRefresh()` — includes manual refresh trigger
  - Returns: vessels[], count, isLoading, error, lastRefreshed, isRefreshing

#### V2ShippingIntelligencePage Rewrite
Complete redesign with three-panel layout:

**Left Panel: Corridor List**
- Sorted by risk_level (CRITICAL → LOW)
- Shows computed statistics:
  - Shipment count
  - Average risk score
  - Element 9 mismatch rate %
  - Average shipper age
  - Unique shippers
- Primary HS chapter badges
- Click to select corridor

**Right Panel: Tabbed Interface**

1. **Pre-Manifest Tab**
   - List of inbound vessels in corridor
   - AIS status (UNDERWAY, AT_BERTH, INBOUND)
   - Speed, ETA, current position
   - IMO number, flag state
   - Corridor risk profile summary

2. **Active Shipments Tab**
   - Shipments in selected corridor
   - Risk score badge
   - HS code and declared value
   - Pricing anomaly flags (SEVERE, HIGH, PREMIUM)
   - Element 9 mismatches
   - Click to view compliance detail

3. **Duties & Enforcement Tab**
   - AD/CVD duties from corridor_duties table
     - Case number, duty type, HS prefix, rate
     - Product description
     - Status (ACTIVE, REVOKED, UNDER_REVIEW)
     - Link to source URL (USITC, ustr.gov, cbp.gov)
   - EAPA enforcement actions
     - Case ID, entity name, status
     - Duty evaded amount
     - Case year, source (CBP press release)
   - Selected shipment compliance breakdown
     - H1/H2/H3 score breakdown
     - ISF Element 9 status
     - Pricing variance analysis (% vs benchmark)

**Header**
- Manual Refresh button
- Last refresh timestamp
- Corridor count
- Loading states

**Empty State**
- "Select a corridor to begin" when nothing selected

### 5. Bug Fixes

#### Column Name Mismatch (api/services/risk_corridors/db.py)
Fixed 11 SQL queries using wrong column names:
- `commodity_code` → `hs_code`
- `declared_value` → `declared_value_usd`
- `shipper_country` → `origin_country`
- `consignee_country` → `destination_country`

This was preventing corridor risk data from being retrieved (all queries returned empty).

## 🔄 Data Flow

```
Frontend (V2ShippingIntelligencePage)
    ↓
useCorridorIntelligence / usePreManifestVessels
    ↓
Sentry-API Proxy Routes (/api/corridors/*, /api/pre-manifest/*)
    ↓
Sentry-Data Service REST API
    ↓
SQLite Database (corridors, corridor_duties, corridor_enforcement_actions, pre_manifest_vessels)
    ↓
Pattern Indicators (computed live from shipments table)
```

## 🚀 Next Steps for Deployment

### 1. Local Testing
```bash
# Start services locally
docker-compose up

# Test API endpoints
curl http://localhost:8005/corridors
curl http://localhost:8000/api/corridors

# Check UI at http://localhost:5173
```

### 2. Staging Deployment
```bash
# Current deploy.yml already has:
# - build-data job (creates Dockerfile for sentry-data)
# - deploy-data job (Cloud Run deployment)
# - Selective build+deploy (only changed services)
# - GCS FUSE persistence for SQLite

git push origin dev
# GitHub Actions will trigger automated deploy
```

### 3. Configuration for External APIs

#### VesselFinder API Integration
1. Add `VESSEL_FINDER_API_KEY` to `.env` or Cloud Run secret
2. Uncomment API call in `refresh_jobs.py:refresh_pre_manifest_vessels()`
3. Update vessel query logic to filter by `destination_country = 'US'` and `eta_us < 30 days`
4. Scheduler runs every 30 minutes automatically

#### Trade.gov Tariff API Integration
1. Optional: add `TRADEGOV_API_KEY` if needed (trade.gov doesn't require key)
2. Uncomment API call in `refresh_jobs.py:refresh_corridor_duties()`
3. Parse response and upsert into `corridor_duties`
4. Scheduler runs daily automatically

## 📊 Key Features

### ✅ Compliance-Focused Design
- All data tied to H1/H2/H3 risk scoring model
- Pre-manifest intelligence available before shipment filing
- Pattern indicators computed from real shipment data (no estimates)

### ✅ Audit Trail
- All duties/enforcement actions source-linked (URLs included)
- CBP press releases cited as public records
- USITC case numbers traceable

### ✅ Real-Time Updates
- Corridor stats compute live from shipments table
- Pattern indicators update as new shipments arrive
- No stale hardcoded data in frontend

### ✅ Scalable Architecture
- Database-driven (extensible to 1000s of corridors)
- Background scheduler (30-min/daily refresh cadence)
- Pattern indicators via SQL aggregation (not ML models)

## 🔐 Security & Compliance

- No credentials in frontend code
- Inter-service auth via OIDC (Cloud Run) or local HTTP
- Seed data from public CBP/USITC sources only
- SQLite locked to single writer per deployment (Cloud Run max-instances=1)
- GCS FUSE persistence (survives pod restarts)

## 📝 Git Commits

```
e1d28c1 refactor: Rewrite V2ShippingIntelligencePage with DB-driven architecture
e116c72 feat: Backend-first Shipping Intelligence with DB-driven corridors and pre-manifest vessels
53bff07 docs: Update DEPLOYMENT.md with selective build+deploy and entity resolution troubleshooting
2022e67 feat: Selective build+deploy on changed services (staging only)
1b2b053 refactor: Enable parallel Cloud Run deployment via dynamic URL resolution
```

## 🧪 Testing Checklist

- [ ] Local: `curl http://localhost:8005/corridors` returns 7 corridors with computed stats
- [ ] Local: `curl http://localhost:8005/corridors/VN→US` returns duties and enforcement actions
- [ ] Local: `curl http://localhost:8005/pre-manifest/vessels` returns empty list (no VesselFinder data yet)
- [ ] Local: UI loads Shipping Intelligence page without errors
- [ ] Local: Corridor list populated from API (not hardcoded)
- [ ] Local: Click corridor shows pre-manifest vessels, active shipments, duties/enforcement
- [ ] Local: Refresh button triggers API calls
- [ ] Staging: Deploy successful, routes accessible
- [ ] Staging: Data persists across pod restart (GCS FUSE)
- [ ] Staging: Scheduler jobs logged (check Cloud Run logs for refresh jobs)

## ⚠️ Known Limitations

1. **VesselFinder API**: Currently mocked (awaiting API key)
   - Structure in place, ready for credential integration
   
2. **trade.gov API**: Currently mocked (free API, optional key)
   - Structure in place, ready for rate/case data integration
   
3. **Pre-Manifest Vessels**: Currently empty in local dev
   - Will populate once VesselFinder API integrated
   - Can manually insert test data via POST endpoint

## 📚 Files Modified

**Backend (Sentry-Data)**
- `services/data/db.py` — +380 lines (4 new tables + 8 functions)
- `services/data/main.py` — +240 lines (API endpoints + seed function)
- `services/data/seed_data/corridors_seed.json` — new file

**Backend (Sentry-API)**
- `services/api/main.py` — +115 lines (proxy routes + scheduler init)
- `services/api/refresh_jobs.py` — new file (background jobs)
- `services/api/requirements.txt` — +1 line (apscheduler)

**Backend (Risk Corridors Module)**
- `api/services/risk_corridors/db.py` — 76 lines fixed (column names)

**Frontend**
- `ui/src/v2/hooks/useShippingIntelligence.ts` — refactored (extracted pure function)
- `ui/src/v2/hooks/useCorridorIntelligence.ts` — new file (141 lines)
- `ui/src/v2/hooks/usePreManifestVessels.ts` — new file (136 lines)
- `ui/src/v2/pages/V2ShippingIntelligencePage.tsx` — rewritten (637 lines, was 293)

**Total Changes**: 1,417 insertions, 98 deletions across 11 files

## 🎓 Key Learnings

1. **Pattern Indicators**: Computed live via SQL aggregation (mismatch rate, shipper age, unique count) rather than hardcoded estimates
2. **Audit Trail**: Public data sources (CBP press releases, USITC cases) linked in database for traceability
3. **Pre-Manifest Intelligence**: Available before manifest filed, derived from corridor risk profiles + vessel AIS
4. **Compliance-Focused**: Every feature aligned with H1/H2/H3 risk scoring model
5. **Extensible Architecture**: Seed data can grow from 7 to 1000+ corridors without code changes

---

**Status**: ✅ Complete and Ready for Testing  
**Next Phase**: VesselFinder/trade.gov API integration + staging validation
