"""Year-over-Year Surge Detection Engine

Detects temporal anomalies in corridor activity by comparing current period
volume/value vs prior matching period.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class TemporalAnalyzer:
    """Detects temporal anomalies in corridor activity.

    Primary use case: Flag corridors where volume/value surged unexpectedly
    vs prior matching period (e.g., this week vs last week, this month vs
    last month, this quarter vs last year same quarter).
    """

    # YoY surge thresholds (percentage increase)
    SURGE_THRESHOLDS = {
        "CRITICAL": 250,  # > 250% surge
        "HIGH": 150,  # > 150% surge
        "MEDIUM": 75,  # > 75% surge
        "NORMAL": 0,  # < 75% surge
    }

    def __init__(self):
        """Initialize temporal analyzer."""
        pass

    def calculate_yoy_surge(
        self,
        current_metrics: Dict[str, Any],
        prior_metrics: Dict[str, Any],
        time_period_name: str = "7-day",
    ) -> Dict[str, Any]:
        """Compare current corridor metrics vs prior matching period.

        **Logic**: Calculate percentage surge for shipment count and aggregate value.
        Flag as CRITICAL if > 250%, HIGH if > 150%, etc.

        Args:
            current_metrics: Dict with keys:
                - shipment_count: int
                - aggregate_value: float (USD)
            prior_metrics: Dict with same keys (from prior period)
            time_period_name: Description of period (e.g., "7-day", "monthly")

        Returns:
            Dict with keys:
                - volume_surge_pct: % change in shipment count
                - value_surge_pct: % change in aggregate value
                - surge_status: "CRITICAL" | "HIGH" | "MEDIUM" | "NORMAL"
                - signal: Human-readable description
                - current_shipment_count: int
                - prior_shipment_count: int
                - current_value_usd: float
                - prior_value_usd: float
        """
        current_count = current_metrics.get("shipment_count", 0)
        prior_count = prior_metrics.get("shipment_count", 0)
        current_value = current_metrics.get("aggregate_value", 0)
        prior_value = prior_metrics.get("aggregate_value", 0)

        # Calculate surge percentages (with safe division)
        volume_surge_pct = (
            ((current_count - prior_count) / max(prior_count, 1)) * 100
            if prior_count > 0
            else (100 if current_count > 0 else 0)
        )

        value_surge_pct = (
            ((current_value - prior_value) / max(prior_value, 1)) * 100
            if prior_value > 0
            else (100 if current_value > 0 else 0)
        )

        # Determine surge status (use volume surge as primary signal)
        surge_status = self._classify_surge_severity(volume_surge_pct)

        return {
            "volume_surge_pct": round(volume_surge_pct, 1),
            "value_surge_pct": round(value_surge_pct, 1),
            "surge_status": surge_status,
            "signal": f"Volume surge {round(volume_surge_pct, 1)}% {time_period_name} "
            f"({current_count} vs {prior_count} shipments); "
            f"value surge {round(value_surge_pct, 1)}%",
            "current_shipment_count": current_count,
            "prior_shipment_count": prior_count,
            "current_value_usd": round(current_value, 2),
            "prior_value_usd": round(prior_value, 2),
        }

    def detect_seasonal_anomaly(
        self,
        current_period_value: float,
        historical_values: Dict[str, float],
    ) -> Dict[str, Any]:
        """Detect if current period deviates from seasonal pattern.

        **Use case**: Some commodities (e.g., agricultural) have natural seasonal
        patterns. This detector flags when a period's activity significantly
        deviates from historical same-period baseline.

        Args:
            current_period_value: Current period aggregate value (USD)
            historical_values: Dict mapping period names to historical values
                E.g., {"Jan-2024": 50000, "Jan-2025": 48000, "Feb-2024": 45000}

        Returns:
            Dict with:
                - anomaly_detected: bool
                - historical_average: float
                - current_deviation_pct: float
                - signal: Description
        """
        if not historical_values:
            return {
                "anomaly_detected": False,
                "historical_average": 0.0,
                "current_deviation_pct": 0.0,
                "signal": "No historical data for comparison",
            }

        values = list(historical_values.values())
        if not values:
            return {
                "anomaly_detected": False,
                "historical_average": 0.0,
                "current_deviation_pct": 0.0,
                "signal": "Historical data is empty",
            }

        historical_avg = sum(values) / len(values)
        if historical_avg == 0:
            return {
                "anomaly_detected": False,
                "historical_average": 0.0,
                "current_deviation_pct": 0.0,
                "signal": "Historical average is zero",
            }

        deviation_pct = (
            ((current_period_value - historical_avg) / historical_avg) * 100
        )
        anomaly_detected = abs(deviation_pct) > 50  # Flag > 50% deviation

        return {
            "anomaly_detected": anomaly_detected,
            "historical_average": round(historical_avg, 2),
            "current_value": round(current_period_value, 2),
            "current_deviation_pct": round(deviation_pct, 1),
            "signal": f"Current period {round(deviation_pct, 1)}% vs historical average "
            f"({current_period_value:.0f} vs {historical_avg:.0f})",
        }

    def calculate_trend(
        self, time_series: List[Tuple[str, float]], window_days: int = 7
    ) -> Dict[str, Any]:
        """Calculate trend direction (up/down/flat) over time series.

        **Use case**: Detect if a corridor is consistently ramping up activity,
        which could indicate planned evasion campaign.

        Args:
            time_series: List of (date_str, value) tuples
            window_days: Number of days to use for trend window

        Returns:
            Dict with:
                - trend: "UP" | "DOWN" | "FLAT"
                - slope: float (change per day)
                - r_squared: float (fit quality 0-1)
                - signal: Description
        """
        if len(time_series) < 2:
            return {
                "trend": "INSUFFICIENT_DATA",
                "slope": 0.0,
                "r_squared": 0.0,
                "signal": "Not enough data points",
            }

        # Simple linear regression
        n = len(time_series)
        x_vals = list(range(n))
        y_vals = [v for _, v in time_series]

        x_mean = sum(x_vals) / n
        y_mean = sum(y_vals) / n

        numerator = sum((x_vals[i] - x_mean) * (y_vals[i] - y_mean) for i in range(n))
        denominator = sum((x_vals[i] - x_mean) ** 2 for i in range(n))

        if denominator == 0:
            return {
                "trend": "FLAT",
                "slope": 0.0,
                "r_squared": 0.0,
                "signal": "No variance in x (constant time intervals)",
            }

        slope = numerator / denominator

        # Calculate R²
        ss_tot = sum((y_vals[i] - y_mean) ** 2 for i in range(n))
        ss_res = sum((y_vals[i] - (slope * x_vals[i] + (y_mean - slope * x_mean))) ** 2 for i in range(n))
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

        # Classify trend
        if slope > y_mean * 0.05:  # > 5% increase per step
            trend = "UP"
        elif slope < -y_mean * 0.05:  # > 5% decrease per step
            trend = "DOWN"
        else:
            trend = "FLAT"

        return {
            "trend": trend,
            "slope": round(slope, 2),
            "r_squared": round(r_squared, 3),
            "signal": f"{trend} trend with slope {round(slope, 2)} per period (R²={round(r_squared, 3)})",
            "data_points": n,
        }

    def detect_cyclical_pattern(
        self, time_series: List[Tuple[str, float]]
    ) -> Dict[str, Any]:
        """Detect if corridor shows cyclical shipping pattern.

        **Use case**: Some evasion tactics operate on cycles (e.g., ship weekly
        to avoid suspicion, or use port rotation).

        Args:
            time_series: List of (date_str, value) tuples (should be chronologically ordered)

        Returns:
            Dict with:
                - pattern_detected: bool
                - regularity: "VERY_REGULAR" | "SOMEWHAT_REGULAR" | "IRREGULAR"
                - cycle_length_days: int or None
                - signal: Description
        """
        if len(time_series) < 3:
            return {
                "pattern_detected": False,
                "regularity": "INSUFFICIENT_DATA",
                "cycle_length_days": None,
                "signal": "Not enough data points",
            }

        # Extract dates and convert
        dates = []
        for date_str, _ in time_series:
            try:
                dates.append(datetime.fromisoformat(date_str))
            except (ValueError, TypeError):
                logger.warning(f"Could not parse date: {date_str}")
                return {
                    "pattern_detected": False,
                    "regularity": "PARSE_ERROR",
                    "cycle_length_days": None,
                    "signal": "Could not parse dates",
                }

        # Calculate intervals between consecutive shipments
        intervals = []
        for i in range(1, len(dates)):
            interval = (dates[i] - dates[i - 1]).days
            if interval > 0:  # Ignore same-day or negative intervals
                intervals.append(interval)

        if not intervals:
            return {
                "pattern_detected": False,
                "regularity": "SINGLE_DAY",
                "cycle_length_days": None,
                "signal": "All shipments on same date",
            }

        # Analyze regularity
        avg_interval = sum(intervals) / len(intervals)
        variance = sum((i - avg_interval) ** 2 for i in intervals) / len(intervals)
        std_dev = variance**0.5
        coeff_variation = (std_dev / avg_interval) if avg_interval > 0 else 0

        # Classify regularity
        if coeff_variation < 0.15:  # < 15% variation = very regular
            regularity = "VERY_REGULAR"
            pattern_detected = True
        elif coeff_variation < 0.40:  # < 40% variation = somewhat regular
            regularity = "SOMEWHAT_REGULAR"
            pattern_detected = True
        else:
            regularity = "IRREGULAR"
            pattern_detected = False

        return {
            "pattern_detected": pattern_detected,
            "regularity": regularity,
            "cycle_length_days": round(avg_interval),
            "std_dev_days": round(std_dev, 1),
            "coefficient_variation": round(coeff_variation, 3),
            "signal": f"{regularity} pattern: ~{round(avg_interval)} day cycle "
            f"(σ={round(std_dev, 1)} days, CV={round(coeff_variation, 3)})",
            "shipment_count": len(time_series),
        }

    def _classify_surge_severity(self, surge_pct: float) -> str:
        """Classify surge percentage into severity level.

        Args:
            surge_pct: Percentage change

        Returns:
            "CRITICAL" | "HIGH" | "MEDIUM" | "NORMAL"
        """
        if surge_pct > self.SURGE_THRESHOLDS["CRITICAL"]:
            return "CRITICAL"
        elif surge_pct > self.SURGE_THRESHOLDS["HIGH"]:
            return "HIGH"
        elif surge_pct > self.SURGE_THRESHOLDS["MEDIUM"]:
            return "MEDIUM"
        else:
            return "NORMAL"
