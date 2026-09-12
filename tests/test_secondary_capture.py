"""
Unit & Integration Test Suite for DICOM Secondary Capture (SC) Export & C-STORE Push.
Validates DICOM PS 3.3 compliance, RGB pixel formatting, Grad-CAM burn-in,
quantitative calipers, and DIMSE C-STORE dispatch.
"""
import io
import pytest
import numpy as np
import pydicom
from pydicom.uid import SecondaryCaptureImageStorage
from fastapi.testclient import TestClient

from api.app import app
from core.dicom_handler import synthesize_secondary_capture_dicom
from core.audit_logger import get_audit_logger


client = TestClient(app)


def test_secondary_capture_synthesis_direct():
    """Verify low-level synthesize_secondary_capture_dicom complies with DICOM PS 3.3."""
    H, W = 512, 512
    raw_gray = np.full((H, W), 128, dtype=np.uint8)
    heatmap_norm = np.zeros((H, W), dtype=np.float32)
    # Put a hotspot in the upper-right quadrant
    heatmap_norm[100:250, 300:450] = 0.95

    calipers = [
        {"type": "ruler", "x1": 0.2, "y1": 0.3, "x2": 0.4, "y2": 0.5, "length_mm": 42.5, "label": "42.5 mm"},
        {"type": "ctr", "cardiac": {"x1": 0.3, "y1": 0.6, "x2": 0.7, "y2": 0.6, "mm": 140.0},
                        "thoracic": {"x1": 0.15, "y1": 0.7, "x2": 0.85, "y2": 0.7, "mm": 260.0},
                        "ratio": 0.538},
        {"type": "roi", "cx": 0.7, "cy": 0.35, "rx": 0.1, "ry": 0.1, "areaCm2": 15.2},
        {"type": "arrow", "x1": 0.6, "y1": 0.2, "x2": 0.7, "y2": 0.3, "label": "Opacification"}
    ]

    sc_bytes, ds = synthesize_secondary_capture_dicom(
        original_image=raw_gray,
        heatmap=heatmap_norm,
        patient_id="TEST-PT-001",
        patient_name="DOE^JOHN",
        patient_age="045Y",
        patient_sex="M",
        study_id="STUDY-TEST-SC",
        diagnosis="Pneumonia",
        confidence=94.2,
        dominant_zone="Right Mid Zone",
        calipers=calipers,
        colormap_name="inferno",
        heatmap_alpha=0.45,
        include_banner=True
    )

    # 1. Check binary stream & magic bytes
    assert len(sc_bytes) > 132
    assert sc_bytes[128:132] == b"DICM", "Missing standard DICOM header magic bytes 'DICM' at offset 128"

    # 2. Parse back with pydicom
    parsed_ds = pydicom.dcmread(io.BytesIO(sc_bytes))

    # 3. Check SOP Class & Storage Attributes
    assert parsed_ds.SOPClassUID == SecondaryCaptureImageStorage
    assert parsed_ds.PhotometricInterpretation == "RGB"
    assert parsed_ds.SamplesPerPixel == 3
    assert parsed_ds.PlanarConfiguration == 0
    assert parsed_ds.BitsAllocated == 8
    assert parsed_ds.BitsStored == 8
    assert parsed_ds.HighBit == 7
    assert parsed_ds.BurnedInAnnotation == "YES"
    assert parsed_ds.ConversionType == "WSD"
    assert parsed_ds.PatientID == "TEST-PT-001"
    assert parsed_ds.PatientName == "DOE^JOHN"
    assert parsed_ds.Rows == H
    assert parsed_ds.Columns == W

    # 4. Check Pixel Data is authentic 3-channel RGB
    pixel_array = parsed_ds.pixel_array
    assert pixel_array.shape == (H, W, 3)
    assert pixel_array.dtype == np.uint8
    assert np.mean(pixel_array) > 0


def test_api_export_secondary_capture_endpoint():
    """Verify POST /api/v1/export/secondary-capture generates and streams valid .dcm."""
    wl_res = client.get("/api/v1/worklist")
    assert wl_res.status_code == 200
    res_data = wl_res.json()
    studies = res_data.get("studies", [])
    assert len(studies) > 0
    test_study = studies[0]
    study_id = test_study["study_id"]

    req_body = {
        "study_id": study_id,
        "calipers": [
            {"type": "ruler", "x1": 0.25, "y1": 0.25, "x2": 0.55, "y2": 0.55, "length_mm": 55.0, "label": "55.0 mm"}
        ],
        "colormap": "viridis",
        "include_hud": True,
        "alpha": 0.40
    }

    res = client.post("/api/v1/export/secondary-capture", json=req_body)
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/dicom"
    assert "attachment; filename=\"ALVEON_SC_" in res.headers["content-disposition"]
    assert res.headers["X-SOP-Class-UID"] == "1.2.840.10008.5.1.4.1.1.7"

    # Verify returned bytes are a valid DICOM dataset
    raw_dcm = res.content
    assert raw_dcm[128:132] == b"DICM"
    parsed = pydicom.dcmread(io.BytesIO(raw_dcm))
    assert parsed.SOPClassUID == SecondaryCaptureImageStorage
    assert parsed.PhotometricInterpretation == "RGB"
    assert parsed.BurnedInAnnotation == "YES"
    assert parsed.pixel_array.shape[2] == 3


def test_api_push_secondary_capture_to_local_pacs():
    """Verify POST /api/v1/pacs/push-secondary-capture transmits via C-STORE to port 11112."""
    wl_res = client.get("/api/v1/worklist")
    assert wl_res.status_code == 200
    res_data = wl_res.json()
    studies = res_data.get("studies", [])
    assert len(studies) > 0
    study_id = studies[0]["study_id"]

    push_payload = {
        "study_id": study_id,
        "host": "127.0.0.1",
        "port": 11112,
        "ae_title": "ALVEON_PACS",
        "calipers": [
            {"type": "ruler", "x1": 0.1, "y1": 0.1, "x2": 0.3, "y2": 0.3, "length_mm": 28.0}
        ],
        "colormap": "inferno",
        "include_hud": True,
        "alpha": 0.40
    }

    res = client.post("/api/v1/pacs/push-secondary-capture", json=push_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["success"] is True
    assert data["study_id"] == study_id
    assert "sop_instance_uid" in data
    assert data["destination"] == "ALVEON_PACS@127.0.0.1:11112"
    assert data["latency_ms"] >= 0.0


def test_hipaa_audit_log_captures_secondary_capture():
    """Verify that SC export and C-STORE push are logged in HIPAA audit trail."""
    audit_logger = get_audit_logger()
    recent_events = audit_logger.query(limit=50)
    
    actions = [event.action for event in recent_events]
    assert "DICOM_SC_EXPORT" in actions, f"Expected DICOM_SC_EXPORT in actions: {actions}"
    assert "DICOM_SC_CSTORE_PUSH" in actions, f"Expected DICOM_SC_CSTORE_PUSH in actions: {actions}"
