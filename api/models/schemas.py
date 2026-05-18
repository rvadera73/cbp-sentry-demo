"""
Pydantic schemas for request/response validation
"""
from pydantic import BaseModel
from typing import List, Optional, Any, Dict


class ManifestRow(BaseModel):
    """Single row from manifest"""
    shipper: str
    consignee: str
    hts_code: str
    quantity_kg: float
    value_usd: float
    description: str
    flag_suspicious: bool = False


class ManifestIngestRequest(BaseModel):
    """Request to ingest a manifest"""
    manifest_id: str
    source: str
    data: Dict[str, Any]


class ManifestIngestResponse(BaseModel):
    """Response from manifest ingest"""
    success: bool
    manifest_id: str
    record_count: int
    status: str
    message: Optional[str] = None
    row_count: Optional[int] = None
    shipment_ids: Optional[List[str]] = None
    preview: Optional[List[ManifestRow]] = None


class EntityResolutionRequest(BaseModel):
    """Request for entity resolution"""
    manifest_id: str


class EntityResolutionResult(BaseModel):
    """Single entity resolution result"""
    record_id: int
    entity_type: str
    confidence: float
    resolved_data: Dict[str, Any]


class ScoringRequest(BaseModel):
    """Request for risk scoring"""
    entity_id: int


class ScoreResponse(BaseModel):
    """Risk score response"""
    success: bool
    entity_id: int
    risk_score: float
    threat_score: float
    risk_level: str


class WhyResponse(BaseModel):
    """Explanation response"""
    success: bool
    entity_id: int
    risk_score: float
    risk_level: str
    explanation: str
    factors: List[str]
    recommendations: List[str]


class ReferralPackage(BaseModel):
    """Referral package for downstream systems"""
    referral_id: str
    entity_id: int
    risk_score: float
    risk_level: str
    recommended_action: str
    package_data: Dict[str, Any]


class GraphNode(BaseModel):
    """Node in knowledge graph"""
    id: str
    label: str
    type: str
    properties: Dict[str, Any]


class GraphEdge(BaseModel):
    """Edge in knowledge graph"""
    source: str
    target: str
    relationship_type: str
    weight: float


class GraphPayload(BaseModel):
    """Knowledge graph payload"""
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    metadata: Dict[str, Any]


# ===== Scoring Pipeline Schemas =====

class ScoreComponent(BaseModel):
    """Single component of multi-tier score"""
    name: str
    tier: int
    score: float
    max: float
    percentage: float
    description: str


class XAIAssertion(BaseModel):
    """Explainable AI assertion with evidence"""
    text: str
    source: str
    confidence: float = 0.85


class BBNPosteriors(BaseModel):
    """Bayesian Belief Network posterior probabilities"""
    entity_linked_to_cn_parent: Optional[float] = None
    shipper_age_very_new: Optional[float] = None
    ad_cvd_active: Optional[float] = None
    stuffing_coo_mismatch: Optional[float] = None
    price_below_market: Optional[float] = None
    ais_dwell_anomaly: Optional[float] = None
    origin_doc_fraudulent: Optional[float] = None
    time_critical: Optional[float] = None


class ScoreResponse(BaseModel):
    """4-tier ML scoring pipeline response"""
    total_score: float
    confidence_tier: str  # LOW, MEDIUM, HIGH
    components: List[ScoreComponent]
    xai_assertions: List[XAIAssertion]
    bbn_posteriors: Optional[BBNPosteriors] = None
    revenue_impact_usd: float = 0.0


# ===== Entity Resolution Schemas =====

class EntityResolution(BaseModel):
    """Single entity resolution result from Senzing"""
    entity_id: str
    entity_name: str
    entity_type: str
    country: str
    jurisdiction: str
    confidence: float
    senzing_record_id: str
    risk_score: int
    matches: List[Dict[str, Any]] = []
    metadata: Dict[str, Any] = {}


class EntityRelationship(BaseModel):
    """Relationship between two entities"""
    source: str
    target: str
    relationship_type: str
    confidence: float
    evidence: List[str] = []


class ERLoadRequest(BaseModel):
    """Request to load entities from manifest"""
    manifest_id: str


class ERLoadResponse(BaseModel):
    """Response from entity loading"""
    entities_loaded: int
    resolutions: List[EntityResolution]
    relationships: List[EntityRelationship]
    summary: Dict[str, Any]


class WhyExplanation(BaseModel):
    """Why-explanation for entity connection"""
    why_key: str
    entity_a: str
    entity_b: str
    confidence: float
    explanation: str
    evidence: List[Dict[str, Any]] = []


class GraphNodePayload(BaseModel):
    """Node in entity graph response"""
    id: str
    label: str
    type: str
    risk_score: int
    jurisdiction: str
    metadata: Dict[str, Any] = {}
    position: Optional[Dict[str, float]] = None


