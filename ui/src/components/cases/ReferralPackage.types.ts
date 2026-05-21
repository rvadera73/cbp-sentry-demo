/**
 * ReferralPackage Type Definitions
 * Comprehensive type system for Referral Package component suite
 * CBP Sentry Illegal Transshipment Intelligence Dashboard
 */

/**
 * Entity in the supply chain
 */
export interface SupplyChainEntity {
  name: string;
  country: string;
  riskLevel: 'low' | 'medium' | 'high' | 'critical';
  entityType?: string; // e.g., "Manufacturer", "Trader", "Exporter", "Importer"
  confidence?: number;
  registrationStatus?: string;
}

/**
 * Entity chain representing the path from manufacturer to importer
 */
export interface EntityChain {
  entities: SupplyChainEntity[];
}

/**
 * Risk pipeline score component (H1, H2, H3)
 */
export interface PipelineScore {
  score: number;
  maxScore: number;
  label: string;
  algorithmicWeights?: {
    [key: string]: number;
  };
}

/**
 * Vessel tracking data point
 */
export interface VesselDataPoint {
  timestamp: string;
  port: string;
  action: 'loading' | 'unloading' | 'transshipment' | 'dwell';
  durationHours?: number;
  anomaly?: boolean;
  anomalyType?: string;
}

/**
 * Discrepancy between declared and verified information
 */
export interface Discrepancy {
  field: string;
  declared: string;
  verified: string;
  status: 'match' | 'partial' | 'missing' | 'mismatch';
  severity?: 'low' | 'medium' | 'high';
}

/**
 * Conditional scenario for what-if simulation
 */
export interface ConditionalScenario {
  condition: string;
  description: string;
  projectedScore: number;
  isActive: boolean;
  requiredEvidence?: string;
  mitigatingFactor?: string;
}

/**
 * Section 3-1: Shipment Identification
 */
export interface Section3_1_ShipmentIdentification {
  mbl: string;
  hbl: string;
  eta: string;
  pod: string;
  vessel_name: string;
  voyage_number: string;
  manifest_date: string;
  manifest_timeline?: {
    filed_date: string;
    daysBeforeArrival: number;
  };
}

/**
 * Section 3-2: Line Items
 */
export interface LineItem {
  line_number: number;
  hts_code: string;
  commodity_description: string;
  quantity: number;
  unit: string;
  declared_value: number;
  unit_price: number;
  flag?: 'HIGH' | 'MEDIUM' | 'LOW';
  flagReason?: string;
}

export interface Section3_2_LineItems {
  items: LineItem[];
  totalValue: number;
  totalQuantity: number;
  commodityCategory?: string;
}

/**
 * Section 3-3: Routing History
 */
export interface PortCall {
  port_code: string;
  port_name: string;
  country: string;
  date_arrival?: string;
  date_departure?: string;
  dwell_hours?: number;
  activity: string;
  anomaly_flags?: string[];
  ais_data_quality?: 'HIGH' | 'MEDIUM' | 'LOW';
}

export interface Section3_3_RoutingHistory {
  current_route: PortCall[];
  prior_routes?: PortCall[][];
  transshipment_indicators?: string[];
}

/**
 * Section 3-4: Parties and Roles
 */
export interface Party {
  party_id: string;
  name: string;
  country: string;
  role: 'SHIPPER' | 'CONSIGNEE' | 'MANUFACTURER' | 'FREIGHT_FORWARDER' | 'BROKER' | 'HOLDING_COMPANY';
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  confidence_score?: number;
  prior_filings?: number;
  enforcement_history?: string;
}

export interface Section3_4_PartiesAndRoles {
  parties: Party[];
  network_degree?: number;
}

/**
 * Section 3-5: Entity Ownership Chain
 */
export interface OwnershipLevel {
  level: number; // 1 = L1 (direct), 2 = L2 (parent), 3 = L3 (ultimate beneficial owner)
  entities: SupplyChainEntity[];
  confidence: number;
  evidence_count: number;
}

