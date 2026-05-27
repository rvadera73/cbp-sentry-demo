/**
 * Step 1: Risk Assessment Confirmation
 * Officer agrees/adjusts risk score and confidence level
 */

import React from 'react';
import { Step1Props } from '../types/ReferralGeneration.types';

export default function Step1RiskAssessment({
  data,
  currentRiskScore,
  onChange
}: Step1Props) {
  const handleAgreeChange = (agree: boolean) => {
    onChange({
      ...data,
      agreeWithScore: agree,
      officerScore: agree ? undefined : data.officerScore,
      adjustmentReason: agree ? '' : data.adjustmentReason
    });
  };

  const handleScoreChange = (score: number) => {
    onChange({
      ...data,
      officerScore: score
    });
  };

  const handleReasonChange = (reason: string) => {
    onChange({
      ...data,
      adjustmentReason: reason
    });
  };

  const handleConfidenceChange = (confidence: 'low' | 'medium' | 'high') => {
    onChange({
      ...data,
      confidence
    });
  };

  return (
    <div className="step-form">
      <div className="step-header">
        <h2 className="step-title">Risk Assessment Confirmation</h2>
        <p className="step-description">
          Review the Sentry-calculated risk score and confirm or adjust it based on your assessment
        </p>
      </div>

      {data.validationErrors && data.validationErrors.length > 0 && (
        <div className="validation-errors">
          <h4>Please correct the following:</h4>
          <ul>
            {data.validationErrors.map((err, idx) => (
              <li key={idx}>{err}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="form-group">
        <div className="risk-score-display">
          <span className="score-label">System Risk Score:</span>
          <span className="score-value">{currentRiskScore}/100</span>
        </div>
      </div>

      <div className="form-group">
        <span className="form-label required">Do you agree with this assessment?</span>
        <div className="radio-group">
          <label className="radio-option">
            <input
              type="radio"
              name="agree"
              checked={data.agreeWithScore === true}
              onChange={() => handleAgreeChange(true)}
            />
            <span className="option-text">Yes, the system score is appropriate</span>
          </label>
          <label className="radio-option">
            <input
              type="radio"
              name="agree"
              checked={data.agreeWithScore === false}
              onChange={() => handleAgreeChange(false)}
            />
            <span className="option-text">No, I need to adjust the score</span>
          </label>
        </div>
      </div>

      {data.agreeWithScore === false && (
        <>
          <div className="form-group">
            <label htmlFor="officer-score" className="form-label required">
              Your Assessment Score
            </label>
            <div className="score-input-group">
              <input
                id="officer-score"
                type="number"
                min="0"
                max="100"
                value={data.officerScore || ''}
                onChange={(e) => handleScoreChange(parseInt(e.target.value))}
                className="form-input"
                placeholder="Enter score 0-100"
              />
              <div className="score-feedback">
                {data.officerScore !== undefined && (
                  <span className={`score-indicator risk-${getRiskLevel(data.officerScore).toLowerCase()}`}>
                    {getRiskLevel(data.officerScore)}
                  </span>
                )}
              </div>
            </div>
          </div>

          <div className="form-group">
            <label htmlFor="adjustment-reason" className="form-label required">
              Why are you adjusting the score?
            </label>
            <textarea
              id="adjustment-reason"
              value={data.adjustmentReason || ''}
              onChange={(e) => handleReasonChange(e.target.value)}
              className="form-textarea"
              placeholder="Explain your rationale for score adjustment..."
              minLength={50}
              maxLength={500}
            />
            <div className="textarea-info">
              <span className="char-count">
                {data.adjustmentReason?.length || 0}/500 characters
              </span>
            </div>
          </div>
        </>
      )}

      <div className="form-group">
        <span className="form-label required">Confidence in Your Assessment</span>
        <div className="radio-group">
          <label className="radio-option">
            <input
              type="radio"
              name="confidence"
              value="low"
              checked={data.confidence === 'low'}
              onChange={(e) => handleConfidenceChange(e.target.value as 'low' | 'medium' | 'high')}
            />
            <span className="option-text">Low (40-60% confident)</span>
          </label>
          <label className="radio-option">
            <input
              type="radio"
              name="confidence"
              value="medium"
              checked={data.confidence === 'medium'}
              onChange={(e) => handleConfidenceChange(e.target.value as 'low' | 'medium' | 'high')}
            />
            <span className="option-text">Medium (60-80% confident)</span>
          </label>
          <label className="radio-option">
            <input
              type="radio"
              name="confidence"
              value="high"
              checked={data.confidence === 'high'}
              onChange={(e) => handleConfidenceChange(e.target.value as 'low' | 'medium' | 'high')}
            />
            <span className="option-text">High (80%+ confident)</span>
          </label>
        </div>
      </div>
    </div>
  );
}

function getRiskLevel(score: number): string {
  if (score >= 70) return 'HIGH';
  if (score >= 50) return 'MEDIUM';
  if (score >= 40) return 'LOW';
  return 'MINIMAL';
}
