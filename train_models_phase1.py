#!/usr/bin/env python3
"""
Phase 1 Model Training Pipeline for CBP Sentry Risk Scoring Engine

This script trains:
1. XGBoost classifier for illegal transshipment detection
2. Isolation Forest for anomaly detection
3. SHAP explainer for model interpretability

Training data: 10,287 samples (287 positive, 10,000 negative)
Features: 72 engineered features
Target AUC: >= 0.82 on test set
"""

import os
import sys
import json
import time
import warnings
import numpy as np
import pandas as pd
import pickle
import joblib
from pathlib import Path
from datetime import datetime

# ML libraries
import xgboost as xgb
from sklearn.model_selection import train_test_split, StratifiedKFold
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    roc_auc_score, precision_score, recall_score, f1_score,
    confusion_matrix, classification_report, roc_curve
)
import shap

warnings.filterwarnings('ignore')

# Configuration
DATA_DIR = Path("/home/rahulvadera/cbp-sentry/data")
MODELS_DIR = Path("/home/rahulvadera/cbp-sentry/models")
RESULTS_DIR = Path("/home/rahulvadera/cbp-sentry/test-results")

LABELED_FEATURE_MATRIX_PATH = DATA_DIR / "feature_matrix_72_with_labels.csv"
CLEAN_RESULTS_PATH = RESULTS_DIR / "clean_training_results.json"
CLEAN_DETAILED_RESULTS_PATH = RESULTS_DIR / "clean_training_detailed_metrics.json"

# Features to exclude from clean retraining because they are direct or indirect
# proxies for label construction in the current synthetic training set.
LEAKY_FEATURES = [
    'DOCUMENTATION_002_adcvd_applicable',
    'DOCUMENTATION_005_value_weight_anomaly',
    'DOCUMENTATION_008_origin_shipper_mismatch',
    'DOCUMENTATION_009_country_chain_length',
    'DOCUMENTATION_010_filing_status_risk',
    'DOCUMENTATION_011_dwell_time_zscore',
    'ROUTING_004_dwell_time_quartile',
    'ROUTING_005_multi_port_routing',
    'ROUTING_008_complex_routing',
    'ROUTING_009_transshipment_corridor',
    'COMMODITY_005_unit_price_anomaly',
    'COMMODITY_009_commodity_frequency',
    'CORRIDOR_003_shipper_risk_score',
    'CORRIDOR_004_supply_chain_complexity',
    'CORRIDOR_006_se_asia_hub_risk',
    'CORRIDOR_008_hong_kong_route',
    'CORRIDOR_014_multi_hop_routing',
    'CORRIDOR_015_combined_corridor_risk',
    'PARTY_006_shipper_legitimacy_score',
    'PARTY_008_shipper_repeat_frequency',
    'PARTY_009_location_mismatch_score',
    'PATTERN_001_value_anomaly_score',
    'PATTERN_002_weight_anomaly_score',
    'PATTERN_003_vw_ratio_anomaly_score',
    'PATTERN_004_dwell_anomaly_score',
    'PATTERN_005_ensemble_anomaly',
    'PATTERN_006_rare_shipper_dest',
    'PATTERN_007_corridor_price_deviation',
    'PATTERN_008_rare_commodity_origin',
    'PATTERN_009_shipper_concentration',
    'PATTERN_010_multidim_outlier_score',
    'TIME_SENSITIVITY_001_accelerated_shipping',
    'TIME_SENSITIVITY_002_high_volume_shipper',
    'TIME_SENSITIVITY_003_port_congestion_proxy',
    'TIME_SENSITIVITY_004_urgency_indicator',
    'TIME_SENSITIVITY_005_commodity_surge',
]

# Ensure directories exist
MODELS_DIR.mkdir(exist_ok=True)
RESULTS_DIR.mkdir(exist_ok=True)

# Hyperparameters
XGBOOST_PARAMS = {
    'n_estimators': 100,
    'max_depth': 6,
    'learning_rate': 0.05,
    'subsample': 0.8,
    'colsample_bytree': 0.8,
    'scale_pos_weight': 35,  # Handle class imbalance
    'random_state': 42,
    'eval_metric': 'logloss',
    'early_stopping_rounds': 20,
    'n_jobs': -1,
    'verbosity': 0
}

IFOREST_PARAMS = {
    'n_estimators': 100,
    'contamination': 0.03,
    'random_state': 42,
    'n_jobs': -1
}

