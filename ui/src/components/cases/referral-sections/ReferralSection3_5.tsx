import React from 'react';
import { GitBranch } from 'lucide-react';
import { Section3_5_EntityOwnershipChain } from '../ReferralPackage.types';
import { SectionWrapper } from './SectionWrapper';

interface ReferralSection3_5Props {
  data: Section3_5_EntityOwnershipChain;
  defaultExpanded?: boolean;
}

export function ReferralSection3_5({
  data,
  defaultExpanded = false,
}: ReferralSection3_5Props) {
  const highRiskLevels = data.levels.filter((l) =>
    l.entities.some((e) => e.riskLevel === 'high' || e.riskLevel === 'critical')
  );
  const anomalyCount = highRiskLevels.length;

  const getRiskColor = (level: string) => {
    switch (level) {
      case 'critical':
      case 'high':
        return { bg: '#ffe6e6', border: '#d9381e', text: '#8b0000' };
      case 'medium':
        return { bg: '#fff7e6', border: '#e6a100', text: '#7a5300' };
      default:
        return { bg: '#e7f4e4', border: '#2e8540', text: '#1b4d22' };
    }
  };

  return (
    <SectionWrapper
      sectionId="section-3-5"
      sectionNumber="3-5"
      title="Entity Ownership Chain"
      icon={<GitBranch size={16} />}
      dataQuality="COMPLETE"
      anomalyCount={anomalyCount}
      defaultExpanded={defaultExpanded}
    >
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          gap: '24px',
        }}
      >
        {data.levels.map((level) => {
          const levelLabel = {
            1: 'L1 — Direct Entity',
            2: 'L2 — Parent Company',
            3: 'L3 — Ultimate Beneficial Owner',
          }[level.level] || `Level ${level.level}`;

          return (
            <div key={level.level}>
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'baseline',
                  marginBottom: '12px',
                  paddingBottom: '8px',
                  borderBottom: '2px solid #e5e8eb',
                }}
              >
                <h4
                  style={{
                    margin: 0,
                    fontSize: '13px',
                    fontWeight: 600,
                    color: '#1a202c',
                  }}
                >
                  {levelLabel}
                </h4>
                <span
                  style={{
                    fontSize: '11px',
                    fontWeight: 600,
                    color: '#5a6c7d',
                    backgroundColor: '#f0f4f8',
                    padding: '4px 8px',
                    borderRadius: '4px',
                  }}
                >
                  {Math.round(level.confidence * 100)}% Confidence • {level.evidence_count} Evidence
                </span>
              </div>

              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))',
                  gap: '12px',
                }}
              >
                {level.entities.map((entity, idx) => {
                  const colors = getRiskColor(entity.riskLevel);
                  return (
                    <div
                      key={idx}
                      style={{
                        padding: '12px',
                        border: `1px solid ${colors.border}`,
                        borderLeft: `3px solid ${colors.border}`,
                        borderRadius: '6px',
                        backgroundColor: colors.bg,
                      }}
                    >
                      <div
                        style={{
                          fontSize: '13px',
                          fontWeight: 600,
                          color: colors.text,
                          marginBottom: '8px',
                        }}
                      >
                        {entity.name}
                      </div>
                      <table
                        style={{
                          width: '100%',
                          fontSize: '12px',
                          color: colors.text,
                          borderCollapse: 'collapse',
                        }}
                      >
                        <tbody>
                          <tr>
                            <td
                              style={{
                                fontWeight: 600,
                                paddingBottom: '4px',
                                paddingRight: '8px',
                              }}
                            >
                              Country:
                            </td>
                            <td style={{ paddingBottom: '4px' }}>{entity.country}</td>
                          </tr>
                          <tr>
                            <td
                              style={{
                                fontWeight: 600,
                                paddingBottom: '4px',
                                paddingRight: '8px',
                              }}
                            >
                              Risk Level:
                            </td>
                            <td
                              style={{
                                paddingBottom: '4px',
                                fontWeight: 600,
                                textTransform: 'uppercase',
                              }}
                            >
                              {entity.riskLevel}
                            </td>
                          </tr>
                          {entity.entityType && (
                            <tr>
                              <td
                                style={{
                                  fontWeight: 600,
                                  paddingBottom: '4px',
                                  paddingRight: '8px',
                                }}
                              >
                                Type:
                              </td>
                              <td style={{ paddingBottom: '4px' }}>
                                {entity.entityType}
                              </td>
                            </tr>
                          )}
                          {entity.confidence !== undefined && (
                            <tr>
                              <td
                                style={{
                                  fontWeight: 600,
                                  paddingRight: '8px',
                                }}
                              >
                                Confidence:
                              </td>
                              <td>
                                {Math.round(entity.confidence * 100)}%
                              </td>
                            </tr>
                          )}
                          {entity.registrationStatus && (
                            <tr>
                              <td
                                style={{
                                  fontWeight: 600,
                                  paddingRight: '8px',
                                }}
                              >
                                Status:
                              </td>
                              <td>{entity.registrationStatus}</td>
                            </tr>
                          )}
                        </tbody>
                      </table>
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}

        {data.ultimate_beneficial_owner && (
          <div
            style={{
              padding: '16px',
              backgroundColor: '#f0f4f8',
              border: '2px solid #013060',
              borderRadius: '6px',
              marginTop: '8px',
            }}
          >
            <div
              style={{
                fontSize: '11px',
                fontWeight: 600,
                color: '#5a6c7d',
                marginBottom: '8px',
                textTransform: 'uppercase',
                letterSpacing: '0.5px',
              }}
            >
              Ultimate Beneficial Owner (UBO)
            </div>
            <div
              style={{
                fontSize: '14px',
                fontWeight: 600,
                color: '#013060',
                marginBottom: '6px',
              }}
            >
              {data.ultimate_beneficial_owner.name}
            </div>
            <div style={{ fontSize: '12px', color: '#2d3748' }}>
              {data.ultimate_beneficial_owner.country} •{' '}
              <span style={{ fontWeight: 600 }}>
                {data.ultimate_beneficial_owner.riskLevel.toUpperCase()}
              </span>
            </div>
          </div>
        )}
      </div>
    </SectionWrapper>
  );
}
