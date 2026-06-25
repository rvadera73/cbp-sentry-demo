# Entity Resolution - Complete Research & Architecture Findings
## Data Sources, APIs, Database Design

**Status:** Research Complete - Ready for Full Implementation Planning  
**Date:** May 27, 2026  
**Prepared By:** Architecture Team

---

## SECTION 1: EXISTING SYSTEM VALIDATION ✅

### 1.1 SENZING SDK - RESEARCH FINDINGS

**Status:** ✅ Installed and working  
**Location:** `services/api/senzing_client.py`

**Current Senzing Implementation:**
```python
# Available Methods in SenzingClient:
1. resolve_entities(shipper_name, consignee_name)
   └─ Returns: entities[], graph_edges[], confidence scores
   └ Works in: FIXTURE MODE (offline) and LIVE MODE (if service available)

2. get_why_connected(entity_id_a, entity_id_b)
   └─ Returns: evidence[], relationship type, confidence
   └─ Evidence types: DIRECTOR_SHARED, FREIGHT_FORWARDER_SHARED, REGISTERED_AGENT_SHARED, OWNERSHIP_STAKE, BOARD_OVERLAP, FACILITY_LOCATION
   └─ Example: "Director Li Wei appears in both corporate registries" (0.94 confidence)

3. _build_edges_from_entities(entities)
   └─ Extracts relationship edges from entity data
   └─ Returns: source_id, target_id, relationship, confidence

4. _avg_confidence(entities)
   └─ Calculates average confidence across entities

# Current Operation Mode:
API_MODE = os.getenv("API_MODE", "fixture")  # Defaults to "fixture" (offline demo)
SENZING_URL = os.getenv("SENZING_URL", "http://senzing:8250")

# In Fixture Mode:
- Returns hardcoded data for test cases (Greenfield, Solaria, SunPath)
- Greenfield case: Full 3-level chain with why-connected evidence
- SunPath case: With prior EAPA filings (2023-EAPA-001, 2023-AD-CV-002)
- Includes prior_filings: case_id, determination

# In Live Mode:
- Connects to Senzing REST API at http://senzing:8250
- Calls: /heartbeat, /entity-search, /entity-chain
- Falls back to FIXTURE if service unavailable
```

**🚀 KEY INSIGHT:** Senzing already returns `prior_filings` data! Data structure exists:
```json
"prior_filings": [
  {"case_id": "2023-EAPA-001", "determination": "evasion"},
  {"case_id": "2023-AD-CV-002", "determination": "duty"}
]
```

**✅ READY TO USE:**
- resolve_entities() - Get entity chains with confidence
- get_why_connected() - Get evidence linking entities
- prior_filings already in fixture data (need to confirm in live API)
- related_entities with relationship types
- risk_flags (NEW_SHIPPER, TRANSSHIPMENT_CORRIDOR)

**⚠️ TODO:**
- Confirm live Senzing API returns prior_filings field
- If not, we need to create our own enforcement history DB and join with Senzing data

---

### 1.2 CORD ENGINE - VALIDATION ✅

**Status:** ✅ Fully implemented and working  
**Location:** `services/api/cord_engine.py`

**What CORD Provides:**
```
• 244K entities indexed in SQLite FTS5
• Search: Full-text search on name, country, entity type
• Data fields indexed:
  - record_id: Unique identifier
  - data_source: GLEIF | OFAC | [other]
  - record_type: Entity type classification
  - name_primary: Official registered name
  - names_aka: Alternative/known names (space-separated)
  - country: Registration country (ISO 2-letter code)
  - ofac_program: If OFAC SDN listed (SDNL, IEEUL, NPWMD, etc.)
  - sanctions_topic: Sanctions classification (Iran, DPRK, etc.)
  - raw_json: Full entity record

• Special OFAC table: Faster SDN lookups
  - record_id, name_primary, names_aka, sdn_program, entity_type, raw_json
```

**Current CORD Database Tables:**
```
cord_fts (FTS5 virtual table - full-text search)
ofac_sdn (OFAC-specific lookups)
```

**Available Queries:**
```sql
1. Full-text search by name:
   SELECT * FROM cord_fts WHERE cord_fts MATCH 'greenfield'
   
2. Search by country:
   SELECT * FROM cord_fts WHERE country = 'CN'
   
3. OFAC SDN quick lookup:
   SELECT * FROM ofac_sdn WHERE name_primary LIKE '%greenfield%'
   
4. Get raw entity record:
   SELECT raw_json FROM cord_fts WHERE record_id = 'xyz'
```

**✅ READY TO USE:**
- Entity search (FTS5 - fast, fuzzy matching)
- OFAC SDN status (dedicated table for quick checks)
- Alternative names (names_aka field)
- Entity details (raw_json contains full record)

