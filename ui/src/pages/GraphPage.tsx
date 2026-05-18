import React, { useState, useRef } from 'react'

interface GraphNode {
  id: string
  label: string
  type: string
  jurisdiction?: string
  risk_score: number
  imo?: string
  metadata?: Record<string, any>
  position?: { x: number; y: number }
}

interface GraphEdge {
  source: string
  target: string
  label: string
  confidence: number
}

interface GraphData {
  nodes: GraphNode[]
  edges: GraphEdge[]
  metadata?: Record<string, any>
}

interface GraphPageProps {
  graph?: GraphData
}

const GraphPage: React.FC<GraphPageProps> = ({ graph }) => {
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null)
  const ariaLiveRef = useRef<HTMLDivElement>(null)

  // Handle node click
  const handleNodeClick = (node: GraphNode) => {
    if (selectedNode?.id === node.id) {
      // Deselect on second click
      setSelectedNode(null)
      announceToScreenReader(`Deselected ${node.label}`)
    } else {
      // Select node
      setSelectedNode(node)
      announceToScreenReader(`Selected ${node.label}, Type: ${node.type}, Risk Score: ${node.risk_score}`)
    }
  }

  // Announce to screen readers
  const announceToScreenReader = (message: string) => {
    if (ariaLiveRef.current) {
      ariaLiveRef.current.textContent = message
    }
  }

  // Get connected entities for sidebar
  const getConnectedEntities = (): Array<{ node: GraphNode; relationship: string; confidence: number }> => {
    if (!selectedNode || !graph) return []

    return graph.edges
      .filter(
        (edge) =>
          edge.source === selectedNode.id || edge.target === selectedNode.id
      )
      .map((edge) => {
        const targetId = edge.source === selectedNode.id ? edge.target : edge.source
        const targetNode = graph.nodes.find((n) => n.id === targetId)
        return {
          node: targetNode!,
          relationship: edge.label,
          confidence: edge.confidence,
        }
      })
  }

  // Handle empty graph gracefully
  if (!graph) {
    return (
      <div className="p-6">
        <p className="text-sentry-slate">Loading graph...</p>
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
              {graph?.nodes?.length || 0} entities, {graph?.edges?.length || 0} relationships
            </p>
          </div>

          {/* Node List */}
          <div className="p-6 space-y-3 overflow-y-auto h-[calc(100%-80px)]">
            {graph?.nodes?.map((node) => (
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
                  {node.jurisdiction && ` • ${node.jurisdiction}`}
                  {node.risk_score > 0 && ` • Risk: ${node.risk_score}/100`}
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

              {/* Jurisdiction */}
              {selectedNode.jurisdiction && (
                <div>
                  <label className="text-sm font-semibold text-gray-600">
                    Jurisdiction
                  </label>
                  <p className="text-gray-900 mt-1">{selectedNode.jurisdiction}</p>
                </div>
              )}

              {/* Risk Score */}
              {typeof selectedNode.risk_score === 'number' && selectedNode.risk_score >= 0 && (
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
                          Confidence: {(conn.confidence * 100).toFixed(0)}%
                        </div>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Why Connected Button */}
              <button
                onClick={() => {}}
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
    </div>
  )
}

export default GraphPage
