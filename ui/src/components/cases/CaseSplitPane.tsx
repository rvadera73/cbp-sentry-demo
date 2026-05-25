import React, { useEffect } from 'react';
import CaseCard, { CaseCardData } from './CaseCard';
import CORDEntityChain from './CORDEntityChain';
import { useWorkflow } from '../../context/WorkflowContext';
import './CaseSplitPane.css';

interface CaseSplitPaneProps {
  cases: CaseCardData[];
  selectedCaseId: string | null;
  onCaseSelect?: (caseId: string) => void;
  onCaseClick?: (caseId: string) => void;
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
