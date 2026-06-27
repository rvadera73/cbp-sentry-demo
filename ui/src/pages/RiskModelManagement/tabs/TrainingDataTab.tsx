/**
 * Training & Data Tab - Training Runs & Dataset Stats
 *
 * 100% API-driven. No hardcoded feature audit, reference-data freshness,
 * dataset hashes, or sample counts.
 *
 * Data source:
 * - GET /jobs → training run history with status, model type, metrics, MLflow run id
 */

import React, { useEffect, useState } from 'react'
import { AlertTriangle, Loader } from 'lucide-react'
import { CBPColors, CBPTypography } from '../../../styles/CBPDesignSystem'
import { getMLOpsEndpoint } from '../../../services/apiUrl'

interface TrainingJob {
  job_id: string
  model_type?: string
  notes?: string | null
  status: string
  started_at?: string | null
  completed_at?: string | null
  mlflow_run_id?: string | null
  model_version?: string | number | null
  metrics?: Record<string, any>
}

const fmtMetric = (value: any, digits = 3): string => {
  const n = typeof value === 'number' ? value : Number(value)
  return Number.isFinite(n) ? n.toFixed(digits) : '—'
}

const TrainingDataTab: React.FC = () => {
  const [jobs, setJobs] = useState<TrainingJob[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    const load = async () => {
      setLoading(true)
      setError(null)
      try {
        const res = await fetch(getMLOpsEndpoint('/jobs'))
        if (!res.ok) throw new Error(`Jobs request failed (${res.status})`)
        const data = await res.json()
        if (!cancelled) setJobs(Array.isArray(data.jobs) ? data.jobs : [])
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Failed to load training jobs')
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
          <p className="mt-2 text-slate-600">Loading training jobs from /jobs…</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-sm p-6 flex items-start gap-3">
        <AlertTriangle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
        <div>
          <p className="font-semibold text-red-900">Unable to load training jobs</p>
          <p className="text-sm text-red-700 mt-1">{error}</p>
        </div>
      </div>
    )
  }

  // Derive dataset summary from the most recent completed job's metrics (real data).
  const latestCompleted = jobs.find(j => j.status === 'completed' && j.metrics && Object.keys(j.metrics).length > 0)
  const ds = latestCompleted?.metrics || {}

  return (
    <div className="space-y-8">
      {/* Dataset Summary (from latest completed run) */}
      {latestCompleted && (
        <div className="border border-[#D0D7DE] bg-white rounded-sm p-6">
          <div className="flex items-center gap-3 mb-6">
            <div className="w-8 h-8 rounded-full flex items-center justify-center text-white text-[11px] font-bold" style={{ backgroundColor: CBPColors.primary }}>
              1
            </div>
            <div>
              <h3 className={`text-sm font-bold ${CBPTypography.label}`}>Latest Training Dataset</h3>
              <p className={`text-[11px] ${CBPTypography.small} mt-0.5`}>From job {latestCompleted.job_id}</p>
            </div>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            <div className="p-4 bg-slate-50 rounded-sm border border-[#D0D7DE]">
              <div className={`text-[10px] font-bold uppercase tracking-wide ${CBPTypography.tableCaption}`}>Training Samples</div>
              <div className="text-3xl font-bold text-slate-900 mt-2">
                {Number.isFinite(Number(ds.training_samples)) ? Number(ds.training_samples).toLocaleString() : '—'}
              </div>
            </div>
            <div className="p-4 bg-slate-50 rounded-sm border border-[#D0D7DE]">
              <div className={`text-[10px] font-bold uppercase tracking-wide ${CBPTypography.tableCaption}`}>Test Samples</div>
              <div className="text-3xl font-bold text-slate-900 mt-2">
                {Number.isFinite(Number(ds.test_samples)) ? Number(ds.test_samples).toLocaleString() : '—'}
              </div>
            </div>
            <div className="p-4 bg-slate-50 rounded-sm border border-[#D0D7DE]">
              <div className={`text-[10px] font-bold uppercase tracking-wide ${CBPTypography.tableCaption}`}>Feature Count</div>
              <div className="text-3xl font-bold text-slate-900 mt-2">
                {Number.isFinite(Number(ds.feature_count)) ? Number(ds.feature_count).toLocaleString() : '—'}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Training Run History */}
      <div className="border border-[#D0D7DE] bg-white rounded-sm p-6">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-8 h-8 rounded-full flex items-center justify-center text-white text-[11px] font-bold" style={{ backgroundColor: CBPColors.primary }}>
            {latestCompleted ? 2 : 1}
          </div>
          <div>
            <h3 className={`text-sm font-bold ${CBPTypography.label}`}>Training Run History</h3>
            <p className={`text-[11px] ${CBPTypography.small} mt-0.5`}>All training jobs from the pipeline</p>
          </div>
        </div>

        <div className="space-y-4">
          {jobs.length === 0 ? (
            <div className="text-center py-8 text-slate-500"><p>No training jobs found.</p></div>
          ) : (
            jobs.map((run) => {
              const start = run.started_at ? new Date(run.started_at) : null
              const end = run.completed_at ? new Date(run.completed_at) : null
              const durationMins = start && end ? Math.max(0, Math.round((end.getTime() - start.getTime()) / 60000)) : null
              const m = run.metrics || {}
              const statusClass =
                run.status === 'completed' ? 'bg-green-100 text-green-700'
                : run.status === 'failed' ? 'bg-red-100 text-red-700'
                : run.status === 'running' ? 'bg-blue-100 text-blue-700'
                : 'bg-yellow-100 text-yellow-700'

              return (
                <div key={run.job_id} className="border border-[#D0D7DE] rounded-sm p-4 bg-slate-50">
                  <div className="flex items-start justify-between mb-3">
                    <div>
                      <h4 className={`text-sm font-bold ${CBPTypography.label}`}>{run.job_id}</h4>
                      <p className={`text-[11px] ${CBPTypography.body} mt-1`}>
                        {run.model_type || 'unknown'} model
                        {run.mlflow_run_id ? ` · MLflow ${run.mlflow_run_id.substring(0, 8)}…` : ''}
                        {run.notes ? ` · ${run.notes}` : ''}
                      </p>
                    </div>
                    <span className={`inline-flex items-center px-2 py-1 rounded text-xs font-semibold flex-shrink-0 ${statusClass}`}>
                      {run.status.toUpperCase()}
                    </span>
                  </div>

                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4">
                    <div>
                      <div className={`text-[10px] font-bold uppercase tracking-wide ${CBPTypography.tableCaption}`}>Model Version</div>
                      <div className="text-sm font-semibold text-slate-900 mt-1">{run.model_version ? `v${run.model_version}` : '—'}</div>
                    </div>
                    <div>
                      <div className={`text-[10px] font-bold uppercase tracking-wide ${CBPTypography.tableCaption}`}>Started</div>
                      <div className="text-sm font-semibold text-slate-900 mt-1">{start ? start.toLocaleString() : '—'}</div>
                    </div>
                    <div>
                      <div className={`text-[10px] font-bold uppercase tracking-wide ${CBPTypography.tableCaption}`}>Training Samples</div>
                      <div className="text-sm font-semibold text-slate-900 mt-1">
                        {Number.isFinite(Number(m.training_samples)) ? Number(m.training_samples).toLocaleString() : '—'}
                      </div>
                    </div>
                    <div>
                      <div className={`text-[10px] font-bold uppercase tracking-wide ${CBPTypography.tableCaption}`}>Duration</div>
                      <div className="text-sm font-semibold text-slate-900 mt-1">{durationMins !== null ? `${durationMins} min` : '—'}</div>
                    </div>
                  </div>

                  {m && Object.keys(m).length > 0 && (
                    <div className="mt-3 pt-3 border-t border-[#D0D7DE]">
                      <p className={`text-[11px] ${CBPTypography.body}`}>
                        <strong>Metrics:</strong> AUC={fmtMetric(m.auc ?? m.xgb_auc)} · Precision={fmtMetric(m.precision ?? m.xgb_precision)} · Recall={fmtMetric(m.recall ?? m.xgb_recall)} · F1={fmtMetric(m.f1 ?? m.f1_score)} · Test Samples={Number.isFinite(Number(m.test_samples)) ? Number(m.test_samples).toLocaleString() : '—'}
                      </p>
                    </div>
                  )}
                </div>
              )
            })
          )}
        </div>
      </div>
    </div>
  )
}

export default TrainingDataTab
