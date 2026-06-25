# Precise Risk Model: Executive Summary & Kickoff

**Project**: Precise Risk Model - Generalized, Multi-Tenant Risk Scoring Framework  
**Status**: Ready for Implementation Kickoff  
**Timeline**: 16 weeks (4 phases) to production-ready  
**Budget**: $190K-200K (AWS/GCP, labor, data)  
**Team**: 2 backend engineers, 1 ML engineer, 1 DevOps, 0.5 FTE domain experts

---

## WHAT WE'RE BUILDING

A **generalized, reusable risk scoring framework** that:

1. **Works across domains**: CBP Illegal Transshipment, FDA Imports Fraud, Opioid Detection (same codebase, different configs)
2. **Is operational with current data**: EAPA (287 confirmed cases), Senzing (entity resolution), current manifests
3. **Doesn't break existing functionality**: All 5 CBP Sentry tabs work unchanged
4. **Reduces code duplication**: One code path (Precise Risk Model) replaces hardcoded risk_scoring_engine.py
5. **Is production-ready**: Feature flags, rollback safety, monitoring, active learning

---

## KEY DECISIONS (LOCKED)

### Architecture
| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Database** | Same DB (cbp_sentry), new schema (risk_scoring) | Shared infrastructure, data isolation via domain_id |
| **Service** | Separate microservice (precise-risk-engine-api) | Independent scaling, reusable, clean separation |
| **Storage** | GCP Cloud Storage (not S3) | Align with existing infrastructure |
| **Model Versioning** | Database-based (PostgreSQL), not Git | Models queryable, temporal, no pickles in Git |
| **Code Approach** | Configuration-driven, zero hardcoding | One codebase serves all domains |
| **Multi-Tenancy** | Design for it, deploy single-tenant | Future-proof architecture |
| **Backward Compatibility** | Keep legacy risk_scoring_engine.py (archived, feature-flagged) | Instant rollback if new model fails |

### Data
| Source | Status | Sufficiency |
|--------|--------|-------------|
| **EAPA Cases** | Available (287 confirmed transshipment) | Sufficient for baseline XGBoost training (AUC 0.82-0.84) |
| **Senzing** | Currently deployed (244K entities) | Used for party risk, entity resolution |
| **Current Manifests** | Live feed (50K/week) | Used for feature engineering |
| **OpenCorp API** | Free, needs integration (5 days) | Beneficial ownership enrichment |
| **Vessel/AIS Data** | Partial, needs integration (weeks 2-3) | Routing anomalies, dwell baselines |

### UI/UX
| Screen | Status | Changes |
|--------|--------|---------|
| **V2AITuningPage** | Enhanced | Domain selector added, dynamic factor loading |
| **CommandCenter** | Unchanged | Shows new model's metrics (no workflow change) |
| **ActiveInvestigations** | Unchanged | No changes |
| **ShipmentIntelligence** | Unchanged | No changes |
| **EntityResolution** | Unchanged | No changes |

---

## IMPLEMENTATION ROADMAP

### Phase 1: Foundation (Weeks 1-4)
```
Goal: Deploy XGBoost model on EAPA + manifest data
├─ Week 1: Data validation (EAPA 287 cases + 10K non-EAPA)
├─ Week 2: Feature engineering (72 CBP features)
├─ Week 3: Model training (XGBoost, Isolation Forest, SHAP)
├─ Week 4: Microservice deployment (precise-risk-engine-api)
└─ Deliverable: Risk engine ready, AUC 0.82+ on CBP
```

### Phase 2: Integration (Weeks 5-8)
```
Goal: Integrate without breaking existing functionality
├─ Week 5-6: Service integration (feature flag for gradual rollout)
├─ Week 7: V2AITuningPage refactoring (domain selector, dynamic loading)
├─ Week 8: Cleanup (archive legacy code, full regression testing)
└─ Deliverable: All tabs working through new model, rollback-safe
```

