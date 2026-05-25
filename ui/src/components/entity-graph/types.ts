/**
 * Type definitions for entity graph visualization.
 *
 * Aligned with backend Entity interface and React Flow graph structure.
 */

export interface EntityNode {
  entity_id: string;
  name: string;
  country: string;
  entity_type: 'SHIPPER' | 'INTERMEDIARY' | 'MANUFACTURER' | 'HOLDING_COMPANY' | string;
  role: string;
  data_source: string;
  confidence: number;
  relationships: EntityRelationship[];
  risk_score?: number;
  risk_flags?: string[];
  warnings?: Warning[];
}

export interface EntityRelationship {
  type: string;
  target: string;
  confidence: number;
}

export interface Warning {
  type: 'ISF_ELEMENT_9_MISMATCH' | 'DWELL_ANOMALY' | 'NEW_SHIPPER' | string;
  severity: 'LOW' | 'MEDIUM' | 'HIGH';
  message: string;
  confidence?: number;
}

export interface EntityGraph {
  chain: EntityNode[];
  data_sources: string[];
  ofac_detected: boolean;
  risk_score: number;
  confidence_metrics?: Record<string, number>;
  shipment_id?: string;
  processing_timestamp?: string;
}

// React Flow node and edge types
export interface FlowNodeData {
  entity: EntityNode;
  level: number;
  isHighlighted?: boolean;
  hasWarnings?: boolean;
}

export interface FlowEdgeData {
  relationship: EntityRelationship;
  relationship_type: string;
}

export interface ISFEnrichmentData {
  element_9?: {
    is_mismatch: boolean;
    declared_country: string;
    actual_stuffing_country?: string;
    mismatch_confidence: number;
  };
  dwell_anomaly?: {
    dwell_days: number;
    baseline_days: number;
    anomaly_ratio: number;
  };
  new_shipper?: boolean;
  shipper_age_months?: number;
}
