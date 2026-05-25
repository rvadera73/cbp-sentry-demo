import React, { useState } from 'react';
import { getRiskLevel, isValidRiskBreakdown, exportBreakdownAsJSON, exportBreakdownAsCSV } from './utils';
import { RiskScoreBreakdownComponentProps } from './types';
import RiskScoreHeader from './RiskScoreHeader';
import RiskComponentTable from './RiskComponentTable';
import './RiskScoreBreakdown.css';

interface CollapsibleSectionProps {
  title: string;
  icon: string;
  expanded?: boolean;
  children: React.ReactNode;
}

const CollapsibleSection: React.FC<CollapsibleSectionProps> = ({
  title,
  icon,
  expanded = true,
  children
}) => {
  const [isOpen, setIsOpen] = useState(expanded);

  return (
    <div className="collapsible-section">
      <button
        className={`section-header ${isOpen ? 'open' : 'closed'}`}
        onClick={() => setIsOpen(!isOpen)}
      >
        <span className="section-icon">{icon}</span>
        <span className="section-title">{title}</span>
        <span className="section-toggle">{isOpen ? '−' : '+'}</span>
      </button>
      {isOpen && <div className="section-content">{children}</div>}
    </div>
  );
};

export const RiskScoreBreakdown: React.FC<RiskScoreBreakdownComponentProps> = ({
  data,
  loading = false,
  error,
  onRefresh
}) => {
  const [exportFormat, setExportFormat] = useState<'json' | 'csv'>('json');
  const [showExport, setShowExport] = useState(false);

  if (loading) {
    return (
      <div className="risk-breakdown-loading">
        <div className="spinner" />
        <p>Calculating risk score...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="risk-breakdown-error">
        <div className="error-icon">❌</div>
        <p className="error-message">{error}</p>
        {onRefresh && (
          <button className="btn-retry" onClick={onRefresh}>
            Try Again
          </button>
        )}
      </div>
    );
  }

  if (!data || !isValidRiskBreakdown(data)) {
    return (
      <div className="risk-breakdown-empty">
        <p>No risk breakdown data available</p>
      </div>
    );
  }

  const riskLevel = getRiskLevel(data.final_score);

  const handleExport = () => {
    let content = '';
    let filename = `risk-breakdown-${data.shipment_id}`;

    if (exportFormat === 'json') {
      content = exportBreakdownAsJSON(data);
      filename += '.json';
    } else {
      content = exportBreakdownAsCSV(data);
      filename += '.csv';
    }

    const blob = new Blob([content], { type: 'text/plain' });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    link.click();
    window.URL.revokeObjectURL(url);
  };

  return (
    <div className="risk-score-breakdown">
      <RiskScoreHeader
        score={data.final_score}
        confidence={data.confidence_interval}
        riskLevel={riskLevel}
      />

      <CollapsibleSection title="Component Details" icon="📊" expanded={true}>
        <RiskComponentTable components={data.components} />
      </CollapsibleSection>

      {data.calculation_table && (
        <CollapsibleSection title="Calculation Breakdown" icon="🧮" expanded={false}>
          <div className="calculation-section">
            <table className="calculation-table">
              <thead>
                <tr>
                  <th>Step</th>
                  <th>Description</th>
                  <th align="right">Value</th>
                </tr>
              </thead>
              <tbody>
                {data.calculation_table.calculation_steps.map((step, idx) => (
                  <tr key={idx}>
                    <td className="step-number">{step.step}</td>
                    <td className="step-description">{step.description}</td>
                    <td align="right" className="step-value">
                      {step.value.toFixed(2)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CollapsibleSection>
      )}

      {(data.corridor_risk_adjustment || data.additional_adjustments) && (
        <CollapsibleSection title="Adjustments & Modifiers" icon="⚙️" expanded={false}>
          <div className="adjustments-section">
            {data.corridor_risk_adjustment && (
              <div className="adjustment-card">
                <h5>{data.corridor_risk_adjustment.type}</h5>
                <p className="adjustment-reason">{data.corridor_risk_adjustment.reason}</p>
                <div className="adjustment-calculation">
                  <span className="adjustment-label">Calculation:</span>
                  <span className="adjustment-formula">
                    {data.corridor_risk_adjustment.baseline?.toFixed(1)} ×{' '}
                    {data.corridor_risk_adjustment.multiplier?.toFixed(2)} ={' '}
                    <strong>+{data.corridor_risk_adjustment.adjustment_points.toFixed(1)}</strong>
                  </span>
                </div>
              </div>
            )}

            {data.additional_adjustments?.map((adj, idx) => (
              <div key={idx} className="adjustment-card">
                <h5>{adj.type}</h5>
                <p className="adjustment-reason">{adj.reason}</p>
                <div className="adjustment-calculation">
                  <span className="adjustment-value">
                    {adj.adjustment_points >= 0 ? '+' : ''}
                    {adj.adjustment_points.toFixed(1)} points
                  </span>
                </div>
              </div>
            ))}
          </div>
        </CollapsibleSection>
      )}

      <div className="export-section">
        <button className="btn-export" onClick={() => setShowExport(!showExport)}>
          📥 Export Data
        </button>

        {showExport && (
          <div className="export-panel">
            <div className="export-format">
              <label>
                <input
                  type="radio"
                  name="export-format"
                  value="json"
                  checked={exportFormat === 'json'}
                  onChange={(e) => setExportFormat(e.target.value as 'json')}
                />
                JSON
              </label>
              <label>
                <input
                  type="radio"
                  name="export-format"
                  value="csv"
                  checked={exportFormat === 'csv'}
                  onChange={(e) => setExportFormat(e.target.value as 'csv')}
                />
                CSV
              </label>
            </div>
            <button className="btn-download" onClick={handleExport}>
              Download
            </button>
          </div>
        )}
      </div>

      <div className="breakdown-metadata">
        <p className="metadata-text">
          <strong>Shipment ID:</strong> {data.shipment_id}
        </p>
      </div>
    </div>
  );
};

export default RiskScoreBreakdown;
