"""ISF enrichment service for analyzing and enriching ISF data with vessel tracking."""

from datetime import datetime
from typing import Optional, List, Tuple
from .models import (
    ISFData,
    ISFEnrichmentRequest,
    ISFEnrichmentResponse,
    Element9Data,
    VesselInfo,
    VesselDataArchive,
)
from .vessel_tracker import VesselTrackerClient


class ISFEnrichmentService:
    """Service for enriching manifest data with real-time ISF information."""

    def __init__(self, vessel_tracker: VesselTrackerClient):
        """Initialize ISF enrichment service."""
        self.vessel_tracker = vessel_tracker
        self.high_risk_corridors = {
            ("CN", "MY"): 8,  # China to Malaysia
            ("CN", "VN"): 8,  # China to Vietnam
            ("CN", "TH"): 8,  # China to Thailand
            ("CN", "KH"): 8,  # China to Cambodia
            ("CN", "US"): 5,  # Direct China to US (suspicious if transshipped)
        }
        self.transshipment_ports = ["SGSIN", "MYKTK", "VNSGN", "THBKK", "KHPNH"]
        # Dwell time anomaly detection configuration
        self.dwell_baseline_days = 2.3  # Global baseline; should be per-vessel/port from archive
        self.dwell_multiplier_threshold = 2.5  # Flag if dwell > baseline × 2.5 (catches 6d vs 2.3d = 2.6x)

    async def enrich_manifest(self, request: ISFEnrichmentRequest) -> ISFEnrichmentResponse:
        """Enrich manifest with ISF data and Element 9 analysis."""
        start_time = datetime.utcnow()

        try:
            # Fetch vessel information
            vessel_info = None
            if request.imo:
                vessel_info = await self.vessel_tracker.get_vessel_info(request.imo)
            elif request.vessel_name:
                vessel_info = await self._search_vessel_by_name(request.vessel_name)

            # Get port call history for dwell analysis
            port_calls = []
            if vessel_info and vessel_info.imo:
                port_calls = await self.vessel_tracker.get_port_calls(vessel_info.imo)
                vessel_info.port_calls = port_calls

            # Analyze Element 9
            element_9 = await self._analyze_element_9(
                request.shipper_country,
                request.consignee_country,
                request.declared_origin,
                vessel_info,
                port_calls,
            )

            # Build ISF data
            isf_data = ISFData(
                manifest_id=request.manifest_id,
                filing_date=request.filing_date,
                shipper_name=request.shipper_name,
                shipper_country=request.shipper_country,
                consignee_name=request.consignee_name,
                consignee_country=request.consignee_country,
                vessel=vessel_info,
                imo=request.imo,
                vessel_name=request.vessel_name,
                element_9=element_9,
                hs_code=request.hs_code,
                sources=self._get_data_sources(vessel_info),
            )

            # Calculate data completeness
            isf_data.data_completeness_pct = self._calculate_completeness(isf_data)
            isf_data.confidence_score = element_9.mismatch_confidence

            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000

            return ISFEnrichmentResponse(
                manifest_id=request.manifest_id,
                status="success",
                isf_data=isf_data,
                element_9_analysis=element_9,
                vessel_info=vessel_info,
                processing_time_ms=processing_time,
            )

        except Exception as e:
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            return ISFEnrichmentResponse(
                manifest_id=request.manifest_id,
                status="error",
                error_reason=str(e),
                processing_time_ms=processing_time,
            )

    async def _analyze_element_9(
        self,
        shipper_country: str,
        consignee_country: str,
        declared_origin: Optional[str],
        vessel_info: Optional[VesselInfo],
        port_calls: List,
    ) -> Element9Data:
        """Analyze ISF Element 9 (Country of Origin Pre-Arrival)."""

        # Determine actual stuffing location from vessel port calls
        actual_stuffing_country = None
        stuffing_port = None
        dwell_days = 0

        if vessel_info and port_calls:
            # Most recent port call before estimated departure (likely loading/stuffing port)
            for port in port_calls[:3]:  # Check last 3 port calls
                if port.departure_date:
                    actual_stuffing_country = port.country
                    stuffing_port = port.port_code
                    dwell_days = port.dwell_days or 0
                    break

        # Detect Element 9 mismatch
        element_9_declared = declared_origin or shipper_country
        is_mismatch = False
        risk_level = "LOW"
        mismatch_confidence = 0.0
        evidence = []

        if actual_stuffing_country and element_9_declared:
            # Check for mismatch
            if actual_stuffing_country.upper() != element_9_declared.upper():
                is_mismatch = True
                evidence.append(
                    f"Declared origin {element_9_declared} but vessel last loaded from {actual_stuffing_country}"
                )

                # Check if it's a known transshipment corridor
                corridor = (actual_stuffing_country[:2], consignee_country[:2])
                if corridor in self.high_risk_corridors:
                    risk_level = "HIGH"
                    mismatch_confidence = 0.95
                    evidence.append(f"Known high-risk transshipment corridor: {corridor[0]}→{corridor[1]}")
                elif stuffing_port and stuffing_port in self.transshipment_ports:
                    risk_level = "MEDIUM"
                    mismatch_confidence = 0.85
                    evidence.append(f"Known transshipment port: {stuffing_port}")
                else:
                    risk_level = "MEDIUM"
                    mismatch_confidence = 0.75
                    evidence.append("Potential transshipment detected")

            # Check dwell time anomalies (multiplier-based, not absolute threshold)
            if dwell_days:
                dwell_multiplier = dwell_days / self.dwell_baseline_days if self.dwell_baseline_days > 0 else 0
                if dwell_multiplier > self.dwell_multiplier_threshold:
                    evidence.append(f"Extended dwell: {dwell_days} days ({dwell_multiplier:.1f}× baseline {self.dwell_baseline_days}d)")
                    if risk_level == "LOW":
                        risk_level = "MEDIUM"
                        mismatch_confidence = 0.6
                    else:
                        mismatch_confidence = min(mismatch_confidence + 0.1, 1.0)

        # Direct origin mismatch (shipper ≠ declared)
        if shipper_country.upper() != element_9_declared.upper():
            evidence.append(f"Shipper country {shipper_country} differs from declared origin {element_9_declared}")
            if not is_mismatch:
                risk_level = "MEDIUM"
                mismatch_confidence = 0.7

        return Element9Data(
            declared_country=element_9_declared,
            declared_country_code=element_9_declared[:2].upper() if element_9_declared else "XX",
            actual_stuffing_location=stuffing_port,
            actual_stuffing_country=actual_stuffing_country,
            actual_stuffing_country_code=actual_stuffing_country[:2].upper() if actual_stuffing_country else "XX",
            port_of_loading=stuffing_port,
            vessel_name=vessel_info.vessel_name if vessel_info else None,
            is_mismatch=is_mismatch,
            mismatch_confidence=mismatch_confidence,
            risk_level=risk_level,
            evidence=evidence,
            data_sources=["VesselFinder", "Port Authority Records"],
        )

    async def _search_vessel_by_name(self, vessel_name: str) -> Optional[VesselInfo]:
        """Search for vessel by name (fallback if IMO not available)."""
        # This would require additional VesselFinder API call
        # For now, return None (requires vessel name search endpoint)
        return None

    def _get_data_sources(self, vessel_info: Optional[VesselInfo]) -> List[str]:
        """Get list of data sources used for enrichment."""
        sources = ["ISF Filing Data"]
        if vessel_info:
            sources.extend(["VesselFinder", "AIS", "Port Authority"])
        return sources

    def _calculate_completeness(self, isf_data: ISFData) -> float:
        """Calculate ISF data completeness percentage."""
        total_fields = 0
        filled_fields = 0

        # Check basic party fields
        fields = [
            isf_data.shipper_name,
            isf_data.shipper_country,
            isf_data.consignee_name,
            isf_data.consignee_country,
        ]
        total_fields += len(fields)
        filled_fields += sum(1 for f in fields if f)

        # Check vessel fields
        if isf_data.vessel:
            total_fields += 2
            filled_fields += 1
            if isf_data.vessel.imo:
                filled_fields += 1

        # Check Element 9
        if isf_data.element_9:
            total_fields += 2
            if isf_data.element_9.declared_country:
                filled_fields += 1
            if isf_data.element_9.actual_stuffing_country:
                filled_fields += 1

        if total_fields == 0:
            return 0.0

        return (filled_fields / total_fields) * 100.0

    async def archive_vessel_data(self, vessel_info: VesselInfo) -> VesselDataArchive:
        """Archive vessel data for historical analysis."""
        # Calculate dwell patterns
        dwell_patterns = {}
        for port_call in vessel_info.port_calls:
            port = port_call.port_code
            if port not in dwell_patterns:
                dwell_patterns[port] = []
            if port_call.dwell_days:
                dwell_patterns[port].append(port_call.dwell_days)

        # Calculate averages
        avg_dwell = {}
        for port, dwells in dwell_patterns.items():
            avg_dwell[port] = sum(dwells) / len(dwells) if dwells else 0

        # Extract routing patterns
        routing_patterns = []
        for i in range(len(vessel_info.port_calls) - 1):
            route = f"{vessel_info.port_calls[i].port_code}->{vessel_info.port_calls[i + 1].port_code}"
            routing_patterns.append(route)

        return VesselDataArchive(
            imo=vessel_info.imo,
            vessel_name=vessel_info.vessel_name,
            flag_country=vessel_info.flag_country,
            port_calls=vessel_info.port_calls,
            dwell_patterns=avg_dwell,
            routing_patterns=routing_patterns,
        )
