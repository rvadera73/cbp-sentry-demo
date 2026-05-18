# GitHub CI/CD and Automation Setup

This directory contains GitHub Actions workflows, issue templates, and automation configurations for the Sentry CBP project.

## Directory Structure

```
.github/
├── workflows/              # GitHub Actions CI/CD pipelines
│   ├── test.yml           # Run pytest (backend) + vitest (frontend) on PR
│   ├── a11y.yml           # WCAG 2.0 AA accessibility checks (jest-axe)
│   ├── lint.yml           # Code formatting and linting checks
│   ├── security.yml       # Dependency and secret scanning
│   ├── deploy-gcp.yml     # Deploy to GCP Cloud Run (on main merge)
│   └── deploy-aws.yml     # Deploy to AWS Lambda/ECS (template)
│
├── ISSUE_TEMPLATE/        # GitHub issue templates
│   ├── feature.md         # Feature request template (with H1/H2/H3 horizons)
│   ├── bug.md             # Bug report template
│   └── accessibility.md   # WCAG 2.0 AA compliance issue template
│
├── projects/
│   └── board.yml          # GitHub Projects board configuration (documentation)
│
├── config.yml             # Repository settings and secrets configuration
├── dependabot.yml         # Automated dependency updates (weekly)
├── CODEOWNERS             # Enforce code review on critical areas
├── pull_request_template.md  # PR template (auto-fills PR description)
└── README.md              # This file
```

---

## Workflows

### 1. **test.yml** — Run Tests on PR
- **Trigger**: Push to `main`/`develop`, Pull Request
- **Steps**:
  1. Checkout code
  2. Set up Python 3.12
  3. Install Python dependencies (`pip install -r api/requirements.txt`)
  4. Run pytest on `api/tests/`
  5. Set up Node 20
  6. Install npm dependencies (`npm ci`)
  7. Run vitest (if configured) or type-check
  8. Upload coverage reports

**Required**: `api/requirements.txt`, `api/tests/` directory

---

### 2. **a11y.yml** — WCAG 2.0 AA Accessibility Checks
- **Trigger**: Push to `main`/`develop`, Pull Request (UI changes only)
- **Steps**:
  1. Install jest-axe and testing libraries
  2. Run jest-axe on all components
  3. Fail if violations found
  4. Generate accessibility report
  5. Comment on PR with violations

**Required**: `npm run test:a11y` script in `ui/package.json`

**Setup needed**: Add to `ui/package.json`:
```json
{
  "scripts": {
    "test:a11y": "jest --testPathPattern=a11y --passWithNoTests"
  }
}
```

---

### 3. **lint.yml** — Code Formatting & Linting
- **Trigger**: Push to `main`/`develop`, Pull Request
- **Steps**:
  1. Python: black, isort, flake8
  2. TypeScript: prettier, ESLint (if configured)
  3. Fail if formatting issues found

**Optional**: Requires configuration files (`.flake8`, `.prettierrc`, `.eslintrc`)

---

### 4. **security.yml** — Dependency & Secret Scanning
- **Trigger**: Every PR, weekly schedule (Monday 0:00 UTC)
- **Steps**:
  1. pip-audit (Python dependencies)
  2. npm audit (Node dependencies)
  3. CodeQL (static analysis)
  4. TruffleHog (secret scanning)

---

### 5. **deploy-gcp.yml** — Deploy to GCP Cloud Run
- **Trigger**: Merge to `main` branch
- **Steps**:
  1. Authenticate to Google Cloud (Workload Identity Federation)
  2. Build and push API Docker image to Artifact Registry
  3. Build and push UI Docker image to Artifact Registry
  4. Deploy API to Cloud Run (sentry-api service)
  5. Deploy UI to Cloud Run (sentry-ui service)
  6. Set environment variables (GCP_PROJECT, DEMO_MODE=false)

**Required secrets** (set in Settings → Secrets → Actions):
- `GCP_PROJECT_ID` — GCP project ID (e.g., `cbp-sentry`)
- `WIF_PROVIDER` — Workload Identity Federation provider
- `WIF_SERVICE_ACCOUNT` — GitHub Actions service account email

