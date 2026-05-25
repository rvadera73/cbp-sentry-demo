import React from 'react';
import { getRiskColor, getRiskLevel } from './utils';
import { RiskScoreHeaderProps } from './types';
import './RiskScoreHeader.css';

const RiskScoreHeader: React.FC<RiskScoreHeaderProps> = ({ score, confidence, riskLevel }) => {
  const color = getRiskColor(score);
  const level = getRiskLevel(score);

  return (
    <div className="risk-score-header">
      <div className="risk-score-card" style={{ borderLeftColor: color }}>
        <div className="score-display">
          <div>
            <div className="score-number" style={{ color }}>
              {Math.round(score)}
            </div>
            <div className="score-label">Risk Score</div>
          </div>
          <div className="risk-badge" style={{ backgroundColor: color }}>
            {level}
          </div>
        </div>

        <div className="score-meta">
          <span className="confidence-label">Confidence:</span>
          <span className="confidence-value">{confidence}</span>
        </div>

        <div className="score-range">
          <div className="range-bar">
            <div
              className="range-fill"
              style={{
                width: `${Math.min(100, score)}%`,
                backgroundColor: color
              }}
            />
          </div>
          <div className="range-labels">
            <span>0</span>
            <span>50</span>
            <span>100</span>
          </div>
        </div>

        <div className="risk-classification">
          <p>
            {level === 'CRITICAL' && 'Critical risk — immediate enforcement action recommended'}
            {level === 'HIGH' && 'High risk — enhanced examination and investigation recommended'}
            {level === 'MEDIUM' && 'Medium risk — standard examination procedures recommended'}
            {level === 'LOW' && 'Low risk — standard processing or clearance recommended'}
          </p>
        </div>
      </div>
    </div>
  );
};

export default RiskScoreHeader;
