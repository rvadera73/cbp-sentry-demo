import React, { useEffect } from 'react';
import CaseCard, { CaseCardData } from './CaseCard';
import CORDEntityChain from './CORDEntityChain';
import ReferralPackage from './ReferralPackage';
import { ReferralPackageData, PipelineScore, Discrepancy, EntityChain, ConditionalScenario } from './ReferralPackage.types';
import { useWorkflow } from '../../context/WorkflowContext';
import './CaseSplitPane.css';

interface CaseSplitPaneProps {
  cases: CaseCardData[];
  selectedCaseId: string | null;
  onCaseSelect?: (caseId: string) => void;
  onCaseClick?: (caseId: string) => void;
}

/**
 * buildReferralPackageData: Transform case data into ReferralPackageData structure
 * This helper maps existing case fields to the referral package type system
 */
function buildReferralPackageData(caseData: CaseCardData): ReferralPackageData {
  const risk = Math.round(caseData.risk_score || 0);

  // Score pipeline (H1, H2, H3) - distribute total risk across three assessment vectors
  const h1Score = Math.min(40, Math.floor(risk * 0.4));
  const h2Score = Math.min(40, Math.floor(risk * 0.35));
  const h3Score = Math.min(40, Math.floor(risk * 0.25));

  return {
    shipper_name: caseData.shipper_name,
    shipper_country: caseData.route_origin,
    consignee_name: caseData.consignee_name,
    declared_origin: caseData.route_origin,
    actual_origin: caseData.route_origin, // In real scenario, would come from vessel tracking data
    risk_score: risk,
    vessel_path: [caseData.route_origin, 'Port of Hong Kong', caseData.route_destination],

    h1_score: {
      score: h1Score,
      maxScore: 40,
      label: 'Macro Volume Anomaly (+240% YoY Spike)',
      algorithmicWeights: {
        'Trading Volume Variance': 45,
        'Corridor Traffic Pattern': 35,
        'Seasonal Adjustment': 20,
      },
    },

    h2_score: {
      score: h2Score,
      maxScore: 40,
      label: 'Vessel Risk - Transshipment Hub Dwell',
      algorithmicWeights: {
        'Port Dwell Time Anomaly': 50,
        'Co-loading Frequency': 35,
        'Flag State Risk Profile': 15,
      },
    },

    h3_score: {
      score: h3Score,
      maxScore: 40,
      label: 'Network Intelligence - Entity Chain Risk',
      algorithmicWeights: {
        'Entity Relationship Strength': 40,
        'Transaction Pattern Match': 35,
        'Sanctions/Watchlist Score': 25,
      },
    },

    discrepancies: [
      {
        field: 'Manufacturing Location',
        declared: caseData.route_origin,
        verified: 'Port of Hong Kong',
        status: 'mismatch',
      },
      {
        field: 'Port of Loading',
        declared: caseData.route_origin,
        verified: 'Port of Hong Kong',
        status: 'mismatch',
      },
      {
        field: 'HTS Commodity Code',
        declared: caseData.commodity_code,
        verified: caseData.commodity_code,
        status: 'match',
      },
      {
        field: 'Declared Value',
        declared: `$${caseData.declared_value.toLocaleString()}`,
        verified: 'Under Verification',
        status: 'partial',
      },
      {
        field: 'Factory Production Records',
        declared: 'Available',
        verified: 'MISSING',
        status: 'missing',
      },
    ],

    entityChain: {
      entities: [
        {
          name: 'CN Mfg Corp',
          country: 'China',
          riskLevel: 'high',
          entityType: 'Manufacturer',
        },
        {
          name: 'HK Trading Ltd',
          country: 'Hong Kong',
          riskLevel: 'medium',
          entityType: 'Trading House',
        },
        {
          name: 'VN Export Partners',
          country: 'Vietnam',
          riskLevel: 'medium',
          entityType: 'Exporter',
        },
        {
          name: caseData.shipper_name,
          country: caseData.route_origin,
          riskLevel: 'low',
          entityType: 'Freight Forwarder',
        },
        {
          name: caseData.consignee_name,
          country: caseData.route_destination,
          riskLevel: 'low',
          entityType: 'Importer',
        },
      ],
    },

    conditionalScenarios: [
      {
        condition: 'If Shipper becomes Established',
        description: 'Commercial history of 3+ years with CBP clearance',
        projectedScore: 89,
        isActive: false,
      },
      {
        condition: 'If Missing Docs Verified',
        description: 'Factory production and export documentation provided',
        projectedScore: 87,
        isActive: false,
      },
      {
        condition: 'If Pricing Aligns with Market',
        description: 'Third-party cost analysis confirms commodity valuation',
        projectedScore: 82,
        isActive: false,
      },
    ],
  };
}

