# Precise Risk Model: Implementation Plan (Data-Driven & Backward Compatible)

**Constraints**:
1. Model must be operational with CURRENT available datasets (Senzing, EAPA, manifests)
2. Existing CBP Sentry functionality (5 tabs, all screens) must work without breaking
3. Refactor to reduce code duplication between old risk_scoring_engine.py and new Precise Risk Model
4. Storage: GCP Cloud Storage (not S3)

---

## PART 1: DATA AVAILABILITY ASSESSMENT

### Phase 1 Data Sources (What We Have Now)

```
DATA SOURCE 1: EAPA Confirmed Cases (Baseline Training)
├─ 287 confirmed transshipment cases (2021-2025)
├─ Each case has:
│  ├─ Shipment manifest (origin, destination, commodity, value)
│  ├─ ISF data (container stuffing location)
│  ├─ Vessel info (AIS tracking, flags, operators)
│  ├─ Party info (shipper, consignee, importer age, violations)
│  ├─ Tariff data (AD/CVD rates, HS codes)
│  ├─ Investigation outcome (confirmed transshipment = label: 1)
│  └─ Detection signals (which rules triggered? which features anomalous?)
├─ Storage: PostgreSQL cbp_sentry database
├─ Available: NOW
└─ Sufficient for: XGBoost training (AUC 0.82-0.84 with 287 samples)

DATA SOURCE 2: Senzing Entity Resolution (Current)
├─ 244K CORD entities (shipper, consignee, vessel operators)
├─ Entity resolution confidence scores (99.2% success rate)
├─ L1/L2/L3 relationship mapping (who owns what, who ships with whom)
├─ OFAC SDN screening results (hit/no-hit)
├─ Integration: services/api/senzing_client.py (already deployed)
├─ Available: NOW
└─ Used for: Party risk, entity network analysis, beneficial ownership lookups

DATA SOURCE 3: Current Manifest Ingest (Daily Feed)
├─ ~50K shipments/week through CBP ports
├─ Each shipment has:
│  ├─ Shipper, consignee, commodity, value
│  ├─ HS code, tariff classification
│  ├─ Vessel name, flag, registration
│  ├─ Port of origin, destination, intermediate ports
│  └─ Filing timestamp, amendment history
├─ Storage: PostgreSQL cbp_sentry.shipments
├─ Available: NOW (live feed)
└─ Used for: Feature engineering (dwell, pricing, routing anomalies)

DATA SOURCE 4: OpenCorp API (Beneficial Ownership)
├─ 50M+ company registrations with UBO data
├─ Opacity scores (shell company risk)
├─ Jurisdiction risk assessment
├─ Integration: Via services/api/ (new, 5 days to integrate)
├─ Cost: $500-1,000/month caching at scale
└─ Available: NOW (free API signup)

DATA SOURCE 5: Vessel/Shipping Data (MarineTraffic, IMO)
├─ AIS transponder data (vessel locations, dwell times)
├─ Vessel ownership, flag history, age
├─ Port-of-call patterns
├─ Status: PARTIAL (need to integrate)
├─ Timeline: Week 2-3 of Phase 1
└─ Used for: Routing anomalies, dwell time baselines

TOTAL LABELED TRAINING DATA (For XGBoost):
├─ EAPA cases: 287 confirmed transshipment (label: 1)
├─ Assumed legitimate: 10,000 random non-EAPA shipments (label: 0)
├─ Class balance: 2.8% positive (typical imbalance)
├─ Sufficient for Phase 1? YES - 10K cases is enough for baseline (AUC 0.82-0.84)
└─ Data quality: HIGH (EAPA = ground truth)
```

### Missing Data (If Phase 1 Insufficient)

```
DATA SOURCES NOT YET AVAILABLE:

1. Real CBP Investigation Feedback
   ├─ What: Analyst confirmation that a referral was real fraud
   ├─ Why needed: Ground truth for active learning (feedback table)
   ├─ Timeline: Starts Month 2 (after first referrals are investigated)
   ├─ Impact if missing: Can't do active learning in Phase 1, but can in Phase 2
   └─ Fallback: Use EAPA cases only (static training set)

2. Historical Gate 1 Decisions (Pre-Model)
   ├─ What: Which shipments were referred before? What was the referral reason?
   ├─ Why needed: Understand historical patterns, tune rule thresholds
   ├─ Timeline: Need to query CBP's existing referral logs
   ├─ Impact if missing: Rules thresholds less calibrated, but still workable
   └─ Fallback: Data-driven thresholds from distribution (percentiles)

3. Price Intelligence (Real-time Commodity Prices)
   ├─ What: LME (aluminum), ICIS (chemicals), Platts (energy)
   ├─ Why needed: Detect pricing anomalies (declared vs market)
   ├─ Timeline: Week 3-4 of Phase 1 (API integrations)
   ├─ Impact if missing: Can't score pricing anomalies, skip that feature
   └─ Fallback: Static price baselines (historical averages)
```

