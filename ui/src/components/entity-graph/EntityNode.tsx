/**
 * Custom React Flow node for entity visualization.
 *
 * Displays entity information with risk coloring and warning indicators.
 */

import React from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import { FlowNodeData } from './types';
import { getEntityTypeBadge } from './utils';
import './EntityNode.css';

export default function EntityNode({ data, selected }: NodeProps<FlowNodeData>) {
  const { entity, hasWarnings } = data;

  const riskScore = entity.risk_score ?? 0;
  let riskLevel = 'low';
  if (riskScore >= 80) riskLevel = 'critical';
  else if (riskScore >= 60) riskLevel = 'high';
  else if (riskScore >= 40) riskLevel = 'medium';

  return (
    <div className={`entity-node ${riskLevel} ${selected ? 'selected' : ''} ${hasWarnings ? 'has-warnings' : ''}`}>
      <Handle type="target" position={Position.Top} />

      <div className="entity-node-header">
        <div className="entity-badge">{getEntityTypeBadge(entity.entity_type)}</div>
        <div className="entity-title">{entity.name}</div>
        {hasWarnings && <div className="warning-indicator">⚠️</div>}
      </div>

      <div className="entity-node-body">
        <div className="entity-meta">
          <span className="country-code">{entity.country}</span>
          <span className="role-label">{entity.role}</span>
        </div>

        <div className="entity-metrics">
          <div className="metric">
            <span className="label">Confidence:</span>
            <span className="value">{(entity.confidence * 100).toFixed(0)}%</span>
          </div>
          {entity.risk_score !== undefined && (
            <div className="metric">
              <span className="label">Risk:</span>
              <span className={`value risk-${riskLevel}`}>{entity.risk_score}/100</span>
            </div>
          )}
        </div>
      </div>

      <Handle type="source" position={Position.Bottom} />
    </div>
  );
}
