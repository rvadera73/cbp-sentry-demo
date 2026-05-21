import React, { useState } from 'react';
import {
  Check,
  AlertCircle,
  X,
  ChevronRight,
} from 'lucide-react';
import {
  ReferralEvidentiaryPanelProps,
  Discrepancy,
  SupplyChainEntity,
} from './ReferralPackage.types';
import './ReferralEvidentiaryPanel.css';

/**
 * Tab 1: Evidentiary Discrepancies
 * Side-by-side comparison of declared vs. verified information
 */
function EvidentiarySummaryTab({ discrepancies }: { discrepancies: Discrepancy[] }) {
  const getStatusIcon = (status: Discrepancy['status']) => {
    switch (status) {
      case 'match':
        return <Check size={18} className="status-icon status-icon--match" />;
      case 'partial':
        return <AlertCircle size={18} className="status-icon status-icon--partial" />;
      case 'missing':
      case 'mismatch':
        return <X size={18} className="status-icon status-icon--missing" />;
      default:
        return null;
    }
  };

  return (
    <div className="evidentiary-tab">
      <div className="discrepancy-table">
        <div className="table-header">
          <div className="table-col--field">Field</div>
          <div className="table-col--declared">Declared</div>
          <div className="table-col--verified">Verified</div>
          <div className="table-col--status">Status</div>
        </div>

        {discrepancies.map((discrepancy, idx) => (
          <div key={idx} className={`table-row status-${discrepancy.status}`}>
            <div className="table-col--field">
              <span className="field-label">{discrepancy.field}</span>
            </div>
            <div className="table-col--declared">
              <span className="field-value">{discrepancy.declared}</span>
            </div>
            <div className="table-col--verified">
              <span className="field-value">{discrepancy.verified}</span>
            </div>
            <div className="table-col--status">
              {getStatusIcon(discrepancy.status)}
              <span className="status-text">{discrepancy.status}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

/**
 * Tab 2: Entity Chain Tree
 * Vertical flow diagram of supply chain entities with risk indicators
 */
interface EntityChainTreeProps {
  entities: SupplyChainEntity[];
}

function EntityChainTreeTab({ entities }: EntityChainTreeProps) {
  const getRiskBorderClass = (riskLevel: string) => {
    switch (riskLevel) {
      case 'critical':
      case 'high':
        return 'entity-node--high-risk';
      case 'medium':
        return 'entity-node--medium-risk';
      case 'low':
        return 'entity-node--low-risk';
      default:
        return 'entity-node--neutral';
    }
  };

  return (
    <div className="entity-chain-tab">
      <div className="entity-flow">
        {entities.map((entity, idx) => (
          <React.Fragment key={idx}>
            <div className={`entity-node ${getRiskBorderClass(entity.riskLevel)}`}>
              <div className="entity-node__content">
                <h4 className="entity-node__name">{entity.name}</h4>
                <p className="entity-node__country">{entity.country}</p>
                {entity.entityType && (
                  <span className="entity-node__type">{entity.entityType}</span>
                )}
              </div>
            </div>

            {/* Arrow between entities */}
            {idx < entities.length - 1 && (
              <div className="flow-arrow" aria-hidden="true">
                <ChevronRight size={20} />
              </div>
            )}
          </React.Fragment>
        ))}
      </div>
    </div>
  );
}

/**
 * Tab 3: What-If Simulation
 * Interactive conditional scenarios with dynamic score updates
 */
function WhatIfSimulationTab({
  scenarios,
  baselineScore,
}: {
  scenarios: Array<{
    condition: string;
    description: string;
    projectedScore: number;
    isActive: boolean;
  }>;
  baselineScore: number;
}) {
  const [activeScenarios, setActiveScenarios] = useState<Set<number>>(
    new Set(scenarios.map((s, i) => s.isActive ? i : -1).filter(i => i !== -1))
  );

  const handleToggle = (idx: number) => {
    const newActive = new Set(activeScenarios);
    if (newActive.has(idx)) {
      newActive.delete(idx);
    } else {
      newActive.add(idx);
    }
    setActiveScenarios(newActive);
  };

  const projectedScore = activeScenarios.size > 0
    ? Math.round(
        scenarios.reduce((sum, s, i) => {
          return activeScenarios.has(i) ? sum + (s.projectedScore - baselineScore) : sum;
        }, baselineScore)
      )
    : baselineScore;

  return (
    <div className="whatif-tab">
      <div className="whatif-container">
        <div className="whatif-scenarios">
          {scenarios.map((scenario, idx) => (
            <div key={idx} className="scenario-row">
              <label className="scenario-checkbox">
                <input
                  type="checkbox"
                  checked={activeScenarios.has(idx)}
                  onChange={() => handleToggle(idx)}
                  aria-label={`Toggle scenario: ${scenario.condition}`}
                />
                <span className="checkbox-marker" />
              </label>

              <div className="scenario-content">
                <h4 className="scenario-title">{scenario.condition}</h4>
                <p className="scenario-description">{scenario.description}</p>
              </div>

              <div className="scenario-score">
                <span className="score-label">Projected:</span>
                <span
                  className="score-value"
                  aria-label={`Projected score: ${scenario.projectedScore} out of 100`}
                >
                  {scenario.projectedScore}/100
                </span>
              </div>
            </div>
          ))}
        </div>

        {/* Projected Score Summary */}
        <div className="whatif-summary">
          <div className="summary-item">
            <span className="summary-label">Baseline Score:</span>
            <span className="summary-value">{baselineScore}/100</span>
          </div>
          <div className="summary-item">
            <span className="summary-label">Projected Score:</span>
            <span
              className="summary-value summary-value--projected"
              aria-live="polite"
              aria-atomic="true"
            >
              {projectedScore}/100
            </span>
          </div>
          <div className="summary-delta">
            <span className="delta-label">Delta:</span>
            <span
              className={`delta-value ${
                projectedScore < baselineScore ? 'delta-positive' : 'delta-negative'
              }`}
            >
              {projectedScore - baselineScore > 0 ? '+' : ''}
              {projectedScore - baselineScore}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

/**
 * ReferralEvidentiaryPanel
 * Tabbed panel with 3 investigative views
 *
 * Tab 1: Evidentiary Discrepancies - declared vs. verified comparison
 * Tab 2: Entity Chain Tree - supply chain visualization
 * Tab 3: What-If Simulation - conditional scenario modeling
 *
 * Accessibility:
 * - role="tablist", role="tab", role="tabpanel"
 * - aria-selected, aria-controls for tab management
 * - All interactive elements keyboard accessible
 */
export default function ReferralEvidentiaryPanel({
  discrepancies,
  entityChain,
  conditionalScenarios,
}: ReferralEvidentiaryPanelProps) {
  const [activeTab, setActiveTab] = useState(0);

  const tabs = [
    { label: 'Evidentiary Discrepancies', id: 'tab-evidentiary' },
    { label: 'Entity Chain Tree', id: 'tab-entity' },
    { label: 'What-If Simulation', id: 'tab-whatif' },
  ];

  const handleTabChange = (idx: number) => {
    setActiveTab(idx);
  };

  const handleTabKeyDown = (
    e: React.KeyboardEvent,
    idx: number,
    tabsLength: number
  ) => {
    let newIdx = idx;

    if (e.key === 'ArrowRight') {
      e.preventDefault();
      newIdx = (idx + 1) % tabsLength;
    } else if (e.key === 'ArrowLeft') {
      e.preventDefault();
      newIdx = (idx - 1 + tabsLength) % tabsLength;
    } else if (e.key === 'Home') {
      e.preventDefault();
      newIdx = 0;
    } else if (e.key === 'End') {
      e.preventDefault();
      newIdx = tabsLength - 1;
    }

    if (newIdx !== idx) {
      setActiveTab(newIdx);
      // Focus the newly selected tab
      setTimeout(() => {
        const tabButton = document.querySelector(`[data-tab-index="${newIdx}"]`) as HTMLElement;
        if (tabButton) {
          tabButton.focus();
        }
      }, 0);
    }
  };

  return (
    <div className="referral-evidentiary-panel">
      {/* Tab List */}
      <div className="evidentiary-tabs" role="tablist">
        {tabs.map((tab, idx) => (
          <button
            key={tab.id}
            role="tab"
            aria-selected={activeTab === idx}
            aria-controls={tab.id}
            data-tab-index={idx}
            className={`evidentiary-tab-button ${activeTab === idx ? 'active' : ''}`}
            onClick={() => handleTabChange(idx)}
            onKeyDown={(e) => handleTabKeyDown(e, idx, tabs.length)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Panels */}
      <div className="evidentiary-content">
        {/* Tab 1: Evidentiary Discrepancies */}
        <div
          id="tab-evidentiary"
          role="tabpanel"
          aria-labelledby={tabs[0].id}
          className={`evidentiary-panel ${activeTab === 0 ? 'active' : ''}`}
        >
          <EvidentiarySummaryTab discrepancies={discrepancies} />
        </div>

        {/* Tab 2: Entity Chain Tree */}
        <div
          id="tab-entity"
          role="tabpanel"
          aria-labelledby={tabs[1].id}
          className={`evidentiary-panel ${activeTab === 1 ? 'active' : ''}`}
        >
          <EntityChainTreeTab entities={entityChain.entities} />
        </div>

        {/* Tab 3: What-If Simulation */}
        <div
          id="tab-whatif"
          role="tabpanel"
          aria-labelledby={tabs[2].id}
          className={`evidentiary-panel ${activeTab === 2 ? 'active' : ''}`}
        >
          <WhatIfSimulationTab
            scenarios={conditionalScenarios}
            baselineScore={100 - Math.round(
              conditionalScenarios.reduce((sum, s) => sum + s.projectedScore, 0) / conditionalScenarios.length
            )}
          />
        </div>
      </div>
    </div>
  );
}
