import React, { useState } from 'react';
import {
  ReferralSection3_1,
  ReferralSection3_2,
  ReferralSection3_3,
  ReferralSection3_4,
  ReferralSection3_5,
  ReferralSection3_6,
  ReferralSection3_7,
  ReferralSection3_8,
  ReferralSection3_9,
  ReferralSection3_10,
  ReferralSection3_11,
  ReferralSection3_12,
  ReferralSection3_13,
  ReferralSection3_14,
} from './referral-sections';
import { ReferralPackageData } from './ReferralPackage.types';
import ReferralNarrativeBanner from './ReferralNarrativeBanner';
import ReferralScorePipeline from './ReferralScorePipeline';
import ReferralActionCenter from './ReferralActionCenter';
import '../referral-sections.css';
import './ReferralPackage.css';

interface ReferralPackageEnhancedProps {
  data: ReferralPackageData;
  onExecuteReferral?: (notes: string) => void;
  onHoldExamine?: (notes: string) => void;
  onOverride?: (justifications: string[], notes: string) => void;
}

/**
 * ReferralPackageEnhanced
 *
 * Comprehensive 14-section investigation referral package with:
 * - High-impact narrative banner + H1/H2/H3 risk scoring
 * - Detailed investigation sections (3-1 through 3-14)
 * - Section expand/collapse with expand-all controls
 * - Icon system, status badges, and anomaly detection
 * - Progressive disclosure of detailed analysis
 * - Full keyboard accessibility and print support
 * - SHAP-based feature importance (Section 3-12)
 * - Interactive what-if scenarios (Section 3-13)
 * - Legal authority citations (Section 3-11)
 *
 * Accessibility:
 * - WCAG 2.1 AA compliant
 * - Keyboard navigation (Tab, Enter, Space)
 * - Screen reader support with proper heading hierarchy
 * - High-contrast badges (4.5:1 minimum)
 * - Semantic HTML structure
 */