**⚠️ MISSING:**
- No pre-computed entity chains in CORD
- No relationship edges between entities
- No why-connected evidence (that's Senzing's role)
- Will need to query Senzing for chain resolution

---

### 1.3 MANIFEST DATA - VALIDATION ✅

**Status:** ✅ Available and structured  
**Location:** `data/cbp_sentry.db` → `shipments` and `manifests` tables

**Manifest/Shipment Schema:**
```
shipments TABLE:
  • id (TEXT) - Shipment ID
  • manifest_id (TEXT) - Linked to manifest
  • shipper_name (TEXT) ✅ Entity Resolution entry point
  • consignee_name (TEXT) ✅ Entity Resolution entry point
  • origin_country (TEXT) ✅ Country code for entity search
  • destination_country (TEXT)
  • hs_code (TEXT) - Commodity classification
  • declared_value_usd (REAL)
  • declared_weight_kg (REAL)
  • description (TEXT) - Commodity description
  • vessel_name (TEXT)
  • status (TEXT)
  • risk_score (REAL) ✅ Already calculated
  • ofac_screened_at (TIMESTAMP)
  • ofac_match (BOOLEAN) ✅ Already screened
  • shipper_country (TEXT)
  • consignee_country (TEXT)
  • element9_is_mismatch (INTEGER) - Element 9 (Country of Origin) check
  • element9_confidence (REAL)
  • ad_cvd_applicable (INTEGER) - Anti-dumping/CVD rate applicable
  • ad_cvd_rate (REAL) - Tariff rate
  • ais_stuffing_country (TEXT)
  • port_calls (TEXT) - Transshipment indicators
  • dwell_days (REAL) - Port dwell time
  • [20+ other fields for risk scoring]

manifests TABLE:
  • id (TEXT)
  • filename (TEXT)
  • row_count (INTEGER)
  • extracted_at (TIMESTAMP)
```

**💡 KEY INSIGHT:**
- Shipment data already has shipper_name, consignee_name, countries
- Ready to pass directly to entity resolution
- No additional data transformation needed
- Can link back to shipment_id for case files

**Example Query for Entity Resolution:**
```sql
SELECT 
  id as shipment_id,
  shipper_name,
  shipper_country,
  consignee_name,
  consignee_country,
  hs_code,
  declared_value_usd,
  risk_score,
  ofac_match
FROM shipments
WHERE risk_score >= 50
LIMIT 100
```

---

### 1.4 ISF DATA - VALIDATION

**Status:** ⚠️ **NEED CONFIRMATION FROM YOU**

**What we found:**
- `manifest_upload_jobs` table exists (tracks upload processing)
- No explicit "isf" table visible in current schema
- ISF data likely embedded in manifests or shipments tables

**Question for you:**
- Is ISF (Import Security Filing) data stored separately?
- Or is it merged into the manifests/shipments tables?
- What specific ISF fields do you want to use for entity resolution?

**Typical ISF Fields (if available):**
- ISF filer information (importer of record)
- Seller, consignee, ship-to party details
- More granular consignee/importer information than manifest

---

## SECTION 2: CBP ENFORCEMENT HISTORY RESEARCH 📚

### 2.1 CBP Public Data Sources

**SOURCE 1: CBP EAPA (Enforce and Protect Act) Cases**
```
URL: https://www.cbp.gov/trade/commencement-investigations/eapa
Status: ✅ PUBLIC - Free access

Data Available:
  • Case ID (e.g., 2023-EAPA-001)
  • Complainant (who filed)
  • Respondent (importer being investigated)
  • Product description
  • Investigation status (Preliminary/Final/Closed)
  • Determination (Evasion/No evasion)
  • Date filed
  • Announcement date

Format: HTML table + PDF case reports
No official API, but structured web data

Data Download:
  - Can scrape HTML table OR
  - Download CSV export (if available) OR
  - Parse PDF case reports
```

**SOURCE 2: US ITA (International Trade Administration) - AD/CVD Cases**
```
URL: https://enforcement.trade.gov/
Status: ✅ PUBLIC - Free access

Data Available:
  • Case ID
  • Product (commodity affected by tariff)
  • Country (origin)
  • Case status
  • Duty rate imposed
  • Company names (respondents)
  • Investigation dates

Format: Searchable web interface + API
Some data available via API

Data Download:
  - Web search (limited)
  - PDF reports
  - No public bulk API, but structured web data
```

**SOURCE 3: BIS Entity List (Commerce Department)**
```
URL: https://www.bis.doc.gov/index.php/policy-guidance/lists-of-parties-of-concern/entity-list
Status: ✅ PUBLIC - Free download

Data Available:
  • Entity name
  • Country
  • Why listed (EAR controls, FCPA, etc.)
  • Denial orders

Format: CSV/JSON download
Machine-readable

Data Download:
  - Direct CSV/JSON download from BIS website
  - Updated regularly (weekly)
```

