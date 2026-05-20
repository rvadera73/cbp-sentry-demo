import React, { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ChevronLeft, AlertTriangle, TrendingUp, Zap, BarChart3 } from 'lucide-react'
import { api } from '../services/api'
import type { Shipment } from '../types/sentry'

const ShipmentDetailPage: React.FC = () => {
  const { shipmentId } = useParams<{ shipmentId: string }>()
  const navigate = useNavigate()

  const [shipment, setShipment] = useState<Shipment | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string>('')
  const [activeTab, setActiveTab] = useState<'overview' | 'horizons' | 'referral'>('overview')
  const [highlightedSections, setHighlightedSections] = useState<string[]>([])

  useEffect(() => {
    loadShipment()
  }, [shipmentId])

  const loadShipment = async () => {
    if (!shipmentId) return
    setLoading(true)
    setError('')
    try {
      const data = await api.getShipment(parseInt(shipmentId))
      if (data && !data.error) {
        setShipment(data)
      } else {
        setError('Shipment not found')
      }
    } catch (err) {
      setError(`Error loading shipment: ${err instanceof Error ? err.message : 'Unknown error'}`)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="text-center py-12">
        <TrendingUp className="w-8 h-8 text-sentry-teal mx-auto animate-spin" />
        <p className="mt-4 text-gray-600 font-semibold">Loading shipment details...</p>
      </div>
    )
  }

  if (error || !shipment) {
    return (
      <div className="text-center py-12">
        <AlertTriangle className="w-12 h-12 text-red-500 mx-auto mb-4" />
        <p className="text-red-600 font-semibold">{error || 'Shipment not found'}</p>
        <button onClick={() => navigate('/shipments')} className="mt-4 text-sentry-teal font-semibold hover:underline">
          Back to Shipments
        </button>
      </div>
    )
  }

  const getRiskColor = (score: number): string => {
    if (score >= 80) return 'bg-red-100 text-red-800 border-red-300'
    if (score >= 50) return 'bg-yellow-100 text-yellow-800 border-yellow-300'
    return 'bg-green-100 text-green-800 border-green-300'
  }

  const getRiskBadgeColor = (level: string): string => {
    if (level === 'CRITICAL') return 'bg-red-500 text-white'
    if (level === 'HIGH') return 'bg-orange-500 text-white'
    if (level === 'MEDIUM') return 'bg-yellow-500 text-white'
    return 'bg-green-500 text-white'
  }

  const referralSections = [
    { id: 'shipment-id', label: 'Shipment Identification', poweredBy: ['H1', 'H3'] },
    { id: 'parties', label: 'Parties & Entities', poweredBy: ['H1', 'H3'] },
    { id: 'commodity', label: 'Commodity Analysis', poweredBy: ['H1', 'H3'] },
    { id: 'routing', label: 'Routing & Transportation', poweredBy: ['H2', 'H3'] },
    { id: 'risks', label: 'Risk Factors', poweredBy: ['H1', 'H2', 'H3'] },
    { id: 'evidence', label: 'Supporting Evidence', poweredBy: ['H2', 'H3'] },
    { id: 'recommendation', label: 'Recommendation', poweredBy: ['H3'] },
  ]

  const toggleSectionHighlight = (sectionId: string, horizons: string[]) => {
    setHighlightedSections(highlightedSections.includes(sectionId) ? [] : horizons)
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100">
      {/* Header */}
      <div className="bg-sentry-navy text-white py-6 px-6">
        <div className="max-w-7xl mx-auto">
          <button
            onClick={() => navigate('/shipments')}
            className="flex items-center gap-2 text-sentry-light-blue hover:text-white mb-4 transition"
          >
            <ChevronLeft className="w-5 h-5" />
            Back to Shipments
          </button>
          <div className="flex justify-between items-start">
            <div>
              <h1 className="text-4xl font-black mb-2">{shipment.manifest_id}</h1>
              <p className="text-blue-100 text-lg">
                {shipment.shipper_name} → {shipment.consignee_name}
              </p>
            </div>
            <span className={`px-6 py-3 rounded-full text-2xl font-black ${getRiskBadgeColor(shipment.h1_risk_level)}`}>
              {shipment.risk_score}/100
            </span>
          </div>
        </div>
      </div>

      {/* Content Tabs */}
      <div className="max-w-7xl mx-auto px-6 py-8">
        <div className="grid grid-cols-3 gap-6">
          {/* Tabs */}
          <div className="col-span-3">
            <div className="flex gap-2 border-b border-gray-300 mb-6">
              {[
                { id: 'overview', label: 'Overview', icon: BarChart3 },
                { id: 'horizons', label: 'Three Horizons', icon: Zap },
                { id: 'referral', label: 'Referral Package', icon: AlertTriangle },
              ].map(({ id, label, icon: Icon }) => (
                <button
                  key={id}
                  onClick={() => setActiveTab(id as any)}
                  className={`flex items-center gap-2 px-4 py-3 font-semibold border-b-2 transition-colors ${
                    activeTab === id
                      ? 'border-sentry-teal text-sentry-teal'
                      : 'border-transparent text-gray-600 hover:text-gray-900'
                  }`}
                >
                  <Icon className="w-5 h-5" />
                  {label}
                </button>
              ))}
            </div>
          </div>

          {/* Overview Tab */}
          {activeTab === 'overview' && (
            <>
              <div className="col-span-2 space-y-6">
                {/* Route Section */}
                <div className="bg-white rounded-lg shadow p-6 border border-gray-200">
                  <h2 className="text-lg font-black text-sentry-navy mb-4">Trade Route</h2>
                  <div className="grid grid-cols-2 gap-6">
                    <div>
                      <p className="text-xs font-black text-gray-600 uppercase mb-2">Origin</p>
                      <p className="font-semibold text-gray-900">{shipment.shipper_name}</p>
                      <p className="text-sm text-gray-600">
                        {shipment.shipper_city}, {shipment.shipper_country}
                      </p>
                      <p className="text-xs text-gray-500 mt-2 font-mono">
                        {shipment.shipper_lat.toFixed(4)}, {shipment.shipper_lon.toFixed(4)}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs font-black text-gray-600 uppercase mb-2">Destination</p>
                      <p className="font-semibold text-gray-900">{shipment.consignee_name}</p>
                      <p className="text-sm text-gray-600">
                        {shipment.consignee_city}, {shipment.consignee_country}
                      </p>
                      <p className="text-xs text-gray-500 mt-2 font-mono">
                        {shipment.consignee_lat.toFixed(4)}, {shipment.consignee_lon.toFixed(4)}
                      </p>
                    </div>
                  </div>
                </div>

                {/* Commodity Section */}
                <div className="bg-white rounded-lg shadow p-6 border border-gray-200">
                  <h2 className="text-lg font-black text-sentry-navy mb-4">Commodity</h2>
                  <div className="grid grid-cols-2 gap-6">
                    <div>
                      <p className="text-xs font-black text-gray-600 uppercase mb-2">Product</p>
                      <p className="font-semibold text-gray-900">{shipment.commodity_name}</p>
                      <p className="text-sm text-gray-600 font-mono">HTS {shipment.commodity_code}</p>
                    </div>
                    <div>
                      <p className="text-xs font-black text-gray-600 uppercase mb-2">Declared Value</p>
                      <p className="font-black text-2xl text-gray-900">${shipment.declared_value.toLocaleString()}</p>
                    </div>
                  </div>
                </div>
              </div>

              <div className="col-span-1 space-y-6">
                {/* Status Card */}
                <div className="bg-white rounded-lg shadow p-6 border border-gray-200">
                  <p className="text-xs font-black text-gray-600 uppercase mb-3">Status</p>
                  <p className={`px-4 py-2 rounded text-sm font-black text-center ${getRiskColor(shipment.risk_score)}`}>
                    {shipment.status}
                  </p>
                </div>

                {/* H1 Risk Level */}
                <div className="bg-white rounded-lg shadow p-6 border border-gray-200">
                  <p className="text-xs font-black text-gray-600 uppercase mb-3">H1 Risk Level</p>
                  <span className={`px-4 py-2 rounded text-sm font-black inline-block ${getRiskBadgeColor(shipment.h1_risk_level)}`}>
                    {shipment.h1_risk_level}
                  </span>
                </div>

                {/* H2 Signals */}
                {shipment.h2_signals && shipment.h2_signals.length > 0 && (
                  <div className="bg-white rounded-lg shadow p-6 border border-gray-200">
                    <p className="text-xs font-black text-gray-600 uppercase mb-3">H2 Signals</p>
                    <div className="space-y-2">
                      {shipment.h2_signals.map((signal, idx) => (
                        <span key={idx} className="block px-3 py-1 bg-orange-100 text-orange-700 text-xs rounded font-semibold">
                          {signal.replace(/_/g, ' ')}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </>
          )}

          {/* Horizons Tab */}
          {activeTab === 'horizons' && (
            <div className="col-span-3">
              <div className="grid grid-cols-3 gap-6">
                {/* H1 Corridor Risk */}
                <div className="bg-white rounded-lg shadow p-6 border border-gray-200">
                  <h3 className="text-lg font-black text-sentry-navy mb-4">H1: Corridor Risk</h3>
                  <div className="space-y-3">
                    <div>
                      <p className="text-xs font-black text-gray-600 uppercase">Route</p>
                      <p className="font-semibold">{shipment.shipper_country} → {shipment.consignee_country}</p>
                    </div>
                    <div>
                      <p className="text-xs font-black text-gray-600 uppercase">Risk Level</p>
                      <p className={`font-black text-lg inline-block px-3 py-1 rounded ${getRiskBadgeColor(shipment.h1_risk_level)}`}>
                        {shipment.h1_risk_level}
                      </p>
                    </div>
                  </div>
                </div>

                {/* H2 Pre-Intelligence */}
                <div className="bg-white rounded-lg shadow p-6 border border-gray-200">
                  <h3 className="text-lg font-black text-sentry-navy mb-4">H2: Pre-Intelligence</h3>
                  <div className="space-y-2">
                    {shipment.h2_signals && shipment.h2_signals.length > 0 ? (
                      shipment.h2_signals.map((signal, idx) => (
                        <div key={idx} className="px-3 py-2 bg-orange-100 rounded text-xs font-semibold text-orange-700">
                          ⚠ {signal.replace(/_/g, ' ')}
                        </div>
                      ))
                    ) : (
                      <p className="text-gray-600 text-sm">No signals detected</p>
                    )}
                  </div>
                </div>

                {/* H3 Assessment */}
                <div className="bg-sentry-navy text-white rounded-lg shadow p-6">
                  <h3 className="text-lg font-black mb-4">H3: Full Assessment</h3>
                  <div className="space-y-3">
                    <div>
                      <p className="text-xs text-sentry-light-blue font-black uppercase">Risk Score</p>
                      <p className="font-black text-4xl text-sentry-teal">{shipment.risk_score}</p>
                    </div>
                    <div>
                      <p className="text-xs text-sentry-light-blue font-black uppercase">Recommendation</p>
                      <p className="font-semibold text-sentry-orange">{shipment.h3_recommendation}</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Referral Package Tab */}
          {activeTab === 'referral' && (
            <div className="col-span-3">
              <div className="bg-white rounded-lg shadow border border-gray-200 overflow-hidden">
                <div className="bg-gray-50 px-6 py-4 border-b border-gray-200">
                  <p className="text-sm font-black text-gray-600 uppercase">Referral Document Sections</p>
                  <p className="text-xs text-gray-600 mt-1">Click a section to highlight data sources from the Three Horizons</p>
                </div>
                <div className="divide-y divide-gray-200">
                  {referralSections.map((section) => (
                    <button
                      key={section.id}
                      onClick={() => toggleSectionHighlight(section.id, section.poweredBy)}
                      className={`w-full text-left px-6 py-4 transition-all ${
                        highlightedSections.length === 0 ? 'hover:bg-gray-50' : highlightedSections.includes(section.poweredBy[0]) ? 'bg-sentry-teal/10 border-l-4 border-sentry-teal' : 'opacity-50'
                      }`}
                    >
                      <div className="flex justify-between items-start">
                        <div>
                          <p className="font-semibold text-gray-900">{section.label}</p>
                          <p className="text-xs text-gray-600 mt-1">Powered by: {section.poweredBy.join(', ')}</p>
                        </div>
                        <div className="flex gap-2">
                          {section.poweredBy.map((horizon) => (
                            <span key={horizon} className="px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded font-semibold">
                              {horizon}
                            </span>
                          ))}
                        </div>
                      </div>
                    </button>
                  ))}
                </div>
              </div>

              <div className="mt-6 p-4 bg-blue-50 rounded-lg border border-blue-200">
                <p className="text-sm text-blue-900">
                  <span className="font-black">💡 Insight:</span> Hover over any section to see how the Three Horizons (H1 Corridor Risk, H2 Pre-Intelligence, H3 Full Assessment) power different parts of
                  the referral document. This demonstrates the integrated intelligence pipeline from real-time risk assessment to enforcement recommendations.
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default ShipmentDetailPage
