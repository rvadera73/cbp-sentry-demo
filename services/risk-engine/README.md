# Precise Risk Engine API

Flask microservice for CBP illegal transshipment risk scoring.

## Overview

Precise Risk Engine API is a config-driven risk scoring microservice that calculates risk scores based on 7 factors, applies 3 decision gates, and enforces 8 conditional rules.

## Architecture

- **Framework**: Flask 2.3.3
- **Port**: 8004
- **Database**: PostgreSQL (risk_scoring schema)
- **Cache**: Redis
- **Configuration**: YAML-based (cbp.yaml)

## Project Structure

```
services/risk-engine/
├── app.py                    # Flask app factory
├── wsgi.py                  # WSGI entry point for gunicorn
├── routes/
│   ├── __init__.py
│   ├── scoring.py           # Scoring endpoints (/api/v1/scoring)
│   ├── rules.py             # Rules management (/api/v1/rules)
│   ├── feedback.py          # Feedback collection (/api/v1/feedback)
│   └── metrics.py           # Metrics and monitoring (/api/v1/metrics)
├── models/
│   ├── __init__.py
│   └── risk_model.py        # Generic PreciseRiskModel
├── services/
│   ├── __init__.py          # Cache and DB initialization
│   ├── cache_service.py     # Redis caching utilities
│   ├── database.py          # PostgreSQL utilities
│   └── drift_detection.py   # Model drift monitoring
├── config/
│   └── cbp.yaml             # Risk model configuration
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   └── test_routes.py       # Route unit tests
├── requirements.txt
├── Dockerfile
└── README.md
```

## Configuration

### Environment Variables

```bash
FLASK_ENV=development|testing|production
PORT=8004
DB_HOST=localhost
DB_PORT=5432
DB_NAME=cbp_sentry
DB_USER=postgres
DB_PASSWORD=password
REDIS_HOST=localhost
REDIS_PORT=6379
MODEL_CONFIG_PATH=/path/to/cbp.yaml
```

### Model Configuration (cbp.yaml)

The model is fully configured via YAML:

- **7 Factors**: Entity characteristics that influence risk
  - entity_risk_score
  - historical_violation_count
  - connectivity_score
  - trade_frequency_anomaly
  - sanctioned_status
  - jurisdiction_risk
  - product_sensitivity

- **3 Gates**: Threshold-based decision points
  - sanctioned_party_gate (factor: sanctioned_status, threshold: 50)
  - violation_history_gate (factor: historical_violation_count, threshold: 30)
  - trade_anomaly_gate (factor: trade_frequency_anomaly, threshold: 60)

- **8 Rules**: Conditional logic for risk escalation
  - rule_01_high_volume_low_history
  - rule_02_connectivity_violation_pattern
  - rule_03_sanctioned_adjacent
  - rule_04_product_jurisdiction_combo
  - rule_05_entity_network_cluster
  - rule_06_rapid_entity_changes
  - rule_07_anomalous_product_mix
  - rule_08_jurisdiction_historical_match

## API Endpoints

### Health Check
```
GET /health
```

### Scoring
```
POST /api/v1/scoring/score
POST /api/v1/scoring/batch-score
GET /api/v1/scoring/score/<entity_id>
DELETE /api/v1/scoring/score/<entity_id>
POST /api/v1/scoring/clear-cache
```

### Rules
```
GET /api/v1/rules/list
GET /api/v1/rules/<rule_name>
POST /api/v1/rules/test
GET /api/v1/rules/severity/<severity_level>
```

### Feedback
```
POST /api/v1/feedback/submit
GET /api/v1/feedback/list
GET /api/v1/feedback/<feedback_id>
POST /api/v1/feedback/analyze
PATCH /api/v1/feedback/<feedback_id>/update
```

### Metrics
```
GET /api/v1/metrics/summary
GET /api/v1/metrics/model-info
GET /api/v1/metrics/factors
GET /api/v1/metrics/gates
GET /api/v1/metrics/drift-report
POST /api/v1/metrics/performance
POST /api/v1/metrics/reset
```

## Installation

### Local Development

