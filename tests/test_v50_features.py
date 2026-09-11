"""
Tests for ALVEON v5.0 Production Enterprise Suite:
- Step 1: Guided Interactive Clinical Tour System ("Day in the Life of a Radiologist")
- Step 2: Production Containerization & Deployment Hardening (deploy/verify_deployment.py)
- Step 3: Real Hospital Modality Connectivity & PACS Network Interface (core/modality_router.py)
- Step 4: Clinical AI Arsenal Expansion (core/prior_comparison.py & core/dicom_sr.py)
"""

import pytest
from pathlib import Path
import pydicom
from fastapi.testclient import TestClient
from api.app import app
from core.modality_router import get_modality_router, ModalityRouterEngine
from core.prior_comparison import get_prior_comparison_engine, PriorComparisonEngine
from core.dicom_sr import get_dicom_sr_engine, DicomSREngine, ENHANCED_SR_SOP_CLASS
from deploy.verify_deployment import check_core_engines, check_storage_permissions


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


# =====================================================================
# STEP 3: HOSPITAL MODALITY CONNECTIVITY & ROUTER TESTS
# =====================================================================

def test_modality_router_directory():
    """Verify registered hospital modalities directory and metadata."""
    engine = get_modality_router()
    modalities = engine.list_modalities()
    assert len(modalities) >= 4
    
    mod_ids = [m.modality_id for m in modalities]
    assert "MOD-XR-01" in mod_ids
    assert "MOD-CT-02" in mod_ids
    assert "PACS-ORTHANC" in mod_ids
    assert "MOD-ICU-03" in mod_ids

    xr_mod = engine.get_modality("MOD-XR-01")
    assert xr_mod is not None
    assert xr_mod.ae_title == "TRAUMA_XR_01"
    assert xr_mod.modality_type == "DX"
    assert xr_mod.port == 11112


def test_modality_c_echo_verification():
    """Verify DICOM C-ECHO verification SCU ping test."""
    engine = get_modality_router()
    res = engine.verify_modality_connectivity("MOD-XR-01")
    assert res["status"] == "ONLINE"
    assert "0x0000" in res["c_echo_response"]
    assert res["latency_ms"] > 0
    assert res["verified_at"] is not None


def test_modality_query_retrieve():
    """Verify DICOM C-MOVE / C-GET query-retrieve execution."""
    engine = get_modality_router()
    res = engine.query_retrieve_study("MOD-XR-01", {
        "study_instance_uid": "1.2.826.0.1.3680043.9.7123.test",
        "patient_mrn": "MRN-TEST-100",
        "patient_name": "Test^Patient"
    })
    assert res["status"] == "success"
    assert res["retrieval_log"]["operation"] == "C-MOVE"
    assert res["retrieval_log"]["destination_aet"] == "ALVEON_PACS"


def test_auto_routing_rules_evaluation():
    """Verify intelligent auto-routing rules evaluate and dispatch STAT critical studies."""
    engine = get_modality_router()
    
    # 1. Critical Pneumothorax study -> should auto-route to Trauma Bay 1
    study_meta = {
        "study_id": "STUDY-PNEUMO-01",
        "patient_mrn": "MRN-TRAUMA-99",
        "primary_finding": "Tension Pneumothorax",
        "modality": "DX",
        "status": "PENDING"
    }
    dispatched = engine.evaluate_auto_routing(study_meta)
    assert len(dispatched) >= 1
    assert any(d["target_ae_title"] == "TRAUMA_XR_01" for d in dispatched)

    # 2. Neuro CT study -> should auto-route to Neuro CT team
    neuro_meta = {
        "study_id": "STUDY-NEURO-02",
        "patient_mrn": "MRN-STROKE-88",
        "primary_finding": "Acute MCA Ischemic Infarct",
        "modality": "CT",
        "status": "PENDING"
    }
    neuro_dispatched = engine.evaluate_auto_routing(neuro_meta)
    assert len(neuro_dispatched) >= 1
    assert any(d["target_ae_title"] == "NEURO_CT_02" for d in neuro_dispatched)


