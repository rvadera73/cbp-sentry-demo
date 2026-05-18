# Sentry CBP MVP — Customer Setup Guide

## Overview

This guide walks you through the **manual setup steps** required to activate GitHub Actions CI/CD for the Sentry CBP project. All code, workflows, and configurations are ready — this guide covers the infrastructure permissions and secrets needed to run them.

**Estimated time:** 20–30 minutes  
**Difficulty:** Intermediate (copy-paste commands + GitHub UI navigation)  
**Prerequisite:** GitHub repository admin access

---

## Step 1: Enable GitHub Actions

### 1.1 Navigate to Actions Settings

1. Go to your repository: https://github.com/rvadera73/cbp-sentry-demo
2. Click **Settings** (top right)
3. In the left sidebar, click **Actions** → **General**
4. Under "Actions permissions," select **Allow all actions and reusable workflows**
5. Click **Save**

### 1.2 Verify Workflow Files

All workflow files are ready in `.github/workflows/`:
- `test.yml` — Runs pytest + vitest on every PR
- `a11y.yml` — WCAG 2.0 AA accessibility checks
- `lint.yml` — Python + TypeScript linting
- `security.yml` — Dependency audit + CodeQL
- `deploy-gcp.yml` — Deploy to Cloud Run (requires GCP setup below)
- `deploy-aws.yml` — Deploy to Lambda/ECS (optional template)

---

## Step 2: Branch Protection Rules (Enforce Code Quality)

### 2.1 Protect Main Branch

1. Go to **Settings** → **Branches** (left sidebar)
2. Click **Add rule**
3. Fill in the form:
   - **Branch name pattern:** `main`
   - Check ✅ **Require a pull request before merging**
   - Check ✅ **Require status checks to pass before merging**
   - Check ✅ **Require branches to be up to date before merging**
   - Check ✅ **Require code reviews before merging** (at least 1)
   - Check ✅ **Dismiss stale pull request approvals when new commits are pushed**
   - Check ✅ **Require status checks to pass:**
     - Select `test` (pytest + vitest)
     - Select `a11y` (WCAG 2.0 AA checks)
     - Select `lint` (code quality)
     - Optionally: `security` (if running CodeQL)

4. Click **Create** (or **Save changes** if updating)

### 2.2 Why This Matters

- **Prevents accidental merges** of untested code
- **Blocks PRs** if tests fail
- **Requires approvals** before merging to main
- **Ensures WCAG 2.0 AA** compliance (jest-axe checks)
- **Keeps main deployable** at all times

---

## Step 3: GitHub Secrets (GCP Deployment)

If you plan to deploy to **GCP Cloud Run**, set up these secrets. (AWS deployment requires different setup; see Step 4.2.)

### 3.1 Create Secrets in GitHub

1. Go to **Settings** → **Secrets and variables** → **Actions** (left sidebar)
2. Click **New repository secret**

**Create these 3 secrets:**

#### Secret 1: `GCP_PROJECT_ID`
- **Value:** Your GCP project ID (e.g., `cbp-sentry`)
- Click **Add secret**

#### Secret 2: `WIF_PROVIDER`
- This is your GCP Workload Identity Federation provider
- Run this command in your GCP project (replace `cbp-sentry` with your project):
  ```bash
  gcloud iam workload-identity-pools providers describe "github" \
    --project="cbp-sentry" \
    --location="global" \
    --workload-identity-pool="github-pool" \
    --format='value(name)'
  ```
- Copy the output (looks like `projects/12345/locations/global/workloadIdentityPools/github-pool/providers/github`)
- Paste as the secret value
- Click **Add secret**

#### Secret 3: `WIF_SERVICE_ACCOUNT`
- This is your GCP service account email
- Run this command:
  ```bash
  gcloud iam service-accounts list \
    --project="cbp-sentry" \
    --filter="email:sentry-github@*" \
    --format='value(email)'
  ```
- Copy the output (looks like `sentry-github@cbp-sentry.iam.gserviceaccount.com`)
- Paste as the secret value
- Click **Add secret**

### 3.2 Why These Secrets?

- **GCP_PROJECT_ID** — Tells GitHub which GCP project to deploy to
- **WIF_PROVIDER** — Allows GitHub Actions to authenticate to GCP without storing API keys
- **WIF_SERVICE_ACCOUNT** — The GCP service account that GitHub Actions will use

**Security note:** These secrets are not exposed in logs. GitHub encrypts them in transit and at rest.

---

## Step 4: Code Quality Enforcement

### 4.1 Install jest-axe for Accessibility Testing

The `a11y.yml` workflow requires `jest-axe` to be installed in the UI project. This is already in `package.json`, but needs to be installed locally and verified.

```bash
cd /home/rahulvadera/cbp-sentry/ui
npm install --save-dev jest-axe
npm run test:a11y  # Verify it works
```

