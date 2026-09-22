# ============================================================
# DocuSense — Dockerfile
# Uses Python 3.11-slim for a lean production image.
# API keys are injected via environment variables at runtime.
# ============================================================

FROM python:3.11-slim

# Metadata
LABEL maintainer="DocuSense"
LABEL description="Lightweight Grounded RAG Service"

# Set environment defaults (overridden by docker-compose / .env)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_HOST=0.0.0.0 \
    APP_PORT=8000

# System dependencies for faiss-cpu
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first (better layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY app/ ./app/
COPY data/ ./data/

# Create storage directory for FAISS index
RUN mkdir -p storage/faiss

# Expose API port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Run the API server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
