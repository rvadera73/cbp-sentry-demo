"""
Performance Metrics Calculation Engine

Generic, domain-agnostic engine for calculating performance metrics.
Supports multiple metric types: count_per_period, ratio, rate_of_change, threshold.

Designed to work with:
- YAML config files (source of truth for domain structure)
- MLflow tags (model-specific gate requirements)
- SQLite database (direct queries for calculation)
"""

import json
import sqlite3
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, date
from pathlib import Path
import yaml

logger = logging.getLogger(__name__)


@dataclass
class MetricResult:
    """Result of a single metric calculation"""
    metric_name: str
    metric_type: str
    measured_value: float
    threshold_value: float
    status: str  # 'passed', 'failed', 'pending', 'error'
    period_start_date: date
    period_end_date: date
    unit: str
    calculation_details: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with date serialization"""
        d = asdict(self)
        d['period_start_date'] = self.period_start_date.isoformat()
        d['period_end_date'] = self.period_end_date.isoformat()
        return d


class PerformanceMetricsEngine:
    """
    Calculates performance metrics for a given domain and model.

    Supports configuration via:
    - Config file (YAML): Domain structure, gate definitions, metric specs
    - MLflow tags: Model-specific performance requirements

    Example usage:
        engine = PerformanceMetricsEngine(config_path="metrics_config_cbp.yml")
        results = engine.calculate_metrics(
            period_start=date(2026, 1, 1),
            period_end=date(2026, 3, 31)
        )
    """

    def __init__(self, config_dict: Optional[Dict] = None, config_path: Optional[str] = None,
                 db_path: str = "/home/rahulvadera/cbp-sentry/data/cbp_sentry.db"):
        """
        Initialize engine with configuration.

        Args:
            config_dict: Configuration dictionary (takes precedence)
            config_path: Path to YAML config file
            db_path: Path to SQLite database
        """
        self.db_path = db_path
        self.config = config_dict or {}

        # Load from file if provided
        if config_path and not config_dict:
            self.config = self._load_yaml_config(config_path)

        if not self.config:
            raise ValueError("Must provide either config_dict or config_path")

        self.domain = self.config.get('domain')
        self.model = self.config.get('model')
        self.gates = self.config.get('gates', [])

        logger.info(f"PerformanceMetricsEngine initialized for {self.domain}/{self.model}")

    @staticmethod
    def _load_yaml_config(config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)

    def calculate_metrics(self, period_start: date, period_end: date) -> List[MetricResult]:
        """
        Calculate all metrics for the given period.

        Args:
            period_start: Start date of evaluation period
            period_end: End date of evaluation period

        Returns:
            List of MetricResult objects
        """
        results = []

        # Find applicable gate(s) for this period
        applicable_gates = self._find_applicable_gates(period_start, period_end)

        for gate in applicable_gates:
            gate_id = gate.get('gate_id')
            metrics = gate.get('metrics', [])

            for metric_spec in metrics:
                try:
                    result = self._calculate_metric(
                        metric_spec=metric_spec,
                        period_start=period_start,
                        period_end=period_end
                    )
                    results.append(result)
                except Exception as e:
                    logger.error(f"Error calculating {metric_spec.get('name')}: {e}")
                    results.append(MetricResult(
                        metric_name=metric_spec.get('name', 'unknown'),
                        metric_type=metric_spec.get('type', 'unknown'),
                        measured_value=0.0,
                        threshold_value=metric_spec.get('threshold', 0.0),
                        status='error',
                        period_start_date=period_start,
                        period_end_date=period_end,
                        unit=metric_spec.get('unit', ''),
                        calculation_details={'error': str(e)}
                    ))

        return results

    def _find_applicable_gates(self, period_start: date, period_end: date) -> List[Dict]:
        """
        Find which gates are applicable for the given period.

        Based on award_date and timeline_days.
        """
        applicable = []
        award_date = self._parse_date(self.config.get('award_date'))

        if not award_date:
            return self.gates  # Return all gates if no award date specified

        for gate in self.gates:
            timeline_days = gate.get('timeline_days', [0, 999])
            days_since_award = (datetime.now().date() - award_date).days

            if timeline_days[0] <= days_since_award <= timeline_days[1]:
                applicable.append(gate)

        return applicable

    def _calculate_metric(self, metric_spec: Dict, period_start: date, period_end: date) -> MetricResult:
        """
        Calculate a single metric based on its type.

        Metric types:
        - count_per_period: Count rows matching filter in period
        - ratio: Numerator / denominator
        - rate_of_change: (Current - Baseline) / Baseline * 100
        - threshold: Compare static value against threshold
        """
        metric_type = metric_spec.get('type')
        metric_name = metric_spec.get('name')
        threshold = float(metric_spec.get('threshold', 0.0))

        if metric_type == 'count_per_period':
            measured_value = self._count_per_period(
                source=metric_spec.get('source'),
                filter_logic=metric_spec.get('filter'),
                period=metric_spec.get('period'),
                period_start=period_start,
                period_end=period_end
            )
        elif metric_type == 'ratio':
            measured_value = self._ratio_metric(
                numerator_config=metric_spec.get('numerator'),
                denominator_config=metric_spec.get('denominator'),
                period_start=period_start,
                period_end=period_end
            )
        elif metric_type == 'rate_of_change':
            measured_value = self._rate_of_change(
                source=metric_spec.get('source'),
                measure=metric_spec.get('measure'),
                baseline=metric_spec.get('baseline'),
                period_start=period_start,
                period_end=period_end
            )
        elif metric_type == 'threshold':
            measured_value = self._threshold_metric(
                source=metric_spec.get('source'),
                measure=metric_spec.get('measure'),
                period_start=period_start,
                period_end=period_end
            )
        else:
            raise ValueError(f"Unknown metric type: {metric_type}")

        # Determine status
        status = 'passed' if measured_value >= threshold else 'failed'

        return MetricResult(
            metric_name=metric_name,
            metric_type=metric_type,
            measured_value=measured_value,
            threshold_value=threshold,
            status=status,
            period_start_date=period_start,
            period_end_date=period_end,
            unit=metric_spec.get('unit', ''),
            calculation_details={
                'query_type': metric_type,
                'source': metric_spec.get('source'),
                'period_days': (period_end - period_start).days
            }
        )

    def _count_per_period(self, source: str, filter_logic: Optional[str],
                          period: str, period_start: date, period_end: date) -> float:
        """
        Count rows matching filter in the given period.

        Examples:
        - source: 'reference_packages'
          filter_logic: "status='approved' AND created > date_sub(now(), INTERVAL 7 day)"
          period: 'week'
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Build base query
            query = f"SELECT COUNT(*) FROM {source}"

            # Add date filter
            if source == 'reference_packages':
                date_filter = f"created_at BETWEEN '{period_start}' AND '{period_end}'"
            else:
                date_filter = f"created_at BETWEEN '{period_start}' AND '{period_end}'"

            query += f" WHERE {date_filter}"

            # Add custom filter if provided
            if filter_logic:
                query += f" AND ({filter_logic})"

            logger.debug(f"Executing count query: {query}")
            cursor.execute(query)
            result = cursor.fetchone()
            count = float(result[0]) if result else 0.0

            return count

        finally:
            conn.close()

    def _ratio_metric(self, numerator_config: Dict, denominator_config: Dict,
                      period_start: date, period_end: date) -> float:
        """
        Calculate numerator / denominator ratio.

        Example:
            numerator: {source: 'shipments', filter: "status='processed'"}
            denominator: {source: 'shipments', filter: "status IN ('pending', 'processed')"}
        """
        numerator = self._count_per_period(
            source=numerator_config.get('source'),
            filter_logic=numerator_config.get('filter'),
            period='day',
            period_start=period_start,
            period_end=period_end
        )

        denominator = self._count_per_period(
            source=denominator_config.get('source'),
            filter_logic=denominator_config.get('filter'),
            period='day',
            period_start=period_start,
            period_end=period_end
        )

        if denominator == 0:
            return 0.0

        return (numerator / denominator) * 100.0

    def _rate_of_change(self, source: str, measure: str,
                        baseline: float, period_start: date, period_end: date) -> float:
        """
        Calculate rate of change: (Current - Baseline) / Baseline * 100

        Example:
            source: 'risk_scores'
            measure: 'average score'
            baseline: 0.65
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Query current average for the period
            query = f"""
                SELECT AVG(score) FROM {source}
                WHERE created_at BETWEEN '{period_start}' AND '{period_end}'
            """
            cursor.execute(query)
            result = cursor.fetchone()
            current_value = float(result[0]) if result and result[0] else 0.0

            if baseline == 0:
                return 0.0

            rate_of_change = ((current_value - baseline) / baseline) * 100.0
            return rate_of_change

        finally:
            conn.close()

    def _threshold_metric(self, source: str, measure: str,
                          period_start: date, period_end: date) -> float:
        """
        Retrieve a static threshold metric value from database.

        Example:
            source: 'model_evaluation'
            measure: 'auc'
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Query for the specific measure
            # This assumes a table with model evaluation metrics
            query = f"""
                SELECT value FROM model_evaluation_metrics
                WHERE metric_name='{measure}'
                AND model_id='{self.model}'
                ORDER BY created_at DESC LIMIT 1
            """
            cursor.execute(query)
            result = cursor.fetchone()

            return float(result[0]) if result else 0.0

        except Exception as e:
            logger.warning(f"Could not retrieve threshold metric {measure}: {e}")
            return 0.0

        finally:
            conn.close()

    @staticmethod
    def _parse_date(date_str: Optional[str]) -> Optional[date]:
        """Parse date string in ISO format"""
        if not date_str:
            return None
        try:
            return datetime.fromisoformat(date_str).date()
        except (ValueError, TypeError):
            return None

    def save_results_to_db(self, results: List[MetricResult]) -> None:
        """
        Save metric calculation results to database.

        Stores in performance_gate_results table.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            for result in results:
                cursor.execute("""
                    INSERT OR REPLACE INTO performance_gate_results
                    (id, domain, model_id, gate_id, metric_name, measured_value,
                     threshold_value, status, period_start_date, period_end_date,
                     calculated_at, calculation_details)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    f"{self.domain}-{self.model}-{result.metric_name}-{result.period_start_date}",
                    self.domain,
                    self.model,
                    'current',  # Will be updated to actual gate_id when available
                    result.metric_name,
                    result.measured_value,
                    result.threshold_value,
                    result.status,
                    str(result.period_start_date),
                    str(result.period_end_date),
                    datetime.now().isoformat(),
                    json.dumps(result.calculation_details)
                ))

            conn.commit()
            logger.info(f"Saved {len(results)} metric results to database")

        except Exception as e:
            logger.error(f"Error saving results to database: {e}")
            conn.rollback()
            raise

        finally:
            conn.close()
