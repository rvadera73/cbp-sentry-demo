# Entity Resolution Page Redesign
## Product Owner Design Document & CBP Officer UX Workflow

**Version:** 1.0  
**Date:** May 27, 2026  
**Status:** Design Phase - Ready for Discussion  
**Audience:** CBP Officers, Customs Investigators, Enforcement Teams

---

## EXECUTIVE SUMMARY

### Problem Statement
CBP Officers investigating potential illegal transshipment schemes need to quickly understand complex entity networks and identify hidden relationships between shippers, consignees, and manufacturers across multiple countries. Current Entity Resolution page provides basic entity information but lacks:

1. **Relationship Evidence** — Why are entities connected? (shared directors, agents, locations)
2. **Beneficial Ownership** — Who ultimately controls the entity network?
3. **Risk Aggregation** — What is the overall risk across the entire supply chain?
4. **Enforcement History** — Has this entity or related parties violated trade laws before?
5. **Visual Navigation** — Hard to understand complex 4+ level supply chains in text format

### Solution Overview
Redesign Entity Resolution page as a **Comprehensive Senzing-powered Entity Intelligence Dashboard** that enables:

- **Interactive relationship graphs** showing entity networks with visual evidence
- **Drill-down analysis** from shipper → parent → ultimate beneficial owner
- **Evidence-based linking** explaining why entities are related (director overlap, shared agents, etc.)
- **Risk assessment** aggregated across entire entity chain
- **Enforcement history** showing prior CBP violations
- **Corporate structure visualization** showing ownership percentages, voting rights, etc.

---

## CBP OFFICER USE CASES

### Use Case 1: Investigating Suspicious Shipper (ENTRY POINT)

**Scenario:** Officer receives manifest with unknown shipper from Vietnam. Needs to determine if legitimate or part of transshipment scheme.

**Current Workflow:**
1. Search for "Greenfield Industrial Trading Co., Ltd."
2. See basic info: Vietnam, Tax ID, Risk Level
3. Must manually research parent companies, beneficial owners
4. Limited information on why entities are related

**Desired Workflow:**
1. Search for shipper name
2. See **full 4-level supply chain** with visual representation
3. Instantly see **why each entity is connected** (e.g., "Director Li Wei appears in both corporate registries")
4. Check **prior CBP enforcement** — has this or related entities violated before?
5. View **beneficial owner** at top of chain
6. See **aggregated risk score** for entire network
7. Drill down into any entity to explore **alternate relationships**

### Use Case 2: Detecting Related Party Networks

**Scenario:** Officer investigates company A, discovers it shares directors with company B. Needs to find all entities in this network.

**Current Workflow:**
1. Manual web searches for director names
2. Cross-reference company registries (SAMR, GLEIF, etc.)
3. Build mental model of relationships
4. May miss connections

**Desired Workflow:**
1. Click on director name in entity detail panel
2. See **all companies where this director serves**
3. Expand each to see **their supply chains**
4. Build **network visualization** showing all interconnections
5. Export as **relationship network diagram** for case file
6. Identify **pattern of transshipment** if multiple entities in same chain

### Use Case 3: Sanction Screening & OFAC Compliance

**Scenario:** Officer must ensure entity is not on sanctions lists before clearing shipment.

**Current Workflow:**
1. Check entity risk level (CRITICAL, HIGH, etc.)
2. Limited detail on WHY it's flagged
3. Must manually check OFAC SDN list

**Desired Workflow:**
1. See **OFAC SDN status** clearly labeled on entity card
2. Show **OFAC program** (SDNL, IEEUL, NPWMD, etc.)
3. Show **sanctions topic** (Iran, North Korea, Specially Designated Nationals, etc.)
4. Check **if any entity in supply chain** is on SDN list
5. Flag entire chain if **beneficial owner** is sanctioned
6. Show **confidence score** that match is accurate

### Use Case 4: Enforcement History & Pattern Recognition

**Scenario:** Officer is looking for indicators that entity has evaded duties before.

**Current Workflow:**
1. Entity page shows only current information
2. No indication of prior CBP cases
3. Must search case management system separately

**Desired Workflow:**
1. See **Prior CBP Filings** section showing enforcement history
2. View details: Case ID, case type (EAPA, AD/CVD, etc.), determination, outcome
3. See if entity has **pattern of violations** (repeat evader, etc.)
4. Check if **related entities** have violations
5. Flag if **similar commodities** have been subject to enforcement actions

---

## CURRENT STATE ANALYSIS

