import React, { useState } from 'react'
import { CheckCircle, AlertCircle, FileText } from 'lucide-react'

interface QuickActionPanelProps {
  shipment: any | null
}

const QuickActionPanel: React.FC<QuickActionPanelProps> = ({ shipment }) => {
  const [action, setAction] = useState<string | null>(null)
  const [notes, setNotes] = useState('')

  if (!shipment) {
    return (
      <div className="p-6 text-center text-sentry-light-blue">
        <AlertCircle className="w-8 h-8 mx-auto mb-3 opacity-50" />
        <p className="text-sm">Click a shipment on the map to take action</p>
      </div>
    )
  }

  const getRiskBadgeColor = (risk: string) => {
    if (risk === 'HIGH') return 'bg-red-500/20 border-red-500/50 text-red-300'
    if (risk === 'MEDIUM') return 'bg-yellow-500/20 border-yellow-500/50 text-yellow-300'
    return 'bg-green-500/20 border-green-500/50 text-green-300'
  }

  const handleAction = (actionType: string) => {
    setAction(actionType)
    // In real app, would save to backend
    setTimeout(() => {
      alert(`Action "${actionType}" logged for ${shipment.manifest_id}`)
      setAction(null)
      setNotes('')
    }, 500)
  }

  return (
    <div className="p-6 bg-sentry-navy/80">
      {/* Shipment Header */}
      <div className="mb-4">
        <p className="text-xs text-sentry-light-blue uppercase font-semibold">Selected Shipment</p>
        <p className="text-lg font-black text-white truncate">{shipment.manifest_id}</p>
        <p className="text-sm text-sentry-light-blue mt-1">
          {shipment.shipper_name} → {shipment.consignee_name}
        </p>
      </div>

      {/* Risk Badge */}
      <div className="flex items-center gap-3 mb-4 p-3 rounded-lg bg-sentry-navy border border-sentry-teal/20">
        <div>
          <p className="text-xs text-sentry-light-blue uppercase">Risk Score</p>
          <p className="text-2xl font-black text-sentry-orange">{shipment.risk_score}/100</p>
        </div>
        <div className="ml-auto">
          <span
            className={`px-3 py-1 rounded font-semibold text-xs border ${getRiskBadgeColor(
              shipment.h1_risk_level
            )}`}
          >
            {shipment.h1_risk_level}
          </span>
        </div>
      </div>

      {/* Quick Actions */}
      <p className="text-xs text-sentry-light-blue uppercase font-semibold mb-3">Officer Actions</p>
      <div className="space-y-2 mb-4">
        <button
          onClick={() => handleAction('RELEASE')}
          disabled={action !== null}
          className={`w-full flex items-center gap-2 px-4 py-3 rounded-lg font-semibold transition-all ${
            action === 'RELEASE'
              ? 'bg-green-600 text-white'
              : 'bg-green-500/20 border border-green-500/50 text-green-300 hover:bg-green-500/30'
          } disabled:opacity-50`}
        >
          <CheckCircle className="w-4 h-4" />
          Release / Clear
        </button>

        <button
          onClick={() => handleAction('EXAMINE')}
          disabled={action !== null}
          className={`w-full flex items-center gap-2 px-4 py-3 rounded-lg font-semibold transition-all ${
            action === 'EXAMINE'
              ? 'bg-yellow-600 text-white'
              : 'bg-yellow-500/20 border border-yellow-500/50 text-yellow-300 hover:bg-yellow-500/30'
          } disabled:opacity-50`}
        >
          <AlertCircle className="w-4 h-4" />
          Exam / Inspect
        </button>

        <button
          onClick={() => handleAction('REFER')}
          disabled={action !== null}
          className={`w-full flex items-center gap-2 px-4 py-3 rounded-lg font-semibold transition-all ${
            action === 'REFER'
              ? 'bg-red-600 text-white'
              : 'bg-red-500/20 border border-red-500/50 text-red-300 hover:bg-red-500/30'
          } disabled:opacity-50`}
        >
          <FileText className="w-4 h-4" />
          Generate Referral
        </button>
      </div>

      {/* Notes */}
      <p className="text-xs text-sentry-light-blue uppercase font-semibold mb-2">Officer Notes</p>
      <textarea
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
        placeholder="Add internal notes..."
        className="w-full px-3 py-2 bg-sentry-navy border border-sentry-teal/20 rounded text-white text-xs placeholder-gray-500 focus:border-sentry-teal focus:outline-none resize-none"
        rows={3}
      />

      {action && (
        <div className="mt-3 p-3 bg-green-500/10 border border-green-500/30 rounded text-green-300 text-xs">
          ✓ Action logged: {action}
        </div>
      )}
    </div>
  )
}

export default QuickActionPanel
