/**
 * Step 2: Evidence Review Checklist
 * Officer reviews critical and supporting evidence items
 */

import React from 'react';
import { CheckCircle, Circle } from 'lucide-react';
import { Step2Props, EVIDENCE_ITEMS } from '../types/ReferralGeneration.types';

export default function Step2EvidenceReview({
  data,
  onChange
}: Step2Props) {
  const handleItemReviewed = (itemId: string, reviewed: boolean) => {
    const newItems = {
      ...data.reviewedItems,
      [itemId]: {
        ...data.reviewedItems[itemId],
        reviewed
      }
    };
    onChange({
      ...data,
      reviewedItems: newItems,
      allCriticalReviewed: EVIDENCE_ITEMS
        .filter(i => i.isCritical)
        .every(i => newItems[i.id]?.reviewed)
    });
  };

  const handleNoteChange = (itemId: string, notes: string) => {
    onChange({
      ...data,
      reviewedItems: {
        ...data.reviewedItems,
        [itemId]: {
          ...data.reviewedItems[itemId],
          notes
        }
      }
    });
  };

  const criticalItems = EVIDENCE_ITEMS.filter(i => i.isCritical);
  const supportingItems = EVIDENCE_ITEMS.filter(i => !i.isCritical);

  const criticalReviewed = criticalItems.filter(i => data.reviewedItems[i.id]?.reviewed).length;

  return (
    <div className="step-form">
      <div className="step-header">
        <h2 className="step-title">Evidence Review Checklist</h2>
        <p className="step-description">
          Verify you've reviewed all critical evidence items. Supporting items are optional.
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

      <div className="evidence-progress">
        <span>Critical items reviewed: {criticalReviewed}/{criticalItems.length}</span>
        {data.allCriticalReviewed && (
          <span className="progress-complete">✓ All critical items reviewed</span>
        )}
      </div>

      {/* Critical Evidence */}
      <div className="evidence-section">
        <h3 className="section-title critical">Critical Evidence (Required)</h3>
        <div className="evidence-list">
          {criticalItems.map(item => (
            <div key={item.id} className="evidence-item critical">
              <div className="item-checkbox">
                <input
                  type="checkbox"
                  id={item.id}
                  checked={data.reviewedItems[item.id]?.reviewed || false}
                  onChange={(e) => handleItemReviewed(item.id, e.target.checked)}
                />
                <label htmlFor={item.id}>
                  <span className="item-label">{item.label}</span>
                  <span className="item-description">{item.description}</span>
                </label>
              </div>

              {data.reviewedItems[item.id]?.reviewed && (
                <div className="item-notes">
                  <textarea
                    value={data.reviewedItems[item.id]?.notes || ''}
                    onChange={(e) => handleNoteChange(item.id, e.target.value)}
                    placeholder="Optional: Add notes about this evidence..."
                    className="notes-textarea"
                    rows={2}
                  />
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Supporting Evidence */}
      <div className="evidence-section">
        <h3 className="section-title supporting">Supporting Evidence (Optional)</h3>
        <div className="evidence-list">
          {supportingItems.map(item => (
            <div key={item.id} className="evidence-item">
              <div className="item-checkbox">
                <input
                  type="checkbox"
                  id={item.id}
                  checked={data.reviewedItems[item.id]?.reviewed || false}
                  onChange={(e) => handleItemReviewed(item.id, e.target.checked)}
                />
                <label htmlFor={item.id}>
                  <span className="item-label">{item.label}</span>
                  <span className="item-description">{item.description}</span>
                </label>
              </div>

              {data.reviewedItems[item.id]?.reviewed && (
                <div className="item-notes">
                  <textarea
                    value={data.reviewedItems[item.id]?.notes || ''}
                    onChange={(e) => handleNoteChange(item.id, e.target.value)}
                    placeholder="Optional: Add notes about this evidence..."
                    className="notes-textarea"
                    rows={2}
                  />
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      <div className="evidence-summary">
        <p>
          Total reviewed: <strong>{Object.values(data.reviewedItems).filter(r => r.reviewed).length}/{EVIDENCE_ITEMS.length}</strong>
        </p>
      </div>
    </div>
  );
}
