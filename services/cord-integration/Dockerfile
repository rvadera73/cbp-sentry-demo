# CORD Integration API Service - Senzing SDK Wrapper
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY main.py .
COPY cord_loader.py .
COPY cbp_augmentor.py .
COPY resolver.py .
COPY demo_entities.py .

# Health check script
RUN echo '#!/bin/bash\ncurl -f http://localhost:8004/health || exit 1' > /healthcheck.sh && \
    chmod +x /healthcheck.sh

# Expose port
EXPOSE 8004

# Run application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8004"]