### What Works Well
✅ Entity search by name  
✅ Risk level determination (Critical/High/Medium/Low)  
✅ Watchlist status (Flagged/Not Flagged)  
✅ 3-level CORD chain resolution (Shipper → Parent → Manufacturer)  
✅ Basic entity details (name, ID, country, tax ID)  
✅ Supply chain parties list (role, entity, country)  

### What's Missing (Gaps)
❌ **Why-Connected Evidence** — No explanation for relationships  
❌ **4-Level Supply Chain** — Stops at 3 levels, missing beneficial owners  
❌ **Visual Relationship Graph** — Text-only format hard to understand  
❌ **OFAC SDN Detail** — No program or sanctions topic shown  
❌ **Prior CBP Cases** — No enforcement history displayed  
❌ **Risk Aggregation** — Only individual entity risk, not chain risk  
❌ **Shared Identifiers** — No indication of shared directors/agents/locations  
❌ **Entity Confidence** — No match confidence scores (0-1) shown  
❌ **Drill-Down** — Can't explore alternate corporate structures  
❌ **Relationship Types** — No indication if OWNS, OWNS_BY, PARENT_OF, etc.  

---

## PROPOSED FEATURE ENHANCEMENTS

### TIER 1 (MVP - Must Have) - Phase 1

#### 1.1 Enhanced Entity Card with OFAC Detail
```
CURRENT:
  Name | Risk Level | Country | Tax ID | Type | Status

ENHANCED:
  Name | Risk Level | Entity Type (with confidence: 0.98)
  ───────────────────────────────────────────────────
  Country | Tax ID | Incorporation Date | Registration Status
  ───────────────────────────────────────────────────
  🚩 OFAC SDN STATUS: WATCH LIST
     Program: IEEUL (Entity Enforcement & Evasion Regulation List)
     Sanctions Topic: Iran Sanctions Regulations
     Match Confidence: 0.96
  ───────────────────────────────────────────────────
  PRIOR ENFORCEMENT:
    • 2023-EAPA-001: Tariff evasion (Settled)
    • 2023-AD-CV-002: Anti-dumping duty (Active)
```

**Implementation:** Expand entity detail panel, add OFAC SDN fields, add prior filings table

#### 1.2 Why-Connected Evidence Panel
```
ENTITY CHAIN:
  Level 1 (Shipper): Greenfield Industrial Trading Co., Ltd. | VN | 0.98
                     ↓ OWNED_BY
  Level 2 (Holding): Greenfield Global Metals Holdings Ltd. | HK | 0.95
                     WHY CONNECTED:
                       ✓ Director Li Wei (Confidence: 0.94)
                       ✓ Registered Agent: China Trade Services (Confidence: 0.91)
                     ↓ PARENT_OF
  Level 3 (Mfg):     Guangdong Greenfield Aluminum Mfg. Co. | CN | 0.92
                     WHY CONNECTED:
                       ✓ Ownership: HK owns 88% per SAMR (Confidence: 0.96)
                       ✓ Shared Location: Guangzhou Industrial Zone (Confidence: 0.93)
```

**Implementation:** Add "why_connected" section to each entity in chain, show relationship type and evidence

#### 1.3 Chain Risk Assessment Summary
```
⚠️ SUPPLY CHAIN RISK ASSESSMENT

Overall Risk Level: CRITICAL (3 of 3 entities flagged)

Risk Factors:
  🚩 Level 1: OFAC SDN match (IEEUL) — Iran Sanctions
  ⚠️ Level 2: Parent company WATCH list
  ⚠️ Level 3: Known transshipment corridor (VN→HK→CN→US)

Aggregated Risk Score: 94/100

Recommendation: Do not clear shipment without further investigation
```

**Implementation:** Add risk aggregation logic, display prominent alert card

### TIER 2 (Enhanced) - Phase 2

#### 2.1 4-Level Beneficial Ownership Chain
```
Current: Shipper → Parent → Manufacturer (3 levels)
Enhanced: Shipper → Parent → Beneficial Owner → Ultimate Beneficial Owner (4 levels)

Show: Ownership percentages, voting rights, directors/shareholders
```

**Implementation:** Extend CORD resolve to 4 levels, add ownership structure diagram

#### 2.2 Interactive Relationship Graph (Visualization)
- Visual network diagram showing all entities as nodes
- Relationship types as edges (OWNS, PARENT_OF, SHARES_DIRECTOR, etc.)
- Confidence scores on each edge
- Risk levels as node colors (red=critical, orange=high, green=low)
- Click entity to see details, click relationship to see evidence
- Zoom/pan for large networks

**Implementation:** Use React Flow or D3.js for interactive graph

