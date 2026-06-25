# Risk Scoring Engine: Decision Framework with Data-Backed Alternatives

**Based on**: CBP scope research, production system benchmarks, financial fraud comparisons  
**Data source**: 25.4M TEU/year, $10B illegal transshipment, 89 EAPA cases (2025), $400M detected, 4-5% detection rate  
**Quality level**: Production systems (not theoretical)

---

## DECISION 1: Model Architecture

**The Problem**: Single LightGBM vulnerable to adversarial evasion. Fraudsters adapt in 6-18 months. Need robustness.

**Context from Research**:
- Financial fraud ensembles: +5-7% accuracy improvement over single models
- Stacking (meta-learner + base learners): 95% acc, 93% recall, 94% F1-score (best in production)
- XGBoost alone: AUC 0.994 in some studies, 0.82 F1 in imbalanced datasets
- Customs fraud (real CBP data): 56-99% accuracy range (imbalance-dependent)
- India Customs production: Ensemble approach with daily real-time alerts
- EU Customs: Random Forest + Autoencoders (unsupervised + supervised hybrid)

---

### ALTERNATIVE 1A: Single Model (LightGBM Only)

```
Architecture:
├─ Gate 1: 8 deterministic rules (high precision)
├─ Gate 2: Single LightGBM classifier (supervised learning)
│  └─ Trained on 287 EAPA cases + Gate 1 outcomes (~45 confirmed by CBP)
├─ Gate 3: Confidence intervals from LightGBM probability calibration
└─ Output: Score + confidence band

Features: 72 engineered features (commodity, party, dwell, pricing, etc.)
Retraining: Monthly
Explainability: SHAP feature importance, decision trees for audit
```

**Pros:**
- ✓ Simple (one model, one codebase)
- ✓ Fast inference (single forward pass)
- ✓ LightGBM is proven in customs (Exiger contract uses similar approach)
- ✓ Explainable via SHAP/LIME

**Cons:**
- ✗ Vulnerable to adversarial evasion (if fraudsters learn feature weights, classification flips with small nudges)
- ✗ No backup if single model fails
- ✗ Class imbalance (3.2% transshipment) difficult to handle; single model overconfident on majority class
- ✗ Once fraudsters discover thresholds (e.g., "unit price >$0.75 = safe"), tactics adapt
- ✗ Concept drift undetected until PPV collapses

**Performance Estimate** (based on research):
- AUC: 0.82-0.85 (imbalanced data)
- PPV @ 80% confidence: ~30-50%
- Sensitivity: ~70% (catching 7 of 10 real schemes)
- Vulnerability: Moderate (single point of failure)

**Cost**: $0 (no additional infrastructure)

**Decision criteria**: Choose if you prioritize simplicity + fast time-to-market over adversarial robustness

---

### ALTERNATIVE 1B: Ensemble (3-Model Voting)

```
Architecture:
├─ Gate 1: 8 deterministic rules (high precision)
├─ Gate 2: 3-Model Ensemble (voting)
│  ├─ Model A: LightGBM (gradient boosting)
│  │  └─ Feature: Structured data (commodity, shipper age, pricing)
│  ├─ Model B: Isolation Forest (unsupervised anomaly detection)
│  │  └─ Feature: Combined feature space (detecting novel combinations)
│  └─ Model C: Bayesian Network (probabilistic reasoning)
│     └─ Feature: Domain expert structure (causal relationships)
│
├─ Decision Logic:
│  ├─ All 3 agree (same class): HIGH CONFIDENCE (90%+)
│  ├─ 2 out of 3: MEDIUM CONFIDENCE (70-80%)
│  └─ 1 out of 3: LOW CONFIDENCE (<70%)
│
└─ Output: Score + confidence + which models triggered

Retraining: Model A (monthly), Model B (weekly), Model C (quarterly)
Explainability: SHAP for LightGBM, isolation path for Isolation Forest, DAG for Bayesian
```

**Pros:**
- ✓ Robust to adversarial evasion (if LightGBM fooled, Isolation Forest catches novel patterns)
- ✓ Unsupervised (Isolation Forest) catches schemes without labeled training data
- ✓ Explainability (Bayesian network provides causal reasoning: "why this score?")
- ✓ Handles concept drift better (models retrain at different frequencies)
- ✓ Proven in production (EU Customs uses similar; financial fraud stacking ensembles are gold standard)

**Cons:**
- ✗ Complex (3 models, integration logic, different hyperparameters)
- ✗ Slower inference (3x forward passes)
- ✗ More operational overhead (monitoring 3 models, 3 drift detectors)
- ✗ Harder to explain to CBP officers ("why did 2 out of 3 models agree?")
- ✗ More engineering effort

**Performance Estimate** (based on ensemble research):
- AUC: 0.88-0.92 (ensemble gain: +5-7% over single)
- PPV @ 80% confidence: 40-60%
- Sensitivity: 75-80% (catching 7.5-8 of 10 real schemes)
- Vulnerability: Low (multiple models degrade gracefully)

**Cost**: ~$50-100/month for additional compute (3x inference, weekly retraining)

**Decision criteria**: Choose if adversarial robustness matters + you have ops team

---

