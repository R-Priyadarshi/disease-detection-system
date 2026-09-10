"""
Integration tests for ALVEON DICOMweb REST services (QIDO-RS, WADO-RS, STOW-RS)
and External PACS connectivity endpoints.
"""

import io
import pytest
from fastapi.testclient import TestClient

from api.app import app
from core.sample_generator import ensure_sample_assets

@pytest.fixture(scope="module")
def client():
    ensure_sample_assets()
    with TestClient(app) as c:
        yield c

def test_qido_rs_search_studies(client):
    """Test QIDO-RS search studies endpoint."""
    response = client.get("/dicomweb/studies")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/dicom+json")
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0

    # Validate DICOM Part 18 Tag Mapping
    first = data[0]
    assert "00100020" in first  # PatientID
    assert "00100010" in first  # PatientName
    assert "0020000D" in first  # StudyInstanceUID
    assert "00080060" in first  # Modality

def test_qido_rs_filter_patient_id(client):
    """Test QIDO-RS patient filter."""
    response = client.get("/dicomweb/studies?PatientID=MRN-90214")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    if len(data) > 0:
        assert data[0]["00100020"]["Value"][0] == "MRN-90214"

def test_wado_rs_retrieve_metadata_and_rendered(client):
    """Test WADO-RS series, instances, metadata, and rendered frame."""
    studies_resp = client.get("/dicomweb/studies")
    studies = studies_resp.json()
    study_uid = studies[0]["0020000D"]["Value"][0]

    # Series
    series_resp = client.get(f"/dicomweb/studies/{study_uid}/series")
    assert series_resp.status_code == 200
    series = series_resp.json()
    series_uid = series[0]["0020000E"]["Value"][0]

    # Instances
    inst_resp = client.get(f"/dicomweb/studies/{study_uid}/series/{series_uid}/instances")
    assert inst_resp.status_code == 200
    instances = inst_resp.json()
    inst_uid = instances[0]["00080018"]["Value"][0]

    # WADO-RS Metadata
    meta_resp = client.get(f"/dicomweb/studies/{study_uid}/series/{series_uid}/instances/{inst_uid}/metadata")
    assert meta_resp.status_code == 200
    assert meta_resp.headers["content-type"].startswith("application/dicom+json")

    # WADO-RS Rendered Frame
    rendered_resp = client.get(f"/dicomweb/studies/{study_uid}/series/{series_uid}/instances/{inst_uid}/rendered")
    assert rendered_resp.status_code == 200
    assert rendered_resp.headers["content-type"] == "image/jpeg"
    assert len(rendered_resp.content) > 100

    # WADO-RS Native DICOM binary
    dcm_resp = client.get(f"/dicomweb/studies/{study_uid}/series/{series_uid}/instances/{inst_uid}")
    assert dcm_resp.status_code == 200
    assert dcm_resp.headers["content-type"] == "application/dicom"
    assert len(dcm_resp.content) > 132

def test_stow_rs_store_instances(client):
    """Test STOW-RS storing DICOM instance via HTTP."""
    from tests.test_external_pacs_cohort import build_pydicom_dataset
    ds = build_pydicom_dataset("MRN-STOW-TEST", "TEST^STOW^PATIENT", 50, "M", "PNEUMONIA")
    bio = io.BytesIO()
    ds.save_as(bio, write_like_original=False)
    raw_dcm = bio.getvalue()

    # Upload via STOW-RS
    response = client.post(
        "/dicomweb/studies",
        content=raw_dcm,
        headers={"content-type": "application/dicom"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["ingested_count"] >= 1

def test_pacs_ping_endpoint(client):
    """Test external PACS C-ECHO endpoint."""
    response = client.post("/api/v1/pacs/ping", json={"host": "127.0.0.1", "port": 11112, "ae_title": "ALVEON_PACS"})
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
