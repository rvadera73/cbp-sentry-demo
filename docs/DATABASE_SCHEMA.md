# Database Schema — PostgreSQL + Neo4j

## Overview

Sentry uses two complementary databases:

- **Neon PostgreSQL** (serverless, relational) — Operational data, auditing
- **Neo4j Aura** (managed, graph) — Entity relationships, ownership chains

Both are cloud-agnostic and work on GCP, AWS, or on-premises.

---

## PostgreSQL Schema (Neon)

### Database Setup

```sql
-- Create database
CREATE DATABASE sentry_db;

-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgvector";  -- For RAG embeddings

-- User
CREATE USER sentry_api WITH PASSWORD 'REDACTED';
GRANT ALL PRIVILEGES ON DATABASE sentry_db TO sentry_api;
```

### Core Tables

#### 1. shipments

**Purpose**: Manifest data + H1, H2, H3 results

```sql
CREATE TABLE shipments (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  
  -- Manifest data
  bill_of_lading VARCHAR(50) NOT NULL UNIQUE,
  manifest_id VARCHAR(50) NOT NULL UNIQUE,
  shipper_id UUID REFERENCES entities(id),
  consignee_id UUID REFERENCES entities(id),
  
  -- Cargo details
  hts_code VARCHAR(20) NOT NULL,
  declared_country_of_origin VARCHAR(2) NOT NULL,
  declared_value_usd DECIMAL(12, 2) NOT NULL,
  total_weight_kg INT NOT NULL,
  
  -- Port information
  port_of_lading VARCHAR(5),
  port_of_unlading VARCHAR(5),
  
  -- Status
  status VARCHAR(20) DEFAULT 'RECEIVED',  -- RECEIVED, ASSESSED, REFERRED, EXAMINED
  in_transit BOOLEAN DEFAULT FALSE,
  estimated_arrival TIMESTAMP,
  
  -- H1 Intelligence
  h1_corridor_id UUID REFERENCES corridors(id),
  h1_risk_level VARCHAR(30),
  
  -- H2 Intelligence
  h2_isf_element_9_location VARCHAR(255),
  h2_isf_stuffing_country VARCHAR(2),
  h2_isf_contradiction BOOLEAN DEFAULT FALSE,
  h2_ais_dwell_days DECIMAL(5, 2),
  h2_ais_dwell_baseline DECIMAL(5, 2),
  h2_ais_anomaly_ratio DECIMAL(5, 2),
  
  -- H3 Scoring
  h3_total_score INT,
  h3_confidence_level VARCHAR(10),  -- LOW, MEDIUM, HIGH
  h3_score_json JSONB,  -- Full score breakdown
  
  -- Referral
  referral_package_id UUID REFERENCES referral_packages(id),
  recommended_action VARCHAR(30),  -- EXAMINE_ON_ARRIVAL, REFER_TO_LAW_ENFORCEMENT
  
  -- Metadata
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  created_by_user_id UUID REFERENCES users(id),
  
  -- Full-text search
  search_vector tsvector,
  
  CONSTRAINT valid_status CHECK (status IN ('RECEIVED', 'ASSESSED', 'REFERRED', 'EXAMINED')),
  CONSTRAINT valid_confidence CHECK (h3_confidence_level IN ('LOW', 'MEDIUM', 'HIGH'))
);

CREATE INDEX idx_shipments_bol ON shipments(bill_of_lading);
CREATE INDEX idx_shipments_manifest ON shipments(manifest_id);
CREATE INDEX idx_shipments_shipper ON shipments(shipper_id);
CREATE INDEX idx_shipments_score ON shipments(h3_total_score DESC);
CREATE INDEX idx_shipments_status ON shipments(status);
CREATE INDEX idx_shipments_created ON shipments(created_at DESC);
CREATE INDEX idx_shipments_fts ON shipments USING GIN(search_vector);
```

#### 2. line_items

**Purpose**: Individual cargo items within shipment

```sql
CREATE TABLE line_items (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  shipment_id UUID NOT NULL REFERENCES shipments(id) ON DELETE CASCADE,
  
  -- Item details
  line_number INT NOT NULL,
  sku VARCHAR(50),
  description TEXT,
  hts_code VARCHAR(20) NOT NULL,
  
  -- Quantity & Value
  quantity_kg INT NOT NULL,
  unit_value_usd DECIMAL(10, 2) NOT NULL,
  line_total_usd DECIMAL(12, 2) NOT NULL,
  
  -- Production details (often missing)
  lot_number VARCHAR(50),
  production_date DATE,
  factory_code VARCHAR(50),
  
  -- Metadata
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  
  UNIQUE(shipment_id, line_number)
);

CREATE INDEX idx_line_items_shipment ON line_items(shipment_id);
CREATE INDEX idx_line_items_hts ON line_items(hts_code);
```

