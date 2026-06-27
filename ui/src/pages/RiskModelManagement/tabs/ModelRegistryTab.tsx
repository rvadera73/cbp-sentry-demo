/**
 * Model Registry Tab - Version Management & Approval Workflow
 *
 * 100% API-driven. No hardcoded lineage, metrics, or approval/voter data.
 *
 * Data sources:
 * - GET  /models                     → registered versions (lineage, metrics, approvals)
 * - POST /models/{version}/approve   → cast an approval/reject vote
 * - POST /models/{version}/promote   → promote to production (requires 3-vote quorum)
 */

import React, { useEffect, useState } from 'react'
import { CheckCircle2, Users, ChevronDown, ChevronRight, Loader, AlertCircle } from 'lucide-react'
import { CBPColors, CBPTypography, CBPComponents, getStatusBadgeClass } from '../../../styles/CBPDesignSystem'
import { getMLOpsEndpoint } from '../../../services/apiUrl'

interface ApprovalVote {
  voter_id: string
  vote: string
  comment?: string | null
  timestamp?: string | null
}

interface ApprovalSummary {
  model_version: string
  approve_count: number
  reject_count: number
  quorum_required: number
  quorum_met: boolean
  votes: ApprovalVote[]
}

interface ModelVersion {
  // MLflow shape
  name?: string
  version?: string
  status?: string | null
  is_production?: boolean
  aliases?: string[]
  description?: string | null
  framework?: string | null
  creation_timestamp?: number | null
  metrics?: Record<string, number>
  approvals?: ApprovalSummary
  // PostgreSQL shape
  model_id?: string
  model_name?: string
  created_at?: string | null
  deployed_at?: string | null
  metadata?: Record<string, any> | null
}

// Reconcile the two backend shapes into one view model.
const normalize = (m: ModelVersion) => {
  const version = String(m.version ?? m.model_id ?? '')
  const status = (m.status || (m.is_production ? 'production' : 'registered') || 'registered').toString()
  const metrics = m.metrics || (m.metadata?.metrics as Record<string, number> | undefined) || {}
  const created = m.creation_timestamp
    ? new Date(m.creation_timestamp).toLocaleDateString()
    : m.created_at
    ? new Date(m.created_at).toLocaleDateString()
    : '—'
  return {
    version,
    status,
    statusLabel: status.toUpperCase(),
    framework: m.framework || (m.metadata?.framework as string | undefined) || '—',
    description: m.description || m.model_name || m.name || version,
    created,
    isProduction: m.is_production ?? status === 'production',
    metrics,
    approvals: m.approvals || null,
  }
}

