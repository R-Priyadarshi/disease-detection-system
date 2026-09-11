"""
ALVEON Production Suite - Four Engineering Pathways Automated Test Suite
========================================================================
Validates Options A, B, C, and D end-to-end:
  - Option A: Containerization & Universal Cloud Deployment Configuration
  - Option B: Deep Learning Weights & Explainable Grad-CAM Engine
  - Option C: DICOMweb & DIMSE PACS Integration
  - Option D: User Authentication & Report / Caliper Persistence
"""

import os
import json
import pytest
from pathlib import Path
from fastapi.testclient import TestClient
import numpy as np
import cv2

from api.app import app
from core.database import (
    get_db_connection,
    get_user_by_username,
    save_radiology_report,
    get_report_by_study,
    list_recent_reports
)
from core.auth import authenticate_user, create_access_token
from core.model import get_model
from core.gradcam import GradCAMGenerator

client = TestClient(app)
ROOT_DIR = Path(__file__).resolve().parent.parent

# --- OPTION A: Cloud Deployment & Containerization ---

def test_option_a_dockerfile_and_render_config():
    dockerfile_path = ROOT_DIR / "Dockerfile"
    render_path = ROOT_DIR / "deploy" / "render.yaml"
    compose_path = ROOT_DIR / "docker-compose.yml"

    assert dockerfile_path.exists(), "Dockerfile must exist"
    assert render_path.exists(), "deploy/render.yaml blueprint must exist"
    assert compose_path.exists(), "docker-compose.yml must exist"

    df_content = dockerfile_path.read_text()
    assert "EXPOSE 8000 7860 11112" in df_content or "7860" in df_content, "Hugging Face Spaces port 7860 must be exposed"
    assert "PORT:-8000" in df_content, "Dynamic PORT environment variable must be handled"


# --- OPTION B: Real Deep Learning Model & Saliency ---

def test_option_b_deep_learning_forward_pass_and_gradcam():
    model = get_model()
    assert model.model is not None, "Model weights must be loaded from TESTCNN.hdf5"
    assert len(model.model.layers) == 11, "Expected 11 layers in CNN architecture"

    # Synthetic chest radiograph test
    test_img = np.full((150, 150), 120, dtype=np.uint8)
    cv2.circle(test_img, (50, 100), 25, 220, -1)  # Simulate right lower lobe focal infiltrate
    tensor = test_img.reshape(1, 150, 150, 1).astype(np.float32) / 255.0

    # 1. Forward Pass
    prob = float(model.model.predict(tensor, verbose=0)[0][0])
    assert 0.0 <= prob <= 1.0, "Model sigmoid output must be between 0.0 and 1.0"

    # 2. Grad-CAM & Zonation
    gradcam = GradCAMGenerator(model)
    blended, heatmap, zonation = gradcam.generate_overlay(test_img, tensor, colormap_name="inferno", alpha=0.45)
    assert heatmap.shape == (150, 150, 3), "Heatmap must be 3-channel RGB"
    assert "dominant_zone" in zonation, "Zonation must include dominant zone"
    assert "right_lower_lobe_pct" in zonation, "Zonation must calculate right lower lobe percentage"

    # 3. Multi-label Inference
    multilabel = model.predict_multilabel(tensor, test_img, zonation)
    assert "diagnosis" in multilabel
    assert "all_findings" in multilabel
    assert len(multilabel["all_findings"]) >= 5


# --- OPTION C: Live Hospital PACS Integration (DICOMweb) ---

def test_option_c_dicomweb_part18_services():
    res = client.get("/dicomweb/studies")
    assert res.status_code == 200, "DICOMweb QIDO-RS /dicomweb/studies must return HTTP 200"
    studies = res.json()
    assert isinstance(studies, list), "DICOMweb studies response must be a JSON array"
    assert len(studies) > 0, "At least one DICOM study must be discoverable"

    # Verify standard PS 3.18 DICOM tag structure
    first_study = studies[0]
    assert "00080018" in first_study or "0020000D" in first_study or "00080050" in first_study


# --- OPTION D: User Authentication & Saved Radiology Reports ---

def test_option_d_auth_and_sqlite_report_persistence():
    # 1. PBKDF2 Database Authentication
    user = authenticate_user("dr.vance", "Alveon2026!")
    assert user is not None, "dr.vance must authenticate against SQLite database"
    assert user.role.value == "ATTENDING_RADIOLOGIST"

    token = create_access_token(user)
    assert token and "." in token, "JWT token must be properly structured"

    # 2. Save Report with Caliper Measurements
    study_uid = "STUDY-TEST-CALIPER-99"
    calipers = [
        {"label": "Subpleural Consolidation", "lengthMm": 38.4, "startX": 120, "startY": 200, "endX": 250, "endY": 210},
        {"label": "CTR Cardiac Width", "lengthMm": 142.1, "startX": 80, "startY": 300, "endX": 360, "endY": 305}
    ]
    report_payload = {
        "study_uid": study_uid,
        "patient_mrn": "MRN-PATHWAY-01",
        "patient_name": "Marcus Kane",
        "examination_technique": "Digital Chest Radiograph, PA Projection",
        "clinical_indication": "Trauma Bay Evaluation",
        "impression": "Focal dense consolidation in right lower lobe. Recommend broad-spectrum antibiotics.",
        "acr_actionable_code": "ACR Category 2",
        "caliper_measurements": calipers,
        "status": "FINAL_SIGNED"
    }

    save_res = client.post(
        "/api/v1/reports/save",
        json=report_payload,
        headers={"Authorization": f"Bearer {token}"}
    )
    assert save_res.status_code == 200, f"Report save failed: {save_res.text}"
    saved_data = save_res.json()
    assert saved_data["status"] == "success"
    assert saved_data["caliper_count"] == 2
    assert saved_data["signature_hash"] is not None

    # 3. Retrieve Saved Report from SQLite
    get_res = client.get(f"/api/v1/reports/study/{study_uid}")
    assert get_res.status_code == 200
    retrieved = get_res.json()
    assert retrieved["patient_mrn"] == "MRN-PATHWAY-01"
    assert retrieved["attesting_physician"] == "Dr. Eleanor Vance, MD"
    assert len(retrieved["caliper_measurements"]) == 2
    assert retrieved["caliper_measurements"][0]["lengthMm"] == 38.4

    # 4. List Reports
    list_res = client.get("/api/v1/reports")
    assert list_res.status_code == 200
    assert list_res.json()["total_reports"] >= 1
