import React, { useState, useEffect } from 'react'
import { AlertTriangle, CheckCircle, TrendingDown } from 'lucide-react'
import { useDataDrift } from '../../v2/hooks/useMCPEngine'

interface DataDriftMonitoringProps {
  onInvestigate?: (featureName: string) => void
}

interface DriftFeature {
  name: string
  driftScore: number
  driftType: 'categorical_shift' | 'numeric_distribution'
  baselineData: string | Record<string, number>
  currentData: string | Record<string, number>
  status: 'elevated' | 'normal'
  recommendation?: string
}

const DataDriftMonitoring: React.FC<DataDriftMonitoringProps> = ({ onInvestigate }) => {
  const [baselinePeriod] = useState('Last 7d Baseline')
  const [currentPeriod] = useState('Last 24h')
  const { drift: mcpDrift, loading, error } = useDataDrift()
  const [features, setFeatures] = useState<DriftFeature[]>([])

  useEffect(() => {
    if (mcpDrift.length) {
      setFeatures(mcpDrift.map(d => ({
        name: d.name,
        driftScore: d.drift_score,
        driftType: d.drift_type as DriftFeature['driftType'],
        baselineData: '',
        currentData: '',
        status: d.status,
        recommendation: d.recommendation,
      })))
    }
  }, [mcpDrift])

  const elevatedDriftCount = features.filter(f => f.status === 'elevated').length
  const normalDriftCount = features.filter(f => f.status === 'normal').length
  const overallDriftScore = features.length
    ? (elevatedDriftCount * 0.34 + normalDriftCount * 0.06) / features.length
    : 0

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <p className="text-sentry-slate">Loading drift monitoring data...</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-sentry-navy mb-2">Data Drift Monitoring</h1>
        <p className="text-sentry-slate">Detect feature distribution changes</p>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-800">
          {error}
        </div>
      )}

      {/* Configuration */}
      <div className="bg-white border border-gray-200 rounded-lg p-4 space-y-3">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
          <div>
            <span className="text-gray-600 font-semibold">Baseline Period:</span>
            <p className="text-sentry-navy font-semibold">{baselinePeriod}</p>
          </div>
          <div>
            <span className="text-gray-600 font-semibold">Current Period:</span>
            <p className="text-sentry-navy font-semibold">{currentPeriod}</p>
          </div>
          <div>
            <span className="text-gray-600 font-semibold">Detection Method:</span>
            <p className="text-sentry-navy font-semibold">Kolmogorov-Smirnov</p>
          </div>
        </div>
      </div>

      {/* Elevated Drift Alert */}
      {elevatedDriftCount > 0 && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 flex items-start gap-3">
          <AlertTriangle className="text-yellow-600 flex-shrink-0 mt-0.5" size={20} />
          <div>
            <h2 className="font-semibold text-yellow-900">Elevated Drift Detected</h2>
            <p className="text-sm text-yellow-800 mt-1">
              {elevatedDriftCount} feature(s) showing significant distribution changes
            </p>
          </div>
        </div>
      )}

      {/* Features List */}
      <div className="space-y-4">
        {features.map((feature, idx) => (
          <div
            key={idx}
            className={`border rounded-lg p-6 ${
              feature.status === 'elevated'
                ? 'bg-yellow-50 border-yellow-200'
                : 'bg-white border-gray-200'
            }`}
          >
            {/* Header */}
            <div className="flex items-start justify-between mb-4">
              <div className="flex-1">
                <h3 className="text-lg font-semibold text-sentry-navy uppercase">{feature.name}</h3>
                <div className="flex items-center gap-2 mt-2">
                  <span className={`text-2xl font-bold ${feature.status === 'elevated' ? 'text-yellow-600' : 'text-green-600'}`}>
                    {feature.driftScore.toFixed(2)}
                  </span>
                  <span
                    className={`inline-block px-2 py-1 rounded text-xs font-medium ${
                      feature.status === 'elevated'
                        ? 'bg-yellow-100 text-yellow-800'
                        : 'bg-green-100 text-green-800'
                    }`}
                  >
                    {feature.status === 'elevated' ? 'Elevated' : 'Normal'}
                  </span>
                </div>
              </div>
              <div>
                {feature.status === 'elevated' ? (
                  <AlertTriangle className="text-yellow-600" size={32} />
                ) : (
                  <CheckCircle className="text-green-600" size={32} />
                )}
              </div>
            </div>

            {/* Drift Details */}
            <div className="mb-4 pb-4 border-b border-gray-200">
              <p className="text-sm text-gray-600 mb-2">
                <span className="font-semibold">Drift Type:</span>{' '}
                {feature.driftType === 'categorical_shift' ? 'Categorical shift' : 'Numeric distribution'}
              </p>
            </div>

            {/* Distribution Data */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-4">
              <div>
                <h4 className="text-sm font-semibold text-sentry-navy mb-2">Baseline Distribution</h4>
                {typeof feature.baselineData === 'string' ? (
                  <p className="text-sm text-gray-700">{feature.baselineData}</p>
                ) : (
                  <div className="space-y-1 text-sm">
                    {Object.entries(feature.baselineData as Record<string, number>).map(([key, val]) => (
                      <div key={key} className="flex justify-between">
                        <span className="text-gray-700">{key}:</span>
                        <span className="font-semibold text-sentry-navy">{val.toFixed(1)}%</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <div>
                <h4 className="text-sm font-semibold text-sentry-navy mb-2">Current Distribution</h4>
                {typeof feature.currentData === 'string' ? (
                  <p className="text-sm text-gray-700">{feature.currentData}</p>
                ) : (
                  <div className="space-y-1 text-sm">
                    {Object.entries(feature.currentData as Record<string, number>).map(([key, val]) => (
                      <div key={key} className="flex justify-between">
                        <span className="text-gray-700">{key}:</span>
                        <span className="font-semibold text-sentry-navy">{val.toFixed(1)}%</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Recommendation */}
            {feature.recommendation && (
              <div className="mb-4 pb-4 border-t border-gray-200 pt-4">
                <p className="text-sm">
                  <span className="font-semibold text-gray-700">Recommendation:</span>{' '}
                  <span className="text-gray-700">{feature.recommendation}</span>
                </p>
              </div>
            )}

            {/* Actions */}
            {feature.status === 'elevated' && (
              <div className="flex gap-2">
                <button
                  onClick={() => onInvestigate?.(feature.name)}
                  className="px-3 py-1 text-sm font-medium bg-yellow-600 text-white rounded hover:bg-yellow-700"
                >
                  Investigate
                </button>
                <button className="px-3 py-1 text-sm font-medium bg-gray-200 text-gray-800 rounded hover:bg-gray-300">
                  Run Detailed Analysis
                </button>
              </div>
            )}

            {feature.status === 'normal' && (
              <button className="px-3 py-1 text-sm font-medium bg-gray-200 text-gray-800 rounded hover:bg-gray-300">
                View Distribution Plot
              </button>
            )}
          </div>
        ))}
      </div>

      {/* Summary */}
      <div className="bg-white border border-gray-200 rounded-lg shadow-sm p-6">
        <h2 className="text-lg font-semibold text-sentry-navy mb-4">Drift Summary</h2>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <div>
            <p className="text-sm text-gray-600">Elevated Drift Features</p>
            <p className="text-2xl font-bold text-yellow-600">{elevatedDriftCount}</p>
          </div>
          <div>
            <p className="text-sm text-gray-600">Normal Features</p>
            <p className="text-2xl font-bold text-green-600">{normalDriftCount}</p>
          </div>
          <div>
            <p className="text-sm text-gray-600">Total Features Checked</p>
            <p className="text-2xl font-bold text-sentry-navy">{features.length}</p>
          </div>
          <div>
            <p className="text-sm text-gray-600">Overall Drift Score</p>
            <p className="text-2xl font-bold text-sentry-navy">{overallDriftScore.toFixed(2)}</p>
            <p className="text-xs text-green-600 mt-1">Acceptable</p>
          </div>
        </div>

        <div className="border-t border-gray-200 pt-6">
          <h3 className="text-sm font-semibold text-sentry-navy mb-3">Recommended Actions:</h3>
          <div className="space-y-2 text-sm text-gray-700">
            <label className="flex items-center gap-2 cursor-pointer">
              <input type="checkbox" className="rounded" />
              Schedule retraining (if drift continues)
            </label>
            <label className="flex items-center gap-2 cursor-pointer">
              <input type="checkbox" className="rounded" />
              Investigate root cause
            </label>
            <label className="flex items-center gap-2 cursor-pointer">
              <input type="checkbox" className="rounded" />
              Monitor closely for 48 hours
            </label>
          </div>
        </div>

        <div className="mt-6 flex gap-2">
          <button className="px-4 py-2 text-sm font-medium bg-sentry-navy text-white rounded hover:bg-opacity-90">
            Acknowledge Alert
          </button>
          <button className="px-4 py-2 text-sm font-medium bg-gray-200 text-gray-800 rounded hover:bg-gray-300">
            Dismiss
          </button>
          <button className="px-4 py-2 text-sm font-medium bg-gray-200 text-gray-800 rounded hover:bg-gray-300">
            More Details
          </button>
        </div>
      </div>
    </div>
  )
}

export default DataDriftMonitoring
