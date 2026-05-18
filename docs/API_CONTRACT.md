# API Contract — OpenAPI Specification

## Overview

All Sentry API routes are cloud-agnostic (no GCP/AWS specific code in business logic). Routes accept JSON, return JSON. Full OpenAPI 3.0 spec provided below.

**Base URL**: `http://localhost:8000` (local) or `https://api.sentry.cbp.dev` (production)

**Authentication**: Bearer token (PIV/CAC via Cloud Identity)

---

## OpenAPI 3.0 Specification

```yaml
openapi: 3.0.0
info:
  title: Sentry API
  version: 1.0.0
  description: Illegal Transshipment Detection System
  contact:
    name: CBP Sentry Team
servers:
  - url: http://localhost:8000
    description: Local development
  - url: https://api.sentry.cbp.dev
    description: Production
paths:
  /health:
    get:
      summary: Health check
      tags:
        - Health
      responses:
        '200':
          description: Service is healthy
          content:
            application/json:
              schema:
                type: object
                properties:
                  status:
                    type: string
                    enum: [ok, degraded]
                  timestamp:
                    type: string
                    format: date-time
```

---

## Core Endpoints

### 1. POST /api/ingest/manifest

**Purpose**: Upload CBP manifest (Excel), validate, extract data

**Request**

```json
{
  "file": "binary",
  "filename": "manifest_2026_05_18.xlsx",
  "uploaded_by": "officer@cbp.local"
}
```

**Response** (201 Created)

```json
{
  "shipment_id": "SHP-001",
  "manifest_id": "MF-2026-001",
  "bill_of_lading": "SAMPLE-BOL-2026-001",
  "status": "RECEIVED",
  "parsing_errors": [],
  "warnings": [
    "HTS code 7604.10.1000 subject to 374% AD/CVD from China"
  ],
  "extracted_fields": {
    "shipper_name": "Greenfield Industrial Trading Co., Ltd.",
    "shipper_country": "VN",
    "consignee_name": "SunPath Energy Distributors LLC",
    "hts_code": "7604.10.1000",
    "declared_country_of_origin": "VN",
    "declared_value_usd": 72030,
    "total_weight_kg": 26200,
    "port_of_lading": "VNSGN",
    "port_of_unlading": "USLAX"
  },
  "created_at": "2026-04-28T14:32:00Z"
}
```

**Error Responses**

```json
{
  "status": 400,
  "error": "INVALID_FILE_FORMAT",
  "detail": "File must be .xlsx or .xls"
}
```

```json
{
  "status": 400,
  "error": "MISSING_REQUIRED_FIELDS",
  "missing_fields": ["shipper_name", "hts_code", "declared_value_usd"]
}
```

---

### 2. POST /api/er/load

**Purpose**: Trigger entity resolution (Senzing) + Neo4j graph build

**Request**

```json
{
  "shipment_id": "SHP-001"
}
```

**Response** (200 OK)

```json
{
  "shipment_id": "SHP-001",
  "er_job_id": "JOB-2026-0514-001",
  "status": "RUNNING",
  "entities_resolved": 6,
  "entities": [
    {
      "entity_id": 1001,
      "entity_name": "Greenfield Industrial Trading Co., Ltd.",
      "entity_type": "SHIPPER",
      "senzing_confidence": 0.91,
      "jurisdiction": "Vietnam",
      "risk_level": "HIGH",
      "matching_evidence": [
        "NAME_ORG: Greenfield transliteration match",
        "REGISTERED_ADDRESS: Freight forwarder office"
      ]
    },
    {
      "entity_id": 1003,
      "entity_name": "Guangdong Greenfield Aluminum Mfg. Co., Ltd.",
      "entity_type": "MANUFACTURER",
      "senzing_confidence": 0.98,
      "jurisdiction": "China",
      "risk_level": "CRITICAL",
      "matching_evidence": [
        "DIRECTOR_NAME: Shared across tiers",
        "PRIOR_FILINGS: 18 CBP filings on HTS 7604.10"
      ],
      "prior_cbp_filings": 18
    }
  ],
  "entity_relationships": [
    {
      "entity_a_id": 1001,
      "entity_b_id": 1002,
      "relationship_type": "OWNED_BY",
      "confidence": 0.87,
      "evidence": "Shared beneficial owner; same freight forwarder"
    },
    {
      "entity_a_id": 1002,
      "entity_b_id": 1003,
      "relationship_type": "OWNED_BY",
      "confidence": 0.98,
      "evidence": "Director name match (Wang Haohui); registered office"
    }
  ],
  "neo4j_graph_url": "/api/graph/shipment/SHP-001",
  "estimated_completion": "2026-04-28T14:45:00Z"
}
```

