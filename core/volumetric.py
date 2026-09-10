"""
ALVEON 3D Volumetric CT/MRI Engine & Multi-Planar Reconstruction (MPR)
Provides 3D voxel stack processing, real-time orthogonal planar slicing (Axial, Coronal, Sagittal),
Hounsfield Unit (HU) windowing transformations, and cine loop navigation.
"""

import io
import base64
import numpy as np
from PIL import Image
from typing import Dict, Any, List, Optional, Tuple
from pydantic import BaseModel, Field


class HUWindowPreset(BaseModel):
    name: str
    description: str
    window_width: int
    window_level: int


# Standard Clinical CT Windowing Presets
WINDOW_PRESETS: Dict[str, HUWindowPreset] = {
    "LUNG": HUWindowPreset(
        name="LUNG",
        description="Pulmonary Parenchyma & Airways (W:1500, L:-600)",
        window_width=1500,
        window_level=-600
    ),
    "MEDIASTINUM": HUWindowPreset(
        name="MEDIASTINUM",
        description="Mediastinum, Cardiac Chambers & Effusion (W:350, L:40)",
        window_width=350,
        window_level=40
    ),
    "BONE": HUWindowPreset(
        name="BONE",
        description="Thoracic Spine, Ribs & Cortical Density (W:2000, L:500)",
        window_width=2000,
        window_level=500
    ),
    "BRAIN": HUWindowPreset(
        name="BRAIN",
        description="Cerebral Parenchyma / High Contrast (W:80, L:40)",
        window_width=80,
        window_level=40
    ),
    "SUBDURAL": HUWindowPreset(
        name="SUBDURAL",
        description="Subdural / Epidural Blood (W:130, L:75)",
        window_width=130,
        window_level=75
    ),
    "STROKE": HUWindowPreset(
        name="STROKE",
        description="Stroke / Early Ischemia (W:35, L:35)",
        window_width=35,
        window_level=35
    )
}


class VolumetricSeries(BaseModel):
    series_id: str
    patient_id: str
    patient_name: str
    modality: str  # CT or MR
    description: str
    num_slices: int
    dimensions: List[int]  # [depth, height, width]
    slice_thickness_mm: float
    pixel_spacing_mm: List[float]
    default_window: str = "LUNG"


