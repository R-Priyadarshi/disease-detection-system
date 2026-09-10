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

def test_folder_cohort_ingestion_and_patient_name_derivation(client):
    """Test folder cohort simulation with multi-level directories and patient name extraction."""
    img1 = Image.new("L", (128, 128), color=60)
    buf1 = io.BytesIO()
    img1.save(buf1, format="PNG")
    buf1.seek(0)

    # DICOM with explicit patient name
    pixels = (np.ones((128, 128), dtype=np.uint16) * 1200)
    pixels[40:90, 40:90] = 3400
    dcm_bytes = dicom_handler.create_synthetic_dicom(
        pixel_array=pixels,
        patient_id="MRN-CONNOR-09",
        patient_name="CONNOR^SARAH",
        patient_age="035Y",
        patient_sex="F"
    )

    img2 = Image.new("L", (128, 128), color=180)
    buf2 = io.BytesIO()
    img2.save(buf2, format="JPEG")
    buf2.seek(0)

    # Simulating a folder drop with relative directory paths
    files = [
        ("files", ("Ward_Emergency/Robert_Taylor_Chest.png", buf1, "image/png")),
        ("files", ("Ward_Emergency/Acute_Cohort/Connor_Sarah.dcm", io.BytesIO(dcm_bytes), "application/dicom")),
        ("files", ("Ward_Emergency/Routine/Marcus_Wright_PA.jpg", buf2, "image/jpeg"))
    ]

    response = client.post("/api/v1/batch/triage", files=files)
    assert response.status_code == 200
    data = response.json()

    assert data["total_ingested"] == 3
    studies = data["triaged_studies"]
    assert len(studies) == 3

    # Check patient names
    names = [s["patient_name"] for s in studies]
    # One of them must be the DICOM patient "CONNOR, SARAH"
    assert any("CONNOR, SARAH" in n or "Connor, Sarah" in n for n in names)
    # The others derived from filename stems
    assert any("Robert Taylor" in n for n in names)
    assert any("Marcus Wright" in n for n in names)

    # Verify priority ranks are sorted
    ranks = [s["priority_rank"] for s in studies]
    assert ranks == sorted(ranks)

def test_delete_worklist_study_and_purge(client):
    """Test deleting an individual study and purging uploaded cohorts."""
    # Ensure baseline is loaded
    worklist_res = client.get("/api/v1/worklist")
    assert worklist_res.status_code == 200
    initial_cases = worklist_res.json()["studies"]
    assert len(initial_cases) >= 1

    # Ingest a batch study
    img = Image.new("L", (100, 100), color=100)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    batch_res = client.post("/api/v1/batch/triage", files=[("files", ("temp_study.png", buf, "image/png"))])
    assert batch_res.status_code == 200
    temp_study_id = batch_res.json()["triaged_studies"][0]["study_id"]

    # Delete the specific study
    del_res = client.delete(f"/api/v1/worklist/{temp_study_id}")
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "success"
    assert del_res.json()["deleted_study_id"] == temp_study_id

    # Verify 404 on deleting non-existent study
    bad_del = client.delete("/api/v1/worklist/ALV-NON-EXISTENT")
    assert bad_del.status_code == 404

    # Test purge uploaded cohorts
    purge_res = client.delete("/api/v1/worklist?uploaded_only=true")
    assert purge_res.status_code == 200
    assert purge_res.json()["status"] == "success"

    # Test reset worklist to baseline
    reset_res = client.post("/api/v1/worklist/reset")
    assert reset_res.status_code == 200
    assert reset_res.json()["status"] == "success"


