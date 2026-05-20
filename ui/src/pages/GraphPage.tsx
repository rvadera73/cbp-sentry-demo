import React, { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useWorkflow } from '../context/WorkflowContext'
import { api } from '../services/api'
import type { GraphNode, GraphLink } from '../types/sentry'

const GraphPage: React.FC = () => {
  const navigate = useNavigate()
  const { state } = useWorkflow()
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null)
  const [graphNodes, setGraphNodes] = useState<GraphNode[]>([])
  const [graphLinks, setGraphLinks] = useState<GraphLink[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const ariaLiveRef = useRef<HTMLDivElement>(null)

  // Load graph on mount
  useEffect(() => {
    loadGraph()
  }, [state.manifestId])

  const loadGraph = async () => {
    if (!state.manifestId) {
      setError('No manifest ID available')
      setLoading(false)
      return
    }

    setLoading(true)
    setError(null)

    try {
      const response = await api.getShipmentGraph(state.manifestId)
      if (response) {
        setGraphNodes(response.nodes)
        setGraphLinks(response.links)
      } else {
        setError('Failed to load graph')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }

  // Handle node click
  const handleNodeClick = (node: GraphNode) => {
    if (selectedNode?.id === node.id) {
      setSelectedNode(null)
      announceToScreenReader(`Deselected ${node.label}`)
    } else {
      setSelectedNode(node)
      announceToScreenReader(
        `Selected ${node.label}, Type: ${node.type}, Risk Score: ${node.risk_score || 'N/A'}`
      )
    }
  }

  // Announce to screen readers
  const announceToScreenReader = (message: string) => {
    if (ariaLiveRef.current) {
      ariaLiveRef.current.textContent = message
    }
  }

  // Get connected entities for sidebar
  const getConnectedEntities = (): Array<{ node: GraphNode; relationship: string; confidence?: number }> => {
    if (!selectedNode) return []

    return graphLinks
      .filter((link) => link.source === selectedNode.id || link.target === selectedNode.id)
      .map((link) => {
        const targetId = link.source === selectedNode.id ? link.target : link.source
        const targetNode = graphNodes.find((n) => n.id === targetId)
        return {
          node: targetNode!,
          relationship: link.relationship,
          confidence: link.confidence,
        }
      })
  }

  if (loading) {
    return (
      <div className="p-6">
        <p className="text-sentry-slate">Loading graph...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-800">
        {error}
      </div>
    )
  }

  const connectedEntities = getConnectedEntities()

  return (
    <div className="graph-container flex h-screen bg-white">
      {/* Screen reader announcements */}
      <div
        ref={ariaLiveRef}
        role="status"
        aria-live="polite"
        className="sr-only"
      />

      {/* Main Graph Canvas */}
      <main className="flex-1 bg-white overflow-hidden">
        <div
          className="canvas w-full h-full relative"
          role="img"
          aria-label="Entity relationship graph"
        >
          <div className="p-4 bg-gray-50 border-b border-gray-200">
            <h1 className="text-2xl font-bold text-sentry-navy">
              Entity Graph Explorer
            </h1>
            <p className="text-sm text-sentry-slate mt-1">
              {graphNodes.length} entities, {graphLinks.length} relationships
            </p>
          </div>

          {/* Node List */}
          <div className="p-6 space-y-3 overflow-y-auto h-[calc(100%-80px)]">
            {graphNodes.map((node) => (
              <div
                key={node.id}
                className={`node p-4 rounded-lg border-2 cursor-pointer transition-all ${
                  selectedNode?.id === node.id
                    ? 'border-blue-600 bg-blue-50'
                    : 'border-gray-200 bg-white hover:border-gray-300'
                }`}
                data-testid={`node-${node.id}`}
                onClick={() => handleNodeClick(node)}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault()
                    handleNodeClick(node)
                  }
                }}
                aria-pressed={selectedNode?.id === node.id}
              >
                <div className="font-semibold text-gray-900">{node.label}</div>
                <div className="text-sm text-sentry-slate mt-1">
                  Type: {node.type}
                  {node.country && ` • ${node.country}`}
                  {node.risk_score && node.risk_score > 0 && ` • Risk: ${node.risk_score}/100`}
                </div>
              </div>
            ))}
          </div>
        </div>
      </main>

      {/* Sidebar */}
      <aside
        className="sidebar w-80 bg-white border-l border-gray-200 overflow-y-auto flex flex-col"
        role="complementary"
        aria-label="Entity details"
      >
        <div className="sticky top-0 bg-white border-b border-gray-200 p-4">
          <h2 className="text-lg font-semibold text-sentry-navy">Entity Details</h2>
        </div>

        <div id="entity-details" className="p-4 flex-1 overflow-y-auto">
          {selectedNode ? (
            <div className="space-y-4">
              {/* Node Name */}
              <div>
                <label className="text-sm font-semibold text-gray-600">Name</label>
                <p className="text-gray-900 mt-1">{selectedNode.label}</p>
              </div>

              {/* Entity Type */}
              <div>
                <label className="text-sm font-semibold text-gray-600">Type</label>
                <p className="text-gray-900 mt-1">{selectedNode.type}</p>
              </div>

              {/* Country */}
              {selectedNode.country && (
                <div>
                  <label className="text-sm font-semibold text-gray-600">
                    Country
                  </label>
                  <p className="text-gray-900 mt-1">{selectedNode.country}</p>
                </div>
              )}

              {/* Risk Score */}
              {selectedNode.risk_score && selectedNode.risk_score >= 0 && (
                <div>
                  <label className="text-sm font-semibold text-gray-600">
                    Risk Score
                  </label>
                  <p className="text-gray-900 mt-1">
                    {selectedNode.risk_score}/100
                  </p>
                </div>
              )}

              {/* Connected Entities */}
              {connectedEntities.length > 0 && (
                <div className="pt-4 border-t border-gray-200">
                  <label className="text-sm font-semibold text-gray-600">
                    Connected Entities
                  </label>
                  <ul className="mt-2 space-y-2">
                    {connectedEntities.map((conn) => (
                      <li
                        key={conn.node.id}
                        className="text-sm p-2 bg-gray-50 rounded border border-gray-200"
                      >
                        <div className="font-medium text-gray-900">
                          {conn.relationship}
                        </div>
                        <div className="text-gray-600">{conn.node.label}</div>
                        <div className="text-xs text-gray-500">
                          Confidence: {conn.confidence ? (conn.confidence * 100).toFixed(0) : 'N/A'}%
                        </div>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Why Connected Button */}
              <button
                onClick={() => navigate('/entity-resolution')}
                className="w-full mt-4 px-4 py-2 bg-sentry-teal text-white rounded font-medium hover:bg-sentry-dark-teal transition-colors"
              >
                Why Connected?
              </button>
            </div>
          ) : (
            <p className="text-sm text-sentry-slate">
              Select a node to view details
            </p>
          )}
        </div>
      </aside>

      {/* Footer Navigation */}
      <div className="fixed bottom-4 right-4 flex gap-3">
        <button
          onClick={() => navigate('/referral/:manifestId')}
          className="px-4 py-2 text-gray-700 bg-white border border-gray-300 rounded hover:bg-gray-50"
        >
          ← Back to Referral
        </button>
      </div>
    </div>
  )
}

export default GraphPage
