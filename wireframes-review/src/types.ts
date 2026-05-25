/**
 * CBP Illegal Transshipment Sentry Platform Data Models
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
  assigned_officer: string;
  investigation_stage: 'Overview' | 'Entities' | 'Shipments' | 'AI Findings' | 'Referral';
  case_status: 'Active' | 'Under Audit' | 'Referral Prepared' | 'Enforced' | 'Closed';
  referral_status: 'Not Initiated' | 'In Progress' | 'Awaiting Approval' | 'Approved' | 'Submitted';
  priority: 'Critical' | 'High' | 'Medium' | 'Low';
  opened_date: string;
  sla_timer: string; // e.g. "12 days left"
  product_category: string;
  ai_confidence: number;
  ai_synopsis?: string;
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
  shared_identifiers: string[]; // List of other entity IDs sharing address or phone
}

export interface Shipment {
  shipment_id: string;
  origin_country: string;
  destination_country: string;
  declared_origin: string; // e.g., Vietnam
  suspected_origin: string; // e.g., China (restricted)
  product_code: string;
  product_description: string;
  route: string[]; // e.g. ["Ningbo", "Hai Phong", "Los Angeles"]
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
  ai_anomaly_score: number; // 0-100
  customs_flags: string[];
  inspection_history: string;
  date: string;
}

export interface AIFinding {
  finding_id: string;
  title: string;
  confidence: number;
  finding_type: 'Origin Concealment' | 'Circular Invoicing' | 'Shell Conglomerate' | 'Routing Deviation' | 'Identity Cloning';
  severity: 'Critical' | 'High' | 'Medium';
  explanation: string;
  evidence_links: string[]; // Case evidence references
  verification_status: 'Accepted' | 'Rejected' | 'Needs Review';
}

export interface ReferralPackage {
  referral_id: string;
  case_id: string;
  package_status: 'Draft' | 'Supervisor Review' | 'DHS Approved' | 'Submitted';
  generated_date: string;
  approval_state: string;
  evidence_inventory_ids: string[]; // Shipment and entities ids
  narrative: {
    executive_summary?: string;
    subject_overview?: string;
    investigation_findings?: string;
    trade_pattern_analysis?: string;
    evidence_summary?: string;
    applicable_violations?: string;
    recommended_enforcement?: string;
  };
}

export interface ThreatFeedEvent {
  id: string;
  severity: 'Critical' | 'High' | 'Medium';
  title: string;
  description: string;
  timestamp: string;
  confidence: number;
  related_entity?: string;
  related_case_id?: string;
}
