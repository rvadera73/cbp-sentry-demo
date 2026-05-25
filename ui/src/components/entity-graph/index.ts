/**
 * Entity Graph Visualization Module
 *
 * Complete implementation for interactive entity relationship graphs with ISF enrichment.
 *
 * Components:
 * - EntityGraphVisualization: Main graph visualization with React Flow
 * - EntityNode: Custom node renderer with risk coloring
 * - ISFWarningsPanel: ISF enrichment warnings display
 *
 * Hooks:
 * - useEntityGraph: Fetch and manage entity graph data
 * - useGraphWarnings: Extract warnings from graph
 * - useEntityHighlight: Track highlighted entity
 * - useEntitySearch: Filter entities by search query
 * - useEntityRiskStyling: Calculate risk-based styling
 *
 * Utilities:
 * - entityGraphToFlowNodes: Convert entity graph to React Flow nodes
 * - entityGraphToFlowEdges: Convert entity graph to React Flow edges
 * - getEntityBorderColor: Get border color by risk
 * - getEntityBackgroundColor: Get background color by risk
 * - getEdgeColor: Get edge color by confidence
 * - formatEntityLabel: Format entity display label
 * - getWarningSeverityColor: Get warning color by severity
 * - getEntityTypeBadge: Get emoji badge for entity type
 *
 * Types:
 * - EntityNode: Entity in the chain
 * - EntityRelationship: Relationship between entities
 * - Warning: ISF enrichment warning
 * - EntityGraph: Complete entity graph structure
 * - FlowNodeData: React Flow node data
 * - FlowEdgeData: React Flow edge data
 * - ISFEnrichmentData: ISF enrichment data
 */

// Components
export { default as EntityGraphVisualization } from './EntityGraphVisualization';
export { default as EntityNode } from './EntityNode';
export { default as ISFWarningsPanel } from './ISFWarningsPanel';

// Hooks
export {
  useEntityGraph,
  useGraphWarnings,
  useEntityHighlight,
  useEntitySearch,
  useEntityRiskStyling,
} from './hooks';

// Utilities
export {
  entityGraphToFlowNodes,
  entityGraphToFlowEdges,
  getEntityBorderColor,
  getEntityBackgroundColor,
  getEdgeColor,
  formatEntityLabel,
  getWarningSeverityColor,
  getEntityTypeBadge,
} from './utils';

// Types
export type {
  EntityNodeData,
  EntityRelationship,
  Warning,
  EntityGraph,
  FlowNodeData,
  FlowEdgeData,
  ISFEnrichmentData,
} from './types';
