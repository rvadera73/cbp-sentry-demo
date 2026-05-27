# Senzing & CORD Capabilities for Entity Resolution

## Overview
- **CORD**: 244K entities with FTS5 full-text search, OFAC SDN data, multiple sources (GLEIF, OFAC, etc.)
- **Senzing**: Entity relationship resolution, why-connected explanations, confidence scoring
- **Combined**: Can show complete 3-4 level supply chains with evidence of connections

---

## CORD Capabilities (Full-Text Search Index)

### Data Available Per Entity
```
- record_id: Unique identifier
- data_source: GLEIF, OFAC, etc.
- record_type: Entity type classification
- name_primary: Primary/official name
- names_aka: Alternative/known names list
- country: Registration country
- ofac_program: If OFAC listed (SDNL, IEEUL, etc.)
- sanctions_topic: Sanctions classification
- raw_json: Full entity record with all details
```

### CORD Search Endpoints
1. **`/api/cord/search`** — FTS5 search by name + country
   - Returns: record_id, data_source, name, country, raw_json
   - Filters: name (fuzzy match), country (exact), limit

2. **`/api/cord/resolve`** — Resolve 3-level shipper → parent → manufacturer chain
   - Input: shipper_name, shipper_country, consignee_name, consignee_country
   - Returns: level_1, level_2, level_3 with relationships and confidence

3. **`/api/cord/entity/{id}`** — Get full entity details
   - Returns: Complete record with all fields

4. **`/api/cord/entity/{id}/chain`** — Get entity ownership/supply chain hierarchy
   - Returns: Array of related entities in chain

5. **`/api/cord/entity/{id}/parties`** — Get supply chain parties
   - Returns: Array of shipper, consignee, manufacturer, intermediary, bank relationships

6. **`/api/cord/why/{entity_a}/{entity_b}`** — Why are two entities connected?
   - Returns: Evidence, confidence, relationship type

---

## Senzing Capabilities (Entity Resolution + Relationship Evidence)

### Data Available Per Entity
```
- entity_id: Senzing ID
- name: Entity name
- country: Country code
- incorporation_date: Registration date
- entity_type: shipper | consignee | manufacturer | intermediary
- confidence: Match confidence (0-1)
- related_entities: Array of connected entities
- prior_filings: CBP/customs enforcement cases
- risk_flags: NEW_SHIPPER, TRANSSHIPMENT_CORRIDOR, etc.
```

### Why-Connected Evidence Types
1. **DIRECTOR_SHARED** — Same director on multiple entities
   - Example: "Director Li Wei appears in both corporate registries"
   - Confidence: ~0.94

2. **FREIGHT_FORWARDER_SHARED** — Same logistics provider used
   - Example: "Both use Pan-Pacific Logistics (FRW-98765)"
   - Confidence: ~0.87

3. **REGISTERED_AGENT_SHARED** — Same legal representative
   - Example: "Both list China Trade Services as agent"
   - Confidence: ~0.91

4. **OWNERSHIP_STAKE** — Direct ownership/shareholding
   - Example: "HK owns 88% of Guangdong Greenfield per SAMR registry"
   - Confidence: ~0.96

5. **BOARD_OVERLAP** — Same executives/board members
   - Example: "Chairman Zhang on boards of both"
   - Confidence: ~0.89

6. **FACILITY_LOCATION** — Share physical location
   - Example: "Both in Guangzhou Industrial Zone, Nansha District"
   - Confidence: ~0.93

### Senzing API Endpoints
1. **`/api/entities/resolve`** — Resolve shipper/consignee entities
   - Input: manifest_id, shipper_name, consignee_name
   - Returns: entities[], graph_edges[], total_confidence, source
   
2. **`/api/entities/why/{entity_a}/{entity_b}`** — Why are they connected?
   - Returns: evidence[], confidence, relationship, explanation

3. **`/api/entities/{entity_id}`** — Get entity details
   - Returns: Full entity record with all relationships

---

## Current Entity Resolution Page Implementation

### What's Showing Now
✅ Entity queue (Greenfield VN, Greenfield CN, Bangalore, Shanghai, Vietnam, Shenzhen)
✅ Risk level detection (Critical/High/Medium/Low)
✅ Watchlist status (Flagged/Not Flagged)
✅ 3-level CORD chain resolution
✅ Entity name, ID, country, tax ID, type

