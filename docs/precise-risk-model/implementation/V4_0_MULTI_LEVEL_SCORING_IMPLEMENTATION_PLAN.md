# Risk Model v4.0 — Implementation Plan (Multi-Subagent Executable)

**Date:** June 29, 2026
**Design source of truth:** [`../decisions/DECISION_MULTI_LEVEL_FACTOR_SCORING.md`](../decisions/DECISION_MULTI_LEVEL_FACTOR_SCORING.md) — this plan does **not** restate design; it executes it.
**Status:** Phase 0 ready to execute now (no external blockers).

> **DOC DISCIPLINE (hard rule for every executor / subagent):** Do **not** create new design, architecture, or `*_SUMMARY` / `*_DESIGN` / `*_ANALYSIS` markdown files. All design lives in the decision record above; all execution status lives in **this** file (check the boxes). Subagents return findings to the orchestrator; the orchestrator updates this single plan. This repo already has doc sprawl (FIXES_SUMMARY, COMPLETE_REDESIGN, ALL_TABS_ARE_MOCK_DATA, …) — do not add to it.

---

## Objective

Ship Risk Model **v4.0**: a 3-level factor score (shipment / corridor / entity) over one resolved-entity graph, the data needed to compute it, the **H2 Entity Resolution** experience, and the **referral** that consumes it — moving model maturity toward **30%** (graph factors calibrated, 3-level gates passing, recall lifted off 0.528).

---

## Workstreams

Each workstream maps to one or more subagents. IDs are referenced by the phase/dependency map.

### WS-A — Data onboarding
- **A1** Expose the **287 EAPA cases** (already in PostgreSQL `cbp_sentry`) as a CORD-resolvable source **`CBP-EAPA`** (entity, country, docket, commodity, route, determination). *Executable now — integration, not acquisition.*
- **A2** Load the public **DHS UFLPA Entity List** as source **`UFLPA-ENTITY-LIST`**. *Executable now.*
- **A3** Tag **NPI-PROVIDERS** (71K, healthcare) and **GLOBALDATA** (40K, name-only) as **identity-resolution mass only — excluded from trade scoring/watchlist.**
- *Accept:* watchlist + `/api/cord/entity` surface EAPA/UFLPA flags; NPI/GLOBALDATA absent from scored output.

### WS-B — Resolved-entity graph & edge materialization
- **B1** Derive edges from shared `IDENTIFIERS`/`ADDRESSES` + `RELATIONSHIPS` (GLEIF, OPEN-OWNERSHIP, OPEN-SANCTIONS) → materialized `entity_edges` table.
- **B2** Graph store: corridor–actor–manifest bipartite + actor↔actor network; populate `/parties` and `/chain` from materialized edges (currently empty for most entities).
- **B3** Graph signals: degree (cross-corridor reach), centrality (hub), shared-identifier shell indicators, resolved-vs-explicit identity delta.
- *Accept:* `/parties`,`/chain` non-empty for flagged entities; degree + shell indicators computable.

### WS-C — Multi-level factor scoring engine
- **C1** Extend `risk_scoring_engine.py` to emit an **entity** `RiskScoreBreakdown` (factors: enforcement flags EAPA/OFAC/UFLPA/fraud, network/shell, cross-corridor reach, newness, prevalence, incoming).
- **C2** Emit a **corridor** `RiskScoreBreakdown` (commodity/routing/pattern/time + party-risk via **top-k blend**, k=5).
- **C3** Graph accounting: contributions = edge weights; node scores = aggregates; **by-shipment-count** apportionment.
- **C4** Event-driven incremental recompute + propagation; stamp every score `(model_version, cord_resolution_version, inputs_hash, computed_at)`.
- *Accept:* corridor + entity scores with factor breakdown; entity-flag change ripples to corridor + shipment; scores reproducible.

### WS-D — MLOps / registry
- **D1** Register **v4.0 as one bundled version** (weights + calibrators + XGBoost + locked params + **CORD resolution snapshot** + feature-pipeline version).
- **D2** Calibrate the new graph factors against EAPA labels; tune k.
- **D3** New validation gate (top-scored corridors/actors rank-correlate with EAPA respondents / bad lanes); per-level drift.
- **D4** Backfill re-score under v4.0; retain prior (`seed_` vs `calculated_`).
- *Accept:* v4.0 registered, gates pass, maturity metric trending to 30% (recall > 0.528).