**SOURCE 4: OFAC Enforcement Actions Database**
```
URL: https://home.treasury.gov/policy-issues/office-of-foreign-assets-control/enforcement
Status: ✅ PUBLIC - Free access

Data Available:
  • Civil penalties
  • Criminal penalties
  • Entity names
  • Settlement amounts (USD)
  • Violation details

Format: CSV/spreadsheet
Database with download link

Data Download:
  - CSV download from Treasury website
  - Machine-readable
```

**SOURCE 5: CBP Intellectual Property Rights (IPR) Border Seizures**
```
URL: https://www.cbp.gov/trade/intellectual-property-rights/trade-violation-enforcement
Status: ✅ PUBLIC

Data Available:
  • IP violation cases
  • Company names involved
  • Commodity (counterfeit goods)
  • Seizure details

Format: Case reports (PDF, HTML)
No structured database
```

---

### 2.2 PROPOSED CBP ENFORCEMENT HISTORY STORAGE SOLUTION

**Architecture:**
```
1. CREATE: sentry_db CBP enforcement tables
2. POPULATE: Web scraping + API ingestion (weekly job)
3. JOIN: Link with entity data via name/country matching
4. CACHE: In local database for fast queries
5. EXPOSE: Via API to Entity Resolution service
```

**Database Schema:**

```sql
-- Table 1: EAPA Cases (Enforce and Protect Act)
CREATE TABLE cbp_eapa_cases (
  case_id TEXT PRIMARY KEY,
  complainant TEXT,
  respondent TEXT,  -- Importer being investigated
  respondent_country TEXT,
  product_description TEXT,
  investigation_status TEXT,  -- Preliminary/Final/Closed
  determination TEXT,  -- Evasion/No evasion/Withdrawn
  penalty_amount_usd REAL,
  date_filed DATE,
  date_announced DATE,
  date_closed DATE,
  case_url TEXT,
  data_source TEXT DEFAULT 'CBP_EAPA',
  last_updated TIMESTAMP,
  raw_data JSON  -- Full case details for reference
);

-- Table 2: AD/CVD (Anti-dumping/Countervailing Duty) Cases
CREATE TABLE cbp_ad_cvd_cases (
  case_id TEXT PRIMARY KEY,
  ita_case_id TEXT,
  product_description TEXT,
  origin_country TEXT,
  respondent_companies TEXT,  -- JSON array of company names
  investigation_status TEXT,
  determination TEXT,  -- Affirmative/Negative
  duty_rate_percent REAL,
  date_filed DATE,
  date_final DATE,
  case_url TEXT,
  data_source TEXT DEFAULT 'ITA',
  last_updated TIMESTAMP,
  raw_data JSON
);

-- Table 3: OFAC Enforcement Actions
CREATE TABLE ofac_enforcement_actions (
  enforcement_id TEXT PRIMARY KEY,
  entity_name TEXT,
  entity_country TEXT,
  penalty_amount_usd REAL,
  violation_type TEXT,
  date_settled DATE,
  case_url TEXT,
  data_source TEXT DEFAULT 'OFAC',
  last_updated TIMESTAMP,
  raw_data JSON
);

-- Table 4: BIS Denied Parties
CREATE TABLE bis_denied_parties (
  entity_id TEXT PRIMARY KEY,
  entity_name TEXT,
  entity_country TEXT,
  listed_reason TEXT,
  list_type TEXT,  -- Entity List / Denied Persons / Unverified List
  date_listed DATE,
  data_source TEXT DEFAULT 'BIS',
  last_updated TIMESTAMP,
  raw_data JSON
);

-- Table 5: Entity Enforcement History (INDEXED VIEW)
-- Links enforcement records to entities in CORD
CREATE TABLE entity_enforcement_history (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  cord_entity_id TEXT,  -- Link to CORD entity (via fuzzy match)
  entity_name TEXT,
  entity_country TEXT,
  case_type TEXT,  -- EAPA / AD-CVD / OFAC / BIS
  case_id TEXT,
  determination TEXT,
  penalty_amount_usd REAL,
  case_date DATE,
  confidence REAL,  -- Confidence of name match (0-1)
  source_table TEXT,
  data_source TEXT,
  created_at TIMESTAMP,
  FOREIGN KEY (source_table, case_id) REFERENCES cbp_eapa_cases(data_source, case_id)
);

-- Table 6: Enforcement History Sync Log
CREATE TABLE enforcement_history_sync_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  data_source TEXT,  -- EAPA / ITA / OFAC / BIS
  last_sync_time TIMESTAMP,
  record_count INTEGER,
  new_records INTEGER,
  updated_records INTEGER,
  error_message TEXT,
  status TEXT  -- SUCCESS / FAILED / IN_PROGRESS
);
```

