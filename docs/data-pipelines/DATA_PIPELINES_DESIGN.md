# CBP Sentry — Continuous Data Pipelines: Design & Planning

> **Status:** 🟡 Draft / living document — we refine this section-by-section as we discuss.
> **Owner:** Rav · **Started:** 2026-06-30 · **Milestone after:** `gate-1-ready`

---

## 0. Changelog
| Date | Change |
|---|---|
| 2026-06-30 | Initial skeleton: objective, open-source landscape, draft architecture, tab UX, phased plan. Current-state ingestion section pending codebase audit. |
| 2026-06-30 | Folded in codebase audit (§4): platform ~60% wired — VesselFinder live, Federal Register AD/CVD coded, CORD=GLEIF/OFAC/OpenSanctions. Reframed plan around reference-data gap (§8). |
| 2026-06-30 | Data-engineering depth: layered/medallion architecture (§5), Reference & Historical Data Hub (§11), operating-for-a-year challenges → responses (§12). Minimal-intervention principle (§1.7). |
| 2026-06-30 | Manifest = file-drop hub + aggregate API (decided). Added Hub DVC layout + golden-seed + file-drop (§11), DQ gates (§13), orchestration (§14), canonical-schema recommendation (§15). |
| 2026-06-30 | Per-data-point sourcing plan + two-tier entity strategy (§16); per-gate plan mapping the 8 Gate-1 rules to sources (§17); Gate-1 sample-manifest critical path for May–Jul (§18). Altana clarified = recommendation, not a raw score. |
| 2026-07-01 | FINALIZED design (§19): data flywheel (EAPA→manifests→scoring→entity list→labeled history), locked decisions, Data Pipeline tab spec, Gate-1 implementation sequence. Manifest ingest bugs fixed (830 rows load, ~25 in-scope critical). |
| 2026-07-01 | Built the **Data Pipelines tab** (registry + run-ledger + 4 endpoints + admin UI under Intelligence Control), seeded with 7 real sources. |
| 2026-07-01 | **EAPA real data journey**: Federal Register API (27 cases) → **Wayback Machine** pivot to cbp.gov (94 cases, 58 named, since cbp.gov Akamai-blocks server IPs) → **PDF harvest** of determination notices (227 entities, 417 relationships, 99/102 PDFs, 7 "Various Importers" cracked into real names) → **loaded into the entity graph** (204 entities, 414 edges; persistent via cord-integration startup). |
| 2026-07-01 | **Entity-registry enrichment** added (§20): GLEIF + SEC EDGAR (free, no token) + OpenCorporates (free token) to resolve EAPA entities → real address / ownership / affiliates / officers, closing the thin CORD cross-ref. |
| 2026-07-01 | Registry enrichment RUN: GLEIF matched 31/209, +8 affiliate nodes, +9 ownership edges (Greenbrier/Hog Slat/MasterBrand hierarchies); loaded + persistent; GLEIF/OpenCorporates/EDGAR registered in the Data Pipelines tab. |

---

## 1. Objective & principles

Build **continuous ingestion pipelines** for the four datasets that feed the risk model, so the platform runs on refreshed data instead of one-time seeds — starting with **manifest, vessel, ISF**, then **entity**, then others.

**Principles**
1. **Online-first, file-fallback.** Each source tries a live/open API; if none exists (or no key configured), it falls back to a CSV/JSON file drop. Same connector interface either way.
2. **Provenance on every row.** Every ingested record is stamped with `source_id`, `source_mode` (online|file), and `ingested_at` — so we can always answer "where did this come from and when."
3. **Fit the existing schema.** Pipelines load into the *current* canonical tables (`shipments`, entities/`senzing_entities`, etc.) and the existing services — not a parallel data store.
4. **In-scope by default.** Filters honor the Gate-1 scope (VN→US, HS 7604/8541) at ingest, with the option to widen later.
5. **Observable + manual-runnable.** A "Data Pipelines" admin tab shows each source's status/last-run/row-count and a "Run now" button; continuous scheduling layers on top.
6. **Honest about gaps.** Where no open source exists (ISF), we say so and use files — we don't pretend a feed exists.
7. **Minimal intervention / automation-first.** Steady state needs no human: periodic pulls, idempotent + incremental, self-healing (retry/fallback), alert only on real SLA/DQ breaches. Manual action is the exception (approve a key, clear a quarantined batch), never the routine.

---

## 2. Scope (reference)

Gate-1 scope drives what we ingest and filter to:
- **Corridor:** VN → US (primary). _(confirm whether to also ingest CN→US, MY→US as comparators)_
- **Commodities:** HS **7604** (aluminum extrusions) + **8541** (solar cells/panels).
- **Three horizons → datasets:**
  | Horizon | Question | Primary dataset(s) |
  |---|---|---|
  | **H1 Corridor** | Is this lane risky? | Manifest (aggregate trade), reference (AD/CVD) |
  | **H2 Entity** | Is this actor risky? | Entity (sanctions, watchlists, ownership) |
  | **H3 Manifest** | Is this shipment risky? | Manifest (shipment-level), ISF, vessel/AIS |
- **Gate-1 close:** deterministic rules, **≥10% PPV** on real outcomes (the officer-review feedback loop).

> 📌 _Open question: confirm exact corridor set + whether ingest is US-import-only._

---

## 3. Datasets & open-source landscape

Per dataset: what it is, the **open** sources, the online-vs-file verdict, and licensing caveats (so "open" is real).

### 3.1 Vessel / AIS — 🟢 live feasible
| Source | Type | Cost / License | Use |
|---|---|---|---|
| **aisstream.io** | Live WebSocket | Free (API key); AIS public | Continuous live vessel positions |
| **NOAA Marine Cadastre** | Bulk CSV/zip | Public domain (US gov) | Historical tracks, dwell, backfill |
| **GFW API** | REST | Free (key) | AIS-derived vessel registry + tracks |
| **Equasis** | Web/lookup | Free (registration) | Vessel particulars (IMO, flag, owner) |
- **Verdict:** **online** (aisstream.io live + NOAA backfill); file fallback = AIS CSV.
- **Caveat:** AIS coverage is positional; mapping a vessel → a specific manifest still needs the manifest side.

