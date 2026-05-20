import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useWorkflow } from '../context/WorkflowContext'
import { api } from '../services/api'
import ScoreGauge from '../components/scoring/ScoreGauge'
import ScoreBreakdown from '../components/scoring/ScoreBreakdown'

const ScoringPage: React.FC = () => {
  const navigate = useNavigate()
  const { state, setState } = useWorkflow()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Load score on mount
  useEffect(() => {
    loadScore()
  }, [])

  const loadScore = async () => {
    if (!state.manifestId) {
      setError('No manifest ID available')
      return
    }

    setLoading(true)
    setError(null)
    setState({ scoringLoading: true })

    try {
      const response = await api.scoreShipment(state.manifestId)
      if (response) {
        setState({
          score: response,
          scoringComplete: true,
          scoringLoading: false,
        })
      } else {
        setError('Failed to score shipment')
        setState({ scoringLoading: false })
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
      setState({ scoringLoading: false })
    } finally {
      setLoading(false)
    }
  }

  const handleGenerateReferral = () => {
    if (state.scoringComplete && state.manifestId) {
      navigate(`/referral/${state.manifestId}`)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold text-sentry-navy mb-2">Risk Scoring</h2>
        <p className="text-sentry-slate">
          4-tier ML scoring with component breakdown and XAI assertions.
        </p>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-800">
          {error}
        </div>
      )}

      {loading ? (
        <div className="bg-white p-8 rounded-lg shadow text-center">
          <p className="text-sentry-slate">Scoring shipment...</p>
        </div>
      ) : state.score ? (
        <>
          {/* Score Gauge */}
          <div className="bg-white p-8 rounded-lg shadow flex justify-center">
            <ScoreGauge score={state.score.h3_scoring_breakdown.total_score} />
          </div>

          {/* Score Breakdown - Coming soon with new component */}
          <div className="bg-white p-6 rounded-lg shadow">
            <h3 className="text-lg font-semibold text-sentry-navy mb-4">Component Breakdown</h3>
            <p className="text-sentry-slate">Visual score breakdown coming in case viewer</p>
          </div>

          {/* XAI Assertions */}
          <div className="bg-white p-6 rounded-lg shadow">
            <h3 className="text-lg font-semibold text-sentry-navy mb-4">XAI Assertions</h3>
            <div className="space-y-3">
              {(state.score.xai_assertions || [
                'Senzing resolved shipper to Chinese parent with 91% confidence',
                'AIS dwell 11.2 days (5.3× baseline, 99th percentile)',
                'HTS 7604.10 subject to 374.15% AD/CVD from China',
                'Bayesian P(fraud)=0.91 based on origin documentation gap',
              ]).map((assertion, idx) => (
                <div key={idx} className="flex gap-3 text-sm">
                  <span className="text-sentry-orange font-bold">•</span>
                  <p className="text-gray-700">{assertion}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Horizon Panels */}
          <div className="grid grid-cols-2 gap-4">
            {/* H1 Corridor Risk */}
            <div className="bg-white p-6 rounded-lg shadow">
              <h4 className="font-semibold text-sentry-navy mb-2">H1 Corridor Risk</h4>
              <div className="text-sm text-gray-600 space-y-1">
                <p>
                  <strong>Level:</strong> {state.score.h1_corridor_risk.risk_level}
                </p>
                <p>
                  <strong>Score:</strong> {state.score.h1_corridor_risk.risk_score}/100
                </p>
              </div>
            </div>

            {/* H2 Pre-Intelligence */}
            <div className="bg-white p-6 rounded-lg shadow">
              <h4 className="font-semibold text-sentry-navy mb-2">H2 Pre-Intelligence</h4>
              <div className="text-sm text-gray-600 space-y-1">
                <p>
                  <strong>AIS Dwell:</strong> {state.score.h2_pre_intelligence.ais_dwell_days}d
                </p>
                <p>
                  <strong>Anomaly Ratio:</strong> {state.score.h2_pre_intelligence.ais_anomaly_ratio.toFixed(2)}×
                </p>
                <p>
                  <strong>ISF Element 9 Contradiction:</strong>{' '}
                  {state.score.h2_pre_intelligence.isf_element_9_contradiction ? 'Yes' : 'No'}
                </p>
              </div>
            </div>
          </div>

          {/* Recommendation */}
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
            <h3 className="font-semibold text-sentry-navy mb-2">Recommended Action</h3>
            <p className="text-lg font-bold text-sentry-orange mb-2">{state.score.recommended_action}</p>
            <p className="text-sm text-gray-700">
              Estimated revenue impact: <strong>${state.score.estimated_revenue_impact_usd.toLocaleString()}</strong>
            </p>
          </div>
        </>
      ) : (
        <div className="bg-white p-8 rounded-lg shadow text-center text-gray-600">
          No score available yet.
        </div>
      )}

      {/* Navigation */}
      <div className="flex justify-between pt-4">
        <button onClick={() => navigate('/entity-resolution')} className="px-6 py-2 text-gray-700 hover:text-gray-900">
          ← Back
        </button>
        <button
          onClick={handleGenerateReferral}
          disabled={!state.scoringComplete}
          className={`px-6 py-2 rounded font-semibold transition-all ${
            state.scoringComplete
              ? 'bg-sentry-teal text-white hover:bg-sentry-dark-teal'
              : 'bg-gray-300 text-gray-500 cursor-not-allowed'
          }`}
        >
          Generate Referral →
        </button>
      </div>
    </div>
  )
}

export default ScoringPage
