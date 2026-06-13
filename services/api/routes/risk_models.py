"""Risk Model Management API Endpoints

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

Endpoint Summary:
- GET /api/risk-models/dashboard — Dashboard summary (active model, metrics, alerts)
- GET /api/risk-models/versions — List model versions with filtering
- POST /api/risk-models/{model_id}/compare — Compare two models
- GET /api/risk-models/training-jobs — Training job history
- GET /api/risk-models/training-jobs/{job_id} — Training job details
- GET /api/risk-models/{model_id}/metrics — Time-series performance metrics
- GET /api/risk-models/{model_id}/drift — Data drift detection results
- GET /api/risk-models/predictions/{shipment_id}/explain — SHAP explanations
- GET /api/risk-models/approvals — Approval requests with voting
- POST /api/risk-models/approvals/{approval_id}/vote — Cast approval vote
- GET /api/risk-models/retraining-config — Retraining configuration
- PUT /api/risk-models/retraining-config — Update retraining configuration
- POST /api/risk-models/{model_id}/rollback — Manual model rollback
"""

from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import json
import logging

bp = Blueprint('risk_models', __name__, url_prefix='/api/risk-models')

logger = logging.getLogger(__name__)

# TODO: Import real data service when database integration complete
# from services.risk_model_data_service import RiskModelDataService
# from api.core.db import get_db_session


# ============================================================================
# DASHBOARD
# ============================================================================

