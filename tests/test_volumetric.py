"""
Tests for ALVEON 3D Volumetric CT Engine & Multi-Planar Reconstruction (MPR)
Verifies 3D volume dimensions, orthogonal planar slicing (Axial, Coronal, Sagittal),
Hounsfield Unit (HU) windowing transformations, and REST endpoints.
"""

import pytest
import numpy as np
from fastapi.testclient import TestClient
from api.app import app
from core.volumetric import get_volumetric_engine, WINDOW_PRESETS

client = TestClient(app)


def test_volumetric_engine_series_list():
    engine = get_volumetric_engine()
    series = engine.list_series()
    assert len(series) >= 2
    assert any(s.series_id == "SERIES-CT-CHEST-3201" for s in series)
    assert any(s.series_id == "SERIES-CT-NORMAL-3202" for s in series)


def test_orthogonal_slice_extraction():
    engine = get_volumetric_engine()
    series_id = "SERIES-CT-CHEST-3201"

    # 1. Axial slice (XY plane)
    raw_ax, ax_8bit, meta_ax = engine.extract_orthogonal_slice(
        series_id=series_id,
        orientation="AXIAL",
        slice_idx=16,
        window_preset="LUNG"
    )
    assert ax_8bit.shape == (160, 160)
    assert ax_8bit.dtype == np.uint8
    assert meta_ax["orientation"] == "AXIAL"
    assert meta_ax["window_width"] == 1500
    assert meta_ax["window_level"] == -600

    # 2. Coronal slice (XZ plane)
    raw_cor, cor_8bit, meta_cor = engine.extract_orthogonal_slice(
        series_id=series_id,
        orientation="CORONAL",
        slice_idx=80,
        window_preset="MEDIASTINUM"
    )
    assert cor_8bit.shape == (32, 160)
    assert meta_cor["orientation"] == "CORONAL"
    assert meta_cor["window_width"] == 350
    assert meta_cor["window_level"] == 40

    # 3. Sagittal slice (YZ plane)
    raw_sag, sag_8bit, meta_sag = engine.extract_orthogonal_slice(
        series_id=series_id,
        orientation="SAGITTAL",
        slice_idx=80,
        window_preset="BONE"
    )
    assert sag_8bit.shape == (32, 160)
    assert meta_sag["orientation"] == "SAGITTAL"
    assert meta_sag["window_width"] == 2000
    assert meta_sag["window_level"] == 500


def test_hounsfield_unit_window_level_math():
    engine = get_volumetric_engine()
    # Test array with distinct HU landmarks
    test_hu = np.array([-1000, -600, 0, 40, 1000], dtype=np.int16)

    # Mediastinum Window (W: 350, L: 40)
    # MinVal = 40 - 175 = -135
    # MaxVal = 40 + 175 = 215
    res = engine.apply_window_level(test_hu, window_width=350, window_level=40)
    assert res[0] == 0    # -1000 is far below MinVal -> 0
    assert res[1] == 0    # -600 is below MinVal -> 0
    assert res[3] == 127  # 40 is exactly mid-level -> ~127
    assert res[4] == 255  # 1000 is far above MaxVal -> 255


def test_api_volumetric_endpoints():
    # 1. List series
    res_list = client.get("/api/v1/volumetric/series")
    assert res_list.status_code == 200
    assert res_list.json()["total_series"] >= 2

    # 2. Get single slice
    res_slice = client.get("/api/v1/volumetric/SERIES-CT-CHEST-3201/slice?orientation=AXIAL&slice_idx=16&window_preset=LUNG")
    assert res_slice.status_code == 200
    s_data = res_slice.json()
    assert s_data["orientation"] == "AXIAL"
    assert s_data["slice_index"] == 16
    assert s_data["data_url"].startswith("data:image/png;base64,")

    # 3. Get synchronized Tri-Planar MPR
    res_mpr = client.post(
        "/api/v1/volumetric/SERIES-CT-CHEST-3201/mpr",
        json={
            "axial_idx": 16,
            "coronal_idx": 80,
            "sagittal_idx": 80,
            "window_preset": "LUNG"
        }
    )
    assert res_mpr.status_code == 200
    mpr_data = res_mpr.json()
    assert "axial" in mpr_data
    assert "coronal" in mpr_data
    assert "sagittal" in mpr_data
    assert mpr_data["crosshairs"]["axial"] == 16
