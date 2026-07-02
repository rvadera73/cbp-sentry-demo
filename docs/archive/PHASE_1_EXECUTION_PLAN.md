# Phase 1 Execution Plan - Precise Risk Model

**Status**: Ready for Implementation  
**Timeline**: 4 weeks (Weeks of June 12-July 10, 2026)  
**Team**: 2 Backend Engineers + 1 ML Engineer + 1 DevOps  

---

## WEEK 1: FOUNDATION (Data Validation + Infrastructure)

### Task 1.1: Data Validation (3 days)
**Owner**: Data Engineer / ML Engineer  
**Deliverable**: training_data.csv (10,287 samples)

```bash
# Location: /home/rahulvadera/cbp-sentry/data/training_data.csv

Steps:
1. Locate EAPA dataset
   - Check: /home/rahulvadera/cbp-sentry/data/ for existing files
   - Check: Database cbp_sentry for EAPA table
   - Verify: 287 confirmed transshipment cases

2. Load EAPA cases (positive class, label=1)
   - Extract: All 287 EAPA cases with required fields
   - Required fields: entity_id, shipment_date, origin, destination, hs_code, quantity, value, importer, shipper
   - Check: No missing critical fields
   - Validate: Data types match expectations

3. Sample 10K non-EAPA manifests (negative class, label=0)
   - Source: CBP Sentry manifest table
   - Filter: Non-EAPA cases (where eapa_case_id IS NULL)
   - Sample: Random 10K from non-EAPA pool
   - Stratification: Maintain realistic distribution (by date, origin, commodity)

4. Create training dataset
   - Combine: 287 EAPA + 10K non-EAPA = 10,287 total
   - Format: CSV with columns: entity_id, features (raw), label, data_source, date_collected
   - Save to: /home/rahulvadera/cbp-sentry/data/training_data.csv

5. Create metadata
   - File: /home/rahulvadera/cbp-sentry/data/training_metadata.json
   - Content: 
     {
       "total_samples": 10287,
       "positive_cases": 287,
       "negative_cases": 10000,
       "class_balance_pct": 2.79,
       "date_created": "2026-06-12",
       "eapa_source": "CBP transshipment database",
       "manifest_source": "cbp_sentry.manifests table",
       "train_test_split": "70/30",
       "required_fields": [...]
     }
```

**Success Criteria**:
- ✅ 10,287 samples loaded
- ✅ 287 positive (EAPA), 10K negative (manifests)
- ✅ No missing critical fields
- ✅ training_data.csv created
- ✅ training_metadata.json created

---

### Task 1.2: PostgreSQL Schema Setup (2 days)
**Owner**: Backend Engineer / DevOps  
**Deliverable**: risk_scoring schema with 12 tables

