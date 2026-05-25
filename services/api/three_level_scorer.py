"""
Three-Level Illegal Transshipment Detection Risk Scorer

Level 1: Corridor Risk (Macro-level trade route analysis)
Level 2: Vessel Risk (Pre-manifest vessel anomalies)
Level 3: Manifest Risk (Transaction-level entity/document validation)

The system combines scores using dynamic weights with feedback-based learning.
"""

import logging
import httpx
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass

from external_apis.ofac_service import ofac_service
from external_apis.opendata_registry_service import registry_service

logger = logging.getLogger(__name__)

# Default baseline weights (can be overridden per corridor)
DEFAULT_WEIGHTS = {
    "w_corridor": 0.20,  # Level 1: Corridor Risk (20%)
    "w_vessel": 0.35,  # Level 2: Vessel Risk (35%)
    "w_manifest": 0.45,  # Level 3: Manifest Risk (45%)
}

DATA_SERVICE_URL = "http://localhost:8005"


@dataclass
class CorridorRiskSignals:
    """Signals for Level 1: Corridor Risk Assessment"""

    macro_volume_spike: float  # 0-100: Volume surge >2σ above 3-year average
    regulatory_delta: float  # 0-100: Recent sanctions or protective tariffs
    confidence: float  # 0-100: Overall confidence in signals


@dataclass
class VesselRiskSignals:
    """Signals for Level 2: Pre-Manifest Vessel Risk"""

    ftz_loitering: float  # 0-100: Vessel dwell >10 days in transshipment port
    ais_dark_activity: float  # 0-100: Missing AIS telemetry near sensitive areas
    confidence: float  # 0-100: Overall confidence in signals


@dataclass
class ManifestRiskSignals:
    """Signals for Level 3: Manifest Risk Assessment"""

    entity_resolution_match: float  # 0-100: Senzing hit on shell/proxy entities
    hs_code_weight_delta: float  # 0-100: Cargo weight variance >±15%
    network_anomaly: float  # 0-100: First-time importer via unfamiliar port
    confidence: float  # 0-100: Overall confidence in signals


