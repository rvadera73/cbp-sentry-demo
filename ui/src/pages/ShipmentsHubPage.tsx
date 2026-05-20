import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { MapPin, AlertTriangle, TrendingUp, Search, Filter, Map as MapIcon, List } from 'lucide-react'
import { api } from '../services/api'
import ShipmentsMap from '../components/shipments/ShipmentsMap'
import type { Shipment, ShipmentRoute } from '../types/sentry'

const ShipmentsHubPage: React.FC = () => {
  const navigate = useNavigate()
  const [shipments, setShipments] = useState<Shipment[]>([])
  const [routes, setRoutes] = useState<ShipmentRoute[]>([])
  const [stats, setStats] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string>('')
  const [viewMode, setViewMode] = useState<'list' | 'map'>('list')

  // Filter states
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedCountry, setSelectedCountry] = useState<string>('')
  const [selectedStatus, setSelectedStatus] = useState<string>('')
  const [riskRange, setRiskRange] = useState({ min: 0, max: 100 })

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    setLoading(true)
    setError('')
    try {
      const shipmentsData = await api.getShipments()
      const statsData = await api.getShipmentsStats()
      const mapData = await api.getShipmentsMapData()
      setShipments(shipmentsData.shipments || [])
      setRoutes(mapData.routes || [])
      setStats(statsData)
    } catch (err) {
      setError(`Error loading shipments: ${err instanceof Error ? err.message : 'Unknown error'}`)
    } finally {
      setLoading(false)
    }
  }

  const filteredShipments = shipments.filter((shipment) => {
    const matchesSearch =
      shipment.shipper_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      shipment.consignee_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      shipment.manifest_id.toLowerCase().includes(searchQuery.toLowerCase())

    const matchesCountry = !selectedCountry || shipment.shipper_country === selectedCountry
    const matchesRisk =
      shipment.risk_score >= riskRange.min && shipment.risk_score <= riskRange.max
    const matchesStatus = !selectedStatus || shipment.status === selectedStatus

    return matchesSearch && matchesCountry && matchesRisk && matchesStatus
  })

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

  const getStatusColor = (status: string): string => {
    if (status === 'EXAMINE') return 'bg-red-100 text-red-800'
    if (status === 'WARN') return 'bg-yellow-100 text-yellow-800'
    return 'bg-green-100 text-green-800'
  }

  const uniqueCountries = Array.from(new Set(shipments.map((s) => s.shipper_country)))

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100">
      {/* Header Section */}
      <div className="bg-gradient-to-r from-sentry-navy to-sentry-dark-teal text-white py-8 px-6">
        <div className="max-w-7xl mx-auto">
          <div className="flex items-center gap-3 mb-4">
            <MapPin className="w-8 h-8" />
            <h1 className="text-4xl font-black">Shipments Hub</h1>
          </div>
          <p className="text-blue-100 text-lg max-w-2xl">
            Monitor and analyze {stats?.total || 0} international shipments with real-time risk
            assessment and geographic tracking.
          </p>
        </div>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="max-w-7xl mx-auto px-6 py-6 grid grid-cols-4 gap-4">
          <div className="bg-white rounded-lg shadow p-4 border-l-4 border-red-500">
            <p className="text-xs font-black text-gray-600 uppercase">High Risk</p>
            <p className="text-3xl font-black text-red-600 mt-2">{stats.highRisk}</p>
          </div>
          <div className="bg-white rounded-lg shadow p-4 border-l-4 border-yellow-500">
            <p className="text-xs font-black text-gray-600 uppercase">Medium Risk</p>
            <p className="text-3xl font-black text-yellow-600 mt-2">{stats.mediumRisk}</p>
          </div>
          <div className="bg-white rounded-lg shadow p-4 border-l-4 border-green-500">
            <p className="text-xs font-black text-gray-600 uppercase">Low Risk</p>
            <p className="text-3xl font-black text-green-600 mt-2">{stats.lowRisk}</p>
          </div>
          <div className="bg-white rounded-lg shadow p-4 border-l-4 border-sentry-teal">
            <p className="text-xs font-black text-gray-600 uppercase">Total</p>
            <p className="text-3xl font-black text-sentry-teal mt-2">{stats.total}</p>
          </div>
        </div>
      )}

      {/* Filters Section */}
      <div className="max-w-7xl mx-auto px-6 py-6">
        <div className="bg-white rounded-lg shadow p-6 border border-gray-200">
          <div className="flex items-center gap-3 mb-4">
            <Filter className="w-5 h-5 text-sentry-navy" />
            <h2 className="text-lg font-black text-sentry-navy">Filters & Search</h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
            {/* Search */}
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">Search</label>
              <div className="relative">
                <Search className="absolute left-3 top-3 w-4 h-4 text-gray-400" />
                <input
                  type="text"
                  placeholder="Shipper, consignee, manifest..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-10 pr-3 py-2 border border-gray-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-sentry-teal"
                />
              </div>
            </div>

            {/* Country Filter */}
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">Origin</label>
              <select
                value={selectedCountry}
                onChange={(e) => setSelectedCountry(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-sentry-teal"
              >
                <option value="">All Countries</option>
                {uniqueCountries.map((country) => (
                  <option key={country} value={country}>
                    {country}
                  </option>
                ))}
              </select>
            </div>

            {/* Risk Range */}
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">
                Risk Score: {riskRange.min}-{riskRange.max}
              </label>
              <div className="flex gap-2">
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={riskRange.min}
                  onChange={(e) =>
                    setRiskRange({ ...riskRange, min: Math.min(parseInt(e.target.value), riskRange.max) })
                  }
                  className="w-full h-2 bg-gray-200 rounded"
                />
              </div>
            </div>

            {/* Status Filter */}
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">Status</label>
              <select
                value={selectedStatus}
                onChange={(e) => setSelectedStatus(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-sentry-teal"
              >
                <option value="">All Statuses</option>
                <option value="EXAMINE">Examine</option>
                <option value="WARN">Warn</option>
                <option value="OK">OK</option>
              </select>
            </div>

            {/* Reset Button */}
            <div className="flex items-end">
              <button
                onClick={() => {
                  setSearchQuery('')
                  setSelectedCountry('')
                  setSelectedStatus('')
                  setRiskRange({ min: 0, max: 100 })
                }}
                className="w-full px-4 py-2 bg-gray-200 hover:bg-gray-300 text-sentry-navy font-semibold rounded transition-all"
              >
                Reset Filters
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* View Mode Tabs */}
      <div className="max-w-7xl mx-auto px-6 py-4">
        <div className="flex gap-2 border-b border-gray-300">
          <button
            onClick={() => setViewMode('list')}
            className={`flex items-center gap-2 px-4 py-3 font-semibold border-b-2 transition-colors ${
              viewMode === 'list'
                ? 'border-sentry-teal text-sentry-teal'
                : 'border-transparent text-gray-600 hover:text-gray-900'
            }`}
          >
            <List className="w-5 h-5" />
            List View
          </button>
          <button
            onClick={() => setViewMode('map')}
            className={`flex items-center gap-2 px-4 py-3 font-semibold border-b-2 transition-colors ${
              viewMode === 'map'
                ? 'border-sentry-teal text-sentry-teal'
                : 'border-transparent text-gray-600 hover:text-gray-900'
            }`}
          >
            <MapIcon className="w-5 h-5" />
            Map View
          </button>
        </div>
      </div>

      {/* Shipments Content */}
      <div className="max-w-7xl mx-auto px-6 pb-12">
        {error && (
          <div className="mb-6 p-4 bg-red-100 border border-red-400 rounded text-red-800">
            {error}
          </div>
        )}

        {loading ? (
          <div className="text-center py-12">
            <div className="inline-block animate-spin">
              <TrendingUp className="w-8 h-8 text-sentry-teal" />
            </div>
            <p className="mt-4 text-gray-600 font-semibold">Loading shipments...</p>
          </div>
        ) : viewMode === 'map' ? (
          <ShipmentsMap routes={routes} />
        ) : filteredShipments.length === 0 ? (
          <div className="text-center py-12 bg-white rounded-lg shadow">
            <AlertTriangle className="w-12 h-12 text-gray-400 mx-auto mb-4" />
            <p className="text-gray-600 font-semibold">No shipments match your filters</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredShipments.map((shipment) => (
              <div
                key={shipment.id}
                className="bg-white rounded-lg shadow hover:shadow-lg transition-shadow border border-gray-200"
              >
                {/* Card Header */}
                <div className={`px-6 py-4 border-b ${getRiskColor(shipment.risk_score)}`}>
                  <div className="flex justify-between items-start mb-2">
                    <div>
                      <p className="text-xs font-black uppercase">Manifest ID</p>
                      <p className="font-mono text-sm font-black mt-1">{shipment.manifest_id}</p>
                    </div>
                    <span className={`px-3 py-1 rounded-full text-xs font-black ${getRiskBadgeColor(shipment.h1_risk_level)}`}>
                      {shipment.risk_score}/100
                    </span>
                  </div>
                </div>

                {/* Route Section */}
                <div className="px-6 py-4 border-b border-gray-200">
                  <p className="text-xs font-black text-gray-600 uppercase mb-3">Trade Route</p>
                  <div className="flex items-center gap-2">
                    <div className="flex-1">
                      <p className="text-sm font-semibold text-gray-900">{shipment.shipper_name}</p>
                      <p className="text-xs text-gray-500">
                        {shipment.shipper_city}, {shipment.shipper_country}
                      </p>
                    </div>
                    <div className="text-xs text-gray-400">→</div>
                    <div className="flex-1">
                      <p className="text-sm font-semibold text-gray-900">{shipment.consignee_name}</p>
                      <p className="text-xs text-gray-500">
                        {shipment.consignee_city}, {shipment.consignee_country}
                      </p>
                    </div>
                  </div>
                </div>

                {/* Commodity Section */}
                <div className="px-6 py-4 border-b border-gray-200">
                  <p className="text-xs font-black text-gray-600 uppercase mb-2">Commodity</p>
                  <p className="font-semibold text-gray-900">{shipment.commodity_name}</p>
                  <p className="text-xs text-gray-500 font-mono">HTS {shipment.commodity_code}</p>
                  <p className="text-xs text-gray-500 mt-1">Value: ${shipment.declared_value.toLocaleString()}</p>
                </div>

                {/* Signals & Status */}
                <div className="px-6 py-4">
                  {shipment.h2_signals && shipment.h2_signals.length > 0 && (
                    <div className="mb-4">
                      <p className="text-xs font-black text-gray-600 uppercase mb-2">H2 Signals</p>
                      <div className="flex flex-wrap gap-1">
                        {shipment.h2_signals.map((signal, idx) => (
                          <span key={idx} className="px-2 py-1 bg-orange-100 text-orange-700 text-xs rounded font-semibold">
                            {signal.replace(/_/g, ' ')}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  <div className="flex items-center gap-3">
                    <span className={`px-3 py-1 rounded text-xs font-black ${getStatusColor(shipment.status)}`}>
                      {shipment.status}
                    </span>
                    <button
                      onClick={() => navigate(`/shipments/${shipment.id}`)}
                      className="text-sentry-teal hover:text-sentry-dark-teal text-sm font-semibold"
                    >
                      View Details →
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Results Info */}
        <div className="mt-8 text-center text-gray-600 text-sm">
          Showing {filteredShipments.length} of {shipments.length} shipments
        </div>
      </div>
    </div>
  )
}

export default ShipmentsHubPage