### ALTERNATIVE 1C: Ensemble Stacking (Meta-Learner)

```
Architecture:
├─ Gate 1: 8 deterministic rules
├─ Gate 2: Stacking Ensemble (production gold standard)
│  ├─ Base Layer (L0):
│  │  ├─ Learner 1: LightGBM (features: commodity, shipper, pricing)
│  │  ├─ Learner 2: Random Forest (features: different feature subset)
│  │  ├─ Learner 3: Gradient Boosting (XGBoost)
│  │  └─ Learner 4: Logistic Regression (baseline)
│  │
│  ├─ Meta Layer (L1):
│  │  └─ Meta-Learner: Logistic Regression on [L0 predictions]
│  │     └─ Learns optimal way to combine base learner outputs
│  │
│  └─ Output: Meta-learner score (theoretically optimal combination)
│
├─ Training:
│  ├─ L0 models: 5-fold CV to prevent data leakage
│  ├─ L1 meta-learner: Hold-out validation set
│  └─ Outer 5-fold CV for performance estimate
│
└─ Retraining: Monthly (full stack)
```

**Pros:**
- ✓ Gold standard for financial fraud (95% acc, 93% recall, 94% F1)
- ✓ Automatically learns optimal combination (vs voting = equal weight)
- ✓ Best performance documented in production (Nature, PMC studies)
- ✓ Handles imbalanced data better than single models
- ✓ Explainable (L0 model importance + meta-learner weights)

**Cons:**
- ✗ Complex training pipeline (cross-validation architecture)
- ✗ Slower inference (4+ base models + meta-learner)
- ✗ Data requirement (need holdout for meta-learner training)
- ✗ Highest operational overhead

**Performance Estimate** (financial fraud research):
- AUC: 0.92-0.96
- PPV: 45-70%
- Sensitivity: 80-90%
- Vulnerability: Very low

**Cost**: $100-200/month compute + engineering overhead

**Decision criteria**: Choose if you need highest accuracy + have resources for complex ops

---

### ALTERNATIVE 1D: Gradient Boosting + Active Learning (Adaptive)

```
Architecture:
├─ Gate 1: 8 deterministic rules
├─ Gate 2: XGBoost with dynamic retraining
│  ├─ Initial model: Trained on 287 EAPA cases
│  ├─ Monthly retraining: Add Gate 1 confirmed outcomes (feedback loop)
│  ├─ Active learning: Analyst reviews uncertain predictions (<60% confidence)
│  │  └─ Hard cases labeled by CBP analyst → added to training set
│  └─ Adaptive thresholds: Weekly threshold adjustment based on recent PPV
│
├─ Drift detection:
│  ├─ Monitor feature distributions (dwell, price, shipper age)
│  ├─ Alert if significant shift detected
│  └─ Trigger retraining if PPV drops >20% week-over-week
│
└─ Output: Score + confidence + uncertainty quantification
```

**Pros:**
- ✓ Improves over time (active learning + feedback loop)
- ✓ Adapts to drift (detects evasion adaptation automatically)
- ✓ Cost-effective (leverage CBP analyst feedback)
- ✓ Explainable (XGBoost SHAP)
- ✓ Realistic (aligns with actual CBP workflow)

**Cons:**
- ✗ Requires analyst labeling effort (10-20 cases/month)
- ✗ Slower to deploy (active learning infrastructure needed)
- ✗ Still single model (less robust than ensemble)
- ✗ Requires drift monitoring system

**Performance Estimate**:
- Initial AUC: 0.82 (single model)
- After 6 months active learning: 0.87-0.89 (with feedback loop)
- Sensitivity improvement: +5-10% after 3 months
- Adaptation: Detects evasion shifts within 2-4 weeks

**Cost**: $50/month compute + analyst time

**Decision criteria**: Choose if you want continuous improvement + have analyst feedback loop

---

## Recommendation: Model Architecture

**For CBP Illegal Transshipment**: **ALTERNATIVE 1D (Gradient Boosting + Active Learning)**

**Why:**
1. **Adversarial robustness**: Retraining monthly + drift detection catches evasion faster than static models
2. **Practical**: Aligns with actual CBP workflow (analyst feedback)
3. **Cost-effective**: $50/month vs $100-200 for stacking
4. **Proven**: Similar to India Customs production system (real-time alerts + feedback)
5. **Scalable**: Can upgrade to stacking later if needed

**Phase 2 upgrade**: Add Isolation Forest (unsupervised) if evasion still adapts

---

## DECISION 2: Gate 1 Rule Architecture

**The Problem**: Current 8 manual rules are threshold-based, vulnerable to evasion. "Dwell >5x baseline" is discoverable.

**Context from Research**:
- CBP current approach: 8 rules with fixed thresholds (Element 9, OFAC, corridor risk, dwell, shipper age, pricing, hub ports, ISF amendments)
- Data-driven approach: Estimate distributions from legitimate shipments, use percentiles instead of multiples
- Anomaly detection: Isolation Forest catches novel patterns unseen in training
- India Customs: Supplier codification + entity-level targeting (learned from data)

---

### ALTERNATIVE 2A: Pure Deterministic Rules (Current)

