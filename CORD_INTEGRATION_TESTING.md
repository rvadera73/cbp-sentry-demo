# CORD Integration API - Testing Guide

## Service Startup

The CORD Integration service is deployed as `sentry-cord-integration` on port 8004. It automatically:

1. **Initializes Senzing Engine** with SQLite backend at `/app/data/senzing.db`
2. **Loads CORD Data** from `/app/cord-data/*.jsonl` (244K+ entities)
3. **Augments with CBP Shipments** from data service (~1300 shipments)
4. **Builds Entity Index** with relationships for 3-level resolution

## Docker Compose Commands

```bash
# Start CORD integration service (with data + API)
docker compose up sentry-cord-integration sentry-data -d

# View CORD logs
docker compose logs -f sentry-cord-integration

# Check service health
curl http://localhost:8004/health

# Stop services
docker compose down
```

## API Endpoints

### Health Check

```bash
curl http://localhost:8004/health
```

Expected response:
```json
{
  "status": "healthy",
  "entity_count": 245000,
  "initialized_at": "2024-05-20T22:30:45.123456",
  "senzing_ready": true
}
```

### Entity Search

```bash
# Search by name
curl "http://localhost:8004/search?name=Greenfield&limit=5"

# Search by name + country
curl "http://localhost:8004/search?name=Greenfield&country=VN&limit=5"
```

Response format:
```json
[
  {
    "entity_id": "GLEIF:lei-14CKXV7T1M327VH4DM16",
    "name": "Greenfield Industrial Trading Co., Ltd.",
    "country": "VN",
    "data_source": "GLEIF",
    "confidence": 0.98
  }
]
```

### Entity Details

```bash
curl "http://localhost:8004/entity/GLEIF:lei-14CKXV7T1M327VH4DM16"
```

Response includes:
- Full entity record
- Parent company relationships
- ISF shipment links
- Confidence scores

### 3-Level Resolution (Shipper Chain)

```bash
curl -X POST http://localhost:8004/resolve \
  -H "Content-Type: application/json" \
  -d '{
    "shipper_name": "Greenfield Industrial Trading Co., Ltd.",
    "shipper_country": "VN",
    "consignee_name": "Gulf Coast Industrial",
    "consignee_country": "US"
  }'
```

Response includes:
- **Level 1**: Shipper entity (high confidence)
- **Level 2**: Parent company (medium confidence)
- **Level 3**: Ultimate owner (low-medium confidence)
- **OFAC Detection**: Boolean flag + entity if detected
- **Risk Scoring**: 0-100 score with indicators
- **ISF Records**: Linked CBP shipment data

Example response:
```json
{
  "status": "success",
  "chain": {
    "level_1": {
      "entity_id": "GLEIF:lei-greenfield-vn",
      "name": "Greenfield Industrial Trading Co., Ltd.",
      "country": "VN",
      "confidence": 0.98
    },
    "level_2": {
      "entity_id": "GLEIF:lei-greenfield-hk",
      "name": "Greenfield Global Metals Holdings Ltd.",
      "country": "HK",
      "confidence": 0.95
    },
    "level_3": {
      "entity_id": "GLEIF:lei-greenfield-cn",
      "name": "Guangdong Greenfield Aluminum Mfg. Co., Ltd.",
      "country": "CN",
      "confidence": 0.92
    }
  },
  "ofac": {
    "detected": false,
    "entity": null
  },
  "isf_records": [
    {
      "entity_id": "CBP-ISF:shipment-12345",
      "manifest_id": "MANI-001",
      "shipment_id": "SHIP-12345"
    }
  ],
  "scoring": {
    "confidence": 0.95,
    "risk_score": 65.0,
    "risk_level": "HIGH",
    "risk_indicator": "CHINA_ORIGIN_HIGH_RISK"
  }
}
```

### Relationship Explanation

```bash
curl -X POST "http://localhost:8004/why/GLEIF:lei-greenfield-vn/GLEIF:lei-greenfield-hk"
```

Response:
```json
{
  "entity_a_id": "GLEIF:lei-greenfield-vn",
  "entity_b_id": "GLEIF:lei-greenfield-hk",
  "relationship_type": "OWNED_BY",
  "explanation": "Link between entities",
  "evidence": [
    {
      "type": "OWNERSHIP_STAKE",
      "details": "Greenfield VN is 100% owned by Greenfield HK"
    }
  ],
  "confidence": 0.95
}
```

## API Gateway Proxy Endpoints

When running full stack, access CORD via API gateway:

```bash
# Health check
curl http://localhost:8000/api/cord/health

# Search
curl "http://localhost:8000/api/cord/search?name=Greenfield&country=VN"

# Resolve
curl -X POST http://localhost:8000/api/cord/resolve \
  -d "shipper_name=Greenfield&shipper_country=VN"

# Entity details
curl "http://localhost:8000/api/cord/entity/{entity_id}"

# Relationship explanation
curl -X POST "http://localhost:8000/api/cord/why/{id_a}/{id_b}"
```

## Startup Sequence

When service starts, observe logs in this order:

1. **Senzing Engine Initialize** (5-10 seconds)
   ```
   ✓ Senzing engine initialized
   ```

2. **CORD Data Load** (60-120 seconds for 244K records)
   ```
   Loading CORD data into Senzing engine...
   Processed 1,000 records
   Processed 50,000 records
   ...
   CORD load result: {status: success, total_records: 244000, ...}
   ```

3. **CBP Augmentation** (2-5 seconds)
   ```
   Augmenting with CBP shipment data...
   CBP augmentation result: {status: success, shipment_count: 1300, cbp_shipper_records: 1300, cbp_isf_records: 1250}
   ```

4. **Ready for Requests** (immediate)
   ```
   ✓ Senzing engine ready with 245,300 entities
   ```

## Performance Expectations

- **Search**: < 100ms for indexed queries
- **Entity Lookup**: < 50ms by entity_id
- **3-Level Resolution**: 100-300ms (database lookups)
- **Why Explanation**: 50-100ms
- **Concurrent Requests**: 100+ sustained

## Database

SQLite database persists at `/app/data/senzing.db`:

```bash
# Inspect database
sqlite3 /app/data/senzing.db "SELECT COUNT(*) FROM senzing_entities;"

# View table schema
sqlite3 /app/data/senzing.db ".schema senzing_entities"

# Query entities
sqlite3 /app/data/senzing.db "SELECT name_primary, country, confidence FROM senzing_entities LIMIT 10;"

# Count by data source
sqlite3 /app/data/senzing.db "SELECT data_source, COUNT(*) FROM senzing_entities GROUP BY data_source;"
```

## Risk Scoring Logic

Risk scores are calculated as:

1. **Base Score**: 50 (neutral)
2. **Jurisdiction Adjustments**:
   - China (CN): +30
   - Iran/Syria/DPRK: +35
   - Russia/Belarus: +25
   - Southeast Asia (VN/TH/MY): +15
3. **Confidence Penalty** (if < 0.7): +20
4. **Complex Ownership** (3-level chain): +5
5. **OFAC Override**: 95 (critical)

Final score normalized to 0-100.

Risk levels:
- **CRITICAL** (80-100): Immediate escalation required
- **HIGH** (60-80): Review before release
- **MEDIUM** (40-60): Monitor and validate
- **LOW** (0-40): Standard processing

## Troubleshooting

### Service won't start
1. Check CORD data directory exists: `ls -la /app/cord-data/*.jsonl`
2. Check data service is running: `curl http://localhost:8005/health`
3. Check logs: `docker logs sentry-cord-integration`

### High memory usage
- Normal: 500MB-1GB for 245K entities in SQLite
- If > 2GB: Check for memory leak, restart service

### Slow queries
1. Verify entity count: `curl http://localhost:8004/health`
2. Check search index: `sqlite3 /app/data/senzing.db ".indices"`
3. Analyze slow query: Add EXPLAIN QUERY PLAN

### OFAC not detected
1. Verify OFAC records loaded: `sqlite3 /app/data/senzing.db "SELECT COUNT(*) FROM senzing_entities WHERE data_source='OFAC';"`
2. Check entity name matches exactly (FTS search)
3. Try exact country code in search

## Verification Checklist

- [ ] Service starts without errors
- [ ] Entity count > 240,000
- [ ] Health endpoint responds
- [ ] Search returns results (Greenfield, etc.)
- [ ] 3-level resolution completes in < 500ms
- [ ] OFAC detection works
- [ ] ISF records are linked
- [ ] Risk scores are within 0-100 range
- [ ] Proxy endpoints work from API gateway
- [ ] Database persists across restarts

## Performance Optimization

For production:
1. Add database indexes on `entity_id`, `name_primary`, `country`
2. Enable SQLite query caching
3. Increase connection pool size
4. Consider Senzing SDK full installation instead of SQLite wrapper
5. Monitor memory usage under load

Example index creation:
```sql
CREATE INDEX idx_entity_id ON senzing_entities(entity_id);
CREATE INDEX idx_name ON senzing_entities(name_primary);
CREATE INDEX idx_country ON senzing_entities(country);
CREATE INDEX idx_data_source ON senzing_entities(data_source);
```
