# Risk Corridors API — Technical Reference

## Quick Start

### Installation
The Risk Corridors service is integrated into the main API. No additional installation required.

### Initialization
Database tables are automatically created on first API startup:
```python
from api.services.risk_corridors.db import init_risk_corridor_tables
init_risk_corridor_tables()  # Called automatically in routes.py
```

### Running Tests
```bash
# From repository root
python3 test_risk_corridors.py

# From api directory
python3 -m pytest services/risk_corridors/test_endpoints.py -v
```

---

## Endpoint Reference

### 1. GET /api/risk-corridors

**Purpose:** Retrieve aggregated risk corridors for dashboard view

**Query Parameters:**
```
industry_filter: str (optional)
  Format: comma-separated HTS codes
  Example: "7604,8541"
  Default: null (all industries)

time_period: str (optional)
  Format: number + 'd' suffix
  Valid: "7d", "14d", "30d"
  Default: "7d"
```

**Response Code:** 200 OK

**Response Schema:**
```json
{
  "corridors": [
    {
      "corridor_id": "HC-7604-VNUS-GDF",
      "hts_chapter": "76",
      "industry_segment": "Industrial Aluminum",
      "origin_country": "VN",
      "destination_country": "US",
      "supplier_entity": "Greenfield Industrial Trading Co., Ltd.",
      "shipment_count": 47,
      "aggregate_value_usd": 2350000,
      "yoy_volume_surge_pct": 312.5,
      "yoy_value_surge_pct": 287.3,
      "macro_volumetric_delta": {
        "status": "FLAGGED",
        "outbound_volume_manifest_tons": 1847,
        "estimated_domestic_capacity_tons": 450,
        "ratio": 4.1,
        "signal": "Outbound volume 4.1× estimated production capacity"
      },
      "ad_cvd_rate_pct": 374.15,
      "active_vessels": 8,
      "risk_level": "HIGH",
      "last_updated": "2026-05-20T14:32:00Z"
    }
  ],
  "summary": {
    "total_active_corridors": 24,
    "high_risk_count": 3,
    "medium_risk_count": 8,
    "aggregate_manifest_value": 45200000
  }
}
```

**cURL Example:**
```bash
curl -X GET "http://localhost:8000/api/risk-corridors?time_period=14d" \
  -H "accept: application/json"
```

---

### 2. GET /api/risk-corridors/{corridor_id}

**Purpose:** Retrieve detailed view of specific corridor with vessel activity and entity chain

**Path Parameters:**
```
corridor_id: str (required)
  Format: "HC-{hts_chapter}-{origin}{dest}-{entity_abbr}"
  Example: "HC-7604-VNUS-GDF"
```

**Query Parameters:**
```
include: str (optional)
  Format: comma-separated options
  Valid: "vessel_activity", "entity_chain", "ftz_events"
  Default: all included
```

**Response Codes:**
- 200 OK — Corridor found
- 404 Not Found — Corridor does not exist
- 400 Bad Request — Invalid corridor_id format

**Response Schema:**
```json
{
  "corridor": {
    "corridor_id": "HC-7604-VNUS-GDF",
    "hts_chapter": "76",
    "industry_segment": "Industrial Aluminum",
    "origin_country": "VN",
    "destination_country": "US",
    "supplier_entity": {
      "entity_id": "cord-gdf-vn-001",
      "name": "Greenfield Industrial Trading Co., Ltd.",
      "country": "VN",
      "risk_score": 91,
      "ofac_status": "CLEAN"
    },
    "active_vessels": [
      {
        "vessel_id": "IMO-9876543",
        "vessel_name": "MV Pacific Horizon",
        "flag_state": "PK",
        "current_port": "Port of Los Angeles",
        "status": "AT_BERTH",
        "port_call_history": [
          {
            "port_name": "Port of Guangzhou",
            "arrival_date": "2026-05-05T00:00:00Z",
            "departure_date": "2026-05-12T00:00:00Z",
            "dwell_days": 7,
            "baseline_dwell_days": 2.1,
            "anomaly": "3.3× baseline dwell"
          }
        ],
        "ftz_dwell_events": [
          {
            "ftz_code": "FTZ-80",
            "ftz_name": "Los Angeles Foreign Trade Zone",
            "entry_date": "2026-05-18T00:00:00Z",
            "estimated_exit": "2026-05-25T00:00:00Z",
            "dwell_days": 7,
            "status": "HIGH_RISK_DWELL"
          }
        ],
        "transshipment_risk_score": 78.0,
        "risk_level": "HIGH"
      }
    ]
  },
  "entity_chain": {
    "level_1": {
      "name": "Greenfield Industrial Trading Co., Ltd.",
      "country": "VN",
      "role": "Shipper"
    },
    "level_2": {
      "name": "Greenfield Global Metals Holdings Ltd.",
      "country": "HK",
      "role": "Holding Company"
    },
    "level_3": {
      "name": "Guangdong Greenfield Aluminum Mfg. Co., Ltd.",
      "country": "CN",
      "role": "Manufacturer"
    },
    "relationships": [
      {
        "from": "level_1",
        "to": "level_2",
        "relationship_type": "OWNED_BY",
        "confidence": 0.95
      }
    ]
  }
}
```

