#!/usr/bin/env python3
"""
Pneumonia Detection CLI & Inference Engine
Backward-compatible and production-grade inference script with Grad-CAM visualization.
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

def predict(fileimg: str, apply_clahe: bool = False, save_gradcam_path: str = None) -> bool:
    """
    Evaluates a single chest radiograph.
    
    Args:
        fileimg: Path to the radiograph image
        apply_clahe: Whether to apply CLAHE contrast enhancement
        save_gradcam_path: Optional path to export Grad-CAM overlay image
        
    Returns:
        bool: True if Pneumonia detected, False if Normal
    """
    model = get_model()
    gradcam = GradCAMGenerator(model)

    tensor, raw_gray = preprocessor.prepare_tensor(fileimg, apply_clahe=apply_clahe)
    res = model.predict_tensor(tensor)

    print(f"\n==========================================")
    print(f"DIAGNOSTIC REPORT: {Path(fileimg).name}")
    print(f"==========================================")
    print(f"  Diagnosis:       {res['diagnosis']}")
    print(f"  Confidence:      {res['confidence_percentage']}% (Probability: {res['probability']})")
    print(f"  Risk Category:   {res['risk_tier']}")
    print(f"  Inference Time:  {res['latency_ms']} ms")
    print(f"  Recommendation:  {res['clinical_recommendation']}")
    print(f"==========================================\n")

    if save_gradcam_path:
        blended, _ = gradcam.generate_overlay(raw_gray, tensor)
        cv2.imwrite(save_gradcam_path, blended)
        print(f"[Grad-CAM] Heatmap saved to: {save_gradcam_path}")

    return res["is_pneumonia"]

def main():
    parser = argparse.ArgumentParser(description="Evaluate Chest X-Ray for Pneumonia detection.")
    parser.add_argument(
        "-i", "--image",
        type=str,
        default="core/assets/samples/sample_pneumonia.jpg",
        help="Path to chest radiograph image file"
    )
    parser.add_argument(
        "--clahe",
        action="store_true",
        help="Apply CLAHE contrast enhancement"
    )
    parser.add_argument(
        "-o", "--output-gradcam",
        type=str,
        default=None,
        help="Path to save Grad-CAM overlay visualization"
    )

    args = parser.parse_args()

    if not Path(args.image).exists():
        # Fallback check
        print(f"Error: Specified image file '{args.image}' does not exist.", file=sys.stderr)
        sys.exit(1)

    result = predict(args.image, apply_clahe=args.clahe, save_gradcam_path=args.output_gradcam)
    sys.exit(0 if result else 0)

if __name__ == "__main__":
    main()