---

### 3. GET /api/er/why/{entity_a}/{entity_b}

**Purpose**: Explain why two entities are connected (Senzing graph)

**Request**

```
GET /api/er/why/1001/1003?shipment_id=SHP-001
```

**Response** (200 OK)

```json
{
  "entity_a": {
    "id": 1001,
    "name": "Greenfield Industrial Trading Co., Ltd.",
    "country": "VN"
  },
  "entity_b": {
    "id": 1003,
    "name": "Guangdong Greenfield Aluminum Mfg. Co., Ltd.",
    "country": "CN"
  },
  "connection_path": [
    {
      "step": 1,
      "entity_id": 1001,
      "entity_name": "Greenfield Industrial Trading Co., Ltd.",
      "relationship": "OWNED_BY"
    },
    {
      "step": 2,
      "entity_id": 1002,
      "entity_name": "Greenfield Global Metals Holdings Ltd.",
      "relationship": "OWNED_BY"
    },
    {
      "step": 3,
      "entity_id": 1003,
      "entity_name": "Guangdong Greenfield Aluminum Mfg. Co., Ltd.",
      "relationship": "(final)"
    }
  ],
  "connection_depth": 2,
  "total_confidence": 0.91,
  "explanation": "Greenfield Vietnam (VN shipper) is owned via Hong Kong holding company by Guangdong Greenfield Aluminum (CN manufacturer). Shared beneficial owner (Wang Haohui) and director linkage confidence: 0.91.",
  "evidence": [
    "Director name: Nguyen Van Hung (VN proxy) ≈ Wang Haohui (CN registered)",
    "Phone: Foshan area code (0757) in multiple registrations",
    "Shared freight forwarder: Saigon Global Logistics JSC across all tiers",
    "Prior CBP filings: 18 shipments from CN entity on same HTS code"
  ]
}
```

---

### 4. POST /api/score/{shipment_id}

**Purpose**: Run 4-tier ML scoring (H1 + H2 + H3 components)

**Request**

```json
{
  "shipment_id": "SHP-001",
  "force_rescore": false
}
```

**Response** (200 OK)

```json
{
  "shipment_id": "SHP-001",
  "score_job_id": "JOB-2026-0514-002",
  "h1_corridor_risk": {
    "corridor_id": "760410_CN_VN_US",
    "risk_level": "CRITICAL_STRUCTURAL_RISK",
    "risk_score": 95,
    "evidence": {
      "china_billet_export_spike": "5.5× (2017-2023)",
      "vietnam_extrusion_correlation": 0.94,
      "tariff_incentive": "390.65% duty if Chinese vs 6.5% if Vietnamese"
    }
  },
  "h2_pre_intelligence": {
    "isf_element_9_contradiction": true,
    "stuffing_location": "Nansha Terminal, Guangzhou",
    "declared_origin": "Vietnam",
    "ais_dwell_days": 11.2,
    "ais_dwell_baseline": 2.1,
    "ais_anomaly_ratio": 5.33,
    "ais_percentile": 99
  },
  "h3_scoring_breakdown": {
    "total_score": 91,
    "confidence_level": "HIGH",
    "components": [
      {
        "tier": 1,
        "component": "Party Profile Risk",
        "score": 15,
        "max": 15,
        "basis": "Senzing resolved shipper to Chinese parent (confidence 0.91)"
      },
      {
        "tier": 2,
        "component": "Routing Consistency",
        "score": 14,
        "max": 15,
        "basis": "AIS dwell 11.2 days (5.3× baseline, 99th percentile)"
      },
      {
        "tier": 3,
        "component": "Commodity Sensitivity",
        "score": 14,
        "max": 15,
        "basis": "HTS 7604.10 subject to 374.15% AD/CVD from China"
      },
      {
        "tier": 3,
        "component": "Historical Pattern Anomaly",
        "score": 12,
        "max": 15,
        "basis": "6-month origin shift (MY→TH→VN); volume spike post-AD/CVD"
      },
      {
        "tier": 4,
        "component": "Origin Documentation Gap",
        "score": 23,
        "max": 25,
        "basis": "No production records, QC docs, factory verification (Bayesian P(fraud)=0.91)"
      },
      {
        "tier": 4,
        "component": "Time Sensitivity",
        "score": 13,
        "max": 15,
        "basis": "In 72-hour enforcement window; evidence complete"
      }
    ]
  },
  "recommended_action": "EXAMINE_ON_ARRIVAL",
  "estimated_revenue_impact_usd": 2100000,
  "scoring_completed_at": "2026-04-28T14:47:00Z"
}
```

