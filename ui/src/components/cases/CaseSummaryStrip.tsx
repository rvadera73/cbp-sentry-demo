import React from 'react';
import { AlertTriangle, TrendingUp, BarChart3, Activity } from 'lucide-react';
import './CaseSummaryStrip.css';

export interface SummaryMetrics {
  highRiskCount: number;
  mediumRiskCount: number;
  lowRiskCount: number;
  totalCases: number;
  totalValue: number;
  activeInvestigations?: number;
  avgRiskScore?: number;
}

interface CaseSummaryStripProps {
  metrics: SummaryMetrics;
  isLoading?: boolean;
}

/**
 * CaseSummaryStrip: Case Summary Sub-Header Block
 *
 * Grid-aligned ribbon displaying key metrics with two-stacked typography:
 * - Label (small, uppercase) + prominent value
 * - Risk color tints applied dynamically
 *
 * Accessibility:
 * - Each metric has aria-label with full description
 * - Values announced with context (e.g., "45 high risk cases")
 * - Color paired with icon + text (never color-alone)
 */
export default function CaseSummaryStrip({ metrics, isLoading = false }: CaseSummaryStripProps) {
  const getTotalLowRisk = () => metrics.lowRiskCount || 0;
  const getTotalMediumRisk = () => metrics.mediumRiskCount || 0;
  const getTotalHighRisk = () => metrics.highRiskCount || 0;

  if (isLoading) {
    return (
      <div className="summary-strip" aria-busy="true" aria-label="Loading case metrics">
        <div className="summary-strip__skeleton"></div>
        <div className="summary-strip__skeleton"></div>
        <div className="summary-strip__skeleton"></div>
        <div className="summary-strip__skeleton"></div>
      </div>
    );
  }

  return (
    <div className="summary-strip" role="region" aria-label="Case summary metrics">
      {/* High Risk Cases */}
      <div className="summary-metric summary-metric--high-risk" aria-label={`${getTotalHighRisk()} high risk cases`}>
        <div className="summary-metric__icon">
          <AlertTriangle size={24} aria-hidden="true" />
        </div>
        <div className="summary-metric__content">
          <span className="summary-metric__label">High Risk</span>
          <span className="summary-metric__value" aria-label={`${getTotalHighRisk()} cases`}>
            {getTotalHighRisk()}
          </span>
        </div>
      </div>

      {/* Medium Risk Cases */}
      <div className="summary-metric summary-metric--medium-risk" aria-label={`${getTotalMediumRisk()} medium risk cases`}>
        <div className="summary-metric__icon">
          <TrendingUp size={24} aria-hidden="true" />
        </div>
        <div className="summary-metric__content">
          <span className="summary-metric__label">Medium Risk</span>
          <span className="summary-metric__value" aria-label={`${getTotalMediumRisk()} cases`}>
            {getTotalMediumRisk()}
          </span>
        </div>
      </div>

      {/* Low Risk Cases */}
      <div className="summary-metric summary-metric--low-risk" aria-label={`${getTotalLowRisk()} low risk cases`}>
        <div className="summary-metric__icon">
          <Activity size={24} aria-hidden="true" />
        </div>
        <div className="summary-metric__content">
          <span className="summary-metric__label">Low Risk</span>
          <span className="summary-metric__value" aria-label={`${getTotalLowRisk()} cases`}>
            {getTotalLowRisk()}
          </span>
        </div>
      </div>

      {/* Total Cases */}
      <div className="summary-metric summary-metric--total" aria-label={`${metrics.totalCases} total cases`}>
        <div className="summary-metric__icon">
          <BarChart3 size={24} aria-hidden="true" />
        </div>
        <div className="summary-metric__content">
          <span className="summary-metric__label">Total Cases</span>
          <span className="summary-metric__value" aria-label={`${metrics.totalCases} cases`}>
            {metrics.totalCases}
          </span>
        </div>
      </div>

      {/* Total Value (if available) */}
      {metrics.totalValue > 0 && (
        <div className="summary-metric summary-metric--value" aria-label={`Total declared value: ${formatCurrency(metrics.totalValue)}`}>
          <div className="summary-metric__icon">
            <BarChart3 size={24} aria-hidden="true" />
          </div>
          <div className="summary-metric__content">
            <span className="summary-metric__label">Total Value</span>
            <span className="summary-metric__value" aria-label={formatCurrency(metrics.totalValue)}>
              {formatCurrency(metrics.totalValue)}
            </span>
          </div>
        </div>
      )}

      {/* Average Risk Score (if available) */}
      {metrics.avgRiskScore !== undefined && (
        <div className="summary-metric summary-metric--avg-score" aria-label={`Average risk score: ${Math.round(metrics.avgRiskScore)} out of 100`}>
          <div className="summary-metric__icon">
            <BarChart3 size={24} aria-hidden="true" />
          </div>
          <div className="summary-metric__content">
            <span className="summary-metric__label">Avg Risk Score</span>
            <span className="summary-metric__value" aria-label={`${Math.round(metrics.avgRiskScore)} out of 100`}>
              {Math.round(metrics.avgRiskScore)}
              <span className="summary-metric__denominator">/100</span>
            </span>
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * formatCurrency: Format large numbers as millions/billions
 */
function formatCurrency(value: number): string {
  if (value >= 1_000_000_000) {
    return `$${(value / 1_000_000_000).toFixed(1)}B`;
  }
  if (value >= 1_000_000) {
    return `$${(value / 1_000_000).toFixed(1)}M`;
  }
  if (value >= 1_000) {
    return `$${(value / 1_000).toFixed(1)}K`;
  }
  return `$${value.toLocaleString()}`;
}
