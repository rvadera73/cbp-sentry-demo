---
name: Accessibility Issue
about: Report a WCAG 2.0 AA compliance violation
title: "[A11Y] "
labels: accessibility
assignees: ''

---

## Component Affected
*Which component or page has the accessibility issue?*

Example: "ReferralPackagePage.tsx — scoring section"

## WCAG 2.0 AA Criterion
*Which WCAG criterion is violated? ([reference](https://www.w3.org/WAI/WCAG21/quickref/))*

- [ ] **1.4.3 Contrast (Minimum)** — Text/background contrast < 4.5:1
- [ ] **2.1.1 Keyboard** — Element not reachable via Tab/Enter
- [ ] **2.1.2 No Keyboard Trap** — Focus stuck (can't Tab away)
- [ ] **2.4.7 Focus Visible** — No visible focus indicator
- [ ] **3.3.2 Labels or Instructions** — Form field not labeled
- [ ] **4.1.2 Name, Role, Value** — Missing/incorrect ARIA roles
- [ ] **4.1.3 Status Messages** — Alerts not announced to screen readers
- [ ] **Other** (specify): ________________

## Severity
*Impact on users.*

- [ ] **CRITICAL** — Major barrier (e.g., cannot complete core task)
- [ ] **MAJOR** — Significant difficulty (e.g., confusing but workaround exists)
- [ ] **MINOR** — Minor inconvenience (e.g., suboptimal experience)

## Type of Issue
*What kind of accessibility problem is it?*

- [ ] **Screen reader** — Content not announced, ARIA labels missing
- [ ] **Keyboard navigation** — Can't reach/use element with keyboard alone
- [ ] **Color contrast** — Text hard to read due to insufficient contrast
- [ ] **Focus management** — Focus indicator missing or hidden
- [ ] **Semantic HTML** — Buttons/links not marked up correctly
- [ ] **Motion/animation** — Flashing or motion causes seizure risk
- [ ] **Other**: ________________

## Description
*Describe the accessibility issue in detail.*

Example: "The 'Export PDF' button has yellow text (#FFD700) on white background, resulting in 1.2:1 contrast ratio (fails WCAG AA requirement of 4.5:1)"

## Steps to Identify
*How can someone verify this issue?*

Example:
1. Open ReferralPackagePage in Chrome
2. Use browser DevTools > Accessibility Inspector
3. Inspect "Export PDF" button
4. Check computed contrast ratio in Accessibility panel
5. Note: 1.2:1 (fails)

**OR** run accessibility test:
```bash
npm run test:a11y
```

## Screen Reader / Keyboard Test
*If applicable, describe what a screen reader user or keyboard-only user experiences.*

**Screen reader (NVDA/JAWS):**
Example: "When focusing the score field, NVDA announces 'text' with no label, instead of 'Confidence score, 91 out of 100'"

**Keyboard navigation:**
Example: "The 'Download' button in the referral section cannot be reached by pressing Tab, only by mouse click"

## Solution (Optional)
*Suggest how to fix this issue.*

Example:
- Change button text color to #003060 (navy) for 9.5:1 contrast ratio
- Add `aria-label="Export referral package as PDF"` to button
- Ensure button is keyboard-accessible with Tab + Enter

## Testing Checklist
*For developers fixing this issue.*

- [ ] Issue is reproducible with provided steps
- [ ] jest-axe reports no violations for this component
- [ ] Manual keyboard navigation test passed (Tab through all elements)
- [ ] Screen reader test passed (NVDA/JAWS announces all content correctly)
- [ ] Color contrast verified (4.5:1 normal text, 3:1 large text)
- [ ] Focus indicator visible (4px outline per USWDS spec)
- [ ] No code duplication (use USWDS components)

## Related Issues
*Link to related accessibility issues or PRs.*

Relates to #NNN (if applicable)
