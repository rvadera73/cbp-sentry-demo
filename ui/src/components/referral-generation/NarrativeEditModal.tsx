/**
 * Narrative Edit Modal
 * Allows officers to edit AI-generated narratives (sections 3-6, 3-7, 3-11, 3-14)
 * with option to regenerate via Gemini
 */

import React, { useState } from 'react';
import { X, Zap, Save } from 'lucide-react';
import { NarrativeEditModalProps } from './types/ReferralGeneration.types';
import './NarrativeEditModal.css';

export default function NarrativeEditModal({
  section,
  referralId,
  onSave,
  onRegenerate,
  onClose,
  isRegenerating = false
}: NarrativeEditModalProps) {
  const [editedContent, setEditedContent] = useState(section.current_narrative);
  const [localIsRegenerating, setLocalIsRegenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleRegenerate = async () => {
    try {
      setLocalIsRegenerating(true);
      setError(null);
      const newContent = await onRegenerate();
      if (newContent) {
        setEditedContent(newContent);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to regenerate narrative');
    } finally {
      setLocalIsRegenerating(false);
    }
  };

  const handleSave = () => {
    if (!editedContent.trim()) {
      setError('Narrative cannot be empty');
      return;
    }
    onSave(editedContent);
  };

  return (
    <div className="narrative-edit-modal-overlay">
      <div className="narrative-edit-modal">
        <div className="modal-header">
          <h3>{section.title}</h3>
          <button
            className="modal-close"
            onClick={onClose}
            aria-label="Close modal"
          >
            <X size={24} />
          </button>
        </div>

        <div className="modal-content">
          {error && (
            <div className="error-banner">
              <p>{error}</p>
            </div>
          )}

          <div className="form-group">
            <label htmlFor="narrative-textarea" className="form-label">
              Edit Narrative
              {section.is_edited && <span className="edited-indicator">(Modified)</span>}
            </label>
            <textarea
              id="narrative-textarea"
              className="narrative-textarea"
              value={editedContent}
              onChange={(e) => setEditedContent(e.target.value)}
              disabled={localIsRegenerating}
              placeholder="Enter narrative text here..."
            />
            <div className="textarea-info">
              <span className="char-count">
                {editedContent.length} characters
              </span>
            </div>
          </div>

          {section.can_regenerate && (
            <div className="regenerate-section">
              <p className="regenerate-label">
                Not satisfied? Let the AI regenerate this section:
              </p>
              <button
                className="btn btn-regenerate"
                onClick={handleRegenerate}
                disabled={localIsRegenerating}
              >
                <Zap size={18} />
                {localIsRegenerating ? 'Regenerating...' : 'Regenerate via Gemini'}
              </button>
            </div>
          )}
        </div>

        <div className="modal-footer">
          <button
            className="btn btn-secondary"
            onClick={onClose}
            disabled={localIsRegenerating}
          >
            Cancel
          </button>
          <button
            className="btn btn-primary"
            onClick={handleSave}
            disabled={localIsRegenerating || !editedContent.trim()}
          >
            <Save size={18} />
            Save Changes
          </button>
        </div>
      </div>
    </div>
  );
}
