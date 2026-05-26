# Deployment Action Plan — Using Existing Workflow

**Date:** May 26, 2026  
**Approach:** Modify existing `deploy.yml` (no new workflows)  
**Goal:** Deploy stable version + continue dev work

---

## 🎯 Current Situation

### Existing Workflow: `deploy.yml`
```
Triggers: Push to 'dev' branch
Deploys to: Staging environment
Services: 4 (api, data, cord, ui)
```

### What You Want
```
1. Deploy stable version from main/stable branch
2. Keep only 3 services (remove sentry-data)
3. Continue development on /dev branch
```

---

## 📋 Action Plan (3 Steps)

### STEP 1: Modify deploy.yml to Support Stable Branch

**File:** `.github/workflows/deploy.yml`

**Change 1: Add stable branch to trigger** (Line 5)
```yaml
# BEFORE:
on:
  push:
    branches: [dev]

# AFTER:
on:
  push:
    branches: [dev, stable]
```

**Change 2: Update setup job to detect branch** (Lines 25-39)
```yaml
# BEFORE:
setup:
  runs-on: ubuntu-latest
  outputs:
    branch: ${{ steps.branch.outputs.name }}
    environment: ${{ steps.env.outputs.name }}
  steps:
    - name: Determine branch and environment
      id: branch
      run: |
        echo "name=dev" >> $GITHUB_OUTPUT

    - name: Set environment
      id: env
      run: |
        echo "name=staging" >> $GITHUB_OUTPUT

# AFTER:
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

**Change 3: Remove sentry-data service** (Optional - if you only need 3 services)

Remove these sections from deploy.yml:

1. **Remove build-data job** (Lines 133-152)
   ```
   Delete entire "build-data" job
   ```

2. **Remove deploy-data job** (Lines 278-317)
   ```
   Delete entire "deploy-data" job
   ```

3. **Update deploy-cord needs** (Line 322)
   ```yaml
   # BEFORE:
   needs: [setup, build-cord, bootstrap-bucket, changes]
   
   # AFTER (unchanged - no changes needed)
   needs: [setup, build-cord, bootstrap-bucket, changes]
   ```

4. **Update deploy-api needs** (Line 208)
   ```yaml
   # BEFORE:
   needs: [setup, build-api, deploy-data, deploy-cord, changes]
   
   # AFTER:
   needs: [setup, build-api, deploy-cord, changes]
   ```

5. **Update deploy-api health check** (Lines 220-230)
   ```yaml
   # BEFORE:
   - name: Wait for dependencies to be healthy
     run: |
       echo "Waiting for sentry-data to be healthy..."
       # ... sentry-data check code ...
       
       echo "Waiting for sentry-cord-integration to be healthy..."
       # ... sentry-cord check code ...
   
   # AFTER:
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

6. **Remove DATA_URL from deploy-api** (Line 273)
   ```yaml
   # BEFORE:
   --set-env-vars DATA_SERVICE_URL=${{ steps.urls.outputs.data_url }} \
   
   # DELETE this line
   ```

7. **Remove data-url output** (Line 244-250)
   ```yaml
   # BEFORE:
   - name: Resolve service URLs
     id: urls
     run: |
       DATA_URL=$(gcloud run services describe sentry-data ...)
       CORD_URL=$(gcloud run services describe sentry-cord-integration ...)
       echo "data_url=${DATA_URL}" >> $GITHUB_OUTPUT
       ...
   
   # AFTER:
   - name: Resolve service URLs
     id: urls
     run: |
       CORD_URL=$(gcloud run services describe sentry-cord-integration --region ${{ env.REGION }} --format 'value(status.url)')
       echo "cord_url=${CORD_URL}" >> $GITHUB_OUTPUT
       echo "Resolved URLs:"
       echo "  CORD: ${CORD_URL}"
   ```

8. **Update test job** (Lines 65-66)
   ```yaml
   # BEFORE:
   - name: Install dependencies
     run: |
       python -m pip install --upgrade pip pytest
       pip install -r services/api/requirements.txt
       pip install -r services/data/requirements.txt
   
   # AFTER:
   - name: Install dependencies
     run: |
       python -m pip install --upgrade pip pytest
       pip install -r services/api/requirements.txt
   ```

   ```yaml
   # BEFORE:
   - name: Run pytest
     run: |
       pytest services/api/tests -v --tb=short || true
       pytest services/data/tests -v --tb=short || true
   
   # AFTER:
   - name: Run pytest
     run: |
       pytest services/api/tests -v --tb=short || true
   ```

---

### STEP 2: Create Stable Branch

