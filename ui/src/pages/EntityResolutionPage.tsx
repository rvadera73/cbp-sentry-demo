import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useWorkflow } from '../context/WorkflowContext'
import { api } from '../services/api'
import type { Entity, WhyResponse } from '../types/sentry'
import { Search, ArrowRight } from 'lucide-react'

const EntityResolutionPage: React.FC = () => {
  const navigate = useNavigate()
  const { state, setState } = useWorkflow()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedEntityId, setSelectedEntityId] = useState<string | null>(null)

  // Entity workspace state
  const [selectedEntityDetails, setSelectedEntityDetails] = useState<any>(null)
  const [entityChain, setEntityChain] = useState<any[]>([])
  const [entityParties, setEntityParties] = useState<any[]>([])
  const [detailsLoading, setDetailsLoading] = useState(false)

  // Why Connected modal state
  const [showWhyModal, setShowWhyModal] = useState(false)
  const [selectedA, setSelectedA] = useState<any | null>(null)
  const [selectedB, setSelectedB] = useState<any | null>(null)
  const [whyData, setWhyData] = useState<any>(null)
  const [whyLoading, setWhyLoading] = useState(false)

  // Load entities from CORD on mount
  useEffect(() => {
    loadEntities()
  }, [])

  const loadEntities = async () => {
    setLoading(true)
    setError(null)
    setState({ entitiesLoading: true })

    try {
      // For now, search for common entities - in production this would be filtered by manifest
      const response = await api.cordSearch('Electronics', undefined, 100)
      if (response?.matches) {
        const entities = response.matches.map((entity: any) => ({
          entity_id: entity.entity_id || entity.id,
          entity_name: entity.name || entity.entity_name,
          entity_type: entity.entity_type || entity.type || 'ORGANIZATION',
          jurisdiction: entity.country || entity.jurisdiction || 'Unknown',
          senzing_confidence: entity.confidence || 0.85,
          risk_level: entity.risk_flags?.includes('OFAC') ? 'CRITICAL' : entity.risk_flags?.length > 0 ? 'HIGH' : 'MEDIUM',
          country: entity.country,
        }))
        setState({
          entities: entities,
          entitiesResolved: true,
          entitiesLoading: false,
        })
      } else {
        setError('No entities found in CORD')
        setState({ entitiesLoading: false })
      }
    } catch (err) {
      console.error('Error loading entities:', err)
      setError(err instanceof Error ? err.message : 'Failed to load entities from CORD')
      setState({ entitiesLoading: false })
    } finally {
      setLoading(false)
    }
  }

  const loadEntityDetails = async (entityId: string) => {
    setDetailsLoading(true)
    try {
      const entityResp = await api.cordGetEntity(entityId)
      setSelectedEntityDetails(entityResp?.entity)

      // Load entity chain
      try {
        // Using graph endpoint as placeholder - update when CORD chain endpoint available
        const chainResp = await api.getShipmentGraph(entityId)
        setEntityChain(chainResp?.nodes || [])
      } catch (err) {
        console.warn('Could not load entity chain:', err)
        setEntityChain([])
      }

      // Load related parties
      try {
        // Using why endpoint as placeholder - update when CORD parties endpoint available
        const partiesResp = await api.cordWhyLinked(entityId, entityId)
        setEntityParties(partiesResp?.explanation ? [partiesResp] : [])
      } catch (err) {
        console.warn('Could not load entity parties:', err)
        setEntityParties([])
      }
    } catch (err) {
      console.error('Error loading entity details:', err)
      setError('Failed to load entity details')
    } finally {
      setDetailsLoading(false)
    }
  }

  const handleEntitySelect = (entityId: string) => {
    setSelectedEntityId(entityId)
    loadEntityDetails(entityId)
  }

  const handleWhyConnected = async () => {
    if (!selectedA || !selectedB) {
      setError('Please select two entities')
      return
    }

    setWhyLoading(true)
    try {
      const response = await api.cordWhyLinked(selectedA.entity_id, selectedB.entity_id)
      if (response?.explanation) {
        setWhyData(response)
      } else {
        setError('No connection found between entities')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch entity connection')
    } finally {
      setWhyLoading(false)
    }
  }

  const handleScoreShipment = () => {
    if (state.entitiesResolved) {
      navigate('/scoring')
    }
  }

  const filteredEntities = (state.entities || []).filter((entity: any) =>
    entity.entity_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    entity.jurisdiction.toLowerCase().includes(searchQuery.toLowerCase())
  )

  if (!selectedEntityId) {
    // ENTITY QUEUE VIEW
    return (
      <div className="flex-1 flex flex-col overflow-hidden h-screen bg-white">
        {/* Header */}
        <div className="bg-white p-4 border-b border-[#D0D7DE] rounded-sm flex justify-between items-center mb-0 shadow-sm">
          <div>
            <h2 className="text-lg font-bold uppercase flex items-center space-x-2 mb-0 text-[#0B1F33]">
              <span>ENTITY RESOLUTION QUEUE</span>
            </h2>
            <p className="text-[11px] mt-1 text-slate-600">CORD/Senzing-resolved entities with jurisdiction and confidence scoring.</p>
          </div>
          <button
            onClick={loadEntities}
            className="px-3 py-1.5 border border-[#D0D7DE] hover:bg-slate-50 text-xs font-bold rounded-sm text-[#0B1F33] cursor-pointer"
          >
            REFRESH
          </button>
        </div>

        {/* Search */}
        <div className="bg-white p-3.5 rounded-sm border-b border-[#D0D7DE] flex items-center gap-4 mb-0">
          <div className="flex-1 relative flex items-center">
            <Search className="h-4 w-4 text-slate-400 absolute left-3" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Filter by entity name or country..."
              className="w-full bg-slate-50 border border-[#D0D7DE] rounded-sm pl-9 pr-4 py-1.5 text-xs text-[#0B1F33] focus:outline-none focus:border-[#005EA2]"
            />
          </div>
        </div>

        {error && (
          <div className="bg-red-50 border-b border-red-200 p-3 text-red-700 text-xs">
            {error}
          </div>
        )}

        {/* Entity Table */}
        <div className="bg-white border-b border-[#D0D7DE] shadow-sm flex-1 overflow-auto">
          {loading ? (
            <div className="flex items-center justify-center h-64 text-slate-500">
              <p>Loading entities from CORD/Senzing...</p>
            </div>
          ) : filteredEntities.length === 0 ? (
            <div className="flex items-center justify-center h-64 text-slate-500">
              <p>No entities found. Try adjusting your search.</p>
            </div>
          ) : (
            <table className="w-full text-left text-xs border-collapse">
              <thead className="sticky top-0 bg-[#F0F4F8] border-b border-[#D0D7DE] font-mono text-[#112E51] font-bold">
                <tr>
                  <th className="p-3 w-20">STATUS</th>
                  <th className="p-3">ENTITY NAME</th>
                  <th className="p-3">TYPE</th>
                  <th className="p-3">JURISDICTION</th>
                  <th className="p-3">CONFIDENCE</th>
                  <th className="p-3 text-right">ACTIONS</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredEntities.map((entity: any) => (
                  <tr key={entity.entity_id} className="hover:bg-slate-50 transition-all cursor-pointer">
                    <td className="p-3">
                      <span className={`inline-block px-2.5 py-1 rounded text-center font-extrabold text-xs text-white ${
                        entity.risk_level === 'CRITICAL' ? 'bg-[#D83933]' : entity.risk_level === 'HIGH' ? 'bg-orange-600' : 'bg-amber-600'
                      }`}>
                        {entity.risk_level}
                      </span>
                    </td>
                    <td className="p-3">
                      <div className="flex flex-col">
                        <span className="font-extrabold text-[#0B1F33]">{entity.entity_name}</span>
                        <span className="text-[10px] text-[#5C5C5C] font-mono block mt-0.5">{entity.entity_id}</span>
                      </div>
                    </td>
                    <td className="p-3 text-slate-800 font-medium text-[11px]">{entity.entity_type}</td>
                    <td className="p-3 text-[#5C5C5C] font-mono text-[11px]">{entity.jurisdiction}</td>
                    <td className="p-3 text-[#0076D6] font-bold text-[11px]">{((entity.senzing_confidence || 0) * 100).toFixed(0)}%</td>
                    <td className="p-3 text-right">
                      <button
                        onClick={() => handleEntitySelect(entity.entity_id)}
                        className="px-3 py-1 bg-[#112E51] hover:bg-[#0076D6] text-white text-[10px] font-bold rounded-sm flex items-center space-x-1 ml-auto"
                      >
                        <span>View Details</span>
                        <ArrowRight className="h-3 w-3" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    )
  }

  // ENTITY WORKSPACE VIEW
  const entity = state.entities?.find((e: any) => e.entity_id === selectedEntityId)

  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-[#F7F9FC]">
      {/* Back Button */}
      <div className="bg-[#F7F9FC] border-b border-[#D0D7DE] px-6 py-2 shrink-0">
        <button
          onClick={() => setSelectedEntityId(null)}
          className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 border border-slate-300 text-[#005EA2] hover:text-[#0076D6] text-xs font-bold rounded-sm flex items-center space-x-1 transition-colors"
        >
          <span>←</span>
          <span>BACK TO QUEUE</span>
        </button>
      </div>

      {/* Entity Details - First Two Rows */}
      <div className="p-6 space-y-4 overflow-y-auto flex-1">
        {/* Row 1: Entity Identity */}
        <div className="bg-white border border-[#D0D7DE] rounded-sm p-5 grid grid-cols-4 gap-4">
          <div>
            <p className="text-[9px] text-slate-600 font-bold uppercase mb-1">Entity Name</p>
            <p className="text-sm font-bold text-[#0B1F33]">{entity?.entity_name}</p>
          </div>
          <div>
            <p className="text-[9px] text-slate-600 font-bold uppercase mb-1">Entity Type</p>
            <p className="text-sm font-bold text-[#0B1F33]">{entity?.entity_type}</p>
          </div>
          <div>
            <p className="text-[9px] text-slate-600 font-bold uppercase mb-1">Jurisdiction</p>
            <p className="text-sm font-bold text-[#0B1F33]">{entity?.jurisdiction}</p>
          </div>
          <div>
            <p className="text-[9px] text-slate-600 font-bold uppercase mb-1">Entity ID</p>
            <p className="text-xs font-mono text-slate-600">{entity?.entity_id}</p>
          </div>
        </div>

        {/* Row 2: Risk & Confidence */}
        <div className="bg-white border border-[#D0D7DE] rounded-sm p-5 grid grid-cols-4 gap-4">
          <div>
            <p className="text-[9px] text-slate-600 font-bold uppercase mb-1">Risk Status</p>
            <span className={`inline-block px-2.5 py-1 rounded text-center font-extrabold text-xs text-white ${
              entity?.risk_level === 'CRITICAL' ? 'bg-[#D83933]' : entity?.risk_level === 'HIGH' ? 'bg-orange-600' : 'bg-amber-600'
            }`}>
              {entity?.risk_level}
            </span>
          </div>
          <div>
            <p className="text-[9px] text-slate-600 font-bold uppercase mb-1">Confidence</p>
            <p className="text-sm font-bold text-[#0076D6]">{((entity?.senzing_confidence || 0) * 100).toFixed(0)}%</p>
          </div>
          <div>
            <p className="text-[9px] text-slate-600 font-bold uppercase mb-1">Source</p>
            <p className="text-sm font-bold text-[#0B1F33]">CORD/Senzing</p>
          </div>
          <div>
            <p className="text-[9px] text-slate-600 font-bold uppercase mb-1">Status</p>
            <p className="text-sm font-bold text-green-700">Resolved</p>
          </div>
        </div>

        {/* Entity Graph */}
        {entityChain.length > 0 && (
          <div className="bg-white border border-[#D0D7DE] rounded-sm p-5">
            <h3 className="text-sm font-bold text-[#0B1F33] mb-3">ENTITY RELATIONSHIP GRAPH</h3>
            <div className="bg-slate-50 p-4 rounded border border-slate-200 text-center text-slate-600 text-xs">
              Entity graph visualization ({entityChain.length} related entities)
            </div>
          </div>
        )}

        {/* Party Associations */}
        {entityParties.length > 0 && (
          <div className="bg-white border border-[#D0D7DE] rounded-sm p-5">
            <h3 className="text-sm font-bold text-[#0B1F33] mb-3">PARTY ASSOCIATIONS</h3>
            <div className="space-y-2">
              {entityParties.map((party: any, idx: number) => (
                <div key={idx} className="p-3 bg-slate-50 border border-slate-200 rounded text-xs">
                  <p className="font-bold text-[#0B1F33]">{party.target || 'Associated Entity'}</p>
                  <p className="text-slate-600 text-[9px] mt-1">{party.explanation || 'Related in supply chain'}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Why Connected Panel */}
        <div className="bg-white border border-[#D0D7DE] rounded-sm p-5">
          <h3 className="text-sm font-bold text-[#0B1F33] mb-3">Why Connected?</h3>
          <p className="text-[9px] text-slate-600 mb-4">
            Select two entities from the queue to view CORD connection path and evidence.
          </p>
          <div className="grid grid-cols-2 gap-3 mb-4">
            <select
              value={selectedA?.entity_id || ''}
              onChange={(e) => {
                const ent = state.entities?.find((x: any) => x.entity_id === e.target.value)
                setSelectedA(ent || null)
              }}
              className="px-3 py-2 border border-[#D0D7DE] rounded-sm bg-white text-[11px] text-[#0B1F33] focus:outline-none focus:border-[#005EA2]"
            >
              <option value="">Select Entity A...</option>
              {state.entities?.map((e: any) => (
                <option key={e.entity_id} value={e.entity_id}>
                  {e.entity_name}
                </option>
              ))}
            </select>
            <select
              value={selectedB?.entity_id || ''}
              onChange={(e) => {
                const ent = state.entities?.find((x: any) => x.entity_id === e.target.value)
                setSelectedB(ent || null)
              }}
              className="px-3 py-2 border border-[#D0D7DE] rounded-sm bg-white text-[11px] text-[#0B1F33] focus:outline-none focus:border-[#005EA2]"
            >
              <option value="">Select Entity B...</option>
              {state.entities?.map((e: any) => (
                <option key={e.entity_id} value={e.entity_id}>
                  {e.entity_name}
                </option>
              ))}
            </select>
          </div>
          <button
            onClick={() => {
              handleWhyConnected()
              setShowWhyModal(true)
            }}
            disabled={!selectedA || !selectedB || whyLoading}
            className={`px-3 py-1.5 rounded-sm text-xs font-bold flex items-center space-x-1 ${
              selectedA && selectedB && !whyLoading
                ? 'bg-[#005EA2] text-white hover:bg-[#0076D6]'
                : 'bg-slate-200 text-slate-500 cursor-not-allowed'
            }`}
          >
            <span>{whyLoading ? 'Loading...' : 'Show Connection'}</span>
          </button>
        </div>
      </div>

      {/* Why Modal */}
      {showWhyModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-sm shadow-xl p-6 max-w-2xl max-h-96 overflow-y-auto border border-[#D0D7DE]">
            <h3 className="text-sm font-bold text-[#0B1F33] mb-4">CONNECTION EXPLANATION</h3>
            {whyData ? (
              <div className="space-y-3">
                <div className="text-xs text-slate-600 font-mono">
                  <strong>{selectedA?.entity_name}</strong> ↔ <strong>{selectedB?.entity_name}</strong>
                </div>
                <div className="bg-blue-50 p-3 rounded border border-blue-200">
                  <p className="text-xs font-semibold text-[#0B1F33] mb-1">Connection:</p>
                  <p className="text-xs text-slate-700">{whyData.explanation || 'Related through supply chain'}</p>
                </div>
              </div>
            ) : (
              <p className="text-xs text-slate-600">Loading connection details...</p>
            )}
            <button
              onClick={() => setShowWhyModal(false)}
              className="mt-4 px-3 py-1.5 bg-slate-200 text-slate-700 rounded-sm text-xs font-bold hover:bg-slate-300"
            >
              Close
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

export default EntityResolutionPage
