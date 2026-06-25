# Platform Comparison Summary (Quick Reference)

## Bottom Line for CBP Sentry

**No single "replacement" platform exists.** CBP should adopt a **hybrid architecture:**
- Use **Exiger** (CBP-contracted) + **Altana** (CBP-contracted) for data enrichment
- Build lightweight **in-house models** on **AWS SageMaker** for CBP-specific scoring
- Integrate **Snorkel** feedback loop for officer-driven model improvement

**First-year cost: $65K-87K** (vs. $200K+ for commercial fraud platform)

---

## Commercial Fraud Platforms: NOT RECOMMENDED

| Platform | Position | Why Not for CBP |
|----------|----------|-----------------|
| **Feedzai** | Enterprise fraud (banks, payments) | Payment fraud ≠ customs trade fraud; black box; government-ready but not CBP-specific |
| **Sift** | E-commerce fraud SaaS | High-velocity digital fraud; no customs expertise; pre-trained models |
| **Kount** | Compliance + device fingerprinting | Consumer fraud focus; Equifax data doesn't help customs cases; no CBP adoption |

**Verdict:** Commercial platforms are misaligned. CBP's 1.5K cases/year is too small for their volume-based pricing; their models are trained on payment/e-commerce fraud, not trade evasion.

---

## Customs-Specific Platforms: ALREADY CONTRACTED

| Platform | Status | Cost | Fit |
|----------|--------|------|-----|
| **Exiger** | CBP contract (Oct 2025) | ~$2M-5M/year | **Transshipment detection** (origin disguise); real-time risk scoring |
| **Altana** | CBP contract (Oct 2025) | ~$1M-3M/year | **Forced labor + counternarcotics** detection; supply chain visibility |
| **WCO / Others** | Strategic guidance only | N/A | No production platforms; BACUDA is capacity-building, not a tool |

**Action Item:** Clarify if Exiger/Altana APIs can integrate with CBP Sentry's 7-factor engine. If yes, use their scores as features.

---

## No-Code/Low-Code ML Platforms: COST PROHIBITIVE

| Platform | Cost/Year | Pros | Cons |
|----------|-----------|------|------|
| **Dataiku** | $80K-120K | Easiest for non-ML teams; governance strong | Expensive for CBP case volume |
| **H2O Driverless AI** | $60K-150K | Fast iteration | H2O-3 free alternative better |
| **Databricks** | $60K-120K | Sub-300ms latency; proven fraud case (Coinbase) | Overkill for batch scoring; complex ops |
| **SageMaker** | $48K-80K | **Native SHAP explainability; government-proven** | Best option for managed platform |
| **Vertex AI** | $48K-84K | **SHAP built-in; best explainability** | GCP GovCloud adoption < AWS |
| **Azure ML** | $60K-120K | Responsible AI toolkit | Less government track record than AWS |

**Verdict:** **SageMaker** is best managed platform (government-proven, native SHAP). But open-source alternatives are cheaper.

---

## Open-Source & Orchestration Stacks: LOWEST COST

| Stack | Cost/Year | Pros | Cons | For CBP? |
|-------|-----------|------|------|----------|
| **MLflow** | $24K-60K | Free; experiment tracking; model registry | No drift detection; requires ML engineer | Yes, if team is technical |
| **Kubeflow** | $24K-60K | Free; end-to-end ML lifecycle; portable | Kubernetes required; high ops overhead; steep learning curve | Yes, but overkill for 1.5K cases/year |
| **Ray Tune** | Minimal | Free; fast hyperparameter tuning | Hyperparameter search only; not a platform | Complementary tool, not standalone |
| **Snorkel** | $18K-30K | Free; weak supervision; labeling functions are explainable | Requires domain expertise to write rules | **Yes, best feedback loop** |

**Verdict:** **Snorkel + XGBoost** is cheapest ($18K-30K/year) and most transparent (rules-based), but requires experienced ML engineer. **MLflow + self-managed** is middle ground.

---

## Active Learning & Weak Supervision: FEEDBACK LOOP

| Platform | Purpose | Cost | Fit for CBP |
|----------|---------|------|-------------|
| **Rubrix** | Annotation UI + active learning | $18K-30K | Useful for feedback loop, but NLP-optimized (CBP data is tabular) |
| **Snorkel** | Weak supervision from rules | $18K-30K | **Excellent:** Officers write rules → model learns → retrain monthly |

**Verdict:** **Snorkel is ideal** for CBP if officers can articulate rules ("China shipper + clothing + $5K = high risk").

---

## Explainability (SHAP) Comparison

