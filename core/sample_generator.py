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

    # 1. Thoracic soft tissue contour (torso backdrop)
    cv2.ellipse(img, (w // 2, h // 2), (w // 2 - 10, h // 2 - 10), 0, 0, 360, 40, -1)

    # 2. Bilateral radiolucent lung fields (air is black/dark)
    # Right lung
    cv2.ellipse(img, (w // 2 - 60, h // 2 - 10), (45, 95), -5, 0, 360, 15, -1)
    # Left lung
    cv2.ellipse(img, (w // 2 + 60, h // 2 - 10), (42, 95), 5, 0, 360, 15, -1)

    # 3. Mediastinum & Cardiac silhouette (radiopaque white/gray)
    cv2.ellipse(img, (w // 2 + 18, h // 2 + 35), (38, 50), -30, 0, 360, 180, -1)
    # Aortic arch
    cv2.circle(img, (w // 2 + 10, h // 2 - 35), 24, 160, -1)

    # 4. Diaphragmatic domes
    cv2.ellipse(img, (w // 2 - 60, h - 50), (60, 35), 0, 180, 360, 170, -1)
    cv2.ellipse(img, (w // 2 + 65, h - 45), (55, 30), 0, 180, 360, 170, -1)

    # 5. Posterior and anterior rib arcs
    for y_offset in range(60, h - 70, 26):
        # Rib shadows
        cv2.ellipse(img, (w // 2 - 60, y_offset), (55, 14), 15, 0, 180, 85, 4)
        cv2.ellipse(img, (w // 2 + 60, y_offset), (55, 14), -15, 0, 180, 85, 4)

    # 6. Spine / Vertebral column (central radiopaque stripe)
    cv2.rectangle(img, (w // 2 - 10, 40), (w // 2 + 10, h - 40), 120, -1)

    # 7. Add subtle bronchovascular markings (tree-like branching)
    for _ in range(12):
        x1 = np.random.randint(w // 2 - 75, w // 2 - 25)
        y1 = np.random.randint(h // 2 - 50, h // 2 + 40)
        x2 = x1 + np.random.randint(-20, 20)
        y2 = y1 + np.random.randint(-20, 20)
        cv2.line(img, (x1, y1), (x2, y2), float(np.random.randint(40, 90)), 2)

    # 8. Pneumonia pathology injection: Dense patchy infiltrates & consolidation
    if is_pneumonia:
        # Patchy consolidation in right lower/mid lobe
        for cx, cy, rad, intensity in [
            (w // 2 - 55, h // 2 + 10, 35, 190),
            (w // 2 - 40, h // 2 + 30, 28, 210),
            (w // 2 - 68, h // 2 + 25, 22, 175),
        ]:
            cv2.circle(img, (cx, cy), rad, intensity, -1)

    # 9. Realistic Gaussian smoothing and quantum mottle sensor noise
    img = cv2.GaussianBlur(img, (7, 7), 2.0)
    noise = np.random.normal(0, 8.0, img.shape).astype(np.float32)
    img = np.clip(img + noise, 0, 255).astype(np.uint8)

    return img

def ensure_sample_assets():
    """Generates and persists sample radiographs if not already present."""
    samples_dir = settings.SAMPLES_DIR
    samples_dir.mkdir(parents=True, exist_ok=True)

    normal_path = samples_dir / "sample_normal.jpg"
    pneumonia_path = samples_dir / "sample_pneumonia.jpg"

    if not normal_path.exists():
        normal_img = create_synthetic_radiograph(is_pneumonia=False, seed=101)
        cv2.imwrite(str(normal_path), normal_img)

    if not pneumonia_path.exists():
        pneumonia_img = create_synthetic_radiograph(is_pneumonia=True, seed=202)
        cv2.imwrite(str(pneumonia_path), pneumonia_img)

if __name__ == "__main__":
    ensure_sample_assets()
    print("Sample radiographs created successfully.")
