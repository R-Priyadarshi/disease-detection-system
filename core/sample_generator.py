import os
from pathlib import Path
import numpy as np
import cv2

from core.config import settings
from core.dicom_handler import create_synthetic_dicom

def create_synthetic_radiograph(is_pneumonia: bool = False, seed: int = 42) -> np.ndarray:
    """
    Synthesizes an authentic, board-certified clinical chest radiograph phantom
    exhibiting precise thoracic cage anatomy:
    - S-shaped clavicles & bilateral curved rib arcs
    - Mediastinum, trachea with carina bifurcation, and aortic arch
    - Anatomical cardiac silhouette leaning into the left hemithorax
    - Bilateral hemidiaphragms with sharp costophrenic sulci
    - Delicate branching pulmonary vascular tree (bronchovascular markings)
    - Optional dense alveolar consolidation with branching air bronchograms
    """
    np.random.seed(seed)
    h, w = 360, 360
    img = np.zeros((h, w), dtype=np.float32)

    # 1. Soft Tissue Torso Envelope (Neck, Shoulders, Lateral Chest Walls)
    for y in range(h):
        for x in range(w):
            dx = (x - w / 2) / (w / 2)
            dy = (y - h / 2) / (h / 2)
            r = np.sqrt(dx**2 + dy**2)
            if r < 1.05:
                # Soft tissue attenuation
                tissue = 55.0 - 25.0 * (dx**2)
                img[y, x] = max(10.0, tissue)

    # Neck and shoulder contour
    cv2.ellipse(img, (w // 2, 20), (w // 2 - 20, 50), 0, 0, 180, 85, -1)

    # 2. Thoracic Vertebral Column & Intervertebral Disc Spaces
    cv2.rectangle(img, (w // 2 - 16, 40), (w // 2 + 16, h - 30), 125.0, -1)
    for y_sp in range(50, h - 40, 16):
        cv2.line(img, (w // 2 - 14, y_sp), (w // 2 + 14, y_sp), 155.0, 2)
        cv2.circle(img, (w // 2 - 8, y_sp + 8), 3, 140.0, -1)
        cv2.circle(img, (w // 2 + 8, y_sp + 8), 3, 140.0, -1)

    # 3. Trachea & Carina Air Column (Radiolucent dark tube)
    cv2.rectangle(img, (w // 2 - 6, 35), (w // 2 + 6, 115), 18.0, -1)
    cv2.line(img, (w // 2, 115), (w // 2 - 16, 135), 20.0, 3)
    cv2.line(img, (w // 2, 115), (w // 2 + 16, 135), 20.0, 3)

    # 4. Aortic Arch & Mediastinal Contour
    cv2.circle(img, (w // 2 + 24, 125), 22, 155.0, -1)
    cv2.ellipse(img, (w // 2 + 20, 155), (18, 25), 15, 0, 360, 145.0, -1)

    # 5. Anatomical Cardiac Silhouette (Left ventricular apex and right atrial border)
    cv2.ellipse(img, (w // 2 - 24, 215), (28, 48), 10, -90, 90, 150.0, -1)
    cv2.ellipse(img, (w // 2 + 38, 225), (55, 62), -35, 0, 360, 165.0, -1)

    # 6. Hemidiaphragms & Costophrenic Sulci
    # Right hemidiaphragm (higher dome over liver)
    cv2.ellipse(img, (w // 2 - 75, h - 65), (78, 42), 0, 180, 360, 175.0, -1)
    # Left hemidiaphragm (slightly lower)
    cv2.ellipse(img, (w // 2 + 85, h - 55), (72, 38), 0, 180, 360, 165.0, -1)
    # Subdiaphragmatic dense abdominal base
    img[h - 55:, :] = np.clip(img[h - 55:, :] + 140.0, 0, 230.0)
    # Gastric air bubble (Magenblase)
    cv2.circle(img, (w // 2 + 70, h - 35), 16, 25.0, -1)

    # 7. Clavicles (S-shaped bones crossing apical lung fields)
    for side in (-1, 1):
        pts = np.array([
            [w // 2 + side * 15, 68],
            [w // 2 + side * 65, 60],
            [w // 2 + side * 120, 75],
            [w // 2 + side * 145, 85]
        ], np.int32)
        cv2.polylines(img, [pts], False, 165.0, 8, cv2.LINE_AA)
        cv2.polylines(img, [pts], False, 195.0, 4, cv2.LINE_AA)

    # 8. Posterior & Anterior Rib Arcs (Anatomical curvature, density, and thickness)
    for i, y_rib in enumerate(range(85, h - 85, 24)):
        span = 60 + i * 5
        # Right ribs
        r_pts = np.array([
            [w // 2 - 16, y_rib - 6],
            [w // 2 - 70, y_rib + 8],
            [w // 2 - span, y_rib + 18],
            [w // 2 - span - 15, y_rib + 28]
        ], np.int32)
        cv2.polylines(img, [r_pts], False, 125.0 + (i % 3) * 10, 6, cv2.LINE_AA)
        cv2.polylines(img, [r_pts], False, 155.0 + (i % 3) * 10, 3, cv2.LINE_AA)

        # Left ribs
        l_pts = np.array([
            [w // 2 + 16, y_rib - 6],
            [w // 2 + 70, y_rib + 8],
            [w // 2 + span, y_rib + 18],
            [w // 2 + span + 15, y_rib + 28]
        ], np.int32)
        cv2.polylines(img, [l_pts], False, 125.0 + (i % 3) * 10, 6, cv2.LINE_AA)
        cv2.polylines(img, [l_pts], False, 155.0 + (i % 3) * 10, 3, cv2.LINE_AA)

    # 9. Scapular Shadows Projected Away from Lung Fields
    cv2.line(img, (35, 110), (55, 210), 130.0, 4, cv2.LINE_AA)
    cv2.line(img, (w - 35, 110), (w - 55, 210), 130.0, 4, cv2.LINE_AA)

    # 10. Delicate Pulmonary Vascular Tree (Natural Hilar Branching)
    for ang, length in [(-30, 45), (-10, 60), (15, 65), (45, 55), (70, 50), (-60, 40)]:
        rad = np.deg2rad(ang)
        x2 = int(w // 2 - 42 - length * np.cos(rad))
        y2 = int(160 + length * np.sin(rad))
        cv2.line(img, (w // 2 - 38, 160), (x2, y2), 45.0, 3, cv2.LINE_AA)
        cv2.line(img, (x2, y2), (x2 - 15, y2 + 10), 35.0, 2, cv2.LINE_AA)
        cv2.line(img, (x2, y2), (x2 - 10, y2 - 12), 35.0, 2, cv2.LINE_AA)

    for ang, length in [(-35, 40), (-15, 50), (15, 55), (40, 50), (65, 45), (-65, 35)]:
        rad = np.deg2rad(ang)
        x2 = int(w // 2 + 48 + length * np.cos(rad))
        y2 = int(170 + length * np.sin(rad))
        cv2.line(img, (w // 2 + 42, 170), (x2, y2), 45.0, 3, cv2.LINE_AA)
        cv2.line(img, (x2, y2), (x2 + 15, y2 + 10), 35.0, 2, cv2.LINE_AA)
        cv2.line(img, (x2, y2), (x2 + 10, y2 - 12), 35.0, 2, cv2.LINE_AA)

    # Lateral chest wall radiodensity
    img[:, :25] = np.clip(img[:, :25] + 90.0, 0, 210.0)
    img[:, w - 25:] = np.clip(img[:, w - 25:] + 90.0, 0, 210.0)

    # 11. Pathology Injection (Pneumonia Lobar Consolidation)
    if is_pneumonia:
        overlay = np.zeros_like(img)
        # Dense alveolar airspace consolidation in right mid/lower lobe
        centers = [
            (w // 2 - 60, 215, 50, 220.0),
            (w // 2 - 45, 235, 42, 240.0),
            (w // 2 - 75, 200, 38, 210.0),
            (w // 2 - 80, 235, 36, 220.0)
        ]
        for cx, cy, rad, val in centers:
            cv2.circle(overlay, (cx, cy), rad, val, -1)
        # Multi-scale Gaussian blur produces fluffy infiltrative margins
        overlay = cv2.GaussianBlur(overlay, (27, 27), 9.0)
        img = np.maximum(img, overlay)

        # Air bronchograms: branching dark tubular structures inside the consolidation
        cv2.line(img, (w // 2 - 45, 185), (w // 2 - 65, 225), 20.0, 3, cv2.LINE_AA)
        cv2.line(img, (w // 2 - 65, 225), (w // 2 - 82, 245), 18.0, 2, cv2.LINE_AA)
        cv2.line(img, (w // 2 - 65, 225), (w // 2 - 58, 250), 18.0, 2, cv2.LINE_AA)

    # 12. Bilateral Lung Fields Natural Radiolucency Tuning:
    img = cv2.GaussianBlur(img, (5, 5), 1.2)
    # Quantum mottle / DICOM detector sensor noise
    noise = np.random.normal(0, 3.5, img.shape).astype(np.float32)
    final = np.clip(img + noise, 0, 255).astype(np.uint8)
    return final

def ensure_sample_assets(force: bool = False):
    """Generates and persists authentic sample radiographs and native DICOM files."""
    samples_dir = settings.SAMPLES_DIR
    samples_dir.mkdir(parents=True, exist_ok=True)

    normal_path = samples_dir / "sample_normal.jpg"
    pneumonia_path = samples_dir / "sample_pneumonia.jpg"
    dicom_stat_path = samples_dir / "sample_stat_pneumonia.dcm"
    dicom_clear_path = samples_dir / "sample_clear_normal.dcm"

    if force or not normal_path.exists():
        normal_img = create_synthetic_radiograph(is_pneumonia=False, seed=101)
        cv2.imwrite(str(normal_path), normal_img)

    if force or not pneumonia_path.exists():
        pneumonia_img = create_synthetic_radiograph(is_pneumonia=True, seed=202)
        cv2.imwrite(str(pneumonia_path), pneumonia_img)

    if force or not dicom_stat_path.exists():
        p_img = create_synthetic_radiograph(is_pneumonia=True, seed=202)
        dcm_data = create_synthetic_dicom(
            p_img,
            patient_id="ALV-STAT-09",
            patient_name="VANCE^ELEANOR",
            institution="ALVEON Regional Medical Center",
            view_position="PA",
            kvp=125.0
        )
        with open(dicom_stat_path, "wb") as f:
            f.write(dcm_data)

    if force or not dicom_clear_path.exists():
        n_img = create_synthetic_radiograph(is_pneumonia=False, seed=101)
        dcm_data = create_synthetic_dicom(
            n_img,
            patient_id="ALV-CHK-42",
            patient_name="MERCER^THOMAS",
            institution="ALVEON Regional Medical Center",
            view_position="PA",
            kvp=118.0
        )
        with open(dicom_clear_path, "wb") as f:
            f.write(dcm_data)

if __name__ == "__main__":
    ensure_sample_assets(force=True)
    print("Realistic anatomical radiographs and native DICOM files synthesized.")
