# Risk Scoring Engine Design Discussion
## Data Science Deep Dive: CBP, FDA, Opioid

**Purpose**: Validate architecture choices, identify optimization opportunities, plan generalization  
**Audience**: Design team making critical decisions (not implementation team)  
**Outcome**: Agreed-upon design + research gaps to fill

---

## Part 1: Critical Questions About Current CBP Architecture

### 1.1 Will the Current 7-Factor, 3-Gate, 8-Rule Design Catch Illegal Transshipment?

**Question 1: Class Imbalance Reality**

The CBP document states:
- Target: 10% PPV (2-3 referrals/week)
- EAPA training set: 287 confirmed cases
- But: How many total shipments per week? 10K? 100K?

```
If 50K shipments/week, 287 cases/year = 5.5 cases/week
Then 2-3 referrals/week = potentially 45-55% of real cases caught?
That's GOOD sensitivity.

But if 500K shipments/week, 287 cases/year = 5.5 cases/week
Then 2-3 referrals/week = only 36-55% sensitivity
That's CONCERNING.
```

**Data scientist perspective**: We don't know the denominator. What's the actual prevalence of illegal transshipment in CBP's data?

**What we need to know**:
1. Shipment volume per week (baseline denominator)
2. Confirmed transshipment rate (what % of shipments are actually illegal transshipment?)
3. Breakdown by corridor (CN→US vs CA→US has very different prevalence)
4. Breakdown by commodity (apparel vs aluminum vs chemicals)

---

**Question 2: Are the 8 Gate 1 Rules Sufficient?**

Current rules are **manually crafted and deterministic**:
```
Rule 1: Element 9 mismatch (BINARY: matches or doesn't)
Rule 2: OFAC hit (BINARY: on list or not)
Rule 3: Corridor + duty rate (THRESHOLD: >15%)
Rule 4: Dwell >5x baseline (THRESHOLD: commodity-specific)
Rule 5: New shipper + high volume (THRESHOLDS: <24mo, >$100K)
Rule 6: Pricing anomaly >15% (THRESHOLD: -15% from market)
Rule 7: Hub port + dwell (THRESHOLD: 3+ days)
Rule 8: ISF amendments >3 (THRESHOLD: >3)
```

**Data scientist concern**: These are **threshold-based, not learned from data**.

Example problem:
- Rule 4 says dwell >5x baseline catches anomalies
- But what if sophisticated fraudsters discovered this and now stay <4.8x baseline?
- The threshold becomes common knowledge → obsolete

**What a data scientist would do instead**:
1. Fit a distribution to legitimate dwell times (e.g., Gaussian mixture)
2. Calculate percentile scores, not fixed multiples
3. Ensemble multiple dwell-related features (dwell, port sequence, AIS silence)
4. Use isolation forest or local outlier factor (LOF) for truly anomalous patterns

---

**Question 3: Gate 1 vs Gate 2 Handoff Problem**

Current design:
```
Gate 1: "Are you obviously suspicious?" (High precision, low recall)
  └─ Use 8 deterministic rules
  └─ Target 10% PPV (only refer the most obvious cases)

Gate 2: "How likely are you actually a transshipment?" (Medium precision, higher recall)
  └─ Use LightGBM ML on 287 EAPA + Gate 1 outcomes
  └─ Target 30% PPV
```

**Data scientist concern**: This is a **sequential filter, not an ensemble**.

Problem:
- Cases that pass Gate 1 ("not obviously suspicious") go to Gate 2
- But some truly illegal cases might not trigger any of the 8 rules
- They arrive at Gate 2 with no ruleset signals → harder for ML to learn

Example: Sophisticated transshipment scheme where:
- ✓ Element 9 is consistent (no mismatch)
- ✓ Shipper is old (not new)
- ✓ Pricing is normal (no anomaly)
- ✓ Dwell is <5x baseline
- ✓ No hub port calls

This case = 0 points from Gate 1 rules, but it IS illegal transshipment.
Gate 2 ML has only 7-factor model to work with (no rule signals).

**Better approach**: Parallel gates (all signals available to all models) instead of sequential filtering.

---

**Question 4: Feature Engineering Gaps**

What signals are MISSING that could improve detection?

The 8 rules + 7 factors use:
- Vessel identity (vessel name, flag)
- Shipping route (port calls, AIS)
- Documentation (ISF, manifests)
- Pricing
- Party profile (shipper age, OFAC)