### What Could Be Added

#### 1. Enhanced Entity Details Panel
```
Current: Name, ID, Country, Tax ID, Source
Could Add:
  - Incorporation date (from Senzing)
  - Entity type with confidence score
  - Prior CBP filings / enforcement history
  - Risk flags (NEW_SHIPPER, TRANSSHIPMENT_CORRIDOR, etc.)
  - All known AKA names (from CORD)
```

#### 2. Why-Connected Deep Dive
```
When two entities are in same chain:
  - Show WHY they're connected
  - Display evidence types (DIRECTOR_SHARED, SHARED_AGENT, etc.)
  - Show confidence for each connection
  - Map the directors/agents/locations shared
```

#### 3. OFAC SDN Status
```
Current: Generic risk flags
Could Add:
  - Explicit OFAC SDN program (if listed)
  - OFAC program type (SDNL, IEEUL, NPWMD, etc.)
  - Sanctions topic classification
  - Facility locations from SDN record
```

#### 4. Complete Supply Chain Map
```
Current: 3-level chain in text list
Could Add:
  - Visual network graph showing all relationships
  - Relationship types (OWNS, PARENT_OF, SUPPLIER_TO, etc.)
  - Confidence scores on each edge
  - Hover to see evidence linking them
```

#### 5. Beneficial Owner Detection
```
Could resolve who ultimately owns/controls entity:
  - Level 1: Direct shipper
  - Level 2: Parent company
  - Level 3: Beneficial owner / Ultimate parent
  - Level 4: Ultimate beneficial owner (if available)
```

#### 6. Risk Aggregation Across Chain
```
If ANY entity in chain is:
  - On OFAC SDN → Mark chain as HIGH/CRITICAL
  - New shipper → Flag as TRANSSHIPMENT risk
  - Shared agent with known violator → RELATED PARTY RISK
  
Show: "Chain Risk Assessment" with aggregated score
```

#### 7. Prior Enforcement History
```
Could show:
  - CBP enforcement actions on this entity
  - Settlement agreements
  - Previous referral packages
  - Outcome of prior investigations
  - Similar entities with violations
```

#### 8. Intermediary & Agent Network
```
Could show:
  - All freight forwarders used by entity
  - All registered agents used by entity
  - All banks/financial institutions involved
  - Cross-references with other entities (if shared)
```

---

## Recommended Feature Additions (Priority Order)

### 🔴 HIGH PRIORITY
1. **Why-Connected Evidence Panel** — When showing chain, explain each connection with evidence
2. **OFAC SDN Program Display** — Show if entity is on SDN list and which program
3. **Prior CBP Filings** — Show enforcement history and prior cases
4. **Beneficial Owner Chain** — Resolve up to 4 levels to find ultimate beneficial owner

### 🟡 MEDIUM PRIORITY
5. **Risk Aggregation** — Show risk for entire chain, not just individual entity
6. **Shared Agent/Forwarder Network** — Show all intermediaries and cross-references
7. **Entity Confidence Score** — Show Senzing confidence for each match (0-1)
8. **Alternative Names (AKA)** — Show all known aliases from CORD

### 🟢 LOW PRIORITY
9. **Visual Network Graph** — Interactive graph of relationships instead of text list
10. **Timeline** — Show incorporation dates, case dates, events in chronological order
11. **Commodity/Route Analysis** — For each entity, show typical products and trade routes
12. **Sanctions Topic Classification** — OFAC sanctions categories

---

## API Calls Needed for Each Feature

### Why-Connected (HIGH PRIORITY)
```
For each pair in entity_chain:
  GET /api/entities/why/{entity_a}/{entity_b}
  Returns: evidence[], confidence, relationship
  
Show as: "Director Li Wei → Both entities"
         "Shared freight forwarder → Pan-Pacific Logistics"
         "Ownership stake → HK owns 88% per SAMR"
```

### OFAC SDN Status (HIGH PRIORITY)
```
For each entity in chain:
  GET /api/cord/entity/{id}  (already fetched)
  Extract: ofac_program, sanctions_topic
  
Show as: "🚩 OFAC SDN Listed"
         "Program: SDNL (Specially Designated Nationals List)"
         "Topic: Cuba Embargo"
```