def test_modality_api_endpoints(client):
    """Test FastAPI REST endpoints for modality router."""
    # GET /api/v1/modalities
    res = client.get("/api/v1/modalities")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert len(data["modalities"]) >= 4

    # POST /api/v1/modalities/verify
    res = client.post("/api/v1/modalities/verify", json={"modality_id": "MOD-XR-01"})
    assert res.status_code == 200
    assert res.json()["verification"]["status"] == "ONLINE"

    # POST /api/v1/modalities/query-retrieve
    res = client.post("/api/v1/modalities/query-retrieve", json={
        "modality_id": "MOD-XR-01",
        "patient_mrn": "MRN-TRAUMA-4410"
    })
    assert res.status_code == 200
    assert res.json()["status"] == "success"

    # GET /api/v1/modalities/routing-rules
    res = client.get("/api/v1/modalities/routing-rules")
    assert res.status_code == 200
    assert len(res.json()["rules"]) >= 3

    # POST /api/v1/modalities/route
    res = client.post("/api/v1/modalities/route", json={
        "study_id": "ALV-STAT-09",
        "target_modality_id": "MOD-XR-01",
        "primary_finding": "PNEUMOTHORAX"
    })
    assert res.status_code == 200
    assert res.json()["status"] == "success"


# =====================================================================
# STEP 4: LONGITUDINAL PRIOR COMPARISON & SUBTRACTION TESTS
# =====================================================================

def test_longitudinal_prior_comparison_engine():
    """Verify rigid affine co-registration and subtraction difference mapping."""
    engine = get_prior_comparison_engine()
    
    # Create synthetic test grayscale image as base64
    import numpy as np
    from PIL import Image
    import io
    import base64
    
    arr = np.ones((120, 120), dtype=np.uint8) * 128
    arr[40:80, 40:80] = 220 # Simulated infiltrate
    img = Image.fromarray(arr)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64_img = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("utf-8")

    res = engine.compare_studies(
        current_image_b64=b64_img,
        patient_mrn="MRN-TEST-LONGITUDINAL"
    )

    assert res["patient_mrn"] == "MRN-TEST-LONGITUDINAL"
    assert res["registration_status"] == "AFFINE_CONVERGED_OPTIMAL"
    assert "interval_assessment" in res
    assert isinstance(res["interval_delta_pct"], float)
    assert res["prior_image_b64"].startswith("data:image/png;base64,")
    assert res["subtraction_heatmap_b64"].startswith("data:image/png;base64,")
    assert len(res["clinical_summary"]) > 10


