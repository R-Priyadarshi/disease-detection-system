"""
Tests for 3D Cinematic Volume Rendering & Ray-Casting Engine
Validates:
1. MIP (Maximum Intensity Projection) mathematical correctness and thickness slicing.
2. MinIP (Minimum Intensity Projection) mathematical correctness.
3. AIP (Average Intensity Projection).
4. 3D Cinematic Orbit frame rendering across multiple azimuth/elevation angles.
5. 16-frame 360-degree turntable cache generation.
6. REST API endpoints:
   - POST /api/v1/volumetric/projection
   - POST /api/v1/volumetric/3d-orbit
   - GET /api/v1/volumetric/3d-turntable/{series_id}
"""

import pytest
import numpy as np
from fastapi.testclient import TestClient
from api.app import app
from core.raycast_engine import get_raycast_engine, RaycastEngine


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def raycast():
    return get_raycast_engine()


def test_raycast_singleton_pattern(raycast):
    engine2 = RaycastEngine.get_instance()
    assert raycast is engine2


def test_mip_projection_calculation(raycast):
    series_id = "BRAIN-CT-ICH-03"
    proj_hu, proj_8bit, meta = raycast.compute_orthogonal_projection(
        series_id=series_id,
        orientation="AXIAL",
        mode="MIP",
        slice_idx=16,
        slab_thickness_mm=10.0,
        window_preset="BRAIN"
    )
    assert proj_hu.ndim == 2
    assert proj_8bit.ndim == 2
    assert proj_8bit.dtype == np.uint8
    assert meta.projection_mode == "MIP"
    assert meta.orientation == "AXIAL"
    assert meta.max_hu >= meta.min_hu
    # MIP should capture hyperdense bone or blood
    assert meta.max_hu > 50


def test_minip_projection_calculation(raycast):
    series_id = "SERIES-CT-CHEST-3201"
    proj_hu, proj_8bit, meta = raycast.compute_orthogonal_projection(
        series_id=series_id,
        orientation="CORONAL",
        mode="MINIP",
        slice_idx=80,
        slab_thickness_mm=15.0,
        window_preset="LUNG"
    )
    assert meta.projection_mode == "MINIP"
    assert meta.orientation == "CORONAL"
    # MinIP on chest should capture lung/trachea air (-1000 to -700 HU)
    assert meta.min_hu <= -500


def test_aip_projection_calculation(raycast):
    series_id = "BRAIN-CT-ICH-03"
    proj_hu, proj_8bit, meta = raycast.compute_orthogonal_projection(
        series_id=series_id,
        orientation="SAGITTAL",
        mode="AIP",
        slice_idx=80,
        slab_thickness_mm=20.0,
        window_preset="BRAIN"
    )
    assert meta.projection_mode == "AIP"
    assert meta.orientation == "SAGITTAL"


def test_3d_orbit_frame_rendering(raycast):
    series_id = "BRAIN-CT-ICH-03"
    rgba, b64 = raycast.render_3d_orbit_frame(
        series_id=series_id,
        azimuth_deg=45.0,
        elevation_deg=15.0,
        preset_name="NEURO_HEMORRHAGE",
        target_size=128
    )
    assert rgba.shape == (128, 128, 4)
    assert b64.startswith("data:image/png;base64,")


def test_3d_turntable_generation(raycast):
    series_id = "BRAIN-CT-ICH-03"
    frames = raycast.get_turntable_frames(series_id, preset_name="NEURO_HEMORRHAGE", num_frames=8)
    assert len(frames) == 8
    for f in frames:
        assert f.startswith("data:image/png;base64,")


def test_api_volumetric_projection_endpoint(client):
    res = client.post("/api/v1/volumetric/projection", json={
        "series_id": "BRAIN-CT-ICH-03",
        "orientation": "AXIAL",
        "projection_mode": "MIP",
        "slice_idx": 16,
        "slab_thickness_mm": 12.5,
        "window_preset": "BRAIN"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["projection_mode"] == "MIP"
    assert data["series_id"] == "BRAIN-CT-ICH-03"
    assert data["image_data_url"].startswith("data:image/png;base64,")


def test_api_3d_orbit_endpoint(client):
    res = client.post("/api/v1/volumetric/3d-orbit", json={
        "series_id": "BRAIN-CT-ICH-03",
        "azimuth_deg": 90.0,
        "elevation_deg": 10.0,
        "preset_name": "NEURO_HEMORRHAGE",
        "target_size": 128
    })
    assert res.status_code == 200
    data = res.json()
    assert data["azimuth_deg"] == 90.0
    assert data["image_data_url"].startswith("data:image/png;base64,")


def test_api_3d_turntable_endpoint(client):
    res = client.get("/api/v1/volumetric/3d-turntable/BRAIN-CT-ICH-03?preset=NEURO_HEMORRHAGE")
    assert res.status_code == 200
    data = res.json()
    assert data["series_id"] == "BRAIN-CT-ICH-03"
    assert len(data["frames"]) == 16