### Prior CBP Filings (HIGH PRIORITY)
```
Use Senzing response:
  entity.prior_filings = [{case_id, determination}, ...]
  
Show as: "2023-EAPA-001: Tariff evasion (settled)"
         "2023-AD-CV-002: Anti-dumping duty violation"
```

### Risk Aggregation (MEDIUM PRIORITY)
```
Logic:
  - If any entity = OFAC SDN → chain_risk = CRITICAL
  - If any entity = new_shipper → chain_risk = HIGH
  - If any intermediate = on_violation_list → chain_risk = HIGH
  - Else → chain_risk = MEDIUM or LOW
  
Show as: "⚠️ Chain Risk: CRITICAL (3 of 4 entities flagged)"
```

---

## Sample Output Structure

```json
{
  "entity_id": "greenfield-vn|vn",
  "entity_name": "Greenfield Industrial Trading Co., Ltd.",
  "country": "VN",
  "watchlist_status": "Flagged",
  "risk_level": "High",
  
  "entity_details": {
    "incorporation_date": "2025-09-15",
    "entity_type": "Shipper (Confidence: 0.98)",
    "ofac_status": "WATCH",
    "ofac_program": "IEEUL",
    "ofac_sanctions_topic": "Iran Sanctions",
    "known_aliases": ["GF Trading", "Greenfield Industrial Co."],
    "prior_filings": [
      {
        "case_id": "2023-EAPA-001",
        "determination": "Tariff evasion",
        "status": "Settled"
      }
    ],
    "risk_flags": ["TRANSSHIPMENT_CORRIDOR", "WATCH_LIST_MATCH"]
  },
  
  "entity_chain": [
    {
      "level": 1,
      "name": "Greenfield Industrial Trading Co., Ltd.",
      "country": "VN",
      "type": "Shipper",
      "confidence": 0.98,
      "role": "Direct shipper"
    },
    {
      "level": 2,
      "name": "Greenfield Global Metals Holdings Ltd.",
      "country": "HK",
      "type": "Holding Company",
      "confidence": 0.95,
      "role": "Parent/Owner",
      "why_connected": {
        "relationship": "OWNED_BY",
        "evidence": [
          {
            "type": "DIRECTOR_SHARED",
            "details": "Director Li Wei in both registries",
            "confidence": 0.94
          },
          {
            "type": "REGISTERED_AGENT_SHARED",
            "details": "China Trade Services, Room 1204",
            "confidence": 0.91
          }
        ]
      }
    },
    {
      "level": 3,
      "name": "Guangdong Greenfield Aluminum Mfg. Co., Ltd.",
      "country": "CN",
      "type": "Manufacturer",
      "confidence": 0.92,
      "role": "Ultimate manufacturer",
      "why_connected": {
        "relationship": "PARENT_COMPANY",
        "evidence": [
          {
            "type": "OWNERSHIP_STAKE",
            "details": "HK owns 88% per SAMR registry",
            "confidence": 0.96
          }
        ]
      }
    }
  ],
  
  "chain_risk_assessment": {
    "overall_risk": "CRITICAL",
    "flagged_entities": 3,
    "total_entities": 3,
    "reasons": [
      "Level 1: OFAC SDN match (IEEUL)",
      "Level 2: Parent company WATCH list",
      "Level 3: Facilitates restricted trade"
    ]
  }
}
```

---

## Implementation Roadmap

**Week 1: Foundation**
- Add why-connected evidence to chain display ✅
- Add OFAC SDN program field ✅
- Add prior CBP filings ✅

**Week 2: Enhancement**
- Add risk aggregation scoring
- Add alternative names display
- Add entity confidence scores

**Week 3: Polish**
- Visual network graph (optional)
- Timeline view (optional)
- Shared agent/forwarder analysis

---

## Notes for Development
- All data comes from existing APIs, no new endpoints needed
- CORD has 244K entities indexed, search is instant
- Senzing fixtures include Greenfield, SunPath, Solaria test cases
- Confidence scores (0-1) already calculated by both systems
- Evidence types are standardized across why-connected responses
