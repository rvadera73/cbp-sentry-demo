/**
 * Model Registry Tab — version lineage, metrics, and approval workflow.
 * 100% API-driven (cbp-risk-engine /models, /models/{v}/approve|promote).
 */
import React, { useEffect, useState } from 'react'
import { CheckCircle2, ChevronRight, GitBranch } from 'lucide-react'
import { getMLOpsEndpoint } from '../../../services/apiUrl'
import { SectionHeader, Panel, StatusPill, LoadingState, ErrorState } from '../../../components/ui'

interface ModelVersion {
  name?: string; version?: string; status?: string | null; is_production?: boolean
  framework?: string | null; description?: string | null
  creation_timestamp?: number | null; created_at?: string | null
  metrics?: Record<string, number>; model_id?: string; model_name?: string
  maturity_pct?: number | null; metadata?: Record<string, any> | null
  approval?: any; approvals?: any
}

const normalizeApproval = (m: ModelVersion) => {
  const a = m.approval || m.approvals
  if (!a) return null
  const approved = a.approved_count ?? a.approve_count ?? 0
  const required = a.required_approvers ?? a.quorum_required ?? 3
  const votes = a.approval_votes || a.votes || []
  return { approved, required, met: approved >= required, votes }
}

const normalize = (m: ModelVersion) => {
  const meta = m.metadata || {}
  const status = (m.status || (m.is_production ? 'production' : 'registered') || 'registered').toString()
  const created = m.creation_timestamp
    ? new Date(m.creation_timestamp).toLocaleDateString()
    : m.created_at ? new Date(m.created_at).toLocaleDateString() : '—'
  return {
    version: String(m.version ?? m.model_id ?? ''),
    status,
    isProduction: m.is_production ?? status === 'production',
    framework: m.framework || (meta.framework as string) || '—',
    description: m.description || (meta.description as string) || m.model_name || m.name || '',
    created,
    maturity: m.maturity_pct ?? (meta.maturity_pct as number) ?? null,
    metrics: m.metrics || {},
    approval: normalizeApproval(m),
  }
}

const accentFor = (status: string) =>
  status === 'production' ? '#10B981' : status === 'candidate' ? '#2563EB' : status === 'deprecated' ? '#DC2626' : '#94A3B8'

const fmtMetric = (v: any) => (typeof v === 'number' ? (v < 1 ? v.toFixed(3) : v.toLocaleString()) : String(v))
const KEY_METRICS = ['auc', 'f1_score', 'accuracy', 'precision', 'recall']

