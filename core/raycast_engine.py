"""
ALVEON 3D Cinematic Volume Rendering & Ray-Casting Engine
Provides:
1. Maximum Intensity Projection (MIP) for CT Angiography & Vascular Enhancement.
2. Minimum Intensity Projection (MinIP) for Airway Tree & Hypodense Pathology.
3. Average Intensity Projection (AIP) for Conventional Radiograph Emulation.
4. Variable Slab Thickness Orthogonal Projections (Axial, Coronal, Sagittal).
5. 3D Cinematic Turntable Ray-Marcher with Transfer Function Opacity Compositing.
"""

import io
import math
import base64
import numpy as np
import cv2
from PIL import Image
from typing import Dict, Any, List, Optional, Tuple
from pydantic import BaseModel, Field

from core.volumetric import VolumetricCTEngine, WINDOW_PRESETS, HUWindowPreset


class ProjectionMetadata(BaseModel):
    series_id: str
    projection_mode: str  # "MIP", "MINIP", "AIP", "CINEMATIC_3D"
    orientation: str  # "AXIAL", "CORONAL", "SAGITTAL", "ORBIT"
    slice_index: int
    slab_thickness_mm: float
    window_preset: str
    window_width: int
    window_level: int
    mean_hu: float
    min_hu: int
    max_hu: int


class TransferFunctionPreset(BaseModel):
    name: str
    description: str
    bone_color: Tuple[int, int, int] = (240, 235, 220)
    hematoma_color: Tuple[int, int, int] = (255, 40, 75)
    vessel_color: Tuple[int, int, int] = (255, 175, 40)
    tissue_color: Tuple[int, int, int] = (190, 145, 125)


TRANSFER_PRESETS: Dict[str, TransferFunctionPreset] = {
    "NEURO_HEMORRHAGE": TransferFunctionPreset(
        name="NEURO_HEMORRHAGE",
        description="High-contrast calvarium bone suppression with glowing crimson hematoma"
    ),
    "CHEST_VASCULAR": TransferFunctionPreset(
        name="CHEST_VASCULAR",
        description="Pulmonary vasculature and thoracic cardiac chamber contrast",
        vessel_color=(255, 195, 60)
    ),
    "BONE_ANATOMY": TransferFunctionPreset(
        name="BONE_ANATOMY",
        description="High-density skeletal cortical structures with surface shading"
    )
}