class ThreeLevelScorer:
    """Main three-level risk scoring engine"""

    def __init__(self):
        self.data_url = DATA_SERVICE_URL

    async def score_shipment(
        self,
        shipment_id: str,
        shipper_name: str,
        shipper_country: str,
        consignee_name: str,
        consignee_country: str,
        hs_code: str,
        declared_value_usd: float,
        declared_weight_kg: float,
        vessel_name: Optional[str] = None,
        corridor_weights: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """
        Score a shipment across three risk levels and return combined assessment.

        Args:
            shipment_id: Unique shipment identifier
            shipper_name, shipper_country: Origin entity details
            consignee_name, consignee_country: Destination entity details
            hs_code: Harmonized System product code
            declared_value_usd: Value of shipment
            declared_weight_kg: Weight of shipment
            vessel_name: Name of transporting vessel
            corridor_weights: Optional custom weights for this corridor

        Returns:
            Dict with three-level scores, total score, risk level, and XAI factors
        """
        logger.info(f"Scoring shipment {shipment_id}: {shipper_country}→{consignee_country} HS{hs_code}")

        # Use provided weights or defaults
        weights = corridor_weights or DEFAULT_WEIGHTS

        try:
            # Level 1: Corridor Risk
            corridor_signals = await self._assess_corridor_risk(shipper_country, consignee_country, hs_code)
            corridor_score = self._calculate_corridor_score(corridor_signals)

            # Level 2: Vessel Risk
            vessel_signals = await self._assess_vessel_risk(vessel_name, shipper_country, consignee_country)
            vessel_score = self._calculate_vessel_score(vessel_signals)

            # Level 3: Manifest Risk
            manifest_signals = await self._assess_manifest_risk(
                shipper_name,
                shipper_country,
                consignee_name,
                consignee_country,
                hs_code,
                declared_value_usd,
                declared_weight_kg,
            )
            manifest_score = self._calculate_manifest_score(manifest_signals)

            # Calculate weighted total
            total_score = (
                weights["w_corridor"] * corridor_score
                + weights["w_vessel"] * vessel_score
                + weights["w_manifest"] * manifest_score
            ) * 100  # Scale to 0-100

            # Determine risk level
            if total_score >= 90:
                risk_level = "CRITICAL"
            elif total_score >= 70:
                risk_level = "HIGH"
            elif total_score >= 50:
                risk_level = "MEDIUM"
            else:
                risk_level = "LOW"

            # Generate XAI factors
            xai_factors = self._generate_xai_factors(corridor_signals, vessel_signals, manifest_signals, weights)

            result = {
                "shipment_id": shipment_id,
                "corridor_score": round(corridor_score, 2),
                "vessel_score": round(vessel_score, 2),
                "manifest_score": round(manifest_score, 2),
                "total_score": round(total_score, 2),
                "risk_level": risk_level,
                "requires_altana": total_score >= 90,
                "weights": weights,
                "components": {
                    "corridor": {
                        "macro_volume_spike": corridor_signals.macro_volume_spike,
                        "regulatory_delta": corridor_signals.regulatory_delta,
                        "confidence": corridor_signals.confidence,
                    },
                    "vessel": {
                        "ftz_loitering": vessel_signals.ftz_loitering,
                        "ais_dark_activity": vessel_signals.ais_dark_activity,
                        "confidence": vessel_signals.confidence,
                    },
                    "manifest": {
                        "entity_resolution_match": manifest_signals.entity_resolution_match,
                        "hs_code_weight_delta": manifest_signals.hs_code_weight_delta,
                        "network_anomaly": manifest_signals.network_anomaly,
                        "confidence": manifest_signals.confidence,
                    },
                },
                "xai_factors": xai_factors,
                "timestamp": datetime.utcnow().isoformat(),
            }

            logger.info(f"Shipment {shipment_id} scored: {result['total_score']}/100 ({risk_level})")
            return result

        except Exception as e:
            logger.error(f"Error scoring shipment {shipment_id}: {e}")
            raise

    async def _assess_corridor_risk(self, origin_country: str, dest_country: str, hs_code: str) -> CorridorRiskSignals:
        """
        Level 1: Assess macro-level corridor risk.
        Evaluates trade lane capacity and regulatory environment.
        """
        try:
            async with httpx.AsyncClient() as client:
                # Mock assessment - in production, query UN Comtrade, World Bank, ITC
                resp = await client.get(
                    f"{self.data_url}/corridor-risk",
                    params={
                        "origin": origin_country,
                        "destination": dest_country,
                        "hs_code": hs_code,
                    },
                    timeout=10,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return CorridorRiskSignals(
                        macro_volume_spike=data.get("macro_volume_spike", 0),
                        regulatory_delta=data.get("regulatory_delta", 0),
                        confidence=data.get("confidence", 0),
                    )
        except Exception as e:
            logger.warning(f"Could not fetch corridor risk data: {e}")

        # Fallback: Rule-based assessment
        return self._corridor_risk_baseline(origin_country, dest_country, hs_code)

    def _corridor_risk_baseline(self, origin: str, destination: str, hs_code: str) -> CorridorRiskSignals:
        """Baseline rule-based corridor risk assessment"""
        # High-risk corridors for transshipment
        high_risk_corridors = ["VN-US", "MY-US", "KH-US", "TH-US", "CN-MY", "CN-VN"]
        # High-risk HS codes (aluminum extrusions, solar panels)
        high_risk_codes = ["7604", "8541"]

        corridor_key = f"{origin}-{destination}"
        volume_spike = 60.0 if corridor_key in high_risk_corridors else 30.0
        regulatory = 50.0 if destination == "US" else 20.0
        hs_risk = 50.0 if any(hs_code.startswith(code) for code in high_risk_codes) else 10.0

        return CorridorRiskSignals(
            macro_volume_spike=min(volume_spike + hs_risk, 100.0),
            regulatory_delta=regulatory,
            confidence=75.0,
        )

    async def _assess_vessel_risk(self, vessel_name: Optional[str], origin: str, destination: str) -> VesselRiskSignals:
        """
        Level 2: Assess pre-manifest vessel anomalies.
        Evaluates AIS patterns, port dwell times, and routing anomalies.
        """
        if not vessel_name:
            return VesselRiskSignals(
                ftz_loitering=0.0,
                ais_dark_activity=0.0,
                confidence=0.0,
            )

        try:
            async with httpx.AsyncClient() as client:
                # Mock assessment - in production, query AISStream/VesselFinder
                resp = await client.get(
                    f"{self.data_url}/vessel-risk",
                    params={"vessel_name": vessel_name},
                    timeout=10,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return VesselRiskSignals(
                        ftz_loitering=data.get("ftz_loitering", 0),
                        ais_dark_activity=data.get("ais_dark_activity", 0),
                        confidence=data.get("confidence", 0),
                    )
        except Exception as e:
            logger.warning(f"Could not fetch vessel risk data: {e}")

        # Fallback: Rule-based assessment based on vessel name patterns
        return self._vessel_risk_baseline(vessel_name)

    def _vessel_risk_baseline(self, vessel_name: Optional[str]) -> VesselRiskSignals:
        """Baseline rule-based vessel risk assessment"""
        if not vessel_name:
            return VesselRiskSignals(ftz_loitering=0.0, ais_dark_activity=0.0, confidence=0.0)

        # Known transshipment hub ports
        suspicious_patterns = ["Panama", "Singapore", "Malaysia", "Hong Kong"]
        is_suspicious = any(p.lower() in vessel_name.lower() for p in suspicious_patterns)

        return VesselRiskSignals(
            ftz_loitering=60.0 if is_suspicious else 20.0,
            ais_dark_activity=40.0 if is_suspicious else 10.0,
            confidence=70.0,
        )

    async def _assess_manifest_risk(
        self,
        shipper_name: str,
        shipper_country: str,
        consignee_name: str,
        consignee_country: str,
        hs_code: str,
        declared_value_usd: float,
        declared_weight_kg: float,
    ) -> ManifestRiskSignals:
        """
        Level 3: Assess transaction-level manifest risk.
        Uses Senzing entity resolution, OFAC/registry checks, weight anomalies, and network patterns.
        """
        entity_match = 0.0
        ofac_risk = 0.0
        registry_risk = 0.0

        try:
            async with httpx.AsyncClient() as client:
                # Query Senzing entity resolution
                resp = await client.post(
                    f"{self.data_url}/entity-resolution",
                    json={
                        "shipper": shipper_name,
                        "shipper_country": shipper_country,
                        "consignee": consignee_name,
                        "consignee_country": consignee_country,
                    },
                    timeout=15,
                )
                if resp.status_code == 200:
                    entity_data = resp.json()
                    entity_match = entity_data.get("entity_match_risk", 0)
                else:
                    entity_match = 0.0

        except Exception as e:
            logger.warning(f"Could not fetch entity resolution data: {e}")
            entity_match = 0.0

        # OFAC SDN check for shipper and consignee
        try:
            shipper_ofac = await ofac_service.check_entity(shipper_name)
            if shipper_ofac.matched:
                ofac_risk = 85.0
                logger.warning(f"OFAC match found for shipper: {shipper_ofac.sdn_name}")

            consignee_ofac = await ofac_service.check_entity(consignee_name)
            if consignee_ofac.matched and ofac_risk < 85.0:
                ofac_risk = 75.0
                logger.warning(f"OFAC match found for consignee: {consignee_ofac.sdn_name}")
        except Exception as e:
            logger.warning(f"OFAC check failed: {e}")

        # Corporate registry check via OpenData.org / OpenCorporates
        try:
            shipper_registry = await registry_service.lookup_entity(shipper_name, shipper_country)
            if shipper_registry.found and shipper_registry.risk_flags:
                # Score based on risk flags (recent incorporation, generic names, etc.)
                registry_risk = min(len(shipper_registry.risk_flags) * 20, 60.0)
                logger.info(f"Registry risks for {shipper_name}: {shipper_registry.risk_flags}")

            # Verify ownership chain if shipper is recently incorporated
            if shipper_registry.found:
                days_old = self._get_incorporation_age_days(shipper_registry.incorporation_date)
                if days_old and days_old < 180:
                    registry_risk = min(registry_risk + 25.0, 85.0)

        except Exception as e:
            logger.warning(f"Registry check failed: {e}")

        # Combine OFAC and registry risks into entity match score
        entity_match = max(entity_match, ofac_risk, registry_risk)

        # Weight delta assessment (±15% tolerance)
        weight_delta = self._assess_weight_delta(hs_code, declared_weight_kg)

        # Network anomaly (first-time importer detection)
        network_anomaly = 50.0  # Placeholder - would check shipper history

        return ManifestRiskSignals(
            entity_resolution_match=entity_match,
            hs_code_weight_delta=weight_delta,
            network_anomaly=network_anomaly,
            confidence=80.0,
        )

    def _get_incorporation_age_days(self, incorporation_date: Optional[str]) -> Optional[int]:
        """Calculate number of days since incorporation"""
        if not incorporation_date:
            return None
        try:
            from dateutil import parser as dateutil_parser

            incorp_date = dateutil_parser.parse(incorporation_date)
            age_days = (datetime.utcnow() - incorp_date).days
            return age_days
        except:
            return None

    def _assess_weight_delta(self, hs_code: str, declared_weight_kg: float) -> float:
        """Assess if cargo weight deviates significantly from HS code averages"""
        # Known HS code weight benchmarks (kg per unit)
        weight_benchmarks = {
            "7604": 2.5,  # Aluminum extrusions
            "8541": 0.3,  # Solar modules
            "7610": 2.8,  # Aluminum structures
        }

        hs_prefix = hs_code[:4]
        if hs_prefix not in weight_benchmarks:
            return 0.0

        benchmark_weight = weight_benchmarks[hs_prefix]
        tolerance = benchmark_weight * 0.15  # ±15%

        if abs(declared_weight_kg - benchmark_weight) > tolerance:
            # Calculate deviation percentage
            deviation_pct = abs(declared_weight_kg - benchmark_weight) / benchmark_weight * 100
            return min(deviation_pct, 100.0)
        return 0.0

    def _calculate_corridor_score(self, signals: CorridorRiskSignals) -> float:
        """Calculate Level 1 corridor risk score (0-1.0)"""
        # Weight: 60% volume spike, 40% regulatory
        score = (0.60 * signals.macro_volume_spike + 0.40 * signals.regulatory_delta) / 100
        return min(score, 1.0)

    def _calculate_vessel_score(self, signals: VesselRiskSignals) -> float:
        """Calculate Level 2 vessel risk score (0-1.0)"""
        # Weight: 40% FTZ loitering, 60% AIS dark activity
        score = (0.40 * signals.ftz_loitering + 0.60 * signals.ais_dark_activity) / 100
        return min(score, 1.0)

    def _calculate_manifest_score(self, signals: ManifestRiskSignals) -> float:
        """Calculate Level 3 manifest risk score (0-1.0)"""
        # Weight: 50% entity match, 30% weight delta, 20% network anomaly
        score = (
            0.50 * signals.entity_resolution_match
            + 0.30 * signals.hs_code_weight_delta
            + 0.20 * signals.network_anomaly
        ) / 100
        return min(score, 1.0)

    def _generate_xai_factors(
        self,
        corridor: CorridorRiskSignals,
        vessel: VesselRiskSignals,
        manifest: ManifestRiskSignals,
        weights: Dict[str, float],
    ) -> List[str]:
        """Generate explainable AI factors explaining the risk score"""
        factors = []

        # Level 1 factors
        if corridor.macro_volume_spike > 50:
            factors.append(f"Macro volume spike detected: {corridor.macro_volume_spike:.0f}% above historical baseline")
        if corridor.regulatory_delta > 40:
            factors.append("Recent trade sanctions or protective tariffs on origin country")

        # Level 2 factors
        if vessel.ftz_loitering > 50:
            factors.append(f"Vessel loitering in free trade zone: {vessel.ftz_loitering:.0f}% anomaly flag")
        if vessel.ais_dark_activity > 50:
            factors.append(f"AIS dark activity detected: {vessel.ais_dark_activity:.0f}% anomaly flag")

        # Level 3 factors
        if manifest.entity_resolution_match > 50:
            factors.append(
                f"Senzing entity resolution match to shell/proxy entities: {manifest.entity_resolution_match:.0f}%"
            )
        if manifest.hs_code_weight_delta > 15:
            factors.append(
                f"Cargo weight variance exceeds ±15% tolerance: {manifest.hs_code_weight_delta:.0f}% deviation"
            )
        if manifest.network_anomaly > 50:
            factors.append("First-time importer detected via unfamiliar port routing")

        return factors if factors else ["All risk indicators within normal parameters"]


# Global scorer instance
scorer = ThreeLevelScorer()
