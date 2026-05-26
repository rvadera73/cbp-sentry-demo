# GitHub Actions Deployment Workflow Analysis

**Date:** May 26, 2026  
**File:** `.github/workflows/deploy.yml`  
**Current Status:** Active, deploys to staging

---

## 🎯 Current Workflow Overview

```
Trigger: Push to 'dev' branch or manual workflow dispatch

Pipeline:
  1. Setup (determine branch/env)
  2. Test (pytest + TypeScript)
  3. Bootstrap (GCS bucket)
  4. Build & Push Images (4 services)
  5. Deploy to Cloud Run (4 services in order)
  6. Smoke Tests (health checks)
  7. Slack Notification
```

---

## 📋 Services Being Deployed

### Current (4 Services)
```
1. sentry-data           (services/data, port 8005)
2. sentry-cord-integration (services/cord-integration, port 8004)
3. sentry-api            (services/api, port 8000)
4. sentry-ui             (ui, port 80)
```

### Dependency Chain
```
Test
  ↓
Bootstrap GCS Bucket
  ├─ build-api ──┐
  ├─ build-data ─┤─ deploy-data ──┐
  ├─ build-cord ─┤─ deploy-cord ──┼─ deploy-api
  └─ build-ui ───┼─ deploy-ui ────┘
                 │
              smoke-tests
                 │
              notify (Slack)
```

---

## 🔍 Workflow Details

### Stage 1: Setup
```yaml
Outputs:
  - branch: 'dev' (hardcoded)
  - environment: 'staging' (hardcoded)

Location: Lines 25-39
```

**Issue:** Environment is hardcoded to 'staging', cannot deploy to production

### Stage 2: Test
```yaml
Steps:
  1. Install Python dependencies
     - services/api/requirements.txt ✅
     - services/data/requirements.txt ✅
  
  2. Run Python tests
     - pytest services/api/tests
     - pytest services/data/tests
  
  3. Install UI dependencies
     - npm ci
  
  4. TypeScript check
     - npx tsc --noEmit
  
Location: Lines 52-86
```

### Stage 3: Bootstrap
```yaml
Creates GCS bucket: gs://cbp-sentry-appdata
Purpose: Shared storage for all services

Mounts:
  - API: /app/data (read/write)
  - CORD: /app/cord-data (read/write)
  - Data: /app/data (read/write)

Location: Lines 88-110
```

### Stage 4: Build Images

**4A. Build API** (Lines 112-131)
```
Source: services/api/
Registry: us-central1-docker.pkg.dev
Image: sentry-api:{commit-sha}
```

**4B. Build Data** (Lines 133-152)
```
Source: services/data/
Registry: us-central1-docker.pkg.dev
Image: sentry-data:{commit-sha}
```

**4C. Build CORD** (Lines 154-173)
```
Source: services/cord-integration/
Registry: us-central1-docker.pkg.dev
Image: sentry-cord:{commit-sha}
```

**4D. Build UI** (Lines 175-203)
```
Source: ui/
Registry: us-central1-docker.pkg.dev
Image: sentry-ui:{commit-sha}

Special: Passes API_URL as build arg to frontend
  API_URL = $(running-sentry-api-url)/api
```

### Stage 5: Deploy Services

**5A. Deploy Data** (Lines 278-317)
```yaml
Service: sentry-data
Port: 8005
Memory: 1Gi
CPU: 1
Min instances: 1
Max instances: 1 (single instance, no scaling)

Environment:
  DEPLOYMENT_ENV: staging
```

**5B. Deploy CORD** (Lines 319-368)
```yaml
Service: sentry-cord-integration
Port: 8004
Memory: 2Gi
CPU: 2
Min instances: 1
Max instances: 1 (single instance)

Environment:
  CORD_DATA_DIR: /app/cord-data
  DATA_SERVICE_URL: $(sentry-data-url)
  DEPLOYMENT_ENV: staging

Depends on: Data service
```

