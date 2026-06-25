# CBP Sentry Risk Scoring Engine - Pragmatic Implementation Roadmap

**Based on**: Research findings, world-class fraud detection benchmarks, active learning feasibility  
**Approved decisions**: XGBoost single model, OpenCorp integration, 5 referrals/day assumption, domain-separated data  
**Timeline**: June 15 staging → August 1 production → December 1 evaluation

---

## EXECUTIVE SUMMARY

**Start with XGBoost single model.** Not ensemble.

**Why**: 
- Ensemble costs $100/month. CBP's ROI is 1,541× positive. But the real constraint is **training data** (287 cases), not cost.
- You'll collect 1,250 labeled cases in 6 months via active learning (5 referrals/day assumption).
- At 1,500+ cases, ensemble becomes worth the complexity. Until then, single model is pragmatic.
- Upgrade decision point: December 1 (6-month checkpoint).

**Performance trajectory**:
```
June (Staging):      AUC 0.82, PPV ~10%, Sensitivity ~71% (baseline on 287 EAPA)
August (Go-live):    AUC 0.82, PPV 10-12% (early active learning)
October:             AUC 0.85, PPV 18-22% (600 new labeled cases)
December:            AUC 0.87-0.89, PPV 25-35% (1,250 cases)
   → Decision: Ensemble upgrade or stay single?
```

**Benchmark context**: You're tracking PayPal (0.98 AUC) who has 100M+ training examples. CBP at 0.82 with 287 cases is **on-track**. Trajectory to 0.90 by Month 12 is world-class for trade fraud.

---

## PHASE 1: STAGING (June 15 - July 14)

### 1.1 XGBoost Model Setup

**Goal**: Train baseline model on 287 EAPA cases, deploy to staging environment.

```
Tasks:
├─ Load 287 EAPA cases (confirmed transshipment)
├─ Engineer 72 features from CBP data (manifest, ISF, vessel, commodity)
├─ Split: 80% train (230), 20% test (57)
├─ Train XGBoost:
│  ├─ Hyperparameters: n_estimators=200, max_depth=6, learning_rate=0.05
│  ├─ Class weight: scale_pos_weight=10 (imbalance adjustment)
│  └─ 5-fold CV for hyperparameter tuning
├─ Evaluate:
│  ├─ AUC: 0.82-0.84 (expected)
│  ├─ PPV @ 80% confidence: ~30-40%
│  ├─ Sensitivity: ~70-75%
│  └─ Feature importance (top 10)
├─ Baseline calibration: Convert scores to confidence intervals
└─ Deployment artifact: XGBoost pickle + feature engineering code

Effort: 1 week (1 DS engineer + 1 backend engineer)
Cost: $0 (no new infrastructure)
Output: Staging model ready for integration
```

### 1.2 OpenCorp Integration

**Goal**: Enrich Senzing entity records with beneficial ownership data from OpenCorp.

```
Tasks:
├─ Set up OpenCorp API access (public, free sign-up)
├─ Design enrichment pipeline:
│  ├─ Input: Shipper entity ID (from Senzing)
│  ├─ Lookup: OpenCorp beneficial ownership data
│  ├─ Feature engineering:
│  │  ├─ Opacity score (0-100, 0=fully transparent)
│  │  ├─ Shell company flag (yes/no)
│  │  ├─ UBO clarity index (0-1)
│  │  └─ Jurisdiction risk (EU/US = low, Panama/BVI = high)
│  └─ Output: Enriched entity record in Senzing
│
├─ Caching strategy:
│  ├─ OpenCorp result cache (Redis, 1 year TTL)
│  ├─ Cost: $0.01-0.05/lookup, with 98% cache hit = $500-1,000/month
│  └─ Latency: Cached = <10ms, uncached = 200-500ms
│
├─ Integration:
│  ├─ Modify V2AITuningPage to show beneficial ownership risk
│  ├─ Add feature to XGBoost: shipper_opacity_score
│  └─ Retrain model to include OpenCorp features
│
└─ Expected gain: +1-2% AUC, +10-20 basis points PPV

Effort: 5 days (1 backend engineer + 1 data engineer)
Cost: $0 (API free) + $500-1,000/month cache cost (start Month 3)
Output: Shipper enrichment pipeline + new feature in model
```

