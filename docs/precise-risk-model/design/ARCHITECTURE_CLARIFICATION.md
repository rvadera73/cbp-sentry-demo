# Architecture Clarification: Precise Risk Model Integration

**Purpose**: Clear decisions on schema, service, versioning, and UI integration  
**Status**: Pre-implementation clarification (awaiting approval)

---

## DECISION 1: DATABASE SCHEMA (Same DB or Separate?)

### OPTION A: Separate Database per Domain (NOT RECOMMENDED)
```
cbp_sentry_cbp
├─ Tables: scorecard, features, model_scores, feedback, etc.

cbp_sentry_fda
├─ Tables: scorecard, features, model_scores, feedback, etc.

cbp_sentry_opioid
├─ Tables: scorecard, features, model_scores, feedback, etc.
```
**Cons**: Replication, migration complexity, separate backups

### OPTION B: Same Database, Separate Schemas (RECOMMENDED) ⭐
```
cbp_sentry (main database)
├─ Schema: public (existing CBP Sentry tables)
├─ Schema: risk_scoring (shared Risk Scoring Engine tables)
│  ├─ Tables: domains, scorecards, rule_parameters, rule_change_events
│  ├─ Table: features (domain_id key)
│  ├─ Table: model_scores (domain_id key)
│  ├─ Table: feedback (domain_id key)
│  ├─ Table: model_training_runs (domain_id key)
│  └─ Table: drift_alerts (domain_id key)
│
└─ Schema: risk_scoring_models (model artifacts metadata)
   ├─ Table: model_versions (xgboost_path, iforest_path, shap_path, deployed)
   └─ Table: model_performance (auc, precision, recall, training_size)

Key constraint: ALL tables have (domain_id, tenant_id) composite key
└─ Prevents data mixing across domains/tenants
```

**Advantages**:
- Single database backup
- Single connection pool
- Shared infrastructure with CBP Sentry
- Easy data isolation via domain_id + tenant_id
- No replication overhead

**Recommendation**: **OPTION B (Same DB, risk_scoring schema)**

---

## DECISION 2: SERVICE ARCHITECTURE (Same Service or Microservice?)

### OPTION A: Monolithic Integration (Risk Scoring Code + CBP Sentry = 1 Service)
```
cbp-sentry-api (Docker container)
├─ Endpoints: /api/shipments, /api/referral, /api/graph (existing)
├─ NEW Endpoints: /api/score/{domain}, /api/feedback, /api/rules (Risk Scoring)
└─ All in same Flask/Python process
```

**Pros**: Simple deployment, shared connection pools  
**Cons**: Single service = coupling, harder to scale Risk Scoring independently

---

### OPTION B: Separate Microservice (Risk Scoring as Independent Service) ⭐ RECOMMENDED
```
cbp-sentry-api (existing service)
├─ Endpoints: /api/shipments, /api/referral, /api/graph
├─ V2AITuningPage (existing)
└─ Calls → precise-risk-engine-service via HTTP

precise-risk-engine-api (new microservice)
├─ Endpoints: /api/score/{domain}/{entity_id}
├─ Endpoints: /api/feedback/{domain}/{entity_id}
├─ Endpoints: /api/model/{domain}/metrics
├─ Endpoints: /api/rules/{domain}
├─ Shared database: cbp_sentry (risk_scoring schema)
└─ Separate Docker container, separate port (e.g., :8004)

Service registry: Consul/Kubernetes DNS
├─ cbp-sentry-api discovers precise-risk-engine-api
└─ Auto-routing, load balancing, failover
```

**Pros**:
- Independent scaling (Risk Scoring can scale 10x, CBP Sentry stays at 1x)
- Clear separation (Risk Scoring logic isolated)
- Reusable (other agencies can deploy just Risk Scoring)
- Multi-tenant ready (one instance serves CBP, FDA, Opioid)
- Easier testing (separate service = separate test suite)

**Cons**:
- Network latency (HTTP call vs in-process)
- Deployment coordination

**Recommendation**: **OPTION B (Separate Microservice)**

---

## DECISION 3: MODEL VERSIONING (Git-Based or DB-Based?)

### OPTION A: Git-Based (My Original Design - NOT RECOMMENDED)
```
Git repository:
├─ cbp_v1.yaml (scorecard definition)
├─ cbp_v2.yaml (scorecard definition)
├─ fda_v1.yaml
└─ Code: feature_engineer.py, model_trainer.py

Issues:
├─ Model artifacts (XGBoost pickle, SHAP) are large (10-100MB)
├─ Can't store pickles in Git (they're binary, non-textual)
├─ Model retraining requires code commit (ceremony, review lag)
└─ Can't A/B test models (no parallel versions in production)
```

