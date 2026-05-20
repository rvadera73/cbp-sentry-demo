#!/usr/bin/env python3
"""
Build and train ML models for Sentry CBP scoring pipeline.

Generates synthetic training data and trains:
1. Isolation Forest (AIS anomaly detection) → isolation_forest.pkl + scaler.pkl
2. LightGBM (transshipment pattern recognition) → lgbm_classifier.txt

Run: python scripts/build_models.py (from api/ directory)
"""

import os
import sys
import pickle
import numpy as np
import pandas as pd
from pathlib import Path

# Add api/ to path so we can import when running from repo root
sys.path.insert(0, str(Path(__file__).parent.parent))

from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import lightgbm as lgb


def generate_ais_records(n_total: int = 1000, contamination: float = 0.1) -> tuple:
    """
    Generate synthetic AIS vessel tracking records.

    Features: dwell_days, transit_days, cost_delta, rerouting_count
    Labels: ~10% anomalies (high dwell), ~90% normal

    Args:
        n_total: Total records to generate
        contamination: Fraction of anomalies

    Returns:
        (X_array, y_labels) - Feature matrix and anomaly labels
    """
    np.random.seed(42)

    n_anomalies = int(n_total * contamination)
    n_normal = n_total - n_anomalies

    records = []

    # Normal records (typical shipping)
    for _ in range(n_normal):
        dwell_days = np.random.normal(2.1, 0.8)  # Baseline 2.1 days
        transit_days = np.random.normal(20, 3)
        cost_delta = np.random.normal(0, 50)  # Price variance in USD
        rerouting_count = np.random.poisson(0.3)  # Few reroutes

        records.append({
            'dwell_days': max(0.1, dwell_days),
            'transit_days': max(5, transit_days),
            'cost_delta': cost_delta,
            'rerouting_count': rerouting_count,
            'anomaly': 0
        })

    # Anomalous records (suspicious: long dwell, extra reroutes, cost spikes)
    for _ in range(n_anomalies):
        dwell_days = np.random.uniform(8, 15)  # Extended dwell (5-7× baseline)
        transit_days = np.random.normal(22, 4)
        cost_delta = np.random.uniform(-200, 200)  # Larger price variance
        rerouting_count = np.random.poisson(2)  # More reroutes

        records.append({
            'dwell_days': dwell_days,
            'transit_days': max(5, transit_days),
            'cost_delta': cost_delta,
            'rerouting_count': rerouting_count,
            'anomaly': 1
        })

    df = pd.DataFrame(records)
    X = df[['dwell_days', 'transit_days', 'cost_delta', 'rerouting_count']].values
    y = df['anomaly'].values

    return X, y


def generate_manifest_records(n_total: int = 500, pos_ratio: float = 0.2) -> tuple:
    """
    Generate synthetic manifest records for transshipment detection.

    Features: hts_6digit, country_origin_encoded, shipper_age_months, ad_duty_rate,
              er_confidence, ais_anomaly_score, isf_stuffing_country, price_market_ratio
    Labels: 1 = transshipment (suspect), 0 = legitimate

    Args:
        n_total: Total records to generate
        pos_ratio: Fraction of transshipment labels

    Returns:
        (X_array, y_labels) - Feature matrix and binary labels
    """
    np.random.seed(42)

    n_pos = int(n_total * pos_ratio)
    n_neg = n_total - n_pos

    records = []

    # Legitimate shipments (label=0)
    for _ in range(n_neg):
        hts_6digit = np.random.choice([170190, 270300, 640999, 760410])  # Aluminum, minerals
        country_origin = np.random.choice([1, 2, 3], p=[0.4, 0.3, 0.3])  # Encoded countries
        shipper_age_months = np.random.uniform(12, 240)  # 1-20 years old
        ad_duty_rate = np.random.uniform(0, 50)  # 0-50% duty
        er_confidence = np.random.uniform(0.7, 1.0)  # High confidence
        ais_anomaly_score = np.random.uniform(-1, 0.3)  # Normal AIS
        isf_stuffing = np.random.choice([0, 1])  # 0=Origin country, 1=Third country
        price_market_ratio = np.random.uniform(0.85, 1.05)  # Market price ±15%

        records.append({
            'hts_6digit': hts_6digit,
            'country_origin': country_origin,
            'shipper_age_months': shipper_age_months,
            'ad_duty_rate': ad_duty_rate,
            'er_confidence': er_confidence,
            'ais_anomaly_score': ais_anomaly_score,
            'isf_stuffing_country': isf_stuffing,
            'price_market_ratio': price_market_ratio,
            'transshipment': 0
        })

    # Transshipment records (label=1)
    for _ in range(n_pos):
        hts_6digit = np.random.choice([760410, 760421])  # Aluminum extrusions (high risk)
        country_origin = np.random.choice([5, 6])  # Vietnam, Thailand
        shipper_age_months = np.random.uniform(3, 36)  # Newer shipper
        ad_duty_rate = np.random.uniform(50, 400)  # High duty rates
        er_confidence = np.random.uniform(0.6, 0.95)  # Lower confidence
        ais_anomaly_score = np.random.uniform(0.5, 1.0)  # High anomaly score
        isf_stuffing = 1  # Stuffing in third country (e.g., China)
        price_market_ratio = np.random.uniform(0.70, 0.95)  # Below market

        records.append({
            'hts_6digit': hts_6digit,
            'country_origin': country_origin,
            'shipper_age_months': shipper_age_months,
            'ad_duty_rate': ad_duty_rate,
            'er_confidence': er_confidence,
            'ais_anomaly_score': ais_anomaly_score,
            'isf_stuffing_country': isf_stuffing,
            'price_market_ratio': price_market_ratio,
            'transshipment': 1
        })

    df = pd.DataFrame(records)
    X = df[['hts_6digit', 'country_origin', 'shipper_age_months', 'ad_duty_rate',
             'er_confidence', 'ais_anomaly_score', 'isf_stuffing_country', 'price_market_ratio']].values
    y = df['transshipment'].values

    return X, y


