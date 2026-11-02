# ==============================================================================
# Production Dockerfile
# AI-Based Missing Person Identification & Tracking System
# ==============================================================================
FROM python:3.12-slim-bookworm

# Set environment defaults
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    PORT=8000 \
    HOST=0.0.0.0

# Install native OS dependencies required by OpenCV and video processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root system user for security compliance
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -s /bin/bash -m appuser

WORKDIR /app

# Install Python dependencies first for optimal Docker layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application directories and files
COPY backend/ backend/
COPY frontend/ frontend/
COPY models/ models/
COPY sample_data/ sample_data/
COPY deploy/ deploy/
COPY run.py .

# Create storage directories and set ownership to appuser
RUN mkdir -p storage/references storage/sightings && \
    chmod +x deploy/entrypoint.sh && \
    chown -R appuser:appgroup /app

# Switch to non-privileged user
USER appuser

# Expose internal API and Web UI port
EXPOSE 8000

# Container health probe
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -f http://127.0.0.1:8000/healthz || exit 1

ENTRYPOINT ["deploy/entrypoint.sh"]
