/**
 * CBP Sentry V2 Wireframe UI Type Definitions
 * Maps from API responses to wireframe display models
 */

export interface CBPOfficer {
  id: string;
  name: string;
  badge: string;
  role: string;
  email: string;
  shift: string;
  avatar: string;
}

export interface Case {
  case_id: string;
  case_name: string;
  target_entity: string;
  risk_score: number;
  /** Original seeded/estimated risk score before model scoring */
  seed_risk_score?: number;
  /** Canonical score from the 7-factor engine. Prefer over risk_score when present. */
  calculated_risk_score?: number;
  model_version?: string;
  model_maturity?: number;           // e.g. 15 = 15% maturity
  risk_score_calculated_at?: string;
  /** Validation note explaining score source and any discrepancy */
  score_validation?: { status: string; message: string; maturity_note?: string; seed_score?: number; model_score?: number };
  assigned_officer: string;
  investigation_stage: 'Overview' | 'Entities' | 'Shipments' | 'AI Findings' | 'Evidence & Referral';
  case_status: 'Active' | 'Under Audit' | 'Referral Prepared' | 'Enforced' | 'Closed';
  referral_status: 'Not Initiated' | 'In Progress' | 'Awaiting Approval' | 'Approved' | 'Submitted';
  priority: 'Critical' | 'High' | 'Medium' | 'Low';
  opened_date: string;
  sla_timer: string;
  product_category: string;
  ai_confidence: number;
  ai_synopsis?: string;

  // Commodity & Corridor Context
  commodity_code?: string;
  commodity_name?: string;
  origin_country?: string;
  destination_country?: string;

  // Scoring Components
  h1_score?: number;
  h2_score?: number;
  h3_score?: number;

  // Tariff & Trade Context
  ad_cvd_applicable?: boolean;
  ad_cvd_rate?: number;

  // Shipment Context
  shipper_age_months?: number;
  declared_weight_kg?: number;
  dwell_days?: number;

  // Anomaly Signals
  manifest_anomalies?: string[];
}

export type EntityType = 'Importer' | 'Exporter' | 'Intermediary' | 'Manufacturer' | 'Shell Company' | 'Broker';

export interface TradeEntity {
  entity_id: string;
  entity_type: EntityType;
  entity_name: string;
  country: string;
  risk_level: 'Critical' | 'High' | 'Medium' | 'Low' | 'Verified';
  sanctions_status: 'None' | 'Match Found' | 'Under Investigation' | 'Blocked list';
  known_affiliations: string[];
  enforcement_history: string;
  ownership_indicators: string;
  registration_status: string;
  watchlist_status: string;
  address: string;
  tax_id: string;
  phone: string;
  shared_identifiers: string[];
  entity_chain?: Array<{
    entity_id: string | number;
    name: string;
    country: string;
    entity_type: string;
    role: string;
    confidence: number;
    relationships?: Array<{
      type: string;
      target: string;
      confidence: number;
    }>;
    data_source?: string;
  }>;
  parties?: Array<{
    entity: string;
    role: string;
    country: string;
  }>;
}

export interface Shipment {
  shipment_id: string;
  origin_country: string;
  destination_country: string;
  declared_origin: string;
  suspected_origin: string;
  product_code: string;
  product_description: string;
  route: string[];
  container_id: string;
  manifest_data: {
    shipper: string;
    consignee: string;
    weight_kg: number;
    declared_value_usd: number;
    carrier: string;
    vessel: string;
    voyage_number: string;
    bill_of_lading: string;
  };
  manifest_anomalies: string[];
  ai_anomaly_score: number;
  customs_flags: string[];
  inspection_history: string;
  date: string;

  // API Fields for Data Integration
  hs_code?: string;
  commodity_name?: string;
  h1_score?: number;
  h2_score?: number;
  h3_score?: number;
  h1_risk_level?: string;
  h2_signals?: string[];
  h3_recommendation?: string;
  element9_is_mismatch?: boolean;
  element9_declared_country?: string;
  element9_actual_country?: string;
  shipper_name?: string;
  shipper_country?: string;
  shipper_age_months?: number;
  dwell_days?: number;
  ad_cvd_applicable?: boolean;
  ad_cvd_rate?: number;
  port_calls?: string[];
  vessel_name?: string;
  vessel_imo?: string;
  risk_score?: number;

  // Shipping Intelligence Fields (Trade Analyst View)
  cbp_corridor?: {
    route: string; // "CN→US", "VN→US", etc
    risk_profile: string; // "TARIFF_EVASION", "ORIGIN_CONCEALMENT", "EXPORT_CONTROL"
    corridor_risk_score: number; // Country pair baseline risk
    applicable_duties: {
      duty_type: string; // "Section 301", "AD/CVD", "UFLPA"
      rate: number; // Percentage
    }[];
  };

  isf_filing?: {
    status: 'FILED' | 'AMENDED' | 'PENDING' | 'DISCREPANCY';
    filed_date?: string;
    filer_code?: string;
    amendments?: number;
    discrepancies?: Array<{
      field: string; // "Element 9", "Weight", "Value"
      filed_value: string;
      actual_value: string;
      severity: 'CRITICAL' | 'HIGH' | 'MEDIUM';
    }>;
  };

