/**
 * Overview Tab - Gate Progression & Exit Criteria
 *
 * 100% API-driven. No hardcoded gates, blockers, or exit criteria.
 *
 * Data sources:
 * - GET /metrics/gates      → gate progression, per-gate metric thresholds (exit criteria + blockers)
 * - GET /models/production  → active production model card (version, status, metrics)
 */

import React, { useEffect, useState } from 'react'
import { CheckCircle2, AlertCircle, ChevronRight, Lock, Loader } from 'lucide-react'
import { CBPColors, CBPTypography } from '../../../styles/CBPDesignSystem'
import { getMLOpsEndpoint } from '../../../services/apiUrl'

interface GateMetric {
  name: string
  measured_value: number
  threshold: number
  unit?: string | null
  passed: boolean
  description?: string | null
}

interface Gate {
  gate_id: number | string
  gate_name: string
  timeline_days?: number | null
  passed: boolean
  metrics: GateMetric[]
}

interface GatesResponse {
  days_since_award: number
  gates: Gate[]
}

// Extract a numeric metric from either the MLflow (model.metrics) or
// PostgreSQL (model.metadata) production-model shapes.
const readMetric = (model: any, keys: string[]): number | null => {
  const sources = [model?.metrics, model?.metadata?.metrics, model?.metadata].filter(Boolean)
  for (const source of sources) {
    for (const key of keys) {
      const value = source?.[key]
      if (typeof value === 'number' && !Number.isNaN(value)) return value
    }
  }
  return null
}

