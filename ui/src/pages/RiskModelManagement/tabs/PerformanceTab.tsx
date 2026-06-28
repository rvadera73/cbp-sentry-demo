/**
 * Performance Tab - Model Metrics & Feature Importance
 *
 * 100% API-driven. No hardcoded metrics, fallbacks, or mock feature importance.
 *
 * Data sources:
 * - GET /metrics/performance  → AUC, precision, recall, F1, accuracy, sample counts
 * - GET /features/importance  → XGBoost gain/weight/cover ranking per feature
 */

import React, { useEffect, useState } from 'react'
import { AlertCircle, Loader } from 'lucide-react'
import { CBPColors, CBPTypography } from '../../../styles/CBPDesignSystem'
import { getMLOpsEndpoint } from '../../../services/apiUrl'

interface PerformanceMetrics {
  auc: number | null
  precision: number | null
  recall: number | null
  f1_score: number | null
  accuracy: number | null
  training_samples: number | null
  test_samples: number | null
  feature_count: number | null
}

interface ImportanceItem {
  feature: string
  description: string
  gain: number
  weight: number
  cover: number
}

const pct = (value: number | null): string => (value === null || Number.isNaN(value) ? '—' : `${(value * 100).toFixed(1)}%`)
const num = (value: number | null): string => (value === null || Number.isNaN(value) ? '—' : value.toLocaleString())
const fixed = (value: number | null, digits = 3): string => (value === null || Number.isNaN(value) ? '—' : value.toFixed(digits))

