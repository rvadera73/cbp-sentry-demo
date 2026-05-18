# WCAG 2.0 AA Accessibility Compliance

## Overview

Sentry must be fully accessible to all users, including those with visual, hearing, cognitive, and motor disabilities. This document specifies the **WCAG 2.0 AA** requirements and testing protocols before every commit.

**Key principle**: Accessibility is non-negotiable. Every component must pass `npm run test:a11y` before merge.

---

## WCAG 2.0 AA Standard Checklist

### 1. Perceivable — Information Must Be Presented Clearly

#### 1.4.3 Contrast (Minimum)
- **Requirement**: Text and interactive elements must have 4.5:1 contrast ratio (normal), 3:1 (large text, UI components)
- **Target**: All text on UI components
- **USWDS Guarantee**: Default USWDS theme meets 4.5:1 for all standard components
- **How to Test**:
  ```bash
  npx axe-core ui/src/views/**/*.tsx
  # or
  npm run test:a11y -- --report wcag2aa
  ```

**Color Palette** (from CLAUDE.md):
- Navy (primary): `#013060` — 13.8:1 on white background
- Teal (secondary): `#4AC4D3` — 4.6:1 on white background
- Orange (accent): `#E6800C` — 4.5:1 on white background
- Light blue (background): `#DBF3F6` — 1.2:1 on white (use only for backgrounds, never text)
- Dark teal (dark text): `#0B6980` — 8.2:1 on white background
- Slate (dark text): `#44546A` — 6.5:1 on white background

**Never use**:
- Red + green combinations (colorblind users)
- Low-contrast text (<4.5:1)
- Color as the only means of conveying information

#### 1.4.5 Images of Text
- **Requirement**: Text should never be embedded in images
- **Exception**: Logos, charts, diagrams (alternative text required)
- **Example**: Risk gauge visualizations must be SVG or canvas, not PNG with text burned in

#### 2.1.1 Keyboard Access
- **Requirement**: All functionality must be accessible via keyboard
- **Target**: Every interactive element (button, link, input, select)
- **How to Test**: Tab through entire page without touching mouse
  - Focus should be visible (4px outline, USWDS default)
  - Tab order should be logical (left-to-right, top-to-bottom)
  - No keyboard traps (user can Tab out of all elements)

#### 2.4.2 Page Titled
- **Requirement**: Every page must have a unique, descriptive `<title>`
- **Example**: "Sentry — Manifest Upload" not "Sentry App"
- **Implementation**:
  ```typescript
  <title>Sentry — Manifest Upload | CBP Illegal Transshipment Detection</title>
  ```

#### 2.4.3 Focus Order
- **Requirement**: Tab order must follow logical, visual order
- **Test**: `Tab` key should move focus in expected sequence
- **Fix**: Set `tabIndex` on custom components, ensure semantic HTML

#### 3.1.1 Language of Page
- **Requirement**: Primary language declared
- **Implementation**:
  ```html
  <html lang="en">
  ```

### 2. Operable — Users Must Be Able to Navigate and Interact

#### 2.1.2 No Keyboard Trap
- **Requirement**: Keyboard users can move focus away from all elements
- **Exception**: Modal dialogs (must have explicit close or Escape key)
- **Test**:
  ```javascript
  // Modal must close on Escape
  useEffect(() => {
    const handleEscape = (e) => {
      if (e.key === "Escape") closeModal();
    };
    document.addEventListener("keydown", handleEscape);
    return () => document.removeEventListener("keydown", handleEscape);
  }, []);
  ```

#### 2.2.1 Timing Adjustable
- **Requirement**: No auto-advances, auto-submits, or hidden time limits
- **Special case**: Refresh token timeout must warn user with dismissible alert + ability to extend session

#### 2.4.7 Focus Visible
- **Requirement**: When focused, interactive elements must be visually distinct
- **USWDS Standard**: 4px solid outline, navy color (`#013060`)
- **Never**: Remove focus outline (`:focus { outline: none; }`)
- **Custom focus**:
  ```css
  /* Approved USWDS focus style */
  :focus {
    outline: 4px solid #013060;
    outline-offset: 2px;
  }
  ```

#### 2.5.2 Pointer Cancellation
- **Requirement**: No functions triggered on mouse-down alone (down-event only)
- **Requirement**: Functions triggered on mouse-up or click (not down)
- **Example**:
  ```javascript
  /* ❌ Bad — triggers on mouse down */
  onMouseDown={() => deleteItem()}
  
  /* ✅ Good — triggers on click (mouse up) */
  onClick={() => deleteItem()}
  ```

### 3. Understandable — Content Must Be Clear

#### 3.2.1 On Focus
- **Requirement**: No unexpected context change when element gains focus
- **Test**: Tabbing through page should not trigger navigation, form submissions, or major state changes
- **Allowed**: Showing tooltip, loading preview