```sql
-- Location: /home/rahulvadera/cbp-sentry/schema/risk_scoring_schema.sql

CREATE SCHEMA risk_scoring;

-- Table 1: Domains
CREATE TABLE risk_scoring.domains (
  domain_id VARCHAR(50) PRIMARY KEY,
  name VARCHAR(255),
  description TEXT,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Table 2: Scorecards (factor weights, rules, thresholds)
CREATE TABLE risk_scoring.scorecards (
  scorecard_id VARCHAR(100) PRIMARY KEY,
  domain_id VARCHAR(50) REFERENCES risk_scoring.domains(domain_id),
  factors JSONB,  -- {DOCUMENTATION_RISK: {weight: 0.25}, ...}
  rules JSONB,    -- [{rule_id: W-121, name: OFAC_MATCH, condition: ...}, ...]
  thresholds JSONB,  -- {gate1: 30, gate2: 60, gate3: 80}
  git_commit_sha VARCHAR(40),
  activated_at TIMESTAMP,
  deactivated_at TIMESTAMP,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Table 3: Features (CBP)
CREATE TABLE risk_scoring.features_cbp (
  feature_id VARCHAR(100) PRIMARY KEY,
  feature_name VARCHAR(255),
  feature_description TEXT,
  factor_category VARCHAR(50),  -- DOCUMENTATION_RISK, ROUTING_RISK, etc.
  data_type VARCHAR(50),  -- numeric, binary, categorical
  created_at TIMESTAMP DEFAULT NOW()
);

-- Table 4: Rule Parameters (SCD Type 2)
CREATE TABLE risk_scoring.rule_parameters (
  parameter_id SERIAL PRIMARY KEY,
  rule_id VARCHAR(50),
  domain_id VARCHAR(50) REFERENCES risk_scoring.domains(domain_id),
  parameter_name VARCHAR(100),
  parameter_value FLOAT,
  valid_from TIMESTAMP,
  valid_to TIMESTAMP,
  created_by VARCHAR(100),
  created_at TIMESTAMP DEFAULT NOW()
);

-- Table 5: Rule Change Events (audit log)
CREATE TABLE risk_scoring.rule_change_events (
  event_id SERIAL PRIMARY KEY,
  rule_id VARCHAR(50),
  domain_id VARCHAR(50) REFERENCES risk_scoring.domains(domain_id),
  change_type VARCHAR(50),  -- INSERT, UPDATE, DELETE
  old_value JSONB,
  new_value JSONB,
  changed_by VARCHAR(100),
  changed_at TIMESTAMP DEFAULT NOW()
);

-- Table 6: Model Scores
CREATE TABLE risk_scoring.model_scores (
  score_id SERIAL PRIMARY KEY,
  entity_id VARCHAR(100),
  domain_id VARCHAR(50) REFERENCES risk_scoring.domains(domain_id),
  risk_score FLOAT,
  confidence FLOAT,
  explanation JSONB,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Table 7: Feedback (analyst labels for active learning)
CREATE TABLE risk_scoring.feedback (
  feedback_id SERIAL PRIMARY KEY,
  entity_id VARCHAR(100),
  domain_id VARCHAR(50) REFERENCES risk_scoring.domains(domain_id),
  analyst_label INT,  -- 0 or 1
  analyst_confidence FLOAT,
  notes TEXT,
  created_by VARCHAR(100),
  created_at TIMESTAMP DEFAULT NOW()
);

-- Table 8: Model Training Runs
CREATE TABLE risk_scoring.model_training_runs (
  training_id SERIAL PRIMARY KEY,
  domain_id VARCHAR(50) REFERENCES risk_scoring.domains(domain_id),
  scorecard_version VARCHAR(50),
  xgboost_version VARCHAR(50),
  iforest_version VARCHAR(50),
  training_start TIMESTAMP,
  training_end TIMESTAMP,
  training_sample_size INT,
  auc FLOAT,
  precision FLOAT,
  recall FLOAT,
  f1_score FLOAT,
  deployed BOOLEAN DEFAULT FALSE,
  deployed_at TIMESTAMP,
  approved_by VARCHAR(100),
  created_at TIMESTAMP DEFAULT NOW()
);

-- Table 9: Drift Alerts
CREATE TABLE risk_scoring.drift_alerts (
  alert_id SERIAL PRIMARY KEY,
  domain_id VARCHAR(50) REFERENCES risk_scoring.domains(domain_id),
  feature_name VARCHAR(100),
  ks_statistic FLOAT,
  p_value FLOAT,
  detected_at TIMESTAMP,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Table 10: Model Versions (GCP metadata)
CREATE TABLE risk_scoring.model_versions (
  model_version_id VARCHAR(50) PRIMARY KEY,
  domain_id VARCHAR(50) REFERENCES risk_scoring.domains(domain_id),
  model_type VARCHAR(50),  -- xgboost, isolation_forest, shap_explainer
  model_path VARCHAR(255),  -- gs://bucket/path/to/model
  trained_at TIMESTAMP,
  deployed_at TIMESTAMP,
  auc FLOAT,
  precision FLOAT,
  recall FLOAT,
  deployed BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Insert CBP domain
INSERT INTO risk_scoring.domains (domain_id, name, description) VALUES
('cbp', 'CBP Illegal Transshipment Detection', 'Detect misdeclared shipments and transshipment fraud');
```

