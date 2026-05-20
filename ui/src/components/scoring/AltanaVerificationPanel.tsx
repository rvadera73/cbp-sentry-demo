import { useState, useEffect } from 'react';
import './AltanaVerificationPanel.css';

interface Finding {
  type: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  title: string;
  description: string;
  evidence: string[];
  confidence_pct: number;
}

interface AltanaResult {
  shipment_id: string;
  verification_status: string;
  confidence_pct: number;
  findings: Finding[];
  recommendation: string;
  overall_assessment: string;
  timestamp: string;
  data_sources: string[];
  error?: string;
}

interface Props {
  shipmentId: string;
  riskScore: number;
  onClose: () => void;
}

export default function AltanaVerificationPanel({
  shipmentId,
  riskScore,
  onClose,
}: Props) {
  const [result, setResult] = useState<AltanaResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [expandedFinding, setExpandedFinding] = useState<number | null>(0);

  useEffect(() => {
    if (riskScore < 90) {
      setLoading(false);
      return;
    }

    // Trigger Altana verification
    triggerVerification();
  }, [shipmentId, riskScore]);

  const triggerVerification = async () => {
    try {
      // Detect API URL
      const hostname = window.location.hostname;
      let apiUrl = '/api';
      const cloudRunMatch = hostname.match(/^sentry-ui-(\d+)\.(.+?)\.run\.app$/);
      if (cloudRunMatch) {
        const [, hash, region] = cloudRunMatch;
        apiUrl = `https://sentry-api-${hash}.${region}.run.app/api`;
      } else if (hostname !== 'localhost' && !hostname.startsWith('localhost:')) {
        apiUrl = `https://sentry-api-${hostname.split('-').slice(1).join('-')}`;
      }

      const response = await fetch(
        `${apiUrl}/altana/verify/${shipmentId}`,
        { method: 'POST' }
      );

      if (response.ok) {
        const data = await response.json();
        setResult(data);
      } else {
        setResult({
          shipment_id: shipmentId,
          verification_status: 'error',
          confidence_pct: 0,
          findings: [],
          recommendation: 'MANUAL_REVIEW',
          overall_assessment: 'Verification failed',
          timestamp: new Date().toISOString(),
          data_sources: [],
          error: 'Failed to retrieve verification results',
        });
      }
    } catch (error) {
      console.error('Error triggering Altana verification:', error);
      setResult({
        shipment_id: shipmentId,
        verification_status: 'error',
        confidence_pct: 0,
        findings: [],
        recommendation: 'MANUAL_REVIEW',
        overall_assessment: 'Verification error',
        timestamp: new Date().toISOString(),
        data_sources: [],
        error: 'Network error during verification',
      });
    } finally {
      setLoading(false);
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical':
        return '#d62828';
      case 'high':
        return '#f5a623';
      case 'medium':
        return '#fdb913';
      case 'low':
        return '#00a91c';
      default:
        return '#0066cc';
    }
  };

  const getRecommendationBadge = (rec: string) => {
    switch (rec) {
      case 'EXAMINE':
        return { bg: '#ffcccc', color: '#9b2c2c', text: '🔍 EXAMINE' };
      case 'MANUAL_REVIEW':
        return { bg: '#fff4cc', color: '#8b5a00', text: '⚠️ MANUAL REVIEW' };
      case 'CLEAR':
        return { bg: '#d4f4dd', color: '#004d00', text: '✓ CLEAR' };
      default:
        return { bg: '#f0f7ff', color: '#003366', text: '❓ PENDING' };
    }
  };

  if (riskScore < 90) {
    return (
      <div className="altana-panel altana-not-triggered">
        <div className="altana-message">
          <p>Altana Atlas verification is only triggered for shipments scoring ≥ 90% risk.</p>
          <p>Current score: {riskScore.toFixed(0)}/100 - Below threshold</p>
        </div>
        <button className="usa-button usa-button--secondary" onClick={onClose}>
          Close
        </button>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="altana-panel altana-loading">
        <div className="loading-spinner"></div>
        <p>🌐 Querying Altana Global Knowledge Graph...</p>
        <p className="loading-detail">Tracing upstream suppliers and verifying manufacturing origin</p>
      </div>
    );
  }

  if (!result) {
    return (
      <div className="altana-panel altana-error">
        <p>⚠️ Could not retrieve verification results</p>
        <button className="usa-button usa-button--secondary" onClick={onClose}>
          Close
        </button>
      </div>
    );
  }

  const recommendation = getRecommendationBadge(result.recommendation);

  return (
    <div className="altana-panel">
      <div className="altana-header">
        <h3>🌐 Altana Atlas Supply Chain Verification</h3>
        <button className="altana-close" onClick={onClose}>
          ×
        </button>
      </div>

      {result.error ? (
        <div className="altana-error-message">{result.error}</div>
      ) : (
        <>
          {/* Overall Assessment */}
          <div className="altana-assessment">
            <div className="assessment-header">
              <div>
                <h4>Overall Assessment</h4>
                <p className="assessment-text">{result.overall_assessment}</p>
              </div>
              <div
                className="recommendation-badge"
                style={{
                  backgroundColor: recommendation.bg,
                  color: recommendation.color,
                }}
              >
                {recommendation.text}
              </div>
            </div>
            <div className="confidence-meter">
              <div className="confidence-label">Verification Confidence:</div>
              <div className="confidence-bar-container">
                <div
                  className="confidence-bar"
                  style={{ width: `${result.confidence_pct}%` }}
                ></div>
              </div>
              <div className="confidence-value">{result.confidence_pct.toFixed(0)}%</div>
            </div>
          </div>

          {/* Findings */}
          {result.findings.length > 0 && (
            <div className="altana-findings">
              <h4>Key Findings ({result.findings.length})</h4>
              <div className="findings-list">
                {result.findings.map((finding, idx) => (
                  <div
                    key={idx}
                    className="finding-card"
                    style={{ borderLeftColor: getSeverityColor(finding.severity) }}
                    onClick={() => setExpandedFinding(expandedFinding === idx ? null : idx)}
                  >
                    <div className="finding-header">
                      <div className="finding-title">
                        <span
                          className="severity-badge"
                          style={{
                            backgroundColor: getSeverityColor(finding.severity),
                            color: 'white',
                          }}
                        >
                          {finding.severity.toUpperCase()}
                        </span>
                        <h5>{finding.title}</h5>
                      </div>
                      <div className="finding-confidence">{finding.confidence_pct.toFixed(0)}%</div>
                    </div>

                    <p className="finding-description">{finding.description}</p>

                    {expandedFinding === idx && (
                      <div className="finding-evidence">
                        <strong>Supporting Evidence:</strong>
                        <ul>
                          {finding.evidence.map((item, i) => (
                            <li key={i}>{item}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                    <div className="finding-expand-hint">
                      {expandedFinding === idx ? '▼ Hide Details' : '▶ Show Details'}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Data Sources */}
          <div className="altana-sources">
            <strong>Data Sources Used:</strong>
            <ul>
              {result.data_sources.map((source, idx) => (
                <li key={idx}>{source}</li>
              ))}
            </ul>
          </div>

          {/* Next Steps */}
          <div className="altana-next-steps">
            <strong>Recommended Action:</strong>
            {result.recommendation === 'EXAMINE' && (
              <p>
                ✓ Generate CF-28 examination notice and escalate to TRLED (Targeting and
                Enforcement Division) for formal transshipment investigation.
              </p>
            )}
            {result.recommendation === 'MANUAL_REVIEW' && (
              <p>
                ⚠️ Manual review required. Escalate to supervisor for case-by-case assessment and
                decision on examination authority.
              </p>
            )}
            {result.recommendation === 'CLEAR' && (
              <p>✓ No additional verification required. Proceed with standard processing and clearance.</p>
            )}
          </div>
        </>
      )}

      <div className="altana-footer">
        <small>
          Verification timestamp: {new Date(result.timestamp).toLocaleString()} |
          Status: {result.verification_status}
        </small>
        <button className="usa-button usa-button--secondary" onClick={onClose}>
          Close Verification Panel
        </button>
      </div>
    </div>
  );
}