export default function ReferralPackageEnhanced({
  data,
  onExecuteReferral = () => {},
  onHoldExamine = () => {},
  onOverride = () => {},
}: ReferralPackageEnhancedProps) {
  const [expandAllSections, setExpandAllSections] = useState(false);

  const allSectionsPresent = !!(
    data.section_3_1 &&
    data.section_3_2 &&
    data.section_3_3 &&
    data.section_3_4 &&
    data.section_3_5 &&
    data.section_3_6 &&
    data.section_3_7 &&
    data.section_3_8 &&
    data.section_3_9 &&
    data.section_3_10 &&
    data.section_3_11 &&
    data.section_3_12 &&
    data.section_3_13 &&
    data.section_3_14
  );

  const sectionsPresent = [
    data.section_3_1,
    data.section_3_2,
    data.section_3_3,
    data.section_3_4,
    data.section_3_5,
    data.section_3_6,
    data.section_3_7,
    data.section_3_8,
    data.section_3_9,
    data.section_3_10,
    data.section_3_11,
    data.section_3_12,
    data.section_3_13,
    data.section_3_14,
  ].filter(Boolean).length;

  return (
    <section className="referral-package" aria-labelledby="referral-title">
      <h2 id="referral-title" className="referral-package__title">
        Referral Package: Illegal Transshipment Investigation
      </h2>

      <div className="referral-package__content">
        {/* 1. Narrative Banner */}
        <ReferralNarrativeBanner
          shipper_name={data.shipper_name}
          shipper_country={data.shipper_country}
          declared_origin={data.declared_origin}
          actual_origin={data.actual_origin}
          risk_score={data.risk_score}
          vessel_path={data.vessel_path}
        />

        {/* 2. Score Pipeline */}
        <ReferralScorePipeline
          h1_score={data.h1_score}
          h2_score={data.h2_score}
          h3_score={data.h3_score}
        />

        {/* Section Control Bar */}
        {allSectionsPresent && (
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              padding: '16px 20px',
              backgroundColor: '#f0f4f8',
              border: '1px solid #e5e8eb',
              borderRadius: '6px',
              marginTop: '24px',
              marginBottom: '16px',
            }}
          >
            <h3
              style={{
                margin: 0,
                fontSize: '14px',
                fontWeight: 600,
                color: '#1a202c',
              }}
            >
              14 Investigation Sections ({sectionsPresent} available)
            </h3>
            <button
              onClick={() => setExpandAllSections(!expandAllSections)}
              style={{
                padding: '6px 12px',
                backgroundColor: expandAllSections ? '#013060' : '#ffffff',
                color: expandAllSections ? '#ffffff' : '#013060',
                border: '1px solid #013060',
                borderRadius: '4px',
                fontWeight: 600,
                fontSize: '12px',
                cursor: 'pointer',
                transition: 'all 0.2s',
              }}
              onMouseEnter={(e) => {
                if (expandAllSections) {
                  (e.target as HTMLButtonElement).style.backgroundColor = '#0b4a6b';
                }
              }}
              onMouseLeave={(e) => {
                if (expandAllSections) {
                  (e.target as HTMLButtonElement).style.backgroundColor = '#013060';
                }
              }}
              aria-label={expandAllSections ? 'Collapse all sections' : 'Expand all sections'}
            >
              {expandAllSections ? 'Collapse All' : 'Expand All'}
            </button>
          </div>
        )}

        {/* 3. Investigation Sections (3-1 through 3-14) */}
        <div className="referral-sections-container">
          {data.section_3_1 && (
            <ReferralSection3_1
              data={data.section_3_1}
              defaultExpanded={expandAllSections}
            />
          )}

          {data.section_3_2 && (
            <ReferralSection3_2
              data={data.section_3_2}
              defaultExpanded={expandAllSections}
            />
          )}

          {data.section_3_3 && (
            <ReferralSection3_3
              data={data.section_3_3}
              defaultExpanded={expandAllSections}
            />
          )}

          {data.section_3_4 && (
            <ReferralSection3_4
              data={data.section_3_4}
              defaultExpanded={expandAllSections}
            />
          )}

          {data.section_3_5 && (
            <ReferralSection3_5
              data={data.section_3_5}
              defaultExpanded={expandAllSections}
            />
          )}

          {data.section_3_6 && (
            <ReferralSection3_6
              data={data.section_3_6}
              defaultExpanded={expandAllSections}
            />
          )}

          {data.section_3_7 && (
            <ReferralSection3_7
              data={data.section_3_7}
              defaultExpanded={expandAllSections}
            />
          )}

          {data.section_3_8 && (
            <ReferralSection3_8
              data={data.section_3_8}
              defaultExpanded={expandAllSections}
            />
          )}

          {data.section_3_9 && (
            <ReferralSection3_9
              data={data.section_3_9}
              defaultExpanded={expandAllSections}
            />
          )}

          {data.section_3_10 && (
            <ReferralSection3_10
              data={data.section_3_10}
              defaultExpanded={expandAllSections}
            />
          )}

          {data.section_3_11 && (
            <ReferralSection3_11
              data={data.section_3_11}
              defaultExpanded={expandAllSections}
            />
          )}

          {data.section_3_12 && (
            <ReferralSection3_12
              data={data.section_3_12}
              defaultExpanded={expandAllSections}
            />
          )}

          {data.section_3_13 && (
            <ReferralSection3_13
              data={data.section_3_13}
              defaultExpanded={expandAllSections}
            />
          )}

          {data.section_3_14 && (
            <ReferralSection3_14
              data={data.section_3_14}
              defaultExpanded={expandAllSections}
            />
          )}

          {sectionsPresent === 0 && (
            <div
              style={{
                padding: '40px',
                textAlign: 'center',
                backgroundColor: '#f7fafc',
                border: '1px solid #e5e8eb',
                borderRadius: '6px',
                color: '#5a6c7d',
              }}
            >
              <p style={{ margin: 0, fontSize: '14px' }}>
                No detailed investigation sections available. The referral package includes only the summary analysis
                (Narrative Banner + H1/H2/H3 Scores).
              </p>
            </div>
          )}
        </div>
      </div>

      {/* 4. Action Center (Sticky Footer) */}
      <ReferralActionCenter
        risk_score={data.risk_score}
        onExecuteReferral={onExecuteReferral}
        onHoldExamine={onHoldExamine}
        onOverride={onOverride}
      />
    </section>
  );
}