```bash
cd /home/rahulvadera/cbp-sentry

# Ensure on main branch
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

### STEP 3: Test Deployment

#### Test on Dev (Staging)
```bash
# Make a test change on dev branch
git checkout dev
echo "# Test" >> TEST_FILE.md
git add TEST_FILE.md
git commit -m "test: trigger deployment to staging"
git push origin dev

# Watch GitHub Actions:
#   GitHub → Actions → Deploy — Sentry (Cloud Run)
#   Should deploy to staging environment
#   Check service URLs when complete
```

#### Promote to Stable (Production)
```bash
# When ready to go to production:
git checkout stable
git pull origin main  # or merge from dev
git push origin stable

# Watch GitHub Actions:
#   Should deploy to production environment
#   Services: sentry-api, sentry-cord-integration, sentry-ui
#   NO sentry-data
```

---

## 📊 Deployment Flow After Changes

```
Development:
  Feature branch → Push to dev → Auto-deploy to STAGING
  Test & verify at: https://sentry-ui-staging.run.app

Production:
  Code ready → Merge to stable → Auto-deploy to PRODUCTION
  Access at: https://sentry-ui.run.app

Workflow Decision Tree:
  
  Push to dev?        → Deploy to staging
                        Environment: staging
                        Services: api, cord, ui (3 services)
  
  Push to stable?     → Deploy to production
                        Environment: production
                        Services: api, cord, ui (3 services)
```

---

## ✅ Checklist

Before You Start:

- [ ] You understand the existing deploy.yml workflow
- [ ] You know where to make changes (lines listed above)
- [ ] You confirm you want to remove sentry-data (3 services only)
- [ ] You're ready to create stable branch from main

After Making Changes:

- [ ] Edit deploy.yml with the 8 changes listed above
- [ ] Commit: `git commit -m "chore: update deploy workflow for stable/production"`
- [ ] Push to dev: `git push origin dev`
- [ ] Verify workflow still works on dev (deploys to staging)
- [ ] Create stable branch from main
- [ ] Push to stable: trigger production deployment

Verify Deployment:

- [ ] Check GitHub Actions logs (no errors)
- [ ] Verify staging deployment works (push to dev)
- [ ] Verify production deployment works (push to stable)
- [ ] Test service URLs are accessible
- [ ] Confirm only 3 services deployed (no sentry-data)

---

## 🔗 Service URLs After Deployment

**Staging** (from dev push):
```
UI:  https://sentry-ui-staging.run.app (if separate instance exists)
API: https://sentry-api-staging.run.app (if separate instance exists)

OR (same instance):
UI:  https://sentry-ui.run.app
API: https://sentry-api.run.app
```

**Production** (from stable push):
```
UI:  https://sentry-ui.run.app
API: https://sentry-api.run.app
CORD: https://sentry-cord-integration.run.app
```

---

## ⚠️ Important Notes

1. **Staging vs Production Environment Variable**
   - If deploy.yml checks `DEPLOYMENT_ENV`, it will now correctly set to:
     - "staging" for dev branch
     - "production" for stable branch
   - Services can use this to behave differently

2. **Breaking Change: Removing sentry-data**
   - If services depend on sentry-data, this will break
   - Verify API can run without sentry-data service
   - Check if DATA_SERVICE_URL is optional in code

3. **GitHub Secrets Still Required**
   ```
   GCP_PROJECT_ID
   GCP_SA_KEY
   VESSELAPI_KEY (optional)
   OFAC_API_KEY (optional)
   SLACK_WEBHOOK (optional)
   ```

4. **Slack Notification**
   - Still sends deployment status
   - You can disable by removing notify job (lines 442-472)

---

## 📞 When Issues Occur

### "Workflow failed" on stable push
```
Check:
  1. GitHub Actions logs (what step failed?)
  2. GCP permissions (service account)
  3. Docker image issues (check Artifact Registry)
  4. Service health checks (timeout?)
```

### "sentry-data service not found"
```
This is expected! We removed it.
Check API logs to ensure it doesn't need sentry-data.
```

### "API can't reach CORD"
```
Check:
  1. CORD service deployed successfully
  2. CORD_SERVICE_URL env var is set correctly
  3. API → CORD network connectivity
  4. Health check passed before API deployment
```

---

## 🚀 Summary

| Step | Action | Status |
|------|--------|--------|
| 1 | Edit deploy.yml (8 changes) | Ready |
| 2 | Create stable branch | Ready |
| 3 | Test on dev (staging) | Ready |
| 4 | Test on stable (production) | Ready |
| 5 | Continue dev work on /dev | Ready |

All using **existing workflow** (no new files needed!)