#### 3.2.2 On Input
- **Requirement**: No unexpected context change when user provides input
- **Test**: Changing dropdown value should not auto-submit form
- **Required**: Explicit "Submit" button
- **Exception**: Real-time search results (Google-like)

#### 3.3.1 Error Identification
- **Requirement**: When form submission fails, error must be:
  - Identified to the user programmatically (not just red color)
  - Linked to the form control that caused it
  - Described in plain language
- **Example**:
  ```typescript
  <input
    id="shipper_name"
    aria-invalid="true"
    aria-describedby="shipper_error"
    value={shipperName}
  />
  <div id="shipper_error" className="usa-error-message">
    Shipper name is required
  </div>
  ```

#### 3.3.2 Labels or Instructions
- **Requirement**: All form inputs must have associated labels
- **Implementation**:
  ```typescript
  <label htmlFor="manifest_file">Upload Manifest (Excel):</label>
  <input id="manifest_file" type="file" />
  ```

#### 3.3.4 Error Prevention
- **Requirement**: Submission confirmation before major destructive actions
- **Example**: "Confirm deletion of this referral package?" before delete

### 4. Robust — Must Work with All Assistive Technologies

#### 4.1.2 Name, Role, Value
- **Requirement**: All components must have:
  - **Name**: Accessible text label
  - **Role**: Semantic HTML or ARIA role
  - **Value**: Current state (checked, selected, disabled, etc.)
- **Test**:
  ```javascript
  // Good example
  <button aria-label="Close modal" onClick={closeModal}>
    ✕
  </button>
  
  // Bad example
  <div onClick={closeModal}>Close</div> // No role, no name
  ```

#### 4.1.3 Status Messages
- **Requirement**: Status messages (loading, success, error) must be announced to screen readers
- **Implementation**:
  ```typescript
  <div role="status" aria-live="polite" aria-atomic="true">
    {loadingMessage}
  </div>
  ```

---

## USWDS Component Accessibility Guarantees

All USWDS components come with built-in accessibility. Use them directly—don't customize:

| USWDS Component | Accessibility Guarantee | Do Not Override |
|---|---|---|
| Button | Focus outline, contrast, semantic `<button>` | `:focus` outline |
| Link | Underline, color contrast, semantic `<a>` | Text decoration |
| Input | Label association, error states, `aria-invalid` | Outline |
| Alert | `role="alert"`, `aria-live="polite"` | Role, aria-live |
| Table | Sortable headers, `aria-sort` | Semantic structure |
| Modal | Keyboard trap prevention, focus management | Escape key close |

---

## jest-axe Automated Testing

### Setup

```bash
npm install --save-dev jest-axe @axe-core/react
```

### Basic Test Pattern

```typescript
import { render, screen } from "@testing-library/react";
import { axe, toHaveNoViolations } from "jest-axe";

expect.extend(toHaveNoViolations);

describe("ManifestUploadForm", () => {
  it("should have no accessibility violations", async () => {
    const { container } = render(<ManifestUploadForm />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});
```

### Component-Level Tests

Create `__tests__/accessibility.spec.tsx` for every component:

```typescript
// ui/src/views/manifest/__tests__/accessibility.spec.tsx
import { axe, toHaveNoViolations } from "jest-axe";
import { render } from "@testing-library/react";
import ManifestTable from "../ManifestTable";

expect.extend(toHaveNoViolations);

describe("ManifestTable a11y", () => {
  it("table has proper headers and scope", async () => {
    const { container } = render(
      <ManifestTable
        manifests={[
          {
            id: "MF-001",
            shipper: "Test Shipper",
            hts_code: "7604.10.1000",
          },
        ]}
      />
    );
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it("table can be sorted by keyboard", async () => {
    const { getByRole } = render(
      <ManifestTable manifests={[/* ... */]} />
    );
    
    const headerButton = getByRole("button", { name: /sort by/i });
    headerButton.focus();
    
    // Verify focus is visible
    expect(headerButton).toHaveFocus();
    expect(headerButton).toHaveStyle("outline: 4px solid");
  });
});
```

### Page-Level Integration Tests

```typescript
// ui/src/pages/__tests__/ScoringPage.a11y.spec.tsx
import { axe, toHaveNoViolations } from "jest-axe";
import { render, screen, waitFor } from "@testing-library/react";
import ScoringPage from "../ScoringPage";

expect.extend(toHaveNoViolations);

describe("ScoringPage a11y", () => {
  it("page has proper landmarks", async () => {
    const { container } = render(<ScoringPage />);
    
    // Verify landmarks exist
    expect(container.querySelector("main")).toBeInTheDocument();
    expect(container.querySelector("nav")).toBeInTheDocument();
    
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it("can navigate with keyboard only", async () => {
    const { getByRole } = render(<ScoringPage />);
    
    // Start at top
    expect(document.body).toHaveFocus();
    
    // Tab to first interactive element
    userEvent.tab();
    const firstButton = getByRole("button", { name: /upload/i });
    expect(firstButton).toHaveFocus();
    
    // Continue tabbing through page
    // Verify no keyboard traps
    for (let i = 0; i < 50; i++) {
      userEvent.tab();
      expect(document.activeElement).not.toBe(document.body);
    }
  });
});
```