**Data Population Strategy:**

```
WEEKLY SCHEDULED JOB:
  1. EAPA Cases:
     - Scrape https://www.cbp.gov/trade/commencement-investigations/eapa
     - Parse HTML table
     - Extract: case_id, respondent, determination, date_filed
     - Insert into cbp_eapa_cases
     
  2. AD/CVD Cases:
     - Scrape https://enforcement.trade.gov/
     - Extract: case_id, origin_country, product, duty_rate
     - Insert into cbp_ad_cvd_cases
     
  3. OFAC Enforcement:
     - Download: https://home.treasury.gov/policy-issues/office-of-foreign-assets-control/enforcement
     - Parse CSV
     - Insert into ofac_enforcement_actions
     
  4. BIS Entity List:
     - Download: https://www.bis.doc.gov/...entity-list
     - Parse CSV
     - Insert into bis_denied_parties

  5. Fuzzy Match to CORD Entities:
     - For each enforcement record:
       - Search CORD for matching entity name + country
       - Store match with confidence score (name_similarity)
       - Insert into entity_enforcement_history

  6. Log sync operation
```

**Query Example (for Entity Resolution):**
```sql
-- Get enforcement history for an entity
SELECT 
  case_type,
  case_id,
  determination,
  penalty_amount_usd,
  case_date,
  confidence,
  data_source
FROM entity_enforcement_history
WHERE cord_entity_id = 'greenfield-vn'
ORDER BY case_date DESC;
```

---

## SECTION 3: OPEN CORPORATES INTEGRATION RESEARCH 🌍

### 3.1 Open Corporates API - Analysis

**What is Open Corporates?**
```
• Global corporate registry database
• ~150M companies worldwide
• Aggregates data from: US Secretary of State, UK Companies House, 
  China's SAMR, Hong Kong, Singapore, etc.
• Public and commercial APIs available
```

**Data Available:**
```
Per Entity:
  • Company name (registered + alternative names)
  • Registration number (in jurisdiction)
  • Jurisdiction (state/country)
  • Company type
  • Incorporation date
  • Status (active/dissolved/etc)
  • Address
  • Officers (directors, shareholders)
  • Company filings
  • Relationships (parent company, subsidiaries)
  • Industry classification

Officers/Directors:
  • Name
  • Position (Director, Shareholder, etc)
  • Date of birth (if public)
  • Other companies they're associated with
```

**API Tiers:**

```
TIER 1: FREE API
  • Endpoint: https://api.opencorporates.com/companies/search
  • Rate limit: 10 requests per second
  • Authentication: No API key needed
  • Response: Basic company data (name, address, type)
  
  Example Query:
    GET /companies/search?name=greenfield&jurisdiction_code=cn
    
  Response:
    {
      "companies": [{
        "name": "Greenfield Industrial Trading Co., Ltd.",
        "jurisdiction_code": "cn",
        "company_number": "123456789",
        "incorporation_date": "2025-09-15",
        "status": "Active",
        "company_url": "https://opencorporates.com/companies/cn/123456789",
        "officers": [...]
      }]
    }

TIER 2: COMMERCIAL API (Paid)
  • Full officer data with relationships
  • Cross-jurisdiction search
  • Hierarchical relationship mapping
  • Historical data (company changes over time)
  • Better rate limits (1000 requests/hour)

TIER 3: BULK DOWNLOAD
  • CSV/JSON dumps of all companies in jurisdiction
  • Updated daily/weekly
  • One-time setup, then local search
```

**Key Endpoints:**

```
1. Company Search
   GET /companies/search?name=<name>&jurisdiction_code=<code>
   Returns: List of matching companies with basic details

2. Company Detail
   GET /companies/<jurisdiction>/<company_number>
   Returns: Full company record with officers, relationships

3. Officer Lookup
   GET /officers/search?name=<name>
   Returns: All companies where person is an officer

4. Corporate Structure
   GET /companies/<jurisdiction>/<company_number>/corporate_structure
   Returns: Parent/subsidiary relationships
   (Requires commercial API)
```

**Integration Approach:**

```
OPTION A: FREE API + CACHING
  • Use free API for queries
  • Cache results in sentry_db
  • Build hierarchical structure locally
  • Update cache weekly
  • No cost, but limited features
  
OPTION B: BULK DOWNLOAD + LOCAL SEARCH
  • Download company CSVs for target jurisdictions (CN, VN, HK, MY, etc)
  • Import into sentry_db
  • Build local FTS5 index like CORD does
  • Most cost-effective, fastest queries
  • One-time setup per jurisdiction

OPTION C: COMMERCIAL API
  • Real-time corporate structure queries
  • Full officer/director/shareholder relationships
  • Cross-jurisdiction linking
  • Significant cost ($500-2000/month)
  • Best for live data
```

