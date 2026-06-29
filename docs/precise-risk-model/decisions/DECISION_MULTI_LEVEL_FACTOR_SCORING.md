# Decision: Multi-Level Factor Scoring over a Resolved-Entity Graph (Risk Model v4.0)

**Date:** June 29, 2026
**Status:** Scoring synthesis + lifecycle **DECIDED**; aggregation/apportionment rules **LOCKED**; data-readiness items **OPEN (prerequisites for H2 build)**
**Extends:** `design/PRECISE_RISK_MODEL_COMPLETE_DESIGN.md`, `design/ARCHITECTURE_CLARIFICATION.md`
**Drives:** the H2 (Entity Resolution) design, which must not begin until the data-readiness gate below is closed.

---

## 1. Context & Finding

The platform is a **3-horizon** intelligence funnel:

- **H1 — Corridor:** lanes (origin → transshipment → destination + commodity) and the trade-law regime (AD/CVD, Section 301, UFLPA). Standing/strategic.
- **H2 — Entity Resolution:** the prevalent actors flagged by EAPA / OFAC / forced-labor / fraud-criminal datasets (what CORD covers), and their resolved networks. The actor-intelligence middle.
- **H3 — Manifest/Shipment:** the specific shipment arriving within ~72 hours — inspect or not. Tactical/time-bound.

**The finding:** Corridor (H1) and Entity (H2) should each get their **own** risk score, built from the **same seven-factor recipe** the shipment scorer already uses (`score_shipment()` in `risk_scoring_engine.py`), computed over **one shared resolved-entity graph** — and the **factor breakdown of each score is the navigation between the horizons**. Two of the existing seven factors *are* the horizon bridges: **party-risk → H2**, **time/incoming → H3**.

This is a maturity step, not a rewrite: it reuses the existing rule-engine + XGBoost ensemble and the existing `RiskComponentScore`/`by_factor` breakdown contract.

---

## 2. Decision — Three Pillars

1. **Same recipe, three subjects.** Run the existing 7-factor recipe (documentation, commodity, routing, **party**, **corridor**, pattern, **time**) on three subjects: shipment (have it), corridor, and actor. One scoring contract (`RiskScoreBreakdown`), three levels.
2. **Factors are the map.** The biggest factors of a score are its drill paths. A corridor's *party-risk* factor opens into its actors (H2); an actor's *incoming/time* factor opens into its 72-hour arrivals (H3). The score explanation and the inter-horizon navigation are the same object.
3. **One graph underneath.** Actors cross corridors, so every score reads from one resolved-entity graph: **an actor is one node with one global score; each corridor sees an apportioned slice.** Contributions are edge weights; horizon scores are node aggregates. This prevents the double-counting/fragmentation a naive per-corridor computation would reintroduce.

---

## 3. The Seven Factors at Three Levels

| Factor (existing engine) | Shipment (H3) | Corridor (H1) | Actor (H2) |
|---|---|---|---|
| Documentation | ISF/Element-9 discrepancies | aggregate discrepancy rate | filings tied to actor |
| Commodity | HS sensitivity, AD/CVD/301/UFLPA | lane commodity-law exposure | actor's commodity mix |
| Routing | declared-vs-suspected origin | transshipment-hub risk | actor's routing footprint |
| **Party → bridges to H2** | shipper/consignee screen | **aggregate of actors in lane** | enforcement flags + network + reach |
| Corridor → bridges to H1 | the shipment's lane risk | (the subject) | corridors the actor spans |
| Pattern | manifest anomalies | lane anomaly density | actor anomaly history |
| **Time → bridges to H3** | dwell/incoming | incoming pressure | **has 72-hour arrival** |

---

## 4. Locked Rules

### 4.1 Aggregation (party-risk factor) — **LOCKED: top-k blend**
How a corridor's party-risk factor combines its actors.
- *Alt A — max:* worst single actor damns the lane. Surfaces single bad actors; ignores prevalence; unstable to one outlier.
- *Alt B — sum:* prevalence-weighted; rewards systemic lanes; inflated by many low-risk actors.
- **Chosen — top-k blend:** weighted blend of the k highest-risk actors (k configurable, default 5). Captures both "one sanctioned party" and "systemic lane" without unbounded inflation. k and blend weights are tuned on validation and **pinned in the registered model version**.

