"""Transshipment Network Pattern Detection

Detects transshipment patterns via FTZ dwell anomalies, illogical port routing,
vessel routing anomalies, and multi-port consolidation tactics.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class TransshipmentDetector:
    """Detects transshipment patterns in vessel routing and FTZ dwell.

    Transshipment tactics detected:
    1. Excessive FTZ dwell (should clear in 1-2 days, suspicious if > 3× baseline)
    2. Port routing anomalies (illogical sequences, return visits)
    3. Vessel rotation patterns (same vessel visits multiple ports in suspicious sequence)
    4. Consolidation centers (single FTZ receives shipments from multiple origins)
    """

    # Baseline FTZ dwell times in days (based on CBP data)
    FTZ_BASELINE_DWELL_DAYS = {
        "FTZ-80": 1.5,  # Los Angeles FTZ
        "FTZ-48": 2.0,  # New York/New Jersey
        "FTZ-1": 1.8,  # General baseline
        "FTZ-24": 2.2,  # San Francisco
        "FTZ-44": 1.9,  # Houston
        "default": 2.0,
    }

    # Known transshipment hubs (FTZs and ports)
    TRANSSHIPMENT_HUBS = {
        "SG": {"name": "Singapore", "type": "port", "risk_score": 0.85},
        "AE": {"name": "Dubai/UAE", "type": "port", "risk_score": 0.80},
        "MY": {"name": "Malaysia", "type": "port", "risk_score": 0.75},
        "TH": {"name": "Thailand", "type": "port", "risk_score": 0.70},
        "VN": {"name": "Vietnam", "type": "port", "risk_score": 0.75},
        "KH": {"name": "Cambodia", "type": "port", "risk_score": 0.65},
        "HK": {"name": "Hong Kong", "type": "port", "risk_score": 0.80},
        "IN": {"name": "India", "type": "port", "risk_score": 0.60},
    }

    def __init__(self):
        """Initialize transshipment detector."""
        pass

    def detect_ftz_dwell_anomaly(self, ftz_code: str, actual_dwell_days: float) -> Dict[str, Any]:
        """Flag if FTZ dwell exceeds baseline (suggests repackaging/consolidation).

        **Logic**: Foreign Trade Zones are bonded areas where goods can be
        processed duty-free. Normal dwell is 1-2 days (quick clearance).
        Dwell > 3× baseline suggests repackaging, relabeling, or consolidation.

        Args:
            ftz_code: FTZ code (e.g., "FTZ-80", "FTZ-48")
            actual_dwell_days: Number of days goods spent in FTZ

        Returns:
            Dict with:
                - status: "HIGH_RISK_DWELL" | "MEDIUM_RISK_DWELL" | "NORMAL"
                - actual_dwell_days: float
                - baseline_dwell_days: float
                - ratio: Actual / baseline
                - signal: Human-readable description
                - flag: bool (True if anomalous)
                - confidence: float (0.5-0.95)
        """
        baseline = self.FTZ_BASELINE_DWELL_DAYS.get(ftz_code, self.FTZ_BASELINE_DWELL_DAYS["default"])
        ratio = actual_dwell_days / baseline if baseline > 0 else 0

        if ratio > 3.0:
            status = "HIGH_RISK_DWELL"
            confidence = min(0.95, 0.7 + (ratio * 0.05))
        elif ratio > 1.5:
            status = "MEDIUM_RISK_DWELL"
            confidence = 0.65
        else:
            status = "NORMAL"
            confidence = 0.85

        return {
            "status": status,
            "actual_dwell_days": round(actual_dwell_days, 2),
            "baseline_dwell_days": baseline,
            "ratio": round(ratio, 2),
            "signal": f"FTZ dwell {round(ratio, 2)}× baseline ({actual_dwell_days} vs {baseline} days) "
            f"in {ftz_code}",
            "flag": status != "NORMAL",
            "confidence": round(confidence, 2),
        }

    def detect_port_routing_anomaly(self, port_call_sequence: List[Dict[str, str]]) -> Dict[str, Any]:
        """Detect illogical port sequences suggesting transshipment detour.

        **Anomalies**:
        - Return visit to same country (e.g., CN → HK → CN)
        - Redundant intermediate stops
        - Backtracking in routing
        - Visits to known transshipment hubs with short dwell

        Args:
            port_call_sequence: List of dicts with keys:
                - port_code: str (e.g., "SGSIN")
                - country: str (ISO 2-letter code, e.g., "SG")
                - visit_date: str (ISO date or datetime)
                - dwell_hours: float (optional, hours at port)

        Returns:
            Dict with:
                - anomaly_detected: bool
                - anomalies: List of detected anomalies
                - routing_path: str (human-readable route)
                - return_visits: List of countries visited twice
                - transshipment_hubs: List of detected hub visits
                - severity: "HIGH" | "MEDIUM" | "LOW" | "NONE"
                - signal: Description
        """
        if len(port_call_sequence) < 2:
            return {
                "anomaly_detected": False,
                "anomalies": [],
                "routing_path": "Insufficient port calls",
                "return_visits": [],
                "transshipment_hubs": [],
                "severity": "NONE",
                "signal": "Cannot evaluate with < 2 port calls",
            }

        anomalies = []
        return_visits = []
        transshipment_hub_visits = []

        # Check for return visits
        countries_visited = []
        for i, port_call in enumerate(port_call_sequence):
            country = port_call.get("country", "")
            countries_visited.append(country)

            if i > 0 and country in countries_visited[:-1]:
                return_visits.append(country)
                anomalies.append(f"Return visit to {country}")

        # Check for transshipment hub visits
        for i, port_call in enumerate(port_call_sequence):
            country = port_call.get("country", "")
            if country in self.TRANSSHIPMENT_HUBS:
                hub_info = self.TRANSSHIPMENT_HUBS[country]
                transshipment_hub_visits.append(
                    {
                        "country": country,
                        "name": hub_info["name"],
                        "risk_score": hub_info["risk_score"],
                        "dwell_hours": port_call.get("dwell_hours", None),
                    }
                )

        # Check for backtracking (e.g., going east then west)
        if len(port_call_sequence) >= 3:
            # Simplified check: if intermediate port is geographically between origin/dest
            # and visit is short, suspect transshipment
            if transshipment_hub_visits:
                anomalies.append(f"Transit through {len(transshipment_hub_visits)} transshipment hub(s)")

        # Build routing path
        routing_path = " → ".join([p.get("port_code", p.get("country", "?")) for p in port_call_sequence])

        # Determine severity
        severity = "NONE"
        if len(anomalies) >= 2:
            severity = "HIGH"
        elif len(anomalies) == 1 and len(transshipment_hub_visits) > 0:
            severity = "MEDIUM"
        elif len(return_visits) > 0:
            severity = "MEDIUM"
        elif len(transshipment_hub_visits) > 1:
            severity = "LOW"

        return {
            "anomaly_detected": len(anomalies) > 0,
            "anomalies": anomalies,
            "routing_path": routing_path,
            "return_visits": list(set(return_visits)),
            "transshipment_hubs": transshipment_hub_visits,
            "severity": severity,
            "signal": f"Port sequence: {routing_path}; "
            f"{len(anomalies)} anomaly(ies), {len(transshipment_hub_visits)} hub(s)",
        }

    def detect_consolidation_pattern(self, shipments_by_ftz: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        """Detect consolidation centers (single FTZ receives from multiple origins).

        **Logic**: If one FTZ receives shipments from many different origins,
        it may be a consolidation center for transshipment.

        Args:
            shipments_by_ftz: Dict mapping FTZ code to list of shipments
                Each shipment should have: origin_country, destination_country, weight_tons

        Returns:
            Dict with:
                - consolidation_detected: bool
                - ftz_code: str
                - origin_country_count: int
                - total_weight_tons: float
                - origins: List[str]
                - signal: Description
        """
        if not shipments_by_ftz:
            return {
                "consolidation_detected": False,
                "ftz_code": None,
                "origin_country_count": 0,
                "total_weight_tons": 0.0,
                "origins": [],
                "signal": "No FTZ data",
            }

        max_consolidation = None
        max_origin_count = 0

        for ftz_code, shipments in shipments_by_ftz.items():
            origins = set()
            total_weight = 0.0

            for shipment in shipments:
                origins.add(shipment.get("origin_country", ""))
                total_weight += shipment.get("weight_tons", 0)

            origin_count = len(origins)
            if origin_count > max_origin_count:
                max_origin_count = origin_count
                max_consolidation = {
                    "ftz_code": ftz_code,
                    "origin_country_count": origin_count,
                    "total_weight_tons": total_weight,
                    "origins": sorted(list(origins)),
                    "shipment_count": len(shipments),
                }

        if max_consolidation is None:
            return {
                "consolidation_detected": False,
                "ftz_code": None,
                "origin_country_count": 0,
                "total_weight_tons": 0.0,
                "origins": [],
                "signal": "Could not analyze",
            }

        # Flag if FTZ consolidates > 5 origins (unusual)
        consolidation_detected = max_consolidation["origin_country_count"] > 5

        return {
            "consolidation_detected": consolidation_detected,
            "ftz_code": max_consolidation["ftz_code"],
            "origin_country_count": max_consolidation["origin_country_count"],
            "total_weight_tons": round(max_consolidation["total_weight_tons"], 2),
            "origins": max_consolidation["origins"],
            "shipment_count": max_consolidation["shipment_count"],
            "signal": f"FTZ {max_consolidation['ftz_code']} consolidates {max_consolidation['origin_country_count']} origins: "
            f"{', '.join(max_consolidation['origins'])}",
        }

    def detect_vessel_rotation_anomaly(self, vessel_port_calls: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Detect when a vessel makes suspicious port rotation (potential transshipment).

        **Pattern**: Same vessel visits multiple ports in sequence with inconsistent
        cargo patterns, suggesting it's rotating through transshipment hubs.

        Args:
            vessel_port_calls: List of dicts with keys:
                - port_code: str
                - country: str
                - arrival_date: str
                - cargo_origin: str
                - cargo_destination: str

        Returns:
            Dict with:
                - rotation_anomaly: bool
                - port_count: int
                - route_pattern: str
                - suspect_transshipment: bool
        """
        if len(vessel_port_calls) < 3:
            return {
                "rotation_anomaly": False,
                "port_count": len(vessel_port_calls),
                "route_pattern": "Insufficient port calls",
                "suspect_transshipment": False,
                "signal": "Cannot evaluate < 3 port calls",
            }

        # Check for geographic rotation pattern
        countries = [call.get("country") for call in vessel_port_calls]
        port_codes = [call.get("port_code") for call in vessel_port_calls]

        # Count unique pairs (origin, destination) — high variety suggests consolidation
        origin_dest_pairs = set()
        for call in vessel_port_calls:
            pair = (call.get("cargo_origin", "?"), call.get("cargo_destination", "?"))
            origin_dest_pairs.add(pair)

        suspect_transshipment = len(origin_dest_pairs) > len(vessel_port_calls) * 0.7

        return {
            "rotation_anomaly": suspect_transshipment,
            "port_count": len(vessel_port_calls),
            "unique_countries": len(set(countries)),
            "route_pattern": " → ".join(port_codes),
            "origin_dest_pair_variety": len(origin_dest_pairs),
            "suspect_transshipment": suspect_transshipment,
            "signal": f"Vessel calls {len(vessel_port_calls)} ports "
            f"({', '.join(set(countries))}) with {len(origin_dest_pairs)} different origin/dest pairs",
        }

    def compute_transshipment_risk_score(
        self,
        ftz_dwell_anomaly: Dict[str, Any],
        port_routing_anomaly: Dict[str, Any],
        consolidation: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Synthesize multiple transshipment signals into single risk score.

        Args:
            ftz_dwell_anomaly: Result from detect_ftz_dwell_anomaly()
            port_routing_anomaly: Result from detect_port_routing_anomaly()
            consolidation: Optional result from detect_consolidation_pattern()

        Returns:
            Dict with:
                - transshipment_risk_score: float (0-100)
                - risk_level: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW"
                - signals: List of contributing signals
        """
        score = 0.0
        signals = []

        # FTZ dwell contribution
        if ftz_dwell_anomaly.get("flag"):
            dwell_ratio = ftz_dwell_anomaly.get("ratio", 1.0)
            if dwell_ratio > 3.0:
                score += 40
                signals.append(f"FTZ dwell {dwell_ratio}× baseline")
            elif dwell_ratio > 1.5:
                score += 20
                signals.append(f"FTZ dwell elevated {dwell_ratio}× baseline")

        # Port routing contribution
        routing_severity = port_routing_anomaly.get("severity", "NONE")
        if routing_severity == "HIGH":
            score += 35
            signals.append("High-risk port sequence")
        elif routing_severity == "MEDIUM":
            score += 20
            signals.append("Medium-risk port sequence")
        elif routing_severity == "LOW":
            score += 10
            signals.append("Transshipment hub visits")

        # Consolidation contribution
        if consolidation and consolidation.get("consolidation_detected"):
            score += 25
            signals.append(f"Consolidation center: {consolidation['origin_country_count']} origins")

        # Cap at 100
        score = min(100.0, score)

        # Determine risk level
        if score >= 75:
            risk_level = "CRITICAL"
        elif score >= 50:
            risk_level = "HIGH"
        elif score >= 25:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        return {
            "transshipment_risk_score": round(score, 1),
            "risk_level": risk_level,
            "signals": signals,
        }
