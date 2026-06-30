/**
 * Performance Tab — model metrics + XGBoost feature importance.
 * Data: GET /metrics/performance, GET /features/importance.
 */
import React, { useEffect, useState } from 'react'
import { TrendingUp, BarChart3 } from 'lucide-react'
import { getMLOpsEndpoint } from '../../../services/apiUrl'
import { SectionHeader, Panel, StatStrip, LoadingState, ErrorState } from '../../../components/ui'

interface Metrics {
  auc: number | null; precision: number | null; recall: number | null; f1_score: number | null
  accuracy: number | null; training_samples: number | null; test_samples: number | null; feature_count: number | null
}
interface ImportanceItem { feature: string; description: string; gain: number; weight: number; cover: number }

const pct = (v: number | null) => (v == null || Number.isNaN(v) ? '—' : `${(v * 100).toFixed(1)}%`)
const num = (v: number | null) => (v == null || Number.isNaN(v) ? '—' : v.toLocaleString())
const fixed = (v: number | null, d = 3) => (v == null || Number.isNaN(v) ? '—' : v.toFixed(d))

const PerformanceTab: React.FC<{ selectedVersion?: string }> = ({ selectedVersion }) => {
  const [metrics, setMetrics] = useState<Metrics | null>(null)
  const [importance, setImportance] = useState<ImportanceItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const withModel = (p: string) => (selectedVersion ? `${p}${p.includes('?') ? '&' : '?'}model_version=${encodeURIComponent(selectedVersion)}` : p)

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      setLoading(true); setError(null)
      try {
        const [perfRes, impRes] = await Promise.all([
          fetch(getMLOpsEndpoint(withModel('/metrics/performance'))),
          fetch(getMLOpsEndpoint(withModel('/features/importance'))),
        ])
        if (!perfRes.ok) throw new Error(`Performance request failed (${perfRes.status})`)
        const m = (await perfRes.json()).metrics || {}
        const imp = impRes.ok ? await impRes.json() : { importance: [] }
        if (!cancelled) {
          setMetrics({
            auc: m.auc ?? null, precision: m.precision ?? null, recall: m.recall ?? null,
            f1_score: m.f1_score ?? null, accuracy: m.accuracy ?? null,
            training_samples: m.training_samples ?? null, test_samples: m.test_samples ?? null,
            feature_count: m.feature_count ?? null,
          })
          setImportance(Array.isArray(imp.importance) ? imp.importance : [])
        }
      } catch (e) { if (!cancelled) setError(e instanceof Error ? e.message : 'Failed to load performance') }
      finally { if (!cancelled) setLoading(false) }
    })()
    return () => { cancelled = true }
  }, [selectedVersion])

  if (loading) return <LoadingState label="Loading performance metrics…" />
  if (error || !metrics) return <ErrorState title="Unable to load performance metrics" detail={error} />

  const maxGain = importance.reduce((mx, it) => Math.max(mx, it.gain), 0)

  return (
    <div className="space-y-5">
      <Panel>
        <SectionHeader title="Key Performance Metrics" subtitle="XGBoost evaluation from the latest training run" icon={<TrendingUp className="w-4 h-4" />} />
        <StatStrip items={[
          { label: 'AUC-ROC', value: fixed(metrics.auc) },
          { label: 'Accuracy', value: pct(metrics.accuracy) },
          { label: 'F1 Score', value: pct(metrics.f1_score) },
          { label: 'Precision', value: pct(metrics.precision) },
          { label: 'Recall', value: pct(metrics.recall) },
          { label: 'Features', value: num(metrics.feature_count) },
          { label: 'Train Samples', value: num(metrics.training_samples) },
          { label: 'Test Samples', value: num(metrics.test_samples) },
        ]} />
      </Panel>

      <Panel>
        <SectionHeader title="Feature Importance" subtitle="XGBoost gain importance per feature (top 15)" icon={<BarChart3 className="w-4 h-4" />} />
        {importance.length === 0 ? (
          <p className="text-[12px] text-[#5C5C5C] py-4 text-center">No feature importance — XGBoost model not loaded.</p>
        ) : (
          <ul className="space-y-2.5">
            {importance.slice(0, 15).map(f => (
              <li key={f.feature}>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-[11px] font-semibold text-[#0B1F33] truncate">{f.description || f.feature}</span>
                  <span className="text-[10px] font-mono text-[#5C5C5C] flex-shrink-0 ml-2">gain {f.gain.toFixed(2)}</span>
                </div>
                <div className="w-full h-3.5 bg-slate-100 rounded-sm overflow-hidden border border-[#D0D7DE]" role="img" aria-label={`${f.description || f.feature} gain ${f.gain.toFixed(2)}`}>
                  <div className="h-full bg-[#005EA2]" style={{ width: maxGain > 0 ? `${(f.gain / maxGain) * 100}%` : '0%' }} />
                </div>
                <div className="text-[10px] text-[#5C5C5C] mt-0.5 font-mono">weight {f.weight.toFixed(0)} · cover {f.cover.toFixed(2)}</div>
              </li>
            ))}
          </ul>
        )}
      </Panel>
    </div>
  )
}

export default PerformanceTab
