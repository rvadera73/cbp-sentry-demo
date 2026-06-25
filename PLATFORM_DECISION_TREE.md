# Platform Selection Decision Tree

```
START: Should CBP replace in-house model building?
│
├─ Q1: Do you need a complete fraud detection platform (not just model training)?
│  │
│  ├─ YES (need end-to-end platform)
│  │  ├─ Q2: Can you afford $150K+/year?
│  │  │  ├─ YES
│  │  │  │  └─ → Dataiku ($80K-120K/yr) or Databricks ($60K-120K/yr)
│  │  │  │     (Best for non-ML teams; Databricks better for real-time)
│  │  │  │
│  │  │  └─ NO (budget-constrained)
│  │  │     └─ → Q3: Can you manage Kubernetes clusters?
│  │  │        ├─ YES → Kubeflow ($24K-60K/yr infrastructure)
│  │  │        └─ NO → SageMaker ($48K-80K/yr, managed service)
│  │
│  └─ NO (just need model building + some ops)
│     └─ → Q3: Do you need explainability (SHAP) for regulatory compliance?
│        ├─ YES
│        │  ├─ Q4: Can you afford $50K+/year managed platform?
│        │  │  ├─ YES
│        │  │  │  └─ → SageMaker Clarify ($48K-80K/yr)
│        │  │  │     (Native SHAP, government-proven, FedRAMP)
│        │  │  │
│        │  │  └─ NO
│        │  │     └─ → Vertex AI ($48K-84K/yr)
│        │  │        (Same SHAP support as SageMaker, GCP alternative)
│        │  │
│        │  └─ Q5: Would you prefer open-source + self-managed?
│        │     ├─ YES
│        │     │  └─ → MLflow + SHAP + Snorkel ($18K-30K/yr)
│        │     │     (Cheapest; requires technical team)
│        │     │
│        │     └─ NO
│        │        └─ → SageMaker Clarify (government-proven)
│        │
│        └─ NO (explainability not required)
│           └─ → H2O-3 (free, open-source)
│              (No SHAP, but works for internal use)
│
└─ Q2: Should you leverage CBP's Exiger + Altana contracts?
   │
   ├─ YES (integrate Exiger transshipment + Altana forced labor scores)
   │  │
   │  └─ → HYBRID ARCHITECTURE (Recommended)
   │     ├─ Data layer: Exiger API + Altana API for enrichment
   │     ├─ Model layer: SageMaker + XGBoost for CBP-specific scoring
   │     ├─ Feedback layer: Snorkel for officer-driven rules
   │     └─ Cost: $70K-97K/year (SageMaker) or $36K-48K (open-source)
   │
   └─ NO (build from scratch)
      │
      └─ → Q3: Is latency critical? (< 1 second response time)
         ├─ YES
         │  └─ → Databricks ($60K-120K/yr)
         │     (Sub-300ms real-time scoring with Spark RTM)
         │
         └─ NO (batch scoring OK)
            └─ → SageMaker ($48K-80K/yr, lower cost than Databricks)
               (Same accuracy, easier ops, lower cost)
```

---

## Decision Flowchart (Text Version)

### IF Budget-First → Snorkel + XGBoost
**Cost:** $18K-30K/year  
**Requirement:** Experienced ML engineer  
**Pros:** Cheapest; labeling functions are explainable (compliance-friendly)  
**Cons:** Requires writing domain-specific rules; no drift detection  
**Timeline:** 6-10 weeks  
**Best for:** CBP if officers can articulate fraud rules; tight iteration cycle

```
Officer writes rules (Snorkel):
  "If shipper = China AND HS code = 6204 AND value > $5K, then risk=HIGH"
        ↓
Snorkel combines rules into weak labels
        ↓
XGBoost trains on weak labels
        ↓
Deploy model; get feedback from officers
        ↓
Modify rules → Retrain monthly
```

---

