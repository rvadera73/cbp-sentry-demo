/**
 * Monitoring Tab — analyst feedback + score/feature drift.
 * Data: GET /metrics/drift, GET /feedback/summary.
 */
import React, { useEffect, useState } from 'react'
import { MessageSquare, TrendingUp } from 'lucide-react'
import { getMLOpsEndpoint } from '../../../services/apiUrl'
import { SectionHeader, Panel, StatStrip, StatusPill, DataTable, LoadingState, ErrorState, Column } from '../components/ui'

interface DriftFeature {
  feature: string; drift_score: number; alert_level: 'critical' | 'warning' | 'normal'
  current_mean: number | null; baseline_mean: number | null
}
interface DriftResponse {
  generated_at: string; sample_source: string; sample_size: number
  summary: { critical: number; warning: number; normal: number }; features: DriftFeature[]
}
interface FactorSummary { factor: string; override_count: number; avg_delta: number | null; positive_overrides: number; negative_overrides: number }
interface FeedbackSummary { total_feedback: number; factor_summary: FactorSummary[] }

const MonitoringTab: React.FC = () => {
  const [drift, setDrift] = useState<DriftResponse | null>(null)
  const [feedback, setFeedback] = useState<FeedbackSummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      setLoading(true); setError(null)
      try {
        const [dRes, fRes] = await Promise.all([
          fetch(getMLOpsEndpoint('/metrics/drift')),
          fetch(getMLOpsEndpoint('/feedback/summary')),
        ])
        if (!dRes.ok) throw new Error(`Drift request failed (${dRes.status})`)
        if (!cancelled) {
          setDrift(await dRes.json())
          setFeedback(fRes.ok ? await fRes.json() : null)
        }
      } catch (e) { if (!cancelled) setError(e instanceof Error ? e.message : 'Failed to load monitoring data') }
      finally { if (!cancelled) setLoading(false) }
    })()
    return () => { cancelled = true }
  }, [])

  if (loading) return <LoadingState label="Loading monitoring data…" />
  if (error || !drift) return <ErrorState title="Unable to load monitoring data" detail={error} />

  const driftColumns: Column[] = [
    { key: 'feature', label: 'Feature', render: r => <span className="font-mono">{r.feature}</span> },
    { key: 'drift_score', label: 'Drift (KS)', align: 'right', mono: true, render: r => Number(r.drift_score).toFixed(3) },
    { key: 'shift', label: 'Baseline → Current', align: 'right', mono: true, render: r => (r.baseline_mean != null && r.current_mean != null ? `${r.baseline_mean.toFixed(1)} → ${r.current_mean.toFixed(1)}` : '—') },
    { key: 'alert_level', label: 'Status', align: 'center', render: r => <StatusPill status={r.alert_level} /> },
  ]

  return (
    <div className="space-y-5">
      <Panel>
        <SectionHeader title="Analyst Feedback" subtitle="Officer agree/reject signals routed to the training store" icon={<MessageSquare className="w-4 h-4" />} />
        <StatStrip items={[
          { label: 'Total Feedback', value: feedback ? feedback.total_feedback.toLocaleString() : '—' },
          ...((feedback?.factor_summary || []).slice(0, 3).map(f => ({
            label: f.factor, value: f.override_count, hint: `+${f.positive_overrides} / -${f.negative_overrides}`,
          }))),
        ]} />
        {feedback && feedback.factor_summary.length === 0 && (
          <p className="text-[11px] text-[#5C5C5C] mt-2">No analyst dispositions recorded yet.</p>
        )}
      </Panel>

      <Panel>
        <SectionHeader
          title="Data Drift Detection"
          subtitle={`${drift.sample_source} · ${drift.sample_size.toLocaleString()} records · ${new Date(drift.generated_at).toLocaleString()}`}
          icon={<TrendingUp className="w-4 h-4" />}
        />
        <div className="mb-3">
          <StatStrip items={[
            { label: 'Critical', value: drift.summary.critical, color: '#DC2626' },
            { label: 'Warning', value: drift.summary.warning, color: '#B45309' },
            { label: 'Normal', value: drift.summary.normal, color: '#15803D' },
          ]} />
        </div>
        <DataTable columns={driftColumns} rows={drift.features} caption="Per-feature drift (two-sample KS over prediction_log)"
          empty="No drift computed — needs more scored shipments in prediction_log." />
        {drift.summary.critical > 0 && (
          <p className="text-[11px] text-red-700 mt-2" role="alert">
            {drift.summary.critical} feature(s) at critical drift — review distribution shifts and consider retraining.
          </p>
        )}
      </Panel>
    </div>
  )
}

export default MonitoringTab