def load_data():
    """Load training data and feature matrix."""
    print("[1/7] Loading data...")
    start_time = time.time()

    if not LABELED_FEATURE_MATRIX_PATH.exists():
        raise FileNotFoundError(
            f"Missing labeled feature matrix: {LABELED_FEATURE_MATRIX_PATH}"
        )

    dataset = pd.read_csv(LABELED_FEATURE_MATRIX_PATH)
    required_columns = {'shipment_id', 'label'}
    missing = required_columns - set(dataset.columns)
    if missing:
        raise ValueError(f"Labeled feature matrix missing columns: {sorted(missing)}")

    y = dataset['label'].values
    X_df = dataset.drop(columns=['shipment_id', 'label']).copy()

    dropped_features = [col for col in LEAKY_FEATURES if col in X_df.columns]
    if dropped_features:
        X_df = X_df.drop(columns=dropped_features)

    X = X_df.values

    load_time = time.time() - start_time
    print(f"   - Loaded {X.shape[0]} samples with {X.shape[1]} clean features")
    print(f"   - Class distribution: {np.sum(y==0)} negative, {np.sum(y==1)} positive")
    print(f"   - Dropped {len(dropped_features)} leak-prone features")
    print(f"   - Load time: {load_time:.2f}s")

    return X, y, X_df.columns.tolist(), dataset, dropped_features

def prepare_train_test_split(X, y, test_size=0.3, random_state=42):
    """Create stratified train/test split."""
    print("\n[2/7] Creating stratified train/test split...")
    start_time = time.time()

    X_train, X_test, y_train, y_test = train_test_split(
        X, y,
        test_size=test_size,
        random_state=random_state,
        stratify=y,
        shuffle=True
    )

    split_time = time.time() - start_time

    print(f"   - Training set: {X_train.shape[0]} samples")
    print(f"     - Negative: {np.sum(y_train==0)}, Positive: {np.sum(y_train==1)}")
    print(f"   - Test set: {X_test.shape[0]} samples")
    print(f"     - Negative: {np.sum(y_test==0)}, Positive: {np.sum(y_test==1)}")
    print(f"   - Split time: {split_time:.2f}s")

    return X_train, X_test, y_train, y_test

def train_xgboost(X_train, y_train, X_test, y_test, feature_names):
    """Train XGBoost classifier."""
    print("\n[3/7] Training XGBoost classifier...")
    start_time = time.time()

    # Create DMatrix for XGBoost
    dtrain = xgb.DMatrix(X_train, label=y_train, feature_names=feature_names)
    dtest = xgb.DMatrix(X_test, label=y_test, feature_names=feature_names)

    # Train with early stopping
    evals = [(dtrain, 'train'), (dtest, 'eval')]
    evals_result = {}

    xgb_model = xgb.train(
        XGBOOST_PARAMS,
        dtrain,
        num_boost_round=200,
        evals=evals,
        evals_result=evals_result,
        early_stopping_rounds=20,
        verbose_eval=False
    )

    train_time = time.time() - start_time
    print(f"   - Trained {xgb_model.num_boosted_rounds()} boosting rounds")
    print(f"   - Training time: {train_time:.2f}s")

    return xgb_model, train_time

def train_isolation_forest(X_train):
    """Train Isolation Forest for anomaly detection."""
    print("\n[4/7] Training Isolation Forest...")
    start_time = time.time()

    iforest_model = IsolationForest(**IFOREST_PARAMS)
    iforest_model.fit(X_train)

    train_time = time.time() - start_time

    # Count anomalies detected
    predictions = iforest_model.predict(X_train)
    anomalies = np.sum(predictions == -1)

    print(f"   - Training samples: {X_train.shape[0]}")
    print(f"   - Anomalies detected: {anomalies} ({100*anomalies/len(predictions):.2f}%)")
    print(f"   - Training time: {train_time:.2f}s")

    return iforest_model, train_time, anomalies