If `npm run test:a11y` is not in `package.json`, add this script:

```json
{
  "scripts": {
    "test:a11y": "vitest run --include='**/*.a11y.spec.tsx'",
    "test": "vitest run"
  }
}
```

### 4.2 Enable Code Owners

The repo has a `CODEOWNERS` file that requires at least 1 approval from `@rvadera73` before merging to main.

This is already configured. When you create a PR:
- GitHub will automatically request a review from the CODEOWNERS
- PR cannot be merged without their approval

---

## Step 5: Verify Workflow Setup

### 5.1 Run a Test Workflow

To verify everything is connected:

1. Create a test branch:
   ```bash
   cd /home/rahulvadera/cbp-sentry
   git checkout -b test/setup-verification
   git push origin test/setup-verification
   ```

2. Create a simple test PR:
   - Go to GitHub
   - Click **Pull requests** → **New pull request**
   - Base: `main`
   - Compare: `test/setup-verification`
   - Click **Create pull request**

3. Watch the workflows run:
   - Go to **Actions** tab
   - You'll see `test`, `a11y`, and `lint` workflows running
   - They should complete in 2-5 minutes

4. If all pass ✅:
   - Close this PR (don't merge)
   - Delete the test branch

### 5.2 What You'll See

**Successful workflow status:**
```
✅ test (pytest + vitest)
✅ a11y (jest-axe WCAG 2.0 AA)
✅ lint (code quality)
```

**If any fail:**
- Click on the failed workflow
- Scroll to the error message
- See [Troubleshooting](#troubleshooting) below

---

## Step 6: Enable Dependabot (Optional but Recommended)

Dependabot automatically checks for outdated dependencies and opens PRs to update them.

### 6.1 Enable Dependabot Alerts

1. Go to **Settings** → **Code security and analysis** (left sidebar)
2. Click **Enable** next to:
   - Dependabot alerts ✅
   - Dependabot security updates ✅

### 6.2 Configure Dependabot

A `.github/dependabot.yml` file is already in the repo. It automatically:
- Checks `package.json` (Node) weekly
- Checks `requirements.txt` (Python) weekly
- Opens PRs with security updates

You don't need to do anything — it's already active.

---

## Step 7: Verify Repository Settings

Run this checklist to confirm everything is set up:

### Security & Compliance
- [ ] Repository is **not public** (or public if intentional)
- [ ] Branch protection enabled on `main` (Settings → Branches)
- [ ] CODEOWNERS file exists (`.github/CODEOWNERS`)
- [ ] GitHub Secrets created (`GCP_PROJECT_ID`, `WIF_PROVIDER`, `WIF_SERVICE_ACCOUNT`)

### CI/CD
- [ ] GitHub Actions enabled (Settings → Actions)
- [ ] All 6 workflows present in `.github/workflows/`
- [ ] `test.yml` covers pytest + vitest
- [ ] `a11y.yml` runs jest-axe
- [ ] `deploy-gcp.yml` configured for your GCP project

### Code Quality
- [ ] `jest-axe` installed in `ui/` (`npm ls jest-axe`)
- [ ] `pytest` installed in `api/` (`pip list | grep pytest`)
- [ ] `TESTING.md` reviewed (understand TDD approach)

### Development
- [ ] Local Docker Compose works (`docker-compose up`)
- [ ] `.env.example` filled in (rename to `.env` for local dev)
- [ ] `CLAUDE.md` read (development workflow)

---

## Step 8: First Development Workflow

Once everything is set up, here's the workflow for every feature:

### 8.1 Create Feature Branch

```bash
cd /home/rahulvadera/cbp-sentry
git checkout -b feat/issue-123-manifest-parser
```

### 8.2 Write Tests First (TDD)

```bash
# Backend test
cat > api/tests/test_manifest_parser.py << 'EOF'
def test_parse_greenfield_manifest():
    manifest_data = load_fixture("greenfield_manifest.json")
    result = parse_manifest(manifest_data)
    assert result["shipment_id"] == "SHP-001"
    assert len(result["line_items"]) == 3
EOF

# Frontend test
cat > ui/tests/components/ManifestTable.spec.tsx << 'EOF'
it("renders manifest rows", () => {
  const { getByRole } = render(<ManifestTable data={mockData} />);
  expect(getByRole("table")).toBeInTheDocument();
});
EOF
```

### 8.3 Run Tests Locally

```bash
cd /home/rahulvadera/cbp-sentry

# Backend
pytest api/tests/test_manifest_parser.py -v

# Frontend
npm run test -- ManifestTable.spec.tsx --watch
```

### 8.4 Implement Code (RED → GREEN → REFACTOR)

Edit the code until tests pass.

### 8.5 Run All Checks Before Commit

```bash
# All backend tests
pytest api/tests/ -v

# All frontend tests
npm run test

# Accessibility
npm run test:a11y

# Linting
npm run lint
```

### 8.6 Commit & Push

```bash
git add -A
git commit -m "feat: implement manifest parser

- Parses Excel uploads (password: CBPDemo2026)
- Normalizes shipper/consignee fields
- Extracts HTS codes
- Flags suspicious entries

Close #123"

git push origin feat/issue-123-manifest-parser
```

### 8.7 Create Pull Request

1. Go to GitHub
2. Click **Pull requests** → **New pull request**
3. Base: `main`
4. Compare: `feat/issue-123-manifest-parser`
5. Click **Create pull request**
6. Description auto-populates from commit message

### 8.8 Wait for Checks

GitHub Actions will automatically:
- Run `test` workflow (pytest + vitest)
- Run `a11y` workflow (jest-axe)
- Run `lint` workflow
- Request code review from CODEOWNERS

All must pass ✅ before merge is allowed.

### 8.9 Merge

Once approved and all checks pass:
- Click **Squash and merge** (combines all commits into one)
- Delete the feature branch
- GitHub closes issue #123 automatically

---

## Troubleshooting

### Problem: Workflows not running

**Solution:**
1. Go to **Settings** → **Actions** → **General**
2. Verify **Allow all actions and reusable workflows** is selected
3. Go to **Actions** tab and manually trigger a workflow

### Problem: `test` workflow fails

**Check the error:**
1. Click the failed workflow
2. Scroll to see which test failed
3. Look for assertion errors
4. Run locally: `pytest api/tests/ -v` or `npm run test`

Common issues:
- Missing dependencies: `pip install -r api/requirements.txt` or `npm install`
- Database not initialized: `docker-compose up postgres` (local testing)
- PYTHONPATH not set: `export PYTHONPATH=/home/rahulvadera/cbp-sentry:$PYTHONPATH`

### Problem: `a11y` workflow fails (jest-axe errors)

**Examples:**
- Color contrast < 4.5:1 → Check Tailwind config, adjust colors
- Missing ARIA labels → Add `aria-label` or `aria-labelledby`
- Keyboard trap → Ensure Tab can exit focus, test manually

Run locally: `npm run test:a11y` to reproduce and fix.

### Problem: GCP Cloud Run deployment fails

**Check these:**
1. GCP project exists: `gcloud projects list`
2. Workload Identity Pool exists: `gcloud iam workload-identity-pools list --location=global`
3. Service account exists: `gcloud iam service-accounts list`
4. Secrets are correct in GitHub (Settings → Secrets)

If issues persist, see `deploy/gcp/TROUBLESHOOTING.md`.

### Problem: "Require status checks" but workflow not showing

**Solution:**
1. Go to **Settings** → **Branches** → **main** (edit rule)
2. In "Require status checks," click **Search for status checks**
3. Type `test`, `a11y`, `lint` — they should appear
4. Select them
5. Click **Save**

---

## Deployment to GCP Cloud Run

Once all checks pass and you merge to `main`, the `deploy-gcp.yml` workflow automatically:

1. Builds Docker images (api + ui)
2. Pushes to Artifact Registry
3. Deploys to Cloud Run
4. Sets environment variables

**View deployment:**
```bash
gcloud run services list --region us-central1
gcloud run services describe sentry-api --region us-central1
gcloud run services describe sentry-ui --region us-central1
```

**Live URLs:**
- API: https://sentry-api-xxxxx.a.run.app
- UI: https://sentry-ui-xxxxx.a.run.app

---

## Quick Reference

| Task | Command | Time |
|------|---------|------|
| Local dev | `docker-compose up` | 2 min |
| Run tests | `pytest` + `npm run test` | 1 min |
| Run a11y checks | `npm run test:a11y` | 30 sec |
| Lint code | `npm run lint` | 15 sec |
| Create branch | `git checkout -b feat/...` | 10 sec |
| Push changes | `git push origin feat/...` | 30 sec |
| View CI/CD | GitHub **Actions** tab | instant |
| Deploy to GCP | Merge to `main` | 5 min (automatic) |

---

## Next Steps

1. ✅ Complete all steps in this guide
2. ✅ Run verification workflow (Step 5)
3. ✅ Review `CLAUDE.md` (development workflow)
4. ✅ Review `TESTING.md` (TDD approach)
5. ✅ Start Phase 1 (Manifest Ingest) using the TDD workflow above

---

## Support

If you encounter issues:

1. Check the **Troubleshooting** section above
2. Review workflow logs in GitHub **Actions** tab
3. Read the relevant documentation:
   - `CLAUDE.md` — Development workflow
   - `TESTING.md` — TDD approach
   - `.github/README.md` — CI/CD details
   - `.github/INTEGRATION_GUIDE.md` — How everything connects

---

**Last updated:** 2026-05-18  
**For:** Sentry CBP MVP  
**Status:** Ready for deployment