**GCP Setup** (one-time):
```bash
# 1. Create GCP service account
gcloud iam service-accounts create github-actions \
  --display-name="GitHub Actions"

# 2. Grant Cloud Run and Artifact Registry permissions
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member=serviceAccount:github-actions@PROJECT_ID.iam.gserviceaccount.com \
  --role=roles/run.admin

gcloud projects add-iam-policy-binding PROJECT_ID \
  --member=serviceAccount:github-actions@PROJECT_ID.iam.gserviceaccount.com \
  --role=roles/artifactregistry.admin

# 3. Set up Workload Identity Federation
gcloud iam workload-identity-pools create github \
  --project=PROJECT_ID \
  --location=global \
  --display-name="GitHub"

gcloud iam workload-identity-pools providers create-oidc github \
  --project=PROJECT_ID \
  --location=global \
  --workload-identity-pool=github \
  --display-name="GitHub" \
  --attribute-mapping="google.subject=sub,attribute.repository=assertion.repository,attribute.repository_owner=assertion.repository_owner" \
  --issuer-uri="https://token.actions.githubusercontent.com"

gcloud iam service-accounts add-iam-policy-binding \
  github-actions@PROJECT_ID.iam.gserviceaccount.com \
  --role=roles/iam.workloadIdentityUser \
  --member="principalSet://iam.googleapis.com/projects/PROJECT_ID/locations/global/workloadIdentityPools/github/attribute.repository/rvadera73/cbp-sentry"
```

---

### 6. **deploy-aws.yml** — Deploy to AWS Lambda/ECS (Template)
- **Trigger**: Manual workflow dispatch
- **Status**: Template only, requires AWS configuration
- **Components**:
  - Build and push API image to Amazon ECR
  - Build and push UI image to Amazon ECR
  - Deploy API to ECS
  - Deploy UI assets to S3 + CloudFront

**Required secrets**:
- `AWS_ACCOUNT_ID`
- `AWS_ROLE_TO_ASSUME`
- `AWS_S3_BUCKET`
- `CLOUDFRONT_DISTRIBUTION_ID`

**See deploy-aws.yml for setup instructions.**

---

## Issue Templates

### Feature Request Template
- Field: Description (what feature?)
- Field: Business context (H1/H2/H3 horizon?)
- Field: Acceptance criteria (checklist)
- Field: Testing approach (TDD)
- Field: WCAG 2.0 AA considerations

**Usage**: Click "New Issue" → Select "Feature Request"

---

