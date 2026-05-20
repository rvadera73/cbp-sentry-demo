import { useState } from 'react';
import './ThreeLevelScoreBreakdown.css';

interface ThreeLevelScoreData {
  corridor_score: number;
  vessel_score: number;
  manifest_score: number;
  total_score: number;
  risk_level: string;
  requires_altana: boolean;
  weights: {
    w_corridor: number;
    w_vessel: number;
    w_manifest: number;
  };
  components: {
    corridor: {
      macro_volume_spike: number;
      regulatory_delta: number;
      confidence: number;
    };
    vessel: {
      ftz_loitering: number;
      ais_dark_activity: number;
      confidence: number;
    };
    manifest: {
      entity_resolution_match: number;
      hs_code_weight_delta: number;
      network_anomaly: number;
      confidence: number;
    };
  };
  xai_factors: string[];
}

interface Props {
  score: ThreeLevelScoreData | null;
  loading?: boolean;
}

export default function ThreeLevelScoreBreakdown({ score, loading }: Props) {
  const [expandedLevel, setExpandedLevel] = useState<string | null>(null);

  if (loading) {
    return <div className="three-level-loading">Calculating three-level risk score...</div>;
  }

  if (!score) {
    return <div className="three-level-empty">No score available</div>;
  }

  const getRiskColor = (riskLevel: string) => {
    switch (riskLevel) {
      case 'CRITICAL':
        return '#d62828';
      case 'HIGH':
        return '#f5a623';
      case 'MEDIUM':
        return '#fdb913';
      case 'LOW':
        return '#00a91c';
      default:
        return '#0066cc';
    }
  };

  return (
    <div className="three-level-breakdown">
      {/* Overall Score Card */}
      <div className="overall-score">
        <div className="score-circle" style={{ borderColor: getRiskColor(score.risk_level) }}>
          <div className="score-value">{Math.round(score.total_score)}</div>
          <div className="score-unit">/100</div>
        </div>
        <div className="score-info">
          <div
            className="risk-badge"
            style={{ backgroundColor: getRiskColor(score.risk_level) }}
          >
            {score.risk_level} RISK
          </div>
          {score.requires_altana && (
            <div className="altana-flag">🔍 Requires Altana Verification</div>
          )}
        </div>
      </div>

      {/* Three-Level Scores */}
      <div className="levels-container">
        {/* Level 1: Corridor Risk */}
        <div className="level-card level-1">
          <div
            className="level-header"
            onClick={() =>
              setExpandedLevel(
                expandedLevel === 'corridor' ? null : 'corridor'
              )
            }
          >
            <div className="level-title">
              <span className="level-icon">🌍</span>
              <span>Level 1: Corridor Risk (Macro)</span>
            </div>
            <div className="level-score">
              {(score.corridor_score * 100).toFixed(0)}/100
            </div>
            <div className="level-weight">
              {(score.weights.w_corridor * 100).toFixed(0)}% weight
            </div>
          </div>

          {expandedLevel === 'corridor' && (
            <div className="level-details">
              <div className="detail-row">
                <span>Macro Volume Spike:</span>
                <span>
                  {score.components.corridor.macro_volume_spike.toFixed(0)}%
                </span>
              </div>
              <div className="detail-row">
                <span>Regulatory Delta:</span>
                <span>
                  {score.components.corridor.regulatory_delta.toFixed(0)}%
                </span>
              </div>
              <div className="detail-row">
                <span>Confidence:</span>
                <span>
                  {score.components.corridor.confidence.toFixed(0)}%
                </span>
              </div>
              <div className="detail-bar">
                <div
                  className="detail-fill"
                  style={{
                    width: `${score.corridor_score * 100}%`,
                    backgroundColor: '#003366',
                  }}
                ></div>
              </div>
            </div>
          )}
        </div>

        {/* Level 2: Vessel Risk */}
        <div className="level-card level-2">
          <div
            className="level-header"
            onClick={() =>
              setExpandedLevel(expandedLevel === 'vessel' ? null : 'vessel')
            }
          >
            <div className="level-title">
              <span className="level-icon">⚓</span>
              <span>Level 2: Vessel Risk (Pre-Manifest)</span>
            </div>
            <div className="level-score">
              {(score.vessel_score * 100).toFixed(0)}/100
            </div>
            <div className="level-weight">
              {(score.weights.w_vessel * 100).toFixed(0)}% weight
            </div>
          </div>

          {expandedLevel === 'vessel' && (
            <div className="level-details">
              <div className="detail-row">
                <span>FTZ Loitering:</span>
                <span>
                  {score.components.vessel.ftz_loitering.toFixed(0)}%
                </span>
              </div>
              <div className="detail-row">
                <span>AIS Dark Activity:</span>
                <span>
                  {score.components.vessel.ais_dark_activity.toFixed(0)}%
                </span>
              </div>
              <div className="detail-row">
                <span>Confidence:</span>
                <span>
                  {score.components.vessel.confidence.toFixed(0)}%
                </span>
              </div>
              <div className="detail-bar">
                <div
                  className="detail-fill"
                  style={{
                    width: `${score.vessel_score * 100}%`,
                    backgroundColor: '#0066cc',
                  }}
                ></div>
              </div>
            </div>
          )}
        </div>

        {/* Level 3: Manifest Risk */}
        <div className="level-card level-3">
          <div
            className="level-header"
            onClick={() =>
              setExpandedLevel(
                expandedLevel === 'manifest' ? null : 'manifest'
              )
            }
          >
            <div className="level-title">
              <span className="level-icon">📋</span>
              <span>Level 3: Manifest Risk (Transaction)</span>
            </div>
            <div className="level-score">
              {(score.manifest_score * 100).toFixed(0)}/100
            </div>
            <div className="level-weight">
              {(score.weights.w_manifest * 100).toFixed(0)}% weight
            </div>
          </div>

          {expandedLevel === 'manifest' && (
            <div className="level-details">
              <div className="detail-row">
                <span>Entity Resolution Match:</span>
                <span>
                  {score.components.manifest.entity_resolution_match.toFixed(
                    0
                  )}%
                </span>
              </div>
              <div className="detail-row">
                <span>HS Code/Weight Delta:</span>
                <span>
                  {score.components.manifest.hs_code_weight_delta.toFixed(0)}%
                </span>
              </div>
              <div className="detail-row">
                <span>Network Anomaly:</span>
                <span>
                  {score.components.manifest.network_anomaly.toFixed(0)}%
                </span>
              </div>
              <div className="detail-row">
                <span>Confidence:</span>
                <span>
                  {score.components.manifest.confidence.toFixed(0)}%
                </span>
              </div>
              <div className="detail-bar">
                <div
                  className="detail-fill"
                  style={{
                    width: `${score.manifest_score * 100}%`,
                    backgroundColor: '#00a4ef',
                  }}
                ></div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* XAI Factors */}
      {score.xai_factors && score.xai_factors.length > 0 && (
        <div className="xai-factors">
          <h4>Key Risk Factors (Explainable AI)</h4>
          <ul>
            {score.xai_factors.map((factor, idx) => (
              <li key={idx}>{factor}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Weight Configuration Info */}
      <div className="weight-info">
        <p className="info-text">
          Current weights: Corridor {(score.weights.w_corridor * 100).toFixed(0)}% | Vessel{' '}
          {(score.weights.w_vessel * 100).toFixed(0)}% | Manifest{' '}
          {(score.weights.w_manifest * 100).toFixed(0)}%
        </p>
      </div>
    </div>
  );
}
