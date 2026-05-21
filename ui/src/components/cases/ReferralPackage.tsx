import React from 'react';
import ReferralNarrativeBanner from './ReferralNarrativeBanner';
import ReferralScorePipeline from './ReferralScorePipeline';
import ReferralEvidentiaryPanel from './ReferralEvidentiaryPanel';
import ReferralActionCenter from './ReferralActionCenter';
import { ReferralPackageData } from './ReferralPackage.types';
import './ReferralPackage.css';

interface ReferralPackageProps {
  data: ReferralPackageData;
  onExecuteReferral?: (notes: string) => void;
  onHoldExamine?: (notes: string) => void;
  onOverride?: (justifications: string[], notes: string) => void;
}

/**
 * ReferralPackage
 * Comprehensive investigative referral package integrating all analysis components
 *
 * Structure:
 * 1. Narrative Banner - High-risk alert with contextual narrative
 * 2. Score Pipeline - H1/H2/H3 progressive risk assessment
 * 3. Evidentiary Panel - 3 tabs: discrepancies, entity chain, what-if
 * 4. Action Center - Execute, hold, or override with justifications
 *
 * Accessibility:
 * - Semantic HTML with proper heading hierarchy
 * - All interactive elements keyboard accessible
 * - aria-live regions for dynamic updates
 * - WCAG 2.1 AA contrast compliance
 */
export default function ReferralPackage({
  data,
  onExecuteReferral = () => {},
  onHoldExamine = () => {},
  onOverride = () => {},
}: ReferralPackageProps) {
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

        {/* 3. Evidentiary Panel */}
        <ReferralEvidentiaryPanel
          discrepancies={data.discrepancies}
          entityChain={data.entityChain}
          conditionalScenarios={data.conditionalScenarios}
        />
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
