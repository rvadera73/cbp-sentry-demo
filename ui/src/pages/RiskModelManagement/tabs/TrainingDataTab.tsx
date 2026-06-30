/**
 * Training & Data Tab — training run history + dataset stats.
 * Data: GET /jobs (risk_scoring.model_training_runs).
 */
import React, { useEffect, useState } from 'react'
import { Database, Activity } from 'lucide-react'
import { getMLOpsEndpoint } from '../../../services/apiUrl'
import { SectionHeader, Panel, StatStrip, StatusPill, DataTable, LoadingState, ErrorState, Column } from '../../../components/ui'

interface TrainingJob {
  job_id: string; model_type?: string; status: string
  started_at?: string | null; completed_at?: string | null
  mlflow_run_id?: string | null; model_version?: string | number | null
  training_records?: number | null; test_records?: number | null
  metrics?: Record<string, any>
}

const n = (v: any) => (Number.isFinite(Number(v)) ? Number(v).toLocaleString() : '—')
const f = (v: any, d = 3) => { const x = Number(v); return Number.isFinite(x) ? x.toFixed(d) : '—' }

const TrainingDataTab: React.FC<{ selectedVersion?: string }> = ({ selectedVersion }) => {
  const [jobs, setJobs] = useState<TrainingJob[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const withModel = (p: string) => (selectedVersion ? `${p}${p.includes('?') ? '&' : '?'}model_version=${encodeURIComponent(selectedVersion)}` : p)

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      setLoading(true); setError(null)
      try {
        const res = await fetch(getMLOpsEndpoint(withModel('/jobs')))
        if (!res.ok) throw new Error(`Jobs request failed (${res.status})`)
        const data = await res.json()
        if (!cancelled) setJobs(Array.isArray(data.jobs) ? data.jobs : [])
      } catch (e) { if (!cancelled) setError(e instanceof Error ? e.message : 'Failed to load training jobs') }
      finally { if (!cancelled) setLoading(false) }
    })()
    return () => { cancelled = true }
  }, [selectedVersion])

  if (loading) return <LoadingState label="Loading training jobs…" />
  if (error) return <ErrorState title="Unable to load training jobs" detail={error} />

  const latest = jobs.find(j => j.status === 'completed' && j.metrics && Object.keys(j.metrics).length > 0)
  const ds = latest?.metrics || {}

  const columns: Column[] = [
    { key: 'job_id', label: 'Job', mono: true, render: r => <span className="font-mono">{r.job_id}</span> },
    { key: 'model_type', label: 'Model', render: r => r.model_type || '—' },
    { key: 'status', label: 'Status', align: 'center', render: r => <StatusPill status={r.status} /> },
    { key: 'started_at', label: 'Started', render: r => (r.started_at ? new Date(r.started_at).toLocaleDateString() : '—') },
    { key: 'records', label: 'Train / Test', align: 'right', mono: true, render: r => `${n(r.training_records ?? r.metrics?.training_samples)} / ${n(r.test_records ?? r.metrics?.test_samples)}` },
    { key: 'auc', label: 'AUC', align: 'right', mono: true, render: r => f(r.metrics?.auc ?? r.metrics?.xgb_auc) },
    { key: 'f1', label: 'F1', align: 'right', mono: true, render: r => f(r.metrics?.f1 ?? r.metrics?.f1_score) },
  ]

  return (
    <div className="space-y-5">
      {latest && (
        <Panel>
          <SectionHeader title="Latest Training Dataset" subtitle={`From job ${latest.job_id}`} icon={<Database className="w-4 h-4" />} />
          <StatStrip items={[
            { label: 'Training Samples', value: n(ds.training_samples) },
            { label: 'Test Samples', value: n(ds.test_samples) },
            { label: 'Feature Count', value: n(ds.feature_count) },
          ]} />
        </Panel>
      )}

      <Panel>
        <SectionHeader title="Training Run History" subtitle="All training jobs from the pipeline" icon={<Activity className="w-4 h-4" />} />
        <DataTable columns={columns} rows={jobs} caption="Training run history" empty="No training jobs recorded yet." />
      </Panel>
    </div>
  )
}

export default TrainingDataTab