def evaluate_xgboost(xgb_model, X_test, y_test, feature_names):
    """Evaluate XGBoost on test set."""
    print("\n[5/7] Evaluating XGBoost...")
    start_time = time.time()

    dtest = xgb.DMatrix(X_test, label=y_test, feature_names=feature_names)
    y_pred_proba = xgb_model.predict(dtest)
    y_pred = (y_pred_proba >= 0.5).astype(int)

    # Calculate metrics
    auc = roc_auc_score(y_test, y_pred_proba)
    precision = precision_score(y_test, y_pred, zero_division=0)
    recall = recall_score(y_test, y_pred, zero_division=0)
    f1 = f1_score(y_test, y_pred, zero_division=0)

    # Confusion matrix for sensitivity/specificity
    tn, fp, fn, tp = confusion_matrix(y_test, y_pred).ravel()
    sensitivity = tp / (tp + fn) if (tp + fn) > 0 else 0
    specificity = tn / (tn + fp) if (tn + fp) > 0 else 0

    eval_time = time.time() - start_time

    print(f"   - AUC: {auc:.4f}")
    print(f"   - Precision: {precision:.4f}")
    print(f"   - Recall: {recall:.4f}")
    print(f"   - F1 Score: {f1:.4f}")
    print(f"   - Sensitivity: {sensitivity:.4f}")
    print(f"   - Specificity: {specificity:.4f}")
    print(f"   - Evaluation time: {eval_time:.2f}s")

    metrics = {
        'auc': auc,
        'precision': precision,
        'recall': recall,
        'f1': f1,
        'sensitivity': sensitivity,
        'specificity': specificity,
        'confusion_matrix': {'tn': int(tn), 'fp': int(fp), 'fn': int(fn), 'tp': int(tp)}
    }

    return y_pred_proba, y_pred, metrics

def create_shap_explainer(xgb_model, X_train_sample, feature_names):
    """Create SHAP explainer for model interpretability."""
    print("\n[6/7] Creating SHAP explainer...")
    start_time = time.time()

    try:
        # Create TreeExplainer for XGBoost
        explainer = shap.TreeExplainer(xgb_model)

        # Generate SHAP values for sample
        shap_values = explainer.shap_values(X_train_sample)

        explainer_time = time.time() - start_time

        print(f"   - Explainer created for {X_train_sample.shape[0]} samples")
        print(f"   - SHAP values shape: {np.array(shap_values).shape}")
        print(f"   - Explainer creation time: {explainer_time:.2f}s")

        return explainer, shap_values, True, explainer_time
    except Exception as e:
        print(f"   - ERROR: Could not create SHAP explainer: {str(e)}")
        return None, None, False, 0

def compute_score_calibration(y_pred_proba, y_test, feature_names, models_dir):
    """
    Compute percentile-anchored calibration mapping XGBoost probability → 0-100 risk score.

    Anchors:
        neg_95th_pct  → score 40  (top 5% of negative class still below HIGH threshold)
        pos_05th_pct  → score 75  (bottom 5% of positive class already above HIGH threshold)

    Saves models/score_calibration.json consumed by risk_scoring_engine.py at inference.
    """
    print("\n[Calibration] Computing score calibration parameters...")

    neg_probs = y_pred_proba[y_test == 0]
    pos_probs = y_pred_proba[y_test == 1]

    neg_95th = float(np.percentile(neg_probs, 95))
    pos_05th = float(np.percentile(pos_probs, 5))
    pos_50th = float(np.percentile(pos_probs, 50))

    # Full population percentile anchors (all train+test probs)
    all_probs = y_pred_proba
    percentile_anchors = {
        "p50":     float(np.percentile(all_probs, 50)),
        "p75":     float(np.percentile(all_probs, 75)),
        "p85":     float(np.percentile(all_probs, 85)),
        "p90":     float(np.percentile(all_probs, 90)),
        "p95":     float(np.percentile(all_probs, 95)),
        "p99":     float(np.percentile(all_probs, 99)),
        "pos_p10": float(np.percentile(pos_probs, 10)),
        "pos_p50": float(np.percentile(pos_probs, 50)),
        "neg_p95": neg_95th,
        "neg_p99": float(np.percentile(neg_probs, 99)),
    }

    calibration = {
        "version": "1.0",
        "method": "percentile_anchored_linear",
        "anchors": {
            "neg_95th_pct": neg_95th,
            "pos_05th_pct": pos_05th,
            "pos_50th_pct": pos_50th,
            "low_score": 40.0,
            "high_score": 75.0,
        },
        # Batch-percentile anchors for operational scoring (top 25% → score ≥ 70)
        "percentile_anchors": percentile_anchors,
        "thresholds": {
            "LOW": 40,
            "MEDIUM": 55,
            "HIGH": 70,
            "CRITICAL": 85,
        },
        "clean_features": feature_names,
        "feature_count": len(feature_names),
        "neg_prob_stats": {
            "mean": float(np.mean(neg_probs)),
            "p50": float(np.percentile(neg_probs, 50)),
            "p95": neg_95th,
        },
        "pos_prob_stats": {
            "mean": float(np.mean(pos_probs)),
            "p05": pos_05th,
            "p50": pos_50th,
            "p95": float(np.percentile(pos_probs, 95)),
        },
    }

    cal_path = models_dir / "score_calibration.json"
    with open(cal_path, "w") as f:
        json.dump(calibration, f, indent=2)

    print(f"   - neg_95th_pct: {neg_95th:.4f}  → score 40")
    print(f"   - pos_05th_pct: {pos_05th:.4f}  → score 75")
    print(f"   - Clean features saved: {len(feature_names)}")
    print(f"   - Calibration saved to: {cal_path}")

    return calibration