**Requirement:** CBP officers must explain scores to traders (regulatory compliance).

| Platform | SHAP Support | Rating |
|----------|-------------|--------|
| **SageMaker Clarify** | Native SHAP + audit trail | ⭐⭐⭐⭐⭐ |
| **Vertex AI** | Native Sampled Shapley | ⭐⭐⭐⭐⭐ |
| **Azure ML** | Responsible AI toolkit (SHAP) | ⭐⭐⭐⭐ |
| **Snorkel** | Labeling functions are rules (implicitly explainable) | ⭐⭐⭐⭐ |
| **Dataiku** | Feature importance (unclear if native SHAP) | ⭐⭐⭐ |
| **H2O, Databricks, Kubeflow, MLflow** | Manual SHAP integration required | ⭐⭐⭐ |
| **Feedzai, Sift, Kount** | Not disclosed; likely not SHAP-native | ⭐⭐ |

**Verdict:** **SageMaker Clarify** or **Snorkel labeling functions** are best for regulatory compliance.

---

## Government Adoption (FedRAMP, GovCloud)

| Platform | GovCloud | FedRAMP | Federal Case Studies |
|----------|----------|---------|----------------------|
| **AWS SageMaker** | ✅ Yes | ✅ High | ✅ Treasury ($375M fraud recovery), HHS fraud detection |
| **Azure ML** | ✅ Yes (Azure Gov) | ✅ High | ✅ Federal agencies |
| **Google Vertex AI** | ✅ Yes (FedRAMP pending) | ⚠️ Emerging | ⚠️ Not as established as AWS |
| **Exiger** | ✅ CBP-contracted | ✅ Likely | ✅ CBP (Oct 2025) |
| **Altana** | ✅ CBP-contracted | ✅ Likely | ✅ CBP (Oct 2025) |
| **Databricks** | ✅ Via AWS GovCloud | ⚠️ Unclear | ⚠️ Not government-specific |
| **Feedzai** | Government-ready | Unclear | Government clients, not CBP-confirmed |
| **Others** | ❌ Not GovCloud | ❌ No | ❌ Not federal |

**Verdict:** **AWS SageMaker** > **Azure ML** > **Google Vertex AI** for government compliance.

---

## Retraining Frequency & Cost

**CBP Context:** ~1.5K referrals/year = ~125/month

| Scenario | Frequency | Cost/Retrain | Annual Cost |
|----------|-----------|-------------|-------------|
| **Monthly (best for evolving fraud)** | Every 30 days | $300-500 | $3.6K-6K |
| **Quarterly (conservative)** | Every 90 days | $300-500 | $1.2K-2K |
| **Annual (minimal)** | Once/year | $300-500 | $300-500 |

**Plus Platform Cost:**
- **Dataiku:** +$80K-120K/year
- **SageMaker:** +$48K-80K/year
- **Kubeflow (self-managed):** +$24K-60K/year
- **Snorkel + open-source:** +$18K-30K/year

---

## Time to Production

| Platform | Weeks | Breakdown |
|----------|-------|-----------|
| **SageMaker** | 10-14 | Setup (1-2), data prep (2-3), model building (2-4), validation (2-3) |
| **Vertex AI** | 10-14 | Same as SageMaker |
| **Dataiku** | 8-12 | Easier for non-ML teams |
| **Snorkel + XGBoost** | 6-10 | Labeling functions (2-3), Snorkel setup (1-2), model training (2-3), validation (1-2) |
| **Databricks** | 8-16 | Spark setup (2-4), feature engineering (2-4), model building (2-4), validation (2-4) |
| **H2O (free)** | 4-8 | If team is experienced |
| **Kubeflow** | 12-20 | Kubernetes setup (2-4), pipeline design (2-3), containerization (2-3), feature store (2-3), serving (2-3), monitoring (2-3) |

---

## Recommended Architecture (Hybrid)

