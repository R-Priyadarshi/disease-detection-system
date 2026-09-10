# ==============================================================================
# PneumoScan AI - Production Docker Container
# Multi-stage lightweight deployment container with OpenCV runtime libraries
# ==============================================================================

FROM python:3.12-slim as base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

# Install system dependencies required by OpenCV & image processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application codebase and model weights
COPY core/ /app/core/
COPY api/ /app/api/
COPY web/ /app/web/
COPY test.py /app/test.py
COPY TESTCNN.hdf5 /app/TESTCNN.hdf5

# Pre-generate sample radiograph assets
RUN python -m core.sample_generator

# Create non-root medical app user for security
RUN useradd -m -u 1001 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