def calibrate_prob_to_score(prob: float, cal: dict) -> float:
    """Map XGBoost probability [0,1] → risk score [0,100] using anchored linear scaling."""
    low_p = cal["anchors"]["neg_95th_pct"]
    high_p = cal["anchors"]["pos_05th_pct"]
    low_s = cal["anchors"]["low_score"]
    high_s = cal["anchors"]["high_score"]

    if prob <= low_p:
        score = 5.0 + (prob / max(low_p, 1e-9)) * (low_s - 5.0)
    elif prob >= high_p:
        score = high_s + ((prob - high_p) / max(1.0 - high_p, 1e-9)) * (95.0 - high_s)
    else:
        score = low_s + ((prob - low_p) / max(high_p - low_p, 1e-9)) * (high_s - low_s)

    return float(min(95.0, max(5.0, score)))


def save_models(xgb_model, iforest_model, explainer, shap_values, models_dir):
    """Save all trained models to disk."""
    print("\n[7/7] Saving models to disk...")

    # Save XGBoost
    xgb_path = models_dir / "xgboost_model.json"
    xgb_model.save_model(str(xgb_path))
    print(f"   - XGBoost saved to: {xgb_path}")

    # Save Isolation Forest
    iforest_path = models_dir / "isolation_forest_model.pkl"
    joblib.dump(iforest_model, iforest_path)
    print(f"   - Isolation Forest saved to: {iforest_path}")

    # Save SHAP explainer if successful
    explainer_path = None
    if explainer is not None:
        explainer_path = models_dir / "shap_explainer.pkl"
        joblib.dump(explainer, explainer_path)
        print(f"   - SHAP explainer saved to: {explainer_path}")

        # Also save SHAP values for reference
        shap_values_path = models_dir / "shap_values_sample.npy"
        np.save(shap_values_path, shap_values)
        print(f"   - SHAP values saved to: {shap_values_path}")

    return str(xgb_path), str(iforest_path), explainer_path is not None

