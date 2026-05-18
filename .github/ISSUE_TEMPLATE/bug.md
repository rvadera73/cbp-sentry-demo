---
name: Bug Report
about: Report a defect or regression
title: "[BUG] "
labels: bug
assignees: ''

---

## Description
*Briefly describe the issue.*

Example: "Referral package score displays as NaN when confidence is undefined"

## Steps to Reproduce
*Provide exact steps to replicate the bug.*

1. Go to...
2. Upload...
3. Click...
4. Observe...

Example:
1. Go to `/scoring` page
2. Upload manifest with missing confidence field
3. Click "Generate referral"
4. Observe score field shows "NaN" instead of "0"

## Expected Behavior
*What should happen?*

The score should display as "0" or be hidden if confidence is undefined, with a warning message explaining why.

## Actual Behavior
*What actually happens?*

The score displays as "NaN" (not a number), which breaks the UI layout and confuses officers.

## Environment
*In which environment did this occur?*

- [ ] **Local** (docker-compose)
- [ ] **Staging** (Cloud Run)
- [ ] **Production** (Cloud Run)

**Affected Component**: Scoring page / ReferralPackagePage.tsx

**Browser/System** (if frontend bug):
- Browser: Chrome 131 / Safari 18 / Firefox 133
- OS: Windows 11 / macOS / Ubuntu 22.04
- Screen reader (if a11y related): NVDA / JAWS 2024

## WCAG Impact (if applicable)
*Does this bug affect accessibility?*

- [ ] **None** — Backend/logic only
- [ ] **Color contrast** — Text unreadable due to low contrast
- [ ] **Keyboard navigation** — Can't reach element with Tab
- [ ] **Screen reader** — Content not announced properly
- [ ] **Focus visible** — Focus indicator missing or obscured

Example:
- [ ] **Keyboard navigation** — "Export PDF" button can't be reached with Tab, only works with mouse

## Error Logs
*Include relevant error messages or stack traces.*

```
TypeError: Cannot read property 'toFixed' of undefined
  at ReferralScore.tsx:45
```

## Checklist
- [ ] I have checked for duplicate issues
- [ ] I can reproduce this bug consistently
- [ ] I have provided steps to reproduce
- [ ] I have checked the browser console for errors (frontend bugs)

## Related Issues
*Link to related bugs or PRs.*

Relates to #NNN (if applicable)