**Recommended:** OPTION B for Entity Resolution use case
- Import Open Corporates data for CN, VN, HK, MY, SG (main trade partners)
- Use free API for on-demand lookups if needed
- No subscription cost
- Fast local queries (5-50ms)

**Database Schema for Open Corporates:**

```sql
CREATE TABLE open_corporates_companies (
  id TEXT PRIMARY KEY,  -- jurisdiction:company_number
  company_name TEXT,
  jurisdiction_code TEXT,
  company_number TEXT,
  company_type TEXT,
  incorporation_date DATE,
  status TEXT,
  address TEXT,
  api_url TEXT,
  data_source TEXT DEFAULT 'OPENCORPORATES',
  last_updated TIMESTAMP,
  raw_json TEXT  -- Full API response
);

CREATE TABLE open_corporates_officers (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  company_id TEXT,
  officer_name TEXT,
  officer_position TEXT,
  date_of_birth DATE,
  date_of_appointment DATE,
  date_of_cessation DATE,
  data_source TEXT DEFAULT 'OPENCORPORATES',
  FOREIGN KEY (company_id) REFERENCES open_corporates_companies(id)
);

CREATE TABLE open_corporates_relationships (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source_company_id TEXT,
  target_company_id TEXT,
  relationship_type TEXT,  -- PARENT / SUBSIDIARY / OWNER_OF / OWNED_BY
  relationship_name TEXT,
  data_source TEXT DEFAULT 'OPENCORPORATES',
  FOREIGN KEY (source_company_id) REFERENCES open_corporates_companies(id),
  FOREIGN KEY (target_company_id) REFERENCES open_corporates_companies(id)
);

-- Indexes for fast lookups
CREATE INDEX idx_oc_company_name ON open_corporates_companies(company_name);
CREATE INDEX idx_oc_jurisdiction ON open_corporates_companies(jurisdiction_code);
CREATE INDEX idx_oc_officers_company ON open_corporates_officers(company_id);
```

---

## SECTION 4: UN COMTRADE API RESEARCH 📊

### 4.1 What is UN Comtrade?

```
• UN database of international merchandise trade statistics
• ~170 countries reporting
• ~6,000 commodities (HS codes)
• Updated monthly
• Free public API
• 30+ years of historical data
```

**Data Available:**

```
Per Trade Flow:
  • Exporter country
  • Importer country
  • HS code (6-digit commodity classification)
  • Trade value (USD)
  • Trade quantity (if applicable)
  • Year/Month
  • Trade flow direction (Export/Import/Re-export/Re-import)

Aggregated Statistics:
  • Top exporters of a commodity
  • Top importers of a commodity
  • Trade trends (5-10 year history)
  • Country pair trade volume
  • Commodity trends
```

**API Details:**

```
Endpoint: https://comtrade.un.org/api/get
Public: ✅ FREE
Authentication: No API key, but registering gives higher rate limits

Parameters:
  • r (reporter): Country code, example: "CN,VN,HK"
  • p (partner): Trading partner country code, example: "US"
  • ps (period): Year or month, example: "202501" for Jan 2025
  • px (classification): HS (Harmonized System) or others
  • head (header): C (commodities) or S (services)
  • cc (commodity code): 6-digit HS code, example: "850810"
  • type: C (commodities) or S (services)
  • fmt: JSON or CSV

Example Query:
  GET https://comtrade.un.org/api/get?
    r=CN&
    p=US&
    ps=202501&
    px=HS&
    cc=850810&
    type=C&
    fmt=json

Response:
  {
    "dataset": [
      {
        "ref_area": "CN",
        "partner_area": "US",
        "trade_flow": "Export",
        "commodity": "850810",
        "trade_value_usd": 1234567,
        "quantity": 100,
        "year": 2025,
        "month": 1
      }
    ]
  }

Rate Limits:
  • Anonymous: 100 requests/hour
  • Registered: 10,000 requests/day (free tier)
  • Paid: Unlimited
```

**Comtrade Use Case in Entity Resolution:**

```
SCENARIO: Officer investigates shipper from China exporting to US

Use Comtrade to:
  1. Check if commodity from shipper's country to destination is:
     - Normal/legitimate trade flow, OR
     - Unusual pattern (red flag for transshipment)
     
  2. Find: Does China-to-US trade in this commodity exist?
     Example: 
       • Aluminum ingots (HS 760612) shipped CN→US
       • Is this normal? Check Comtrade: YES, $500M/year trade
       • Shipper is legitimate exporter (low risk)
       
  3. Detect transshipment:
       • Shipper claims "aluminum ingots" (HS 850810 - electrical equipment)
       • But normal trade is: CN exports → VN finishes → US imports
       • Comtrade shows: VN-to-US trade volume is high
       • Suggests: Transshipment through Vietnam (rerouting to evade tariff)
       
  4. Identify high-risk routes:
       • Pull top 10 origin countries for commodity to US
       • Flag unusual routes: If trade normally CN→US, but manifest shows CN→HK→US
```