---

## Screen Reader Testing (Manual Protocol)

### NVDA Testing (Windows/Linux)

1. **Download**: https://www.nvaccess.org/download/
2. **Enable**: Start NVDA
3. **Test protocol**:
   ```
   Insert+F7 → Open developer console (error check)
   Tab through page → Listen to focus announcements
   Insert+B → Next button
   Insert+H → Next heading
   Insert+L → Next list
   Insert+T → Next table
   ```
4. **Check**:
   - Page title announced on load
   - Form labels announced before inputs
   - Buttons have descriptive labels (not just "Click here")
   - Tables announced with row/column headers
   - Error messages associated with form fields

### JAWS Testing (Premium, Windows)

1. **Toggle forms mode**: Insert+Z
2. **Read by line**: Arrow keys
3. **Read by field**: Tab key
4. **Test features**:
   - Form labels read correctly
   - Required fields announced
   - Error states announced
   - Button purposes clear

### VoiceOver Testing (Mac)

1. **Enable**: System Preferences → Accessibility → VoiceOver
2. **Nav**: VO+U (rotor), VO+Right Arrow (next)
3. **Test**:
   - Headings properly nested (h1 → h2 → h3, not h1 → h3)
   - Lists announced with item count
   - Interactive elements have descriptive labels

---

## Keyboard Navigation Checklist

### Before Committing

- [ ] Tab through entire page without mouse
- [ ] Focus outline visible on every focusable element (4px navy)
- [ ] Tab order is logical (left-to-right, top-to-bottom)
- [ ] No keyboard traps (can Tab out of modals, dropdowns)
- [ ] Enter/Space activate buttons
- [ ] Arrow keys navigate lists/tabs
- [ ] Escape closes modals/dropdowns
- [ ] All functionality available via keyboard

### Custom Component Focus Management

```typescript
// Recommended pattern for custom components
const CustomComponent = forwardRef((props, ref) => {
  const [isFocused, setIsFocused] = useState(false);

  return (
    <div
      ref={ref}
      role="button"
      tabIndex={0}
      onFocus={() => setIsFocused(true)}
      onBlur={() => setIsFocused(false)}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          props.onClick?.();
        }
      }}
      style={{
        outline: isFocused ? "4px solid #013060" : "none",
        outlineOffset: isFocused ? "2px" : "0",
      }}
    >
      {props.children}
    </div>
  );
});
```

---

## Semantic HTML Requirements

### Use Semantic Elements, Not Divs

```typescript
/* ❌ Bad — div with role */
<div role="button" onClick={handleClick}>
  Click me
</div>

/* ✅ Good — semantic button */
<button onClick={handleClick}>Click me</button>

/* ❌ Bad — div with role */
<div role="heading" aria-level="1">Page Title</div>

/* ✅ Good — semantic heading */
<h1>Page Title</h1>

/* ❌ Bad — no label */
<input type="text" />

/* ✅ Good — associated label */
<label htmlFor="name">Name:</label>
<input id="name" type="text" />
```

### Heading Hierarchy

- Every page must have exactly one `<h1>` (page title)
- Headings must nest properly: h1 → h2 → h3 (no h1 → h3 jumps)
- Use headings for structure, not styling
- Example:
  ```typescript
  <h1>Sentry Dashboard</h1>
  <section>
    <h2>Upload Manifest</h2>
    <h3>Step 1: Select File</h3>
    <h3>Step 2: Confirm Details</h3>
  </section>
  ```

---

## ARIA Labels and Descriptions

### When to Use ARIA

- **Only when semantic HTML is insufficient**
- **Never override semantics**: Don't use `role="button"` on a `<div>` when `<button>` exists
- **Always supplement HTML**, never replace it

### Pattern: Hidden Labels

```typescript
/* For icon-only buttons */
<button aria-label="Close modal">
  <CloseIcon />
</button>

/* For screen reader context */
<form>
  <label htmlFor="manifest">Upload manifest:</label>
  <input id="manifest" type="file" />
  <span id="manifest-help" className="usa-hint">
    Accepted formats: Excel (.xlsx, .xls), CSV
  </span>
  <input aria-describedby="manifest-help" />
</form>
```

### Pattern: Live Regions

```typescript
/* For loading, success, error messages */
<div role="status" aria-live="polite" aria-atomic="true">
  {loadingMessage}
</div>

/* For alert boxes */
<div role="alert" aria-live="assertive">
  {errorMessage}
</div>
```