### Bug Report Template
- Field: Description (what's broken?)
- Field: Steps to reproduce (numbered list)
- Field: Expected vs. actual behavior
- Field: Environment (local/stage/prod)
- Field: WCAG impact (if applicable)

**Usage**: Click "New Issue" → Select "Bug Report"

---

### Accessibility Issue Template
- Field: Component affected
- Field: WCAG 2.0 AA criterion (with links)
- Field: Severity (critical/major/minor)
- Field: Issue type (screen reader/keyboard/contrast/etc.)
- Field: Testing checklist

**Usage**: Click "New Issue" → Select "Accessibility Issue"

---

## GitHub Projects Board

**Purpose**: Track feature development using Kanban columns.

**Columns**:
1. **Backlog** — New issues, not yet started
2. **Ready for Development** — Refined, has acceptance criteria
3. **In Progress** — Currently being worked on
4. **In Review** — PR submitted, awaiting review
5. **Done** — Merged to main, deployed

**Labels**:
- **Status**: `status/backlog`, `status/ready`, `status/in-progress`, `status/in-review`, `status/done`
- **Priority**: `priority/critical`, `priority/high`, `priority/medium`, `priority/low`
- **Type**: `type/feature`, `type/bug`, `type/a11y`, `type/refactor`, `type/docs`
- **Horizon**: `horizon/H1`, `horizon/H2`, `horizon/H3`
- **Area**: `area/api`, `area/ui`, `area/database`, `area/deployment`

**Setup**: Manual (Settings → Projects → New Project) or via API.

---

## Dependabot Configuration

**Purpose**: Automated dependency updates and security alerts.

**Schedule**: Weekly (Monday 09:00 UTC)

**Behavior**:
- Python (pip): Updates to `api/requirements.txt`
- Node (npm): Updates to `ui/package-lock.json`
- GitHub Actions: Updates to workflow files

**Constraints**:
- Ignores major version updates for critical packages (fastapi, react, typescript, neo4j)
- Limits open PRs to 5 (Python) / 5 (Node) / 3 (Actions)
- Auto-assigns to @rvadera73 for review

---

## CODEOWNERS

**Purpose**: Enforce code review on critical areas.

**Rules**:
- All code: @rvadera73 (required reviewer)
- API backend: @rvadera73
- UI frontend: @rvadera73
- Deployment configs: @rvadera73

**Effect**: PRs cannot be merged without approval from CODEOWNERS.

---

## Development Workflow (TDD)

1. **Create Issue**: Describe feature/bug in GitHub, add labels and horizon
2. **Create Branch**: `git checkout -b feat/issue-123-short-name`
3. **Write Test First** (RED phase):
   ```bash
   npm run test -- --watch
   ```
4. **Write Implementation** (GREEN phase)
5. **Run All Tests**:
   ```bash
   pytest api/tests/ -v
   npm run test
   ```
6. **Check Accessibility** (WCAG 2.0 AA):
   ```bash
   npm run test:a11y
   ```
7. **Commit** (reference issue):
   ```bash
   git commit -m "feat: add manifest parser
   
   - Validates HTS code format
   - Flags suspicious entries
   
   Close #123"
   ```
8. **Push**: `git push origin feat/issue-123-short-name`
9. **Create PR**: GitHub Actions run test.yml, a11y.yml, lint.yml, security.yml
10. **Review**: Await approval from CODEOWNERS
11. **Merge**: GitHub Actions deploy to Cloud Run (main branch only)

---

## Repository Settings (Manual Setup)

### Branch Protection (Settings → Branches → main)
- [x] Require pull request reviews (1 approval)
- [x] Dismiss stale reviews on new commits
- [x] Require code owner reviews
- [x] Require status checks to pass:
  - `Test / test`
  - `Accessibility (WCAG 2.0 AA) / accessibility`
  - `Lint & Format / lint`
  - `Security Scanning / security`
- [x] Require branches to be up to date
- [ ] Allow force pushes (disabled)
- [ ] Allow deletions (disabled)

### Code Security & Analysis (Settings → Code security and analysis)
- [x] Dependabot alerts (enabled)
- [x] Dependabot security updates (enabled)
- [x] CodeQL analysis (enabled)
- [x] Secret scanning (enabled if private repo)

### GitHub Actions (Settings → Actions)
- [x] Allow GitHub Actions to create and approve pull requests
- [x] Cache quota: up to 5GB

---

## Troubleshooting

### Test workflow failing
1. Check that `api/requirements.txt` exists
2. Ensure `api/tests/` directory exists with test files
3. Verify Python version (3.12) in test.yml
4. Run locally: `pytest api/tests/ -v`

### A11y workflow failing
1. Ensure jest-axe is installed: `npm install --save-dev jest-axe`
2. Create `ui/tests/accessibility.spec.tsx` or similar
3. Add `test:a11y` script to `ui/package.json`
4. Run locally: `npm run test:a11y`

### Deploy-GCP failing
1. Verify GCP credentials are set in GitHub Secrets
2. Check that Cloud Run services exist (sentry-api, sentry-ui)
3. Ensure Artifact Registry bucket exists
4. Run locally to test Docker build: `docker build ./api -t test`

### Deploy-AWS not configured
1. AWS workflow is a template; follow instructions in deploy-aws.yml
2. Set up AWS OIDC provider (one-time setup)
3. Add GitHub Secrets: AWS_ACCOUNT_ID, AWS_ROLE_TO_ASSUME, etc.
4. Create ECS cluster and S3 bucket before deploying

---

## References

- **Workflows**: `.github/workflows/*.yml`
- **Issue templates**: `.github/ISSUE_TEMPLATE/*.md`
- **Development**: See `CLAUDE.md` (project instructions)
- **Architecture**: See `ARCHITECTURE.md` (system design)
- **WCAG 2.0**: https://www.w3.org/WAI/WCAG21/quickref/
- **jest-axe**: https://github.com/nickcolley/jest-axe
- **GitHub Actions**: https://docs.github.com/en/actions

---

## Quick Start

### Local Development
```bash
# Install dependencies
cd api && pip install -r requirements.txt
cd ../ui && npm ci

# Run tests
pytest api/tests/ -v
npm run test

# Check accessibility
npm run test:a11y

# Run locally
docker-compose up --build
```

### Push to GitHub
```bash
git checkout -b feat/issue-123-feature-name
# ... make changes ...
pytest api/tests/ -v && npm run test && npm run test:a11y
git commit -m "feat: description

Close #123"
git push origin feat/issue-123-feature-name
# Create PR on GitHub
```

---

**Questions?** See `CLAUDE.md` or check existing issues/PRs for examples.
