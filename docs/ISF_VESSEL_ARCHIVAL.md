# ISF & Vessel Data Archival System

## Overview

The CBP-Sentry system maintains a persistent SQLite archive of ISF filings and vessel tracking data to build long-term intelligence patterns. Over time, this creates a **historical intelligence dataset** that enables:

- **Dwell time anomaly detection** (compare current vessel behavior vs. historical baseline)
- **Routing pattern discovery** (identify unusual routes, transshipment corridors)
- **Corridor risk assessment** (O→D risk profiles based on historical mismatch rates)
- **Vessel risk profiling** (flag "known anomalous" vessels by IMO)

## Architecture

### Database Schema (SQLite)

**File:** `/data/vessel_archive.db`

#### Vessels Table
Tracks unique vessels by IMO with static characteristics.

```sql
CREATE TABLE vessels (
    imo TEXT PRIMARY KEY,
    vessel_name TEXT NOT NULL,
    flag_country TEXT,
    vessel_type TEXT,
    length_m REAL,
    beam_m REAL,
    capacity_teu INTEGER,
    capacity_tonnes INTEGER,
    built_year INTEGER,
    first_seen TIMESTAMP,
    last_updated TIMESTAMP,
    metadata TEXT  -- JSON: mmsi, last_position, etc.
);
```

#### Port Calls Table
Historical port visits for each vessel (append-only).

```sql
CREATE TABLE port_calls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    imo TEXT NOT NULL,
    port_code TEXT NOT NULL,
    port_name TEXT,
    country TEXT,
    arrival_date TIMESTAMP,
    departure_date TIMESTAMP,
    dwell_days INTEGER,
    latitude REAL,
    longitude REAL,
    recorded_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (imo) REFERENCES vessels(imo)
);
```

#### ISF Filings Table
Every ISF filing (manifest) is archived with Element 9 analysis.

```sql
CREATE TABLE isf_filings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    manifest_id TEXT UNIQUE,
    shipper_name TEXT,
    shipper_country TEXT,
    consignee_name TEXT,
    consignee_country TEXT,
    vessel_imo TEXT,
    vessel_name TEXT,
    element9_declared TEXT,
    element9_actual TEXT,
    element9_mismatch BOOLEAN,
    element9_risk_level TEXT,  -- LOW, MEDIUM, HIGH
    filing_date TIMESTAMP,
    recorded_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_quality_score REAL,  -- 0-100%
    FOREIGN KEY (vessel_imo) REFERENCES vessels(imo)
);
```

#### Dwell Patterns Table
Aggregated statistics for vessel dwell times by port.

```sql
CREATE TABLE dwell_patterns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    imo TEXT NOT NULL,
    port_code TEXT NOT NULL,
    avg_dwell_days REAL,
    min_dwell_days INTEGER,
    max_dwell_days INTEGER,
    sample_count INTEGER,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (imo) REFERENCES vessels(imo)
);
```

**Auto-populated from port_calls** during anomaly detection runs.

#### Routing Patterns Table
Tracks common vessel routes.

```sql
CREATE TABLE routing_patterns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    imo TEXT NOT NULL,
    from_port TEXT NOT NULL,
    to_port TEXT NOT NULL,
    frequency INTEGER,  -- how many times observed
    avg_transit_days REAL,
    last_observed TIMESTAMP,
    FOREIGN KEY (imo) REFERENCES vessels(imo)
);
```

**Auto-populated** from consecutive port_calls sequences.

#### Anomalies Table
Detected anomalies and their resolution status.

```sql
CREATE TABLE anomalies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    imo TEXT NOT NULL,
    anomaly_type TEXT,  -- DWELL_UNUSUAL, ROUTE_UNUSUAL, etc.
    severity TEXT,      -- LOW, MEDIUM, HIGH
    description TEXT,
    detected_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolution_status TEXT DEFAULT 'OPEN',  -- OPEN, ACKNOWLEDGED, RESOLVED
    FOREIGN KEY (imo) REFERENCES vessels(imo)
);
```

## Integration Points

### 1. ISF Ingestion Workflow

When a manifest is uploaded:

```
Upload Manifest
    ↓
Parse ISF fields (shipper, consignee, vessel, Element 9)
    ↓
VesselEnrichmentService.enrich_manifest()
    ↓
Fetch vessel data from VesselFinder API
    ↓
Analyze Element 9 (declared vs actual origin)
    ↓
Archive to SQLite: ISFEnrichmentService.archive_isf_filing()
    ↓
Vessel archive: VesselArchiveDB.archive_vessel()
    ↓
Return to Case Viewer (display Element 9 risk)
```

### 2. Anomaly Detection Loop

Runs periodically (e.g., hourly) on recent filings:

```python
async def detect_anomalies_batch():
    # Get new filings from last hour
    filings = await db.get_filings(since=now - 1 hour)
    
    for filing in filings:
        vessel = await archive_db.get_vessel(filing.vessel_imo)
        if not vessel:
            continue
        
        # Compare current dwell vs historical avg
        anomalies = await archive_db.detect_anomalies(vessel.imo, vessel)
        
        # Log anomalies
        for anomaly in anomalies:
            await archive_db.db.execute(
                "INSERT INTO anomalies (...) VALUES (...)",
                (vessel.imo, anomaly.type, anomaly.severity, ...)
            )
        
        # Update dwell patterns
        await update_dwell_patterns(vessel)
        await update_routing_patterns(vessel)
```

### 3. Risk Scoring Integration

H2 (Vessel Anomaly) scoring uses archived patterns:

```python
def score_h2_vessel_anomaly(shipment):
    # Get dwell history for this vessel at this port
    dwell_history = archive_db.get_vessel_dwell_history(
        imo=shipment.vessel_imo,
        port=shipment.origin_port,
        days=90  # last 90 days
    )
    
    # Calculate baseline
    baseline_dwell = median(dwell_history)
    current_dwell = shipment.dwell_days
    
    # Score if anomalous
    if current_dwell > baseline_dwell * 5:
        return 12  # out of 35 for H2
    elif current_dwell > baseline_dwell * 3:
        return 8
    else:
        return 0
```

### 4. Case Viewer Display

Entity Chain tab shows historical vessel context:

```
Vessel: MV Pacific Horizon (IMO: 1234567)
├── Recent Dwell History
│   ├── Shanghai (CNSHA): 11.2 days (vs avg 2.8 days) ⚠️ 4x baseline
│   ├── Hong Kong (HKHKG): 3.1 days (normal)
│   └── Singapore (SGSIN): 2.4 days (normal)
├── Common Routes
│   ├── Shanghai → Singapore (12 observed, 4.2 days transit)
│   ├── Singapore → Newark (8 observed, 15.1 days transit)
│   └── Shanghai → Newark (5 observed) ⚠️ 1x observed (unusual)
└── Anomalies
    ├── DWELL_UNUSUAL [HIGH]: 11.2d at Shanghai vs 2.8d baseline
    └── ROUTE_UNUSUAL [MEDIUM]: Shanghai → Newark direct (typically via Singapore)
```

## APIs

### Archive Service Endpoints

#### Archive ISF Filing

```http
POST /api/isf/archive
Content-Type: application/json

{
  "manifest_id": "MFN-2026-001234",
  "isf_data": { ... complete ISFData object ... }
}

Response:
{
  "status": "archived",
  "vessel_imo": "1234567",
  "element_9_risk": "HIGH",
  "anomalies_detected": ["DWELL_UNUSUAL", "ROUTE_UNUSUAL"]
}
```

#### Get Vessel Risk Profile

```http
GET /api/isf/vessel/1234567/risk-profile

Response:
{
  "imo": "1234567",
  "vessel_name": "MV Pacific Horizon",
  "flag_country": "PA",
  "risk_level": "HIGH",
  "open_anomalies": 3,
  "element9_mismatches": 7,
  "dwell_anomalies": [
    {
      "port": "CNSHA",
      "avg_dwell_days": 2.8,
      "current_dwell_days": 11.2,
      "anomaly_ratio": 4.0
    }
  ],
  "suspicious_routes": ["Shanghai → Newark direct"],
  "last_seen": "2026-05-19T10:30:00Z"
}
```

#### Get Corridor Intelligence

```http
GET /api/isf/corridor/CN-US

Response:
{
  "corridor": "CN → US",
  "total_filings": 342,
  "element9_mismatches": 78,
  "mismatch_rate": 0.228,  // 22.8% mismatch rate
  "high_risk_vessels": [
    { "imo": "1234567", "incidents": 5 },
    { "imo": "9876543", "incidents": 3 }
  ],
  "transshipment_indicators": [
    { "port": "SGSIN", "frequency": 45 },
    { "port": "HKHKG", "frequency": 38 }
  ]
}
```

#### Detect Anomalies for Vessel

```http
POST /api/isf/vessel/1234567/detect-anomalies
Content-Type: application/json

{
  "current_vessel_data": { ... VesselInfo object ... }
}

Response:
{
  "anomalies": [
    {
      "type": "DWELL_UNUSUAL",
      "severity": "HIGH",
      "description": "Dwell at Shanghai: 11.2d vs avg 2.8d (4.0x baseline)",
      "evidence": {
        "current_dwell": 11.2,
        "historical_avg": 2.8,
        "samples": 15,
        "baseline_threshold": 14.0
      }
    }
  ]
}
```

#### Export Intelligence Report

