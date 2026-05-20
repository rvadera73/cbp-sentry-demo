"""ISF enrichment data models for vessel tracking and Element 9 analysis."""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class PortCall(BaseModel):
    """Port visit details from vessel history."""
    port_code: str
    port_name: str
    country: str
    arrival_date: Optional[datetime] = None
    departure_date: Optional[datetime] = None
    dwell_days: Optional[int] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class VesselInfo(BaseModel):
    """Vessel identification and characteristics."""
    imo: str
    mmsi: Optional[str] = None
    vessel_name: str
    flag_country: str
    vessel_type: str
    length_m: Optional[float] = None
    beam_m: Optional[float] = None
    capacity_teu: Optional[int] = None
    capacity_metric_tonnes: Optional[int] = None
    built_year: Optional[int] = None
    last_position: Optional[dict] = None
    port_calls: List[PortCall] = []


class Element9Data(BaseModel):
    """ISF Element 9: Country of Origin Pre-Arrival analysis."""
    declared_country: str
    declared_country_code: str
    actual_stuffing_location: Optional[str] = None
    actual_stuffing_country: Optional[str] = None
    actual_stuffing_country_code: Optional[str] = None
    port_of_loading: Optional[str] = None
    port_of_unlading: Optional[str] = None
    vessel_name: Optional[str] = None
    is_mismatch: bool = False
    mismatch_confidence: float = Field(0.0, ge=0.0, le=1.0)
    risk_level: str = "LOW"  # LOW, MEDIUM, HIGH
    evidence: List[str] = []
    data_sources: List[str] = []
    last_updated: datetime = Field(default_factory=datetime.utcnow)


class ISFData(BaseModel):
    """Complete ISF (Importer Security Filing) enriched data."""
    manifest_id: str
    shipment_id: Optional[str] = None
    filing_date: datetime

    # Parties
    shipper_name: str
    shipper_country: str
    consignee_name: str
    consignee_country: str
    manufacturer_name: Optional[str] = None
    manufacturer_country: Optional[str] = None
    buyer_name: Optional[str] = None
    buyer_country: Optional[str] = None

    # Vessel information
    vessel: Optional[VesselInfo] = None
    imo: Optional[str] = None
    vessel_name: Optional[str] = None

    # Element 9 analysis
    element_9: Element9Data

    # Port routing
    port_of_loading: Optional[str] = None
    port_of_unlading: Optional[str] = None
    estimated_arrival: Optional[datetime] = None

    # Commodity
    hs_code: Optional[str] = None
    commodity_description: Optional[str] = None
    declared_value_usd: Optional[float] = None
    weight_kg: Optional[float] = None

    # Quality metrics
    data_completeness_pct: float = Field(0.0, ge=0.0, le=100.0)
    confidence_score: float = Field(0.0, ge=0.0, le=1.0)
    sources: List[str] = []
    last_enriched: datetime = Field(default_factory=datetime.utcnow)


class ISFEnrichmentRequest(BaseModel):
    """Request to enrich manifest with ISF data."""
    manifest_id: str
    shipper_name: str
    shipper_country: str
    consignee_name: str
    consignee_country: str
    vessel_name: Optional[str] = None
    imo: Optional[str] = None
    declared_origin: Optional[str] = None
    hs_code: Optional[str] = None
    filing_date: datetime = Field(default_factory=datetime.utcnow)


class ISFEnrichmentResponse(BaseModel):
    """Response with enriched ISF data."""
    manifest_id: str
    status: str = "success"  # success, partial, error
    isf_data: Optional[ISFData] = None
    element_9_analysis: Optional[Element9Data] = None
    vessel_info: Optional[VesselInfo] = None
    warnings: List[str] = []
    error_reason: Optional[str] = None
    processing_time_ms: float = 0.0


class VesselDataArchive(BaseModel):
    """Historical vessel data for archival and analysis."""
    imo: str
    vessel_name: str
    flag_country: str
    archived_date: datetime = Field(default_factory=datetime.utcnow)
    port_calls: List[PortCall] = []
    dwell_patterns: dict = {}  # port -> avg dwell days
    routing_patterns: List[str] = []  # common routes
    anomalies: List[dict] = []  # detected anomalies
    metadata: dict = {}  # any additional data
