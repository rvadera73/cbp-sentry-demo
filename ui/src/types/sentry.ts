/**
 * Sentry CBP TypeScript type definitions
 */

// Ingest Response
export interface ManifestIngestResponse {
  success: boolean
  manifest_id: string
  record_count: number
  row_count: number
  status: string
  message: string
  shipment_ids: string[]
  preview: Array<{
    shipper: string
    consignee: string
    hts_code: string
    quantity_kg: number
    value_usd: number
    description: string
    flag_suspicious: boolean
  }>
}

// Entity Resolution
export interface Entity {
  entity_id: number
  entity_name: string
  entity_type: 'SHIPPER' | 'MANUFACTURER' | 'CONSIGNEE' | 'HOLDING_COMPANY' | 'VESSEL' | 'FREIGHT_FORWARDER'
  senzing_confidence: number
  jurisdiction: string
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'
  matching_evidence: string[]
  prior_cbp_filings?: number
}

export interface EntityRelationship {
  entity_a_id: number
  entity_b_id: number
  relationship_type: string
  confidence: number
  evidence: string
}

export interface ERLoadResponse {
  shipment_id: string
  er_job_id: string
  status: 'RUNNING' | 'COMPLETED' | 'ERROR'
  entities_resolved: number
  entities: Entity[]
  entity_relationships: EntityRelationship[]
  neo4j_graph_url: string
  estimated_completion: string
}

// Why Response
export interface ConnectionPathStep {
  step: number
  entity_id: number
  entity_name: string
  relationship: string
}

export interface WhyResponse {
  entity_a: {
    id: number
    name: string
    country: string
  }
  entity_b: {
    id: number
    name: string
    country: string
  }
  connection_path: ConnectionPathStep[]
  connection_depth: number
  total_confidence: number
  explanation: string
  evidence: string[]
}

// Scoring
export interface ScoreComponent {
  tier: number
  component: string
  score: number
  max: number
  basis: string
}

export interface H1CorridorRisk {
  corridor_id: string
  risk_level: string
  risk_score: number
  evidence: Record<string, any>
}

export interface H2PreIntelligence {
  isf_element_9_contradiction: boolean
  stuffing_location: string
  declared_origin: string
  ais_dwell_days: number
  ais_dwell_baseline: number
  ais_anomaly_ratio: number
  ais_percentile: number
}

export interface H3ScoringBreakdown {
  total_score: number
  confidence_level: 'LOW' | 'MEDIUM' | 'HIGH'
  components: ScoreComponent[]
}

export interface ScoreResponse {
  shipment_id: string
  score_job_id: string
  h1_corridor_risk: H1CorridorRisk
  h2_pre_intelligence: H2PreIntelligence
  h3_scoring_breakdown: H3ScoringBreakdown
  recommended_action: string
  estimated_revenue_impact_usd: number
  scoring_completed_at: string
  xai_assertions?: string[]
}

// Referral Package
export interface ReferralShipmentIdentification {
  bill_of_lading: string
  shipper_name: string
  shipper_country: string
  consignee_name: string
  consignee_address: string
  port_of_lading: string
  port_of_unlading: string
  cargo_description: string
  hts_code: string
  declared_country_of_origin: string
  declared_value_usd: number
  total_weight_kg: number
}

export interface ReferralLineItem {
  line_number: number
  sku: string
  description: string
  quantity_kg: number
  unit_value_usd: number
  line_total_usd: number
}

export interface ReferralRoutingEvent {
  event: string
  location: string
  date: string
  notes: string
}

export interface ReferralEntityOwnershipChain {
  tier: number
  entity_id: number
  entity_name: string
  country: string
  ownership_percentage?: number
  director_names?: string[]
  registered_address?: string
}

export interface ReferralPackageSections {
  shipment_identification: ReferralShipmentIdentification
  line_items: ReferralLineItem[]
  routing_history: ReferralRoutingEvent[]
  parties: Entity[]
  entity_ownership_chain: ReferralEntityOwnershipChain[]
  [key: string]: any
}

export interface ReferralPackage {
  package_id: string
  created_at: string
  shipment_id: string
  manifest_id: string
  in_transit: boolean
  estimated_arrival: string
  confidence_level: string
  total_score: number
  recommended_action: string
  sections: ReferralPackageSections
}

// Graph
export interface GraphNode {
  id: string
  label: string
  type: string
  country?: string
  risk_level?: string
  senzing_confidence?: number
  prior_cbp_filings?: number
  imo?: string
  dwell_days?: number
  anomaly_flag?: boolean
  jurisdiction?: string
  risk_score?: number
}

export interface GraphLink {
  source: string
  target: string
  relationship: string
  confidence?: number
  label?: string
  dwell_days?: number
}

export interface GraphPayload {
  shipment_id: string
  nodes: GraphNode[]
  links: GraphLink[]
}

// Horizons API
export interface H1Response {
  corridor_id: string
  risk_level: string
  risk_score: number
  evidence: Record<string, any>
}

export interface H2Response {
  shipment_id: string
  isf_element_9_contradiction: boolean
  stuffing_location: string
  declared_origin: string
  ais_dwell_days: number
  ais_dwell_baseline: number
  ais_anomaly_ratio: number
  ais_percentile: number
}

// Manifest row for display
export interface ManifestRow {
  rowNumber: number
  shipperName: string
  shipperCountry: string
  consigneeName: string
  htsCode: string
  declaredOrigin: string
  declaredValue: number
  status: string
}

export interface APIResponse<T> {
  success: boolean
  data?: T
  error?: string
  message?: string
}

export interface HealthCheck {
  status: 'healthy' | 'unhealthy'
  environment: string
  debug: boolean
}

// Shipments Hub
export interface Shipment {
  id: number
  manifest_id: string
  shipper_name: string
  shipper_country: string
  shipper_city: string
  shipper_lat: number
  shipper_lon: number
  consignee_name: string
  consignee_country: string
  consignee_city: string
  consignee_lat: number
  consignee_lon: number
  commodity_code: string
  commodity_name: string
  declared_value: number
  risk_score: number
  h1_risk_level: string
  h2_signals: string[]
  h3_recommendation: string
  status: string
  created_at?: string
}

export interface ShipmentsResponse {
  total: number
  limit: number
  offset: number
  shipments: Shipment[]
}

export interface ShipmentsStats {
  total: number
  highRisk: number
  mediumRisk: number
  lowRisk: number
  topOrigins: Array<{ country: string; count: number }>
  topDestinations: Array<{ country: string; count: number }>
}

export interface ShipmentRoute {
  id: number
  manifestId: string
  shipperName: string
  from: { lat: number; lon: number }
  consigneeName: string
  to: { lat: number; lon: number }
  riskScore: number
  status: string
}
