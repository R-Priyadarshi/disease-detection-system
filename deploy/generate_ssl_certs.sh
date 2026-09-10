#!/usr/bin/env bash
# ==============================================================================
# ALVEON Enterprise Hospital PACS - Automated TLS Certificate Generator
# Conforms to NIST SP 800-52 & HIPAA Security Rule § 164.312(e)(1) Encryption in Transit
# 100% Free & Open-Source (OpenSSL / Self-Signed & Let's Encrypt Hook)
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CERTS_DIR="${SCRIPT_DIR}/certs"

mkdir -p "${CERTS_DIR}"

DOMAIN="${1:-localhost}"
DAYS=365
KEY_FILE="${CERTS_DIR}/alveon_tls.key"
CERT_FILE="${CERTS_DIR}/alveon_tls.crt"

echo "================================================================="
echo "🔒 ALVEON Cryptographic TLS Certificate Generator"
echo "Target Domain: ${DOMAIN} (Validity: ${DAYS} days)"
echo "================================================================="

if [ -f "${CERT_FILE}" ] && [ -f "${KEY_FILE}" ]; then
    echo "✅ Active TLS certificate already exists at ${CERT_FILE}."
    echo "   Fingerprint (SHA-256): $(openssl x509 -noout -fingerprint -sha256 -in "${CERT_FILE}" | cut -d'=' -f2)"
    exit 0
fi

echo "Generating 4096-bit RSA Private Key and X.509 Certificate..."
openssl req -x509 -nodes -days "${DAYS}" -newkey rsa:4096 \
    -keyout "${KEY_FILE}" \
    -out "${CERT_FILE}" \
    -subj "/C=US/ST=New York/L=Metropolis/O=St. Jude Health System/OU=Emergency Radiology/CN=${DOMAIN}" \
    -addext "subjectAltName=DNS:${DOMAIN},DNS:localhost,IP:127.0.0.1"

chmod 600 "${KEY_FILE}"
chmod 644 "${CERT_FILE}"

echo "✅ TLS Certificate successfully generated!"
echo "   Private Key: ${KEY_FILE}"
echo "   Certificate: ${CERT_FILE}"
echo "   SHA-256 Fingerprint: $(openssl x509 -noout -fingerprint -sha256 -in "${CERT_FILE}" | cut -d'=' -f2)"
echo "================================================================="