---

### 5. POST /api/referral/{shipment_id}/generate

**Purpose**: Generate enforcement-ready referral package (Tables 3-1 to 3-14)

**Request**

```json
{
  "shipment_id": "SHP-001",
  "generate_pdf": true,
  "include_what_if_scenarios": true
}
```

**Response** (202 Accepted)

```json
{
  "package_id": "SENTRY-2026-001",
  "shipment_id": "SHP-001",
  "job_id": "JOB-2026-0514-003",
  "status": "PROCESSING",
  "estimated_completion": "2026-04-28T14:50:00Z",
  "polling_url": "/api/referral/SENTRY-2026-001/status"
}
```

**Polling Response** (GET /api/referral/{package_id}/status)

```json
{
  "package_id": "SENTRY-2026-001",
  "status": "COMPLETED",
  "completed_at": "2026-04-28T14:49:30Z",
  "output_urls": {
    "json": "/api/referral/SENTRY-2026-001/package.json",
    "pdf": "/api/referral/SENTRY-2026-001/package.pdf",
    "csv": "/api/referral/SENTRY-2026-001/tables.csv"
  }
}
```

---

### 6. GET /api/referral/{package_id}

**Purpose**: Retrieve full referral package

**Request**

```
GET /api/referral/SENTRY-2026-001?format=json
```

**Response** (200 OK)

See **REFERRAL_PACKAGE.md** for full JSON structure (Tables 3-1 through 3-14).

---

### 7. GET /api/graph/shipment/{shipment_id}

**Purpose**: Return Neo4j entity graph for visualization

**Request**

```
GET /api/graph/shipment/SHP-001?depth=2
```

**Response** (200 OK)

```json
{
  "shipment_id": "SHP-001",
  "nodes": [
    {
      "id": "entity-1001",
      "label": "Greenfield Industrial Trading Co., Ltd.",
      "type": "SHIPPER",
      "country": "VN",
      "risk_level": "HIGH",
      "senzing_confidence": 0.91
    },
    {
      "id": "entity-1002",
      "label": "Greenfield Global Metals Holdings Ltd.",
      "type": "HOLDING_COMPANY",
      "country": "HK",
      "risk_level": "HIGH",
      "senzing_confidence": 0.87
    },
    {
      "id": "entity-1003",
      "label": "Guangdong Greenfield Aluminum Mfg. Co., Ltd.",
      "type": "MANUFACTURER",
      "country": "CN",
      "risk_level": "CRITICAL",
      "senzing_confidence": 0.98,
      "prior_cbp_filings": 18
    },
    {
      "id": "vessel-9834521",
      "label": "MV Pacific Horizon",
      "type": "VESSEL",
      "imo": "9834521"
    },
    {
      "id": "port-cnggz",
      "label": "Guangzhou (Nansha)",
      "type": "PORT",
      "country": "CN",
      "dwell_days": 11.2,
      "anomaly_flag": true
    }
  ],
  "links": [
    {
      "source": "entity-1001",
      "target": "entity-1002",
      "relationship": "OWNED_BY",
      "confidence": 0.87,
      "label": "Beneficial owner"
    },
    {
      "source": "entity-1002",
      "target": "entity-1003",
      "relationship": "OWNED_BY",
      "confidence": 0.98,
      "label": "Ownership chain"
    },
    {
      "source": "entity-1001",
      "target": "vessel-9834521",
      "relationship": "SHIPPER_OF",
      "label": "Shipped via"
    },
    {
      "source": "vessel-9834521",
      "target": "port-cnggz",
      "relationship": "CALLED_AT",
      "dwell_days": 11.2,
      "label": "Dwell: 11.2 days"
    }
  ]
}
```

---

### 8. GET /api/shipments (Dashboard Query)

**Purpose**: List shipments with filtering and sorting

**Request**

```
GET /api/shipments?status=RECEIVED&score_min=80&score_max=100&limit=50&offset=0
```

**Response** (200 OK)

```json
{
  "total": 247,
  "limit": 50,
  "offset": 0,
  "shipments": [
    {
      "shipment_id": "SHP-001",
      "bill_of_lading": "SAMPLE-BOL-2026-001",
      "shipper_name": "Greenfield Industrial Trading Co., Ltd.",
      "h3_score": 91,
      "confidence_level": "HIGH",
      "status": "ASSESSED",
      "recommended_action": "EXAMINE_ON_ARRIVAL",
      "created_at": "2026-04-28T14:32:00Z",
      "referral_package_id": "SENTRY-2026-001"
    }
  ]
}
```

