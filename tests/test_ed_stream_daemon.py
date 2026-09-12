"""
Unit and Integration Tests for Continuous Emergency Department Stream Simulation Daemon
=========================================================================================
Tests daemon lifecycle, dynamic cadence adjustments, realistic case synthesis,
worklist injection, MCI burst simulation, and FastAPI REST endpoints.
"""

import pytest
import asyncio
from fastapi.testclient import TestClient

from api.app import create_app
from core.ed_stream_daemon import get_ed_stream_daemon, EDStreamDaemon
from api import routes

@pytest.fixture(scope="module")
def client():
    app = create_app()
    with TestClient(app) as c:
        yield c

@pytest.fixture(autouse=True)
def cleanup_daemon():
    daemon = get_ed_stream_daemon()
    daemon.stop()
    yield
    daemon.stop()


def test_ed_stream_daemon_singleton():
    daemon1 = get_ed_stream_daemon()
    daemon2 = get_ed_stream_daemon()
    assert daemon1 is daemon2
    assert isinstance(daemon1, EDStreamDaemon)

    status = daemon1.get_status()
    assert "is_running" in status
    assert "cadence_seconds" in status
    assert "total_streamed" in status
    assert status["is_running"] is False


def test_ed_stream_daemon_cadence():
    daemon = get_ed_stream_daemon()
    daemon.set_cadence(12.5)
    assert daemon.cadence_seconds == 12.5

    # Should clamp to at least 5.0 seconds
    daemon.set_cadence(2.0)
    assert daemon.cadence_seconds == 5.0

    daemon.set_cadence(30.0)
    assert daemon.cadence_seconds == 30.0


@pytest.mark.anyio
async def test_ed_stream_daemon_inject_single():
    daemon = get_ed_stream_daemon()
    initial_count = daemon.total_streamed

    study = await daemon.inject_study(is_burst=False)

    assert study.study_id.startswith("ALV-ED-")
    assert study.patient_mrn.startswith("MRN-ED-")
    assert study.priority in ["STAT_CRITICAL", "URGENT", "ROUTINE"]
    assert study.priority_rank in [1, 2, 3]
    assert len(study.image_b64) > 100
    assert len(study.gradcam_overlay_b64) > 100
    assert daemon.total_streamed == initial_count + 1

    # Verify present in active worklist cache
    assert routes._WORKLIST_CACHE is not None
    study_ids = [s.study_id for s in routes._WORKLIST_CACHE]
    assert study.study_id in study_ids


@pytest.mark.anyio
async def test_ed_stream_daemon_trigger_burst():
    daemon = get_ed_stream_daemon()
    initial_count = daemon.total_streamed

    burst = await daemon.trigger_burst(count=3)
    assert len(burst) == 3
    assert daemon.total_streamed == initial_count + 3

    for s in burst:
        assert s.study_id.startswith("ALV-ED-")
        assert s.patient_mrn.startswith("MRN-ED-")


def test_api_ed_stream_status_endpoint(client: TestClient):
    res = client.get("/api/v1/ed-stream/status")
    assert res.status_code == 200
    data = res.json()
    assert "is_running" in data
    assert "cadence_seconds" in data
    assert "total_streamed" in data
    assert "active_listeners" in data


def test_api_ed_stream_start_stop_endpoints(client: TestClient):
    # Start
    res_start = client.post("/api/v1/ed-stream/start", json={"cadence_seconds": 15.0})
    assert res_start.status_code == 200
    data_start = res_start.json()
    assert data_start["is_running"] is True
    assert data_start["cadence_seconds"] == 15.0

    # Check status
    res_status = client.get("/api/v1/ed-stream/status")
    assert res_status.status_code == 200
    assert res_status.json()["is_running"] is True

    # Stop
    res_stop = client.post("/api/v1/ed-stream/stop")
    assert res_stop.status_code == 200
    data_stop = res_stop.json()
    assert data_stop["is_running"] is False


def test_api_ed_stream_cadence_endpoint(client: TestClient):
    res = client.post("/api/v1/ed-stream/cadence", json={"cadence_seconds": 45.0})
    assert res.status_code == 200
    data = res.json()
    assert data["cadence_seconds"] == 45.0


def test_api_ed_stream_burst_endpoint(client: TestClient):
    res = client.post("/api/v1/ed-stream/burst", json={"count": 2})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["alert_level"] == "CODE_BLACK_MASS_CASUALTY"
    assert data["count"] == 2
    assert len(data["studies"]) == 2
    assert "telemetry" in data


def test_api_ed_stream_inject_single_endpoint(client: TestClient):
    res = client.post("/api/v1/ed-stream/inject-single")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "study" in data
    assert data["study"]["study_id"].startswith("ALV-ED-")
    assert "telemetry" in data