---

### OPTION B: Database-Based (RECOMMENDED) ⭐
```
PostgreSQL tables:

scorecards (immutable, code-reviewed)
├─ scorecard_id: 'cbp_v1', 'cbp_v2'
├─ factors: JSON (DOCUMENTATION_RISK: 25%, ...)
├─ rules: JSON ([{ruleId: 'W-121', priority: 1}, ...])
├─ thresholds: JSON ({gate1: 30, gate2: 60, gate3: 80})
├─ git_commit_sha: 'abc123' (links to Git code review)
├─ activated_at, deactivated_at (versioning)
└─ created_by, created_at

model_versions (for training runs)
├─ model_version_id: 'cbp_xgb_v3', 'cbp_iforest_v3'
├─ domain_id: 'cbp'
├─ model_type: 'xgboost' | 'isolation_forest' | 'shap_explainer'
├─ model_path: 's3://bucket/models/cbp/xgboost_v3.pkl'
├─ trained_at, deployed_at
├─ training_size, auc, precision, recall, f1
├─ deployed: true/false
└─ notes: 'Monthly retrain, 1,250 cases'

model_training_runs (audit log)
├─ training_id
├─ domain_id
├─ scorecard_version: 'cbp_v1'
├─ xgboost_version: 'cbp_xgb_v3'
├─ iforest_version: 'cbp_iforest_v3'
├─ training_start, training_end
├─ training_sample_size: 1537
├─ auc: 0.89
├─ deployed: true/false
└─ approved_by: 'supervisor@cbp.gov'

Git only stores:
├─ Code: feature_engineer.py, model_trainer.py
├─ Scorecard configs: cbp.yaml, fda.yaml, opioid.yaml (immutable policy)
└─ No model artifacts in Git
```

**Advantages**:
- Model versions are queryable (temporal: "which model was active on July 15?")
- Can retrain monthly without code commit
- Can A/B test models (deploy v3, keep v2 for fallback)
- Model artifact (pickle) is in S3, metadata in DB
- Full audit trail of training runs

**Recommendation**: **OPTION B (DB-Based)**

---

## DECISION 4: MULTI-TENANT DESIGN (For Future Scalability)

### Current (v1): Single Tenant
```
Precise Risk Model serves only CBP (for now)

Database structure:
├─ Tables have domain_id (cbp, fda, opioid)
├─ No tenant_id column yet (implicit: always CBP)
└─ Query: SELECT * FROM model_scores WHERE domain_id = 'cbp'
```

### Future (v2): Multi-Tenant Ready
```
When you want to serve multiple agencies (CBP, FDA, DHS, etc.):

Database structure:
├─ Tables have (tenant_id, domain_id) composite key
├─ Tenant 1 (CBP): tenant_id=1, domains=[cbp, fraud_detection]
├─ Tenant 2 (FDA): tenant_id=2, domains=[fda_imports]
├─ Tenant 3 (DEA): tenant_id=3, domains=[opioid]
└─ Query: SELECT * FROM model_scores WHERE tenant_id = 1 AND domain_id = 'cbp'

API routing:
├─ Request header: X-Tenant-ID: 1
├─ API extracts tenant_id from request
├─ Queries filtered by (tenant_id, domain_id)
└─ Prevents cross-tenant data leakage
```

**For now**: Keep schema multi-tenant ready, but assume tenant_id = 1 (CBP Sentry)

**Recommendation**: **Design for multi-tenant (add tenant_id column), but deploy single-tenant (tenant_id=1)**

---

## DECISION 5: NO HARDCODING - Full Configuration-Driven

### OPTION A: Hardcoded Features (BAD - Current Risk Model Risk)
```python
# risk_scoring_engine.py (HARDCODED FOR CBP)

def score_cbp_shipment(shipment):
    doc_risk = _score_documentation_risk(shipment) * 0.25  # Hardcoded 25%
    routing_risk = _score_routing_risk(shipment) * 0.15    # Hardcoded 15%
    # ... 5 more hardcoded factors
    # ... 8 hardcoded rules
    # ... 3 hardcoded gates
    return final_score

# To add FDA: Duplicate entire function with FDA logic (code duplication)
```

**Problem**: FDA and Opioid require copies of this function with different logic

---