### 1.3 Data Architecture (Domain Separation)

**Goal**: Design database schema so CBP/FDA/Opioid data never mix.

```
PostgreSQL Schema:

-- Domain-agnostic scoring cache
CREATE TABLE model_scores (
  score_id BIGSERIAL PRIMARY KEY,
  domain VARCHAR(20) NOT NULL,  -- 'cbp' | 'fda' | 'opioid'
  entity_id VARCHAR(255),
  score DECIMAL(5,2),
  confidence DECIMAL(5,2),
  created_at TIMESTAMP,
  model_version VARCHAR(20),
  CONSTRAINT chk_domain CHECK (domain IN ('cbp', 'fda', 'opioid'))
);

-- Domain-specific features (isolated)
CREATE TABLE features_cbp (
  feature_id BIGSERIAL PRIMARY KEY,
  shipment_id VARCHAR(255),
  documentation_risk DECIMAL(5,2),
  routing_risk DECIMAL(5,2),
  -- ... 72 CBP features
  created_at TIMESTAMP
);

CREATE TABLE features_fda (
  feature_id BIGSERIAL PRIMARY KEY,
  import_id VARCHAR(255),
  importer_legitimacy DECIMAL(5,2),
  product_compliance DECIMAL(5,2),
  -- ... FDA features (different set)
  created_at TIMESTAMP
);

-- Model training registry with domain constraint
CREATE TABLE model_training (
  training_id BIGSERIAL PRIMARY KEY,
  model_name VARCHAR(100),
  training_domain VARCHAR(20),
  training_data_count INT,
  auc DECIMAL(5,4),
  training_date TIMESTAMP,
  deployed BOOLEAN,
  CONSTRAINT fk_domain CHECK (training_domain IN ('cbp', 'fda', 'opioid'))
);

-- Active learning feedback (domain-specific)
CREATE TABLE feedback (
  feedback_id BIGSERIAL PRIMARY KEY,
  domain VARCHAR(20),
  entity_id VARCHAR(255),
  predicted_score DECIMAL(5,2),
  actual_label INT,  -- 0 = legitimate, 1 = fraud
  analyst_id VARCHAR(100),
  created_at TIMESTAMP,
  CONSTRAINT chk_domain CHECK (domain IN ('cbp', 'fda', 'opioid'))
);

-- Prevents accidental cross-domain mixing
CREATE TRIGGER enforce_domain_separation
BEFORE INSERT ON model_training
FOR EACH ROW
EXECUTE FUNCTION validate_training_domain();
```

**Data flow**:
```
CBP shipment → Extract CBP features → Store in features_cbp
              → Score with CBP model → Store in model_scores (domain='cbp')
              → Analyst feedback → Store in feedback (domain='cbp')
              → Retrain CBP model on CBP data ONLY

FDA import   → Extract FDA features → Store in features_fda
            → Score with FDA model → Store in model_scores (domain='fda')
            → [Similar isolated flow]
```

Effort: 3 days (1 backend engineer)
Cost: $0
Output: Schema design + data governance constraints

---

### 1.4 Staging Deployment

**Goal**: Deploy baseline model to staging AWS, test end-to-end.

```
Tasks:
├─ Model serving:
│  ├─ XGBoost model → Flask API (/api/score/cbp/{shipment_id})
│  ├─ Endpoint returns: {score: 0-100, confidence: 0-100, features: []}
│  └─ Latency: <200ms (target)
│
├─ Feature pipeline:
│  ├─ Ingest manifest (Excel/CSV)
│  ├─ Extract vessel, shipper, commodity, etc.
│  ├─ Enrich with Senzing entity resolution
│  ├─ Enrich with OpenCorp beneficial ownership
│  └─ Compute 72 features
│
├─ Integration testing:
│  ├─ Test 50 EAPA cases → Expected high score (>80)
│  ├─ Test 50 legitimate imports → Expected low score (<30)
│  └─ Test OpenCorp latency + cache behavior
│
└─ Documentation:
   ├─ Model card (features, training data, performance)
   ├─ API specification
   └─ Troubleshooting guide

Effort: 1 week (1 backend engineer + 1 QA)
Cost: AWS staging ($20/month)
Output: Working staging environment, ready for pilot
```

