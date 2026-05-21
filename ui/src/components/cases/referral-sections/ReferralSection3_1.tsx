import React from 'react';
import { FileText, Calendar, Ship } from 'lucide-react';
import { Section3_1_ShipmentIdentification } from '../ReferralPackage.types';
import { SectionWrapper } from './SectionWrapper';

interface ReferralSection3_1Props {
  data: Section3_1_ShipmentIdentification;
  defaultExpanded?: boolean;
}

export function ReferralSection3_1({
  data,
  defaultExpanded = false,
}: ReferralSection3_1Props) {
  const daysBeforeArrival = data.manifest_timeline?.daysBeforeArrival ?? 0;
  const timelinessFlag = daysBeforeArrival < 5;

  return (
    <SectionWrapper
      sectionId="section-3-1"
      sectionNumber="3-1"
      title="Shipment Identification"
      icon={<FileText size={16} />}
      dataQuality="COMPLETE"
      anomalyCount={timelinessFlag ? 1 : 0}
      defaultExpanded={defaultExpanded}
    >
      <div className="referral-section__stats">
        <div className="referral-section__stat">
          <span className="referral-section__stat-label">MBL</span>
          <code className="referral-section__stat-value">{data.mbl}</code>
        </div>
        <div className="referral-section__stat">
          <span className="referral-section__stat-label">HBL</span>
          <code className="referral-section__stat-value">{data.hbl}</code>
        </div>
        <div className="referral-section__stat">
          <span className="referral-section__stat-label">Vessel</span>
          <span className="referral-section__stat-value" style={{ fontSize: '16px' }}>
            {data.vessel_name.substring(0, 12)}
          </span>
        </div>
        <div className="referral-section__stat">
          <span className="referral-section__stat-label">POD</span>
          <code className="referral-section__stat-value">{data.pod}</code>
        </div>
      </div>

      <table className="referral-section__table" role="presentation">
        <tbody>
          <tr>
            <td style={{ fontWeight: 600, width: '40%' }}>Voyage Number</td>
            <td>
              <code>{data.voyage_number}</code>
            </td>
          </tr>
          <tr>
            <td style={{ fontWeight: 600 }}>Manifest Filed</td>
            <td>{new Date(data.manifest_date).toLocaleDateString()}</td>
          </tr>
          {data.manifest_timeline && (
            <tr
              style={{
                backgroundColor: timelinessFlag ? '#ffe6e6' : 'inherit',
              }}
            >
              <td style={{ fontWeight: 600 }}>Days Before Arrival</td>
              <td>
                <strong>{data.manifest_timeline.daysBeforeArrival}</strong>
                {timelinessFlag && (
                  <span
                    style={{
                      marginLeft: '8px',
                      color: '#d9381e',
                      fontSize: '12px',
                      fontWeight: 600,
                    }}
                  >
                    ⚠️ Late filing (&lt;5 days)
                  </span>
                )}
              </td>
            </tr>
          )}
          <tr>
            <td style={{ fontWeight: 600 }}>ETA</td>
            <td>{new Date(data.eta).toLocaleString()}</td>
          </tr>
        </tbody>
      </table>

      {timelinessFlag && (
        <div className="referral-section__evidence">
          <span className="referral-section__evidence-label">Timeline Anomaly</span>
          Late manifest filing (&lt;5 days before arrival) may indicate
          transshipment activity not yet reflected in ISF data.
        </div>
      )}
    </SectionWrapper>
  );
}
