import React, { useState } from 'react'
import { Search, ArrowRight, Check, X } from 'lucide-react'

interface PredictionExplanationsProps {
  onCompare?: (shipmentId: string, model: string) => void
}

interface ShapFeature {
  name: string
  value: string
  contribution: number
  direction: 'up' | 'down'
}

interface ModelComparison {
  v2_1?: {
    score: number
    factors: Array<{
      name: string
      raw_score: number
      weight: number
      contribution: number
      evidence: string[]
    }>
    confidence: number | null
  }
  v3_0?: {
    score: number
    factors: Array<{
      name: string
      contribution: number
    }>
    confidence: number | null
  }
  difference?: {
    score_delta: number
    score_delta_percent: number
    better_model: string
    reason: string
  }
}

interface PredictionExplanation {
  shipmentId: string
  origin: string
  destination: string
  commodity: string
  declaredValue: number
  containerType: string
  modelVersion: string
  score: number
  classification: string
  confidence: number
  processingTime: number
  baseScore: number
  positiveFactors: ShapFeature[]
  negativeFactors: ShapFeature[]
  interpretation: string[]
  comparison?: ModelComparison
}

const PredictionExplanations: React.FC<PredictionExplanationsProps> = ({ onCompare }) => {
  const [searchTerm, setSearchTerm] = useState('SHP-00142857')
  const [explanation, setExplanation] = useState<PredictionExplanation | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [showComparison, setShowComparison] = useState(false)
  const [comparisonLoading, setComparisonLoading] = useState(false)

  const handleSearch = async () => {
    if (!searchTerm.trim()) {
      setError('Please enter a shipment ID')
      return
    }

    setLoading(true)
    setError(null)
    setShowComparison(false)
    try {
      // Fetch SHAP explanation from API
      const explainResponse = await fetch(`/api/risk-models/predictions/${searchTerm}/explain?model_version=v3.0`)
      if (!explainResponse.ok) {
        if (explainResponse.status === 404) {
          throw new Error(`Shipment ${searchTerm} not found`)
        }
        throw new Error('Failed to load explanation')
      }
      const explainData = await explainResponse.json()

      // Convert to component format
      setExplanation({
        shipmentId: searchTerm,
        origin: explainData.shipment?.origin_country || 'Unknown',
        destination: explainData.shipment?.destination_country || 'US',
        commodity: explainData.shipment?.commodity_description || 'Unknown',
        declaredValue: explainData.shipment?.declared_value || 0,
        containerType: explainData.shipment?.container_type || 'Unknown',
        modelVersion: 'v3.0',
        score: explainData.prediction?.score || 0,
        classification: explainData.prediction?.classification || 'UNKNOWN',
        confidence: explainData.prediction?.confidence || 0,
        processingTime: explainData.prediction?.processing_time_ms || 0,
        baseScore: explainData.shap_explanation?.base_score || 0,
        positiveFactors: explainData.shap_explanation?.factors_increasing_risk?.map((f: any) => ({
          name: f.name,
          value: String(f.value),
          contribution: f.contribution,
          direction: 'up' as const
        })) || [],
        negativeFactors: explainData.shap_explanation?.factors_decreasing_risk?.map((f: any) => ({
          name: f.name,
          value: String(f.value),
          contribution: f.contribution,
          direction: 'down' as const
        })) || [],
        interpretation: explainData.interpretation || ['Unable to generate interpretation'],
      })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load explanation')
    } finally {
      setLoading(false)
    }
  }

  const handleLoadComparison = async () => {
    if (!explanation) return

    setComparisonLoading(true)
    try {
      const compareResponse = await fetch(`/api/risk-models/compare?shipment_id=${explanation.shipmentId}`)
      if (!compareResponse.ok) {
        throw new Error('Failed to load model comparison')
      }
      const comparisonData = await compareResponse.json()

      // Update explanation with comparison
      setExplanation(prev => prev ? { ...prev, comparison: comparisonData } : null)
      setShowComparison(true)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load comparison')
    } finally {
      setComparisonLoading(false)
    }
  }

  const getClassificationColor = (classification: string) => {
    switch (classification) {
      case 'CLEAR':
        return { bg: 'bg-green-50', text: 'text-green-900', badge: 'bg-green-100 text-green-800' }
      case 'EXAMINE':
        return { bg: 'bg-yellow-50', text: 'text-yellow-900', badge: 'bg-yellow-100 text-yellow-800' }
      case 'HOLD':
        return { bg: 'bg-red-50', text: 'text-red-900', badge: 'bg-red-100 text-red-800' }
      default:
        return { bg: 'bg-gray-50', text: 'text-gray-900', badge: 'bg-gray-100 text-gray-800' }
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-sentry-navy mb-2">Prediction Explanations</h1>
        <p className="text-sentry-slate">Understand individual predictions with SHAP analysis</p>
      </div>

      {/* Search */}
      <div className="bg-white border border-gray-200 rounded-lg p-4">
        <label className="text-sm font-semibold text-gray-700 mb-2 block">Search Shipment:</label>
        <div className="flex gap-2">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-3 text-gray-400" size={18} />
            <input
              type="text"
              value={searchTerm}
              onChange={e => setSearchTerm(e.target.value)}
              onKeyPress={e => e.key === 'Enter' && handleSearch()}
              placeholder="SHP-00142857"
              className="w-full pl-10 pr-3 py-2 border border-gray-300 rounded font-mono text-sm"
            />
          </div>
          <button
            onClick={handleSearch}
            className="px-4 py-2 font-medium bg-sentry-navy text-white rounded hover:bg-opacity-90"
          >
            Search
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-800">
          {error}
        </div>
      )}

      {loading && (
        <div className="bg-white border border-gray-200 rounded-lg p-6 text-center">
          <p className="text-sentry-slate">Loading explanation...</p>
        </div>
      )}

      {explanation && (
        <>
          {/* Shipment Summary */}
          <div className="bg-white border border-gray-200 rounded-lg shadow-sm p-6">
            <h2 className="text-lg font-semibold text-sentry-navy mb-4">Shipment Summary</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-600">Shipment ID:</span>
                  <span className="font-mono font-semibold text-sentry-navy">{explanation.shipmentId}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Origin:</span>
                  <span className="font-semibold text-sentry-navy">{explanation.origin}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Destination:</span>
                  <span className="font-semibold text-sentry-navy">{explanation.destination}</span>
                </div>
              </div>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-600">Commodity:</span>
                  <span className="font-semibold text-sentry-navy">{explanation.commodity}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Declared Value:</span>
                  <span className="font-semibold text-sentry-navy">${explanation.declaredValue.toLocaleString()}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Container:</span>
                  <span className="font-semibold text-sentry-navy">{explanation.containerType}</span>
                </div>
              </div>
            </div>
          </div>

          {/* Prediction */}
          <div className="bg-white border border-gray-200 rounded-lg shadow-sm p-6">
            <h2 className="text-lg font-semibold text-sentry-navy mb-4">Prediction</h2>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div>
                <p className="text-sm text-gray-600">Model:</p>
                <p className="text-lg font-semibold text-sentry-navy">{explanation.modelVersion}</p>
              </div>
              <div>
                <p className="text-sm text-gray-600">Score:</p>
                <div className="flex items-center gap-2 mt-1">
                  <p className="text-2xl font-bold text-sentry-navy">{explanation.score.toFixed(2)}</p>
                  <span className={`inline-block px-2 py-1 rounded text-xs font-medium ${getClassificationColor(explanation.classification).badge}`}>
                    {explanation.classification}
                  </span>
                </div>
              </div>
              <div>
                <p className="text-sm text-gray-600">Confidence:</p>
                <p className="text-lg font-semibold text-sentry-navy">{(explanation.confidence * 100).toFixed(0)}%</p>
              </div>
              <div>
                <p className="text-sm text-gray-600">Processing Time:</p>
                <p className="text-lg font-semibold text-sentry-navy">{explanation.processingTime}ms</p>
              </div>
            </div>
          </div>

          {/* SHAP Explanation */}
          <div className={`border-2 rounded-lg shadow-sm p-6 ${getClassificationColor(explanation.classification).bg}`}>
            <h2 className={`text-lg font-semibold ${getClassificationColor(explanation.classification).text} mb-4`}>
              SHAP Explanation
            </h2>

            <div className="mb-4 text-sm">
              <p className="text-gray-700">
                <span className="font-semibold">Base Score:</span> {explanation.baseScore.toFixed(2)}
              </p>
            </div>

            {/* Positive Factors */}
            <div className="mb-6">
              <h3 className="text-sm font-semibold text-sentry-navy mb-3">Factors Increasing Risk (Pushing up)</h3>
              <div className="space-y-2">
                {explanation.positiveFactors.map((factor, idx) => (
                  <div key={idx} className="bg-white rounded p-3 border border-yellow-200">
                    <div className="flex items-center justify-between mb-2">
                      <p className="font-semibold text-gray-800">{factor.name}</p>
                      <span className="text-green-600 font-semibold">+{factor.contribution.toFixed(2)}</span>
                    </div>
                    <div className="flex items-center">
                      <div className="flex-1 bg-yellow-100 rounded-full h-2 mr-2" style={{ width: `${Math.min(factor.contribution * 100, 100)}%` }}>
                        <div className="bg-yellow-500 h-2 rounded-full" style={{ width: '100%' }}></div>
                      </div>
                      <span className="text-xs text-gray-600 whitespace-nowrap">{factor.value}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Negative Factors */}
            {explanation.negativeFactors.length > 0 && (
              <div className="mb-6">
                <h3 className="text-sm font-semibold text-sentry-navy mb-3">Factors Decreasing Risk (Pushing down)</h3>
                <div className="space-y-2">
                  {explanation.negativeFactors.map((factor, idx) => (
                    <div key={idx} className="bg-white rounded p-3 border border-green-200">
                      <div className="flex items-center justify-between mb-2">
                        <p className="font-semibold text-gray-800">{factor.name}</p>
                        <span className="text-red-600 font-semibold">-{factor.contribution.toFixed(2)}</span>
                      </div>
                      <div className="flex items-center">
                        <div className="flex-1 bg-green-100 rounded-full h-2 mr-2" style={{ width: `${Math.min(factor.contribution * 50, 100)}%` }}>
                          <div className="bg-green-500 h-2 rounded-full" style={{ width: '100%' }}></div>
                        </div>
                        <span className="text-xs text-gray-600 whitespace-nowrap">{factor.value}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Final Score Calculation */}
            <div className="bg-white rounded p-3 border-2 border-sentry-navy">
              <p className="text-sm font-semibold text-sentry-navy">
                Final Score: {explanation.baseScore.toFixed(2)} + {explanation.positiveFactors.reduce((sum, f) => sum + f.contribution, 0).toFixed(2)} - {explanation.negativeFactors.reduce((sum, f) => sum + f.contribution, 0).toFixed(2)} = {explanation.score.toFixed(2)} ✓
              </p>
            </div>
          </div>

          {/* Interpretation */}
          <div className="bg-white border border-gray-200 rounded-lg shadow-sm p-6">
            <h2 className="text-lg font-semibold text-sentry-navy mb-4">Interpretation</h2>
            <div className="bg-blue-50 border-l-4 border-blue-600 p-4 rounded text-sm text-gray-700 space-y-1">
              {explanation.interpretation.map((line, idx) => (
                <p key={idx} className={line.startsWith('-') || line.match(/^\d+\./) ? 'ml-4' : ''}>
                  {line}
                </p>
              ))}
            </div>
          </div>

          {/* Comparison Toggle */}
          <div className="bg-white border border-gray-200 rounded-lg shadow-sm p-6">
            <h2 className="text-lg font-semibold text-sentry-navy mb-4">Model Comparison</h2>

            {!showComparison ? (
              <button
                onClick={handleLoadComparison}
                disabled={comparisonLoading}
                className="w-full px-4 py-3 text-sm font-medium bg-blue-50 text-blue-700 border border-blue-200 rounded hover:bg-blue-100 disabled:opacity-50"
              >
                {comparisonLoading ? 'Loading comparison...' : 'Compare with v2.1 (Rule-Based Legacy Model)'}
              </button>
            ) : explanation?.comparison ? (
              <div className="space-y-4">
                {/* Side-by-side comparison */}
                <div className="grid grid-cols-2 gap-4">
                  {/* v2.1 */}
                  <div className="bg-gray-50 rounded p-4 border border-gray-200">
                    <h3 className="font-semibold text-gray-900 mb-3">v2.1 (Rule-Based)</h3>
                    <div className="space-y-2 text-sm">
                      <div className="flex justify-between items-center">
                        <span className="text-gray-600">Score:</span>
                        <span className="font-bold text-lg text-gray-900">{explanation.comparison.v2_1?.score.toFixed(1)}</span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-gray-600">Confidence:</span>
                        <span className="text-gray-900">—</span>
                      </div>
                      <div className="mt-3">
                        <p className="text-xs font-semibold text-gray-700 mb-2">Factors:</p>
                        <div className="space-y-1">
                          {explanation.comparison.v2_1?.factors?.slice(0, 3).map((f, idx) => (
                            <div key={idx} className="text-xs">
                              <div className="flex justify-between">
                                <span className="text-gray-600">{f.name}:</span>
                                <span className="font-semibold text-gray-900">{f.raw_score.toFixed(1)}</span>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* v3.0 */}
                  <div className="bg-blue-50 rounded p-4 border border-blue-200">
                    <h3 className="font-semibold text-gray-900 mb-3">v3.0 (ML-Based)</h3>
                    <div className="space-y-2 text-sm">
                      <div className="flex justify-between items-center">
                        <span className="text-gray-600">Score:</span>
                        <span className="font-bold text-lg text-sentry-navy">{explanation.score.toFixed(1)}</span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-gray-600">Confidence:</span>
                        <span className="font-semibold text-sentry-navy">{(explanation.confidence * 100).toFixed(0)}%</span>
                      </div>
                      <div className="mt-3">
                        <p className="text-xs font-semibold text-gray-700 mb-2">Top Factors:</p>
                        <div className="space-y-1">
                          {explanation.comparison.v3_0?.factors?.slice(0, 3).map((f, idx) => (
                            <div key={idx} className="text-xs flex justify-between">
                              <span className="text-gray-600">{f.name}:</span>
                              <span className="font-semibold text-gray-900">+{f.contribution.toFixed(2)}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Analysis */}
                {explanation.comparison.difference && (
                  <div className="bg-yellow-50 border border-yellow-200 rounded p-4">
                    <h3 className="font-semibold text-gray-900 mb-2">Analysis</h3>
                    <div className="space-y-2 text-sm">
                      <div className="flex justify-between">
                        <span className="text-gray-700">Score Delta:</span>
                        <span className={`font-semibold ${explanation.comparison.difference.score_delta >= 0 ? 'text-orange-600' : 'text-green-600'}`}>
                          {explanation.comparison.difference.score_delta >= 0 ? '+' : ''}{explanation.comparison.difference.score_delta.toFixed(1)} ({explanation.comparison.difference.score_delta_percent.toFixed(0)}%)
                        </span>
                      </div>
                      <div className="flex justify-between items-start">
                        <span className="text-gray-700">Better Model:</span>
                        <div className="flex items-center gap-1">
                          <span className="font-semibold text-sentry-navy">{explanation.comparison.difference.better_model}</span>
                          <Check size={16} className="text-green-600" />
                        </div>
                      </div>
                      <div className="flex justify-between items-start">
                        <span className="text-gray-700">Reason:</span>
                        <span className="text-right text-gray-900 font-medium">{explanation.comparison.difference.reason}</span>
                      </div>
                    </div>
                  </div>
                )}

                <button
                  onClick={() => setShowComparison(false)}
                  className="w-full px-4 py-2 text-sm font-medium bg-gray-100 text-gray-700 rounded hover:bg-gray-200"
                >
                  Hide Comparison
                </button>
              </div>
            ) : (
              <div className="text-sm text-gray-600">Unable to load comparison</div>
            )}
          </div>
        </>
      )}
    </div>
  )
}

export default PredictionExplanations