#### 2.3 Shared Identifiers Network
```
DIRECTORS:
  Li Wei: Greenfield Trading (VN) | Greenfield Holdings (HK) | Greenfield Mfg (CN)
  → Potential shell company network indicator

REGISTERED AGENTS:
  China Trade Services: 6 entities in CORD database
  → Centralized control indicator

FREIGHT FORWARDERS:
  Pan-Pacific Logistics: Used by Greenfield (VN), SunPath (US)
  → Indicates supply chain relationship
```

**Implementation:** Extract and display shared identifiers from entity chains

#### 2.4 Alternative Corporate Structures
```
When entity has multiple ownership paths or alternate names:
  Greenfield Industrial Trading Co., Ltd.
    AKA: GF Trading | Greenfield Industrial Co.
    Also know as: Green Field Industrial (Thai entity with similar name)

Show alternate registered locations, business addresses
```

**Implementation:** Include AKA names from CORD, show multiple corporate registrations

### TIER 3 (Advanced) - Phase 3

#### 3.1 Enforcement History Timeline
```
2025-Q2: Investigation initiated
2025-Q3: Referral package generated (Case: 2023-EAPA-001)
2025-Q4: Settlement agreement signed
2026-Q1: Duty collected, case closed

Show: Case progression, settlement amounts, violations found
```

**Implementation:** Timeline visualization of prior CBP cases

#### 3.2 Commodity & Route Pattern Analysis
```
For each entity in chain, show:
  Typical commodities: Steel coils, aluminum ingots, rare earth elements
  Trade routes: CN → VN → US (63%), CN → HK → US (28%), Direct (9%)
  High-risk routes: Any routes through known transshipment hubs?
  Duty evasion pattern: Previous enforcement for same commodity?
```

**Implementation:** Connect to commodity scoring data, trade flow analysis

#### 3.3 Sanctions Program Classification
```
Show: SDNL, IEEUL, NPWMD, etc.
Explain: What each program means, what is prohibited
Show: Any related entities in same sanctions program
```

**Implementation:** Add sanctions topic detail, cross-reference related entities

#### 3.4 Beneficial Owner Validation Workflow
```
Confidence Assessment:
  High Confidence (>0.9): Data from official sources (SAMR, GLEIF, etc.)
  Medium Confidence (0.7-0.9): Data from multiple commercial sources
  Low Confidence (<0.7): Limited sources or conflicting data

Allow officer to: Mark as verified, request manual investigation, override
```

**Implementation:** Add confidence assessment UI, add validation workflow

---

## UX WORKFLOW - CBP OFFICER PERSPECTIVE

### Workflow 1: Initial Entity Investigation

```
1. SEARCH & SELECT
   ├─ Officer searches for shipper name (e.g., "Greenfield Industrial")
   ├─ Results show: Entity name, country, risk level, watchlist status
   └─ Officer clicks entity to open detail panel

2. ENTITY OVERVIEW (Right Panel Opens)
   ├─ See entity card with all basic details
   ├─ See OFAC SDN status immediately (color-coded: red if listed)
   ├─ See prior CBP filings at a glance
   └─ See supply chain parties in table

3. CHAIN VISUALIZATION
   ├─ See visual representation of 3-4 level supply chain
   ├─ Each level shows: Name | Country | Type | Confidence
   ├─ Each arrow shows: Relationship type (OWNS, PARENT_OF, etc.)
   └─ Each arrow has: WHY CONNECTED section (evidence)

4. WHY-CONNECTED INVESTIGATION
   ├─ Officer hovers over chain arrow
   ├─ Sees evidence types: DIRECTOR_SHARED, OWNERSHIP_STAKE, REGISTERED_AGENT_SHARED
   ├─ Each evidence shows: Type | Details | Confidence | Source
   └─ Officer can click evidence to drill down (e.g., click "Director Li Wei" to see all entities)

5. RISK ASSESSMENT
   ├─ See aggregated chain risk (e.g., "CRITICAL - 3 of 3 entities flagged")
   ├─ See breakdown of risk factors
   ├─ See recommendation (clear/investigate further/escalate)
   └─ See confidence in risk assessment

6. DRILL DOWN (Optional)
   ├─ Click any entity in chain to expand its details
   ├─ See that entity's related entities and relationships
   ├─ Build mental model of full network
   ├─ Export network diagram for case file
   └─ Return to parent view

7. DECISION
   ├─ Officer decides: Clear shipment / Escalate / Request further investigation
   ├─ Log decision and evidence trail
   └─ Forward to enforcement team if needed
```

### Workflow 2: Detecting Related Party Network