### Phase 3: Multi-Domain (Weeks 9-12)
```
Goal: Extend to FDA and Opioid (same code, different configs)
├─ Week 9-10: FDA domain (data gathering, feature engineering, training)
├─ Week 11: Opioid domain (similar process)
├─ Week 12: Multi-domain validation (no data mixing, routing works)
└─ Deliverable: 3 domains live (1 codebase, 3 configs)
```

### Phase 4: Production Hardening (Weeks 13-16)
```
Goal: Security, performance, scalability
├─ Week 13-14: Hardening (GCP compliance, load testing, DR)
├─ Week 15: Productization (template configs for future domains)
├─ Week 16: Final planning (roadmap for Bayesian networks, ensemble models)
└─ Deliverable: Production-ready "Precise Risk Model" product
```

---

## DATA SUFFICIENCY DECISION GATE (Week 2)

### If Data Is Sufficient (Expected)
```
Proceed with Phase 1 XGBoost training
├─ EAPA 287 cases + 10K manifests = 10,287 training samples
├─ 2.8% positive class (transshipment cases)
├─ Expected AUC: 0.82-0.84
└─ Timeline: On schedule
```

### If Data Is Insufficient (Contingency)
```
Activate Scenario B (escalation path)
├─ Option 1: Extend data search (+100-200 EAPA cases from CBP records)
├─ Option 2: Deploy rules-only (Gate 1 deterministic, skip XGBoost for now)
├─ Option 3: Transfer learning (if FDA/Opioid have more labeled cases)
└─ Decision: Made at Week 2 checkpointc with stakeholders
```

---

## SAFETY & ROLLBACK

### Feature Flag Strategy
```python
# In configuration
use_legacy_model = False  # Default: new Precise Risk Model

# In code
if use_legacy_model:
    score = risk_scoring_engine_legacy.score(shipment)
else:
    score = call_risk_engine_api(shipment)

# If new model fails in production:
# 1. Set use_legacy_model = True
# 2. Restart services
# 3. Immediate rollback (no redeployment)
# 4. Continue operating on old model while investigating
```

### Parallel Running (Weeks 5-8)
```
Both models run simultaneously during integration
├─ New model: Calls precise-risk-engine-api (HTTP)
├─ Old model: Calls risk_scoring_engine_legacy.py (in-process, read-only)
├─ Compare scores: Track divergence, debug differences
├─ Traffic ramping:
│  ├─ Week 5: 10% traffic on new model, 90% old
│  ├─ Week 6: 50% traffic on new model, 50% old
│  ├─ Week 7: 90% traffic on new model, 10% old
│  └─ Week 8: 100% traffic on new model (old still running, can switch back)
└─ Confidence: Before going 100%, teams are confident
```

### Archival Strategy
```
Legacy code (archived, kept indefinitely):
├─ File: risk_scoring_engine_legacy.py (not deleted, just marked deprecated)
├─ File: risk_models_legacy.py (not deleted, just marked deprecated)
├─ Branch: Git branch legacy/risk-scoring (snapshot if needed)
├─ Feature flag: Enables/disables legacy code at runtime
└─ Post-Week 16: Can optionally move to separate branch, but code remains in main
```

---

## SUCCESS METRICS

### Model Performance Targets
```
Week 4 (Phase 1):
├─ AUC: 0.82-0.84 (on 287 EAPA cases)
├─ PPV @ 80% confidence: 30-40%
├─ Sensitivity: 70-75%
└─ Inference latency P95: <200ms

Week 8 (Phase 2, post-integration):
├─ AUC: Maintained at 0.82+ (no regression from integration)
├─ All 5 tabs: Functional (zero regressions)
├─ Feature flag test: Can switch old ↔ new instantly
└─ Rollback test: Verified working end-to-end

Week 12 (Phase 3, multi-domain):
├─ CBP AUC: 0.82+ (maintained)
├─ FDA AUC: 0.80+ (new domain)
├─ Opioid AUC: 0.78+ (new domain)
└─ Data isolation: Zero cross-domain data leakage

Week 16 (Phase 4, production):
├─ CBP AUC: 0.90+ (with active learning: 1,500+ cases)
├─ Load test: 1,000 scores/second (sustained)
├─ Disaster recovery: <1 hour RTO/RPO
└─ Monitoring: Drift detection, PPV tracking, latency alerts
```

