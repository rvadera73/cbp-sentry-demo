# ML Model Operations & Training Guide

**Version:** 1.0 | **Date:** 2026-06-12 | **Purpose:** Establish repeatable processes for model training, application, and rollback

This document provides a framework for implementing new ML models in CBP Sentry. It covers:
1. Model training and validation
2. Database schema versioning
3. Safe deployment with rollback capability
4. Monitoring and validation
5. Revert procedures

---

## 1. Overview: The Model Lifecycle

```
┌──────────────────────────────────────────────────────────────────┐
│ PHASE 1: TRAINING & VALIDATION (Lab Environment)                │
├──────────────────────────────────────────────────────────────────┤
│ 1. Collect & prepare training data                               │
│ 2. Feature engineering & selection                               │
│ 3. Model training (with cross-validation)                        │
│ 4. Performance evaluation (accuracy, AUC, latency)               │
│ 5. Hyperparameter tuning                                         │
│ 6. Final validation on holdout test set                          │
│ Output: Trained model artifacts (.pkl, .h5, etc.)               │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│ PHASE 2: SNAPSHOT & PREPARE (Staging Environment)               │
├──────────────────────────────────────────────────────────────────┤
│ 1. Create complete data model snapshots (SQL dumps)              │
│ 2. Add versioning columns/tables to database schema              │
│ 3. Document model metadata (version, features, performance)      │
│ 4. Package trained model for deployment                          │
│ 5. Create rollback scripts                                       │
│ Output: Versioned database, documented model, rollback plan      │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│ PHASE 3: DEPLOY & SCORE (Local/Staging Testing)                 │
├──────────────────────────────────────────────────────────────────┤
│ 1. Deploy microservice with new model                            │
│ 2. Run database migration (add versioning)                       │
│ 3. Rescore all existing data with new model                      │
│ 4. Compare new vs legacy scores                                  │
│ 5. Validate through UI with model version badges                │
│ Output: All shipments have new model scores, comparison data     │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│ PHASE 4: MONITOR & VALIDATE (Production Testing)                │
├──────────────────────────────────────────────────────────────────┤
│ 1. Monitor error rates, latency, fallback events                 │
│ 2. Validate score distributions against expectations             │
│ 3. Track classification rate changes (% HOLD, EXAMINE, CLEAR)    │
│ 4. Gather stakeholder feedback                                   │
│ Output: Performance metrics, validation report                   │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│ DECISION: KEEP or ROLLBACK                                       │
├──────────────────────────────────────────────────────────────────┤
│ IF KEEP:    Promote to production, archive snapshots             │
│ IF ROLLBACK: Restore from snapshot, revert model version         │
│ IF ITERATE: Refine model and repeat Phase 1                      │
└──────────────────────────────────────────────────────────────────┘
```

---

## 2. Phase 1: Training & Validation (Lab)

### 2.1 Prepare Training Dataset

**Objective:** Collect labeled historical data

```python
# Location: services/risk-engine/training/prepare_dataset.py

import pandas as pd
from typing import Tuple

def prepare_training_data() -> Tuple[pd.DataFrame, pd.Series]:
    """
    Load training data from production database or synthetic data
    
    Returns:
        X: Feature matrix (72 CBP features)
        y: Labels (risk_score or binary classification)
    """
    # Option 1: Load from production (if available)
    # df = pd.read_sql('SELECT * FROM shipments', con=db_connection)
    
    # Option 2: Use synthetic data (recommended for initial training)
    # df = generate_synthetic_shipments(n_samples=10000)
    
    # Option 3: Load from archive
    df = pd.read_csv('training_data/shipments_labeled.csv')
    
    # Feature selection (72 CBP fields)
    features = [
        'origin_country', 'destination_country', 'shipper_age_months',
        'consignee_age_months', 'dwell_days', 'declared_value_usd',
        'declared_weight_kg', 'hs_code', 'vessel_flag', 'port_calls',
        'element9_is_mismatch', 'ad_cvd_applicable', 'ad_cvd_rate',
        # ... 59 more features
    ]
    
    X = df[features]
    y = df['risk_score'] > 65  # Binary: high-risk (>65) vs low-risk
    
    return X, y


def validate_data_quality(X: pd.DataFrame, y: pd.Series) -> dict:
    """Check for data issues before training"""
    return {
        'total_records': len(X),
        'missing_values': X.isnull().sum().to_dict(),
        'class_balance': y.value_counts().to_dict(),
        'feature_variance': X.var().to_dict(),
        'outliers_detected': detect_outliers(X)
    }
```

