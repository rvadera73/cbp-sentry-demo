/**
 * Monitoring Tab - Feedback & Score Drift
 *
 * 100% API-driven. No hardcoded feedback stats, recent predictions, or drift results.
 *
 * Data sources:
 * - GET /metrics/drift     → per-feature drift scores + critical/warning/normal summary
 * - GET /feedback/summary  → total analyst feedback + per-factor override summary
 */

import React, { useEffect, useState } from 'react'
import { TrendingUp, AlertTriangle, Loader } from 'lucide-react'
import { CBPColors, CBPTypography } from '../../../styles/CBPDesignSystem'
import { getMLOpsEndpoint } from '../../../services/apiUrl'

interface DriftFeature {
  feature: string
  drift_score: number
  alert_level: 'critical' | 'warning' | 'normal'
  current_mean: number | null
  baseline_mean: number | null
}

interface DriftResponse {
  generated_at: string
  sample_source: string
  sample_size: number
  summary: { critical: number; warning: number; normal: number }
  features: DriftFeature[]
}

interface FactorSummary {
  factor: string
  override_count: number
  avg_delta: number | null
  positive_overrides: number
  negative_overrides: number
}

interface FeedbackSummary {
  total_feedback: number
  factor_summary: FactorSummary[]
}

const driftBadge = (level: string) => {
  switch (level) {
    case 'critical':
      return { row: 'bg-red-50 border-red-400', badge: 'bg-red-200 text-red-900', text: 'text-red-900' }
    case 'warning':
      return { row: 'bg-amber-50 border-amber-400', badge: 'bg-amber-200 text-amber-900', text: 'text-amber-900' }
    default:
      return { row: 'bg-green-50 border-green-400', badge: 'bg-green-200 text-green-900', text: 'text-green-900' }
  }
}

