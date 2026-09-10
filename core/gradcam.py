from typing import Tuple, Optional, Dict, Any
import numpy as np
import cv2
import tensorflow as tf
from tensorflow import keras

from core.config import settings
from core.model import PneumoniaCNNModel

COLORMAP_REGISTRY = {
    "inferno": cv2.COLORMAP_INFERNO,  # Perceptually uniform gold/red/purple (Medical standard)
    "viridis": cv2.COLORMAP_VIRIDIS,  # Colorblind-safe green/yellow/blue
    "plasma": cv2.COLORMAP_PLASMA,    # High dynamic range thermal
    "hot": cv2.COLORMAP_HOT,          # Classic blackbody radiation
    "jet": cv2.COLORMAP_JET           # Legacy rainbow
}

class GradCAMGenerator:
    """
    Gradient-weighted Class Activation Mapping (Grad-CAM) generator
    for explaining CNN chest radiography classifications with anatomical zonation.
    """

    def __init__(self, cnn_wrapper: PneumoniaCNNModel):
        self.cnn_wrapper = cnn_wrapper
        self.target_layer_name = cnn_wrapper.target_conv_layer_name
        self._grad_model: Optional[keras.Model] = None
        self._init_grad_model()

    def _init_grad_model(self):
        """Constructs gradient extraction sub-graph with symbolic base input."""
        base_model = self.cnn_wrapper.model
        if base_model is None:
            raise RuntimeError("Base CNN model is not loaded.")

        target_layer = base_model.get_layer(self.target_layer_name)
        self._grad_model = keras.Model(
            inputs=base_model.input,
            outputs=[target_layer.output, base_model.output]
        )

    def compute_heatmap(self, tensor: np.ndarray) -> np.ndarray:
        """
        Computes 2D normalized activation heatmap [0.0, 1.0].
        
        Args:
            tensor: (1, 150, 150, 1) float32 normalized image tensor
            
        Returns:
            heatmap: (H, W) float32 array in range [0, 1]
        """
        if self._grad_model is None:
            self._init_grad_model()

        with tf.GradientTape() as tape:
            conv_outputs, predictions = self._grad_model(tensor, training=False)
            loss = predictions[:, 0]

        # Gradients of target class score w.r.t feature maps of last conv layer
        grads = tape.gradient(loss, conv_outputs)
        if grads is None:
            return np.zeros((settings.INPUT_HEIGHT, settings.INPUT_WIDTH), dtype=np.float32)

        # Global average pooling of gradients
        pooled_grads = tf.reduce_mean(grads, axis=(0, 1, 2))

        # Weight the feature maps by their gradient importance
        conv_outputs = conv_outputs[0]
        heatmap = tf.reduce_sum(conv_outputs * pooled_grads, axis=-1)

        # ReLU: Keep only features that positively correlate with the classification
        heatmap = tf.maximum(heatmap, 0.0)
        max_val = tf.math.reduce_max(heatmap)
        if max_val > 1e-7:
            heatmap = heatmap / max_val

        return heatmap.numpy()

    def analyze_anatomical_zonation(self, heatmap: np.ndarray) -> Dict[str, Any]:
        """
        Calculates quantified opacity concentration across anatomical thoracic quadrants.
        Radiographic convention: Left side of image is Patient's Right Lung.
        """
        h, w = heatmap.shape
        mid_h, mid_w = h // 2, w // 2

        # Patient Right Lung (Left half of film)
        rul = float(np.mean(heatmap[:mid_h, :mid_w]))
        rll = float(np.mean(heatmap[mid_h:, :mid_w]))

        # Patient Left Lung (Right half of film)
        lul = float(np.mean(heatmap[:mid_h, mid_w:]))
        lll = float(np.mean(heatmap[mid_h:, mid_w:]))

        total = rul + rll + lul + lll + 1e-6
        pct_rul = round((rul / total) * 100, 1)
        pct_rll = round((rll / total) * 100, 1)
        pct_lul = round((lul / total) * 100, 1)
        pct_lll = round((lll / total) * 100, 1)

        zones = {
            "Right Upper Lobe": pct_rul,
            "Right Lower Lobe": pct_rll,
            "Left Upper Lobe": pct_lul,
            "Left Lower Lobe": pct_lll,
        }
        dominant_zone = max(zones, key=zones.get)

        return {
            "right_upper_lobe_pct": pct_rul,
            "right_lower_lobe_pct": pct_rll,
            "left_upper_lobe_pct": pct_lul,
            "left_lower_lobe_pct": pct_lll,
            "dominant_zone": dominant_zone
        }

    def generate_overlay(
        self,
        original_gray: np.ndarray,
        tensor: np.ndarray,
        colormap_name: str = "inferno",
        alpha: float = 0.45
    ) -> Tuple[np.ndarray, np.ndarray, Dict[str, Any]]:
        """
        Generates colored heatmap and blends it onto the original grayscale radiograph.
        
        Args:
            original_gray: (H, W) uint8 grayscale image
            tensor: (1, 150, 150, 1) float32 model tensor
            colormap_name: "inferno", "viridis", "plasma", "hot", or "jet"
            alpha: Heatmap blend opacity [0.0, 1.0]
            
        Returns:
            Tuple of:
              - blended_bgr: (H, W, 3) uint8 image with heatmap superimposed
              - colored_heatmap_bgr: (H, W, 3) raw colored heatmap
              - zonation: Dict with anatomical quadrant metrics
        """
        raw_heatmap = self.compute_heatmap(tensor)
        zonation = self.analyze_anatomical_zonation(raw_heatmap)

        # Resize heatmap to match the input image shape
        h, w = original_gray.shape[:2]
        resized_heatmap = cv2.resize(raw_heatmap, (w, h), interpolation=cv2.INTER_CUBIC)

        # Rescale heatmap to 0-255 uint8
        heatmap_uint8 = np.uint8(255 * np.clip(resized_heatmap, 0.0, 1.0))

        # Select medical colormap
        colormap_id = COLORMAP_REGISTRY.get(colormap_name.lower(), cv2.COLORMAP_INFERNO)
        colored_heatmap = cv2.applyColorMap(heatmap_uint8, colormap_id)

        # Convert original image to 3-channel BGR for blending
        if original_gray.ndim == 2:
            orig_bgr = cv2.cvtColor(original_gray, cv2.COLOR_GRAY2BGR)
        else:
            orig_bgr = original_gray.copy()

        # Superimpose heatmap onto radiograph
        blended = cv2.addWeighted(orig_bgr, 1.0 - alpha, colored_heatmap, alpha, 0)

        return blended, colored_heatmap, zonation
