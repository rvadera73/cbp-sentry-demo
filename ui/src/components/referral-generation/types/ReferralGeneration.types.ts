/**
 * Referral Package Generation - Complete Type Definitions
 * Supports Tab 1 (Display) and Tab 2 (Officer Analysis Form)
 */

// ============================================================================
// TAB 1: REFERRAL DISPLAY TYPES
// ============================================================================

export interface ReferralDisplayData {
  referral_id: string;
  shipment_id: string;
  created_at: string;
  risk_score: number;
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  risk_breakdown?: RiskBreakdown;
  sections: Record<string, any>;
  edited_sections?: Record<string, EditedSection>;
  analyzed_sections?: Record<string, AnalyzedSection>;
  overall_confidence?: number;
}

export interface AnalyzedSection {
  section_id: string;
  raw_data: any;
  analysis: {
    narrative: string;
    risk_factors: Array<{
      factor: string;
      level: 'HIGH' | 'MEDIUM' | 'LOW';
      evidence: string;
    }>;
    confidence_score: number;
  };
  narrative?: string;
  risk_factors?: Array<{
    factor: string;
    level: 'HIGH' | 'MEDIUM' | 'LOW';
    evidence: string;
  }>;
  confidence_score?: number;
}

export interface RiskBreakdown {
  final_score: number;
  components: RiskComponent[];
}

export interface RiskComponent {
  component: string;
  factor: string;
  score: number;
  weight: number;
  weighted_result: number;
  rationale: string;
  evidence: string[];
}

export interface EditedSection {
  original_content: string;
  edited_content: string;
  edited_at: string;
  edited_by: string;
  regeneration_count: number;
}

export interface NarrativeSection {
  section_id: 'section_3_6' | 'section_3_7' | 'section_3_11' | 'section_3_14';
  title: string;
  current_narrative: string;
  is_edited: boolean;
  can_regenerate: boolean;
}

// ============================================================================
// TAB 2: OFFICER ANALYSIS FORM TYPES
// ============================================================================

export interface Step1RiskAssessment {
  agreeWithScore: boolean;
  officerScore?: number;
  adjustmentReason?: string;
  confidence: 'low' | 'medium' | 'high';
  validationErrors?: string[];
}

export interface Step2EvidenceReview {
  reviewedItems: Record<string, EvidenceItem>;
  allCriticalReviewed: boolean;
  validationErrors?: string[];
}

export interface EvidenceItem {
  reviewed: boolean;
  notes?: string;
  isCritical: boolean;
}

export interface Step3ActionRecommendation {
  action: 'execute_trled' | 'hold_examine' | 'release_monitor';

  // TRLED Referral fields
  referralType?: 'EAPA' | 'Duty_Evasion' | 'Fraud' | 'Other';
  priority?: 'low' | 'medium' | 'high';
  holdingPeriodDays?: number;
  assignedDistrict?: string;
  examinerNotes?: string;

  // Hold for Examination fields
  holdDurationDays?: number;
  examinationType?: 'documentary' | 'physical' | 'hybrid';
  examinationScope?: string;
  notifyImporter?: boolean;

  // Release with Monitoring fields
  monitoringType?: 'standard' | 'enhanced' | 'realtime';
  monitoringDurationDays?: number;
  conditions?: string;
  auditTrailFlag?: boolean;

  validationErrors?: string[];
}

export interface Step4OfficeSignature {
  caseNarrative: string;
  certificationAccepted: boolean;
  officerId: string;
  officerName: string;
  badgeNumber: string;
  district: string;
  signature?: string;
  signedAt?: string;
  validationErrors?: string[];
}

export interface OfficerAnalysisFormData {
  referral_id: string;
  analysis_id?: string;
  step1: Step1RiskAssessment;
  step2: Step2EvidenceReview;
  step3: Step3ActionRecommendation;
  step4: Step4OfficeSignature;
  current_step: number;
  form_status: 'draft' | 'in_progress' | 'submitted';
  last_saved_at?: string;
  submitted_at?: string;
}

// ============================================================================
// COMPONENT PROPS
// ============================================================================

export interface ReferralPackageGenerationTabProps {
  shipmentId: string;
  onClose?: () => void;
}