### Operational Metrics
```
Week 8: Backward Compatibility
├─ CommandCenter tab: Shows metrics correctly
├─ ActiveInvestigations: Case data loads correctly
├─ ShipmentIntelligence: Entity enrichment works
├─ EntityResolution: Graph visualization works
└─ Regression tests: All pass, zero test breakage

Week 12: Multi-Domain
├─ Domain selector: Works (cbp, fda, opioid)
├─ Config isolation: No data mixing
├─ API routing: domain_id correctly routed
└─ Scorecard loading: Dynamic factors load per domain

Week 16: Production
├─ Uptime: 99.9%+
├─ Incident response: Rollback <5 minutes
└─ Documentation: Complete (adding new domain takes <1 day)
```

---

## TEAM & RESPONSIBILITIES

### Core Team (Required)
```
Backend Engineer #1: Service architecture, API development
├─ Weeks 1-4: Microservice scaffold, API endpoints
├─ Weeks 5-8: Integration, feature flag implementation
└─ Weeks 9-16: Multi-domain support, refactoring

Backend Engineer #2: V2UITuningPage refactoring, integration testing
├─ Weeks 1-4: Parallel feature engineering code review
├─ Weeks 5-8: V2AITuningPage refactoring, regression testing
└─ Weeks 9-16: Multi-domain UI enhancements

ML Engineer: Model training, active learning pipeline
├─ Weeks 1-4: Feature engineering, XGBoost training, SHAP setup
├─ Weeks 5-8: Model comparison (old vs new), drift detection
├─ Weeks 9-16: Active learning, monthly retraining, model versioning

DevOps Engineer (0.5 FTE): Deployment, monitoring, infrastructure
├─ Weeks 1-4: Docker, GCP Cloud Storage, ECS setup
├─ Weeks 5-8: Feature flag implementation, health checks
└─ Weeks 9-16: Scaling, monitoring, disaster recovery

Domain Experts (0.5 FTE, on-call):
├─ FDA expert: Weeks 9-10 (domain-specific features, rules)
├─ Opioid expert: Week 11 (domain-specific features, rules)
└─ CBP expert: Throughout (feedback, validation, UAT)
```

### Stakeholders (Weekly Sync)
```
CBP Operations Team:
├─ Validates backward compatibility
├─ Provides feedback for active learning
└─ Approves rollout to production

Leadership:
├─ Reviews timeline, budget, metrics
├─ Approves escalations (data sufficiency, feature flags)
└─ Sponsors multi-domain roadmap
```

---

## BUDGET BREAKDOWN

### Development Costs
```
Phase 1 (Weeks 1-4): $30K
├─ 2 backend engineers: $20K
├─ 1 ML engineer: $10K

Phase 2 (Weeks 5-8): $30K
├─ 2 backend engineers: $15K
├─ 1 ML engineer: $10K
├─ 1 DevOps engineer: $5K

Phase 3 (Weeks 9-12): $20K
├─ 2 backend engineers: $10K
├─ 1 ML engineer: $5K
├─ Domain experts: $5K

Phase 4 (Weeks 13-16): $25K
├─ 1 backend engineer: $10K
├─ 1 DevOps engineer: $10K
├─ Documentation, planning: $5K

TOTAL LABOR: $120K
```

### Infrastructure Costs
```
AWS/GCP: $50K (6 months)
├─ RDS PostgreSQL: $200/month × 6 = $1,200
├─ GCP Cloud Storage: $50/month × 6 = $300
├─ ElastiCache Redis: $100/month × 6 = $600
├─ ECS/Compute: $300/month × 6 = $1,800
└─ Monitoring/Tools: $500/month × 6 = $3,000

Data/APIs: $20K (6 months)
├─ OpenCorp API caching: $500-1,000/month × 3 = $1,500-3,000
├─ Vessel/AIS data: $100/month × 6 = $600
└─ Buffer: $15K

TOTAL INFRA: $70K
```

