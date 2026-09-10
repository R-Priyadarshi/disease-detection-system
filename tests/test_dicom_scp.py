import io
import socket
import numpy as np
import pytest
import pydicom
from fastapi.testclient import TestClient
from pynetdicom import AE
from pynetdicom.sop_class import Verification, SecondaryCaptureImageStorage

from api.app import app
from core import dicom_handler
from core.dicom_listener import get_dicom_scp

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

def test_dicom_status_endpoint(client):
    """Test GET /api/v1/dicom/status returns node telemetry."""
    response = client.get("/api/v1/dicom/status")
    assert response.status_code == 200
    data = response.json()
    assert "ae_title" in data
    assert "port" in data
    assert "is_active" in data
    assert "total_studies_received" in data
    assert data["ae_title"] == "ALVEON_PACS"

def test_dicom_c_echo_loopback():
    """Test C-ECHO verification against active SCP service on test port."""
    # Find free port
    s = socket.socket()
    s.bind(('', 0))
    test_port = s.getsockname()[1]
    s.close()

    from core.dicom_listener import DicomScpService
    test_scp = DicomScpService(ae_title="TEST_ALVEON", port=test_port)
    test_scp.start()
    assert test_scp.is_running

    try:
        echo_res = test_scp.send_echo(host="127.0.0.1", port=test_port)
        assert echo_res["status"] == "success"
        assert echo_res["latency_ms"] >= 0
    finally:
        test_scp.stop()

def test_dicom_c_store_ingestion_into_worklist():
    """Test C-STORE dataset transmission dynamically populates ER triage queue."""
    s = socket.socket()
    s.bind(('', 0))
    test_port = s.getsockname()[1]
    s.close()

    from core.dicom_listener import DicomScpService
    test_scp = DicomScpService(ae_title="ALVEON_STORE", port=test_port)
    test_scp.start()
    assert test_scp.is_running

    try:
        # Create synthetic DICOM
        pixels = (np.ones((128, 128), dtype=np.uint16) * 1000)
        pixels[30:80, 30:80] = 3800  # Dense consolidation
        dcm_bytes = dicom_handler.create_synthetic_dicom(
            pixel_array=pixels,
            patient_id="MRN-SCP-AUTO-99",
            patient_name="RIPLEY^ELLEN",
            patient_age="34Y",
            patient_sex="F"
        )
        ds = pydicom.dcmread(io.BytesIO(dcm_bytes))

        # Transmit via SCU
        client_ae = AE(ae_title="MODALITY_SCU")
        client_ae.add_requested_context(ds.SOPClassUID)
        assoc = client_ae.associate("127.0.0.1", test_port, ae_title="ALVEON_STORE")
        assert assoc.is_established
        status = assoc.send_c_store(ds)
        assoc.release()

        assert status.Status == 0x0000
        assert test_scp.total_received >= 1

        # Verify study was ingested into worklist cache
        from api.routes import _WORKLIST_CACHE
        assert _WORKLIST_CACHE is not None
        match = next((s for s in _WORKLIST_CACHE if s.patient_mrn == "MRN-SCP-AUTO-99"), None)
        assert match is not None
        assert "RIPLEY" in match.patient_name
        assert match.status == "PENDING"
    finally:
        test_scp.stop()