---

### 9. POST /api/shipments/{shipment_id}/feedback

**Purpose**: Log officer action + feedback

**Request**

```json
{
  "action_taken": "ACCEPTED",
  "confidence_adjustment": 0,
  "reason": "Officer examined cargo, confirms Chinese origin",
  "outcome": "GOODS_SEIZED",
  "examination_findings": {
    "origin_verified": "China",
    "markings_discrepancy": "Product markings indicate Chinese origin, not Vietnamese",
    "goods_seized": true,
    "estimated_value": 72030
  }
}
```

**Response** (201 Created)

```json
{
  "feedback_id": "FB-2026-0514-001",
  "shipment_id": "SHP-001",
  "action": "ACCEPTED",
  "outcome": "GOODS_SEIZED",
  "recorded_at": "2026-04-28T16:30:00Z",
  "user": "officer@cbp.local"
}
```

---

## Error Handling

### Standard Error Response

```json
{
  "error": "ERROR_CODE",
  "message": "Human-readable error message",
  "status": 400,
  "request_id": "REQ-2026-0514-001",
  "timestamp": "2026-04-28T14:32:00Z"
}
```

### Common Error Codes

| Code | HTTP Status | Meaning |
|------|-------------|---------|
| `INVALID_FILE_FORMAT` | 400 | File is not Excel or CSV |
| `MISSING_REQUIRED_FIELDS` | 400 | Manifest missing required columns |
| `SHIPMENT_NOT_FOUND` | 404 | Shipment ID doesn't exist |
| `SENZING_ERROR` | 503 | Entity resolution service unavailable |
| `DATABASE_ERROR` | 500 | PostgreSQL or Neo4j error |
| `UNAUTHORIZED` | 401 | Missing/invalid auth token |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests |

---

## Authentication

### Bearer Token (PIV/CAC)

```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

Tokens issued by GSA Cloud Identity or agency PIV system. Includes:
- `sub` (subject): Officer email (officer@cbp.local)
- `badge_number`: CBP badge number
- `roles`: ['officer', 'supervisor', 'admin']
- `exp`: Expiration (24 hours)

---

## Rate Limiting

```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 987
X-RateLimit-Reset: 1714347600
```

Limits:
- **Manifest upload**: 100/hour per user
- **Scoring**: 1000/hour per user
- **Graph queries**: 500/hour per user

---

## Versioning

API version in URL: `/api/v1/...` (current stable)

Backward compatibility guaranteed within major version.

---

## WebSocket (Real-Time Updates)

**Connect**: `ws://localhost:8000/api/ws/{shipment_id}`

**Messages**:

```json
{
  "event": "SCORING_STARTED",
  "shipment_id": "SHP-001",
  "timestamp": "2026-04-28T14:32:00Z"
}
```

```json
{
  "event": "SCORE_UPDATED",
  "shipment_id": "SHP-001",
  "score": 91,
  "confidence": "HIGH",
  "timestamp": "2026-04-28T14:47:00Z"
}
```

```json
{
  "event": "REFERRAL_READY",
  "shipment_id": "SHP-001",
  "package_id": "SENTRY-2026-001",
  "timestamp": "2026-04-28T14:50:00Z"
}
```

---

## SDK / Client Libraries

### Python (FastAPI client)

```python
from sentry_client import SentryAPI

client = SentryAPI(base_url="https://api.sentry.cbp.dev", token=token)

# Upload manifest
shipment = await client.ingest_manifest(file_path)

# Score
score = await client.score(shipment.shipment_id)

# Get referral
package = await client.get_referral(shipment.shipment_id)
```

### TypeScript (React frontend)

```typescript
import { SentryAPI } from '@sentry-ui/api-client';

const api = new SentryAPI({
  baseURL: 'https://api.sentry.cbp.dev',
  token: authToken,
});

const shipment = await api.ingestManifest(file);
const score = await api.score(shipment.shipment_id);
const pkg = await api.getReferral(shipment.shipment_id);
```

---

## Testing

### Mock Server (for E2E tests)

```bash
npm run test:api:mock
# Starts mock server on localhost:8001 with fixtures
```

### Integration Tests

```bash
npm run test:api:integration
# Runs against local Docker Compose stack
```
