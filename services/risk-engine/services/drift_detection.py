"""Drift detection service for model monitoring."""
import logging
from typing import Dict, List, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class DriftDetector:
    """Detects distribution and performance drift in risk scoring."""

    def __init__(self, baseline_stats: Dict[str, Any] = None):
        """
        Initialize drift detector.

        Args:
            baseline_stats: Baseline statistics for drift comparison
        """
        self.baseline_stats = baseline_stats or {}
        self.current_stats = {}

    def update_statistics(self, scores: List[float]):
        """
        Update current statistics with new scores.

        Args:
            scores: List of risk scores
        """
        if not scores:
            return

        self.current_stats = {
            "mean": sum(scores) / len(scores),
            "min": min(scores),
            "max": max(scores),
            "count": len(scores),
            "timestamp": datetime.utcnow().isoformat(),
        }
        logger.debug(f"Updated statistics: {self.current_stats}")

    def detect_drift(self, threshold: float = 0.1) -> Dict[str, Any]:
        """
        Detect drift between baseline and current statistics.

        Args:
            threshold: Drift threshold (0-1)

        Returns:
            Drift detection result
        """
        if not self.baseline_stats or not self.current_stats:
            return {"drift_detected": False, "reason": "Insufficient data"}

        baseline_mean = self.baseline_stats.get("mean", 0)
        current_mean = self.current_stats.get("mean", 0)

        if baseline_mean == 0:
            return {"drift_detected": False, "reason": "Baseline mean is zero"}

        mean_drift = abs(current_mean - baseline_mean) / baseline_mean
        drift_detected = mean_drift > threshold

        return {
            "drift_detected": drift_detected,
            "mean_drift": mean_drift,
            "threshold": threshold,
            "baseline_mean": baseline_mean,
            "current_mean": current_mean,
            "timestamp": self.current_stats.get("timestamp"),
        }

    def get_health_report(self) -> Dict[str, Any]:
        """Get comprehensive model health report."""
        return {
            "baseline_stats": self.baseline_stats,
            "current_stats": self.current_stats,
            "drift_assessment": self.detect_drift(),
        }
