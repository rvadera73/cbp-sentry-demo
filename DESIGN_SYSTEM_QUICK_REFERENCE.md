# Federal Design System — Quick Reference

## Color Palette

### Primary Colors
```
Navy Header:    #003366
Primary Blue:   #0050D8 ← Use for CTAs, focus rings
Blue Hover:     #0043BC
Blue Active:    #003399
Light Blue BG:  #E7F6FF
```

### Risk Colors
```
High Risk Red:     #D9381E (background: #FCF2F2)
Medium Risk Orange: #E6A100 (background: #FEF5E6)
Low Risk Green:    #2E8540 (background: #E7F4E4)
```

### Neutral
```
White:         #FFFFFF
Light Gray:    #F5F5F5
Border:        #D0D0D0
Text Primary:  #003366
Text Secondary: #5B616B
```

---

## Button Styles

### HTML/CSS
```html
<!-- Primary Button -->
<button class="btn-primary">
  Upload Manifest
</button>

<!-- Secondary Button -->
<button class="btn-secondary">
  Cancel
</button>

<!-- Danger Button -->
<button class="btn-danger">
  Delete
</button>
```

### React Component
```typescript
import Button from '@/components/common/Button';
import { Upload } from 'lucide-react';

<Button variant="primary" icon={<Upload size={16} />}>
  Upload Manifest
</Button>
```

---

## Form Inputs

### CSS Classes
```css
/* Already applied to all form elements */
input, select, textarea {
  border: 1px solid #D0D0D0;
  padding: 12px 16px;
  border-radius: 4px;
  font-size: 14px;
}

input:focus {
  border-color: #0050D8;
  outline: 3px solid rgba(0, 80, 216, 0.2);
  outline-offset: 2px;
}
```

### HTML Example
```html
<div class="form-group">
  <label for="email" class="required">Email Address</label>
  <input type="email" id="email" />
  <span class="help-text">Required field</span>
</div>

<div class="form-group">
  <label for="country">Country</label>
  <select id="country">
    <option>Select country...</option>
  </select>
</div>
```

---

## Spacing System (8px baseline)

```
xs: 4px    (--space-xs)
sm: 8px    (--space-sm)
md: 16px   (--space-md)
lg: 24px   (--space-lg)
xl: 32px   (--space-xl)
2xl: 48px  (--space-2xl)
3xl: 64px  (--space-3xl)
```

Use multiples of 8px for all margins/padding.

---

## Typography

### Font Stack
```
'Public Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif
```

### Heading Sizes
```
H1: 32px, weight 700
H2: 24px, weight 700
H3: 20px, weight 600
H4: 18px, weight 600
H5: 16px, weight 600
H6: 14px, weight 600
```

### Body Text
```
Regular: 16px, weight 400
Small:   14px, weight 400
Caption: 12px, weight 400
```

---

## Focus Rings (WCAG 2.1 AA)

All interactive elements need:
```css
:focus-visible {
  outline: 3px solid #0050D8;
  outline-offset: 2px;
}
```

**Automatically applied to:**
- Buttons (all variants)
- Input fields
- Select dropdowns
- Links
- Checkboxes/Radios

---

## Transitions

```css
/* Default: 200ms ease */
transition: all 200ms ease;

/* For specific properties */
transition: background-color 200ms ease, border-color 200ms ease;
```

---

## Component Import Paths

```typescript
// Button component
import Button from '@/components/common/Button';

// Geographic map
import GeographicMapView from '@/components/cases/GeographicMapView';

// Header with logo
import Header from '@/components/layout/Header';
```

---

## Common Patterns

### Error Message
```html
<input type="text" />
<span class="error-message">This field is required</span>
```

### Success Message
```html
<span class="success-message">Changes saved successfully</span>
```

### Form Validation Alert
```html
<div class="form-validation error">
  <span>Please correct the errors below</span>
</div>
```

### Risk Badge
```html
<div class="risk-badge high">HIGH RISK</div>
<div class="risk-badge medium">MEDIUM RISK</div>
<div class="risk-badge low">LOW RISK</div>
```

---

## Responsive Breakpoints

```css
/* Mobile */
@media (max-width: 640px) {
  /* Single column layout */
}

/* Tablet */
@media (min-width: 641px) and (max-width: 1024px) {
  /* Two column layout */
}

/* Desktop */
@media (min-width: 1025px) {
  /* Full layout */
}
```

---

## Map Component

```typescript
import GeographicMapView from '@/components/cases/GeographicMapView';

<GeographicMapView
  cases={shipmentData}
  selectedCaseId={selectedCaseId}
  onCaseSelect={(caseId) => handleSelect(caseId)}
/>
```

**Features:**
- Leaflet-based map with OpenStreetMap tiles
- Color-coded markers: Red (origin), Blue (destination)
- Interactive tooltips and popups
- Risk-based route coloring
- Responsive legend

---

## Header with Logo

```typescript
<Header
  title="Sentry Intelligence Platform"
  showNav={true}
  showUploadButton={true}
  onUploadClick={handleUpload}
/>
```

**Elements:**
- Shield icon (white on navy)
- "Sentry" platform name
- "Intelligence Platform" subtitle
- Navigation links
- Role-based menu
- User email and role display
- Logout button

---

## CSS Variables

Access in any CSS file:

```css
.my-component {
  background-color: var(--uswds-primary-blue); /* #0050D8 */
  color: var(--neutral-text-primary); /* #003366 */
  padding: var(--space-md); /* 16px */
  border: 1px solid var(--neutral-border); /* #D0D0D0 */
  border-radius: 4px;
  transition: all var(--transition-base); /* 200ms ease */
}

.my-component:focus-visible {
  outline: 3px solid var(--federal-focus); /* #0050D8 */
  outline-offset: 2px;
}
```

---

## Accessibility Checklist

When adding new components:
- [ ] Focus ring visible on Tab
- [ ] All buttons/links keyboard accessible
- [ ] Color contrast 4.5:1 minimum
- [ ] Form labels associated with inputs
- [ ] ARIA labels where needed
- [ ] Semantic HTML structure

---

## Common Issues & Fixes

**Button not getting focus ring?**
```css
button:focus-visible {
  outline: 3px solid #0050D8;
  outline-offset: 2px;
}
```

**Form input border not showing?**
```css
input {
  border: 1px solid #D0D0D0;
}
```

**Colors look wrong?**
- Check you're using #0050D8 (blue), not #2491ff
- Navy is #003366, not #013060
- Red is #D9381E, not #dc2626

**Transition too slow/fast?**
```css
transition: all 200ms ease; /* Always use 200ms */
```

---

## File Locations

```
/ui/src/styles/
  ├── design-tokens.css      ← Color variables & button styles
  ├── forms.css              ← Form element styling
  ├── Header.css             ← Header component styles
  └── ...

/ui/src/components/
  ├── common/
  │   └── Button.tsx         ← Button component
  ├── layout/
  │   └── Header.tsx         ← Header component
  └── cases/
      ├── GeographicMapView.tsx   ← Map component
      └── GeographicMapView.css   ← Map styles
```

---

## Support & Questions

For design system questions:
1. Check `/DESIGN_SYSTEM_IMPLEMENTATION.md` for full spec
2. Reference color values in `design-tokens.css`
3. Check component examples above
4. Review existing component implementations

---

**Last Updated:** May 20, 2026  
**Version:** 1.0  
**Status:** Production Ready ✓
