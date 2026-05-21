import React from 'react';
import { ChevronRight, AlertCircle } from 'lucide-react';
import './CaseCard.css';

export interface CaseCardData {
  id: string;
  manifest_id: string;
  shipper_name: string;
  trade_name?: string;
  entity_type?: string;
  consignee_name: string;
  route_origin: string;
  route_destination: string;
  corridor_name?: string;
  commodity_code: string;
  commodity_description?: string;
  declared_value: number;
  risk_score: number;
  filing_date: string;
  status?: string;
}

interface CaseCardProps {
  data: CaseCardData;
  isSelected?: boolean;
  onSelect?: (id: string) => void;
  onClick?: (id: string) => void;
  variant?: 'list' | 'split' | 'map';
  showArrow?: boolean;
}

/**
 * getRiskLevel: Map numeric score to badge text + semantic token class
 */
export function getRiskLevel(score: number): { level: string; tokenClass: string } {
  if (score >= 70) {
    return { level: 'HIGH RISK', tokenClass: 'risk-token-l3' };
  }
  if (score >= 40) {
    return { level: 'MEDIUM RISK', tokenClass: 'risk-token-l2' };
  }
  return { level: 'LOW RISK', tokenClass: 'risk-token-l1' };
}

/**
 * CaseCard: Enterprise case management card with semantic risk coloring.
 *
 * Displays:
 * - Left Pillar: Risk indicator block with color from risk_score
 * - Center: Legal name (bold) + trade name, route, consignee
 * - Bottom: HTS code + description (ellipsis in list, full in split)
 *
 * Accessibility:
 * - Never color-alone: numeric score + text badge included
 * - Screen reader: announces risk level via aria-label
 * - Keyboard: full tab/arrow navigation support
 * - Focus ring: prominent outline-offset per WCAG 2.1 AA
 */
export default function CaseCard({
  data,
  isSelected = false,
  onSelect,
  onClick,
  variant = 'list',
  showArrow = true,
}: CaseCardProps) {
  const score = Math.round(data.risk_score || 0);
  const { level, tokenClass } = getRiskLevel(score);
  const isCritical = score >= 90;

  const handleClick = () => {
    if (onSelect) onSelect(data.id);
    if (onClick) onClick(data.id);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      handleClick();
    }
  };

  return (
    <div
      role="button"
      tabIndex={0}
      aria-label={`Case ${data.manifest_id}: ${data.shipper_name}, Risk Score ${score}/100 - ${level}`}
      aria-selected={isSelected}
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      className={`case-card ${tokenClass} ${isSelected ? 'case-card--selected' : ''} case-card--${variant} ${
        isCritical ? 'risk-indicator-critical' : ''
      }`}
    >
      {/* Left Pillar: Risk Indicator Block */}
      <div className="case-card__risk-pillar">
        <div className="case-card__risk-badge" aria-label={`Risk level: ${level}`}>
          <span className="case-card__risk-level">{level}</span>
        </div>
        <span className="case-card__risk-score" aria-label={`Risk score: ${score} out of 100`}>
          {score}
          <span className="case-card__risk-denominator">/100</span>
        </span>
      </div>

      {/* Center Content: Entity + Route Information */}
      <div className="case-card__content">
        {/* Entity Identification */}
        <div className="case-card__entity">
          <div className="case-card__legal-name">{data.shipper_name}</div>
          {data.trade_name && <div className="case-card__trade-name">{data.trade_name}</div>}
          {data.entity_type && <span className="case-card__entity-type">{data.entity_type}</span>}
          <span className="case-card__filing-id" title={`Filing ID: ${data.manifest_id}`}>
            {data.manifest_id}
          </span>
        </div>

        {/* Route & Logistics */}
        <div className="case-card__route">
          <span className="case-card__route-segment">{data.route_origin}</span>
          <span className="case-card__route-arrow">→</span>
          <span className="case-card__route-segment">{data.route_destination}</span>
          {data.corridor_name && (
            <span className="case-card__corridor" title={`Corridor: ${data.corridor_name}`}>
              {data.corridor_name}
            </span>
          )}
        </div>

        {/* Consignee */}
        <div className="case-card__consignee">
          <span className="case-card__label">Consignee:</span>
          <span className="case-card__value">{data.consignee_name}</span>
        </div>

        {/* HTS Code & Description */}
        <div className="case-card__hts">
          <div className="case-card__hts-code">
            <span className="case-card__label">HTS:</span>
            <code className="case-card__code">{data.commodity_code}</code>
          </div>
          {data.commodity_description && (
            <div className="case-card__hts-description">{data.commodity_description}</div>
          )}
        </div>

        {/* Financial & Filing Information */}
        <div className="case-card__footer">
          <div className="case-card__footer-item">
            <span className="case-card__label">Declared Value</span>
            <span className="case-card__value">${(data.declared_value || 0).toLocaleString()}</span>
          </div>
          <div className="case-card__footer-item">
            <span className="case-card__label">Filed</span>
            <span className="case-card__value">{new Date(data.filing_date).toLocaleDateString()}</span>
          </div>
          {data.status && (
            <div className="case-card__footer-item">
              <span className="case-card__label">Status</span>
              <span className="case-card__value">{data.status}</span>
            </div>
          )}
        </div>
      </div>

      {/* Right Side: Action Arrow + Critical Indicator */}
      <div className="case-card__actions">
        {isCritical && (
          <AlertCircle
            size={20}
            className="case-card__critical-icon"
            aria-label="Critical risk score (90+)"
          />
        )}
        {showArrow && <ChevronRight size={24} className="case-card__arrow" aria-hidden="true" />}
      </div>
    </div>
  );
}
