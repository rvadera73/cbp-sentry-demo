# GitHub CI/CD Setup Checklist

This checklist guides you through activating the CI/CD pipelines and automation for the Sentry CBP project.

## ✅ Files Created (Already Done)

- [x] `.github/workflows/test.yml` — Run pytest + vitest on PR
- [x] `.github/workflows/a11y.yml` — WCAG 2.0 AA checks (jest-axe)
- [x] `.github/workflows/lint.yml` — Code linting (black, isort, prettier)
- [x] `.github/workflows/security.yml` — Dependency + secret scanning
- [x] `.github/workflows/deploy-gcp.yml` — Deploy to Cloud Run
- [x] `.github/workflows/deploy-aws.yml` — Deploy to AWS (template)
- [x] `.github/ISSUE_TEMPLATE/feature.md` — Feature request template
- [x] `.github/ISSUE_TEMPLATE/bug.md` — Bug report template
- [x] `.github/ISSUE_TEMPLATE/accessibility.md` — A11y issue template
- [x] `.github/pull_request_template.md` — PR template
- [x] `.github/CODEOWNERS` — Enforce code review
- [x] `.github/dependabot.yml` — Automated dependency updates
- [x] `.github/config.yml` — Repository settings documentation
- [x] `.github/projects/board.yml` — GitHub Projects board configuration
- [x] `.github/README.md` — CI/CD documentation

---

## 🔧 Manual Setup Required

### 1. Enable GitHub Features (Settings)

#### Branch Protection (Settings → Branches)
- [ ] Click "Add rule" button
- [ ] Pattern: `main`
- [ ] ✓ Require pull request reviews before merging
  - Require approvals: **1**
- [ ] ✓ Dismiss stale pull request approvals when new commits are pushed
- [ ] ✓ Require approval of the most recent reviewable push
- [ ] ✓ Require status checks to pass before merging
  - Required status checks:
    - `Test / test`
    - `Accessibility (WCAG 2.0 AA) / accessibility`
    - `Lint & Format / lint`
    - `Security Scanning / security`
- [ ] ✓ Require branches to be up to date before merging
- [ ] ❌ Allow force pushes (disabled)
- [ ] ❌ Allow deletions (disabled)
- [ ] Click "Create" to save

#### Code Security (Settings → Code security and analysis)
- [ ] ✓ Enable Dependabot alerts
- [ ] ✓ Enable Dependabot security updates
- [ ] ✓ Enable CodeQL analysis

#### Actions (Settings → Actions)
- [ ] ✓ Allow GitHub Actions to create and approve pull requests

---

### 2. Set Up GCP Deployment (for deploy-gcp.yml)

#### GCP One-Time Setup
```bash
# Replace PROJECT_ID with your actual GCP project ID (e.g., cbp-sentry)
PROJECT_ID="cbp-sentry"

# 1. Create service account for GitHub Actions
gcloud iam service-accounts create github-actions \
  --display-name="GitHub Actions" \
  --project=$PROJECT_ID

# 2. Grant Cloud Run deployment permission
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member=serviceAccount:github-actions@${PROJECT_ID}.iam.gserviceaccount.com \
  --role=roles/run.admin

# 3. Grant Artifact Registry permission
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member=serviceAccount:github-actions@${PROJECT_ID}.iam.gserviceaccount.com \
  --role=roles/artifactregistry.admin

# 4. Create Artifact Registry repository
gcloud artifacts repositories create sentry \
  --repository-format=docker \
  --location=us-central1 \
  --project=$PROJECT_ID

# 5. Create Workload Identity Pool
gcloud iam workload-identity-pools create github \
  --project=$PROJECT_ID \
  --location=global \
  --display-name="GitHub"

# 6. Create Workload Identity Provider
gcloud iam workload-identity-pools providers create-oidc github \
  --project=$PROJECT_ID \
  --location=global \
  --workload-identity-pool=github \
  --display-name="GitHub" \
  --attribute-mapping="google.subject=sub,attribute.repository=assertion.repository,attribute.repository_owner=assertion.repository_owner" \
  --issuer-uri="https://token.actions.githubusercontent.com"

# 7. Grant service account OIDC access (replace GITHUB_REPO with your repo)
gcloud iam service-accounts add-iam-policy-binding \
  github-actions@${PROJECT_ID}.iam.gserviceaccount.com \
  --role=roles/iam.workloadIdentityUser \
  --member="principalSet://iam.googleapis.com/projects/$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')/locations/global/workloadIdentityPools/github/attribute.repository/rvadera73/cbp-sentry"

echo "GCP setup complete. Get WIF_PROVIDER value for GitHub Secrets:"
gcloud iam workload-identity-pools describe github \
  --project=$PROJECT_ID \
  --location=global \
  --format='value(name)'
```

