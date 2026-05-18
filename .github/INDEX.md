# GitHub CI/CD & Automation — Complete Index

This `.github/` directory contains all GitHub Actions workflows, automation, and templates for the Sentry CBP project.

**Total**: 17 files | 2,446 lines of YAML + documentation | 120 KB

---

## 📖 Documentation (Start Here)

### 1. **README.md** — Full CI/CD Reference Guide
- Overview of all workflows
- Step-by-step setup instructions
- GCP and AWS configuration guides
- Local development workflow
- Troubleshooting section
- **Read this first after SETUP_CHECKLIST**

### 2. **SETUP_CHECKLIST.md** — Actionable Setup Steps
- Branch protection configuration
- GCP service account setup (with shell commands)
- GitHub Secrets configuration
- UI testing setup (jest-axe installation)
- GitHub Projects board creation
- Verification checklist
- **Follow these steps immediately**

### 3. **INTEGRATION_GUIDE.md** — How CI/CD Integrates with CLAUDE.md
- Development workflow loop (Issue → Deploy)
- Step-by-step example: Manifest parser feature
- How GitHub Actions enforces CLAUDE.md requirements
- Local testing checklist
- Troubleshooting
- **Read after understanding CLAUDE.md**

---

## 🔄 Workflows (.github/workflows/)

### **test.yml** (67 lines) — Run Tests on PR
**Purpose**: Ensure all code has passing tests before merge

**Trigger**: Push to main/develop, all PRs

**Steps**:
1. Checkout code
2. Set up Python 3.12
3. Install api/requirements.txt
4. Run pytest api/tests/
5. Set up Node 20
6. Install npm deps (ui/)
7. Run vitest (ui/tests/) or type-check
8. Upload coverage reports

**Status checks**: `Test / test` (required for merge)

---

### **a11y.yml** (81 lines) — WCAG 2.0 AA Accessibility Checks
**Purpose**: Enforce accessibility compliance before merge

**Trigger**: PR with UI changes

**Steps**:
1. Install jest-axe
2. Run jest-axe on components
3. Fail if violations found
4. Generate accessibility report
5. Comment on PR with violations

**Status checks**: `Accessibility (WCAG 2.0 AA) / accessibility` (required for merge)

**Required**: `npm run test:a11y` script in ui/package.json

---

### **lint.yml** (75 lines) — Code Formatting & Linting
**Purpose**: Enforce code style consistency

**Trigger**: All PRs and pushes

**Steps**:
- Python: black, isort, flake8
- TypeScript: prettier, ESLint (if configured)
- Fails if formatting issues found

**Status checks**: `Lint & Format / lint` (required for merge)

---

### **security.yml** (89 lines) — Dependency & Secret Scanning
**Purpose**: Catch security vulnerabilities

**Trigger**: All PRs, weekly schedule (Monday 0:00 UTC)

**Steps**:
1. pip-audit (Python dependencies)
2. npm audit (Node dependencies)
3. CodeQL (static analysis)
4. TruffleHog (secret scanning)

**Status checks**: `Security Scanning / security` (required for merge)

---

### **deploy-gcp.yml** (126 lines) — Deploy to GCP Cloud Run
**Purpose**: Auto-deploy to production on merge to main

**Trigger**: Merge to main branch only

**Steps**:
1. Authenticate to Google Cloud (Workload Identity Federation)
2. Build and push API Docker image to Artifact Registry
3. Build and push UI Docker image to Artifact Registry
4. Deploy API to Cloud Run (sentry-api service)
5. Deploy UI to Cloud Run (sentry-ui service)
6. Set env vars (GCP_PROJECT, DEMO_MODE=false)

**Required Secrets**:
- `GCP_PROJECT_ID` — Your GCP project ID
- `WIF_PROVIDER` — Workload Identity Federation provider
- `WIF_SERVICE_ACCOUNT` — GitHub Actions service account

**GCP Setup**: See SETUP_CHECKLIST.md

---

### **deploy-aws.yml** (138 lines) — Deploy to AWS Lambda/ECS
**Purpose**: Template for AWS deployment

**Trigger**: Manual workflow dispatch

**Status**: Template only, requires AWS configuration

**Steps**:
1. Authenticate to AWS (OIDC)
2. Build and push to ECR
3. Deploy API to ECS
4. Deploy UI to S3 + CloudFront
5. Invalidate CloudFront cache

**Required Secrets**: AWS_ACCOUNT_ID, AWS_ROLE_TO_ASSUME, AWS_S3_BUCKET, CLOUDFRONT_DISTRIBUTION_ID

**Setup**: Follow instructions in deploy-aws.yml

---

## 📝 Issue Templates (.github/ISSUE_TEMPLATE/)

### **feature.md** — Feature Request Template
**Fields**:
- Description (what feature?)
- Business context (H1/H2/H3 horizon?)
- Acceptance criteria (checklist)
- Testing approach (TDD)
- WCAG 2.0 AA considerations

**Usage**: New Issue → Select "Feature Request"

---