### 2.2 Feature Engineering

**Objective:** Transform 72 raw features into 7 weighted factors

```python
# Location: services/risk-engine/training/feature_engineering.py

import numpy as np

def engineer_features(X: pd.DataFrame) -> pd.DataFrame:
    """
    Transform 72 CBP features into 7 risk factors
    
    Returns:
        DataFrame with 7 factor columns (normalized to 0-100)
    """
    
    factors = pd.DataFrame()
    
    # Factor 1: Documentation Risk (25% weight)
    # Combines: Element 9 mismatch, ISF amendments, completeness
    factors['documentation_risk'] = (
        X['element9_is_mismatch'].astype(int) * 50 +
        X['manifest_amendments'] * 30 +
        (1 - X['field_completeness']) * 20
    )
    
    # Factor 2: Routing Risk (15% weight)
    # Combines: Corridor baseline, AIS dwell, vessel flag
    factors['routing_risk'] = (
        X['corridor_baseline_risk'] * 40 +
        X['dwell_anomaly'] * 40 +
        X['vessel_flag_risk'] * 20
    )
    
    # Factor 3: Commodity Risk (15% weight)
    # Combines: Tariff rate, export control, UFLPA
    factors['commodity_risk'] = (
        X['tariff_rate_risk'] * 50 +
        X['export_control_flag'] * 30 +
        X['uflpa_flag'] * 20
    )
    
    # Factor 4: Corridor Risk (20% weight)
    # Pre-computed country-pair baseline
    factors['corridor_risk'] = X['corridor_risk_baseline']
    
    # Factor 5: Party Risk (15% weight)
    # Combines: Shipper age, violations, OFAC, beneficial ownership
    factors['party_risk'] = (
        (100 - X['shipper_age_months']) / 100 * 35 +
        X['violation_count'] / X['violation_count'].max() * 30 +
        X['ofac_match_score'] * 20 +
        X['beneficial_ownership_opacity'] * 15
    )
    
    # Factor 6: Pattern Risk (10% weight)
    # Combines: Price anomaly, weight anomaly, frequency
    factors['pattern_risk'] = (
        X['price_anomaly_score'] * 50 +
        X['weight_anomaly_score'] * 25 +
        X['frequency_anomaly_score'] * 25
    )
    
    # Factor 7: Time Sensitivity (10% weight)
    # Pre-tariff timing, seasonal anomalies
    factors['time_sensitivity_risk'] = (
        X['pre_tariff_timing'] * 50 +
        X['seasonal_anomaly'] * 50
    )
    
    # Normalize all factors to 0-100
    for col in factors.columns:
        factors[col] = factors[col].clip(0, 100)
    
    return factors


def validate_feature_weights(factors: pd.DataFrame) -> dict:
    """Ensure weights sum to 100%"""
    weights = {
        'documentation_risk': 0.25,
        'routing_risk': 0.15,
        'commodity_risk': 0.15,
        'corridor_risk': 0.20,
        'party_risk': 0.15,
        'pattern_risk': 0.10,
        'time_sensitivity_risk': 0.10
    }
    
    total_weight = sum(weights.values())
    
    return {
        'weights': weights,
        'total': total_weight,
        'is_normalized': abs(total_weight - 1.0) < 0.001,
        'error': f"Weights sum to {total_weight}, expected 1.0"
    }
```

### 2.3 Model Training

**Objective:** Train XGBoost classifier with cross-validation