class RaycastEngine:
    """Core computational engine for 3D MIP, MinIP, and Cinematic Ray-Casting."""

    _instance: Optional['RaycastEngine'] = None

    def __init__(self):
        self._vol_engine = VolumetricCTEngine.get_instance()
        # Turntable cache: {f"{series_id}_{preset}": [16 base64 frame strings]}
        self._turntable_cache: Dict[str, List[str]] = {}

    @classmethod
    def get_instance(cls) -> 'RaycastEngine':
        if cls._instance is None:
            cls._instance = RaycastEngine()
        return cls._instance

    def compute_orthogonal_projection(
        self,
        series_id: str,
        orientation: str = "AXIAL",
        mode: str = "MIP",
        slice_idx: int = 16,
        slab_thickness_mm: float = 15.0,
        window_preset: str = "LUNG",
        custom_width: Optional[int] = None,
        custom_level: Optional[int] = None
    ) -> Tuple[np.ndarray, np.ndarray, ProjectionMetadata]:
        """
        Computes thick-slab or full-volume MIP, MinIP, or AIP along an orthogonal plane.
        - orientation: "AXIAL", "CORONAL", "SAGITTAL"
        - mode: "MIP" (max), "MINIP" (min), "AIP" (mean)
        - slab_thickness_mm: 0 means full volume, >0 means local thick slab around slice_idx
        """
        vol = self._vol_engine._volumes.get(series_id)
        if vol is None:
            raise KeyError(f"Series '{series_id}' not found in volumetric registry.")

        d, h, w = vol.shape
        orient = orientation.upper()
        mode_upper = mode.upper()

        # Determine projection axis and slice bounds
        if orient == "AXIAL":
            # Viewing along Z axis (depth)
            spacing_mm = 2.5
            total_slices = d
            proj_axis = 0
            safe_center = max(0, min(slice_idx, d - 1))
        elif orient == "CORONAL":
            # Viewing along Y axis (height)
            spacing_mm = 1.2
            total_slices = h
            proj_axis = 1
            safe_center = max(0, min(slice_idx, h - 1))
        elif orient == "SAGITTAL":
            # Viewing along X axis (width)
            spacing_mm = 1.2
            total_slices = w
            proj_axis = 2
            safe_center = max(0, min(slice_idx, w - 1))
        else:
            raise ValueError(f"Invalid orientation '{orientation}'. Choose AXIAL, CORONAL, or SAGITTAL.")

        # Compute slab slice range
        if slab_thickness_mm <= 0.0 or slab_thickness_mm >= (total_slices * spacing_mm):
            # Full volume projection
            sub_vol = vol
        else:
            half_slices = max(1, int(round((slab_thickness_mm / spacing_mm) / 2.0)))
            start_idx = max(0, safe_center - half_slices)
            end_idx = min(total_slices, safe_center + half_slices + 1)

            if proj_axis == 0:
                sub_vol = vol[start_idx:end_idx, :, :]
            elif proj_axis == 1:
                sub_vol = vol[:, start_idx:end_idx, :]
            else:
                sub_vol = vol[:, :, start_idx:end_idx]

        # Execute Projection Operator
        if mode_upper == "MIP":
            proj_hu = np.max(sub_vol, axis=proj_axis)
        elif mode_upper == "MINIP":
            proj_hu = np.min(sub_vol, axis=proj_axis)
        elif mode_upper in ("AIP", "AVERAGE"):
            proj_hu = np.mean(sub_vol, axis=proj_axis).astype(np.int16)
        else:
            raise ValueError(f"Invalid projection mode '{mode}'. Choose MIP, MINIP, or AIP.")

        # Apply HU Window / Level Transformation
        preset = WINDOW_PRESETS.get(window_preset.upper(), WINDOW_PRESETS.get("LUNG"))
        ww = custom_width if custom_width is not None else (preset.window_width if preset else 1500)
        wl = custom_level if custom_level is not None else (preset.window_level if preset else -600)

        proj_8bit = self._vol_engine.apply_window_level(proj_hu, ww, wl)

        meta = ProjectionMetadata(
            series_id=series_id,
            projection_mode=mode_upper,
            orientation=orient,
            slice_index=safe_center,
            slab_thickness_mm=round(slab_thickness_mm, 1),
            window_preset=window_preset,
            window_width=ww,
            window_level=wl,
            mean_hu=round(float(np.mean(proj_hu)), 1),
            min_hu=int(np.min(proj_hu)),
            max_hu=int(np.max(proj_hu))
        )

        return proj_hu, proj_8bit, meta

    def render_3d_orbit_frame(
        self,
        series_id: str,
        azimuth_deg: float = 0.0,
        elevation_deg: float = 15.0,
        preset_name: str = "NEURO_HEMORRHAGE",
        target_size: int = 320
    ) -> Tuple[np.ndarray, str]:
        """
        Performs 3D volume ray-marching at specified azimuth and elevation viewing angles.
        Returns: (RGBA numpy array (target_size, target_size, 4), base64_png_string)
        """
        vol = self._vol_engine._volumes.get(series_id)
        if vol is None:
            raise KeyError(f"Series '{series_id}' not found.")

        d, h, w = vol.shape

        # Normalize rotation angles
        azimuth_deg = float(azimuth_deg % 360.0)
        elevation_deg = float(np.clip(elevation_deg, -45.0, 45.0))

        # Rotate volume around vertical (Z) axis by azimuth_deg
        rotated_slices = []
        center = (w / 2.0, h / 2.0)
        rot_mat = cv2.getRotationMatrix2D(center, -azimuth_deg, 1.0)

        for z in range(d):
            sl = vol[z, :, :].astype(np.float32)
            rot_sl = cv2.warpAffine(
                sl, rot_mat, (w, h),
                flags=cv2.INTER_LINEAR,
                borderMode=cv2.BORDER_CONSTANT,
                borderValue=-1000.0
            )
            rotated_slices.append(rot_sl)

        rot_vol = np.stack(rotated_slices, axis=0)  # Shape (D, H, W)

        # Apply elevation tilt if non-zero (tilt along Y axis)
        if abs(elevation_deg) > 1.0:
            elev_slices = []
            e_center = (w / 2.0, d / 2.0)
            elev_mat = cv2.getRotationMatrix2D(e_center, elevation_deg, 1.0)
            for y in range(h):
                xz_plane = rot_vol[:, y, :].astype(np.float32)
                rot_xz = cv2.warpAffine(
                    xz_plane, elev_mat, (w, d),
                    flags=cv2.INTER_LINEAR,
                    borderMode=cv2.BORDER_CONSTANT,
                    borderValue=-1000.0
                )
                elev_slices.append(rot_xz)
            rot_vol = np.stack(elev_slices, axis=1)  # Reshape back

        # Perform Front-to-Back Volume Ray-Marching along Axis 1 (coronal depth)
        # We step through Y: 0 -> H-1
        # Accumulator image: (D, W, 4) in RGBA float
        step_count = rot_vol.shape[1]
        out_h, out_w = rot_vol.shape[0], rot_vol.shape[2]

        accum_rgb = np.zeros((out_h, out_w, 3), dtype=np.float32)
        accum_alpha = np.zeros((out_h, out_w), dtype=np.float32)

        # Retrieve Transfer Function Palette
        tf = TRANSFER_PRESETS.get(preset_name.upper(), TRANSFER_PRESETS["NEURO_HEMORRHAGE"])

        # Sample across depth in 16 uniformly spaced ray steps
        sample_indices = np.linspace(0, step_count - 1, num=min(24, step_count), dtype=int)

        # Simple diffuse surface shading light vector
        light_dir = np.array([0.4, -0.6, 0.7])
        light_dir = light_dir / np.linalg.norm(light_dir)

        for step_idx in sample_indices:
            sample_hu = rot_vol[:, step_idx, :]

            # Compute Opacity & Color masks based on Hounsfield Units
            # 1. Bone (+300 to +1500 HU)
            bone_mask = sample_hu >= 300
            # 2. Hematoma / Hyperdense Blood (+50 to +90 HU)
            hematoma_mask = (sample_hu >= 50) & (sample_hu <= 90)
            # 3. Soft tissue (+15 to +100 HU, excluding hematoma if neuro)
            tissue_mask = (sample_hu >= 15) & (sample_hu <= 120) & (~hematoma_mask) & (~bone_mask)

            # Local sample opacity
            sample_alpha = np.zeros((out_h, out_w), dtype=np.float32)
            sample_color = np.zeros((out_h, out_w, 3), dtype=np.float32)

            # Bone contribution
            sample_alpha[bone_mask] = 0.85
            for c_idx in range(3):
                sample_color[bone_mask, c_idx] = tf.bone_color[c_idx]

            # Hematoma contribution (vibrant crimson)
            if "NEURO" in preset_name.upper() or "HEMORRHAGE" in preset_name.upper():
                sample_alpha[hematoma_mask] = 0.95
                for c_idx in range(3):
                    sample_color[hematoma_mask, c_idx] = tf.hematoma_color[c_idx]
            else:
                sample_alpha[hematoma_mask] = 0.60
                for c_idx in range(3):
                    sample_color[hematoma_mask, c_idx] = tf.vessel_color[c_idx]

            # Soft tissue contribution
            sample_alpha[tissue_mask] = 0.15
            for c_idx in range(3):
                sample_color[tissue_mask, c_idx] = tf.tissue_color[c_idx]

            # Alpha compositing (Front to back)
            transmittance = 1.0 - accum_alpha
            weight = transmittance * sample_alpha

            for c_idx in range(3):
                accum_rgb[:, :, c_idx] += weight * sample_color[:, :, c_idx]

            accum_alpha += weight

            # Early ray termination check
            if np.all(accum_alpha >= 0.98):
                break

        # Normalize and assemble final RGBA
        final_rgb = np.clip(accum_rgb, 0.0, 255.0).astype(np.uint8)
        final_alpha = np.clip(accum_alpha * 255.0, 0.0, 255.0).astype(np.uint8)

        # Resize to square target aspect ratio (target_size x target_size)
        rgba = np.dstack([final_rgb, final_alpha])
        resized = cv2.resize(rgba, (target_size, target_size), interpolation=cv2.INTER_LINEAR)

        # Convert to Base64 PNG
        pil_img = Image.fromarray(resized, mode='RGBA')
        buf = io.BytesIO()
        pil_img.save(buf, format="PNG", optimize=True)
        base64_str = f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode('utf-8')}"

        return resized, base64_str

    def get_turntable_frames(
        self, series_id: str, preset_name: str = "NEURO_HEMORRHAGE", num_frames: int = 16
    ) -> List[str]:
        """
        Generates 16 uniformly spaced 360-degree turntable frames for smooth interactive scrubbing.
        Uses in-memory caching to ensure instant client-side response.
        """
        cache_key = f"{series_id}_{preset_name}_{num_frames}"
        if cache_key in self._turntable_cache:
            return self._turntable_cache[cache_key]

        frames = []
        angles = np.linspace(0.0, 360.0, num=num_frames, endpoint=False)

        for ang in angles:
            _, b64 = self.render_3d_orbit_frame(
                series_id=series_id,
                azimuth_deg=float(ang),
                elevation_deg=15.0,
                preset_name=preset_name,
                target_size=256
            )
            frames.append(b64)

        self._turntable_cache[cache_key] = frames
        return frames


def get_raycast_engine() -> RaycastEngine:
    return RaycastEngine.get_instance()