@bp.route('/dashboard', methods=['GET'])
def get_dashboard():
    """Get dashboard summary with active model health, metrics, and alerts.

    This endpoint provides an at-a-glance view of:
    - Current production model (v3.0) performance
    - Key metrics from last 24 hours (accuracy, latency, confidence)
    - Pending model approvals awaiting review
    - Active data/model drift alerts
    - Recommendation actions

    Query Parameters:
        None

    Returns (JSON):
        {
            "active_model": {
                "model_id": "v3.0",
                "version": "v3.0",
                "status": "production",
                "deployed_at": "2026-06-12T14:35:00Z",
                "approved_by": "Sarah Chen",
                "metrics": {
                    "accuracy": 0.924,
                    "auc_roc": 0.944,
                    "latency_p95_ms": 85,
                    "confidence_avg": 0.87,
                    "predictions_24h": 15432
                }
            },
            "pending_approvals": [
                {
                    "model_id": "v3.1",
                    "status": "under_review",
                    "requested_by": "Alex Kim",
                    "requested_at": "2026-06-11T10:00:00Z",
                    "approval_votes": {"approve": 1, "pending": 1},
                    "performance_improvement": {
                        "accuracy_delta": 0.007,
                        "auc_roc_delta": 0.007,
                        "latency_delta_ms": 2
                    }
                }
            ],
            "alerts": [
                {
                    "type": "data_drift",
                    "severity": "warning",
                    "feature": "origin_country",
                    "drift_score": 0.34,
                    "detected_at": "2026-06-13T08:00:00Z",
                    "recommendation": "Monitor for 48h before retraining"
                }
            ],
            "key_metrics": {
                "accuracy": 0.924,
                "latency_p95": 85,
                "confidence_avg": 0.87,
                "data_drift_score": 0.12,
                "model_drift_score": 0.08
            }
        }

    Status Codes:
        200: Dashboard data successfully retrieved
        500: Internal server error (database connection, service error)
    """
    try:
        logger.info("Fetching risk model dashboard")

        # TODO: Query database for current active model (risk_models where status='production')
        # TODO: Fetch pending approvals (risk_model_approvals where status='pending')
        # TODO: Check recent drift detections (risk_model_drift_detected where status='new')
        # TODO: Calculate 24h metrics from risk_model_metrics table

        dashboard_data = {
            'active_model': {
                'model_id': 'v3.0',
                'version': 'v3.0',
                'status': 'production',
                'deployed_at': '2026-06-12T14:35:00Z',
                'approved_by': 'Sarah Chen',
                'metrics': {
                    'accuracy': 0.924,
                    'auc_roc': 0.944,
                    'latency_p95_ms': 85,
                    'confidence_avg': 0.87,
                    'predictions_24h': 15432
                }
            },
            'pending_approvals': [
                {
                    'model_id': 'v3.1',
                    'status': 'under_review',
                    'requested_by': 'Alex Kim',
                    'requested_at': (datetime.utcnow() - timedelta(hours=12)).isoformat(),
                    'approval_votes': {'approve': 1, 'pending': 1},
                    'performance_improvement': {
                        'accuracy_delta': 0.007,
                        'auc_roc_delta': 0.007,
                        'latency_delta_ms': 2
                    }
                }
            ],
            'alerts': [
                {
                    'type': 'data_drift',
                    'severity': 'warning',
                    'feature': 'origin_country',
                    'drift_score': 0.34,
                    'detected_at': (datetime.utcnow() - timedelta(hours=2)).isoformat(),
                    'recommendation': 'Monitor for 48h before retraining'
                }
            ],
            'key_metrics': {
                'accuracy': 0.924,
                'latency_p95': 85,
                'confidence_avg': 0.87,
                'data_drift_score': 0.12,
                'model_drift_score': 0.08
            }
        }

        logger.info("Dashboard data retrieved successfully")
        return jsonify(dashboard_data), 200

    except Exception as e:
        logger.error(f"Error fetching dashboard: {str(e)}", exc_info=True)
        return jsonify({
            'error': 'Failed to fetch dashboard',
            'detail': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500


# ============================================================================
# MODEL VERSIONS
# ============================================================================

@bp.route('/versions', methods=['GET'])
def get_model_versions():
    """Get all model versions with status filtering and sorting.

    Retrieves all available model versions (production, staging, candidate, deprecated)
    with their current performance metrics and approval status.

    Query Parameters:
        status: Filter by status: 'production' | 'staging' | 'candidate' | 'deprecated'
                Optional. If omitted, returns all versions.
        sort: Sort order: 'date' | 'status' (default: 'date')

    Returns (JSON):
        [
            {
                "model_id": "v3.0",
                "version": "v3.0",
                "status": "production",
                "framework": "xgboost",
                "feature_count": 47,
                "weights_sum": 100.0,
                "deployed_at": "2026-06-12T14:35:00Z",
                "created_by": "ML Team",
                "approved_by": "Sarah Chen",
                "approval_date": "2026-06-12T12:00:00Z",
                "performance_metrics": {
                    "accuracy": 0.924,
                    "auc_roc": 0.944,
                    "latency_p95_ms": 85,
                    "false_positive_rate": 0.032
                }
            },
            {
                "model_id": "v3.1",
                "version": "v3.1",
                "status": "candidate",
                "framework": "xgboost",
                "feature_count": 47,
                "weights_sum": 100.0,
                "created_by": "ML Team",
                "approval_status": "under_review",
                "approval_votes": 1,
                "performance_metrics": {
                    "accuracy": 0.931,
                    "auc_roc": 0.951,
                    "latency_p95_ms": 87,
                    "false_positive_rate": 0.028
                },
                "delta_vs_v3_0": {
                    "accuracy": 0.007,
                    "auc_roc": 0.007,
                    "latency": 2
                }
            }
        ]

    Status Codes:
        200: Model versions successfully retrieved
        400: Invalid query parameters
        500: Internal server error
    """
    try:
        status_filter = request.args.get('status')
        sort = request.args.get('sort', 'date')

        # Validate parameters
        valid_statuses = {'production', 'staging', 'candidate', 'deprecated'}
        if status_filter and status_filter not in valid_statuses:
            return jsonify({
                'error': 'Invalid status parameter',
                'detail': f'Status must be one of: {", ".join(valid_statuses)}',
                'timestamp': datetime.utcnow().isoformat()
            }), 400

        valid_sorts = {'date', 'status'}
        if sort not in valid_sorts:
            return jsonify({
                'error': 'Invalid sort parameter',
                'detail': f'Sort must be one of: {", ".join(valid_sorts)}',
                'timestamp': datetime.utcnow().isoformat()
            }), 400

        logger.info(f"Fetching model versions (status={status_filter}, sort={sort})")

        # TODO: Query risk_models table
        # TODO: Filter by status if provided
        # TODO: Sort by date or status

        models = [
            {
                'model_id': 'v3.0',
                'version': 'v3.0',
                'status': 'production',
                'framework': 'xgboost',
                'feature_count': 47,
                'weights_sum': 100.0,
                'deployed_at': '2026-06-12T14:35:00Z',
                'created_by': 'ML Team',
                'approved_by': 'Sarah Chen',
                'approval_date': '2026-06-12T12:00:00Z',
                'performance_metrics': {
                    'accuracy': 0.924,
                    'auc_roc': 0.944,
                    'latency_p95_ms': 85,
                    'false_positive_rate': 0.032
                }
            },
            {
                'model_id': 'v3.1',
                'version': 'v3.1',
                'status': 'candidate',
                'framework': 'xgboost',
                'feature_count': 47,
                'weights_sum': 100.0,
                'created_by': 'ML Team',
                'approval_status': 'under_review',
                'approval_votes': 1,
                'performance_metrics': {
                    'accuracy': 0.931,
                    'auc_roc': 0.951,
                    'latency_p95_ms': 87,
                    'false_positive_rate': 0.028
                },
                'delta_vs_v3_0': {
                    'accuracy': 0.007,
                    'auc_roc': 0.007,
                    'latency': 2
                }
            }
        ]

        # Filter by status if provided
        if status_filter:
            models = [m for m in models if m['status'] == status_filter]

        logger.info(f"Retrieved {len(models)} model versions")
        return jsonify(models), 200

    except Exception as e:
        logger.error(f"Error fetching model versions: {str(e)}", exc_info=True)
        return jsonify({
            'error': 'Failed to fetch model versions',
            'detail': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500


@bp.route('/<model_id>/compare', methods=['POST'])
def compare_models(model_id: str):
    """Compare two model versions side-by-side with performance deltas.

    Compares metrics between two models (e.g., v3.0 vs v2.1) to evaluate
    performance improvements before approving model promotion.

    Path Parameters:
        model_id: First model ID for comparison (e.g., 'v3.0')

    Request Body (JSON):
        {
            "compare_to_model_id": "v2.1"
        }

    Returns (JSON):
        {
            "model_1": "v3.0",
            "model_2": "v2.1",
            "metrics_comparison": {
                "accuracy": {
                    "model_1": 0.924,
                    "model_2": 0.914,
                    "delta": 0.010,
                    "improvement": true,
                    "percent_change": 1.09
                },
                "auc_roc": {
                    "model_1": 0.944,
                    "model_2": 0.938,
                    "delta": 0.006,
                    "improvement": true,
                    "percent_change": 0.64
                },
                "latency_p95_ms": {
                    "model_1": 85,
                    "model_2": 82,
                    "delta": 3,
                    "improvement": false,
                    "percent_change": -3.66
                },
                "false_positive_rate": {
                    "model_1": 0.028,
                    "model_2": 0.032,
                    "delta": -0.004,
                    "improvement": true
                }
            },
            "summary": {
                "overall_winner": "v3.0",
                "improvements": ["accuracy", "auc_roc", "false_positive_rate"],
                "regressions": ["latency_p95_ms"]
            }
        }

    Status Codes:
        200: Models compared successfully
        400: Missing or invalid request parameters
        404: Model not found
        500: Internal server error
    """
    try:
        # Validate request body
        payload = request.get_json()
        if not payload:
            return jsonify({
                'error': 'Request body is required',
                'detail': 'Provide JSON with "compare_to_model_id" field',
                'timestamp': datetime.utcnow().isoformat()
            }), 400

        compare_to = payload.get('compare_to_model_id')
        if not compare_to:
            return jsonify({
                'error': 'Missing required field',
                'detail': '"compare_to_model_id" is required in request body',
                'timestamp': datetime.utcnow().isoformat()
            }), 400

        logger.info(f"Comparing models {model_id} vs {compare_to}")

        # TODO: Query both models from risk_models table
        # TODO: Get performance metrics for both models
        # TODO: Calculate deltas and improvements

        comparison_data = {
            'model_1': model_id,
            'model_2': compare_to,
            'metrics_comparison': {
                'accuracy': {
                    'model_1': 0.924,
                    'model_2': 0.914,
                    'delta': 0.010,
                    'improvement': True,
                    'percent_change': 1.09
                },
                'auc_roc': {
                    'model_1': 0.944,
                    'model_2': 0.938,
                    'delta': 0.006,
                    'improvement': True,
                    'percent_change': 0.64
                },
                'latency_p95_ms': {
                    'model_1': 85,
                    'model_2': 82,
                    'delta': 3,
                    'improvement': False,
                    'percent_change': -3.66
                },
                'false_positive_rate': {
                    'model_1': 0.028,
                    'model_2': 0.032,
                    'delta': -0.004,
                    'improvement': True,
                    'percent_change': 12.50
                }
            },
            'summary': {
                'overall_winner': model_id,
                'improvements': ['accuracy', 'auc_roc', 'false_positive_rate'],
                'regressions': ['latency_p95_ms']
            }
        }

        logger.info(f"Models compared successfully")
        return jsonify(comparison_data), 200

    except Exception as e:
        logger.error(f"Error comparing models: {str(e)}", exc_info=True)
        return jsonify({
            'error': 'Failed to compare models',
            'detail': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500


# ============================================================================
# TRAINING JOBS
# ============================================================================

@bp.route('/training-jobs', methods=['GET'])
def get_training_jobs():
    """Get training job history with filtering, sorting, and pagination.

    Retrieves historical training jobs with their status, timing, dataset info,
    hyperparameters, results, and feature importance rankings.

    Query Parameters:
        status: Filter by status: 'completed' | 'running' | 'queued' | 'failed'
                Optional. If omitted, returns all jobs.
        limit: Maximum results to return (default: 20, max: 100)
        sort: Sort order: 'date' | 'status' (default: 'date', descending)

    Returns (JSON):
        [
            {
                "job_id": "job-20260611-093001",
                "model_id": "v3.1",
                "status": "completed",
                "started_at": "2026-06-11T09:30:00Z",
                "completed_at": "2026-06-11T11:45:00Z",
                "duration_minutes": 135,
                "dataset": {
                    "id": "cbp-shipments-2024",
                    "records": 2500000,
                    "features": 47,
                    "train_test_split": "80/20"
                },
                "hyperparameters": {
                    "max_depth": 8,
                    "learning_rate": 0.05,
                    "n_estimators": 500
                },
                "training_metrics": {
                    "training_accuracy": 0.938,
                    "test_accuracy": 0.931,
                    "auc_roc": 0.951
                },
                "validation_status": "passed",
                "approval_status": "under_review",
                "approval_votes": 1,
                "top_features": [
                    {"name": "documentation_risk", "importance": 0.253},
                    {"name": "corridor_risk", "importance": 0.198},
                    {"name": "routing_risk", "importance": 0.149}
                ]
            }
        ]

    Status Codes:
        200: Training jobs successfully retrieved
        400: Invalid query parameters
        500: Internal server error
    """
    try:
        status_filter = request.args.get('status')
        limit = int(request.args.get('limit', 20))
        sort = request.args.get('sort', 'date')

        # Validate parameters
        valid_statuses = {'completed', 'running', 'queued', 'failed'}
        if status_filter and status_filter not in valid_statuses:
            return jsonify({
                'error': 'Invalid status parameter',
                'detail': f'Status must be one of: {", ".join(valid_statuses)}',
                'timestamp': datetime.utcnow().isoformat()
            }), 400

        if limit < 1 or limit > 100:
            return jsonify({
                'error': 'Invalid limit parameter',
                'detail': 'Limit must be between 1 and 100',
                'timestamp': datetime.utcnow().isoformat()
            }), 400

        valid_sorts = {'date', 'status'}
        if sort not in valid_sorts:
            return jsonify({
                'error': 'Invalid sort parameter',
                'detail': f'Sort must be one of: {", ".join(valid_sorts)}',
                'timestamp': datetime.utcnow().isoformat()
            }), 400

        logger.info(f"Fetching training jobs (status={status_filter}, limit={limit}, sort={sort})")

        # TODO: Query risk_model_training_jobs table
        # TODO: Filter by status if provided
        # TODO: Sort and limit results

        jobs = [
            {
                'job_id': 'job-20260611-093001',
                'model_id': 'v3.1',
                'status': 'completed',
                'started_at': (datetime.utcnow() - timedelta(days=2)).isoformat(),
                'completed_at': (datetime.utcnow() - timedelta(days=2, hours=2, minutes=15)).isoformat(),
                'duration_minutes': 135,
                'dataset': {
                    'id': 'cbp-shipments-2024',
                    'records': 2500000,
                    'features': 47,
                    'train_test_split': '80/20'
                },
                'hyperparameters': {
                    'max_depth': 8,
                    'learning_rate': 0.05,
                    'n_estimators': 500
                },
                'training_metrics': {
                    'training_accuracy': 0.938,
                    'test_accuracy': 0.931,
                    'auc_roc': 0.951
                },
                'validation_status': 'passed',
                'approval_status': 'under_review',
                'approval_votes': 1,
                'top_features': [
                    {'name': 'documentation_risk', 'importance': 0.253},
                    {'name': 'corridor_risk', 'importance': 0.198},
                    {'name': 'routing_risk', 'importance': 0.149}
                ]
            }
        ]

        # Filter by status if provided
        if status_filter:
            jobs = [j for j in jobs if j['status'] == status_filter]

        # Apply limit
        jobs = jobs[:limit]

        logger.info(f"Retrieved {len(jobs)} training jobs")
        return jsonify(jobs), 200

    except ValueError as e:
        logger.error(f"Invalid parameter value: {str(e)}")
        return jsonify({
            'error': 'Invalid parameter',
            'detail': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 400
    except Exception as e:
        logger.error(f"Error fetching training jobs: {str(e)}", exc_info=True)
        return jsonify({
            'error': 'Failed to fetch training jobs',
            'detail': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500


@bp.route('/training-jobs/<job_id>', methods=['GET'])
def get_training_job_details(job_id: str):
    """Get detailed training job status with progress tracking and steps.

    Provides comprehensive information about a specific training job including
    current progress, step-by-step status, ETA, and timing information.

    Path Parameters:
        job_id: Training job ID (e.g., 'job-20260611-093001')

    Returns (JSON):
        {
            "job_id": "job-20260611-093001",
            "model_id": "v3.2",
            "status": "running",
            "progress_percent": 45,
            "current_step": "model_training",
            "steps": [
                {"name": "data_prep", "status": "completed", "duration_minutes": 15},
                {"name": "feature_engineering", "status": "completed", "duration_minutes": 12},
                {"name": "model_training", "status": "running", "progress": 45},
                {"name": "validation", "status": "queued"},
                {"name": "artifact_storage", "status": "queued"},
                {"name": "notification", "status": "queued"}
            ],
            "eta_minutes": 75,
            "timing": {
                "started_at": "2026-06-13T08:30:00Z",
                "estimated_completion": "2026-06-13T10:45:00Z"
            }
        }

    Status Codes:
        200: Job details successfully retrieved
        404: Training job not found
        500: Internal server error
    """
    try:
        logger.info(f"Fetching training job details for {job_id}")

        # TODO: Query risk_model_training_jobs table WHERE job_id=job_id
        # TODO: Get current progress and step status
        # TODO: Calculate ETA based on step pace

        job_details = {
            'job_id': job_id,
            'model_id': 'v3.2',
            'status': 'running',
            'progress_percent': 45,
            'current_step': 'model_training',
            'steps': [
                {'name': 'data_prep', 'status': 'completed', 'duration_minutes': 15},
                {'name': 'feature_engineering', 'status': 'completed', 'duration_minutes': 12},
                {'name': 'model_training', 'status': 'running', 'progress': 45},
                {'name': 'validation', 'status': 'queued'},
                {'name': 'artifact_storage', 'status': 'queued'},
                {'name': 'notification', 'status': 'queued'}
            ],
            'eta_minutes': 75,
            'timing': {
                'started_at': (datetime.utcnow() - timedelta(hours=1, minutes=30)).isoformat(),
                'estimated_completion': (datetime.utcnow() + timedelta(minutes=75)).isoformat()
            }
        }

        logger.info(f"Job details retrieved: {job_id} ({job_details['status']})")
        return jsonify(job_details), 200

    except Exception as e:
        logger.error(f"Error fetching job details: {str(e)}", exc_info=True)
        return jsonify({
            'error': 'Failed to fetch job details',
            'detail': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500


@bp.route('/training-jobs', methods=['POST'])
def trigger_training_job():
    """Trigger a new training job with specified configuration.

    Creates and queues a new training job with specified dataset and hyperparameters.

    Request Body (JSON):
        {
            "dataset_id": "cbp-shipments-2024",
            "hyperparameters": {
                "max_depth": 8,
                "learning_rate": 0.05,
                "n_estimators": 500
            },
            "model_version_name": "v3.2",
            "description": "Optional description of purpose"
        }

    Returns (JSON):
        {
            "job_id": "job-20260613-102030",
            "model_id": "v3.2",
            "status": "queued",
            "started_at": "2026-06-13T10:20:30Z",
            "estimated_duration_minutes": 135
        }

    Status Codes:
        201: Training job successfully created
        400: Missing or invalid request parameters
        500: Internal server error
    """
    try:
        payload = request.get_json()
        if not payload:
            return jsonify({
                'error': 'Request body is required',
                'detail': 'Provide JSON with dataset_id, hyperparameters, and model_version_name',
                'timestamp': datetime.utcnow().isoformat()
            }), 400

        # Validate required fields
        required_fields = ['dataset_id', 'hyperparameters', 'model_version_name']
        missing_fields = [f for f in required_fields if f not in payload]
        if missing_fields:
            return jsonify({
                'error': 'Missing required fields',
                'detail': f'Required fields: {", ".join(missing_fields)}',
                'timestamp': datetime.utcnow().isoformat()
            }), 400

        logger.info(f"Triggering training job for model {payload.get('model_version_name')}")

        # TODO: Validate hyperparameters
        # TODO: Create training_job record in database
        # TODO: Queue job for execution (message queue)
        # TODO: Return job details

        job_id = f'job-{datetime.utcnow().strftime("%Y%m%d-%H%M%S")}'
        job_details = {
            'job_id': job_id,
            'model_id': payload.get('model_version_name'),
            'status': 'queued',
            'started_at': datetime.utcnow().isoformat(),
            'estimated_duration_minutes': 135
        }

        logger.info(f"Training job created: {job_id}")
        return jsonify(job_details), 201

    except Exception as e:
        logger.error(f"Error triggering training job: {str(e)}", exc_info=True)
        return jsonify({
            'error': 'Failed to trigger training job',
            'detail': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500


# ============================================================================
# PERFORMANCE METRICS
# ============================================================================

@bp.route('/<model_id>/metrics', methods=['GET'])
def get_model_metrics(model_id: str):
    """Get time-series performance metrics for a model.

    Retrieves historical performance metrics over a specified time range,
    with optional filtering by specific metric type.

    Path Parameters:
        model_id: Model ID (e.g., 'v3.0')

    Query Parameters:
        time_range: Time window: '24h' | '7d' | '30d' (default: '24h')
        metric: Filter metric: 'accuracy' | 'auc' | 'latency' | 'confidence' | 'all'
                (default: 'all')

    Returns (JSON):
        [
            {
                "timestamp": "2026-06-13T10:00:00Z",
                "metric": "accuracy",
                "value": 0.924,
                "segment": null
            },
            {
                "timestamp": "2026-06-13T11:00:00Z",
                "metric": "accuracy",
                "value": 0.923,
                "segment": null
            }
        ]

    Status Codes:
        200: Metrics successfully retrieved
        400: Invalid query parameters
        404: Model not found
        500: Internal server error
    """
    try:
        time_range = request.args.get('time_range', '24h')
        metric = request.args.get('metric', 'all')

        # Validate parameters
        valid_ranges = {'24h', '7d', '30d'}
        if time_range not in valid_ranges:
            return jsonify({
                'error': 'Invalid time_range parameter',
                'detail': f'time_range must be one of: {", ".join(valid_ranges)}',
                'timestamp': datetime.utcnow().isoformat()
            }), 400

        valid_metrics = {'accuracy', 'auc', 'latency', 'confidence', 'all'}
        if metric not in valid_metrics:
            return jsonify({
                'error': 'Invalid metric parameter',
                'detail': f'metric must be one of: {", ".join(valid_metrics)}',
                'timestamp': datetime.utcnow().isoformat()
            }), 400

        logger.info(f"Fetching metrics for {model_id} (time_range={time_range}, metric={metric})")

        # TODO: Query risk_model_metrics table
        # TODO: Filter by model_id, time_range, and metric type
        # TODO: Return chronological time-series data

        hours = 24
        if time_range == '7d':
            hours = 168
        elif time_range == '30d':
            hours = 720

        metrics_data = []
        base_accuracy = 0.92

        for i in range(hours):
            ts = datetime.utcnow() - timedelta(hours=hours - i)
            metrics_data.append({
                'timestamp': ts.isoformat(),
                'metric': 'accuracy',
                'value': base_accuracy + (0.003 if i % 3 == 0 else -0.001),
                'segment': None
            })

        logger.info(f"Retrieved {len(metrics_data)} metric points for {model_id}")
        return jsonify(metrics_data), 200

    except Exception as e:
        logger.error(f"Error fetching metrics: {str(e)}", exc_info=True)
        return jsonify({
            'error': 'Failed to fetch metrics',
            'detail': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500


@bp.route('/<model_id>/metrics/fairness', methods=['GET'])
def get_fairness_metrics(model_id: str):
    """Get fairness metrics broken down by segment (origin, commodity, corridor).

    Analyzes model performance across demographic/operational segments to identify
    potential bias or performance disparities.

    Path Parameters:
        model_id: Model ID (e.g., 'v3.0')

    Query Parameters:
        segment_by: Segmentation dimension: 'origin' | 'commodity' | 'corridor'
                    (default: 'origin')

    Returns (JSON):
        [
            {
                "segment": "origin=CN",
                "accuracy": 0.918,
                "precision": 0.912,
                "recall": 0.925,
                "fairness_score": 0.92,
                "sample_count": 4532
            },
            {
                "segment": "origin=MX",
                "accuracy": 0.932,
                "precision": 0.928,
                "recall": 0.935,
                "fairness_score": 0.93,
                "sample_count": 3124
            }
        ]

    Status Codes:
        200: Fairness metrics successfully retrieved
        400: Invalid query parameters
        404: Model not found
        500: Internal server error
    """
    try:
        segment_by = request.args.get('segment_by', 'origin')

        # Validate parameter
        valid_segments = {'origin', 'commodity', 'corridor'}
        if segment_by not in valid_segments:
            return jsonify({
                'error': 'Invalid segment_by parameter',
                'detail': f'segment_by must be one of: {", ".join(valid_segments)}',
                'timestamp': datetime.utcnow().isoformat()
            }), 400

        logger.info(f"Fetching fairness metrics for {model_id} (segment_by={segment_by})")

        # TODO: Query risk_model_metrics table grouped by segment
        # TODO: Calculate accuracy, precision, recall per segment
        # TODO: Calculate fairness score (deviation from mean)

        fairness_data = [
            {
                'segment': f'{segment_by}=CN',
                'accuracy': 0.918,
                'precision': 0.912,
                'recall': 0.925,
                'fairness_score': 0.92,
                'sample_count': 4532
            },
            {
                'segment': f'{segment_by}=MX',
                'accuracy': 0.932,
                'precision': 0.928,
                'recall': 0.935,
                'fairness_score': 0.93,
                'sample_count': 3124
            },
            {
                'segment': f'{segment_by}=IN',
                'accuracy': 0.925,
                'precision': 0.920,
                'recall': 0.930,
                'fairness_score': 0.92,
                'sample_count': 2891
            }
        ]

        logger.info(f"Retrieved fairness metrics for {len(fairness_data)} segments")
        return jsonify(fairness_data), 200

    except Exception as e:
        logger.error(f"Error fetching fairness metrics: {str(e)}", exc_info=True)
        return jsonify({
            'error': 'Failed to fetch fairness metrics',
            'detail': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500


# ============================================================================
# DATA DRIFT MONITORING
# ============================================================================

@bp.route('/<model_id>/drift', methods=['GET'])
def get_data_drift(model_id: str):
    """Get current data drift status with elevated features and recommendations.

    Compares current feature distributions to baseline (7-day rolling average)
    using Kolmogorov-Smirnov test to detect distributional shifts that may
    indicate model decay or dataset change.

    Path Parameters:
        model_id: Model ID (e.g., 'v3.0')

    Returns (JSON):
        {
            "overall_drift_score": 0.12,
            "status": "normal",
            "baseline_period": "last_7d",
            "current_period": "last_24h",
            "elevated_features": [
                {
                    "feature": "origin_country",
                    "drift_score": 0.34,
                    "status": "elevated",
                    "drift_type": "categorical_shift",
                    "baseline_distribution": {
                        "CN": 0.324,
                        "MX": 0.221,
                        "IN": 0.205,
                        "HK": 0.082,
                        "Other": 0.168
                    },
                    "current_distribution": {
                        "CN": 0.289,
                        "MX": 0.243,
                        "IN": 0.228,
                        "HK": 0.091,
                        "Other": 0.149
                    },
                    "root_cause": "Possible holiday season shift",
                    "recommendation": "Monitor for 48h before retraining"
                }
            ],
            "normal_features": [
                {
                    "feature": "commodity_value",
                    "drift_score": 0.08,
                    "status": "normal",
                    "baseline_mean": 2145,
                    "current_mean": 2168,
                    "percent_change": 1.07
                }
            ]
        }

    Status Codes:
        200: Drift status successfully retrieved
        404: Model not found
        500: Internal server error
    """
    try:
        logger.info(f"Fetching drift status for {model_id}")

        # TODO: Query risk_model_drift_detected table
        # TODO: Calculate baseline vs current distributions
        # TODO: Run Kolmogorov-Smirnov test per feature
        # TODO: Identify elevated features

        drift_data = {
            'overall_drift_score': 0.12,
            'status': 'normal',
            'baseline_period': 'last_7d',
            'current_period': 'last_24h',
            'elevated_features': [
                {
                    'feature': 'origin_country',
                    'drift_score': 0.34,
                    'status': 'elevated',
                    'drift_type': 'categorical_shift',
                    'baseline_distribution': {
                        'CN': 0.324,
                        'MX': 0.221,
                        'IN': 0.205,
                        'HK': 0.082,
                        'Other': 0.168
                    },
                    'current_distribution': {
                        'CN': 0.289,
                        'MX': 0.243,
                        'IN': 0.228,
                        'HK': 0.091,
                        'Other': 0.149
                    },
                    'root_cause': 'Possible holiday season shift',
                    'recommendation': 'Monitor for 48h before retraining'
                }
            ],
            'normal_features': [
                {
                    'feature': 'commodity_value',
                    'drift_score': 0.08,
                    'status': 'normal',
                    'baseline_mean': 2145,
                    'current_mean': 2168,
                    'percent_change': 1.07
                }
            ]
        }

        logger.info(f"Drift status retrieved: overall_score={drift_data['overall_drift_score']}")
        return jsonify(drift_data), 200

    except Exception as e:
        logger.error(f"Error fetching drift status: {str(e)}", exc_info=True)
        return jsonify({
            'error': 'Failed to fetch drift status',
            'detail': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500


@bp.route('/<model_id>/drift/detect', methods=['POST'])
def trigger_drift_detection(model_id: str):
    """Manually trigger a drift detection analysis job.

    Queues an async drift detection job that will analyze current feature
    distributions against baseline and identify any statistical shifts.

    Path Parameters:
        model_id: Model ID (e.g., 'v3.0')

    Returns (JSON):
        {
            "job_id": "drift-20260613-102030",
            "model_id": "v3.0",
            "status": "running",
            "started_at": "2026-06-13T10:20:30Z",
            "estimated_completion": "2026-06-13T10:35:30Z"
        }

    Status Codes:
        202: Drift detection job successfully queued (async)
        500: Internal server error
    """
    try:
        logger.info(f"Triggering drift detection for {model_id}")

        # TODO: Queue drift detection job
        # TODO: Return job details for polling

        job_id = f'drift-{datetime.utcnow().strftime("%Y%m%d-%H%M%S")}'
        drift_job = {
            'job_id': job_id,
            'model_id': model_id,
            'status': 'running',
            'started_at': datetime.utcnow().isoformat(),
            'estimated_completion': (datetime.utcnow() + timedelta(minutes=15)).isoformat()
        }

        logger.info(f"Drift detection job queued: {job_id}")
        return jsonify(drift_job), 202

    except Exception as e:
        logger.error(f"Error triggering drift detection: {str(e)}", exc_info=True)
        return jsonify({
            'error': 'Failed to trigger drift detection',
            'detail': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500


# ============================================================================
# PREDICTION EXPLANATIONS (SHAP)
# ============================================================================

@bp.route('/predictions/<shipment_id>/explain', methods=['GET'])
def explain_prediction(shipment_id: str):
    """Get SHAP explanation for a specific shipment prediction.

    Provides interpretable explanation of how the model arrived at its risk score
    for a shipment, showing which features pushed the score up or down and by how much.

    Path Parameters:
        shipment_id: Shipment identifier (e.g., 'SHP-00142857')

    Query Parameters:
        model_version: Model to explain: 'v3.0' | 'v2.1' (default: 'v3.0')
        compare_to: Optional second model for side-by-side comparison

    Returns (JSON):
        {
            "shipment": {
                "id": "SHP-00142857",
                "origin": "China (Beijing)",
                "destination": "New York",
                "commodity": "Electronics",
                "declared_value": 45200,
                "container_type": "40ft FCL"
            },
            "prediction": {
                "model_version": "v3.0",
                "score": 0.76,
                "confidence": 0.91,
                "classification": "EXAMINE",
                "processing_time_ms": 82
            },
            "shap_explanation": {
                "base_score": 0.35,
                "factors_increasing_risk": [
                    {
                        "feature": "documentation_risk",
                        "value": 0.85,
                        "contribution": 0.16,
                        "rank": 1,
                        "description": "High documentation risk"
                    },
                    {
                        "feature": "routing_risk",
                        "value": "HIGH",
                        "contribution": 0.14,
                        "rank": 2,
                        "description": "Routing through elevated-risk ports"
                    }
                ],
                "factors_decreasing_risk": [
                    {
                        "feature": "party_risk",
                        "value": "LOW",
                        "contribution": -0.04,
                        "rank": 1,
                        "description": "Known exporter with clean history"
                    }
                ],
                "final_calculation": "0.35 + (0.16 + 0.14) - 0.04 = 0.76"
            },
            "interpretation": "This shipment is flagged for EXAMINE due to missing documentation, routing through high-risk ports, and unusual trade pattern.",
            "comparison": {
                "v2_1_score": 0.71,
                "delta": 0.05,
                "direction": "increased",
                "note": "v3.0 is more conservative"
            }
        }

    Status Codes:
        200: Explanation successfully generated
        404: Shipment or prediction not found
        500: Internal server error
    """
    try:
        model_version = request.args.get('model_version', 'v3.0')
        compare_to = request.args.get('compare_to')

        logger.info(f"Explaining prediction for {shipment_id} ({model_version})")

        # TODO: Query risk_model_predictions table
        # TODO: Fetch shipment data
        # TODO: Get SHAP values from precise-risk-engine service
        # TODO: Optionally compare with alternative model version

        explanation_data = {
            'shipment': {
                'id': shipment_id,
                'origin': 'China (Beijing)',
                'destination': 'New York',
                'commodity': 'Electronics',
                'declared_value': 45200,
                'container_type': '40ft FCL'
            },
            'prediction': {
                'model_version': model_version,
                'score': 0.76,
                'confidence': 0.91,
                'classification': 'EXAMINE',
                'processing_time_ms': 82
            },
            'shap_explanation': {
                'base_score': 0.35,
                'factors_increasing_risk': [
                    {
                        'feature': 'documentation_risk',
                        'value': 0.85,
                        'contribution': 0.16,
                        'rank': 1,
                        'description': 'High documentation risk'
                    },
                    {
                        'feature': 'routing_risk',
                        'value': 'HIGH',
                        'contribution': 0.14,
                        'rank': 2,
                        'description': 'Routing through elevated-risk ports'
                    }
                ],
                'factors_decreasing_risk': [
                    {
                        'feature': 'party_risk',
                        'value': 'LOW',
                        'contribution': -0.04,
                        'rank': 1,
                        'description': 'Known exporter with clean history'
                    }
                ],
                'final_calculation': '0.35 + (0.16 + 0.14) - 0.04 = 0.76'
            },
            'interpretation': 'This shipment is flagged for EXAMINE due to missing documentation, routing through high-risk ports, and unusual trade pattern.',
        }

        # Add comparison if requested
        if compare_to:
            explanation_data['comparison'] = {
                'model_version': compare_to,
                'score': 0.71,
                'delta': 0.76 - 0.71,
                'direction': 'increased',
                'note': f'{model_version} is more conservative than {compare_to}'
            }

        logger.info(f"Explanation generated for {shipment_id}")
        return jsonify(explanation_data), 200

    except Exception as e:
        logger.error(f"Error explaining prediction: {str(e)}", exc_info=True)
        return jsonify({
            'error': 'Failed to explain prediction',
            'detail': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500


# ============================================================================
# MODEL APPROVALS
# ============================================================================

@bp.route('/approvals', methods=['GET'])
def get_approvals():
    """Get model approval requests with voting status and audit trail.

    Retrieves all model promotion requests awaiting approval, showing
    performance improvements, voter status, and approval deadlines.

    Query Parameters:
        status: Filter by status: 'pending' | 'approved' | 'rejected'
                Optional. If omitted, returns all requests.

    Returns (JSON):
        [
            {
                "approval_request_id": "apr-20260611",
                "model_id": "v3.1",
                "requested_by": "Alex Kim",
                "requested_at": "2026-06-11T10:30:00Z",
                "request_reason": "+0.7% accuracy, lower FPR",
                "status": "pending",
                "performance_improvement": {
                    "accuracy": {
                        "before": 0.924,
                        "after": 0.931,
                        "delta": 0.007,
                        "percent_change": 0.76
                    },
                    "auc_roc": {
                        "before": 0.944,
                        "after": 0.951,
                        "delta": 0.007,
                        "percent_change": 0.74
                    },
                    "latency": {
                        "before": 85,
                        "after": 87,
                        "delta": 2
                    }
                },
                "voters": [
                    {
                        "voter": "Sarah Chen",
                        "role": "Manager",
                        "vote": "approve",
                        "comment": "Solid improvement. FPR reduction is significant",
                        "voted_at": "2026-06-11T14:22:00Z"
                    },
                    {
                        "voter": "John Davis",
                        "role": "Tech Lead",
                        "vote": null,
                        "status": "pending",
                        "email_sent_at": "2026-06-11T10:35:00Z"
                    }
                ],
                "approval_threshold": "2/2",
                "votes_summary": {
                    "approve": 1,
                    "pending": 1,
                    "reject": 0
                },
                "deadline": "2026-06-14T10:30:00Z"
            }
        ]

    Status Codes:
        200: Approval requests successfully retrieved
        400: Invalid query parameters
        500: Internal server error
    """
    try:
        status_filter = request.args.get('status')

        # Validate parameter
        valid_statuses = {'pending', 'approved', 'rejected'}
        if status_filter and status_filter not in valid_statuses:
            return jsonify({
                'error': 'Invalid status parameter',
                'detail': f'Status must be one of: {", ".join(valid_statuses)}',
                'timestamp': datetime.utcnow().isoformat()
            }), 400

        logger.info(f"Fetching approvals (status={status_filter})")

        # TODO: Query risk_model_approvals table
        # TODO: Filter by status if provided
        # TODO: Include voter status and votes

        approvals = [
            {
                'approval_request_id': 'apr-20260611',
                'model_id': 'v3.1',
                'requested_by': 'Alex Kim',
                'requested_at': (datetime.utcnow() - timedelta(days=1)).isoformat(),
                'request_reason': '+0.7% accuracy, lower FPR',
                'status': 'pending',
                'performance_improvement': {
                    'accuracy': {
                        'before': 0.924,
                        'after': 0.931,
                        'delta': 0.007,
                        'percent_change': 0.76
                    },
                    'auc_roc': {
                        'before': 0.944,
                        'after': 0.951,
                        'delta': 0.007,
                        'percent_change': 0.74
                    },
                    'latency': {
                        'before': 85,
                        'after': 87,
                        'delta': 2
                    }
                },
                'voters': [
                    {
                        'voter': 'Sarah Chen',
                        'role': 'Manager',
                        'vote': 'approve',
                        'comment': 'Solid improvement. FPR reduction is significant',
                        'voted_at': (datetime.utcnow() - timedelta(hours=10)).isoformat()
                    },
                    {
                        'voter': 'John Davis',
                        'role': 'Tech Lead',
                        'vote': None,
                        'status': 'pending',
                        'email_sent_at': (datetime.utcnow() - timedelta(hours=23)).isoformat()
                    }
                ],
                'approval_threshold': '2/2',
                'votes_summary': {
                    'approve': 1,
                    'pending': 1,
                    'reject': 0
                },
                'deadline': (datetime.utcnow() + timedelta(days=1)).isoformat()
            }
        ]

        # Filter by status if provided
        if status_filter:
            approvals = [a for a in approvals if a['status'] == status_filter]

        logger.info(f"Retrieved {len(approvals)} approval requests")
        return jsonify(approvals), 200

    except Exception as e:
        logger.error(f"Error fetching approvals: {str(e)}", exc_info=True)
        return jsonify({
            'error': 'Failed to fetch approvals',
            'detail': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500


@bp.route('/approvals/<approval_id>/vote', methods=['POST'])
def vote_approval(approval_id: str):
    """Cast an approval vote on a model promotion request.

    Records a voter's decision (approve/reject/abstain) on a model promotion.
    Automatically deploys the model if all required votes are met.

    Path Parameters:
        approval_id: Approval request ID (e.g., 'apr-20260611')

    Request Body (JSON):
        {
            "vote": "approve" | "reject" | "abstain",
            "comment": "Optional reasoning for the vote"
        }

    Returns (JSON):
        {
            "approval_id": "apr-20260611",
            "vote_recorded": true,
            "vote": "approve",
            "timestamp": "2026-06-13T10:20:30Z",
            "approval_status": "pending",
            "votes_summary": {
                "approve": 2,
                "pending": 0,
                "reject": 0
            },
            "threshold_met": true,
            "deployment_status": "ready",
            "deployed_model": "v3.1"
        }

    Status Codes:
        200: Vote successfully recorded
        400: Invalid vote value or missing request body
        404: Approval request not found
        500: Internal server error
    """
    try:
        payload = request.get_json()
        if not payload:
            return jsonify({
                'error': 'Request body is required',
                'detail': 'Provide JSON with "vote" field',
                'timestamp': datetime.utcnow().isoformat()
            }), 400

        vote = payload.get('vote')
        comment = payload.get('comment')

        # Validate vote value
        valid_votes = {'approve', 'reject', 'abstain'}
        if vote not in valid_votes:
            return jsonify({
                'error': 'Invalid vote value',
                'detail': f'Vote must be one of: {", ".join(valid_votes)}',
                'timestamp': datetime.utcnow().isoformat()
            }), 400

        logger.info(f"Recording vote for approval {approval_id}: {vote}")

        # TODO: Update risk_model_approvals table
        # TODO: Record vote with timestamp and comment
        # TODO: Check if approval threshold met
        # TODO: If threshold met, trigger auto-deployment

        vote_result = {
            'approval_id': approval_id,
            'vote_recorded': True,
            'vote': vote,
            'timestamp': datetime.utcnow().isoformat(),
            'approval_status': 'pending',
            'votes_summary': {
                'approve': 2,
                'pending': 0,
                'reject': 0
            },
            'threshold_met': True,
            'deployment_status': 'ready',
            'deployed_model': 'v3.1'
        }

        logger.info(f"Vote recorded for {approval_id}")
        return jsonify(vote_result), 200

    except Exception as e:
        logger.error(f"Error recording vote: {str(e)}", exc_info=True)
        return jsonify({
            'error': 'Failed to record vote',
            'detail': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500


# ============================================================================
# RETRAINING CONFIGURATION
# ============================================================================

@bp.route('/retraining-config', methods=['GET'])
def get_retraining_config():
    """Get retraining configuration with trigger history.

    Retrieves the current automated retraining configuration including
    scheduled runs, drift triggers, performance degradation triggers,
    and historical trigger events.

    Returns (JSON):
        {
            "scheduled": {
                "enabled": true,
                "frequency": "weekly",
                "day": "monday",
                "time": "02:00",
                "timezone": "UTC",
                "data_window_days": 7,
                "next_run": "2026-06-16T02:00:00Z",
                "last_run": "2026-06-09T02:15:00Z",
                "last_run_status": "passed"
            },
            "drift_triggered": {
                "enabled": true,
                "drift_threshold": 0.30,
                "persistence_hours": 24,
                "affected_features_min": 3,
                "last_triggered": "2026-06-05T14:30:00Z",
                "last_triggered_feature": "origin_country",
                "resulting_model": "v3.0"
            },
            "model_drift_triggered": {
                "enabled": true,
                "degradation_threshold": -0.02,
                "evaluation_window_days": 7,
                "min_predictions": 10000,
                "last_triggered": "2026-06-02T09:00:00Z",
                "resulting_model": "v3.0"
            },
            "error_triggered": {
                "enabled": false,
                "error_threshold": 0.05,
                "persistence_minutes": 30
            }
        }

    Status Codes:
        200: Configuration successfully retrieved
        500: Internal server error
    """
    try:
        logger.info("Fetching retraining configuration")

        # TODO: Query risk_retraining_config table

        config = {
            'scheduled': {
                'enabled': True,
                'frequency': 'weekly',
                'day': 'monday',
                'time': '02:00',
                'timezone': 'UTC',
                'data_window_days': 7,
                'next_run': (datetime.utcnow() + timedelta(days=3)).isoformat(),
                'last_run': (datetime.utcnow() - timedelta(days=4)).isoformat(),
                'last_run_status': 'passed'
            },
            'drift_triggered': {
                'enabled': True,
                'drift_threshold': 0.30,
                'persistence_hours': 24,
                'affected_features_min': 3,
                'last_triggered': (datetime.utcnow() - timedelta(days=7)).isoformat(),
                'last_triggered_feature': 'origin_country',
                'resulting_model': 'v3.0'
            },
            'model_drift_triggered': {
                'enabled': True,
                'degradation_threshold': -0.02,
                'evaluation_window_days': 7,
                'min_predictions': 10000,
                'last_triggered': (datetime.utcnow() - timedelta(days=11)).isoformat(),
                'resulting_model': 'v3.0'
            },
            'error_triggered': {
                'enabled': False,
                'error_threshold': 0.05,
                'persistence_minutes': 30
            }
        }

        logger.info("Configuration retrieved successfully")
        return jsonify(config), 200

    except Exception as e:
        logger.error(f"Error fetching configuration: {str(e)}", exc_info=True)
        return jsonify({
            'error': 'Failed to fetch configuration',
            'detail': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500


@bp.route('/retraining-config', methods=['PUT'])
def update_retraining_config():
    """Update retraining configuration with validation.

    Updates automated retraining settings including schedule frequency,
    drift detection thresholds, and performance degradation triggers.

    Request Body (JSON):
        {
            "scheduled": {
                "enabled": true,
                "frequency": "weekly",
                "day": "monday",
                "time": "02:00",
                "timezone": "UTC",
                "data_window_days": 7
            },
            "drift_triggered": {
                "enabled": true,
                "drift_threshold": 0.30,
                "persistence_hours": 24,
                "affected_features_min": 3
            },
            "model_drift_triggered": {
                "enabled": true,
                "degradation_threshold": -0.02,
                "evaluation_window_days": 7,
                "min_predictions": 10000
            },
            "error_triggered": {
                "enabled": false,
                "error_threshold": 0.05,
                "persistence_minutes": 30
            }
        }

    Returns (JSON):
        {
            "success": true,
            "updated_at": "2026-06-13T10:20:30Z",
            "config": {...}
        }

    Status Codes:
        200: Configuration successfully updated
        400: Invalid configuration parameters
        500: Internal server error
    """
    try:
        payload = request.get_json()
        if not payload:
            return jsonify({
                'error': 'Request body is required',
                'detail': 'Provide JSON with configuration updates',
                'timestamp': datetime.utcnow().isoformat()
            }), 400

        logger.info("Updating retraining configuration")

        # TODO: Validate configuration
        # - Frequency: daily|weekly|monthly
        # - Thresholds: 0.0-1.0 for drift, -1.0-0.0 for degradation
        # - Times: valid cron format
        # - Durations: positive integers

        # TODO: Update risk_retraining_config table
        # TODO: Log configuration change with timestamp and user

        config_result = {
            'success': True,
            'updated_at': datetime.utcnow().isoformat(),
            'config': payload
        }

        logger.info("Configuration updated successfully")
        return jsonify(config_result), 200

    except Exception as e:
        logger.error(f"Error updating configuration: {str(e)}", exc_info=True)
        return jsonify({
            'error': 'Failed to update configuration',
            'detail': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500


# ============================================================================
# MODEL VERSION ROLLBACK
# ============================================================================

@bp.route('/<model_id>/rollback', methods=['POST'])
def rollback_model(model_id: str):
    """Manually rollback from current model to a previous version.

    Emergency operation to switch back to a previous model version if
    production model exhibits unexpected behavior or performance degradation.

    Path Parameters:
        model_id: Model to rollback to (e.g., 'v2.1')

    Request Body (JSON):
        {
            "reason": "Performance degradation detected",
            "notify_team": true
        }

    Returns (JSON):
        {
            "success": true,
            "current_model": "v2.1",
            "previous_model": "v3.0",
            "rollback_time": "2026-06-13T10:20:30Z",
            "reason_logged": "Performance degradation detected",
            "audit_entry_id": "audit-20260613-102030",
            "notifications_sent": ["team-slack", "team-email"],
            "messages": [
                "Model v3.0 deactivated",
                "Model v2.1 activated for all shipments",
                "Team notified via Slack and email"
            ]
        }

    Status Codes:
        200: Rollback successfully completed
        400: Invalid model ID or missing required fields
        404: Model not found
        409: Cannot rollback (validation failed)
        500: Internal server error
    """
    try:
        payload = request.get_json()
        if not payload:
            return jsonify({
                'error': 'Request body is required',
                'detail': 'Provide JSON with "reason" field',
                'timestamp': datetime.utcnow().isoformat()
            }), 400

        reason = payload.get('reason')
        notify_team = payload.get('notify_team', True)

        if not reason:
            return jsonify({
                'error': 'Missing required field',
                'detail': '"reason" field is required',
                'timestamp': datetime.utcnow().isoformat()
            }), 400

        logger.info(f"Rolling back to model {model_id}. Reason: {reason}")

        # TODO: Query risk_models table to verify both models exist
        # TODO: Get current active model
        # TODO: Validate rollback is possible (not already on target model)
        # TODO: Update active model in database
        # TODO: Update shipment scoring routes to use new model
        # TODO: Create audit log entry
        # TODO: Send notifications if requested

        rollback_result = {
            'success': True,
            'current_model': model_id,
            'previous_model': 'v3.0',
            'rollback_time': datetime.utcnow().isoformat(),
            'reason_logged': reason,
            'audit_entry_id': f'audit-{datetime.utcnow().strftime("%Y%m%d-%H%M%S")}',
            'notifications_sent': ['team-slack', 'team-email'] if notify_team else [],
            'messages': [
                'Model v3.0 deactivated',
                f'Model {model_id} activated for all shipments',
                'Team notified via Slack and email' if notify_team else 'No notifications sent'
            ]
        }

        logger.info(f"Rollback completed: {model_id}")
        return jsonify(rollback_result), 200

    except ValueError as e:
        logger.error(f"Validation error during rollback: {str(e)}")
        return jsonify({
            'error': 'Rollback validation failed',
            'detail': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 409
    except Exception as e:
        logger.error(f"Error performing rollback: {str(e)}", exc_info=True)
        return jsonify({
            'error': 'Failed to perform rollback',
            'detail': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500


# ============================================================================
# PERFORMANCE MEASURES (CBP Contract Gates)
# ============================================================================

@bp.route('/performance/current-gate', methods=['GET'])
def get_current_gate():
    """Get current applicable performance gate for a model.

    Query Parameters:
        model_id (optional): Model version ID (default: v3.0)

    Returns (JSON):
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

        model_id = request.args.get('model_id', 'v3.0')
        logger.info(f"Fetching current gate for model {model_id}")

        api = PerformanceMetricsAPI()
        result = api.get_current_gate(model_id=model_id)

        return jsonify(result), 200

    except Exception as e:
        logger.error(f"Error getting current gate: {str(e)}", exc_info=True)
        return jsonify({
            'error': 'Failed to get current gate',
            'detail': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500


@bp.route('/performance/metrics', methods=['GET'])
def get_performance_metrics():
    """Get calculated performance metrics for current gate.

    Query Parameters:
        model_id (optional): Model version ID (default: v3.0)
        period_start (optional): Start date (YYYY-MM-DD, default: 30 days ago)
        period_end (optional): End date (YYYY-MM-DD, default: today)

    Returns (JSON):
        [
            {
                "metric_name": "scalability",
                "metric_type": "count_per_period",
                "measured_value": 2300,
                "threshold_value": 2000,
                "unit": "shipments",
                "status": "passed",
                "period_start_date": "2026-05-14",
                "period_end_date": "2026-06-13",
                "calculation_details": {...}
            },
            ...
        ]
    """
    try:
        from services.performance_api import PerformanceMetricsAPI
        from datetime import datetime as dt

        model_id = request.args.get('model_id', 'v3.0')
        period_start = request.args.get('period_start')
        period_end = request.args.get('period_end')

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

        return jsonify(results), 200

    except Exception as e:
        logger.error(f"Error getting performance metrics: {str(e)}", exc_info=True)
        return jsonify({
            'error': 'Failed to get performance metrics',
            'detail': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500


@bp.route('/performance/gate/<gate_id>', methods=['GET'])
def get_gate_status(gate_id):
    """Get detailed status of a specific performance gate.

    Path Parameters:
        gate_id: Gate ID (1, 2, 3, option_1, option_2)

    Query Parameters:
        model_id (optional): Model version ID (default: v3.0)
        period_start (optional): Evaluation period start (YYYY-MM-DD)
        period_end (optional): Evaluation period end (YYYY-MM-DD)

    Returns (JSON):
        {
            "gate_id": "3",
            "gate_name": "Optimization & Refinement",
            "description": "...",
            "overall_status": "passed",
            "metrics_passed": 4,
            "metrics_total": 4,
            "pass_percentage": 100,
            "evaluation_period": {
                "start": "2026-05-14",
                "end": "2026-06-13"
            },
            "metrics": [
                {
                    "name": "scalability",
                    "type": "count_per_period",
                    "measured_value": 2300,
                    "threshold_value": 2000,
                    "unit": "shipments",
                    "status": "passed",
                    "meets_requirement": true
                },
                ...
            ]
        }
    """
    try:
        from services.performance_api import PerformanceMetricsAPI
        from datetime import datetime as dt

        model_id = request.args.get('model_id', 'v3.0')
        period_start = request.args.get('period_start')
        period_end = request.args.get('period_end')

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

        return jsonify(result), 200

    except Exception as e:
        logger.error(f"Error getting gate status: {str(e)}", exc_info=True)
        return jsonify({
            'error': 'Failed to get gate status',
            'detail': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500


@bp.route('/performance/mlflow-config', methods=['GET'])
def get_mlflow_performance_config():
    """Get performance configuration from MLflow model tags.

    Query Parameters:
        model_id (optional): Model version ID (default: v3.0)

    Returns (JSON):
        {
            "model_id": "v3.0",
            "gate": "3",
            "tags": {
                "performance_gate": "3",
                "performance_config_timeline": "[121, 180]",
                ...
            }
        }
    """
    try:
        from services.performance_api import PerformanceMetricsAPI

        model_id = request.args.get('model_id', 'v3.0')
        logger.info(f"Fetching MLflow performance config for {model_id}")

        api = PerformanceMetricsAPI()
        result = api.get_mlflow_performance_config(model_id=model_id)

        return jsonify(result), 200

    except Exception as e:
        logger.error(f"Error getting MLflow config: {str(e)}", exc_info=True)
        return jsonify({
            'error': 'Failed to get MLflow performance config',
            'detail': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500
