/**
 * Utility functions for entity graph visualization.
 *
 * Handles conversion to React Flow format, layout calculations, and styling.
 */

import { Node, Edge } from 'reactflow';
import { EntityGraph, EntityNode, EntityRelationship, FlowNodeData, FlowEdgeData } from './types';

/**
 * Convert entity graph to React Flow nodes.
 *
 * Creates hierarchical layout with:
 * - Level 1 (Shipper) at top
 * - Level 2 (Intermediary) in middle
 * - Level 3 (Manufacturer) at bottom
 */
export function entityGraphToFlowNodes(graph: EntityGraph): Node<FlowNodeData>[] {
  const nodes: Node<FlowNodeData>[] = [];
  const nodeWidth = 280;
  const nodeHeight = 120;
  const verticalSpacing = 200;
  const horizontalSpacing = 100;

  graph.chain.forEach((entity, index) => {
    const node: Node<FlowNodeData> = {
      id: entity.entity_id,
      data: {
        entity,
        level: index,
        hasWarnings: (entity.warnings ?? []).length > 0,
      },
      position: {
        x: 0,
        y: index * verticalSpacing,
      },
      style: {
        width: nodeWidth,
        height: nodeHeight,
        border: `2px solid ${getEntityBorderColor(entity)}`,
        borderRadius: '8px',
        background: getEntityBackgroundColor(entity),
        padding: '12px',
        fontSize: '12px',
      },
    };

    nodes.push(node);
  });

  // Center nodes horizontally
  nodes.forEach((node) => {
    node.position.x = -nodeWidth / 2;
  });

  return nodes;
}

/**
 * Convert entity graph to React Flow edges.
 *
 * Creates edges between consecutive levels based on relationships.
 */
export function entityGraphToFlowEdges(graph: EntityGraph): Edge<FlowEdgeData>[] {
  const edges: Edge<FlowEdgeData>[] = [];

  for (let i = 0; i < graph.chain.length - 1; i++) {
    const source = graph.chain[i];
    const target = graph.chain[i + 1];

    // Get relationship between source and target
    const relationship = source.relationships.find(
      (rel) => rel.target.toLowerCase() === target.name.toLowerCase()
    );

    if (relationship) {
      const edge: Edge<FlowEdgeData> = {
        id: `${source.entity_id}-${target.entity_id}`,
        source: source.entity_id,
        target: target.entity_id,
        data: {
          relationship,
          relationship_type: relationship.type,
        },
        label: `${relationship.type}\n(${(relationship.confidence * 100).toFixed(0)}%)`,
        animated: relationship.confidence >= 0.9,
        style: {
          strokeWidth: 2,
          stroke: getEdgeColor(relationship.confidence),
        },
        markerEnd: { type: 'arrowclosed', color: getEdgeColor(relationship.confidence) },
      };

      edges.push(edge);
    }
  }

  return edges;
}

/**
 * Get border color for entity node based on risk level.
 */
export function getEntityBorderColor(entity: EntityNode): string {
  const riskScore = entity.risk_score ?? 0;

  if (riskScore >= 80) return '#d32f2f'; // RED
  if (riskScore >= 60) return '#f57c00'; // ORANGE
  if (riskScore >= 40) return '#fbc02d'; // YELLOW
  return '#388e3c'; // GREEN
}

/**
 * Get background color for entity node.
 */
export function getEntityBackgroundColor(entity: EntityNode): string {
  // Light red for high risk
  if ((entity.risk_score ?? 0) >= 80) return '#ffebee';
  // Light orange for medium risk
  if ((entity.risk_score ?? 0) >= 60) return '#fff3e0';
  // Light yellow for moderate risk
  if ((entity.risk_score ?? 0) >= 40) return '#fffde7';
  // Light green for low risk
  return '#f1f8e9';
}

/**
 * Get edge color based on confidence level.
 */
export function getEdgeColor(confidence: number): string {
  if (confidence >= 0.95) return '#1976d2'; // Strong blue
  if (confidence >= 0.85) return '#0288d1'; // Blue
  if (confidence >= 0.75) return '#00bcd4'; // Cyan
  return '#4dd0e1'; // Light cyan
}

/**
 * Format entity display label.
 */
export function formatEntityLabel(entity: EntityNode): string {
  return `${entity.name}\n${entity.country} • ${entity.role}\n${(entity.confidence * 100).toFixed(0)}% confidence`;
}

/**
 * Get warning severity color.
 */
export function getWarningSeverityColor(severity: string): string {
  switch (severity) {
    case 'HIGH':
      return '#d32f2f';
    case 'MEDIUM':
      return '#f57c00';
    case 'LOW':
      return '#fbc02d';
    default:
      return '#666';
  }
}

/**
 * Get entity type icon/badge.
 */
export function getEntityTypeBadge(entityType: string): string {
  const badges: Record<string, string> = {
    SHIPPER: '📦',
    INTERMEDIARY: '🏢',
    MANUFACTURER: '🏭',
    HOLDING_COMPANY: '💼',
    OFAC: '⚠️',
  };

  return badges[entityType] ?? '🔷';
}