#### 3. entities

**Purpose**: Shipper, consignee, manufacturers, freight forwarders

```sql
CREATE TABLE entities (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  
  -- Core identity
  name VARCHAR(255) NOT NULL,
  name_normalized VARCHAR(255),  -- Normalized for matching
  entity_type VARCHAR(30) NOT NULL,  -- SHIPPER, CONSIGNEE, MANUFACTURER, HOLDING_COMPANY, FREIGHT_FORWARDER
  
  -- Registration
  jurisdiction VARCHAR(100),
  registration_number VARCHAR(100),
  registration_date DATE,
  registration_source VARCHAR(100),  -- Vietnam DPI, SAMR, HK Registry, etc.
  
  -- Contact
  address VARCHAR(500),
  address_normalized VARCHAR(500),
  phone VARCHAR(20),
  email VARCHAR(100),
  
  -- Business Details
  legal_structure VARCHAR(100),  -- LLC, Ltd., Corp., etc.
  tax_id VARCHAR(50),
  business_scope TEXT,
  
  -- Senzing
  senzing_entity_id INT,
  senzing_confidence DECIMAL(3, 2),  -- 0.0-1.0
  senzing_match_keys JSONB,  -- Array of match evidence
  
  -- Risk Assessment
  entity_risk_score INT,  -- 0-100
  entity_risk_level VARCHAR(20),  -- LOW, MEDIUM, HIGH, CRITICAL
  risk_flags JSONB,  -- Array of flags
  
  -- Beneficial Ownership
  beneficial_owner_name VARCHAR(255),
  beneficial_owner_id UUID REFERENCES entities(id),  -- Self-reference
  
  -- Prior Filings
  prior_cbp_filing_count INT DEFAULT 0,
  prior_cbp_filing_total_mt DECIMAL(12, 2) DEFAULT 0,
  prior_enforcement_actions INT DEFAULT 0,
  
  -- Metadata
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  data_sources JSONB,  -- OpenCorporates, SAMR, Vietnam DPI, etc.
  
  CONSTRAINT valid_type CHECK (entity_type IN ('SHIPPER', 'CONSIGNEE', 'MANUFACTURER', 'HOLDING_COMPANY', 'FREIGHT_FORWARDER', 'OTHER')),
  CONSTRAINT valid_risk_level CHECK (entity_risk_level IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL'))
);

CREATE INDEX idx_entities_name ON entities(name_normalized);
CREATE INDEX idx_entities_registration ON entities(registration_number, jurisdiction);
CREATE INDEX idx_entities_senzing ON entities(senzing_entity_id);
CREATE INDEX idx_entities_type ON entities(entity_type);
CREATE INDEX idx_entities_risk ON entities(entity_risk_score DESC);
```

#### 4. entity_relationships

**Purpose**: Ownership, directorship, freight forwarding links

```sql
CREATE TABLE entity_relationships (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  
  -- Relationship
  entity_a_id UUID NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
  entity_b_id UUID NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
  relationship_type VARCHAR(50) NOT NULL,  -- OWNED_BY, DIRECTOR_SHARED, FREIGHT_FORWARDED_BY
  
  -- Evidence
  confidence DECIMAL(3, 2),  -- 0.0-1.0 (from Senzing)
  match_keys JSONB,  -- Matching evidence (name, phone, director name, etc.)
  
  -- Metadata
  source VARCHAR(100),  -- SENZING, MANUAL, CORPORATE_REGISTRY
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  
  CONSTRAINT valid_relationship CHECK (relationship_type IN ('OWNED_BY', 'DIRECTOR_SHARED', 'FREIGHT_FORWARDED_BY', 'PRIOR_FILING'))
);

CREATE INDEX idx_entity_rel_a ON entity_relationships(entity_a_id);
CREATE INDEX idx_entity_rel_b ON entity_relationships(entity_b_id);
CREATE INDEX idx_entity_rel_type ON entity_relationships(relationship_type);
```

#### 5. corridors

**Purpose**: H1 corridor risk assessment

