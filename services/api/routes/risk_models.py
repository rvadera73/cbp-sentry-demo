"""Risk Model Management API - Proxies to cbp-risk-engine MLOps Registry

All endpoints proxy to cbp-risk-engine which is the single source of truth for:
- Model versions (MLflow registry)
- Approvals workflow
- Training jobs
- Performance metrics
- Gate progression
"""

import httpx
import logging
from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta

bp = Blueprint('risk_models', __name__, url_prefix='/api/risk-models')
logger = logging.getLogger(__name__)

# cbp-risk-engine service URL (same network, port 8010)
CBP_RISK_ENGINE_URL = "http://localhost:8010"

# ============================================================================
# PROXY: GET /api/risk-models/dashboard
# Maps to cbp-risk-engine: GET /models + GET /metrics/performance + GET /metrics/drift
# ============================================================================

@bp.route('/dashboard', methods=['GET'])
def get_dashboard():
    """Get dashboard summary from cbp-risk-engine.

    Aggregates:
    - Production model from /models/production
    - Performance metrics from /metrics/performance
    - Drift alerts from /metrics/drift
    - Gate progression from /metrics/gates
    """
    try:
        logger.info("Fetching risk model dashboard from cbp-risk-engine")

        # Fetch production model
        with httpx.Client() as client:
            prod_response = client.get(f"{CBP_RISK_ENGINE_URL}/api/models/production")
            prod_response.raise_for_status()
            active_model = prod_response.json()

            # Fetch metrics
            perf_response = client.get(f"{CBP_RISK_ENGINE_URL}/api/metrics/performance")
            perf_response.raise_for_status()
            metrics = perf_response.json()

            # Fetch drift
            drift_response = client.get(f"{CBP_RISK_ENGINE_URL}/api/metrics/drift")
            drift_response.raise_for_status()
            drift_data = drift_response.json()

            # Fetch gates
            gates_response = client.get(f"{CBP_RISK_ENGINE_URL}/api/metrics/gates")
            gates_response.raise_for_status()
            gates_data = gates_response.json()

        # Transform to dashboard format
        dashboard_data = {
            'active_model': active_model,
            'metrics': metrics,
            'drift_alerts': drift_data.get('alerts', []),
            'gates': gates_data,
            'timestamp': datetime.utcnow().isoformat()
        }

        logger.info("Dashboard data retrieved successfully from cbp-risk-engine")
        return jsonify(dashboard_data), 200

    except httpx.HTTPError as e:
        logger.error(f"Error fetching dashboard from cbp-risk-engine: {str(e)}")
        return jsonify({
            'error': 'Failed to fetch dashboard',
            'detail': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500
    except Exception as e:
        logger.error(f"Unexpected error in dashboard: {str(e)}")
        return jsonify({
            'error': 'Internal server error',
            'detail': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500


# ============================================================================
# PROXY: GET /api/risk-models/versions
# Maps to cbp-risk-engine: GET /models
# ============================================================================

@bp.route('/versions', methods=['GET'])
def get_model_versions():
    """Get all model versions from cbp-risk-engine MLflow registry."""
    try:
        logger.info("Fetching model versions from cbp-risk-engine")

        with httpx.Client() as client:
            response = client.get(f"{CBP_RISK_ENGINE_URL}/api/models")
            response.raise_for_status()
            models = response.json()

        logger.info("Model versions retrieved successfully")
        return jsonify(models), 200

    except httpx.HTTPError as e:
        logger.error(f"Error fetching versions from cbp-risk-engine: {str(e)}")
        return jsonify({
            'error': 'Failed to fetch model versions',
            'detail': str(e)
        }), 500


# ============================================================================
# PROXY: GET /api/risk-models/{model_id}
# Maps to cbp-risk-engine: GET /models/{version_id}
# ============================================================================

@bp.route('/<model_id>', methods=['GET'])
def get_model(model_id):
    """Get specific model version details from cbp-risk-engine."""
    try:
        logger.info(f"Fetching model {model_id} from cbp-risk-engine")

        with httpx.Client() as client:
            response = client.get(f"{CBP_RISK_ENGINE_URL}/api/models/{model_id}")
            response.raise_for_status()
            model = response.json()

        logger.info(f"Model {model_id} retrieved successfully")
        return jsonify(model), 200

    except httpx.HTTPError as e:
        logger.error(f"Error fetching model {model_id}: {str(e)}")
        if 'not found' in str(e).lower():
            return jsonify({'error': f'Model {model_id} not found'}), 404
        return jsonify({'error': 'Failed to fetch model', 'detail': str(e)}), 500


# ============================================================================
# PROXY: POST /api/risk-models/{model_id}/approve
# Maps to cbp-risk-engine: POST /models/{version_id}/approve
# ============================================================================

@bp.route('/<model_id>/approve', methods=['POST'])
def approve_model(model_id):
    """Submit approval vote for a model version."""
    try:
        data = request.get_json()
        logger.info(f"Approving model {model_id}")

        with httpx.Client() as client:
            response = client.post(
                f"{CBP_RISK_ENGINE_URL}/api/models/{model_id}/approve",
                json=data
            )
            response.raise_for_status()
            result = response.json()

        logger.info(f"Model {model_id} approval recorded")
        return jsonify(result), 200

    except httpx.HTTPError as e:
        logger.error(f"Error approving model {model_id}: {str(e)}")
        return jsonify({'error': 'Failed to approve model', 'detail': str(e)}), 500


# ============================================================================
# PROXY: POST /api/risk-models/{model_id}/promote
# Maps to cbp-risk-engine: POST /models/{version_id}/promote
# ============================================================================

@bp.route('/<model_id>/promote', methods=['POST'])
def promote_model(model_id):
    """Promote model version to production."""
    try:
        data = request.get_json() or {}
        logger.info(f"Promoting model {model_id}")

        with httpx.Client() as client:
            response = client.post(
                f"{CBP_RISK_ENGINE_URL}/api/models/{model_id}/promote",
                json=data
            )
            response.raise_for_status()
            result = response.json()

        logger.info(f"Model {model_id} promoted")
        return jsonify(result), 200

    except httpx.HTTPError as e:
        logger.error(f"Error promoting model {model_id}: {str(e)}")
        return jsonify({'error': 'Failed to promote model', 'detail': str(e)}), 500


# ============================================================================
# PROXY: GET /api/risk-models/training-jobs
# Maps to cbp-risk-engine: GET /jobs
# ============================================================================

@bp.route('/training-jobs', methods=['GET'])
def get_training_jobs():
    """Get all training jobs from cbp-risk-engine."""
    try:
        logger.info("Fetching training jobs from cbp-risk-engine")

        with httpx.Client() as client:
            response = client.get(f"{CBP_RISK_ENGINE_URL}/api/jobs")
            response.raise_for_status()
            jobs = response.json()

        logger.info("Training jobs retrieved successfully")
        return jsonify(jobs), 200

    except httpx.HTTPError as e:
        logger.error(f"Error fetching training jobs: {str(e)}")
        return jsonify({'error': 'Failed to fetch training jobs', 'detail': str(e)}), 500


# ============================================================================
# PROXY: GET /api/risk-models/training-jobs/{job_id}
# Maps to cbp-risk-engine: GET /jobs/{job_id}
# ============================================================================

@bp.route('/training-jobs/<job_id>', methods=['GET'])
def get_training_job(job_id):
    """Get specific training job details."""
    try:
        logger.info(f"Fetching training job {job_id}")

        with httpx.Client() as client:
            response = client.get(f"{CBP_RISK_ENGINE_URL}/api/jobs/{job_id}")
            response.raise_for_status()
            job = response.json()

        logger.info(f"Training job {job_id} retrieved")
        return jsonify(job), 200

    except httpx.HTTPError as e:
        logger.error(f"Error fetching training job {job_id}: {str(e)}")
        if 'not found' in str(e).lower():
            return jsonify({'error': f'Job {job_id} not found'}), 404
        return jsonify({'error': 'Failed to fetch job', 'detail': str(e)}), 500


# ============================================================================
# PROXY: POST /api/risk-models/train
# Maps to cbp-risk-engine: POST /train
# ============================================================================

@bp.route('/train', methods=['POST'])
def trigger_training():
    """Trigger a new training job."""
    try:
        data = request.get_json() or {}
        logger.info("Triggering training job")

        with httpx.Client() as client:
            response = client.post(
                f"{CBP_RISK_ENGINE_URL}/api/train",
                json=data
            )
            response.raise_for_status()
            result = response.json()

        logger.info("Training job triggered")
        return jsonify(result), 200

    except httpx.HTTPError as e:
        logger.error(f"Error triggering training: {str(e)}")
        return jsonify({'error': 'Failed to trigger training', 'detail': str(e)}), 500


# ============================================================================
# PROXY: GET /api/risk-models/metrics/performance
# Maps to cbp-risk-engine: GET /metrics/performance
# ============================================================================

@bp.route('/metrics/performance', methods=['GET'])
def get_performance_metrics():
    """Get model performance metrics."""
    try:
        logger.info("Fetching performance metrics")

        with httpx.Client() as client:
            response = client.get(f"{CBP_RISK_ENGINE_URL}/api/metrics/performance")
            response.raise_for_status()
            metrics = response.json()

        return jsonify(metrics), 200

    except httpx.HTTPError as e:
        logger.error(f"Error fetching performance metrics: {str(e)}")
        return jsonify({'error': 'Failed to fetch metrics', 'detail': str(e)}), 500


# ============================================================================
# PROXY: GET /api/risk-models/metrics/gates
# Maps to cbp-risk-engine: GET /metrics/gates
# ============================================================================

@bp.route('/metrics/gates', methods=['GET'])
def get_gate_metrics():
    """Get gate progression metrics."""
    try:
        logger.info("Fetching gate metrics")

        with httpx.Client() as client:
            response = client.get(f"{CBP_RISK_ENGINE_URL}/api/metrics/gates")
            response.raise_for_status()
            gates = response.json()

        return jsonify(gates), 200

    except httpx.HTTPError as e:
        logger.error(f"Error fetching gate metrics: {str(e)}")
        return jsonify({'error': 'Failed to fetch gates', 'detail': str(e)}), 500


# ============================================================================
# PROXY: GET /api/risk-models/metrics/drift
# Maps to cbp-risk-engine: GET /metrics/drift
# ============================================================================

@bp.route('/metrics/drift', methods=['GET'])
def get_drift_metrics():
    """Get data drift detection results."""
    try:
        logger.info("Fetching drift metrics")

        with httpx.Client() as client:
            response = client.get(f"{CBP_RISK_ENGINE_URL}/api/metrics/drift")
            response.raise_for_status()
            drift = response.json()

        return jsonify(drift), 200

    except httpx.HTTPError as e:
        logger.error(f"Error fetching drift metrics: {str(e)}")
        return jsonify({'error': 'Failed to fetch drift', 'detail': str(e)}), 500
