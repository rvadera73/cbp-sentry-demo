"""Risk Model Management API Routes (FastAPI)

Provides endpoints for the Risk Model Management tab with REAL v3.0 model data:
- Model versioning and metadata from database
- Training job history from risk_model_training_jobs table
- Performance metrics from actual predictions (risk_model_metrics)
- Data drift detection on real feature distributions
- Prediction explanations (SHAP) from precise-risk-engine service
- Model approval workflow from risk_model_approvals table
- Retraining configuration from risk_retraining_config table

All data comes from real sources:
  - Shipments database
  - Risk model tables (v4_0_risk_model_management.py)
  - precise-risk-engine service (http://localhost:8004)
"""

from fastapi import APIRouter, Query, HTTPException, Body, Depends
from pydantic import BaseModel, ValidationError
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta
import logging

router = APIRouter(prefix="/api/risk-models", tags=["risk-models"])
logger = logging.getLogger(__name__)

# Import real data service
from services.risk_model_data_service import RiskModelDataService, get_data_service


# ============================================================================
# PYDANTIC MODELS (Request/Response Schemas)
# ============================================================================

class ModelMetrics(BaseModel):
    accuracy: float
    auc_roc: float
    latency_p95_ms: int
    confidence_avg: float
    predictions_24h: int


class ActiveModel(BaseModel):
    model_id: str
    version: str
    status: str
    deployed_at: str
    approved_by: str
    metrics: ModelMetrics


class Alert(BaseModel):
    type: str
    severity: str
    feature: Optional[str] = None
    drift_score: Optional[float] = None
    detected_at: str
    recommendation: str


class KeyMetrics(BaseModel):
    accuracy: float
    latency_p95: int
    confidence_avg: float
    data_drift_score: float
    model_drift_score: float


class DashboardResponse(BaseModel):
    active_model: ActiveModel
    pending_approvals: List[Dict[str, Any]]
    alerts: List[Alert]
    key_metrics: KeyMetrics


# ============================================================================
# DASHBOARD
# ============================================================================

@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(data_service: RiskModelDataService = Depends(get_data_service)):
    """Get dashboard summary with active model health, metrics, and alerts.

    This endpoint provides an at-a-glance view of:
    - Current production model (v3.0) performance from database
    - Key metrics from last 24 hours (accuracy, latency, confidence)
    - Pending model approvals awaiting review
    - Active data/model drift alerts

    Returns:
        Dashboard with REAL v3.0 metrics, pending approvals, and drift alerts
    """
    try:
        logger.info("Fetching risk model dashboard")

        # Get REAL data from database via data service
        dashboard_data = await data_service.get_dashboard()

        logger.info("Dashboard data retrieved successfully from database")
        return dashboard_data

    except Exception as e:
        logger.error(f"Error fetching dashboard: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Dashboard error: {str(e)}")


# ============================================================================
# MODEL VERSIONS
# ============================================================================

@router.get("/versions")
async def get_model_versions(
    status: Optional[str] = Query(None, description="Filter by status: production|staging|candidate|deprecated"),
    data_service: RiskModelDataService = Depends(get_data_service)
):
    """Get all model versions with status filtering.

    Query Parameters:
        status: Filter by model status

    Returns:
        List of model versions with metrics
    """
    try:
        logger.info(f"Fetching model versions (status filter: {status})")

        # Get REAL versions from data service
        versions = await data_service.get_all_versions()

        # Filter by status if provided
        if status:
            versions = [v for v in versions if v.get('status') == status]
            logger.info(f"Filtered to {len(versions)} versions with status={status}")

        return versions

    except Exception as e:
        logger.error(f"Error fetching model versions: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Model versions error: {str(e)}")


# ============================================================================
# TRAINING JOBS
# ============================================================================

