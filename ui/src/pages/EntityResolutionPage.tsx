import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useWorkflow } from '../context/WorkflowContext'
import { api } from '../services/api'
import type { Entity, WhyResponse } from '../types/sentry'

const EntityResolutionPage: React.FC = () => {
  const navigate = useNavigate()
  const { state, setState } = useWorkflow()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Why Connected modal state
  const [showWhyModal, setShowWhyModal] = useState(false)
  const [selectedA, setSelectedA] = useState<Entity | null>(null)
  const [selectedB, setSelectedB] = useState<Entity | null>(null)
  const [whyData, setWhyData] = useState<WhyResponse | null>(null)
  const [whyLoading, setWhyLoading] = useState(false)

  // Load entities on mount
  useEffect(() => {
    loadEntities()
  }, [])

  const loadEntities = async () => {
    if (!state.manifestId) {
      setError('No manifest ID available')
      return
    }

    setLoading(true)
    setError(null)
    setState({ entitiesLoading: true })

    try {
      const response = await api.resolveEntities(state.manifestId)
      if (response) {
        setState({
          entities: response.entities,
          entitiesResolved: true,
          entitiesLoading: false,
        })
      } else {
        setError('Failed to resolve entities')
        setState({ entitiesLoading: false })
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
      setState({ entitiesLoading: false })
    } finally {
      setLoading(false)
    }
  }

  const handleWhyConnected = async () => {
    if (!selectedA || !selectedB) {
      setError('Please select two entities')
      return
    }

    setWhyLoading(true)
    try {
      const response = await api.getEntityWhy(selectedA.entity_id, selectedB.entity_id, state.manifestId || undefined)
      if (response) {
        setWhyData(response)
      } else {
        setError('Failed to fetch entity connection explanation')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setWhyLoading(false)
    }
  }

  const handleScoreShipment = () => {
    if (state.entitiesResolved) {
      navigate('/scoring')
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold text-sentry-navy mb-2">Entity Resolution</h2>
        <p className="text-sentry-slate">
          Senzing-resolved entities from the ingested manifest with confidence scores.
        </p>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-800">
          {error}
        </div>
      )}

      {loading ? (
        <div className="bg-white p-8 rounded-lg shadow text-center">
          <p className="text-sentry-slate">Loading entities...</p>
        </div>
      ) : state.entities && state.entities.length > 0 ? (
        <>
          {/* Entity Table */}
          <div className="bg-white rounded-lg shadow overflow-hidden">
            <div className="p-6 border-b border-gray-200">
              <h3 className="font-semibold text-sentry-navy">
                Resolved Entities ({state.entities.length})
              </h3>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left font-semibold text-gray-700">Name</th>
                    <th className="px-6 py-3 text-left font-semibold text-gray-700">Type</th>
                    <th className="px-6 py-3 text-left font-semibold text-gray-700">Country</th>
                    <th className="px-6 py-3 text-left font-semibold text-gray-700">Confidence</th>
                    <th className="px-6 py-3 text-left font-semibold text-gray-700">Risk Level</th>
                  </tr>
                </thead>
                <tbody>
                  {state.entities.map((entity) => (
                    <tr key={entity.entity_id} className="border-t border-gray-200 hover:bg-gray-50">
                      <td className="px-6 py-4 font-medium text-gray-900">{entity.entity_name}</td>
                      <td className="px-6 py-4 text-gray-600">{entity.entity_type}</td>
                      <td className="px-6 py-4 text-gray-600">{entity.jurisdiction}</td>
                      <td className="px-6 py-4">
                        <span className="inline-block bg-blue-100 text-blue-800 px-2 py-1 rounded text-xs font-semibold">
                          {(entity.senzing_confidence * 100).toFixed(0)}%
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        <span
                          className={`inline-block px-2 py-1 rounded text-xs font-semibold ${
                            entity.risk_level === 'CRITICAL'
                              ? 'bg-red-100 text-red-800'
                              : entity.risk_level === 'HIGH'
                                ? 'bg-orange-100 text-orange-800'
                                : 'bg-yellow-100 text-yellow-800'
                          }`}
                        >
                          {entity.risk_level}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Why Connected Panel */}
          <div className="bg-white p-6 rounded-lg shadow">
            <h3 className="font-semibold text-sentry-navy mb-4">Why Connected?</h3>
            <p className="text-sm text-sentry-slate mb-4">
              Select two entities to view the Senzing connection path and evidence.
            </p>
            <div className="grid grid-cols-2 gap-4 mb-4">
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">Entity A</label>
                <select
                  value={selectedA?.entity_id || ''}
                  onChange={(e) => {
                    const entity = state.entities?.find((ent) => ent.entity_id.toString() === e.target.value)
                    setSelectedA(entity || null)
                  }}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg bg-white text-gray-900"
                >
                  <option value="">Select entity...</option>
                  {state.entities?.map((entity) => (
                    <option key={entity.entity_id} value={entity.entity_id}>
                      {entity.entity_name}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">Entity B</label>
                <select
                  value={selectedB?.entity_id || ''}
                  onChange={(e) => {
                    const entity = state.entities?.find((ent) => ent.entity_id.toString() === e.target.value)
                    setSelectedB(entity || null)
                  }}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg bg-white text-gray-900"
                >
                  <option value="">Select entity...</option>
                  {state.entities?.map((entity) => (
                    <option key={entity.entity_id} value={entity.entity_id}>
                      {entity.entity_name}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            <button
              onClick={() => {
                handleWhyConnected()
                setShowWhyModal(true)
              }}
              disabled={!selectedA || !selectedB || whyLoading}
              className={`px-6 py-2 rounded font-semibold transition-all ${
                selectedA && selectedB && !whyLoading
                  ? 'bg-sentry-orange text-white hover:opacity-80'
                  : 'bg-gray-300 text-gray-500 cursor-not-allowed'
              }`}
            >
              {whyLoading ? 'Loading...' : 'Show Connection'}
            </button>
          </div>

          {/* Why Modal */}
          {showWhyModal && (
            <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
              <div className="bg-white rounded-lg shadow-xl p-6 max-w-2xl max-h-96 overflow-y-auto">
                <h3 className="text-xl font-bold text-sentry-navy mb-4">Connection Explanation</h3>
                {whyData ? (
                  <div className="space-y-4">
                    <div className="text-sm text-gray-600">
                      <strong>{whyData.entity_a.name}</strong> ({whyData.entity_a.country}) →
                      <strong> {whyData.entity_b.name}</strong> ({whyData.entity_b.country})
                    </div>
                    <div className="bg-blue-50 p-3 rounded border border-blue-200">
                      <p className="text-sm font-semibold text-sentry-navy mb-2">Explanation:</p>
                      <p className="text-sm text-gray-700">{whyData.explanation}</p>
                    </div>
                    <div className="bg-orange-50 p-3 rounded border border-orange-200">
                      <p className="text-sm font-semibold text-sentry-navy mb-2">Evidence:</p>
                      <ul className="text-sm text-gray-700 list-disc list-inside space-y-1">
                        {whyData.evidence.map((ev, idx) => (
                          <li key={idx}>{ev}</li>
                        ))}
                      </ul>
                    </div>
                    <div className="text-xs text-gray-500">
                      Connection Depth: {whyData.connection_depth} | Confidence: {(whyData.total_confidence * 100).toFixed(0)}%
                    </div>
                  </div>
                ) : (
                  <p className="text-gray-600">Loading...</p>
                )}
                <button
                  onClick={() => setShowWhyModal(false)}
                  className="mt-4 px-4 py-2 bg-gray-200 text-gray-700 rounded hover:bg-gray-300"
                >
                  Close
                </button>
              </div>
            </div>
          )}
        </>
      ) : (
        <div className="bg-white p-8 rounded-lg shadow text-center text-gray-600">
          No entities resolved yet.
        </div>
      )}

      {/* Navigation */}
      <div className="flex justify-between pt-4">
        <button
          onClick={() => navigate('/ingest')}
          className="px-6 py-2 text-gray-700 hover:text-gray-900"
        >
          ← Back
        </button>
        <button
          onClick={handleScoreShipment}
          disabled={!state.entitiesResolved}
          className={`px-6 py-2 rounded font-semibold transition-all ${
            state.entitiesResolved
              ? 'bg-sentry-teal text-white hover:bg-sentry-dark-teal'
              : 'bg-gray-300 text-gray-500 cursor-not-allowed'
          }`}
        >
          Score Shipment →
        </button>
      </div>
    </div>
  )
}

export default EntityResolutionPage