### DECISION: Phase 1 Strategy (What If Data Insufficient?)

**Scenario A: EAPA + Current Manifests Are Sufficient (LIKELY)**
```
Can train XGBoost on:
├─ 287 EAPA cases (confirmed transshipment)
├─ 10,000 random non-EAPA shipments (assumed legitimate)
├─ 72 features from manifests + Senzing
└─ Result: AUC 0.82-0.84

Deploy to production with:
├─ Deterministic rules (OFAC, Element 9, corridors) - high precision
├─ XGBoost model (learns from 287 cases) - medium precision
├─ Active learning enabled (collect analyst feedback)
└─ Timeline: 4 weeks (Phase 1)
```

**Scenario B: EAPA Data Insufficient (If Unlikely, But Plan For)**
```
If 287 cases + 10K non-EAPA < AUC 0.75 threshold:

Option 1: Extend Training Data
├─ Task: Identify additional confirmed transshipment cases from CBP records
│  (cases before 2021, cases with tags like "transshipment attempted", etc.)
├─ Effort: 1 week data archaeology
├─ Expected: +100-200 additional labeled cases
└─ Result: 387-487 confirmed cases → AUC likely 0.80+

Option 2: Start with Rules-Only (No ML)
├─ Deploy Gate 1 (deterministic rules) only
├─ Skip Gate 2 (XGBoost) until more data available
├─ Collect analyst feedback for 2-3 months
├─ Retrain with 500+ labeled cases by Month 4
└─ Acceptable: Lower PPV initially (20-30%), improves over time

Option 3: Transfer Learning from FDA/Opioid
├─ If FDA/Opioid have more labeled fraud cases available
├─ Pre-train XGBoost on FDA data, fine-tune on 287 EAPA cases
├─ Bootstraps learning when CBP data is limited
└─ Advanced approach (Month 2-3)

DECISION: Proceed with Scenario A (expect sufficient data)
If insufficient → Escalate week 2 (activate Scenario B)
```

---

## PART 2: REFACTORING CURRENT CBP SENTRY (Avoid Duplication)

### Current Architecture (Before Refactor)

```
cbp-sentry-api (monolithic)
├─ services/api/risk_scoring_engine.py (32KB)
│  ├─ _score_documentation_risk()
│  ├─ _score_commodity_risk()
│  ├─ _score_routing_risk()
│  ├─ ... (8 functions, hardcoded CBP logic)
│  └─ Final score calculation (weighted sum, hardcoded factors)
│
├─ services/api/risk_models.py (15KB)
│  ├─ DOCUMENTATION_RISK definition
│  ├─ COMMODITY_RISK definition
│  ├─ ... (7 factor definitions, hardcoded)
│  └─ Thresholds (hardcoded: gate1=30, gate2=60, gate3=80)
│
├─ services/api/routes/scoring.py
│  ├─ POST /api/score/{shipment_id}
│  └─ Calls risk_scoring_engine.py directly (in-process)
│
├─ ui/src/v2/pages/V2AITuningPage.tsx (250+ lines)
│  └─ Hardcoded 7 factors, hardcoded sliders, hardcoded weights
│
└─ Other tabs/screens:
   ├─ CommandCenter.tsx (working, no changes needed)
   ├─ ActiveInvestigations.tsx (working, no changes needed)
   ├─ ShipmentIntelligence.tsx (working, no changes needed)
   └─ EntityResolution.tsx (working, no changes needed)

DUPLICATION RISK:
├─ risk_scoring_engine.py has hardcoded CBP logic
├─ When Precise Risk Model is added, will have generic code + CBP config
├─ Both will exist → maintainers confused, two code paths
└─ Solution: Refactor to use Precise Risk Model, remove old risk_scoring_engine.py
```

### Refactored Architecture (After Integration)