class VolumetricCTEngine:
    """Manages 3D voxel volumes, MPR re-slicing, and HU window transformations."""

    _instance: Optional['VolumetricCTEngine'] = None

    def __init__(self):
        # In-memory storage for 3D volumes: {series_id: np.ndarray (shape D, H, W, dtype=int16 in HU)}
        self._volumes: Dict[str, np.ndarray] = {}
        self._metadata: Dict[str, VolumetricSeries] = {}
        self._initialize_default_3d_cohort()

    @classmethod
    def get_instance(cls) -> 'VolumetricCTEngine':
        if cls._instance is None:
            cls._instance = VolumetricCTEngine()
        return cls._instance

    def _initialize_default_3d_cohort(self):
        """Generates anatomically grounded 3D chest CT volumes for clinical demonstration."""
        # 1. Emergency Chest CT: 32-slice Thoracic Trauma & Infiltration
        series_id_1 = "SERIES-CT-CHEST-3201"
        vol1 = self._synthesize_3d_chest_ct(
            depth=32, height=160, width=160,
            has_consolidation=True, has_effusion=True
        )
        self._volumes[series_id_1] = vol1
        self._metadata[series_id_1] = VolumetricSeries(
            series_id=series_id_1,
            patient_id="MRN-HASTINGS-7741",
            patient_name="Hastings^Rose",
            modality="CT",
            description="Chest CT Angiogram (1.25mm Thoracic Reconstructed Stack)",
            num_slices=32,
            dimensions=[32, 160, 160],
            slice_thickness_mm=2.5,
            pixel_spacing_mm=[1.2, 1.2],
            default_window="LUNG"
        )

        # 2. Routine High-Resolution Chest CT: 32-slice Baseline
        series_id_2 = "SERIES-CT-NORMAL-3202"
        vol2 = self._synthesize_3d_chest_ct(
            depth=32, height=160, width=160,
            has_consolidation=False, has_effusion=False
        )
        self._volumes[series_id_2] = vol2
        self._metadata[series_id_2] = VolumetricSeries(
            series_id=series_id_2,
            patient_id="MRN-DRAKE-1109",
            patient_name="Drake^Vivian",
            modality="CT",
            description="HRCT Chest Screening (Inspiratory Volumetric)",
            num_slices=32,
            dimensions=[32, 160, 160],
            slice_thickness_mm=2.5,
            pixel_spacing_mm=[1.2, 1.2],
            default_window="MEDIASTINUM"
        )

        # 3. 3D Neuro CT Series: Acute Stroke & Subdural Hematoma
        try:
            from core.neuro_engine import get_neuro_engine
            neuro = get_neuro_engine()
            for s_id, s in neuro.series_registry.items():
                self._volumes[s_id] = s.volume_hu.astype(np.int16)
                self._metadata[s_id] = VolumetricSeries(
                    series_id=s.series_id,
                    patient_id=s.patient_mrn,
                    patient_name=s.patient_name,
                    modality="CT",
                    description=f"{s.primary_neuro_finding} (32 Slices)",
                    num_slices=s.matrix_shape[0],
                    dimensions=list(s.matrix_shape),
                    slice_thickness_mm=2.5,
                    pixel_spacing_mm=[1.0, 1.0],
                    default_window="BRAIN"
                )
        except Exception:
            pass

    def _synthesize_3d_chest_ct(
        self, depth: int = 32, height: int = 160, width: int = 160,
        has_consolidation: bool = False, has_effusion: bool = False
    ) -> np.ndarray:
        """
        Synthesizes a realistic 3D thoracic CT volume in true Hounsfield Units (HU):
        - Ambient air: -1000 HU
        - Subcutaneous fat: -100 HU
        - Muscle / Soft Tissue wall: +40 HU
        - Ribs & Thoracic Spine: +700 HU
        - Pulmonary Parenchyma: -750 HU
        - Trachea & Mainstem Bronchi: -980 HU
        - Heart / Great Vessels: +45 HU
        - Consolidation (if present): +35 HU
        - Pleural Effusion (if present): +15 HU
        """
        vol = np.full((depth, height, width), -1000, dtype=np.int16)

        # Coordinate grids
        z_coords = np.linspace(0, 1, depth)
        y_grid, x_grid = np.ogrid[:height, :width]
        cy, cx = height / 2.0, width / 2.0

        for z_idx in range(depth):
            z_rel = z_coords[z_idx]  # 0.0 (Apex) to 1.0 (Diaphragm)

            # Thoracic outer elliptical body contour
            body_ry = height * 0.40
            body_rx = width * 0.44
            body_dist = ((y_grid - cy) / body_ry) ** 2 + ((x_grid - cx) / body_rx) ** 2
            vol[z_idx, body_dist <= 1.0] = 40  # Soft tissue (+40 HU)

            # Subcutaneous fat layer
            fat_mask = (body_dist > 0.88) & (body_dist <= 1.0)
            vol[z_idx, fat_mask] = -90

            # Thoracic ribs & spine (Bone ~ +750 HU)
            # Spine (posterior midline)
            spine_dist = ((y_grid - (cy + body_ry * 0.70)) / 10.0) ** 2 + ((x_grid - cx) / 8.0) ** 2
            vol[z_idx, spine_dist <= 1.0] = 850
            # Rib ring
            rib_ring = (body_dist >= 0.78) & (body_dist <= 0.84)
            rib_ang = np.arctan2(y_grid - cy, x_grid - cx)
            rib_segment = (np.sin(rib_ang * 6.0) > 0.3) & rib_ring
            vol[z_idx, rib_segment] = 750

            # Lungs (Air/Parenchyma ~ -750 HU)
            if 0.15 <= z_rel <= 0.90:
                lung_scale = np.sin((z_rel - 0.15) / 0.75 * np.pi) ** 0.5
                # Right Lung
                rl_cy = cy - 2.0
                rl_cx = cx - (width * 0.22)
                rl_dist = ((y_grid - rl_cy) / (height * 0.28 * lung_scale + 1e-3)) ** 2 + \
                          ((x_grid - rl_cx) / (width * 0.17 * lung_scale + 1e-3)) ** 2
                vol[z_idx, rl_dist <= 1.0] = -750

                # Left Lung
                ll_cy = cy - 2.0
                ll_cx = cx + (width * 0.22)
                ll_dist = ((y_grid - ll_cy) / (height * 0.28 * lung_scale + 1e-3)) ** 2 + \
                          ((x_grid - ll_cx) / (width * 0.16 * lung_scale + 1e-3)) ** 2
                vol[z_idx, ll_dist <= 1.0] = -750

                # Mediastinum / Heart (+45 HU)
                if 0.35 <= z_rel <= 0.85:
                    heart_scale = np.sin((z_rel - 0.35) / 0.50 * np.pi)
                    h_cy = cy + 4.0
                    h_cx = cx + (width * 0.05 * heart_scale)
                    h_dist = ((y_grid - h_cy) / (height * 0.18 * heart_scale + 1e-3)) ** 2 + \
                             ((x_grid - h_cx) / (width * 0.16 * heart_scale + 1e-3)) ** 2
                    vol[z_idx, h_dist <= 1.0] = 45

                # Bronchovascular tree (fine structures ~ +20 HU)
                bv_mask = (rl_dist > 0.2) & (rl_dist < 0.6) & (np.sin(x_grid * 0.4 + y_grid * 0.3) > 0.85)
                vol[z_idx, bv_mask & (rl_dist <= 1.0)] = 20
                bv_lmask = (ll_dist > 0.2) & (ll_dist < 0.6) & (np.sin(x_grid * 0.4 - y_grid * 0.3) > 0.85)
                vol[z_idx, bv_lmask & (ll_dist <= 1.0)] = 20

                # Pathological features (if enabled)
                if has_consolidation and 0.45 <= z_rel <= 0.75:
                    # Focal right lower/mid lobe consolidation (+35 HU)
                    cons_dist = ((y_grid - (rl_cy + 15)) / 14.0) ** 2 + ((x_grid - (rl_cx + 8)) / 12.0) ** 2
                    vol[z_idx, (cons_dist <= 1.0) & (rl_dist <= 1.0)] = 35

                if has_effusion and 0.65 <= z_rel <= 0.90:
                    # Dependent posterior left pleural fluid (+15 HU)
                    eff_dist = ((y_grid - (cy + height * 0.20)) / 18.0) ** 2 + ((x_grid - ll_cx) / 16.0) ** 2
                    vol[z_idx, (eff_dist <= 1.0) & (ll_dist <= 1.0)] = 18

            # Central Trachea / Carina (-980 HU)
            if z_rel <= 0.40:
                trach_dist = ((y_grid - (cy - height * 0.12)) / 6.0) ** 2 + ((x_grid - cx) / 5.0) ** 2
                vol[z_idx, trach_dist <= 1.0] = -980

        return vol

    def list_series(self) -> List[VolumetricSeries]:
        """Returns metadata for all available 3D volumetric series."""
        return list(self._metadata.values())

    def get_series(self, series_id: str) -> Optional[VolumetricSeries]:
        """Fetches metadata for a specific 3D series."""
        return self._metadata.get(series_id)

    def apply_window_level(
        self, slice_hu: np.ndarray, window_width: int, window_level: int
    ) -> np.ndarray:
        """
        Applies clinical Hounsfield Unit window/level linear transformation:
        MinVal = Level - Width / 2
        MaxVal = Level + Width / 2
        Intensity = clip((HU - MinVal) / Width * 255, 0, 255)
        """
        min_val = window_level - (window_width / 2.0)
        max_val = window_level + (window_width / 2.0)

        # Vectorized clamping and scaling
        scaled = (slice_hu.astype(np.float32) - min_val) / (max_val - min_val) * 255.0
        clipped = np.clip(scaled, 0.0, 255.0).astype(np.uint8)
        return clipped

    def extract_orthogonal_slice(
        self,
        series_id: str,
        orientation: str,  # "AXIAL", "CORONAL", "SAGITTAL"
        slice_idx: int,
        window_preset: str = "LUNG",
        custom_width: Optional[int] = None,
        custom_level: Optional[int] = None
    ) -> Tuple[np.ndarray, np.ndarray, Dict[str, Any]]:
        """
        Extracts a 2D planar slice from the 3D volume along any orthogonal orientation:
        - AXIAL (XY plane): slice at depth index z
        - CORONAL (XZ plane): slice at height index y
        - SAGITTAL (YZ plane): slice at width index x
        Returns: (raw_hu_slice, windowed_8bit_slice, slice_metadata)
        """
        vol = self._volumes.get(series_id)
        if vol is None:
            raise KeyError(f"Volumetric series '{series_id}' not found.")

        d, h, w = vol.shape
        orient = orientation.upper()

        if orient == "AXIAL":
            safe_idx = max(0, min(slice_idx, d - 1))
            slice_hu = vol[safe_idx, :, :]
            location_mm = float(safe_idx * 2.5 - (d * 2.5 / 2.0))
            max_slices = d
        elif orient == "CORONAL":
            safe_idx = max(0, min(slice_idx, h - 1))
            # Slice along Y axis: shape is (D, W) -> resized to match aspect ratio
            slice_hu = vol[:, safe_idx, :]
            location_mm = float(safe_idx * 1.2 - (h * 1.2 / 2.0))
            max_slices = h
        elif orient == "SAGITTAL":
            safe_idx = max(0, min(slice_idx, w - 1))
            # Slice along X axis: shape is (D, H)
            slice_hu = vol[:, :, safe_idx]
            location_mm = float(safe_idx * 1.2 - (w * 1.2 / 2.0))
            max_slices = w
        else:
            raise ValueError(f"Invalid orientation '{orientation}'. Choose AXIAL, CORONAL, or SAGITTAL.")

        # Resolve window settings
        preset = WINDOW_PRESETS.get(window_preset.upper(), WINDOW_PRESETS["LUNG"])
        ww = custom_width if custom_width is not None else preset.window_width
        wl = custom_level if custom_level is not None else preset.window_level

        # Windowing
        slice_8bit = self.apply_window_level(slice_hu, ww, wl)

        meta = {
            "series_id": series_id,
            "orientation": orient,
            "slice_index": safe_idx,
            "max_slices": max_slices,
            "slice_location_mm": round(location_mm, 2),
            "window_preset": window_preset,
            "window_width": ww,
            "window_level": wl,
            "mean_hu": float(np.mean(slice_hu)),
            "min_hu": int(np.min(slice_hu)),
            "max_hu": int(np.max(slice_hu))
        }

        return slice_hu, slice_8bit, meta

    def slice_to_data_url(self, slice_8bit: np.ndarray, format: str = "PNG") -> str:
        """Converts an 8-bit slice matrix into an optimized Base64 data URL."""
        img = Image.fromarray(slice_8bit, mode='L')
        buf = io.BytesIO()
        img.save(buf, format=format)
        encoded = base64.b64encode(buf.getvalue()).decode('utf-8')
        mime = "image/png" if format.upper() == "PNG" else "image/jpeg"
        return f"data:{mime};base64,{encoded}"

    def get_tri_planar_mpr(
        self,
        series_id: str,
        axial_idx: int = 16,
        coronal_idx: int = 80,
        sagittal_idx: int = 80,
        window_preset: str = "LUNG"
    ) -> Dict[str, Any]:
        """
        Extracts synchronized Tri-Planar Multi-Planar Reconstruction views:
        Axial, Coronal, and Sagittal planes with crosshair intersections.
        """
        _, ax_8bit, ax_meta = self.extract_orthogonal_slice(
            series_id, "AXIAL", axial_idx, window_preset
        )
        _, cor_8bit, cor_meta = self.extract_orthogonal_slice(
            series_id, "CORONAL", coronal_idx, window_preset
        )
        _, sag_8bit, sag_meta = self.extract_orthogonal_slice(
            series_id, "SAGITTAL", sagittal_idx, window_preset
        )

        return {
            "series_id": series_id,
            "window_preset": window_preset,
            "crosshairs": {
                "axial": axial_idx,
                "coronal": coronal_idx,
                "sagittal": sagittal_idx
            },
            "axial": {
                "data_url": self.slice_to_data_url(ax_8bit),
                "metadata": ax_meta
            },
            "coronal": {
                "data_url": self.slice_to_data_url(cor_8bit),
                "metadata": cor_meta
            },
            "sagittal": {
                "data_url": self.slice_to_data_url(sag_8bit),
                "metadata": sag_meta
            }
        }


def get_volumetric_engine() -> VolumetricCTEngine:
    """Singleton getter for 3D volumetric engine."""
    return VolumetricCTEngine.get_instance()