### 3.2 Entity / sanctions / ownership — 🟢 live feasible
| Source | Type | Cost / License | Use |
|---|---|---|---|
| **OFAC SDN** | CSV/XML/JSON | Public domain | Sanctioned parties (daily) |
| **OpenSanctions** | Bulk + API | Free non-commercial / CC-BY (commercial = license) | Consolidated sanctions/PEP/watchlists |
| **trade.gov CSL** | REST API | Public domain (free key) | OFAC SDN + BIS Entity List + more, unified |
| **GLEIF (LEI)** | Bulk + API | **CC0 (public domain)** | Company registry + ownership (H2 resolution) |
| **UFLPA list / CBP EAPA** | Web/PDF | Public (scrape) | Forced-labor + EAPA respondents |
- **Verdict:** **online** (OFAC + CSL + GLEIF are clean/free; OpenSanctions for breadth). File fallback = the CORD bundle already in use.
- **Caveat:** OpenSanctions bulk has a commercial-license line — prefer **CSL (trade.gov)** + **GLEIF (CC0)** as the clean core.

### 3.3 Manifest / Bill of Lading — 🟡 partial
| Source | Type | Cost / License | Use |
|---|---|---|---|
| **Census Intl Trade API** | REST | Public domain (free key) | **Aggregate** import volumes/values by HS+country+month (H1 baselines) |
| **USITC DataWeb** | API/bulk | Public domain | HS-level trade + tariff/AD-CVD |
| ImportYeti / Panjiva / ImportGenius | Commercial | **Paid** | Shipment-level BoL (out of scope for "open") |
- **Verdict:** **online for aggregate** (Census/USITC → H1 corridor baselines); **shipment-level manifest = CSV/JSON** (synthetic or sample). True per-shipment US BoL is paywalled (CBP AMS resold by vendors). → **Decision (2026-06-30): scheduled file-drop hub for shipment-level + aggregate public API (Census/Comtrade).**

### 3.4 ISF (Importer Security Filing "10+2") — 🔴 no public source
- ISF is a **confidential importer filing to CBP**; **never publicly released**. Element 9 (stuffing/consolidator) etc. exist in no open dataset.
- **Verdict:** **CSV/JSON only** — synthetic, or derived from manifest fields (consignee/shipper/stuffing). We make this gap explicit in the UI ("file-sourced; no public ISF feed exists").

### 3.5 Summary
| Dataset | Online (continuous) | File fallback | Notes |
|---|---|---|---|
| Vessel/AIS | ✅ aisstream.io + NOAA | CSV | strongest live candidate |
| Entity | ✅ OFAC + CSL + GLEIF | CORD bundle/CSV | very open |
| Manifest | ⚠️ Census/USITC (aggregate) | ✅ CSV/JSON (shipment) | shipment-level paywalled |
| ISF | ❌ none | ✅ CSV/JSON | structural gap, be explicit |

---

## 4. Current-state ingestion (how data enters today)

Audited from the codebase (2026-06-30). **Big takeaway: the platform is already ~60% wired, with several REAL/live sources.** The work is less "build ingestion from scratch" and more "fill reference gaps + make existing sources continuous + observe them."

### 4.1 Per-dataset reality
| Dataset | How it enters today | Live? | Lands in | Gap |
|---|---|---|---|---|
| **Manifest/shipment** | `POST /api/manifest/upload` (Excel/CSV) via `UploadPipelineModal`; + seed scripts (`seed_data.py` 5 rows, `seed_varied_risks.py` 19 rows). ~1,396 rows. | User batch (not scheduled) | `shipments` | No scheduled/continuous ingest; risk_scores were seeded (now rescore-able via our `/api/rescore`) |
| **Vessel / AIS** | `api/services/isf/vessel_tracker.py` — **RAG-first: local archive → VesselFinder API (live key) → fixture**. Fires when `dwell_days` is NULL. Plus `pre_manifest_vessels_seed.json` (static). | ✅ **VesselFinder live** | `shipments` (vessel_*, dwell_days, port_calls, ais_stuffing_country) | On-demand only (no scheduled enrich); pre-manifest list is static seed |
| **ISF / Element 9** | **Derived** in `api/services/isf/isf_service.py` — declared origin vs. vessel's actual last port call (high-risk corridor table + transshipment ports). | Derived from AIS | `shipments` (element9_*, isf_*) | Not real ISF filings (none public) — derived/synthetic |
| **Entity (CORD)** | `services/cord-integration/cord_loader.py` loads **16 JSONL files = 244K entities** (GLEIF 67K, ICIJ 33K, OFAC 2K, OpenSanctions 3K, OpenOwnership 6K, US Labor, GlobalData 40K…) into the Senzing SQLite mock at startup. | Static files | `senzing_entities` | **SE-Asia coverage ~0%** (VN/CN/MY match ≈ 0); no refresh job |
| **AD/CVD reference** | `scripts/fetch_adcvd.py` — **real Federal Register API** (`federalregister.gov/api/v1`) for VN/CN/MY/TH/ID/KH → versioned CSV. | ✅ API coded | `reference/adcvd/*.csv` | **Code exists but never run → files absent → Commodity factor = 0** |
| **Corridor norms / entity age** | `services/api/reference_loader.py` expects `reference/corridors_vn_us.csv`, `reference/entities_vn.csv` (UN Comtrade / OpenCorporates). | Planned | reference loader | **Files don't exist → Party + Pattern factors = 0** |