  vessel_tracking?: {
    ais_status: 'ACTIVE' | 'INACTIVE' | 'SPOOFING_DETECTED';
    last_known_location?: {
      lat: number;
      lon: number;
      port?: string;
      timestamp?: string;
    };
    eta_port_of_entry?: string; // Date/time
    days_to_arrival?: number;
    voyage_milestones?: Array<{
      milestone: string; // "Departed Origin", "Transshipment", "Approaching POE"
      location: string;
      timestamp: string;
    }>;
  };

  port_of_entry?: {
    port_code: string; // "USNYC", "USLA", etc
    port_name: string; // "Port of New York/New Jersey"
    expected_arrival: string;
    dwell_days?: number;
    inspection_status?: 'NONE' | 'REQUESTED' | 'SCHEDULED' | 'COMPLETED';
  };

  pricing_analysis?: {
    declared_value_usd: number;
    declared_weight_kg: number;
    unit_price_per_kg: number;
    benchmark_price_per_kg?: number;
    price_variance_percent?: number; // Negative = underpriced
    value_flag?: 'LOW' | 'NORMAL' | 'HIGH';
  };

  consignee_profile?: {
    prior_imports: number;
    prior_violations?: number;
    import_history: string; // "New importer", "Established", "High volume"
    compliance_rating?: 'VERIFIED' | 'COMPLIANT' | 'AT_RISK' | 'BLOCKED';
  };

  // Risk Scoring Breakdown (Detailed ML Model)
  risk_breakdown?: {
    components: Array<{
      component: string; // e.g., "Documentation Risk"
      factor: string; // e.g., "documentation"
      score: number; // 0-10
      weight: number; // Percentage (0-100)
      weighted_result: number; // score * weight / 10
      rationale: string;
      evidence?: string[];
    }>;
    subtotal: number; // Sum of weighted components
    corridor_risk_adjustment?: {
      baseline: number;
      multiplier: number;
      adjustment_points: number;
      reason: string;
    };
    additional_adjustments?: Array<{
      adjustment_type: string;
      points: number;
      reason: string;
    }>;
    final_score: number; // 0-100
    confidence_interval: string; // e.g., "85.0±2.5"
  };

  // Altana Validation Audit Trail
  audit_trail?: {
    initial_score: number;
    altana_query: boolean;
    altana_confidence?: number; // 0-100
    altana_response?: {
      risk_factors: string[];
      recommendation: string;
      supply_chain_opacity?: number;
      sanctions_exposure?: boolean;
    };
    model_adjustment: number;
    final_risk_score: number;
    adjustment_reason: string;
    timestamp: string;
  };

  // AI Synthesis
  ai_synthesis?: {
    summary: string;
    key_factors: string[];
    altana_validation?: any;
  };

  /** Canonical score from 7-factor engine — prefer over risk_score when present */
  calculated_risk_score?: number;
  /** Original seeded/estimated risk score before model scoring */
  seed_risk_score?: number;
  model_version?: string;
  model_maturity?: number;
  risk_score_calculated_at?: string;
  /** Validation note explaining score source and any discrepancy */
  score_validation?: { status: string; message: string; maturity_note?: string; seed_score?: number; model_score?: number };
}

export interface AIFinding {
  finding_id: string;
  title: string;
  confidence: number;
  finding_type: 'Origin Concealment' | 'Circular Invoicing' | 'Shell Conglomerate' | 'Routing Deviation' | 'Identity Cloning' | 'Tariff Evasion';
  severity: 'Critical' | 'High' | 'Medium';
  explanation: string;
  evidence_links: string[];
  verification_status: 'Accepted' | 'Rejected' | 'Needs Review';
}

export interface ReferralPackage {
  referral_id: string;
  shipment_id: string;
  manifest_id?: string;
  created_at: string;
  risk_score: number;
  risk_level: string;

  // CSOP sections
  sections: Record<string, any>;

  // Risk breakdown
  risk_breakdown?: {
    final_score: number;
    components: Array<{
      component: string;
      score: number;
      weight: number;
      weighted_result: number;
      rationale?: string;
      evidence?: string;
    }>;
  };

  // Legacy fields for backward compatibility
  case_id?: string;
  package_status?: 'Draft' | 'Supervisor Review' | 'DHS Approved' | 'Submitted';
  generated_date?: string;
  approval_state?: string;
  evidence_inventory_ids?: string[];
  narrative?: {
    executive_summary?: string;
    subject_overview?: string;
    investigation_findings?: string;
    trade_pattern_analysis?: string;
    evidence_summary?: string;
    applicable_violations?: string;
    recommended_enforcement?: string;
  };
  corridor_context?: {
    origin: string;
    destination: string;
    ad_cvd_rate?: number;
    commodity_name: string;
    h1_risk_level: string;
  };
  scenarios?: Array<{
    scenario: string;
    impact: string;
    revised_score: number;
    confidence: string;
  }>;
  risk_indicators?: Array<{
    indicator: string;
    present: boolean;
    evidence: string;
    authority: string;
  }>;
}

export interface ThreatFeedEvent {
  id: string;
  severity: 'Critical' | 'High' | 'Medium' | 'Low';
  title: string;
  description: string;
  timestamp: string;
  confidence: number;
  related_entity?: string;
  related_case_id?: string;
}