```
1. INITIAL INVESTIGATION
   └─ Officer is investigating Entity A for potential evasion

2. VIEW SHARED DIRECTORS
   ├─ Click "SHARED IDENTIFIERS" section
   ├─ See: Director Li Wei serves on 6 entities
   ├─ Color-code by flag status (red if any flagged)
   └─ Click director name to expand

3. EXPAND NETWORK
   ├─ See all 6 entities where Li Wei serves
   ├─ Each entity shows: Name | Country | Risk Level | Watchlist Status
   ├─ Some entities are also in Entity A's supply chain
   └─ Officer recognizes pattern: Layering network

4. RELATED PARTY ANALYSIS
   ├─ Check if any of these 6 entities are:
   │  ├─ On sanctions lists
   │  ├─ Have prior CBP enforcement
   │  └─ Appear in other shipments
   ├─ Build timeline: When were entities incorporated?
   └─ Pattern emerges: Entities incorporated in quick succession

5. NETWORK VISUALIZATION
   ├─ Click "View Network" button
   ├─ See visual graph showing:
   │  ├─ All 6 entities as nodes (colored by risk level)
   │  ├─ Connections as edges (labeled with relationship type)
   │  └─ Director overlap clearly visible as shared connection
   ├─ Zoom/pan to explore
   └─ Right-click entity to see detail

6. ESCALATION
   ├─ Officer finds pattern indicating shell company network
   ├─ Exports network diagram as PDF
   ├─ Submits as evidence for referral
   └─ Marks case as "High Priority - Network Investigation"
```

### Workflow 3: Sanction Screening

```
1. RECEIVE MANIFEST
   └─ New shipment manifest arrives for processing

2. QUICK SCREEN
   ├─ Search for shipper name
   ├─ See entity card
   ├─ Check OFAC SDN status (prominent red badge if listed)
   ├─ Check if any entity in supply chain is SDN listed
   └─ Check prior enforcement

3. DETAILED REVIEW (If flagged)
   ├─ Read OFAC program details (SDNL, IEEUL, NPWMD, etc.)
   ├─ Read sanctions topic (Iran, North Korea, Embargoed Countries, etc.)
   ├─ Understand what is prohibited for this sanctions program
   ├─ Check if commodity is covered by sanctions
   └─ Check if destination country is prohibited

4. RELATED ENTITY CHECK
   ├─ See if beneficial owner is on SDN list
   ├─ See if any parent/intermediate company is listed
   ├─ See if shared directors have SDN matches
   └─ Determine: Is entire supply chain prohibited?

5. DECISION
   ├─ Clear shipment (low risk)
   ├─ Request further investigation (medium risk)
   ├─ Block shipment immediately (SDN match or sanctions violation)
   └─ Refer to OFACSanctions team (if complex international case)
```

---

## DATA REQUIREMENTS ANALYSIS

### Data Currently Available
✅ Entity name, country, tax ID (CORD)  
✅ Entity type & confidence (Senzing)  
✅ Risk level & watchlist status (CORD + OFAC)  
✅ 3-level supply chain (CORD resolve endpoint)  
✅ Supply chain parties (CORD entity/{id}/parties)  
✅ Related entities (Senzing)  

### Data Currently Missing (Need to Fetch)

#### 1. Why-Connected Evidence (HIGH PRIORITY)
**Missing:** Evidence linking each entity in chain  
**Available From:** Senzing `/api/entities/why/{entity_a}/{entity_b}` endpoint  
**What to Fetch:** For each pair in chain, fetch why-connected evidence  
**Data Structure:**
```json
{
  "evidence": [
    {
      "type": "DIRECTOR_SHARED",
      "details": "Director Li Wei in both corporate registries",
      "confidence": 0.94,
      "source": "SAMR + Hong Kong BR"
    }
  ],
  "relationship": "OWNED_BY",
  "confidence": 0.95
}
```

#### 2. OFAC SDN Program & Topic (HIGH PRIORITY)
**Missing:** Detailed OFAC program name and sanctions classification  
**Available From:** CORD entity details already contain this  
**What to Fetch:** Already in `entity.ofac_program` and `sanctions_topic`  
**Data Structure:**
```json
{
  "ofac_program": "IEEUL",
  "ofac_program_name": "Entity Enforcement & Evasion Regulation List",
  "sanctions_topic": "Iran Sanctions Regulations",
  "match_confidence": 0.96
}
```
**Action:** Extract from existing entity response, display prominently

