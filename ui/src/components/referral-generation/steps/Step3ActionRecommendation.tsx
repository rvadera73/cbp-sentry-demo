/**
 * Step 3: Action Recommendation
 * Officer selects action and provides relevant details
 */

import React from 'react';
import { Step3Props, ACTION_OPTIONS } from '../types/ReferralGeneration.types';

export default function Step3ActionRecommendation({
  data,
  onChange
}: Step3Props) {
  const handleActionChange = (action: 'execute_trled' | 'hold_examine' | 'release_monitor') => {
    onChange({
      ...data,
      action
    });
  };

  const isTRLED = data.action === 'execute_trled';
  const isHold = data.action === 'hold_examine';
  const isRelease = data.action === 'release_monitor';

  return (
    <div className="step-form">
      <div className="step-header">
        <h2 className="step-title">Action Recommendation</h2>
        <p className="step-description">
          Select the recommended enforcement action for this shipment
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
        <span className="form-label required">Recommended Action</span>
        <div className="action-grid">
          {ACTION_OPTIONS.map(option => (
            <label key={option.id} className="action-option">
              <input
                type="radio"
                name="action"
                value={option.id}
                checked={data.action === option.id}
                onChange={() => handleActionChange(option.id as any)}
              />
              <div className="action-content">
                <span className="action-title">{option.label}</span>
                <span className="action-description">{option.description}</span>
              </div>
            </label>
          ))}
        </div>
      </div>

      {/* TRLED Specific Fields */}
      {isTRLED && (
        <>
          <div className="form-group">
            <label htmlFor="referral-type" className="form-label required">
              Referral Type
            </label>
            <select
              id="referral-type"
              value={data.referralType || 'EAPA'}
              onChange={(e) => onChange({ ...data, referralType: e.target.value as any })}
              className="form-select"
            >
              <option value="EAPA">EAPA Investigation</option>
              <option value="Duty_Evasion">Duty Evasion</option>
              <option value="Fraud">Fraud</option>
              <option value="Other">Other</option>
            </select>
          </div>

          <div className="form-group">
            <label htmlFor="priority" className="form-label required">
              Priority Level
            </label>
            <select
              id="priority"
              value={data.priority || 'high'}
              onChange={(e) => onChange({ ...data, priority: e.target.value as any })}
              className="form-select"
            >
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
            </select>
          </div>

          <div className="form-group">
            <label htmlFor="holding-period" className="form-label">
              Holding Period (days)
            </label>
            <input
              id="holding-period"
              type="number"
              min="1"
              max="90"
              value={data.holdingPeriodDays || 30}
              onChange={(e) => onChange({ ...data, holdingPeriodDays: parseInt(e.target.value) })}
              className="form-input"
            />
          </div>

          <div className="form-group">
            <label htmlFor="assigned-district" className="form-label">
              Assigned District/Office
            </label>
            <input
              id="assigned-district"
              type="text"
              value={data.assignedDistrict || ''}
              onChange={(e) => onChange({ ...data, assignedDistrict: e.target.value })}
              className="form-input"
              placeholder="e.g., Los Angeles Field Office"
            />
          </div>

          <div className="form-group">
            <label htmlFor="examiner-notes" className="form-label">
              Notes for Examiner
            </label>
            <textarea
              id="examiner-notes"
              value={data.examinerNotes || ''}
              onChange={(e) => onChange({ ...data, examinerNotes: e.target.value })}
              className="form-textarea"
              placeholder="Any special instructions or context..."
              rows={3}
            />
          </div>
        </>
      )}

      {/* Hold for Examination Fields */}
      {isHold && (
        <>
          <div className="form-group">
            <label htmlFor="hold-duration" className="form-label required">
              Hold Duration (days)
            </label>
            <input
              id="hold-duration"
              type="number"
              min="1"
              max="30"
              value={data.holdDurationDays || 5}
              onChange={(e) => onChange({ ...data, holdDurationDays: parseInt(e.target.value) })}
              className="form-input"
            />
          </div>

          <div className="form-group">
            <label htmlFor="exam-type" className="form-label required">
              Examination Type
            </label>
            <select
              id="exam-type"
              value={data.examinationType || 'documentary'}
              onChange={(e) => onChange({ ...data, examinationType: e.target.value as any })}
              className="form-select"
            >
              <option value="documentary">Documentary</option>
              <option value="physical">Physical</option>
              <option value="hybrid">Hybrid (Both)</option>
            </select>
          </div>

          <div className="form-group">
            <label htmlFor="exam-scope" className="form-label required">
              Examination Scope
            </label>
            <textarea
              id="exam-scope"
              value={data.examinationScope || ''}
              onChange={(e) => onChange({ ...data, examinationScope: e.target.value })}
              className="form-textarea"
              placeholder="Describe what should be examined..."
              rows={3}
            />
          </div>

          <div className="form-group">
            <label className="checkbox-option">
              <input
                type="checkbox"
                checked={data.notifyImporter || false}
                onChange={(e) => onChange({ ...data, notifyImporter: e.target.checked })}
              />
              <span className="option-text">Notify importer of examination</span>
            </label>
          </div>
        </>
      )}

      {/* Release with Monitoring Fields */}
      {isRelease && (
        <>
          <div className="form-group">
            <label htmlFor="monitoring-type" className="form-label required">
              Monitoring Type
            </label>
            <select
              id="monitoring-type"
              value={data.monitoringType || 'standard'}
              onChange={(e) => onChange({ ...data, monitoringType: e.target.value as any })}
              className="form-select"
            >
              <option value="standard">Standard Monitoring</option>
              <option value="enhanced">Enhanced Monitoring</option>
              <option value="realtime">Real-time Monitoring</option>
            </select>
          </div>

          <div className="form-group">
            <label htmlFor="monitoring-duration" className="form-label required">
              Monitoring Duration (days)
            </label>
            <input
              id="monitoring-duration"
              type="number"
              min="7"
              max="180"
              value={data.monitoringDurationDays || 60}
              onChange={(e) => onChange({ ...data, monitoringDurationDays: parseInt(e.target.value) })}
              className="form-input"
            />
          </div>

          <div className="form-group">
            <label htmlFor="conditions" className="form-label">
              Monitoring Conditions
            </label>
            <textarea
              id="conditions"
              value={data.conditions || ''}
              onChange={(e) => onChange({ ...data, conditions: e.target.value })}
              className="form-textarea"
              placeholder="e.g., Weekly import reporting, Trade flow analysis..."
              rows={3}
            />
          </div>

          <div className="form-group">
            <label className="checkbox-option">
              <input
                type="checkbox"
                checked={data.auditTrailFlag || false}
                onChange={(e) => onChange({ ...data, auditTrailFlag: e.target.checked })}
              />
              <span className="option-text">Flag for audit trail and follow-up</span>
            </label>
          </div>
        </>
      )}
    </div>
  );
}