### **bug.md** — Bug Report Template
**Fields**:
- Description (what's broken?)
- Steps to reproduce (numbered list)
- Expected vs. actual behavior
- Environment (local/stage/prod)
- WCAG impact (if applicable)

**Usage**: New Issue → Select "Bug Report"

---

### **accessibility.md** — Accessibility Issue Template
**Fields**:
- Component affected
- WCAG 2.0 AA criterion (with links)
- Severity (critical/major/minor)
- Issue type (screen reader/keyboard/contrast/etc.)
- Testing checklist

**Usage**: New Issue → Select "Accessibility Issue"

---

## ⚙️ Configuration Files

### **CODEOWNERS** — Code Review Enforcement
**Purpose**: Require approval from specific reviewers

**Current Rule**:
```
* @rvadera73
```

All code requires approval from @rvadera73 before merge.

---

### **dependabot.yml** — Automated Dependency Updates
**Purpose**: Weekly dependency updates and security patches

**Configuration**:
- **Python (pip)**: api/requirements.txt
  - Schedule: Weekly (Monday 09:00 UTC)
  - Open PRs limit: 5
  - Ignores: Major versions of fastapi, neo4j

- **Node (npm)**: ui/package-lock.json
  - Schedule: Weekly (Monday 09:00 UTC)
  - Open PRs limit: 5
  - Ignores: Major versions of react, typescript

- **GitHub Actions**: Workflow files
  - Schedule: Weekly (Monday 09:00 UTC)
  - Open PRs limit: 3

---

### **pull_request_template.md** — PR Description Template
**Purpose**: Auto-fill PR description with checklist

**Sections**:
- Description (brief summary)
- Changes (numbered list)
- Testing (checkbox: tests, a11y, manual)
- Accessibility (WCAG compliance)
- Checklist (alignment with CLAUDE.md)

---

### **config.yml** — Repository Settings Reference
**Purpose**: Document repository configuration

**Includes**:
- Branch protection rules (recommended settings)
- GitHub Actions secrets (list)
- Integrations (Dependabot, CodeQL)
- Recommended GitHub Settings paths

---

### **projects/board.yml** — GitHub Projects Configuration
**Purpose**: Document Kanban board structure

**Columns**:
1. Backlog
2. Ready for Development
3. In Progress
4. In Review
5. Done

**Labels**: 20+ labels with taxonomy (status, priority, type, horizon, area)

---

## 📊 File Structure Summary

```
.github/
├── workflows/                   (6 GitHub Actions)
│   ├── test.yml                (67 lines)
│   ├── a11y.yml                (81 lines)
│   ├── lint.yml                (75 lines)
│   ├── security.yml            (89 lines)
│   ├── deploy-gcp.yml          (126 lines)
│   └── deploy-aws.yml          (138 lines)
│
├── ISSUE_TEMPLATE/             (3 templates)
│   ├── feature.md
│   ├── bug.md
│   └── accessibility.md
│
├── projects/                    (1 config)
│   └── board.yml
│
├── Documentation
│   ├── INDEX.md                 (this file)
│   ├── README.md                (comprehensive guide)
│   ├── SETUP_CHECKLIST.md       (actionable steps)
│   └── INTEGRATION_GUIDE.md     (workflow integration)
│
├── Configuration
│   ├── CODEOWNERS               (code review enforcement)
│   ├── dependabot.yml           (dependency updates)
│   ├── pull_request_template.md (PR template)
│   ├── config.yml               (settings reference)
│   └── config.yml               (already mentioned)

Total: 17 files | 2,446 lines | 120 KB
```

---

## 🚀 Quick Start (3 Steps)

### Step 1: Read Setup Guide
```
.github/SETUP_CHECKLIST.md
```
Follow all steps to configure branch protection, GCP secrets, UI testing.

### Step 2: Understand Workflows
```
.github/README.md
```
Read the workflow details and troubleshooting section.

### Step 3: Start Coding
```
CLAUDE.md — Development Workflow section
```
Follow TDD workflow, reference INTEGRATION_GUIDE.md if needed.

---

## 🔧 Manual Setup Checklist

- [ ] Read SETUP_CHECKLIST.md
- [ ] Configure branch protection (Settings → Branches → main)
- [ ] Set up GCP (run shell commands from SETUP_CHECKLIST.md)
- [ ] Add GitHub Secrets (GCP_PROJECT_ID, WIF_PROVIDER, WIF_SERVICE_ACCOUNT)
- [ ] Install jest-axe (npm install --save-dev jest-axe)
- [ ] Add test:a11y script to ui/package.json
- [ ] Enable Dependabot (Settings → Code security and analysis)
- [ ] Create test PR to verify workflows pass
- [ ] Create first feature issue

---

## 📚 Documentation Cross-Reference

| Task | Document |
|------|----------|
| Set up CI/CD | SETUP_CHECKLIST.md |
| Understand workflows | README.md |
| Learn integration with CLAUDE.md | INTEGRATION_GUIDE.md |
| Troubleshoot CI/CD | README.md § Troubleshooting |
| Create feature issue | ISSUE_TEMPLATE/feature.md |
| Report bug | ISSUE_TEMPLATE/bug.md |
| Report a11y issue | ISSUE_TEMPLATE/accessibility.md |
| Development workflow | CLAUDE.md § Development Workflow |
| System architecture | ARCHITECTURE.md |

---

## ✅ What Gets Enforced

| Requirement | Enforcement | Workflow |
|-------------|------------|----------|
| Tests pass | Required status check | test.yml |
| WCAG 2.0 AA | Required status check | a11y.yml |
| Code linting | Required status check | lint.yml |
| No vulnerabilities | Required status check | security.yml |
| Code review | CODEOWNERS (1 approval) | GitHub |
| Branch protection | Enforce on main | GitHub Settings |
| Dependency updates | Weekly PRs | dependabot.yml |
| Issue tracking | Templates enforce structure | GitHub Issues |

---

## 🎯 Workflow Execution Order

1. **test.yml** (3-5 min) — Run in parallel with a11y.yml, lint.yml, security.yml
2. **a11y.yml** (2-3 min) — Run in parallel
3. **lint.yml** (1-2 min) — Run in parallel
4. **security.yml** (5-10 min) — Run in parallel
5. **Manual code review** (waiting for CODEOWNERS approval)
6. **Merge to main**
7. **deploy-gcp.yml** (10-15 min) — Deploy to Cloud Run

**Total PR review time**: ~15-20 minutes (workflows run in parallel)
**Total deployment time**: ~10-15 minutes (GCP Cloud Run)

---

## 🆘 Troubleshooting Index

| Issue | Guide |
|-------|-------|
| GitHub Actions fails | README.md § Troubleshooting |
| deploy-gcp.yml fails | README.md § Troubleshooting → Deploy-GCP |
| A11y tests fail | README.md § Troubleshooting → A11y |
| Secrets not found | SETUP_CHECKLIST.md § Step 2 |
| jest-axe not installed | SETUP_CHECKLIST.md § Step 3 |
| GCP permissions error | SETUP_CHECKLIST.md § GCP One-Time Setup |

---

## 📖 How to Read This Directory

**For first-time setup**:
1. SETUP_CHECKLIST.md (follow all steps)
2. README.md (understand what you set up)
3. INTEGRATION_GUIDE.md (see how it works with CLAUDE.md)

**For daily development**:
- Reference CLAUDE.md "Development Workflow"
- Check workflows in `.github/workflows/` if something fails
- Use issue templates from `.github/ISSUE_TEMPLATE/`

**For troubleshooting**:
- Check README.md § Troubleshooting
- Review workflow logs in GitHub Actions
- Create issue using appropriate template

---

## 🔗 Key External Links

- **GitHub Actions**: https://docs.github.com/en/actions
- **jest-axe**: https://github.com/nickcolley/jest-axe
- **WCAG 2.0 AA**: https://www.w3.org/WAI/WCAG21/quickref/
- **GCP Cloud Run**: https://cloud.google.com/run/docs
- **AWS Lambda**: https://docs.aws.amazon.com/lambda/

---

## 📋 Files in This Directory

| File | Lines | Purpose |
|------|-------|---------|
| workflows/test.yml | 67 | Python + TypeScript testing |
| workflows/a11y.yml | 81 | WCAG 2.0 AA enforcement |
| workflows/lint.yml | 75 | Code formatting |
| workflows/security.yml | 89 | Dependency + secret scanning |
| workflows/deploy-gcp.yml | 126 | GCP Cloud Run deployment |
| workflows/deploy-aws.yml | 138 | AWS Lambda/ECS template |
| ISSUE_TEMPLATE/feature.md | — | Feature request template |
| ISSUE_TEMPLATE/bug.md | — | Bug report template |
| ISSUE_TEMPLATE/accessibility.md | — | A11y issue template |
| pull_request_template.md | — | PR description template |
| CODEOWNERS | — | Code review enforcement |
| dependabot.yml | — | Dependency updates |
| config.yml | — | Settings reference |
| projects/board.yml | — | Kanban board config |
| README.md | — | Comprehensive guide |
| SETUP_CHECKLIST.md | — | Actionable setup steps |
| INTEGRATION_GUIDE.md | — | Workflow integration |
| **INDEX.md** | — | **This file** |

---

## ✨ Summary

This `.github/` directory provides:
- ✅ 6 GitHub Actions workflows (test, a11y, lint, security, deploy-gcp, deploy-aws)
- ✅ 3 issue templates (feature, bug, a11y)
- ✅ Code review enforcement (CODEOWNERS)
- ✅ Automated dependency updates (Dependabot)
- ✅ Comprehensive documentation (README, SETUP_CHECKLIST, INTEGRATION_GUIDE)
- ✅ GitHub Projects board configuration
- ✅ Cloud-neutral deployment (GCP Cloud Run + AWS template)
- ✅ WCAG 2.0 AA accessibility enforcement
- ✅ TDD enforcement (tests required before merge)

**All aligned with CLAUDE.md development workflow.**

---

**Next step**: Read `.github/SETUP_CHECKLIST.md` and follow the steps.
