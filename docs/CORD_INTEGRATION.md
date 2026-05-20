# Senzing CORD Integration for CBP International Trade Investigations

## Overview

This system uses **Senzing CORD (Collections Of Relatable Data)** to provide real-world entity resolution for international trade investigations. Three CORD collections are recommended for comprehensive coverage:

| CORD Collection | Coverage | Records | Primary Use Case |
|---------|----------|---------|----------|
| **London CORD** | Europe, Asia, Middle East | 10M+ | International supply chains (CN→VN→US, MY→US routes) |
| **Moscow CORD** | Russia, Central Asia, CIS | 6M+ | Russian & post-Soviet supply chains (RU→KZ→US) |
| **Las Vegas CORD** | US Importers, Distributors | 5M+ | Domestic US supply chain mapping, consignee verification |

### London CORD Datasets
| Dataset | Coverage | Use Case |
|---------|----------|----------|
| **GLEIF** | Global Legal Entity Identifiers | Match shipper/manufacturer by international ID |
| **ICIJ Offshore** | Beneficial ownership chains | Trace hidden ownership (CN→HK→VN) |
| **OpenSanctions** | International sanctions lists | OFAC + EU + UN + country-specific |
| **GlobalData** | International corporate records | Company details, directors, financials |
| **UK Companies House** | UK entity registration | UK consignees, holding companies |

## Why Multiple CORDs for CBP?

### Use Case 1: China-Vietnam-US (Aluminum)

**Route:** Guangdong (CN) → Hong Kong (holding) → Vietnam (trader) → Newark (US)

**London CORD matches:**
- ✓ Guangdong Greenfield (GLEIF LEI: 5493001KJTIIGC8Y1Q12)
- ✓ Greenfield HK Holdings (ICIJ offshore record + director link: Li Chen)
- ✓ Greenfield Vietnam Trading (OpenSanctions flag)
- ✓ SunPath Energy Newark (GlobalData US import profile)

**Resolution:** Senzing detects all as single connected network, flags transshipment

### Use Case 2: Russia-Kazakhstan-US (Steel)

**Route:** Magnitogorsk (RU) → Almaty (KZ) → Singapore (SG) → Long Beach (US)

**Moscow CORD matches:**
- ✓ Magnitogorsk Steel Works (Russian Federal Tax Service EGRUL registry)
- ✓ KazTrade Import-Export (Kazakhstan registry - Central Asian CORD)
- ✓ Singapore trading company (cross-reference with London CORD)
- ✓ OFAC alert: Russian sanctions → flags for examination

**Resolution:** Moscow CORD identifies Russian manufacturer, Kazakhstan intermediary, OFAC trigger

### CORD Selection Guide

| Route | Primary CORD | Secondary | Tertiary | Coverage |
|-------|--------------|-----------|----------|----------|
| China → Vietnam → US | London | Las Vegas | — | GLEIF, ICIJ, CN/VN registries, US importer verify |
| Russia → Kazakhstan → US | Moscow | London | Las Vegas | Russian tax service, Central Asian, OFAC-RU, US consignee |
| India → Malaysia → US | London | Moscow | Las Vegas | GLEIF, Indian corporate registry, US importer verify |
| Middle East → EU → US | London | — | Las Vegas | GLEIF, EU registries, OFAC-ME, US consignee |
| Multiple routes (full coverage) | London + Moscow + Las Vegas | — | — | Domestic + international network mapping |

**Recommendation:** Load **all three CORDs** for complete supply chain visibility:
- **London:** International shippers, manufacturers, middlemen
- **Moscow:** Russian/CIS manufacturers and intermediaries  
- **Las Vegas:** US importers, distributors, consignees (verify end-buyer legitimacy)

## Downloading CORD Collections

CBP-Sentry supports **multiple CORD regions** for comprehensive international coverage:

### London CORD (Primary)
**Best for:** European, Asian, and Middle Eastern trade routes

1. Visit: https://senzing.com/senzing-ready-data-collections-cord/
2. Select: **London Collection**
3. Download: CSV or Senzing JSON format
4. Save to: `/home/rahulvadera/cbp-sentry/cord_data/london-cord-latest.jsonl`

