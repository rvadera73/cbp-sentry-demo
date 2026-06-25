"""
Risk Model Test Data Seeding Script
====================================

Creates realistic test data for integration tests covering all risk model management tables:

1. risk_models — Model registry with v3.0 (production), v3.1 (candidate), v2.1 (deprecated)
2. risk_model_training_jobs — Training job history with metrics
3. risk_model_metrics — Time-series performance metrics (accuracy, latency, confidence)
4. risk_model_predictions — 100 real shipment predictions with SHAP values
5. risk_model_drift_detected — Data and model drift detection records
6. risk_model_approvals — Approval workflow state
7. risk_retraining_config — Automated retraining configuration

All data is realistic and consistent with CBP Sentry operations.
Date: 2026-06-13
"""

import uuid
import json
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)


async def seed_test_data(db_session: AsyncSession) -> dict:
    """
    Seed comprehensive test data for risk model integration tests.

    Returns:
        dict with counts of seeded records:
        {
            'models': int,
            'training_jobs': int,
            'metrics': int,
            'predictions': int,
            'drift_records': int,
            'approvals': int,
            'config': int
        }
    """
    try:
        counts = {
            'models': 0,
            'training_jobs': 0,
            'metrics': 0,
            'predictions': 0,
            'drift_records': 0,
            'approvals': 0,
            'config': 0
        }

        # =====================================================================
        # 1. SEED risk_models (model registry)
        # =====================================================================
        logger.info("Seeding risk_models...")

        # v3.0 - Production (approved, deployed)
        model_v3_0_id = str(uuid.uuid4())
        await db_session.execute(text("""
            INSERT OR IGNORE INTO risk_models
            (id, model_id, version, name, status, framework, model_type, feature_count,
             weights_sum, metadata, created_by, approved_by, deployed_at, approved_at, updated_at)
            VALUES
            (:id, :model_id, :version, :name, :status, :framework, :model_type, :feature_count,
             :weights_sum, :metadata, :created_by, :approved_by, :deployed_at, :approved_at, :updated_at)
        """), {
            'id': model_v3_0_id,
            'model_id': 'v3.0',
            'version': '3.0',
            'name': 'CBP Risk Model v3.0 — Production',
            'status': 'production',
            'framework': 'xgboost',
            'model_type': 'gradient_boosting_classifier',
            'feature_count': 47,
            'weights_sum': 100.0,
            'metadata': json.dumps({
                'accuracy': 0.924,
                'auc_roc': 0.958,
                'precision': 0.942,
                'recall': 0.905,
                'training_data_records': 2500000,
                'training_start_date': '2026-06-01',
                'training_end_date': '2026-06-11'
            }),
            'created_by': 'ml_team@cbp.dhs.gov',
            'approved_by': 'chief_data_officer@cbp.dhs.gov',
            'deployed_at': datetime.utcnow() - timedelta(days=2),
            'approved_at': datetime.utcnow() - timedelta(days=2),
            'updated_at': datetime.utcnow()
        })
        counts['models'] += 1
        logger.info(f"  ✓ Created v3.0 production model: {model_v3_0_id}")

        # v3.1 - Candidate (pending approval, 1/2 votes)
        model_v3_1_id = str(uuid.uuid4())
        await db_session.execute(text("""
            INSERT OR IGNORE INTO risk_models
            (id, model_id, version, name, status, framework, model_type, feature_count,
             weights_sum, metadata, created_by, updated_at)
            VALUES
            (:id, :model_id, :version, :name, :status, :framework, :model_type, :feature_count,
             :weights_sum, :metadata, :created_by, :updated_at)
        """), {
            'id': model_v3_1_id,
            'model_id': 'v3.1',
            'version': '3.1',
            'name': 'CBP Risk Model v3.1 — Candidate',
            'status': 'candidate',
            'framework': 'xgboost',
            'model_type': 'gradient_boosting_classifier',
            'feature_count': 47,
            'weights_sum': 100.0,
            'metadata': json.dumps({
                'accuracy': 0.931,
                'auc_roc': 0.963,
                'precision': 0.949,
                'recall': 0.913,
                'training_data_records': 2500000,
                'training_start_date': '2026-06-05',
                'training_end_date': '2026-06-12',
                'improvements': [
                    'Feature importance rebalancing for origin country signals',
                    'Enhanced ISF Element 9 anomaly detection',
                    'Improved fairness metrics across MX, IN, HK origins'
                ]
            }),
            'created_by': 'ml_team@cbp.dhs.gov',
            'updated_at': datetime.utcnow()
        })
        counts['models'] += 1
        logger.info(f"  ✓ Created v3.1 candidate model: {model_v3_1_id}")

        # v2.1 - Deprecated (100% weights due to legacy constraint)
        model_v2_1_id = str(uuid.uuid4())
        await db_session.execute(text("""
            INSERT OR IGNORE INTO risk_models
            (id, model_id, version, name, status, framework, model_type, feature_count,
             weights_sum, metadata, created_by, deprecated_at, updated_at)
            VALUES
            (:id, :model_id, :version, :name, :status, :framework, :model_type, :feature_count,
             :weights_sum, :metadata, :created_by, :deprecated_at, :updated_at)
        """), {
            'id': model_v2_1_id,
            'model_id': 'v2.1',
            'version': '2.1',
            'name': 'CBP Risk Model v2.1 — Deprecated',
            'status': 'deprecated',
            'framework': 'xgboost',
            'model_type': 'gradient_boosting_classifier',
            'feature_count': 32,
            'weights_sum': 110.0,  # Legacy weight constraint
            'metadata': json.dumps({
                'accuracy': 0.891,
                'auc_roc': 0.931,
                'precision': 0.897,
                'recall': 0.876,
                'deprecation_reason': 'Replaced by v3.0 with improved fairness metrics'
            }),
            'created_by': 'ml_team@cbp.dhs.gov',
            'deprecated_at': datetime.utcnow() - timedelta(days=30),
            'updated_at': datetime.utcnow()
        })
        counts['models'] += 1
        logger.info(f"  ✓ Created v2.1 deprecated model: {model_v2_1_id}")

        # =====================================================================
        # 2. SEED risk_model_training_jobs (training history)
        # =====================================================================
        logger.info("Seeding risk_model_training_jobs...")

        # Job for v3.1 (completed)
        job_v3_1_id = str(uuid.uuid4())
        job_v3_1_started = datetime.utcnow() - timedelta(days=1, hours=12)
        job_v3_1_completed = job_v3_1_started + timedelta(hours=6)
        await db_session.execute(text("""
            INSERT OR IGNORE INTO risk_model_training_jobs
            (id, model_id, job_id, dataset_id, status, started_at, completed_at,
             training_records, test_records, hyperparameters, training_metrics,
             validation_status, artifacts_path, created_at)
            VALUES
            (:id, :model_id, :job_id, :dataset_id, :status, :started_at, :completed_at,
             :training_records, :test_records, :hyperparameters, :training_metrics,
             :validation_status, :artifacts_path, :created_at)
        """), {
            'id': job_v3_1_id,
            'model_id': model_v3_1_id,
            'job_id': 'job-20260611-093001',
            'dataset_id': 'dataset-2026-06-05-to-2026-06-12',
            'status': 'completed',
            'started_at': job_v3_1_started,
            'completed_at': job_v3_1_completed,
            'training_records': 2500000,
            'test_records': 625000,
            'hyperparameters': json.dumps({
                'n_estimators': 500,
                'max_depth': 12,
                'learning_rate': 0.08,
                'subsample': 0.8,
                'colsample_bytree': 0.9,
                'min_child_weight': 3,
                'gamma': 0.1,
                'random_state': 42
            }),
            'training_metrics': json.dumps({
                'train_accuracy': 0.948,
                'test_accuracy': 0.931,
                'train_auc_roc': 0.972,
                'test_auc_roc': 0.963,
                'precision': 0.949,
                'recall': 0.913,
                'f1_score': 0.930,
                'training_duration_hours': 6.2
            }),
            'validation_status': 'passed',
            'artifacts_path': 's3://cbp-sentry-models/v3.1/job-20260611-093001/',
            'created_at': datetime.utcnow() - timedelta(days=1, hours=12)
        })
        counts['training_jobs'] += 1
        logger.info(f"  ✓ Created v3.1 training job: {job_v3_1_id}")

        # Job for v3.0 (completed, deployed)
        job_v3_0_id = str(uuid.uuid4())
        job_v3_0_started = datetime.utcnow() - timedelta(days=2, hours=18)
        job_v3_0_completed = job_v3_0_started + timedelta(hours=5.5)
        await db_session.execute(text("""
            INSERT OR IGNORE INTO risk_model_training_jobs
            (id, model_id, job_id, dataset_id, status, started_at, completed_at,
             training_records, test_records, hyperparameters, training_metrics,
             validation_status, artifacts_path, created_at)
            VALUES
            (:id, :model_id, :job_id, :dataset_id, :status, :started_at, :completed_at,
             :training_records, :test_records, :hyperparameters, :training_metrics,
             :validation_status, :artifacts_path, :created_at)
        """), {
            'id': job_v3_0_id,
            'model_id': model_v3_0_id,
            'job_id': 'job-20260612-143501',
            'dataset_id': 'dataset-2026-06-01-to-2026-06-11',
            'status': 'completed',
            'started_at': job_v3_0_started,
            'completed_at': job_v3_0_completed,
            'training_records': 2500000,
            'test_records': 625000,
            'hyperparameters': json.dumps({
                'n_estimators': 500,
                'max_depth': 12,
                'learning_rate': 0.08,
                'subsample': 0.8,
                'colsample_bytree': 0.9,
                'min_child_weight': 3,
                'gamma': 0.1,
                'random_state': 42
            }),
            'training_metrics': json.dumps({
                'train_accuracy': 0.942,
                'test_accuracy': 0.924,
                'train_auc_roc': 0.967,
                'test_auc_roc': 0.958,
                'precision': 0.942,
                'recall': 0.905,
                'f1_score': 0.923,
                'training_duration_hours': 5.5
            }),
            'validation_status': 'passed',
            'artifacts_path': 's3://cbp-sentry-models/v3.0/job-20260612-143501/',
            'created_at': datetime.utcnow() - timedelta(days=2, hours=18)
        })
        counts['training_jobs'] += 1
        logger.info(f"  ✓ Created v3.0 training job: {job_v3_0_id}")

        # Job for v3.2 (running at 45% progress)
        job_v3_2_id = str(uuid.uuid4())
        job_v3_2_started = datetime.utcnow() - timedelta(hours=2, minutes=45)
        model_v3_2_id = str(uuid.uuid4())
        await db_session.execute(text("""
            INSERT OR IGNORE INTO risk_models
            (id, model_id, version, name, status, framework, model_type, feature_count,
             weights_sum, metadata, created_by, updated_at)
            VALUES
            (:id, :model_id, :version, :name, :status, :framework, :model_type, :feature_count,
             :weights_sum, :metadata, :created_by, :updated_at)
        """), {
            'id': model_v3_2_id,
            'model_id': 'v3.2',
            'version': '3.2',
            'name': 'CBP Risk Model v3.2 — In Training',
            'status': 'training',
            'framework': 'xgboost',
            'model_type': 'gradient_boosting_classifier',
            'feature_count': 48,
            'weights_sum': 100.0,
            'metadata': json.dumps({
                'description': 'Enhanced model with new origin country fairness adjustments'
            }),
            'created_by': 'ml_team@cbp.dhs.gov',
            'updated_at': datetime.utcnow()
        })
        counts['models'] += 1

        await db_session.execute(text("""
            INSERT OR IGNORE INTO risk_model_training_jobs
            (id, model_id, job_id, dataset_id, status, started_at,
             training_records, hyperparameters, created_at)
            VALUES
            (:id, :model_id, :job_id, :dataset_id, :status, :started_at,
             :training_records, :hyperparameters, :created_at)
        """), {
            'id': job_v3_2_id,
            'model_id': model_v3_2_id,
            'job_id': 'job-20260613-020000',
            'dataset_id': 'dataset-2026-06-08-to-2026-06-13',
            'status': 'running',
            'started_at': job_v3_2_started,
            'training_records': 2500000,
            'hyperparameters': json.dumps({
                'n_estimators': 550,
                'max_depth': 13,
                'learning_rate': 0.075,
                'subsample': 0.8,
                'colsample_bytree': 0.9,
                'min_child_weight': 3,
                'gamma': 0.08
            }),
            'created_at': job_v3_2_started
        })
        counts['training_jobs'] += 1
        logger.info(f"  ✓ Created v3.2 training job (45% progress): {job_v3_2_id}")

        # =====================================================================
        # 3. SEED risk_model_metrics (time-series metrics)
        # =====================================================================
        logger.info("Seeding risk_model_metrics (24 hours of data)...")

        # Generate 24 hours of accuracy data for v3.0 (0.920-0.928 range)
        current_time = datetime.utcnow()
        for hour_offset in range(24):
            metric_time = current_time - timedelta(hours=hour_offset)
            accuracy = 0.924 + (0.004 * (0.5 - (hour_offset % 12) / 12))  # Oscillates 0.920-0.928

            metric_id = str(uuid.uuid4())
            await db_session.execute(text("""
                INSERT OR IGNORE INTO risk_model_metrics
                (id, model_id, metric_name, metric_value, timestamp, created_at)
                VALUES (:id, :model_id, :metric_name, :metric_value, :timestamp, :created_at)
            """), {
                'id': metric_id,
                'model_id': model_v3_0_id,
                'metric_name': 'accuracy',
                'metric_value': round(accuracy, 4),
                'timestamp': metric_time,
                'created_at': datetime.utcnow()
            })
            counts['metrics'] += 1

        # Generate 24 hours of latency data (80-90ms range)
        for hour_offset in range(24):
            metric_time = current_time - timedelta(hours=hour_offset)
            latency = 85 + (5 * (0.5 - (hour_offset % 12) / 12))  # Oscillates 80-90ms

            metric_id = str(uuid.uuid4())
            await db_session.execute(text("""
                INSERT OR IGNORE INTO risk_model_metrics
                (id, model_id, metric_name, metric_value, timestamp, created_at)
                VALUES (:id, :model_id, :metric_name, :metric_value, :timestamp, :created_at)
            """), {
                'id': metric_id,
                'model_id': model_v3_0_id,
                'metric_name': 'latency_ms',
                'metric_value': round(latency, 2),
                'timestamp': metric_time,
                'created_at': datetime.utcnow()
            })
            counts['metrics'] += 1

        # Generate 24 hours of confidence data (0.85-0.89 range)
        for hour_offset in range(24):
            metric_time = current_time - timedelta(hours=hour_offset)
            confidence = 0.87 + (0.02 * (0.5 - (hour_offset % 12) / 12))  # Oscillates 0.85-0.89

            metric_id = str(uuid.uuid4())
            await db_session.execute(text("""
                INSERT OR IGNORE INTO risk_model_metrics
                (id, model_id, metric_name, metric_value, timestamp, created_at)
                VALUES (:id, :model_id, :metric_name, :metric_value, :timestamp, :created_at)
            """), {
                'id': metric_id,
                'model_id': model_v3_0_id,
                'metric_name': 'confidence',
                'metric_value': round(confidence, 4),
                'timestamp': metric_time,
                'created_at': datetime.utcnow()
            })
            counts['metrics'] += 1

        # Fairness metrics by origin country
        fairness_data = [
            ('CN', 0.921, 0.89),   # Slight underperformance on China
            ('VN', 0.927, 0.91),   # Strong performance on Vietnam
            ('MX', 0.925, 0.88),   # Good, slight variance
            ('IN', 0.920, 0.87),   # Slightly lower on India
            ('HK', 0.926, 0.90),   # Good on Hong Kong
        ]

        for origin, accuracy, confidence in fairness_data:
            # Accuracy by origin
            metric_id = str(uuid.uuid4())
            await db_session.execute(text("""
                INSERT OR IGNORE INTO risk_model_metrics
                (id, model_id, metric_name, metric_value, segment, timestamp, created_at)
                VALUES (:id, :model_id, :metric_name, :metric_value, :segment, :timestamp, :created_at)
            """), {
                'id': metric_id,
                'model_id': model_v3_0_id,
                'metric_name': 'accuracy_by_origin',
                'metric_value': accuracy,
                'segment': origin,
                'timestamp': current_time,
                'created_at': datetime.utcnow()
            })
            counts['metrics'] += 1

            # Confidence by origin
            metric_id = str(uuid.uuid4())
            await db_session.execute(text("""
                INSERT OR IGNORE INTO risk_model_metrics
                (id, model_id, metric_name, metric_value, segment, timestamp, created_at)
                VALUES (:id, :model_id, :metric_name, :metric_value, :segment, :timestamp, :created_at)
            """), {
                'id': metric_id,
                'model_id': model_v3_0_id,
                'metric_name': 'confidence_by_origin',
                'metric_value': confidence,
                'segment': origin,
                'timestamp': current_time,
                'created_at': datetime.utcnow()
            })
            counts['metrics'] += 1

        logger.info(f"  ✓ Seeded {counts['metrics']} metric records (accuracy, latency, confidence, fairness)")

        # =====================================================================
        # 4. SEED risk_model_predictions (100 shipment predictions)
        # =====================================================================
        logger.info("Seeding risk_model_predictions (100 shipment predictions)...")

        # Real shipment scenarios for CBP operations
        prediction_scenarios = [
            # High-risk origin fraud cases
            {
                'shipment_id': 'SHP-001-VN-ALUMINUM',
                'score': 91.2,
                'confidence': 0.94,
                'classification': 'EXAMINE',
                'risk_factors': ['ISF Element 9 mismatch', 'China origin linkage', 'Price below market', 'AD/CVD incentive'],
                'latency_ms': 87
            },
            {
                'shipment_id': 'SHP-002-CN-ELECTRONICS',
                'score': 87.5,
                'confidence': 0.91,
                'classification': 'EXAMINE',
                'risk_factors': ['AIS dwell anomaly', 'Shipper age < 1 year', 'High-risk commodity'],
                'latency_ms': 92
            },
            {
                'shipment_id': 'SHP-003-IN-TEXTILES',
                'score': 68.3,
                'confidence': 0.87,
                'classification': 'HOLD',
                'risk_factors': ['Price variance 15%', 'New forwarder', 'Quota sensitive'],
                'latency_ms': 81
            },
            # Medium-risk cases
            {
                'shipment_id': 'SHP-004-TH-APPAREL',
                'score': 52.1,
                'confidence': 0.82,
                'classification': 'HOLD',
                'risk_factors': ['Shipper age 6 months', 'Multi-origin pattern', 'Standard pricing'],
                'latency_ms': 84
            },
            {
                'shipment_id': 'SHP-005-MX-PRODUCE',
                'score': 38.9,
                'confidence': 0.79,
                'classification': 'CLEAR',
                'risk_factors': ['Repeat shipper', 'Market-rate pricing', 'Known consignee'],
                'latency_ms': 85
            },
            # Low-risk cases
            {
                'shipment_id': 'SHP-006-CA-MACHINERY',
                'score': 15.4,
                'confidence': 0.96,
                'classification': 'CLEAR',
                'risk_factors': [],
                'latency_ms': 78
            },
            {
                'shipment_id': 'SHP-007-DE-CHEMICALS',
                'score': 12.7,
                'confidence': 0.97,
                'classification': 'CLEAR',
                'risk_factors': [],
                'latency_ms': 79
            },
            {
                'shipment_id': 'SHP-008-JP-AUTOMOTIVE',
                'score': 22.1,
                'confidence': 0.94,
                'classification': 'CLEAR',
                'risk_factors': ['Minor: New HS code'],
                'latency_ms': 82
            },
        ]

        # Expand scenarios to 100 predictions
        base_idx = 0
        for i in range(100):
            scenario = prediction_scenarios[i % len(prediction_scenarios)]

            # Vary scores slightly for realism
            score_variation = (i % 10 - 5) * 0.5  # ±2.5 variation
            score = max(0, min(100, scenario['score'] + score_variation))

            # Determine classification based on score
            if score >= 70:
                classification = 'EXAMINE'
            elif score >= 40:
                classification = 'HOLD'
            else:
                classification = 'CLEAR'

            # Generate SHAP values
            shap_values = {
                'isf_element9_mismatch': round((score * 0.25 if 'ISF' in str(scenario.get('risk_factors', [])) else 0), 2),
                'shipper_age_months': round((score * 0.15 if 'age' in str(scenario.get('risk_factors', [])).lower() else 0), 2),
                'origin_country_risk': round((score * 0.20), 2),
                'commodity_value': round((score * 0.15), 2),
                'ais_dwell_anomaly': round((score * 0.12 if 'AIS' in str(scenario.get('risk_factors', [])) else 0), 2),
                'price_variance_pct': round((score * 0.08 if 'Price' in str(scenario.get('risk_factors', [])) else 0), 2),
                'vessel_routing_flag': round((score * 0.05), 2),
            }

            prediction_id = str(uuid.uuid4())
            await db_session.execute(text("""
                INSERT OR IGNORE INTO risk_model_predictions
                (id, model_id, shipment_id, score, confidence, classification, shap_values,
                 feature_contributions, latency_ms, created_at)
                VALUES
                (:id, :model_id, :shipment_id, :score, :confidence, :classification, :shap_values,
                 :feature_contributions, :latency_ms, :created_at)
            """), {
                'id': prediction_id,
                'model_id': model_v3_0_id,
                'shipment_id': f"{scenario['shipment_id']}-{i:03d}",
                'score': round(score, 1),
                'confidence': round(min(1.0, scenario['confidence'] + (i % 10) * 0.005), 3),
                'classification': classification,
                'shap_values': json.dumps(shap_values),
                'feature_contributions': json.dumps({
                    'top_3_features': [k for k, v in sorted(shap_values.items(), key=lambda x: x[1], reverse=True)][:3]
                }),
                'latency_ms': scenario['latency_ms'] + (i % 5),
                'created_at': datetime.utcnow() - timedelta(hours=i // 10)
            })
            counts['predictions'] += 1

        logger.info(f"  ✓ Seeded {counts['predictions']} prediction records")

        # =====================================================================
        # 5. SEED risk_model_drift_detected
        # =====================================================================
        logger.info("Seeding risk_model_drift_detected...")

        # Origin country drift (score 0.34, elevated)
        drift_id = str(uuid.uuid4())
        await db_session.execute(text("""
            INSERT OR IGNORE INTO risk_model_drift_detected
            (id, model_id, feature_name, drift_type, drift_score, baseline_distribution,
             current_distribution, detected_at, status, created_at, updated_at)
            VALUES
            (:id, :model_id, :feature_name, :drift_type, :drift_score, :baseline_distribution,
             :current_distribution, :detected_at, :status, :created_at, :updated_at)
        """), {
            'id': drift_id,
            'model_id': model_v3_0_id,
            'feature_name': 'origin_country',
            'drift_type': 'data_drift',
            'drift_score': 0.34,
            'baseline_distribution': json.dumps({
                'CN': 0.22,
                'VN': 0.18,
                'MX': 0.20,
                'IN': 0.15,
                'TH': 0.12,
                'Other': 0.13
            }),
            'current_distribution': json.dumps({
                'CN': 0.28,  # Increased
                'VN': 0.16,  # Decreased
                'MX': 0.19,
                'IN': 0.14,
                'TH': 0.11,
                'Other': 0.12
            }),
            'detected_at': datetime.utcnow() - timedelta(hours=6),
            'status': 'acknowledged',
            'created_at': datetime.utcnow() - timedelta(hours=6),
            'updated_at': datetime.utcnow() - timedelta(hours=2)
        })
        counts['drift_records'] += 1
        logger.info(f"  ✓ Created origin_country drift record (score 0.34, elevated)")

        # Commodity value drift (score 0.08, normal)
        drift_id = str(uuid.uuid4())
        await db_session.execute(text("""
            INSERT OR IGNORE INTO risk_model_drift_detected
            (id, model_id, feature_name, drift_type, drift_score, baseline_distribution,
             current_distribution, detected_at, status, created_at, updated_at)
            VALUES
            (:id, :model_id, :feature_name, :drift_type, :drift_score, :baseline_distribution,
             :current_distribution, :detected_at, :status, :created_at, :updated_at)
        """), {
            'id': drift_id,
            'model_id': model_v3_0_id,
            'feature_name': 'commodity_value_usd',
            'drift_type': 'data_drift',
            'drift_score': 0.08,
            'baseline_distribution': json.dumps({
                'mean': 52340.50,
                'std': 28920.30,
                'min': 5000,
                'max': 450000,
                'percentile_50': 42100
            }),
            'current_distribution': json.dumps({
                'mean': 51890.20,  # Slightly lower
                'std': 29150.40,
                'min': 4800,
                'max': 465000,
                'percentile_50': 41800
            }),
            'detected_at': datetime.utcnow() - timedelta(days=1),
            'status': 'resolved',
            'created_at': datetime.utcnow() - timedelta(days=1),
            'updated_at': datetime.utcnow() - timedelta(hours=12)
        })
        counts['drift_records'] += 1
        logger.info(f"  ✓ Created commodity_value drift record (score 0.08, normal)")

        # =====================================================================
        # 6. SEED risk_model_approvals
        # =====================================================================
        logger.info("Seeding risk_model_approvals...")

        # Pending approval for v3.1 (1/2 votes)
        approval_id = str(uuid.uuid4())
        await db_session.execute(text("""
            INSERT OR IGNORE INTO risk_model_approvals
            (id, model_id, approval_request_id, requested_by, requested_at, request_reason,
             voters, status, approval_stage, notes, created_at, updated_at)
            VALUES
            (:id, :model_id, :approval_request_id, :requested_by, :requested_at, :request_reason,
             :voters, :status, :approval_stage, :notes, :created_at, :updated_at)
        """), {
            'id': approval_id,
            'model_id': model_v3_1_id,
            'approval_request_id': 'apr-20260612-v3.1-candidate',
            'requested_by': 'ml_team@cbp.dhs.gov',
            'requested_at': datetime.utcnow() - timedelta(hours=18),
            'request_reason': 'Promoted v3.1 from training to candidate status pending approval for production deployment',
            'voters': json.dumps({
                'chief_data_officer': {'name': 'Dr. Sarah Chen', 'vote': 'approve', 'voted_at': (datetime.utcnow() - timedelta(hours=12)).isoformat()},
                'chief_risk_officer': {'name': 'James Rodriguez', 'vote': None, 'voted_at': None},
                'operations_director': {'name': 'Lisa Kim', 'vote': None, 'voted_at': None}
            }),
            'status': 'pending',
            'approval_stage': '1/3',
            'notes': 'v3.1 shows 0.7% accuracy improvement and better fairness metrics across minority origins. Awaiting Risk Officer review.',
            'created_at': datetime.utcnow() - timedelta(hours=18),
            'updated_at': datetime.utcnow() - timedelta(hours=12)
        })
        counts['approvals'] += 1
        logger.info(f"  ✓ Created pending approval for v3.1 (1/3 votes)")

        # Approved v3.0 (2/2 votes, deployed)
        approval_id = str(uuid.uuid4())
        await db_session.execute(text("""
            INSERT OR IGNORE INTO risk_model_approvals
            (id, model_id, approval_request_id, requested_by, requested_at, request_reason,
             voters, status, approval_stage, approved_at, approved_by, deployed_at,
             notes, created_at, updated_at)
            VALUES
            (:id, :model_id, :approval_request_id, :requested_by, :requested_at, :request_reason,
             :voters, :status, :approval_stage, :approved_at, :approved_by, :deployed_at,
             :notes, :created_at, :updated_at)
        """), {
            'id': approval_id,
            'model_id': model_v3_0_id,
            'approval_request_id': 'apr-20260610-v3.0-production',
            'requested_by': 'ml_team@cbp.dhs.gov',
            'requested_at': datetime.utcnow() - timedelta(days=2, hours=18),
            'request_reason': 'Promote v3.0 from staging to production deployment',
            'voters': json.dumps({
                'chief_data_officer': {'name': 'Dr. Sarah Chen', 'vote': 'approve', 'voted_at': (datetime.utcnow() - timedelta(days=2, hours=12)).isoformat()},
                'chief_risk_officer': {'name': 'James Rodriguez', 'vote': 'approve', 'voted_at': (datetime.utcnow() - timedelta(days=2, hours=6)).isoformat()},
                'operations_director': {'name': 'Lisa Kim', 'vote': None, 'voted_at': None}
            }),
            'status': 'approved',
            'approval_stage': '2/3',
            'approved_at': datetime.utcnow() - timedelta(days=2, hours=6),
            'approved_by': 'chief_risk_officer@cbp.dhs.gov',
            'deployed_at': datetime.utcnow() - timedelta(days=2),
            'notes': 'v3.0 approved for production. Deployed to 10% traffic initially, monitoring for issues.',
            'created_at': datetime.utcnow() - timedelta(days=2, hours=18),
            'updated_at': datetime.utcnow() - timedelta(days=2)
        })
        counts['approvals'] += 1
        logger.info(f"  ✓ Created approved v3.0 (2/3 votes, deployed)")

        # Rejected v2.2 (failed validation)
        approval_id = str(uuid.uuid4())
        await db_session.execute(text("""
            INSERT OR IGNORE INTO risk_model_approvals
            (id, approval_request_id, requested_by, requested_at, request_reason,
             voters, status, notes, created_at, updated_at)
            VALUES
            (:id, :approval_request_id, :requested_by, :requested_at, :request_reason,
             :voters, :status, :notes, :created_at, :updated_at)
        """), {
            'id': approval_id,
            'approval_request_id': 'apr-20260601-v2.2-rejected',
            'requested_by': 'ml_team@cbp.dhs.gov',
            'requested_at': datetime.utcnow() - timedelta(days=12),
            'request_reason': 'Promote v2.2 to production',
            'voters': json.dumps({
                'chief_data_officer': {'name': 'Dr. Sarah Chen', 'vote': 'reject', 'voted_at': (datetime.utcnow() - timedelta(days=12, hours=8)).isoformat()},
                'chief_risk_officer': {'name': 'James Rodriguez', 'vote': None, 'voted_at': None}
            }),
            'status': 'rejected',
            'notes': 'v2.2 rejected due to validation failures: 8 fairness test failures on MX and IN origins, precision drop on high-value shipments.',
            'created_at': datetime.utcnow() - timedelta(days=12),
            'updated_at': datetime.utcnow() - timedelta(days=12, hours=4)
        })
        counts['approvals'] += 1
        logger.info(f"  ✓ Created rejected approval for v2.2")

        # =====================================================================
        # 7. SEED risk_retraining_config
        # =====================================================================
        logger.info("Seeding risk_retraining_config...")

        config_id = str(uuid.uuid4())
        await db_session.execute(text("""
            INSERT OR IGNORE INTO risk_retraining_config
            (id, config_name, enabled, schedule_frequency, schedule_time, schedule_timezone,
             data_window_days, drift_threshold, drift_persistence_hours,
             model_degradation_threshold, evaluation_window_days, min_predictions_threshold,
             error_threshold, error_persistence_minutes, notification_email, notification_slack,
             last_triggered_at, last_triggered_reason, created_at, updated_at)
            VALUES
            (:id, :config_name, :enabled, :schedule_frequency, :schedule_time, :schedule_timezone,
             :data_window_days, :drift_threshold, :drift_persistence_hours,
             :model_degradation_threshold, :evaluation_window_days, :min_predictions_threshold,
             :error_threshold, :error_persistence_minutes, :notification_email, :notification_slack,
             :last_triggered_at, :last_triggered_reason, :created_at, :updated_at)
        """), {
            'id': config_id,
            'config_name': 'Default CBP Sentry Retraining Configuration',
            'enabled': True,
            'schedule_frequency': 'weekly',
            'schedule_time': '02:00',  # 2 AM UTC
            'schedule_timezone': 'UTC',
            'data_window_days': 7,
            'drift_threshold': 0.30,  # Elevated threshold for triggers
            'drift_persistence_hours': 24,  # Must persist for 24 hours before triggering
            'model_degradation_threshold': -2.0,  # Trigger if accuracy drops 2%+
            'evaluation_window_days': 7,
            'min_predictions_threshold': 10000,  # Need 10K predictions for stability
            'error_threshold': 5.0,  # 5% error rate threshold
            'error_persistence_minutes': 30,  # Persist for 30 minutes
            'notification_email': True,
            'notification_slack': True,
            'last_triggered_at': datetime.utcnow() - timedelta(days=6),
            'last_triggered_reason': 'Weekly scheduled retraining completed successfully',
            'created_at': datetime.utcnow() - timedelta(days=60),
            'updated_at': datetime.utcnow()
        })
        counts['config'] += 1
        logger.info(f"  ✓ Created retraining configuration")

        # Commit all seeded data
        await db_session.commit()

        logger.info("\n✅ Test data seeding completed successfully!")
        logger.info(f"   Total records seeded: {sum(counts.values())}")
        for key, val in counts.items():
            logger.info(f"   - {key}: {val}")

        return counts

    except Exception as e:
        await db_session.rollback()
        logger.error(f"❌ Error seeding test data: {e}", exc_info=True)
        raise