```python
# Location: services/risk-engine/training/train_model.py

from xgboost import XGBClassifier
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.metrics import accuracy_score, roc_auc_score, confusion_matrix
import joblib

def train_xgboost_model(X, y, output_path: str = 'models/'):
    """Train XGBoost classifier"""
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    
    # Train model
    model = XGBClassifier(
        n_estimators=100,
        max_depth=6,
        learning_rate=0.1,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42
    )
    
    model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=0)
    
    # Evaluate
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]
    
    metrics = {
        'accuracy': accuracy_score(y_test, y_pred),
        'auc_roc': roc_auc_score(y_test, y_proba),
        'precision': precision_score(y_test, y_pred),
        'recall': recall_score(y_test, y_pred),
        'f1': f1_score(y_test, y_pred),
        'confusion_matrix': confusion_matrix(y_test, y_pred).tolist()
    }
    
    print(f"✅ Model trained. AUC-ROC: {metrics['auc_roc']:.3f}")
    
    # Save model
    joblib.dump(model, f'{output_path}/xgboost_model.pkl')
    
    return model, metrics


def train_anomaly_detector(X, output_path: str = 'models/'):
    """Train Isolation Forest for uncertainty quantification (Gate 3)"""
    from sklearn.ensemble import IsolationForest
    
    iso_forest = IsolationForest(contamination=0.1, random_state=42)
    iso_forest.fit(X)
    
    joblib.dump(iso_forest, f'{output_path}/isolation_forest.pkl')
    print("✅ Anomaly detector trained")
    
    return iso_forest


def train_shap_explainer(model, X_sample, output_path: str = 'models/'):
    """Train SHAP explainer for model interpretability"""
    import shap
    
    explainer = shap.TreeExplainer(model)
    joblib.dump(explainer, f'{output_path}/shap_explainer.pkl')
    
    print("✅ SHAP explainer created")
    return explainer
```

### 2.4 Final Validation

**Objective:** Ensure model meets acceptance criteria

```python
# Location: services/risk-engine/training/validate_model.py

def validate_model_requirements(model_metrics: dict) -> dict:
    """
    Check if model meets acceptance criteria
    
    Acceptance Criteria:
    - AUC-ROC >= 0.85
    - Accuracy >= 0.80
    - Latency <= 100ms
    - All critical features present
    """
    
    requirements = {
        'auc_roc_threshold': 0.85,
        'accuracy_threshold': 0.80,
        'latency_threshold_ms': 100,
        'required_features': 72
    }
    
    passed = {
        'auc_roc': model_metrics['auc_roc'] >= requirements['auc_roc_threshold'],
        'accuracy': model_metrics['accuracy'] >= requirements['accuracy_threshold'],
        'all_checks_pass': True
    }
    
    if not all(passed.values()):
        passed['all_checks_pass'] = False
        print("❌ Model does not meet acceptance criteria")
        return passed
    
    print("✅ Model passes all validation criteria")
    return passed
```

---

## 3. Phase 2: Snapshot & Prepare (Staging)

### 3.1 Create Data Model Snapshots

**Objective:** Full backup of current database state

```bash
#!/bin/bash
# Location: scripts/snapshot_database_pre_migration.sh

set -e

DB_PATH="./data/cbp_sentry.db"
BACKUP_DIR="./backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

echo "📦 Creating database snapshots..."

# 1. Export schema
sqlite3 "$DB_PATH" ".schema" > "$BACKUP_DIR/schema.sql"
echo "✅ Schema exported"

# 2. Export complete database dump
sqlite3 "$DB_PATH" ".dump" > "$BACKUP_DIR/complete_dump.sql"
echo "✅ Complete dump exported"

# 3. Export table-by-table for selective restore
for table in shipments manifests scores entities; do
    sqlite3 "$DB_PATH" "SELECT * FROM $table;" > "$BACKUP_DIR/${table}_data.csv"
    echo "✅ $table exported"
done

# 4. Document snapshot metadata
cat > "$BACKUP_DIR/SNAPSHOT_METADATA.json" << EOF
{
  "snapshot_date": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "model_version_active": "v2.1",
  "total_shipments": $(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM shipments;"),
  "database_size_bytes": $(stat -c%s "$DB_PATH"),
  "files": {
    "schema": "schema.sql",
    "complete_dump": "complete_dump.sql",
    "shipments_data": "shipments_data.csv"
  }
}
EOF

echo "✅ Snapshot complete: $BACKUP_DIR"

# 5. Commit to git
git add "backups/$(basename $BACKUP_DIR)"
git commit -m "snapshot: Pre-v3.0 database backup (v2.1 legacy)"
git tag -a "v2.1-snapshot-$(date +%Y%m%d)" -m "Database snapshot before v3.0 deployment"

echo "✅ Committed to git with tag"
```

