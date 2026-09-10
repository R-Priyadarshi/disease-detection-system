import os
from pathlib import Path
import numpy as np
import cv2

from core.config import settings

def create_synthetic_radiograph(is_pneumonia: bool = False, seed: int = 42) -> np.ndarray:
    """
    Synthesizes a realistic chest radiograph phantom exhibiting characteristic
    thoracic cage geometry (ribs, spine, cardiac silhouette, diaphragm, lung fields),
    with optional focal consolidations and air bronchograms for pneumonia simulation.
    """
    np.random.seed(seed)
    h, w = 300, 300
    img = np.zeros((h, w), dtype=np.float32)

    if not is_pneumonia:
        # Calibrated radiolucent clear lung anatomy:
        # Dark non-attenuating lung parenchyma with bright mediastinal & rib borders
        img[:, :40] = 175.0
        img[:, 260:] = 175.0
        img[:, 130:170] = 160.0 # spine & mediastinum
        img[:50, :] = 140.0 # thoracic inlet
        img[250:, :] = 170.0 # diaphragmatic domes
        for y in range(60, 250, 28):
            cv2.ellipse(img, (75, y), (50, 10), 10, 0, 180, 110, 3)
            cv2.ellipse(img, (225, y), (50, 10), -10, 0, 180, 110, 3)
        img[60:240, 40:130] = np.random.uniform(0.0, 10.0, (180, 90))
        img[60:240, 170:260] = np.random.uniform(0.0, 10.0, (180, 90))
        img = cv2.GaussianBlur(img, (5, 5), 1.5)
        return np.clip(img, 0, 255).astype(np.uint8)

    # Pneumonia Anatomy with Consolidation:
    # 1. Thoracic soft tissue contour (torso backdrop)
    cv2.ellipse(img, (w // 2, h // 2), (w // 2 - 10, h // 2 - 10), 0, 0, 360, 40, -1)

    # 2. Bilateral radiolucent lung fields
    cv2.ellipse(img, (w // 2 - 60, h // 2 - 10), (45, 95), -5, 0, 360, 15, -1)
    cv2.ellipse(img, (w // 2 + 60, h // 2 - 10), (42, 95), 5, 0, 360, 15, -1)

    # 3. Mediastinum & Cardiac silhouette
    cv2.ellipse(img, (w // 2 + 18, h // 2 + 35), (38, 50), -30, 0, 360, 180, -1)
    cv2.circle(img, (w // 2 + 10, h // 2 - 35), 24, 160, -1)

    # 4. Diaphragmatic domes
    cv2.ellipse(img, (w // 2 - 60, h - 50), (60, 35), 0, 180, 360, 170, -1)
    cv2.ellipse(img, (w // 2 + 65, h - 45), (55, 30), 0, 180, 360, 170, -1)

    # 5. Posterior and anterior rib arcs
    for y_offset in range(60, h - 70, 26):
        cv2.ellipse(img, (w // 2 - 60, y_offset), (55, 14), 15, 0, 180, 85, 4)
        cv2.ellipse(img, (w // 2 + 60, y_offset), (55, 14), -15, 0, 180, 85, 4)

    # 6. Spine
    cv2.rectangle(img, (w // 2 - 10, 40), (w // 2 + 10, h - 40), 120, -1)

    # 7. Dense patchy consolidation & infiltrates in right lower/mid lobe
    for cx, cy, rad, intensity in [
        (w // 2 - 55, h // 2 + 10, 35, 190),
        (w // 2 - 40, h // 2 + 30, 28, 210),
        (w // 2 - 68, h // 2 + 25, 22, 175),
    ]:
        cv2.circle(img, (cx, cy), rad, intensity, -1)

    img = cv2.GaussianBlur(img, (7, 7), 2.0)
    noise = np.random.normal(0, 8.0, img.shape).astype(np.float32)
    return np.clip(img + noise, 0, 255).astype(np.uint8)

from core.dicom_handler import create_synthetic_dicom

def ensure_sample_assets():
    """Generates and persists sample radiographs and native DICOM files if not already present."""
    samples_dir = settings.SAMPLES_DIR
    samples_dir.mkdir(parents=True, exist_ok=True)

    normal_path = samples_dir / "sample_normal.jpg"
    pneumonia_path = samples_dir / "sample_pneumonia.jpg"
    dicom_stat_path = samples_dir / "sample_stat_pneumonia.dcm"
    dicom_clear_path = samples_dir / "sample_clear_normal.dcm"

    if not normal_path.exists():
        normal_img = create_synthetic_radiograph(is_pneumonia=False, seed=101)
        cv2.imwrite(str(normal_path), normal_img)

    if not pneumonia_path.exists():
        pneumonia_img = create_synthetic_radiograph(is_pneumonia=True, seed=202)
        cv2.imwrite(str(pneumonia_path), pneumonia_img)

    if not dicom_stat_path.exists():
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

    if not dicom_clear_path.exists():
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
    ensure_sample_assets()
    print("Sample radiographs created successfully.")
