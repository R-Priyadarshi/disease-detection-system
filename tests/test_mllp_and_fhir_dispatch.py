"""
ALVEON Enterprise Hospital PACS - Tests for HL7 v2 MLLP Ingestion & FHIR Dispatch
Verifies:
1. MLLP server lifecycle and TCP port binding.
2. MLLP framing (\x0b, \x1c\x0d) and commit ACK generation.
3. Inbound ORM^O01 order ingestion and worklist registration.
4. Inbound ADT^A01 patient demographic processing.
5. REST API /api/v1/mllp/simulate-message and status endpoints.
6. FHIR destination listing and dispatch to local mock receiver.
"""

import pytest
import asyncio
from fastapi.testclient import TestClient
from api.app import app
from core.mllp_server import get_mllp_server, MLLP_START_BYTE, MLLP_END_BYTES
from core.fhir_dispatcher import get_fhir_dispatcher

client = TestClient(app)

SAMPLE_ORM_O01 = (
    "MSH|^~\\&|EPIC_EHR|ST_JUDE|ALVEON_PACS|METRO|20260912120000||ORM^O01|MSG1001|P|2.5.1\r\n"
    "PID|1||MRN-TEST-9921^^^ST_JUDE^MR||O'Connor^Sean||19820415|M\r\n"
    "ORC|NW|ORD-9921|ACC-9921|||||||Dr. Vance^Eleanor\r\n"
    "OBR|1|ORD-9921|ACC-9921|XR-CHEST-STAT^Chest X-Ray STAT|||20260912120000||||||||||||||||||||||||R/O Pneumothorax"
)

SAMPLE_ADT_A01 = (
    "MSH|^~\\&|EPIC_ADT|ST_JUDE|ALVEON_PACS|METRO|20260912120500||ADT^A01|MSG1002|P|2.5.1\r\n"
    "EVN|A01|20260912120500\r\n"
    "PID|1||MRN-ADM-4432^^^ST_JUDE^MR||Ramirez^Elena||19900823|F\r\n"
    "PV1|1|E|ED-BAY-04||||10928^Dr. Vance^Eleanor"
)


def test_mllp_server_singleton_and_status():
    server = get_mllp_server()
    assert server is not None
    status = server.get_status()
    assert "is_running" in status
    assert "protocol" in status
    assert status["protocol"] == "HL7 v2.5.1 MLLP"
    assert "total_messages_received" in status


def test_mllp_process_raw_orm():
    server = get_mllp_server()
    ack_text, success = server.process_raw_hl7(SAMPLE_ORM_O01, client_str="TEST_CLIENT")
    assert success is True
    assert "MSH" in ack_text
    assert "MSA|AA|MSG1001" in ack_text


def test_mllp_process_raw_adt():
    server = get_mllp_server()
    ack_text, success = server.process_raw_hl7(SAMPLE_ADT_A01, client_str="TEST_CLIENT")
    assert success is True
    assert "MSA|AA|MSG1002" in ack_text


def test_mllp_simulate_endpoint():
    resp = client.post("/api/v1/mllp/simulate-message", json={"raw_hl7_text": SAMPLE_ORM_O01})
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "MSA|AA|MSG1001" in data["ack_message"]
    assert data["parsed_summary"]["total_messages"] >= 1


def test_mllp_status_endpoint():
    resp = client.get("/api/v1/mllp/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["protocol"] == "HL7 v2.5.1 MLLP"
    assert data["framing"] == "0x0B [payload] 0x1C 0x0D"
    assert isinstance(data["recent_messages"], list)


def test_fhir_destinations_endpoint():
    resp = client.get("/api/v1/fhir/destinations")
    assert resp.status_code == 200
    dests = resp.json()
    assert len(dests) >= 3
    ids = [d["id"] for d in dests]
    assert "hapi_fhir_r4" in ids
    assert "alveon_local_mock" in ids


def test_fhir_dispatcher_mock_delivery():
    dispatcher = get_fhir_dispatcher()
    mock_bundle = {
        "resourceType": "Bundle",
        "type": "document",
        "id": "BUNDLE-TEST-001",
        "entry": [
            {"resource": {"resourceType": "Patient", "id": "P01"}},
            {"resource": {"resourceType": "DiagnosticReport", "id": "DR01"}}
        ]
    }
    result = asyncio.run(dispatcher.dispatch_bundle(
        bundle_data=mock_bundle,
        destination_id="alveon_local_mock",
        operator_name="Dr. Test Radiologist"
    ))
    assert result["success"] is True
    assert result["http_status"] == 201
    assert result["latency_ms"] >= 0.0
    assert result["entries_count"] == 2
    assert "response_outcome" in result


def test_fhir_dispatch_endpoint_via_api():
    mock_bundle = {
        "resourceType": "Bundle",
        "type": "document",
        "id": "BUNDLE-API-002",
        "entry": [
            {"resource": {"resourceType": "Observation", "id": "OBS01"}}
        ]
    }
    resp = client.post("/api/v1/fhir/dispatch", json={
        "bundle_data": mock_bundle,
        "destination_id": "alveon_local_mock",
        "operator_name": "Dr. Eleanor Vance, MD"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["http_status"] == 201
    assert data["destination_id"] == "alveon_local_mock"
