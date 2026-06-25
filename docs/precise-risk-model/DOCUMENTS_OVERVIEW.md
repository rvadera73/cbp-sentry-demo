# Precise Risk Model: Documents Overview

**Two Key Documents for Team Review**

---

## DOCUMENT 1: PRECISE_RISK_MODEL_COMPLETE_DESIGN.md
**Purpose**: Complete technical architecture & specifications  
**Audience**: Architects, engineers, technical leads  
**Length**: ~50 pages (10 detailed sections)

### What's In It:

#### PART 1: Architecture Overview
- **System Diagram**: End-to-end data flow (ingest → scoring → decision)
- **Technology Stack**: Python, PostgreSQL, Redis, GCP Storage, XGBoost, Isolation Forest, SHAP
- **Data Flow**: Entity ingest → Feature Store → Scoring → Cache → Decision Store → Retraining

#### PART 2: Core Data Model (PostgreSQL)
- **12 Tables** with complete schema definitions:
  - `domains` (cbp, fda, opioid)
  - `scorecards` (factors, rules, thresholds per domain)
  - `features_cbp / features_fda / features_opioid` (domain-isolated)
  - `rule_parameters` (SCD Type 2 versioning)
  - `rule_change_events` (immutable audit log)
  - `model_scores` (immutable, timestamped)
  - `feedback` (analyst labels for active learning)
  - `model_training_runs` (training metadata)
  - `drift_alerts` (auto-triggered)
  - `model_versions` (GCP Storage metadata)

- **Redis Cache Structure**: Key format, TTL, invalidation strategy

#### PART 3: Scoring Engine Architecture (3-Gate Model)
- **Gate 1**: Deterministic Rules
  - Manual rules (OFAC, Element 9)
  - Data-driven thresholds (percentiles)
  - Anomaly detection (Isolation Forest)

- **Gate 2**: ML Classification
  - XGBoost model (72 features)
  - Confidence calibration
  - SHAP explanations

- **Gate 3**: Uncertainty Quantification
  - Bayesian Network (future)
  - Confidence intervals

#### PART 4: Feature Engineering (Domain-Specific)
- **CBP Features** (72 total):
  - DOCUMENTATION_RISK: ISF completeness, Element 9, manifest accuracy
  - ROUTING_RISK: AIS dwell, port selection, vessel flag
  - COMMODITY_RISK: HS code, tariff rates, export controls
  - CORRIDOR_RISK: Country pair, corridor multipliers
  - PARTY_RISK: Shipper age, OFAC, violations
  - PATTERN_RISK: ML anomalies, pricing deviation
  - TIME_SENSITIVITY: Pre-tariff timing, seasonal anomalies

- **FDA Features** (8 domain-specific):
  - IMPORTER_LEGITIMACY, PRODUCT_COMPLIANCE, SUPPLY_CHAIN_INTEGRITY, etc.

- **Opioid Features** (5 domain-specific):
  - PRESCRIPTION_VOLUME, PRESCRIBER_PATTERN, PATIENT_BEHAVIOR, etc.

#### PART 5: Model Training & Active Learning
- **Monthly Retraining Pipeline**:
  - Load training data (feedback + historical)
  - Feature engineering
  - Train XGBoost (imbalance handling)
  - Train Isolation Forest
  - Generate SHAP explainer
  - Evaluate on test set
  - Deploy if improved

- **Active Learning Workflow**:
  - Analyst labels uncertain cases (50-70% confidence)
  - Feedback stored in PostgreSQL
  - Threshold for retraining (50+ new labels)

#### PART 6: Monitoring & Drift Detection
- **Real-Time Drift Detection**:
  - Feature distribution shifts (KS test)
  - PPV trend analysis
  - Confidence miscalibration
  - Auto-trigger retraining

- **Monitoring Dashboard**:
  - API latency (P50, P95, P99)
  - Model performance (AUC, PPV, sensitivity)
  - Referral volume, confirmed cases
  - Feature drift alerts

#### PART 7: API & Integration
- **REST Endpoints**:
  - `POST /api/score/{domain}/{entity_id}` → score + confidence + explanation
  - `POST /api/feedback/{domain}/{entity_id}` → analyst label
  - `GET /api/model/{domain}/metrics` → performance metrics
  - `GET /api/rules/{domain}` → active rules + parameters
  - `POST /api/rules/{domain}/{rule_id}/parameter` → update rule

#### PART 8: Implementation Roadmap (24 weeks)
- **Phase 1** (Weeks 1-4): Foundation, XGBoost on 287 EAPA cases
- **Phase 2** (Weeks 5-12): Active learning, production deployment
- **Phase 3** (Weeks 13-16): Multi-domain (FDA, Opioid)
- **Phase 4** (Weeks 17-24): Productization, scaling