#### GitHub Secrets (Settings → Secrets → Actions)
Add these secrets:
- [ ] `GCP_PROJECT_ID` = Your GCP project ID (e.g., `cbp-sentry`)
- [ ] `WIF_PROVIDER` = Output from command above (e.g., `projects/123456/locations/global/workloadIdentityPools/github/providers/github`)
- [ ] `WIF_SERVICE_ACCOUNT` = `github-actions@[PROJECT_ID].iam.gserviceaccount.com`

#### Verify Cloud Run Services
- [ ] Create Cloud Run services (or deploy-gcp.yml will do this):
  ```bash
  gcloud run create sentry-api --source ./api --region us-central1 --allow-unauthenticated
  gcloud run create sentry-ui --source ./ui --region us-central1 --allow-unauthenticated
  ```

---

### 3. Configure UI Testing (for a11y.yml and test.yml)

#### Add test:a11y script to ui/package.json
```json
{
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview",
    "type-check": "tsc --noEmit",
    "test": "vitest",
    "test:a11y": "jest --testPathPattern=a11y --passWithNoTests"
  }
}
```

#### Install jest-axe
```bash
cd ui
npm install --save-dev jest-axe @testing-library/jest-dom @testing-library/react
```

#### Create accessibility test file (example)
Create `ui/tests/accessibility.spec.tsx`:
```typescript
import { render } from '@testing-library/react';
import { axe } from 'jest-axe';
import { ReferralPackagePage } from '../src/pages/ReferralPackagePage';

describe('Accessibility (WCAG 2.0 AA)', () => {
  it('ReferralPackagePage has no accessibility violations', async () => {
    const { container } = render(<ReferralPackagePage />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});
```

---

### 4. Create GitHub Project Board

#### Manual Setup (GitHub UI)
- [ ] Go to your repo → Projects → New project
- [ ] Name: "Sentry Development Board"
- [ ] Template: **Kanban**
- [ ] Create the following columns (if not auto-created):
  - Backlog
  - Ready for Development
  - In Progress
  - In Review
  - Done
- [ ] Configure automation:
  - Backlog: Auto-add new issues
  - Done: Auto-close on PR merge

#### Via GitHub CLI
```bash
# Create project (if GitHub CLI installed)
gh project create --title "Sentry Development Board" --format json
```

---

### 5. Set Up Dependabot (Optional but Recommended)

- [ ] GitHub will auto-detect `.github/dependabot.yml`
- [ ] Go to Settings → Code security and analysis → Enable Dependabot alerts & updates
- [ ] Dependabot will open PRs weekly on Monday at 09:00 UTC
- [ ] Review and merge PRs as needed

---

### 6. Create GitHub Labels (Optional)

