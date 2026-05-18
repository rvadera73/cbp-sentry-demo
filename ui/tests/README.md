# Sentry CBP UI Tests

## Overview

This directory contains the **Test-Driven Development (TDD) skeleton** for the Sentry CBP React UI. All tests are written first (RED phase) before implementation.

## Philosophy

**Red → Green → Refactor**

1. **RED**: Write tests that *fail* (no implementation yet)
2. **GREEN**: Implement React components to pass tests
3. **REFACTOR**: Improve code while keeping tests green

This repository begins in the **RED phase**. Tests serve as executable specifications.

## Test Structure

### Setup & Configuration

| File | Purpose |
|------|---------|
| `setup.ts` | Vitest + React Testing Library + jest-axe initialization |
| `vitest.config.ts` | Vitest configuration (jsdom, coverage, globals) |

### Component Tests

| Module | Coverage |
|--------|----------|
| `components/accessibility.spec.tsx` | WCAG 2.0 AA compliance for all components |
| `components/ManifestTable.spec.tsx` | Manifest data table rendering, sorting, keyboard nav |
| `components/ScoreGauge.spec.tsx` | Risk score gauge (0-100), color thresholds, animation |

### Page Tests

| Module | Coverage |
|--------|----------|
| `pages/ReferralPackagePage.spec.tsx` | Full referral JSON display, expandable sections, PDF export |
| `pages/GraphPage.spec.tsx` | Entity graph explorer, node interaction, why-connected |

## Running Tests

### Prerequisites

```bash
npm install
```

### Run All Tests

```bash
npm test
```

### Run Specific Test File

```bash
npm test components/ManifestTable.spec.tsx
```

### Run with Coverage

```bash
npm test -- --coverage
```

### Run in Watch Mode

```bash
npm test -- --watch
```

### Run UI Dashboard

```bash
npm run test:ui
```

This opens an interactive browser dashboard showing test results, coverage, and code.

## Test Patterns

### Component Tests with React Testing Library

```typescript
import { render, screen } from "@testing-library/react";
import { ScoreGauge } from "@/components/ScoreGauge";

it("should render score", () => {
  render(<ScoreGauge score={91} />);
  expect(screen.getByText("91")).toBeInTheDocument();
});
```

### Async Testing

```typescript
import userEvent from "@testing-library/user-event";

it("should handle click", async () => {
  const user = userEvent.setup();
  render(<Button>Click</Button>);

  const button = screen.getByRole("button");
  await user.click(button);

  expect(/* ... */);
});
```

### jest-axe Accessibility Testing

```typescript
import { axe, toHaveNoViolations } from "jest-axe";

expect.extend(toHaveNoViolations);

it("should have no accessibility violations", async () => {
  const { container } = render(<YourComponent />);
  const results = await axe(container);
  expect(results).toHaveNoViolations();
});
```

### Mocking User Interactions

```typescript
import { vi } from "vitest";

it("should call handler on submit", async () => {
  const mockSubmit = vi.fn();
  render(<Form onSubmit={mockSubmit} />);

  const button = screen.getByRole("button", { name: /submit/i });
  await userEvent.click(button);

  expect(mockSubmit).toHaveBeenCalled();
});
```

## Test Organization

### By Concern

- **accessibility.spec.tsx**: WCAG 2.0 AA compliance (jest-axe, contrast, keyboard nav)
- **ManifestTable.spec.tsx**: Table rendering and data display
- **ScoreGauge.spec.tsx**: Visual component (gauge animation, color thresholds)
- **ReferralPackagePage.spec.tsx**: Complex page with multiple sections
- **GraphPage.spec.tsx**: Interactive graph explorer with sidebar

### Test Class Structure

Each test file uses `describe` blocks for organization:

```typescript
describe("ComponentName", () => {
  describe("Rendering", () => {
    it("should render...");
    it("should display...");
  });

  describe("User Interaction", () => {
    it("should handle click...");
  });

  describe("Accessibility", () => {
    it("should pass jest-axe...");
  });
});
```

## Accessibility Testing

All components **must** pass WCAG 2.0 AA compliance. Tests check:

### jest-axe Automated Checks
```typescript
it("should pass jest-axe scan", async () => {
  const { container } = render(<Component />);
  const results = await axe(container);
  expect(results).toHaveNoViolations();
});
```

### Color Contrast (4.5:1 minimum for text)
- jest-axe automatically checks contrast ratios
- Use CSS color palette:
  - Dark text: `#333333` or darker
  - Light backgrounds: `#ffffff` or lighter
  - Ensure ratio >= 4.5:1

### Keyboard Navigation
```typescript
it("should navigate with Tab key", async () => {
  const user = userEvent.setup();
  render(<Component />);

  await user.tab();
  expect(document.activeElement).toBe(/* interactive element */);
});
```

### ARIA Labels & Roles
```typescript
it("should have ARIA labels", () => {
  render(<Button aria-label="Close dialog">×</Button>);
  expect(screen.getByRole("button", { name: /close/i })).toBeInTheDocument();
});
```

## Greenfield Test Case

The Greenfield aluminum case is the canonical test scenario:

