import io
import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from api.app import app
from core import dicom_handler
from core.sample_generator import ensure_sample_assets

@pytest.fixture(scope="module")
def client():
    ensure_sample_assets()
    with TestClient(app) as c:
        yield c

def test_emergency_triage_worklist(client):
    """Test the ER STAT Triage Worklist returns prioritized studies."""
    response = client.get("/api/v1/worklist")
    assert response.status_code == 200
    data = response.json()

    assert data["total_cases"] >= 5
    assert data["stat_critical_count"] >= 1
    assert data["pending_count"] >= 1
    assert len(data["studies"]) == data["total_cases"]

    # Verify priority sorting: STAT_CRITICAL must be at the very top
    first_study = data["studies"][0]
    assert first_study["priority"] == "STAT_CRITICAL"
    assert first_study["priority_rank"] == 1
    assert first_study["is_pneumonia"] is True
    assert "dicom_metadata" in first_study
    assert "zonation" in first_study
    assert first_study["image_b64"].startswith("data:image/jpeg;base64,")
    assert first_study["gradcam_overlay_b64"].startswith("data:image/jpeg;base64,")

def test_radiologist_electronic_signoff(client):
    """Test radiologist attestation and SHA-256 electronic sign-off workflow."""
    # First get a study from worklist
    worklist_res = client.get("/api/v1/worklist")
    assert worklist_res.status_code == 200
    studies = worklist_res.json()["studies"]
    target_study = studies[0]
    study_id = target_study["study_id"]

    signoff_payload = {
        "study_id": study_id,
        "physician_name": "Dr. Eleanor Vance, MD",
        "physician_license": "RAD-US-89410",
        "findings_summary": "Confirmed extensive right lower lobe consolidation consistent with acute bacterial pneumonia.",
        "attestation_accepted": True
    }

    response = client.post("/api/v1/signoff", json=signoff_payload)
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "success"
    assert data["study_id"] == study_id
    assert data["signoff_badge"] == "VERIFIED & SIGNED"
    assert len(data["audit_hash"]) == 16
    assert "Dr. Eleanor Vance, MD" in data["physician_signature"]

    # Verify the worklist now reflects the SIGNED status
    refreshed_res = client.get("/api/v1/worklist")
    updated_study = next(s for s in refreshed_res.json()["studies"] if s["study_id"] == study_id)
    assert updated_study["status"] == "SIGNED"

def test_batch_cohort_triage(client):
    """Test simultaneous batch triage of multiple radiographs."""
    # Create two test images
    img1 = Image.new("L", (150, 150), color=50)
    buf1 = io.BytesIO()
    img1.save(buf1, format="JPEG")
    buf1.seek(0)

    # Create a synthetic DICOM
    pixels = np.ones((128, 128), dtype=np.uint16) * 1500
    dcm_bytes = dicom_handler.create_synthetic_dicom(
        pixel_array=pixels,
        patient_id="MRN-BATCH-01",
        patient_name="BATCH^PATIENT"
    )

    files = [
        ("files", ("batch_img1.jpg", buf1, "image/jpeg")),
        ("files", ("batch_case2.dcm", io.BytesIO(dcm_bytes), "application/dicom"))
    ]

    response = client.post("/api/v1/batch/triage", files=files)
    assert response.status_code == 200
    data = response.json()

    assert data["total_ingested"] == 2
    assert len(data["triaged_studies"]) == 2
    assert "critical_stat_count" in data
    # Verify sorting by acuity rank
    assert data["triaged_studies"][0]["priority_rank"] <= data["triaged_studies"][1]["priority_rank"]

def test_predict_with_native_dicom(client):
    """Test predicting directly from an uploaded 16-bit binary DICOM file."""
    pixels = (np.ones((256, 256), dtype=np.uint16) * 800)
    # Inject a hyperdense focal consolidation
    pixels[80:180, 80:180] = 3500

    dcm_bytes = dicom_handler.create_synthetic_dicom(
        pixel_array=pixels,
        patient_id="MRN-DICOM-TEST",
        patient_name="TEST^DICOM",
        kvp=125.0,
        exposure_time=12
    )

    response = client.post(
        "/api/v1/predict",
        files={"file": ("inbound_scan.dcm", io.BytesIO(dcm_bytes), "application/dicom")},
        data={"apply_clahe": "true", "colormap": "inferno", "heatmap_alpha": "0.6"}
    )
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "success"
    assert data["diagnosis"] in {"PNEUMONIA", "NORMAL"}
    assert "dicom_metadata" in data
    meta = data["dicom_metadata"]
    assert meta["is_dicom"] is True
    assert meta["patient_id"] == "MRN-DICOM-TEST"
    assert meta["patient_name"] == "TEST^DICOM"
    assert "125" in str(meta["kvp"])
    assert "12" in str(meta["exposure_time"])