#### PART 9: Success Metrics & Targets
- **Phase 1**: AUC 0.82-0.84, PPV 30-40%, Sensitivity 70-75%
- **Phase 2**: AUC 0.87-0.89, PPV 35-45%, Sensitivity 78-82%
- **Phase 3**: CBP 0.90+, FDA 0.85+, Opioid 0.83+
- **Phase 4**: CBP 0.90-0.92, all domains at target

#### PART 10: Governance & Compliance
- **Rule Versioning** (SCD Type 2): Who, what, when, why
- **Model Audit Trail**: Every score logged with explanation
- **Replaceability**: Can recreate any historical score (temporal queries)

---

## DOCUMENT 2: PRECISE_RISK_MODEL_IMPLEMENTATION_PLAN.md
**Purpose**: Data-driven, pragmatic implementation with risk management  
**Audience**: Project managers, decision makers, team leads  
**Length**: ~30 pages (6 detailed sections)

### What's In It:

#### PART 1: Data Availability Assessment
- **Current Data Sources** (What we have NOW):
  - EAPA: 287 confirmed transshipment cases ✅
  - Senzing: 244K entities, 99.2% resolution success ✅
  - Current Manifests: 50K/week live feed ✅
  - OpenCorp API: 50M companies, beneficial ownership ✅
  - Vessel/AIS Data: Partial, needs integration (weeks 2-3)

- **Data Sufficiency Analysis**:
  - Can train XGBoost on 287 EAPA + 10K non-EAPA = 10,287 samples
  - Class balance: 2.8% positive (typical imbalance)
  - Sufficient for Phase 1? **YES** (AUC 0.82-0.84 expected)

- **Missing Data Contingencies** (If Phase 1 insufficient):
  - **Scenario A** (Expected): EAPA + manifests sufficient → proceed
  - **Scenario B** (Fallback): Extended data search, rules-only deployment, or transfer learning
  - **Decision Gate Week 2**: Go/No-Go checkpoint

#### PART 2: Refactoring Current CBP Sentry (No Duplication)
- **Current Architecture** (Before):
  - `risk_scoring_engine.py` (32KB, hardcoded CBP logic)
  - `risk_models.py` (15KB, hardcoded factors/thresholds)
  - V2AITuningPage (hardcoded 7 factors)
  - **Problem**: Code duplication when FDA/Opioid added

- **Refactored Architecture** (After):
  - Delete `risk_scoring_engine.py` (moved to Precise Risk Model)
  - Delete `risk_models.py` (moved to risk_scoring.scorecards table)
  - V2AITuningPage: Domain selector, dynamic factor loading
  - **Result**: Zero duplication, one code path for 3 domains

- **Backward Compatibility Guarantee**:
  - ✅ CommandCenter tab: Works unchanged
  - ✅ ActiveInvestigations tab: Works unchanged
  - ✅ ShipmentIntelligence tab: Works unchanged
  - ✅ EntityResolution tab: Works unchanged
  - ✅ V2AITuningPage: Enhanced (domain selector) but functionality same

#### PART 3: Storage (GCP Cloud Storage)
- **Model Artifacts Location**:
  - `gs://cbp-sentry-models/cbp/xgboost/v1.pkl`
  - `gs://cbp-sentry-models/cbp/isolation_forest/v1.pkl`
  - `gs://cbp-sentry-models/cbp/shap_explainer/v1.pkl`
  - Cost: ~$0.02/GB/month (negligible)

#### PART 4: Implementation Roadmap (16 weeks, 4 phases)

**Phase 1: Foundation (Weeks 1-4)**
- Week 1: Data validation (287 EAPA + 10K non-EAPA)
- Week 2: Feature engineering (72 CBP features)
- Week 3: Model training (XGBoost, Isolation Forest, SHAP)
- Week 4: Microservice deployment (precise-risk-engine-api)
- **Deliverable**: Risk engine ready, AUC 0.82+
- **Data Gate**: Week 2 checkpoint

**Phase 2: Integration (Weeks 5-8)**
- Week 5-6: Service integration (cbp-sentry-api → risk-engine-api)
- Week 7: V2AITuningPage refactoring (domain selector)
- Week 8: Cleanup (archive legacy code, full testing)
- **Deliverable**: All tabs working through new model, rollback-safe
- **With rollback safety**:
  - Rename `risk_scoring_engine.py` → `risk_scoring_engine_legacy.py`
  - Feature flag: `use_legacy_model = False` (default)
  - If new model fails: Set flag to `True` → instant fallback

**Phase 3: Multi-Domain (Weeks 9-12)**
- Week 9-10: FDA domain (data, features, training)
- Week 11: Opioid domain (same process)
- Week 12: Multi-domain validation
- **Deliverable**: 3 domains live (1 codebase, 3 configs)