```
8 Manual Rules:
├─ Rule 1: Element 9 mismatch → +20 pts
├─ Rule 2: OFAC hit → +25 pts
├─ Rule 3: Corridor + duty >15% → +15 pts
├─ Rule 4: Dwell >5x baseline → +18 pts
├─ Rule 5: New shipper + $100K+ → +10 pts
├─ Rule 6: Pricing <85% market → +12 pts
├─ Rule 7: Hub port + dwell → +14 pts
└─ Rule 8: ISF amendments >3 → +12 pts

Corroboration: ≥3 independent sources before referral
```

**Pros:**
- ✓ Explainable (easy for officer to understand)
- ✓ Implementable immediately
- ✓ Currently in CBP codebase (no rework)
- ✓ Works for Gate 1 (high precision, low recall)

**Cons:**
- ✗ Fragile thresholds (5x baseline becomes common knowledge)
- ✗ No adaptation (same rules after 1 year)
- ✗ Missing sophisticated schemes (false negatives)
- ✗ Easy to evade (adjust one feature below threshold)
- ✗ No data-driven justification (why >5x, not >4x?)

**Performance Estimate** (from CBP document):
- PPV: 10% (target met)
- Sensitivity: 71% (from EAPA backtest)
- Referral volume: 2-3/week

**Vulnerability**: High (fraudsters adapt in 6-12 months)

**Cost**: $0

**Decision criteria**: Choose ONLY as MVP (first 3 months); plan upgrade

---

### ALTERNATIVE 2B: Data-Driven Thresholds (Hybrid)

```
3 Critical Rules (Manual):
├─ Rule 1: OFAC hit → CRITICAL (binary, no threshold)
└─ Rule 2: Element 9 exact mismatch → HIGH (binary, no threshold)

5 Learned Rules (Threshold-based, percentile-driven):
├─ Rule 3: Dwell anomaly → 95th percentile of legitimate dwell (commodity-specific)
│  └─ Instead of "5x baseline", use "dwell > $P95(commodity)"
│  └─ Data-driven, automatically adapts with new shipments
│
├─ Rule 4: Pricing anomaly → 5th percentile of market price (commodity-specific)
│  └─ Instead of "85% market", use "price < $P5(market)"
│
├─ Rule 5: Shipper age + volume anomaly → IQR-based (Tukey outliers)
│  └─ age < $Q1 AND value > $Q3 = outlier combination
│
├─ Rule 6: Entity network anomaly → co-occurrence risk score
│  └─ Shipper + Consignee + Vessel operator combination never seen = flag
│
└─ Rule 7: Port-corridor mismatch → Bayes probability
   └─ P(origin_country | port_of_stuffing) - if low, flag

Recalibration: Monthly (percentiles updated from new shipments)
```

**Pros:**
- ✓ Learned from data (not arbitrary)
- ✓ Adaptive (thresholds shift as fraudster tactics evolve)
- ✓ Balances manual rules (critical ones) with learned rules (subtle patterns)
- ✓ Reduces false positives (outlier-based, not threshold-based)
- ✓ Explainable ("shipper age in bottom 1% of distribution")

**Cons:**
- ✗ Requires monthly recalibration (ops overhead)
- ✗ Less explainable to non-technical officers
- ✗ Data quality dependency (bad data → bad thresholds)
- ✗ Still rule-based (not ML-based)

**Performance Estimate**:
- PPV: 12-15% (improve vs 10%)
- Sensitivity: 75-78% (improve vs 71%)
- Referral volume: 2.5-3.5/week

**Vulnerability**: Medium (harder to evade, but still possible)

**Cost**: $20/month (automated threshold calculation)

**Decision criteria**: Choose for Month 2-3 after MVP

---

### ALTERNATIVE 2C: Hybrid (Manual + Anomaly Detection)

```
Gate 1 Tier 1 (Manual Rules - Precision >95%):
├─ OFAC/SDN hit → Immediate referral
└─ Element 9 exact mismatch → Immediate referral

Gate 1 Tier 2 (Learned Rules - Percentile-based):
├─ Dwell >95th percentile
├─ Pricing <5th percentile
├─ Shipper age <Q1 + volume >Q3
└─ Corroboration: ≥2 of these signals

Gate 1 Tier 3 (Unsupervised Anomaly Detection):
├─ Isolation Forest on [dwell, pricing, shipper_age, vessel_flag, shipper_country]
│  └─ Catches novel combinations unseen in training
├─ Local Outlier Factor on normalized features
│  └─ Density-based: spot local clusters of anomalies
└─ Flags: Feature combination is rare (top 1% anomaly score)

Corroboration Decision:
├─ Tier 1 signal alone: REFER (CRITICAL)
├─ Tier 2 signals ≥2: REFER (HIGH RISK)
├─ Tier 3 anomaly + Tier 2 signal: REFER (ELEVATED RISK)
└─ Tier 3 anomaly alone: Hold for Gate 2 (SUSPICIOUS)
```

**Pros:**
- ✓ Multi-layered defense (deterministic + learned + unsupervised)
- ✓ Catches novel schemes (Isolation Forest finds combinations not in training)
- ✓ Automatic adaptation (anomaly detection retrains weekly)
- ✓ Robust to evasion (hard to avoid all three tiers)
- ✓ Proven (EU Customs uses RF + Autoencoders, similar approach)