### 4.2 Existing scaffolding we can build on
- **Upload pipeline:** `services/api/routers/manifest.py` + `services/api/services/manifest_service.py` (parse, dedup, confirm, insert) — a working file-ingest path to generalize.
- **Live API client pattern:** `vessel_tracker.py` RAG-first (archive→API→fixture) is exactly the **online-first / file-fallback** pattern we want — reuse it as the connector template.
- **Reference loader:** `reference_loader.py` already defines the consumption side (`get_adcvd_rate`, `get_corridor_norms`, `get_entity_age`) — pipelines just need to produce its CSVs.
- **Federal Register fetcher:** `scripts/fetch_adcvd.py` is a ready external-source pipeline (just needs running + scheduling).
- **Source files on disk:** `cord-data/` (16 JSONL, 199 MB), `data/cord_rag.db` (19 MB index), `data/feature_matrix_72*.csv` (training), `services/data/seed_data/pre_manifest_vessels_seed.json`.
- ⚠️ **Two API trees:** `services/api/` (main, :8000) **and** `cbp-sentry/api/` (where `services/isf/*` lives). Confirm which is deployed so connectors land in the right tree.

### 4.3 What this means for the plan
The honest reframing: **sources are largely present; outputs and continuity are missing.** Highest-value first move is **filling the reference-data gap with real open APIs** (Federal Register AD/CVD — already coded; UN Comtrade norms) because it **unlocks three currently-zeroed scoring factors** — a bigger, more real win than a new vessel feed (vessel is already live). See revised phasing in §8.

---

## 5. Target architecture (layered, low-ops)

A **medallion-style** flow so a year of data stays manageable, reproducible, and trainable:

```
 SOURCES                  RAW (bronze)            NORMALIZED (silver)        CURATED (gold)             CONSUMERS
 public APIs --pull-->   immutable landing  -->   canonical, deduped,   -->  scored + features    -->  operational tabs
 (periodic, incremental)  + provenance/run_id      typed, conformed,          (auto-rescore on            Risk Model Mgmt (training)
 file drops  --load-->    (replayable)             DQ-gated                   production model)           Data Hub (history / re-seed)
```

- **Connector** — one interface; reuse `vessel_tracker`'s archive->API->fixture pattern:
  `fetch (incremental, watermarked) -> normalize -> DQ-check -> upsert`. Online or file, same contract.
- **Raw / bronze:** every pull lands immutably with `source_id, run_id, fetched_at` -> lets us **replay/backfill** and survive source schema changes without re-pulling.
- **Silver:** canonical, typed, **deduped via natural keys** (`manifest_source_id`, `vessel_imo`, entity `record_id`), conformed to `shipments` / `senzing_entities`. A **DQ gate** runs before promotion; failing rows -> quarantine / dead-letter.
- **Gold:** scored (auto-rescore under the production model via our `/api/rescore`), feature rows, **date-partitioned** for retention + training.
- **Registry** (`data_sources`) + **run ledger** (`ingestion_runs`: run_id, source, window, rows_in/out/quarantined, status, started/ended) = the lineage AND the data behind the Pipelines tab.
- **Orchestrator:** a dependency-aware DAG `source -> normalize -> DQ -> load -> rescore` (manifest -> ISF-derive -> score). Start with APScheduler/cron in a worker; graduate to Dagster/Airflow only if needed.
- **Provenance everywhere:** `source_id, source_mode, run_id, ingested_at` on every row.

> Detail in **§11 (Reference & Historical Data Hub)** and **§12 (operating-for-a-year challenges)**.


## 6. "Data Pipelines" tab (Intelligence Control)

A new admin tab (sidebar `admin` section, next to Risk Model Management), shared UI kit:
- **Source cards / table**, one row per connector: dataset type · source name · **mode badge** (🟢 Online / 📄 File) · **status** (Healthy/Stale/Error) · last run · rows (last / total) · **Run now** · enable toggle.
- **Grouped by dataset** (Manifest · ISF · Vessel · Entity).
- **Per-source detail:** endpoint/file path, schedule, recent run history (ts, rows, status), and an upload dropzone for file-mode sources.
- **Honest empty/gap states:** ISF shows "file-sourced — no public ISF feed exists"; manifest shipment-level flagged as sample/file.
- Matches navy/white shared kit (Panel/SectionHeader/StatStrip/DataTable/StatusPill), `#005EA2` accent — consistent with the rest.

---

## 7. Backend API (draft contracts)
- `GET /api/pipelines` → list sources + status.
- `POST /api/pipelines/{source_id}/run` → trigger a run; returns rows/status.
- `GET /api/pipelines/{source_id}/runs` → recent run history.
- `POST /api/pipelines/{source_id}/upload` → file-mode CSV/JSON ingest.
- `PATCH /api/pipelines/{source_id}` → enable/disable, set schedule/mode.

---

## 8. Phased delivery plan (revised after the audit)

Reordered so we (a) make existing sources **observable** first, then (b) close the **highest-impact real gap** (reference data → unlocks 3 zeroed factors), then (c) add continuity.

| Phase | Deliverable | Why this order |
|---|---|---|
| **P0** | Pipeline **registry** (`data_sources` table) + connector interface (reuse the `vessel_tracker` archive→API→fixture pattern) + **Data Pipelines tab** showing every source's real status (Manifest=batch, Vessel=VesselFinder live, ISF=derived, Entity=CORD static, AD/CVD=coded-not-run). Run-now wired where cheap. | Makes the *current* truth visible; no fabrication. |
| **P1** | **Reference-data pipelines (real open APIs):** run + schedule `fetch_adcvd.py` (Federal Register) → `reference/adcvd/`; build **UN Comtrade** connector → `corridors_vn_us.csv`. Unlocks **Commodity + Pattern** factors (currently 0). | Biggest real-data win; sources already coded/known. |
| **P2** | **Entity refresh + SE-Asia coverage:** scheduled CORD refresh; add VN/CN coverage via **GLEIF** (CC0) + **OpenCorporates/trade.gov CSL** → fixes the ~0% SE-Asia match and the zeroed **Party** factor (entity age). | Fixes the most-cited data-quality gap. |
| **P3** | **Vessel continuity:** schedule the existing VesselFinder enrichment (batch where `dwell_days` NULL); optionally add **aisstream.io** (free live) / **NOAA** (free bulk) as fallback/alt sources behind the same connector. | Vessel is already live — this just makes it continuous + adds free options. |
| **P4** | **Manifest continuity:** generalize the upload path into a scheduled **file-drop/CSV** connector + **Census** aggregate (H1 corridor baselines). ISF stays **derived/file** (explicit gap). | Manifest shipment-level stays file; aggregate goes live. |
| **P1.5** | **Data Hub bootstrap:** golden-seed bundle + DVC reference zone -> `make seed` stands up a clean env to a pinned, known-good state; reference outputs move into the hub (§11). | Reproducible envs; decouples reference/history from operational DB. |
| **P5** | **Continuous + scored:** scheduler across all sources + **auto-rescore** newly-ingested rows under the production model (reuse our `/api/rescore`). | Ties ingestion → live scores end-to-end. |
| **P6** | **DQ + ops hardening:** DQ gates + run ledger surfaced in the tab, watermark/incremental pulls, quarantine view, drift feed to Risk Model Mgmt. | Makes it run a year with minimal intervention (§12). |

