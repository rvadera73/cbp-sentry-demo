"""Macro Volumetric Delta Calculator

Detects when a corridor's outbound volume exceeds known domestic capacity,
signaling potential transshipment or duty evasion at scale.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class VolumetricAnalyzer:
    """Detects macro-level volume anomalies indicating evasion at scale.

    Core logic: Compare total manifest volume in a time period against
    known domestic production capacity. A ratio > 3.0× is flagged as anomalous.
    """

    def __init__(self, hts_classifier=None):
        """Initialize with optional HTS classifier dependency.

        Args:
            hts_classifier: HTSIndustryClassifier instance (optional, for capacity lookup)
        """
        self.hts_classifier = hts_classifier

    def calculate_macro_volumetric_delta(
        self,
        hts_code: str,
        origin_country: str,
        destination_country: str,
        manifest_rows: List[Dict[str, Any]],
        time_period_days: int = 7,
        baseline_capacity_tons: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Compare total manifest volume against known domestic production capacity.

        **Logic**: For a corridor (HTS + origin + destination), sum all manifest rows
        and compare against daily capacity × time period. Ratios > 3.0 indicate
        potential duty evasion or transshipment at scale.

        Args:
            hts_code: 6-digit HTS code
            origin_country: Alleged country of origin (ISO 2-letter)
            destination_country: Destination country (ISO 2-letter)
            manifest_rows: List of shipment records in corridor
                Each row should have a 'weight_tons' or 'declared_weight_kg' field
            time_period_days: Aggregation window (default 7 days)
            baseline_capacity_tons: Override baseline capacity (uses classifier if None)

        Returns:
            Dict with keys:
                - status: "FLAGGED" | "NORMAL"
                - outbound_volume_manifest_tons: Total manifest volume
                - estimated_daily_capacity_tons: Capacity per day
                - estimated_period_capacity_tons: Capacity for period
                - ratio: outbound / period_capacity
                - signal: Human-readable description
                - confidence: 0.5-0.95 (higher ratio = higher confidence)
                - severity: "CRITICAL" | "HIGH" | "MEDIUM"
        """
        # Get baseline capacity
        if baseline_capacity_tons is None:
            if self.hts_classifier:
                baseline_capacity_tons = self.hts_classifier.get_baseline_capacity_tons(
                    hts_code
                )
            else:
                # Default capacity for unknown HTS
                baseline_capacity_tons = 10_000_000

        # Aggregate manifest volume
        total_manifest_tons = 0.0
        for row in manifest_rows:
            # Support both weight_tons and declared_weight_kg
            if "weight_tons" in row:
                total_manifest_tons += row.get("weight_tons", 0)
            elif "declared_weight_kg" in row:
                total_manifest_tons += row.get("declared_weight_kg", 0) / 1000.0
            else:
                logger.warning(f"Row missing weight field: {row}")

        # Calculate period capacity
        daily_capacity_tons = baseline_capacity_tons / 365.0
        period_capacity_tons = daily_capacity_tons * time_period_days

        # Compute ratio
        ratio = (
            total_manifest_tons / period_capacity_tons if period_capacity_tons > 0 else 0
        )

        # Determine status and severity
        if ratio > 4.0:
            status = "FLAGGED"
            severity = "CRITICAL"
        elif ratio > 3.0:
            status = "FLAGGED"
            severity = "HIGH"
        elif ratio > 2.0:
            status = "NORMAL"
            severity = "MEDIUM"
        else:
            status = "NORMAL"
            severity = "LOW"

        # Confidence: higher ratio = higher confidence (but capped at 0.95)
        confidence = min(0.95, 0.5 + (ratio * 0.05))

        return {
            "status": status,
            "outbound_volume_manifest_tons": round(total_manifest_tons, 2),
            "estimated_daily_capacity_tons": round(daily_capacity_tons, 1),
            "estimated_period_capacity_tons": round(period_capacity_tons, 1),
            "ratio": round(ratio, 2),
            "signal": f"Outbound volume {round(ratio, 2)}× estimated production capacity ({total_manifest_tons:.0f} tons vs {period_capacity_tons:.0f} ton capacity)",
            "confidence": round(confidence, 2),
            "severity": severity,
        }

    def detect_weight_value_mismatch(
        self, manifest_rows: List[Dict[str, Any]], hts_code: str
    ) -> Dict[str, Any]:
        """Detect price/weight anomalies suggesting misclassification or transshipment.

        Low unit price can indicate dumping; inconsistent pricing across shipments
        in same corridor can signal transshipment (repackaging).

        Args:
            manifest_rows: List of shipment records
            hts_code: HTS code for baseline comparison

        Returns:
            Dict with:
                - anomaly_detected: bool
                - average_unit_price_per_ton: float
                - price_std_dev: float
                - lowest_unit_price: float
                - suspect_rows: List of indices with anomalous pricing
                - signal: Description
        """
        if not manifest_rows:
            return {
                "anomaly_detected": False,
                "average_unit_price_per_ton": 0.0,
                "price_std_dev": 0.0,
                "lowest_unit_price": 0.0,
                "suspect_rows": [],
                "signal": "No rows to analyze",
            }

        # Calculate unit prices (USD per ton)
        unit_prices = []
        for i, row in enumerate(manifest_rows):
            weight_tons = row.get("weight_tons", 0)
            if weight_tons == 0:
                weight_tons = row.get("declared_weight_kg", 0) / 1000.0

            value_usd = row.get("declared_value", 0) or row.get("value_usd", 0)

            if weight_tons > 0:
                unit_price = value_usd / weight_tons
                unit_prices.append((i, unit_price))

        if not unit_prices:
            return {
                "anomaly_detected": False,
                "average_unit_price_per_ton": 0.0,
                "price_std_dev": 0.0,
                "lowest_unit_price": 0.0,
                "suspect_rows": [],
                "signal": "Unable to calculate unit prices (missing weight/value)",
            }

        prices = [p[1] for p in unit_prices]
        avg_price = sum(prices) / len(prices)
        min_price = min(prices)
        max_price = max(prices)

        # Calculate std dev
        variance = sum((p - avg_price) ** 2 for p in prices) / len(prices)
        std_dev = variance**0.5

        # Flag outliers (> 2 std devs from mean or > 3× difference in range)
        suspect_rows = []
        for idx, price in unit_prices:
            if price < (avg_price - 2 * std_dev) or price > (avg_price + 2 * std_dev):
                suspect_rows.append(idx)

        anomaly_detected = len(suspect_rows) > 0 and std_dev > avg_price * 0.3

        return {
            "anomaly_detected": anomaly_detected,
            "average_unit_price_per_ton": round(avg_price, 2),
            "price_std_dev": round(std_dev, 2),
            "lowest_unit_price": round(min_price, 2),
            "highest_unit_price": round(max_price, 2),
            "price_range_ratio": round(max_price / min_price, 2) if min_price > 0 else 0,
            "suspect_rows": suspect_rows,
            "signal": (
                f"Price variation {round(std_dev, 2)} std dev; "
                f"range {min_price:.0f}-{max_price:.0f} USD/ton"
            ),
        }

    def detect_frequency_spike(
        self, manifest_rows: List[Dict[str, Any]], baseline_shipments_per_week: int = 5
    ) -> Dict[str, Any]:
        """Detect unusual shipping frequency in corridor.

        Args:
            manifest_rows: List of shipment records (should have 'filing_date' or 'date')
            baseline_shipments_per_week: Expected weekly shipment count

        Returns:
            Dict with spike analysis
        """
        if not manifest_rows:
            return {
                "spike_detected": False,
                "shipment_count": 0,
                "frequency_anomaly": "No data",
            }

        # Extract and deduplicate dates
        dates = []
        for row in manifest_rows:
            date_field = row.get("filing_date") or row.get("date")
            if date_field:
                dates.append(date_field)

        if not dates:
            return {
                "spike_detected": False,
                "shipment_count": len(manifest_rows),
                "frequency_anomaly": "No date information",
            }

        # Calculate days between shipments
        try:
            if isinstance(dates[0], str):
                from datetime import datetime

                dates = [datetime.fromisoformat(d) for d in dates]
            dates.sort()
        except Exception as e:
            logger.warning(f"Failed to parse dates: {e}")
            return {
                "spike_detected": False,
                "shipment_count": len(manifest_rows),
                "frequency_anomaly": "Could not parse dates",
            }

        # Analyze frequency
        spike_detected = False
        if len(dates) > 1:
            time_span_days = (dates[-1] - dates[0]).days
            if time_span_days > 0:
                actual_frequency = len(dates) / (time_span_days / 7.0)
                spike_threshold = baseline_shipments_per_week * 2.0
                spike_detected = actual_frequency > spike_threshold
            else:
                # All dates on same day = spike
                spike_detected = len(dates) > 2

        return {
            "spike_detected": spike_detected,
            "shipment_count": len(manifest_rows),
            "frequency_anomaly": f"~{len(manifest_rows)} shipments over {(dates[-1] - dates[0]).days if len(dates) > 1 else 0} days"
            if len(dates) > 1
            else f"{len(manifest_rows)} shipments on single date",
        }