```sql
CREATE TABLE corridors (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  
  -- Corridor identity
  hts_6 VARCHAR(10) NOT NULL,
  origin_country VARCHAR(2) NOT NULL,
  intermediate_country VARCHAR(2),
  destination_country VARCHAR(2) NOT NULL,
  
  -- H1 Analysis
  risk_level VARCHAR(30),  -- LOW_RISK, MEDIUM_RISK, HIGH_RISK, CRITICAL_STRUCTURAL_RISK
  risk_score INT,
  
  -- Evidence
  china_export_growth_pct DECIMAL(6, 2),
  vietnam_import_growth_pct DECIMAL(6, 2),
  correlation_coefficient DECIMAL(3, 2),
  capacity_gap_mt INT,
  evasion_incentive_pct DECIMAL(6, 2),
  
  -- AD/CVD Cases
  ad_cvd_cases JSONB,  -- Array of case numbers, rates
  enforcement_history TEXT,
  
  -- Metadata
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  
  UNIQUE(hts_6, origin_country, intermediate_country, destination_country)
);

CREATE INDEX idx_corridors_hts ON corridors(hts_6);
CREATE INDEX idx_corridors_risk ON corridors(risk_level);
```

#### 6. referral_packages

**Purpose**: Final referral document output

```sql
CREATE TABLE referral_packages (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  
  package_id VARCHAR(50) NOT NULL UNIQUE,
  shipment_id UUID NOT NULL REFERENCES shipments(id) ON DELETE CASCADE,
  
  -- Assessment Results
  confidence_level VARCHAR(10),  -- LOW, MEDIUM, HIGH
  total_score INT,
  recommended_action VARCHAR(50),  -- EXAMINE_ON_ARRIVAL, REFER_TO_LAW_ENFORCEMENT
  
  -- Revenue Impact
  estimated_revenue_impact_usd DECIMAL(12, 2),
  
  -- Full Package
  package_json JSONB,  -- Complete Tables 3-1 through 3-14
  
  -- Generated Documents
  pdf_url VARCHAR(500),  -- Cloud Storage URL
  csv_url VARCHAR(500),
  
  -- Metadata
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  accepted_by_user_id UUID REFERENCES users(id),
  accepted_at TIMESTAMP,
  officer_notes TEXT,
  
  CONSTRAINT valid_action CHECK (recommended_action IN ('EXAMINE_ON_ARRIVAL', 'REFER_TO_LAW_ENFORCEMENT', 'STANDARD_PROCESSING'))
);

CREATE INDEX idx_referral_shipment ON referral_packages(shipment_id);
CREATE INDEX idx_referral_score ON referral_packages(total_score DESC);
```

#### 7. user_feedback

**Purpose**: Track officer actions and feedback

```sql
CREATE TABLE user_feedback (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  
  referral_package_id UUID NOT NULL REFERENCES referral_packages(id),
  user_id UUID NOT NULL REFERENCES users(id),
  
  -- Feedback
  action_taken VARCHAR(50),  -- ACCEPTED, MODIFIED, REJECTED
  confidence_adjustment INT,  -- -20 to +20 adjustment to score
  
  reason TEXT,
  outcome VARCHAR(50),  -- EXAM_SCHEDULED, GOODS_SEIZED, NO_ACTION, UNDER_REVIEW
  
  -- Evidence Collection
  examination_findings JSONB,  -- What CBP found during exam
  
  -- Metadata
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_feedback_package ON user_feedback(referral_package_id);
CREATE INDEX idx_feedback_user ON user_feedback(user_id);
```

#### 8. users

**Purpose**: CBP officer authentication and audit

```sql
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  
  email VARCHAR(100) NOT NULL UNIQUE,
  name VARCHAR(100) NOT NULL,
  badge_number VARCHAR(50),
  
  -- Identity
  auth_provider VARCHAR(50),  -- PIV, CAC, GSA_LOGIN
  auth_subject_id VARCHAR(255) UNIQUE,
  
  -- Permissions
  roles JSONB,  -- ['officer', 'supervisor', 'admin']
  
  -- Audit
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  last_login TIMESTAMP,
  is_active BOOLEAN DEFAULT TRUE
);

CREATE INDEX idx_users_email ON users(email);
```

### Queries

#### Find all shipments with score >= 80

```sql
SELECT s.bill_of_lading, s.shipper_id, s.h3_total_score, e.name AS shipper_name
FROM shipments s
LEFT JOIN entities e ON s.shipper_id = e.id
WHERE s.h3_total_score >= 80
ORDER BY s.h3_total_score DESC;
```

#### Find entities owned by a specific beneficial owner

```sql
WITH RECURSIVE entity_chain AS (
  SELECT id, name, beneficial_owner_id
  FROM entities
  WHERE registration_number = 'VN-0320869823'  -- Greenfield Vietnam
  
  UNION ALL
  
  SELECT e.id, e.name, e.beneficial_owner_id
  FROM entities e
  INNER JOIN entity_chain ec ON e.beneficial_owner_id = ec.id
)
SELECT * FROM entity_chain;
```