### 3.2 Document Model Metadata

**Objective:** Create versioning records

```python
# File: services/data/schemas/MODEL_VERSIONS.json

{
  "models": [
    {
      "id": "model-v2.1",
      "version": "v2.1",
      "name": "Legacy Rule-Based Model",
      "type": "legacy",
      "status": "frozen",
      "features_count": 72,
      "gates": 3,
      "rules": 8,
      "weight_sum": 1.10,
      "created_date": "2026-05-23",
      "performance": {
        "avg_score": 62.5,
        "min_score": 25.0,
        "max_score": 98.0,
        "hold_rate": 0.27,
        "latency_ms": 50
      },
      "snapshot_path": "backups/20260612_101530/complete_dump.sql",
      "snapshot_date": "2026-06-12T10:15:30Z",
      "notes": "Over-weighted (110% total). Retained for backward compatibility."
    },
    {
      "id": "model-v3.0",
      "version": "v3.0",
      "name": "Precise Risk Model (XGBoost)",
      "type": "precise",
      "status": "active",
      "features_count": 72,
      "gates": 3,
      "rules": 8,
      "weight_sum": 1.0,
      "created_date": "2026-06-12",
      "training": {
        "training_data_size": 10000,
        "test_data_size": 2500,
        "accuracy": 0.92,
        "auc_roc": 0.94,
        "precision": 0.88,
        "recall": 0.90,
        "f1": 0.89
      },
      "performance": {
        "latency_ms": 85,
        "confidence_mean": 0.87,
        "confidence_std": 0.12
      },
      "deployment_path": "services/risk-engine/models/",
      "deployment_date": "2026-06-12T15:00:00Z",
      "notes": "ML-based model with proper weight normalization and uncertainty quantification."
    }
  ],
  "migration_plan": {
    "phase_1_training": "Complete",
    "phase_2_snapshot": "Complete",
    "phase_3_deploy_score": "In Progress",
    "phase_4_validate": "Pending",
    "phase_5_decision": "Pending"
  }
}
```

---

## 4. Phase 3: Deploy & Score

### 4.1 Database Migration

**Objective:** Add versioning infrastructure without data loss

```sql
-- File: services/data/migrations/add_model_versioning.sql

BEGIN TRANSACTION;

-- Add columns to shipments table
ALTER TABLE shipments ADD COLUMN IF NOT EXISTS model_version VARCHAR(50);
ALTER TABLE shipments ADD COLUMN IF NOT EXISTS precise_score FLOAT;
ALTER TABLE shipments ADD COLUMN IF NOT EXISTS model_confidence FLOAT;
ALTER TABLE shipments ADD COLUMN IF NOT EXISTS model_factors JSON;

-- Create model_metadata table
CREATE TABLE IF NOT EXISTS model_metadata (
    id TEXT PRIMARY KEY,
    version TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    features_count INTEGER,
    gates_count INTEGER,
    rules_count INTEGER,
    weight_sum FLOAT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    description TEXT
);

-- Create score_history table
CREATE TABLE IF NOT EXISTS score_history (
    id TEXT PRIMARY KEY,
    shipment_id TEXT NOT NULL,
    model_version TEXT NOT NULL,
    legacy_score FLOAT,
    precise_score FLOAT,
    precise_confidence FLOAT,
    scored_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (shipment_id) REFERENCES shipments(id)
);

-- Default existing shipments to v2.1
UPDATE shipments SET model_version = 'v2.1' WHERE model_version IS NULL;

COMMIT;
```