```
cbp-sentry-api (refactored, reduced)
├─ services/api/risk_scoring_engine.py (DEPRECATED, deleted)
│  └─ Replaced by: precise-risk-engine-api microservice
│
├─ services/api/routes/scoring.py (REFACTORED)
│  └─ POST /api/score/{shipment_id}
│     └─ Calls → precise-risk-engine-api (HTTP call)
│     └─ Returns score from microservice
│
├─ services/api/risk_models.py (DEPRECATED, deleted)
│  └─ Replaced by: risk_scoring.scorecards table in DB
│
├─ ui/src/v2/pages/V2AITuningPage.tsx (REFACTORED)
│  ├─ Domain selector (cbp, fda, opioid)
│  ├─ Dynamically load factors from API
│  ├─ Dynamically load rules from API
│  └─ All calls → precise-risk-engine-api

precise-risk-engine-api (NEW microservice)
├─ services/risk-engine/models/precise_risk_model.py
│  ├─ PreciseRiskModel class (generic, config-driven)
│  └─ score() method (works for any domain)
├─ services/risk-engine/routes/scoring.py
│  └─ POST /api/risk-engine/score/{domain}/{entity_id}
├─ services/risk-engine/routes/rules.py
│  └─ GET/POST /api/risk-engine/rules/{domain}
├─ services/risk-engine/config/
│  ├─ cbp.yaml (factors, rules, thresholds)
│  ├─ fda.yaml
│  └─ opioid.yaml

Other tabs/screens (UNCHANGED):
├─ CommandCenter.tsx (no changes, still calls cbp-sentry-api for referral data)
├─ ActiveInvestigations.tsx (no changes)
├─ ShipmentIntelligence.tsx (no changes)
└─ EntityResolution.tsx (no changes)

RESULT:
├─ Zero duplication (one code path through Precise Risk Model)
├─ Existing functionality preserved (all tabs still work)
├─ Easier maintenance (config-driven, not hardcoded)
└─ Ready to add FDA/Opioid (same microservice, different config)
```

### Refactoring Plan (Phases)

```
PHASE 0: Parallel Development (Weeks 1-4)
├─ Develop Precise Risk Model (new microservice, in isolation)
├─ Existing CBP Sentry (commands center, investigations, etc.) continues working
├─ No touching of existing code yet
└─ Deliverable: risk-engine-api ready for integration testing

PHASE 1: Integration (Weeks 5-8)
├─ Week 5-6: Add HTTP calls from cbp-sentry-api to risk-engine-api
│  ├─ Modify POST /api/score/{shipment_id}
│  │  └─ Old: calls risk_scoring_engine.py directly
│  │  └─ New: calls risk-engine-api via HTTP
│  └─ Verify all existing tests still pass
├─ Week 7: Refactor V2AITuningPage to call risk-engine-api
│  └─ Add domain selector, dynamic factor loading
├─ Week 8: Remove old code
│  ├─ Delete risk_scoring_engine.py (if no other code depends on it)
│  ├─ Delete risk_models.py (move config to risk_scoring.scorecards table)
│  └─ Update tests to use new API paths
└─ Deliverable: All existing functionality working through Precise Risk Model

PHASE 2: Multi-Domain Support (Weeks 9-12)
├─ Add FDA scorecard config
├─ Add Opioid scorecard config
├─ Existing CBP tabs unchanged (still call same API, domain_id='cbp')
└─ Deliverable: 3 domains supported, one codebase

BACKWARD COMPATIBILITY CHECKS:
├─ CommandCenter tab: Loads referrals (calls cbp-sentry-api, unchanged)
├─ ActiveInvestigations tab: Shows investigation cases (unchanged)
├─ ShipmentIntelligence tab: Shows shipment details (unchanged)
├─ EntityResolution tab: Shows entity graph (unchanged)
├─ V2AITuningPage: Now calls risk-engine-api (domain selector added, but same functionality)
└─ All other tabs: Completely unchanged

TESTING:
├─ Unit tests: Precise Risk Model (independent)
├─ Integration tests: cbp-sentry-api → risk-engine-api (HTTP integration)
├─ E2E tests: Existing UI flows (CommandCenter, ActiveInvestigations, etc.) still work
├─ Regression tests: V2AITuningPage saves/loads weights correctly
└─ Data tests: Score consistency (old vs new code path produces same results for CBP)
```

---

