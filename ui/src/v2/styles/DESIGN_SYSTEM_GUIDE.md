# CBP Sentry Design System Guide

## Overview
This design system ensures consistent styling across all pages and components. All pages MUST use these constants instead of hardcoding colors, fonts, and spacing.

## Quick Start

### Import the design system in your component:
```typescript
import { COLORS, TYPOGRAPHY, COMPONENTS, PATTERNS } from '../styles/designSystem';
```

## Color System

### Primary Colors
- `COLORS.primary` → #005EA2 (Primary action buttons)
- `COLORS.primaryHover` → #0076D6 (Hover state)
- `COLORS.primaryLight` → #0B1F33 (Dark text)

### Status Colors
- `COLORS.critical` → #D83933 (Red - Critical risk)
- `COLORS.warning` → #FFBE2E (Yellow - Warning)
- `COLORS.success` → #07A41E (Green - Success)

### Neutral Colors
- `COLORS.white` → #ffffff
- `COLORS.lightGray` → #F7F9FC (Page background)
- `COLORS.borderGray` → #D0D7DE (Borders)
- `COLORS.textDark` → #0B1F33 (Primary text)
- `COLORS.textMedium` → #5C5C5C (Secondary text)

## Typography System

### Headings
```typescript
<h1 className={TYPOGRAPHY.h1}>Page Title</h1>
<h2 className={TYPOGRAPHY.h2}>Section Title</h2>
<h3 className={TYPOGRAPHY.h3}>Card Title</h3>
```

### Body Text
```typescript
<p className={TYPOGRAPHY.body}>Regular text</p>
<p className={TYPOGRAPHY.bodySmall}>Smaller text</p>
<p className={TYPOGRAPHY.label}>LABEL TEXT</p>
<p className={TYPOGRAPHY.tiny}>Very small text</p>
```

### Special Styles
```typescript
<span className={TYPOGRAPHY.bold}>Bold text</span>
<span className={TYPOGRAPHY.mono}>Monospace text</span>
```

## Component Styles

### Buttons
```typescript
{/* Primary button */}
<button className={COMPONENTS.button.primary}>Primary Action</button>

{/* Secondary button */}
<button className={COMPONENTS.button.secondary}>Secondary Action</button>

{/* Success button */}
<button className={COMPONENTS.button.success}>Submit</button>

{/* Danger button */}
<button className={COMPONENTS.button.danger}>Delete</button>
```

### Cards
```typescript
{/* Standard card */}
<div className={COMPONENTS.card}>
  <h3 className={TYPOGRAPHY.sectionTitle}>Card Title</h3>
  {/* Card content */}
</div>

{/* Large card */}
<div className={COMPONENTS.cardLarge}>
  {/* Card content */}
</div>

{/* Accent card */}
<div className={COMPONENTS.cardAccent}>
  {/* Card content */}
</div>
```

### Badges
```typescript
<span className={COMPONENTS.badge.error}>Error</span>
<span className={COMPONENTS.badge.warning}>Warning</span>
<span className={COMPONENTS.badge.success}>Success</span>
<span className={COMPONENTS.badge.info}>Info</span>
```

## Layout Patterns

### Summary Card Pattern
```typescript
<div className={PATTERNS.summaryCard}>
  <div className="grid grid-cols-4 gap-6">
    <div>
      <p className={TYPOGRAPHY.label}>Label</p>
      <p className={TYPOGRAPHY.body}>Value</p>
    </div>
    {/* More fields... */}
  </div>
</div>
```

### Progress Bar Pattern
```typescript
<div className={PATTERNS.progressBar}>
  <div className="flex items-center justify-center space-x-12">
    {/* Progress steps */}
  </div>
</div>
```

### Content Pane
```typescript
<div className={PATTERNS.contentPane}>
  {/* Page content */}
</div>
```

### Action Bar (Bottom buttons)
```typescript
<div className={PATTERNS.actionBar}>
  <div className="flex justify-end gap-3">
    <button className={COMPONENTS.button.secondary}>Cancel</button>
    <button className={COMPONENTS.button.primary}>Save</button>
  </div>
</div>
```

## Status/Risk Indicators

Use the `getStatusColor` function for dynamic status colors:

```typescript
import { getStatusColor } from '../styles/designSystem';

const status = 'critical'; // or 'high', 'medium', 'low', 'neutral'
const statusStyle = getStatusColor(status);

<div className={`${statusStyle.bg} ${statusStyle.text} p-4 rounded`}>
  Critical Risk
</div>
```

## Spacing

Use Tailwind's spacing utilities consistently:
- `p-2`, `p-3`, `p-4`, `p-6` for padding
- `m-2`, `m-3`, `m-4` for margins
- `gap-2`, `gap-3`, `gap-4`, `gap-6` for gaps
- `space-y-2`, `space-y-4` for vertical spacing

## Borders

```typescript
{/* Standard border */}
<div className={BORDERS.thin}>Content</div>

{/* Thick border */}
<div className={BORDERS.thick}>Content</div>

{/* Bottom border only */}
<div className={BORDERS.bottom}>Content</div>
```

## Common Page Structure

Every page should follow this structure for consistency:

```typescript
<div className="flex flex-col h-full bg-[#F7F9FC]">
  {/* 1. Progress/Status Bar (if applicable) */}
  <div className={PATTERNS.progressBar}>
    {/* Progress indicators */}
  </div>

  {/* 2. Summary Card with high-level details */}
  <div className={PATTERNS.summaryCard}>
    {/* Key metrics/details */}
  </div>

  {/* 3. Main Content Area */}
  <div className={PATTERNS.contentPane}>
    {/* Page content */}
  </div>

  {/* 4. Action Bar with buttons */}
  <div className={PATTERNS.actionBar}>
    {/* Buttons */}
  </div>
</div>
```

## Checklist for New Pages

When creating a new page, verify:
- ✅ All colors come from `COLORS` constants
- ✅ All typography uses `TYPOGRAPHY` classes
- ✅ All buttons use `COMPONENTS.button.*` styles
- ✅ All cards use `COMPONENTS.card*` styles
- ✅ All spacing uses consistent units (p-4, gap-4, etc.)
- ✅ All borders use `BORDERS` constants
- ✅ Page follows the standard layout structure
- ✅ Status colors use `getStatusColor()` helper

## Examples

### Evidence & Referral Tab
Uses:
- `PATTERNS.progressBar` for 4-stage workflow
- `PATTERNS.summaryCard` for case details
- `PATTERNS.contentPane` for main content
- `PATTERNS.actionBar` for navigation buttons

### Dashboard/Investigations List
Uses:
- `COMPONENTS.card` for each case card
- `COMPONENTS.badge.*` for status indicators
- `TYPOGRAPHY` for consistent text styling
- `COLORS.status*` for risk levels

### AI Tuning Page
Uses:
- Horizontal tabs (similar to workflow tabs)
- `COMPONENTS.card` for each tab's content
- `TYPOGRAPHY` for all text
- `COMPONENTS.button.*` for Apply/Save buttons

## Maintenance

When you need to update styling across all pages:
1. Modify the constant in `designSystem.ts`
2. All pages automatically use the new style
3. No need to update individual pages

This ensures consistency and makes global theme changes trivial.
