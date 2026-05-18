"""
Pydantic schemas for request/response validation
"""
from pydantic import BaseModel
from typing import List, Optional, Any, Dict


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
