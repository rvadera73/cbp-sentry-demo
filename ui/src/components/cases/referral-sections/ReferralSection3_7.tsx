import React, { useState } from 'react';
import { Network } from 'lucide-react';
import { Section3_7_TradeFlowIntelligence } from '../ReferralPackage.types';
import { SectionWrapper } from './SectionWrapper';

interface ReferralSection3_7Props {
  data: Section3_7_TradeFlowIntelligence;
  defaultExpanded?: boolean;
}

export function ReferralSection3_7({
  data,
  defaultExpanded = false,
}: ReferralSection3_7Props) {
  const [expandedMapping, setExpandedMapping] = useState<Set<number>>(new Set());

  const toggleMapping = (idx: number) => {
    const newSet = new Set(expandedMapping);
    if (newSet.has(idx)) {
      newSet.delete(idx);
    } else {
      newSet.add(idx);
    }
    setExpandedMapping(newSet);
  };

  const anomalyCount = (data.prior_case_mappings?.length ?? 0) + (data.correlation_matrix?.filter((c) => c.correlation_strength === 'HIGH').length ?? 0);

  return (
    <SectionWrapper
      sectionId="section-3-7"
      sectionNumber="3-7"
      title="Trade Flow Intelligence"
      icon={<Network size={16} />}
      dataQuality={data.correlation_matrix ? 'COMPLETE' : 'PARTIAL'}
      anomalyCount={anomalyCount}
      defaultExpanded={defaultExpanded}
    >
      <div className="referral-section__stats">
        {data.network_degree !== undefined && (
          <div className="referral-section__stat">
            <span className="referral-section__stat-label">Network Degree</span>
            <span className="referral-section__stat-value">{data.network_degree}</span>
          </div>
        )}
        {data.correlation_matrix && (
          <div className="referral-section__stat">
            <span className="referral-section__stat-label">Correlations Found</span>
            <span className="referral-section__stat-value">{data.correlation_matrix.length}</span>
          </div>
        )}
        {data.prior_case_mappings && (
          <div className="referral-section__stat">
            <span className="referral-section__stat-label">Prior Cases</span>
            <span className="referral-section__stat-value">{data.prior_case_mappings.length}</span>
          </div>
        )}
      </div>

      {data.correlation_matrix && data.correlation_matrix.length > 0 && (
        <div style={{ marginTop: '16px' }}>
          <h4 style={{ margin: '0 0 12px 0', fontSize: '13px', fontWeight: 600 }}>
            Shipment Correlation Matrix
          </h4>
          {data.correlation_matrix.map((corr, idx) => {
            const strengthColor = {
              HIGH: { bg: '#ffe6e6', border: '#d9381e', text: '#8b0000' },
              MEDIUM: { bg: '#fff7e6', border: '#e6a100', text: '#7a5300' },
              LOW: { bg: '#f0f4f8', border: '#5a6c7d', text: '#2d3748' },
            }[corr.correlation_strength];

            return (
              <div
                key={idx}
                style={{
                  padding: '12px',
                  border: `1px solid ${strengthColor.border}`,
                  borderLeft: `3px solid ${strengthColor.border}`,
                  backgroundColor: strengthColor.bg,
                  borderRadius: '6px',
                  marginBottom: '8px',
                }}
              >
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 120px', gap: '12px', alignItems: 'start' }}>
                  <div>
                    <div style={{ fontSize: '13px', fontWeight: 600, color: strengthColor.text, marginBottom: '4px' }}>
                      {corr.other_shipment_id}
                    </div>
                    {corr.case_number && (
                      <div style={{ fontSize: '11px', color: strengthColor.text, marginBottom: '6px' }}>
                        Case: <code>{corr.case_number}</code>
                      </div>
                    )}
                    <div style={{ fontSize: '12px', color: strengthColor.text }}>
                      <strong>Shared:</strong> {corr.common_fields.join(', ')}
                    </div>
                    {corr.shared_entity_type && (
                      <div style={{ fontSize: '11px', color: strengthColor.text, marginTop: '4px' }}>
                        <strong>Entity Type:</strong> {corr.shared_entity_type}
                      </div>
                    )}
                  </div>
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      padding: '8px',
                      backgroundColor: 'rgba(255,255,255,0.5)',
                      borderRadius: '4px',
                      fontSize: '12px',
                      fontWeight: 600,
                      color: strengthColor.text,
                    }}
                  >
                    {corr.correlation_strength}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {data.prior_case_mappings && data.prior_case_mappings.length > 0 && (
        <div style={{ marginTop: '16px' }}>
          <h4 style={{ margin: '0 0 12px 0', fontSize: '13px', fontWeight: 600 }}>
            Prior Case Mappings (Evasion Methodology)
          </h4>
          {data.prior_case_mappings.map((mapping, idx) => {
            const isExpanded = expandedMapping.has(idx);

            return (
              <div
                key={idx}
                style={{
                  border: '1px solid #e5e8eb',
                  borderRadius: '6px',
                  overflow: 'hidden',
                  marginBottom: '8px',
                  backgroundColor: isExpanded ? '#f0f4f8' : '#ffffff',
                }}
              >
                <div
                  onClick={() => toggleMapping(idx)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      toggleMapping(idx);
                    }
                  }}
                  role="button"
                  tabIndex={0}
                  style={{
                    padding: '12px',
                    cursor: 'pointer',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                  }}
                >
                  <div>
                    <div style={{ fontSize: '13px', fontWeight: 600, color: '#1a202c', marginBottom: '4px' }}>
                      Case {mapping.case_number}
                    </div>
                    <div style={{ fontSize: '12px', color: '#5a6c7d' }}>
                      Similarity: <strong>{Math.round(mapping.similarity_score * 100)}%</strong>
                    </div>
                  </div>
                  <div
                    style={{
                      fontSize: '20px',
                      transform: isExpanded ? 'rotate(90deg)' : 'rotate(0deg)',
                      transition: 'transform 0.2s',
                    }}
                  >
                    ›
                  </div>
                </div>

                {isExpanded && (
                  <div style={{ borderTop: '1px solid #e5e8eb', padding: '12px' }}>
                    <div className="referral-section__evidence">
                      <span className="referral-section__evidence-label">Evasion Methodology</span>
                      {mapping.evasion_methodology}
                    </div>
                    <div
                      className="referral-section__evidence"
                      style={{ marginTop: '12px', borderLeftColor: '#4ac4d3' }}
                    >
                      <span className="referral-section__evidence-label">Recommended Countermeasure</span>
                      {mapping.countermeasure}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {data.degree_description && (
        <div
          style={{
            marginTop: '16px',
            padding: '12px',
            backgroundColor: '#f0f4f8',
            borderRadius: '6px',
            fontSize: '12px',
            color: '#2d3748',
            lineHeight: '1.5',
          }}
        >
          <strong>Network Context:</strong> {data.degree_description}
        </div>
      )}
    </SectionWrapper>
  );
}