**Includes:** GLEIF, ICIJ, OpenSanctions, GlobalData, UK Companies House, OFAC

### Moscow CORD (Secondary)
**Best for:** Russian, Central Asian, and CIS trade routes

1. Visit: https://senzing.com/senzing-ready-data-collections-cord/
2. Select: **Moscow Collection**
3. Download: Senzing JSON format (recommended)
4. Save to: `/home/rahulvadera/cbp-sentry/cord_data/moscow-cord-latest.jsonl`

**Includes:** Russian Federal Tax Service, Russian Registry (EGRUL), ICIJ offshore (Russian/CIS), OFAC Russia sanctions, Central Asian registries (Kazakhstan, Uzbekistan)

### Las Vegas CORD (Tertiary - US Importers)
**Best for:** US-based importers, distributors, and consignees

1. Visit: https://senzing.com/senzing-ready-data-collections-cord/
2. Select: **Las Vegas Collection**
3. Download: Senzing JSON format (recommended)
4. Save to: `/home/rahulvadera/cbp-sentry/cord_data/lasvegas-cord-latest.jsonl`

**Includes:** 
- US Importer Records (Trade Data)
- D&B Dun & Bradstreet US Directory
- SEC EDGAR US Companies
- US Port Authority Records
- Customs Broker Registrations
- US Warehouse/Distribution Centers

**Use Cases:**
- Verify consignee legitimacy (is the US buyer real?)
- Detect shell importers (high-risk consignees)
- Map domestic supply chain (consignee → distributor → end-use)
- Cross-reference with international suppliers (known Greenfield shipper → unknown US consignee?)

### File Structure

**CSV Format:**
```
name,country_code,address,registration_number,gleif_lei,directors,beneficial_owners,status
"Guangdong Greenfield Aluminum Co. Ltd.","CN","No. 1258 Lingnan Road, Foshan, Guangdong 528200","914406817654321098","5493001KJTIIGC8Y1Q12","Li Chen; Wang Wei","Li Family Trust (60%); Guangdong Investment Group (40%)","ACTIVE"
...
```

**Senzing JSON Format (recommended):**
```jsonl
{"DATA_SOURCE": "CORD_LONDON_GLEIF", "RECORD_ID": "cn_greenfield_001", "NAME_FULL": "Guangdong Greenfield Aluminum Co., Ltd.", "GLEIF_LEI": "5493001KJTIIGC8Y1Q12", ...}
{"DATA_SOURCE": "CORD_LONDON_ICIJ", "RECORD_ID": "hk_greenfield_001", "NAME_FULL": "Greenfield Global Holdings Ltd.", "BENEFICIAL_OWNERS": ["Li Chen"], ...}
...
```

## Loading CORD into Senzing

### Option 1: Automatic on Startup (Recommended)

The system automatically loads CORD when Senzing starts:

```bash
# Inside docker-compose.yml, senzing-init service runs:
python api/scripts/init_cord_data.py
```

This:
1. Waits for Senzing to be healthy
2. Loads curated CORD entities from `seed_data/cord_cbp_entities.jsonl`
3. Verifies key entities (Greenfield, Solaria, SunPath) are loaded
4. Prints confirmation

**To add full London + Moscow CORD:**
1. Download from https://senzing.com/senzing-ready-data-collections-cord/
2. Place in `cord_data/`:
   ```
   cord_data/
   ├── london-cord-latest.jsonl      (2GB, ~10M records)
   ├── moscow-cord-latest.jsonl       (1.2GB, ~6M records)
   └── sample-cord-test.jsonl         (test entities)
   ```
3. Update `scripts/init_cord_data.py` to load all three sources

### Option 2: Manual Load - London CORD

```bash
python api/scripts/cord_loader.py \
  --cord-json cord_data/london-cord-latest.jsonl \
  --data-source CORD_LONDON \
  --senzing-url http://localhost:8250
```

Output:
```
Loading CORD JSON: cord_data/london-cord-latest.jsonl
Processed 100 records...
Processed 200 records...
...
✓ CORD load complete: {"loaded": 10000000, "errors": 42}
```

