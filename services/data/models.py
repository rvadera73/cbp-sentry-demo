"""Pydantic models for data layer"""
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


class ShipmentBase(BaseModel):
    manifest_id: str
    shipper_name: str
    consignee_name: str
    origin_country: str
    destination_country: str
    hs_code: str
    declared_value_usd: float
    declared_weight_kg: float
    description: Optional[str] = None
    vessel_name: Optional[str] = None
    status: str = "received"


class ShipmentCreate(ShipmentBase):
    pass


class ShipmentUpdate(BaseModel):
    status: Optional[str] = None
    risk_score: Optional[float] = None
    risk_delta: Optional[float] = None
    last_polled_at: Optional[datetime] = None
    ofac_screened_at: Optional[datetime] = None
    ofac_match: Optional[bool] = None


class Shipment(ShipmentBase):
    id: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    risk_score: Optional[float] = None
    risk_delta: Optional[float] = None
    last_polled_at: Optional[datetime] = None
    ofac_screened_at: Optional[datetime] = None
    ofac_match: Optional[bool] = None
    h1_score: Optional[float] = None
    h2_score: Optional[float] = None
    h1_h2_score: Optional[float] = None

    class Config:
        from_attributes = True


class ManifestCreate(BaseModel):
    id: str
    filename: str
    row_count: int
    extracted_at: datetime


class Manifest(ManifestCreate):
    class Config:
        from_attributes = True


class ScoreCreate(BaseModel):
    shipment_id: str
    h1_score: Optional[float] = None
    h2_score: Optional[float] = None
    h1_h2_score: Optional[float] = None
    total_score: Optional[float] = None
    components: Optional[Dict[str, Any]] = None
    xai_assertions: Optional[List[str]] = None


class Score(ScoreCreate):
    id: str
    created_at: datetime

    class Config:
        from_attributes = True


# ============= THREE-LEVEL RISK SCORING MODELS =============

class WeightConfiguration(BaseModel):
    """Global or corridor-specific weight configuration"""
    id: str
    corridor: Optional[str] = None  # e.g., "VN-US", None for global
    w_corridor: float  # Weight for Level 1 (Corridor Risk)
    w_vessel: float    # Weight for Level 2 (Vessel Risk)
    w_manifest: float  # Weight for Level 3 (Manifest Risk)
    created_at: datetime
    updated_at: Optional[datetime] = None
    created_by: str    # Analyst name/ID who set this
    notes: Optional[str] = None

    class Config:
        from_attributes = True


class WeightConfigurationCreate(BaseModel):
    corridor: Optional[str] = None
    w_corridor: float
    w_vessel: float
    w_manifest: float
    notes: Optional[str] = None


class ScoringOverride(BaseModel):
    """Record of analyst feedback/override on a scoring decision"""
    id: str
    shipment_id: str
    original_score: float
    override_decision: str  # "ACCEPT" or "REJECT"
    feedback_type: Optional[str] = None  # "factory_expansion", "dual_origin", "misclassified_vessel", etc.
    analyst_id: str
    analyst_name: str
    created_at: datetime
    notes: Optional[str] = None

    class Config:
        from_attributes = True


class ScoringOverrideCreate(BaseModel):
    shipment_id: str
    original_score: float
    override_decision: str
    feedback_type: Optional[str] = None
    analyst_id: str
    analyst_name: str
    notes: Optional[str] = None


class WeightSuggestion(BaseModel):
    """Suggested weight adjustment based on override patterns"""
    id: str
    corridor: Optional[str] = None
    affected_feature: str  # "w_corridor", "w_vessel", or "w_manifest"
    suggested_value: float
    confidence_pct: float  # Confidence in the suggestion (0-100)
    corroboration_count: int  # Number of overrides supporting this
    status: str  # "pending", "approved", "rejected"
    created_at: datetime
    reviewed_at: Optional[datetime] = None
    reviewed_by: Optional[str] = None
    rationale: str  # Explanation of why this change is suggested

    class Config:
        from_attributes = True


class WeightSuggestionCreate(BaseModel):
    corridor: Optional[str] = None
    affected_feature: str
    suggested_value: float
    confidence_pct: float
    corroboration_count: int
    rationale: str


class ThreeLevelScore(BaseModel):
    """Complete three-level risk score breakdown"""
    shipment_id: str
    corridor_score: float  # Level 1: 0-100
    vessel_score: float    # Level 2: 0-100
    manifest_score: float  # Level 3: 0-100
    w_corridor: float
    w_vessel: float
    w_manifest: float
    total_score: float  # Weighted total: 0-100
    risk_level: str  # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    requires_altana: bool  # True if total_score >= 90
    components: Dict[str, Any]  # Detailed breakdown by component
    xai_factors: List[str]  # Explainable AI factors contributing to score

    class Config:
        from_attributes = True
