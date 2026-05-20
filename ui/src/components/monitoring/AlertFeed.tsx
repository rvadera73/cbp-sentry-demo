import React, { useMemo } from 'react'
import { AlertTriangle, Zap, Flag } from 'lucide-react'

interface AlertFeedProps {
  shipments: any[]
}

const AlertFeed: React.FC<AlertFeedProps> = ({ shipments }) => {
  const alerts = useMemo(() => {
    const generatedAlerts: any[] = []

    shipments.forEach((shipment, idx) => {
      // High risk alerts
      if (shipment.risk_score >= 70) {
        generatedAlerts.push({
          id: `high-${idx}`,
          type: 'HIGH_RISK',
          severity: 'CRITICAL',
          timestamp: new Date(Date.now() - Math.random() * 600000),
          message: `${shipment.shipper_name} → ${shipment.consignee_name}`,
          details: `Risk score: ${shipment.risk_score}/100`,
          shipment: shipment.manifest_id,
        })
      }

      // H2 Signal alerts
      if (shipment.h2_signals && shipment.h2_signals.length > 0) {
        shipment.h2_signals.forEach((signal: string, sidx: number) => {
          generatedAlerts.push({
            id: `h2-${idx}-${sidx}`,
            type: 'H2_ANOMALY',
            severity: 'WARNING',
            timestamp: new Date(Date.now() - Math.random() * 600000),
            message: signal.replace(/_/g, ' '),
            details: shipment.manifest_id,
            shipment: shipment.manifest_id,
          })
        })
      }
    })

    // Sort by timestamp descending
    return generatedAlerts.sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime()).slice(0, 15)
  }, [shipments])

  const getAlertIcon = (type: string) => {
    if (type === 'HIGH_RISK') return <Flag className="w-4 h-4 text-red-400" />
    if (type === 'H2_ANOMALY') return <Zap className="w-4 h-4 text-yellow-400" />
    return <AlertTriangle className="w-4 h-4 text-orange-400" />
  }

  const getAlertBgColor = (severity: string) => {
    if (severity === 'CRITICAL') return 'bg-red-500/10 border-red-500/30'
    if (severity === 'WARNING') return 'bg-yellow-500/10 border-yellow-500/30'
    return 'bg-orange-500/10 border-orange-500/30'
  }

  const getAlertTextColor = (severity: string) => {
    if (severity === 'CRITICAL') return 'text-red-300'
    if (severity === 'WARNING') return 'text-yellow-300'
    return 'text-orange-300'
  }

  const formatTime = (date: Date) => {
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / 60000)

    if (diffMins < 1) return 'just now'
    if (diffMins < 60) return `${diffMins}m ago`

    const diffHours = Math.floor(diffMins / 60)
    if (diffHours < 24) return `${diffHours}h ago`

    const diffDays = Math.floor(diffHours / 24)
    return `${diffDays}d ago`
  }

  return (
    <div className="p-6 bg-sentry-navy/80 flex flex-col">
      <p className="text-xs text-sentry-light-blue uppercase font-semibold mb-4">Real-Time Alert Feed ({alerts.length})</p>

      <div className="flex-1 overflow-y-auto space-y-2 pr-2">
        {alerts.length > 0 ? (
          alerts.map((alert) => (
            <div key={alert.id} className={`p-3 rounded border ${getAlertBgColor(alert.severity)}`}>
              <div className="flex gap-3">
                <div className="flex-none mt-0.5">{getAlertIcon(alert.type)}</div>
                <div className="flex-1 min-w-0">
                  <p className={`font-semibold text-sm ${getAlertTextColor(alert.severity)} truncate`}>{alert.message}</p>
                  <p className="text-xs text-sentry-light-blue mt-1 truncate">{alert.details}</p>
                  <p className="text-xs text-gray-500 mt-1">{formatTime(alert.timestamp)}</p>
                </div>
              </div>
            </div>
          ))
        ) : (
          <div className="text-center py-8 text-sentry-light-blue/50">
            <p className="text-sm">No alerts</p>
            <p className="text-xs">All systems nominal</p>
          </div>
        )}
      </div>
    </div>
  )
}

export default AlertFeed
