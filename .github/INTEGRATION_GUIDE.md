# GitHub CI/CD Integration Guide

This guide shows how GitHub CI/CD workflows integrate with the development workflow described in `CLAUDE.md`.

---

## Development Workflow Loop

```
1. CREATE ISSUE
   ↓ (GitHub Issues)
2. CREATE BRANCH
   ↓ (git checkout -b)
3. WRITE TEST (TDD)
   ↓ (npm run test -- --watch)
4. IMPLEMENT FEATURE
   ↓ (Code + tests)
5. RUN LOCAL CHECKS
   ├─ pytest api/tests/
   ├─ npm run test
   └─ npm run test:a11y
   ↓ (git commit -m)
6. PUSH & CREATE PR
   ↓ (GitHub Actions trigger)
7. WORKFLOWS RUN
   ├─ test.yml (pytest + vitest)
   ├─ a11y.yml (jest-axe)
   ├─ lint.yml (black, prettier)
   └─ security.yml (CodeQL, pip-audit)
   ↓ (All green ✓)
8. CODE REVIEW
   ├─ CODEOWNERS approval required
   └─ PR comments from maintainers
   ↓ (Approve + merge)
9. MERGE TO MAIN
   ↓ (GitHub Actions trigger)
10. DEPLOY
    ├─ deploy-gcp.yml (Cloud Run)
    └─ deploy-aws.yml (AWS Lambda/ECS)
    ↓ (Done ✓)
```

---

## Step-by-Step: From Issue to Deployment

### Step 1: Create Issue (GitHub)

**Go to**: Repo → Issues → New Issue

**Select template**: Feature Request / Bug Report / Accessibility

**Example issue**:
```
Title: [FEATURE] Add manifest Excel parser (#123)

Description:
- Extracts shipper, consignee, HTS code from Excel manifest
- Validates required fields
- Flags suspicious entries

Horizon: H3 (72-hour trigger)
Type: feature
Priority: high
Area: api
```

**Actions**:
- [ ] Add labels: `horizon/H3`, `type/feature`, `priority/high`, `area/api`
- [ ] Add to project board (moves to Backlog column)
- [ ] Add acceptance criteria in issue body

---

### Step 2: Create Branch (Local Git)

From CLAUDE.md:
```bash
git checkout -b feat/issue-123-manifest-parser
```

**Naming convention**: `{type}/{issue-number}-{short-name}`
- `feat/` — New feature
- `fix/` — Bug fix
- `refactor/` — Code cleanup
- `docs/` — Documentation
- `test/` — Testing improvements

---

### Step 3: Write Test First (TDD)

From CLAUDE.md: **"Write test first (RED phase)"**

**Backend test** (`api/tests/test_manifest_parser.py`):
```python
import pytest
from api.services.ingest.manifest import ManifestParser

def test_parse_excel_manifest():
    """Test manifest parser extracts shipper, consignee, HTS code"""
    manifest = ManifestParser.from_excel("test_manifest.xlsx")
    
    assert manifest.shipper == "Greenfield Trading"
    assert manifest.consignee == "US Importer Inc"
    assert manifest.line_items[0].hts_code == "7604.10.1000"

def test_validate_required_fields():
    """Test parser validates required fields"""
    with pytest.raises(ValueError):
        ManifestParser.from_excel("missing_fields.xlsx")

def test_flag_suspicious_entries():
    """Test parser flags entries with price anomalies"""
    manifest = ManifestParser.from_excel("suspicious.xlsx")
    assert manifest.line_items[0].risk_flags["price_anomaly"] == True
```

**Run locally** (watch mode):
```bash
cd api
pytest tests/test_manifest_parser.py -v --tb=short --watch
```