### Option 3: Manual Load - Moscow CORD

```bash
python api/scripts/cord_loader.py \
  --cord-json cord_data/moscow-cord-latest.jsonl \
  --data-source CORD_MOSCOW \
  --senzing-url http://localhost:8250
```

### Option 4: Load Both (Complete Coverage)

```bash
# Load London (Asian + EU routes)
python api/scripts/cord_loader.py \
  --cord-json cord_data/london-cord-latest.jsonl \
  --data-source CORD_LONDON

# Load Moscow (Russian + CIS routes)
python api/scripts/cord_loader.py \
  --cord-json cord_data/moscow-cord-latest.jsonl \
  --data-source CORD_MOSCOW

# Verify loaded
curl http://localhost:8250/records | grep -c CORD_LONDON
curl http://localhost:8250/records | grep -c CORD_MOSCOW
```

## Using CORD Data in Entity Resolution

### Flow

```
Manifest upload (Greenfield) 
  ↓
Extract shipper: "Greenfield Industrial Trading Co., Ltd." (VN)
  ↓
Query Senzing against CORD data
  ↓
Senzing finds:
  • Greenfield Global Holdings (HK) — director match: Li Chen
  • Guangdong Greenfield (CN) — GLEIF match + beneficial owner: Li Chen
  • OpenSanctions flag: Related entity flagged
  ↓
API returns:
  {
    "resolutions": [
      {
        "shipper_name": "Greenfield Industrial Trading Co., Ltd.",
        "matched_entity": "Greenfield Global Holdings Ltd.",
        "confidence": 0.98,
        "match_reason": "Director: Li Chen + GLEIF cross-reference",
        "cord_source": "CORD_LONDON_ICIJ",
        "entity_graph_link": "hk_greenfield_001 → cn_greenfield_001"
      }
    ]
  }
```

### API Endpoint

```
POST /api/er/load
{
  "manifest_id": "MFN-2025-0001"
}

Returns:
{
  "entities_loaded": 5,
  "resolutions": [...],
  "relationships": ["director_shared", "gleif_match", "beneficial_owner"],
  "summary": {
    "cord_data_used": true,
    "data_sources": ["CORD_LONDON_GLEIF", "CORD_LONDON_ICIJ", "CORD_LONDON_OPENSANCTIONS"]
  }
}
```

## Mapped CORD Data Sources

| Source | Field | CBP Use |
|--------|-------|---------|
| **CORD_LONDON_GLEIF** | GLEIF_LEI, REGISTRATION_NUMBER | Match manufacturers globally |
| **CORD_LONDON_ICIJ** | BENEFICIAL_OWNERS, DIRECTORS, RELATED_ENTITIES | Trace ownership chains |
| **CORD_LONDON_OPENSANCTIONS** | SANCTIONS_LIST, OFAC_STATUS, PEP_STATUS | Flag sanctioned entities |
| **CORD_LONDON_GLOBALDATA** | INDUSTRY_CODE, FINANCIAL_STATUS, EMPLOYEE_COUNT | Company intelligence |
| **CORD_LONDON_UK_CH** | COMPANY_HOUSE_NUMBER | UK holding companies |

## Example: Greenfield Case Resolution

**Input:** Manifest with shipper "Greenfield Industrial Trading Co., Ltd." (VN)

**Senzing Query via CORD:**
```
Search name="Greenfield" + country=VN → found in CORD_LONDON_ICIJ
  ↓
Found director: Li Chen → search across all CORD sources
  ↓
Found in GLEIF: Guangdong Greenfield (CN) with director Li Chen
Found in ICIJ: Greenfield HK Holdings with beneficial owner Li Chen
Found in OPENSANCTIONS: No direct hit, but see: "Chen Enterprises Trading Group" (adjacent to Li Chen)
```

