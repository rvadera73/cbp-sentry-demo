# CBP Sentry Design System v1.0

## Platform Identity

**Name:** Sentry Intelligence Platform  
**Tagline:** Real-time trade enforcement intelligence  
**Logo:** (To be created) Minimal shield with network nodes  

---

## Color Palette

### Primary Brand Colors (Federal Blue)
- **Primary Blue:** `#0050D8` (USWDS primary, focus/active state)
- **Navy:** `#003366` (Header, dark backgrounds)
- **Light Blue:** `#E7F6FF` (Hover states, light backgrounds)

### Status/Risk Colors
- **High Risk (Red):** `#D9381E` (Stop/Danger)
- **Medium Risk (Orange):** `#E6A100` (Caution/Warning)
- **Low Risk (Green):** `#2E8540` (Safe/Success)
- **Information (Blue):** `#0050D8` (News/Updates)
- **Neutral (Gray):** `#5B616B` (Disabled, secondary info)

### Backgrounds
- **White:** `#FFFFFF` (Default background)
- **Light Gray:** `#F5F5F5` (Section backgrounds)
- **Dark Background:** `#003366` (Headers, dark panels)
- **Overlay:** `rgba(0, 0, 0, 0.7)` (Modal overlays)

### Semantic Feedback Colors
- **Success:** `#2E8540` with light variant `#E7F4E4`
- **Error:** `#D9381E` with light variant `#FCEBE8`
- **Warning:** `#E6A100` with light variant `#FEF5E6`
- **Info:** `#0050D8` with light variant `#EBF6FF`

---

## Typography

### Font Stack
```css
--font-sans: 'Public Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
--font-mono: 'Roboto Mono', 'Courier New', monospace;
```

### Heading Styles

| Level | Size | Weight | Line Height | Letter Spacing |
|-------|------|--------|-------------|----------------|
| H1 | 32px | 700 | 1.4 | -0.5px |
| H2 | 24px | 700 | 1.3 | -0.3px |
| H3 | 20px | 600 | 1.3 | -0.1px |
| H4 | 18px | 600 | 1.25 | 0px |
| H5 | 16px | 600 | 1.25 | 0px |
| H6 | 14px | 600 | 1.25 | 0px |

### Body Text Styles

| Type | Size | Weight | Line Height | Usage |
|------|------|--------|-------------|-------|
| Body | 16px | 400 | 1.6 | Default paragraph text |
| Body Small | 14px | 400 | 1.5 | Secondary text, labels |
| Caption | 12px | 400 | 1.5 | Form hints, metadata |
| Code | 13px | 400 | 1.5 | Code blocks, technical |

---

## Spacing System

Base unit: **8px**

```css
--spacing-xs: 4px;
--spacing-sm: 8px;
--spacing-md: 16px;
--spacing-lg: 24px;
--spacing-xl: 32px;
--spacing-2xl: 48px;
--spacing-3xl: 64px;
```

**Grid:** 8px baseline grid; all margins/padding multiples of 8px

---

## Button Styles

### Primary Button
```css
/* Default State */
background-color: #0050D8;
color: #FFFFFF;
border: 1px solid #0050D8;
padding: 12px 24px;
font-size: 14px;
font-weight: 600;
border-radius: 4px;
cursor: pointer;
transition: all 200ms ease;

/* Hover */
background-color: #0043BC;
box-shadow: 0 2px 4px rgba(0, 80, 216, 0.3);

/* Focus */
outline: 3px solid #0050D8;
outline-offset: 2px;

/* Active */
background-color: #003399;
box-shadow: 0 0 0 4px rgba(0, 80, 216, 0.2);

/* Disabled */
background-color: #CCCCCC;
color: #6B7280;
border-color: #CCCCCC;
cursor: not-allowed;
opacity: 0.6;
```

### Secondary Button
```css
/* Default State */
background-color: #F5F5F5;
color: #003366;
border: 1px solid #D0D0D0;
padding: 12px 24px;
font-size: 14px;
font-weight: 600;
border-radius: 4px;
cursor: pointer;

/* Hover */
background-color: #E7F6FF;
border-color: #0050D8;
color: #003366;

/* Focus */
outline: 3px solid #0050D8;
outline-offset: 2px;

/* Active */
background-color: #D0E8FF;
border-color: #0050D8;
```