### 4.2 Rescore All Shipments

See `rescore_shipments_v3.py` created earlier

---

## 5. Phase 4: Monitor & Validate

### 5.1 Monitoring Queries

```sql
-- Score distribution comparison
SELECT 
    'v2.1' as model,
    COUNT(*) as count,
    AVG(risk_score) as avg_score,
    MIN(risk_score) as min_score,
    MAX(risk_score) as max_score,
    STDDEV(risk_score) as stddev_score
FROM shipments
WHERE model_version = 'v2.1'

UNION ALL

SELECT 
    'v3.0' as model,
    COUNT(*) as count,
    AVG(precise_score) as avg_score,
    MIN(precise_score) as min_score,
    MAX(precise_score) as max_score,
    STDDEV(precise_score) as stddev_score
FROM shipments
WHERE model_version = 'v3.0';

-- Classification rate comparison
SELECT 
    CASE 
        WHEN score >= 80 THEN 'HOLD'
        WHEN score >= 50 THEN 'EXAMINE'
        ELSE 'CLEAR'
    END as recommendation,
    COUNT(*) as v2_1_count
FROM shipments
WHERE model_version = 'v2.1'
GROUP BY recommendation

UNION ALL

SELECT 
    CASE 
        WHEN score >= 80 THEN 'HOLD'
        WHEN score >= 50 THEN 'EXAMINE'
        ELSE 'CLEAR'
    END as recommendation,
    COUNT(*) as v3_0_count
FROM shipments
WHERE model_version = 'v3.0'
GROUP BY recommendation;

-- Score changes analysis
SELECT 
    COUNT(*) as total_shipments,
    AVG(precise_score - legacy_score) as avg_score_change,
    MIN(precise_score - legacy_score) as min_change,
    MAX(precise_score - legacy_score) as max_change,
    SUM(CASE WHEN (precise_score - legacy_score) > 10 THEN 1 ELSE 0 END) as increased_by_10_plus,
    SUM(CASE WHEN (precise_score - legacy_score) < -10 THEN 1 ELSE 0 END) as decreased_by_10_plus
FROM score_history
WHERE model_version = 'v3.0';
```

---

## 6. Phase 5: Rollback Procedures

### 6.1 Quick Rollback (Feature Flag)

```bash
# Instant switch via API (no downtime)
curl -X POST http://localhost:8000/api/model/version/switch \
  -H "Content-Type: application/json" \
  -d '{"active_version": "v2.1", "reason": "Critical issue detected"}'

# Response: {"switched_to": "v2.1", "previous_version": "v3.0", "status": "success"}
```

### 6.2 Database Rollback

```bash
#!/bin/bash
# Restore from snapshot if needed

set -e

BACKUP_FILE="backups/20260612_101530/complete_dump.sql"

echo "🔄 Restoring database from snapshot..."

# Stop services
docker-compose down

# Restore backup
rm ./data/cbp_sentry.db
sqlite3 ./data/cbp_sentry.db < "$BACKUP_FILE"

# Restart with legacy model
export MODEL_VERSION_ACTIVE=v2.1
docker-compose up -d

# Verify
curl http://localhost:8000/api/model/version

echo "✅ Database restored to v2.1"
```

### 6.3 Partial Rollback (Keep v3.0 Infrastructure, Use v2.1 Scores)

```sql
-- Revert to legacy scores
UPDATE shipments 
SET precise_score = NULL,
    model_confidence = NULL,
    model_factors = NULL,
    model_version = 'v2.1-reverted'
WHERE model_version = 'v3.0';
```

---

## 7. Success Criteria Checklist

### Phase 1: Training
- [ ] Dataset collected (>10K records recommended)
- [ ] Features validated (72 CBP fields, no missing critical columns)
- [ ] Model trained and cross-validated
- [ ] Performance metrics meet acceptance criteria
  - [ ] AUC-ROC >= 0.85
  - [ ] Accuracy >= 0.80
  - [ ] Inference latency <= 100ms
