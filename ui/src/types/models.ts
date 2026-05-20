export interface Case {
  id: string;
  manifest_id: string;
  shipper_name: string;
  shipper_country: string;
  consignee_name: string;
  consignee_country: string;
  commodity_code: string;
  declared_value: number;
  declared_weight_kg?: number;
  risk_score: number;
  h1_score?: number;
  h2_score?: number;
  h3_score?: number;
  h1_risk_level?: string;
  h2_signals?: string[];
  h3_recommendation?: string;
  created_at: string;
  vessel_name?: string;
  port_of_origin?: string;
  port_of_destination?: string;
  [key: string]: any; // Allow for additional fields from API
}

export interface ScoreComponent {
  name: string;
  score: number;
  max_score?: number;
  max?: number;
  percentage?: number;
  pct?: number;
  factors?: string[];
  horizon?: 'H1' | 'H2' | 'H3';
}

export interface ScoreResult {
  shipment_id: string;
  total_score: number;
  confidence_tier: 'LOW' | 'MEDIUM' | 'HIGH';
  components: ScoreComponent[];
  xai_assertions: string[];
  h1_score: number;
  h2_score: number;
  h3_score: number;
}

export interface ReferralSection {
  section_number: string;
  title: string;
  content: any;
  data_source: string;
}

export interface ReferralPackage {
  shipment_id: string;
  case_number: string;
  score: ScoreResult;
  sections: ReferralSection[];
}

export interface Entity {
  id: string;
  name?: string;
  label?: string; // API may use 'label' instead of 'name'
  country: string;
  entity_type: 'SHIPPER' | 'CONSIGNEE' | 'MANUFACTURER' | 'FREIGHT_FORWARDER' | 'HOLDING_COMPANY' | 'VESSEL';
  senzing_confidence?: number;
}

export interface EntityRelationship {
  source_id: string;
  target_id: string;
  relationship_type: 'OWNED_BY' | 'DIRECTOR_SHARED' | 'SHIPS_VIA' | 'FREIGHT_FORWARDED_BY' | 'PRIOR_FILING';
  confidence: number;
  evidence: string[];
}

export interface GraphData {
  nodes: Entity[];
  edges: EntityRelationship[];
}

export interface InvestigationNote {
  id: string;
  shipment_id: string;
  content: string;
  created_at: string;
  created_by?: string;
  status: 'DRAFT' | 'SAVED' | 'SUBMITTED';
}

export interface CaseFilter {
  riskLevel?: 'HIGH' | 'MEDIUM' | 'LOW' | 'all';
  searchTerm?: string;
  sortBy?: 'risk' | 'date' | 'value';
  sortOrder?: 'asc' | 'desc';
}
