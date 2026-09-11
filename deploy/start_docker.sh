#!/usr/bin/env bash
# ==============================================================================
# ALVEON PACS v5.1 - Production Docker Compose Startup Script
# Verifies environment, builds containers, and launches stack in background
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$ROOT_DIR"

echo "==================================================================="
echo "🏥 Launching ALVEON PACS Production Docker Enterprise Stack"
echo "==================================================================="

# Ensure storage directories exist
mkdir -p data/dicom_storage
mkdir -p deploy/certs

# Generate self-signed TLS certificates if missing
if [ ! -f "deploy/certs/alveon_tls.crt" ]; then
    echo "🔒 Generating local TLS 1.3 self-signed certificates..."
    bash deploy/generate_ssl_certs.sh
fi

echo "🚀 Starting Docker Compose services (app, orthanc, proxy)..."
if command -v docker-compose &> /dev/null; then
    docker-compose up -d --build
elif docker compose version &> /dev/null; then
    docker compose up -d --build
else
    echo "⚠️ Docker is not installed or not running in this environment."
    echo "To run natively without Docker: source .venv/bin/activate && uvicorn api.app:app --host 0.0.0.0 --port 8000"
    exit 0
fi

echo "==================================================================="
echo "✅ ALVEON PACS Stack Launched Successfully!"
echo "   • HTTPS Webstation: https://localhost"
echo "   • HTTP Webstation:  http://localhost:8000"
echo "   • DICOM SCP:        Port 11112 (AET: ALVEON_STORE_SCP)"
echo "   • Orthanc VNA:      http://localhost:8042 (DICOM Port 4242)"
echo "==================================================================="
