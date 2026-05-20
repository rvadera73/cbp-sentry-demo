import React, { useState, useEffect } from 'react'
import { AlertTriangle, TrendingUp, Zap, Clock } from 'lucide-react'
import { api } from '../services/api'
import LiveMap from '../components/monitoring/LiveMap'
import AlertFeed from '../components/monitoring/AlertFeed'
import PortIntelligence from '../components/monitoring/PortIntelligence'
import QuickActionPanel from '../components/monitoring/QuickActionPanel'

const LiveMonitoringPage: React.FC = () => {
  const [shipments, setShipments] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedShipment, setSelectedShipment] = useState<any>(null)
  const [stats, setStats] = useState({
    total: 0,
    highRisk: 0,
    mediumRisk: 0,
    lowRisk: 0,
    alerts: 0
  })

  useEffect(() => {
    loadShipments()
    const interval = setInterval(loadShipments, 30000) // Refresh every 30 seconds
    return () => clearInterval(interval)
  }, [])

  const loadShipments = async () => {
    try {
      const response = await api.getShipments(100, 0)
      const shipmentsList = response.shipments || []
      setShipments(shipmentsList)

      // Calculate stats
      const highRisk = shipmentsList.filter((s: any) => s.risk_score >= 70).length
      const mediumRisk = shipmentsList.filter((s: any) => s.risk_score >= 50 && s.risk_score < 70).length
      const lowRisk = shipmentsList.filter((s: any) => s.risk_score < 50).length
      const alerts = shipmentsList.filter((s: any) => s.h2_signals?.length > 0).length

      setStats({
        total: shipmentsList.length,
        highRisk,
        mediumRisk,
        lowRisk,
        alerts
      })
    } catch (error) {
      console.error('Failed to load shipments:', error)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="h-screen bg-sentry-navy text-white overflow-hidden">
      {/* Header */}
      <div className="bg-gradient-to-r from-sentry-navy to-sentry-dark-teal px-6 py-4 border-b border-sentry-teal/20">
        <div className="max-w-full mx-auto">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-3xl font-black flex items-center gap-2">
                <Zap className="w-8 h-8 text-sentry-teal" />
                SENTRY LIVE INTELLIGENCE
              </h1>
              <p className="text-sentry-light-blue text-sm mt-1">Real-time shipment monitoring & enforcement dashboard</p>
            </div>
            <div className="text-right">
              <p className="text-sm text-sentry-light-blue">Last Updated: Just now</p>
              <p className="text-2xl font-black text-sentry-teal">{stats.total} Shipments In Transit</p>
            </div>
          </div>
        </div>
      </div>

      {/* Stats Bar */}
      <div className="bg-sentry-navy/50 px-6 py-3 border-b border-sentry-teal/10 grid grid-cols-5 gap-4">
        <div className="flex items-center gap-3">
          <div className="w-3 h-3 rounded-full bg-red-500 animate-pulse"></div>
          <div>
            <p className="text-xs text-sentry-light-blue">HIGH RISK</p>
            <p className="text-xl font-black text-red-400">{stats.highRisk}</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <div className="w-3 h-3 rounded-full bg-yellow-500 animate-pulse"></div>
          <div>
            <p className="text-xs text-sentry-light-blue">MEDIUM RISK</p>
            <p className="text-xl font-black text-yellow-400">{stats.mediumRisk}</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <div className="w-3 h-3 rounded-full bg-green-500"></div>
          <div>
            <p className="text-xs text-sentry-light-blue">LOW RISK</p>
            <p className="text-xl font-black text-green-400">{stats.lowRisk}</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <AlertTriangle className="w-5 h-5 text-sentry-orange" />
          <div>
            <p className="text-xs text-sentry-light-blue">ACTIVE ALERTS</p>
            <p className="text-xl font-black text-sentry-orange">{stats.alerts}</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Clock className="w-5 h-5 text-sentry-light-blue" />
          <div>
            <p className="text-xs text-sentry-light-blue">STATUS</p>
            <p className="text-xl font-black text-sentry-light-blue">LIVE</p>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="h-[calc(100vh-180px)] flex gap-0">
        {/* Left: Map (60%) */}
        <div className="w-3/5 bg-gray-900 border-r border-sentry-teal/10">
          {loading ? (
            <div className="w-full h-full flex items-center justify-center">
              <div className="text-center">
                <TrendingUp className="w-12 h-12 text-sentry-teal mx-auto mb-4 animate-spin" />
                <p className="text-sentry-light-blue">Loading world map...</p>
              </div>
            </div>
          ) : (
            <LiveMap
              shipments={shipments}
              selectedShipment={selectedShipment}
              onSelectShipment={setSelectedShipment}
            />
          )}
        </div>

        {/* Right: Panels (40%) */}
        <div className="w-2/5 flex flex-col overflow-hidden">
          {/* Quick Actions (30%) */}
          <div className="flex-none border-b border-sentry-teal/10">
            <QuickActionPanel shipment={selectedShipment} />
          </div>

          {/* Port Intelligence (35%) */}
          <div className="flex-none border-b border-sentry-teal/10 overflow-y-auto max-h-[35%]">
            <PortIntelligence shipments={shipments} />
          </div>

          {/* Alert Feed (35%) */}
          <div className="flex-1 overflow-y-auto">
            <AlertFeed shipments={shipments} />
          </div>
        </div>
      </div>
    </div>
  )
}

export default LiveMonitoringPage
