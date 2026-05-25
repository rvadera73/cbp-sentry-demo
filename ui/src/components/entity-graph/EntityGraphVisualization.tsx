/**
 * Interactive entity relationship graph visualization.
 *
 * Uses React Flow for hierarchical layout with:
 * - 3-level ownership chain (Shipper → Intermediary → Manufacturer)
 * - ISF enrichment warnings merged into nodes
 * - Risk-based node coloring
 * - Relationship confidence visualization
 *
 * Phase 3 Implementation (in development)
 */

import React, { useCallback } from 'react';
import ReactFlow, {
  Node,
  Edge,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  NodeTypes,
  EdgeTypes,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { EntityGraph, FlowNodeData } from './types';
import { entityGraphToFlowNodes, entityGraphToFlowEdges } from './utils';
import EntityNode from './EntityNode';
import ISFWarningsPanel from './ISFWarningsPanel';
import './EntityGraphVisualization.css';

const nodeTypes: NodeTypes = {
  entity: EntityNode,
};

interface EntityGraphVisualizationProps {
  graph: EntityGraph | null;
  loading?: boolean;
  error?: string | null;
}

export default function EntityGraphVisualization({
  graph,
  loading = false,
  error = null,
}: EntityGraphVisualizationProps) {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [selectedEntityId, setSelectedEntityId] = React.useState<string | null>(null);

  // Initialize graph nodes and edges when data loads
  React.useEffect(() => {
    if (graph) {
      const flowNodes = entityGraphToFlowNodes(graph);
      const flowEdges = entityGraphToFlowEdges(graph);

      // Set node type to custom entity node
      const typedNodes = flowNodes.map((node) => ({
        ...node,
        type: 'entity',
      }));

      setNodes(typedNodes);
      setEdges(flowEdges);
    }
  }, [graph, setNodes, setEdges]);

  const onNodeClick = useCallback(
    (event: React.MouseEvent, node: Node<FlowNodeData>) => {
      setSelectedEntityId(node.data.entity.entity_id);
    },
    []
  );

  if (loading) {
    return (
      <div className="entity-graph-loading">
        <div className="spinner">⏳ Loading entity graph...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="entity-graph-error">
        <div className="error-message">❌ {error}</div>
      </div>
    );
  }

  if (!graph || graph.chain.length === 0) {
    return (
      <div className="entity-graph-empty">
        <div className="empty-message">📊 No entity chain data available</div>
      </div>
    );
  }

  const selectedEntity = graph.chain.find((e) => e.entity_id === selectedEntityId);

  return (
    <div className="entity-graph-container">
      <div className="entity-graph-header">
        <h3>Entity Relationship Graph</h3>
        <div className="metadata">
          <span className="risk-score">Risk: {graph.risk_score}/100</span>
          <span className="sources">{graph.data_sources.join(', ')}</span>
          {graph.ofac_detected && <span className="ofac-badge">⚠️ OFAC Detected</span>}
        </div>
      </div>

      <div className="entity-graph-content">
        <div className="flow-container">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onNodeClick={onNodeClick}
            nodeTypes={nodeTypes}
            fitView
          >
            <Background />
            <Controls />
          </ReactFlow>
        </div>

        {selectedEntity && (
          <div className="entity-details-panel">
            <EntityDetails entity={selectedEntity} />
          </div>
        )}
      </div>

      <ISFWarningsPanel graph={graph} />
    </div>
  );
}

/**
 * Entity details sidebar component.
 */
function EntityDetails({ entity }: { entity: any }) {
  return (
    <div className="entity-details">
      <h4>{entity.name}</h4>
      <div className="details-grid">
        <div className="detail-item">
          <label>Entity ID</label>
          <span>{entity.entity_id}</span>
        </div>
        <div className="detail-item">
          <label>Country</label>
          <span>{entity.country}</span>
        </div>
        <div className="detail-item">
          <label>Role</label>
          <span>{entity.role}</span>
        </div>
        <div className="detail-item">
          <label>Confidence</label>
          <span>{(entity.confidence * 100).toFixed(0)}%</span>
        </div>
        <div className="detail-item">
          <label>Risk Score</label>
          <span>{entity.risk_score ?? 'N/A'}</span>
        </div>
        <div className="detail-item">
          <label>Data Source</label>
          <span>{entity.data_source}</span>
        </div>
      </div>

      {entity.relationships && entity.relationships.length > 0 && (
        <div className="relationships-section">
          <h5>Relationships</h5>
          <ul>
            {entity.relationships.map((rel: any, idx: number) => (
              <li key={idx}>
                <strong>{rel.type}:</strong> {rel.target} ({(rel.confidence * 100).toFixed(0)}%)
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