**Success Criteria**:
- ✅ risk_scoring schema created
- ✅ All 10 tables created (12 with staging tables)
- ✅ Foreign keys and constraints in place
- ✅ CBP domain registered
- ✅ SQL script version controlled

---

### Task 1.3: GCP Cloud Storage Setup (1 day)
**Owner**: DevOps  
**Deliverable**: GCP bucket gs://cbp-sentry-models/

```bash
# Location: /home/rahulvadera/cbp-sentry/config/gcp_setup.sh

# Create GCP bucket (if not exists)
gsutil mb gs://cbp-sentry-models/

# Create subdirectories for models
gsutil -m mkdir gs://cbp-sentry-models/cbp/xgboost/
gsutil -m mkdir gs://cbp-sentry-models/cbp/isolation_forest/
gsutil -m mkdir gs://cbp-sentry-models/cbp/shap_explainer/

# Set lifecycle policy (keep 5 versions, auto-delete after 90 days)
# (Optional, configure as needed)

# Test upload
echo "test" | gsutil cp - gs://cbp-sentry-models/test.txt
```

**Success Criteria**:
- ✅ Bucket gs://cbp-sentry-models/ exists
- ✅ Subdirectories created (xgboost, isolation_forest, shap_explainer)
- ✅ Upload/download tested
- ✅ Credentials configured

---

### Task 1.4: Redis Cache Setup (1 day)
**Owner**: DevOps  
**Deliverable**: Redis instance configured

```python
# Location: /home/rahulvadera/cbp-sentry/services/risk-engine/services/cache_service.py

import redis
import json
import os

class CacheService:
    def __init__(self):
        self.redis_client = redis.Redis(
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', 6379)),
            db=int(os.getenv('REDIS_DB', 0)),
            decode_responses=True
        )
    
    def get(self, key):
        value = self.redis_client.get(key)
        return json.loads(value) if value else None
    
    def set(self, key, value, ttl=604800):  # 7 days default
        self.redis_client.setex(key, ttl, json.dumps(value))
    
    def invalidate(self, domain, entity_id):
        key = f"risk_score:{domain}:{entity_id}"
        self.redis_client.delete(key)
    
    def health_check(self):
        return self.redis_client.ping()
```

**Success Criteria**:
- ✅ Redis instance running
- ✅ Connection test passes (PING)
- ✅ CacheService implementation complete
- ✅ TTL and key format documented

---

## WEEK 2: FEATURE ENGINEERING

### Task 2.1: Build 72 CBP Features (5 days)
**Owner**: ML Engineer  
**Deliverable**: feature_matrix.npy (10,287 x 72)

