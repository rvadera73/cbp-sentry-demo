FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Step 1: Install Python dependencies (cached independently)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Step 2: Copy application code
COPY . .

# Create health check script
RUN printf '#!/bin/sh\ncurl -f http://localhost:8005/health || exit 1\n' > /healthcheck.sh && chmod +x /healthcheck.sh

# Health check
HEALTHCHECK --interval=10s --timeout=5s --start-period=30s --retries=5 \
  CMD /healthcheck.sh

EXPOSE 8005

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8005"]
