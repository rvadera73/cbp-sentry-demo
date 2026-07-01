# Entity Registry Enrichment

`scripts/enrich_entities_registry.py` resolves the **real EAPA entities** against
**public company registries** to enrich them with addresses, ownership,
affiliates, and officers — closing the CORD coverage gap. The EAPA
determinations give us entity *names* and *roles* but no structured registry
facts; this script adds them.

## Input

`services/api/reference/eapa_entities.csv`
(columns: `eapa_case, entity_name, role, country, source_pdf`)

The script works over the **distinct `entity_name` values** (~209).

## Sources

| # | Source | Key | What we get | Coverage |
|---|--------|-----|-------------|----------|
| 1 | **GLEIF** (Global LEI Foundation) | none (free) | LEI, legal name, legal address (country/city/line), entity status, **direct-parent / direct-children ownership** | PRIMARY. Only entities that hold an LEI (larger / international). Many small importers won't match — expected. |
| 2 | **SEC EDGAR** | descriptive User-Agent (SEC fair-access) | CIK + conformed company name + business address if a **public filer** exists | Most EAPA importers are private → few hits. |
| 3 | **OpenCorporates** | `OC_API_TOKEN` env var | jurisdiction, company number, incorporation date, registered address, **officer names** (→ SHARED_OFFICER edges) | Richest US source (state registries + officers) but token-gated. Skipped gracefully if no token. |

All HTTP uses stdlib **`urllib`** (not `requests`) with a browser User-Agent for
GLEIF/OpenCorporates and a descriptive contact UA for SEC, because some
government endpoints fingerprint and deny non-browser clients.

### Match guarding

GLEIF/EDGAR fuzzy ranking can return unrelated companies (e.g.
`"Gogo International, Inc"` → `"INC Group Inc."`). We accept a fuzzy top hit only
when the normalized token sets are equal or one is a subset of the other
(`Accuride` ⊆ `Accuride Corp`), which filters spurious matches while keeping
suffix-only differences. Corporate suffixes (Inc, LLC, Ltd, Corp, Group, …) and
punctuation are stripped before comparison.

## Outputs (written to `services/api/reference/`)

**`entity_registry.csv`**
`entity_name, source, matched_name, identifier, country, address, incorporation_date, status`
- `identifier` = LEI (GLEIF), CIK (EDGAR), or company_number (OpenCorporates)
- one row per (entity, source) match

**`entity_registry_relationships.csv`**
`src_name, rel_type, dst_name, dst_identifier, source`
- `rel_type` ∈ `OWNED_BY` (GLEIF direct-parent), `PARENT_OF` (GLEIF
  direct-children), `SHARED_OFFICER` (OpenCorporates officer), `AFFILIATE`

## Usage

```bash
# full run over all distinct names (GLEIF is the bulk; takes several minutes)
python3 scripts/enrich_entities_registry.py

# first N names only
python3 scripts/enrich_entities_registry.py --limit 20

# do everything but write nothing
python3 scripts/enrich_entities_registry.py --dry-run

# activate OpenCorporates (US state registries + officers)
OC_API_TOKEN=xxxxx python3 scripts/enrich_entities_registry.py
```

Get a free OpenCorporates token at <https://opencorporates.com/api_accounts/new>.

## Behavior

- **Polite**: ~0.3s delay between requests, retries with exponential backoff on
  429/5xx/timeouts, skips individual failures instead of aborting.
- **Idempotent**: re-running overwrites the two output CSVs from scratch.
- **No existing code is modified** — this is additive enrichment only.

## Coverage limits (be honest)

GLEIF only covers entities that hold an LEI, so small/private US importers
(the bulk of EAPA respondents) will not match. EDGAR only covers SEC public
filers. Without an `OC_API_TOKEN` there is **no** US state-registry / officer
coverage — that token is what unlocks the richest source. Treat the registry as
a partial, best-effort enrichment, not a complete resolution of every entity.
