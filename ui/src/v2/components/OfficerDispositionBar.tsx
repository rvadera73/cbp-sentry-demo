/**
 * Officer Disposition Bar
 *
 * Records the officer's triage decision (Hold / Examine / Clear) for a shipment
 * as a Gate-1 outcome via POST /api/feedback/outcome → cbp-risk-engine
 * (risk_scoring.gate1_outcomes). These outcomes are the real Gate-2 training
 * signal that advances model maturity.
 */

import React, { useState } from 'react'
import { getAPIEndpoint } from '../../services/apiUrl'

interface Props {
  shipmentId?: string
  predictedRisk?: number
}

const ACTIONS: { key: string; label: string; outcome: string; cls: string }[] = [
  { key: 'HOLD', label: 'Hold for Exam', outcome: 'pending', cls: 'bg-[#D83933]' },
  { key: 'EXAMINE', label: 'Examine', outcome: 'pending', cls: 'bg-[#C7791B]' },
  { key: 'CLEAR', label: 'Clear', outcome: 'cleared', cls: 'bg-[#07A41E]' },
]

const OfficerDispositionBar: React.FC<Props> = ({ shipmentId, predictedRisk }) => {
  const [submitting, setSubmitting] = useState<string | null>(null)
  const [recorded, setRecorded] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const record = async (action: string, outcome: string) => {
    if (!shipmentId) return
    setSubmitting(action)
    setError(null)
    try {
      const params = new URLSearchParams({
        shipment_id: shipmentId,
        officer_action: action,
        outcome,
        analyst_id: 'officer',
      })
      if (typeof predictedRisk === 'number') params.append('predicted_risk', String(predictedRisk))
      const res = await fetch(`${getAPIEndpoint('/feedback/outcome')}?${params.toString()}`, { method: 'POST' })
      if (!res.ok) throw new Error(`Request failed (${res.status})`)
      const data = await res.json()
      if (data.status === 'failed') throw new Error(data.error || 'Failed to record outcome')
      setRecorded(action)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to record outcome')
    } finally {
      setSubmitting(null)
    }
  }

  return (
    <div className="bg-white border border-[#D0D7DE] rounded-sm p-4">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-bold text-[#0B1F33] uppercase">Officer Disposition</h3>
        {recorded && (
          <span className="text-[11px] text-green-700 font-semibold">
            Recorded: {recorded} → Gate-1 outcome logged
          </span>
        )}
      </div>
      <p className="text-[11px] text-[#5C5C5C] mb-3">
        Your decision is logged as a Gate-1 outcome — the training signal that advances model maturity toward Gate 2.
      </p>
      <div className="flex gap-2">
        {ACTIONS.map((a) => (
          <button
            key={a.key}
            type="button"
            disabled={submitting !== null || !shipmentId}
            onClick={() => record(a.key, a.outcome)}
            className={`${a.cls} text-white text-xs font-bold px-4 py-2 rounded-sm disabled:opacity-50 disabled:cursor-not-allowed`}
          >
            {submitting === a.key ? 'Recording…' : a.label}
          </button>
        ))}
      </div>
      {error && <p className="text-[11px] text-red-600 mt-2">{error}</p>}
    </div>
  )
}

export default OfficerDispositionBar