### Danger Button (Delete/Override)
```css
/* Default State */
background-color: #D9381E;
color: #FFFFFF;
border: 1px solid #D9381E;
padding: 12px 24px;

/* Hover */
background-color: #B8280F;
box-shadow: 0 2px 4px rgba(217, 56, 30, 0.3);

/* Focus */
outline: 3px solid #D9381E;
outline-offset: 2px;
```

### Button Group (Upload, Export)
```css
display: flex;
gap: 12px;
flex-wrap: wrap;
justify-content: flex-start;

button {
  min-width: 120px;
  padding: 12px 20px;
}
```

---

## Form Elements

### Input Field
```css
border: 1px solid #D0D0D0;
padding: 12px 16px;
font-size: 14px;
border-radius: 4px;
font-family: var(--font-sans);
transition: border-color 200ms ease;

/* Focus */
border-color: #0050D8;
outline: 3px solid rgba(0, 80, 216, 0.2);
outline-offset: 2px;

/* Error */
border-color: #D9381E;
background-color: #FCEBE8;
```

### Select Dropdown
```css
border: 1px solid #D0D0D0;
padding: 12px 16px;
font-size: 14px;
border-radius: 4px;
background-color: #FFFFFF;
cursor: pointer;

/* Focus */
border-color: #0050D8;
outline: 3px solid rgba(0, 80, 216, 0.2);
```

### Checkbox & Radio
```css
width: 20px;
height: 20px;
cursor: pointer;
accent-color: #0050D8;

/* Focus */
outline: 3px solid #0050D8;
outline-offset: 2px;
```

---

## Cards & Panels

### Card Container
```css
background-color: #FFFFFF;
border: 1px solid #E0E0E0;
border-radius: 8px;
padding: 24px;
box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
transition: box-shadow 200ms ease;

/* Hover */
box-shadow: 0 4px 8px rgba(0, 0, 0, 0.12);
```

### Panel with Status (Risk Level)
```css
border-left: 4px solid {status-color};
background-color: {light-status-color};
padding: 16px;
border-radius: 4px;

/* High Risk */
border-left-color: #D9381E;
background-color: #FCEBE8;

/* Medium Risk */
border-left-color: #E6A100;
background-color: #FEF5E6;

/* Low Risk */
border-left-color: #2E8540;
background-color: #E7F4E4;
```

---

## Navigation & Layout

### Header
```css
background-color: #003366;
color: #FFFFFF;
padding: 16px 24px;
display: flex;
justify-content: space-between;
align-items: center;
box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);

/* Logo */
font-size: 20px;
font-weight: 700;

/* Nav Links */
color: #E7F6FF;
text-decoration: none;
padding: 8px 16px;
border-radius: 4px;

/* Nav Links Hover */
background-color: rgba(255, 255, 255, 0.1);
color: #FFFFFF;

/* Active Nav Link */
background-color: #0050D8;
color: #FFFFFF;
```

### Sidebar (Case Queue)
```css
background-color: #F5F5F5;
border-right: 1px solid #E0E0E0;
padding: 16px;
width: 300px;
overflow-y: auto;

/* Item */
padding: 12px;
border-radius: 4px;
cursor: pointer;
transition: background-color 200ms ease;

/* Item Hover */
background-color: #E7F6FF;

/* Item Active/Selected */
background-color: #0050D8;
color: #FFFFFF;
font-weight: 600;
```

### Tab Navigation
```css
display: flex;
border-bottom: 2px solid #E0E0E0;
gap: 0;

/* Tab Button */
padding: 12px 20px;
background-color: transparent;
border: none;
border-bottom: 3px solid transparent;
color: #5B616B;
font-size: 14px;
font-weight: 600;
cursor: pointer;
transition: all 200ms ease;

/* Tab Hover */
color: #003366;
background-color: #F5F5F5;

/* Tab Active */
border-bottom-color: #0050D8;
color: #0050D8;
background-color: transparent;

/* Tab Focus */
outline: 3px solid #0050D8;
outline-offset: -3px;
```

---

## Alert & Notification Styles

### Alert Container
```css
padding: 16px;
border-radius: 4px;
border-left: 4px solid;
margin-bottom: 16px;
display: flex;
gap: 12px;

/* Success */
border-left-color: #2E8540;
background-color: #E7F4E4;
color: #2E8540;

/* Error */
border-left-color: #D9381E;
background-color: #FCEBE8;
color: #8B220B;

/* Warning */
border-left-color: #E6A100;
background-color: #FEF5E6;
color: #8B6F00;

/* Info */
border-left-color: #0050D8;
background-color: #EBF6FF;
color: #003366;
```