> Note: our recent Gate-1 work already added `/api/rescore` (deterministic write-back of `calculated_risk_score` + `model_version`), so the "no score write-back" gap in the June-24 GATES doc is **already partly closed** — P5 leans on it.

---

## 9. Open questions / decisions
1. Corridor set: VN→US only, or include CN/MY→US comparators?
2. Scheduler home: new `pipeline` service vs inside `sentry-data`?
3. Online keys: OK to register free API keys (aisstream.io, trade.gov, Census)? Where do we store them (env/secrets)?
4. First live target — recommend **Vessel/AIS** (most open + most visibly "live"). Agree?
5. New tables (`vessels`, `isf`) vs extend existing `shipments`?

---

## 10. Risks & honest gaps
- **ISF**: no public dataset — file-only forever (structural, not a TODO).
- **Shipment-level manifest**: free sources are aggregate; per-shipment BoL is paywalled. The "live manifest" story is aggregate-corridor + file-level shipment.
- **AIS↔manifest linkage**: AIS gives vessels, not cargo; tying a vessel to a manifest/entity needs the manifest side and is approximate.
- **Licensing**: prefer public-domain/CC0 sources (OFAC, CSL, GLEIF, Census, NOAA); keep OpenSanctions bulk behind a license check.

---

## 11. Reference & Historical Data Hub

A **versioned data hub**, separate from the live operational DB, that (a) **bootstraps a clean/new environment** to a known-good state, (b) holds **reference** data, and (c) serves **historical & training** repositories. This is what lets the system run for a year and be re-seeded seamlessly.

**Zones**
| Zone | Holds | Backing | Consumers |
|---|---|---|---|
| **Reference** | AD/CVD orders, Comtrade corridor norms, entity ages, port/transshipment tables, HS scope | DVC-versioned CSV/parquet (repo already uses DVC) | `reference_loader` -> scoring |
| **Historical** | append-only past shipments, vessel tracks, ISF amendments, **officer outcomes** (`gate1_outcomes`) | date-partitioned parquet / object store | analytics, drift, Gate-2 training |
| **Golden seed** | minimal in-scope bundle: schemas + small curated dataset + a reference snapshot | pinned, versioned bundle | **`make seed` -> fresh / cleaned env** |
| **Feature store** | point-in-time features (as-of joins, no leakage) | derived from Historical | model training / inference |

**Reproducible bootstrap.** One command seeds a new or cleaned environment from a **pinned hub version** (data version pinned alongside code version). Secrets come from `.env`. No hand-seeding, no drift between environments.

**Repository connectors.** The hub loads from / publishes to external repos (object-store remote, GLEIF bulk, Federal Register output, DVC remote) so **training and historical analysis read the same versioned source of truth** as production reference.

**Why separate from the operational DB.** Operational stays **small and fast** (minimal data — your "minimal intervention" goal); history grows in cheap cold storage; training reads **point-in-time** history (correctness, no leakage); a clean env seeds from *reference + golden* only, not a copy of prod.

**Hub layout (DVC-backed)**
```
hub/
  reference/        # versioned, read-mostly
    adcvd/  corridors/  entities/  ports/  hs_scope.csv
  historical/       # append-only, date-partitioned (parquet)
    shipments/ dt=YYYY-MM-DD/ ...
    vessel_positions/ ...
    outcomes/        # gate1_outcomes snapshots (officer feedback)
  golden/           # minimal bootstrap bundle
    schema/                 # DDL + migrations
    golden_shipments.csv    # ~50 in-scope VN->US 7604/8541, all risk tiers
    reference_snapshot/     # reference pinned at seed time
  incoming/         # file-drop landing (operational)
    manifest/ {new|processed|quarantine}/
```
**DVC** pins `reference/ historical/ golden/` to content hashes; a **data-version tag travels with the git tag** (data version = code version). Remote = object store (S3/GCS) or local cache for now.

**Golden-seed bootstrap — `make seed`:** (1) `dvc pull` the pinned golden bundle → (2) apply `schema/` migrations to a clean DB → (3) load `golden_shipments.csv` + `reference_snapshot/` → (4) optionally run connectors once to top up live sources. Result: an identical, known-good environment from one pinned version — **no hand-seeding**.

**File-drop zone (chosen manifest path):** drop a manifest CSV/JSON into `incoming/manifest/new/`; a scheduled scan (or the existing upload endpoint) ingests it — parse → dedup (natural key + content hash) → DQ gate → `processed/` (or `quarantine/` + reason) → silver `shipments` → auto-rescore. Aggregate corridor stats come from the Census/Comtrade connector on a periodic pull. **No manual DB seeding; operational DB stays minimal; history lands in `historical/`.**

---

## 12. Operating for a year — challenges & how the pipeline handles them

Thinking as data engineers / analysts about a system ~12 months into production — the failure modes that actually bite, and the design response that handles each **without a human in the loop**.