**cURL Example:**
```bash
curl -X GET "http://localhost:8000/api/risk-corridors/HC-7604-VNUS-GDF?include=vessel_activity,entity_chain" \
  -H "accept: application/json"
```

---

### 3. GET /api/ports/{port_code}/vessels-of-interest

**Purpose:** Get vessels of interest at specific US port with risk assessment

**Path Parameters:**
```
port_code: str (required)
  Valid: "USLA", "USLB", "USNJ", "USNY"
  USLA = Port of Los Angeles
  USLB = Port of Long Beach
  USNJ = Port of Newark
  USNY = Port of New York
```

**Query Parameters:**
```
time_window: str (optional)
  Format: number + 'd' suffix
  Valid: "7d", "14d", "30d"
  Default: "7d"

risk_filter: str (optional)
  Valid: "HIGH", "MEDIUM", "LOW"
  Default: null (all risk levels)
```

**Response Codes:**
- 200 OK — Success

**Response Schema:**
```json
{
  "port": "USLA",
  "port_name": "Port of Los Angeles",
  "vessels_of_interest": [
    {
      "vessel_id": "IMO-9876543",
      "vessel_name": "MV Pacific Horizon",
      "eta": "2026-05-20T16:00:00Z",
      "status": "INBOUND",
      "cargo_risk_level": "HIGH",
      "cargo_summary": {
        "primary_hts_chapter": "76",
        "industry_segment": "Industrial Aluminum",
        "total_manifest_value_usd": 500000,
        "manifest_count": 3
      },
      "route_anomalies": [
        "Port of Guangzhou dwell: 7 days (3.3× baseline)",
        "Transshipment routing via Hong Kong detected",
        "AIS signal gap: 18 hours near Sulu Strait"
      ],
      "recommended_actions": [
        "Enhanced Physical Examination on Arrival",
        "ISF Element 9 review (Stuffing location mismatch)",
        "OFAC check for flag state vessel agents"
      ]
    }
  ],
  "summary": {
    "total_vessels_at_port": 47,
    "vessels_of_interest": 3,
    "high_risk_count": 2,
    "exam_capacity_available": 5
  }
}
```

**cURL Example:**
```bash
curl -X GET "http://localhost:8000/api/ports/USLA/vessels-of-interest?risk_filter=HIGH&time_window=7d" \
  -H "accept: application/json"
```

---

### 4. GET /api/risk-corridors/{corridor_id}/timeline

**Purpose:** Get historical timeline of corridor activity for incident reconstruction

**Path Parameters:**
```
corridor_id: str (required)
  Format: "HC-{hts_chapter}-{origin}{dest}-{entity_abbr}"
  Example: "HC-7604-VNUS-GDF"
```

**Query Parameters:**
```
start_date: str (required)
  Format: ISO date "YYYY-MM-DD"
  Example: "2026-04-01"

end_date: str (required)
  Format: ISO date "YYYY-MM-DD"
  Example: "2026-05-20"

granularity: str (optional)
  Valid: "daily", "weekly", "monthly"
  Default: "daily"
```

**Response Codes:**
- 200 OK — Success
- 400 Bad Request — Invalid date range or format
- 404 Not Found — Corridor not found

**Response Schema:**
```json
{
  "corridor_id": "HC-7604-VNUS-GDF",
  "timeline_snapshots": [
    {
      "date": "2026-04-01",
      "shipment_count": 5,
      "aggregate_value_usd": 250000,
      "active_entities": [
        "Greenfield Industrial Trading Co., Ltd. (VN)"
      ],
      "active_vessels": [],
      "notable_events": []
    },
    {
      "date": "2026-04-15",
      "shipment_count": 8,
      "aggregate_value_usd": 400000,
      "active_entities": [
        "Greenfield Industrial Trading Co., Ltd. (VN)",
        "Greenfield Global Metals Holdings Ltd. (HK)"
      ],
      "active_vessels": ["MV Pacific Horizon"],
      "notable_events": [
        "New entity link detected: VN shipper → HK holding company"
      ]
    }
  ],
  "entity_evolution": {
    "entities_formed": 1,
    "entity_formations": [
      {
        "date": "2026-04-10",
        "entity_name": "Greenfield Global Metals Holdings Ltd.",
        "country": "HK",
        "first_shipment_after_formation": 5,
        "suspicious_timing": true
      }
    ]
  }
}
```

