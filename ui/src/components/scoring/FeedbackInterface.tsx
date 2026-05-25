import { useState } from 'react';
import { API_BASE_URL } from '../../services/apiUrl';
import './FeedbackInterface.css';

interface Props {
  shipmentId: string;
  originalScore: number;
  onSubmit: () => void;
  onCancel: () => void;
}

type DecisionType = 'ACCEPT' | 'REJECT';
type FeedbackType = 'factory_expansion' | 'dual_origin' | 'misclassified_vessel' | '';

export default function FeedbackInterface({
  shipmentId,
  originalScore,
  onSubmit,
  onCancel,
}: Props) {
  const userEmail = localStorage.getItem('user_email') || 'analyst@cbp.dhs.gov'
  const [decision, setDecision] = useState<DecisionType>('ACCEPT');
  const [feedbackType, setFeedbackType] = useState<FeedbackType>('');
  const [notes, setNotes] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const feedbackOptions = [
    { value: '', label: '(None - standard acceptance)' },
    { value: 'factory_expansion', label: 'Legitimate Factory Expansion' },
    { value: 'dual_origin', label: 'Valid Dual-Origin Raw Materials' },
    { value: 'misclassified_vessel', label: 'Misclassified Vessel Track' },
  ];

  const handleSubmit = async () => {
    if (!decision) {
      alert('Please select Accept or Reject');
      return;
    }

    if (decision === 'REJECT' && !feedbackType) {
      alert('Please select a reason for rejecting this score');
      return;
    }

    setSubmitting(true);

    try {
      const params = new URLSearchParams();
      params.append('shipment_id', shipmentId);
      params.append('original_score', originalScore.toString());
      params.append('override_decision', decision);
      if (feedbackType) {
        params.append('feedback_type', feedbackType);
      }
      params.append('analyst_email', userEmail);
      if (notes) {
        params.append('notes', notes);
      }

      const response = await fetch(
        `${API_BASE_URL}/feedback/override?${params.toString()}`,
        { method: 'POST' }
      );

      if (response.ok) {
        setSubmitted(true);
        setTimeout(() => {
          onSubmit();
        }, 1500);
      } else {
        alert('Error submitting feedback');
      }
    } catch (error) {
      console.error('Error submitting feedback:', error);
      alert('Error submitting feedback');
    } finally {
      setSubmitting(false);
    }
  };

  if (submitted) {
    return (
      <div className="feedback-interface feedback-success">
        <div className="success-message">
          <div className="success-icon">✓</div>
          <h4>Feedback Recorded</h4>
          <p>
            Your {decision.toLowerCase()} decision has been recorded.
            {feedbackType && ` Reason: ${feedbackOptions.find((opt) => opt.value === feedbackType)?.label}`}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="feedback-interface">
      <div className="feedback-header">
        <h4>📋 Analyst Feedback on Risk Score</h4>
        <p className="feedback-score">
          Original Score: <strong>{originalScore.toFixed(0)}/100</strong>
        </p>
      </div>

      <div className="feedback-section">
        <label className="feedback-label">Do you agree with this risk score?</label>
        <div className="decision-buttons">
          <button
            className={`decision-button accept ${decision === 'ACCEPT' ? 'active' : ''}`}
            onClick={() => {
              setDecision('ACCEPT');
              setFeedbackType('');
            }}
          >
            ✓ Accept - Score is Accurate
          </button>
          <button
            className={`decision-button reject ${decision === 'REJECT' ? 'active' : ''}`}
            onClick={() => setDecision('REJECT')}
          >
            ✕ Reject - Score is Inaccurate
          </button>
        </div>
      </div>

      {decision === 'REJECT' && (
        <div className="feedback-section">
          <label className="feedback-label">
            Why is the score inaccurate? (This helps AI learning)
          </label>
          <select
            className="usa-select feedback-select"
            value={feedbackType}
            onChange={(e) => setFeedbackType(e.target.value as FeedbackType)}
          >
            {feedbackOptions.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
          {feedbackType && (
            <div className="feedback-explanation">
              {feedbackType === 'factory_expansion' && (
                <p>
                  💡 This helps the system reduce false positives from legitimate business expansion in
                  high-risk corridors.
                </p>
              )}
              {feedbackType === 'dual_origin' && (
                <p>
                  💡 This helps the system recognize valid supply chains with dual sourcing from multiple
                  origins.
                </p>
              )}
              {feedbackType === 'misclassified_vessel' && (
                <p>
                  💡 This helps the system improve vessel routing pattern recognition and reduce AIS anomaly
                  false flags.
                </p>
              )}
            </div>
          )}
        </div>
      )}

      <div className="feedback-section">
        <label className="feedback-label">Additional Notes (Optional)</label>
        <textarea
          className="feedback-textarea"
          placeholder="Add any additional context, observations, or evidence that influenced your decision..."
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          rows={3}
        />
      </div>

      <div className="feedback-info">
        <strong>How This Works:</strong>
        <ul>
          <li>Your feedback is recorded and analyzed for patterns</li>
          <li>After 3+ similar overrides, the system suggests weight adjustments</li>
          <li>All changes require analyst approval via the Scoring Calibration Dashboard</li>
          <li>Complete audit trail maintained for compliance</li>
        </ul>
      </div>

      <div className="feedback-actions">
        <button
          className="usa-button usa-button--primary"
          onClick={handleSubmit}
          disabled={submitting || !decision}
        >
          {submitting ? '⟳ Submitting...' : '✓ Submit Feedback'}
        </button>
        <button className="usa-button usa-button--secondary" onClick={onCancel} disabled={submitting}>
          Cancel
        </button>
      </div>
    </div>
  );
}