**Status**: ❌ RED (test fails, code doesn't exist)

---

### Step 4: Implement Feature

**Create implementation** (`api/services/ingest/manifest.py`):
```python
import openpyxl
from pydantic import BaseModel, Field

class LineItem(BaseModel):
    hts_code: str
    description: str
    unit_price: float
    risk_flags: dict = Field(default_factory=dict)

class Manifest(BaseModel):
    shipper: str
    consignee: str
    line_items: list[LineItem]

class ManifestParser:
    @staticmethod
    def from_excel(filepath: str) -> Manifest:
        wb = openpyxl.load_workbook(filepath)
        ws = wb.active
        
        # Extract shipper/consignee from headers
        shipper = ws['B2'].value
        consignee = ws['B3'].value
        
        # Extract line items
        line_items = []
        for row in ws.iter_rows(min_row=5):
            hts_code = row[0].value
            description = row[1].value
            unit_price = row[3].value
            
            flags = {}
            if unit_price < 10:  # Flag anomaly
                flags['price_anomaly'] = True
            
            line_items.append(LineItem(
                hts_code=hts_code,
                description=description,
                unit_price=unit_price,
                risk_flags=flags
            ))
        
        return Manifest(shipper=shipper, consignee=consignee, line_items=line_items)
```

**Run tests again**:
```bash
pytest tests/test_manifest_parser.py -v
```

**Status**: ✅ GREEN (tests pass)

---

### Step 5: Check Accessibility (UI changes only)

**If touching React components**:
```bash
cd ui
npm run test:a11y
```

**Example**: If building a form for manifest upload
- [ ] Form fields labeled (ARIA labels)
- [ ] Color contrast 4.5:1 (USWDS default)
- [ ] Keyboard navigable (Tab, Enter)
- [ ] Focus visible (4px outline)

---

### Step 6: Commit & Push

**From CLAUDE.md**:
```bash
git commit -m "feat: add manifest Excel parser

- Extracts shipper, consignee, HTS code from Excel
- Validates required fields (raises ValueError)
- Flags suspicious entries (price anomalies)
- Tests: 3 test cases, all green

Close #123"

git push origin feat/issue-123-manifest-parser
```

**Key points**:
- Commit message references issue (`Close #123`)
- Describes WHAT changed and WHY
- Doesn't duplicate test names (tests speak for themselves)

---

### Step 7: GitHub Actions Workflows Trigger

When you push, **GitHub Actions automatically run**:

#### **test.yml** ✅
- Runs `pytest api/tests/` (your new tests)
- Runs `npm run test` (frontend tests)
- Uploads coverage report
- Status: ✅ PASS (if all tests pass)

#### **a11y.yml** ✅ (if UI changes)
- Runs `npm run test:a11y`
- Checks WCAG 2.0 AA violations
- Status: ✅ PASS (if no violations)

#### **lint.yml** ✅
- Runs `black api/` (Python formatter)
- Runs `isort api/` (import sorter)
- Runs prettier (TypeScript formatter)
- Status: ✅ PASS (if code is formatted)

#### **security.yml** ✅
- Runs `pip-audit` (Python dependencies)
- Runs `npm audit` (Node dependencies)
- Runs CodeQL (static analysis)
- Status: ✅ PASS (if no vulnerabilities)

**All checks pass** → Green checkmark on PR

---

### Step 8: Create Pull Request

**Go to**: GitHub → Pull Requests → New PR

**Branch**: `feat/issue-123-manifest-parser` → `main`

**Title**: `feat: add manifest Excel parser`

**Body**: PR template auto-fills:
```markdown
## Description
Fixes #123

## Changes
- Extracts shipper, consignee, HTS code from Excel
- Validates required fields
- Flags suspicious entries

## Testing
- [x] Unit tests pass (pytest)
- [x] WCAG 2.0 AA checks pass
- [x] Keyboard navigation tested
```

**GitHub Actions status**:
- [x] test.yml — ✅ PASS
- [x] a11y.yml — ✅ PASS (if UI changes)
- [x] lint.yml — ✅ PASS
- [x] security.yml — ✅ PASS

---

### Step 9: Code Review

**From CLAUDE.md**: *"Require at least 1 approval from CODEOWNERS"*

**CODEOWNERS** (`.github/CODEOWNERS`):
```
/api/ @rvadera73
/ui/ @rvadera73
```

**Review process**:
1. Maintainer reviews code
2. Checks:
   - Matches USWDS patterns (UI only)
   - No code duplication
   - Tests cover happy path + edge cases
   - Referral package structure unchanged (if applicable)
3. Approves or requests changes

---

### Step 10: Merge & Deploy

**Merge**: Click "Merge pull request"

**What happens automatically**:
1. PR is merged to `main`
2. GitHub Actions trigger `deploy-gcp.yml`
3. Workflow:
   - Builds Docker images (api + ui)
   - Pushes to Artifact Registry
   - Deploys to Cloud Run:
     - `sentry-api` service
     - `sentry-ui` service
   - Sets env vars: `DEMO_MODE=false`, `ENVIRONMENT=production`
4. Issue #123 auto-closes (from commit message)
5. GitHub Projects board auto-moves to "Done"

**Verify deployment**:
```bash
# Check Cloud Run services
gcloud run services list --region us-central1

# View logs
gcloud run services logs read sentry-api --region us-central1 --limit 50
```

---

## Workflow Files Reference

| File | Trigger | Purpose | Branch |
|------|---------|---------|--------|
| `test.yml` | PR + Push | pytest + vitest + coverage | main, develop |
| `a11y.yml` | PR (UI only) | WCAG 2.0 AA checks | main, develop |
| `lint.yml` | PR + Push | Code formatting | main, develop |
| `security.yml` | PR + weekly | Dependency audit + CodeQL | main, develop |
| `deploy-gcp.yml` | Merge to main | Build + deploy to Cloud Run | main only |
| `deploy-aws.yml` | Manual only | Deploy to AWS Lambda/ECS | aws-main |

---

## GitHub Projects Board Integration

**Automatic board updates**:

| Event | Board Action |
|-------|--------------|
| New issue created | → Backlog column |
| Label `status/ready` added | → Ready for Development |
| Label `status/in-progress` added | → In Progress |
| PR created (links issue) | → In Review |
| PR merged (with "Close #NNN") | → Done (auto-closes issue) |

**Manual workflow** (from issue):
1. Issue created (Backlog)
2. Add acceptance criteria (Backlog)
3. Add `status/ready` label (Ready for Development)
4. Assign to developer (In Progress)
5. Create PR (In Review)
6. Merge PR (Done) ← Issue auto-closes

---

## Local Testing Checklist (Before Pushing)

From CLAUDE.md: *"Checklist before committing"*

**Run these locally**:
```bash
# Backend tests
cd api
pip install -r requirements.txt
pytest tests/ -v --tb=short

# Frontend tests
cd ../ui
npm ci
npm run test
npm run type-check

# Accessibility (UI only)
npm run test:a11y

# Local deployment
docker-compose up --build
# Verify: http://localhost:3000 (UI) + http://localhost:8000/docs (API)
```

**All green?** ✅ Safe to commit and push.

---

## Troubleshooting

### Issue: GitHub Actions workflow fails

**Check 1**: Are secrets configured?
- Go to Settings → Secrets → Actions
- Verify `GCP_PROJECT_ID`, `WIF_PROVIDER`, `WIF_SERVICE_ACCOUNT` are set

**Check 2**: Does code pass local tests?
```bash
pytest api/tests/ -v
npm run test
npm run test:a11y
```

**Check 3**: View workflow logs
- Go to Pull Request → "Checks" tab
- Click failed workflow → "View logs"
- Look for error message

### Issue: deploy-gcp.yml fails

**Check 1**: Cloud Run services exist?
```bash
gcloud run services list --region us-central1
```

**Check 2**: Artifact Registry bucket exists?
```bash
gcloud artifacts repositories list --location=us-central1
```

**Check 3**: GCP service account has permissions?
```bash
gcloud projects get-iam-policy $PROJECT_ID \
  --flatten=bindings[].members \
  --filter=bindings.members:github-actions@*
```

### Issue: A11y tests fail

**Check 1**: Is jest-axe installed?
```bash
npm list jest-axe
```

**Check 2**: Create test file
```bash
touch ui/tests/accessibility.spec.tsx
```

**Check 3**: Run locally
```bash
npm run test:a11y
```

---

## Integration with CLAUDE.md

**CLAUDE.md Requirement**: *"Tests pass (`npm run test`), WCAG 2.0 AA (`npm run test:a11y`)"*

**How GitHub CI/CD enforces it**:
- `test.yml` — Runs `pytest api/tests/` and `npm run test`
- `a11y.yml` — Runs `npm run test:a11y`
- Branch protection — **Requires both to pass** before merge

**Result**: You cannot merge code with failing tests. GitHub enforces CLAUDE.md requirements automatically.

---

## Key Files

- **Workflows**: `.github/workflows/*.yml`
- **Issue templates**: `.github/ISSUE_TEMPLATE/*.md`
- **Board config**: `.github/projects/board.yml`
- **Code owners**: `.github/CODEOWNERS`
- **Dependency updates**: `.github/dependabot.yml`
- **Setup guide**: `.github/SETUP_CHECKLIST.md`
- **CI/CD docs**: `.github/README.md` (this directory)

---

## Next Steps

1. **Complete `.github/SETUP_CHECKLIST.md`** (branch protection, GCP secrets, etc.)
2. **Create first test issue** to verify workflow end-to-end
3. **Test a small PR** to ensure GitHub Actions pass
4. **Reference CLAUDE.md** for development workflow during coding

---

**Ready to start?** See `CLAUDE.md` § "Development Workflow" for step-by-step guide.