const ModelRegistryTab: React.FC = () => {
  const [versions, setVersions] = useState<ModelVersion[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [expanded, setExpanded] = useState<string | null>(null)
  const [actionLoading, setActionLoading] = useState<string | null>(null)
  const [actionMessage, setActionMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  const loadModels = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(getMLOpsEndpoint('/models'))
      if (!res.ok) throw new Error(`Models request failed (${res.status})`)
      const data = await res.json()
      setVersions(Array.isArray(data.versions) ? data.versions : [])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load models')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadModels()
  }, [])

  const flashMessage = (type: 'success' | 'error', text: string) => {
    setActionMessage({ type, text })
    setTimeout(() => setActionMessage(null), 3500)
  }

  const handleVote = async (version: string, approve: boolean) => {
    setActionLoading(`vote-${version}`)
    try {
      const res = await fetch(getMLOpsEndpoint(`/models/${version}/approve`), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ voter_id: 'current_user', vote: approve ? 'approve' : 'reject' }),
      })
      if (!res.ok) throw new Error(`Vote failed (${res.status})`)
      flashMessage('success', `Vote recorded for v${version}`)
      await loadModels()
    } catch (err) {
      flashMessage('error', err instanceof Error ? err.message : 'Failed to submit vote')
    } finally {
      setActionLoading(null)
    }
  }

  const handlePromote = async (version: string) => {
    setActionLoading(`promote-${version}`)
    try {
      const res = await fetch(getMLOpsEndpoint(`/models/${version}/promote`), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ requested_by: 'current_user' }),
      })
      if (!res.ok) {
        const detail = await res.json().catch(() => null)
        throw new Error(detail?.detail || `Promote failed (${res.status})`)
      }
      flashMessage('success', `Model v${version} promoted to production`)
      await loadModels()
    } catch (err) {
      flashMessage('error', err instanceof Error ? err.message : 'Failed to promote model')
    } finally {
      setActionLoading(null)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <Loader className="w-8 h-8 animate-spin text-[#005EA2] mx-auto" />
          <p className="mt-2 text-slate-600">Loading model registry from /models…</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-sm p-6 flex items-start gap-3">
        <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
        <div>
          <p className="font-semibold text-red-900">Unable to load model registry</p>
          <p className="text-sm text-red-700 mt-1">{error}</p>
        </div>
      </div>
    )
  }

  const lineage = versions.map(normalize)

  return (
    <div className="space-y-8">
      {actionMessage && (
        <div className={`p-4 rounded-sm border-l-4 ${actionMessage.type === 'success' ? 'bg-green-50 border-green-400' : 'bg-red-50 border-red-400'}`}>
          <p className={`text-sm font-semibold ${actionMessage.type === 'success' ? 'text-green-900' : 'text-red-900'}`}>
            {actionMessage.text}
          </p>
        </div>
      )}

      {/* Model Lineage */}
      <div className="border border-[#D0D7DE] bg-white rounded-sm p-6">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-8 h-8 rounded-full flex items-center justify-center text-white text-[11px] font-bold" style={{ backgroundColor: CBPColors.primary }}>
            1
          </div>
          <div>
            <h3 className={`text-sm font-bold ${CBPTypography.label}`}>Model Lineage</h3>
            <p className={`text-[11px] ${CBPTypography.small} mt-0.5`}>Registered version progression</p>
          </div>
        </div>

        {lineage.length === 0 ? (
          <div className="text-center py-8 text-slate-500"><p>No registered model versions found.</p></div>
        ) : (
          <div className="flex items-center gap-2 overflow-x-auto pb-4 px-4 py-3 bg-slate-50 rounded-sm border border-slate-200">
            {lineage.map((item, idx) => (
              <div key={item.version} className="flex items-center gap-2 flex-shrink-0">
                <div className="text-center">
                  <div className={`text-[10px] font-bold uppercase tracking-wide ${CBPTypography.tableCaption} mb-1`}>
                    {item.statusLabel}
                  </div>
                  <div className={`px-3 py-1.5 rounded text-[11px] font-mono font-semibold ${getStatusBadgeClass(item.statusLabel)}`}>
                    v{item.version}
                  </div>
                  <div className={`text-[10px] ${CBPTypography.small} mt-1`}>{item.framework}</div>
                </div>
                {idx < lineage.length - 1 && <ChevronRight className="w-4 h-4 text-slate-400 flex-shrink-0 mx-1" />}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Version Cards */}
      <div className="space-y-4">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-8 h-8 rounded-full flex items-center justify-center text-white text-[11px] font-bold" style={{ backgroundColor: CBPColors.primary }}>
            2
          </div>
          <h3 className={`text-sm font-bold ${CBPTypography.label}`}>Registered Versions</h3>
        </div>

        {lineage.map((version) => {
          const approvals = version.approvals
          const isExpanded = expanded === version.version
          const metricEntries = Object.entries(version.metrics)

          return (
            <div
              key={version.version}
              className="border-l-4 bg-white rounded-sm transition-all overflow-hidden"
              style={{ borderColor: version.isProduction ? '#10B981' : version.status === 'staging' ? '#F59E0B' : '#94A3B8' }}
            >
              <button
                onClick={() => setExpanded(isExpanded ? null : version.version)}
                className="w-full p-4 hover:bg-slate-50 transition-colors flex items-start justify-between"
              >
                <div className="flex-1 text-left">
                  <div className="flex items-center gap-3 mb-2">
                    <h4 className={`text-sm font-bold ${CBPTypography.label}`}>v{version.version}</h4>
                    <span className={getStatusBadgeClass(version.statusLabel)}>{version.statusLabel}</span>
                    {version.isProduction && (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-green-100 text-green-700 text-[10px] font-semibold">
                        <CheckCircle2 className="w-3 h-3" /> PRODUCTION
                      </span>
                    )}
                  </div>
                  <p className={`text-[11px] ${CBPTypography.body}`}>{version.description}</p>
                  <p className={`text-[10px] ${CBPTypography.small} mt-1`}>
                    Framework: {version.framework} · Created: {version.created}
                  </p>
                </div>
                <div className="text-slate-400">
                  {isExpanded ? <ChevronDown className="w-5 h-5" /> : <ChevronRight className="w-5 h-5" />}
                </div>
              </button>

              {isExpanded && (
                <>
                  <div className="border-t border-[#D0D7DE] px-4 py-4 bg-slate-50 space-y-4">
                    {metricEntries.length > 0 && (
                      <div>
                        <p className={`text-[10px] font-bold uppercase tracking-wide ${CBPTypography.tableCaption} mb-3`}>Performance Metrics</p>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                          {metricEntries.map(([key, value]) => (
                            <div key={key}>
                              <div className={`text-[10px] uppercase tracking-wide ${CBPTypography.tableCaption}`}>{key.replace(/_/g, ' ')}</div>
                              <div className="text-lg font-bold text-slate-900 mt-1">
                                {typeof value === 'number' ? value.toFixed(3) : String(value)}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    <div>
                      <p className={`text-[10px] font-bold uppercase tracking-wide ${CBPTypography.tableCaption} mb-3 flex items-center gap-2`}>
                        <Users className="w-3.5 h-3.5" /> Approval Workflow
                      </p>
                      {approvals ? (
                        <div className={`p-3 rounded-sm border-l-4 ${approvals.quorum_met ? 'bg-green-50 border-green-400' : 'bg-amber-50 border-amber-400'}`}>
                          <div className="flex items-center justify-between mb-3">
                            <div>
                              <p className={`text-sm font-bold ${approvals.quorum_met ? 'text-green-900' : 'text-amber-900'}`}>
                                {approvals.approve_count}/{approvals.quorum_required} approve votes
                                {approvals.reject_count > 0 ? ` · ${approvals.reject_count} reject` : ''}
                              </p>
                              <p className={`text-[10px] mt-1 ${approvals.quorum_met ? 'text-green-700' : 'text-amber-700'}`}>
                                {approvals.quorum_met ? 'Quorum met — ready to promote' : 'Waiting for votes'}
                              </p>
                            </div>
                            {approvals.quorum_met && <CheckCircle2 className="w-5 h-5 text-green-600 flex-shrink-0" />}
                          </div>
                          {approvals.votes.length > 0 ? (
                            <div className="space-y-2">
                              {approvals.votes.map((voter, idx) => (
                                <div key={`${voter.voter_id}-${idx}`} className="flex items-center gap-2 text-[10px]">
                                  <span className={`inline-block w-2 h-2 rounded-full ${voter.vote === 'approve' ? 'bg-green-600' : voter.vote === 'reject' ? 'bg-red-600' : 'bg-slate-400'}`} />
                                  <span className="font-semibold text-slate-900 min-w-[120px]">{voter.voter_id}</span>
                                  <span className={voter.vote === 'approve' ? 'text-green-700' : voter.vote === 'reject' ? 'text-red-700' : 'text-slate-500'}>
                                    {voter.vote ? voter.vote.toUpperCase() : 'PENDING'}
                                  </span>
                                  {voter.timestamp && (
                                    <span className="text-slate-500 ml-auto">{new Date(voter.timestamp).toLocaleDateString()}</span>
                                  )}
                                </div>
                              ))}
                            </div>
                          ) : (
                            <p className="text-[10px] text-slate-500">No votes cast yet.</p>
                          )}
                        </div>
                      ) : (
                        <p className="text-[11px] text-slate-500">No approval data available for this version.</p>
                      )}
                    </div>
                  </div>

                  <div className="border-t border-[#D0D7DE] px-4 py-3 bg-white flex gap-2 flex-wrap">
                    <button
                      onClick={() => handleVote(version.version, true)}
                      disabled={actionLoading === `vote-${version.version}`}
                      className={`${CBPComponents.buttonSecondary} disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2`}
                    >
                      {actionLoading === `vote-${version.version}` && <Loader className="w-3 h-3 animate-spin" />}
                      Approve
                    </button>
                    <button
                      onClick={() => handleVote(version.version, false)}
                      disabled={actionLoading === `vote-${version.version}`}
                      className={`${CBPComponents.buttonSecondary} disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2`}
                    >
                      Reject
                    </button>
                    {!version.isProduction && (
                      <button
                        onClick={() => handlePromote(version.version)}
                        disabled={actionLoading === `promote-${version.version}` || !approvals?.quorum_met}
                        title={!approvals?.quorum_met ? 'Requires 3-vote approval quorum' : undefined}
                        className={`${CBPComponents.buttonPrimary} disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2`}
                      >
                        {actionLoading === `promote-${version.version}` && <Loader className="w-3 h-3 animate-spin" />}
                        Promote to Production
                      </button>
                    )}
                  </div>
                </>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

export default ModelRegistryTab