### 4.2 Apportionment (cross-corridor actor) — **LOCKED: by shipment count**
How a cross-corridor actor's risk splits across the lanes it touches.
- *Alt A — even split / Alt B — by declared value / Alt C — full weight to each (overlap).*
- **Chosen — by shipment count:** the actor's contribution to each corridor is proportional to its share of shipments in that corridor. Keeps corridor scores additive and auditable; the actor retains its full **global** H2 score separately (node aggregate).

---

## 5. Graph Accounting (the invariant)

> **Factor contributions are edge weights; horizon scores are graph-global node aggregates.**

- Actor carries a **global H2 score** (node property).
- Actor carries an **apportioned contribution** to each corridor's party-risk factor (corridor→actor edge property, §4.2).
- Corridor score sums **edge** contributions (§4.1 over its actors); actor score aggregates over **all** its edges.

This is what makes cross-corridor actors first-class and keeps scores stable (no double-count as an actor recurs across lanes).

---

## 6. Model Lifecycle & MLOps (v4.0)

v4.0 keeps the v3.x machinery (rule-engine + XGBoost 70/30 ensemble, EAPA-labeled, MLflow-registered, gate-promoted; see `MODEL_LIFECYCLE_CLARIFICATION.md`). What changes is the artifact and the computation.

### 6.1 Registry — single bundled version (DECIDED)
v4.0 registers as **one** model version (not three), pinning as a coherent unit:
- 7 factor blend weights + per-factor calibrators (prob→score),
- the XGBoost ensemble artifact,
- locked aggregation (top-k, k+weights) and apportionment (by-shipment-count) params,
- **the CORD/Senzing resolution snapshot version** (new lineage dependency — re-resolving entities changes scores even at fixed weights),
- the feature-pipeline version.

Rationale: corridor and actor scores are aggregations of the *same* factor model; registering them together guarantees all three levels always agree. Lifecycle unchanged: training run → register version → gates → candidate/staging/production.

### 6.2 Training / calibration
- Labels unchanged: EAPA determinations + analyst feedback + enforcement outcomes.
- **New work:** the graph-derived features (network centrality, shell indicators, cross-corridor reach, resolved-identity delta) are calibrated/weighted against EAPA labels. These are the maturity lever — v3.x recall is **0.528 (misses 47%)**, and the misses are transshipment-via-resolved-networks, exactly what these features detect.
- Per-factor calibration (`feedback_engine.get_current_weights()`): each factor's calibrator and blend weight is fit and validated independently — modular and testable.
- Aggregation/apportionment are **config** (locked), tuned on a validation split, pinned in the version — not trained.
- Corridor/entity scores validated by a **new gate**: do top-scored corridors/actors rank-correlate with known EAPA respondents / bad lanes?

### 6.3 Computation & propagation (new operational piece)
Event-driven **incremental recompute over the graph**:
- new 72h manifest → score shipment → update corridor + entity contributions;
- new CORD resolution / entity merge → recompute entity node → ripple (apportioned) to corridors → to shipments;
- new EAPA/OFAC/labor flag → recompute entity → ripple up;
- new model version promoted → **backfill re-score**, retaining prior scores for audit (existing `seed_risk_score` vs `calculated_risk_score`).

Shape: contributions materialized at edges; node scores aggregated incrementally; on-read recompute for hot nodes. **Every stored score records `(model_version, cord_resolution_version, inputs_hash, computed_at)`** → reproducible and defensible in a referral.

### 6.4 Monitoring & maturity
- Drift detection extends to per-factor **and** per-level (3 levels).
- Feedback loop closes maturity: dispositions → labels → recalibrate (esp. graph factors) → candidate v4.1 → gates → promote.
- **Maturity to 30% = graph factors calibrated + 3-level validation gates passing + recall lifted off 0.528.**

---

## 7. Data-Readiness Gate (CORD audit, 2026-06-29) — **OPEN, prerequisite for H2**

CORD index = 244K records across 11 sources. Coverage vs the H2 factors:

| H2 factor | Source(s) | Status |
|---|---|---|
| OFAC / sanctions | OFAC (2K), OPEN-SANCTIONS (3.1K) | ✅ |
| Beneficial ownership / network edges | OPEN-OWNERSHIP (5.8K), GLEIF, OPEN-SANCTIONS (`RELATIONSHIPS`) | ✅ data, ⚠️ not materialized |
| Shared address/identifier (shell) | `IDENTIFIERS`/`ADDRESSES` across GLEIF/NOMINO/OPEN-* | ✅ |
| Newness / incorporation dates | GLEIF `DATES`, ICIJ `INCORPORATED`, OFAC est. date, OPEN-OWNERSHIP `DATES` | ✅ |
| Offshore / fraud / risk | ICIJ (33K), NOMINO-RISK (14K `riskcode`) | ✅ |
| **EAPA respondent** | — | ❌ **MISSING (0 matches)** |
| **UFLPA Entity List** | — (US-LABOR-VIOLATIONS is DOL wage/labor, not the DHS UFLPA list) | ❌ **MISSING (0 matches)** |
| Cross-corridor reach / prevalence / incoming | operational shipments/corridors (by design, not CORD) | join required |

**Required before H2 build:**
1. **Onboard CBP-EAPA** as a first-class source (the ~287 EAPA determinations) — the anchor flag of the entire entity model; currently absent.
2. **Onboard UFLPA-ENTITY-LIST** (DHS) — the gold forced-labor flag; distinct from DOL labor violations.
3. **Materialize relationship → edges** (expand Senzing load and/or derive edges from shared `IDENTIFIERS`/`ADDRESSES`) so the network/shell/centrality factors are computable. (`/parties` and `/chain` currently return empty for most entities.)
4. **Mark NPI-PROVIDERS (71K, US healthcare) and GLOBALDATA (40K, name-only) as identity-resolution mass only — excluded from trade scoring** so they don't pollute the actor watchlist.

---

## 8. Referral Package = Primary Consumer of the H2 Score

The referral (14-section CSOP doc) is the output surface of H2. It already organizes around Horizon 1–3 (Q3), already has **Section 3-5 "Entity Ownership Chain (CORD-resolved)"**, and already uses the **`RiskComponent` factor-attribution model** — the same contract as `RiskScoreBreakdown`. So the entity score renders natively. Enhancements (each = an H2 factor, gated by §7):

| Evidence to add | Insertion point | Gated by |
|---|---|---|
| Per-entity factor-attributed risk score | §3-10 / `referral_comprehensive_v2.py:334`; `ReferralPackageV2.tsx:797` | H2 score |
| OFAC / sanctions status (**in DB, not rendered — quick win, no H2 dep**) | §3-10 | none |
| Beneficial ownership (UBO) + shared-identifier evidence | extend §3-5 / `referral_comprehensive_v2.py:187` | edge materialization |
| Shell indicators (incorporation age, address/officer churn) | §3-5 / §3-10 | newness data (have) + edges |
| EAPA anchor linkage ("shipper appears in N prior EAPA petitions") | extend §3-7 / `referral_comprehensive_v2.py:294` | CBP-EAPA onboarding |
| Cross-corridor reach | §3-7 / §3-12 | operational join |
| Entity network graph (risk-colored nodes, why-connected, confidence) | new §3-5a + `EntityNetworkEvidencePanel.tsx` | edge materialization |

**Sequencing:** referral enhancements follow the H2 score and the §7 data onboarding — they are the same v4.0 program, not a separate effort. The OFAC-render quick win is the only piece deliverable independently now.

---

## 9. Consequences

- **Positive:** explainable (tree = score explanation), stable (graph dedup), defensible (provenance-stamped scores), reuses existing engine + breakdown contract + referral scaffolding; one paradigm across H1/H2/H3.
- **Cost/Risk:** new graph-accounting substrate; two new data sources (EAPA, UFLPA) to onboard and license; edge-materialization compute; calibration of new factors before maturity claims hold.
- **Gate:** H2 design/build does not start until §7 items 1–3 are scheduled/owned.

---

## 10. Open Items (to close at H2 kickoff)

1. Source/license + load path for **CBP-EAPA** and **UFLPA-ENTITY-LIST**.
2. Edge-materialization approach (Senzing load expansion vs shared-identifier derivation vs both).
3. Confirm **k** (top-k) default = 5 and the blend-weight curve on a validation split.
4. Where corridor/entity score computation lives (extend the existing engine to emit corridor/entity `RiskScoreBreakdown` — recommended — vs a separate aggregation pass).