```python
# Location: /home/rahulvadera/cbp-sentry/data/feature_engineering.py

import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler

def engineer_documentation_risk_features(df):
    """12 features: ISF completeness, Element 9, manifest accuracy, etc."""
    features = pd.DataFrame()
    features['isf_completeness_score'] = df['isf_filled_fields'] / df['total_isf_fields'] * 100
    features['element_9_consistency'] = (df['element_9_matches_manifest'] * 100)
    features['manifest_accuracy_score'] = df['manifest_accuracy']
    features['missing_field_count'] = df['missing_fields_count']
    features['error_rate_pct'] = df['errors'] / df['total_records'] * 100
    features['document_age_days'] = (pd.Timestamp.now() - df['document_date']).dt.days
    features['importer_documentation_history'] = df['importer_doc_score']
    features['declarant_reliability_score'] = df['declarant_reliability']
    features['submission_completeness'] = df['submission_complete'] * 100
    features['historical_violation_count'] = df['importer_violations']
    features['amendment_frequency'] = df['amendment_count']
    features['document_type_mismatch'] = df['doc_type_mismatch'].astype(int)
    return features

def engineer_routing_risk_features(df):
    """10 features: AIS dwell, port risk, vessel flag, etc."""
    features = pd.DataFrame()
    features['ais_dwell_anomaly'] = df['dwell_zscore'].abs() > 2.5
    features['dwell_time_zscore'] = df['dwell_zscore']
    features['port_selection_risk'] = df['port_risk_score']
    features['vessel_flag_risk'] = df['vessel_flag_risk']
    features['port_pair_frequency'] = df['port_pair_count']
    features['routing_deviation_from_normal'] = df['routing_zscore']
    features['unusual_intermediate_ports'] = df['intermediate_port_count']
    features['vessel_age_years'] = df['vessel_age']
    features['vessel_size_anomaly'] = df['vessel_size_zscore']
    features['arrival_timing_anomaly'] = df['arrival_timing_anomaly'].astype(int)
    return features

# ... More feature engineering functions for remaining 5 factors ...

def build_feature_matrix(training_data_file):
    """Build complete 72-feature matrix"""
    df = pd.read_csv(training_data_file)
    
    features_list = []
    features_list.append(engineer_documentation_risk_features(df))  # 12 features
    features_list.append(engineer_routing_risk_features(df))  # 10 features
    # ... add remaining 5 factor groups ...
    
    feature_matrix = pd.concat(features_list, axis=1)
    
    # Standardize
    scaler = StandardScaler()
    feature_matrix_scaled = scaler.fit_transform(feature_matrix)
    
    # Save
    np.save('/home/rahulvadera/cbp-sentry/data/feature_matrix.npy', feature_matrix_scaled)
    feature_matrix.to_csv('/home/rahulvadera/cbp-sentry/data/feature_matrix.csv')
    
    return feature_matrix_scaled

# Run
if __name__ == '__main__':
    X = build_feature_matrix('/home/rahulvadera/cbp-sentry/data/training_data.csv')
    print(f"Feature matrix shape: {X.shape}")  # Expected: (10287, 72)
```

**Success Criteria**:
- ✅ All 72 features implemented
- ✅ Feature matrix shape: (10,287 x 72)
- ✅ No null values (or imputation strategy applied)
- ✅ feature_matrix.npy saved
- ✅ Correlation analysis: max < 0.95
- ✅ Feature definitions documented

---

## WEEK 3: MODEL TRAINING

### Task 3.1: Train XGBoost + Isolation Forest + SHAP (5 days)
**Owner**: ML Engineer  
**Deliverable**: Trained models + metrics

