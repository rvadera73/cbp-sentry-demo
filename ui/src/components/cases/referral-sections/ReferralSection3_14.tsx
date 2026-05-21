import React from 'react';
import { Database } from 'lucide-react';
import { Section3_14_DataSources } from '../ReferralPackage.types';
import { SectionWrapper } from './SectionWrapper';

interface ReferralSection3_14Props {
  data: Section3_14_DataSources;
  defaultExpanded?: boolean;
}

export function ReferralSection3_14({
  data,
  defaultExpanded = false,
}: ReferralSection3_14Props) {
  const lowConfidenceSources = data.sources.filter((s) => s.confidence_percentage < 70);
  const anomalyCount = lowConfidenceSources.length;

  const getSourceIcon = (sourceType: string) => {
    switch (sourceType) {
      case 'API':
        return '🔌';
      case 'MANUAL_ENTRY':
        return '✍️';
      case 'THIRD_PARTY':
        return '🤝';
      case 'GOVERNMENT_DB':
        return '🏛️';
      default:
        return '📊';
    }
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 90) return { bg: '#e7f4e4', border: '#2e8540', text: '#1b4d22' };
    if (confidence >= 70) return { bg: '#fff7e6', border: '#e6a100', text: '#7a5300' };
    return { bg: '#ffe6e6', border: '#d9381e', text: '#8b0000' };
  };

  return (
    <SectionWrapper
      sectionId="section-3-14"
      sectionNumber="3-14"
      title="Data Sources & Attribution"
      icon={<Database size={16} />}
      dataQuality="COMPLETE"
      anomalyCount={anomalyCount}
      defaultExpanded={defaultExpanded}
    >
      <div className="referral-section__stats">
        <div className="referral-section__stat">
          <span className="referral-section__stat-label">Total Sources</span>
          <span className="referral-section__stat-value">{data.sources.length}</span>
        </div>
        {data.overall_confidence !== undefined && (
          <div className="referral-section__stat">
            <span className="referral-section__stat-label">Overall Confidence</span>
            <span className="referral-section__stat-value">
              {Math.round(data.overall_confidence)}%
            </span>
          </div>
        )}
        {lowConfidenceSources.length > 0 && (
          <div className="referral-section__stat">
            <span className="referral-section__stat-label">Low Confidence</span>
            <span className="referral-section__stat-value" style={{ color: '#d9381e' }}>
              {lowConfidenceSources.length}
            </span>
          </div>
        )}
      </div>

      {data.overall_confidence !== undefined && (
        <div
          style={{
            marginTop: '16px',
            padding: '12px',
            backgroundColor: '#f0f4f8',
            borderRadius: '6px',
            border: '1px solid #d0dce5',
          }}
        >
          <div
            style={{
              fontSize: '12px',
              fontWeight: 600,
              color: '#1a202c',
              marginBottom: '8px',
            }}
          >
            Data Source Reliability
          </div>
          <div style={{ width: '100%', height: '8px', backgroundColor: '#e5e8eb', borderRadius: '4px', overflow: 'hidden', marginBottom: '8px' }}>
            <div
              style={{
                height: '100%',
                width: `${data.overall_confidence}%`,
                backgroundColor:
                  data.overall_confidence >= 80
                    ? '#2e8540'
                    : data.overall_confidence >= 60
                      ? '#e6a100'
                      : '#d9381e',
                transition: 'width 0.3s ease',
              }}
            />
          </div>
          <div
            style={{
              fontSize: '12px',
              color: '#2d3748',
              lineHeight: '1.4',
            }}
          >
            {data.overall_confidence >= 85
              ? '✓ High-confidence data sources. Suitable for enforcement decisions.'
              : data.overall_confidence >= 70
                ? '⚠️ Mixed-confidence sources. Cross-reference critical data points.'
                : '✗ Low-confidence data. Recommend additional verification.'}
          </div>
        </div>
      )}

      <div style={{ marginTop: '16px' }}>
        <h4
          style={{
            margin: '0 0 12px 0',
            fontSize: '13px',
            fontWeight: 600,
          }}
        >
          Source Details
        </h4>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {data.sources.map((source, idx) => {
            const colors = getConfidenceColor(source.confidence_percentage);

            return (
              <div
                key={idx}
                style={{
                  padding: '12px',
                  border: `1px solid ${colors.border}`,
                  borderLeft: `3px solid ${colors.border}`,
                  backgroundColor: colors.bg,
                  borderRadius: '6px',
                }}
              >
                <div
                  style={{
                    display: 'grid',
                    gridTemplateColumns: '1fr 1fr 120px',
                    gap: '12px',
                    alignItems: 'start',
                  }}
                >
                  <div>
                    <div
                      style={{
                        fontSize: '13px',
                        fontWeight: 600,
                        color: colors.text,
                        marginBottom: '4px',
                      }}
                    >
                      {getSourceIcon(source.source_type)} {source.source_name}
                    </div>
                    <div style={{ fontSize: '11px', color: colors.text }}>
                      <strong>Type:</strong> {source.source_type.replace(/_/g, ' ')}
                    </div>
                    {source.last_updated && (
                      <div style={{ fontSize: '11px', color: colors.text, marginTop: '2px' }}>
                        <strong>Updated:</strong> {new Date(source.last_updated).toLocaleDateString()}
                      </div>
                    )}
                    {source.data_points_count !== undefined && (
                      <div style={{ fontSize: '11px', color: colors.text, marginTop: '2px' }}>
                        <strong>Data Points:</strong> {source.data_points_count}
                      </div>
                    )}
                  </div>

                  <div />

                  <div
                    style={{
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems: 'flex-end',
                    }}
                  >
                    <div
                      style={{
                        fontSize: '18px',
                        fontWeight: 700,
                        color: colors.text,
                        lineHeight: 1,
                      }}
                    >
                      {source.confidence_percentage}%
                    </div>
                    <div
                      style={{
                        fontSize: '10px',
                        fontWeight: 600,
                        color: colors.text,
                        marginTop: '4px',
                        textTransform: 'uppercase',
                        letterSpacing: '0.5px',
                      }}
                    >
                      {source.confidence_percentage >= 90
                        ? 'High'
                        : source.confidence_percentage >= 70
                          ? 'Medium'
                          : 'Low'}
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {lowConfidenceSources.length > 0 && (
        <div style={{ marginTop: '16px' }}>
          <h4
            style={{
              margin: '0 0 12px 0',
              fontSize: '13px',
              fontWeight: 600,
              color: '#d9381e',
            }}
          >
            Low-Confidence Sources (Verification Recommended)
          </h4>
          {lowConfidenceSources.map((source, idx) => (
            <div
              key={idx}
              className="referral-section__evidence"
              style={{ borderLeftColor: '#d9381e' }}
            >
              <span className="referral-section__evidence-label">
                {source.source_name} ({source.confidence_percentage}%)
              </span>
              Recommend additional verification from authoritative sources before using for
              enforcement decisions.
            </div>
          ))}
        </div>
      )}

      <div
        style={{
          marginTop: '16px',
          padding: '12px',
          backgroundColor: '#f7fafc',
          borderRadius: '6px',
          border: '1px solid #d0dce5',
          fontSize: '12px',
          color: '#2d3748',
          lineHeight: '1.5',
        }}
      >
        <strong>Data Source Categories:</strong>
        <ul style={{ margin: '8px 0', paddingLeft: '20px' }}>
          <li>
            <strong>🏛️ Government DB:</strong> Official CBP, Census, or Treasury databases
          </li>
          <li>
            <strong>🔌 API:</strong> Real-time data feeds (VesselAPI, AIS, Senzing, etc.)
          </li>
          <li>
            <strong>🤝 Third-Party:</strong> Partner intelligence, commercial databases
          </li>
          <li>
            <strong>✍️ Manual Entry:</strong> Officer-entered data, custom analysis
          </li>
        </ul>
      </div>
    </SectionWrapper>
  );
}