Run this script to create labels:
```bash
gh label create "status/backlog" --color cccccc --description "Issue in backlog"
gh label create "status/ready" --color 0366d6 --description "Ready for development"
gh label create "status/in-progress" --color fbca04 --description "Currently being worked on"
gh label create "status/in-review" --color a5a5a5 --description "PR submitted, awaiting review"
gh label create "status/done" --color 28a745 --description "Merged and deployed"

gh label create "priority/critical" --color d73a49 --description "Blocking issue"
gh label create "priority/high" --color ff6b6b --description "High priority"
gh label create "priority/medium" --color ffc640 --description "Medium priority"
gh label create "priority/low" --color 85e89d --description "Low priority"

gh label create "type/feature" --color 0075ca --description "New feature"
gh label create "type/bug" --color d73a49 --description "Bug report"
gh label create "type/a11y" --color ff6b6b --description "WCAG 2.0 AA issue"
gh label create "type/refactor" --color 9e6a03 --description "Code cleanup"
gh label create "type/docs" --color 0366d6 --description "Documentation"

gh label create "horizon/H1" --color 0366d6 --description "Macro analysis (weeks before)"
gh label create "horizon/H2" --color 0366d6 --description "Pre-manifest intel (14-22 days)"
gh label create "horizon/H3" --color 0366d6 --description "Full assessment (72-hour)"

gh label create "area/api" --color 8250df --description "Backend (Python)"
gh label create "area/ui" --color 8250df --description "Frontend (React)"
gh label create "area/database" --color 8250df --description "PostgreSQL / Neo4j"
gh label create "area/deployment" --color 8250df --description "Deployment (GCP/AWS)"
```

---

### 7. Set Up AWS Deployment (Optional, for deploy-aws.yml)

**Note**: This is a template workflow. Follow setup instructions in `.github/workflows/deploy-aws.yml`.

```bash
# Create AWS OIDC provider (one-time)
aws iam create-open-id-connect-provider \
  --url https://token.actions.githubusercontent.com \
  --client-id-list sts.amazonaws.com \
  --thumbprint-list YOUR_THUMBPRINT

# Create IAM role for GitHub Actions
# See deploy-aws.yml for trust policy

# Add GitHub Secrets: AWS_ACCOUNT_ID, AWS_ROLE_TO_ASSUME, AWS_S3_BUCKET, CLOUDFRONT_DISTRIBUTION_ID
```

---

## ✅ Verification Checklist

After completing setup:

- [ ] Branch protection rules active on `main` branch
- [ ] GitHub Actions workflows visible in "Actions" tab
- [ ] Can see: test.yml, a11y.yml, lint.yml, security.yml, deploy-gcp.yml statuses
- [ ] Create test issue → Check that issue templates appear
- [ ] Create test PR → Verify workflows run and pass
- [ ] Check GitHub Projects board → Can create board and configure columns
- [ ] (GCP only) Verify deploy-gcp.yml deploys to Cloud Run after merge to main

---

## 🎯 Next Steps

1. **Complete manual setup above** (branch protection, secrets, GCP setup)
2. **Test the workflows**:
   ```bash
   # Create a test branch
   git checkout -b test/ci-workflow
   
   # Make a small change
   echo "# Test" >> README.md
   
   # Commit and push
   git commit -am "test: verify CI workflow"
   git push origin test/ci-workflow
   
   # Go to GitHub → Pull requests → Create PR
   # Watch Actions tab for workflow runs
   ```

3. **Create your first feature issue**:
   - Go to Issues → New issue
   - Select "Feature Request"
   - Add horizon label (H1/H2/H3)
   - Wait for approval in issue comments
   - Create branch from issue: `git checkout -b feat/issue-NNN-short-name`

4. **For accessibility testing**: Install jest-axe and create first test (see step 3 above)

---

## 📚 References

- **GitHub Actions Docs**: https://docs.github.com/en/actions
- **Workflow Syntax**: https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions
- **jest-axe**: https://github.com/nickcolley/jest-axe
- **WCAG 2.0 AA**: https://www.w3.org/WAI/WCAG21/quickref/
- **Project Documentation**: See `.github/README.md`

---

**Questions?** Check `.github/README.md` or existing issues on GitHub.