export interface Section3_5_EntityOwnershipChain {
  levels: OwnershipLevel[];
  ultimate_beneficial_owner?: SupplyChainEntity;
}

/**
 * Section 3-6: Historical Import Pattern
 */
export interface ImportTrend {
  period: string; // "2025-Q1", "2026-01", etc.
  volume: number;
  value: number;
  shipment_count: number;
}

export interface OriginDistribution {
  country: string;
  percentage: number;
  shipment_count: number;
}

export interface Section3_6_HistoricalPattern {
  six_month_trends?: ImportTrend[];
  origin_distribution?: OriginDistribution[];
  yoy_volume_delta?: number; // percentage change
  yoy_value_delta?: number; // percentage change
  surge_inflection_points?: string[];
  anomalies?: string[];
}

/**
 * Section 3-7: Trade Flow Intelligence
 */
export interface ShipmentCorrelation {
  other_shipment_id: string;
  case_number?: string;
  common_fields: string[];
  correlation_strength: 'HIGH' | 'MEDIUM' | 'LOW';
  shared_entity_type: string;
}

export interface PriorCaseMapping {
  case_number: string;
  similarity_score: number;
  evasion_methodology: string;
  countermeasure: string;
}

export interface Section3_7_TradeFlowIntelligence {
  correlation_matrix?: ShipmentCorrelation[];
  prior_case_mappings?: PriorCaseMapping[];
  network_degree?: number;
  degree_description?: string;
}

/**
 * Section 3-8: Document Review
 */
export interface DocumentItem {
  doc_type: string;
  doc_name: string;
  status: 'PRESENT' | 'MISSING' | 'SUSPICIOUS';
  evidence?: string;
  risk_level?: 'LOW' | 'MEDIUM' | 'HIGH';
}

export interface Section3_8_DocumentReview {
  documents: DocumentItem[];
  checklist_completion?: number; // percentage
  critical_gaps?: string[];
}

/**
 * Section 3-9: Document Consistency
 */
export interface ConsistencyCheck {
  field: string;
  source_1: string;
  source_2: string;
  match_status: 'MATCH' | 'PARTIAL' | 'MISMATCH';
  alignment_score?: number; // 0-100
}

export interface Section3_9_DocumentConsistency {
  checks: ConsistencyCheck[];
  overall_alignment_score?: number; // 0-100
}

/**
 * Section 3-10: Supplier Verification
 */
export interface SupplierCapacity {
  supplier_name: string;
  max_annual_capacity: number;
  declared_volume: number;
  actual_volume: number;
  capacity_utilization_pct?: number;
  capacity_flag?: boolean;
  evidence?: string;
}

export interface Section3_10_SupplierVerification {
  suppliers: SupplierCapacity[];
  total_capacity_gap?: number;
  critical_suppliers?: string[];
}

/**
 * Section 3-11: Risk Indicators
 */
export interface RiskIndicator {
  indicator_id: string;
  name: string;
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  legal_authority?: string; // e.g., "EAPA 19 U.S.C. 1516a", "HTS 9803.00.80"
  evidence: string;
  countermeasures?: string[];
  mitigation_pathway?: string;
}

export interface Section3_11_RiskIndicators {
  indicators: RiskIndicator[];
  critical_count?: number;
  high_count?: number;
}

/**
 * Section 3-12: Score Breakdown
 */
export interface ScoreComponent {
  component_name: string;
  score: number;
  max_score: number;
  weight_percentage?: number;
  shap_value?: number; // Feature importance
  shap_impact?: 'POSITIVE' | 'NEGATIVE';
}

export interface Section3_12_ScoreBreakdown {
  components: ScoreComponent[];
  total_score: number;
  max_score: number;
  top_contributing_factors?: ScoreComponent[];
}

/**
 * Section 3-13: What-If Scenarios
 */