@router.get("/training-jobs")
async def get_training_jobs(
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(20, description="Max results"),
    data_service: RiskModelDataService = Depends(get_data_service)
):
    """Get training job history with filtering.

    Query Parameters:
        status: completed|running|queued|failed
        limit: Maximum results (default: 20)

    Returns:
        List of training jobs with metadata
    """
    try:
        logger.info(f"Fetching training jobs (status={status}, limit={limit})")

        # Get REAL training jobs from data service
        jobs = await data_service.get_training_jobs(status=status)

        # Limit results
        jobs = jobs[:limit]

        logger.info(f"Retrieved {len(jobs)} training jobs")
        return jobs

    except Exception as e:
        logger.error(f"Error fetching training jobs: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Training jobs error: {str(e)}")


@router.get("/training-jobs/{job_id}")
async def get_training_job_details(
    job_id: str,
    data_service: RiskModelDataService = Depends(get_data_service)
):
    """Get detailed training job status.

    Path Parameters:
        job_id: Training job ID

    Returns:
        Detailed job information with progress
    """
    try:
        logger.info(f"Fetching training job details for {job_id}")

        # Get REAL training job details from data service
        job = await data_service.get_training_job_details(job_id)

        if not job:
            logger.warning(f"Training job {job_id} not found")
            raise HTTPException(status_code=404, detail=f"Training job {job_id} not found")

        logger.info(f"Retrieved training job details for {job_id}")
        return job

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching training job details: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Training job details error: {str(e)}")


# ============================================================================
# PERFORMANCE METRICS
# ============================================================================

@router.get("/{model_id}/metrics")
async def get_model_metrics(
    model_id: str,
    time_range: str = Query("24h", description="24h|7d|30d"),
    metric: Optional[str] = Query(None, description="accuracy|latency|confidence"),
    data_service: RiskModelDataService = Depends(get_data_service)
):
    """Get time-series performance metrics for a model.

    Path Parameters:
        model_id: Model ID (e.g., v3.0)

    Query Parameters:
        time_range: 24h, 7d, or 30d
        metric: Specific metric to retrieve

    Returns:
        Time-series data points
    """
    try:
        logger.info(f"Fetching metrics for {model_id} (time_range={time_range}, metric={metric})")

        # Parse time_range to hours
        hours_map = {'24h': 24, '7d': 168, '30d': 720}
        hours = hours_map.get(time_range, 24)

        # Default to accuracy if not specified
        metric_name = metric or 'accuracy'

        # Get REAL time-series metrics from data service
        metrics = await data_service.get_metrics_timeseries(
            model_id=model_id,
            metric=metric_name,
            hours=hours
        )

        logger.info(f"Retrieved {len(metrics)} metric data points for {model_id}")
        return metrics

    except Exception as e:
        logger.error(f"Error fetching model metrics: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Model metrics error: {str(e)}")


# ============================================================================
# DATA DRIFT MONITORING
# ============================================================================

@router.get("/{model_id}/drift")
async def get_data_drift(
    model_id: str = "v3.0",
    data_service: RiskModelDataService = Depends(get_data_service)
):
    """Get current data drift status and alerts.

    Returns:
        Drift analysis with elevated features
    """
    try:
        logger.info(f"Detecting data drift for {model_id}")

        # Get REAL drift detection from data service
        drift_result = await data_service.detect_data_drift(model_id=model_id)

        # Determine overall status
        overall_score = drift_result.get('overall_drift_score', 0.0)
        status = 'critical' if overall_score > 0.50 else 'elevated' if overall_score > 0.30 else 'normal'

        logger.info(f"Data drift analysis complete: score={overall_score:.3f}, status={status}")

        return {
            'overall_drift_score': overall_score,
            'status': status,
            'elevated_features': drift_result.get('elevated_features', []),
            'normal_features': drift_result.get('normal_features', [])
        }

    except Exception as e:
        logger.error(f"Error detecting data drift: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Data drift error: {str(e)}")


# ============================================================================
# PREDICTION EXPLANATIONS (SHAP)
# ============================================================================