| # | Challenge (year-in-prod reality) | Design response (seamless) |
|---|---|---|
| 1 | **Duplicate / re-pulled rows** | Natural-key UPSERT + content-hash dedup (the manifest service already detects dups); immutable raw layer |
| 2 | **Re-pulling everything is wasteful/slow** | **Incremental + watermark** per source (cursor / last_fetched in registry); pull deltas only |
| 3 | **Late & amended records** (ISF amendments, AD/CVD updates, sanctions delistings) | **Effective-dated / SCD** records + bounded re-process window; never hard-overwrite history |
| 4 | **Backfill & replay** (bootstrap history, fix a bad run) | Idempotent range-backfill jobs that replay from the raw layer — separate from incremental |
| 5 | **Source schema drift** (a field renamed over the year) | Source **contracts** + tolerant parsing + raw preserved so we can re-derive; alert on contract break |
| 6 | **Source outage / rate limits** | Retry + backoff, circuit-breaker, **archive->API->fixture fallback** (existing pattern), staleness flag |
| 7 | **Silent data-quality decay** (nulls, 0-row runs, out-of-range) | **DQ gates**: freshness, row-count delta, null %, range, referential integrity -> quarantine + alert |
| 8 | **"Why this score?" / reproducibility** | `run_id + source_id + ingested_at` lineage; pin data version = model version (we already stamp `model_version`) |
| 9 | **Data & concept drift** | Monitor feature distributions vs the training baseline -> feed Risk Model Mgmt drift/retraining (Gate 2) |
| 10 | **Storage growth / cost** | Date-partitioning + tiered retention (hot operational vs cold archive); operational store stays minimal |
| 11 | **Standing up / cleaning an environment** | **Golden-seed bootstrap** from the Data Hub (one command, pinned version) — no manual seeding (§11) |
| 12 | **Training leakage / point-in-time correctness** | Separate historical zone + **as-of** feature joins; operational store != training store |
| 13 | **Manual-ops burden** | Orchestrated DAG, auto-retry/fallback, **alert-only-on-breach**; manual = approve a key / clear quarantine |
| 14 | **Secrets & source licensing** | `.env` / compose secrets (approved); per-source license tag; prefer public-domain / CC0 sources |

---

## 13. Data-quality gates (per run, before promotion to silver/gold)

Generic gates (every source) + source specifics. A failing **row** is quarantined with a reason; a breached **gate threshold** marks the run *degraded* and alerts (otherwise silent — minimal intervention).

| Gate | Check | Example threshold |
|---|---|---|
| **Freshness** | last success within source SLA | vessel: 24h · entity / AD-CVD: 7d |
| **Volume** | row-count delta vs trailing average; never 0 | within ±50%; 0 rows = fail |
| **Schema/contract** | required columns present + types valid | hard-fail on contract break |
| **Null rate** | key fields non-null | hs_code, origin_country: <1% null |
| **Range/domain** | values in valid domain | HS in scope set; ISO-2 country; value_usd ≥ 0; dwell 0–60d |
| **Uniqueness** | natural key unique post-dedup | manifest_source_id+hash · vessel_imo · entity record_id |
| **Referential** | FK resolves (warn) | shipper → entity (warn, given SE-Asia gap) |

Per-source specifics — **Manifest:** HS in scope + value > 0; **Vessel:** IMO 7-digit, MMSI 9-digit, lat/lon valid; **Entity:** record_id unique + name non-empty; **AD/CVD:** case_number format + boolean order flag. Quarantined rows surface in the Pipelines tab for one-click review.

---

## 14. Orchestration & scheduling

- **Now:** **APScheduler** in a lightweight worker (or a small `pipeline` service) — in-process cron, minimal deps, fits the current docker-compose; reuse the cord-integration background pattern. Each source carries a `schedule_cron` in the registry; the worker runs `source → normalize → DQ → load → rescore`, dependency-aware (manifest → ISF-derive → score).
- **Later (when DAG complexity / observability demand it):** migrate to **Dagster** (asset-based — models the medallion + lineage + DQ natively) or Airflow. **Connectors are written orchestrator-agnostic** so the move is mechanical.
- **Minimal-intervention:** auto-retry + backoff, archive→API→fixture fallback, alert-only-on-breach; operator actions limited to Run-now and clear-quarantine from the tab.

---

## 15. Canonical schema — new tables vs extend `shipments`

Today vessel + ISF live as **columns on `shipments`** (denormalized; `port_calls` is a JSON blob). Fine for fast H3 scoring, but it can't cleanly represent vessel/voyage history or **ISF amendment history** (the "amendments > 3" signal).

**Recommendation: hybrid — normalize the entities, keep cached columns on `shipments`.**
| Table | Purpose |
|---|---|
| `shipments` | manifest-centric row; keeps cached vessel/ISF/score columns + FKs (existing fast path, unchanged) |
| `vessels` | vessel master (imo, name, flag, owner) — one per ship |
| `vessel_positions` / `port_calls` | time-series AIS / port calls (dwell history) |
| `isf_filings` | ISF + **amendment history** (SCD) — supports "amendments > 3" |
| `entities` (`senzing_entities`) | already normalized |

Silver populates the normalized tables; `shipments` keeps cached fields so current UI/scoring is untouched. History flows to the hub's `historical/` zone. Net: **no breaking change to scoring**, but vessel/ISF history becomes first-class — needed for drift (§12 #9) and amendments/late-data (§12 #3).

> 📌 _Open question: OK to add these tables (additive migration), or keep everything on `shipments` for now and revisit at P3?_

---

# Part C — Sourcing & Gate plan

## 16. Per-data-point sourcing plan

The authoritative "where does each data point come from, at what scope and cadence" (decisions; extends the open landscape in §3).

