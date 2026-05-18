---
name: Feature Request
about: Propose a new feature or enhancement
title: "[FEATURE] "
labels: enhancement
assignees: ''

---

## Description
*Provide a clear and concise description of the feature.*

Example: "Add ability to export referral package as PDF for enforcement team"

## Business Context
*Which product horizon does this feature belong to?*

- [ ] **H1** — Macro corridor analysis (weeks before shipment)
- [ ] **H2** — Pre-manifest intelligence (14-22 days before)
- [ ] **H3** — Full assessment + referral package (72-hour trigger)
- [ ] **Other** (specify): ________________

## Acceptance Criteria
*What constitutes "done" for this feature?*

- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3

Example:
- [ ] API endpoint `/referral/{id}/export?format=pdf` returns valid PDF
- [ ] PDF includes all 14 tables from referral package spec
- [ ] PDF renders correctly in Chrome, Safari, Firefox
- [ ] File size < 5MB for typical shipment

## Testing Approach (TDD)
*Describe how this feature will be tested.*

- [ ] Unit tests (pytest for backend, vitest for frontend)
- [ ] Integration tests
- [ ] E2E tests (if applicable)

Example:
```python
# api/tests/test_referral_export.py
def test_referral_export_pdf_format():
    response = client.get("/referral/SENTRY-001/export?format=pdf")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert len(response.content) > 0
```

## WCAG 2.0 AA Considerations
*Does this feature touch the UI? What accessibility requirements apply?*

- [ ] New React component (must pass jest-axe)
- [ ] Forms or input fields (must be keyboard-navigable)
- [ ] Charts/visualizations (must support color contrast 4.5:1)
- [ ] Table display (must be semantically marked up)
- [ ] No WCAG impact (backend-only feature)

Example:
- [ ] Export button has visible focus indicator (4px outline)
- [ ] "Export as PDF" label is announced by screen readers
- [ ] PDF file download uses `<a download>` not custom JS

## Related Issues
*Link to related feature requests, bugs, or proposals.*

Relates to #NNN (if applicable)

## Proposed Implementation (Optional)
*Suggest technical approach if you have one.*

Example:
- Use `reportlab` Python library for PDF generation
- Add export button to ReferralPackagePage.tsx
- Store PDF in Cloud Storage (GCS / S3) with 30-day retention
