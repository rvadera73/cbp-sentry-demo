import React from 'react';
import { BarChart3 } from 'lucide-react';
import { Section3_12_ScoreBreakdown } from '../ReferralPackage.types';
import { SectionWrapper } from './SectionWrapper';

interface ReferralSection3_12Props {
  data: Section3_12_ScoreBreakdown;
  defaultExpanded?: boolean;
}

export function ReferralSection3_12({
  data,
  defaultExpanded = false,
}: ReferralSection3_12Props) {
  const scorePercentage = (data.total_score / data.max_score) * 100;
  const topFactors = data.top_contributing_factors || [];

  const getScoreColor = (percentage: number) => {
    if (percentage >= 70) return '#d9381e';
    if (percentage >= 40) return '#e6a100';
    return '#2e8540';
  };

  return (
    <SectionWrapper
      sectionId="section-3-12"
      sectionNumber="3-12"
      title="Score Breakdown with SHAP Feature Importance"
      icon={<BarChart3 size={16} />}
      dataQuality="COMPLETE"
      defaultExpanded={defaultExpanded}
    >
      <div style={{ marginBottom: '20px' }}>
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'baseline',
            marginBottom: '12px',
          }}
        >
          <h4 style={{ margin: '0', fontSize: '13px', fontWeight: 600 }}>
            Overall Risk Score
          </h4>
          <span
            style={{
              fontSize: '28px',
              fontWeight: 700,
              color: getScoreColor(scorePercentage),
              fontFamily: "'Roboto Mono', monospace",
            }}
          >
            {data.total_score}/{data.max_score}
          </span>
        </div>
        <div style={{ width: '100%', height: '8px', backgroundColor: '#e5e8eb', borderRadius: '4px', overflow: 'hidden' }}>
          <div
            style={{
              height: '100%',
              width: `${scorePercentage}%`,
              backgroundColor: getScoreColor(scorePercentage),
              transition: 'width 0.3s ease',
            }}
          />
        </div>
        <div style={{ marginTop: '8px', fontSize: '12px', color: '#5a6c7d', textAlign: 'center' }}>
          {scorePercentage.toFixed(0)}% Risk Level
        </div>
      </div>

      {topFactors.length > 0 && (
        <div
          style={{
            padding: '12px',
            backgroundColor: '#f0f4f8',
            borderRadius: '6px',
            marginBottom: '16px',
            border: '1px solid #d0dce5',
          }}
        >
          <div style={{ fontSize: '12px', fontWeight: 600, color: '#1a202c', marginBottom: '8px' }}>
            Top Contributing Factors (SHAP):
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {topFactors.map((factor, idx) => {
              const isPositive = factor.shap_impact === 'POSITIVE';
              const shapAbsolute = Math.abs(factor.shap_value ?? 0);
              const maxShap = Math.max(...topFactors.map((f) => Math.abs(f.shap_value ?? 0)), 1);
              const shapPercentage = (shapAbsolute / maxShap) * 100;

              return (
                <div key={idx} style={{ display: 'grid', gridTemplateColumns: '200px 1fr 60px', gap: '8px', alignItems: 'center' }}>
                  <div
                    style={{
                      fontSize: '12px',
                      fontWeight: 600,
                      color: '#2d3748',
                      whiteSpace: 'nowrap',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                    }}
                  >
                    {factor.component_name}
                  </div>
                  <div style={{ height: '6px', backgroundColor: '#e5e8eb', borderRadius: '3px', overflow: 'hidden' }}>
                    <div
                      style={{
                        height: '100%',
                        width: `${shapPercentage}%`,
                        backgroundColor: isPositive ? '#d9381e' : '#2e8540',
                        transition: 'width 0.3s ease',
                      }}
                    />
                  </div>
                  <div
                    style={{
                      fontSize: '11px',
                      fontWeight: 600,
                      color: isPositive ? '#d9381e' : '#2e8540',
                      textAlign: 'right',
                    }}
                  >
                    {isPositive ? '+' : '-'}{shapAbsolute.toFixed(2)}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      <div style={{ marginBottom: '16px' }}>
        <h4 style={{ margin: '0 0 12px 0', fontSize: '13px', fontWeight: 600 }}>
          Component Scores
        </h4>
        <table className="referral-section__table">
          <thead>
            <tr>
              <th>Component</th>
              <th style={{ textAlign: 'center' }}>Score</th>
              {data.components.some((c) => c.weight_percentage !== undefined) && (
                <th style={{ textAlign: 'center' }}>Weight</th>
              )}
              {data.components.some((c) => c.shap_value !== undefined) && (
                <th style={{ textAlign: 'center' }}>SHAP</th>
              )}
            </tr>
          </thead>
          <tbody>
            {data.components.map((component, idx) => (
              <tr key={idx}>
                <td style={{ fontWeight: 600 }}>{component.component_name}</td>
                <td style={{ textAlign: 'center' }}>
                  <code>
                    {component.score}/{component.max_score}
                  </code>
                </td>
                {data.components.some((c) => c.weight_percentage !== undefined) && (
                  <td style={{ textAlign: 'center' }}>
                    {component.weight_percentage !== undefined
                      ? `${component.weight_percentage}%`
                      : '—'}
                  </td>
                )}
                {data.components.some((c) => c.shap_value !== undefined) && (
                  <td
                    style={{
                      textAlign: 'center',
                      color: component.shap_impact === 'POSITIVE' ? '#d9381e' : '#2e8540',
                      fontWeight: 600,
                    }}
                  >
                    {component.shap_value !== undefined
                      ? `${component.shap_impact === 'POSITIVE' ? '+' : '-'}${Math.abs(
                          component.shap_value
                        ).toFixed(2)}`
                      : '—'}
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div
        style={{
          padding: '12px',
          backgroundColor: '#f7fafc',
          border: '1px solid #d0dce5',
          borderRadius: '6px',
          fontSize: '12px',
          color: '#2d3748',
          lineHeight: '1.5',
        }}
      >
        <strong>SHAP Interpretation:</strong> Positive SHAP values indicate factors that increase risk; negative values
        indicate risk mitigation. The bar length shows the magnitude of impact relative to other factors.
      </div>
    </SectionWrapper>
  );
}