def test_prior_comparison_api_endpoint(client):
    """Test POST /api/v1/prior/compare endpoint with fallback to active study."""
    res = client.post("/api/v1/prior/compare", json={
        "patient_mrn": "MRN-TRAUMA-4410",
        "current_study_id": "ALV-STAT-09"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["registration_status"] == "AFFINE_CONVERGED_OPTIMAL"
    assert data["prior_image_b64"] is not None
    assert data["subtraction_heatmap_b64"] is not None


# =====================================================================
# STEP 4: DICOM PART 16 STRUCTURED REPORTING (TID 1500) TESTS
# =====================================================================

def test_dicom_sr_dataset_structure():
    """Verify generated dataset complies with DICOM PS 3.16 / TID 1500."""
    engine = get_dicom_sr_engine()
    ds = engine.generate_sr_dataset(
        study_id="STUDY-SR-TEST-01",
        patient_mrn="MRN-SR-99",
        patient_name="DOE^JOHN",
        patient_sex="M",
        primary_finding="PNEUMOTHORAX",
        confidence_percentage=99.8,
        caliper_measurements=[{"name": "Apical Separation", "length_mm": 38.5}],
        ctr_index=0.48,
        acr_category="ACR Category 1 (Critical STAT Alert)",
        radiologist_name="Vance^Eleanor^^^Dr."
    )

    # Validate Enhanced SR Storage SOP Class
    assert ds.SOPClassUID == ENHANCED_SR_SOP_CLASS
    assert ds.Modality == "SR"
    assert ds.PatientID == "MRN-SR-99"
    assert ds.PatientName == "DOE^JOHN"
    assert ds.CompletionFlag == "COMPLETE"
    assert ds.VerificationFlag == "VERIFIED"

    # Validate Document Root (CONTAINER)
    assert ds.ValueType == "CONTAINER"
    assert ds.ConceptNameCodeSequence[0].CodeValue == "18748-4"
    assert ds.ConceptNameCodeSequence[0].CodingSchemeDesignator == "LN"

    # Validate Tree of Content Items
    content_types = [item.ValueType for item in ds.ContentSequence]
    assert "CODE" in content_types  # Primary AI Finding
    assert "NUM" in content_types   # Confidence & Measurements
    assert "TEXT" in content_types  # Critical Notification

    # Validate SCT Finding code for Pneumothorax
    finding_item = next(item for item in ds.ContentSequence if item.ValueType == "CODE")
    assert finding_item.ConceptCodeSequence[0].CodeValue == "36118008"
    assert finding_item.ConceptCodeSequence[0].CodingSchemeDesignator == "SCT"
    assert finding_item.ConceptCodeSequence[0].CodeMeaning == "Pneumothorax"


def test_dicom_sr_file_export_and_pydicom_readback(tmp_path):
    """Verify binary .dcm export is a valid DICOM Part 10 file readable by pydicom."""
    engine = DicomSREngine(storage_dir=tmp_path)
    ds = engine.generate_sr_dataset(
        study_id="STUDY-EXPORT-02",
        patient_mrn="MRN-EXP-02",
        patient_name="SMITH^ALICE",
        primary_finding="PNEUMONIA"
    )

    exported_file = engine.export_sr_to_file(ds)
    assert exported_file.exists()
    assert exported_file.stat().st_size > 1000  # Valid binary DICOM dataset

    # Read back using pydicom.dcmread
    read_ds = pydicom.dcmread(str(exported_file))
    assert read_ds.SOPClassUID == ENHANCED_SR_SOP_CLASS
    assert read_ds.PatientID == "MRN-EXP-02"
    assert read_ds.Modality == "SR"
    assert len(read_ds.ContentSequence) >= 3


def test_dicom_sr_api_generate_and_download(client):
    """Test REST API generation and binary download of DICOM SR objects."""
    res = client.post("/api/v1/dicom-sr/generate", json={
        "study_id": "ALV-STAT-09",
        "patient_mrn": "MRN-TRAUMA-4410",
        "patient_name": "Elena Rostova",
        "primary_finding": "PNEUMOTHORAX",
        "confidence_percentage": 99.8,
        "ctr_index": 0.46
    })
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["standard_conformance"] == "DICOM PS 3.16 / TID 1500"
    assert data["file_size_bytes"] > 1000
    assert "SR_ALV-STAT-09_" in data["filename"]

    # Test downloading the binary .dcm file
    dl_res = client.get(data["download_url"])
    assert dl_res.status_code == 200
    assert dl_res.headers["content-type"] == "application/dicom"
    assert len(dl_res.content) == data["file_size_bytes"]

    # Test forwarding over C-STORE
    fwd_res = client.post("/api/v1/dicom-sr/forward", json={
        "study_id": "ALV-STAT-09",
        "target_ae_title": "ORTHANC_VNA"
    })
    assert fwd_res.status_code == 200
    assert fwd_res.json()["forward_details"]["dimse_status"] == "SUCCESS (0x0000)"


# =====================================================================
# STEP 2: DEPLOYMENT VERIFICATION TESTS
# =====================================================================

def test_deployment_verifier_suite():
    """Verify deployment verification checks for engines and storage."""
    # 1. Engine check
    assert check_core_engines() is True

    # 2. Storage permissions check
    storage_dir = Path(__file__).resolve().parent.parent / "data" / "dicom_storage"
    assert check_storage_permissions(storage_dir) is True
