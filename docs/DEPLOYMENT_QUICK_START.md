# Deployment Quick Start — Using "Deploy — Sentry (Cloud Run)"

**Workflow Name:** "Deploy — Sentry (Cloud Run)"  
**File:** `.github/workflows/deploy.yml`  
**Status:** Ready to use

---

## 🎯 What You Want To Do

1. **Deploy a stable version** that's tested and ready
2. **Use 3 services only** (api, cord, ui - no data service)
3. **Keep dev branch** for ongoing development
4. **Use existing GitHub Actions** (no new workflows)

---

## ✅ 3-Step Plan

### STEP 1: Modify Existing Workflow (5 minutes)

**File:** `.github/workflows/deploy.yml`

**Edit 1 - Support stable branch** (Line 5)
```yaml
on:
  push:
    branches: [dev, stable]  # ← Add 'stable' here
  pull_request:
    branches: [dev]
  workflow_dispatch:
    inputs:
      environment:
        description: Deployment environment
        required: false
        default: staging
        type: choice
        options:
          - staging
          - production
```

**Edit 2 - Detect branch automatically** (Lines 31-39)
```yaml
setup:
  runs-on: ubuntu-latest
  outputs:
    branch: ${{ steps.branch.outputs.name }}
    environment: ${{ steps.env.outputs.name }}
  steps:
    - name: Determine branch and environment
      id: branch
      run: |
        if [[ "${{ github.ref }}" == "refs/heads/stable" ]]; then
          echo "name=stable" >> $GITHUB_OUTPUT
        else
          echo "name=dev" >> $GITHUB_OUTPUT
        fi

    - name: Set environment
      id: env
      run: |
        if [[ "${{ github.ref }}" == "refs/heads/stable" ]]; then
          echo "name=production" >> $GITHUB_OUTPUT
        else
          echo "name=staging" >> $GITHUB_OUTPUT
        fi
```

**Edit 3 - Remove sentry-data service**

Delete these complete sections:

a. Remove "build-data" job (lines 133-152)
   ```
   Delete the entire job starting with:
   build-data:
     name: Build sentry-data
   ```

b. Remove "deploy-data" job (lines 278-317)
   ```
   Delete the entire job starting with:
   deploy-data:
     name: Deploy sentry-data
   ```

c. Update "deploy-api" dependencies (line 208)
   ```yaml
   BEFORE:
   needs: [setup, build-api, deploy-data, deploy-cord, changes]
   
   AFTER:
   needs: [setup, build-api, deploy-cord, changes]
   ```

d. Update "deploy-api" health checks (lines 220-240)
   ```yaml
   BEFORE:
   - name: Wait for dependencies to be healthy
     run: |
       echo "Waiting for sentry-data to be healthy..."
       for i in {1..30}; do
         if curl -sf https://$(gcloud run services describe sentry-data --region ${{ env.REGION }} --format 'value(status.url)' | sed 's|https://||')/health > /dev/null 2>&1; then
           echo "✅ sentry-data is healthy"
           break
         fi
         echo "Attempt $i/30: sentry-data not ready yet, waiting 5s..."
         sleep 5
       done

       echo "Waiting for sentry-cord-integration to be healthy..."
       ...
   
   AFTER:
   - name: Wait for dependencies to be healthy
     run: |
       echo "Waiting for sentry-cord-integration to be healthy..."
       for i in {1..30}; do
         if curl -sf https://$(gcloud run services describe sentry-cord-integration --region ${{ env.REGION }} --format 'value(status.url)' | sed 's|https://||')/health > /dev/null 2>&1; then
           echo "✅ sentry-cord-integration is healthy"
           break
         fi
         echo "Attempt $i/30: sentry-cord-integration not ready yet, waiting 5s..."
         sleep 5
       done
   ```

e. Remove DATA_URL reference (line 273)
   ```yaml
   BEFORE:
   --set-env-vars API_MODE=live \
   --set-env-vars DEPLOYMENT_ENV=${{ needs.setup.outputs.environment }} \
   --set-env-vars DATA_SERVICE_URL=${{ steps.urls.outputs.data_url }} \
   --set-env-vars CORD_SERVICE_URL=${{ steps.urls.outputs.cord_url }} \
   
   AFTER:
   --set-env-vars API_MODE=live \
   --set-env-vars DEPLOYMENT_ENV=${{ needs.setup.outputs.environment }} \
   --set-env-vars CORD_SERVICE_URL=${{ steps.urls.outputs.cord_url }} \
   ```

f. Remove DATA output from deploy-api (lines 244-250)
   ```yaml
   BEFORE:
   - name: Resolve service URLs
     id: urls
     run: |
       DATA_URL=$(gcloud run services describe sentry-data --region ${{ env.REGION }} --format 'value(status.url)')
       CORD_URL=$(gcloud run services describe sentry-cord-integration --region ${{ env.REGION }} --format 'value(status.url)')
       echo "data_url=${DATA_URL}" >> $GITHUB_OUTPUT
       echo "cord_url=${CORD_URL}" >> $GITHUB_OUTPUT
       echo "Resolved URLs:"
       echo "  Data: ${DATA_URL}"
       echo "  CORD: ${CORD_URL}"
   
   AFTER:
   - name: Resolve service URLs
     id: urls
     run: |
       CORD_URL=$(gcloud run services describe sentry-cord-integration --region ${{ env.REGION }} --format 'value(status.url)')
       echo "cord_url=${CORD_URL}" >> $GITHUB_OUTPUT
       echo "Resolved URLs:"
       echo "  CORD: ${CORD_URL}"
   ```

