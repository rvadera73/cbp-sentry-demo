# CBP Sentry Deployment Guide

**Date:** May 26, 2026  
**Purpose:** Guide for deploying stable versions and managing GitHub Actions CI/CD

---

## 🎯 Deployment Strategy

```
┌─────────────────────────────────────────────────────────┐
│                   Branch Strategy                        │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  main              ← Stable, tested, ready for review   │
│   ↓                                                      │
│  stable            ← Production deployments              │
│   ↓                                                      │
│  (auto-deploy)  → Cloud Run Staging                     │
│                 → Health Checks                         │
│                 → Manual approval → Production          │
│                                                          │
│  dev               ← Development, new features          │
│   ↓                                                      │
│  (manual deploy) → Local testing only                   │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

---

## 📋 Workflow Overview

### GitHub Actions Pipeline (`.github/workflows/deploy-stable.yml`)

```
Stage 1: Build & Test
  ├─ Python tests (backend)
  ├─ Node tests (frontend)
  └─ Build artifacts

Stage 2: Build Docker Images
  ├─ API image → GCR
  └─ UI image → GCR

Stage 3: Deploy to Staging
  ├─ Deploy API to Cloud Run (sentry-api-staging)
  └─ Deploy UI to Cloud Run (sentry-ui-staging)

Stage 4: Health Checks
  ├─ Check API /health endpoint
  └─ Check UI home page

Stage 5: Deploy to Production (If stable branch)
  ├─ Deploy API to Cloud Run (sentry-api)
  └─ Deploy UI to Cloud Run (sentry-ui)

Stage 6: Notify
  └─ Summary & next steps
```

---

## 🚀 Getting Started

### Step 1: Set Up GitHub Secrets

Add these secrets to your GitHub repository (`Settings → Secrets → Actions`):

```
GCP_PROJECT_ID          → Your GCP project ID (e.g., cbp-sentry)
GCP_SA_KEY              → Service Account JSON key (base64 encoded)
```

**How to get GCP_SA_KEY:**
```bash
# 1. Create service account in GCP Console
# 2. Generate JSON key
# 3. Encode and add to GitHub Secrets:

cat service-account-key.json | base64 -w 0 | xclip -selection clipboard
# Paste into GitHub Secrets as GCP_SA_KEY
```

### Step 2: Create the Stable Branch

```bash
# Create stable branch from main
git checkout main
git pull origin main
git checkout -b stable
git push -u origin stable

# From now on:
# - main: stable, tested code
# - stable: production-ready code (triggers auto-deploy)
# - dev: new features & development
```

### Step 3: Set Branch Protection Rules

In GitHub: `Settings → Branches → Add Rule`

```
Branch name pattern: stable

Require status checks to pass:
  ✅ build-and-test
  ✅ build-docker
  ✅ deploy-staging
  ✅ health-check

Require code reviews: 1
Dismiss stale reviews: Yes
```

---

## 📖 How to Deploy

### Deployment Scenario 1: New Feature Ready (dev → main → stable)

```bash
# 1. On dev branch, finish feature
git checkout dev
git add .
git commit -m "feat: new feature description"
git push origin dev

# 2. Create Pull Request: dev → main
# In GitHub UI:
#   - Create PR from dev to main
#   - Add description
#   - Request review
#   - Merge when approved

# 3. Once merged to main, create PR: main → stable
# In GitHub UI:
#   - Create PR from main to stable
#   - GitHub Actions starts automatically
#   - Stages 1-4 run (build, test, staging deploy)
#   - Verify staging at: https://sentry-ui-staging-*.run.app
#   - If good, merge to stable → auto-deploys to production!

# 4. Verify production deployment
#   - Check: https://console.cloud.google.com/run
#   - View logs in Cloud Run
```

### Deployment Scenario 2: Fix Production Bug (hotfix)

```bash
# 1. Create hotfix from main
git checkout main
git pull origin main
git checkout -b hotfix/critical-bug

# 2. Make fix
git add .
git commit -m "fix: critical bug description"

# 3. Create PR: hotfix/critical-bug → main
#   - Fast-track review (critical bug)
#   - Merge to main when approved

# 4. Create PR: main → stable
#   - This triggers auto-deployment
#   - No additional approval needed (already in main)

# 5. Once stable is deployed, delete hotfix branch
git checkout main
git pull origin main
git branch -D hotfix/critical-bug
git push origin --delete hotfix/critical-bug
```

### Deployment Scenario 3: Manual Trigger

If you need to re-deploy without code changes:

```
In GitHub UI:
  1. Go to: Actions → Deploy Stable
  2. Click: "Run workflow"
  3. Select branch: stable
  4. Click: "Run workflow"
  
This re-runs the entire pipeline without a new commit.
```

---

## 📊 Branch Responsibilities

### `main` Branch
```
Purpose:           Stable, reviewed, tested code
Protected:         Yes (require PR reviews)
Auto-deployment:   No
Merge from:        dev (via PR)
Merge to:          stable (via PR)
Deployment:        N/A (staging via stable branch)

Commit message:
  feat: New feature description
  fix: Bug fix description
  docs: Documentation update
```

### `stable` Branch
```
Purpose:           Production-ready, auto-deploying
Protected:         Yes (require status checks)
Auto-deployment:   Yes (GitHub Actions)
Merge from:        main (via PR)
Merge to:          N/A
Deployment:        → Cloud Run Staging → Production

Workflow:
  1. Code merged to stable
  2. Tests run automatically
  3. Staging deployment
  4. Health checks
  5. Production deployment (if stable branch)
  6. Notification