const PerformanceTab: React.FC = () => {
  const [metrics, setMetrics] = useState<PerformanceMetrics | null>(null)
  const [importance, setImportance] = useState<ImportanceItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    const load = async () => {
      setLoading(true)
      setError(null)
      try {
        const [perfRes, impRes] = await Promise.all([
          fetch(getMLOpsEndpoint('/metrics/performance')),
          fetch(getMLOpsEndpoint('/features/importance')),
        ])
        if (!perfRes.ok) throw new Error(`Performance metrics request failed (${perfRes.status})`)
        const perf = await perfRes.json()
        const m = perf.metrics || {}
        // Feature importance is optional (500 when the XGBoost model is not loaded).
        const imp = impRes.ok ? await impRes.json() : { importance: [] }
        if (!cancelled) {
          setMetrics({
            auc: m.auc ?? null,
            precision: m.precision ?? null,
            recall: m.recall ?? null,
            f1_score: m.f1_score ?? null,
            accuracy: m.accuracy ?? null,
            training_samples: m.training_samples ?? null,
            test_samples: m.test_samples ?? null,
            feature_count: m.feature_count ?? null,
          })
          setImportance(Array.isArray(imp.importance) ? imp.importance : [])
        }
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Failed to load performance data')
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => {
      cancelled = true
    }
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <Loader className="w-8 h-8 animate-spin text-[#005EA2] mx-auto" />
          <p className="mt-2 text-slate-600">Loading metrics from /metrics/performance…</p>
        </div>
      </div>
    )
  }

  if (error || !metrics) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-sm p-4 flex items-start gap-3">
        <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
        <div>
          <p className="font-semibold text-red-900">Unable to load performance metrics</p>
          <p className="text-sm text-red-700 mt-1">{error || 'No metrics returned by /metrics/performance'}</p>
        </div>
      </div>
    )
  }

  const maxGain = importance.reduce((max, item) => Math.max(max, item.gain), 0)

  return (
    <div className="space-y-8">
      {/* Key Performance Metrics */}
      <div className="border border-[#D0D7DE] bg-white rounded-sm p-4">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-8 h-8 rounded-full flex items-center justify-center text-white text-[11px] font-bold" style={{ backgroundColor: CBPColors.primary }}>
            1
          </div>
          <div>
            <h3 className={`text-sm font-bold ${CBPTypography.label}`}>Key Performance Metrics</h3>
            <p className={`text-[11px] ${CBPTypography.small} mt-0.5`}>XGBoost evaluation from latest training results</p>
          </div>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          <div className="p-4 bg-slate-50 rounded-sm border border-[#D0D7DE]">
            <div className={`text-[10px] font-bold uppercase tracking-wide ${CBPTypography.tableCaption}`}>AUC-ROC</div>
            <div className="text-2xl font-bold text-[#0B1F33] mt-2">{fixed(metrics.auc)}</div>
            <p className={`text-[10px] ${CBPTypography.small} mt-1`}>Discrimination ability</p>
          </div>
          <div className="p-4 bg-slate-50 rounded-sm border border-[#D0D7DE]">
            <div className={`text-[10px] font-bold uppercase tracking-wide ${CBPTypography.tableCaption}`}>Accuracy</div>
            <div className="text-2xl font-bold text-[#0B1F33] mt-2">{pct(metrics.accuracy)}</div>
            <p className={`text-[10px] ${CBPTypography.small} mt-1`}>Correct predictions</p>
          </div>
          <div className="p-4 bg-slate-50 rounded-sm border border-[#D0D7DE]">
            <div className={`text-[10px] font-bold uppercase tracking-wide ${CBPTypography.tableCaption}`}>F1 Score</div>
            <div className="text-2xl font-bold text-[#0B1F33] mt-2">{pct(metrics.f1_score)}</div>
            <p className={`text-[10px] ${CBPTypography.small} mt-1`}>Precision/recall balance</p>
          </div>
          <div className="p-4 bg-slate-50 rounded-sm border border-[#D0D7DE]">
            <div className={`text-[10px] font-bold uppercase tracking-wide ${CBPTypography.tableCaption}`}>Precision</div>
            <div className="text-2xl font-bold text-[#0B1F33] mt-2">{pct(metrics.precision)}</div>
            <p className={`text-[10px] ${CBPTypography.small} mt-1`}>True positive rate</p>
          </div>
          <div className="p-4 bg-slate-50 rounded-sm border border-[#D0D7DE]">
            <div className={`text-[10px] font-bold uppercase tracking-wide ${CBPTypography.tableCaption}`}>Recall</div>
            <div className="text-2xl font-bold text-[#0B1F33] mt-2">{pct(metrics.recall)}</div>
            <p className={`text-[10px] ${CBPTypography.small} mt-1`}>Coverage of positives</p>
          </div>
          <div className="p-4 bg-slate-50 rounded-sm border border-[#D0D7DE]">
            <div className={`text-[10px] font-bold uppercase tracking-wide ${CBPTypography.tableCaption}`}>Feature Count</div>
            <div className="text-2xl font-bold text-[#0B1F33] mt-2">{num(metrics.feature_count)}</div>
            <p className={`text-[10px] ${CBPTypography.small} mt-1`}>Model input features</p>
          </div>
        </div>

        <div className="mt-4 grid grid-cols-2 gap-4">
          <div className="p-3 bg-slate-50 rounded-sm border border-[#D0D7DE]">
            <div className={`text-[10px] font-bold uppercase tracking-wide ${CBPTypography.tableCaption}`}>Training Samples</div>
            <div className="text-lg font-bold text-[#0B1F33] mt-1">{num(metrics.training_samples)}</div>
          </div>
          <div className="p-3 bg-slate-50 rounded-sm border border-[#D0D7DE]">
            <div className={`text-[10px] font-bold uppercase tracking-wide ${CBPTypography.tableCaption}`}>Test Samples</div>
            <div className="text-lg font-bold text-[#0B1F33] mt-1">{num(metrics.test_samples)}</div>
          </div>
        </div>
      </div>

      {/* Feature Importance */}
      <div className="border border-[#D0D7DE] bg-white rounded-sm p-4">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-8 h-8 rounded-full flex items-center justify-center text-white text-[11px] font-bold" style={{ backgroundColor: CBPColors.primary }}>
            2
          </div>
          <div>
            <h3 className={`text-sm font-bold ${CBPTypography.label}`}>Feature Importance Ranking</h3>
            <p className={`text-[11px] ${CBPTypography.small} mt-0.5`}>XGBoost gain importance per feature (top 15)</p>
          </div>
        </div>

        {importance.length === 0 ? (
          <div className="text-center py-8 text-slate-500">
            <p>No feature importance available — XGBoost model is not loaded.</p>
          </div>
        ) : (
          <div className="space-y-3">
            {importance.slice(0, 15).map((feature) => (
              <div key={feature.feature}>
                <div className="flex items-center justify-between mb-2">
                  <span className={`text-[11px] font-semibold text-[#0B1F33]`}>
                    {feature.description || feature.feature}
                  </span>
                  <span className={`text-[10px] ${CBPTypography.tableCaption}`}>gain {feature.gain.toFixed(2)}</span>
                </div>
                <div className="w-full h-4 bg-slate-100 rounded-sm overflow-hidden border border-[#D0D7DE]">
                  <div
                    className="h-full transition-all"
                    style={{
                      width: maxGain > 0 ? `${(feature.gain / maxGain) * 100}%` : '0%',
                      backgroundColor: CBPColors.primary,
                    }}
                  />
                </div>
                <div className={`text-[10px] ${CBPTypography.small} mt-1`}>
                  weight {feature.weight.toFixed(0)} · cover {feature.cover.toFixed(2)}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export default PerformanceTab
