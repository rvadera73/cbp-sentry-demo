import React, { useState, useEffect } from 'react'
import { Download, BarChart3 } from 'lucide-react'
import { usePerformanceMetrics } from '../../v2/hooks/useMCPEngine'

interface PerformanceMetricsProps {
  onExport?: () => void
}

interface MetricPoint {
  timestamp: string
  accuracy: number
  latency: number
}

interface ConfusionMatrixData {
  clear: { clear: number; examine: number; hold: number }
  examine: { clear: number; examine: number; hold: number }
  hold: { clear: number; examine: number; hold: number }
}

interface FairnessMetric {
  segment: string
  accuracy: number
  count: number
}

const PerformanceMetrics: React.FC<PerformanceMetricsProps> = ({ onExport }) => {
  const [timeRange, setTimeRange] = useState<'24h' | '7d' | '30d' | 'custom'>('24h')
  const [compareModel, setCompareModel] = useState<string>('')
  const { history: mcpHistory, performance, loading } = usePerformanceMetrics()
  const [accuracyTrend, setAccuracyTrend] = useState<MetricPoint[]>([])
  const [confusionMatrix, setConfusionMatrix] = useState<ConfusionMatrixData | null>(null)
  const [fairnessMetrics, setFairnessMetrics] = useState<FairnessMetric[]>([])

  useEffect(() => {
    if (mcpHistory.length) {
      setAccuracyTrend(mcpHistory.map(h => ({
        timestamp: new Date(h.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        accuracy: (h.accuracy ?? 0) * 100,
        latency: h.latency_p95_ms ?? 0,
      })))
    }
    if (performance) {
      const p = performance as Record<string, unknown>
      const cm = p['confusion_matrix'] as ConfusionMatrixData | undefined
      if (cm) setConfusionMatrix(cm)
      const fm = p['fairness_by_corridor'] as FairnessMetric[] | undefined
      if (fm) setFairnessMetrics(fm)
    }
  }, [mcpHistory, performance])

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <p className="text-sentry-slate">Loading performance metrics...</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-sentry-navy mb-2">Performance Metrics Dashboard</h1>
        <p className="text-sentry-slate">Time-series monitoring of model performance</p>
      </div>

      {/* Controls */}
      <div className="bg-white border border-gray-200 rounded-lg p-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="text-sm font-semibold text-gray-700 mb-2 block">Time Range:</label>
            <div className="flex flex-wrap gap-2">
              {(['24h', '7d', '30d', 'custom'] as const).map(t => (
                <button
                  key={t}
                  onClick={() => setTimeRange(t)}
                  className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
                    timeRange === t
                      ? 'bg-sentry-navy text-white'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  Last {t === 'custom' ? 'Custom' : t.toUpperCase()}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="text-sm font-semibold text-gray-700 mb-2 block">Compare Model:</label>
            <div className="flex gap-2">
              <select
                value={compareModel}
                onChange={e => setCompareModel(e.target.value)}
                className="flex-1 px-3 py-2 border border-gray-300 rounded text-sm font-medium"
              >
                <option value="v3.0">v3.0 (Active)</option>
                <option value="v3.1">v3.1 (Candidate)</option>
                <option value="v2.1">v2.1 (Legacy)</option>
              </select>
            </div>
          </div>
        </div>
      </div>

      {/* Accuracy Trend */}
      <div className="bg-white border border-gray-200 rounded-lg shadow-sm p-6">
        <h2 className="text-lg font-semibold text-sentry-navy mb-4">Accuracy Trend</h2>
        <div className="bg-gray-50 rounded p-4 h-48 flex items-center justify-center">
          <div className="text-center text-gray-600">
            <BarChart3 className="mx-auto mb-2 text-gray-400" size={32} />
            <p className="text-sm">Chart visualization (Chart.js or similar library recommended)</p>
            <p className="text-xs mt-1 text-gray-500">Time-series accuracy data available in state</p>
          </div>
        </div>
        <div className="mt-4 text-sm">
          <div className="flex justify-between">
            <span className="text-gray-600">Model v3.0 Accuracy:</span>
            <span className="font-semibold text-sentry-navy">92.4%</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-600">Model v3.1 Accuracy:</span>
            <span className="font-semibold text-green-600">93.1% (+0.7%)</span>
          </div>
        </div>
      </div>

      {/* Latency Distribution */}
      <div className="bg-white border border-gray-200 rounded-lg shadow-sm p-6">
        <h2 className="text-lg font-semibold text-sentry-navy mb-4">Latency Distribution (p95)</h2>
        <div className="space-y-4">
          <div>
            <div className="flex justify-between mb-2">
              <span className="text-sm font-semibold text-gray-700">v3.0</span>
              <span className="text-sm font-semibold text-sentry-navy">85ms</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div className="bg-sentry-navy h-2 rounded-full" style={{ width: '42.5%' }}></div>
            </div>
          </div>
          <div>
            <div className="flex justify-between mb-2">
              <span className="text-sm font-semibold text-gray-700">v3.1</span>
              <span className="text-sm font-semibold text-sentry-navy">87ms</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div className="bg-blue-600 h-2 rounded-full" style={{ width: '43.5%' }}></div>
            </div>
          </div>
        </div>
      </div>

      {/* Confusion Matrix */}
      <div className="bg-white border border-gray-200 rounded-lg shadow-sm p-6">
        <h2 className="text-lg font-semibold text-sentry-navy mb-4">Confusion Matrix (v3.0, Last 24h)</h2>
        {confusionMatrix && (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-100">
                  <th className="px-4 py-2 text-left font-semibold text-gray-700">Actual \ Predicted</th>
                  <th className="px-4 py-2 text-center font-semibold text-gray-700">CLEAR</th>
                  <th className="px-4 py-2 text-center font-semibold text-gray-700">EXAMINE</th>
                  <th className="px-4 py-2 text-center font-semibold text-gray-700">HOLD</th>
                </tr>
              </thead>
              <tbody>
                <tr className="border-t border-gray-200">
                  <td className="px-4 py-2 font-semibold text-gray-700">CLEAR</td>
                  <td className="px-4 py-2 text-center bg-green-50">{confusionMatrix.clear.clear}</td>
                  <td className="px-4 py-2 text-center">{confusionMatrix.clear.examine}</td>
                  <td className="px-4 py-2 text-center">{confusionMatrix.clear.hold}</td>
                </tr>
                <tr className="border-t border-gray-200">
                  <td className="px-4 py-2 font-semibold text-gray-700">EXAMINE</td>
                  <td className="px-4 py-2 text-center">{confusionMatrix.examine.clear}</td>
                  <td className="px-4 py-2 text-center bg-green-50">{confusionMatrix.examine.examine}</td>
                  <td className="px-4 py-2 text-center">{confusionMatrix.examine.hold}</td>
                </tr>
                <tr className="border-t border-gray-200">
                  <td className="px-4 py-2 font-semibold text-gray-700">HOLD</td>
                  <td className="px-4 py-2 text-center">{confusionMatrix.hold.clear}</td>
                  <td className="px-4 py-2 text-center">{confusionMatrix.hold.examine}</td>
                  <td className="px-4 py-2 text-center bg-green-50">{confusionMatrix.hold.hold}</td>
                </tr>
              </tbody>
            </table>
          </div>
        )}
        <div className="mt-4 space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-gray-600">Recall (HOLD):</span>
            <span className="font-semibold text-sentry-navy">79.2%</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-600">Precision (HOLD):</span>
            <span className="font-semibold text-sentry-navy">83.1%</span>
          </div>
        </div>
      </div>

      {/* Fairness Metrics */}
      <div className="bg-white border border-gray-200 rounded-lg shadow-sm p-6">
        <h2 className="text-lg font-semibold text-sentry-navy mb-4">Fairness Metrics (v3.0)</h2>
        <div className="space-y-3 mb-4">
          {fairnessMetrics.map((metric, idx) => (
            <div key={idx} className="flex items-center justify-between">
              <div className="flex-1">
                <p className="text-sm font-semibold text-gray-700">{metric.segment}</p>
                <p className="text-xs text-gray-600">N={metric.count.toLocaleString()}</p>
              </div>
              <div className="text-right">
                <p className="text-sm font-semibold text-sentry-navy">Accuracy: {metric.accuracy.toFixed(1)}%</p>
              </div>
            </div>
          ))}
        </div>
        <div className="pt-4 border-t border-gray-200">
          <div className="flex justify-between items-center">
            <span className="text-sm font-semibold text-gray-700">Fairness Score:</span>
            <div className="flex items-center gap-2">
              <span className="text-lg font-bold text-green-600">0.94</span>
              <span className="inline-block px-2 py-1 rounded text-xs font-medium bg-green-100 text-green-800">
                Good ✓
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Export & Report */}
      <div className="bg-white border border-gray-200 rounded-lg shadow-sm p-6">
        <h2 className="text-lg font-semibold text-sentry-navy mb-4">Export & Report</h2>
        <div className="flex flex-wrap gap-3">
          <button
            onClick={onExport}
            className="px-4 py-2 text-sm font-medium bg-sentry-navy text-white rounded hover:bg-opacity-90 flex items-center gap-2"
          >
            <Download size={16} />
            Download CSV
          </button>
          <button className="px-4 py-2 text-sm font-medium bg-gray-200 text-gray-800 rounded hover:bg-gray-300">
            Generate Report
          </button>
          <button className="px-4 py-2 text-sm font-medium bg-gray-200 text-gray-800 rounded hover:bg-gray-300">
            Alert Setup
          </button>
        </div>
      </div>
    </div>
  )
}

export default PerformanceMetrics