#### 3. Prior CBP Filings (HIGH PRIORITY)
**Missing:** CBP enforcement history for entity  
**Available From:** Senzing `entity.prior_filings` already contains this  
**What to Fetch:** Already in response: `prior_filings = [{case_id, determination, status}, ...]`  
**Data Structure:**
```json
{
  "case_id": "2023-EAPA-001",
  "case_type": "EAPA",
  "violation": "Tariff evasion",
  "determination": "Evasion confirmed",
  "status": "Settled",
  "penalty_amount_usd": 250000,
  "date_filed": "2023-Q2"
}
```
**Action:** Request to include in Senzing response, display in UI

#### 4. 4-Level Beneficial Ownership Chain (MEDIUM PRIORITY)
**Missing:** Beneficial owner and ultimate beneficial owner (4th level)  
**Available From:** Extend CORD resolve endpoint to 4 levels  
**What to Fetch:** Need to call CORD `/api/cord/entity/{id}/chain` for level 3, then resolve level 4  
**Data Structure:**
```json
{
  "level": 4,
  "name": "Ultimate Beneficial Owner Company",
  "country": "CN",
  "ownership_percentage": 100,
  "voting_rights": 100,
  "relationship": "ULTIMATE_BENEFICIAL_OWNER"
}
```
**Action:** Modify CORD resolve to 4 levels, or make sequential calls

#### 5. Shared Identifiers (MEDIUM PRIORITY)
**Missing:** All shared directors, agents, locations across entity network  
**Available From:** Need to query CORD for all entities with same director/agent/location  
**What to Fetch:** Build from entity_chain by extracting identifiers, query CORD for all entities with those identifiers  
**Data Structure:**
```json
{
  "shared_directors": [
    {
      "name": "Li Wei",
      "entities": ["greenfield-vn", "greenfield-hk", "greenfield-cn"],
      "roles": ["Director", "Chairman", "Director"],
      "confidence": 0.94
    }
  ],
  "shared_agents": [
    {
      "name": "China Trade Services",
      "entities": ["greenfield-vn", "greenfield-hk"],
      "count_in_database": 6
    }
  ]
}
```
**Action:** Build from existing data, add CORD queries for cross-entity search

#### 6. Alternative Corporate Names (LOW PRIORITY)
**Missing:** All known AKA names for entity  
**Available From:** CORD already has `names_aka` field  
**What to Fetch:** Include in entity response  
**Data Structure:**
```json
{
  "names_aka": ["GF Trading", "Greenfield Industrial Co.", "Green Field Industrial Ltd."]
}
```
**Action:** Extract from existing CORD response, display on entity card

#### 7. Entity Confidence Scores (LOW PRIORITY)
**Missing:** Match confidence (0-1) for entity resolution  
**Available From:** Senzing already returns this  
**What to Fetch:** Use existing `entity.confidence` field  
**Data Structure:**
```json
{
  "entity_id": "greenfield-vn",
  "name": "Greenfield Industrial Trading Co., Ltd.",
  "confidence": 0.98,
  "confidence_explanation": "High confidence: Name matched in multiple official sources (SAMR, CORD, etc.)"
}
```
**Action:** Display alongside entity type

---

## PUBLIC DATA SOURCES FOR ENHANCEMENT

### Already Integrated
✅ CORD (Compliance & Regulatory Database) - 244K entities with full details  
✅ OFAC SDN List - Sanctions screening  
✅ Senzing - Entity resolution and relationship evidence  

### Additional Public Sources (If Needed)

#### 1. Corporate Registry Data
- **China SAMR** (State Administration for Market Regulation) - Corporate registrations
  - Free tier: Basic entity search
  - Limited API access, mostly web-based
  
- **Hong Kong Corporations Registry** - HK entity filings
  - Free: Basic search on registry website
  - Limited API, requires web scraping (legal for public data)
  
- **Malaysia SSM Registry** - Malaysian company registration
  - Free: Basic search
  - No public API

- **Vietnam National Business Registration Portal** - Vietnamese business data
  - Free: Basic search
  - Limited English support

#### 2. Beneficial Owner Data
- **GLEIF LEI Registry** (Legal Entity Identifiers)
  - Free, comprehensive beneficiary information
  - API available, 100 requests/day free
  - Already likely in CORD

- **Open Corporates** - Global corporate ownership data
  - Free tier: Bulk API access
  - ~150M companies worldwide

- **Dun & Bradstreet** (D&B)
  - Commercial database, but public DUNS registry
  - Free basic search, paid enhanced data

#### 3. Enforcement/Compliance History
- **CBP EAPA Cases Database** - Online public case database
  - Free access: www.cbp.gov/trade/commencement-investigations/eapa
  - Searchable by importer name, case number

- **US ITA (International Trade Administration)**
  - Free: Anti-dumping/countervailing duty cases
  - Searchable database

- **BIS Entity List** (Commerce Department)
  - Free: Denied parties, export violators
  - Public API available