What's **NOT included** that transshipment schemes exploit:
- **Beneficial ownership networks**: Are the shipper, consignee, and vessel operator connected through ownership?
- **Financial flows**: Do payment flows match physical flows? (e.g., shipper paid but consignee in different country?)
- **Trade pattern history**: Is this shipper's typical route/commodity? Or deviation?
- **Port-specific infrastructure**: Does origin port have transshipment facilities?
- **Regulatory history**: Has origin port been flagged for transshipment activity?
- **Seasonal/temporal shifts**: Import volumes spike before tariff deadlines
- **Freight forwarder patterns**: Are logistics partners known to facilitate transshipment?
- **HS code reclassification risk**: Can commodity be relabeled to lower duty?
- **Supply chain variance**: Single supplier shipping to many dispersed buyers (vs consolidator buying from many and shipping to one)?

---

### 1.2 Model Selection: Is LightGBM the Right Choice?

The design proposes:
- **Gate 1**: Deterministic rules (high precision)
- **Gate 2**: LightGBM (gradient boosting)
- **Gate 3**: Bayesian Network (uncertainty quantification)

**Question**: Is this the right model stack?

**Data scientist evaluation**:

| Model | Pros for CBP | Cons for CBP |
|-------|-------------|------------|
| **Decision Tree / Tree Ensemble** (LightGBM, XGBoost) | ✓ Handles categorical features (country, commodity) ✓ Feature importance clear ✓ Fast inference ✓ Handles missing data | ✗ Vulnerable to adversarial evasion (nudge a few features = classification flips) ✗ No uncertainty quantification ✗ Unstable with imbalanced data (3.2% positive) |
| **Neural Networks** | ✓ Can learn complex patterns ✓ Transfer learning (pre-train on FDA, fine-tune for CBP) ✓ End-to-end learning | ✗ Black box (explainability = compliance issue) ✗ Slower inference ✗ Harder to handle categorical features |
| **Isolation Forest** | ✓ Unsupervised (no labels needed) ✓ Anomaly-focused ✓ Less vulnerable to concept drift | ✗ No scoring = only "anomaly" vs "normal" ✗ Hard to interpret for compliance |
| **Bayesian Network** | ✓ Explicit uncertainty ✓ Causal reasoning ✓ Compliant with explainability | ✗ Needs domain expert to define structure ✗ Slow to train with many variables |
| **Ensemble (Multiple Models)** | ✓ Combines strengths ✓ More robust ✓ Reduces overconfidence | ✗ Complex to maintain ✗ Harder to explain |

**Critical insight**: **For illegal transshipment detection, accuracy alone isn't enough—you need explainability AND robustness to adversarial evasion.**

If fraudsters learn the model, they'll adapt. A single LightGBM model is vulnerable.

---

**Question: Should We Use Ensemble Instead?**

Proposed: **3-Model Ensemble**
```
Model 1: Tree-based (LightGBM)
├─ Strengths: Feature importance, fast, handles categorical
└─ Role: Capture patterns in structured data

Model 2: Anomaly Detection (Isolation Forest + Local Outlier Factor)
├─ Strengths: Unsupervised, catches novel schemes
└─ Role: Flag unusual combinations of features (even if individual features normal)

Model 3: Causal/Domain Model (Bayesian Network)
├─ Strengths: Explainability, incorporates domain knowledge
└─ Role: Reasoning about "does this pattern make sense for legit trade?"

Final Decision: Ensemble voting
├─ All 3 agree = HIGH CONFIDENCE (80%+)
├─ 2 out of 3 = MEDIUM CONFIDENCE (50-80%)
└─ 1 out of 3 = LOW CONFIDENCE (<50%)
```

**Advantage**: If fraudsters learn LightGBM, anomaly detection catches novel patterns. If they fool both, Bayesian reasoning catches logical inconsistencies.

---

### 1.3 Concept Drift: Adversarial Evasion

**Critical question**: How do we handle fraudsters adapting to our model?

Example scenario:
```
Month 1: Our model flags "AIS silent >3 days" as transshipment
Month 2: Fraudsters read news about CBP AI, keep AIS on at all times
Month 3: Our model is now blind to that signal → PPV drops

What's our response?
```

**Current design answer**: None. The document doesn't mention retraining frequency, evasion monitoring, or adversarial testing.

