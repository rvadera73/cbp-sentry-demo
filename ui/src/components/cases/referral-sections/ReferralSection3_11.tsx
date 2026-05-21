import React, { useState } from 'react';
import { AlertTriangle, ChevronRight } from 'lucide-react';
import { Section3_11_RiskIndicators } from '../ReferralPackage.types';
import { SectionWrapper } from './SectionWrapper';

interface ReferralSection3_11Props {
  data: Section3_11_RiskIndicators;
  defaultExpanded?: boolean;
}

export function ReferralSection3_11({
  data,
  defaultExpanded = false,
}: ReferralSection3_11Props) {
  const [expandedIndicators, setExpandedIndicators] = useState<Set<string>>(new Set());

  const toggleIndicator = (id: string) => {
    const newSet = new Set(expandedIndicators);
    if (newSet.has(id)) {
      newSet.delete(id);
    } else {
      newSet.add(id);
    }
    setExpandedIndicators(newSet);
  };

  const criticalCount = data.critical_count ?? data.indicators.filter((i) => i.severity === 'CRITICAL').length;
  const highCount = data.high_count ?? data.indicators.filter((i) => i.severity === 'HIGH').length;
  const totalAnomalies = criticalCount + highCount;

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'CRITICAL':
        return { bg: '#ffe6e6', border: '#8b0000', text: '#8b0000', light: '#fcf2f2' };
      case 'HIGH':
        return { bg: '#fff7e6', border: '#7a5300', text: '#7a5300', light: '#fff7e6' };
      case 'MEDIUM':
        return { bg: '#e6f3ff', border: '#003d99', text: '#003d99', light: '#f0f4f8' };
      default:
        return { bg: '#f0f4f8', border: '#5a6c7d', text: '#5a6c7d', light: '#ffffff' };
    }
  };

  return (
    <SectionWrapper
      sectionId="section-3-11"
      sectionNumber="3-11"
      title="Risk Indicators with Legal Authority"
      icon={<AlertTriangle size={16} />}
      dataQuality="COMPLETE"
      anomalyCount={totalAnomalies}
      defaultExpanded={defaultExpanded}
    >
      <div className="referral-section__stats">
        <div className="referral-section__stat">
          <span className="referral-section__stat-label">Total Indicators</span>
          <span className="referral-section__stat-value">{data.indicators.length}</span>
        </div>
        {criticalCount > 0 && (
          <div className="referral-section__stat">
            <span className="referral-section__stat-label">Critical</span>
            <span className="referral-section__stat-value" style={{ color: '#8b0000' }}>
              {criticalCount}
            </span>
          </div>
        )}
        {highCount > 0 && (
          <div className="referral-section__stat">
            <span className="referral-section__stat-label">High</span>
            <span className="referral-section__stat-value" style={{ color: '#7a5300' }}>
              {highCount}
            </span>
          </div>
        )}
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginTop: '16px' }}>
        {data.indicators.map((indicator) => {
          const colors = getSeverityColor(indicator.severity);
          const isExpanded = expandedIndicators.has(indicator.indicator_id);

          return (
            <div
              key={indicator.indicator_id}
              style={{
                border: `1px solid ${colors.border}`,
                borderRadius: '6px',
                overflow: 'hidden',
                backgroundColor: isExpanded ? colors.bg : colors.light,
              }}
            >
              <div
                onClick={() => toggleIndicator(indicator.indicator_id)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    toggleIndicator(indicator.indicator_id);
                  }
                }}
                role="button"
                tabIndex={0}
                style={{
                  padding: '12px',
                  cursor: 'pointer',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'flex-start',
                  backgroundColor: isExpanded ? colors.bg : 'inherit',
                  transition: 'background-color 0.2s',
                }}
              >
                <div style={{ flex: 1 }}>
                  <div
                    style={{
                      fontSize: '13px',
                      fontWeight: 600,
                      color: colors.text,
                      marginBottom: '4px',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '8px',
                    }}
                  >
                    <span
                      style={{
                        display: 'inline-block',
                        padding: '2px 6px',
                        backgroundColor: colors.border,
                        color: 'white',
                        fontSize: '10px',
                        fontWeight: 700,
                        borderRadius: '3px',
                        textTransform: 'uppercase',
                      }}
                    >
                      {indicator.severity.substring(0, 3)}
                    </span>
                    {indicator.name}
                  </div>
                  {indicator.legal_authority && (
                    <div
                      style={{
                        fontSize: '11px',
                        color: colors.text,
                        opacity: 0.8,
                      }}
                    >
                      Legal Authority:{' '}
                      <span className="referral-section__legal-cite">
                        {indicator.legal_authority}
                      </span>
                    </div>
                  )}
                </div>
                <ChevronRight
                  size={20}
                  style={{
                    color: colors.text,
                    transform: isExpanded ? 'rotate(90deg)' : 'rotate(0deg)',
                    transition: 'transform 0.2s',
                    flexShrink: 0,
                    marginLeft: '8px',
                  }}
                />
              </div>

              {isExpanded && (
                <div style={{ borderTop: `1px solid ${colors.border}`, padding: '12px' }}>
                  <div className="referral-section__evidence">
                    <span className="referral-section__evidence-label">Evidence</span>
                    {indicator.evidence}
                  </div>

                  {indicator.countermeasures && indicator.countermeasures.length > 0 && (
                    <div
                      style={{
                        marginTop: '12px',
                        padding: '12px',
                        backgroundColor: '#f7fafc',
                        borderRadius: '4px',
                        borderLeft: '3px solid #4ac4d3',
                      }}
                    >
                      <div
                        style={{
                          fontSize: '12px',
                          fontWeight: 600,
                          color: '#1a202c',
                          marginBottom: '6px',
                        }}
                      >
                        Potential Countermeasures:
                      </div>
                      <ul style={{ margin: '0', paddingLeft: '20px', color: '#2d3748', fontSize: '12px' }}>
                        {indicator.countermeasures.map((measure, idx) => (
                          <li key={idx} style={{ marginBottom: '4px' }}>
                            {measure}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {indicator.mitigation_pathway && (
                    <div
                      style={{
                        marginTop: '12px',
                        padding: '12px',
                        backgroundColor: '#e7f4e4',
                        borderRadius: '4px',
                        borderLeft: '3px solid #2e8540',
                      }}
                    >
                      <div
                        style={{
                          fontSize: '12px',
                          fontWeight: 600,
                          color: '#1b4d22',
                          marginBottom: '4px',
                        }}
                      >
                        CBP Remediation Pathway:
                      </div>
                      <div
                        style={{
                          fontSize: '12px',
                          color: '#1b4d22',
                          lineHeight: '1.5',
                        }}
                      >
                        {indicator.mitigation_pathway}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {totalAnomalies > 0 && (
        <div
          style={{
            marginTop: '16px',
            padding: '12px',
            backgroundColor: '#fcf2f2',
            border: '1px solid #d9381e',
            borderRadius: '6px',
          }}
        >
          <div
            style={{
              fontSize: '12px',
              fontWeight: 600,
              color: '#8b0000',
              marginBottom: '6px',
            }}
          >
            ⚠️ {totalAnomalies} High-Severity Risk Indicator{totalAnomalies !== 1 ? 's' : ''} Detected
          </div>
          <div style={{ fontSize: '12px', color: '#5a2d2d', lineHeight: '1.4' }}>
            This shipment exhibits multiple high-severity risk characteristics that warrant detailed investigation and
            possible enforcement action under applicable CBP authorities.
          </div>
        </div>
      )}
    </SectionWrapper>
  );
}