g. Update test job (lines 64-71)
   ```yaml
   BEFORE:
   - name: Install dependencies
     run: |
       python -m pip install --upgrade pip pytest
       pip install -r services/api/requirements.txt
       pip install -r services/data/requirements.txt

   - name: Run pytest
     run: |
       pytest services/api/tests -v --tb=short || true
       pytest services/data/tests -v --tb=short || true
   
   AFTER:
   - name: Install dependencies
     run: |
       python -m pip install --upgrade pip pytest
       pip install -r services/api/requirements.txt

   - name: Run pytest
     run: |
       pytest services/api/tests -v --tb=short || true
   ```

---

### STEP 2: Create Stable Branch

```bash
cd /home/rahulvadera/cbp-sentry

# Switch to main
git checkout main
git pull origin main

# Create stable branch
git checkout -b stable

# Push to remote
git push -u origin stable

# Verify
git branch -a | grep stable
```

---

### STEP 3: Test & Deploy

#### Test Staging (dev branch)
```bash
git checkout dev
echo "test" >> TEMP_TEST.txt
git add TEMP_TEST.txt
git commit -m "test: trigger staging deployment"
git push origin dev

# Watch GitHub Actions:
# → GitHub → Actions → "Deploy — Sentry (Cloud Run)"
# → Should show: environment = staging
# → After ~20 min, deployment complete
# → Check services at Cloud Run dashboard
```

#### Deploy Production (stable branch)
```bash
git checkout stable
git pull origin main
git push origin stable

# Watch GitHub Actions:
# → Should show: environment = production
# → After ~20 min, deployment complete
# → Services live at production URLs
```

---

## 📊 Result After Changes

**When you push to:**

| Branch | Environment | Services | Deployed To |
|--------|-------------|----------|-------------|
| `dev` | staging | api, cord, ui | Staging servers |
| `stable` | production | api, cord, ui | Production servers |

**Services Deployed (3 only):**
1. sentry-api (port 8000)
2. sentry-cord-integration (port 8004)
3. sentry-ui (port 80)

**No sentry-data service** ✅

---

## 🔍 Verify Deployment

### Check in GitHub Actions
```
Actions tab → "Deploy — Sentry (Cloud Run)" → Latest run
Should show all green checkmarks:
  ✅ setup
  ✅ test
  ✅ build-api
  ✅ build-cord
  ✅ build-ui
  ✅ deploy-api
  ✅ deploy-cord
  ✅ deploy-ui
  ✅ smoke-tests
  ✅ notify
```

### Check in GCP Cloud Run
```
Google Cloud Console → Cloud Run

Staging (dev branch):
  - sentry-api (staging)
  - sentry-cord-integration (staging)
  - sentry-ui (staging)

Production (stable branch):
  - sentry-api
  - sentry-cord-integration
  - sentry-ui
```

### Check URLs
```bash
# Get URLs from Cloud Run console or:
gcloud run services list --region us-central1

# Test API
curl https://sentry-api.run.app/health

# Test UI
curl https://sentry-ui.run.app

# Test CORD
curl https://sentry-cord-integration.run.app/health
```

---

## 📋 Deployment Checklist

Before editing deploy.yml:
- [ ] You've read and understand the workflow
- [ ] You confirm removing sentry-data is OK
- [ ] You have GCP_SA_KEY secret configured

Making changes:
- [ ] Edit deploy.yml with 7 changes listed above
- [ ] Commit: `git add .github/workflows/deploy.yml && git commit -m "chore: update deploy workflow for stable+prod"`
- [ ] Push to dev: `git push origin dev`

After changes:
- [ ] Create stable branch from main
- [ ] Test on dev (should deploy to staging)
- [ ] Push to stable (should deploy to production)
- [ ] Verify both deployments in GitHub Actions
- [ ] Verify services at Cloud Run dashboard
- [ ] Continue development on /dev branch

---

## 💡 Day-to-Day Usage

**For Development:**
```bash
# Work on feature branch
git checkout -b feature/my-feature
# ... make changes ...
git commit -m "feat: my feature"

# Push to dev when ready to test
git push origin feature/my-feature
git checkout dev
git merge feature/my-feature
git push origin dev

# GitHub Actions auto-deploys to staging
# Test at https://sentry-ui-staging.run.app (or same URL if single instance)
```

**For Production Release:**
```bash
# When ready to release to production
git checkout stable
git pull origin main  # or merge from dev
git push origin stable

# GitHub Actions auto-deploys to production
# Live at https://sentry-ui.run.app
```

---

## ⚠️ Important

- **Only 3 services** will be deployed (api, cord, ui)
- **sentry-data removed** - ensure API doesn't depend on it
- **Environment variable** set automatically (staging vs production)
- **Workflow name** remains: "Deploy — Sentry (Cloud Run)"
- **No new files** - modifying existing deploy.yml only

Ready to proceed?

