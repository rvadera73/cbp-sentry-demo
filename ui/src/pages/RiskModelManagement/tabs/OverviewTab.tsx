/**
 * Overview Tab — active production model + gate progression / exit criteria.
 * Data: GET /metrics/gates, GET /models/production.
 */
import React, { useEffect, useState } from 'react'
import { CheckCircle2, Lock, ShieldCheck } from 'lucide-react'
import { getMLOpsEndpoint } from '../../../services/apiUrl'
import { SectionHeader, Panel, StatStrip, StatusPill, DataTable, LoadingState, ErrorState, Column } from '../../../components/ui'

interface GateMetric { name: string; measured_value: number | null; threshold: number; unit?: string | null; passed: boolean; description?: string | null }
interface Gate { gate_id: number | string; gate_name: string; passed: boolean; metrics?: GateMetric[]; exit_criteria?: GateMetric[] }
interface GatesResponse { days_since_award: number; gates: Gate[] }

const readMetric = (model: any, keys: string[]): number | null => {
  const sources = [model?.metrics, model?.metadata?.metrics, model?.metadata].filter(Boolean)
  for (const s of sources) for (const k of keys) {
    const v = s?.[k]; if (typeof v === 'number' && !Number.isNaN(v)) return v
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
    ;(async () => {
      setLoading(true); setError(null)
      try {
        const [gRes, mRes] = await Promise.all([
          fetch(getMLOpsEndpoint('/metrics/gates')),
          fetch(getMLOpsEndpoint('/models/production')),
        ])
        if (!gRes.ok) throw new Error(`Gate metrics request failed (${gRes.status})`)
        const gates = await gRes.json()
        const prod = mRes.ok ? await mRes.json() : null
        if (!cancelled) { setGatesData(gates); setModel(prod) }
      } catch (e) { if (!cancelled) setError(e instanceof Error ? e.message : 'Failed to load overview') }
      finally { if (!cancelled) setLoading(false) }
    })()
    return () => { cancelled = true }
  }, [])

  if (loading) return <LoadingState label="Loading gate status…" />
  if (error || !gatesData) return <ErrorState title="Unable to load overview" detail={error} />

  const gates = gatesData.gates || []
  const current = gates.find(g => !g.passed) || gates[gates.length - 1] || null
  const criteria = (current?.metrics || current?.exit_criteria || []) as GateMetric[]
  const met = criteria.filter(c => c.passed).length

  const auc = readMetric(model, ['auc', 'xgb_auc', 'auc_roc'])
  const f1 = readMetric(model, ['f1', 'f1_score', 'xgb_f1'])
  const modelName = model?.model_name || model?.name || model?.model_id || 'No production model'
  const modelVersion = model?.version ?? model?.model_id ?? ''
  const isProd = model?.is_production ?? (model?.status === 'production')

  const critColumns: Column[] = [
    { key: 'description', label: 'Exit Criterion', render: r => r.description || r.name },
    { key: 'measured_value', label: 'Measured', align: 'right', mono: true, render: r => (r.measured_value == null ? '—' : `${r.measured_value}${r.unit ? ` ${r.unit}` : ''}`) },
    { key: 'threshold', label: 'Threshold', align: 'right', mono: true, render: r => `${r.threshold}${r.unit ? ` ${r.unit}` : ''}` },
    { key: 'passed', label: 'Status', align: 'center', render: r => <StatusPill status={r.passed ? 'MET' : 'BLOCKED'} /> },
  ]

  return (
    <div className="space-y-5">
      {/* Active model */}
      <Panel className="border-l-4" >
        <SectionHeader
          title={model ? `${modelName} ${modelVersion ? `· v${modelVersion}` : ''}` : 'No Production Model'}
          subtitle={model ? `${model.status || 'registered'}${model.framework ? ` · ${model.framework}` : ''}` : 'No production model configured'}
          icon={<ShieldCheck className="w-4 h-4" />}
          action={model ? <StatusPill status={isProd ? 'production' : (model.status || 'registered')} /> : undefined}
        />
        <StatStrip items={[
          { label: 'AUC', value: auc != null ? auc.toFixed(3) : '—' },
          { label: 'F1 Score', value: f1 != null ? f1.toFixed(3) : '—' },
          { label: 'Days Since Award', value: gatesData.days_since_award },
          { label: 'Current Gate', value: current ? current.gate_id : '—', hint: current?.gate_name || '' },
        ]} />
      </Panel>

      {/* Gate progression */}
      <Panel>
        <SectionHeader title="Gate Progression" subtitle="Maturity gates evaluated against live metric thresholds" />
        <ol className="flex flex-wrap items-center gap-1.5">
          {gates.map((g, i) => {
            const isCurrent = current && g.gate_id === current.gate_id
            return (
              <li key={g.gate_id} className="flex items-center gap-1.5">
                <div className={`px-3 py-1.5 rounded-sm border text-center min-w-[120px] ${g.passed ? 'bg-green-50 border-green-300' : isCurrent ? 'bg-[#005EA2] border-[#005EA2] text-white' : 'bg-slate-50 border-slate-300'}`}>
                  <div className={`text-[12px] font-bold ${isCurrent ? 'text-white' : 'text-[#0B1F33]'}`}>Gate {g.gate_id}</div>
                  <div className={`text-[10px] ${isCurrent ? 'text-blue-100' : 'text-[#5C5C5C]'}`}>{g.gate_name}</div>
                  <div className={`text-[9px] font-bold uppercase ${g.passed ? 'text-green-700' : isCurrent ? 'text-white' : 'text-[#5C5C5C]'}`}>{g.passed ? 'Passed' : isCurrent ? 'Current' : 'Pending'}</div>
                </div>
                {i < gates.length - 1 && <span className="text-slate-400" aria-hidden>›</span>}
              </li>
            )
          })}
        </ol>
      </Panel>

      {/* Exit criteria */}
      {current && (
        <Panel>
          <SectionHeader
            title={`${current.gate_name} Exit Criteria`}
            subtitle={`${met}/${criteria.length} met · ${criteria.length - met} blocking`}
            icon={criteria.length - met > 0 ? <Lock className="w-4 h-4" /> : <CheckCircle2 className="w-4 h-4" />}
          />
          <DataTable columns={critColumns} rows={criteria} caption={`${current.gate_name} exit criteria`} empty="No criteria defined." />
        </Panel>
      )}
    </div>
  )
}

export default OverviewTab
