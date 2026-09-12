"""
Unit and Integration tests for ALVEON 3D Neuro CT Hemorrhage Volumetry & Automated Voxel Segmentation Suite.
Validates Hounsfield Unit thresholding, 3D voxel summation volume, ABC/2 estimation,
midline mass effect shift, multi-planar mask overlay, API endpoints, and PDF dossier generation.
"""

import pytest
from fastapi.testclient import TestClient
from api.app import create_app
from core.neuro_engine import get_neuro_engine
from core.neuro_volumetry import get_neuro_volumetry_engine, NeuroVolumetryResult
from core.volumetric import get_volumetric_engine

@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)

def test_volumetric_engine_has_neuro_series():
    """Verify all 3 neuro series are registered in the VolumetricCTEngine for MPR slicing."""
    engine = get_volumetric_engine()
    series_ids = [s.series_id for s in engine.list_series()]
    assert "BRAIN-CT-STROKE-01" in series_ids
    assert "BRAIN-CT-SDH-02" in series_ids
    assert "BRAIN-CT-ICH-03" in series_ids

def test_ich_volumetry_calculation():
    """Verify 3D voxel segmentation, volume, ABC/2, and surgical alert on Basal Ganglia ICH."""
    engine = get_neuro_engine()
    result, mask_3d = engine.get_volumetry_analysis("BRAIN-CT-ICH-03", hu_min=50.0, hu_max=85.0)

    assert isinstance(result, NeuroVolumetryResult)
    assert result.series_id == "BRAIN-CT-ICH-03"
    assert result.voxel_volume_cm3 >= 30.0  # Acute ICH is large hematoma (~38 cm³)
    assert result.abc2_volume_cm3 > 0.0
    assert result.midline_shift_mm >= 5.0   # Severe mass effect
    assert result.surgical_evacuation_indicated is True
    assert result.triage_priority == "STAT_CRITICAL_SURGICAL"
    assert result.peak_slice_idx == 16
    assert result.peak_slice_area_cm2 > 10.0
    assert result.slices_with_blood_count >= 15
    assert mask_3d.shape == (32, 256, 256)

def test_sdh_volumetry_calculation():
    """Verify Subdural Hematoma segmentation and surgical triage."""
    engine = get_neuro_engine()
    result, mask_3d = engine.get_volumetry_analysis("BRAIN-CT-SDH-02", hu_min=50.0, hu_max=85.0)

    assert result.series_id == "BRAIN-CT-SDH-02"
    assert result.voxel_volume_cm3 > 10.0
    assert result.midline_shift_mm == 5.4
    assert result.surgical_evacuation_indicated is True  # Midline shift > 5mm triggers surgical criteria
    assert result.triage_priority == "STAT_CRITICAL_SURGICAL"

def test_stroke_ischemia_volumetry():
    """Verify ischemic stroke has 0 or minimal hyperdense hemorrhage."""
    engine = get_neuro_engine()
    result, _ = engine.get_volumetry_analysis("BRAIN-CT-STROKE-01", hu_min=50.0, hu_max=85.0)

    # Ischemic stroke is hypodense (22 HU), not hyperdense blood (50-85 HU)
    assert result.voxel_volume_cm3 == 0.0 or result.voxel_volume_cm3 < 2.0
    assert result.surgical_evacuation_indicated is False

def test_slice_mask_generation():
    """Verify 2D RGBA slice mask generation for Axial, Coronal, Sagittal planes."""
    engine = get_neuro_engine()
    rgba_ax, data_url_ax = engine.get_slice_mask("BRAIN-CT-ICH-03", plane="AXIAL", slice_idx=16)
    assert rgba_ax.shape == (256, 256, 4)
    assert data_url_ax.startswith("data:image/png;base64,")

    rgba_cor, data_url_cor = engine.get_slice_mask("BRAIN-CT-ICH-03", plane="CORONAL", slice_idx=128)
    assert rgba_cor.shape == (32, 256, 4)
    assert data_url_cor.startswith("data:image/png;base64,")

def test_pdf_dossier_generation():
    """Verify ReportLab produces valid institutional PDF bytes."""
    engine = get_neuro_engine()
    pdf_bytes = engine.generate_dossier_pdf("BRAIN-CT-ICH-03")
    assert pdf_bytes.startswith(b"%PDF-1.4")
    assert len(pdf_bytes) > 2000

def test_api_segment_hemorrhage_endpoint(client):
    """Verify POST /api/v1/neuro/volumetry/segment-hemorrhage."""
    res = client.post(
        "/api/v1/neuro/volumetry/segment-hemorrhage",
        json={"series_id": "BRAIN-CT-ICH-03", "current_slice_idx": 16, "plane": "AXIAL"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["series_id"] == "BRAIN-CT-ICH-03"
    assert data["voxel_volume_cm3"] >= 30.0
    assert data["surgical_evacuation_indicated"] is True
    assert data["active_slice_area_cm2"] > 0.0
    assert data["active_slice_mask_base64"].startswith("data:image/png;base64,")

def test_api_slice_mask_endpoint(client):
    """Verify GET /api/v1/neuro/volumetry/{series_id}/slice-mask."""
    res = client.get("/api/v1/neuro/volumetry/BRAIN-CT-ICH-03/slice-mask?plane=AXIAL&slice_idx=16")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["plane"] == "AXIAL"
    assert data["slice_idx"] == 16
    assert data["mask_data_url"].startswith("data:image/png;base64,")

def test_api_dossier_pdf_endpoint(client):
    """Verify POST /api/v1/neuro/volumetry/dossier-pdf."""
    res = client.post(
        "/api/v1/neuro/volumetry/dossier-pdf",
        json={"series_id": "BRAIN-CT-ICH-03"}
    )
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/pdf"
    assert res.content.startswith(b"%PDF-1.4")