#### 4. Sanctions & Watchlists
- **OFAC SDN List** (Treasury Department)
  - Free, regularly updated
  - Already integrated via CORD

- **UN Consolidated List** - UN sanctions
  - Free, XML/CSV export
  - Public, regularly updated

- **EU Consolidated Lists** - EU sanctions
  - Free, HTML/XML
  - For international compliance

---

## TECHNICAL ARCHITECTURE

### Frontend Components

#### New Components Needed
1. **EntityChainVisualization** — Interactive chain display with why-connected evidence
2. **RelationshipGraph** — D3.js/React Flow network visualization
3. **WyConnectedPanel** — Evidence display for relationship
4. **OFACSectionDetail** — OFAC status with program details
5. **SharedIdentifiersPanel** — Shared directors/agents/locations
6. **RiskAssessmentCard** — Aggregated chain risk summary
7. **EnforcementHistoryTimeline** — Prior CBP cases timeline

#### Modified Components
1. **V2EntitiesPage** — Main page layout, add tabs for different views
2. **EntityRelationshipGraph** — Enhance existing graph, add evidence display

### Backend API Endpoints Needed

#### New Endpoints (Phase 1)
```
GET /api/entities/why/{entity_a}/{entity_b}
  Returns: evidence[], confidence, relationship, relationship_type

GET /api/entities/{entity_id}/enforcement-history
  Returns: prior_filings[], settlements, pattern_analysis

GET /api/entities/{entity_id}/shared-identifiers
  Returns: directors[], agents[], locations[], confidence_scores
```

#### Enhanced Endpoints
```
GET /api/cord/resolve (ENHANCED)
  Input: shipper_name, shipper_country, consignee_name, consignee_country
  Output: 4-level chain instead of 3-level (add beneficial owner)
  Add: why_connected evidence for each level
  Add: OFAC SDN details
  Add: Prior CBP filings
```

### Database Queries

#### Need to Store/Cache
- Entity relationship evidence (why-connected)
- Prior CBP enforcement history per entity
- Shared identifiers network
- Risk aggregation scores

#### Performance Optimization
- Cache why-connected queries (expensive Senzing API)
- Index entity relationships for fast lookup
- Pre-compute chain risk assessment during entity resolution
- Cache OFAC SDN matches

---

## IMPLEMENTATION ROADMAP

### Phase 1 (Weeks 1-2): MVP - Core Features
**Goal:** Get high-priority features to CBP team for testing

**Features:**
- ✅ Enhanced entity card (OFAC detail, prior filings)
- ✅ Why-connected evidence for each chain level
- ✅ Chain risk assessment summary
- ✅ Visual chain with relationship types

**Deliverables:**
- Modified V2EntitiesPage with enhanced detail panel
- New EntityChainVisualization component
- New OFACSectionDetail component
- API integration for why-connected and enforcement history

**User Testing:** Show CBP team, get feedback on usefulness and clarity

### Phase 2 (Weeks 3-4): Enhanced Features
**Goal:** Add visualization and 4-level beneficial ownership

**Features:**
- ✅ Interactive relationship graph (D3.js/React Flow)
- ✅ 4-level beneficial owner chain
- ✅ Shared identifiers network (directors, agents)
- ✅ Drill-down navigation

**Deliverables:**
- RelationshipGraph component
- SharedIdentifiersPanel component
- Enhanced CORD integration (4-level resolve)
- Network visualization with zoom/pan

### Phase 3 (Weeks 5-6): Polish & Advanced Features
**Goal:** Add timeline, commodity analysis, enforcement patterns

**Features:**
- ✅ Enforcement history timeline
- ✅ Commodity & route pattern analysis
- ✅ Sanctions program classification detail
- ✅ Beneficial owner validation workflow

**Deliverables:**
- EnforcementHistoryTimeline component
- CommodityAnalysisPanel component
- Validation workflow UI
- Export/sharing functionality

---

## SUCCESS METRICS

### Quantitative Metrics
- **Case Investigation Time**: Reduce from 45 min to 20 min (55% faster)
- **False Positive Rate**: Reduce by 30% (better evidence for decisions)
- **Related Party Detection**: Increase detection rate from 60% to 90%
- **Sanctions Screening Accuracy**: 99.9% (no SDN matches missed)

### Qualitative Metrics
- **Officer Confidence**: Survey: "I understand why entities are connected" - Target: >90% agree
- **Usability**: Task completion rate >95%, error rate <5%
- **Adoption**: >80% of CBP officers using new features within 2 months

