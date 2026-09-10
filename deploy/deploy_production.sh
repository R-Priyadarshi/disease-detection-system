#!/usr/bin/env bash
# ==============================================================================
# ALVEON Enterprise Hospital PACS - One-Touch Production Deployment Script
# 100% Free & Open-Source (Docker, Orthanc, Nginx, OpenSSL, Systemd)
# ==============================================================================

set -euo pipefail

DEPLOY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${DEPLOY_DIR}/.." && pwd)"

echo "================================================================="
echo "🏥 ALVEON Production Enterprise Deployment Initiator"
echo "Root Path: ${ROOT_DIR}"
echo "Deploy Path: ${DEPLOY_DIR}"
echo "================================================================="

# 1. Verify Docker and Docker Compose
echo "[1/4] Checking container runtime prerequisites..."
if ! command -v docker &> /dev/null; then
    echo "❌ Error: Docker is not installed. Please install Docker CE."
    exit 1
fi

if ! docker compose version &> /dev/null; then
    echo "❌ Error: Docker Compose v2 is required."
    exit 1
fi
echo "✅ Docker runtime ready: $(docker --version)"

# 2. Generate or Verify TLS Certificates
echo "[2/4] Verifying NIST/HIPAA TLS 1.3 Cryptographic Certificates..."
bash "${DEPLOY_DIR}/generate_ssl_certs.sh" "${1:-localhost}"

# 3. Create persistent directories
echo "[3/4] Initializing persistent hospital storage volumes..."
mkdir -p "${ROOT_DIR}/data/dicom_storage"
chmod -R 777 "${ROOT_DIR}/data/dicom_storage"

# 4. Bring up Docker Compose stack
echo "[4/4] Launching ALVEON Enterprise Hospital Stack..."
cd "${DEPLOY_DIR}"
docker compose -f docker-compose.prod.yml down --remove-orphans || true
docker compose -f docker-compose.prod.yml up -d --build

echo "================================================================="
echo "🎉 ALVEON Hospital PACS is now LIVE in production!"
echo "   • Workstation Web UI (HTTP):  http://127.0.0.1"
echo "   • Workstation Web UI (HTTPS): https://127.0.0.1 (TLS 1.3)"
echo "   • DICOM Storage SCP Port:     0.0.0.0:11112 (ALVEON_PACS)"
echo "   • Orthanc Hospital PACS:      http://127.0.0.1:8042 (DIMSE: 4242)"
echo "   • Health Probes:              http://127.0.0.1/healthz"
echo "================================================================="
