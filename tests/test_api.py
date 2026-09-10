import io
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from api.app import app
from core.sample_generator import ensure_sample_assets
from core.config import settings

@pytest.fixture(scope="module")
def client():
    ensure_sample_assets()
    with TestClient(app) as c:
        yield c

def test_api_health(client):
    """Test healthcheck endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["model_loaded"] is True
    assert "version" in data

def test_api_samples_list(client):
    """Test demonstration samples retrieval endpoint."""
    response = client.get("/api/v1/samples")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert len(data["samples"]) >= 2
    sample_ids = [s["id"] for s in data["samples"]]
    assert "sample_normal" in sample_ids
    assert "sample_pneumonia" in sample_ids

def test_api_predict_success(client):
    """Test diagnostic prediction via multipart file upload."""
    # Create an in-memory sample image
    img = Image.new("L", (200, 200), color=100)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    buf.seek(0)

    response = client.post(
        "/api/v1/predict",
        files={"file": ("test_xray.jpg", buf, "image/jpeg")},
        data={"apply_clahe": "false", "heatmap_alpha": "0.5"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["diagnosis"] in {"PNEUMONIA", "NORMAL"}
    assert "original_image_b64" in data
    assert "gradcam_overlay_b64" in data
    assert data["confidence_percentage"] >= 0.0

def test_api_predict_empty_file(client):
    """Verify rejection of empty file uploads."""
    response = client.post(
        "/api/v1/predict",
        files={"file": ("empty.jpg", b"", "image/jpeg")}
    )
    assert response.status_code == 400

def test_api_clinical_report(client):
    """Test clinical printable report generation endpoint."""
    report_payload = {
        "patient_id": "TEST-PT-99",
        "patient_name": "Test Patient",
        "diagnosis": "PNEUMONIA",
        "confidence_percentage": 97.5,
        "risk_tier": "HIGH_CONFIDENCE_PNEUMONIA",
        "clinical_recommendation": "Urgent specialist review advised.",
        "original_image_b64": "data:image/jpeg;base64,sample1",
        "gradcam_overlay_b64": "data:image/jpeg;base64,sample2"
    }
    response = client.post("/api/v1/report", json=report_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "summary_html" in data
    assert "TEST-PT-99" in data["summary_html"]