def train_isolation_forest(X: np.ndarray, y: np.ndarray, output_dir: Path) -> None:
    """
    Train Isolation Forest for AIS anomaly detection.

    Saves:
    - isolation_forest.pkl: trained model
    - scaler.pkl: StandardScaler for feature normalization

    Args:
        X: Feature matrix (n_samples, 4)
        y: Anomaly labels (not used for training, just for evaluation)
        output_dir: Directory to save models
    """
    print("Training Isolation Forest on 1000 AIS records...")

    # Normalize features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Train model
    model = IsolationForest(
        contamination=0.1,
        random_state=42,
        n_jobs=-1
    )
    model.fit(X_scaled)

    # Save both scaler and model
    scaler_path = output_dir / "scaler.pkl"
    with open(scaler_path, 'wb') as f:
        pickle.dump(scaler, f)
    print(f"  Saved scaler to {scaler_path}")

    model_path = output_dir / "isolation_forest.pkl"
    with open(model_path, 'wb') as f:
        pickle.dump(model, f)
    print(f"  Saved Isolation Forest to {model_path}")

    # Quick validation
    scores = model.decision_function(X_scaled)
    print(f"  Anomaly scores: min={scores.min():.3f}, max={scores.max():.3f}, mean={scores.mean():.3f}")


def train_lgbm_classifier(X: np.ndarray, y: np.ndarray, output_dir: Path) -> None:
    """
    Train LightGBM classifier for transshipment pattern detection.

    Saves:
    - lgbm_classifier.txt: trained model in Booster format

    Args:
        X: Feature matrix (n_samples, 8)
        y: Binary labels (0=legitimate, 1=transshipment)
        output_dir: Directory to save model
    """
    print("\nTraining LightGBM on 500 manifest records...")

    # Create LightGBM dataset
    train_data = lgb.Dataset(X, label=y)

    # Train with early stopping
    params = {
        'objective': 'binary',
        'metric': 'auc',
        'num_leaves': 31,
        'learning_rate': 0.05,
        'verbose': -1
    }

    model = lgb.train(
        params,
        train_data,
        num_boost_round=100,
        valid_sets=[train_data],
        valid_names=['train']
    )

    # Save model
    model_path = output_dir / "lgbm_classifier.txt"
    model.save_model(str(model_path))
    print(f"  Saved LightGBM to {model_path}")

    # Quick validation
    pred_proba = model.predict(X)
    print(f"  Probability scores: min={pred_proba.min():.3f}, max={pred_proba.max():.3f}, mean={pred_proba.mean():.3f}")


def main():
    """Generate and train all models."""
    # Determine output directory
    script_dir = Path(__file__).parent
    api_dir = script_dir.parent
    output_dir = api_dir / "models"

    # Create models directory if needed
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Models output directory: {output_dir}\n")

    # Generate synthetic AIS data and train Isolation Forest
    X_ais, y_ais = generate_ais_records(n_total=1000, contamination=0.1)
    print(f"Generated 1000 AIS records (100 anomalies, 900 normal)")
    train_isolation_forest(X_ais, y_ais, output_dir)

    # Generate synthetic manifest data and train LightGBM
    X_manifest, y_manifest = generate_manifest_records(n_total=500, pos_ratio=0.2)
    print(f"\nGenerated 500 manifest records (100 transshipment, 400 legitimate)")
    train_lgbm_classifier(X_manifest, y_manifest, output_dir)

    print(f"\n✓ Models saved to {output_dir}/")
    print("  - isolation_forest.pkl")
    print("  - scaler.pkl")
    print("  - lgbm_classifier.txt")
    print("\nReady for scoring service to load and use.")


if __name__ == '__main__':
    main()