**Integration Approach:**

```
OPTION A: QUERY ON-DEMAND (No local DB)
  • When investigating entity + commodity
  • Query Comtrade API for top 10 trade flows
  • Check if shipper's country pair + commodity is normal
  • Cache results (24 hours) to avoid hitting rate limit
  • Storage: Redis or local file cache
  
OPTION B: BULK LOAD + LOCAL SEARCH (Best for Entity Resolution)
  • Monthly bulk download from Comtrade for last 5 years
  • Key country pairs: CN-US, VN-US, HK-US, MY-US, etc
  • Top 500 commodities (HS codes)
  • ~2-5GB of data per 5 years
  • Import into SQLite with indexes
  • Query locally in milliseconds
  
OPTION C: HYBRID (Recommended)
  • Load current year data locally (updated monthly)
  • Query historical data from API (cached)
  • Provides real-time + historical context
```

**Database Schema for Comtrade:**

```sql
CREATE TABLE un_comtrade_trade_flows (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  year INTEGER,
  month INTEGER,
  reporter_country TEXT,  -- Exporter
  partner_country TEXT,   -- Importer
  trade_flow TEXT,  -- Export/Import/Re-export/Re-import
  hs_code TEXT,  -- 6-digit commodity code
  hs_description TEXT,
  trade_value_usd REAL,
  quantity REAL,
  quantity_unit TEXT,
  data_source TEXT DEFAULT 'UN_COMTRADE',
  last_updated TIMESTAMP,
  UNIQUE(year, month, reporter_country, partner_country, hs_code, trade_flow)
);

-- Indexes for entity resolution queries
CREATE INDEX idx_comtrade_country_pair ON un_comtrade_trade_flows(reporter_country, partner_country);
CREATE INDEX idx_comtrade_hs_code ON un_comtrade_trade_flows(hs_code);
CREATE INDEX idx_comtrade_year_month ON un_comtrade_trade_flows(year, month);

-- Summary table: Top traders per commodity route
CREATE TABLE un_comtrade_top_traders (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  year INTEGER,
  reporter_country TEXT,
  partner_country TEXT,
  hs_code TEXT,
  rank INTEGER,  -- 1st, 2nd, 3rd largest exporter
  exporter_name TEXT,  -- Company name (if available)
  trade_value_usd REAL,
  market_share_percent REAL,
  data_source TEXT DEFAULT 'UN_COMTRADE'
);

-- Query Example for Entity Resolution:
SELECT 
  reporter_country, 
  trade_value_usd,
  SUM(trade_value_usd) as annual_volume
FROM un_comtrade_trade_flows
WHERE reporter_country = 'CN'
  AND partner_country = 'US'
  AND hs_code = '850810'
  AND year = 2025
GROUP BY reporter_country;
```

---

## SECTION 5: DATA INTEGRATION ARCHITECTURE 🏗️

### 5.1 Complete Data Flow for Entity Resolution