```python
# Location: /home/rahulvadera/cbp-sentry/models/train_models.py

import xgboost as xgb
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import roc_auc_score, precision_score, recall_score, f1_score
import shap
import pickle

def train_xgboost(X_train, y_train, X_test, y_test):
    """Train XGBoost classifier on EAPA dataset"""
    
    # Handle class imbalance
    scale_pos_weight = (y_train == 0).sum() / (y_train == 1).sum()  # ~35
    
    model = xgb.XGBClassifier(
        n_estimators=100,
        max_depth=6,
        learning_rate=0.1,
        subsample=0.8,
        colsample_bytree=0.8,
        scale_pos_weight=scale_pos_weight,
        random_state=42,
        verbosity=1
    )
    
    # Train
    model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=False)
    
    # Evaluate
    y_pred_proba = model.predict_proba(X_test)[:, 1]
    auc = roc_auc_score(y_test, y_pred_proba)
    precision = precision_score(y_test, model.predict(X_test))
    recall = recall_score(y_test, model.predict(X_test))
    f1 = f1_score(y_test, model.predict(X_test))
    
    print(f"XGBoost - AUC: {auc:.4f}, Precision: {precision:.4f}, Recall: {recall:.4f}, F1: {f1:.4f}")
    
    # Save
    with open('/home/rahulvadera/cbp-sentry/models/xgboost_cbp_v1.pkl', 'wb') as f:
        pickle.dump(model, f)
    
    return model, {'auc': auc, 'precision': precision, 'recall': recall, 'f1': f1}

def train_isolation_forest(X_train, X_test):
    """Train Isolation Forest for anomaly detection"""
    model = IsolationForest(n_estimators=100, contamination=0.03, random_state=42)
    model.fit(X_train)
    
    # Anomaly scores
    anomaly_scores_test = model.decision_function(X_test)
    print(f"Isolation Forest - Anomalies detected: {(anomaly_scores_test < 0).sum()}")
    
    # Save
    with open('/home/rahulvadera/cbp-sentry/models/iforest_cbp_v1.pkl', 'wb') as f:
        pickle.dump(model, f)
    
    return model

def generate_shap_explainer(model, X_sample):
    """Generate SHAP explainer for interpretability"""
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X_sample)
    
    # Save
    with open('/home/rahulvadera/cbp-sentry/models/shap_cbp_v1.pkl', 'wb') as f:
        pickle.dump(explainer, f)
    
    return explainer, shap_values

def main():
    # Load data
    X = np.load('/home/rahulvadera/cbp-sentry/data/feature_matrix.npy')
    y = pd.read_csv('/home/rahulvadera/cbp-sentry/data/training_data.csv')['label'].values
    
    # Split (70/30, stratified)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.3, random_state=42, stratify=y
    )
    
    # Train XGBoost
    xgb_model, xgb_metrics = train_xgboost(X_train, y_train, X_test, y_test)
    
    # Train Isolation Forest
    iforest_model = train_isolation_forest(X_train, X_test)
    
    # Generate SHAP
    X_sample = X_test[:100]  # Sample for explanations
    explainer, shap_values = generate_shap_explainer(xgb_model, X_sample)
    
    print("✅ Model training complete")

if __name__ == '__main__':
    main()
```

**Success Criteria**:
- ✅ XGBoost AUC ≥ 0.82
- ✅ Precision ≥ 0.30
- ✅ Recall ≥ 0.70
- ✅ All 3 models saved (.pkl files)
- ✅ SHAP explainer working
- ✅ Training metadata recorded

---

### Task 3.2: Build precise-risk-engine-api Microservice (5 days)
**Owner**: Backend Engineer  
**Deliverable**: Flask microservice skeleton

```python
# Location: /home/rahulvadera/cbp-sentry/services/risk-engine/app.py

from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from dotenv import load_dotenv

load_dotenv()

def create_app():
    app = Flask(__name__)
    CORS(app)
    
    # Register blueprints
    from routes.scoring import scoring_bp
    from routes.rules import rules_bp
    from routes.feedback import feedback_bp
    from routes.metrics import metrics_bp
    
    app.register_blueprint(scoring_bp, url_prefix='/api')
    app.register_blueprint(rules_bp, url_prefix='/api')
    app.register_blueprint(feedback_bp, url_prefix='/api')
    app.register_blueprint(metrics_bp, url_prefix='/api')
    
    # Health check
    @app.route('/health', methods=['GET'])
    def health():
        return jsonify({'status': 'healthy'}), 200
    
    # Error handlers
    @app.errorhandler(400)
    def bad_request(e):
        return jsonify({'error': 'Bad request'}), 400
    
    @app.errorhandler(404)
    def not_found(e):
        return jsonify({'error': 'Not found'}), 404
    
    @app.errorhandler(500)
    def internal_error(e):
        return jsonify({'error': 'Internal server error'}), 500
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=8004, debug=False)
```