### OPTION B: Configuration-Driven (RECOMMENDED) ⭐
```python
# model.py (GENERIC, NO HARDCODING)

class PreciseRiskModel:
    def __init__(self, domain: str, config: Dict):
        self.domain = domain  # 'cbp', 'fda', 'opioid'
        self.config = config  # Loaded from DB/file
        self.factors = config['factors']  # [{id, weight}, ...]
        self.rules = config['rules']      # [{id, condition}, ...]
        self.thresholds = config['thresholds']  # {gate1: 30, ...}
        self.xgb_model = load_model(config['xgb_model_path'])
        self.iforest_model = load_model(config['iforest_model_path'])
    
    def score(self, entity: Dict) -> Score:
        """Generic scoring logic - works for any domain"""
        
        # Gate 1: Rules (generic)
        rules_score = self._apply_rules(entity)
        
        # Gate 2: ML (generic)
        ml_score = self._apply_ml_model(entity)
        
        # Gate 3: Uncertainty (generic)
        confidence = self._calibrate_confidence(ml_score)
        
        return Score(raw_score=ml_score, confidence=confidence, ...)
    
    def _apply_rules(self, entity: Dict) -> float:
        """Generic rule application - iterates through self.rules"""
        score = 0
        for rule in self.rules:  # Loaded from config
            if self._evaluate_condition(rule['condition'], entity):
                score += rule['base_points'] * self._get_parameter(rule['id'], 'weight')
        return score
    
    # ... Generic methods that work for any domain

# main.py
cbp_model = PreciseRiskModel(
    domain='cbp',
    config=load_config_from_db('cbp')  # Loads factors, rules, thresholds from DB
)

fda_model = PreciseRiskModel(
    domain='fda',
    config=load_config_from_db('fda')  # Different factors, rules, thresholds
)

# Same code, different configs. Zero duplication.
```

**Advantages**:
- One codebase serves all domains
- New domain = new config in DB (no code change)
- Easy to A/B test factors/rules (change config, no redeployment)
- Truly reusable (other agencies copy the service, plug in their config)

**Recommendation**: **OPTION B (Configuration-Driven)**

---

## DECISION 6: UI INTEGRATION (V2AITuningPage)

### Current State
```
V2AITuningPage (existing component)
├─ Manages factor weights (sliders)
├─ Manages rule toggles (checkboxes)
├─ Manages configuration thresholds
└─ Calls APIs: /api/model/weights, /api/rules/save
```

### New Integration
```
V2AITuningPage (enhanced)
├─ Domain selector dropdown (cbp, fda, opioid)
├─ Tab 1: Model Weights (sliders) → calls Precise Risk Engine
│  └─ GET /api/risk-engine/model/{domain}/weights
│  └─ POST /api/risk-engine/model/{domain}/weights
├─ Tab 2: Screening Rules (checkboxes) → calls Precise Risk Engine
│  └─ GET /api/risk-engine/rules/{domain}
│  └─ POST /api/risk-engine/rules/{domain}/{rule_id}/parameter
├─ Tab 3: Configuration (thresholds) → calls Precise Risk Engine
│  └─ GET /api/risk-engine/config/{domain}
│  └─ POST /api/risk-engine/config/{domain}
├─ Tab 4: Performance Metrics → calls Precise Risk Engine
│  └─ GET /api/risk-engine/model/{domain}/metrics
└─ Tab 5: Active Learning (NEW)
   └─ GET /api/risk-engine/uncertain-cases/{domain}
   └─ POST /api/risk-engine/feedback/{domain}/{entity_id}

Architecture:
├─ V2AITuningPage (React, existing UI)
├─ Calls → precise-risk-engine-api (Flask microservice, new)
├─ Database: cbp_sentry.risk_scoring schema (shared PostgreSQL)
└─ No changes to CBP Sentry's core logic (shipment ingestion, referral package)
```

**Benefits**:
- Single UI for all domains (switch domain = switch models)
- Precise Risk Engine is pluggable (can be replaced without touching UI)
- UI stays thin (just API calls)
- Easy to add new domain (new config in DB, no UI code change)

---

## SUMMARY: FINAL ARCHITECTURE DECISIONS