```http
GET /api/isf/archive/export?format=json&period=30d

Response:
{
  "generated": "2026-05-19T10:30:00Z",
  "period_days": 30,
  "summary": {
    "total_vessels": 342,
    "total_port_calls": 1847,
    "total_isf_filings": 1203,
    "open_anomalies": 47,
    "high_risk_mismatches": 18
  },
  "top_risk_vessels": [
    { "imo": "1234567", "risk_score": 8.5 }
  ],
  "top_risk_corridors": [
    { "origin": "CN", "destination": "US", "mismatch_rate": 0.228 }
  ]
}
```

## Usage Examples

### In Python API Service

```python
from services.isf import ISFEnrichmentService, VesselArchiveDB

# Initialize
vessel_tracker = VesselTrackerClient(api_key=os.getenv("VESSELFINDER_API_KEY"))
isf_service = ISFEnrichmentService(vessel_tracker)
archive_db = VesselArchiveDB()

# During manifest upload
isf_response = await isf_service.enrich_manifest(request)
if isf_response.status == "success":
    # Archive for historical analysis
    await archive_db.archive_isf_filing(isf_response.isf_data)
    if isf_response.vessel_info:
        await archive_db.archive_vessel(isf_response.vessel_info)
```

### In Risk Scoring

```python
# When scoring H2 vessel anomaly
async def score_h2(shipment):
    vessel_risk = await archive_db.get_vessel_risk_profile(shipment.vessel_imo)
    
    if vessel_risk["open_anomalies"] > 2:
        return 12  # High dwell/route anomalies
    elif vessel_risk["element9_mismatches"] > 5:
        return 10  # Known transshipment vessel
    else:
        return 0
```

### In Case Viewer

```typescript
// Load vessel history when viewing case
const vesselRisk = await api.get(`/api/isf/vessel/${shipment.vessel_imo}/risk-profile`);

// Display in Entity Chain tab
<VesselHistoryPanel
  imo={shipment.vessel_imo}
  dwell_anomalies={vesselRisk.dwell_anomalies}
  suspicious_routes={vesselRisk.suspicious_routes}
  open_anomalies={vesselRisk.open_anomalies}
/>
```

## Data Lifecycle

### Retention Policy

- **Port Call Records:** Keep indefinitely (minimal space, high historical value)
- **ISF Filings:** Keep 5 years minimum (compliance requirement)
- **Anomalies:** Keep 2 years (actionable intelligence window)
- **Dwell Patterns:** Aggregate quarterly (space savings via aggregation)

### Archival Schedule

```
Every hour:
  → Detect anomalies in new filings
  → Log to anomalies table

Every 6 hours:
  → Calculate dwell patterns (average, min, max)
  → Update routing patterns (frequency, avg transit)

Every month:
  → Aggregate old port calls (keep raw for 30 days)
  → Export intelligence report for analyst review
  → Purge resolved anomalies > 2 years old
```

## Performance Considerations

### Indexing

Create indexes for fast lookups:

```sql
CREATE INDEX idx_port_calls_imo ON port_calls(imo);
CREATE INDEX idx_port_calls_port ON port_calls(port_code);
CREATE INDEX idx_isf_vessel_imo ON isf_filings(vessel_imo);
CREATE INDEX idx_isf_corridor ON isf_filings(shipper_country, consignee_country);
CREATE INDEX idx_anomalies_imo ON anomalies(imo, resolution_status);
```

### Query Examples

**Get dwell anomalies for a vessel (< 1ms with index):**
```sql
SELECT * FROM port_calls WHERE imo = '1234567' ORDER BY departure_date DESC LIMIT 10;
```

**Find all vessels with open HIGH-severity anomalies (< 10ms):**
```sql
SELECT DISTINCT imo FROM anomalies WHERE severity = 'HIGH' AND resolution_status = 'OPEN';
```

**Corridor mismatch rate (< 100ms for full year):**
```sql
SELECT COUNT(*) as total, COUNT(element9_mismatch) as mismatches
FROM isf_filings
WHERE shipper_country = 'CN' AND consignee_country = 'US' AND filing_date > date('now', '-1 year');
```

## Next Steps

1. **Initialize archive DB** when CBP-Sentry starts (one-time)
2. **Archive each ISF filing** during manifest ingestion (real-time)
3. **Run anomaly detection** hourly (background task)
4. **Display vessel context** in Case Viewer tabs
5. **Generate monthly intelligence reports** for analyst review
6. **Feed dwell/routing patterns** into H2 anomaly scorer

## Success Metrics

- **Archive completeness:** > 95% of ISF filings archived within 1 hour
- **Anomaly detection latency:** < 2 seconds per new filing
- **Query performance:** All profile/corridor queries < 500ms
- **Intelligence value:** Anomaly detection catch rate > 80% vs manual review
