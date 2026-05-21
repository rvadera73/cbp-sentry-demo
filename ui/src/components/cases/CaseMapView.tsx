import React, { useMemo } from 'react';
import { CaseCardData } from './CaseCard';
import './CaseMapView.css';

interface CaseMapViewProps {
  cases: CaseCardData[];
  selectedCaseId: string | null;
  onCaseSelect?: (caseId: string) => void;
}

/**
 * CaseMapView: Corridor visualization with geospatial flow
 *
 * Features:
 * - Visual corridor paths: Origin → Transshipment → US Port
 * - Vector paths color-coded by risk level (L1/L2/L3)
 * - Interactive nodes and edges
 *
 * Placeholder Implementation:
 * - SVG canvas with sample corridors
 * - Risk color tokens applied dynamically
 * - Ready for integration with actual geospatial data
 */
export default function CaseMapView({ cases, selectedCaseId, onCaseSelect }: CaseMapViewProps) {
  // Group cases by corridor for visualization
  const corridorData = useMemo(() => {
    const corridors: { [key: string]: CaseCardData[] } = {};

    cases.forEach((c) => {
      const key = c.corridor_name || `${c.route_origin}-${c.route_destination}`;
      if (!corridors[key]) {
        corridors[key] = [];
      }
      corridors[key].push(c);
    });

    return Object.entries(corridors).map(([corridor, caseList]) => {
      const highRiskCount = caseList.filter((c) => (c.risk_score || 0) >= 70).length;
      const avgRisk = caseList.reduce((sum, c) => sum + (c.risk_score || 0), 0) / caseList.length;

      return {
        corridor,
        cases: caseList,
        caseCount: caseList.length,
        highRiskCount,
        avgRisk,
      };
    });
  }, [cases]);

  const getRiskColor = (score: number) => {
    if (score >= 70) return 'var(--risk-l3-border)';
    if (score >= 40) return 'var(--risk-l2-border)';
    return 'var(--risk-l1-border)';
  };

  return (
    <div className="case-map-view">
      <div className="map-container">
        {/* SVG Canvas for Corridor Visualization */}
        <svg
          className="corridor-map"
          viewBox="0 0 1000 600"
          preserveAspectRatio="xMidYMid meet"
          role="img"
          aria-label="Corridor map showing trade routes and risk levels"
        >
          {/* Define gradient for risk colors */}
          <defs>
            {/* High Risk Gradient */}
            <linearGradient id="gradient-high" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" style={{ stopColor: 'var(--risk-l3-border)', stopOpacity: 0.8 }} />
              <stop offset="100%" style={{ stopColor: 'var(--risk-l3-border)', stopOpacity: 0.3 }} />
            </linearGradient>

            {/* Medium Risk Gradient */}
            <linearGradient id="gradient-medium" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" style={{ stopColor: 'var(--risk-l2-border)', stopOpacity: 0.8 }} />
              <stop offset="100%" style={{ stopColor: 'var(--risk-l2-border)', stopOpacity: 0.3 }} />
            </linearGradient>

            {/* Low Risk Gradient */}
            <linearGradient id="gradient-low" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" style={{ stopColor: 'var(--risk-l1-border)', stopOpacity: 0.8 }} />
              <stop offset="100%" style={{ stopColor: 'var(--risk-l1-border)', stopOpacity: 0.3 }} />
            </linearGradient>
          </defs>

          {/* Grid Background */}
          <g className="map-grid" opacity="0.1">
            {Array.from({ length: 11 }).map((_, i) => (
              <line key={`v${i}`} x1={i * 100} y1={0} x2={i * 100} y2={600} stroke="currentColor" />
            ))}
            {Array.from({ length: 7 }).map((_, i) => (
              <line key={`h${i}`} x1={0} y1={i * 100} x2={1000} y2={i * 100} stroke="currentColor" />
            ))}
          </g>

          {/* Regional Labels */}
          <text x="50" y="30" className="map-label" textAnchor="start">
            ORIGIN
          </text>
          <text x="450" y="30" className="map-label" textAnchor="middle">
            TRANSSHIPMENT
          </text>
          <text x="900" y="30" className="map-label" textAnchor="end">
            US PORT
          </text>

          {/* Sample Corridor Paths — Will be replaced with live data */}
          {corridorData.slice(0, 5).map((corridor, idx) => {
            const yOffset = 100 + idx * 100;
            const strokeColor =
              corridor.avgRisk >= 70
                ? 'url(#gradient-high)'
                : corridor.avgRisk >= 40
                  ? 'url(#gradient-medium)'
                  : 'url(#gradient-low)';

            return (
              <g key={corridor.corridor}>
                {/* Path: Origin → Transshipment → US Port */}
                <path
                  d={`M 50 ${yOffset} Q 250 ${yOffset - 20} 500 ${yOffset} T 950 ${yOffset}`}
                  stroke={strokeColor}
                  strokeWidth="3"
                  fill="none"
                  strokeDasharray={corridor.avgRisk >= 70 ? '5,5' : 'none'}
                  className="corridor-path"
                />

                {/* Origin Node */}
                <circle cx="50" cy={yOffset} r="8" fill={getRiskColor(corridor.avgRisk)} />

                {/* Transshipment Node */}
                <circle cx="500" cy={yOffset} r="8" fill={getRiskColor(corridor.avgRisk)} />

                {/* Destination Node */}
                <circle cx="950" cy={yOffset} r="8" fill={getRiskColor(corridor.avgRisk)} />

                {/* Corridor Label */}
                <text
                  x="500"
                  y={yOffset + 35}
                  textAnchor="middle"
                  className="map-corridor-label"
                >
                  {corridor.corridor} ({corridor.caseCount} cases, {corridor.highRiskCount} high-risk)
                </text>
              </g>
            );
          })}
        </svg>
      </div>

      {/* Corridor List Panel */}
      <div className="corridor-list-panel">
        <h3 className="panel-title">Active Corridors</h3>

        <div className="corridor-legend">
          <div className="legend-item">
            <div className="legend-color" style={{ backgroundColor: 'var(--risk-l3-border)' }}></div>
            <span>High Risk (70+)</span>
          </div>
          <div className="legend-item">
            <div className="legend-color" style={{ backgroundColor: 'var(--risk-l2-border)' }}></div>
            <span>Medium Risk (40-69)</span>
          </div>
          <div className="legend-item">
            <div className="legend-color" style={{ backgroundColor: 'var(--risk-l1-border)' }}></div>
            <span>Low Risk (&lt;40)</span>
          </div>
        </div>

        <div className="corridor-items" role="list">
          {corridorData.map((corridor) => (
            <button
              key={corridor.corridor}
              role="listitem"
              onClick={() => {
                // Select first case in corridor
                if (corridor.cases.length > 0 && onCaseSelect) {
                  onCaseSelect(corridor.cases[0].id);
                }
              }}
              className="corridor-item"
              aria-label={`${corridor.corridor}: ${corridor.caseCount} cases, ${corridor.highRiskCount} high risk`}
            >
              <div
                className="corridor-item__color"
                style={{
                  backgroundColor:
                    corridor.avgRisk >= 70
                      ? 'var(--risk-l3-border)'
                      : corridor.avgRisk >= 40
                        ? 'var(--risk-l2-border)'
                        : 'var(--risk-l1-border)',
                }}
              ></div>
              <div className="corridor-item__content">
                <div className="corridor-item__name">{corridor.corridor}</div>
                <div className="corridor-item__stats">
                  <span>{corridor.caseCount} cases</span>
                  <span className="stat-divider">•</span>
                  <span>{Math.round(corridor.avgRisk)}/100 avg risk</span>
                </div>
              </div>
              <div className="corridor-item__count">{corridor.highRiskCount}</div>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