## PART 3: STORAGE: GCP Cloud Storage (Not S3)

### Model Artifacts Location

```
GCP Cloud Storage bucket: cbp-sentry-models

Structure:
├─ gs://cbp-sentry-models/
│  ├─ cbp/
│  │  ├─ xgboost/
│  │  │  ├─ v1.pkl (first model, trained on 287 EAPA)
│  │  │  ├─ v2.pkl (after 500 active learning cases)
│  │  │  └─ v3.pkl (after 1,500 active learning cases)
│  │  ├─ isolation_forest/
│  │  │  ├─ v1.pkl
│  │  │  ├─ v2.pkl
│  │  │  └─ v3.pkl
│  │  ├─ shap_explainer/
│  │  │  ├─ v1.pkl
│  │  │  ├─ v2.pkl
│  │  │  └─ v3.pkl
│  │  └─ metadata.json
│  │     └─ {"version": "v3", "deployed": true, "auc": 0.89, "deployed_at": "2026-12-01"}
│  ├─ fda/
│  │  ├─ xgboost/v1.pkl
│  │  ├─ isolation_forest/v1.pkl
│  │  └─ shap_explainer/v1.pkl
│  └─ opioid/
│     ├─ xgboost/v1.pkl
│     ├─ isolation_forest/v1.pkl
│     └─ shap_explainer/v1.pkl

Python Integration:
├─ from google.cloud import storage
├─ client = storage.Client()
├─ bucket = client.bucket('cbp-sentry-models')
├─ blob = bucket.blob('cbp/xgboost/v3.pkl')
├─ model = joblib.load(blob.download_as_bytes())
└─ Cost: ~$0.02/GB/month (negligible)

Advantages:
├─ Uses existing GCP infrastructure
├─ Automatic versioning (GCP object versioning)
├─ Integration with GCP IAM (service account permissions)
├─ Consistent with current data storage strategy
└─ No new vendor (AWS) introduced
```

---

## PART 4: IMPLEMENTATION ROADMAP (Data-Driven)

### Phase 1: Foundation (Weeks 1-4)

```
Goal: Deploy XGBoost model on EAPA + current manifest data

Week 1: Data Preparation & Validation
├─ [ ] Verify EAPA data availability (287 confirmed cases)
│  └─ Query: SELECT COUNT(*) FROM eapa_cases WHERE confirmed_transshipment = TRUE
├─ [ ] Extract features from 287 EAPA cases
│  ├─ Manifest fields (shipper, commodity, value, HS code)
│  ├─ Senzing entity resolution (shipper age, OFAC hits, violations)
│  ├─ Vessel data (flag, age, operator)
│  └─ Tariff data (AD/CVD rates)
├─ [ ] Identify 10K random non-EAPA shipments (assumed legitimate)
├─ [ ] Create training dataset (287 + 10K = 10,287 total, 2.8% positive)
└─ Effort: 1 ML engineer

IF DATA INSUFFICIENT:
└─ Escalate: Activate Scenario B (extended data search, rules-only fallback)

Week 2: Feature Engineering
├─ [ ] Implement FeatureEngineer class (CBP domain)
├─ [ ] Integrate Senzing (entity resolution) - already available
├─ [ ] Integrate OpenCorp (beneficial ownership) - 5 days
├─ [ ] Add vessel/AIS data (if available)
├─ [ ] Test on 50 EAPA samples
└─ Effort: 1 ML engineer + 1 backend engineer

Week 3: Model Training & Evaluation
├─ [ ] Train XGBoost on 10,287 cases
│  └─ Target: AUC 0.82-0.84
├─ [ ] Train Isolation Forest (anomaly detection)
├─ [ ] Generate SHAP explainer
├─ [ ] Evaluate: precision, recall, F1
├─ [ ] Create model comparison report
└─ Effort: 1 ML engineer

Week 4: Microservice Deployment
├─ [ ] Create precise-risk-engine-api (Flask)
├─ [ ] Implement scoring endpoints
├─ [ ] Create risk_scoring.scorecards table (PostgreSQL)
├─ [ ] Create cbp.yaml config (factors, rules, thresholds)
├─ [ ] Deploy to staging (Docker, AWS ECS)
├─ [ ] Test: POST /api/risk-engine/score/cbp/{entity_id}
└─ Effort: 1 backend engineer + 1 DevOps

DELIVERABLE: Precise Risk Model microservice ready, XGBoost AUC 0.82+
BACKWARD COMPATIBILITY: cbp-sentry-api still uses old risk_scoring_engine.py
NEXT: Week 5 integration
```