**Phase 4: Production Hardening (Weeks 13-16)**
- Week 13-14: Security, compliance, load testing
- Week 15: Productization (template configs)
- Week 16: Planning (Bayesian networks, ensemble models)
- **Deliverable**: Production-ready product

#### PART 5: Data Sufficiency Decision Gate (Week 2)

**If Sufficient (Expected)**:
- EAPA 287 + 10K manifests → Proceed with Phase 1

**If Insufficient (Contingency)**:
- **Option 1**: Extend data search (+100-200 EAPA cases)
- **Option 2**: Deploy rules-only (Gate 1, skip XGBoost for now)
- **Option 3**: Transfer learning (if FDA/Opioid have more data)

#### PART 6: Backward Compatibility Guarantee & Rollback Safety

**Feature Flag Strategy**:
```python
use_legacy_model = False  # Default: new Precise Risk Model

if use_legacy_model:
    score = risk_scoring_engine_legacy.score(shipment)
else:
    score = call_risk_engine_api(shipment)
```

**Parallel Running (Weeks 5-8)**:
- Week 5: 10% new model, 90% old
- Week 6: 50% new model, 50% old
- Week 7: 90% new model, 10% old
- Week 8: 100% new model (old still available)

**Instant Rollback**:
1. Set `use_legacy_model = True`
2. Restart services
3. Immediate switch (no redeployment)

**Archive Strategy**:
- Keep `risk_scoring_engine_legacy.py` in main branch indefinitely
- Post-Week 16: Can optionally move to separate branch

---

## COMPARISON TABLE

| Aspect | Design Document | Implementation Plan |
|--------|-----------------|-------------------|
| **Focus** | Technical architecture & specifications | Data-driven, pragmatic execution |
| **Audience** | Engineers, architects | Project managers, decision makers |
| **What it defines** | "How should it work?" | "How do we build it with what we have?" |
| **Data assumptions** | Assumes EAPA + manifests sufficient | Validates data Week 2, has fallbacks |
| **Backward compatibility** | Described conceptually | Detailed with feature flag, legacy archival |
| **Rollback strategy** | Mentioned briefly | Comprehensive (parallel running, instant switch) |
| **Risk management** | Lists risks at end | Decision gates at Weeks 2, 4, 8, 12, 16 |
| **Team guidance** | "What needs to be built" | "Week-by-week tasks, milestones, go/no-go" |

---

## HOW THEY WORK TOGETHER

```
DESIGN DOCUMENT (What)
    ↓
    Defines complete architecture
    (Database schema, APIs, 3-gate model, features)
    
    ↓
    
IMPLEMENTATION PLAN (How)
    ↓
    Takes the design and applies it pragmatically
    - Validates data availability (Week 2 gate)
    - Identifies data that exists NOW vs contingencies
    - Plans refactoring to avoid code duplication
    - Adds rollback safety (feature flag, legacy archival)
    - Breaks work into 16 weekly phases
    - Defines go/no-go checkpoints
    
    ↓
    
EXECUTIVE SUMMARY (Why & When)
    ↓
    High-level overview for stakeholders
    - Budget: $190K-200K
    - Timeline: 16 weeks
    - Success metrics: AUC 0.82+ → 0.91+
    - Decision checklist for approval
```

---

## KEY TAKEAWAYS

### Design Document Says:
- "Here's the complete technical architecture for a generalized, multi-domain risk scoring engine"
- Defines 12 PostgreSQL tables, 3-gate model, 72 CBP features, APIs, monitoring
- Technical blueprint (what to build)

### Implementation Plan Says:
- "Here's how to build it with the data we have, without breaking existing functionality"
- Validates EAPA 287 cases + manifests sufficient (Week 2 gate)
- Keeps legacy code as rollback (feature flag)
- Refactors to eliminate duplication
- 16-week phases with go/no-go checkpoints
- Pragmatic execution (how to build it safely)

### Executive Summary Says:
- "Here's the high-level overview, costs, timeline, and approval checklist"
- $190K-200K for 16 weeks
- 6 locked architectural decisions
- Success metrics and risk mitigation
- Ready for team kickoff (what to approve)

---

## READY FOR REVIEW?

All three documents are:
- ✅ Data-driven (uses current datasets: EAPA, Senzing, manifests)
- ✅ Backward compatible (all 5 tabs continue working)
- ✅ Safe (rollback strategy, legacy code kept, feature flag)
- ✅ No duplication (refactor old code away)
- ✅ Multi-domain ready (CBP → FDA → Opioid)
- ✅ Approved by you (GCP Storage, legacy archival, constraints incorporated)

**Next step**: Stakeholder review & approval before Week 1 kickoff.