**5C. Deploy API** (Lines 205-276)
```yaml
Service: sentry-api
Port: 8000
Memory: 2Gi
CPU: 2
Min instances: 1
Max instances: 10

Environment:
  API_MODE: live
  DEPLOYMENT_ENV: staging
  DATA_SERVICE_URL: $(sentry-data-url)
  CORD_SERVICE_URL: $(sentry-cord-url)
  VESSELAPI_KEY: $(secret)
  OFAC_API_KEY: $(secret)

Depends on: Data + CORD services
```

**5D. Deploy UI** (Lines 370-401)
```yaml
Service: sentry-ui
Port: 80
Memory: 512Mi
CPU: 1
Min instances: 0
Max instances: 10

Depends on: API being deployed
```

### Stage 6: Smoke Tests (Lines 403-440)
```yaml
Tests:
  1. API /health endpoint → curl -f {api}/health
  2. CORD /health endpoint → curl -f {cord}/health
  3. Service summary → list all 4 URLs
```

### Stage 7: Slack Notification (Lines 442-472)
```yaml
Sends deployment status to Slack webhook
Shows: Environment, branch, commit, result
```

---

## 📊 Service Dependencies

```
                   ┌────────────────┐
                   │    GCS Bucket  │
                   └────────────────┘
                          ↑
          ┌───────────────┼───────────────┐
          │               │               │
      sentry-data   sentry-cord      sentry-api
       (port 8005)   (port 8004)    (port 8000)
          │               │               │
          └───────────────┼───────────────┘
                          │
                      sentry-ui
                      (port 80)
                      
Data flow:
  UI → API (nginx proxy at /api)
  API → CORD (HTTP call to /api/cord/*)
  API → Data (HTTP call to DATA_SERVICE_URL)
  CORD → Data (reads from DATA_SERVICE_URL)
```

---

## ⚙️ Configuration (Environment Variables)

### Secrets (from GitHub)
```
GCP_PROJECT_ID          Required
GCP_SA_KEY              Required
VESSELAPI_KEY           Optional (API secret)
OFAC_API_KEY            Optional (API secret)
SLACK_WEBHOOK           Optional (Slack notifications)
```

### Environment
```
PROJECT_ID:  cbp-sentry (from secrets)
REGION:      us-central1 (hardcoded)
GAR_REPO:    cbp-sentry (hardcoded)
```

---

## 🚀 How to Trigger Deployment

### Automatic (on push to dev)
```bash
git checkout dev
git add .
git commit -m "feat: new feature"
git push origin dev

# Automatically triggers GitHub Actions
# Deploys to staging environment
```

### Manual (via workflow_dispatch)
```
In GitHub UI:
  1. Actions → Deploy — Sentry (Cloud Run)
  2. Run workflow
  3. Select environment: staging or production
  4. Click "Run workflow"
```

---

## 🔴 Current Issues

### Issue 1: Only Deploys to Staging
```
Problem: Environment is hardcoded to 'staging'
Line 39: echo "name=staging" >> $GITHUB_OUTPUT

Impact: Cannot deploy to production via GitHub Actions
Solution: Need to change environment logic based on branch
```

### Issue 2: Dev Branch for Development
```
Current: deploy.yml only triggers on 'dev' branch
Problem: Need separate workflow for 'stable' → production
Solution: Add branch condition or new workflow for stable
```

### Issue 3: Unnecessary sentry-data Service
```
Current: Deploys 4 services including sentry-data
Problem: User says only need 3 services
Question: Is sentry-data still needed?
         Or can API handle data directly?
```

### Issue 4: Build Requirements
```
Current: Requires both:
  - services/api/requirements.txt
  - services/data/requirements.txt

Problem: If removing sentry-data, need to remove its tests
Solution: Make data requirements.txt optional in tests
```

---

## 🎯 To Deploy Stable Version

