/**
 * ISF enrichment warnings panel.
 *
 * Displays Element 9 mismatches, dwell anomalies, and other ISF-derived warnings
 * merged from the shipper node into the entity graph visualization.
 */

import React from 'react';
import { EntityGraph } from './types';
import { getWarningSeverityColor } from './utils';
import './ISFWarningsPanel.css';

interface ISFWarningsPanelProps {
  graph: EntityGraph;
}

export default function ISFWarningsPanel({ graph }: ISFWarningsPanelProps) {
  // Collect all warnings from the chain
  const allWarnings = graph.chain.reduce(
    (acc, entity) => {
      if (entity.warnings && entity.warnings.length > 0) {
        acc.push(
          ...entity.warnings.map((warning) => ({
            ...warning,
            entity: entity.name,
            entity_id: entity.entity_id,
          }))
        );
      }
      return acc;
    },
    [] as any[]
  );

  if (allWarnings.length === 0) {
    return null;
  }

  return (
    <div className="isf-warnings-panel">
      <div className="panel-header">
        <h4>🚨 ISF Enrichment Warnings ({allWarnings.length})</h4>
      </div>

      <div className="warnings-list">
        {allWarnings.map((warning, idx) => (
          <div
            key={idx}
            className={`warning-item severity-${warning.severity.toLowerCase()}`}
            style={{ borderLeftColor: getWarningSeverityColor(warning.severity) }}
          >
            <div className="warning-header">
              <span className="warning-type">{warning.type}</span>
              <span className={`severity-badge severity-${warning.severity.toLowerCase()}`}>
                {warning.severity}
              </span>
            </div>

            <div className="warning-entity">{warning.entity}</div>

            <div className="warning-message">{warning.message}</div>

            {warning.confidence !== undefined && (
              <div className="warning-confidence">
                Confidence: {(warning.confidence * 100).toFixed(0)}%
              </div>
            )}
          </div>
        ))}
      </div>

      <div className="warnings-summary">
        <div className="summary-stat critical">
          {allWarnings.filter((w) => w.severity === 'HIGH').length} High
        </div>
        <div className="summary-stat warning">
          {allWarnings.filter((w) => w.severity === 'MEDIUM').length} Medium
        </div>
        <div className="summary-stat info">
          {allWarnings.filter((w) => w.severity === 'LOW').length} Low
        </div>
      </div>
    </div>
  );
}