**Data scientist recommendation**: Active monitoring for concept drift.

```
Monthly analysis:
├─ Calculate feature distributions for non-referred vs referred vs confirmed cases
├─ Alert if AIS dwell distribution shifts (fraudsters adapting)
├─ Alert if PPV degrades >25% month-over-month
├─ Trigger weekly retraining if drift detected
└─ Maintain evasion playbook (known tactics fraudsters are using)
```

---

### 1.4 Calibration & Confidence Intervals

The current design outputs a **point score (e.g., "87/100")** but CBP officers need **confidence bounds**.

Example:
```
Current: "87% risk of transshipment"
Better: "87% ± 5% confidence (95% CI)"
```

With confidence intervals, officers can:
- Triage cases (87±3% = clear case, invest resources)
- vs (52±10% = too uncertain, deprioritize)

**How to implement**:
1. Use ensemble predictions to estimate variance
2. Bootstrap resampling on training data
3. Quantile regression (predict 5th and 95th percentile, not just mean)

---

## Part 2: Generalization to FDA Imports & Opioid Detection

### 2.1 Can the Same Architecture Work for All Three Domains?

The proposed framework is:
```
7 Factors (weighted) → 8 Rules (deterministic) → ML Model (LightGBM) → Confidence Scoring
```

**Question**: Does this generalize to FDA and Opioid?

**FDA Imports Fraud Analysis**:
```
Similarities to CBP:
├─ Structured data (importer, supplier, product, facility)
├─ Regulatory signals (registration, compliance history)
├─ Financial signals (pricing, payment patterns)
└─ Network signals (supplier reputation, facility network)

Differences from CBP:
├─ Time horizon (CBP = days, FDA = weeks/months for testing)
├─ Documentation (CBP = manifest, FDA = facility inspection, lab results)
├─ Evasion tactics (CBP = routing fraud, FDA = counterfeiting/contamination)
└─ Data sources (CBP = AIS/customs, FDA = inspection databases, lab networks)
```

**Can 7-factor model work for FDA?**

| Factor | CBP Transshipment | FDA Imports Fraud | Match? |
|--------|------------------|------------------|--------|
| Documentation Risk | ISF completeness, manifest | Facility registration, cert of analysis | ✓ Similar concept |
| Routing Risk | AIS patterns, port calls | Supply chain traceability | ✓ Can adapt |
| Commodity Risk | Tariff codes, AD/CVD rates | Product category, compliance history | ✓ Different data |
| Corridor Risk | CN→US vs CA→US | Supplier country risk | ✓ Can adapt |
| Party Risk | Shipper age, OFAC | Importer registrations, violations | ✓ Similar |
| Pattern Risk | Pricing anomaly, weight variance | Lab result patterns, microbial data | ~ Needs ML |
| Time Sensitivity | Pre-tariff timing | Seasonal product availability | ✓ Can adapt |

**Conclusion**: 7-factor framework CAN generalize, but requires domain-specific feature engineering.

---

**Opioid Detection Analysis**:
```
Similarities to CBP:
├─ Volumetric data (prescription quantities)
├─ Network analysis (prescriber, patient, pharmacy)
└─ Behavioral anomalies (unusual patterns)

Major Differences from CBP:
├─ Temporal granularity (daily prescriptions vs batch shipments)
├─ Real-time requirement (flag within hours, not days)
├─ Privacy constraints (HIPAA limits data sharing)
├─ Different actors (DEA, healthcare, insurance, not customs)
└─ Evasion tactics (doctor shopping, pill mills, rogue pharmacies)
```

**Can 7-factor model work for Opioid?**

| Factor | Opioid Diversion | Fit? | Notes |
|--------|------------------|------|-------|
| Documentation Risk | Prescription legitimacy | ✓ | Verify doctor license, patient ID |
| Routing Risk | Pharmacy network patterns | ~ | Different meaning (distribution network vs shipping route) |
| Commodity Risk | Opioid type/strength | ✓ | High-strength (fentanyl) = higher risk |
| Corridor Risk | Origin prescriber → patient geography | ~ | Can adapt (prescriber location vs patient ZIP code mismatch) |
| Party Risk | Prescriber/patient/pharmacy history | ✓ | Prior DEA violations, pill mill reports |
| Pattern Risk | Volumetric anomalies, prescriber clustering | ✓ | Unusual prescription patterns |
| Time Sensitivity | Seasonal trends (cold/flu season vs opioid trends) | ~ | Less relevant than CBP |

