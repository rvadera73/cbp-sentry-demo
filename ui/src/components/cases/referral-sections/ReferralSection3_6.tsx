import React from 'react';
import { TrendingUp } from 'lucide-react';
import { Section3_6_HistoricalPattern } from '../ReferralPackage.types';
import { SectionWrapper } from './SectionWrapper';

interface ReferralSection3_6Props {
  data: Section3_6_HistoricalPattern;
  defaultExpanded?: boolean;
}

export function ReferralSection3_6({
  data,
  defaultExpanded = false,
}: ReferralSection3_6Props) {
  const anomalyCount = (data.anomalies?.length ?? 0) + (data.surge_inflection_points?.length ?? 0);

  const yoyVolumeDelta = data.yoy_volume_delta ?? 0;
  const yoyValueDelta = data.yoy_value_delta ?? 0;
  const volumeSurge = yoyVolumeDelta > 25;
  const valueSurge = yoyValueDelta > 25;

  return (
    <SectionWrapper
      sectionId="section-3-6"
      sectionNumber="3-6"
      title="Historical Import Pattern Analysis"
      icon={<TrendingUp size={16} />}
      dataQuality={data.six_month_trends ? 'COMPLETE' : 'PARTIAL'}
      anomalyCount={anomalyCount}
      defaultExpanded={defaultExpanded}
    >
      <div className="referral-section__stats">
        {yoyVolumeDelta !== undefined && (
          <div className="referral-section__stat">
            <span className="referral-section__stat-label">YoY Volume</span>
            <span
              className="referral-section__stat-value"
              style={{ color: volumeSurge ? '#d9381e' : '#2e8540' }}
            >
              {yoyVolumeDelta > 0 ? '+' : ''}{yoyVolumeDelta}%
            </span>
          </div>
        )}
        {yoyValueDelta !== undefined && (
          <div className="referral-section__stat">
            <span className="referral-section__stat-label">YoY Value</span>
            <span
              className="referral-section__stat-value"
              style={{ color: valueSurge ? '#d9381e' : '#2e8540' }}
            >
              {yoyValueDelta > 0 ? '+' : ''}{yoyValueDelta}%
            </span>
          </div>
        )}
      </div>

      {(volumeSurge || valueSurge) && (
        <div className="referral-section__evidence" style={{ marginTop: '16px' }}>
          <span className="referral-section__evidence-label">Surge Detection</span>
          {volumeSurge && (
            <div>Volume surge: {yoyVolumeDelta}% increase YoY (threshold: 25%)</div>
          )}
          {valueSurge && (
            <div>Value surge: {yoyValueDelta}% increase YoY (threshold: 25%)</div>
          )}
        </div>
      )}

      {data.origin_distribution && data.origin_distribution.length > 0 && (
        <div style={{ marginTop: '16px' }}>
          <h4 style={{ margin: '0 0 12px 0', fontSize: '13px', fontWeight: 600 }}>
            Origin Distribution (Last 6 Months)
          </h4>
          {data.origin_distribution.map((dist, idx) => (
            <div
              key={idx}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '12px',
                padding: '8px',
                marginBottom: '8px',
                backgroundColor: '#f7fafc',
                borderRadius: '4px',
              }}
            >
              <div style={{ width: '120px', fontSize: '12px', fontWeight: 600, color: '#1a202c' }}>
                {dist.country}
              </div>
              <div
                style={{
                  flex: 1,
                  height: '20px',
                  backgroundColor: '#e5e8eb',
                  borderRadius: '3px',
                  overflow: 'hidden',
                }}
              >
                <div
                  style={{
                    height: '100%',
                    width: `${Math.min(dist.percentage * 2, 100)}%`,
                    background: 'linear-gradient(90deg, #013060 0%, #4ac4d3 100%)',
                  }}
                />
              </div>
              <div style={{ width: '80px', textAlign: 'right', fontSize: '12px', fontWeight: 600, color: '#2d3748' }}>
                {dist.percentage}% ({dist.shipment_count} shipments)
              </div>
            </div>
          ))}
        </div>
      )}

      {data.six_month_trends && data.six_month_trends.length > 0 && (
        <div style={{ marginTop: '16px' }}>
          <h4 style={{ margin: '0 0 12px 0', fontSize: '13px', fontWeight: 600 }}>
            6-Month Trend
          </h4>
          <div className="referral-section__chart">
            <table style={{ width: '100%', fontSize: '12px', borderCollapse: 'collapse' }}>
              <thead style={{ borderBottom: '2px solid #d0dce5' }}>
                <tr>
                  <th style={{ padding: '8px', textAlign: 'left', fontWeight: 600 }}>Period</th>
                  <th style={{ padding: '8px', textAlign: 'right', fontWeight: 600 }}>Volume</th>
                  <th style={{ padding: '8px', textAlign: 'right', fontWeight: 600 }}>Value</th>
                  <th style={{ padding: '8px', textAlign: 'right', fontWeight: 600 }}>Shipments</th>
                </tr>
              </thead>
              <tbody>
                {data.six_month_trends.map((trend, idx) => (
                  <tr
                    key={idx}
                    style={{
                      borderBottom: '1px solid #e5e8eb',
                      backgroundColor: idx % 2 === 0 ? '#ffffff' : '#fafbfc',
                    }}
                  >
                    <td style={{ padding: '8px', color: '#2d3748' }}>{trend.period}</td>
                    <td style={{ padding: '8px', textAlign: 'right', color: '#2d3748' }}>
                      {trend.volume.toLocaleString()}
                    </td>
                    <td style={{ padding: '8px', textAlign: 'right', color: '#2d3748' }}>
                      ${(trend.value / 1000).toFixed(0)}K
                    </td>
                    <td style={{ padding: '8px', textAlign: 'right', color: '#2d3748', fontWeight: 600 }}>
                      {trend.shipment_count}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {data.surge_inflection_points && data.surge_inflection_points.length > 0 && (
        <div style={{ marginTop: '16px' }}>
          <h4 style={{ margin: '0 0 12px 0', fontSize: '13px', fontWeight: 600 }}>
            Surge Inflection Points
          </h4>
          {data.surge_inflection_points.map((point, idx) => (
            <div key={idx} className="referral-section__evidence">
              <span style={{ fontSize: '12px', color: '#2d3748' }}>• {point}</span>
            </div>
          ))}
        </div>
      )}

      {data.anomalies && data.anomalies.length > 0 && (
        <div style={{ marginTop: '16px' }}>
          <h4 style={{ margin: '0 0 12px 0', fontSize: '13px', fontWeight: 600, color: '#d9381e' }}>
            Pattern Anomalies
          </h4>
          {data.anomalies.map((anomaly, idx) => (
            <div key={idx} className="referral-section__evidence" style={{ borderLeftColor: '#d9381e' }}>
              <span style={{ fontSize: '12px', color: '#2d3748' }}>⚠️ {anomaly}</span>
            </div>
          ))}
        </div>
      )}
    </SectionWrapper>
  );
}
