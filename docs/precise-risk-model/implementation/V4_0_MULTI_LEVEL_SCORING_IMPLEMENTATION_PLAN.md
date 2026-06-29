# Risk Model v4.0 — Implementation Plan (Multi-Subagent Executable)

**Date:** June 29, 2026
**Design source of truth:** [`../decisions/DECISION_MULTI_LEVEL_FACTOR_SCORING.md`](../decisions/DECISION_MULTI_LEVEL_FACTOR_SCORING.md) — this plan does **not** restate design; it executes it.
**Status:** Ready to execute — contract-first parallel model (Step 0 freeze, then 5 concurrent role-tracks; only final calibration needs the full pipeline assembled).

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

## Execution model: contract-first parallel tracks

The only true serialization point is **freezing the contracts**. Once the interfaces below are fixed, the role-aligned tracks run **concurrently against stubs/fixtures**; integration is a *swap*, not a rebuild. (The current H2 UI already runs on fixtures — proof the pattern works.) This replaces the earlier coarse "phase gate" model: the dependency graph is really *contract → parallel build → late swap-in*, not a serial queue.

### Step 0 — Contract freeze (short; nothing else is blocked once done)
Lock the interfaces every track builds against:
- **CT-1** `RiskScoreBreakdown` at entity + corridor level (reuse the shipment shape)
- **CT-2** `entity_edges` schema (src, dst, edge_type, evidence, confidence)
- **CT-3** CORD source schema for `CBP-EAPA` + `UFLPA-ENTITY-LIST` (entity, country, flag, docket/program, commodity, route)
- **CT-4** graph-signal interface (reach/degree, centrality, shell indicators, resolved-vs-explicit delta)
- **CT-5** score read + propagation API + provenance `(model_version, cord_resolution_version, inputs_hash, computed_at)`
- **CT-6** referral evidence contract (entity factor block, network-evidence block)

### Parallel tracks (run together after Step 0) — one per role group
| Track | Tasks | Builds against (stub) | Primary roles |
|---|---|---|---|
| **T-Data** | A1 EAPA expose · A2 UFLPA load · A3 identity-tag · score/edge tables | CT-2, CT-3 | DBA, data engineer |
| **T-Graph** | B1 edges · B2 store · B3 signals | CT-2, CT-4 (stub edges until B1) | data scientist, backend eng |
| **T-Score** | C1 entity · C2 corridor · C3 accounting | CT-1, CT-3, CT-4 (stub flags/signals) | data scientist, ML eng |
| **T-MLOps** | C4 propagation · D1 registry bundle · D2 calibration harness · D3 gates/drift · D4 backfill | CT-5 (synthetic scores) | ML engineer |
| **T-Experience** | F0 OFAC · E1–E4 H2 UI · F1–F6 referral | CT-1, CT-6 (fixture scores) | UX designer, frontend dev, architect |

All five tracks proceed **in parallel**. File-collision is avoided by module boundaries (own files/dirs per track; worktree isolation for shared touch-points like `cord_engine.py` / `risk_scoring_engine.py`). Even *within* T-Score, the **enforcement-flag factors** (EAPA/OFAC/UFLPA) need only T-Data, while only the **network/shell/reach factors** need T-Graph — so C1 itself splits into two parallel halves.

### Integration barriers (the only late syncs — swap + verify, not rebuild)
- **I-1** real edges (B1) → T-Graph signals
- **I-2** real flags + signals (T-Data, T-Graph) → T-Score
- **I-3** real scores (T-Score) → T-MLOps + T-Experience (replace fixtures/synthetics)
- **I-4** calibration on real scores + EAPA labels → real weights / **maturity-to-30% claim** — the one thing needing full end-to-end; everything before it parallelizes.

So: **1 short freeze → 5 concurrent tracks → 4 late swap-in barriers.** Nothing but I-4 requires the whole pipeline assembled.

### Subagent fan-out
One+ subagents per track, launched together after Step 0. Each: scoped to its module, **typecheck/build/test verification**, returns findings to the orchestrator. **No new docs.** Orchestrator owns the integration barriers (I-1…I-4), checks the boxes below, commits.

---

## Progress (orchestrator updates only)

- [x] **Step 0 — Contracts** — CT-1 ☑ · CT-2 ☑ · CT-3 ☑ · CT-4 ☑ · CT-5 ☑ · CT-6 ☑  *(services/api/v4_contracts.py, ui/src/v2/types/v4Contracts.ts)*
- [ ] **T-Data** — A1 ☐ · A2 ☐ · A3 ☐ · tables ☐
- [ ] **T-Graph** — B1 ☑ · B2 ☐ · B3 ☐
- [ ] **T-Score** — C1 ☑ · C2 ☐ · C3 ☐
- [ ] **T-MLOps** — C4 ☐ · D1 ☐ · D2 ☐ · D3 ☐ · D4 ☐
- [ ] **T-Experience** — F0 ☑ · E1 ☐ · E2 ☐ · E3 ☐ · E4 ☐ · F1 ☐ · F2 ☐ · F3 ☐ · F4 ☐ · F5 ☐ · F6 ☐
- [ ] **Integration** — I-1 ☐ · I-2 ☐ · I-3 ☐ · I-4 (calibration/maturity) ☐

---

## Backlog / tech debt (tracked)

- **DOC-1 — Documentation consolidation (HIGH).** v4.0 design/build content is fragmented across many files (this plan, `decisions/DECISION_MULTI_LEVEL_FACTOR_SCORING.md`, `design/PRECISE_RISK_MODEL_COMPLETE_DESIGN.md`, `design/ARCHITECTURE_CLARIFICATION.md`, `MODEL_LIFECYCLE_CLARIFICATION.md`, `ENTITY_GRAPH_DESIGN_ANALYSIS.md`, the referral UX docs, plus ~40 loose root-level `*_SUMMARY/_DESIGN/_ANALYSIS.md`). A reader must correlate across all of them.
  - **Goal:** one role-organized v4.0 dossier a multi-disciplinary team can start from, with sections per role — **Architect** (system + graph substrate, service boundaries), **Data Scientist** (factors, calibration, labels, maturity), **Data Engineer / DBA** (sources, schemas, edges, migrations), **ML Engineer** (registry, gates, propagation), **Backend Dev** (scoring/graph APIs), **Frontend / UX** (H2 experience, referral) — over a single index with cross-refs, no duplication.
  - **Scope:** audit existing docs → map content to roles → consolidate into the dossier → retire/redirect superseded root-level docs.
  - **Accept:** each named role has one entry point; no design fact lives in two places.
  - **Owner:** TBD. Until then, do **not** spawn new design docs — extend the dossier.

---

## Open items (close at H2 kickoff — from the decision record §10)

1. UFLPA list source/format for A2 (DHS public list); EAPA field mapping for A1.
2. Edge-materialization approach for B1 (shared-identifier derivation vs Senzing load expansion vs both).
3. Confirm k=5 (top-k) + blend curve on a validation split (D2).
4. Corridor/entity scoring location: extend `risk_scoring_engine.py` (recommended) vs separate aggregation pass. 
5. **Entity final-score aggregation** (surfaced building C1): pure-additive over fixed factor weights under-scores single-flag entities — an OFAC-only entity lands ~21/100 (LOW) because only one of seven factors fires, though the OFAC *component* is 9.5/10. Needs a severity-floor (enforcement flag -> minimum tier) or renormalization over applicable factors; resolve at D2 calibration / pinned v4.0 weights. Until then the H2 watchlist flag->tier mapping and the entity scorer disagree.
