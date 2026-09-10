import io
import base64
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from api.app import app
from core.pdf_generator import generate_clinical_report_pdf

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

def test_pdf_generation_valid_bytes():
    """Verify that generate_clinical_report_pdf returns valid PDF-1.4 binary data."""
    # Create sample image
    img = Image.new("RGB", (120, 120), color=(80, 120, 180))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    b64 = "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()

    payload = {
        "study_id": "ALV-PDF-01",
        "patient_name": "Vance, Eleanor",
        "patient_mrn": "MRN-90214-ER",
        "patient_age_sex": "64Y / Female",
        "study_time": "2026-09-10 22:30 EST",
        "modality": "DX",
        "priority": "STAT_CRITICAL",
        "diagnosis": "PNEUMONIA",
        "is_pneumonia": True,
        "confidence_percentage": 94.8,
        "dominant_zone": "Right Lower Lobe",
        "zonation": {
            "rul_percentage": 10.5,
            "rll_percentage": 76.2,
            "lul_percentage": 4.1,
            "lll_percentage": 9.2
        },
        "original_image_b64": b64,
        "gradcam_overlay_b64": b64,
        "physician_name": "Dr. Eleanor Vance, MD",
        "physician_license": "RAD-US-89410",
        "audit_hash": "5BAB7D64C1123400",
        "status": "SIGNED"
    }

    pdf_buffer = generate_clinical_report_pdf(payload)
    data = pdf_buffer.read()

    assert len(data) > 3000
    assert data.startswith(b"%PDF-1.4")
    assert b"%%EOF" in data

def test_pdf_post_endpoint(client):
    """Test POST /api/v1/report/pdf endpoint streams certified PDF file."""
    payload = {
        "study_id": "ALV-TEST-PDF",
        "patient_name": "Kovacs, Laszlo",
        "patient_mrn": "MRN-KOVACS-01",
        "is_pneumonia": False,
        "diagnosis": "NORMAL",
        "confidence_percentage": 98.2
    }
    response = client.post("/api/v1/report/pdf", json=payload)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "attachment" in response.headers.get("content-disposition", "")
    assert response.content.startswith(b"%PDF")

def test_pdf_get_study_endpoint(client):
    """Test GET /api/v1/worklist/{study_id}/pdf streams PDF for any queue study."""
    # First get a study from worklist
    res = client.get("/api/v1/worklist")
    assert res.status_code == 200
    study_id = res.json()["studies"][0]["study_id"]

    pdf_res = client.get(f"/api/v1/worklist/{study_id}/pdf")
    assert pdf_res.status_code == 200
    assert pdf_res.headers["content-type"] == "application/pdf"
    assert len(pdf_res.content) > 3000
    assert pdf_res.content.startswith(b"%PDF")