---

## Color and Contrast

### Required Contrast Ratios

| Text Type | Ratio | Example |
|---|---|---|
| Normal text (≥14px) | 4.5:1 | Body copy, labels |
| Large text (≥18px or 14px bold) | 3:1 | Headings, large UI text |
| UI components (buttons, inputs) | 3:1 | Button borders, focus outline |
| Graphical elements | 3:1 | Icons, chart axes |

### Testing Contrast

```bash
# Use WebAIM contrast checker
# https://webaim.org/resources/contrastchecker/

# Or programmatic test
npm run test:a11y -- --rule color-contrast
```

### Color Blindness Considerations

- **Never use color alone** to convey information
- Pair colors with patterns, icons, or text
- Example:
  ```typescript
  /* ❌ Bad — red alone means error */
  <div style={{ color: "red" }}>Error</div>
  
  /* ✅ Good — red + icon + text */
  <div style={{ color: "red" }}>
    ❌ Error: {errorMessage}
  </div>
  ```

---

## Testing Strategy (TDD + A11y)

### Before Committing

```bash
# 1. Run unit tests
npm run test

# 2. Run accessibility tests
npm run test:a11y

# 3. Manual keyboard navigation
# Tab through entire UI, verify focus visible

# 4. Screen reader spot-check (if adding new component)
# NVDA: Insert+F7, listen to page announcement

# 5. Commit only if all pass
git commit -m "feat: add referral package viewer

- Fully WCAG 2.0 AA compliant
- jest-axe passes
- Keyboard navigation tested
- Screen reader verified (NVDA)"
```

### GitHub Actions Workflow

```yaml
# .github/workflows/a11y.yml
name: WCAG 2.0 Accessibility Check

on: [pull_request]

jobs:
  accessibility:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: 18
      - run: npm ci
      - run: npm run test:a11y -- --force-exit
      - run: npm run test:a11y:e2e -- --force-exit
```

---

## Common Violations & Fixes

### Violation: Missing Form Labels

```typescript
/* ❌ Before */
<input type="text" placeholder="Shipper name" />

/* ✅ After */
<label htmlFor="shipper">Shipper Name:</label>
<input id="shipper" type="text" placeholder="Enter shipper name" />
```

### Violation: Images Without Alt Text

```typescript
/* ❌ Before */
<img src="greenfield-logo.png" />

/* ✅ After */
<img src="greenfield-logo.png" alt="Greenfield Aluminum company logo" />

/* For decorative images */
<img src="divider.png" alt="" aria-hidden="true" />
```

### Violation: Empty Buttons

```typescript
/* ❌ Before */
<button onClick={handleDelete}>
  <TrashIcon />
</button>

/* ✅ After */
<button onClick={handleDelete} aria-label="Delete referral package">
  <TrashIcon />
</button>
```

### Violation: Color-Only Information

```typescript
/* ❌ Before */
<div style={{ color: "red" }}>High Risk</div>
<div style={{ color: "green" }}>Low Risk</div>

/* ✅ After */
<div style={{ color: "red" }}>
  <strong>🔴 High Risk</strong>
</div>
<div style={{ color: "green" }}>
  <strong>🟢 Low Risk</strong>
</div>
```

### Violation: Keyboard Trap

```typescript
/* ❌ Before — user can't escape */
<input onKeyDown={(e) => { if (e.key === "Tab") e.preventDefault(); }} />

/* ✅ After — only Escape traps, which opens escape button */
<Modal onEscapeKeyDown={closeModal}>
  <button onClick={closeModal}>Close</button>
</Modal>
```

---

## Pre-Commit Checklist

Before every commit:

- [ ] `npm run test` passes
- [ ] `npm run test:a11y` passes (0 violations)
- [ ] Keyboard navigation tested (Tab through page)
- [ ] Focus outline visible (4px navy)
- [ ] No form labels missing
- [ ] All buttons have text or aria-label
- [ ] Images have alt text
- [ ] Color contrast ≥4.5:1 for text
- [ ] No keyboard traps (can escape modals)
- [ ] Screen reader spot-check (NVDA ~2 min if new component)

---

## Resources

- **WCAG 2.0 Guidelines**: https://www.w3.org/WAI/WCAG21/quickref/
- **jest-axe**: https://github.com/nickcolley/jest-axe
- **USWDS Accessibility**: https://designsystem.digital.gov/documentation/designers/
- **WebAIM**: https://webaim.org/articles/
- **ARIA Best Practices**: https://www.w3.org/WAI/ARIA/apg/

---

## Contact & Questions

For accessibility questions or to report violations:
1. Open GitHub Issue with `accessibility` label
2. Include: Component name, test output, expected behavior
3. Assign to @[accessibility-reviewer]