/**
 * CaseSplitPane: Split-screen investigator view
 *
 * Layout:
 * - Left panel: Case list (scrollable independently)
 * - Right panel: Expanded detail + referral package
 *   - Buttons: [Accept] [Flag to CBP] [Override]
 *
 * Accessibility:
 * - Two distinct regions: list + detail
 * - aria-label on both
 * - Right panel updates with aria-live when case selected
 */
export default function CaseSplitPane({
  cases,
  selectedCaseId,
  onCaseSelect,
  onCaseClick,
}: CaseSplitPaneProps) {
  const { updateScore, advanceStep } = useWorkflow();
  const selectedCase = cases.find((c) => c.id === selectedCaseId);

  // Track case selection in workflow context
  useEffect(() => {
    if (selectedCase) {
      // Update scores based on selected case data
      const h1 = Math.min(40, Math.floor((selectedCase.risk_score || 0) * 0.4));
      const h2 = Math.min(40, Math.floor((selectedCase.risk_score || 0) * 0.35));
      const h3 = Math.min(40, Math.floor((selectedCase.risk_score || 0) * 0.25));

      updateScore(h1, h2, h3);

      // Advance to scoring step
      if (selectedCase.risk_score >= 40) {
        advanceStep('scoring', 'complete');
      }
    }
  }, [selectedCase?.id, updateScore, advanceStep]);

  return (
    <div className="case-split-pane">
      {/* Left Panel: Case List */}
      <div className="split-pane__left" role="region" aria-label="Case list panel">
        <div className="case-list-wrapper" role="list" aria-label={`${cases.length} cases`}>
          {cases.map((caseData) => (
            <div key={caseData.id} role="listitem">
              <CaseCard
                data={caseData}
                isSelected={selectedCaseId === caseData.id}
                onSelect={onCaseSelect}
                onClick={onCaseClick}
                variant="split"
                showArrow={false}
              />
            </div>
          ))}
        </div>
      </div>

      {/* Right Panel: Detail + Referral Package */}
      <div
        className="split-pane__right"
        role="region"
        aria-label="Case detail panel"
        aria-live="polite"
        aria-atomic="false"
      >
        {selectedCase ? (
          <div className="case-detail-container">
            {/* Case Header */}
            <div className="case-detail__header">
              <h2 className="case-detail__title">{selectedCase.shipper_name}</h2>
              <p className="case-detail__subtitle">{selectedCase.manifest_id}</p>
            </div>

            {/* Quick Stats */}
            <div className="case-detail__stats">
              <div className="stat-item">
                <span className="stat-label">Risk Score</span>
                <span className="stat-value">{Math.round(selectedCase.risk_score || 0)}/100</span>
              </div>
              <div className="stat-item">
                <span className="stat-label">Declared Value</span>
                <span className="stat-value">${(selectedCase.declared_value || 0).toLocaleString()}</span>
              </div>
              <div className="stat-item">
                <span className="stat-label">Filed</span>
                <span className="stat-value">{new Date(selectedCase.filing_date).toLocaleDateString()}</span>
              </div>
              {selectedCase.status && (
                <div className="stat-item">
                  <span className="stat-label">Status</span>
                  <span className="stat-value">{selectedCase.status}</span>
                </div>
              )}
            </div>

            {/* Logistics Detail */}
            <section className="case-detail__section">
              <h3 className="section-title">Logistics</h3>
              <div className="detail-grid">
                <div className="detail-row">
                  <span className="detail-label">Origin</span>
                  <span className="detail-value">{selectedCase.route_origin}</span>
                </div>
                <div className="detail-row">
                  <span className="detail-label">Destination</span>
                  <span className="detail-value">{selectedCase.route_destination}</span>
                </div>
                {selectedCase.corridor_name && (
                  <div className="detail-row">
                    <span className="detail-label">Corridor</span>
                    <span className="detail-value">{selectedCase.corridor_name}</span>
                  </div>
                )}
              </div>
            </section>

            {/* Entity Detail */}
            <section className="case-detail__section">
              <h3 className="section-title">Entity Information</h3>
              <div className="detail-grid">
                <div className="detail-row">
                  <span className="detail-label">Legal Name</span>
                  <span className="detail-value">{selectedCase.shipper_name}</span>
                </div>
                {selectedCase.trade_name && (
                  <div className="detail-row">
                    <span className="detail-label">Trade Name</span>
                    <span className="detail-value">{selectedCase.trade_name}</span>
                  </div>
                )}
                {selectedCase.entity_type && (
                  <div className="detail-row">
                    <span className="detail-label">Entity Type</span>
                    <span className="detail-value">{selectedCase.entity_type}</span>
                  </div>
                )}
                <div className="detail-row">
                  <span className="detail-label">Consignee</span>
                  <span className="detail-value">{selectedCase.consignee_name}</span>
                </div>
              </div>
            </section>

            {/* Commodity Detail */}
            <section className="case-detail__section">
              <h3 className="section-title">Commodity</h3>
              <div className="detail-grid">
                <div className="detail-row">
                  <span className="detail-label">HTS Code</span>
                  <code className="detail-value detail-code">{selectedCase.commodity_code}</code>
                </div>
                {selectedCase.commodity_description && (
                  <div className="detail-row detail-row--full">
                    <span className="detail-label">Description</span>
                    <span className="detail-value">{selectedCase.commodity_description}</span>
                  </div>
                )}
              </div>
            </section>

            {/* Entity Chain (CORD) */}
            <section className="case-detail__section">
              <h3 className="section-title">Entity Ownership Chain</h3>
              <CORDEntityChain
                shipper_name={selectedCase.shipper_name}
                shipper_country={selectedCase.route_origin}
                consignee_name={selectedCase.consignee_name}
                consignee_country={selectedCase.route_destination}
              />
            </section>

            {/* Referral Package - Integrated Investigation Tool */}
            {selectedCase.risk_score >= 40 && (
              <ReferralPackage
                data={buildReferralPackageData(selectedCase)}
                onExecuteReferral={(notes) => {
                  console.log('Execute referral:', selectedCase.id, notes);
                }}
                onHoldExamine={(notes) => {
                  console.log('Hold and examine:', selectedCase.id, notes);
                }}
                onOverride={(justifications, notes) => {
                  console.log('Override:', selectedCase.id, justifications, notes);
                }}
              />
            )}

            {/* Action Buttons */}
            <div className="case-detail__actions">
              <button
                type="button"
                className="action-btn action-btn--primary"
                aria-label="Accept this case"
              >
                Accept
              </button>
              <button
                type="button"
                className="action-btn action-btn--secondary"
                aria-label="Flag this case to CBP"
              >
                Flag to CBP
              </button>
              <button
                type="button"
                className="action-btn action-btn--secondary"
                aria-label="Override risk assessment"
              >
                Override
              </button>
            </div>
          </div>
        ) : (
          <div className="case-detail__empty">
            <p>Select a case to view details</p>
          </div>
        )}
      </div>
    </div>
  );
}
