import React from 'react';
import { GitCompare } from 'lucide-react';
import { Section3_9_DocumentConsistency } from '../ReferralPackage.types';
import { SectionWrapper } from './SectionWrapper';

interface ReferralSection3_9Props {
  data: Section3_9_DocumentConsistency;
  defaultExpanded?: boolean;
}

export function ReferralSection3_9({
  data,
  defaultExpanded = false,
}: ReferralSection3_9Props) {
  const mismatchCount = data.checks.filter((c) => c.match_status === 'MISMATCH').length;
  const partialCount = data.checks.filter((c) => c.match_status === 'PARTIAL').length;
  const anomalyCount = mismatchCount + partialCount;

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'MATCH':
        return { bg: '#e7f4e4', border: '#2e8540', text: '#1b4d22', icon: '✓' };
      case 'MISMATCH':
        return { bg: '#ffe6e6', border: '#d9381e', text: '#8b0000', icon: '✗' };
      case 'PARTIAL':
        return { bg: '#fff7e6', border: '#e6a100', text: '#7a5300', icon: '⚠️' };
      default:
        return { bg: '#f0f4f8', border: '#5a6c7d', text: '#2d3748', icon: '?' };
    }
  };

  return (
    <SectionWrapper
      sectionId="section-3-9"
      sectionNumber="3-9"
      title="Document Consistency Matrix"
      icon={<GitCompare size={16} />}
      dataQuality="COMPLETE"
      anomalyCount={anomalyCount}
      defaultExpanded={defaultExpanded}
    >
      {data.overall_alignment_score !== undefined && (
        <div className="referral-section__stats">
          <div className="referral-section__stat">
            <span className="referral-section__stat-label">Alignment Score</span>
            <span className="referral-section__stat-value">
              {Math.round(data.overall_alignment_score)}%
            </span>
          </div>
          <div className="referral-section__stat">
            <span className="referral-section__stat-label">Total Checks</span>
            <span className="referral-section__stat-value">{data.checks.length}</span>
          </div>
          <div className="referral-section__stat">
            <span className="referral-section__stat-label">Matches</span>
            <span className="referral-section__stat-value" style={{ color: '#2e8540' }}>
              {data.checks.filter((c) => c.match_status === 'MATCH').length}
            </span>
          </div>
          <div className="referral-section__stat">
            <span className="referral-section__stat-label">Mismatches</span>
            <span className="referral-section__stat-value" style={{ color: '#d9381e' }}>
              {mismatchCount}
            </span>
          </div>
        </div>
      )}

      <table className="referral-section__table" style={{ marginTop: '16px' }}>
        <thead>
          <tr>
            <th style={{ width: '25%' }}>Field</th>
            <th style={{ width: '25%' }}>Source 1</th>
            <th style={{ width: '25%' }}>Source 2</th>
            <th style={{ width: '12.5%', textAlign: 'center' }}>Status</th>
            {data.checks.some((c) => c.alignment_score !== undefined) && (
              <th style={{ width: '12.5%', textAlign: 'center' }}>Alignment</th>
            )}
          </tr>
        </thead>
        <tbody>
          {data.checks.map((check, idx) => {
            const colors = getStatusColor(check.match_status);

            return (
              <tr
                key={idx}
                style={{
                  backgroundColor: colors.bg,
                }}
              >
                <td style={{ color: colors.text, fontWeight: 600 }}>
                  {check.field}
                </td>
                <td style={{ color: colors.text, fontSize: '12px' }}>
                  <code>{check.source_1.substring(0, 30)}</code>
                </td>
                <td style={{ color: colors.text, fontSize: '12px' }}>
                  <code>{check.source_2.substring(0, 30)}</code>
                </td>
                <td
                  style={{
                    textAlign: 'center',
                    color: colors.text,
                    fontWeight: 600,
                  }}
                >
                  {colors.icon} {check.match_status}
                </td>
                {data.checks.some((c) => c.alignment_score !== undefined) && (
                  <td style={{ textAlign: 'center', fontWeight: 600, color: colors.text }}>
                    {check.alignment_score !== undefined
                      ? `${check.alignment_score}%`
                      : '—'}
                  </td>
                )}
              </tr>
            );
          })}
        </tbody>
      </table>

      {data.overall_alignment_score !== undefined && (
        <div
          style={{
            marginTop: '16px',
            padding: '12px',
            backgroundColor: '#f0f4f8',
            borderRadius: '6px',
            border: '1px solid #d0dce5',
          }}
        >
          <div style={{ fontSize: '12px', fontWeight: 600, color: '#1a202c', marginBottom: '8px' }}>
            Consistency Analysis
          </div>
          <div style={{ width: '100%', height: '8px', backgroundColor: '#e5e8eb', borderRadius: '4px', overflow: 'hidden', marginBottom: '8px' }}>
            <div
              style={{
                height: '100%',
                width: `${data.overall_alignment_score}%`,
                backgroundColor: data.overall_alignment_score >= 80
                  ? '#2e8540'
                  : data.overall_alignment_score >= 60
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
            {data.overall_alignment_score >= 90
              ? 'Excellent document alignment. Minimal inconsistencies detected.'
              : data.overall_alignment_score >= 70
                ? 'Good alignment. Minor discrepancies present but not critical.'
                : data.overall_alignment_score >= 50
                  ? 'Moderate alignment issues. Requires further investigation.'
                  : 'Poor alignment. Significant inconsistencies require detailed analysis.'}
          </div>
        </div>
      )}

      {anomalyCount > 0 && (
        <div style={{ marginTop: '16px' }}>
          <h4
            style={{
              margin: '0 0 12px 0',
              fontSize: '13px',
              fontWeight: 600,
              color: '#d9381e',
            }}
          >
            Discrepancies Requiring Investigation
          </h4>
          {data.checks
            .filter((c) => c.match_status !== 'MATCH')
            .map((check, idx) => {
              const colors = getStatusColor(check.match_status);

              return (
                <div
                  key={idx}
                  className="referral-section__evidence"
                  style={{
                    borderLeftColor: colors.border,
                    backgroundColor: colors.bg,
                  }}
                >
                  <span className="referral-section__evidence-label">
                    {colors.icon} {check.field}
                  </span>
                  <div style={{ fontSize: '12px', color: '#2d3748', marginTop: '4px' }}>
                    <strong>Source 1:</strong> {check.source_1}
                    <br />
                    <strong>Source 2:</strong> {check.source_2}
                  </div>
                </div>
              );
            })}
        </div>
      )}
    </SectionWrapper>
  );
}
