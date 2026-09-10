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
    assert data["project_name"] == "ALVEON"
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
    """Test diagnostic prediction via multipart file upload with colormap and zonation."""
    img = Image.new("L", (200, 200), color=100)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    buf.seek(0)

    response = client.post(
        "/api/v1/predict",
        files={"file": ("test_xray.jpg", buf, "image/jpeg")},
        data={"apply_clahe": "false", "colormap": "inferno", "heatmap_alpha": "0.5"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["diagnosis"] in {"PNEUMONIA", "NORMAL"}
    assert "zonation" in data
    assert "dominant_zone" in data["zonation"]
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
    """Test clinical consultation report generation endpoint."""
    report_payload = {
        "patient_id": "ALV-PT-99",
        "patient_name": "Test Patient",
        "diagnosis": "PNEUMONIA",
        "confidence_percentage": 97.5,
        "risk_tier": "HIGH_CONFIDENCE_PNEUMONIA",
        "clinical_recommendation": "Urgent specialist review advised.",
        "zonation": {
            "right_upper_lobe_pct": 10.0,
            "right_lower_lobe_pct": 75.0,
            "left_upper_lobe_pct": 8.0,
            "left_lower_lobe_pct": 7.0,
            "dominant_zone": "Right Lower Lobe"
        },
        "original_image_b64": "data:image/jpeg;base64,sample1",
        "gradcam_overlay_b64": "data:image/jpeg;base64,sample2"
    }
    response = client.post("/api/v1/report", json=report_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "summary_html" in data
    assert "ALV-PT-99" in data["summary_html"]
    assert "ALVEON THORACIC PACS" in data["summary_html"]
