# EAPA Scraper (`fetch_eapa.py`)

Pulls **real** CBP Enforce-and-Protect-Act (EAPA) determinations into a CSV,
intended to replace the **synthetic** EAPA seed baked into
`services/data/db.py` (`_seed_reference_data`, the block marked
`Rows below are SYNTHETIC`).

## What it does

Fetches the public CBP EAPA pages, parses per-case fields with BeautifulSoup,
de-dupes by EAPA case number, and writes a normalized CSV to
`services/api/reference/eapa_real.csv`.

Source pages:

| Notice type                          | URL |
|--------------------------------------|-----|
| Notice of Action                     | https://www.cbp.gov/trade/eapa/notices-action |
| Final Administrative Determination   | https://www.cbp.gov/trade/trade-enforcement/tftea/eapa/requests-administrative-review/final-administrative-determinations |
| Notice of Final Determination        | https://www.cbp.gov/trade/trade-enforcement/tftea/enforce-and-protect-act-eapa/notices-final-determination |
| EAPA Actions Archive                 | https://www.cbp.gov/trade/trade-enforcement/tftea/eapa/eapa-actions-archive |

## Requirements

`requests`, `beautifulsoup4`, `lxml` (all already present in this repo's env).
Optional: `pdfplumber` **or** `pypdf` — if installed, the script best-effort
pulls respondent/commodity/country from the first page of linked PDFs. If
neither is present, PDF entries are still captured as (case, title, link).

```bash
python3 -c "import requests, bs4, lxml"   # check
pip install --quiet requests beautifulsoup4 lxml   # if missing
```

## Usage

```bash
# Live fetch -> services/api/reference/eapa_real.csv
python3 scripts/fetch_eapa.py

# Print what would be written, write nothing
python3 scripts/fetch_eapa.py --dry-run

# Parse manually-saved .html pages instead of fetching (fallback)
python3 scripts/fetch_eapa.py --from-local data/eapa_raw

# Custom output path
python3 scripts/fetch_eapa.py --out /tmp/eapa.csv

# Skip PDF text enrichment even if pdfplumber/pypdf is installed
python3 scripts/fetch_eapa.py --no-pdf
```

Behavior:
- Sends a realistic Chrome `User-Agent` (cbp.gov 403s the default python UA),
  with polite delays, retries, and exponential backoff.
- **HTTP 403 / blocked pages are logged and skipped** — the run continues.
- If **all** live pages are blocked and `data/eapa_raw/` exists, it
  automatically falls back to parsing saved `.html` files there.
- Idempotent: re-running produces a byte-identical CSV.

## ⚠️ cbp.gov blocks server-side scraping

As of this writing, `www.cbp.gov` returns **HTTP 403** to automated requests
(Akamai bot protection) even with a real browser `User-Agent`, from
datacenter / WSL / CI IP ranges. A browser on a normal residential connection
loads the pages fine.

**To get real data, save the pages manually and use `--from-local`:**

1. Open each source URL (table above) in a normal browser.
2. `File -> Save Page As -> "Web Page, HTML Only"` into `data/eapa_raw/`.
   Name the files with a hint so the notice type is inferred, e.g.
   `notices_action.html`, `final_admin_determinations.html`,
   `notices_final_determination.html`, `eapa_archive.html`.
3. Run: `python3 scripts/fetch_eapa.py --from-local data/eapa_raw`

`data/eapa_raw/notices_action_sample.html` is a small **fixture** that
demonstrates the parser end-to-end; replace/augment it with real saved pages.

## Output CSV — field mapping

`services/api/reference/eapa_real.csv`

| Column               | Source in HTML                                                        |
|----------------------|----------------------------------------------------------------------|
| `eapa_case`          | Case number regex (`EAPA[ Case[ Number]] NNNN`), normalized to `EAPA-NNNN` |
| `respondents`        | Importer/respondent column, or parsed from the notice-link title; multiple joined with `;` |
| `commodity`          | Commodity/merchandise column, or a "covered merchandise" phrase in PDF text |
| `country_of_origin`  | Origin column, or "country of origin / transshipped through X" phrase |
| `determination_date` | Date column or first date found near the entry                        |
| `notice_type`        | Notice column value, else the source page's category                  |
| `source_url`         | Absolute URL of the linked notice/PDF (falls back to the page URL)    |

De-duped by `eapa_case`; blank fields from one occurrence are filled from
another for the same case.

## Loading the CSV into the entity list later

The scraped respondents are candidate **importers/respondents** that CBP has
adjudicated for AD/CVD evasion — high-value positives for entity resolution
and risk calibration. Sketch to load them alongside the existing reference
entities (`services/api/reference/entities_vn.csv`):

```python
import csv

with open("services/api/reference/eapa_real.csv", encoding="utf-8") as fh:
    for row in csv.DictReader(fh):
        for name in filter(None, (n.strip() for n in row["respondents"].split(";"))):
            upsert_entity(
                company_name=name,
                country=row["country_of_origin"] or None,
                source="EAPA",
                eapa_case=row["eapa_case"],
                commodity=row["commodity"] or None,
                notice_type=row["notice_type"],
                determination_date=row["determination_date"] or None,
                source_url=row["source_url"],
                label="eapa_respondent",   # genuine AD/CVD-evasion positive
            )
```

To **replace the synthetic seed** in `services/data/db.py`, have
`_seed_reference_data` read `eapa_real.csv` (when present) instead of the
hard-coded `eapa_cases` list, mapping `respondents -> respondent`,
`country_of_origin -> origin_country`, `commodity -> commodity`, and deriving
`year` from `determination_date`.
