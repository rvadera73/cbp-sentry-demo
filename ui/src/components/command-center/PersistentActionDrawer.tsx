import React, { useState } from 'react';
import { useCommandCenter } from '../../context/CommandCenterContext';
import { api } from '../../services/api';
import '../../styles/command-center/PersistentActionDrawer.css';

interface FeedbackOption {
  id: string;
  label: string;
  description: string;
}

const feedbackOptions: FeedbackOption[] = [
  { id: 'labor_strike', label: 'Verified Labor Strike Port Delay', description: 'Port labor action caused extended dwell' },
  { id: 'production_capacity', label: 'Valid Dual-Origin Production Capacity', description: 'Entity legitimately produces in multiple countries' },
  { id: 'seasonal_surge', label: 'Legitimate Seasonal Surge', description: 'Seasonal demand spike is normal for this corridor' },
  { id: 'carrier_schedule', label: 'Carrier Schedule Anomaly', description: 'Vessel routing based on carrier schedule, not evasion' },
  { id: 'correct_assessment', label: 'Correct Assessment', description: 'High-risk signal is valid and correctly assessed' },
];

export default function PersistentActionDrawer() {
  const { state } = useCommandCenter();
  const [showFeedback, setShowFeedback] = useState(false);
  const [selectedFeedback, setSelectedFeedback] = useState<string | null>(null);
  const [notes, setNotes] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const hasSelection = !!(state.selectedCorridor || state.selectedVessel);
  const canIssueHold = !!state.selectedVessel;
  const canGenerateReferral = !!(state.selectedCorridor || state.selectedVessel);

  const handleGenerateReferral = async () => {
    if (!canGenerateReferral) return;

    setIsLoading(true);
    try {
      const result = await api.generateReferral(
        state.selectedCorridor?.corridor_id,
        state.selectedVessel?.vessel_id,
        state.selectedCorridor?.manifest_ids || []
      );

      if (result?.status === 'success') {
        alert(`EAPA Referral Package generated: ${result.referral_id}`);
      } else {
        alert('Failed to generate referral package. Please try again.');
      }
    } catch (error) {
      console.error('Error generating referral:', error);
      alert('An error occurred while generating the referral package.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleIssueHold = async () => {
    if (!canIssueHold) return;

    setIsLoading(true);
    try {
      const result = await api.issueVesselHold(
        state.selectedVessel!.vessel_id,
        'FULL',
        'High-risk transshipment indicator detected'
      );

      if (result?.status === 'success') {
        alert(`Hold issued for ${state.selectedVessel!.vessel_name}. Hold ID: ${result.hold_id}`);
      } else {
        alert('Failed to issue hold. Please try again.');
      }
    } catch (error) {
      console.error('Error issuing hold:', error);
      alert('An error occurred while issuing the hold.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmitFeedback = async () => {
    if (!selectedFeedback) {
      alert('Please select a feedback category');
      return;
    }

    setIsLoading(true);
    try {
      const result = await api.logFeedbackOverride(
        selectedFeedback,
        notes,
        undefined,
        state.selectedVessel?.vessel_id
      );

      if (result?.status === 'success') {
        alert(`Feedback logged successfully. Feedback ID: ${result.feedback_id}`);
        setShowFeedback(false);
        setSelectedFeedback(null);
        setNotes('');
      } else {
        alert('Failed to log feedback. Please try again.');
      }
    } catch (error) {
      console.error('Error logging feedback:', error);
      alert('An error occurred while logging feedback.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="persistent-action-drawer">
      <div className="action-drawer__header">
        <h3>Investigation Actions</h3>
        {hasSelection && (
          <div className="action-drawer__selection-info">
            {state.selectedCorridor && (
              <span className="selection-badge">
                Corridor: {state.selectedCorridor.hts_chapter} • {state.selectedCorridor.origin_country}→{state.selectedCorridor.destination_country}
              </span>
            )}
            {state.selectedVessel && (
              <span className="selection-badge">
                Vessel: {state.selectedVessel.vessel_name}
              </span>
            )}
          </div>
        )}
      </div>

      {!hasSelection && (
        <div className="action-drawer__help-message" role="status" aria-live="polite">
          <p>👈 Select a corridor or vessel from the main view to enable investigation actions</p>
        </div>
      )}

      <div className="action-drawer__content">
        <div className="action-drawer__button-group" title={!canGenerateReferral ? 'Select a corridor or vessel first' : undefined}>
          <button
            className="action-drawer__btn action-drawer__btn--primary"
            onClick={handleGenerateReferral}
            aria-label="Generate formal CBP EAPA referral package"
            disabled={isLoading || !canGenerateReferral}
          >
            📋 Generate EAPA Referral
          </button>
          {!canGenerateReferral && (
            <span className="action-drawer__hint">Select corridor or vessel</span>
          )}
        </div>

        <div className="action-drawer__button-group" title={!canIssueHold ? 'Select a vessel first' : undefined}>
          <button
            className="action-drawer__btn action-drawer__btn--secondary"
            onClick={handleIssueHold}
            aria-label="Issue hold for physical examination on arrival"
            disabled={isLoading || !canIssueHold}
          >
            🚫 Issue Hold for Exam
          </button>
          {!canIssueHold && (
            <span className="action-drawer__hint">Select a vessel</span>
          )}
        </div>

        <div className="action-drawer__button-group">
          <button
            className="action-drawer__btn action-drawer__btn--secondary"
            onClick={() => setShowFeedback(!showFeedback)}
            aria-label="Log human feedback override for model training"
            aria-expanded={showFeedback}
            disabled={isLoading}
          >
            📝 Log Feedback
          </button>
        </div>
      </div>

      {showFeedback && (
        <div className="action-drawer__feedback" role="region" aria-label="Feedback override form">
          <div className="feedback-form">
            <label className="feedback-form__label">Override Category:</label>
            <div className="feedback-form__options">
              {feedbackOptions.map(option => (
                <div key={option.id} className="feedback-form__option">
                  <input
                    type="radio"
                    id={option.id}
                    name="feedback"
                    value={option.id}
                    checked={selectedFeedback === option.id}
                    onChange={e => setSelectedFeedback(e.target.value)}
                    aria-describedby={`${option.id}-desc`}
                  />
                  <label htmlFor={option.id} className="feedback-form__option-label">
                    {option.label}
                  </label>
                  <p id={`${option.id}-desc`} className="feedback-form__option-desc">
                    {option.description}
                  </p>
                </div>
              ))}
            </div>

            <label className="feedback-form__label">Additional Notes:</label>
            <textarea
              value={notes}
              onChange={e => setNotes(e.target.value)}
              placeholder="Provide context for this feedback..."
              className="feedback-form__textarea"
              aria-label="Additional notes for feedback override"
            />

            <div className="feedback-form__actions">
              <button
                className="feedback-form__btn feedback-form__btn--submit"
                onClick={handleSubmitFeedback}
                disabled={isLoading}
              >
                {isLoading ? 'Submitting...' : 'Submit Feedback'}
              </button>
              <button
                className="feedback-form__btn feedback-form__btn--cancel"
                onClick={() => {
                  setShowFeedback(false);
                  setSelectedFeedback(null);
                  setNotes('');
                }}
                disabled={isLoading}
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