### Business Metrics
- **Enforcement Cases**: Increase referrals by 20% (better detection)
- **Duty Collection**: Increase collections by 15% (catch more evaders)
- **Compliance**: 100% OFAC compliance (zero missed sanctions matches)

---

## OPEN QUESTIONS FOR DISCUSSION

### 1. Data Availability
- **Q:** Do we have access to 4-level beneficial owner data, or only 3 levels currently?
- **A:** [To be discussed]

- **Q:** Can CORD resolve endpoint be extended to 4 levels, or do we need sequential queries?
- **A:** [To be discussed]

### 2. Performance & Caching
- **Q:** How long does why-connected evidence query take from Senzing? Should we pre-compute?
- **A:** [To be discussed]

- **Q:** Should we cache entity chains or always fetch fresh?
- **A:** [To be discussed]

### 3. Visualization
- **Q:** For complex networks (50+ entities), will D3.js network graph be slow?
- **A:** [To be discussed]

- **Q:** Should we implement progressive loading (initial 10 entities, load on demand)?
- **A:** [To be discussed]

### 4. CBP Process Integration
- **Q:** How will Entity Resolution integrate with referral generation workflow?
- **A:** [To be discussed]

- **Q:** Should entities/chains be exportable to referral packages?
- **A:** [To be discussed]

### 5. Public Data Sources
- **Q:** Should we integrate additional public corporate registry data beyond CORD?
- **A:** [To be discussed]

- **Q:** What's the business case for scraping China SAMR, Hong Kong BR, Malaysia SSM?
- **A:** [To be discussed]

---

## APPENDIX A: SAMPLE USER INTERFACE MOCKUP

### Current State vs. Proposed State

#### Current (List + Basic Detail)
```
┌─────────────────────────────────────────────────────────────┐
│ Entity Resolution                                           │
├─────────────────────────┬───────────────────────────────────┤
│ Search: [Greenfield]    │ Name: Greenfield Industrial... VN │
│                         │ Type: Manufacturer  ID: green-vn  │
│ ┌─────────────────────┐ │ Country: Vietnam  Tax ID: xxxxxx  │
│ │ Greenfield Ind VN  │ │ Status: Flagged                   │
│ │ Risk: HIGH          │ │                                   │
│ │ Country: VN         │ │ Entity Chain:                     │
│ │ [WORKSPACE]         │ │ 1. Greenfield Industrial (VN)    │
│ └─────────────────────┘ │ 2. Greenfield Holdings (HK)      │
│ ┌─────────────────────┐ │ 3. Greenfield Mfg (CN)           │
│ │ Greenfield Hld HK   │ │                                   │
│ │ Risk: HIGH          │ │ Supply Chain Parties:            │
│ │ Country: HK         │ │ Shipper: Greenfield VN           │
│ │ [WORKSPACE]         │ │ Mfg: Greenfield CN               │
│ └─────────────────────┘ │ Consignee: SunPath US            │
│ ┌─────────────────────┐ │                                   │
│ │ Greenfield Mfg CN   │ │ [BACK TO QUEUE]                  │
│ │ Risk: HIGH          │ └───────────────────────────────────┘
│ │ Country: CN         │
│ │ [WORKSPACE]         │
│ └─────────────────────┘
└─────────────────────────────────────────────────────────────┘
```