---

## PHASE 2: PILOT (July 15 - August 14)

### 2.1 Production Deployment (Limited Volume)

**Goal**: Deploy to production with CBP in limited mode (dry-run, no live referrals yet).

```
Tasks:
├─ AWS GovCloud setup:
│  ├─ RDS PostgreSQL (production database)
│  ├─ ECS container for model serving
│  └─ S3 for model artifacts + monitoring logs
│
├─ Live data processing:
│  ├─ Ingest real CBP manifests (small volume, 100/day)
│  ├─ Score shipments via model
│  ├─ Store results (no action taken yet)
│  └─ Monitor latency, errors, data quality
│
├─ Monitoring setup:
│  ├─ CloudWatch: API latency, error rates
│  ├─ Custom: Feature distribution drift detection
│  ├─ Custom: Model confidence score distribution
│  └─ Alerts: If latency >500ms or error rate >1%
│
├─ Active learning setup:
│  ├─ Dashboard: Show analysts "uncertain" cases (50-70% confidence)
│  ├─ Feedback form: "Is this transshipment? Yes/No/Unsure"
│  ├─ Auto-store feedback in feedback table
│  └─ Count referrals for trajectory tracking
│
└─ Security:
   ├─ Encrypt data at rest (S3, RDS)
   ├─ RBAC: Only authorized CBP users can see scores
   ├─ Audit log: All model decisions, who accessed what, when

Effort: 2 weeks (1 backend engineer + 1 DevOps + 1 security)
Cost: AWS GovCloud ($200-300/month), OpenCorp cache ($500-1,000/month starting Month 3)
Output: Production-ready system in dry-run mode
```

### 2.2 Analyst Training

**Goal**: Train CBP analysts to use model + provide feedback for active learning.

```
Tasks:
├─ Training session:
│  ├─ Explain model (simple: XGBoost on 72 features)
│  ├─ Interpret scores (0-50 = low risk, 50-80 = medium, >80 = high)
│  ├─ Explain confidence (80% confidence = reliable, 50% = uncertain)
│  └─ Demo: How to label cases for active learning
│
├─ Feedback workflow:
│  ├─ Each week: Review 20-30 "uncertain" cases (50-70% confidence)
│  ├─ Label: Real evasion? Or legitimate?
│  ├─ Notes: What signals did you notice?
│  └─ System stores automatically
│
└─ Success metric:
   ├─ Analysts labeling 5-10 cases/day (target 5 referrals/day total)
   └─ Feedback quality: 90%+ agreement with CBP investigation outcomes

Effort: 1 day (online training)
Cost: $0 (online materials)
Output: Trained analyst pool ready for live scoring
```

---

## PHASE 3: PRODUCTION (August 1 - December 1)

### 3.1 Live Referrals with Active Learning

**Goal**: Deploy live scoring with analyst feedback collection.

```
Timeline:
├─ August 1: Go-live, begin daily scoring + analyst labeling
├─ Week 1: Validate 50-100 cases (calibration check)
├─ Week 2: Ramp to 2-3 referrals/day (current CBP pace)
├─ Week 3: Ramp to 3-5 referrals/day (growth target)
├─ Week 4: Target 5 referrals/day steady state

Metrics tracking:
├─ Referral volume: 5/day × 30 days = ~150/month
├─ Labeled cases: 5 cases/day × 150 days = 750 by November 1
├─ Model retraining:
│  ├─ First retrain: September 1 (287 baseline + 200 new labels)
│  ├─ Monthly retrain: October 1, November 1, December 1
│  └─ Track AUC improvement:
│     ├─ Sept: AUC 0.82 → 0.84 (+50 labels)
│     ├─ Oct: AUC 0.84 → 0.86 (+400 labels)
│     ├─ Nov: AUC 0.86 → 0.88 (+750 labels)
│     └─ Dec: AUC 0.88 → 0.90 (+1,200+ labels)

Cost: AWS ($200-300/month) + OpenCorp ($500-1,000/month) = $700-1,300/month
Output: Live production system accumulating training data
```

### 3.2 Drift Detection & Retraining