- [ ] Model artifacts saved and versioned

### Phase 2: Snapshot & Prepare
- [ ] Database snapshot created (schema + data dump)
- [ ] Snapshot verified (can restore successfully)
- [ ] Git tag created for snapshot
- [ ] Model metadata documented
- [ ] Rollback procedures documented and tested

### Phase 3: Deploy & Score
- [ ] Microservice deployed and healthy
- [ ] Database migration applied successfully
- [ ] All shipments rescored with new model
- [ ] Score_history table populated
- [ ] UI displays model version badge
- [ ] No critical errors in logs

### Phase 4: Validate
- [ ] Score distribution documented and acceptable
- [ ] Classification rates (% HOLD, EXAMINE, CLEAR) documented
- [ ] Latency metrics < 100ms
- [ ] Error rate (fallback events) < 1%
- [ ] Stakeholder feedback collected
- [ ] Score changes analyzed and explained

### Phase 5: Decision
- [ ] Performance review meeting completed
- [ ] Decision made: KEEP, ITERATE, or ROLLBACK
- [ ] If ROLLBACK: Verified rollback successful
- [ ] If KEEP: Archive snapshots and document lessons learned

---

## 8. Templates for Future Models

### Template: Model Metadata

```json
{
  "version": "vX.Y",
  "name": "Your Model Name",
  "type": "legacy | precise | ensemble",
  "status": "training | staging | production | archived",
  "features_count": 72,
  "gates_count": 3,
  "rules_count": 8,
  "weight_sum": 1.0,
  "created_date": "YYYY-MM-DD",
  "performance": {
    "accuracy": 0.XX,
    "auc_roc": 0.XX,
    "precision": 0.XX,
    "recall": 0.XX,
    "f1": 0.XX,
    "latency_ms": XX
  },
  "snapshot_path": "backups/TIMESTAMP/",
  "notes": "..."
}
```

### Template: Rollback Script

```bash
#!/bin/bash
# Rollback from v{{new_version}} to v{{old_version}}

set -e

OLD_VERSION={{old_version}}
NEW_VERSION={{new_version}}
SNAPSHOT_FILE={{snapshot_path}}

echo "🔄 Rolling back from $NEW_VERSION to $OLD_VERSION..."

# 1. Switch feature flag
export MODEL_VERSION_ACTIVE=$OLD_VERSION

# 2. (Optional) Restore database if needed
# sqlite3 ./data/cbp_sentry.db < "$SNAPSHOT_FILE"

# 3. Restart services
docker-compose restart sentry-api

# 4. Verify
sleep 5
curl http://localhost:8000/api/model/version

echo "✅ Rollback complete"
```

---

## 9. Key Lessons & Best Practices

### DO:
✅ Always create snapshots before deploying new models  
✅ Use feature flags for safe switchover  
✅ Document model metadata and performance metrics  
✅ Test rollback procedures before production deployment  
✅ Track all scores in audit trail (score_history table)  
✅ Ensure weight factors sum to exactly 1.0 (100%)  
✅ Use version tags in git for easy reference  
✅ Monitor for 24+ hours before final decision  
✅ Keep both models available for easy comparison  

### DON'T:
❌ Deploy without testing rollback first  
❌ Skip database snapshots or backups  
❌ Ignore weight normalization (1.0 vs 1.1)  
❌ Delete old model data immediately  
❌ Make silent changes without versioning  
❌ Assume new model is better without validation  
❌ Forget to document changes in audit trail  
❌ Deploy to production without staging test  

---

## 10. Contacts & Escalation

- **Model Training Issues**: ML Team
- **Database Issues**: Data Engineering
- **Deployment Issues**: DevOps/Platform
- **Production Incidents**: On-Call Engineer + Manager
- **Performance Review**: Product + Analytics + Engineering

---

This guide should be updated with each new model deployment and refined based on lessons learned.
