"""Risk Model Management API Routes - Proxies to cbp-risk-engine MLOps Registry

All endpoints proxy to cbp-risk-engine which is the single source of truth for:
- Model versions (MLflow registry)
- Approvals workflow
- Training jobs
- Performance metrics
- Gate progression
"""

import httpx
import logging
from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from datetime import datetime

router = APIRouter(prefix="/api/risk-models", tags=["risk-models"])
logger = logging.getLogger(__name__)

# cbp-risk-engine service URL (real MLOps registry)
# Inside Docker container, use service name; from host, use localhost:8010
CBP_RISK_ENGINE_URL = "http://cbp-risk-engine:8010"


@router.get("/dashboard")
async def get_dashboard():
    """Get dashboard summary from cbp-risk-engine.

    Aggregates:
    - Production model from /api/models/production
    - Performance metrics from /api/metrics/performance
    - Drift alerts from /api/metrics/drift
    - Gate progression from /api/metrics/gates
    """
    try:
        logger.info("Fetching risk model dashboard from cbp-risk-engine")

        async with httpx.AsyncClient() as client:
            # Fetch all models
            models_response = await client.get(f"{CBP_RISK_ENGINE_URL}/api/models")
            models_response.raise_for_status()
            models_data = models_response.json()

            # Find production model
            production_model = None
            for model_info in models_data.get('versions', []):
                if model_info.get('is_production'):
                    production_model = model_info
                    break

            # If no production model, use the first/latest
            if not production_model and models_data.get('versions'):
                production_model = models_data['versions'][0]

            # Fetch metrics
            metrics_response = await client.get(f"{CBP_RISK_ENGINE_URL}/api/metrics/performance")
            if metrics_response.status_code == 200:
                metrics = metrics_response.json()
            else:
                metrics = {}

            # Fetch drift alerts if available
            drift_response = await client.get(f"{CBP_RISK_ENGINE_URL}/api/metrics/drift")
            if drift_response.status_code == 200:
                drift_data = drift_response.json()
            else:
                drift_data = {'alerts': []}

            # Fetch gates if available
            gates_response = await client.get(f"{CBP_RISK_ENGINE_URL}/api/metrics/gates")
            if gates_response.status_code == 200:
                gates = gates_response.json()
            else:
                gates = {}

        # Transform to dashboard format
        dashboard_data = {
            'active_model': production_model,
            'pending_approvals': [m for m in models_data.get('versions', []) if not m.get('is_production')],
            'alerts': drift_data.get('alerts', []),
            'gates': gates,
            'key_metrics': metrics.get('key_metrics', {}) if metrics else {},
            'timestamp': datetime.utcnow().isoformat()
        }

        logger.info("Dashboard data retrieved successfully from cbp-risk-engine")
        return dashboard_data

    except httpx.HTTPError as e:
        logger.error(f"Error fetching dashboard from cbp-risk-engine: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch dashboard: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in dashboard: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/versions")
async def get_model_versions(status: Optional[str] = Query(None)):
    """Get all model versions from cbp-risk-engine MLflow registry."""
    try:
        logger.info(f"Fetching model versions (status filter: {status})")

        async with httpx.AsyncClient() as client:
            response = await client.get(f"{CBP_RISK_ENGINE_URL}/api/models")
            response.raise_for_status()
            models = response.json()

        # Return all versions
        versions = models.get('versions', [])

        # Filter by status if provided
        if status:
            versions = [v for v in versions if v.get('is_production') == (status == 'production')]

        logger.info(f"Retrieved {len(versions)} model versions")
        return versions

    except httpx.HTTPError as e:
        logger.error(f"Error fetching versions from cbp-risk-engine: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch model versions: {str(e)}")