```
Database:
├─ Same: cbp_sentry PostgreSQL (shared with CBP Sentry)
├─ New schema: risk_scoring (isolated from public schema)
└─ Design for multi-tenant (add tenant_id column), but deploy single-tenant

Service:
├─ New microservice: precise-risk-engine-api (port 8004, separate container)
├─ Shared database: cbp_sentry.risk_scoring schema
├─ Called by: cbp-sentry-api and V2AITuningPage
└─ Independent scaling, reusable, multi-tenant ready

Model Versioning:
├─ Scorecards (factors, rules, thresholds): Database (immutable, versioned)
├─ Model artifacts (XGBoost, Isolation Forest, SHAP): S3 (linked from DB)
├─ Training metadata: Database (audit trail, versioning)
└─ Code (feature engineering, training logic): Git (code review)

No Hardcoding:
├─ All configs loaded from database at runtime
├─ One codebase serves CBP, FDA, Opioid, future domains
├─ Domain separation via domain_id + tenant_id
└─ Zero code duplication across domains

UI Integration:
├─ V2AITuningPage enhanced (domain selector + Active Learning tab)
├─ Calls Precise Risk Engine microservice APIs
├─ No changes to existing CBP Sentry logic
└─ Easy to add new domain (new config, no UI code)
```

---

## IMPLEMENTATION: Same CBP Sentry Platform

```
Current CBP Sentry structure:
├─ services/api/ (Python Flask)
│  ├─ routes/shipments.py
│  ├─ routes/referral.py
│  ├─ routes/graph.py
│  └─ services/risk_scoring_engine.py (to be refactored)
├─ ui/src/v2/pages/V2AITuningPage.tsx
└─ database.sql (PostgreSQL schema)

New structure:
├─ services/api/ (cbp-sentry-api, existing)
├─ services/risk-engine/ (NEW MICROSERVICE, separate container)
│  ├─ app.py (Flask)
│  ├─ routes/scoring.py
│  ├─ routes/rules.py
│  ├─ routes/feedback.py
│  ├─ routes/metrics.py
│  ├─ models/precise_risk_model.py (generic, config-driven)
│  ├─ models/model_trainer.py (retraining pipeline)
│  ├─ services/drift_detector.py
│  ├─ services/active_learner.py
│  └─ config/ (domain configs: cbp.yaml, fda.yaml, opioid.yaml)
├─ ui/src/v2/pages/V2AITuningPage.tsx (enhanced with domain selector)
└─ database.sql (add risk_scoring schema)

Deployment:
├─ Docker: cbp-sentry-api (port 8000)
├─ Docker: risk-engine-api (port 8004) ← NEW
├─ RDS: PostgreSQL cbp_sentry (shared)
├─ ElastiCache: Redis (shared)
└─ S3: Model artifacts (shared)
```

---

## DECISION 7: MULTI-LEVEL FACTOR SCORING OVER A RESOLVED-ENTITY GRAPH (v4.0)

**Status: Provisional** — scoring synthesis + lifecycle decided; aggregation/apportionment locked; data-readiness items open. Full record: `decisions/DECISION_MULTI_LEVEL_FACTOR_SCORING.md`.

- Corridor (H1) and Entity (H2) each get their own `RiskScoreBreakdown` from the **same 7-factor recipe** as the shipment scorer; the factor breakdown is the inter-horizon navigation (party-risk → H2, time/incoming → H3).
- **One resolved-entity graph** underneath: contributions = edge weights, horizon scores = node aggregates (prevents cross-corridor double-counting).
- **Locked:** aggregation = **top-k blend** (k≈5); apportionment = **by shipment count**.
- **Registry:** v4.0 = a **single bundled version** (factor weights + calibrators + XGBoost + locked params + **CORD resolution snapshot** + feature-pipeline version). Same train→register→gate→promote lifecycle.
- **Data-readiness gate (OPEN, blocks H2):** onboard **CBP-EAPA** and **UFLPA Entity List** (both absent from CORD); materialize relationship→edges; exclude NPI/GLOBALDATA from scoring.
- **Referral package = primary consumer** of the H2 score (renders factor-attributed entity risk, OFAC, EAPA anchor, network); same v4.0 program.

---

## Questions for Clarification

**Before we finalize, confirm:**

1. ✅ **Same DB, different schema** (risk_scoring schema in cbp_sentry)?
2. ✅ **Separate microservice** (precise-risk-engine-api)?
3. ✅ **DB-based model versioning** (no pickles in Git)?
4. ✅ **Configuration-driven** (no hardcoding)?
5. ✅ **Multi-tenant ready, single-tenant deployed** (tenant_id column, but tenant_id=1)?
6. ✅ **V2AITuningPage calls microservice APIs** (not embedded logic)?
7. 🔶 **v4.0 multi-level factor scoring** (single bundled version; EAPA/UFLPA onboarding gate before H2) — see DECISION 7.

**If all approved**, next step: Rewrite PRECISE_RISK_MODEL_COMPLETE_DESIGN.md with these decisions baked in.

