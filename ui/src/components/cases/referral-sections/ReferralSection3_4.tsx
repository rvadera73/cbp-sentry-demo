import React from 'react';
import { Users } from 'lucide-react';
import { Section3_4_PartiesAndRoles } from '../ReferralPackage.types';
import { SectionWrapper } from './SectionWrapper';

interface ReferralSection3_4Props {
  data: Section3_4_PartiesAndRoles;
  defaultExpanded?: boolean;
}

export function ReferralSection3_4({
  data,
  defaultExpanded = false,
}: ReferralSection3_4Props) {
  const highRiskParties = data.parties.filter((p) => p.risk_level === 'HIGH' || p.risk_level === 'CRITICAL');
  const anomalyCount = highRiskParties.length;

  const getRiskColor = (level: string) => {
    switch (level) {
      case 'CRITICAL':
      case 'HIGH':
        return { bg: '#ffe6e6', border: '#d9381e', text: '#8b0000' };
      case 'MEDIUM':
        return { bg: '#fff7e6', border: '#e6a100', text: '#7a5300' };
      default:
        return { bg: '#e7f4e4', border: '#2e8540', text: '#1b4d22' };
    }
  };

  return (
    <SectionWrapper
      sectionId="section-3-4"
      sectionNumber="3-4"
      title="Parties and Roles"
      icon={<Users size={16} />}
      dataQuality="COMPLETE"
      anomalyCount={anomalyCount}
      defaultExpanded={defaultExpanded}
    >
      {data.network_degree !== undefined && (
        <div className="referral-section__stats">
          <div className="referral-section__stat">
            <span className="referral-section__stat-label">Total Parties</span>
            <span className="referral-section__stat-value">{data.parties.length}</span>
          </div>
          <div className="referral-section__stat">
            <span className="referral-section__stat-label">Network Degree</span>
            <span className="referral-section__stat-value">{data.network_degree}</span>
          </div>
          <div className="referral-section__stat">
            <span className="referral-section__stat-label">High Risk Parties</span>
            <span className="referral-section__stat-value">{highRiskParties.length}</span>
          </div>
        </div>
      )}

      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginTop: '16px' }}>
        {data.parties.map((party) => {
          const colors = getRiskColor(party.risk_level);
          return (
            <div
              key={party.party_id}
              className="referral-section__entity-card"
              style={{
                backgroundColor: colors.bg,
                borderColor: colors.border,
                borderLeftColor: colors.border,
              }}
            >
              <div style={{ flex: 1, minWidth: 0 }}>
                <div
                  style={{
                    fontSize: '13px',
                    fontWeight: 600,
                    color: colors.text,
                    marginBottom: '4px',
                  }}
                >
                  {party.name}
                </div>
                <div
                  style={{
                    fontSize: '12px',
                    color: colors.text,
                    marginBottom: '6px',
                    display: 'grid',
                    gridTemplateColumns: '1fr 1fr',
                    gap: '8px',
                  }}
                >
                  <span>{party.country}</span>
                  <span style={{ opacity: 0.8 }}>Role: {party.role}</span>
                </div>
                {party.enforcement_history && (
                  <div
                    style={{
                      fontSize: '11px',
                      color: '#d9381e',
                      fontWeight: 600,
                      marginTop: '4px',
                    }}
                  >
                    ⚠️ Enforcement History: {party.enforcement_history}
                  </div>
                )}
              </div>
              <div
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'flex-end',
                  gap: '6px',
                  flexShrink: 0,
                }}
              >
                <span
                  className="referral-section__entity-badge"
                  style={{
                    backgroundColor: colors.bg,
                    color: colors.text,
                    border: `1px solid ${colors.border}`,
                    fontWeight: 700,
                  }}
                >
                  {party.risk_level}
                </span>
                {party.confidence_score !== undefined && (
                  <div style={{ fontSize: '11px', color: colors.text }}>
                    <span style={{ fontWeight: 600 }}>
                      {Math.round(party.confidence_score * 100)}%
                    </span>
                    <br />
                    Confidence
                  </div>
                )}
                {party.prior_filings !== undefined && (
                  <div style={{ fontSize: '11px', color: colors.text }}>
                    <span style={{ fontWeight: 600 }}>
                      {party.prior_filings}
                    </span>
                    <br />
                    Prior Filings
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </SectionWrapper>
  );
}