---

## Accessibility Standards

### Focus Indicators
- **Outline:** 3px solid `#0050D8`
- **Outline Offset:** 2px
- **Color Contrast:** Minimum 4.5:1 for all text (WCAG 2.1 AA)

### ARIA Attributes
```html
<!-- Button Groups -->
<div role="toolbar" aria-label="Case actions">

<!-- Tabs -->
<div role="tablist">
  <button role="tab" aria-selected="true" aria-controls="panel-1">

<!-- Lists -->
<ul role="list">
  <li role="listitem">

<!-- Live Regions -->
<div aria-live="polite" aria-atomic="false">

<!-- Modal Dialogs -->
<div role="dialog" aria-modal="true" aria-labelledby="title">
```

### Keyboard Navigation
- Tab order: Natural flow, left-to-right, top-to-bottom
- Tab stops: Buttons, links, form inputs, interactive elements
- Escape: Close modals, dropdowns
- Enter: Activate buttons, toggle checkboxes
- Arrow keys: Navigate lists, tabs

---

## Responsive Design Breakpoints

```css
/* Mobile */
@media (max-width: 640px) {
  /* Single column, stacked layout */
  --grid-cols: 1;
  --padding: 12px;
  font-size: 14px;
}

/* Tablet */
@media (min-width: 641px) and (max-width: 1024px) {
  /* Two column layout */
  --grid-cols: 2;
  --padding: 16px;
}

/* Desktop */
@media (min-width: 1025px) {
  /* Three column layout */
  --grid-cols: 3;
  --padding: 24px;
}
```

---

## Component Examples

### Risk Score Badge
```jsx
<div className={`risk-badge risk-${level}`}>
  <span className="risk-score">{score}/100</span>
  <span className="risk-label">{label}</span>
</div>
```

CSS:
```css
.risk-badge {
  padding: 8px 12px;
  border-radius: 4px;
  font-weight: 600;
  display: inline-flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.risk-high { background-color: #FCEBE8; color: #D9381E; }
.risk-medium { background-color: #FEF5E6; color: #E6A100; }
.risk-low { background-color: #E7F4E4; color: #2E8540; }
```

### Entity Chain Visualization
```jsx
<div className="entity-chain">
  <div className="entity-node" style={{ borderColor: countryColor }}>
    {entityName}
  </div>
  <div className="relationship-arrow">→</div>
  <div className="entity-node" style={{ borderColor: countryColor }}>
    {parentName}
  </div>
</div>
```

CSS:
```css
.entity-node {
  padding: 12px 16px;
  border: 2px solid;
  border-radius: 6px;
  background-color: #FFFFFF;
  font-weight: 600;
}

.relationship-arrow {
  color: #D0D0D0;
  font-size: 20px;
  padding: 0 12px;
}
```

---

## Shadow & Elevation System

```css
--shadow-sm: 0 1px 3px rgba(0, 0, 0, 0.08);
--shadow-md: 0 2px 4px rgba(0, 0, 0, 0.12);
--shadow-lg: 0 4px 8px rgba(0, 0, 0, 0.16);
--shadow-xl: 0 8px 16px rgba(0, 0, 0, 0.20);
```

---

## Implementation Checklist

- [ ] Apply primary brand colors (#0050D8 navy header, #003366 for dark panels)
- [ ] Implement button styles: Primary (blue), Secondary (light), Danger (red)
- [ ] Standardize form element focus rings (3px blue outline, 2px offset)
- [ ] Create risk-level color badges (High: red, Medium: orange, Low: green)
- [ ] Implement card & panel styles with proper shadows
- [ ] Set up navigation/header styling
- [ ] Apply tab navigation styles with active state
- [ ] Implement alert/notification styling
- [ ] Test keyboard navigation and focus indicators
- [ ] Verify contrast ratios (4.5:1 minimum for WCAG AA)
- [ ] Implement responsive breakpoints (mobile, tablet, desktop)
- [ ] Apply typography hierarchy (H1-H6 sizes and weights)
- [ ] Implement spacing system (8px baseline grid)