**cURL Example:**
```bash
curl -X GET "http://localhost:8000/api/risk-corridors/HC-7604-VNUS-GDF/timeline?start_date=2026-04-01&end_date=2026-05-20" \
  -H "accept: application/json"
```

---

### 5. POST /api/feedback/override

**Purpose:** Log officer feedback override for model retraining

**Request Body:**
```json
{
  "shipment_id": "MANIFEST-GRF-001",
  "corridor_id": "HC-7604-VNUS-GDF",
  "risk_score_original": 91.0,
  "override_action": "MARK_FALSE_POSITIVE",
  "justification_category": "VERIFIED_LABOR_STRIKE_PORT_DELAY",
  "justification_detail": "Port of Guangzhou labor action caused extended dwell; not transshipment.",
  "officer_id": "CBP-12345",
  "override_timestamp": "2026-05-20T15:45:00Z"
}
```

**Override Actions:**
- `MARK_FALSE_POSITIVE` — Flagged corridor is benign
- `MARK_TRUE_POSITIVE` — Unflagged shipment detected as high-risk
- `REQUEST_FOLLOW_UP` — Escalate for special investigation

**Justification Categories:**
- `VERIFIED_LABOR_STRIKE_PORT_DELAY` — Port strike/labor action
- `VERIFIED_CAPACITY_EXPANSION` — Legitimate capacity increase
- `VERIFIED_MISCLASSIFIED_VESSEL` — Wrong vessel identification
- `SUSPECTED_TRANSSHIPMENT` — Potential transshipment detected
- `SUSPECTED_EVASION_NETWORK` — Potential evasion network
- `OTHER` — Other justification

**Response Codes:**
- 201 Created — Override logged successfully
- 422 Unprocessable Entity — Invalid request data

**Response Schema:**
```json
{
  "override_id": "OVERRIDE-2026-05-20-001",
  "status": "LOGGED",
  "feedback_stored_for_model_retraining": true,
  "next_model_training_window": "2026-06-01"
}
```

**cURL Example:**
```bash
curl -X POST "http://localhost:8000/api/feedback/override" \
  -H "Content-Type: application/json" \
  -d '{
    "shipment_id": "MANIFEST-GRF-001",
    "corridor_id": "HC-7604-VNUS-GDF",
    "risk_score_original": 91.0,
    "override_action": "MARK_FALSE_POSITIVE",
    "justification_category": "VERIFIED_LABOR_STRIKE_PORT_DELAY",
    "justification_detail": "Port of Guangzhou labor action caused extended dwell; not transshipment.",
    "officer_id": "CBP-12345",
    "override_timestamp": "2026-05-20T15:45:00Z"
  }'
```

---

## Data Structures

### Corridor ID Format
```
HC-{hts_chapter}-{origin}{destination}-{entity_abbr}

Examples:
- HC-7604-VNUS-GDF
  - HTS: 7604 (Aluminum)
  - Route: Vietnam → USA
  - Entity: Greenfield

- HC-8541-MYUS-SOL
  - HTS: 8541 (Electronics)
  - Route: Malaysia → USA
  - Entity: SolarTech
```

### Risk Level Classification
```
HIGH    — risk_score >= 80
MEDIUM  — 60 <= risk_score < 80
LOW     — risk_score < 60
```

### Vessel Status Values
```
AT_BERTH  — Vessel currently at port
INBOUND   — Vessel en route to port
DEPARTED  — Vessel left port
UNDERWAY  — Vessel in transit
```

### FTZ Status Values
```
HIGH_RISK_DWELL  — Dwell exceeds risk threshold
NORMAL           — Dwell within acceptable range
CLEARED          — Goods cleared from FTZ
```

---

## Error Responses

### 400 Bad Request
```json
{
  "detail": "Invalid date format or range: start_date must be before end_date"
}
```

### 404 Not Found
```json
{
  "detail": "Corridor HC-9999-ZZZZ-XXX not found"
}
```