**Cons:**
- ✗ Complex (3 tiers of logic)
- ✗ Harder to explain (what's "anomaly score 0.87"?)
- ✗ Requires unsupervised model infrastructure
- ✗ False alarm risk (anomaly ≠ fraud)

**Performance Estimate**:
- PPV: 15-20%
- Sensitivity: 80-85%
- Referral volume: 3-4/week
- Novel scheme capture: +10-15% over rules alone

**Vulnerability**: Low (multiple layers, unsupervised catches novel patterns)

**Cost**: $30/month (Isolation Forest retraining + infrastructure)

**Decision criteria**: Choose if budget allows + want comprehensive defense

---

## Recommendation: Gate 1 Architecture

**For CBP**: **ALTERNATIVE 2C (Hybrid: Manual + Learned + Anomaly Detection)**

**Rationale:**
1. **Layered defense**: Manual (OFAC, Element 9) can't be evaded; learned rules adapt; anomaly detection catches novel schemes
2. **Research-backed**: EU Customs proved this works (RF + Autoencoder)
3. **Detection improvement**: +10-15% sensitivity gain over pure rules
4. **Cost-reasonable**: $30/month additional
5. **Evasion-resistant**: Fraudsters must evade ALL three layers

---

## DECISION 3: Feature Engineering Strategy

**The Problem**: Current 7 factors don't capture all transshipment signals. Missing: beneficial ownership, payment flows, supply chain variance.

**Context from Research**:
- **Most predictive features** (production customs systems):
  - Unit value deviation (top 2 in Indian ML models)
  - Port/dwell anomalies (known transshipment indicators)
  - Beneficial ownership opacity (69% higher risk if unknown)
  - Entity network connections (connected to known bad actors?)
  - Supplier codification (India Customs proven feature)
  - AIS signal anomalies (vessel tracking gaps)
  
- **Current CBP 7 factors** cover: commodity risk, documentation, routing, party, corridor, pattern, time
- **Missing**: Ownership transparency, financial flows, supply chain variance, historical port/operator signals

---

### ALTERNATIVE 3A: Current 7 Factors (No Enhancement)

```
Factor Engineering:
├─ DOCUMENTATION_RISK (25%)
│  ├─ ISF completeness
│  ├─ Element 9 consistency
│  └─ Manifest field accuracy
│
├─ ROUTING_RISK (15%)
│  ├─ AIS dwell
│  ├─ Port selection
│  └─ Vessel flag
│
├─ COMMODITY_RISK (15%)
│  ├─ Tariff code
│  ├─ AD/CVD rates
│  └─ Export controls
│
├─ CORRIDOR_RISK (20%)
│  ├─ Country pair (CN→US, VN→US, etc.)
│  └─ Corridor multipliers (1.5x for high-risk)
│
├─ PARTY_RISK (15%)
│  ├─ Shipper age
│  ├─ OFAC match
│  └─ Prior violations
│
├─ PATTERN_RISK (10%)
│  ├─ ML anomaly (Isolation Forest)
│  └─ Pricing deviation
│
└─ TIME_SENSITIVITY (10%)
   ├─ Pre-tariff timing
   └─ Seasonal anomaly
```

**Pros:**
- ✓ Already implemented in codebase
- ✓ No additional data integration
- ✓ Fast to deploy

**Cons:**
- ✗ Missing critical signals (ownership, payment flows)
- ✗ Lower accuracy vs. enriched feature set
- ✗ Performance ceiling: ~0.82 AUC (estimated)

**Performance Estimate**: AUC 0.80-0.84

**Cost**: $0

**Decision criteria**: MVP only; plan enhancement

---

### ALTERNATIVE 3B: Enriched Features (Add Ownership + Supply Chain)

```
Current 7 Factors + 5 New Features:

New Feature 1: BENEFICIAL OWNERSHIP TRANSPARENCY
├─ Data source: Sayari Graph, OpenCorporates, jurisdiction risk
├─ Score: 0-100 (100 = fully transparent, 0 = unknown owner)
├─ Research: Opaque owners 69% higher risk in Moody's analysis
├─ Integration: Weekly lookup
└─ Importance estimate: 0.08 (8% of model)

New Feature 2: SHIPPER-CONSIGNEE RELATIONSHIP HISTORY
├─ Data source: Historical trade database
├─ Score: Have shipped together before? Frequency?
├─ Logic: One-off shipper-consignee pair = risk; repeat = lower risk
├─ Integration: Lookup CBP historical manifests
└─ Importance estimate: 0.07

New Feature 3: SUPPLY CHAIN VOLATILITY
├─ Data source: Supplier changes, payment pattern variance
├─ Score: Supplier stability index (same supplier vs. constantly changing)
├─ Logic: Transshipment schemes often use multiple suppliers simultaneously
├─ Integration: Finance/payment data (if available)
└─ Importance estimate: 0.06

New Feature 4: ENTITY NETWORK CLUSTERING
├─ Data source: Entity graph (Senzing + CORD)
├─ Score: Is shipper/consignee/vessel operator in network with known bad actors?
├─ Logic: Beneficial ownership networks reveal hidden connections
├─ Integration: L1/L2/L3 entity resolution + graph distance
└─ Importance estimate: 0.07

New Feature 5: VESSEL OPERATOR RISK PROFILE
├─ Data source: AIS history, vessel age, flag-hopping, ownership changes
├─ Score: Vessel operator reputation (known to enable evasion?)
├─ Logic: Certain operators facilitate transshipment for hire
├─ Integration: MarineTraffic, IMO registry, Windward data
└─ Importance estimate: 0.06

Recalibration: Monthly for ownership/network data
```

**Pros:**
- ✓ Addresses known gaps (beneficial ownership, supply chain)
- ✓ Proven predictive (69% higher risk for opaque owners)
- ✓ Better accuracy: +10-15% AUC improvement
- ✓ Catches sophisticated schemes (network-based detection)

**Cons:**
- ✗ Data integration complexity (4-5 new data sources)
- ✗ Cost: $50-100/month (data licensing)
- ✗ Latency: Entity resolution adds 200-500ms per shipment
- ✗ Data quality risk (reliance on external providers)

**Performance Estimate**: AUC 0.88-0.92, PPV +20-30%

**Cost**: $100-150/month (data licensing + integration)

**Decision criteria**: Choose if you have budget + data partnerships

---

### ALTERNATIVE 3C: Modular Feature Architecture

```
Core Features (Always Enabled):
├─ DOCUMENTATION_RISK
├─ ROUTING_RISK
├─ COMMODITY_RISK
├─ CORRIDOR_RISK
├─ PARTY_RISK
├─ PATTERN_RISK
└─ TIME_SENSITIVITY

Premium Features (Optional, Licensed):
├─ BENEFICIAL_OWNERSHIP_TRANSPARENCY (requires Sayari/OpenCorp)
├─ ENTITY_NETWORK_RISK (requires CORD + entity resolution)
└─ SUPPLY_CHAIN_VOLATILITY (requires trade finance data)

Domain-Specific Features (Togglable):
├─ For CBP: Tariff-specific, port-specific
├─ For FDA: Facility inspection history, supplier compliance
├─ For Opioid: Prescriber network, patient pattern

Feature Store Architecture:
├─ Core features: DuckDB (immediate)
├─ Premium: Lazy-load on demand (if data available)
├─ Fallback: Skip feature if unavailable, use 0 or mean imputation
└─ Monitoring: Track which features available per shipment
```

**Pros:**
- ✓ Flexible (MVP with core 7, enhance with premium)
- ✓ Cost-scalable (pay for data only if you use it)
- ✓ Modular (can add/remove features without retraining)
- ✓ Works across domains (CBP/FDA/Opioid with different features)

**Cons:**
- ✗ Missing features = performance loss
- ✗ More complex architecture (feature fallback logic)
- ✗ Inconsistent predictions (shipment with ownership data vs without)

**Performance Estimate**:
- MVP (7 features): AUC 0.82
- With premium (12 features): AUC 0.89

**Cost**: $0-150/month (depending on licenses)

**Decision criteria**: Choose if you want flexibility + phased rollout

---

## Recommendation: Feature Engineering

**For CBP MVP**: **ALTERNATIVE 3C (Modular)**

**Rationale:**
1. **Phased approach**: Start with 7 factors, add ownership + network as data partnerships mature
2. **Cost-efficient**: Pay for premium features only if you have access
3. **Cross-domain**: Same architecture works for FDA/Opioid with different feature toggles
4. **Risk-managed**: Core features proven, premium are enhancements

**Phase 1 (Months 1-3)**: 7 core factors  
**Phase 2 (Months 4-6)**: Add beneficial ownership (license Sayari or OpenCorp)  
**Phase 3 (Months 7+)**: Add entity network + supply chain

---

## DECISION 4: Generalization Strategy (CBP → FDA → Opioid)

**The Problem**: 7-factor CBP model doesn't fit FDA/Opioid equally. Need framework that scales.

**Context from Research**:
- **CBP**: Transport + tariff fraud (7 factors fit well)
- **FDA**: Supply chain fraud (similar structure, different data sources)
- **Opioid**: Behavioral + prescription fraud (different paradigm entirely)

---

### ALTERNATIVE 4A: Single Unified Model (One Factor Set for All)

```
"Universal Risk Model"

7 Factors (reinterpreted for all domains):
├─ DOCUMENTATION_RISK
│  ├─ CBP: ISF, manifest
│  ├─ FDA: Facility registration, cert of analysis
│  └─ Opioid: Prescription legitimacy
│
├─ ROUTING_RISK
│  ├─ CBP: Port/vessel routing
│  ├─ FDA: Supply chain routing
│  └─ Opioid: Prescriber-patient routing (unusual locations?)
│
[... same for all 7 factors, reinterpreted per domain]
```

**Pros:**
- ✓ Single codebase (one model architecture)
- ✓ Cross-domain transfer learning (train on CBP, fine-tune for FDA)

**Cons:**
- ✗ Forced fit (some factors don't apply to Opioid)
- ✗ Lower accuracy per domain (generic model wins on none)
- ✗ Factors don't align well (Opioid's "routing risk" is weak concept)
- ✗ Poor performance (expected 10-15% AUC loss vs domain-specific)

**Performance Estimate**:
- CBP: AUC 0.80 (vs 0.92 if optimized)
- FDA: AUC 0.75 (vs 0.88 if optimized)
- Opioid: AUC 0.70 (vs 0.85 if optimized)

**Cost**: $0 (no additional models)

**Decision criteria**: Choose ONLY if forced to single codebase; performance trade-off unacceptable

---

### ALTERNATIVE 4B: Domain-Specific Factor Sets (Recommended)

```
Domain Architecture:

CBP Illegal Transshipment (7 factors)
├─ DOCUMENTATION_RISK (25%)
├─ ROUTING_RISK (15%)
├─ COMMODITY_RISK (15%)
├─ CORRIDOR_RISK (20%)
├─ PARTY_RISK (15%)
├─ PATTERN_RISK (10%)
└─ TIME_SENSITIVITY (10%)

FDA Imports Fraud (8 factors)
├─ IMPORTER_LEGITIMACY (25%) - facility registration, compliance history
├─ PRODUCT_COMPLIANCE (20%) - lab results, supplier verification
├─ SUPPLY_CHAIN_INTEGRITY (20%) - traceability, supplier reputation
├─ SUPPLIER_RISK (15%) - facility inspections, prior recalls
├─ COUNTERFEITING_INDICATORS (10%) - packaging, serial numbers
├─ DOCUMENTATION_RISK (5%) - cert of analysis, inspection reports
├─ PATTERN_ANOMALY (5%) - unusual product combinations
└─ TEMPORAL_RISK (5%) - seasonal patterns

Opioid Detection (5 factors)
├─ PRESCRIPTION_VOLUME (25%) - daily quantity spikes, pill count
├─ PRESCRIBER_PATTERN (25%) - specialty mismatch, license status, DEA history
├─ PATIENT_BEHAVIOR (20%) - doctor shopping, pharmacy hopping, demographics
├─ PHARMACY_NETWORK (20%) - facility type, inspection history, ownership
└─ DIVERSION_SIGNALS (10%) - DEA watch list, theft reports, rogue operator flags

Shared Architecture (All Domains):
├─ 3-Gate progression (deterministic → ML → Bayesian)
├─ Ensemble models (LightGBM + Isolation Forest + Bayesian)
├─ Same monitoring/retraining infrastructure
├─ Same V2AITuningPage framework (load factors per domain)
└─ Same storage (DuckDB params + PostgreSQL scores)
```

**Pros:**
- ✓ Optimized per domain (factors chosen for maximum predictiveness)
- ✓ Best accuracy per domain (AUC 0.88-0.92 each)
- ✓ Shared infrastructure (one retraining pipeline, one monitoring system)
- ✓ Proven approach (EU Customs, India Customs use domain-specific features + shared infra)

**Cons:**
- ✗ More engineering (3x feature engineering, 3x model tuning)
- ✗ Requires domain expertise (who defines FDA factors?)
- ✗ More monitoring (3 models to track)

**Performance Estimate**:
- CBP: AUC 0.90-0.92
- FDA: AUC 0.87-0.89
- Opioid: AUC 0.85-0.88

**Cost**: $100-150/month (3x infrastructure, shared)

**Decision criteria**: Choose if you have domain experts + budget

---

### ALTERNATIVE 4C: Hierarchical Model (Parent + Domain-Specific)

```
Hierarchical Architecture:

Parent Layer (Universal Risk Classifier)
├─ Detects: "Is this transaction/entity generally risky?"
├─ Features: Behavioral (volume, frequency), entity (age, history)
├─ Output: Baseline risk score (0-100)
└─ Applies to all domains

Domain Layers (Specialized Detectors)
├─ CBP Layer: Adds tariff-specific, routing-specific features
├─ FDA Layer: Adds supply-chain-specific, facility-specific features
├─ Opioid Layer: Adds prescriber-specific, patient-specific features

Final Score = Parent Score + Domain Score
```

**Pros:**
- ✓ Captures universal patterns (all fraud is risky)
- ✓ Adds domain specificity (tariff fraud ≠ opioid diversion)
- ✓ Transfer learning (train parent on CBP, adapts to FDA/Opioid)
- ✓ Balanced approach (shared + specialized)

**Cons:**
- ✗ Complex training logic (parent + domain models)
- ✗ Harder to debug (score from two sources)
- ✗ Less studied (not standard in customs/fraud literature)

**Performance Estimate**:
- CBP: AUC 0.86-0.88
- FDA: AUC 0.83-0.85
- Opioid: AUC 0.80-0.82

**Cost**: $120-180/month

**Decision criteria**: Choose if you want elegant trade-off between unified + domain-specific

---

## Recommendation: Generalization Strategy

**For Multi-Domain Success**: **ALTERNATIVE 4B (Domain-Specific Factor Sets + Shared Architecture)**

**Rationale:**
1. **Performance**: 10-15% AUC gain vs unified model
2. **Research-backed**: EU/India/Singapore all use domain-specific features
3. **Shared infrastructure**: One monitoring/retraining pipeline reduces ops complexity
4. **Scalability**: Can add 4th, 5th domain by defining factors

**Execution**:
- **CBP**: Immediate (7 factors defined in existing docs)
- **FDA**: Months 4-6 (requires FDA domain expert, supply chain research)
- **Opioid**: Months 7-9 (requires DEA/PDMP data partnership)

---

## DECISION 5: Retraining Frequency & Drift Detection

**The Problem**: Fraudsters adapt in 6-18 months. Need automated detection of when model degrades.

**Context from Research**:
- **Vietnam route lag**: 6+ years from initial tariff to widespread adaptation
- **Recent evasion**: 6-18 month lag from CBP detection to fraudster adaptation
- **Financial fraud**: 3.8x evasion technique increase 2020→2024 (continuous evolution)
- **CBP current approach**: No documented drift detection; relies on PPV monitoring

---

### ALTERNATIVE 5A: Fixed Schedule Retraining

```
Monthly Retraining:
├─ First Friday of month: Retrain all models
├─ Add all Gate 1 confirmed outcomes from prior month
├─ Add all feedback from CBP analysts
├─ Deploy new model, rollback if performance worse
└─ Cost: $30/month (compute)

Changes detected: Only discovered via PPV trending (reactive)
```

**Pros:**
- ✓ Simple (automated schedule)
- ✓ Captures recent evasion tactics

**Cons:**
- ✗ Reactive (only discover drift AFTER it happens via lower PPV)
- ✗ Lag (up to 4 weeks before retraining runs)
- ✗ Over-retraining in stable months (wastes compute)
- ✗ Under-retraining in active evasion periods

**Performance Impact**:
- PPV decay: Detectable 3-4 weeks after evasion starts
- Recovery lag: 4+ weeks until next retraining

**Cost**: $30/month

**Decision criteria**: Choose as baseline; upgrade if budget allows

---

### ALTERNATIVE 5B: Automated Drift Detection (Recommended)

```
Continuous Monitoring (Real-Time):

Feature Distribution Monitoring:
├─ Weekly: Calculate 5th, 25th, 50th, 75th, 95th percentiles of each feature
├─ Compare vs. historical baseline (6-month rolling window)
├─ Alert if:
│  ├─ Dwell time distribution shifts >20%
│  ├─ Pricing distribution shifts >15%
│  ├─ Shipper age distribution shifts >25%
│  └─ New vessel operators appearing (>5% weekly new entrants)
└─ Data source: Historical manifests + real-time arrivals

PPV Trend Analysis:
├─ Weekly: Calculate PPV for each model confidence band
├─ Alert if:
│  ├─ Overall PPV drops >20% vs 4-week average
│  ├─ High-confidence predictions (>80%) drop in PPV
│  └─ Low-confidence predictions (50-70%) improve suddenly (model uncertainty shift)
└─ Trigger: Automatic retraining if alert fires

Trigger Logic:
├─ Alert (yellow): Investigate, prepare retraining
├─ Critical alert (red): Immediate retraining + emergency deployment
└─ Recovery confirmed: Continue monitoring, document learnings
```

**Pros:**
- ✓ Proactive (detect drift before PPV collapses)
- ✓ Faster response (days vs weeks)
- ✓ Efficient (retrain only when needed)
- ✓ Evidence-based (can show "here's when evasion started")

**Cons:**
- ✗ Complex (requires monitoring infrastructure)
- ✗ False alarms (seasonal variation can trigger alerts)
- ✗ More operational overhead

**Performance Impact**:
- Detection lag: 2-7 days after evasion shift
- Recovery lag: 5-10 days (faster retraining response)
- PPV maintained: 80%+ of baseline, vs 50-60% in delayed scenario

**Cost**: $80/month (monitoring + drift analysis)

**Decision criteria**: Choose if budget allows + evasion is ongoing concern

---

### ALTERNATIVE 5C: Active Learning (Analyst-Triggered Retraining)

```
Feedback Loop:

CBP Analyst Workflow:
├─ Weekly: Analyst reviews 20-30 "uncertain" cases (50-70% confidence)
├─ Analyst labels: "Real evasion" OR "Legitimate trade"
├─ Labels stored in feedback database
└─ After 10 labels in new pattern area: Trigger retraining

Pattern Detection:
├─ Monitor analyst labels for new common patterns
├─ If 10+ cases labeled same way in last month: New evasion tactic discovered
├─ Trigger weekly retraining to capture pattern
└─ Analyst gets early feedback loop (see model improve in real-time)

Retraining:
├─ On-demand when analyst labels threshold hit
├─ Minimal (add 10-20 new examples) vs full monthly retraining
├─ Faster deployment (1-2 days vs 4 weeks)
└─ Cost-efficient (only retrain when needed)
```

**Pros:**
- ✓ Leverages analyst expertise (humans discover patterns first)
- ✓ Fast response (1-2 days vs 4 weeks)
- ✓ Cost-efficient (retrain on-demand)
- ✓ Improves analyst engagement (see model learning)
- ✓ Proven in production (active learning is standard in fraud detection)

**Cons:**
- ✗ Requires analyst participation (10-20 labels/month)
- ✗ Depends on analyst quality
- ✗ Doesn't catch automated evasion (human review lag)

**Performance Impact**:
- Evasion detection: Depends on analyst review speed (2-10 days)
- PPV recovery: Fast (retraining within week)
- Adaptability: Excellent (learns from analyst feedback)

**Cost**: $50/month (infrastructure) + analyst time

**Decision criteria**: Choose if you have analyst capacity

---

## Recommendation: Retraining Strategy

**For CBP**: **ALTERNATIVE 5B (Automated Drift Detection) + Phase-In of 5C (Active Learning)**

**Rationale:**
1. **Dual defense**: Automated detection catches statistical drift, analysts catch business logic changes
2. **Cost-effective**: $80/month for drift + minimal analyst load
3. **Proven**: India Customs uses similar (daily retraining alerts)
4. **Evasion-resistant**: 6-18 month lag becomes 2-7 days early detection

**Phase 1 (Months 1-3)**: Fixed schedule (baseline)  
**Phase 2 (Months 4-6)**: Add drift detection ($80/month)  
**Phase 3 (Months 7+)**: Add analyst active learning feedback loop

---

## DECISION 6: Storage Architecture (Revisit)

**Updated context**: CBP processes 25M TEU/year = ~50K shipments/week = ~100K including air/rail.

---

### ALTERNATIVE 6A: DuckDB Only

```
All data in DuckDB:
├─ Rules parameters (tuning by analysts)
├─ Audit trail (change history)
├─ Scoring cache (shipment results)
└─ Feedback (CBP outcomes)
```

**Problem**: 100K scores/week = 5.2M rows/year in scoring cache. DuckDB local becomes slow.

**Pros**: $0 cost
**Cons**: Query slowdown, scaling pain at 10K+ shipments/day

---

### ALTERNATIVE 6B: DuckDB + PostgreSQL (Recommended)

```
DuckDB (Rules & Configuration):
├─ Rules definitions (immutable, in Git)
├─ Rule parameters (versioned, SCD Type 2)
├─ Audit trail (change events)
├─ Retraining triggers (drift alerts)
└─ Cost: $0 (local) → $50/month (MotherDuck Starter, if managed)

PostgreSQL (Shipment Scores):
├─ Scoring cache (100K/week = 5.2M/year)
├─ Performance metadata (AUC, PPV by score bin)
├─ Feedback data (CBP investigation outcomes)
└─ Cost: $50-150/month (AWS RDS, depends on size)

Git (Rule Definitions):
├─ v2.rules.yaml (immutable, code review gate)
├─ Factor definitions (per domain)
└─ Cost: $0

Total: $50-200/month
```

**Pros**:
- ✓ DuckDB for rules (temporal queries, version history)
- ✓ PostgreSQL for scores (optimized for OLTP, 100K inserts/day)
- ✓ Git for code (immutable, auditable)

**Cons**:
- ✗ Two databases (ops complexity)

---

### ALTERNATIVE 6C: Firestore + PostgreSQL

```
Firestore (Rules & Configuration):
├─ Real-time updates (if multi-analyst worldwide)
├─ Managed (no ops)
├─ Cost: ~$50-100/month (light usage)

PostgreSQL (Shipment Scores):
├─ Cost: $50-150/month

Total: $100-250/month (vs $50-200 for DuckDB)
```

**Verdict**: DuckDB + PostgreSQL (6B) is best ROI

---

## SUMMARY: Recommended Architecture

```
Model Architecture (Decision 1):
├─ XGBoost + Active Learning (Gradient Boosting)
├─ Monthly retraining + drift detection
├─ Performance: AUC 0.87-0.89 (vs 0.82 baseline)

Gate 1 Rules (Decision 2):
├─ Hybrid (Manual OFAC/Element9 + Learned percentiles + Anomaly)
├─ 3-tier defense: Precision > Recall > Anomaly
├─ Retraining: Weekly (Isolation Forest)

Features (Decision 3):
├─ 7 core factors (CBP) + Modular premium features
├─ Phase 2: Add beneficial ownership ($100/month)
├─ Phase 3: Add entity network + supply chain

Generalization (Decision 4):
├─ Domain-specific factor sets (CBP/FDA/Opioid)
├─ Shared infrastructure (same gates, monitoring, storage)

Retraining (Decision 5):
├─ Automated drift detection (weekly)
├─ Active learning feedback loop (optional Phase 2)

Storage (Decision 6):
├─ DuckDB (rules, audit) + PostgreSQL (scores)
├─ Git (rule definitions)
├─ Cost: $100-200/month

Expected Performance:
├─ CBP Gate 1: 15-20% PPV (vs 10% target)
├─ CBP Gate 2: 35-45% PPV (vs 30% target)
├─ Sensitivity: 80-85% (vs 71% baseline)
├─ Evasion detection: 2-7 days (vs 6-18 months)
```

---

**Approval needed on**:
1. Model architecture (single XGBoost vs ensemble)?
2. Gate 1 (hybrid vs pure rules)?
3. Feature licensing budget ($0 vs $100+/month for ownership data)?
4. Domain expertise (who defines FDA/Opioid factors)?
5. Analyst capacity (can they do active learning)?

