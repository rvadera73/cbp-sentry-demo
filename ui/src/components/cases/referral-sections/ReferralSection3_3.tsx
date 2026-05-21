import React from 'react';
import { Navigation } from 'lucide-react';
import { Section3_3_RoutingHistory } from '../ReferralPackage.types';
import { SectionWrapper } from './SectionWrapper';

interface ReferralSection3_3Props {
  data: Section3_3_RoutingHistory;
  defaultExpanded?: boolean;
}

export function ReferralSection3_3({
  data,
  defaultExpanded = false,
}: ReferralSection3_3Props) {
  const currentRoute = data.current_route || [];
  const anomalousPorts = currentRoute.filter((p) => p.anomaly_flags?.length ?? 0 > 0);
  const anomalyCount = anomalousPorts.length;

  const renderPortDetails = (port: any, index: number) => {
    const hasAnomalies = port.anomaly_flags && port.anomaly_flags.length > 0;
    const dwellHours = port.dwell_hours ?? 0;
    const isTransshipmentRisk = dwellHours > 48; // >2 days dwell

    return (
      <div
        key={index}
        style={{
          padding: '12px',
          marginBottom: '8px',
          backgroundColor: hasAnomalies ? '#ffe6e6' : isTransshipmentRisk ? '#fff7e6' : '#f7fafc',
          border: '1px solid ' + (hasAnomalies ? '#d9381e' : isTransshipmentRisk ? '#e6a100' : '#e5e8eb'),
          borderRadius: '6px',
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: '8px',
        }}
      >
        <div>
          <div style={{ fontSize: '11px', fontWeight: 600, color: '#5a6c7d', marginBottom: '2px' }}>
            PORT
          </div>
          <div style={{ fontSize: '13px', fontWeight: 600, color: '#1a202c' }}>
            {port.port_code} — {port.port_name}, {port.country}
          </div>
        </div>

        <div>
          <div style={{ fontSize: '11px', fontWeight: 600, color: '#5a6c7d', marginBottom: '2px' }}>
            ACTIVITY
          </div>
          <div style={{ fontSize: '13px', color: '#2d3748' }}>
            {port.activity}
          </div>
        </div>

        {port.date_arrival && (
          <div>
            <div style={{ fontSize: '11px', fontWeight: 600, color: '#5a6c7d', marginBottom: '2px' }}>
              ARRIVAL
            </div>
            <div style={{ fontSize: '12px', color: '#2d3748' }}>
              {new Date(port.date_arrival).toLocaleDateString()}
            </div>
          </div>
        )}

        {port.date_departure && (
          <div>
            <div style={{ fontSize: '11px', fontWeight: 600, color: '#5a6c7d', marginBottom: '2px' }}>
              DEPARTURE
            </div>
            <div style={{ fontSize: '12px', color: '#2d3748' }}>
              {new Date(port.date_departure).toLocaleDateString()}
            </div>
          </div>
        )}

        {port.dwell_hours !== undefined && (
          <div>
            <div style={{ fontSize: '11px', fontWeight: 600, color: '#5a6c7d', marginBottom: '2px' }}>
              DWELL TIME
            </div>
            <div
              style={{
                fontSize: '13px',
                fontWeight: 600,
                color: isTransshipmentRisk ? '#d9381e' : '#2d3748',
              }}
            >
              {port.dwell_hours}h
              {isTransshipmentRisk && (
                <span style={{ fontSize: '11px', marginLeft: '4px' }}>⚠️ Extended</span>
              )}
            </div>
          </div>
        )}

        {port.ais_data_quality && (
          <div>
            <div style={{ fontSize: '11px', fontWeight: 600, color: '#5a6c7d', marginBottom: '2px' }}>
              AIS QUALITY
            </div>
            <div style={{ fontSize: '12px', color: '#2d3748' }}>
              {port.ais_data_quality}
            </div>
          </div>
        )}

        {hasAnomalies && (
          <div style={{ gridColumn: '1 / -1', borderTop: '1px solid #d9381e', paddingTop: '8px', marginTop: '4px' }}>
            <div style={{ fontSize: '11px', fontWeight: 600, color: '#d9381e', marginBottom: '4px' }}>
              ANOMALIES DETECTED:
            </div>
            {port.anomaly_flags?.map((flag: string, idx: number) => (
              <div key={idx} style={{ fontSize: '12px', color: '#8b0000', marginBottom: '2px' }}>
                • {flag}
              </div>
            ))}
          </div>
        )}
      </div>
    );
  };

  return (
    <SectionWrapper
      sectionId="section-3-3"
      sectionNumber="3-3"
      title="Routing History & AIS Port Calls"
      icon={<Navigation size={16} />}
      dataQuality="COMPLETE"
      anomalyCount={anomalyCount}
      defaultExpanded={defaultExpanded}
    >
      <div style={{ marginBottom: '16px' }}>
        <h4 style={{ margin: '0 0 12px 0', fontSize: '13px', fontWeight: 600 }}>
          Current Voyage ({currentRoute.length} Port Calls)
        </h4>
        {currentRoute.length > 0 ? (
          <div>{currentRoute.map((port, idx) => renderPortDetails(port, idx))}</div>
        ) : (
          <div style={{ padding: '12px', color: '#5a6c7d' }}>
            No routing data available
          </div>
        )}
      </div>

      {data.transshipment_indicators && data.transshipment_indicators.length > 0 && (
        <div className="referral-section__evidence">
          <span className="referral-section__evidence-label">Transshipment Risk Indicators</span>
          <ul style={{ margin: '4px 0', paddingLeft: '16px' }}>
            {data.transshipment_indicators.map((indicator, idx) => (
              <li key={idx} style={{ fontSize: '12px', color: '#2d3748', marginBottom: '2px' }}>
                {indicator}
              </li>
            ))}
          </ul>
        </div>
      )}
    </SectionWrapper>
  );
}
