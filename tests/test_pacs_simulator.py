"""
Tests for ALVEON Hospital Modality & VNA Simulator
Verifies modality hardware simulation, acquisition synthesis, and socket C-STORE push over port 11112.
"""

import pytest
from fastapi.testclient import TestClient
from api.app import app
from core.pacs_simulator import get_pacs_simulator

client = TestClient(app)


def test_list_hospital_modalities():
    sim = get_pacs_simulator()
    modalities = sim.list_modalities()
    assert len(modalities) >= 3
    assert any(m.device_id == "MOD-XR-BAY1" for m in modalities)
    assert any(m.device_id == "MOD-CT-SCAN2" for m in modalities)


def test_api_list_modalities_endpoint():
    res = client.get("/api/v1/pacs/modalities")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert len(data["modalities"]) >= 3


def test_simulate_modality_cstore_push_over_port_11112():
    # Trigger automated simulated C-STORE push from Emergency Bay 1 XR
    res = client.post(
        "/api/v1/pacs/simulate-modality",
        json={
            "modality_key": "XR_EMERGENCY_BAY_1",
            "study_idx": 0,
            "target_port": 11112
        }
    )
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["status_code"] == "0x0000"
    assert data["study_transmitted"]["patient_name"] == "Sterling^Connor"
    assert data["network_latency_ms"] > 0
    assert "SOPInstanceUID" in data["sop_instance_uid"] or len(data["sop_instance_uid"]) > 10
