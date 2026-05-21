import React from 'react';
import { FileCheck } from 'lucide-react';
import { Section3_8_DocumentReview } from '../ReferralPackage.types';
import { SectionWrapper } from './SectionWrapper';

interface ReferralSection3_8Props {
  data: Section3_8_DocumentReview;
  defaultExpanded?: boolean;
}

export function ReferralSection3_8({
  data,
  defaultExpanded = false,
}: ReferralSection3_8Props) {
  const missingCount = data.documents.filter((d) => d.status === 'MISSING').length;
  const suspiciousCount = data.documents.filter((d) => d.status === 'SUSPICIOUS').length;
  const anomalyCount = missingCount + suspiciousCount;

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'PRESENT':
        return '✓';
      case 'MISSING':
        return '✗';
      case 'SUSPICIOUS':
        return '⚠️';
      default:
        return '?';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'PRESENT':
        return { bg: '#e7f4e4', border: '#2e8540', text: '#1b4d22' };
      case 'MISSING':
        return { bg: '#ffe6e6', border: '#d9381e', text: '#8b0000' };
      case 'SUSPICIOUS':
        return { bg: '#fff7e6', border: '#e6a100', text: '#7a5300' };
      default:
        return { bg: '#f0f4f8', border: '#5a6c7d', text: '#2d3748' };
    }
  };

  return (
    <SectionWrapper
      sectionId="section-3-8"
      sectionNumber="3-8"
      title="Document Review Checklist"
      icon={<FileCheck size={16} />}
      dataQuality="COMPLETE"
      anomalyCount={anomalyCount}
      defaultExpanded={defaultExpanded}
    >
      <div className="referral-section__stats">
        <div className="referral-section__stat">
          <span className="referral-section__stat-label">Total Documents</span>
          <span className="referral-section__stat-value">{data.documents.length}</span>
        </div>
        {data.checklist_completion !== undefined && (
          <div className="referral-section__stat">
            <span className="referral-section__stat-label">Completion</span>
            <span className="referral-section__stat-value">
              {data.checklist_completion}%
            </span>
          </div>
        )}
        {missingCount > 0 && (
          <div className="referral-section__stat">
            <span className="referral-section__stat-label">Missing</span>
            <span className="referral-section__stat-value" style={{ color: '#d9381e' }}>
              {missingCount}
            </span>
          </div>
        )}
        {suspiciousCount > 0 && (
          <div className="referral-section__stat">
            <span className="referral-section__stat-label">Suspicious</span>
            <span className="referral-section__stat-value" style={{ color: '#e6a100' }}>
              {suspiciousCount}
            </span>
          </div>
        )}
      </div>

      <table className="referral-section__table" style={{ marginTop: '16px' }}>
        <thead>
          <tr>
            <th style={{ width: '40%' }}>Document Type</th>
            <th style={{ width: '30%' }}>Document Name</th>
            <th style={{ width: '15%', textAlign: 'center' }}>Status</th>
            <th style={{ width: '15%', textAlign: 'center' }}>Risk Level</th>
          </tr>
        </thead>
        <tbody>
          {data.documents.map((doc, idx) => {
            const colors = getStatusColor(doc.status);

            return (
              <tr
                key={idx}
                style={{
                  backgroundColor: colors.bg,
                }}
              >
                <td style={{ color: colors.text, fontWeight: 600 }}>
                  {doc.doc_type}
                </td>
                <td style={{ color: colors.text }}>
                  {doc.doc_name.length > 30
                    ? doc.doc_name.substring(0, 30) + '…'
                    : doc.doc_name}
                </td>
                <td style={{ textAlign: 'center', color: colors.text, fontWeight: 600 }}>
                  {getStatusIcon(doc.status)} {doc.status}
                </td>
                <td style={{ textAlign: 'center' }}>
                  {doc.risk_level && (
                    <span
                      style={{
                        padding: '3px 6px',
                        borderRadius: '3px',
                        fontSize: '11px',
                        fontWeight: 600,
                        backgroundColor: colors.border,
                        color: 'white',
                        textTransform: 'uppercase',
                      }}
                    >
                      {doc.risk_level.substring(0, 3)}
                    </span>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>

      {anomalyCount > 0 && data.critical_gaps && data.critical_gaps.length > 0 && (
        <div style={{ marginTop: '16px' }}>
          <h4 style={{ margin: '0 0 12px 0', fontSize: '13px', fontWeight: 600, color: '#d9381e' }}>
            Critical Document Gaps
          </h4>
          {data.critical_gaps.map((gap, idx) => (
            <div
              key={idx}
              className="referral-section__evidence"
              style={{ borderLeftColor: '#d9381e' }}
            >
              <span style={{ fontSize: '12px', color: '#2d3748' }}>⚠️ {gap}</span>
            </div>
          ))}
        </div>
      )}

      {data.documents.some((d) => d.evidence) && (
        <div style={{ marginTop: '16px' }}>
          <h4 style={{ margin: '0 0 12px 0', fontSize: '13px', fontWeight: 600 }}>
            Evidence Notes
          </h4>
          {data.documents
            .filter((d) => d.evidence)
            .map((doc, idx) => (
              <div key={idx} className="referral-section__evidence">
                <span className="referral-section__evidence-label">
                  {doc.doc_type} ({doc.status})
                </span>
                {doc.evidence}
              </div>
            ))}
        </div>
      )}
    </SectionWrapper>
  );
}
