# EAPA determination-PDF entity & relationship harvester

`scripts/fetch_eapa_pdfs.py`

Downloads the individual CBP **Enforce and Protect Act (EAPA)** notice PDFs and
extracts the **real parties** named inside them — importers/respondents, foreign
suppliers/manufacturers, the alleger, and alleger counsel — plus the **within-case
relationships** between them. This is Gate-1-critical real data.

It is a deeper companion to `scripts/fetch_eapa.py` (which produces a case-level
roll-up from the listing pages). This script goes *into the PDFs*.

## Why it works (and why not `requests`)

- The cbp.gov EAPA **listing** pages are Akamai-blocked (403). The individual
  `/document/publications/eapa-...` **landing** pages and the
  `/sites/default/files/*.pdf` PDFs are directly fetchable (200) with a browser
  User-Agent.
- The case → landing-page mapping is recovered from the **Wayback** snapshot of the
  listing pages (archive.org is not blocked). We resolve the closest snapshot via the
  availability API (with a CDX-API fallback, since availability is occasionally
  flaky), then fetch the raw `id_` capture and scrape the anchors.
- **Important:** cbp.gov's Akamai layer fingerprints the Python `requests` library's
  TLS/header signature and returns **403** for it, while stdlib **`urllib`** is served
  **200** with the same headers. The script therefore fetches everything via `urllib`
  (verified empirically). `requests` is not required.

## Pipeline

1. For each listing page
   (`.../trade/eapa/notices-action` and
   `.../tftea/eapa/eapa-actions-archive`), resolve the closest Wayback snapshot and
   scrape the case anchors. Two anchor formats are handled:
   - notices-action: `EAPA [Cons.] Case ####: <Respondent> (<notice type>, <date>)`
     → direct `/document/...` link.
   - actions-archive: `EAPA Action: <notice type> in EAPA Case #### - <commodity>`
     → an intermediate action page that links to the `/document/...` page (the text
     after the dash is the *commodity*, not the respondent, so it is not trusted as an
     importer).
   When a case appears with several notices, the **Notice of Determination as to
   Evasion** is preferred over Final Determination over Initiation (determinations name
   the exporters + scheme).
2. For each selected case, fetch the landing page directly from cbp.gov, find the
   `.pdf` link (following one hop through the intermediate action page when needed, and
   only to a document whose slug contains the case number), download it (cached under
   `data/eapa_pdfs/<case>.pdf`), and parse the first ~8 pages with `pdfplumber`.
   Obviously-wrong PDFs (e.g. an unrelated annual review) are rejected.
3. Extract per case (best-effort heuristics):
   - **importers / respondents** — for consolidated "Various Importers" cases the
     determination text lists the actual importer names ("...importers X (X), Y (Y),
     ... (collectively, "the Importers")"); those are pulled out.
   - **alleger** — "<Company> ("X" or "the Alleger")", "the Alleger, <Co>",
     "<Coalition of …> (the Alleger)", or "On behalf of <Co>".
   - **alleger counsel** — the law firm in the page-1 "Counsel to: <alleger>" block.
   - **foreign exporter / manufacturer / producer** — strict company-name matches near
     role words (exporter/manufacturer/producer/supplied by/…).
   - **country_of_origin** and any **transshipment country**.
   - **adcvd_case** (`A-###-###` / `C-###-###`) and **commodity**.

## Outputs (written to `services/api/reference/`)

- `eapa_entities.csv` — `eapa_case, entity_name, role, country, source_pdf`
  (role ∈ importer | foreign_supplier | manufacturer | alleger | counsel), one row per
  entity per case.
- `eapa_relationships.csv` — `eapa_case, src_entity, rel_type, dst_entity`, within-case
  edges:
  - importer ↔ importer = `CO_RESPONDENT`
  - importer → foreign_supplier/manufacturer = `SUPPLIED_BY`
  - respondent → alleger = `ALLEGED_BY`
  - paired names in one respondent field ("Dymatec USA, LLC and Dymatec, Ltd.") =
    `RELATED_ENTITY`
- `eapa_enriched.csv` — one roll-up row per case: `eapa_case, importers,
  foreign_suppliers, alleger, country, commodity, adcvd_case, determination_date,
  notice_type, source_pdf`.

## Usage

```bash
python3 scripts/fetch_eapa_pdfs.py --limit 8        # quick validation on 8 cases
python3 scripts/fetch_eapa_pdfs.py                  # full run (all cases)
python3 scripts/fetch_eapa_pdfs.py --out-dir /tmp   # write CSVs elsewhere
```

Idempotent. PDFs are cached under `data/eapa_pdfs/` (keyed by case number) so re-runs
do not re-download. Delete that directory to force a fresh fetch. Polite ~1.2 s delay
between cbp.gov fetches with retry/backoff on 403/429/5xx.

Requires `pdfplumber`. `requests` is optional and unused for fetching.

## Honest caveats on extraction quality

This is messy free-text PDF parsing.

- **Determination** notices parse best: real importer lists, allegers, counsel,
  country, adcvd, commodity. **Initiation / Interim-Measures** notices name fewer
  parties, so those rows are sparser.
- Foreign-supplier / manufacturer extraction is the noisiest field and is deliberately
  conservative (strict company-suffix + no sentence-fragment names), so it *misses*
  some real suppliers rather than emitting garbage.
- Role labels are heuristic: a name tagged `alleger` is occasionally an exporter, and
  vice-versa, when the surrounding phrasing is ambiguous.
- A handful of older cases resolve to no reachable / no case-specific PDF and are
  reported as failures (they still get an anchor-only roll-up row where the respondent
  is trustworthy).
- Blanks are expected and OK — the goal is to capture what is reliably parseable.
