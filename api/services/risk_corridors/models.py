"""
Pydantic models for Risk Corridor API
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class MacroVolumetricDelta(BaseModel):
    """Macro volumetric anomaly detection"""
    status: str  # "FLAGGED" or "NORMAL"
    outbound_volume_manifest_tons: float
    estimated_domestic_capacity_tons: float
    ratio: float
    signal: str


class RiskCorridor(BaseModel):
    """Risk Corridor aggregation"""
    corridor_id: str
    hts_chapter: str
    industry_segment: str
    origin_country: str
    destination_country: str
    supplier_entity: str
    shipment_count: int
    aggregate_value_usd: float
    yoy_volume_surge_pct: float
    yoy_value_surge_pct: float
    macro_volumetric_delta: MacroVolumetricDelta
    ad_cvd_rate_pct: float
    active_vessels: int
    risk_level: str  # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    last_updated: datetime


class RiskCorridorIndexResponse(BaseModel):
    """Response for risk corridor index endpoint"""
    corridors: List[RiskCorridor]
    summary: Dict[str, Any]


class PortCallHistory(BaseModel):
    """Port call event in vessel history"""
    port_name: str
    arrival_date: datetime
    departure_date: datetime
    dwell_days: int
    baseline_dwell_days: float
    anomaly: Optional[str] = None


class FTZDwellEvent(BaseModel):
    """Foreign Trade Zone dwell event"""
    ftz_code: str
    ftz_name: str
    entry_date: datetime
    estimated_exit: datetime
    dwell_days: int
    status: str  # "HIGH_RISK_DWELL", "NORMAL"


class VesselDetail(BaseModel):
    """Vessel with activity details"""
    vessel_id: str
    vessel_name: str
    flag_state: str
    current_port: str
    status: str  # "AT_BERTH", "INBOUND", "UNDERWAY"
    port_call_history: List[PortCallHistory]
    ftz_dwell_events: List[FTZDwellEvent]
    transshipment_risk_score: float
    risk_level: str


class SupplierEntity(BaseModel):
    """Supplier entity in corridor"""
    entity_id: str
    name: str
    country: str
    risk_score: float
    ofac_status: str


class EntityChainLevel(BaseModel):
    """Single level in entity chain"""
    name: str
    country: str
    role: str


class EntityRelationship(BaseModel):
    """Relationship between entities"""
    from_entity: str = Field(default=None, alias="from")
    to_entity: str = Field(default=None, alias="to")
    type: str = Field(default=None, alias="relationship_type")
    confidence: float

    class Config:
        populate_by_name = True


class EntityChain(BaseModel):
    """Supply chain entity relationships"""
    level_1: EntityChainLevel
    level_2: Optional[EntityChainLevel] = None
    level_3: Optional[EntityChainLevel] = None
    relationships: List[EntityRelationship]

    class Config:
        populate_by_name = True


class RiskCorridorDetail(BaseModel):
    """Detailed risk corridor view"""
    corridor_id: str
    hts_chapter: str
    industry_segment: str
    origin_country: str
    destination_country: str
    supplier_entity: SupplierEntity
    active_vessels: List[VesselDetail]


class RiskCorridorDetailResponse(BaseModel):
    """Response for risk corridor detail endpoint"""
    corridor: RiskCorridorDetail
    entity_chain: EntityChain


class VesselOfInterest(BaseModel):
    """Vessel of interest at port"""
    vessel_id: str
    vessel_name: str
    eta: datetime
    status: str  # "INBOUND", "AT_BERTH", "DEPARTED"
    cargo_risk_level: str
    cargo_summary: Dict[str, Any]
    route_anomalies: List[str]
    recommended_actions: List[str]


class PortVesselsResponse(BaseModel):
    """Response for vessels at port endpoint"""
    port: str
    port_name: str
    vessels_of_interest: List[VesselOfInterest]
    summary: Dict[str, Any]


class TimelineSnapshot(BaseModel):
    """Historical snapshot of corridor at point in time"""
    date: str  # ISO date YYYY-MM-DD
    shipment_count: int
    aggregate_value_usd: float
    active_entities: List[str]
    active_vessels: List[str]
    notable_events: List[str]


class EntityFormation(BaseModel):
    """Suspicious entity formation event"""
    date: str
    entity_name: str
    country: str
    first_shipment_after_formation: int
    suspicious_timing: bool


class EntityEvolution(BaseModel):
    """Entity evolution tracking"""
    entities_formed: int
    entity_formations: List[EntityFormation]


class TimelineResponse(BaseModel):
    """Response for timeline endpoint"""
    corridor_id: str
    timeline_snapshots: List[TimelineSnapshot]
    entity_evolution: EntityEvolution


class FeedbackOverride(BaseModel):
    """Officer feedback override"""
    shipment_id: str
    corridor_id: str
    risk_score_original: float
    override_action: str  # "MARK_FALSE_POSITIVE", "MARK_TRUE_POSITIVE", "REQUEST_FOLLOW_UP"
    justification_category: str
    justification_detail: str
    officer_id: str
    override_timestamp: datetime


class FeedbackOverrideResponse(BaseModel):
    """Response for feedback override endpoint"""
    override_id: str
    status: str
    feedback_stored_for_model_retraining: bool
    next_model_training_window: str
