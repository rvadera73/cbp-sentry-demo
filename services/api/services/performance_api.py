"""
Performance Metrics API Endpoints

Provides REST API for querying performance metrics and gate status.
Integrated with MLflow for model configuration and the metrics engine for calculations.
"""

import json
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, date, timedelta
from fastapi import HTTPException
import mlflow

from services.performance_metrics_engine import PerformanceMetricsEngine, MetricResult

logger = logging.getLogger(__name__)


class PerformanceMetricsAPI:
    """API for performance metrics and gate tracking"""

    def __init__(self, mlflow_tracking_uri: str = "http://localhost:5000",
                 metrics_config_path: str = "/app/metrics_config_cbp.yml"):
        """
        Initialize API with MLflow connection and config path.

        Args:
            mlflow_tracking_uri: MLflow server URL
            metrics_config_path: Path to metrics config YAML
        """
        self.mlflow_tracking_uri = mlflow_tracking_uri
        self.metrics_config_path = metrics_config_path
        mlflow.set_tracking_uri(mlflow_tracking_uri)

    def get_current_gate(self, model_id: str = "v3.0") -> Dict[str, Any]:
        """
        Get the current applicable gate for a model based on timeline.

        Args:
            model_id: Model version ID (e.g., 'v3.0')

        Returns:
            Dict with gate information and days remaining
        """
        try:
            engine = PerformanceMetricsEngine(config_path=self.metrics_config_path)

            # Load MLflow run to get award date
            runs = mlflow.search_runs(experiment_names=["CBP-Sentry-Risk-Models"])
            if runs.empty:
                raise HTTPException(status_code=404, detail="No MLflow runs found")

            # Find matching model version
            model_runs = runs[runs['tags.mlflow.runName'].str.contains(model_id, na=False)]
            if model_runs.empty:
                raise HTTPException(status_code=404, detail=f"Model {model_id} not found in MLflow")

            # Get award date from config
            award_date = engine._parse_date(engine.config.get('award_date'))
            if not award_date:
                raise HTTPException(status_code=400, detail="Award date not configured")

            # Calculate days since award
            days_since_award = (datetime.now().date() - award_date).days

            # Find applicable gates
            applicable_gates = []
            for gate in engine.gates:
                timeline_days = gate.get('timeline_days', [0, 999])
                if timeline_days[0] <= days_since_award <= timeline_days[1]:
                    applicable_gates.append(gate)

            if not applicable_gates:
                # Find next gate
                next_gate = None
                for gate in engine.gates:
                    timeline_days = gate.get('timeline_days', [0, 999])
                    if timeline_days[0] > days_since_award:
                        next_gate = gate
                        break

                return {
                    "status": "awaiting_gate",
                    "days_since_award": days_since_award,
                    "current_gate": None,
                    "next_gate": next_gate.get('gate_id') if next_gate else None,
                    "days_until_next": (next_gate.get('timeline_days', [0, 0])[0] - days_since_award) if next_gate else None
                }

            current_gate = applicable_gates[0]
            timeline_days = current_gate.get('timeline_days', [0, 999])
            days_until_next = timeline_days[1] - days_since_award

            return {
                "status": "active",
                "days_since_award": days_since_award,
                "current_gate": {
                    "gate_id": current_gate.get('gate_id'),
                    "gate_name": current_gate.get('gate_name'),
                    "timeline_days": current_gate.get('timeline_days'),
                    "description": current_gate.get('description')
                },
                "days_until_next_gate": days_until_next,
                "metrics_count": len(current_gate.get('metrics', []))
            }

        except Exception as e:
            logger.error(f"Error getting current gate: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    def get_performance_metrics(self, model_id: str = "v3.0",
                                period_start: Optional[date] = None,
                                period_end: Optional[date] = None) -> List[Dict[str, Any]]:
        """
        Calculate current performance metrics for a model.

        Args:
            model_id: Model version ID
            period_start: Start date (defaults to 30 days ago)
            period_end: End date (defaults to today)

        Returns:
            List of metric results with status
        """
        try:
            # Default to last 30 days
            if not period_end:
                period_end = datetime.now().date()
            if not period_start:
                period_start = period_end - timedelta(days=30)

            engine = PerformanceMetricsEngine(config_path=self.metrics_config_path)
            results = engine.calculate_metrics(period_start, period_end)

            return [result.to_dict() for result in results]

        except Exception as e:
            logger.error(f"Error calculating metrics: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    def get_gate_status(self, model_id: str = "v3.0", gate_id: str = "1",
                        period_start: Optional[date] = None,
                        period_end: Optional[date] = None) -> Dict[str, Any]:
        """
        Get detailed status of a specific gate for a model.

        Args:
            model_id: Model version ID
            gate_id: Gate number/ID (1, 2, 3, option_1, option_2)
            period_start: Evaluation period start
            period_end: Evaluation period end

        Returns:
            Gate status with all metrics and pass/fail details
        """
        try:
            # Default period
            if not period_end:
                period_end = datetime.now().date()
            if not period_start:
                period_start = period_end - timedelta(days=30)

            engine = PerformanceMetricsEngine(config_path=self.metrics_config_path)

            # Find gate config
            gate_config = None
            for gate in engine.gates:
                if str(gate.get('gate_id')) == str(gate_id):
                    gate_config = gate
                    break

            if not gate_config:
                raise HTTPException(status_code=404, detail=f"Gate {gate_id} not found")

            # Calculate metrics for this gate
            results = engine.calculate_metrics(period_start, period_end)

            # Filter to metrics in this gate
            gate_metric_names = {m.get('name') for m in gate_config.get('metrics', [])}
            gate_results = [r for r in results if r.metric_name in gate_metric_names]

            # Determine overall pass/fail
            passed_count = sum(1 for r in gate_results if r.status == 'passed')
            total_count = len(gate_results)
            overall_status = 'passed' if passed_count == total_count else 'failed'

            return {
                "gate_id": gate_id,
                "gate_name": gate_config.get('gate_name'),
                "description": gate_config.get('description'),
                "overall_status": overall_status,
                "metrics_passed": passed_count,
                "metrics_total": total_count,
                "pass_percentage": (passed_count / total_count * 100) if total_count > 0 else 0,
                "evaluation_period": {
                    "start": period_start.isoformat(),
                    "end": period_end.isoformat()
                },
                "metrics": [
                    {
                        "name": r.metric_name,
                        "type": r.metric_type,
                        "measured_value": r.measured_value,
                        "threshold_value": r.threshold_value,
                        "unit": r.unit,
                        "status": r.status,
                        "meets_requirement": r.status == 'passed'
                    }
                    for r in gate_results
                ]
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting gate status: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    def get_mlflow_performance_config(self, model_id: str = "v3.0") -> Dict[str, Any]:
        """
        Retrieve performance configuration from MLflow tags for a model.

        Args:
            model_id: Model version ID

        Returns:
            Performance config from MLflow artifacts
        """
        try:
            runs = mlflow.search_runs(experiment_names=["CBP-Sentry-Risk-Models"])
            if runs.empty:
                raise HTTPException(status_code=404, detail="No MLflow runs found")

            # Find model run
            model_runs = runs[runs['tags.mlflow.runName'].str.contains(model_id, na=False)]
            if model_runs.empty:
                raise HTTPException(status_code=404, detail=f"Model {model_id} not in MLflow")

            # Get most recent run
            latest_run = model_runs.iloc[0]
            run_id = latest_run['run_id']

            # Load artifacts
            run = mlflow.get_run(run_id)

            # Get tags
            config = {
                "model_id": model_id,
                "gate": run.data.tags.get('performance_gate', 'unknown'),
                "tags": {
                    k: v for k, v in run.data.tags.items()
                    if k.startswith('performance_')
                }
            }

            return config

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error retrieving MLflow config: {e}")
            raise HTTPException(status_code=500, detail=str(e))
