#!/usr/bin/env python3
"""
ALVEON — Command-Line Radiographic Diagnostic Engine
Hospital-grade inference utility with multi-colormap Grad-CAM and anatomical zonation.
"""

import sys
import argparse
from pathlib import Path
import cv2
import numpy as np

from core.config import settings
from core.model import get_model
from core.preprocessor import preprocessor
from core.gradcam import GradCAMGenerator

def predict(
    fileimg: str,
    apply_clahe: bool = False,
    colormap: str = "inferno",
    save_gradcam_path: str = None
) -> bool:
    """
    Evaluates a thoracic radiograph under ALVEON diagnostic standards.
    """
    model = get_model()
    gradcam = GradCAMGenerator(model)

    tensor, raw_gray = preprocessor.prepare_tensor(fileimg, apply_clahe=apply_clahe)
    res = model.predict_tensor(tensor)
    blended, heatmap, zonation = gradcam.generate_overlay(raw_gray, tensor, colormap_name=colormap)

    print(f"\n========================================================")
    print(f"ALVEON THORACIC PACS REPORT: {Path(fileimg).name}")
    print(f"========================================================")
    print(f"  Primary Impression:  {res['diagnosis']} ({res['confidence_percentage']}%)")
    print(f"  Risk Category:       {res['risk_tier']}")
    print(f"  Dominant Focus:      {zonation['dominant_zone']}")
    print(f"  Quadrant Zonation:")
    print(f"    - Right Upper Lobe: {zonation['right_upper_lobe_pct']}%")
    print(f"    - Right Lower Lobe: {zonation['right_lower_lobe_pct']}%")
    print(f"    - Left Upper Lobe:  {zonation['left_upper_lobe_pct']}%")
    print(f"    - Left Lower Lobe:  {zonation['left_lower_lobe_pct']}%")
    print(f"  Inference Latency:   {res['latency_ms']} ms")
    print(f"  Guidance:            {res['clinical_recommendation']}")
    print(f"========================================================\n")

    if save_gradcam_path:
        cv2.imwrite(save_gradcam_path, blended)
        print(f"[ALVEON] Radiographic plate saved to: {save_gradcam_path}")

    return res["is_pneumonia"]

def main():
    parser = argparse.ArgumentParser(description="ALVEON Thoracic Radiographic Evaluation CLI.")
    parser.add_argument(
        "-i", "--image",
        type=str,
        default="core/assets/samples/sample_pneumonia.jpg",
        help="Path to chest radiograph image file"
    )
    parser.add_argument(
        "--clahe",
        action="store_true",
        help="Apply CLAHE contrast equalization"
    )
    parser.add_argument(
        "-c", "--colormap",
        type=str,
        default="inferno",
        choices=["inferno", "viridis", "plasma", "hot", "jet"],
        help="Perceptual medical colormap for Grad-CAM"
    )
    parser.add_argument(
        "-o", "--output-gradcam",
        type=str,
        default=None,
        help="Path to save Grad-CAM radiographic plate"
    )

    args = parser.parse_args()

    if not Path(args.image).exists():
        print(f"Error: Radiograph file '{args.image}' does not exist.", file=sys.stderr)
        sys.exit(1)

    result = predict(
        args.image,
        apply_clahe=args.clahe,
        colormap=args.colormap,
        save_gradcam_path=args.output_gradcam
    )
    sys.exit(0 if result else 0)

if __name__ == "__main__":
    main()