#### Proposed (Enhanced with Evidence & Risk Assessment)
```
┌──────────────────────────────────────────────────────────────────┐
│ Entity Resolution | With Senzing Intelligence                   │
├──────────────────────────────────┬────────────────────────────────┤
│ Search: [Greenfield________]     │ 📋 GREENFIELD INDUSTRIAL...  │
│ [Filter by Risk] [Export Network]│ ✓ Entity Type: Shipper (0.98) │
│                                  │ Country: Vietnam | Tax: xxxxx  │
│ ┌──────────────────────────────┐ │ Incorporated: 2025-09-15      │
│ │ Greenfield Industrial Co VN  │ │                              │
│ │ Risk: 🔴 HIGH               │ │ 🚩 OFAC SDN: WATCH LIST     │
│ │ Country: VN | 0.98 conf     │ │    Program: IEEUL            │
│ │ [Details] [Network] [Export] │ │    Topic: Iran Sanctions     │
│ └──────────────────────────────┘ │    Confidence: 0.96          │
│ ┌──────────────────────────────┐ │                              │
│ │ Greenfield Global Met HK     │ │ 📌 PRIOR CBP FILINGS:       │
│ │ Risk: 🟠 MEDIUM             │ │ • 2023-EAPA-001 (Settled)   │
│ │ Country: HK | 0.95 conf     │ │ • 2023-AD-CV-002 (Active)   │
│ │ [Details] [Network] [Export] │ │                              │
│ └──────────────────────────────┘ │ ⚠️  SUPPLY CHAIN RISK      │
│ ┌──────────────────────────────┐ │ Overall: CRITICAL (3/3)    │
│ │ Guangdong Greenfield Mfg CN  │ │ • All entities flagged     │
│ │ Risk: 🔴 HIGH               │ │ • OFAC match at level 1    │
│ │ Country: CN | 0.92 conf     │ │ • Transshipment corridor   │
│ │ [Details] [Network] [Export] │ │                              │
│ └──────────────────────────────┘ │ 🔗 ENTITY CHAIN WITH EVIDENCE
│                                  │                              │
│                                  │ Level 1: Greenfield Ind VN  │
│                                  │ (Shipper, 0.98)             │
│                                  │          ↓ OWNED_BY          │
│                                  │ 📌 Why Connected:           │
│                                  │ • Director Li Wei (0.94)    │
│                                  │ • Shared Agent (0.91)       │
│                                  │          ↓                  │
│                                  │ Level 2: Greenfield Hld HK  │
│                                  │ (Holding, 0.95)             │
│                                  │          ↓ PARENT_OF         │
│                                  │ 📌 Why Connected:           │
│                                  │ • Ownership: 88% (0.96)     │
│                                  │ • Same Location (0.93)      │
│                                  │          ↓                  │
│                                  │ Level 3: Guangdong Mfg CN   │
│                                  │ (Mfg, 0.92)                 │
│                                  │                              │
│                                  │ [View Graph] [View Network] │
│                                  │ [Back to Queue]             │
│                                  │                              │
└──────────────────────────────────────────────────────────────────┘
```

---

## APPENDIX B: DATA FLOW DIAGRAM

```
CBP Officer Portal
    │
    └─→ [Search Entity] "Greenfield Industrial"
         │
         └─→ CORD Service (244K entities)
             │
             ├─→ Full-text search → [entity_list]
             │
             └─→ [Officer selects entity]
                 │
                 ├─→ /cord/entity/{id}
                 │   └─→ Basic entity details + OFAC SDN status
                 │
                 ├─→ /cord/resolve (shipper, country)
                 │   └─→ 3-4 level chain [level_1, level_2, level_3, level_4]
                 │
                 ├─→ /cord/entity/{id}/parties
                 │   └─→ Supply chain parties (shipper, mfg, consignee, etc.)
                 │
                 └─→ Senzing Service
                     │
                     ├─→ /entities/resolve
                     │   └─→ Confidence scores, entity types, risk flags
                     │
                     ├─→ /entities/why/{entity_a}/{entity_b} [For each pair in chain]
                     │   └─→ Evidence (DIRECTOR_SHARED, OWNERSHIP_STAKE, etc.)
                     │
                     ├─→ /entities/{id}/prior-filings [For each entity]
                     │   └─→ Prior CBP enforcement history
                     │
                     └─→ Database Cache
                         └─→ Store: Chains, evidence, prior filings for fast lookup

Result: Complete Entity Intelligence Dashboard
    ├─ Entity details with OFAC SDN
    ├─ 4-level supply chain with why-connected evidence
    ├─ Risk aggregation across chain
    ├─ Prior CBP enforcement history
    ├─ Shared identifiers network
    ├─ Visual relationship graph
    └─ Officer decision + audit trail
```

---

## APPENDIX C: DISCUSSION GUIDE FOR STAKEHOLDERS

### For CBP Leadership
- **Value:** Reduce case investigation time by 55%, improve enforcement rate by 20%
- **Risk:** Integration with Senzing/CORD, data quality/freshness, performance at scale
- **Timeline:** 6 weeks to full feature set

### For CBP Officers (Target Users)
- **Pain Points:** Long investigation times, manual research needed, hard to understand complex networks
- **Benefits:** Faster case review, better network detection, clearer evidence trails
- **Training Needed:** 2 hours initial training, continued support

### For IT/Security
- **API Integration:** New endpoints for why-connected, enforcement history
- **Data Security:** PII handling (director names, agents), OFAC data, case information
- **Performance:** Caching strategy, query optimization for large networks
- **Compliance:** Data retention, audit logging, access controls

### For Data/Analytics
- **Data Freshness:** CORD updates (real-time? daily?), Senzing confidence, enforcement data updates
- **Data Quality:** Entity matching accuracy, why-connected confidence, enforcement history coverage
- **Monitoring:** Track entity resolution success rate, user adoption, false positive rate

---

**END OF DOCUMENT**

*Next Step: Discuss with CBP team, get feedback on proposed features, prioritize based on impact*