export interface ReferralDisplayPanelProps {
  referralData: ReferralDisplayData;
  onNarrativeEdit?: (sectionId: string, editedContent: string) => void;
  onExportPDF?: () => void;
}

export interface ReferralSectionProps {
  sectionId: string;
  title: string;
  content: any;
  isNarrativeSection?: boolean;
  isEdited?: boolean;
  onEditNarrative?: (sectionId: string) => void;
}

export interface NarrativeEditModalProps {
  section: NarrativeSection;
  referralId: string;
  onSave: (editedContent: string) => void;
  onRegenerate: () => Promise<string>;
  onClose: () => void;
  isRegenerating?: boolean;
}

export interface OfficerAnalysisFormProps {
  referralId: string;
  referralData: ReferralDisplayData;
  initialData?: OfficerAnalysisFormData;
  onSubmit: (formData: OfficerAnalysisFormData) => Promise<void>;
  onCancel?: () => void;
}

export interface Step1Props {
  data: Step1RiskAssessment;
  currentRiskScore: number;
  onChange: (data: Step1RiskAssessment) => void;
  onNext: () => boolean;
}

export interface Step2Props {
  data: Step2EvidenceReview;
  onChange: (data: Step2EvidenceReview) => void;
  onNext: () => boolean;
}

export interface Step3Props {
  data: Step3ActionRecommendation;
  onChange: (data: Step3ActionRecommendation) => void;
  onNext: () => boolean;
}

export interface Step4Props {
  data: Step4OfficeSignature;
  onChange: (data: Step4OfficeSignature) => void;
  onSubmit: () => boolean;
  isSubmitting?: boolean;
}

// ============================================================================
// API RESPONSE TYPES
// ============================================================================

export interface GenerateReferralResponse {
  status: 'success' | 'error';
  referral?: ReferralDisplayData;
  error?: string;
}

export interface SaveOfficerAnalysisResponse {
  status: 'success' | 'error';
  analysis_id?: string;
  message?: string;
  error?: string;
}

export interface ExportPDFResponse {
  status: 'success' | 'error';
  pdf_url?: string;
  error?: string;
}

// ============================================================================
// UTILITY TYPES
// ============================================================================

export interface FormValidationError {
  step: number;
  field: string;
  message: string;
}

export interface PDFExportOptions {
  includeAnalysis: boolean;
  includeAnnotations: boolean;
  fileName?: string;
}

export const EVIDENCE_ITEMS = [
  {
    id: 'isf_element9_mismatch',
    label: 'ISF Element 9 Mismatch',
    description: 'Container stuffing country vs declared origin',
    isCritical: true
  },
  {
    id: 'vessel_dwell_anomaly',
    label: 'Vessel Dwell Time Anomaly',
    description: 'Port dwell exceeds commodity baseline',
    isCritical: true
  },
  {
    id: 'price_variance',
    label: 'Price Variance Analysis',
    description: 'Unit price vs market baseline',
    isCritical: true
  },
  {
    id: 'entity_resolution',
    label: 'Entity Resolution Report',
    description: 'Party identity and ownership chain',
    isCritical: true
  },
  {
    id: 'ais_routing_pattern',
    label: 'AIS Routing Pattern Analysis',
    description: 'Port call sequences and anomalies',
    isCritical: false
  },
  {
    id: 'historical_imports',
    label: 'Historical Import Patterns',
    description: 'Shipper profile and trends',
    isCritical: false
  },
  {
    id: 'related_cases',
    label: 'Related Cases & Precedents',
    description: 'Similar shipments and outcomes',
    isCritical: false
  }
];

export const ACTION_OPTIONS = [
  {
    id: 'execute_trled',
    label: 'Execute TRLED Referral',
    description: 'Refer to EAPA or enforcement unit',
    color: 'danger'
  },
  {
    id: 'hold_examine',
    label: 'Hold for Examination',
    description: 'Physical or documentary exam on arrival',
    color: 'warning'
  },
  {
    id: 'release_monitor',
    label: 'Release with Monitoring',
    description: 'Release cargo with follow-up monitoring',
    color: 'info'
  }
];