class GraphEdgePayload(BaseModel):
    """Edge in entity graph response"""
    source: str
    target: str
    relationship_type: str
    confidence: float
    label: Optional[str] = None


class EntityGraphPayload(BaseModel):
    """Entity resolution graph response"""
    nodes: List[GraphNodePayload]
    edges: List[GraphEdgePayload]
    metadata: Dict[str, Any] = {}


class WhyConnectedResponse(BaseModel):
    """Why-connected explanation response"""
    entity_a: str
    entity_b: str
    relationship_chain: List[Dict[str, Any]] = []
    explanation: str
    evidence: List[Dict[str, Any]] = []
    confidence: float


# ===== Referral Package Schemas (Phase 4) =====

class ShipmentIdentification(BaseModel):
    """Table 3-1: Shipment Identification"""
    bill_id: str
    manifest_id: str
    shipper: str
    shipper_country: str
    consignee: str
    consignee_country: str
    hts_code: str
    hts_description: str
    declared_value_usd: float
    total_weight_kg: float
    weight_mt: float
    vessel_name: str
    port_of_lading: str
    port_of_discharge: str
    eta: str


class LineItem(BaseModel):
    """Table 3-2: Line Items"""
    sku: str
    description: str
    quantity_kg: float
    hts_code: str
    weight_mt: float
    declared_value_usd: float
    duty_rate: float
    estimated_duty_usd: float


class RoutingHistoryEntry(BaseModel):
    """Table 3-3: Routing History"""
    location: str
    country: str
    date: str
    event: str
    ais_anomaly: bool = False
    dwell_days: Optional[float] = None
    baseline_days: Optional[float] = None
    anomaly_ratio: Optional[float] = None


class Party(BaseModel):
    """Table 3-4: Parties"""
    role: str
    name: str
    country: str
    senzing_id: int
    risk_score: float
    confidence: float


class OwnershipChainLevel(BaseModel):
    """Table 3-5: Entity Ownership Chain"""
    level: int
    entity: str
    jurisdiction: str
    relationship: str
    confidence: float


class ImportPatternMonth(BaseModel):
    """Table 3-6: Import Pattern"""
    month: str
    shipments: int
    weight_kg: float
    declared_origin: str
    unit_value: float


class TradeFlowContext(BaseModel):
    """Table 3-7: Trade Flow Context"""
    hts_code: str
    ad_cvd_status: str
    china_rate: float
    vietnam_rate: float
    duty_evasion_incentive: str
    trade_corridor_risk: str


class DocumentType(BaseModel):
    """Table 3-8: Document Review"""
    type: str
    filed_date: str
    shipper_declared: Optional[str] = None
    origin_declared: Optional[str] = None
    element_9: Optional[str] = None
    status: Optional[str] = None


class DocumentConsistencyIssue(BaseModel):
    """Table 3-9: Document Consistency"""
    issue: str
    type: str
    evidence: str


class ManufacturingVerification(BaseModel):
    """Table 3-10: Manufacturing Verification"""
    true_manufacturer: str
    factory_location: str
    facility_confirmed: bool
    production_records: str
    certificates: str
    prior_filings: int


class RiskIndicator(BaseModel):
    """Table 3-11: Risk Indicators"""
    indicator: str
    severity: str
    evidence: str
    confidence: float


class ScoreComponentDetail(BaseModel):
    """Single component in Table 3-12 breakdown"""
    name: str
    tier: int
    score: float
    max: float
    percentage: float
    description: str


class ScoreBreakdown(BaseModel):
    """Table 3-12: Score Breakdown"""
    total: int
    confidence_tier: str
    components: List[ScoreComponentDetail]


class WhatIfScenario(BaseModel):
    """Table 3-13: What-If Scenarios"""
    scenario: str
    assumption: str
    expected_score: int
    key_differences: str


class DataSource(BaseModel):
    """Table 3-14: Data Sources"""
    name: str
    confidence: float
    data_element: str


class ReferralPackageSections(BaseModel):
    """All sections (Tables 3-1 through 3-14)"""
    shipment_id: ShipmentIdentification
    line_items: List[LineItem]
    routing_history: List[RoutingHistoryEntry]
    parties: List[Party]
    ownership_chain: List[OwnershipChainLevel]
    import_pattern: List[ImportPatternMonth]
    trade_flow: TradeFlowContext
    document_review: List[DocumentType]
    document_consistency: List[DocumentConsistencyIssue]
    manufacturing_verification: ManufacturingVerification
    risk_indicators: List[RiskIndicator]
    score_breakdown: ScoreBreakdown
    what_if_scenarios: List[WhatIfScenario]
    data_sources: List[DataSource]


class ReferralPackageResponse(BaseModel):
    """Complete referral package for downstream systems"""
    package_id: str
    shipment_id: str
    confidence_level: str
    score: int
    recommended_action: str
    sections: ReferralPackageSections