**Output:**
```json
{
  "entity_chain": [
    {
      "name": "Greenfield Industrial Trading Co., Ltd.",
      "country": "VN",
      "cord_source": "CORD_LONDON_ICIJ",
      "confidence": 0.92,
      "role": "shipper"
    },
    {
      "name": "Greenfield Global Holdings Ltd.",
      "country": "HK",
      "cord_source": "CORD_LONDON_GLEIF",
      "confidence": 0.98,
      "link_type": "director_shared",
      "link_evidence": "Director Li Chen (100% match)"
    },
    {
      "name": "Guangdong Greenfield Aluminum Mfg. Co., Ltd.",
      "country": "CN",
      "cord_source": "CORD_LONDON_GLEIF",
      "gleif_lei": "5493001KJTIIGC8Y1Q12",
      "confidence": 0.99,
      "link_type": "beneficial_owner",
      "link_evidence": "Beneficial Owner: Li Family Trust (registered to Li Chen)"
    }
  ],
  "why_connected": "Li Chen appears as director in VN entity, beneficial owner in HK holding, and beneficial owner in CN manufacturer. High confidence that VN shipper is fronting for CN manufacturer via HK intermediary."
}
```

## Testing CORD Integration

### Quick Test

```bash
# Verify CORD data loaded
curl http://localhost:8001/api/er/load \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"manifest_id": "MFN-2025-0001"}'

# Expected response shows real CORD matches, not mocks
```

### Full Test Case

```bash
# Test 1: Greenfield case (should find 3-tier ownership chain)
curl -X POST http://localhost:3001/api/er/load \
  -d '{"manifest_id": "greenfield-test"}' | grep -i "li chen"

# Test 2: Why connected (should show CORD evidence)
curl http://localhost:3001/api/er/why/vn_greenfield_001/cn_greenfield_001 \
  | grep -i "gleif\|beneficial\|director"

# Test 3: Graph visualization (should show real relationships)
curl http://localhost:3001/api/graph/cn_greenfield_001
```

## Next Steps

### 1. Download London CORD
- Visit: https://senzing.com/senzing-ready-data-collections-cord/
- Register for free evaluation
- Download "London Collection" in Senzing JSON format

### 2. Load into System
```bash
cd /home/rahulvadera/cbp-sentry
python api/scripts/cord_loader.py \
  --cord-json cord_data/london-cord.jsonl \
  --data-source CORD_LONDON
```

### 3. Verify Integration
- Navigate to Case Viewer
- Open Greenfield case (/cases/1)
- Click "Entity Chain" tab
- Verify real CORD data appears (not mock)
- Check "Why Connected" shows GLEIF + ICIJ evidence

### 4. (Optional) Add Moscow CORD
For Russian/CIS trade routes, download Moscow CORD for:
- Russian corporate registry
- CIS sanctions data
- Offshore beneficial ownership (Central Asia)

## Architecture

```
User uploads manifest
  ↓
CBP-Sentry ingest service
  ↓
Extract entities (shipper, manufacturer, consignee)
  ↓
Load into Senzing instance
  ↓
Senzing queries against loaded CORD data
  ↓
Returns: Entity matches + relationships + confidence
  ↓
UI displays: Entity chain diagram + Why explanation
```

## Troubleshooting

### "Senzing service unavailable"
- Ensure Senzing container is running: `docker-compose ps`
- Check Senzing logs: `docker-compose logs senzing`
- Verify CORD loader waited for health check

### "No entities found"
- Check CORD file path: `ls -la seed_data/cord_cbp_entities.jsonl`
- Check Senzing loaded data: `curl http://localhost:8250/records`
- Verify data source: records should have `DATA_SOURCE: CORD_LONDON*`

### "Confidence score too low"
- CORD data may be limited. Download full London CORD from https://senzing.com
- Add more reference data sources
- Adjust Senzing confidence thresholds

## References

- [Senzing CORD Overview](https://senzing.com/senzing-ready-data-collections-cord/)
- [Download CORD Collections](https://senzing.com/senzing-ready-data-collections-cord/)
- [Senzing REST API Documentation](https://docs.senzing.com/)
- [GLEIF Entity Data](https://www.gleif.org/)
- [ICIJ Offshore Leaks Database](https://offshoreleaks.icij.org/)