**Conclusion**: 7-factor framework is LESS suitable for Opioid. Needs 5 new factors:
- Prescription Volume (daily volume spikes)
- Patient Behavior (doctor shopping = visits to multiple prescribers)
- Prescriber Pattern (specialty mismatch: surgeon prescribing pain meds?)
- Pharmacy Network (rogue pharmacy indicators)
- Diversion Signals (DEA watch list, theft reports)

**Implication**: The framework CAN generalize, but it's not ONE model for all domains. It's:
- **CBP**: 7 factors (transport + trade)
- **FDA**: 7-8 factors (supply chain + compliance)
- **Opioid**: 5 factors (behavioral + network)

Different factor sets, same architecture.

---

### 2.2 Generalized Architecture Proposal

Instead of "7 factors for all", use:

```
GENERALIZED RISK SCORING FRAMEWORK
├─ DOMAIN REGISTRY (define what's in scope for each domain)
│  ├─ CBP: 7 factors, 8 rules, 3 gates
│  ├─ FDA: 7 factors, 6 rules, 3 gates
│  └─ Opioid: 5 factors, 4 rules, 3 gates
│
├─ FEATURE ENGINEERING ENGINE (domain-specific)
│  ├─ CBP: Extract AIS, vessel, tariff data
│  ├─ FDA: Extract facility, supplier, lab data
│  └─ Opioid: Extract prescriber, patient, pharmacy data
│
├─ MODEL SELECTION (same architecture, different tuning)
│  ├─ Gate 1: Deterministic rules (domain-specific thresholds)
│  ├─ Gate 2: LightGBM + Isolation Forest + Bayesian (same ensemble, different features)
│  └─ Gate 3: Uncertainty quantification (same approach)
│
└─ EVALUATION METRICS (domain-specific success measures)
   ├─ CBP: PPV 10% → 30% → 50%, Sensitivity ≥70%
   ├─ FDA: PPV 5% → 20% → 40%, Sensitivity ≥60%
   └─ Opioid: PPV 15% → 40% → 60%, Sensitivity ≥75%
```

---

## Part 3: Storage & Parameters (The DuckDB Question)

### 3.1 Why DuckDB? (Re-examining the Choice)

The user asked: "**Why DuckDB? I suggested it, but I'm not sure of the reasoning.**"

Let me be honest: **We switched to DuckDB for rules versioning, but the real decision should be based on what we're actually storing and querying.**

**What are we storing?**
```
1. RULES DEFINITIONS (immutable, in Git)
   ├─ Condition logic (text)
   ├─ Base risk points (numeric)
   └─ Governance level (enum)
   
2. RULE PARAMETERS (mutable, analyst-tuned)
   ├─ Weights (numeric)
   ├─ Thresholds (numeric)
   ├─ Corridor overrides (JSON)
   └─ Version history (SCD Type 2)

3. AUDIT TRAIL (immutable, append-only)
   ├─ Who changed what when
   ├─ Old value → New value
   └─ Approval status

4. SCORING CACHE (immutable, reference)
   ├─ Shipment ID
   ├─ Score
   ├─ Score breakdown (by factor)
   └─ Timestamp

5. FEEDBACK DATA (immutable, from CBP)
   ├─ Referral ID
   ├─ Investigation outcome (confirmed/not)
   └─ Analyst notes
```

**Query patterns we need:**
```
Q1: "What was the weight for rule W-121 on March 15?" (Temporal query)
   → DuckDB: SELECT * FROM rule_parameters 
     WHERE rule_id='W-121' AND valid_from <= '2026-03-15' 
     AND (valid_to IS NULL OR valid_to > '2026-03-15')
   → Firestore: Must manually reconstruct from version history

Q2: "Show all changes made by analyst@cbp.gov in March" (Audit query)
   → DuckDB: SELECT * FROM rule_change_events 
     WHERE analyst_id='analyst@cbp.gov' AND month(created_at)=3
   → Firestore: Query change log collection (similar)

Q3: "Cache the score for 50K daily shipments" (Write-heavy)
   → DuckDB: INSERT 50K rows/day (fast, append-only)
   → Firestore: 50K write operations/day = $500/month cost

Q4: "Aggregate: which rules fire most often?" (Analytics)
   → DuckDB: SELECT rule_id, COUNT(*) FROM rule_triggers GROUP BY rule_id
   → Firestore: Not efficient (no aggregation)
```