```bash
cd services/risk-engine

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the app
python wsgi.py
```

The app will be available at `http://localhost:8004`

### Docker

```bash
# Build the image
docker build -t precise-risk-engine:latest .

# Run the container
docker run -p 8004:8004 \
  -e DB_HOST=localhost \
  -e REDIS_HOST=localhost \
  precise-risk-engine:latest
```

## Testing

```bash
# Install test dependencies
pip install pytest pytest-cov

# Run tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=. --cov-report=html
```

## Usage Example

### Score a Single Entity

```bash
curl -X POST http://localhost:8004/api/v1/scoring/score \
  -H "Content-Type: application/json" \
  -d '{
    "entity_id": "entity_001",
    "entity_data": {
      "entity_risk_score": 25,
      "historical_violation_count": 5,
      "connectivity_score": 40,
      "trade_frequency_anomaly": 35,
      "sanctioned_status": 0,
      "jurisdiction_risk": 20,
      "product_sensitivity": 15
    }
  }'
```

### Batch Score Multiple Entities

```bash
curl -X POST http://localhost:8004/api/v1/scoring/batch-score \
  -H "Content-Type: application/json" \
  -d '{
    "entities": [
      {
        "entity_id": "entity_001",
        "entity_data": {...}
      },
      {
        "entity_id": "entity_002",
        "entity_data": {...}
      }
    ]
  }'
```

### Get Model Info

```bash
curl http://localhost:8004/api/v1/metrics/model-info
```

### List Rules

```bash
curl http://localhost:8004/api/v1/rules/list
```

### Submit Feedback

```bash
curl -X POST http://localhost:8004/api/v1/feedback/submit \
  -H "Content-Type: application/json" \
  -d '{
    "entity_id": "entity_001",
    "predicted_score": 45.5,
    "actual_outcome": "low_risk",
    "correction_score": 35.0,
    "notes": "Feedback on score accuracy"
  }'
```

## Database Schema

The service expects a `risk_scoring` schema in PostgreSQL with tables for:
- risk_scores
- rules_applied
- feedback_records
- metrics

(Schema creation is handled by the service initialization)

## Monitoring

### Health Check

```bash
curl http://localhost:8004/health
```

### Metrics Summary

```bash
curl http://localhost:8004/api/v1/metrics/summary
```

### Drift Detection

```bash
curl http://localhost:8004/api/v1/metrics/drift-report
```

## Features

- **Config-Driven Model**: No hardcoding; all configuration in YAML
- **Generic PreciseRiskModel**: Reusable across different domains
- **Cache Integration**: Redis-backed caching for performance
- **Database Integration**: PostgreSQL with risk_scoring schema
- **Drift Detection**: Monitor model performance over time
- **Feedback Loop**: Collect and analyze feedback for model improvement
- **Metrics & Monitoring**: Comprehensive metrics endpoint
- **Docker Ready**: Includes Dockerfile and docker-compose integration
- **Comprehensive Tests**: Unit and integration test suite
- **Error Handling**: Graceful error handling with proper HTTP codes

## Development Roadmap

Phase 1 (Current): Core microservice skeleton
- ✓ Flask app factory
- ✓ 4 API blueprints
- ✓ Generic PreciseRiskModel
- ✓ Config-driven cbp.yaml
- ✓ Cache and database services
- ✓ Dockerfile
- ✓ Unit tests

Phase 2: Production Hardening
- Database schema creation
- Redis connection pooling
- Request validation and schema
- API documentation (Swagger/OpenAPI)
- Advanced error handling
- Rate limiting
- Authentication/Authorization

Phase 3: Advanced Features
- Rule engine integration (Drools or similar)
- Model versioning
- A/B testing framework
- Real-time drift alerts
- Performance optimization

## Dependencies

- Flask 2.3.3
- Flask-CORS 4.0.0
- Flask-SQLAlchemy 3.0.5
- Flask-Caching 2.1.0
- psycopg2-binary 2.9.7
- redis 5.0.0
- PyYAML 6.0.1
- python-dotenv 1.0.0
- gunicorn 21.2.0

## License

Internal CBP Project