```
┌─────────────────────────────────────────────────────────────────────┐
│ ENTITY RESOLUTION SERVICE - COMPLETE DATA ARCHITECTURE             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│ INPUT: Shipment (shipper_name, consignee_name, country, hs_code)  │
│        From: sentry_db.shipments table                             │
│                                                                     │
│ WORKFLOW:                                                           │
│                                                                     │
│ 1. ENTITY IDENTIFICATION                                           │
│    └─→ CORD Search (FTS5):                                         │
│        INPUT: shipper_name, shipper_country                        │
│        OUTPUT: Top 10 matching entities with confidence scores     │
│        TIME: ~50ms (FTS5 is fast)                                  │
│                                                                     │
│ 2. ENTITY CONFIDENCE & RESOLUTION                                  │
│    └─→ Senzing SDK:                                                │
│        INPUT: Entity candidates from CORD                          │
│        OUTPUT: Matched entity with confidence (0-1)                │
│        TIME: 200-500ms (depends on network)                        │
│        FALLBACK: Use CORD match if Senzing unavailable             │
│                                                                     │
│ 3. ENTITY CHAIN RESOLUTION (4 LEVELS)                              │
│    └─→ Senzing SDK resolve_entities():                             │
│        INPUT: Matched entity ID                                    │
│        OUTPUT: related_entities[] with relationships               │
│        LEVELS: Shipper → Parent → Beneficial Owner → [Ultimate]    │
│        TIME: 500-1000ms                                            │
│                                                                     │
│ 4. WHY-CONNECTED EVIDENCE                                          │
│    └─→ Senzing SDK get_why_connected():                            │
│        FOR each pair in chain:                                     │
│          INPUT: entity_a, entity_b                                 │
│          OUTPUT: evidence[], relationship, confidence              │
│        EVIDENCE: DIRECTOR_SHARED, OWNERSHIP_STAKE, etc             │
│        TIME: 100ms × (chain_length-1)                              │
│                                                                     │
│ 5. OFAC/SDN SCREENING                                              │
│    └─→ CORD ofac_sdn table (direct lookup):                        │
│        INPUT: Entity names                                         │
│        OUTPUT: SDN program, sanctions topic, confidence            │
│        TIME: ~10ms (indexed table lookup)                          │
│                                                                     │
│ 6. ENFORCEMENT HISTORY LOOKUP                                      │
│    └─→ sentry_db.entity_enforcement_history table:                │
│        FOR each entity in chain:                                   │
│          INPUT: Entity name, country                               │
│          OUTPUT: EAPA/AD-CVD/OFAC/BIS cases, settlements           │
│        TIME: 50-100ms per entity                                   │
│                                                                     │
│ 7. OPEN CORPORATES OFFICERS & STRUCTURE                            │
│    └─→ sentry_db.open_corporates_* tables (local):                 │
│        INPUT: Entity name, country                                 │
│        OUTPUT: Officers/Directors, subsidiaries, parent company    │
│        TIME: 50-100ms (local FTS5 search)                          │
│        FALLBACK: Query free API if not in local DB                 │
│                                                                     │
│ 8. COMTRADE TRADE FLOW ANALYSIS                                    │
│    └─→ sentry_db.un_comtrade_trade_flows table:                    │
│        INPUT: Country pair + HS code                               │
│        OUTPUT: Annual trade volume, top exporters, trends          │
│        ANALYSIS: Is this trade route normal? Transshipment red flag│
│        TIME: 50-100ms (local indexed query)                        │
│                                                                     │
│ 9. RISK AGGREGATION                                                │
│    └─→ Business Logic:                                             │
│        Evaluate:                                                   │
│        • Any entity on OFAC SDN → CRITICAL                         │
│        • Prior enforcement + current shipping → HIGH               │
│        • New shipper + transshipment route → MEDIUM                │
│        • Normal trade + no enforcement → LOW                       │
│        TIME: 10ms                                                  │
│                                                                     │
│ OUTPUT: Complete entity intelligence object                        │
│         └─ entity_details                                          │
│         └─ entity_chain (4 levels)                                 │
│         └─ why_connected (evidence)                                │
│         └─ enforcement_history                                     │
│         └─ corporate_structure                                     │
│         └─ trade_flow_analysis                                     │
│         └─ risk_assessment (aggregated)                            │
│                                                                     │
│ TOTAL TIME: ~1-2 seconds (from shipment → full intelligence)       │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## SECTION 6: IMPLEMENTATION CHECKLIST ✅

### 6.1 What We Have (Ready to Use)

```
✅ Senzing SDK installed + working
   • resolve_entities() - Get entity chains
   • get_why_connected() - Get evidence
   • prior_filings in fixture data
   
✅ CORD database (244K entities)
   • Full-text search (FTS5)
   • OFAC SDN lookups
   • Alternative names
   
✅ Manifest data in sentry_db
   • shipper_name, consignee_name
   • Countries, HS codes, values
   • Ready to pass to entity resolution
   
✅ Senzing fixtures (offline mode)
   • Test data: Greenfield, Solaria, SunPath
   • Complete chain with evidence
   • Prior filings included
```

### 6.2 What We Need to Build

```
🔨 Backend Services:
   ❌ entity_resolution_service.py (NEW)
      └─ Orchestrate CORD + Senzing calls
      └─ Build complete entity intelligence
      └─ Risk aggregation logic
      
   ❌ entity_resolution_router.py (NEW)
      └─ API endpoints for frontend
      └─ /entity/search
      └─ /entity/resolve-shipment
      └─ /entity/{id}/intelligence
      
   ❌ enforcement_history_loader.py (NEW)
      └─ Web scraper for EAPA/AD-CVD/OFAC/BIS
      └─ Weekly sync job
      └─ Name matching with CORD entities
      
   ❌ open_corporates_loader.py (NEW)
      └─ Download Open Corporates bulk data
      └─ Import to sentry_db
      └─ Build FTS5 index
      
   ❌ comtrade_loader.py (NEW)
      └─ Download UN Comtrade data
      └─ Import historical data
      └─ Monthly updates

🔨 Database:
   ❌ New tables in sentry_db:
      └─ cbp_eapa_cases
      └─ cbp_ad_cvd_cases
      └─ ofac_enforcement_actions
      └─ bis_denied_parties
      └─ entity_enforcement_history
      └─ open_corporates_companies
      └─ open_corporates_officers
      └─ un_comtrade_trade_flows
      
   ❌ Indexes on above tables (for performance)