#### Find shipments with same shipper-consignee pattern

```sql
SELECT s1.bill_of_lading, s1.shipper_id, s1.consignee_id, COUNT(*) AS shipment_count
FROM shipments s1
GROUP BY s1.shipper_id, s1.consignee_id
HAVING COUNT(*) > 1
ORDER BY shipment_count DESC;
```

---

## Neo4j Graph Schema (Aura)

### Node Labels

#### :Entity

```cypher
(:Entity {
  id: UUID,
  name: String,
  entity_type: String,  -- SHIPPER, CONSIGNEE, MANUFACTURER, HOLDING_COMPANY
  jurisdiction: String,
  registration_number: String,
  registration_date: Date,
  senzing_entity_id: Integer,
  senzing_confidence: Float,
  entity_risk_score: Integer,
  entity_risk_level: String  -- LOW, MEDIUM, HIGH, CRITICAL
})
```

#### :Vessel

```cypher
(:Vessel {
  imo: String,
  name: String,
  flag: String,
  operator: String,
  callsign: String
})
```

#### :Port

```cypher
(:Port {
  unlocode: String,
  name: String,
  country: String
})
```

#### :HTS

```cypher
(:HTS {
  code: String,
  description: String,
  ad_rate: Float,
  cvd_rate: Float,
  section_232_rate: Float
})
```

#### :Shipment

```cypher
(:Shipment {
  bill_of_lading: String,
  manifest_id: String,
  hts_code: String,
  declared_origin: String,
  h3_score: Integer,
  h3_confidence_level: String,
  created_at: DateTime
})
```

#### :Corridor

```cypher
(:Corridor {
  hts_6: String,
  origin: String,
  destination: String,
  risk_level: String,
  risk_score: Integer
})
```

### Relationship Types

#### Ownership & Control

```cypher
(:Entity)-[:OWNED_BY {confidence: Float, match_keys: [String]}]->(:Entity)
(:Entity)-[:DIRECTOR_SHARED {director_name: String}]->(:Entity)
(:Entity)-[:BENEFICIAL_OWNER_OF]->(:Entity)
```

#### Trading & Logistics

```cypher
(:Entity)-[:SHIPPER_OF {shipment_id: String}]->(:Shipment)
(:Entity)-[:CONSIGNEE_OF {shipment_id: String}]->(:Shipment)
(:Entity)-[:FREIGHT_FORWARDED_BY]->(:Entity)
(:Shipment)-[:CARRIED_BY]->(:Vessel)
```

#### Routes & Locations

```cypher
(:Vessel)-[:CALLED_AT {dwell_days: Float, anomaly_ratio: Float}]->(:Port)
(:Shipment)-[:DECLARED_UNDER]->(:HTS)
(:Shipment)-[:PART_OF]->(:Corridor)
```

#### Enforcement

```cypher
(:Entity)-[:PRIOR_ENFORCEMENT {case_id: String, year: Integer}]->(:Entity)
(:Shipment)-[:FLAGGED_BY]->(:Corridor)
(:Entity)-[:LINKED_TO {confidence: Float}]->(:Entity)
```

### Key Queries

#### Find ownership chain (Greenfield example)

```cypher
MATCH path = (vn:Entity {registration_number: 'VN-0320869823'})-[:OWNED_BY*0..5]-(cn:Entity)
RETURN path, length(path) AS chain_depth
ORDER BY chain_depth DESC
LIMIT 1;
```

#### Why are two entities connected?

```cypher
MATCH path = (entity_a:Entity {name: 'Greenfield Industrial Trading Co., Ltd.'})
      -[relationship:OWNED_BY|DIRECTOR_SHARED|FREIGHT_FORWARDED_BY]-
      (entity_b:Entity {name: 'Guangdong Greenfield Aluminum Mfg. Co., Ltd.'})
RETURN path, type(relationship) AS relationship_type, relationship.confidence;
```

#### Find all high-risk shipments by a low-risk entity

```cypher
MATCH (entity:Entity {entity_risk_level: 'CRITICAL'})
      -[:SHIPPER_OF]->(shipment:Shipment)
WHERE shipment.h3_score >= 80
RETURN entity.name, shipment.bill_of_lading, shipment.h3_score
ORDER BY shipment.h3_score DESC;
```

#### Shipments in a high-risk corridor

```cypher
MATCH (corridor:Corridor {risk_level: 'CRITICAL_STRUCTURAL_RISK'})
      <-[:PART_OF]-(shipment:Shipment)
WHERE shipment.h3_score >= 70
RETURN shipment.bill_of_lading, shipment.h3_score, corridor.hts_6;
```