```
CBP Sentry Risk Scoring Engine
├─ INPUT: Shipment data (HS code, value, port, shipper, AIS, historical)
├─ LAYER 1: External Data Enrichment
│  ├─ Exiger API → Transshipment risk score
│  ├─ Altana API → Forced labor + counternarcotics risk
│  └─ CBP databases → Entity resolution, AIS dwell, referral history
├─ LAYER 2: Feature Engineering
│  ├─ XGBoost feature set (18 factors)
│  ├─ Snorkel weak supervision (officer labeling functions)
│  └─ Historical CBP referral labels (ground truth)
├─ LAYER 3: Model Training & Serving
│  ├─ SageMaker training job (monthly retrain, 125 new cases/month)
│  ├─ XGBoost + Isolation Forest ensemble
│  ├─ Model Registry (version control)
│  └─ SageMaker Endpoint (real-time inference)
├─ LAYER 4: Explainability
│  ├─ SageMaker Clarify → SHAP feature importance
│  ├─ Show top 3-5 factors per score
│  └─ Audit trail for trader appeals
├─ LAYER 5: Officer Feedback Loop
│  ├─ Snorkel: Officers refine labeling functions
│  ├─ Monthly retrain triggers
│  └─ Feedback → model improvement → next month's deployment
└─ OUTPUT: Risk score (0-100) + explanation + Altana supply chain visibility
```

**Cost Breakdown (First Year):**
- SageMaker setup + Clarify: $8K-12K
- Data labeling + feature engineering: $5K-8K
- Model development + validation: $3K-5K
- Monthly operations (12 months @ $4.5K-6K/month): $54K-72K
- **Total: $70K-97K** (mostly SageMaker usage)

**Ongoing (Years 2+):**
- ~$54K-72K/year (SageMaker operations + monthly retraining)

---

## Final Recommendation Matrix

| Rank | Option | Cost | Time | SHAP | Gov Fit | Feedback Loop | Verdict |
|------|--------|------|------|------|---------|---------------|---------|
| 🥇 | **SageMaker + In-House XGBoost** | $70K-97K | 10-14 wks | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Snorkel loop | **BEST** (gov-proven, explainable) |
| 🥈 | **Snorkel + XGBoost (open-source)** | $36K-48K | 6-10 wks | ⭐⭐⭐⭐ | ⭐⭐⭐ | Tight loop | **GOOD** (cheapest, iterative) |
| 🥉 | **Vertex AI + Custom Model** | $70K-97K | 10-14 wks | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | Snorkel loop | **GOOD** (best SHAP, smaller GovCloud adoption) |
| 4️⃣ | **Kubeflow (self-managed)** | $48K-84K | 12-20 wks | ⭐⭐⭐ | ⭐⭐⭐ | Custom | **VIABLE** (lowest ops cost, high setup effort) |
| 5️⃣ | **Dataiku** | $80K-120K | 8-12 wks | ⭐⭐⭐ | ⭐⭐⭐ | Built-in | **NOT RECOMMENDED** (expensive for CBP volume) |

---

## DO NOT PURSUE

| Platform | Reason |
|----------|--------|
| **Feedzai** | Payment fraud focus; no customs trade models |
| **Sift** | E-commerce fraud; pre-trained, limited customization |
| **Kount** | Consumer fraud + compliance screening, not trade evasion detection |
| **Databricks only** | Sub-second latency unnecessary; complex ops for batch scoring |
| **H2O Driverless AI** | Expensive; H2O-3 free + MLflow is better value |

---

## Implementation Roadmap (SageMaker Path)

| Phase | Timeline | Deliverable | Cost |
|-------|----------|-------------|------|
| **Phase 1** | Jun-Jul 2026 | SageMaker + Exiger/Altana API integration | $8K-12K |
| **Phase 2** | Jul-Aug 2026 | Label 300-400 CBP referrals; train XGBoost | $5K-8K + $4K-6K ops |
| **Phase 3** | Aug-Sep 2026 | Deploy SageMaker Endpoint + Clarify (SHAP) | $4K-6K ops |
| **Phase 4** | Sep-Oct 2026 | Snorkel feedback loop + monthly retraining | $1K-2K ops |
| **Phase 5** | Oct-Dec 2026 | Monitoring, drift detection, optimization | $2K ops |
| **Total (First Year)** | - | - | $70K-97K |

---

## Questions for CBP Before Final Decision

1. **Exiger/Altana APIs:** Can CBP query transshipment + forced labor scores in real-time via API?
2. **Training Data:** Are CBP referrals labeled with ground truth (confirmed smuggling/evasion)?
3. **Explainability Requirement:** Will SHAP explanations satisfy regulatory compliance, or do traders need simpler breakdowns?
4. **Latency:** Is batch scoring (hourly) sufficient, or do officers need real-time (< 1 second)?
5. **Retraining Frequency:** Can CBP afford monthly model reviews + retraining?
6. **Budget Flexibility:** Is $70K-97K acceptable, or is cost a hard constraint?
7. **Governance:** Does CBP require full audit trail (decisions logged, appeal process)?
8. **Scaling:** Do you anticipate 1.5K cases/year stable, or 10x growth in future?

---

**Document Last Updated:** June 12, 2026
