/**
 * Step 4: Officer Signature & Certification
 * Final step: narrative, certification, and digital signature
 */

import React, { useEffect, useState } from 'react';
import { Lock } from 'lucide-react';
import { Step4Props } from '../types/ReferralGeneration.types';

export default function Step4OfficeSignature({
  data,
  onChange,
  isSubmitting = false
}: Step4Props) {
  const [officerInfo, setOfficerInfo] = useState(data);

  useEffect(() => {
    // Get officer info from session/context
    setOfficerInfo(prev => ({
      ...prev,
      officerId: 'OFFICER_001',
      officerName: 'John Smith',
      badgeNumber: '45821',
      district: 'Los Angeles Field Office'
    }));
  }, []);

  const handleNarrativeChange = (narrative: string) => {
    onChange({
      ...data,
      caseNarrative: narrative
    });
  };

  const handleCertificationChange = (accepted: boolean) => {
    onChange({
      ...data,
      certificationAccepted: accepted
    });
  };

  const narrativeLength = data.caseNarrative?.length || 0;
  const isNarrativeValid = narrativeLength >= 50 && narrativeLength <= 2000;

  return (
    <div className="step-form">
      <div className="step-header">
        <h2 className="step-title">Officer Signature & Certification</h2>
        <p className="step-description">
          Final review and digital certification of your analysis
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

      {/* Officer Information (Read-only) */}
      <div className="officer-info-section">
        <h3 className="section-title">Officer Information</h3>
        <div className="info-grid">
          <div className="info-row">
            <span className="info-label">Name:</span>
            <span className="info-value">{officerInfo.officerName || 'Not Loaded'}</span>
          </div>
          <div className="info-row">
            <span className="info-label">Badge Number:</span>
            <span className="info-value">{officerInfo.badgeNumber || '—'}</span>
          </div>
          <div className="info-row">
            <span className="info-label">District:</span>
            <span className="info-value">{officerInfo.district || '—'}</span>
          </div>
          <div className="info-row">
            <span className="info-label">Signing Time:</span>
            <span className="info-value">{new Date().toLocaleString()}</span>
          </div>
        </div>
      </div>

      {/* Case Narrative */}
      <div className="form-group">
        <label htmlFor="case-narrative" className="form-label required">
          Case Summary & Investigation Findings
        </label>
        <textarea
          id="case-narrative"
          value={data.caseNarrative || ''}
          onChange={(e) => handleNarrativeChange(e.target.value)}
          className="form-textarea"
          placeholder="Summarize your investigation findings, key evidence, and rationale for the recommended action..."
          minLength={50}
          maxLength={2000}
          disabled={isSubmitting}
        />
        <div className="textarea-info">
          <span className={`char-count ${isNarrativeValid ? 'valid' : 'invalid'}`}>
            {narrativeLength}/2000 characters
            {narrativeLength < 50 && ' (minimum 50 required)'}
          </span>
        </div>
      </div>

      {/* Certification */}
      <div className="certification-section">
        <div className="certification-box">
          <label className="checkbox-large">
            <input
              type="checkbox"
              checked={data.certificationAccepted || false}
              onChange={(e) => handleCertificationChange(e.target.checked)}
              disabled={isSubmitting}
            />
            <span className="checkbox-text">
              <strong>I certify that:</strong> I have reviewed all relevant evidence, conducted a thorough
              assessment, and my analysis above is accurate, complete, and represents my professional judgment.
              This certification serves as my digital signature on this analysis.
            </span>
          </label>
        </div>
      </div>

      {/* Security Notice */}
      <div className="security-notice">
        <Lock size={18} />
        <div>
          <p className="notice-title">Security & Compliance</p>
          <p className="notice-text">
            This form is submitted with your PIV/CAC authentication. All submissions are logged with your
            officer ID, timestamp, and are auditable for compliance purposes.
          </p>
        </div>
      </div>

      {/* Submission Status */}
      {isSubmitting && (
        <div className="submission-info">
          <div className="spinner-small"></div>
          <p>Submitting your analysis...</p>
        </div>
      )}

      {/* Summary Box */}
      <div className="summary-box">
        <h4>Analysis Summary</h4>
        <ul>
          <li>✓ Risk assessment confirmed</li>
          <li>✓ Evidence reviewed</li>
          <li>✓ Action selected</li>
          <li>✓ Case narrative provided</li>
          <li>{data.certificationAccepted ? '✓' : '○'} Certification accepted</li>
        </ul>
      </div>
    </div>
  );
}
