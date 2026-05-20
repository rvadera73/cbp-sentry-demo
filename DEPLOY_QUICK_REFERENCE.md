# CBP Sentry Deployment — Quick Reference

**Simplified approach using service account JSON key (like IACP-2.1)**

## 20-Minute Checklist

### ✅ Step 1: Have These Ready
- ✅ Neon database URL: `postgresql://neondb_owner:npg_MsWUixB5V0yS@ep-square-art-apa1gid4-pooler.c-7.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require`
- ✅ GCP Project: `cbp-sentry`

---

### ⏳ Step 2: Create Service Account & Download Key (10 min)

Open: **https://console.cloud.google.com**  
Project: **cbp-sentry**

#### 2a. Create Service Account
**IAM & Admin** → **Service Accounts** → **Create Service Account**
- Name: `sentry-deploy`
- Click **Create and Continue**

#### 2b. Grant Roles
- `Cloud Run Admin`
- `Artifact Registry Admin`
- `Service Account User`
- Click **Continue** → **Done**

#### 2c. Download JSON Key
- Back in **Service Accounts**, click `sentry-deploy`
- **Keys** tab → **Add Key** → **Create new key**
- Format: **JSON**
- Click **Create**
- Browser downloads: `sentry-deploy-xxxxx.json`
- **SAVE THIS FILE** (you'll paste its contents)

#### 2d. Create Artifact Registry
**Artifact Registry** → **Create Repository**
- Name: `cbp-sentry`
- Format: Docker
- Region: us-central1

#### 2e. Enable APIs
**APIs & Services** → **Enable APIs and Services**
- Cloud Run Admin API
- Artifact Registry API
- Service Account User API

---

### ✅ Step 3: Add GitHub Secrets (5 min)

**https://github.com/rahulvadera/cbp-sentry/settings/secrets/actions**

#### Secret 1: GCP_PROJECT_ID
- Name: `GCP_PROJECT_ID`
- Value: `cbp-sentry`

#### Secret 2: GCP_SA_KEY
- Name: `GCP_SA_KEY`
- Value: **Open the JSON key file** (`sentry-deploy-xxxxx.json`)
  - Copy ALL contents (entire JSON object)
  - Paste into Secret field

#### Secret 3: DATABASE_URL
- Name: `DATABASE_URL`
- Value: `postgresql://neondb_owner:npg_MsWUixB5V0yS@ep-square-art-apa1gid4-pooler.c-7.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require`

#### Secret 4 & 5: API Keys (placeholders)
- Name: `VESSELAPI_KEY` | Value: `placeholder-key`
- Name: `OFAC_API_KEY` | Value: `placeholder-key`

---

### ✅ Step 4: Deploy (5 minutes)

```bash
cd ~/cbp-sentry
git status      # Verify all changes committed
git push origin dev
```

**Monitor**: https://github.com/rahulvadera/cbp-sentry/actions

**What happens automatically:**
1. GitHub Actions reads GCP_SA_KEY
2. Authenticates to GCP
3. Builds 3 Docker images (api, data, ui)
4. Pushes to Artifact Registry
5. Deploys to Cloud Run
6. Smoke tests run
7. Done ✅

---

### ✅ Step 5: Verify (5 minutes)

After GitHub Actions completes (green checkmark):

```bash
# Check services running
gcloud run services list --project cbp-sentry --region us-central1

# Test API
curl https://sentry-api-cbp-sentry.run.app/health

# Open UI
open https://sentry-ui-cbp-sentry.run.app
```

---

## Timeline

| Time | Step |
|---|---|
| Now | Read this guide |
| +10 min | Finish Step 2 (service account + JSON key) |
| +15 min | Add 5 GitHub Secrets |
| +20 min | `git push origin dev` |
| +25 min | GitHub Actions builds & deploys (auto) |
| +30 min | ✅ Live on Cloud Run |

**Total: 30 minutes**

---

## Differences from Prior Version

| Item | Old | New |
|---|---|---|
| Auth | Workload Identity OIDC | Service account JSON key |
| Setup | Complex bootstrap script | Simple: create SA + download key |
| Secrets | 6 secrets including provider URL | 5 simple secrets |
| Complexity | High | Low (like IACP-2.1) |

This approach matches IACP-2.1's proven pattern and is simpler to understand.
