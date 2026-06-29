# Precise Risk Model Documentation

**Generalized, Multi-Tenant Risk Scoring Framework for CBP, FDA, and Opioid Detection**

---

## 📂 Directory Structure

```
docs/precise-risk-model/
├── README.md (this file)
├── DOCUMENTS_OVERVIEW.md ← START HERE
│
├── design/
│  ├── PRECISE_RISK_MODEL_COMPLETE_DESIGN.md (50 pages, technical architecture)
│  └── ARCHITECTURE_CLARIFICATION.md (6 locked decisions)
│
├── implementation/
│  ├── PRECISE_RISK_MODEL_IMPLEMENTATION_PLAN.md (30 pages, 16-week roadmap)
│  ├── PRECISE_RISK_MODEL_EXECUTIVE_SUMMARY.md (20 pages, approval checklist)
│  └── V4_0_MULTI_LEVEL_SCORING_IMPLEMENTATION_PLAN.md (multi-subagent executable plan for DECISION 7) ← NEW
│
└── decisions/
   ├── DECISION_FRAMEWORK_WITH_ALTERNATIVES.md (6 decisions with alternatives)
   ├── BUILD_VS_BUY_DECISION.md (platform evaluation)
   └── DECISION_MULTI_LEVEL_FACTOR_SCORING.md (v4.0: 3-level factor scoring over a resolved-entity graph; MLOps lifecycle; EAPA/UFLPA data gate; referral consumer) ← NEW
```

---

## 🎯 RECOMMENDED READING ORDER

### 1️⃣ **Start Here** (15 min)
- **File**: `DOCUMENTS_OVERVIEW.md`
- **Purpose**: Understand how all documents fit together
- **For**: Everyone (technical and non-technical)

### 2️⃣ **For Stakeholders/Approvers** (20 min)
- **File**: `implementation/PRECISE_RISK_MODEL_EXECUTIVE_SUMMARY.md`
- **Purpose**: Budget, timeline, approval checklist, risk mitigation
- **For**: Leadership, decision makers, project sponsors

### 3️⃣ **For Project Managers/Team Leads** (30 min)
- **File**: `implementation/PRECISE_RISK_MODEL_IMPLEMENTATION_PLAN.md`
- **Purpose**: Week-by-week breakdown, data gates, go/no-go checkpoints
- **For**: Project managers, team leads, architects

### 4️⃣ **For Engineers/Architects** (deep dive)
- **File**: `design/PRECISE_RISK_MODEL_COMPLETE_DESIGN.md`
- **Purpose**: PostgreSQL schema, APIs, 3-gate model, algorithms
- **For**: Engineers, ML engineers, architects

### 5️⃣ **For Design Reviews** (10 min)
- **File**: `design/ARCHITECTURE_CLARIFICATION.md`
- **Purpose**: 6 locked architectural decisions with rationale
- **For**: Architects, lead engineers

### 6️⃣ **For Decision Context** (optional deep dive)
- **File**: `decisions/DECISION_FRAMEWORK_WITH_ALTERNATIVES.md`
- **Purpose**: All alternatives considered for each decision
- **For**: Architects, decision makers who want full context

---

## 📋 QUICK REFERENCE

| Document | Pages | Audience | Focus |
|----------|-------|----------|-------|
| DOCUMENTS_OVERVIEW.md | 3 | Everyone | How docs work together |
| EXECUTIVE_SUMMARY.md | 20 | Leadership | Budget, timeline, approval |
| IMPLEMENTATION_PLAN.md | 30 | Team leads | Week-by-week roadmap |
| COMPLETE_DESIGN.md | 50 | Engineers | Technical architecture |
| ARCHITECTURE_CLARIFICATION.md | 5 | Architects | 6 locked decisions |
| DECISION_FRAMEWORK.md | 20 | Decision makers | All alternatives |
| BUILD_VS_BUY_DECISION.md | 15 | Leadership | Platform evaluation |

---

## 🚀 NEXT STEPS

### For Implementation Kickoff

1. **Day 1**: Review `DOCUMENTS_OVERVIEW.md` (all team)
2. **Day 2**: Review `EXECUTIVE_SUMMARY.md` (stakeholders confirm approval)
3. **Day 3**: Team reads sections relevant to their role
4. **Day 4**: Architecture review (based on ARCHITECTURE_CLARIFICATION.md)
5. **Day 5**: Kickoff meeting (first milestone: Week 1 data validation)

### Success Criteria

All documents are:
- ✅ Data-driven (uses EAPA 287 cases, Senzing, current manifests)
- ✅ Backward compatible (all 5 CBP Sentry tabs continue working)
- ✅ Safe (feature flag, legacy code archival, instant rollback)
- ✅ No duplication (refactored, one code path for 3 domains)
- ✅ Production-ready (monitoring, active learning, drift detection)
- ✅ Multi-tenant ready (design for scale, deploy single-tenant first)

---

## 📞 Questions?

- **Technical questions**: See `design/PRECISE_RISK_MODEL_COMPLETE_DESIGN.md`
- **Timeline/budget questions**: See `implementation/PRECISE_RISK_MODEL_EXECUTIVE_SUMMARY.md`
- **Architecture decisions**: See `design/ARCHITECTURE_CLARIFICATION.md`
- **Why not alternative X?**: See `decisions/DECISION_FRAMEWORK_WITH_ALTERNATIVES.md`

---

**Status**: Ready for stakeholder review and team kickoff.  
**Last Updated**: June 29, 2026 — added DECISION 7 / `DECISION_MULTI_LEVEL_FACTOR_SCORING.md` (v4.0 multi-level factor scoring; data-readiness gate for H2).