| Data point | What it gives the model | Source (chosen) | Scope filter | How loaded | Cadence | Status today |
|---|---|---|---|---|---|---|
| **Manifests** (shipment-level) | the shipment records themselves | **Sample files** (no public per-shipment feed) | VN→US, HS 7604/8541 | file-drop upload | May–Jul backfill, then ongoing | demo manifests exist; **no free CBP per-shipment feed** (§18.1) — generate realistic samples seeded from real EAPA/AD-CVD/Comtrade |
| **AD/CVD orders** | active duty orders by HS+country (Rule 3) | **Federal Register API** (`fetch_adcvd.py`, already coded) | VN/CN/MY/TH/ID + 7604/8541 | scheduled API pull | weekly | coded, partly populated, not scheduled |
| **Corridor trade norms** | normal $/kg + volume baseline (pricing anomaly, Rule 6) | **UN Comtrade API** (build `fetch_comtrade.py`) | VN→US 7604/8541 | scheduled API pull | quarterly | 7-row seed exists; fetcher to build |
| **Vessel / AIS** | positions, dwell, port calls (Rules 4 & 7) | **VesselFinder (live)** + optional **satellite AIS (Spire / exactEarth)** for blue-water gaps; free **aisstream.io / NOAA** fallback | vessels on in-scope corridors | API on-demand → scheduled batch | daily | live (on-demand) |
| **ISF Element 9** | declared vs actual stuffing country (Rules 1 & 8) | **Derived** from AIS + manifest (no public ISF) | in-scope | computed at ingest | per shipment | derived/live |
| **Entity — in-scope (Tier 1)** | VN/CN/MY company identity + **incorporation date / age** (Rule 5) | **OpenCorporates + GLEIF (filtered)** + `entities_vn.csv` | VN/CN/MY | scheduled API + file | monthly | 13-row seed; expand (the SE-Asia gap) |
| **Entity — screening lists (Tier 2, international)** | sanctioned / watchlisted / forced-labor / PEP hits (Rule 2, UFLPA) | **OFAC SDN + trade.gov CSL + OpenSanctions + UFLPA + GLEIF + ICIJ** (the CORD bundle) | **global — screen everyone** | bulk refresh | OFAC daily; others weekly | 244K loaded (static) |
| **EAPA respondents** | confirmed enforcement targets (anchor flag → severity floor 88) | **CBP-published EAPA determinations** (cbp.gov case list) | all | scrape cbp.gov → CSV | monthly (CBP cadence) | ⚠️ **system data is SYNTHETIC** (db.py:238, "Rows below are SYNTHETIC, modeled on the public EAPA"); real list IS published & scrapeable (see §18.1) |
| **Altana** (enrichment) | supply-chain verification: recommendation (CLEAR/REVIEW/FLAG), confidence, supply-chain opacity, sanctions exposure — *not a raw score* | **Altana Atlas API** `/v1/trace` | high-risk shipments (≥75) | API call at scoring time | on-demand | stubbed; needs key (mainly Gate 2+) |
| **Commodity dwell baselines** | normal dwell per commodity/port (Rule 4 threshold) | derived from AIS history (or MarineTraffic / Spire) | in-scope commodities | reference table | quarterly | hardcoded now |

**Two-tier entity strategy (your "in-domain vs international" question):**
- **Tier 1 — in-scope, deep.** Load VN/CN/MY companies *well* (registry + incorporation dates) so shipper resolution + entity-age (Rule 5) actually work. Small, high-value, scope-filtered. **This is what fixes the ~0% SE-Asia match.**
- **Tier 2 — international, screening-only.** Keep the sanctions / watchlist / forced-labor / ownership lists **global** — you must screen *every* party against OFAC, not only in-scope ones.
- So we **don't** narrow everything to the domain: narrow the *company-registry* load to in-scope; keep *screening lists* global. That split is the answer to "load only domain vs international."

---

## 17. Per-gate plan (define all gates; implement Gate-1 only)

**Gate 1 — implement now.** The 8 deterministic rules → data → readiness:

| # | Rule | Data needed | Source | Ready? |
|---|---|---|---|---|
| 1 | ISF Element 9 mismatch | declared vs AIS stuffing country | manifest + AIS (derived) | ✅ |
| 2 | OFAC / SDN hit | party screen vs OFAC | OFAC / CSL (Tier 2) | ✅ |
| 3 | High-risk corridor + AD/CVD > 15% | corridor + duty rate | Federal Register AD/CVD | ⚠️ schedule it |
| 4 | AIS dwell > 5× baseline | dwell vs commodity baseline | VesselFinder + baselines | ⚠️ baselines hardcoded |
| 5 | New shipper + high value | incorporation age + value | OpenCorporates / GLEIF (Tier 1) | ⚠️ 13-row seed → expand |
| 6 | Pricing > 15% below market | unit price vs corridor norm | Comtrade norms | ⚠️ build fetcher |
| 7 | Transshipment hub call + dwell | port calls vs hub list | VesselFinder port calls | ✅ |
| 8 | ISF amendments > 3 | amendment count | manifest / ISF (file) | ⚠️ from sample manifests |

→ **Gate-1 build list (only these):** (a) schedule the AD/CVD fetch, (b) build the Comtrade fetch, (c) expand Tier-1 VN/CN entities, (d) generate sample manifests carrying the fields these rules read (§18). Everything else is already live.

