#!/usr/bin/env bash
# ==============================================================================
# ALVEON PACS v5.1 - Enterprise Turnkey Production Deployment Script
# Supports:
#   ./deploy.sh start    - Spin up full multi-container stack (PACS + Orthanc + DB + Nginx)
#   ./deploy.sh stop     - Gracefully stop containers
#   ./deploy.sh restart  - Clean restart of all microservices
#   ./deploy.sh status   - Check health and port bindings (8000, 11112, 2575, 4242)
#   ./deploy.sh logs     - Stream real-time logs across containers
#   ./deploy.sh test     - Execute end-to-end integration and health tests
# ==============================================================================

set -euo pipefail

# ANSI Color Palette
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
PURPLE='\033[0;35m'
BOLD='\033[1m'
NC='\033[0m' # No Color

APP_NAME="ALVEON PACS & Diagnostic AI Workstation"
VERSION="5.1.0-LTS"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

print_header() {
    echo -e "${CYAN}${BOLD}"
    echo "============================================================================"
    echo "  ${APP_NAME} - Production Deployment System (v${VERSION})"
    echo "  Hospital Interoperability: DICOM C-STORE (11112) | HL7 MLLP (2575)"
    echo "============================================================================"
    echo -e "${NC}"
}

check_dependencies() {
    echo -e "${PURPLE}[+] Verifying environment pre-requisites...${NC}"
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}[ERROR] 'docker' command not found. Please install Docker Engine first.${NC}"
        exit 1
    fi

    # Determine compose command (docker compose vs docker-compose)
    if docker compose version &> /dev/null; then
        COMPOSE_CMD="docker compose"
    elif command -v docker-compose &> /dev/null; then
        COMPOSE_CMD="docker-compose"
    else
        echo -e "${RED}[ERROR] Neither 'docker compose' nor 'docker-compose' was found.${NC}"
        exit 1
    fi
    echo -e "${GREEN}[✓] Docker and Compose detected: ${COMPOSE_CMD}${NC}"
}

start_stack() {
    print_header
    check_dependencies

    echo -e "${PURPLE}[+] Verifying environment configuration...${NC}"
    mkdir -p data/dicom_storage deploy/certs

    # Generate self-signed TLS certs if missing for TLS 1.3 reverse proxy
    if [ ! -f deploy/certs/server.crt ] || [ ! -f deploy/certs/server.key ]; then
        echo -e "${YELLOW}[!] TLS certificates missing. Generating local self-signed certificates...${NC}"
        openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
            -keyout deploy/certs/server.key \
            -out deploy/certs/server.crt \
            -subj "/C=US/ST=Healthcare/L=Diagnostic/O=AlveonPACS/CN=localhost" 2>/dev/null || true
    fi

    echo -e "${CYAN}[+] Building and launching enterprise multi-container cluster...${NC}"
    $COMPOSE_CMD up -d --build

    echo -e "${PURPLE}[+] Waiting for services to become healthy...${NC}"
    local max_retries=30
    local retry_count=0
    local healthy=false

    while [ $retry_count -lt $max_retries ]; do
        if curl -s -f http://127.0.0.1:8000/health > /dev/null 2>&1 || \
           curl -s -f http://127.0.0.1:8000/healthz > /dev/null 2>&1; then
            healthy=true
            break
        fi
        sleep 2
        retry_count=$((retry_count + 1))
        echo -ne "."
    done
    echo ""

    if [ "$healthy" = true ]; then
        echo -e "${GREEN}${BOLD}[✓] ALVEON PACS Stack successfully deployed and verified!${NC}"
        print_status
    else
        echo -e "${YELLOW}[!] System is starting up but health probe timed out. Inspect logs with: ./deploy.sh logs${NC}"
    fi
}

stop_stack() {
    print_header
    check_dependencies
    echo -e "${YELLOW}[+] Gracefully stopping all ALVEON services...${NC}"
    $COMPOSE_CMD down
    echo -e "${GREEN}[✓] All services halted.${NC}"
}

restart_stack() {
    stop_stack
    start_stack
}

print_status() {
    echo -e "\n${CYAN}${BOLD}Service Status & Port Bindings:${NC}"
    echo -e "  ${GREEN}●${NC} Diagnostic Workstation & REST: ${BOLD}http://localhost:8000${NC} (HTTPS: 443)"
    echo -e "  ${GREEN}●${NC} DICOM Storage SCP (C-STORE):   ${BOLD}localhost:11112${NC} (AET: ALVEON_STORE_SCP)"
    echo -e "  ${GREEN}●${NC} HL7 v2 MLLP Ingestion Socket:  ${BOLD}localhost:2575${NC} (MLLP Framing \\x0b...\\x1c\\x0d)"
    echo -e "  ${GREEN}●${NC} Orthanc VNA Storage Archive:   ${BOLD}http://localhost:8042${NC} (DICOM DIMSE: 4242)"
    echo -e "  ${GREEN}●${NC} PostgreSQL Database:           ${BOLD}localhost:5432${NC}"
    echo ""
}

show_logs() {
    check_dependencies
    $COMPOSE_CMD logs -f
}

run_health_test() {
    print_header
    echo -e "${PURPLE}[+] Performing diagnostic pre-flight health checks...${NC}"
    
    echo -ne "1. FastAPI Core Health: "
    if curl -s http://127.0.0.1:8000/health | grep -q "healthy"; then
        echo -e "${GREEN}PASSED${NC}"
    else
        echo -e "${RED}FAILED${NC}"
    fi

    echo -ne "2. HL7 MLLP Telemetry: "
    if curl -s http://127.0.0.1:8000/api/v1/mllp/status | grep -q "status"; then
        echo -e "${GREEN}PASSED${NC}"
    else
        echo -e "${RED}FAILED${NC}"
    fi

    echo -ne "3. FHIR Dispatcher Gateways: "
    if curl -s http://127.0.0.1:8000/api/v1/fhir/destinations | grep -q "destinations"; then
        echo -e "${GREEN}PASSED${NC}"
    else
        echo -e "${RED}FAILED${NC}"
    fi

    echo -ne "4. Emergency Triage Worklist: "
    if curl -s http://127.0.0.1:8000/api/v1/worklist | grep -q "total_cases"; then
        echo -e "${GREEN}PASSED${NC}"
    else
        echo -e "${RED}FAILED${NC}"
    fi
}

# Command Router
ACTION="${1:-start}"

case "$ACTION" in
    start)
        start_stack
        ;;
    stop)
        stop_stack
        ;;
    restart)
        restart_stack
        ;;
    status)
        check_dependencies
        $COMPOSE_CMD ps
        print_status
        ;;
    logs)
        show_logs
        ;;
    test)
        run_health_test
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|logs|test}"
        exit 1
        ;;
esac