### Grand Total
```
Labor: $120K
Infrastructure: $70K
TOTAL: $190K (6 months to production-ready)
```

---

## RISK MITIGATION

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| EAPA data insufficient | Low | High | Week 2 decision gate, data search contingency |
| New model has lower accuracy than old | Medium | Medium | Feature flag, parallel running, comparison tests |
| Integration breaks existing tabs | Low | High | Full regression test suite, feature flag for gradual rollout |
| GCP storage performance issues | Low | Medium | Performance testing Week 4, fallback to local cache |
| Multi-tenant design adds complexity | Medium | Medium | Start single-tenant (domain_id only), add tenant_id later |
| Team turnover delays timeline | Low | Medium | Documentation, pair programming, knowledge transfer |

---

## GO/NO-GO DECISION POINTS

### Week 2: Data Sufficiency
```
Question: Can we train XGBoost on 287 EAPA + 10K manifests with acceptable quality?
Exit Criteria:
├─ YES: Proceed to Phase 1 weeks 3-4 (model training)
└─ NO: Activate Scenario B (escalate, or rules-only deployment)
```

### Week 4: Model Quality
```
Question: Does Phase 1 model meet AUC 0.82+ threshold?
Exit Criteria:
├─ YES: Proceed to Phase 2 (integration)
└─ NO: Retrain with adjusted features, extend Week 4 if needed
```

### Week 8: Backward Compatibility
```
Question: Do all 5 CBP Sentry tabs work through new model?
Exit Criteria:
├─ YES: Proceed to Phase 3 (multi-domain)
└─ NO: Fix regressions, extend Week 8 if needed
```

### Week 12: Multi-Domain Validation
```
Question: Are FDA/Opioid models trained and validated?
Exit Criteria:
├─ YES: Proceed to Phase 4 (hardening)
└─ NO: Extend Phase 3, accelerate Phase 4
```

### Week 16: Production Ready
```
Question: Is system ready for production launch?
Exit Criteria:
├─ YES: Launch "Precise Risk Model" product
└─ NO: Extend hardening, schedule post-launch work
```

---

## APPROVAL CHECKLIST

Before kickoff, confirm:

- [ ] **Storage**: GCP Cloud Storage approved (not S3)
- [ ] **Data**: EAPA (287 cases) + Senzing + manifests confirmed available
- [ ] **Backward Compatibility**: All 5 tabs must remain functional
- [ ] **Rollback Safety**: Legacy code archival + feature flag strategy approved
- [ ] **Team**: Resource allocation confirmed (2 backend, 1 ML, 1 DevOps)
- [ ] **Budget**: $190K-200K approved for 16-week timeline
- [ ] **Success Metrics**: AUC targets, latency targets, TAPs defined
- [ ] **Decision Gates**: Week 2 (data), Week 4 (model), Week 8 (integration), etc.
- [ ] **Stakeholders**: Weekly sync schedule confirmed

---

## NEXT STEPS (Week 1)

**Immediately (Day 1-2)**:
1. [ ] Schedule kickoff meeting (all team + stakeholders)
2. [ ] Confirm EAPA data access (287 confirmed cases)
3. [ ] Confirm Senzing integration (already running)
4. [ ] Set up GCP Cloud Storage bucket (cbp-sentry-models)

**Week 1 (Days 3-5)**:
1. [ ] Create PostgreSQL schema (risk_scoring namespace)
2. [ ] Create Git repository structure (precise-risk-engine)
3. [ ] Data validation (EAPA quality, feature extraction feasibility)
4. [ ] Kickoff team meetings (architecture review, code review process)

**By Week 2**:
1. [ ] Data sufficiency checkpoint
2. [ ] Feature engineering code ready for review
3. [ ] Go/No-Go decision (proceed or escalate)

---

**Ready to execute. Awaiting final approval on checklist above.**