@router.get("/predictions/{shipment_id}/explain")
async def explain_prediction(
    shipment_id: str,
    model_version: str = Query("v3.0", description="Model version"),
    compare_to: Optional[str] = Query(None, description="Compare with another version"),
    data_service: RiskModelDataService = Depends(get_data_service)
):
    """Get SHAP explanation for a shipment prediction.

    Path Parameters:
        shipment_id: Shipment ID (e.g., SHP-00142857)

    Query Parameters:
        model_version: v3.0 (default)
        compare_to: Optional comparison model (e.g., v2.1)

    Returns:
        SHAP explanation with feature contributions
    """
    try:
        logger.info(f"Fetching SHAP explanation for shipment {shipment_id} (model={model_version}, compare_to={compare_to})")

        # Get REAL SHAP explanation from data service
        explanation = await data_service.explain_prediction(
            shipment_id=shipment_id,
            model_version=model_version,
            compare_to=compare_to
        )

        logger.info(f"Retrieved SHAP explanation for shipment {shipment_id}")
        return explanation

    except ValueError as e:
        logger.warning(f"Shipment not found: {str(e)}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error fetching SHAP explanation: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"SHAP explanation error: {str(e)}")


# ============================================================================
# MODEL APPROVALS
# ============================================================================

@router.get("/approvals")
async def get_approvals(
    status: Optional[str] = Query(None),
    data_service: RiskModelDataService = Depends(get_data_service)
):
    """Get approval requests.

    Query Parameters:
        status: pending|approved|rejected

    Returns:
        List of approval requests with voter status
    """
    try:
        logger.info(f"Fetching approval requests (status={status})")

        # Get REAL approval requests from data service
        approvals = await data_service.get_pending_approvals()

        # Filter by status if provided
        if status:
            approvals = [a for a in approvals if a.get('status') == status]
            logger.info(f"Filtered to {len(approvals)} approvals with status={status}")

        logger.info(f"Retrieved {len(approvals)} approval requests")
        return approvals

    except Exception as e:
        logger.error(f"Error fetching approvals: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Approvals error: {str(e)}")


@router.post("/approvals/{approval_id}/vote")
async def vote_approval(
    approval_id: str,
    payload: Dict[str, Any] = Body(...),
    data_service: RiskModelDataService = Depends(get_data_service)
):
    """Cast approval vote.

    Path Parameters:
        approval_id: Approval request ID

    Body:
        {vote: 'approve'|'reject'|'abstain', voter: 'name', comment: '...'}

    Returns:
        Updated approval status
    """
    try:
        # Validate payload
        vote = payload.get('vote')
        voter = payload.get('voter', 'unknown')
        comment = payload.get('comment')

        if vote not in ['approve', 'reject', 'abstain']:
            raise ValueError(f"Invalid vote: {vote}. Must be approve, reject, or abstain")

        logger.info(f"Recording vote from {voter}: {vote} on approval {approval_id}")

        # Record REAL vote using data service
        approval = await data_service.cast_approval_vote(
            approval_id=approval_id,
            voter=voter,
            vote=vote,
            comment=comment
        )

        if not approval:
            logger.warning(f"Approval {approval_id} not found")
            raise HTTPException(status_code=404, detail=f"Approval {approval_id} not found")

        logger.info(f"Vote recorded for approval {approval_id}")
        return {
            'approval_id': approval_id,
            'vote_recorded': True,
            'timestamp': datetime.utcnow().isoformat(),
            'approval_status': approval.get('status', 'pending')
        }

    except ValueError as e:
        logger.warning(f"Vote validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error recording approval vote: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Vote recording error: {str(e)}")


# ============================================================================
# RETRAINING CONFIGURATION
# ============================================================================

@router.get("/retraining-config")
async def get_retraining_config(
    data_service: RiskModelDataService = Depends(get_data_service)
):
    """Get retraining configuration.

    Returns:
        Current retraining settings and trigger status
    """
    try:
        logger.info("Fetching retraining configuration")

        # Get REAL retraining config from data service
        config = await data_service.get_retraining_config()

        logger.info("Retraining configuration retrieved")
        return config

    except Exception as e:
        logger.error(f"Error fetching retraining config: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Retraining config error: {str(e)}")


@router.put("/retraining-config")
async def update_retraining_config(
    config: Dict[str, Any] = Body(...),
    data_service: RiskModelDataService = Depends(get_data_service)
):
    """Update retraining configuration.

    Body:
        {scheduled: {...}, drift_triggered: {...}, ...}

    Returns:
        Updated configuration
    """
    try:
        logger.info(f"Updating retraining configuration: {config}")

        # Update REAL retraining config using data service
        result = await data_service.update_retraining_config(config)

        if not result.get('success'):
            raise HTTPException(status_code=400, detail=result.get('error', 'Configuration update failed'))

        logger.info("Retraining configuration updated successfully")
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating retraining config: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Retraining config update error: {str(e)}")


# ============================================================================
# MODEL ROLLBACK
# ============================================================================

@router.post("/{model_id}/rollback")
async def rollback_model(
    model_id: str,
    payload: Dict[str, Any] = Body(...),
    data_service: RiskModelDataService = Depends(get_data_service)
):
    """Rollback to previous model version.

    Path Parameters:
        model_id: Model to rollback from

    Body:
        {reason: 'string'}

    Returns:
        Rollback confirmation
    """
    try:
        reason = payload.get('reason', 'no reason provided')

        logger.warning(f"ROLLBACK initiated for {model_id}: {reason}")

        # Execute REAL rollback using data service
        result = await data_service.rollback_model(reason=reason)

        if not result.get('success'):
            raise HTTPException(status_code=500, detail=result.get('error', 'Rollback failed'))

        logger.warning(f"Rollback completed: {model_id} → {result.get('current_model')}")
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rolling back model: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Rollback error: {str(e)}")


# ============================================================================
# MODEL COMPARISON
# ============================================================================

@router.get("/compare")
async def compare_models(
    shipment_id: str = Query(..., description="Shipment ID to compare"),
    models: str = Query("v2.1,v3.0", description="Comma-separated model versions to compare"),
    data_service: RiskModelDataService = Depends(get_data_service)
):
    """Compare predictions from multiple model versions on the same shipment.

    This endpoint scores the same shipment with different models and returns
    a comparison showing differences in scoring, confidence, and recommendations.

    Query Parameters:
        shipment_id: Shipment ID (e.g., SHP-XXXXX)
        models: Comma-separated model versions (default: v2.1,v3.0)

    Returns:
        Comparison with scores from both models, differences, and analysis
    """
    try:
        logger.info(f"Comparing models for shipment {shipment_id}: {models}")

        # Parse model list
        model_list = [m.strip() for m in models.split(',')]

        # Get comparison from data service
        comparison = await data_service.compare_models(
            shipment_id=shipment_id,
            models=model_list
        )

        if not comparison:
            logger.warning(f"Shipment {shipment_id} not found")
            raise HTTPException(status_code=404, detail=f"Shipment {shipment_id} not found")

        logger.info(f"Model comparison complete for shipment {shipment_id}")
        return comparison

    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(f"Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error comparing models: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Model comparison error: {str(e)}")


# ============================================================================
# PERFORMANCE MEASURES (CBP Contract Gates)
# ============================================================================

@router.get("/performance/current-gate")
async def get_current_gate(model_id: str = Query("v3.0", description="Model version ID")):
    """Get current applicable performance gate for a model.

    Query Parameters:
        model_id: Model version ID (default: v3.0)

    Returns:
        {
            "status": "active",
            "days_since_award": 154,
            "current_gate": {
                "gate_id": "3",
                "gate_name": "Optimization & Refinement",
                "timeline_days": [121, 180],
                "description": "Performance optimization and model refinement phase"
            },
            "days_until_next_gate": 26,
            "metrics_count": 4
        }
    """
    try:
        from services.performance_api import PerformanceMetricsAPI

        logger.info(f"Fetching current gate for model {model_id}")

        api = PerformanceMetricsAPI()
        result = api.get_current_gate(model_id=model_id)

        return result

    except Exception as e:
        logger.error(f"Error getting current gate: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get current gate: {str(e)}")


@router.get("/performance/metrics")
async def get_performance_metrics(
    model_id: str = Query("v3.0", description="Model version ID"),
    period_start: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    period_end: Optional[str] = Query(None, description="End date (YYYY-MM-DD)")
):
    """Get calculated performance metrics for current gate.

    Query Parameters:
        model_id: Model version ID (default: v3.0)
        period_start: Start date (YYYY-MM-DD, optional - defaults to 30 days ago)
        period_end: End date (YYYY-MM-DD, optional - defaults to today)

    Returns:
        List of metric results with status
    """
    try:
        from services.performance_api import PerformanceMetricsAPI
        from datetime import datetime as dt, date

        # Parse dates
        start_date = None
        end_date = None
        if period_start:
            start_date = dt.strptime(period_start, '%Y-%m-%d').date()
        if period_end:
            end_date = dt.strptime(period_end, '%Y-%m-%d').date()

        logger.info(f"Fetching performance metrics for {model_id} from {period_start} to {period_end}")

        api = PerformanceMetricsAPI()
        results = api.get_performance_metrics(
            model_id=model_id,
            period_start=start_date,
            period_end=end_date
        )

        return results

    except Exception as e:
        logger.error(f"Error getting performance metrics: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get performance metrics: {str(e)}")


@router.get("/performance/gate/{gate_id}")
async def get_gate_status(
    gate_id: str,
    model_id: str = Query("v3.0", description="Model version ID"),
    period_start: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    period_end: Optional[str] = Query(None, description="End date (YYYY-MM-DD)")
):
    """Get detailed status of a specific performance gate.

    Path Parameters:
        gate_id: Gate ID (1, 2, 3, option_1, option_2)

    Query Parameters:
        model_id: Model version ID (default: v3.0)
        period_start: Evaluation period start (YYYY-MM-DD, optional)
        period_end: Evaluation period end (YYYY-MM-DD, optional)

    Returns:
        Gate status with all metrics and pass/fail details
    """
    try:
        from services.performance_api import PerformanceMetricsAPI
        from datetime import datetime as dt

        # Parse dates
        start_date = None
        end_date = None
        if period_start:
            start_date = dt.strptime(period_start, '%Y-%m-%d').date()
        if period_end:
            end_date = dt.strptime(period_end, '%Y-%m-%d').date()

        logger.info(f"Fetching gate status for gate {gate_id} (model {model_id})")

        api = PerformanceMetricsAPI()
        result = api.get_gate_status(
            model_id=model_id,
            gate_id=gate_id,
            period_start=start_date,
            period_end=end_date
        )

        return result

    except Exception as e:
        logger.error(f"Error getting gate status: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get gate status: {str(e)}")


@router.get("/performance/mlflow-config")
async def get_mlflow_performance_config(
    model_id: str = Query("v3.0", description="Model version ID")
):
    """Get performance configuration from MLflow model tags.

    Query Parameters:
        model_id: Model version ID (default: v3.0)

    Returns:
        Performance configuration from MLflow artifacts
    """
    try:
        from services.performance_api import PerformanceMetricsAPI

        logger.info(f"Fetching MLflow performance config for {model_id}")

        api = PerformanceMetricsAPI()
        result = api.get_mlflow_performance_config(model_id=model_id)

        return result

    except Exception as e:
        logger.error(f"Error getting MLflow config: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get MLflow performance config: {str(e)}")