#### Full trace: Entity → Ownership → Shipment → Vessel → Port

```cypher
MATCH (entity:Entity {entity_risk_level: 'CRITICAL'})
      -[:SHIPPER_OF]->(shipment:Shipment)
      -[:CARRIED_BY]->(vessel:Vessel)
      -[:CALLED_AT {dwell_days: > 5}]->(port:Port)
WHERE shipment.h3_score >= 80
RETURN entity.name, shipment.bill_of_lading, vessel.name, port.name, port.country;
```

---

## Data Sync: PostgreSQL ↔ Neo4j

### Sync Strategy

1. **PostgreSQL is source of truth** for operational data
2. **Neo4j is denormalized graph** optimized for traversal queries
3. **Sync triggered** when entity relationships change

### Sync Code (api/core/database_sync.py)

```python
async def sync_entity_to_neo4j(entity_id: UUID, pg_session, neo4j_session):
    """
    When entity created/updated in PostgreSQL, sync to Neo4j.
    """
    
    # Fetch from PostgreSQL
    entity = await pg_session.get(Entity, entity_id)
    
    # Create Neo4j node
    neo4j_session.run("""
        MERGE (e:Entity {id: $id})
        SET e.name = $name,
            e.entity_type = $entity_type,
            e.senzing_entity_id = $senzing_entity_id,
            e.senzing_confidence = $senzing_confidence
        RETURN e
    """, {
        "id": str(entity_id),
        "name": entity.name,
        "entity_type": entity.entity_type,
        "senzing_entity_id": entity.senzing_entity_id,
        "senzing_confidence": entity.senzing_confidence,
    })
    
    # Sync relationships
    for rel in entity.relationships:
        neo4j_session.run("""
            MATCH (a:Entity {id: $entity_a_id})
            MATCH (b:Entity {id: $entity_b_id})
            MERGE (a)-[r:""" + rel.relationship_type + """ {confidence: $confidence}]->(b)
            RETURN r
        """, {
            "entity_a_id": str(rel.entity_a_id),
            "entity_b_id": str(rel.entity_b_id),
            "confidence": rel.confidence,
        })
```

---

## Performance Optimization

### PostgreSQL Indexes

Already defined above. Key ones:
- `idx_shipments_score` — Fast score-based filtering
- `idx_shipments_status` — Workflow filtering
- `idx_entities_senzing` — Entity lookup
- `idx_corridors_risk` — Corridor filtering

### Neo4j Indexes

```cypher
CREATE INDEX entity_id FOR (e:Entity) ON (e.id);
CREATE INDEX entity_senzing FOR (e:Entity) ON (e.senzing_entity_id);
CREATE INDEX shipment_score FOR (s:Shipment) ON (s.h3_score);
CREATE INDEX corridor_risk FOR (c:Corridor) ON (c.risk_level);
```

### Materialized Views (PostgreSQL)

For dashboard queries:

```sql
CREATE MATERIALIZED VIEW shipments_high_risk AS
SELECT 
  s.id,
  s.bill_of_lading,
  s.h3_total_score,
  s.h3_confidence_level,
  e.name AS shipper_name,
  c.risk_level AS corridor_risk,
  COUNT(DISTINCT rp.id) AS referral_count
FROM shipments s
LEFT JOIN entities e ON s.shipper_id = e.id
LEFT JOIN corridors c ON s.h1_corridor_id = c.id
LEFT JOIN referral_packages rp ON s.id = rp.shipment_id
WHERE s.h3_total_score >= 80
GROUP BY s.id, s.bill_of_lading, e.name, c.risk_level;

CREATE INDEX idx_high_risk_score ON shipments_high_risk(h3_total_score DESC);
```

---

## Backup & Recovery

### PostgreSQL Backup

```bash
# Daily backup to Cloud Storage
pg_dump -Fc postgresql://user:pass@neon.io/sentry_db > sentry_backup_$(date +%Y%m%d).dump

# Restore
pg_restore -d sentry_db sentry_backup_20260518.dump
```

### Neo4j Backup

```bash
# Via Neo4j Aura console or API
POST /v1/databases/sentry_db/backups/create

# Point-in-time recovery available
```

---

## Security & Compliance

- **Data at rest**: Encrypted with FIPS 140-2 (Cloud KMS)
- **Data in transit**: TLS 1.3 for all connections
- **Access control**: IAM roles (DHS 4300A compliant)
- **Audit logging**: All queries logged for compliance review