### Phase 2: Integration & Backward Compatibility (Weeks 5-8)

```
Goal: Integrate risk-engine-api without breaking existing tabs

Week 5-6: Service Integration
├─ [ ] Modify cbp-sentry-api POST /api/score/{shipment_id}
│  ├─ Old flow: Call risk_scoring_engine.py (in-process)
│  └─ New flow: Call risk-engine-api (HTTP)
├─ [ ] Add feature flag (gradual rollout)
│  └─ feature_flag.use_new_risk_model = False (default, old path)
│  └─ feature_flag.use_new_risk_model = True (new path, test-only)
├─ [ ] Run all existing tests (CommandCenter, ActiveInvestigations, etc.)
├─ [ ] Verify backward compatibility
└─ Effort: 1 backend engineer + 1 QA

IF TESTS FAIL:
└─ Investigate: Old vs new model producing different scores? 
   Acceptable difference: ±5 points (due to feature engineering changes)
   If >5 points: Debug feature engineering, retrain

Week 7: V2AITuningPage Refactoring
├─ [ ] Add domain selector dropdown
├─ [ ] Dynamically load factors from API
│  └─ GET /api/risk-engine/model/cbp/weights
├─ [ ] Dynamically load rules from API
│  └─ GET /api/risk-engine/rules/cbp
├─ [ ] Test: Adjust weights, save, verify changes persisted
├─ [ ] Test: Adjust rules, save, verify changes persisted
└─ Effort: 1 frontend engineer + 1 backend engineer

Week 8: Cleanup & Finalization (With Rollback Safety)
├─ [ ] Archive old code (don't delete, keep for rollback)
│  ├─ Rename: risk_scoring_engine.py → risk_scoring_engine_legacy.py
│  ├─ Rename: risk_models.py → risk_models_legacy.py
│  ├─ Add comment: "DEPRECATED: Kept for rollback. Use Precise Risk Model instead."
│  ├─ Feature flag: use_legacy_model = False (default)
│  ├─ If use_legacy_model = True, routes call old code path (instant rollback)
│  └─ Git commit: "Archive legacy risk scoring (kept for rollback capability)"
├─ [ ] Run full regression test suite
├─ [ ] Verify all 5 tabs still work (CommandCenter, ActiveInvestigations, etc.)
├─ [ ] Documentation: How to add a new domain (for FDA/Opioid)
├─ [ ] Create rollback runbook:
│  └─ "If new model fails in production, set use_legacy_model=True and restart"
└─ Effort: 1 backend engineer

ROLLBACK STRATEGY:
├─ Instant switch: feature_flag.use_legacy_model = True (no code redeployment)
├─ Path 1 (Old): cbp-sentry-api → risk_scoring_engine_legacy.py (in-process)
├─ Path 2 (New): cbp-sentry-api → precise-risk-engine-api (HTTP)
├─ Feature flag in code controls which path is used
├─ Weeks 5-12: Both paths tested in parallel, new path gradually increases traffic
├─ Post-week 12: If production stable, can optionally archive legacy code to separate branch
└─ Safety: Legacy code remains in main branch indefinitely

DELIVERABLE: All existing functionality working through Precise Risk Model
TEST RESULTS: All CBP Sentry tabs functional, backward compatible
ROLLBACK READY: Legacy code archived and feature-flagged for instant fallback
READY FOR: Phase 3 (multi-domain)
```

### Phase 3: Multi-Domain (Weeks 9-12)

```
Same architecture, different configs for FDA and Opioid
- Existing CBP functionality unchanged
- New domains use same microservice code
- No duplication
```

### Phase 4: Production Hardening (Weeks 13-16)

---

## PART 5: BACKWARD COMPATIBILITY GUARANTEE

### Existing Features (Must Not Break)