### WS-E — H2 Entity Resolution experience (UI) — **GATED on A,B,C**
- **E1** Corridor lens (corridor selector → prevalent actors → factor-tree drill).
- **E2** Actor / cross-corridor lens (US-importer spine, conditioned reach, resolved-vs-explicit delta).
- **E3** Factor-tree navigation (score explanation = navigation; party→H2, incoming→H3 bridges).
- **E4** DAG-annotated shared nodes; network subgraph for discovery.
- *Accept:* actor scores with factor attribution; cross-corridor reach surfaced; drills to corridor (H1) and 72h manifests (H3).

### WS-F — Referral enhancement (H2 consumer)
- **F0** Render **OFAC status** (in DB, not displayed) — `referral_comprehensive_v2.py` §3-10 / `ReferralPackageV2.tsx:797`. **Quick win, no deps.**
- **F1** Per-entity factor-attributed risk (§3-10).
- **F2** Beneficial ownership + shared-identifier evidence (§3-5, `referral_comprehensive_v2.py:187`).
- **F3** Shell indicators (§3-5/§3-10).
- **F4** EAPA anchor linkage (§3-7, `:294`) — needs **A1**.
- **F5** Cross-corridor reach (§3-7/§3-12).
- **F6** New §3-5a entity-network-evidence panel + `EntityNetworkEvidencePanel.tsx` — needs **B**.
- *Accept:* referral renders entity factor score + OFAC + EAPA anchor + network; CSOP 14-section structure intact.

---

## Phase / dependency map (execution order)

| Phase | Tasks | Parallel? | Blockers |
|---|---|---|---|
| **0 — Foundations (NOW)** | A1, A2, A3, B1, **F0**, C1-scaffold | ✅ fully parallel | none |
| **1 — Graph + Scores** | B2, B3, C1-full, C2, C3 | partial | B2/B3←B1; C1←A1/A2+B3; C2/C3←C1 |
| **2 — Lifecycle** | C4, D1–D4 | partial | ←Phase 1 |
| **3 — Experience (gated)** | E1–E4, F1–F6 | partial | ←C scores + A/B data |

---

## Multi-subagent execution

**Phase 0 — launch now (5 parallel subagents, worktree isolation for code-mutating tasks):**

| Subagent | Task | Files (primary) | Verify |
|---|---|---|---|
| `data-eapa` | A1 expose EAPA as CORD source | `services/api/cord_engine.py`, EAPA Postgres read | `/api/cord/entity` shows EAPA flag |
| `data-uflpa` | A2 load UFLPA list + A3 tag identity-only | `cord_engine.py`, loader | watchlist shows UFLPA; NPI/GLOBALDATA excluded |
| `graph-edges` | B1 edge materialization | `cord_engine.py`, new `entity_edges` | edges count > 0 from shared ids/addrs |
| `referral-ofac` | F0 OFAC render quick win | `referral_comprehensive_v2.py`, `ReferralPackageV2.tsx` | OFAC status visible in referral §3-10 |
| `score-scaffold` | C1 entity-scorer skeleton emitting `RiskScoreBreakdown` | `risk_scoring_engine.py` | unit test: entity score returns by_factor |

Each subagent: scoped task, **typecheck/build/test verification**, returns a findings summary to the orchestrator. **No new docs.** Orchestrator integrates, checks the boxes here, commits.

**Phases 1–3** are launched the same way after the prior phase's accept criteria pass (the orchestrator gates each phase).

---

## Progress (orchestrator updates only)

- [ ] **Phase 0** — A1 ☐ · A2 ☐ · A3 ☐ · B1 ☐ · F0 ☐ · C1-scaffold ☐
- [ ] **Phase 1** — B2 ☐ · B3 ☐ · C1 ☐ · C2 ☐ · C3 ☐
- [ ] **Phase 2** — C4 ☐ · D1 ☐ · D2 ☐ · D3 ☐ · D4 ☐
- [ ] **Phase 3** — E1 ☐ · E2 ☐ · E3 ☐ · E4 ☐ · F1 ☐ · F2 ☐ · F3 ☐ · F4 ☐ · F5 ☐ · F6 ☐

---

## Open items (close at H2 kickoff — from the decision record §10)

1. UFLPA list source/format for A2 (DHS public list); EAPA field mapping for A1.
2. Edge-materialization approach for B1 (shared-identifier derivation vs Senzing load expansion vs both).
3. Confirm k=5 (top-k) + blend curve on a validation split (D2).
4. Corridor/entity scoring location: extend `risk_scoring_engine.py` (recommended) vs separate aggregation pass.