### Option A: Use Existing Workflow (Recommended)
```
1. Create 'stable' branch from main:
   git checkout main
   git checkout -b stable
   git push -u origin stable

2. Modify deploy.yml to support stable branch:
   Change line 5: branches: [dev, stable]
   
   Add condition for stable:
   if: github.ref == 'refs/heads/stable'
     environment: production
   else
     environment: staging

3. Push change to deploy.yml and test on stable branch
```

### Option B: Create New Workflow (Cleaner)
```
Create: .github/workflows/deploy-stable.yml

Triggers: push to 'stable' branch
Environment: production (not staging)
Services: API, CORD, UI only (skip sentry-data)
```

---

## 📝 To Keep Only 3 Services (Remove sentry-data)

### Changes Needed

**1. Remove build-data job** (Lines 133-152)
```
Delete:
  build-data job completely
```

**2. Remove deploy-data job** (Lines 278-317)
```
Delete:
  deploy-data job completely
```

**3. Update deploy-cord dependencies**
```
Change Line 322:
  needs: [setup, build-cord, bootstrap-bucket, changes]
  
To:
  needs: [setup, build-cord, bootstrap-bucket, changes]
  (remove deploy-data dependency)
```

**4. Update deploy-api dependencies**
```
Change Line 208:
  needs: [setup, build-api, deploy-data, deploy-cord, changes]
  
To:
  needs: [setup, build-api, deploy-cord, changes]
  (remove deploy-data dependency)
```

**5. Remove DATA service references in deploy-api**
```
Delete Lines 220-230:
  (Wait for sentry-data health check)

Delete from deploy env vars (Lines 273):
  --set-env-vars DATA_SERVICE_URL=${{ steps.urls.outputs.data_url }}
```

**6. Update test requirements**
```
Change Lines 65-66 (install dependencies):
  
From:
  pip install -r services/api/requirements.txt
  pip install -r services/data/requirements.txt

To:
  pip install -r services/api/requirements.txt
  # data service removed
```

**7. Update smoke tests**
```
Remove CORD health check (Lines 422-426) if not needed
Or keep it - it's good to have
```

---

## ✅ Recommended Action Plan

### Step 1: Understand Current State
- ✅ You now understand the workflow
- Services: API, Data, CORD, UI (4 total)
- Deploys to staging on dev branch push
- Manual trigger available

### Step 2: Remove sentry-data (If Not Needed)
```bash
# In deploy.yml, remove:
#   - build-data job
#   - deploy-data job
#   - references to DATA_SERVICE_URL in API deploy
#   - data requirements from test job

# Save and test workflow on dev branch
```

### Step 3: Set Up Stable Branch
```bash
git checkout main
git pull
git checkout -b stable
git push -u origin stable
```

### Step 4: Update Workflow for Stable
```yaml
# Option A: Add stable branch to existing deploy.yml
on:
  push:
    branches: [dev, stable]

# Option B: Create new deploy-production.yml
# (triggers on stable only, environment=production)
```

### Step 5: Deploy Stable Version
```bash
# When ready to deploy:
git checkout stable
# Make sure all code is ready
git push origin stable

# GitHub Actions automatically deploys to production
```

---

## 📋 Summary

| Item | Status |
|------|--------|
| **Workflow Exists** | ✅ Yes (.github/workflows/deploy.yml) |
| **Triggers on Push** | ✅ Yes (dev branch) |
| **Manual Trigger** | ✅ Yes (workflow_dispatch) |
| **Tests Run** | ✅ Yes (pytest + TypeScript) |
| **Builds Docker Images** | ✅ Yes (4 services) |
| **Deploys to Cloud Run** | ✅ Yes (staging) |
| **Health Checks** | ✅ Yes (smoke tests) |
| **Supports Production** | ❌ No (hardcoded to staging) |
| **3 Services Only** | ⚠️ Currently 4 (sentry-data exists) |

---

## 🚀 Next Steps

1. **Confirm you want to remove sentry-data** (or keep it)
2. **Modify deploy.yml** to support stable branch
3. **Create stable branch** from main
4. **Test deployment** to staging from dev
5. **Verify production deployment** from stable

Ready to proceed?