**DuckDB strengths**:
- ✓ Temporal queries (SCD Type 2)
- ✓ Aggregation (GROUP BY, analytics)
- ✓ Cost (free locally, $0-250/mo managed)
- ✓ Append-only audit logs (immutable history)
- ✗ Local only (until MotherDuck matures)
- ✗ Single writer (concurrent analysts need careful design)

**Firestore strengths**:
- ✓ Global real-time writes (if we have 100+ analysts worldwide)
- ✓ Managed (no ops)
- ✗ Per-operation billing ($500/mo for 50K/day)
- ✗ No temporal queries natively
- ✗ No aggregation queries

---

### 3.2 Storage Decision: Local vs Managed

**Honest assessment:**

For **rules parameters** (what analysts tune):
- Volume: ~100 parameters × 2-3 changes/day = 300 writes/day
- Query: "What's the current weight?" (must be fast)
- Consistency: Multi-analyst conflicts (optimistic concurrency)

**Best option: DuckDB locally + MotherDuck Starter (free)**
```
Cost: $0/month indefinitely
Setup: 5 minutes
Conflict handling: Version field (optimistic)
Temporal queries: Native support
Scaling: Free tier covers 1000+ daily shipments
```

For **scoring cache** (shipment scores):
- Volume: 50K-100K shipments/day = 50K-100K writes/day
- Query: "Show me score breakdown for shipment X"
- Consistency: Immutable (write-once)

**Best option: PostgreSQL on AWS RDS**
```
Cost: $50-200/month (production)
Setup: 15 minutes
Indexing: Fast lookups by shipment_id
Scaling: Handles 100K writes/day easily
```

**Revised storage architecture**:
```
DuckDB (Rules parameters + audit)
├─ Local development + Quack protocol (team collaboration)
├─ MotherDuck Starter for production (free tier)
└─ Cost: $0

PostgreSQL (Scoring cache + feedback)
├─ AWS RDS for production
├─ Read-optimized indexes on shipment_id, created_at
└─ Cost: $100-200/month (shared infra)

Git (Rules definitions)
├─ v2.rules.yaml versioned in code
├─ Code review gate for rule changes
└─ Cost: $0
```

---

## Part 4: Design Decisions to Make Now

### Decision 1: Model Architecture

**Option A: Single LightGBM (Current Proposal)**
```
Pros: Simple, fast, one model to maintain
Cons: Vulnerable to adversarial evasion, no uncertainty
```

**Option B: Ensemble (3 Models)**
```
Pros: Robust, combines different approaches, harder to fool
Cons: Complex, 3x the inference cost, harder to explain
```

**Recommendation**: **Option B (Ensemble)** because:
- Fraudsters will eventually learn any single model
- Ensemble forces them to evade ALL three simultaneously
- Trade-off (complexity) is worth the robustness gain

---

### Decision 2: Gate 1 Rules

**Option A: Keep 8 Manual Rules As-Is**
```
Pros: Simple to explain, compliance-friendly
Cons: Threshold-based, vulnerable to evasion
```

**Option B: Hybrid (4 Manual Rules + 1 Anomaly Detection)**
```
Pros: Manual rules for critical signals (OFAC, Element 9), ML for subtle patterns
Cons: More complex, two systems to maintain
```

**Recommendation**: **Option B (Hybrid)**
```
Critical Rules (Manual, High Precision):
├─ OFAC/SDN hit (binary, no false positives)
└─ Element 9 exact mismatch (binary, high confidence)

Anomaly-Based Rules (Unsupervised):
├─ Isolation Forest on dwell, pricing, party age
├─ Local Outlier Factor on feature combinations
└─ Catches novel patterns Gate 1 manual rules miss
```

---

### Decision 3: Generalization Strategy

**Option A: One Model for All Three Domains**
```
Pros: Single codebase
Cons: FDA and Opioid don't fit 7-factor CBP model well
```

**Option B: Domain-Specific Factor Sets + Shared Engine**
```
Pros: Each domain optimized, same architecture
Cons: Requires domain expertise for each factor set
```