def main():
    """Main training pipeline."""
    print("=" * 80)
    print("CBP SENTRY PHASE 1 - MODEL TRAINING PIPELINE")
    print("=" * 80)
    print(f"Start time: {datetime.now().isoformat()}")
    print(f"Data directory: {DATA_DIR}")
    print(f"Models directory: {MODELS_DIR}")

    overall_start_time = time.time()
    issues = []

    try:
        # Load data
        X, y, feature_names, _dataset, dropped_features = load_data()

        # Check for issues
        if X.shape[0] != 10287:
            issues.append(f"Expected 10,287 samples, got {X.shape[0]}")
        if X.shape[1] <= 0:
            issues.append("No clean features available after leakage filtering")
        if np.sum(y == 1) != 287:
            issues.append(f"Expected 287 positive cases, got {np.sum(y == 1)}")

        # Create train/test split
        X_train, X_test, y_train, y_test = prepare_train_test_split(X, y)

        training_samples = len(X_train)
        test_samples = len(X_test)

        # Train XGBoost
        xgb_model, xgb_train_time = train_xgboost(X_train, y_train, X_test, y_test, feature_names)

        # Train Isolation Forest
        iforest_model, iforest_train_time, anomalies = train_isolation_forest(X_train)

        # Evaluate XGBoost
        y_pred_proba, y_pred, metrics = evaluate_xgboost(xgb_model, X_test, y_test, feature_names)

        # Compute + save score calibration
        calibration = compute_score_calibration(y_pred_proba, y_test, feature_names, MODELS_DIR)

        # Spot-check calibration on test set
        cal_scores = [calibrate_prob_to_score(p, calibration) for p in y_pred_proba]
        high_risk_count = sum(1 for s in cal_scores if s >= 70)
        print(f"   - Calibration check: {high_risk_count} of {len(cal_scores)} test samples score ≥70")

        # Create SHAP explainer with sample
        sample_size = min(100, len(X_train))
        X_train_sample = X_train[:sample_size]
        explainer, shap_values, shap_ready, shap_time = create_shap_explainer(
            xgb_model, X_train_sample, feature_names
        )

        # Save models
        xgb_path, iforest_path, shap_ready_saved = save_models(
            xgb_model, iforest_model, explainer, shap_values, MODELS_DIR
        )

        # Calculate total training time
        total_time = time.time() - overall_start_time

        # Verify models are loadable
        print("\n[Verification] Testing model loading...")
        try:
            xgb_loaded = xgb.Booster()
            xgb_loaded.load_model(xgb_path)
            print("   - XGBoost model loads successfully")
        except Exception as e:
            issues.append(f"XGBoost model load error: {str(e)}")

        try:
            iforest_loaded = joblib.load(iforest_path)
            print("   - Isolation Forest model loads successfully")
        except Exception as e:
            issues.append(f"Isolation Forest model load error: {str(e)}")

        # Build output JSON
        output = {
            'xgb_auc': float(metrics['auc']),
            'xgb_precision': float(metrics['precision']),
            'xgb_recall': float(metrics['recall']),
            'f1_score': float(metrics['f1']),
            'training_samples': int(training_samples),
            'test_samples': int(test_samples),
            'feature_count': int(X.shape[1]),
            'clean_feature_matrix_path': str(LABELED_FEATURE_MATRIX_PATH),
            'dropped_features': dropped_features,
            'iforest_anomaly_count': int(anomalies),
            'shap_explainer_ready': bool(shap_ready and shap_ready_saved),
            'xgb_model_path': str(xgb_path),
            'iforest_model_path': str(iforest_path),
            'training_time_seconds': float(total_time),
            'issues': issues
        }

        # Print summary
        print("\n" + "=" * 80)
        print("TRAINING SUMMARY")
        print("=" * 80)
        print(f"Training samples: {training_samples}")
        print(f"Test samples: {test_samples}")
        print(f"Features: {X.shape[1]}")
        print(f"Dropped leak-prone features: {len(dropped_features)}")
        print(f"\nXGBoost Metrics:")
        print(f"  - AUC: {metrics['auc']:.4f}")
        print(f"  - Precision: {metrics['precision']:.4f}")
        print(f"  - Recall: {metrics['recall']:.4f}")
        print(f"  - F1 Score: {metrics['f1']:.4f}")
        print(f"\nIsolation Forest:")
        print(f"  - Anomalies detected: {anomalies}")
        print(f"\nSHAP Explainer:")
        print(f"  - Ready: {shap_ready and shap_ready_saved}")
        print(f"\nTotal training time: {total_time:.2f}s")
        print(f"Models saved to: {MODELS_DIR}")

        if issues:
            print(f"\nIssues found: {len(issues)}")
            for issue in issues:
                print(f"  - {issue}")
        else:
            print("\nNo issues found!")

        print("\n" + "=" * 80)

        # Save output to JSON file
        with open(CLEAN_RESULTS_PATH, 'w') as f:
            json.dump(output, f, indent=2)
        print(f"Results saved to: {CLEAN_RESULTS_PATH}")

        # Also save detailed metrics
        detailed_metrics = {
            'xgboost': metrics,
            'isolation_forest': {
                'anomalies_detected': int(anomalies),
                'contamination': IFOREST_PARAMS['contamination']
            },
            'dataset': {
                'training_samples': int(training_samples),
                'test_samples': int(test_samples),
                'total_features': int(X.shape[1]),
                'dropped_features': dropped_features,
                'positive_cases_train': int(np.sum(y_train == 1)),
                'negative_cases_train': int(np.sum(y_train == 0)),
                'positive_cases_test': int(np.sum(y_test == 1)),
                'negative_cases_test': int(np.sum(y_test == 0))
            },
            'timing': {
                'total_seconds': float(total_time),
                'xgboost_training_seconds': float(xgb_train_time),
                'isolation_forest_training_seconds': float(iforest_train_time),
                'shap_creation_seconds': float(shap_time)
            }
        }

        with open(CLEAN_DETAILED_RESULTS_PATH, 'w') as f:
            json.dump(detailed_metrics, f, indent=2)
        print(f"Detailed metrics saved to: {CLEAN_DETAILED_RESULTS_PATH}")

        return output

    except Exception as e:
        print(f"\nFATAL ERROR: {str(e)}")
        import traceback
        traceback.print_exc()

        return {
            'xgb_auc': 0.0,
            'xgb_precision': 0.0,
            'xgb_recall': 0.0,
            'f1_score': 0.0,
            'training_samples': 0,
            'test_samples': 0,
            'iforest_anomaly_count': 0,
            'shap_explainer_ready': False,
            'xgb_model_path': '',
            'iforest_model_path': '',
            'training_time_seconds': 0.0,
            'issues': [f"Fatal error: {str(e)}"]
        }

if __name__ == "__main__":
    result = main()
    print("\nReturning results to orchestrator...")
    sys.exit(0)
