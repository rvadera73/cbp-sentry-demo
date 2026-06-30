import React, { useCallback, useMemo } from 'react';
import ReactFlow, {
  Node,
  Edge,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
} from 'reactflow';
import 'reactflow/dist/style.css';

interface NetworkEntity {
  entity_id: string;
  name: string;
  entity_type: string;
  country: string;
  risk_score: number;
  relationships?: Array<{
    target_id: string;
    type: string;
    confidence: number;
  }>;
}

interface EntityNetworkGraphProps {
  entities: NetworkEntity[];
  height?: number;
}

function getRiskLevel(riskScore: number): 'critical' | 'high' | 'medium' | 'low' {
  if (riskScore >= 70) return 'critical';
  if (riskScore >= 50) return 'high';
  if (riskScore >= 30) return 'medium';
  return 'low';
}

function getRiskColor(riskScore: number): string {
  if (riskScore >= 70) return '#D83933';
  if (riskScore >= 50) return '#FF9500';
  if (riskScore >= 30) return '#F59E0B';
  return '#22c55e';
}

const EntityNode = ({ data }: { data: any }) => {
  const borderColor = getRiskColor(data.risk_score);
  return (
    <div
      style={{
        padding: '8px',
        borderRadius: '6px',
        border: `2px solid ${borderColor}`,
        background: '#fff',
        width: '140px',
        fontSize: '11px',
        boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
      }}
    >
      <div style={{ fontWeight: 'bold', color: '#0B1F33', marginBottom: '2px' }}>
        {data.label.substring(0, 20)}
      </div>
      <div style={{ fontSize: '9px', color: '#5C5C5C', marginBottom: '2px' }}>
        {data.entity_type} • {data.country}
      </div>
      <div
        style={{
          fontSize: '10px',
          fontWeight: 'bold',
          color: '#fff',
          background: borderColor,
          borderRadius: '3px',
          padding: '2px 4px',
          textAlign: 'center',
        }}
      >
        {data.risk_score}%
      </div>
    </div>
  );
};

const nodeTypes = { entityNode: EntityNode };

export default function EntityNetworkGraph({
  entities,
  height = 400,
}: EntityNetworkGraphProps) {
  // Build nodes from entities. The first entity is treated as the root and
  // pinned at the centre; the rest are laid out radially around it so a
  // root -> related-parties star reads cleanly. Falls back to a simple row
  // when there is only one node.
  const initialNodes: Node[] = useMemo(() => {
    const n = entities.length;
    const radius = Math.max(220, 70 * Math.max(1, n - 1));
    return entities.map((entity, idx) => {
      let position: { x: number; y: number };
      if (n <= 1) {
        position = { x: 0, y: 0 };
      } else if (idx === 0) {
        position = { x: 0, y: 0 }; // root at centre
      } else {
        const angle = (2 * Math.PI * (idx - 1)) / (n - 1);
        position = { x: Math.cos(angle) * radius, y: Math.sin(angle) * radius };
      }
      return {
        id: entity.entity_id,
        data: {
          label: entity.name,
          entity_type: entity.entity_type,
          country: entity.country,
          risk_score: entity.risk_score,
        },
        position,
        type: 'entityNode',
      };
    });
  }, [entities]);

  // Build edges from relationships
  const initialEdges: Edge[] = useMemo(() => {
    const edges: Edge[] = [];
    entities.forEach((entity) => {
      if (entity.relationships) {
        entity.relationships.forEach((rel) => {
          edges.push({
            id: `${entity.entity_id}-${rel.target_id}`,
            source: entity.entity_id,
            target: rel.target_id,
            label: rel.type,
            type: 'smoothstep',
            animated: false,
            style: { stroke: '#888', strokeWidth: 1 },
            labelStyle: { fontSize: '9px', fill: '#5C5C5C' },
          });
        });
      }
    });
    return edges;
  }, [entities]);

  const [nodes, , onNodesChange] = useNodesState(initialNodes);
  const [edges, , onEdgesChange] = useEdgesState(initialEdges);

  return (
    <div style={{ width: '100%', height: `${height}px`, border: '1px solid #D0D7DE', borderRadius: '4px' }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={nodeTypes}
        fitView
      >
        <Background color="#f5f5f5" />
        <Controls showInteractive={false} />
      </ReactFlow>
    </div>
  );
}