### IF Government-Compliance-First → SageMaker Clarify
**Cost:** $48K-80K/year  
**Requirement:** AWS familiarity  
**Pros:** Native SHAP explainability; FedRAMP+GovCloud; proven by Treasury/HHS  
**Cons:** Cloud vendor lock-in (AWS)  
**Timeline:** 10-14 weeks  
**Best for:** CBP if regulatory compliance + audit trail critical; government-standard platform

```
SageMaker Clarify generates SHAP explanations:
  Shipment SHP-123 scored 65/100 because:
    • Shipper flagged (SHAP = +25)
    • Port high-risk (SHAP = +20)
    • HS code suspicious (SHAP = +15)
    • Value anomalous (SHAP = +5)
```

---

### IF Simplicity-First → Dataiku or Vertex AI
**Cost:** $48K-120K/year  
**Requirement:** Business analysts (no coding)  
**Pros:** AutoML reduces model dev time; no-code UI; strong governance  
**Cons:** More expensive than SageMaker; weaker government track record (Vertex AI)  
**Timeline:** 8-14 weeks  
**Best for:** CBP if team has little ML experience; prefer managed service

---

### IF Scaling-First (Future 10x Growth) → Databricks
**Cost:** $60K-120K/year  
**Requirement:** Data engineers + ML engineers  
**Pros:** Sub-300ms real-time latency; Spark-native; proven at massive scale (Coinbase)  
**Cons:** Complex; overkill for 1.5K cases/year  
**Timeline:** 8-16 weeks  
**Best for:** CBP if expect major scaling; high real-time volume; sophisticated data pipelines

---

### IF Full Control (Self-Hosted) → Kubeflow
**Cost:** $24K-60K/year (infrastructure)  
**Requirement:** Kubernetes + ML DevOps expertise  
**Pros:** Portable across clouds; no vendor lock-in; community-supported  
**Cons:** Steep learning curve; long time to production; high ops overhead  
**Timeline:** 12-20 weeks  
**Best for:** CBP if want full control + multi-cloud strategy; have DevOps team

---

### IF Regulatory Compliance + Iterative Feedback → Snorkel + SageMaker Hybrid
**Cost:** $70K-97K/year  
**Requirement:** ML engineer + CBP domain expertise  
**Pros:** Tight feedback loop (officers → Snorkel rules → retrain monthly); SHAP explainability; government-proven  
**Cons:** Most complex integration  
**Timeline:** 10-14 weeks  
**Best for:** CBP (RECOMMENDED PATH) - combines explainability + feedback + government-standard platform

```
Officer feedback loop (RECOMMENDED):
  Month 1: Label 100 cases → Train XGBoost → Deploy → SHAP explanations
           ↓
  Month 2: Officers provide feedback → Write Snorkel rules → Retrain
           ↓
  Month 3: Snorkel generates weak labels → XGBoost improves → Deploy
           ↓
  ... iterate monthly
```

---

## Quick Decision Chart

| Your Priority | Platform | Cost | Time |
|---------------|----------|------|------|
| 💰 **Cheapest** | Snorkel + XGBoost (open-source) | $18K-30K | 6-10 weeks |
| 👮 **Government Compliance** | SageMaker Clarify | $48K-80K | 10-14 weeks |
| 🧑‍💻 **Easiest for Non-ML Team** | Dataiku or Vertex AI | $48K-120K | 8-14 weeks |
| ⚡ **Real-Time Performance** | Databricks | $60K-120K | 8-16 weeks |
| 🔄 **Feedback Loop / Iterative** | Snorkel + SageMaker Hybrid | $70K-97K | 10-14 weeks |
| 🎯 **Full Control** | Kubeflow + MLflow | $24K-60K | 12-20 weeks |
| ✨ **Best SHAP Explainability** | Vertex AI or SageMaker Clarify | $48K-97K | 10-14 weeks |
| 📊 **Balanced All-Rounder** | **SageMaker** | **$48K-80K** | **10-14 weeks** |

---

## NOT Recommended (Why Skip These)

