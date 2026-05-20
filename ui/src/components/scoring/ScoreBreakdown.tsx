import React from 'react'
import { AlertCircle, TrendingUp, CheckCircle } from 'lucide-react'
import { Badge, SectionHeader } from '../shared'
import './ScoreBreakdown.css'

interface ScoringFactor {
  name: string
  contribution: number
  signal: string
  evidence: string[]
  status: 'high' | 'medium' | 'low' | 'neutral'
}

interface HorizonScore {
  horizon: 'H1' | 'H2' | 'H3'
  label: string
  score: number
  maxScore: number
  weight: number
  factors: ScoringFactor[]
  summary: string
}

interface ScoreBreakdownProps {
  totalScore: number
  confidence: 'HIGH' | 'MEDIUM' | 'LOW'
  h1: HorizonScore
  h2: HorizonScore
  h3: HorizonScore
  className?: string
}

const getRiskLevel = (score: number): 'high' | 'medium' | 'low' => {
  if (score >= 70) return 'high'
  if (score >= 40) return 'medium'
  return 'low'
}

const getRiskLabel = (level: 'high' | 'medium' | 'low'): string => {
  return { high: 'HIGH RISK', medium: 'MEDIUM RISK', low: 'LOW RISK' }[level]
}

const ScoreBreakdown: React.FC<ScoreBreakdownProps> = ({
  totalScore,
  confidence,
  h1,
  h2,
  h3,
  className = '',
}) => {
  const riskLevel = getRiskLevel(totalScore)
  const activeFactors = {
    h1: h1.factors.filter((f) => f.contribution > 0),
    h2: h2.factors.filter((f) => f.contribution > 0),
    h3: h3.factors.filter((f) => f.contribution > 0),
  }

  return (
    <div className={`score-breakdown ${className}`}>
      {/* Overall Score Summary */}
      <div className={`score-summary score-${riskLevel}`}>
        <div className="score-gauge">
          <div className="score-number">{Math.round(totalScore)}</div>
          <div className="score-label">{getRiskLabel(riskLevel)}</div>
        </div>
        <div className="score-meta">
          <Badge variant={riskLevel} text={`${confidence} Confidence`} />
          <p className="score-interpretation">
            {riskLevel === 'high'
              ? 'This shipment exhibits multiple high-risk indicators requiring immediate investigation and action.'
              : riskLevel === 'medium'
                ? 'This shipment shows potential risk signals that warrant detailed examination before clearance.'
                : 'This shipment appears consistent with legitimate trade patterns. Routine processing acceptable.'}
          </p>
        </div>
      </div>

      {/* Horizon Scores Visualization */}
      <div className="horizons-grid">
        {[h1, h2, h3].map((horizon) => {
          const activeCount = activeFactors[horizon.horizon.toLowerCase() as 'h1' | 'h2' | 'h3'].length
          return (
            <div key={horizon.horizon} className="horizon-card">
              <div className="horizon-header">
                <h4 className="horizon-title">
                  {horizon.horizon} {horizon.label}
                </h4>
                <span className="horizon-weight">{horizon.weight}% weight</span>
              </div>

              <div className="horizon-score-bar">
                <div
                  className="horizon-score-fill"
                  style={{
                    width: `${(horizon.score / horizon.maxScore) * 100}%`,
                    backgroundColor: [
                      'var(--color-risk-high)',
                      'var(--color-risk-medium)',
                      'var(--color-risk-low)',
                    ][
                      horizon.score >= horizon.maxScore * 0.7
                        ? 0
                        : horizon.score >= horizon.maxScore * 0.4
                          ? 1
                          : 2
                    ],
                  }}
                />
              </div>

              <div className="horizon-score-text">
                <span className="score-value">
                  {Math.round(horizon.score)}/{horizon.maxScore}
                </span>
                <span className="factor-count">
                  {activeCount} {activeCount === 1 ? 'signal' : 'signals'}
                </span>
              </div>

              <p className="horizon-summary">{horizon.summary}</p>

              {/* Contributing Factors */}
              {activeCount > 0 && (
                <div className="contributing-factors">
                  <h5>Contributing Factors:</h5>
                  <ul>
                    {activeFactors[horizon.horizon.toLowerCase() as 'h1' | 'h2' | 'h3'].map((factor, idx) => (
                      <li key={idx} className={`factor-${factor.status}`}>
                        <span className="factor-name">{factor.name}</span>
                        <span className="factor-contribution">+{factor.contribution}pts</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* Detailed Factor Analysis */}
      <SectionHeader
        title="Factor Evidence & Analysis"
        subtitle="Detailed breakdown of scoring signals"
        collapsible
        defaultOpen={true}
      >
        <div className="factor-analysis">
          {[h1, h2, h3].map((horizon) => {
            const active = activeFactors[horizon.horizon.toLowerCase() as 'h1' | 'h2' | 'h3']
            if (active.length === 0) return null

            return (
              <div key={horizon.horizon} className="factor-section">
                <h4 className="factor-section-title">
                  {horizon.horizon} - {horizon.label}
                </h4>
                {active.map((factor, idx) => (
                  <div key={idx} className={`factor-detail factor-detail-${factor.status}`}>
                    <div className="factor-header">
                      <span className="factor-icon">
                        {factor.status === 'high' ? (
                          <AlertCircle size={16} />
                        ) : factor.status === 'medium' ? (
                          <TrendingUp size={16} />
                        ) : (
                          <CheckCircle size={16} />
                        )}
                      </span>
                      <span className="factor-name-large">{factor.name}</span>
                      <span className={`factor-badge badge-${factor.status}`}>
                        +{factor.contribution} pts
                      </span>
                    </div>

                    <div className="factor-signal">
                      <strong>Signal:</strong> {factor.signal}
                    </div>

                    {factor.evidence.length > 0 && (
                      <div className="factor-evidence">
                        <strong>Evidence:</strong>
                        <ul>
                          {factor.evidence.map((ev, i) => (
                            <li key={i}>{ev}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )
          })}
        </div>
      </SectionHeader>

      {/* Score Composition */}
      <div className="score-composition">
        <h4>Final Score Composition</h4>
        <div className="composition-formula">
          <div className="composition-item">
            <span className="comp-label">H1 (20%)</span>
            <span className="comp-value">{Math.round((h1.score / h1.maxScore) * h1.weight)}</span>
          </div>
          <span className="comp-operator">+</span>
          <div className="composition-item">
            <span className="comp-label">H2 (35%)</span>
            <span className="comp-value">{Math.round((h2.score / h2.maxScore) * h2.weight)}</span>
          </div>
          <span className="comp-operator">+</span>
          <div className="composition-item">
            <span className="comp-label">H3 (45%)</span>
            <span className="comp-value">{Math.round((h3.score / h3.maxScore) * h3.weight)}</span>
          </div>
          <span className="comp-operator">=</span>
          <div className="composition-total">
            <span className="comp-label">Total</span>
            <span className="comp-value-total">{Math.round(totalScore)}/100</span>
          </div>
        </div>
      </div>
    </div>
  )
}

export default ScoreBreakdown