const MonitoringTab: React.FC = () => {
  const [drift, setDrift] = useState<DriftResponse | null>(null)
  const [feedback, setFeedback] = useState<FeedbackSummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    const load = async () => {
      setLoading(true)
      setError(null)
      try {
        const [driftRes, feedbackRes] = await Promise.all([
          fetch(getMLOpsEndpoint('/metrics/drift')),
          fetch(getMLOpsEndpoint('/feedback/summary')),
        ])
        if (!driftRes.ok) throw new Error(`Drift request failed (${driftRes.status})`)
        const driftData: DriftResponse = await driftRes.json()
        const feedbackData: FeedbackSummary | null = feedbackRes.ok ? await feedbackRes.json() : null
        if (!cancelled) {
          setDrift(driftData)
          setFeedback(feedbackData)
        }
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Failed to load monitoring data')
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
          <p className="mt-2 text-slate-600">Loading monitoring data…</p>
        </div>
      </div>
    )
  }

  if (error || !drift) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-sm p-6 flex items-start gap-3">
        <AlertTriangle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
        <div>
          <p className="font-semibold text-red-900">Unable to load monitoring data</p>
          <p className="text-sm text-red-700 mt-1">{error || 'No drift data returned by /metrics/drift'}</p>
        </div>
      </div>
    )
  }

  const driftFeatures = drift.features || []

  return (
    <div className="space-y-8">
      {/* Analyst Feedback Summary */}
      <div className="border border-[#D0D7DE] bg-white rounded-sm p-6">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-8 h-8 rounded-full flex items-center justify-center text-white text-[11px] font-bold" style={{ backgroundColor: CBPColors.primary }}>
            1
          </div>
          <div>
            <h3 className={`text-sm font-bold ${CBPTypography.label}`}>Analyst Feedback Summary</h3>
            <p className={`text-[11px] ${CBPTypography.small} mt-0.5`}>Recorded feedback and per-factor weight overrides</p>
          </div>
        </div>

        {feedback ? (
          <>
            <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-sm">
              <div className="flex items-center justify-between">
                <p className={`text-sm font-bold text-blue-900`}>Total Feedback Recorded</p>
                <p className="text-2xl font-bold text-blue-700">{feedback.total_feedback.toLocaleString()}</p>
              </div>
            </div>

            {feedback.factor_summary.length === 0 ? (
              <div className="text-center py-6 text-slate-500"><p>No weight-override factors recorded yet.</p></div>
            ) : (
              <div className="space-y-2">
                <p className={`text-[10px] font-bold uppercase tracking-wide ${CBPTypography.tableCaption} mb-2`}>Factor Overrides</p>
                {feedback.factor_summary.map((f) => (
                  <div key={f.factor} className="flex items-center justify-between p-3 bg-slate-50 border border-[#D0D7DE] rounded-sm">
                    <div className="flex-1">
                      <p className="text-sm font-semibold text-slate-900">{f.factor}</p>
                      <p className={`text-[10px] ${CBPTypography.small} mt-1`}>
                        {f.override_count} override{f.override_count === 1 ? '' : 's'} · avg delta {f.avg_delta !== null ? f.avg_delta.toFixed(4) : '—'}
                      </p>
                    </div>
                    <div className="text-right flex-shrink-0 text-[11px]">
                      <span className="text-green-700 font-semibold">+{f.positive_overrides}</span>
                      <span className="text-slate-400 mx-1">/</span>
                      <span className="text-red-700 font-semibold">-{f.negative_overrides}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </>
        ) : (
          <div className="text-center py-6 text-slate-500"><p>Feedback summary unavailable (/feedback/summary).</p></div>
        )}
      </div>

      {/* Drift Summary */}
      <div className="border border-[#D0D7DE] bg-white rounded-sm p-6">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-8 h-8 rounded-full flex items-center justify-center text-white text-[11px] font-bold" style={{ backgroundColor: CBPColors.primary }}>
            2
          </div>
          <div>
            <h3 className={`text-sm font-bold ${CBPTypography.label}`}>Data Drift Detection</h3>
            <p className={`text-[11px] ${CBPTypography.small} mt-0.5`}>
              Sample source: {drift.sample_source} · {drift.sample_size.toLocaleString()} records · generated {new Date(drift.generated_at).toLocaleString()}
            </p>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-4 mb-6">
          <div className="p-4 bg-red-50 rounded-sm border border-red-200">
            <div className="text-[10px] font-bold uppercase tracking-wide text-red-700">Critical</div>
            <div className="text-3xl font-bold text-red-700 mt-2">{drift.summary.critical}</div>
          </div>
          <div className="p-4 bg-amber-50 rounded-sm border border-amber-200">
            <div className="text-[10px] font-bold uppercase tracking-wide text-amber-700">Warning</div>
            <div className="text-3xl font-bold text-amber-700 mt-2">{drift.summary.warning}</div>
          </div>
          <div className="p-4 bg-green-50 rounded-sm border border-green-200">
            <div className="text-[10px] font-bold uppercase tracking-wide text-green-700">Normal</div>
            <div className="text-3xl font-bold text-green-700 mt-2">{drift.summary.normal}</div>
          </div>
        </div>

        <div className="space-y-3">
          {driftFeatures.length === 0 ? (
            <div className="text-center py-8 text-slate-500"><p>No drift features computed for the current sample.</p></div>
          ) : (
            driftFeatures.map((result) => {
              const style = driftBadge(result.alert_level)
              return (
                <div key={result.feature} className={`p-4 rounded-sm border-l-4 flex items-start justify-between ${style.row}`}>
                  <div className="flex-1">
                    <p className={`text-sm font-bold ${style.text}`}>{result.feature}</p>
                    <p className={`text-[10px] ${CBPTypography.small} mt-1`}>
                      Drift score: {result.drift_score.toFixed(3)}
                      {result.baseline_mean !== null && result.current_mean !== null
                        ? ` · baseline mean ${result.baseline_mean.toFixed(2)} → current ${result.current_mean.toFixed(2)}`
                        : ''}
                    </p>
                  </div>
                  <div className="text-right flex-shrink-0 ml-4">
                    <span className={`inline-flex items-center px-2 py-1 rounded text-xs font-semibold ${style.badge}`}>
                      {result.alert_level.toUpperCase()}
                    </span>
                  </div>
                </div>
              )
            })
          )}
        </div>

        {drift.summary.critical > 0 && (
          <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-sm flex items-start gap-2">
            <AlertTriangle className="w-4 h-4 text-red-600 flex-shrink-0 mt-0.5" />
            <p className="text-[10px] text-red-700">
              <strong>{drift.summary.critical} feature{drift.summary.critical > 1 ? 's' : ''}</strong> at critical drift. Review distribution shifts and consider retraining on recent data.
            </p>
          </div>
        )}
      </div>

      {/* Recommendation derived from live drift state */}
      {(drift.summary.critical > 0 || drift.summary.warning > 0) && (
        <div className="p-4 rounded-sm border-l-4 bg-blue-50 border-blue-400 flex items-start gap-3">
          <TrendingUp className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-bold text-blue-900">Monitoring Recommendation</p>
            <p className="text-[11px] text-blue-700 mt-2">
              {drift.summary.critical + drift.summary.warning} feature(s) drifting beyond threshold. Investigate
              {' '}{driftFeatures.filter(f => f.alert_level !== 'normal').map(f => f.feature).join(', ') || 'flagged features'}
              {' '}before the next scheduled retraining window.
            </p>
          </div>
        </div>
      )}
    </div>
  )
}

export default MonitoringTab