export interface InteractiveScenario {
  scenario_id: string;
  title: string;
  description: string;
  baseline_score: number;
  projected_score: number;
  affected_signals?: string[];
  required_evidence?: string;
  legal_remedy?: string;
  cbp_procedure_link?: string;
}

export interface Section3_13_WhatIfScenarios {
  scenarios: InteractiveScenario[];
  baseline_score: number;
}

/**
 * Section 3-14: Data Sources and Attribution
 */
export interface DataSource {
  source_name: string;
  source_type: 'API' | 'MANUAL_ENTRY' | 'THIRD_PARTY' | 'GOVERNMENT_DB';
  confidence_percentage: number;
  last_updated?: string;
  data_points_count?: number;
}

export interface Section3_14_DataSources {
  sources: DataSource[];
  overall_confidence?: number;
}

/**
 * Props for ReferralNarrativeBanner
 */
export interface ReferralNarrativeBannerProps {
  shipper_name: string;
  shipper_country: string;
  declared_origin: string;
  actual_origin: string;
  risk_score: number;
  vessel_path: string[];
}

/**
 * Props for ReferralScorePipeline
 */
export interface ReferralScorePipelineProps {
  h1_score: PipelineScore;
  h2_score: PipelineScore;
  h3_score: PipelineScore;
}

/**
 * Props for ReferralEvidentiaryPanel
 */
export interface ReferralEvidentiaryPanelProps {
  discrepancies: Discrepancy[];
  entityChain: EntityChain;
  conditionalScenarios: ConditionalScenario[];
}

/**
 * Props for ReferralActionCenter
 */
export interface ReferralActionCenterProps {
  risk_score: number;
  onExecuteReferral: (notes: string) => void;
  onHoldExamine: (notes: string) => void;
  onOverride: (justification: string[], notes: string) => void;
}

/**
 * Complete Referral Package data structure (Legacy - for backward compatibility)
 */
export interface ReferralPackageData {
  shipper_name: string;
  shipper_country: string;
  consignee_name: string;
  declared_origin: string;
  actual_origin: string;
  risk_score: number;
  vessel_path: string[];
  h1_score: PipelineScore;
  h2_score: PipelineScore;
  h3_score: PipelineScore;
  discrepancies: Discrepancy[];
  entityChain: EntityChain;
  conditionalScenarios: ConditionalScenario[];
  // New 14-section structure
  section_3_1?: Section3_1_ShipmentIdentification;
  section_3_2?: Section3_2_LineItems;
  section_3_3?: Section3_3_RoutingHistory;
  section_3_4?: Section3_4_PartiesAndRoles;
  section_3_5?: Section3_5_EntityOwnershipChain;
  section_3_6?: Section3_6_HistoricalPattern;
  section_3_7?: Section3_7_TradeFlowIntelligence;
  section_3_8?: Section3_8_DocumentReview;
  section_3_9?: Section3_9_DocumentConsistency;
  section_3_10?: Section3_10_SupplierVerification;
  section_3_11?: Section3_11_RiskIndicators;
  section_3_12?: Section3_12_ScoreBreakdown;
  section_3_13?: Section3_13_WhatIfScenarios;
  section_3_14?: Section3_14_DataSources;
}

/**
 * Section status and metadata
 */
export interface ReferralSectionMetadata {
  section_id: string;
  section_number: string;
  title: string;
  icon: string; // Lucide icon name
  description: string;
  data_quality: 'COMPLETE' | 'PARTIAL' | 'MINIMAL';
  has_anomalies?: boolean;
  anomaly_count?: number;
}

/**
 * Override justification options
 */
export const OVERRIDE_JUSTIFICATIONS = [
  'Prior relationship with shipper',
  'Commodity alignment with shipper profile',
  'Manifest timing consistent with logistics',
  'Pricing within market range',
  'Trusted third-party verification',
] as const;

export type OverrideJustification = typeof OVERRIDE_JUSTIFICATIONS[number];
