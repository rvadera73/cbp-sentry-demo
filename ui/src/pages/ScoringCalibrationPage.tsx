import { useState, useEffect } from 'react';
import { useRole } from '../context/RoleContext';
import USWDSLayout from '../components/layout/USWDSLayout';
import WeightTrendChart from '../components/scoring/WeightTrendChart';
import { API_BASE_URL } from '../services/apiUrl';
import '../styles/ScoringCalibration.css';
import '../components/scoring/WeightTrendChart.css';

interface WeightConfiguration {
  corridor: string | null;
  w_corridor: number;
  w_vessel: number;
  w_manifest: number;
}

interface WeightSuggestion {
  id: string;
  corridor: string | null;
  affected_feature: string;
  suggested_value: number;
  confidence_pct: number;
  corroboration_count: number;
  status: string;
  created_at: string;
  reviewed_at: string | null;
  reviewed_by: string | null;
  rationale: string;
}

interface ScoringOverride {
  id: string;
  shipment_id: string;
  original_score: number;
  override_decision: string;
  feedback_type: string | null;
  analyst_id: string;
  analyst_name: string;
  created_at: string;
  notes: string | null;
}

export default function ScoringCalibrationPage() {
  const { role } = useRole();
  const userEmail = localStorage.getItem('user_email') || 'analyst@cbp.dhs.gov'
  const [weights, setWeights] = useState<WeightConfiguration | null>(null);
  const [suggestions, setSuggestions] = useState<WeightSuggestion[]>([]);
  const [overrideHistory, setOverrideHistory] = useState<ScoringOverride[]>([]);
  const [selectedCorridor, setSelectedCorridor] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'suggestions' | 'configuration' | 'history'>('suggestions');

  // Check authorization
  useEffect(() => {
    if (role !== 'analyst') {
      // Redirect to dashboard if not analyst
      window.location.href = '/';
    }
  }, [role]);

  useEffect(() => {
    loadCalibrationData();
  }, [selectedCorridor]);

  const loadCalibrationData = async () => {
    setLoading(true);
    try {
      // Load weight configuration
      const configResp = await fetch(
        `${API_BASE_URL}/weight-configuration?corridor=${selectedCorridor || 'null'}`
      );
      if (configResp.ok) {
        setWeights(await configResp.json());
      }

      // Load pending suggestions
      const suggestionsResp = await fetch(
        `${API_BASE_URL}/weight-suggestions?status=pending&corridor=${selectedCorridor || 'null'}`
      );
      if (suggestionsResp.ok) {
        const data = await suggestionsResp.json();
        setSuggestions(data.suggestions || []);
      }

      // Load override history
      const historyResp = await fetch(
        `${API_BASE_URL}/feedback/overrides?limit=50`
      );
      if (historyResp.ok) {
        const data = await historyResp.json();
        setOverrideHistory(data.overrides || []);
      }
    } catch (error) {
      console.error('Error loading calibration data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleApproveSuggestion = async (suggestion: WeightSuggestion) => {
    try {
      const response = await fetch(
        `${API_BASE_URL}/weight-suggestions/${suggestion.id}/approve`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            analyst_email: userEmail,
          }),
        }
      );

      if (response.ok) {
        alert(`Approved: ${suggestion.affected_feature} → ${suggestion.suggested_value.toFixed(3)}`);
        loadCalibrationData();
      } else {
        alert('Error approving suggestion');
      }
    } catch (error) {
      console.error('Error approving suggestion:', error);
    }
  };

  const handleRejectSuggestion = async (suggestion: WeightSuggestion) => {
    const reason = prompt('Reason for rejection (optional):');
    try {
      const response = await fetch(
        `${API_BASE_URL}/weight-suggestions/${suggestion.id}/reject`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            analyst_email: userEmail,
            rejection_reason: reason,
          }),
        }
      );

      if (response.ok) {
        alert('Suggestion rejected');
        loadCalibrationData();
      }
    } catch (error) {
      console.error('Error rejecting suggestion:', error);
    }
  };

  return (
    <USWDSLayout
      title="Scoring Calibration Dashboard"
      subtitle="Dynamic Weight Adjustment & AI Feedback System"
    >
      {role !== 'analyst' ? (
        <div style={{ padding: '2rem', textAlign: 'center' }}>
          <p>⚠️ Access Denied: Only analysts can access scoring calibration.</p>
        </div>
      ) : (
        <>
          {/* Corridor Selector */}
          <div className="calibration-controls">
            <label htmlFor="corridor-select">Select Corridor:</label>
            <select
              id="corridor-select"
              className="usa-select"
              value={selectedCorridor || ''}
              onChange={(e) => setSelectedCorridor(e.target.value || null)}
            >
              <option value="">Global (All Corridors)</option>
              <option value="VN-US">VN → US</option>
              <option value="MY-US">MY → US</option>
              <option value="KH-US">KH → US</option>
              <option value="TH-US">TH → US</option>
              <option value="CN-MY">CN → MY</option>
              <option value="CN-VN">CN → VN</option>
            </select>
          </div>

          {/* Tab Navigation */}
          <div className="calibration-tabs">
            <button
              className={`tab-button ${activeTab === 'suggestions' ? 'active' : ''}`}
              onClick={() => setActiveTab('suggestions')}
            >
              📋 Pending Suggestions ({suggestions.length})
            </button>
            <button
              className={`tab-button ${activeTab === 'configuration' ? 'active' : ''}`}
              onClick={() => setActiveTab('configuration')}
            >
              ⚙️ Weight Configuration
            </button>
            <button
              className={`tab-button ${activeTab === 'history' ? 'active' : ''}`}
              onClick={() => setActiveTab('history')}
            >
              📊 Override History
            </button>
          </div>

          {loading ? (
            <div className="loading">Loading calibration data...</div>
          ) : (
            <>
              {/* Tab 1: Pending Suggestions */}
              {activeTab === 'suggestions' && (
                <div className="tab-content">
                  <h3>AI-Suggested Weight Adjustments</h3>
                  <p className="subtitle">
                    Based on analyst override patterns (requires {3} corroborating decisions)
                  </p>

                  {suggestions.length === 0 ? (
                    <div className="empty-state">
                      <p>No pending suggestions at this time.</p>
                      <p>Suggestions appear after analysts override scoring decisions with consistent patterns.</p>
                    </div>
                  ) : (
                    <div className="suggestions-list">
                      {suggestions.map((suggestion) => (
                        <div key={suggestion.id} className="suggestion-card">
                          <div className="suggestion-header">
                            <div className="suggestion-info">
                              <h4>{suggestion.affected_feature.replace('w_', '').toUpperCase()} Weight</h4>
                              <p className="corridor-tag">
                                {suggestion.corridor ? `Corridor: ${suggestion.corridor}` : 'Global'}
                              </p>
                            </div>
                            <div className="confidence-badge">
                              <div className="confidence-value">{suggestion.confidence_pct.toFixed(0)}%</div>
                              <div className="confidence-label">Confidence</div>
                            </div>
                          </div>

                          <div className="suggestion-details">
                            <p><strong>Current → Suggested:</strong> {suggestion.suggested_value > 0 ? '+' : ''}{suggestion.suggested_value.toFixed(3)}</p>
                            <p><strong>Corroborating Overrides:</strong> {suggestion.corroboration_count}</p>
                            <p><strong>Rationale:</strong> {suggestion.rationale}</p>
                          </div>

                          <div className="suggestion-actions">
                            <button
                              className="usa-button usa-button--primary"
                              onClick={() => handleApproveSuggestion(suggestion)}
                            >
                              ✓ Approve
                            </button>
                            <button
                              className="usa-button usa-button--secondary"
                              onClick={() => handleRejectSuggestion(suggestion)}
                            >
                              ✕ Reject
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Tab 2: Weight Configuration */}
              {activeTab === 'configuration' && weights && (
                <div className="tab-content">
                  <h3>Current Weight Configuration</h3>
                  <p className="subtitle">
                    {selectedCorridor ? `Corridor: ${selectedCorridor}` : 'Global defaults (applies to all corridors)'}
                  </p>

                  <div className="weight-grid">
                    <div className="weight-card level-1">
                      <div className="weight-label">Level 1: Corridor Risk</div>
                      <div className="weight-value">{(weights.w_corridor * 100).toFixed(1)}%</div>
                      <p className="weight-description">Macro-level trade route analysis</p>
                      <div className="weight-bar">
                        <div className="weight-fill" style={{ width: `${weights.w_corridor * 100}%` }}></div>
                      </div>
                    </div>

                    <div className="weight-card level-2">
                      <div className="weight-label">Level 2: Vessel Risk</div>
                      <div className="weight-value">{(weights.w_vessel * 100).toFixed(1)}%</div>
                      <p className="weight-description">Pre-manifest anomaly detection</p>
                      <div className="weight-bar">
                        <div className="weight-fill" style={{ width: `${weights.w_vessel * 100}%` }}></div>
                      </div>
                    </div>

                    <div className="weight-card level-3">
                      <div className="weight-label">Level 3: Manifest Risk</div>
                      <div className="weight-value">{(weights.w_manifest * 100).toFixed(1)}%</div>
                      <p className="weight-description">Transaction-level entity validation</p>
                      <div className="weight-bar">
                        <div className="weight-fill" style={{ width: `${weights.w_manifest * 100}%` }}></div>
                      </div>
                    </div>
                  </div>

                  <div className="weight-info">
                    <p>
                      <strong>Total:</strong> {((weights.w_corridor + weights.w_vessel + weights.w_manifest) * 100).toFixed(1)}%
                    </p>
                    <p className="info-text">
                      Weights are adjusted based on analyst feedback patterns. Changes are applied automatically after approval.
                    </p>
                  </div>

                  {/* Weight Trend Chart */}
                  <WeightTrendChart corridor={selectedCorridor || undefined} days={30} />
                </div>
              )}

              {/* Tab 3: Override History */}
              {activeTab === 'history' && (
                <div className="tab-content">
                  <h3>Recent Override History</h3>
                  <p className="subtitle">Analyst feedback decisions that drive weight suggestions</p>

                  {overrideHistory.length === 0 ? (
                    <div className="empty-state">
                      <p>No override history yet.</p>
                    </div>
                  ) : (
                    <div className="override-table">
                      <table>
                        <thead>
                          <tr>
                            <th>Date</th>
                            <th>Analyst</th>
                            <th>Shipment</th>
                            <th>Original Score</th>
                            <th>Decision</th>
                            <th>Feedback Type</th>
                            <th>Notes</th>
                          </tr>
                        </thead>
                        <tbody>
                          {overrideHistory.map((override) => (
                            <tr key={override.id}>
                              <td>{new Date(override.created_at).toLocaleDateString()}</td>
                              <td>{override.analyst_name}</td>
                              <td className="code">{override.shipment_id.substring(0, 12)}...</td>
                              <td>{override.original_score.toFixed(0)}/100</td>
                              <td>
                                <span className={`decision-badge ${override.override_decision.toLowerCase()}`}>
                                  {override.override_decision}
                                </span>
                              </td>
                              <td>{override.feedback_type || '—'}</td>
                              <td>{override.notes || '—'}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              )}
            </>
          )}
        </>
      )}
    </USWDSLayout>
  );
}