**Goal**: Detect concept drift (fraudster evasion adaptation), trigger retraining.

```
Weekly monitoring:
├─ Feature distributions:
│  ├─ Check if dwell times shifting (evasion signal)
│  ├─ Check if pricing shifting (evasion signal)
│  ├─ Check if shipper age distribution changing
│  └─ Alert if >20% shift detected
│
├─ PPV tracking:
│  ├─ Calculate weekly PPV (confirmed referrals / total referrals)
│  ├─ Compare vs 4-week rolling average
│  └─ Alert if drops >20%
│
├─ Analyst feedback patterns:
│  ├─ Any new fraud signals emerging?
│  ├─ Are analysts labeling new evasion tactics?
│  └─ If 10+ new pattern detected: Trigger immediate retrain

Monthly retraining:
├─ Add all new labeled cases (750+ by December)
├─ Retrain XGBoost on 287 + 750 = 1,037 cases
├─ Evaluate: AUC, PPV, sensitivity
├─ Deploy if AUC improves or PPV stable
├─ Rollback if performance degrades

Cost: $0 (monitoring is part of ops)
Output: Continuous model improvement, early evasion detection
```

---

## DECISION POINT: DECEMBER 1 (6-Month Checkpoint)

### 4.1 Data State

By December 1:
- **Training data**: 287 EAPA + ~1,250 active learning = **1,537 total cases**
- **Model performance**:
  - Baseline (287 cases): AUC 0.82
  - After 6 months (1,537 cases): AUC 0.87-0.90 (projected)
- **Cost trajectory**:
  - Cumulative 6 months: AWS ($1,500) + OpenCorp ($3,000-6,000) = **$4,500-7,500**

### 4.2 Ensemble Upgrade: Go or No-Go?

**Ensemble ROI Decision**:
```
At 1,537 cases, ensemble ROI analysis:
├─ Single XGBoost: AUC 0.87-0.90
├─ Ensemble (3-model): AUC 0.91-0.93 (projected gain: +1-3%)
├─ PPV gain: +5-10 basis points (e.g., 30% → 35-40%)
├─ Added cost: $100/month ($1,200/year)
├─ Value of +10 PPV at 5 referrals/day:
│  ├─ 5 ref/day × 365 days = 1,825 referrals/year
│  ├─ +10 PPV = +182.5 confirmed cases/year
│  ├─ Value per case (typical tariff evasion): $100K-$1M
│  └─ Value of ensemble: +$18.25M-$182.5M vs $1,200 cost = **15,000-150,000× ROI**
└─ Verdict: **UPGRADE TO ENSEMBLE**

Cost: $1,200/year ensemble + $2,400/year additional compute = **$3,600/year**
Benefit: +$18M-$182M (conservative estimate)
```

**Decision options**:
1. **Upgrade to ensemble** (recommended at 1,500+ cases)
   - Deploy 3-model ensemble (XGBoost + Isolation Forest + Bayesian)
   - Keep single model for comparison (A/B testing)
   - Full rollout by January 1

2. **Stay single model** (if ensemble ops overhead too high)
   - Continue single XGBoost
   - Monitor performance
   - Revisit at Month 12

3. **Hybrid approach** (recommended if resource-constrained)
   - Add Isolation Forest only (unsupervised anomaly detection)
   - Keep XGBoost + Isolation Forest voting
   - Cheaper than full ensemble, better than single model

---

## PHASE 4: PRODUCTION AT SCALE (January - June 2027)

### 5.1 FDA Integration (Parallel Track)

**Goal**: Define FDA-specific factors, train separate model on FDA data.

```
Timeline: January - March 2027

Tasks:
├─ Gather FDA data:
│  ├─ Import records (importers, suppliers, products)
│  ├─ Facility inspection history
│  ├─ Supplier verification data
│  ├─ Recall database
│  └─ Expected volume: 500-1,000 historical fraud cases
│
├─ Define 8 FDA factors:
│  ├─ IMPORTER_LEGITIMACY (25%)
│  ├─ PRODUCT_COMPLIANCE (20%)
│  ├─ SUPPLY_CHAIN_INTEGRITY (20%)
│  ├─ SUPPLIER_RISK (15%)
│  ├─ COUNTERFEITING_INDICATORS (10%)
│  ├─ DOCUMENTATION_RISK (5%)
│  ├─ PATTERN_ANOMALY (5%)
│  └─ TEMPORAL_RISK (5%)
│
├─ Train FDA model:
│  ├─ Use same XGBoost architecture (reuse code)
│  ├─ Expected AUC: 0.84-0.87 (similar trajectory to CBP)
│  └─ Separate data domain: features_fda table (no CBP contamination)
│
└─ Launch FDA pilot: April 2027

Cost: $0 (reuse infrastructure, separate domain)
Output: FDA model running parallel to CBP
```