```python
# Location: /home/rahulvadera/cbp-sentry/services/risk-engine/routes/scoring.py

from flask import Blueprint, request, jsonify
from models.precise_risk_model import PreciseRiskModel
from services.cache_service import CacheService

scoring_bp = Blueprint('scoring', __name__)
cache_service = CacheService()

@scoring_bp.route('/score/<domain>/<entity_id>', methods=['POST'])
def score_entity(domain, entity_id):
    """Score an entity using the specified domain model"""
    try:
        entity = request.get_json()
        
        # Check cache
        cached = cache_service.get(f'risk_score:{domain}:{entity_id}')
        if cached:
            return jsonify(cached), 200
        
        # Load model
        model = PreciseRiskModel(domain=domain)
        
        # Score
        result = model.score(entity)
        
        # Cache
        cache_service.set(f'risk_score:{domain}:{entity_id}', result)
        
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@scoring_bp.route('/explain/<domain>/<entity_id>', methods=['GET'])
def explain_score(domain, entity_id):
    """Get SHAP explanation for entity score"""
    try:
        model = PreciseRiskModel(domain=domain)
        explanation = model.explain(entity_id)
        return jsonify(explanation), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400
```

**Success Criteria**:
- ✅ Flask app runs on port 8004
- ✅ All 4 blueprints (scoring, rules, feedback, metrics) implemented
- ✅ CBP config loaded
- ✅ Basic tests pass
- ✅ Dockerfile builds

---

## WEEK 4: INTEGRATION & DEPLOYMENT

### Task 4.1: Integrate Models + Deploy (5 days)
**Owner**: Backend Engineer + DevOps  
**Deliverable**: Live API endpoint

```bash
# Location: /home/rahulvadera/cbp-sentry/services/risk-engine/Dockerfile

FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8004

CMD ["gunicorn", "--bind", "0.0.0.0:8004", "--workers", "4", "app:app"]
```

**Steps**:
1. Integrate trained models into PreciseRiskModel class
2. Upload models to GCP Cloud Storage
3. Build Docker image: `docker build -t gcr.io/cbp-sentry/risk-engine:v1 .`
4. Push to registry: `docker push gcr.io/cbp-sentry/risk-engine:v1`
5. Deploy to GCP Cloud Run or ECS
6. Run end-to-end tests
7. Register models in database

**Success Criteria**:
- ✅ Models integrated
- ✅ Docker deployed
- ✅ API responding on live endpoint
- ✅ Health check passing
- ✅ Integration tests passing
- ✅ AUC ≥ 0.82 verified

---

## DELIVERABLES SUMMARY

| Week | Deliverable | Owner | Status |
|------|-------------|-------|--------|
| 1 | training_data.csv (10,287 samples) | Data Eng | TBD |
| 1 | risk_scoring schema (12 tables) | Backend | TBD |
| 1 | GCP bucket gs://cbp-sentry-models/ | DevOps | TBD |
| 1 | Redis instance configured | DevOps | TBD |
| 2 | feature_matrix.npy (10,287 x 72) | ML Eng | TBD |
| 3 | xgboost_cbp_v1.pkl (AUC ≥ 0.82) | ML Eng | TBD |
| 3 | precise-risk-engine-api (port 8004) | Backend | TBD |
| 4 | Live API endpoint (deployed) | Backend + DevOps | TBD |

---

## GO/NO-GO CHECKPOINTS

**Week 2 (Friday EOD)**: Data Sufficiency Gate
- [ ] training_data.csv verified (10,287 samples, 2.8% positive)
- [ ] Feature matrix shape correct (10,287 x 72)
- [ ] Decision: PROCEED to Week 3 or escalate

**Week 4 (Friday EOD)**: Model Quality Gate
- [ ] XGBoost AUC ≥ 0.82 verified
- [ ] Integration tests passing
- [ ] API deployed and responding
- [ ] Decision: GO to Phase 2 or remediate

---

## NEXT STEPS

1. **Assign team members** to each task
2. **Create Jira/Task tickets** for each deliverable
3. **Set up daily standups** (15 min)
4. **Create Slack channel** for Phase 1 updates
5. **Schedule Week 2 & Week 4 decision gates** with stakeholders

Ready to start? Begin with **Task 1.1: Data Validation**