```typescript
const greenfield_package = {
  package_id: "SENTRY-2026-001",
  shipment_id: "SAMPLE-BOL-2026-001",
  score: 91,
  confidence_level: "HIGH",
  recommended_action: "EXAMINE_ON_ARRIVAL",
  sections: {
    shipment_id: { bill_id: "SAMPLE-BOL-2026-001", ... },
    line_items: [ { hts_code: "7604.10.1000", ... } ],
    score_breakdown: { total: 91, components: [ ... ] },
    data_sources: [ { name: "ISF Data Element 9", ... } ],
  },
};
```

Use this in tests:

```typescript
it("should display Greenfield package", () => {
  render(<ReferralPackagePage package={greenfield_package} />);
  expect(screen.getByText("SENTRY-2026-001")).toBeInTheDocument();
});
```

## Coverage Goals

- **Components**: 80%+ coverage
- **Pages**: 75%+ coverage
- **Overall**: 80%+ coverage

Current coverage: **TBD** (skeleton phase)

View coverage report:

```bash
npm test -- --coverage
# Opens htmlcov/index.html
```

## Common Test Assertions

### DOM Elements

```typescript
// Check if element exists
expect(screen.getByText("Hello")).toBeInTheDocument();

// Check element visibility
expect(screen.getByRole("button")).toBeVisible();

// Check element attributes
expect(screen.getByRole("button")).toHaveAttribute("aria-label", "Submit");

// Check element classes
expect(element).toHaveClass("btn-primary");
```

### User Interactions

```typescript
// Click
await user.click(screen.getByRole("button"));

// Type
await user.type(screen.getByLabelText("Email"), "test@example.com");

// Tab
await user.tab();

// Keyboard
await user.keyboard("{Enter}");
```

### Async Operations

```typescript
// Wait for element
await waitFor(() => {
  expect(screen.getByText("Loaded")).toBeInTheDocument();
});

// Wait with custom conditions
await waitFor(() => expect(mockFetch).toHaveBeenCalled());
```

## Debugging Tests

### View Full Output

```bash
npm test -- --reporter=verbose
```

### Print to Console

```typescript
it("should debug", () => {
  render(<Component />);
  console.log(screen.debug());  // Print DOM tree
});
```

Run with output:

```bash
npm test -- --reporter=verbose 2>&1 | grep -A 50 "ComponentName"
```

### Interactive Debugging

```bash
npm run test:ui
# Opens browser dashboard
```

### Inspect Rendered HTML

```typescript
it("should inspect", () => {
  const { container } = render(<Component />);
  expect(container.innerHTML).toMatch(/expected/);
});
```

## Best Practices

### Do

✅ **Test user interactions, not implementation**
```typescript
// Good: Tests what user sees
it("should submit form on Enter", async () => {
  const user = userEvent.setup();
  render(<Form onSubmit={mockSubmit} />);
  await user.keyboard("{Enter}");
  expect(mockSubmit).toHaveBeenCalled();
});
```

✅ **Use semantic queries (getByRole, getByLabelText)**
```typescript
// Good: Finds by accessible name
const button = screen.getByRole("button", { name: /submit/i });

// Avoid: Implementation detail
const button = screen.getByTestId("submit-button");
```

✅ **Test accessibility alongside functionality**
```typescript
it("should be accessible and functional", async () => {
  const { container } = render(<Component />);

  // Functional test
  await user.click(screen.getByRole("button"));

  // Accessibility test
  const results = await axe(container);
  expect(results).toHaveNoViolations();
});
```

### Don't

❌ **Mock React internals**
```typescript
// Avoid: Over-mocking
vi.mock("react", () => ({ /* ... */ }));
```

❌ **Test CSS/styling directly**
```typescript
// Avoid: Tests brittle CSS
expect(element).toHaveStyle("color: red");

// Better: Test via jest-axe (contrast, visibility)
```

❌ **Use hardcoded timeouts**
```typescript
// Avoid: Brittle delays
setTimeout(() => expect(...), 1000);

// Better: Use waitFor
await waitFor(() => expect(...));
```

## Next Steps (Implementation)

Once tests are written, follow this sequence:

1. **Week 1**: Implement `ui/src/components/` (accessibility.spec passes)
2. **Week 2**: Implement `ui/src/components/ManifestTable` & `ScoreGauge`
3. **Week 3**: Implement `ui/src/pages/ReferralPackagePage`
4. **Week 4**: Implement `ui/src/pages/GraphPage`

Each module should have corresponding tests that move from RED → GREEN.

## References

- **Vitest**: https://vitest.dev/
- **React Testing Library**: https://testing-library.com/react
- **jest-axe**: https://github.com/nickcolley/jest-axe
- **WCAG 2.0**: https://www.w3.org/WAI/WCAG21/quickref/
- **Accessibility**: https://developer.mozilla.org/en-US/docs/Web/Accessibility/ARIA

## Troubleshooting

### Common Issues

**"jest-axe not found"**
```bash
npm install jest-axe
```

**"Test timeout"**
- Increase timeout in vitest.config.ts
- Use `waitFor` with timeout option

**"Element not found"**
- Verify element is rendered with `screen.debug()`
- Check for typos in query text
- Use `getByRole` instead of `getByTestId`

## Questions?

Refer to:
- `setup.ts` — Vitest/RTL initialization
- Individual test file comments — Specific requirements
- ARCHITECTURE.md — System design