🔨 Frontend Components:
   ❌ Entity Resolution Tab redesign
      └─ EntitySearch (search dialog)
      └─ EntityCardEnhanced (entity details)
      └─ SupplyChainVisualization (chain with evidence)
      └─ RelationshipGraph (interactive network)
      └─ EnforcementHistoryPanel
      └─ CorporateStructurePanel
      └─ TradeFlowAnalysisPanel
      
🔨 APIs/Integrations:
   ❌ Confirm: Is live Senzing API returning prior_filings?
   ❌ Integrate: Open Corporates (free API + bulk data)
   ❌ Integrate: UN Comtrade (free API + bulk data)
   ❌ Integrate: CBP EAPA cases (web scraper)
   ❌ Integrate: ITA AD-CVD cases (web scraper)
   ❌ Integrate: OFAC enforcement (CSV download)
   ❌ Integrate: BIS Entity List (CSV download)
```

---

## SECTION 7: QUESTIONS FOR YOU

Before we proceed with implementation, please clarify:

### Question 1: ISF Data
- Is ISF data stored separately from manifests/shipments?
- What specific ISF fields should we expose in Entity Resolution?
- Example: ISF filer info, importer of record, etc.?

### Question 2: Senzing Live API
- Is live Senzing service available (not just fixture mode)?
- Does live Senzing API return `prior_filings` field?
- If not, should we build our own enforcement history database?

### Question 3: Data Import Priorities
- Which should we prioritize:
  - A) CBP enforcement history (EAPA/AD-CVD/OFAC) - Essential
  - B) Open Corporates integration - Nice to have
  - C) UN Comtrade integration - Nice to have
  - D) All of them (if timeline allows)

### Question 4: Public Data Access
- Do you want to use:
  - A) Free APIs only (no subscriptions)
  - B) Free + Open source bulk data (downloaded locally)
  - C) Paid commercial APIs if ROI justifies
  
### Question 5: Architecture Timeline
- Should we build:
  - MVP Phase (4 weeks): CORD + Senzing + enforcement history
  - Enhancement Phase (2-3 weeks): Open Corporates + Comtrade
  - Or everything at once?

---

## APPENDIX: API RESPONSE EXAMPLES

### A. Senzing resolve_entities() Response
```json
{
  "entities": [
    {
      "entity_id": "ENT-GF-VN-001",
      "name": "Greenfield Industrial Trading Co., Ltd.",
      "country": "VN",
      "incorporation_date": "2025-09-15",
      "entity_type": "shipper",
      "confidence": 0.98,
      "risk_flags": ["TRANSSHIPMENT_CORRIDOR"],
      "related_entities": [
        {
          "entity_id": "ENT-GF-HK-001",
          "name": "Greenfield Global Metals Holdings Ltd.",
          "country": "HK",
          "relationship": "OWNED_BY",
          "confidence": 0.95
        }
      ],
      "prior_filings": [
        {
          "case_id": "2023-EAPA-001",
          "determination": "evasion",
          "status": "settled"
        }
      ]
    }
  ],
  "total_confidence": 0.96,
  "source": "senzing"
}
```

### B. Senzing get_why_connected() Response
```json
{
  "entity_a": "Greenfield Industrial Trading Co., Ltd.",
  "entity_b": "Greenfield Global Metals Holdings Ltd.",
  "relationship": "OWNED_BY",
  "confidence": 0.91,
  "evidence": [
    {
      "type": "DIRECTOR_SHARED",
      "details": "Director Li Wei appears in both corporate registries",
      "confidence": 0.94,
      "source": "SAMR + Hong Kong BR"
    },
    {
      "type": "REGISTERED_AGENT_SHARED",
      "details": "Both list China Trade Services as registered agent",
      "confidence": 0.91,
      "source": "Company registration records"
    },
    {
      "type": "OWNERSHIP_STAKE",
      "details": "HK owns 88% per SAMR registry",
      "confidence": 0.96,
      "source": "SAMR registry"
    }
  ]
}
```

### C. CORD Entity Response (raw_json field)
```json
{
  "record_id": "GF-VN-001",
  "data_source": "GLEIF",
  "record_type": "LE",
  "name_primary": "Greenfield Industrial Trading Co., Ltd.",
  "names_aka": ["GF Trading", "Greenfield Industrial Co."],
  "country": "VN",
  "ofac_program": null,
  "sanctions_topic": null,
  "tax_id": "0123456789",
  "incorporation_date": "2025-09-15",
  "address": "123 Trade Street, Ho Chi Minh City, Vietnam",
  "lei": "5493001XYZ1234567890"
}
```

---

**END OF RESEARCH DOCUMENT**

**Next Step:** Await your answers to Section 7 questions, then we'll finalize detailed implementation plan with timeline and resource allocation.
