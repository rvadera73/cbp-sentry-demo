"""Risk Corridor Factory and Orchestration Engine

Orchestrates HTS classification, anomaly detection, and corridor creation.
Central domain logic for Risk Corridor instantiation and enrichment.
"""

import hashlib
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

from .hts_classifier import HTSIndustryClassifier
from .volumetric_analyzer import VolumetricAnalyzer
from .temporal_analyzer import TemporalAnalyzer
from .transshipment_detector import TransshipmentDetector

logger = logging.getLogger(__name__)


class RiskCorridorFactory:
    """Factory for creating and classifying Risk Corridors.

    **Domain Model**: A Risk Corridor is defined by:
    - HTS Industry Segment (e.g., "Solar Infrastructure")
    - Geographic Route (origin country × destination country)
    - Supplier Entity (shipper/manufacturer identity)

    **Responsibilities**:
    1. Classify incoming shipments into corridors
    2. Compute volumetric and temporal anomalies
    3. Detect transshipment network patterns
    4. Validate geographic routing logic
    5. Flag macro-level evasion tactics
    """

    def __init__(self):
        """Initialize all sub-analyzers."""
        self.hts_classifier = HTSIndustryClassifier()
        self.volumetric_analyzer = VolumetricAnalyzer(self.hts_classifier)
        self.temporal_analyzer = TemporalAnalyzer()
        self.transshipment_detector = TransshipmentDetector()

    def create_corridor_from_shipment(self, shipment: Dict[str, Any]) -> Dict[str, Any]:
        """Transform a single shipment into a Risk Corridor context.

        **Core Logic**: Extract HTS code, origin, shipper, and map to industry
        segment. Compute baseline risk score based on segment and evasion routes.

        Args:
            shipment: Dict with keys:
                - hts_code or hs_code: str (6-digit HTS code)
                - origin_country: str (ISO 2-letter code)
                - destination_country: str (ISO 2-letter, default "US")
                - shipper_name: str
                - declared_value_usd: float
                - declared_weight_kg: float
                - vessel_name: str (optional)
                - manifest_id: str (optional)

        Returns:
            Dict with keys:
                - corridor_id: Unique corridor identifier
                - hts_chapter: 4-digit HTS chapter
                - hts_6digit: 6-digit HTS code
                - industry_segment: Industry classification
                - origin_country: Origin country code
                - destination_country: Destination country code
                - supplier_entity: Shipper name
                - supplier_entity_hash: Short hash for ID
                - evasion_origin_shifts: List of suspect transshipment routes
                - baseline_capacity_tons: Annual production capacity
                - ad_cvd_rate_pct: Duty rate
                - risk_score_baseline: 0-100 baseline risk
        """
        # Extract HTS code (handle both 'hts_code' and 'hs_code' field names)
        hts_code = shipment.get("hts_code") or shipment.get("hs_code", "000000")
        origin_country = shipment.get("origin_country", "XX")
        destination_country = shipment.get("destination_country", "US")
        shipper_name = shipment.get("shipper_name", "Unknown")

        # Classify to industry segment
        industry_segment = self.hts_classifier.classify_hts_to_segment(hts_code)

        # Generate corridor ID: HC-[4digitHTS]-[origin][dest]-[entity_hash]
        entity_hash = self._entity_hash(shipper_name)
        corridor_id = (
            f"HC-{str(hts_code)[:4]}-{origin_country}{destination_country}-{entity_hash}"
        )

        # Get evasion origin shifts
        evasion_origin_shifts = self.hts_classifier.get_evasion_origin_shifts(
            hts_code, origin_country
        )

        # Lookup AD/CVD rate
        ad_cvd_rate = self.hts_classifier.lookup_ad_cvd_rate(hts_code, origin_country)

        # Compute baseline risk score
        baseline_risk = self._compute_baseline_risk(industry_segment, evasion_origin_shifts)

        return {
            "corridor_id": corridor_id,
            "hts_chapter": str(hts_code)[:4],
            "hts_6digit": str(hts_code)[:6],
            "industry_segment": industry_segment["segment"],
            "origin_country": origin_country,
            "destination_country": destination_country,
            "supplier_entity": shipper_name,
            "supplier_entity_hash": entity_hash,
            "evasion_origin_shifts": evasion_origin_shifts,
            "baseline_capacity_tons": industry_segment.get("baseline_annual_capacity_tons", 10_000_000),
            "ad_cvd_countries": industry_segment.get("ad_cvd_countries", []),
            "ad_cvd_rate_pct": ad_cvd_rate,
            "risk_score_baseline": baseline_risk,
        }

    def aggregate_corridor_metrics(
        self,
        corridor_id: str,
        shipment_rows: List[Dict[str, Any]],
        time_period_days: int = 7,
        prior_period_shipments: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Aggregate multiple shipments in a corridor and compute all anomalies.

        **Core Logic**: Take shipments grouped by corridor and compute:
        1. Volumetric delta (manifest volume vs production capacity)
        2. YoY surge (current vs prior period)
        3. Transshipment indicators (FTZ dwell, port routing)
        4. Composite risk level

        Args:
            corridor_id: Corridor identifier
            shipment_rows: List of shipments in this corridor
            time_period_days: Aggregation window (default 7 days)
            prior_period_shipments: Optional list of shipments from prior period for YoY

        Returns:
            Fully enriched corridor object with all anomalies pre-computed:
                - corridor_id
                - hts_chapter, hts_6digit, industry_segment
                - origin_country, destination_country, supplier_entity
                - shipment_count, aggregate_value_usd, total_weight_tons
                - active_vessels
                - macro_volumetric_delta: Dict with volumetric analysis
                - yoy_surge: Dict with YoY comparison
                - price_anomalies: Dict with unit price analysis
                - transshipment_risk: Dict with transshipment signals
                - risk_level: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW"
                - composite_risk_score: 0-100
                - last_updated: ISO timestamp
        """
        if not shipment_rows:
            return {
                "corridor_id": corridor_id,
                "error": "No shipments in corridor",
            }

        # Parse base corridor from first shipment
        sample = shipment_rows[0]
        base_corridor = self.create_corridor_from_shipment(sample)

        # Aggregate basic metrics
        shipment_count = len(shipment_rows)
        aggregate_value = sum(
            row.get("declared_value_usd", 0) or row.get("value_usd", 0)
            for row in shipment_rows
        )
        total_weight_tons = sum(
            row.get("declared_weight_kg", 0) / 1000.0 for row in shipment_rows
        )
        active_vessels = len(
            set(
                row.get("vessel_name")
                for row in shipment_rows
                if row.get("vessel_name")
            )
        )

        # Convert weight_kg to weight_tons for analyzer
        shipment_rows_with_tons = [
            {
                **row,
                "weight_tons": row.get("weight_tons")
                or (row.get("declared_weight_kg", 0) / 1000.0),
            }
            for row in shipment_rows
        ]

        # Compute volumetric delta
        volumetric_delta = self.volumetric_analyzer.calculate_macro_volumetric_delta(
            hts_code=base_corridor["hts_6digit"],
            origin_country=base_corridor["origin_country"],
            destination_country=base_corridor["destination_country"],
            manifest_rows=shipment_rows_with_tons,
            time_period_days=time_period_days,
            baseline_capacity_tons=base_corridor["baseline_capacity_tons"],
        )

        # Compute YoY surge
        current_metrics = {"shipment_count": shipment_count, "aggregate_value": aggregate_value}
        if prior_period_shipments:
            prior_count = len(prior_period_shipments)
            prior_value = sum(
                row.get("declared_value_usd", 0) or row.get("value_usd", 0)
                for row in prior_period_shipments
            )
            prior_metrics = {"shipment_count": prior_count, "aggregate_value": prior_value}
        else:
            prior_metrics = {"shipment_count": max(1, shipment_count), "aggregate_value": max(1, aggregate_value)}

        yoy_surge = self.temporal_analyzer.calculate_yoy_surge(
            current_metrics, prior_metrics, time_period_name=f"{time_period_days}-day"
        )

        # Detect price anomalies
        price_anomalies = self.volumetric_analyzer.detect_weight_value_mismatch(
            shipment_rows_with_tons, base_corridor["hts_6digit"]
        )

        # Detect shipping frequency anomalies
        frequency_anomalies = self.volumetric_analyzer.detect_frequency_spike(
            shipment_rows, baseline_shipments_per_week=5
        )

        # Transshipment risk (if FTZ data available)
        transshipment_risk = {"risk_score": 0.0, "risk_level": "LOW", "signals": []}
        if any(row.get("ftz_code") for row in shipment_rows):
            ftz_codes = set(row.get("ftz_code") for row in shipment_rows if row.get("ftz_code"))
            for ftz_code in ftz_codes:
                dwell_days = 2.0  # Default estimate if not provided
                ftz_dwell = self.transshipment_detector.detect_ftz_dwell_anomaly(
                    ftz_code, dwell_days
                )
                if ftz_dwell.get("flag"):
                    transshipment_risk["risk_score"] += ftz_dwell.get("confidence", 0.5) * 20
                    transshipment_risk["signals"].append(ftz_dwell.get("signal", ""))

            transshipment_risk["risk_score"] = min(100.0, transshipment_risk["risk_score"])
            transshipment_risk["risk_level"] = (
                "HIGH" if transshipment_risk["risk_score"] > 60 else
                "MEDIUM" if transshipment_risk["risk_score"] > 30 else
                "LOW"
            )

        # Compute composite risk level
        risk_level = self._compute_corridor_risk_level(
            volumetric_delta["status"],
            yoy_surge["surge_status"],
            base_corridor["risk_score_baseline"],
            price_anomalies.get("anomaly_detected", False),
            transshipment_risk.get("risk_level", "LOW"),
        )

        # Composite risk score (0-100)
        composite_risk_score = self._compute_composite_risk_score(
            volumetric_delta,
            yoy_surge,
            base_corridor["risk_score_baseline"],
            price_anomalies,
            transshipment_risk,
        )

        return {
            **base_corridor,
            "shipment_count": shipment_count,
            "aggregate_value_usd": round(aggregate_value, 2),
            "total_weight_tons": round(total_weight_tons, 2),
            "active_vessels": active_vessels,
            "macro_volumetric_delta": volumetric_delta,
            "yoy_surge": yoy_surge,
            "price_anomalies": price_anomalies,
            "frequency_anomalies": frequency_anomalies,
            "transshipment_risk": transshipment_risk,
            "risk_level": risk_level,
            "composite_risk_score": round(composite_risk_score, 1),
            "last_updated": datetime.now().isoformat(),
        }

    def group_shipments_by_corridor(
        self, shipments: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Group shipments by corridor ID.

        Args:
            shipments: List of shipment dicts

        Returns:
            Dict mapping corridor_id to list of shipments
        """
        corridors = {}
        for shipment in shipments:
            base = self.create_corridor_from_shipment(shipment)
            corridor_id = base["corridor_id"]
            if corridor_id not in corridors:
                corridors[corridor_id] = []
            corridors[corridor_id].append(shipment)
        return corridors

    def _entity_hash(self, entity_name: str) -> str:
        """Generate short 4-character hash for corridor ID."""
        return hashlib.md5(entity_name.encode()).hexdigest()[:4].upper()

    def _compute_baseline_risk(
        self, segment: Dict[str, Any], evasion_shifts: List[str]
    ) -> float:
        """Compute baseline risk score (0-100) before anomaly detection.

        Args:
            segment: Industry segment dict
            evasion_shifts: List of known evasion route alternatives

        Returns:
            Risk score 0-100
        """
        # Base score for high-risk commodities
        if segment["segment"] != "General Merchandise":
            base_score = 50
        else:
            base_score = 10

        # Add points for known evasion routes
        evasion_bonus = len(evasion_shifts) * 10

        return min(100.0, base_score + evasion_bonus)

    def _compute_corridor_risk_level(
        self,
        volumetric_status: str,
        yoy_status: str,
        baseline_risk: float,
        price_anomaly: bool = False,
        transshipment_level: str = "LOW",
    ) -> str:
        """Map multiple signals to HIGH/MEDIUM/LOW.

        Args:
            volumetric_status: "FLAGGED" | "NORMAL"
            yoy_status: "CRITICAL" | "HIGH" | "MEDIUM" | "NORMAL"
            baseline_risk: 0-100
            price_anomaly: bool
            transshipment_level: "HIGH" | "MEDIUM" | "LOW"

        Returns:
            "CRITICAL" | "HIGH" | "MEDIUM" | "LOW"
        """
        high_signals = sum([
            volumetric_status == "FLAGGED",
            yoy_status in ["CRITICAL", "HIGH"],
            baseline_risk >= 70,
            price_anomaly,
            transshipment_level == "HIGH",
        ])

        if high_signals >= 3:
            return "CRITICAL"
        elif high_signals >= 2:
            return "HIGH"
        elif high_signals >= 1:
            return "MEDIUM"
        else:
            return "LOW"

    def _compute_composite_risk_score(
        self,
        volumetric_delta: Dict[str, Any],
        yoy_surge: Dict[str, Any],
        baseline_risk: float,
        price_anomalies: Dict[str, Any],
        transshipment_risk: Dict[str, Any],
    ) -> float:
        """Synthesize all signals into composite 0-100 risk score.

        Args:
            volumetric_delta: From VolumetricAnalyzer
            yoy_surge: From TemporalAnalyzer
            baseline_risk: From _compute_baseline_risk
            price_anomalies: From detect_weight_value_mismatch
            transshipment_risk: From detect_ftz_dwell_anomaly, etc.

        Returns:
            Composite risk score 0-100
        """
        score = baseline_risk * 0.2  # 20% baseline

        # Volumetric contribution (40%)
        if volumetric_delta["status"] == "FLAGGED":
            vol_score = min(40.0, 10 + (volumetric_delta["ratio"] * 5))
        else:
            vol_score = max(0.0, volumetric_delta["ratio"] * 5)
        score += vol_score

        # YoY surge contribution (20%)
        surge_pct = yoy_surge["volume_surge_pct"]
        if yoy_surge["surge_status"] == "CRITICAL":
            score += 20
        elif yoy_surge["surge_status"] == "HIGH":
            score += 15
        elif yoy_surge["surge_status"] == "MEDIUM":
            score += 8
        else:
            score += max(0, min(8, surge_pct / 50))

        # Price anomaly contribution (10%)
        if price_anomalies.get("anomaly_detected"):
            score += 10

        # Transshipment risk contribution (10%)
        score += transshipment_risk.get("risk_score", 0) * 0.1

        return min(100.0, score)
