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


class GraphEdgePayload(BaseModel):
    """Edge in entity graph response"""
    source: str
    target: str
    relationship_type: str
    confidence: float


class EntityGraphPayload(BaseModel):
    """Entity resolution graph response"""
    nodes: List[GraphNodePayload]
    edges: List[GraphEdgePayload]
    metadata: Dict[str, Any] = {}