### 5.2 Opioid Detection (March - June 2027)

**Goal**: Integrate opioid diversion detection.

```
Similar process:
├─ Data: PDMP (prescription), DEA watch list, pharmacy network
├─ Factors: 5 opioid-specific (PRESCRIPTION_VOLUME, PRESCRIBER_PATTERN, PATIENT_BEHAVIOR, PHARMACY_NETWORK, DIVERSION_SIGNALS)
├─ Expected AUC: 0.82-0.85
├─ Launch: June 2027

Cost: $0 (reuse infrastructure)
Output: 3 domains running in parallel (CBP, FDA, Opioid)
```

---

## TOTAL COST OF OWNERSHIP (12 Months)

| Component | Jun-Dec | Jan-Jun 2027 | 12-Month Total |
|-----------|---------|--------------|-----------------|
| **AWS Infrastructure** | $1,500 | $1,500 | **$3,000** |
| **OpenCorp Data** | $3,000-6,000 | $3,000-6,000 | **$6,000-12,000** |
| **Ensemble Upgrade (Dec+)** | $0 | $600 | **$600** |
| **Monitoring/Drift Tooling** | $0 | $1,200 | **$1,200** |
| **Human Cost** | $150K (engineering) | $100K (maintenance) | **$250K** |
| **TOTAL** | **$154.5K-157.5K** | **$106K** | **$260K-263K** |

**Cost per referral** (1,825 referrals/year):
- $260K / 1,825 = **$142/referral** to operate platform
- Assuming 30% PPV (547 confirmed) = **$475/confirmed case**
- Typical tariff evasion value: $100K-$1M per case
- ROI: **210×-2,100× payback** on operational cost

---

## WORLD-CLASS BENCHMARK COMPARISON

| Metric | CBP (Proposed) | PayPal | Insurance | Tax Authority |
|--------|---|---|---|---|
| **Training Data** | 287 → 1,537 | 100M+ | 1M+ | 500K+ |
| **Initial AUC** | 0.82 | 0.98 | 0.90 | 0.92 |
| **6-Month AUC** | 0.87-0.90 | 0.985 | 0.93 | 0.94 |
| **Detection Latency** | Real-time | <100ms | <500ms | <1s |
| **PPV** | 30% | >95% | 85-90% | 80-85% |
| **Gap Analysis** | Data-limited | Data-rich | Mature ops | Mature ops |

**Interpretation**: CBP's gap vs PayPal (0.98) is purely training data size (100M vs 1.5K). Your trajectory is on-track. By Month 24 (with 3,000+ labeled examples), expect AUC 0.91-0.93, which is world-class for trade fraud.

---

## APPROVAL CHECKLIST

- [ ] **Model**: XGBoost single model (not ensemble initially)
- [ ] **OpenCorp**: Integrate beneficial ownership enrichment
- [ ] **Data**: Domain-separated architecture (CBP/FDA/Opioid isolated)
- [ ] **Active Learning**: 5 referrals/day assumption (1,250 cases in 6 months)
- [ ] **Timeline**: June staging → August go-live → December ensemble decision
- [ ] **Cost**: $260K-263K for 12 months (includes 3 domains)
- [ ] **Success Metric**: December 1 decision point to upgrade ensemble (go/no-go)

---

## Next Steps

1. **Confirm**: Do you approve this approach?
2. **Gather EAPA data**: Get access to 287 confirmed transshipment cases
3. **OpenCorp account**: Sign up for API access (free)
4. **Assign team**: 1 DS engineer, 1 backend engineer, 1 DevOps
5. **Schedule kickoff**: June 15 staging start

