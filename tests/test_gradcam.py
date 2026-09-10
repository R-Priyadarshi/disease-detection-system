import pytest
import numpy as np

from core.model import get_model
from core.gradcam import GradCAMGenerator
from core.preprocessor import preprocessor
from core.config import settings

def test_gradcam_heatmap_dimensions():
    """Verify Grad-CAM produces valid 2D normalized heatmaps."""
    model_wrapper = get_model()
    gradcam = GradCAMGenerator(model_wrapper)

    dummy_tensor = np.random.uniform(0.0, 1.0, (1, settings.INPUT_HEIGHT, settings.INPUT_WIDTH, 1)).astype(np.float32)
    heatmap = gradcam.compute_heatmap(dummy_tensor)

    assert heatmap.ndim == 2
    assert heatmap.shape == (34, 34)  # Conv2D_2 output resolution
    assert 0.0 <= float(np.min(heatmap))
    assert float(np.max(heatmap)) <= 1.0 + 1e-5

def test_gradcam_overlay_blending():
    """Verify Grad-CAM overlay blending onto original grayscale image."""
    model_wrapper = get_model()
    gradcam = GradCAMGenerator(model_wrapper)

    dummy_orig = np.full((150, 150), 128, dtype=np.uint8)
    dummy_tensor = np.ones((1, 150, 150, 1), dtype=np.float32) * 0.5

    blended, colored_heat = gradcam.generate_overlay(dummy_orig, dummy_tensor, alpha=0.5)

    assert blended.shape == (150, 150, 3)
    assert blended.dtype == np.uint8
    assert colored_heat.shape == (150, 150, 3)