@router.get("/training-jobs")
async def get_training_jobs(
    status: Optional[str] = Query(None),
    limit: int = Query(20)
):
    """Get training job history from cbp-risk-engine."""
    try:
        logger.info(f"Fetching training jobs (status={status}, limit={limit})")

        async with httpx.AsyncClient() as client:
            response = await client.get(f"{CBP_RISK_ENGINE_URL}/api/jobs")
            if response.status_code == 200:
                jobs = response.json()
            else:
                jobs = {'jobs': []}

        job_list = jobs.get('jobs', []) if isinstance(jobs, dict) else jobs

        # Filter by status if provided
        if status:
            job_list = [j for j in job_list if j.get('status') == status]

        # Limit results
        job_list = job_list[:limit]

        logger.info(f"Retrieved {len(job_list)} training jobs")
        return job_list

    except httpx.HTTPError as e:
        logger.error(f"Error fetching training jobs: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch training jobs: {str(e)}")


@router.get("/training-jobs/{job_id}")
async def get_training_job_details(job_id: str):
    """Get detailed training job status."""
    try:
        logger.info(f"Fetching training job details for {job_id}")

        async with httpx.AsyncClient() as client:
            response = await client.get(f"{CBP_RISK_ENGINE_URL}/api/jobs/{job_id}")
            response.raise_for_status()
            job = response.json()

        logger.info(f"Training job {job_id} retrieved")
        return job

    except httpx.HTTPError as e:
        logger.error(f"Error fetching training job {job_id}: {str(e)}")
        if '404' in str(e):
            raise HTTPException(status_code=404, detail=f"Training job {job_id} not found")
        raise HTTPException(status_code=500, detail=f"Failed to fetch job: {str(e)}")


@router.post("/train")
async def trigger_training(data: Optional[dict] = None):
    """Trigger a new training job."""
    try:
        logger.info("Triggering training job")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{CBP_RISK_ENGINE_URL}/api/train",
                json=data or {}
            )
            response.raise_for_status()
            result = response.json()

        logger.info("Training job triggered")
        return result

    except httpx.HTTPError as e:
        logger.error(f"Error triggering training: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to trigger training: {str(e)}")


@router.get("/{model_id}")
async def get_model(model_id: str):
    """Get specific model version details."""
    try:
        logger.info(f"Fetching model {model_id}")

        async with httpx.AsyncClient() as client:
            response = await client.get(f"{CBP_RISK_ENGINE_URL}/api/models/{model_id}")
            response.raise_for_status()
            model = response.json()

        logger.info(f"Model {model_id} retrieved")
        return model

    except httpx.HTTPError as e:
        logger.error(f"Error fetching model {model_id}: {str(e)}")
        if '404' in str(e):
            raise HTTPException(status_code=404, detail=f"Model {model_id} not found")
        raise HTTPException(status_code=500, detail=f"Failed to fetch model: {str(e)}")


@router.post("/{model_id}/approve")
async def approve_model(model_id: str, data: dict):
    """Submit approval vote for a model version."""
    try:
        logger.info(f"Approving model {model_id}")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{CBP_RISK_ENGINE_URL}/api/models/{model_id}/approve",
                json=data
            )
            response.raise_for_status()
            result = response.json()

        logger.info(f"Model {model_id} approval recorded")
        return result

    except httpx.HTTPError as e:
        logger.error(f"Error approving model {model_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to approve model: {str(e)}")


@router.post("/{model_id}/promote")
async def promote_model(model_id: str, data: Optional[dict] = None):
    """Promote model version to production."""
    try:
        logger.info(f"Promoting model {model_id}")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{CBP_RISK_ENGINE_URL}/api/models/{model_id}/promote",
                json=data or {}
            )
            response.raise_for_status()
            result = response.json()

        logger.info(f"Model {model_id} promoted")
        return result

    except httpx.HTTPError as e:
        logger.error(f"Error promoting model {model_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to promote model: {str(e)}")


