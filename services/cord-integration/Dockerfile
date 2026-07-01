# CORD Integration API Service - Senzing SDK Wrapper
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/cord-integration/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY services/cord-integration/main.py .
COPY services/cord-integration/cord_loader.py .
COPY services/cord-integration/cbp_augmentor.py .
COPY services/cord-integration/resolver.py .
COPY services/cord-integration/demo_entities.py .
COPY services/cord-integration/seed_cbp_entities.py .
COPY services/cord-integration/seed_eapa_senzing.py .
COPY services/cord-integration/derive_relationships.py .
COPY services/cord-integration/load_eapa_network.py .

# Real EAPA entity network (from the PDF harvester) loaded at startup
COPY services/api/reference/eapa_entities.csv /app/reference/eapa_entities.csv
COPY services/api/reference/eapa_relationships.csv /app/reference/eapa_relationships.csv
# Public-registry enrichment (GLEIF/EDGAR/OpenCorporates): identity + affiliates
COPY services/api/reference/entity_registry.csv /app/reference/entity_registry.csv
COPY services/api/reference/entity_registry_relationships.csv /app/reference/entity_registry_relationships.csv

# Copy database files
COPY data/ /app/data/

# Health check script
RUN echo '#!/bin/bash\ncurl -f http://localhost:8004/health || exit 1' > /healthcheck.sh && \
    chmod +x /healthcheck.sh

# Expose port
EXPOSE 8004

# Run application — first seed EAPA respondents into senzing_entities (so the
# deriver can see them), THEN derive CORD relationships into
# senzing_relationships (idempotent; backgrounded so it doesn't block serving),
# then serve.
CMD ["sh", "-c", "python3 seed_eapa_senzing.py >/tmp/seedeapa.log 2>&1; python3 load_eapa_network.py --entities /app/reference/eapa_entities.csv --relationships /app/reference/eapa_relationships.csv >/tmp/loadeapa.log 2>&1; python3 derive_relationships.py >/tmp/derive.log 2>&1 & exec uvicorn main:app --host 0.0.0.0 --port 8004"]