```

### `dev` Branch
```
Purpose:           Development, experiments, new features
Protected:         No
Auto-deployment:   No
Merge from:        feature/* branches
Merge to:          main (via PR)
Deployment:        Local docker-compose only

Workflow:
  1. Work on feature branches
  2. Test locally with docker-compose
  3. Create PR to dev
  4. When ready, create PR from dev → main
```

---

## 🔍 Monitoring Deployments

### View GitHub Actions Logs

```
GitHub UI:
  1. Actions tab
  2. Select "Deploy Stable" workflow
  3. Click latest run
  4. View logs for each stage
```

### View Cloud Run Logs

```bash
# API logs
gcloud run logs read sentry-api --limit 50

# UI logs
gcloud run logs read sentry-ui --limit 50

# Staging logs
gcloud run logs read sentry-api-staging --limit 50
gcloud run logs read sentry-ui-staging --limit 50
```

### Check Deployment Status

```bash
# API status
gcloud run services describe sentry-api --region us-central1

# UI status
gcloud run services describe sentry-ui --region us-central1

# Get URLs
gcloud run services describe sentry-api --region us-central1 --format='value(status.url)'
gcloud run services describe sentry-ui --region us-central1 --format='value(status.url)'
```

---

## ⚠️ Troubleshooting

### Issue: Build fails with "Python dependencies not found"

**Solution:**
```bash
# Create requirements.txt in root
pip freeze > requirements.txt
git add requirements.txt
git commit -m "add: python requirements"
git push
```

### Issue: Docker build fails

**Solution:**
```bash
# Check Dockerfile syntax
docker build -f services/api/Dockerfile ./services/api

# View errors and fix
# Commit and push to trigger new build
```

### Issue: Health check fails

**Cause:** Service takes too long to start, or /health endpoint is broken

**Solution:**
```bash
# Increase timeout in deploy-stable.yml (line 170-180)
# OR fix health endpoint in services/api/main.py

# Check health endpoint:
curl https://sentry-api-staging-*.run.app/health

# If 404, add health endpoint to services/api/main.py
@app.get("/health")
async def health():
    return {"status": "ok"}
```

### Issue: Staging deploys but production doesn't

**Cause:** Branch protection rule or status check failure

**Solution:**
```bash
# Check branch protection rules
# GitHub Settings → Branches → stable

# Verify all checks passed in Actions tab
# Re-run failed checks or merge again
```

### Issue: Need to rollback production

**Solution:**
```bash
# Option 1: Revert in stable branch
git checkout stable
git revert <commit-hash>
git push origin stable
# This triggers auto-deploy with old version

# Option 2: Redeploy previous tag
gcloud run deploy sentry-api \
  --image gcr.io/{project}/sentry-api:previous-tag \
  --region us-central1
```

---

## 📋 Pre-Deployment Checklist

Before merging to `stable`, ensure:

```
Code Quality:
  ☐ All tests passing locally (npm test, pytest)
  ☐ No console errors
  ☐ No TypeScript errors
  ☐ Code reviewed and approved

Functionality:
  ☐ Feature works as designed
  ☐ No regressions
  ☐ API endpoints respond correctly
  ☐ UI pages load correctly

Documentation:
  ☐ Code comments added where needed
  ☐ README updated (if needed)
  ☐ Commit messages are clear
  ☐ CHANGELOG.md updated (optional)

Environment:
  ☐ Database migrations tested
  ☐ API keys/secrets are env vars (not hardcoded)
  ☐ No sensitive data in code
  ☐ Docker images build successfully
```

---

## 🔐 Security Best Practices

### Secrets Management

```
✅ DO:
  • Store API keys in GitHub Secrets
  • Use environment variables in Cloud Run
  • Rotate credentials regularly
  • Enable secret masking in logs

❌ DON'T:
  • Commit .env files
  • Hardcode API keys in code
  • Log sensitive data
  • Store secrets in Docker images
```

### Branch Protection

```
Stable branch requires:
  ✅ Status checks pass
  ✅ Code review (1 approver)
  ✅ Up to date with base branch
  ✅ No stale reviews
```

---

## 📈 Deployment Timeline

### Normal Deployment (dev feature to production)
```
Timeline: ~45-60 minutes

Step 1: Create PR (dev → main)           2 min
Step 2: Code review & approval            5-30 min
Step 3: Merge to main                     1 min
Step 4: Create PR (main → stable)         2 min
Step 5: GitHub Actions runs:
  - Build & test                          10 min
  - Build Docker images                   10 min
  - Deploy to staging                     5 min
  - Health checks                         2 min
  - Deploy to production                  5 min
Step 6: Verify production                 5 min

Total: 30-60 minutes
```

### Hotfix Deployment (critical bug)
```
Timeline: ~30-45 minutes (with expedited review)

Step 1: Create & fix hotfix branch        3 min
Step 2: Fast-track review                 5-10 min
Step 3: Merge to main & stable            2 min
Step 4: Auto-deploy via GitHub Actions    25 min

Total: 30-40 minutes
```

---

## ✅ Summary

| Item | Status |
|------|--------|
| **GitHub Actions Workflow** | ✅ Created (.github/workflows/deploy-stable.yml) |
| **Staging Deployment** | ✅ Auto on merge to stable |
| **Production Deployment** | ✅ Auto on stable branch merge |
| **Health Checks** | ✅ Automated |
| **Branch Protection** | ⚠️  Need to set up (see Step 3) |
| **Secrets** | ⚠️  Need to add GCP_SA_KEY (see Step 1) |
| **Docker Images** | ✅ Auto-built by GitHub Actions |
| **Monitoring** | ✅ Via Cloud Run & GitHub Actions |

---

## 🚀 Next Steps

1. **Create stable branch** (see Step 2)
2. **Add GitHub Secrets** (see Step 1)
3. **Set branch protection** (see Step 3)
4. **Test deployment** by merging a change to stable
5. **Verify staging** & production URLs
6. **Continue dev work** on dev branch