const ModelRegistryTab: React.FC = () => {
  const [versions, setVersions] = useState<ModelVersion[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState<string | null>(null)
  const [msg, setMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  const loadModels = async () => {
    setLoading(true); setError(null)
    try {
      const res = await fetch(getMLOpsEndpoint('/models'))
      if (!res.ok) throw new Error(`Models request failed (${res.status})`)
      const data = await res.json()
      setVersions(Array.isArray(data.versions) ? data.versions : [])
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load models')
    } finally { setLoading(false) }
  }
  useEffect(() => { loadModels() }, [])

  const flash = (type: 'success' | 'error', text: string) => { setMsg({ type, text }); setTimeout(() => setMsg(null), 3500) }

  const vote = async (version: string, approve: boolean) => {
    setBusy(`vote-${version}`)
    try {
      const res = await fetch(getMLOpsEndpoint(`/models/${version}/approve`), {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ voter_id: 'current_user', vote: approve ? 'approve' : 'reject' }),
      })
      if (!res.ok) throw new Error(`Vote failed (${res.status})`)
      flash('success', `Vote recorded for v${version}`); await loadModels()
    } catch (e) { flash('error', e instanceof Error ? e.message : 'Vote failed') } finally { setBusy(null) }
  }
  const promote = async (version: string) => {
    setBusy(`promote-${version}`)
    try {
      const res = await fetch(getMLOpsEndpoint(`/models/${version}/promote`), {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ requested_by: 'current_user' }),
      })
      if (!res.ok) { const d = await res.json().catch(() => null); throw new Error(d?.detail || `Promote failed (${res.status})`) }
      flash('success', `v${version} promoted to production`); await loadModels()
    } catch (e) { flash('error', e instanceof Error ? e.message : 'Promote failed') } finally { setBusy(null) }
  }

  if (loading) return <LoadingState label="Loading model registry…" />
  if (error) return <ErrorState title="Unable to load model registry" detail={error} />

  const lineage = versions.map(normalize)
  // Lineage order: production first, then candidate, then deprecated/other.
  const order = (s: string) => (s === 'production' ? 0 : s === 'staging' ? 1 : s === 'candidate' ? 2 : 3)
  const sorted = [...lineage].sort((a, b) => order(a.status) - order(b.status))

  return (
    <div className="space-y-5">
      {msg && (
        <div role="status" className={`px-3 py-2 rounded-sm border text-[12px] font-semibold ${msg.type === 'success' ? 'bg-green-50 border-green-300 text-green-900' : 'bg-red-50 border-red-300 text-red-900'}`}>
          {msg.text}
        </div>
      )}

      {/* Lineage strip */}
      <Panel>
        <SectionHeader title="Model Lineage" subtitle="Registered version progression" icon={<GitBranch className="w-4 h-4" />} />
        {sorted.length === 0 ? (
          <p className="text-[12px] text-[#5C5C5C]">No registered versions.</p>
        ) : (
          <ol className="flex flex-wrap items-center gap-2">
            {sorted.map((v, i) => (
              <li key={v.version} className="flex items-center gap-2">
                <div className="border rounded-sm px-3 py-1.5 bg-slate-50" style={{ borderColor: accentFor(v.status) }}>
                  <div className="text-[9px] font-bold uppercase tracking-wide text-[#5C5C5C]">{v.status}</div>
                  <div className="text-[12px] font-mono font-bold text-[#0B1F33]">v{v.version}</div>
                  <div className="text-[10px] text-[#5C5C5C]">{v.framework}</div>
                </div>
                {i < sorted.length - 1 && <ChevronRight className="w-4 h-4 text-slate-400" aria-hidden />}
              </li>
            ))}
          </ol>
        )}
      </Panel>

      {/* Version cards */}
      <div>
        <SectionHeader title="Registered Versions" subtitle={`${sorted.length} version${sorted.length === 1 ? '' : 's'} in the registry`} />
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {sorted.map(v => {
            const metricEntries = KEY_METRICS.filter(k => v.metrics[k] != null).map(k => [k, v.metrics[k]] as const)
            const a = v.approval
            return (
              <section key={v.version} className="bg-white border border-[#D0D7DE] rounded-sm border-l-4 flex flex-col" style={{ borderLeftColor: accentFor(v.status) }}>
                <div className="p-3 border-b border-slate-100">
                  <div className="flex items-center justify-between gap-2">
                    <h4 className="text-[13px] font-mono font-bold text-[#0B1F33]">v{v.version}</h4>
                    <StatusPill status={v.status} />
                  </div>
                  <p className="text-[11px] text-[#5C5C5C] mt-1 line-clamp-2">{v.description}</p>
                  <p className="text-[10px] text-[#5C5C5C] mt-1">
                    {v.framework}{v.maturity != null ? ` · ${v.maturity}% maturity` : ''} · {v.created}
                  </p>
                </div>

                {metricEntries.length > 0 && (
                  <div className="grid grid-cols-3 gap-px bg-slate-100 border-b border-slate-100">
                    {metricEntries.slice(0, 3).map(([k, val]) => (
                      <div key={k} className="bg-white p-2 text-center">
                        <div className="text-[9px] font-bold uppercase tracking-wide text-[#5C5C5C]">{k.replace('_', ' ')}</div>
                        <div className="text-[13px] font-mono font-black text-[#0B1F33]">{fmtMetric(val)}</div>
                      </div>
                    ))}
                  </div>
                )}

                <div className="p-3 mt-auto">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-[10px] font-bold uppercase tracking-wide text-[#5C5C5C]">Approvals</span>
                    {a ? (
                      <span className={`text-[11px] font-bold ${a.met ? 'text-green-700' : 'text-amber-700'}`}>
                        {a.approved}/{a.required}{a.met && <CheckCircle2 className="inline w-3.5 h-3.5 ml-1" aria-label="quorum met" />}
                      </span>
                    ) : <span className="text-[11px] text-[#5C5C5C]">none</span>}
                  </div>
                  <div className="flex gap-1.5">
                    <button type="button" onClick={() => vote(v.version, true)} disabled={busy != null}
                      className="flex-1 px-2 py-1.5 border border-[#D0D7DE] rounded text-[11px] font-semibold text-[#0B1F33] hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-[#005EA2] disabled:opacity-50">
                      {busy === `vote-${v.version}` ? '…' : 'Approve'}
                    </button>
                    <button type="button" onClick={() => vote(v.version, false)} disabled={busy != null}
                      className="flex-1 px-2 py-1.5 border border-[#D0D7DE] rounded text-[11px] font-semibold text-[#0B1F33] hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-[#005EA2] disabled:opacity-50">
                      Reject
                    </button>
                    {!v.isProduction && (
                      <button type="button" onClick={() => promote(v.version)} disabled={busy != null || !a?.met}
                        title={!a?.met ? 'Requires approval quorum' : 'Promote to production'}
                        className="flex-1 px-2 py-1.5 bg-[#005EA2] text-white rounded text-[11px] font-semibold hover:bg-[#0b4f86] focus:outline-none focus:ring-2 focus:ring-offset-1 focus:ring-[#005EA2] disabled:opacity-50">
                        {busy === `promote-${v.version}` ? '…' : 'Promote'}
                      </button>
                    )}
                  </div>
                </div>
              </section>
            )
          })}
        </div>
      </div>
    </div>
  )
}

export default ModelRegistryTab