```
1. Command Center Tab
   ├─ Shows live referral metrics (PPV, sensitivity, referral volume)
   ├─ Data source: model_scores + feedback tables
   ├─ Impact: NONE (tabs don't change, only source of scores changes from old to new model)
   └─ Test: Verify metrics display matches new model output

2. Active Investigations Tab
   ├─ Shows analyst-reviewed cases
   ├─ Data source: investigation outcomes, shipment details
   ├─ Impact: NONE (no scoring changes to investigation workflow)
   └─ Test: Verify case details load correctly

3. Shipment Intelligence Tab
   ├─ Shows shipment details, historical context
   ├─ Data source: manifest data, entity resolution (Senzing)
   ├─ Impact: NONE (Senzing still used for enrichment)
   └─ Test: Verify entity graph loads

4. Entity Resolution Tab
   ├─ Shows entity graph, relationships
   ├─ Data source: Senzing CORD, entity resolution
   ├─ Impact: NONE (no changes to entity resolution logic)
   └─ Test: Verify graph visualization works

5. V2AITuningPage (Model Weights Tab)
   ├─ Shows factor weights, rule toggles, thresholds
   ├─ Data source: OLD model_weights API → NEW risk-engine-api
   ├─ Impact: MEDIUM (API endpoint changes, but UI same)
   ├─ Changes: Domain selector added, dynamic loading added
   └─ Test: Verify weights save/load correctly

VERIFICATION STRATEGY:
├─ Week 8: Run full regression test suite
├─ Each tab: Load, verify data displays, verify buttons work
├─ V2AITuningPage: Adjust weights, save, refresh, verify persisted
├─ CommandCenter: Verify referral metrics reflect new model scores
└─ Pass criteria: All tests green, zero regressions
```

---

## PART 6: DECISION GATE: Data Sufficiency (Week 2)

### Weekly Checkpoint (Week 2, Day 5)

```
DECISION CRITERIA:

Question 1: EAPA Data Usable?
├─ Criterion: Can extract 72 features from 287 EAPA cases
├─ Evidence: 287 confirmed cases with manifest, ISF, vessel data
└─ Decision: YES/NO → If NO, activate Scenario B

Question 2: Training Data Quality?
├─ Criterion: Feature distributions look reasonable (no massive outliers)
├─ Evidence: Run describe() on 287 cases, check for missing values
└─ Decision: YES/NO → If NO, may need data cleansing

Question 3: Non-EAPA Legitimate Sample?
├─ Criterion: Can identify 10K random shipments (assumed legitimate)
├─ Evidence: Query shipments outside EAPA, verify no fraud indicators
└─ Decision: YES/NO → If NO, may need alternate sampling

IF ALL YES:
└─ Proceed Week 3 (model training)

IF ANY NO:
├─ Option 1: Activate Scenario B (extended data search)
├─ Option 2: Deploy with rules-only (Gate 1), skip XGBoost (Gate 2)
├─ Option 3: Delay Phase 1, extend data preparation
└─ Decision: Discuss with stakeholders
```

---

## SUMMARY: Implementation Strategy

```
DATA-DRIVEN:
✅ Use available data (EAPA 287 cases + current manifests)
✅ Validate data sufficiency Week 2
✅ If insufficient, activate fallback strategy

BACKWARD COMPATIBLE:
✅ Existing 5 tabs unaffected
✅ Existing workflows unchanged
✅ Feature flag for gradual rollout

NO DUPLICATION:
✅ Remove old risk_scoring_engine.py after integration
✅ One code path (Precise Risk Model) for all domains
✅ Configuration-driven (no hardcoding)

GCP-NATIVE:
✅ Use GCP Cloud Storage (not S3)
✅ Consistent with existing infrastructure

PRODUCTION READY:
✅ 16-week timeline (4 phases)
✅ Weekly decision gates
✅ Full regression testing

RISK MITIGATION:
✅ Feature flag (can switch back to old model if new model fails)
✅ Parallel running (both models running weeks 5-8 for comparison)
✅ Stakeholder checkpoints (data sufficiency, quality gates, performance)
```

---

## NEXT STEP: Approval

**Confirm**:
1. ✅ GCP Cloud Storage (not S3)
2. ✅ Data availability assessment (Senzing + EAPA + manifests sufficient?)
3. ✅ Backward compatibility strategy (all 5 tabs working)
4. ✅ Refactoring plan (remove old risk_scoring_engine.py, no duplication)
5. ✅ Decision gate Week 2 (data sufficiency escalation)

**If approved**: Ready to create final detailed design with:
- PostgreSQL schema (risk_scoring namespace)
- API specifications (precise-risk-engine endpoints)
- Refactoring checklist (old code removal)
- Testing strategy (regression + backward compatibility)
- Risk mitigation (feature flags, parallel running)

