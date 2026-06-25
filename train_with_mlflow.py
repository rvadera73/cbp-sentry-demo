#!/usr/bin/env python3
"""
MLflow-integrated training pipeline for CBP Sentry Risk Model v3.0

Supports performance gate tagging for multi-gate evaluation framework.
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
import sqlite3
import shutil
import yaml

import mlflow

# Configuration
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
MODELS_DIR = Path("/home/rahulvadera/cbp-sentry/models")
DATA_DIR = Path("/home/rahulvadera/cbp-sentry/data")
DB_PATH = Path("/home/rahulvadera/cbp-sentry/data/cbp_sentry.db")
CONFIG_DIR = Path("/home/rahulvadera/cbp-sentry")
METRICS_CONFIG_PATH = CONFIG_DIR / "metrics_config_cbp.yml"

def setup_mlflow():
    """Configure MLflow tracking"""
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    mlflow.set_experiment("CBP-Sentry-Risk-Models")
    print(f"✅ MLflow tracking URI: {MLFLOW_TRACKING_URI}")
    print(f"✅ Experiment: CBP-Sentry-Risk-Models")

def register_existing_model(version: str = "v3.0", gate: str = "3"):
    """Register existing trained models with MLflow with performance metrics config"""

    print(f"\n📦 Registering v{version} with MLflow (Gate: {gate})...")
    
    # Load performance metrics
    perf_file = MODELS_DIR / "model_performance.json"
    with open(perf_file, 'r') as f:
        metrics = json.load(f)
    
    # Load training results
    results_file = Path("/home/rahulvadera/cbp-sentry/test-results/phase1_training_results.json")
    with open(results_file, 'r') as f:
        training_results = json.load(f)
    
    # Start MLflow run
    with mlflow.start_run(run_name=f"{version}-baseline"):
        # Log hyperparameters
        hyperparams = {
            'framework': 'xgboost',
            'n_estimators': 100,
            'max_depth': 6,
            'learning_rate': 0.05,
            'subsample': 0.8,
            'colsample_bytree': 0.8,
            'scale_pos_weight': 35
        }
        mlflow.log_params(hyperparams)
        
        # Log metrics
        mlflow.log_metrics({
            'auc': float(metrics['metrics']['auc']),
            'precision': float(metrics['metrics']['precision']),
            'recall': float(metrics['metrics']['recall']),
            'f1_score': float(metrics['metrics']['f1_score']),
            'test_samples': int(metrics['test_samples']),
            'positive_samples': int(metrics['positive_samples']),
            'negative_samples': int(metrics['negative_samples']),
            'training_samples': int(training_results['training_samples']),
            'anomalies_detected': int(training_results['iforest_anomaly_count'])
        })
        
        # Log model artifacts
        mlflow.log_artifact(str(MODELS_DIR / "xgboost_model.json"), artifact_path="models")
        mlflow.log_artifact(str(MODELS_DIR / "isolation_forest_model.pkl"), artifact_path="models")
        mlflow.log_artifact(str(MODELS_DIR / "shap_explainer.pkl"), artifact_path="models")
        mlflow.log_artifact(str(perf_file), artifact_path="metrics")
        mlflow.log_artifact(str(results_file), artifact_path="metrics")
        
        # Log data info
        mlflow.log_dict({
            'training_data': str(DATA_DIR / "training_data.csv"),
            'feature_matrix': str(DATA_DIR / "feature_matrix_72.csv"),
            'features_count': 72,
            'samples_count': 10287,
            'training_samples': 7200,
            'test_samples': 3087,
            'positive_samples': 287,
            'negative_samples': 10000
        }, artifact_file="data_info.json")
        
        # Log model tags
        mlflow.set_tag("model_type", "xgboost_classifier")
        mlflow.set_tag("framework", "xgboost")
        mlflow.set_tag("domain", "cbp")
        mlflow.set_tag("risk_factors", "7")
        mlflow.set_tag("gates", "3")
        mlflow.set_tag("performance_gate", gate)

        # Load and tag performance metrics configuration
        if METRICS_CONFIG_PATH.exists():
            with open(METRICS_CONFIG_PATH, 'r') as f:
                config = yaml.safe_load(f)

            # Find the specific gate configuration
            gate_config = None
            for g in config.get('gates', []):
                if str(g.get('gate_id')) == str(gate):
                    gate_config = g
                    break

            if gate_config:
                # Tag performance metrics config
                mlflow.set_tag("performance_config_gate", gate)
                mlflow.set_tag("performance_config_timeline", str(gate_config.get('timeline_days')))

                # Log metrics specs as artifact
                metrics_info = {
                    "gate_id": gate_config.get('gate_id'),
                    "gate_name": gate_config.get('gate_name'),
                    "timeline_days": gate_config.get('timeline_days'),
                    "metrics": [
                        {
                            "name": m.get('name'),
                            "type": m.get('type'),
                            "threshold": m.get('threshold'),
                            "unit": m.get('unit')
                        }
                        for m in gate_config.get('metrics', [])
                    ]
                }
                mlflow.log_dict(metrics_info, artifact_file="performance_gate_config.json")
                print(f"✅ Performance gate {gate} configuration tagged")

        run_id = mlflow.active_run().info.run_id
        print(f"✅ MLflow run ID: {run_id}")
        print(f"   View at: http://localhost:5000/#/experiments/1/runs/{run_id}")

    return run_id

def update_database(model_version: str, mlflow_run_id: str):
    """Update risk_models table with v3.0 model metadata"""
    
    print(f"\n💾 Updating database with v{model_version}...")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check if v3.0 already exists
    cursor.execute("SELECT id FROM risk_models WHERE model_id = ?", (model_version,))
    existing = cursor.fetchone()
    
    if existing:
        print(f"⚠️  Model v{model_version} already in database, updating...")
        cursor.execute("""
            UPDATE risk_models 
            SET status='staging', updated_at=CURRENT_TIMESTAMP, 
                artifact_path=?
            WHERE model_id=?
        """, (f"mlflow:run/{mlflow_run_id}", model_version))
    else:
        # Insert new model
        cursor.execute("""
            INSERT INTO risk_models (id, model_id, version, name, status, framework, 
                                   model_type, feature_count, weights_sum, artifact_path, 
                                   created_by, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (
            f"risk-model-{model_version}",
            model_version,
            model_version,
            f"Precise Risk Model {model_version}",
            'staging',
            'xgboost',
            'classifier',
            72,
            1.0,
            f"mlflow:run/{mlflow_run_id}",
            "mlflow-integration"
        ))
        print(f"✅ Created v{model_version} in risk_models table")
    
    # Also create retraining config for v3.0
    cursor.execute("SELECT id FROM risk_retraining_config WHERE model_id = ?", 
                  (model_version,))
    if not cursor.fetchone():
        cursor.execute("""
            INSERT INTO risk_retraining_config (id, model_id, scheduled_retrain, 
                                             retrain_interval_days, 
                                             drift_threshold_warning, 
                                             drift_threshold_critical,
                                             performance_threshold,
                                             auto_trigger_on_drift,
                                             auto_trigger_on_performance,
                                             created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (
            f"config-{model_version}",
            model_version,
            1,  # scheduled_retrain = true
            7,  # retrain every 7 days
            0.30,  # warning threshold
            0.50,  # critical threshold
            0.85,  # performance threshold
            1,     # auto trigger on drift
            1,     # auto trigger on performance drop
        ))
        print(f"✅ Created retraining config for v{model_version}")
    
    conn.commit()
    conn.close()

def main():
    parser = argparse.ArgumentParser(description="Train and register CBP Risk Model with MLflow")
    parser.add_argument("--version", default="v3.0", help="Model version (e.g., v3.0, v3.1)")
    parser.add_argument("--gate", default="3", help="Performance gate (1, 2, 3, option_1, option_2)")
    args = parser.parse_args()
    
    print("=" * 70)
    print(f"🚀 CBP Sentry Model Training Pipeline (MLflow Integration)")
    print("=" * 70)
    
    setup_mlflow()
    mlflow_run_id = register_existing_model(version=args.version, gate=args.gate)
    update_database(args.version, mlflow_run_id)
    
    print("\n" + "=" * 70)
    print(f"✅ Model v{args.version} registered with MLflow!")
    print("=" * 70)
    print("\n📊 Next Steps:")
    print(f"  1. View in MLflow: http://localhost:5000/experiments/1")
    print(f"  2. Check database: SELECT * FROM risk_models WHERE model_id='{args.version}'")
    print(f"  3. Test in UI: http://localhost:3001/risk-models")

if __name__ == "__main__":
    main()