@router.get("/metrics/performance")
async def get_performance_metrics():
    """Get model performance metrics."""
    try:
        logger.info("Fetching performance metrics")

        async with httpx.AsyncClient() as client:
            response = await client.get(f"{CBP_RISK_ENGINE_URL}/api/metrics/performance")
            response.raise_for_status()
            metrics = response.json()

        return metrics

    except httpx.HTTPError as e:
        logger.error(f"Error fetching performance metrics: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch metrics: {str(e)}")


@router.get("/metrics/gates")
async def get_gate_metrics():
    """Get gate progression metrics."""
    try:
        logger.info("Fetching gate metrics")

        async with httpx.AsyncClient() as client:
            response = await client.get(f"{CBP_RISK_ENGINE_URL}/api/metrics/gates")
            response.raise_for_status()
            gates = response.json()

        return gates

    except httpx.HTTPError as e:
        logger.error(f"Error fetching gate metrics: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch gates: {str(e)}")


@router.get("/metrics/drift")
async def get_drift_metrics():
    """Get data drift detection results."""
    try:
        logger.info("Fetching drift metrics")

        async with httpx.AsyncClient() as client:
            response = await client.get(f"{CBP_RISK_ENGINE_URL}/api/metrics/drift")
            response.raise_for_status()
            drift = response.json()

        return drift

    except httpx.HTTPError as e:
        logger.error(f"Error fetching drift metrics: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch drift: {str(e)}")


@router.get("/performance/current-gate")
async def get_current_performance_gate(model_id: str = Query("v3.0")):
    """Get the current applicable performance gate for a risk model."""
    try:
        logger.info(f"Fetching current gate for model {model_id}")

        async with httpx.AsyncClient() as client:
            response = await client.get(f"{CBP_RISK_ENGINE_URL}/api/metrics/gates")
            response.raise_for_status()
            gates = response.json()

        return gates

    except httpx.HTTPError as e:
        logger.error(f"Error fetching current gate: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch gate: {str(e)}")


@router.get("/performance/metrics")
async def get_perf_metrics(
    model_id: str = Query("v3.0"),
    period_days: int = Query(30)
):
    """Calculate current performance metrics for a risk model."""
    try:
        logger.info(f"Fetching performance metrics for model {model_id}, period {period_days} days")

        async with httpx.AsyncClient() as client:
            response = await client.get(f"{CBP_RISK_ENGINE_URL}/api/metrics/performance")
            response.raise_for_status()
            metrics = response.json()

        return metrics

    except httpx.HTTPError as e:
        logger.error(f"Error fetching performance metrics: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch metrics: {str(e)}")


@router.get("/performance/gate/{gate_id}")
async def get_gate_detailed_status(
    gate_id: str,
    model_id: str = Query("v3.0"),
    period_days: int = Query(30)
):
    """Get detailed status of a specific performance gate."""
    try:
        logger.info(f"Fetching gate status for gate {gate_id}, model {model_id}")

        async with httpx.AsyncClient() as client:
            response = await client.get(f"{CBP_RISK_ENGINE_URL}/api/metrics/gates")
            response.raise_for_status()
            gates = response.json()

        # Find the specific gate
        if isinstance(gates, dict):
            gate_data = gates.get(gate_id, {})
        else:
            gate_data = {}

        return gate_data

    except httpx.HTTPError as e:
        logger.error(f"Error fetching gate status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch gate: {str(e)}")


@router.get("/performance/mlflow-config")
async def get_mlflow_performance_config(model_id: str = Query("v3.0")):
    """Retrieve performance configuration from MLflow for a model."""
    try:
        logger.info(f"Fetching MLflow config for model {model_id}")

        async with httpx.AsyncClient() as client:
            response = await client.get(f"{CBP_RISK_ENGINE_URL}/api/models/{model_id}")
            response.raise_for_status()
            model = response.json()

        return model

    except httpx.HTTPError as e:
        logger.error(f"Error fetching MLflow config: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch config: {str(e)}")