const OverviewTab: React.FC = () => {
  const [gatesData, setGatesData] = useState<GatesResponse | null>(null)
  const [model, setModel] = useState<any | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    const load = async () => {
      setLoading(true)
      setError(null)
      try {
        const [gatesRes, modelRes] = await Promise.all([
          fetch(getMLOpsEndpoint('/metrics/gates')),
          fetch(getMLOpsEndpoint('/models/production')),
        ])
        if (!gatesRes.ok) throw new Error(`Gate metrics request failed (${gatesRes.status})`)
        const gates: GatesResponse = await gatesRes.json()
        // Production model is optional (404 when none configured).
        const prodModel = modelRes.ok ? await modelRes.json() : null
        if (!cancelled) {
          setGatesData(gates)
          setModel(prodModel)
        }
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Failed to load overview data')
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
          <p className="mt-2 text-slate-600">Loading gate status from /metrics/gates…</p>
        </div>
      </div>
    )
  }

  if (error || !gatesData) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-sm p-4 flex items-start gap-3">
        <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
        <div>
          <p className="font-semibold text-red-900">Unable to load overview</p>
          <p className="text-sm text-red-700 mt-1">{error || 'No gate data returned by /metrics/gates'}</p>
        </div>
      </div>
    )
  }

  const gates = gatesData.gates || []
  const currentGate = gates.find(g => !g.passed) || gates[gates.length - 1] || null
  const criteria = currentGate?.metrics || []
  const metCount = criteria.filter(c => c.passed).length
  const totalCount = criteria.length
  const blockedCount = totalCount - metCount

  const auc = readMetric(model, ['auc', 'xgb_auc', 'auc_roc'])
  const f1 = readMetric(model, ['f1', 'f1_score', 'xgb_f1'])
  const modelName = model?.name || model?.model_name || model?.model_id || 'No production model'
  const modelVersion = model?.version ?? model?.model_id ?? 'unknown'
  const isProduction = model?.is_production ?? (model?.status === 'production')

  return (
    <div className="space-y-8">
      {/* Active Model Card */}
      <div className="rounded-sm p-4 border-l-4 bg-white" style={{ borderColor: CBPColors.primary }}>
        <div className="flex items-start justify-between mb-6">
          <div>
            <h3 className={`text-lg font-bold ${CBPTypography.label}`}>
              {modelName}{model ? ` v${modelVersion}` : ''}
            </h3>
            <p className={`text-sm ${CBPTypography.body} mt-2`}>
              {model ? (model.status || 'registered') : 'No production model configured'}
              {model?.framework ? ` · ${model.framework}` : ''}
            </p>
          </div>
          {model && (
            <div className={`inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold ${
              isProduction ? 'bg-green-100 text-green-700' : 'bg-amber-100 text-amber-700'
            }`}>
              <CheckCircle2 className="w-3.5 h-3.5" />
              {isProduction ? 'PRODUCTION' : (model.status || 'STAGING').toString().toUpperCase()}
            </div>
          )}
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
          <div>
            <div className={`text-xs font-bold uppercase tracking-wide ${CBPTypography.tableCaption}`}>AUC</div>
            <div className="text-2xl font-bold text-[#0B1F33] mt-2">
              {auc !== null ? auc.toFixed(3) : '—'}
            </div>
            <p className={`text-[10px] ${CBPTypography.small} mt-1`}>Discrimination ability</p>
          </div>
          <div>
            <div className={`text-xs font-bold uppercase tracking-wide ${CBPTypography.tableCaption}`}>F1 Score</div>
            <div className="text-2xl font-bold text-[#0B1F33] mt-2">
              {f1 !== null ? f1.toFixed(3) : '—'}
            </div>
            <p className={`text-[10px] ${CBPTypography.small} mt-1`}>Balanced performance</p>
          </div>
          <div>
            <div className={`text-xs font-bold uppercase tracking-wide ${CBPTypography.tableCaption}`}>Days Since Award</div>
            <div className="text-2xl font-bold text-[#0B1F33] mt-2">{gatesData.days_since_award}</div>
            <p className={`text-[10px] ${CBPTypography.small} mt-1`}>Program timeline</p>
          </div>
          <div>
            <div className={`text-xs font-bold uppercase tracking-wide ${CBPTypography.tableCaption}`}>Current Gate</div>
            <div className="text-2xl font-bold text-[#0B1F33] mt-2">
              {currentGate ? currentGate.gate_id : '—'}
            </div>
            <p className={`text-[10px] ${CBPTypography.small} mt-1`}>{currentGate?.gate_name || ''}</p>
          </div>
        </div>
      </div>

      {/* Gate Progression Timeline */}
      <div>
        <div className="flex items-center gap-3 mb-6">
          <div className="w-8 h-8 rounded-full flex items-center justify-center text-white text-[11px] font-bold flex-shrink-0" style={{ backgroundColor: CBPColors.primary }}>
            1
          </div>
          <div>
            <h3 className={`text-sm font-bold ${CBPTypography.label}`}>Gate Progression Timeline</h3>
            <p className={`text-[11px] ${CBPTypography.small} mt-0.5`}>Maturity gates evaluated against live metric thresholds</p>
          </div>
        </div>

        <div className="flex items-center gap-1 overflow-x-auto pb-4 px-4 py-3 bg-white border border-[#D0D7DE] rounded-sm">
          {gates.map((gate, idx) => {
            const isCurrent = currentGate && gate.gate_id === currentGate.gate_id
            return (
              <div key={gate.gate_id} className="flex items-center gap-2 flex-shrink-0">
                <div
                  className={`flex-shrink-0 h-10 w-10 rounded-full flex items-center justify-center font-bold text-xs ${
                    gate.passed
                      ? 'text-green-700 bg-green-100 border border-green-200'
                      : isCurrent
                      ? 'text-white'
                      : 'text-slate-600 bg-slate-100 border border-slate-300'
                  }`}
                  style={!gate.passed && isCurrent ? { backgroundColor: CBPColors.primary } : undefined}
                >
                  {gate.gate_id}
                </div>
                <div className="hidden sm:block text-center min-w-[90px]">
                  <div className="text-[11px] font-semibold text-[#0B1F33]">{gate.gate_name}</div>
                  <div className="text-[10px] text-slate-500">
                    {gate.passed ? 'Passed' : isCurrent ? 'Current' : 'Pending'}
                  </div>
                </div>
                {idx < gates.length - 1 && (
                  <ChevronRight className="w-4 h-4 text-slate-300 flex-shrink-0" />
                )}
              </div>
            )
          })}
        </div>
      </div>

      {/* Current Gate Exit Criteria */}
      {currentGate && (
        <div>
          <div className="flex items-center gap-3 mb-6">
            <div className="w-8 h-8 rounded-full flex items-center justify-center text-white text-[11px] font-bold flex-shrink-0" style={{ backgroundColor: CBPColors.primary }}>
              2
            </div>
            <div className="flex-1">
              <h3 className={`text-sm font-bold ${CBPTypography.label}`}>{currentGate.gate_name} Exit Criteria</h3>
              <p className={`text-[11px] ${CBPTypography.small} mt-0.5`}>
                {metCount}/{totalCount} met · {blockedCount} blocking item{blockedCount === 1 ? '' : 's'}
              </p>
            </div>
          </div>

          <div className="mb-4 bg-slate-200 rounded-full h-2.5">
            <div
              className="h-2.5 rounded-full transition-all"
              style={{
                width: totalCount ? `${(metCount / totalCount) * 100}%` : '0%',
                backgroundColor: CBPColors.primary,
              }}
            />
          </div>

          <div className="space-y-3">
            {criteria.map(criterion => (
              <div
                key={criterion.name}
                className={`flex items-start gap-3 p-3 rounded-sm border-l-4 ${
                  criterion.passed ? 'bg-green-50 border-green-400' : 'bg-amber-50 border-amber-400'
                }`}
              >
                {criterion.passed ? (
                  <CheckCircle2 className="w-5 h-5 text-green-600 flex-shrink-0 mt-0.5" />
                ) : (
                  <Lock className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
                )}
                <div className="flex-1">
                  <p className={`text-sm font-semibold ${criterion.passed ? 'text-green-900' : 'text-amber-900'}`}>
                    {criterion.description || criterion.name}
                  </p>
                  <p className={`text-[11px] mt-1 ${criterion.passed ? 'text-green-700' : 'text-amber-700'}`}>
                    Measured {criterion.measured_value}{criterion.unit ? ` ${criterion.unit}` : ''} · Threshold {criterion.threshold}{criterion.unit ? ` ${criterion.unit}` : ''}
                  </p>
                </div>
                <span className={`px-2 py-1 rounded text-[10px] font-bold flex-shrink-0 ${
                  criterion.passed ? 'bg-green-200 text-green-800' : 'bg-amber-200 text-amber-800'
                }`}>
                  {criterion.passed ? 'MET' : 'BLOCKED'}
                </span>
              </div>
            ))}
          </div>

          {blockedCount > 0 && (
            <div className="mt-6 p-4 rounded-sm border-l-4 bg-red-50" style={{ borderColor: CBPColors.risk.CRITICAL.border }}>
              <div className="flex items-start gap-3">
                <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="text-sm font-bold text-red-900">
                    {blockedCount} metric{blockedCount > 1 ? 's' : ''} blocking {currentGate.gate_name} closure
                  </p>
                  <ul className="text-[11px] text-red-700 mt-2 list-disc list-inside space-y-1">
                    {criteria.filter(c => !c.passed).map(c => (
                      <li key={c.name}>
                        <strong>{c.description || c.name}</strong>: measured {c.measured_value}{c.unit ? ` ${c.unit}` : ''} vs threshold {c.threshold}{c.unit ? ` ${c.unit}` : ''}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default OverviewTab
