import React, { useState } from 'react';
import { ChevronDown } from 'lucide-react';
import {
  ReferralActionCenterProps,
  OVERRIDE_JUSTIFICATIONS,
  OverrideJustification,
} from './ReferralPackage.types';
import './ReferralActionCenter.css';

/**
 * ReferralActionCenter
 * Sticky footer action panel with execute, hold, and override controls
 *
 * Features:
 * - [Execute TRLED Referral Package] button (primary, dark blue)
 * - [Hold & Examine on Arrival] button (secondary, warning color)
 * - Toggle: "Override System Risk Signal" + checkbox dropdown
 * - Text area: "Officer Investigation Notes & Analysis Log"
 *
 * Accessibility:
 * - aria-label on all inputs
 * - :focus-visible outline on buttons
 * - All state changes announced via aria-live
 */
export default function ReferralActionCenter({
  risk_score,
  onExecuteReferral,
  onHoldExamine,
  onOverride,
}: ReferralActionCenterProps) {
  const [showOverrideOptions, setShowOverrideOptions] = useState(false);
  const [selectedJustifications, setSelectedJustifications] = useState<Set<OverrideJustification>>(
    new Set()
  );
  const [notesContent, setNotesContent] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleJustificationToggle = (justification: OverrideJustification) => {
    const newSet = new Set(selectedJustifications);
    if (newSet.has(justification)) {
      newSet.delete(justification);
    } else {
      newSet.add(justification);
    }
    setSelectedJustifications(newSet);
  };

  const handleExecuteClick = () => {
    setIsSubmitting(true);
    onExecuteReferral(notesContent);
    // Reset after submission (in real app, would be controlled by parent)
    setTimeout(() => {
      setIsSubmitting(false);
      setNotesContent('');
    }, 1000);
  };

  const handleHoldClick = () => {
    setIsSubmitting(true);
    onHoldExamine(notesContent);
    setTimeout(() => {
      setIsSubmitting(false);
      setNotesContent('');
    }, 1000);
  };

  const handleOverrideClick = () => {
    if (selectedJustifications.size === 0) {
      alert('Please select at least one justification for override.');
      return;
    }
    setIsSubmitting(true);
    onOverride(Array.from(selectedJustifications), notesContent);
    setTimeout(() => {
      setIsSubmitting(false);
      setNotesContent('');
      setSelectedJustifications(new Set());
      setShowOverrideOptions(false);
    }, 1000);
  };

  const riskLevel = risk_score >= 70 ? 'HIGH' : risk_score >= 40 ? 'MEDIUM' : 'LOW';

  return (
    <div className="referral-action-center">
      {/* Notes Textarea */}
      <div className="action-section action-section--notes">
        <label htmlFor="investigation-notes" className="action-label">
          Officer Investigation Notes & Analysis Log
        </label>
        <textarea
          id="investigation-notes"
          className="action-textarea"
          placeholder="Document your investigative findings, procedural notes, and decision rationale..."
          value={notesContent}
          onChange={(e) => setNotesContent(e.target.value)}
          aria-label="Investigation notes text area"
          rows={4}
          disabled={isSubmitting}
        />
      </div>

      {/* Risk Score Indicator */}
      <div className="action-section action-section--risk">
        <span className="risk-indicator-label">Current Risk Assessment:</span>
        <span className={`risk-indicator-badge risk-badge--${riskLevel.toLowerCase()}`}>
          {riskLevel} ({Math.round(risk_score)}/100)
        </span>
      </div>

      {/* Override Toggle Section */}
      <div className="action-section action-section--override">
        <div className="override-toggle">
          <label className="override-checkbox">
            <input
              type="checkbox"
              checked={showOverrideOptions}
              onChange={(e) => setShowOverrideOptions(e.target.checked)}
              aria-label="Override system risk signal"
              disabled={isSubmitting}
            />
            <span className="checkbox-marker" />
            <span className="toggle-label">Override System Risk Signal</span>
          </label>
        </div>

        {/* Justification Dropdown */}
        {showOverrideOptions && (
          <div className="justification-dropdown" role="region" aria-label="Override justifications">
            <div className="justification-list">
              {OVERRIDE_JUSTIFICATIONS.map((justification) => (
                <label key={justification} className="justification-item">
                  <input
                    type="checkbox"
                    checked={selectedJustifications.has(justification)}
                    onChange={() => handleJustificationToggle(justification)}
                    aria-label={`Justification: ${justification}`}
                    disabled={isSubmitting}
                  />
                  <span className="justification-marker" />
                  <span className="justification-label">{justification}</span>
                </label>
              ))}
            </div>
            {selectedJustifications.size > 0 && (
              <div className="justification-summary" aria-live="polite" aria-atomic="true">
                <strong>{selectedJustifications.size}</strong> justification(s) selected
              </div>
            )}
          </div>
        )}
      </div>

      {/* Action Buttons */}
      <div className="action-buttons">
        <button
          type="button"
          className="action-btn action-btn--primary"
          onClick={handleExecuteClick}
          disabled={isSubmitting}
          aria-label="Execute TRLED Referral Package"
        >
          {isSubmitting ? 'Processing...' : 'Execute TRLED Referral Package'}
        </button>

        <button
          type="button"
          className="action-btn action-btn--secondary"
          onClick={handleHoldClick}
          disabled={isSubmitting}
          aria-label="Hold case and examine on arrival"
        >
          {isSubmitting ? 'Processing...' : 'Hold & Examine on Arrival'}
        </button>

        {showOverrideOptions && (
          <button
            type="button"
            className="action-btn action-btn--override"
            onClick={handleOverrideClick}
            disabled={isSubmitting || selectedJustifications.size === 0}
            aria-label="Submit override with justifications"
          >
            {isSubmitting ? 'Submitting...' : 'Submit Override'}
          </button>
        )}
      </div>
    </div>
  );
}