| Platform | Reason | Skip |
|----------|--------|------|
| **Feedzai** | Built for payment fraud, not trade evasion; black box models | ❌ Skip |
| **Sift** | E-commerce fraud SaaS; no customs domain knowledge | ❌ Skip |
| **Kount** | Consumer fraud + compliance, not trade fraud detection | ❌ Skip |
| **DataRobot** | Expensive ($100K+); no government track record for customs | ❌ Skip |
| **H2O Driverless AI** | Expensive; H2O-3 free is superior alternative | ❌ Skip |
| **Azure ML only** | Less government fraud adoption than AWS | ⚠️ Consider SageMaker first |
| **Databricks only** | Sub-second latency overkill for 1.5K cases/year volume | ⚠️ Over-engineered |

---

## Implementation Timeline Comparison

```
Snorkel (6-10 weeks):
  Week 1-2:   Design labeling functions
  Week 2-3:   Snorkel setup + label generation
  Week 3-5:   Train XGBoost on Snorkel labels
  Week 6-10:  Validation + deployment

SageMaker (10-14 weeks):
  Week 1-2:   AWS setup + data pipeline
  Week 3-5:   Feature engineering + data prep
  Week 6-9:   Model training + hyperparameter tuning
  Week 10-14: SageMaker Clarify SHAP + validation + deployment

Dataiku (8-12 weeks):
  Week 1-2:   Platform setup + data import
  Week 2-4:   AutoML model building
  Week 5-9:   Model validation + tuning
  Week 10-12: Deployment + MLOps setup

Kubeflow (12-20 weeks):
  Week 1-4:   Kubernetes cluster setup
  Week 5-7:   Pipeline design + containerization
  Week 8-10:  Feature store (Feast) setup
  Week 11-13: Training + model registry
  Week 14-17: KServe serving setup
  Week 18-20: Monitoring + optimization
```

---

## Cost Breakdown Over 3 Years

```
Snorkel + XGBoost (Open-Source):
  Year 1: Setup $5K + ops $24K = $29K
  Year 2: Ops only = $24K
  Year 3: Ops only = $24K
  Total 3-year: $77K ($26K/year average)

SageMaker (RECOMMENDED):
  Year 1: Setup + ops = $70K
  Year 2: Ops only = $54K
  Year 3: Ops only = $54K
  Total 3-year: $178K ($59K/year average)

Dataiku:
  Year 1: Setup + ops = $90K
  Year 2: Ops only = $95K
  Year 3: Ops only = $95K
  Total 3-year: $280K ($93K/year average)

Kubeflow (Self-Managed):
  Year 1: Setup + ops = $48K
  Year 2: Ops only = $36K
  Year 3: Ops only = $36K
  Total 3-year: $120K ($40K/year average)

Feedzai / Commercial:
  Year 1: Licensing + setup = $150K
  Year 2: Licensing only = $150K
  Year 3: Licensing only = $150K
  Total 3-year: $450K ($150K/year average)
```

---

## Final Recommendation

### PRIMARY: SageMaker + Snorkel Hybrid (Best Risk/Reward)
- **Cost:** $70K-97K first year
- **Time:** 10-14 weeks
- **Explainability:** SHAP native + Snorkel rules
- **Government Fit:** FedRAMP + GovCloud + Treasury precedent
- **Feedback Loop:** Officer rules → Snorkel → retrain monthly
- **Why:** Combines government-proven platform (SageMaker) with tight feedback loop (Snorkel)

### SECONDARY: Snorkel + XGBoost (Budget-Conscious)
- **Cost:** $36K-48K first year
- **Time:** 6-10 weeks
- **Explainability:** Labeling functions are inherently explainable rules
- **Feedback Loop:** Tightest (officers directly refine rules)
- **Why:** Cheapest; if CBP officers can articulate fraud rules

### TERTIARY: SageMaker Only (If Budget Tight & Feedback Loop Not Priority)
- **Cost:** $48K-80K first year
- **Time:** 10-14 weeks
- **Explainability:** SHAP native (best for compliance)
- **Government Fit:** Treasury proven
- **Why:** If regulatory compliance is #1 priority; Snorkel integration not critical

---

**Decision Date:** June 12, 2026  
**Next Step:** Answer the 8 clarifying questions in PLATFORM_COMPARISON_SUMMARY.md before final selection