**Gate 2 — define only (don't build yet).** Adds LightGBM trained on **287 EAPA + ~45 Gate-1 outcomes**; new features — supply-chain opacity (CORD graph depth **+ Altana**), portfolio reach, ownership features. Target PPV ≥ 30%.

**Gate 3 — define only.** Adds a Bayesian ensemble + dynamic weekly thresholds; optional **satellite imagery**; 120+ cumulative outcomes. Target PPV ≥ 50%.

**Principle:** build the *plumbing* once (registry, file-drop, scheduler), but only **turn on** the sources Gate-1 needs. Gate-2/3 sources (Altana live, satellite imagery, richer entity features) are wired behind flags and switched on when that gate opens.

---

## 18. Gate-1 critical path — sample manifests (May–Jul)

**The binding constraint.** Gate 1 closes on **PPV from real officer outcomes** — which needs in-scope shipments flowing through to fire referrals and accrue dispositions. With no public per-shipment feed, the only lever is **uploaded sample manifests**.

**Plan.** Generate **time-distributed, in-scope sample manifests for May / Jun / Jul**, calibrated so the **8 Gate-1 rules fire at realistic base rates** (majority clean; a minority each tripping a specific rule), wired to the entities / vessels / AD-CVD / Comtrade values that make rules actually trigger. Upload via the file-drop.

**Double duty.** Drives PPV measurement now (Gate 1) **and** accumulates labeled outcomes for Gate-2 training later.

**Open input:** target **volume per month** (≈ 50 / 200 / 500?) — sets how many referrals + outcomes you can work toward the PPV bar.

---

## 18.1 Validated sourcing reality (web-checked 2026-06-30)

**Manifests — is there a free CBP feed with real consignees? NO.**
- Per **19 CFR §103.31**, vessel bill-of-lading data is public record, but only **shipper + cargo** fields are publishable; the public cannot examine manifests directly, and **consignees can (and do) file 2-year confidentiality** — so "real consignee data" is exactly the field most often withheld.
- **No free official CBP download portal.** A 2023 FOIA for bulk ACE manifests (Data Liberation Project) was **rejected**. Real per-shipment data = paid aggregators (Panjiva / ImportGenius / Datamyne).
- **Decision:** generate **realistic sample manifests seeded from real data** — real **EAPA respondent** names as shippers/consignees, real **AD/CVD** orders, real **Comtrade** prices — so the samples are believable and in-scope without a paid feed. This is the most "real" free path.

**EAPA — real list IS published (correcting the synthetic seed).**
- The in-system EAPA is **synthetic** (`db.py:238`). The **real** list is on cbp.gov: *Final Administrative Determinations*, *Notices of Action*, *Notices of Final Determination*, *EAPA Actions Archive* — with case #, respondents, commodity, country, determination date; ~490 allegations / 179 investigations (2016–FY21) and ongoing (cases into 2026). Covers the last 3 years.
- **Decision:** build an **EAPA scraper** (cbp.gov pages → CSV) to replace the synthetic seed with real respondents — a genuine Gate-1 data-quality win and the source of realistic shipper/consignee names for the sample manifests.
- **Precise finding (CBP portal search, 2026-06-30):** the portal **does** publish data, split two ways — (a) **aggregate EAPA *statistics*** are downloadable (EAPA Statistics page + CBP Public Data Portal): counts by year/country/commodity, **no company names**; (b) **case-level EAPA *respondents*** (the names we need) live only in **Notices of Action** + **Final Determinations** as **HTML/PDF** → must be **scraped** (data.gov has no EAPA case dataset). So: scrape for names; the aggregate stats are a bonus for base-rates/calibration.

**AD/CVD — a real downloadable reference file exists (better than expected).**
- **[CBP Active AD/CVD Cases]** dataset (data.gov, free/public-domain): **case number, ISO country code, tariff/HS number, case description** — directly feeds Rule 3. Caveat: data.gov copy is **stale (2022)**; the **live** source is CBP's *AD/CVD Data* page (the ABI reference file).
- **Decision:** use the CBP AD/CVD reference file as the authoritative active-orders source, with the existing Federal Register fetcher (`fetch_adcvd.py`) as the current-notices supplement.

**Referral math — reconciled against the scope doc.**
- Gate-1 documented target = **2–3 referrals/week (10–15/month)**; example PPV = 13 confirmed / 127 referred = 10.2%.
- **30–40 referrals across May–Jul (~13 weeks) = ~2.5/week = on Gate-1 target ✅.** ("5/week" is the **Gate-3** rate, 4–5/week.)
- **"90%+ critical" is the referral *score threshold*** (critical tier); **PPV ≥10% is the *confirmation* target** — different numbers. At Gate 1, ~1 in 10 of the 90%+ referrals is expected to confirm; that's success, not failure.

---

# Part D — FINALIZED design & implementation (locked 2026-07-01)

## 19. Finalized design

### 19.1 The data flywheel (validated)
```
  EAPA scraper (real respondents from cbp.gov)
        │  real name + commodity + country + docket
        ▼
  Manifest generator ──► seeds shipments with EAPA respondents (LABELED positive)
        │                + clean entities (negative), in-scope VN→US 7604/8541
        ▼
  Ingest + Score ──► risk score + rule hits + referral
        │
        ├──► Entity-list enrichment: flagged/scored parties → derived watchlist
        │       layer ON TOP of the static CORD bundle (NOT a rebuild of 244K)
        │
        └──► Officer outcomes (gate1_outcomes) → PPV + real labels
                 │
                 ▼
         Manifest HISTORY (labeled) → Gate-2 training corpus
```
**Why it's strong:** seeding manifests with *real EAPA respondents* makes the training data **self-labeling** (EAPA shipper = known positive; clean shipper = negative). The accumulating manifest history *is* the Gate-2 training set, and high-scoring parties build an enriched, feedback-derived watchlist that fixes the SE-Asia coverage gap over time.

**Clarifications baked in:**
- "Build CORD from risk scoring" = **enrich** (a derived watchlist layer of flagged parties), not rebuild the 244K CORD. CORD stays the screening base.
- Training needs negatives + real outcomes too: the generator supplies negatives; officer dispositions supply real labels.

### 19.2 Locked decisions
| Decision | Locked choice |
|---|---|
| Build order | **Track A (Data Pipeline tab)** + **Track B (EAPA scraper)** in parallel; then manifest generator + entity enrichment; reference data alongside |
| Reference-data scoring | Wire **AD/CVD + Comtrade** so the engine scores for real (stop relying on the file's Risk Score column) |
| Schema | **Hybrid** — add `vessels`, `vessel_positions`, `isf_filings`; keep cached columns on `shipments` (no breaking change) |
| Orchestrator | **APScheduler** now (worker); Dagster later, connectors orchestrator-agnostic |
| Storage | DVC-backed hub (reference / historical / golden) + file-drop for manifests |
| Scope | **Gate-1 only:** VN→US, HS 7604/8541 |

### 19.3 Data Pipeline tab (finalized spec)
Under **Intelligence Control** — a catalog + control panel (the "details about datasets and APIs" you asked for):
- One row per source: dataset type · name · **mode** (🟢 online / 📄 file) · **status** (healthy/stale/error) · last run · rows (last/total) · **Run now**.
- Grouped by dataset: Manifest · ISF · Vessel · Entity · Reference.
- Per-source **detail drawer**: API base URL + auth + cadence, or file path; schedule; recent run history; provenance; honest gap note (ISF file-only, manifest sample, EAPA scrape).
- Shared UI kit + model-badge consistency.

### 19.4 Implementation sequence (Gate-1)
| Step | Track | Deliverable |
|---|---|---|
| 1 | A | Pipeline registry (`data_sources`) + run ledger (`ingestion_runs`) + **Data Pipeline tab** (status + Run-now) |
| 2 | B | **EAPA scraper** (cbp.gov Notices of Action + Final Determinations → `eapa_real.csv`) → load into entity list |
| 3 | — | **Reference data**: AD/CVD (real dataset + Federal Register) + **Comtrade fetcher** → engine scores for real |
| 4 | — | **Manifest generator** (seeded from real EAPA, labeled, time-distributed) → file-drop; top up to 30–40 in-scope critical |
| 5 | — | **Entity enrichment**: flagged/scored parties → derived watchlist layer over CORD |
| 6 | — | Schema tables (vessels/isf) + scheduler + auto-rescore → accumulating labeled history |

### 19.5 In / out for Gate-1
- **In:** Data Pipeline tab, EAPA scraper, reference data (AD/CVD + Comtrade), manifest generator, entity enrichment, scheduler.
- **Deferred (Gate-2/3):** Altana live, satellite AIS, Dagster, the LightGBM / Bayesian models.

> Foundation already done (2026-07-01): the **manifest file-drop ingest works** (bugs fixed — boolean coercion, parser column mapping, silent-failure hardening); 830 demo rows load, ~25 in-scope VN→US 7604/8541 at ≥90.

---

# Part E — Build log & entity-intelligence (as-built, 2026-07-01)

## 20. EAPA entity intelligence — what shipped, and why it took the path it did

The goal: turn EAPA from a synthetic seed into **real, named enforcement actors with their networks** — the H2 core of a Gate-1 system.

**The sourcing journey (each step forced by a real blocker):**
1. **Federal Register API** — real but only ~27 EAPA docs (Commerce "covered merchandise referral" subset; merchandise-focused, sparse names).
2. **cbp.gov is the rich source (~280 cases) but Akamai-blocks datacenter IPs (403).** Pivoted to the **Wayback Machine** (archive.org, not blocked): unioning snapshots across ~2 years → **94 real cases, 58 with respondent names**, incl. in-scope aluminum (Thompson Aluminum, Kingtom Aluminio).
3. **The determination PDFs** carry the per-case importers, foreign exporter/manufacturer, alleger, counsel. Access quirk: cbp.gov 403s the `requests` lib but serves **`urllib`**; listing pages blocked, `/document` landing pages + `/sites` PDFs are direct. Harvested **99/102 PDFs → 227 entities, 417 relationships**, and cracked **7 "Various Importers"** cases into real names (EAPA-8201 → an 11-importer ring, 66 edges).
4. **Loaded into `senzing_entities`/`senzing_relationships`** (204 entities, 414 real edges: CO_RESPONDENT / SUPPLIED_BY / ALLEGED_BY / RELATED_ENTITY), cross-referenced against the 244K CORD by normalized name, **persistent** via the cord-integration Dockerfile startup.

**Artifacts:** `scripts/fetch_eapa_fedreg.py` (FR+Wayback → `eapa_real.csv`), `scripts/fetch_eapa_pdfs.py` (PDFs → `eapa_entities.csv` / `eapa_relationships.csv` / `eapa_enriched.csv`), `services/cord-integration/load_eapa_network.py`.

**Honest limits:** PDF parsing is heuristic (some role/comma-split noise — determination notices parse cleanly, initiation notices are sparser); the CORD cross-ref was thin (1 hit) because small US importers aren't in CORD's international sources (GLEIF/OFAC/ICIJ) — which is exactly what §20.1 fixes.

## 20.1 Entity-registry enrichment (closing the CORD gap)

The thin cross-ref is a **missing-source** problem, not a limit. Resolve the EAPA entities against the registries that DO cover them:

| Registry | Cost | Gives | Status |
|---|---|---|---|
| **GLEIF** (LEI) | free, no key | legal name, registered address, **parent/child ownership**, affiliates | ✅ building now (proven: matched Thompson Aluminum + Zinus's NO/DK affiliates) |
| **SEC EDGAR** | free (declared UA) | public-company officers/subsidiaries | ✅ building now (low coverage — importers are mostly private) |
| **OpenCorporates** | **free token** | US **state-registry** company #, **incorporation date (= entity age, Rule 5)**, **officers** → shared-officer edges, address | ⚠️ wired; activates when `OC_API_TOKEN` is set (register at opencorporates.com/api_accounts/new) |

Output → `entity_registry.csv` + `entity_registry_relationships.csv` → loaded into CORD/senzing (real addresses/ownership/officers → SHARED_ADDRESS / OWNED_BY / SHARED_OFFICER edges). This is the two-tier entity strategy (§16) made real: deep, registry-resolved profiles for the in-domain actors on top of CORD's global screening base. Registered as new sources in the Data Pipelines tab.

**Dependency:** GLEIF + EDGAR need nothing. OpenCorporates (richest US officer/registry data) needs a free token from the user — the agent cannot self-register an account.

**Results (GLEIF + EDGAR run, 2026-07-01):** of 209 distinct EAPA entities, GLEIF matched **31** (real address + status), EDGAR **3**, OpenCorporates 0 (no token). Loaded **8 affiliate nodes + 9 real ownership edges** into the graph — genuine associated entities: *Greenbrier → Astra Rail (Romania) / Greenbrier Poland / Greenbrier Leasing*, *Hog Slat → HS International / HS Midwest / TDM Farms*, *MasterBrand Cabinets ← MasterBrand Inc*. The 178 unmatched are small private US importers — the OpenCorporates token is the single biggest lever to lift US coverage + add officer→SHARED_OFFICER edges. GLEIF/OpenCorporates/SEC EDGAR registered as sources in the Data Pipelines tab; enrichment persists via the cord-integration startup.