**Recommendation**: **Option B**
```
CBP: 7 factors (transport + trade)
FDA: 7-8 factors (supply chain + compliance)
Opioid: 5 factors (behavioral + network)

All use:
├─ Same gate architecture (deterministic → ML → Bayesian)
├─ Same ensemble approach (LightGBM + Anomaly + Bayesian)
├─ Same storage layer (DuckDB params + PostgreSQL scores)
└─ Different feature engineering per domain
```

---

## Part 5: Research Gaps to Fill

Before we finalize, we need data/research on:

### Gap 1: CBP Data & Baselines
- [ ] **What's the actual shipment volume per week?** (determines sensitivity required)
- [ ] **What's transshipment prevalence?** (CBP estimates: 2-5% of all imports?)
- [ ] **Which corridors are high-risk?** (CN, VN, TH, etc.—validate existing assumptions)
- [ ] **Which commodities are vulnerable?** (apparel, aluminum, solar—validate)
- [ ] **How sophisticated are fraudsters?** (are they learning/evading current rules?)

### Gap 2: Feature Engineering Effectiveness
- [ ] **Which features have highest signal?** (Is Element 9 mismatch really 95% confidence?)
- [ ] **Are there missing features?** (beneficial ownership networks, payment flows, etc.)
- [ ] **What's the feature importance ranking?** (use EAPA dataset for retrospective analysis)

### Gap 3: Model Performance Benchmarks
- [ ] **What's the best-in-class model for trade enforcement?** (research other customs agencies: EU, Singapore, Australia)
- [ ] **What AUC/PPV/Sensitivity are achievable?** (expectations vs reality)
- [ ] **How do ensemble models perform on imbalanced data?** (3.2% positive class is challenging)

### Gap 4: FDA & Opioid Specifics
- [ ] **FDA data: What's the supply chain fraud prevalence?** (determine target metrics)
- [ ] **Opioid data: What signals detect doctor shopping?** (prescriber network analysis)
- [ ] **Can we use transfer learning?** (pre-train on CBP, fine-tune for FDA/Opioid?)

### Gap 5: Operational Constraints
- [ ] **Inference latency budget**: Must score shipment in <100ms? <500ms?
- [ ] **Explainability requirements**: Can we use neural networks, or must we use interpretable models?
- [ ] **Privacy constraints**: FDA/Opioid may have HIPAA limits
- [ ] **Scale**: Peak shipment volume per second (determines infrastructure)

---

## Next Steps: What We Should Do

**Before implementation**, I recommend:

### Week 1: Design Validation
- [ ] Gather CBP data statistics (shipment volume, prevalence, commodity breakdown)
- [ ] Analyze EAPA dataset for feature importance (which rules/features actually matter?)
- [ ] Research benchmarks (what accuracy do other countries achieve?)
- [ ] Validate 7-factor model fit for FDA and Opioid

### Week 2: Model Prototyping
- [ ] Implement 3 ensemble models on EAPA data
- [ ] Compare: single LightGBM vs ensemble vs anomaly detection
- [ ] Evaluate sensitivity/specificity/PPV across each
- [ ] Test adversarial robustness (can we fool the model?)

### Week 3: Architecture Finalization
- [ ] Decide: LightGBM or ensemble?
- [ ] Decide: 8 manual rules or hybrid (manual + anomaly)?
- [ ] Decide: Single factor set or domain-specific?
- [ ] Finalize storage choice (DuckDB + PostgreSQL + Git)

### Week 4: Implementation Plan
- [ ] Create detailed technical spec
- [ ] Phase roadmap (MVP vs Phase 2)
- [ ] Resource requirements

---

## Summary: Where We Stand

**Current design strengths**:
✓ 7 factors + 3 gates + 8 rules is reasonable starting point
✓ Multi-gate approach (deterministic → ML → Bayesian) is sound
✓ V2AITuningPage framework for parameter tuning is solid

**Areas needing reinforcement**:
⚠ Single LightGBM model may be vulnerable to evasion
⚠ Manual thresholds will become obsolete (need data-driven approach)
⚠ Missing features (beneficial ownership, payment flows)
⚠ Generalization to FDA/Opioid needs validation
⚠ Storage choice (DuckDB) is reasonable for rules, but scoring cache needs separate DB

**Data science questions**:
? What's the actual class imbalance (transshipment prevalence)?
? Can ensemble models outperform single LightGBM on imbalanced data?
? What features are most predictive (EAPA analysis)?
? How do we handle adversarial evasion (concept drift)?