### 422 Unprocessable Entity
```json
{
  "detail": [
    {
      "loc": ["body", "override_action"],
      "msg": "value is not a valid enumeration member; permitted: 'MARK_FALSE_POSITIVE', 'MARK_TRUE_POSITIVE', 'REQUEST_FOLLOW_UP'",
      "type": "type_error.enum"
    }
  ]
}
```

### 500 Internal Server Error
```json
{
  "detail": "Internal server error",
  "debug": "SQLite error: database locked"
}
```

---

## Performance Characteristics

### Query Response Times (Measured)
| Query | Time | Rows |
|-------|------|------|
| GET /api/risk-corridors | ~50ms | 15 |
| GET /api/risk-corridors/{id} | ~15ms | 1 |
| GET /api/ports/{code}/vessels | ~20ms | 1-10 |
| GET /api/risk-corridors/{id}/timeline | ~30ms | 8 |
| POST /api/feedback/override | ~5ms | 1 |

### Database Indexes
```sql
CREATE INDEX idx_risk_score ON shipments(risk_score DESC);
CREATE INDEX idx_status ON shipments(status);
CREATE INDEX idx_shipper_country ON shipments(shipper_country);
CREATE INDEX idx_ftz_shipment ON ftz_events(shipment_id);
CREATE INDEX idx_vessel_id ON vessel_tracking(vessel_id);
CREATE INDEX idx_port_call_vessel ON port_call_history(vessel_id);
CREATE INDEX idx_feedback_shipment ON officer_feedback(shipment_id);
```

---

## Integration Examples

### Python Client
```python
import requests

# Get risk corridors
response = requests.get("http://localhost:8000/api/risk-corridors")
corridors = response.json()

# Get specific corridor
corridor_id = corridors['corridors'][0]['corridor_id']
detail = requests.get(f"http://localhost:8000/api/risk-corridors/{corridor_id}")

# Submit feedback
feedback = {
    "shipment_id": "MANIFEST-001",
    "corridor_id": corridor_id,
    "risk_score_original": 85.0,
    "override_action": "MARK_FALSE_POSITIVE",
    "justification_category": "VERIFIED_LABOR_STRIKE_PORT_DELAY",
    "justification_detail": "Port strike caused dwell extension",
    "officer_id": "CBP-12345",
    "override_timestamp": "2026-05-20T15:45:00Z"
}
response = requests.post("http://localhost:8000/api/feedback/override", json=feedback)
override = response.json()
```

### JavaScript/TypeScript Client
```typescript
// Fetch risk corridors
const response = await fetch('/api/risk-corridors');
const data = await response.json();

// Get corridor detail
const corridorId = data.corridors[0].corridor_id;
const detail = await fetch(`/api/risk-corridors/${corridorId}`);

// Submit feedback
const feedback = {
  shipment_id: "MANIFEST-001",
  corridor_id: corridorId,
  risk_score_original: 85,
  override_action: "MARK_FALSE_POSITIVE",
  justification_category: "VERIFIED_LABOR_STRIKE_PORT_DELAY",
  justification_detail: "Port strike caused dwell extension",
  officer_id: "CBP-12345",
  override_timestamp: new Date().toISOString()
};
const result = await fetch('/api/feedback/override', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(feedback)
});
```

---

## Troubleshooting

### Issue: "no such column: vessel_name"
**Cause:** Database schema mismatch with shipments table
**Solution:** Run `init_risk_corridor_tables()` to sync schemas

### Issue: 404 on corridor detail
**Cause:** Corridor ID format incorrect
**Solution:** Use format from index response: "HC-{hts}-{origin}{dest}-{abbr}"

### Issue: Empty timeline snapshots
**Cause:** No shipments in date range
**Solution:** Check date range covers actual shipment dates

### Issue: Slow queries on large dataset
**Cause:** Missing database indexes
**Solution:** Run `init_risk_corridor_tables()` to create indexes

---

## Monitoring & Logging

### Application Logs
```
api.services.risk_corridors - DEBUG - Risk Corridor Index queried
api.services.risk_corridors - DEBUG - 15 corridors returned
api.services.risk_corridors - DEBUG - Feedback override OVERRIDE-2026-05-20-001 logged
```

### Metrics to Track
- Request count per endpoint
- Response times (p50, p95, p99)
- 404/400 error rate
- Feedback override volume
- Database query performance

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-05-20 | Initial release with 5 endpoints |

---

## Support & Contribution

For issues, questions, or contributions:
1. Check the API_IMPLEMENTATION_REPORT.md for detailed architecture
2. Review test suite in api/services/risk_corridors/test_endpoints.py
3. Examine db.py for query logic

---

*Last Updated: 2026-05-20*  
*Status: Production Ready*
