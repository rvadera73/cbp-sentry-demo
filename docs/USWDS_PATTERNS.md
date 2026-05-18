# USWDS Component Pattern Mapping

## Overview

All Sentry UI components must be built using **U.S. Web Design System (USWDS)** patterns. USWDS provides accessible, mobile-first components designed for U.S. government digital services. This document maps each Sentry view to USWDS equivalents and specifies customization rules.

**Key principle**: Use USWDS components off-the-shelf; only customize typography, spacing, and color via CSS variables. Never override accessibility features.

---

## Component Mapping

### 1. ManifestTable → USWDS Table (Sortable, Filterable)

**Purpose**: Display uploaded manifests with sorting and filtering capabilities

**USWDS Base**: [`usa-table` component](https://designsystem.digital.gov/components/table/)

#### Structure

```typescript
// ui/src/views/manifest/ManifestTable.tsx
import { useTable, useSortBy } from "react-table";
import "./ManifestTable.css";

export const ManifestTable = ({ manifests }) => {
  const columns = useMemo(
    () => [
      {
        Header: "Bill of Lading",
        accessor: "bill_of_lading",
        Cell: ({ value }) => <code>{value}</code>,
      },
      {
        Header: "Shipper",
        accessor: "shipper_name",
      },
      {
        Header: "HTS Code",
        accessor: "hts_code",
      },
      {
        Header: "Weight (kg)",
        accessor: "weight_kg",
        Cell: ({ value }) => value.toLocaleString(),
      },
      {
        Header: "Value (USD)",
        accessor: "value_usd",
        Cell: ({ value }) => `$${value.toLocaleString()}`,
      },
      {
        Header: "Status",
        accessor: "status",
        Cell: ({ value }) => (
          <span className={`status status-${value.toLowerCase()}`}>
            {value}
          </span>
        ),
      },
    ],
    []
  );

  const { getTableProps, getTableBodyProps, headerGroups, rows, prepareRow } =
    useTable(
      {
        columns,
        data: manifests,
      },
      useSortBy
    );

  return (
    <table {...getTableProps()} className="usa-table">
      <thead>
        {headerGroups.map((headerGroup) => (
          <tr {...headerGroup.getHeaderGroupProps()}>
            {headerGroup.headers.map((column) => (
              <th
                {...column.getHeaderProps(column.getSortByToggleProps())}
                aria-sort={
                  column.isSorted
                    ? column.isSortedDesc
                      ? "descending"
                      : "ascending"
                    : "none"
                }
              >
                {column.render("Header")}
                <span className="sortIndicator">
                  {column.isSorted ? (column.isSortedDesc ? " ▼" : " ▲") : ""}
                </span>
              </th>
            ))}
          </tr>
        ))}
      </thead>
      <tbody {...getTableBodyProps()}>
        {rows.map((row) => {
          prepareRow(row);
          return (
            <tr {...row.getRowProps()}>
              {row.cells.map((cell) => (
                <td {...cell.getCellProps()}>{cell.render("Cell")}</td>
              ))}
            </tr>
          );
        })}
      </tbody>
    </table>
  );
};
```

#### Styling (CSS)

```css
/* ui/src/views/manifest/ManifestTable.css */
.usa-table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 1.5rem;
  font-family: "Source Sans Pro", sans-serif;
}

.usa-table thead {
  background-color: var(--color-base-lighter);
  border-bottom: 2px solid var(--color-base);
}

.usa-table th {
  padding: 1rem;
  text-align: left;
  font-weight: 600;
  cursor: pointer;
  user-select: none;
}

.usa-table th:hover {
  background-color: var(--color-base-lightest);
}

.usa-table td {
  padding: 1rem;
  border-bottom: 1px solid var(--color-border);
}

.usa-table tr:hover {
  background-color: var(--color-base-lightest);
}

.sortIndicator {
  margin-left: 0.5rem;
  color: var(--color-primary);
  font-weight: bold;
}

.status {
  display: inline-block;
  padding: 0.25rem 0.5rem;
  border-radius: 0.25rem;
  font-weight: 600;
  font-size: 0.875rem;
}

.status-in-transit {
  background-color: #e7f6f8;
  color: var(--color-primary);
}

.status-delivered {
  background-color: #ecf5ec;
  color: #2f8659;
}

.status-flagged {
  background-color: #fef5f1;
  color: var(--color-error);
}

/* Accessibility */
.usa-table th:focus {
  outline: 4px solid var(--color-primary);
  outline-offset: 2px;
}
```

#### Accessibility Features

- ✅ Sortable headers with `aria-sort` attribute
- ✅ Semantic `<table>` with `<thead>` / `<tbody>` structure
- ✅ Row hover highlighting (visual feedback)
- ✅ Keyboard navigation via Tab + Enter for column sorting
- ✅ Focus outline on sortable headers

---

### 2. ScoreGauge → USWDS Progress Indicator (Animated)

**Purpose**: Display risk score (0-100) with color coding and animation

**USWDS Base**: [`usa-process-list` component](https://designsystem.digital.gov/components/process-list/) (customized as circular gauge)

#### Structure

```typescript
// ui/src/views/scoring/ScoreGauge.tsx
import { useMemo, useEffect, useState } from "react";
import "./ScoreGauge.css";

interface ScoreGaugeProps {
  score: number; // 0-100
  maxScore: number; // typically 100
  confidenceLevel: "LOW" | "MEDIUM" | "HIGH";
  label?: string;
}

export const ScoreGauge = ({
  score,
  maxScore = 100,
  confidenceLevel,
  label = "Risk Score",
}: ScoreGaugeProps) => {
  const [displayScore, setDisplayScore] = useState(0);
  const percentage = (displayScore / maxScore) * 100;

  // Animate score on mount
  useEffect(() => {
    if (displayScore === score) return;

    const increment = score > displayScore ? 1 : -1;
    const timer = setTimeout(() => {
      setDisplayScore((prev) => {
        const next = prev + increment;
        return increment > 0 ? Math.min(next, score) : Math.max(next, score);
      });
    }, 10);

    return () => clearTimeout(timer);
  }, [displayScore, score]);

  const colorClass = useMemo(() => {
    if (score >= 80) return "score-high";
    if (score >= 50) return "score-medium";
    return "score-low";
  }, [score]);

  return (
    <div className="score-gauge-container">
      <div className={`score-gauge ${colorClass}`}>
        <svg viewBox="0 0 100 100" className="gauge-svg">
          {/* Background circle */}
          <circle cx="50" cy="50" r="45" className="gauge-background" />

          {/* Progress arc */}
          <circle
            cx="50"
            cy="50"
            r="45"
            className="gauge-progress"
            style={{
              strokeDasharray: `${(percentage / 100) * 282.74} 282.74`,
            }}
          />

          {/* Center text */}
          <text
            x="50"
            y="45"
            textAnchor="middle"
            className="gauge-score-text"
          >
            {displayScore}
          </text>
          <text
            x="50"
            y="60"
            textAnchor="middle"
            className="gauge-max-text"
          >
            / {maxScore}
          </text>
        </svg>

        {/* Confidence badge */}
        <div className={`confidence-badge confidence-${confidenceLevel.toLowerCase()}`}>
          {confidenceLevel}
        </div>
      </div>

      {/* Label and description */}
      <h3 className="gauge-label">{label}</h3>
      <p className="gauge-description">
        {score >= 80 && "High risk of illegal transshipment"}
        {score >= 50 && score < 80 && "Moderate risk indicators present"}
        {score < 50 && "Low risk based on available evidence"}
      </p>

      {/* Status message */}
      <div
        role="status"
        aria-live="polite"
        aria-atomic="true"
        className="gauge-status"
      >
        {score >= 80 && "⚠️ FLAGGED FOR EXAMINATION"}
        {score >= 50 && score < 80 && "⏳ REQUIRES FURTHER REVIEW"}
        {score < 50 && "✓ STANDARD PROCESSING"}
      </div>
    </div>
  );
};
```

#### Styling

```css
/* ui/src/views/scoring/ScoreGauge.css */
.score-gauge-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1.5rem;
  padding: 2rem;
  background-color: var(--color-base-lightest);
  border-radius: 0.5rem;
}

.score-gauge {
  position: relative;
  width: 200px;
  height: 200px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.gauge-svg {
  width: 100%;
  height: 100%;
  transform: rotate(-90deg);
}

.gauge-background {
  fill: none;
  stroke: var(--color-border);
  stroke-width: 8;
}

.gauge-progress {
  fill: none;
  stroke-width: 8;
  stroke-linecap: round;
  transition: stroke-dasharray 0.1s linear;
  stroke: var(--color-primary);
}

/* Color coding */
.score-high .gauge-progress {
  stroke: #c41e3a; /* Error red */
}

.score-medium .gauge-progress {
  stroke: #fdb913; /* Warning yellow */
}

.score-low .gauge-progress {
  stroke: #07a41e; /* Success green */
}

.gauge-score-text {
  font-size: 2.5rem;
  font-weight: bold;
  fill: var(--color-text);
}

.gauge-max-text {
  font-size: 1rem;
  fill: var(--color-text-secondary);
}

.confidence-badge {
  position: absolute;
  bottom: 0;
  right: 0;
  padding: 0.5rem 1rem;
  border-radius: 0.25rem;
  font-weight: 600;
  font-size: 0.875rem;
  background-color: var(--color-base);
  color: white;
}

.confidence-high {
  background-color: #c41e3a;
}

.confidence-medium {
  background-color: #fdb913;
  color: var(--color-text);
}

.confidence-low {
  background-color: #07a41e;
}

.gauge-label {
  font-size: 1.25rem;
  font-weight: 600;
  margin: 0;
}

.gauge-description {
  text-align: center;
  color: var(--color-text-secondary);
  margin: 0;
  font-size: 0.95rem;
}

.gauge-status {
  padding: 0.75rem 1rem;
  border-radius: 0.25rem;
  background-color: var(--color-base);
  color: var(--color-text);
  font-weight: 600;
  width: 100%;
  text-align: center;
}
```

#### Accessibility

- ✅ `role="status"` on status message (announced to screen readers)
- ✅ `aria-live="polite"` (non-interrupting announcements)
- ✅ Semantic color coding with icons (not color-only)
- ✅ Clear numeric display (not icon-only)
- ✅ Animated transition smooth but not distracting

---

### 3. RiskFactors → USWDS Alert (Severity Levels)

**Purpose**: Display 6 risk factors with severity indicators

**USWDS Base**: [`usa-alert` component](https://designsystem.digital.gov/components/alert/)

#### Structure

```typescript
// ui/src/views/scoring/RiskFactors.tsx
import "./RiskFactors.css";

interface RiskFactor {
  indicator: string;
  risk_level: "CRITICAL" | "HIGH" | "MEDIUM-HIGH" | "MEDIUM";
  evidence: string;
  impact_on_score: number;
  why_matters: string;
}

interface RiskFactorsProps {
  factors: RiskFactor[];
  onExpandFactor?: (indicator: string) => void;
}

export const RiskFactors = ({ factors, onExpandFactor }: RiskFactorsProps) => {
  const sortedFactors = [...factors].sort(
    (a, b) => b.impact_on_score - a.impact_on_score
  );

  return (
    <section className="risk-factors-section">
      <h2>Risk Factors</h2>
      <p className="section-description">
        Six risk indicators identified in this shipment, ranked by impact on
        final score:
      </p>

      <div className="risk-factors-list">
        {sortedFactors.map((factor, idx) => (
          <article
            key={`${factor.indicator}-${idx}`}
            className={`risk-factor risk-factor-${factor.risk_level.toLowerCase()}`}
            role="region"
            aria-label={`Risk factor ${idx + 1}: ${factor.indicator}`}
          >
            <div className="risk-factor-header">
              <div className="risk-factor-level">
                <span className={`risk-badge risk-${factor.risk_level.toLowerCase()}`}>
                  {riskLevelIcon(factor.risk_level)}
                  {factor.risk_level.replace("-", " ")}
                </span>
              </div>
              <h3 className="risk-factor-title">{factor.indicator}</h3>
              <span className="risk-factor-weight">
                +{factor.impact_on_score} pts
              </span>
            </div>

            <div className="risk-factor-body">
              <details>
                <summary className="usa-button usa-button--outline">
                  Show Evidence
                </summary>

                <div className="evidence-container">
                  <h4>Evidence</h4>
                  <p>{factor.evidence}</p>

                  <h4>Why It Matters</h4>
                  <p>{factor.why_matters}</p>
                </div>
              </details>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
};

const riskLevelIcon = (level: string) => {
  switch (level) {
    case "CRITICAL":
      return "🔴";
    case "HIGH":
      return "🔴";
    case "MEDIUM-HIGH":
      return "🟠";
    case "MEDIUM":
      return "🟡";
    default:
      return "•";
  }
};
```

#### Styling

```css
/* ui/src/views/scoring/RiskFactors.css */
.risk-factors-section {
  padding: 2rem;
  background-color: var(--color-base-lightest);
  border-radius: 0.5rem;
  margin: 2rem 0;
}

.risk-factors-section h2 {
  margin-top: 0;
  font-size: 1.5rem;
  font-weight: 700;
}

.section-description {
  color: var(--color-text-secondary);
  margin-bottom: 1.5rem;
}

.risk-factors-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.risk-factor {
  border-left: 4px solid var(--color-border);
  background-color: white;
  padding: 1.5rem;
  border-radius: 0.25rem;
}

.risk-factor-critical,
.risk-factor-high {
  border-left-color: #c41e3a;
  background-color: #fef5f1;
}

.risk-factor-medium-high {
  border-left-color: #fdb913;
  background-color: #fffaf0;
}

.risk-factor-medium {
  border-left-color: #fdb913;
  background-color: #fffaf0;
}

.risk-factor-header {
  display: flex;
  align-items: baseline;
  gap: 1rem;
  margin-bottom: 1rem;
}

.risk-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.25rem 0.75rem;
  border-radius: 0.25rem;
  font-weight: 600;
  font-size: 0.875rem;
  white-space: nowrap;
}

.risk-critical,
.risk-high {
  background-color: #c41e3a;
  color: white;
}

.risk-medium-high {
  background-color: #fdb913;
  color: var(--color-text);
}

.risk-medium {
  background-color: #f0ad4e;
  color: var(--color-text);
}

.risk-factor-title {
  flex: 1;
  margin: 0;
  font-size: 1.1rem;
  font-weight: 600;
}

.risk-factor-weight {
  color: var(--color-primary);
  font-weight: bold;
  white-space: nowrap;
}

.evidence-container {
  padding: 1rem;
  background-color: var(--color-base-lightest);
  border-radius: 0.25rem;
  margin-top: 1rem;
}

.evidence-container h4 {
  margin-top: 1rem;
  margin-bottom: 0.5rem;
  font-weight: 600;
  color: var(--color-text);
}

.evidence-container h4:first-child {
  margin-top: 0;
}

.evidence-container p {
  margin: 0 0 0.5rem 0;
  color: var(--color-text-secondary);
  line-height: 1.6;
}

summary {
  cursor: pointer;
  font-weight: 600;
}

summary:focus {
  outline: 4px solid var(--color-primary);
  outline-offset: 2px;
}
```

#### Accessibility

- ✅ Color + icons (not color-only indication)
- ✅ Semantic heading hierarchy
- ✅ `<details>` / `<summary>` for expandable content (keyboard accessible)
- ✅ `role="region"` with `aria-label` for each factor
- ✅ Focus outline on expandable buttons

---

### 4. EntityGraph → USWDS Typography + Custom Diagram

**Purpose**: Display entity ownership chain (Tier 1 → Tier 2 → Tier 3)

**USWDS Base**: [`usa-typography`](https://designsystem.digital.gov/components/typography/) + custom SVG

#### Structure

```typescript
// ui/src/views/entity/EntityGraph.tsx
import "./EntityGraph.css";

interface Entity {
  tier: number;
  entity_name: string;
  jurisdiction: string;
  senzing_confidence: number;
  risk_flag?: string;
}

interface EntityGraphProps {
  entities: Entity[];
  onSelectEntity?: (entity: Entity) => void;
}

export const EntityGraph = ({
  entities,
  onSelectEntity,
}: EntityGraphProps) => {
  return (
    <section className="entity-graph-section">
      <h2>Entity Ownership Chain (Senzing)</h2>

      {/* SVG Diagram */}
      <svg viewBox="0 0 800 600" className="entity-graph-svg">
        {/* Tier 1 Box */}
        <g className="entity-tier-1">
          <rect x="50" y="50" width="220" height="100" className="entity-box" />
          <text x="160" y="75" className="entity-label">
            Tier 1 — Vietnamese Shipper
          </text>
          <text x="160" y="100" className="entity-name">
            {entities[0]?.entity_name}
          </text>
          <text x="160" y="120" className="entity-jurisdiction">
            {entities[0]?.jurisdiction}
          </text>
          <text x="160" y="135" className="entity-confidence">
            Confidence: {(entities[0]?.senzing_confidence * 100).toFixed(0)}%
          </text>
        </g>

        {/* Arrow Tier 1 → Tier 2 */}
        <g className="entity-arrow">
          <line x1="160" y1="150" x2="160" y2="200" />
          <polygon points="160,210 155,200 165,200" />
          <text x="170" y="180" className="arrow-label">
            Beneficial Owner
          </text>
        </g>

        {/* Tier 2 Box */}
        <g className="entity-tier-2">
          <rect x="50" y="210" width="220" height="100" className="entity-box" />
          <text x="160" y="235" className="entity-label">
            Tier 2 — Hong Kong Holding
          </text>
          <text x="160" y="260" className="entity-name">
            {entities[1]?.entity_name}
          </text>
          <text x="160" y="280" className="entity-jurisdiction">
            {entities[1]?.jurisdiction}
          </text>
          <text x="160" y="295" className="entity-confidence">
            Confidence: {(entities[1]?.senzing_confidence * 100).toFixed(0)}%
          </text>
        </g>

        {/* Arrow Tier 2 → Tier 3 */}
        <g className="entity-arrow">
          <line x1="160" y1="310" x2="160" y2="360" />
          <polygon points="160,370 155,360 165,360" />
          <text x="170" y="340" className="arrow-label">
            Ownership Chain
          </text>
        </g>

        {/* Tier 3 Box */}
        <g className="entity-tier-3">
          <rect x="50" y="370" width="220" height="100" className="entity-box" />
          <text x="160" y="395" className="entity-label">
            Tier 3 — Chinese Manufacturer
          </text>
          <text x="160" y="420" className="entity-name">
            {entities[2]?.entity_name}
          </text>
          <text x="160" y="440" className="entity-jurisdiction">
            {entities[2]?.jurisdiction}
          </text>
          <text x="160" y="455" className="entity-confidence">
            Confidence: {(entities[2]?.senzing_confidence * 100).toFixed(0)}%
          </text>
        </g>

        {/* Risk flag */}
        {entities[2]?.risk_flag && (
          <g className="risk-flag">
            <text x="160" y="525" className="risk-flag-text">
              ⚠️ {entities[2].risk_flag}
            </text>
          </g>
        )}
      </svg>

      {/* Textual breakdown */}
      <div className="entity-breakdown">
        {entities.map((entity, idx) => (
          <div
            key={`entity-${idx}`}
            className="entity-card"
            onClick={() => onSelectEntity?.(entity)}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => {
              if (e.key === "Enter") onSelectEntity?.(entity);
            }}
          >
            <h3>Tier {entity.tier} — {entity.entity_name}</h3>
            <dl>
              <dt>Jurisdiction:</dt>
              <dd>{entity.jurisdiction}</dd>
              <dt>Senzing Confidence:</dt>
              <dd>
                <span
                  className={`confidence-badge confidence-${
                    entity.senzing_confidence >= 0.9 ? "high" : "medium"
                  }`}
                >
                  {(entity.senzing_confidence * 100).toFixed(0)}%
                </span>
              </dd>
              {entity.risk_flag && (
                <>
                  <dt>Risk Flag:</dt>
                  <dd className="risk-flag-text">{entity.risk_flag}</dd>
                </>
              )}
            </dl>
          </div>
        ))}
      </div>
    </section>
  );
};
```

#### Styling

```css
/* ui/src/views/entity/EntityGraph.css */
.entity-graph-section {
  padding: 2rem;
  background-color: white;
  border-radius: 0.5rem;
  border: 1px solid var(--color-border);
}

.entity-graph-section h2 {
  margin-top: 0;
  margin-bottom: 1.5rem;
}

.entity-graph-svg {
  width: 100%;
  max-width: 600px;
  margin: 1.5rem auto;
  display: block;
}

.entity-box {
  fill: white;
  stroke: var(--color-primary);
  stroke-width: 2;
}

.entity-tier-1 .entity-box {
  fill: #e7f6f8;
}

.entity-tier-2 .entity-box {
  fill: #f0f0f0;
}

.entity-tier-3 .entity-box {
  fill: #fff3f0;
}

.entity-label {
  font-size: 0.75rem;
  font-weight: 600;
  fill: var(--color-primary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.entity-name {
  font-size: 0.95rem;
  font-weight: 700;
  fill: var(--color-text);
}

.entity-jurisdiction {
  font-size: 0.85rem;
  fill: var(--color-text-secondary);
}

.entity-confidence {
  font-size: 0.8rem;
  fill: #666;
  font-weight: 600;
}

.entity-arrow line {
  stroke: var(--color-primary);
  stroke-width: 2;
}

.entity-arrow polygon {
  fill: var(--color-primary);
}

.arrow-label {
  font-size: 0.8rem;
  fill: var(--color-primary);
  font-style: italic;
}

.risk-flag-text {
  font-size: 0.9rem;
  font-weight: bold;
  fill: #c41e3a;
}

.entity-breakdown {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1rem;
  margin-top: 2rem;
}

.entity-card {
  padding: 1.5rem;
  border: 1px solid var(--color-border);
  border-radius: 0.25rem;
  background-color: var(--color-base-lightest);
  cursor: pointer;
  transition: all 0.2s ease;
}

.entity-card:hover {
  border-color: var(--color-primary);
  background-color: white;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.entity-card:focus {
  outline: 4px solid var(--color-primary);
  outline-offset: 2px;
}

.entity-card h3 {
  margin: 0 0 1rem 0;
  font-size: 1rem;
  font-weight: 700;
  color: var(--color-text);
}

.entity-card dl {
  margin: 0;
}

.entity-card dt {
  font-weight: 600;
  color: var(--color-text);
  margin-top: 0.75rem;
  font-size: 0.875rem;
}

.entity-card dt:first-child {
  margin-top: 0;
}

.entity-card dd {
  margin: 0.25rem 0 0 0;
  color: var(--color-text-secondary);
  font-size: 0.875rem;
}

.confidence-badge {
  display: inline-block;
  padding: 0.25rem 0.5rem;
  border-radius: 0.25rem;
  font-weight: 600;
  font-size: 0.8rem;
}

.confidence-high {
  background-color: #e7f6f8;
  color: var(--color-primary);
}

.confidence-medium {
  background-color: #f0f0f0;
  color: #333;
}
```

#### Accessibility

- ✅ Semantic SVG with text labels (not image-only)
- ✅ Textual breakdown below diagram (no visual diagram required)
- ✅ Entity cards are keyboard focusable (role="button", tabIndex)
- ✅ Clear hierarchy with `<h3>` and `<dl>` (definition lists)

---

### 5. Referral Document → USWDS Layout (Sections, Expandable Panels)

**Purpose**: Display full referral package (Tables 3-1 through 3-14)

**USWDS Base**: [`usa-accordion`](https://designsystem.digital.gov/components/accordion/) + semantic sections

#### Structure

```typescript
// ui/src/views/referral/ReferralDocument.tsx
import { useState } from "react";
import "./ReferralDocument.css";

interface ReferralDocumentProps {
  package: {
    package_id: string;
    shipment_id: string;
    score: number;
    confidence_level: string;
    recommended_action: string;
    sections: any;
  };
}

export const ReferralDocument = ({ package: pkg }: ReferralDocumentProps) => {
  const [expandedSections, setExpandedSections] = useState<Set<string>>(
    new Set(["shipment_identification"])
  );

  const toggleSection = (sectionId: string) => {
    const newSet = new Set(expandedSections);
    if (newSet.has(sectionId)) {
      newSet.delete(sectionId);
    } else {
      newSet.add(sectionId);
    }
    setExpandedSections(newSet);
  };

  const sections = [
    {
      id: "shipment_identification",
      title: "Table 3-1: Shipment Identification",
      content: <ShipmentIdentificationSection data={pkg.sections.shipment_identification} />,
    },
    {
      id: "line_items",
      title: "Table 3-2: Line Items",
      content: <LineItemsSection data={pkg.sections.line_items} />,
    },
    {
      id: "routing_history",
      title: "Table 3-3: Routing History",
      content: <RoutingHistorySection data={pkg.sections.routing_history} />,
    },
    {
      id: "parties_and_roles",
      title: "Table 3-4: Parties and Roles",
      content: <PartiesSection data={pkg.sections.parties_and_roles} />,
    },
    {
      id: "entity_ownership",
      title: "Table 3-5: Entity Ownership Chain (Senzing)",
      content: <EntityOwnershipSection data={pkg.sections.entity_ownership_chain_senzing} />,
    },
    {
      id: "import_pattern",
      title: "Table 3-6: Historical Import Pattern",
      content: <ImportPatternSection data={pkg.sections.historical_import_pattern_analysis} />,
    },
    {
      id: "trade_flow",
      title: "Table 3-7: Trade Flow Intelligence",
      content: <TradeFlowSection data={pkg.sections.trade_flow_intelligence} />,
    },
    {
      id: "document_review",
      title: "Table 3-8: Document Review",
      content: <DocumentReviewSection data={pkg.sections.document_review} />,
    },
    {
      id: "document_consistency",
      title: "Table 3-9: Document Consistency",
      content: <DocumentConsistencySection data={pkg.sections.document_consistency_analysis} />,
    },
    {
      id: "manufacturing_verification",
      title: "Table 3-10: Manufacturing Verification",
      content: <ManufacturingVerificationSection data={pkg.sections.supplier_manufacturing_verification} />,
    },
    {
      id: "risk_indicators",
      title: "Table 3-11: Risk Indicators",
      content: <RiskIndicatorsSection data={pkg.sections.risk_indicator_summary} />,
    },
    {
      id: "score_breakdown",
      title: "Table 3-12: Risk Score Breakdown",
      content: <ScoreBreakdownSection data={pkg.sections.risk_score_breakdown} />,
    },
    {
      id: "what_if",
      title: "Table 3-13: What-If Scenarios",
      content: <WhatIfSection data={pkg.sections.what_if_scenarios} />,
    },
    {
      id: "data_sources",
      title: "Table 3-14: Data Sources",
      content: <DataSourcesSection data={pkg.sections.data_sources_and_uses} />,
    },
  ];

  return (
    <article className="referral-document">
      {/* Header */}
      <header className="referral-header">
        <h1>Sentry Illegal Transshipment Referral Package</h1>
        <div className="referral-meta">
          <dl>
            <dt>Package ID:</dt>
            <dd>{pkg.package_id}</dd>
            <dt>Shipment ID:</dt>
            <dd>{pkg.shipment_id}</dd>
            <dt>Confidence Score:</dt>
            <dd>
              <strong>{pkg.score}/100</strong> ({pkg.confidence_level})
            </dd>
            <dt>Recommended Action:</dt>
            <dd className="action-badge">{pkg.recommended_action}</dd>
          </dl>
        </div>
      </header>

      {/* Accordion */}
      <div className="usa-accordion" role="region" aria-label="Referral package sections">
        {sections.map((section) => (
          <div key={section.id} className="usa-accordion-item">
            <button
              className="usa-accordion-button"
              aria-expanded={expandedSections.has(section.id)}
              aria-controls={section.id}
              onClick={() => toggleSection(section.id)}
            >
              {section.title}
            </button>
            {expandedSections.has(section.id) && (
              <div id={section.id} className="usa-accordion-content">
                {section.content}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Footer */}
      <footer className="referral-footer">
        <button className="usa-button">Download PDF</button>
        <button className="usa-button usa-button--outline">Print</button>
      </footer>
    </article>
  );
};
```

#### Styling

```css
/* ui/src/views/referral/ReferralDocument.css */
.referral-document {
  max-width: 800px;
  margin: 0 auto;
  padding: 2rem;
  background-color: white;
}

.referral-header {
  margin-bottom: 2rem;
  padding-bottom: 2rem;
  border-bottom: 2px solid var(--color-border);
}

.referral-header h1 {
  margin: 0 0 1.5rem 0;
  font-size: 1.75rem;
  font-weight: 700;
}

.referral-meta {
  background-color: var(--color-base-lightest);
  padding: 1rem;
  border-radius: 0.25rem;
}

.referral-meta dl {
  margin: 0;
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 0.5rem 1rem;
}

.referral-meta dt {
  font-weight: 600;
  color: var(--color-text);
}

.referral-meta dd {
  margin: 0;
  color: var(--color-text-secondary);
}

.action-badge {
  display: inline-block;
  padding: 0.5rem 1rem;
  background-color: #c41e3a;
  color: white;
  border-radius: 0.25rem;
  font-weight: 600;
}

.usa-accordion {
  border-top: 2px solid var(--color-border);
}

.usa-accordion-item {
  border-bottom: 2px solid var(--color-border);
}

.usa-accordion-button {
  width: 100%;
  padding: 1rem;
  background-color: var(--color-base-lightest);
  border: none;
  text-align: left;
  font-weight: 600;
  font-size: 1rem;
  cursor: pointer;
  transition: background-color 0.2s;
}

.usa-accordion-button:hover {
  background-color: var(--color-base-lighter);
}

.usa-accordion-button:focus {
  outline: 4px solid var(--color-primary);
  outline-offset: -4px;
}

.usa-accordion-button[aria-expanded="true"]::before {
  content: "▼ ";
  color: var(--color-primary);
  font-weight: bold;
}

.usa-accordion-button[aria-expanded="false"]::before {
  content: "▶ ";
  color: var(--color-primary);
  font-weight: bold;
}

.usa-accordion-content {
  padding: 1.5rem;
  background-color: white;
}

.referral-footer {
  margin-top: 2rem;
  padding-top: 2rem;
  border-top: 2px solid var(--color-border);
  display: flex;
  gap: 1rem;
  justify-content: flex-end;
}
```

#### Accessibility

- ✅ USWDS accordion with `aria-expanded` and `aria-controls`
- ✅ All sections keyboard-navigable (Tab to button, Enter to toggle)
- ✅ Semantic HTML (header, article, footer)
- ✅ Definition list for metadata
- ✅ Focus outline on accordion buttons

---

## Summary: Component Mapping

| Sentry Component | USWDS Base | Key Accessibility Features |
|---|---|---|
| ManifestTable | usa-table | Sortable headers, aria-sort, semantic table |
| ScoreGauge | Progress indicator (custom) | Animated, status role, color + icons |
| RiskFactors | usa-alert (custom) | Expandable, color + icons, semantic headings |
| EntityGraph | Typography + custom SVG | Text labels, entity cards focusable, ARIA labels |
| ReferralDocument | usa-accordion | Keyboard navigation, aria-expanded/controls |

---

## Key Rules

1. **Use USWDS components off-the-shelf** — Don't reimplement
2. **Customize via CSS variables** — Never override accessibility
3. **Keyboard navigation first** — Tab, Enter, Escape must work
4. **Semantic HTML always** — Use `<button>`, `<h1>`, `<label>`, not div+role
5. **Test with jest-axe** — Every component must pass `npm run test:a11y`

---

## Resources

- [USWDS Component Library](https://designsystem.digital.gov/components/)
- [USWDS Accessibility](https://designsystem.digital.gov/documentation/designers/)
- [Accessible React Patterns](https://www.w3.org/WAI/ARIA/apg/patterns/)
