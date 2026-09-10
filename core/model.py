import os
import time
from typing import Dict, Any, Optional
import numpy as np
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras.layers import Input, Conv2D, MaxPool2D, Flatten, Dense, BatchNormalization

from core.config import settings
from core.preprocessor import preprocessor

class ModelLoadError(RuntimeError):
    """Raised when the neural network weights fail to load."""
    pass

class PneumoniaCNNModel:
    """Production wrapper for Chest X-Ray Pneumonia detection CNN."""

    def __init__(self, weights_path: Optional[str] = None):
        self.weights_path = str(weights_path or settings.MODEL_WEIGHTS_PATH)
        self.model: Optional[keras.Model] = None
        self._target_conv_layer_name = "conv2d_2"
        self._build_and_load()

    def _build_architecture(self) -> keras.Model:
        """Constructs the CNN architecture matching the trained weights with symbolic input."""
        inputs = Input(
            shape=(settings.INPUT_HEIGHT, settings.INPUT_WIDTH, settings.INPUT_CHANNELS),
            name="input_layer"
        )
        x = Conv2D(16, (3, 3), activation='relu', name="conv2d")(inputs)
        x = MaxPool2D((2, 2), name="max_pooling2d")(x)
        x = Conv2D(32, (3, 3), activation='relu', name="conv2d_1")(x)
        x = MaxPool2D((2, 2), name="max_pooling2d_1")(x)
        x = Conv2D(64, (3, 3), activation='relu', name="conv2d_2")(x)
        x = MaxPool2D((2, 2), name="max_pooling2d_2")(x)
        x = Flatten(name="flatten")(x)
        x = Dense(16, activation='relu', name="dense")(x)
        x = BatchNormalization(axis=1, name="batch_normalization")(x)
        outputs = Dense(1, activation='sigmoid', name="dense_1")(x)

        model = keras.Model(inputs=inputs, outputs=outputs, name="PneumoniaDetectionCNN")
        return model

    def _build_and_load(self):
        """Builds architecture and loads weights with validation."""
        self.model = self._build_architecture()
        if os.path.exists(self.weights_path):
            try:
                self.model.load_weights(self.weights_path)
            except Exception as e:
                raise ModelLoadError(f"Failed to load weights from '{self.weights_path}': {e}")
        else:
            raise FileNotFoundError(f"Weights file not found at: {self.weights_path}")

    @property
    def target_conv_layer_name(self) -> str:
        """Returns the name of the final convolutional layer for Grad-CAM."""
        return self._target_conv_layer_name

    def predict_tensor(self, tensor: np.ndarray) -> Dict[str, Any]:
        """
        Executes forward inference on preprocessed tensor.
        
        Args:
            tensor: (1, 150, 150, 1) float32 normalized image tensor
            
        Returns:
            Dict containing raw probability, binary diagnosis, confidence percentage,
            risk assessment tier, and execution latency.
        """
        if self.model is None:
            raise RuntimeError("Model is not initialized.")

        start_time = time.perf_counter()
        raw_output = self.model(tensor, training=False)
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

        prob = float(raw_output.numpy()[0][0])
        is_positive = bool(prob >= settings.CONFIDENCE_THRESHOLD_POSITIVE)

        if is_positive:
            diagnosis = "PNEUMONIA"
            confidence = prob * 100.0
            if prob >= settings.RISK_THRESHOLD_HIGH:
                risk_tier = "HIGH_CONFIDENCE_PNEUMONIA"
                clinical_note = "High likelihood of pulmonary consolidation/infiltrate detected. Immediate clinical review recommended."
            else:
                risk_tier = "MODERATE_RISK_PNEUMONIA"
                clinical_note = "Features suggestive of mild or developing pneumonia detected. Clinical correlation advised."
        else:
            diagnosis = "NORMAL"
            confidence = (1.0 - prob) * 100.0
            if prob < (1.0 - settings.RISK_THRESHOLD_HIGH):
                risk_tier = "CLEAR_LUNG_FIELDS"
                clinical_note = "No acute radiographic evidence of consolidative pneumonia detected."
            else:
                risk_tier = "BORDERLINE_NORMAL"
                clinical_note = "Borderline clear lung fields with subtle focal patterns. Consider follow-up if symptoms persist."

        return {
            "diagnosis": diagnosis,
            "is_pneumonia": is_positive,
            "probability": round(prob, 4),
            "confidence_percentage": round(confidence, 1),
            "risk_tier": risk_tier,
            "clinical_recommendation": clinical_note,
            "latency_ms": latency_ms
        }

    def predict_multilabel(
        self,
        tensor: np.ndarray,
        raw_gray: np.ndarray,
        zonation: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Executes full multi-label thoracic diagnostic evaluation across all 6
        pathology classes (Pneumonia, Pneumothorax, Pleural Effusion, Cardiomegaly,
        Atelectasis, and Normal).
        """
        base = self.predict_tensor(tensor)
        from core.multilabel import get_multilabel_engine
        multi_engine = get_multilabel_engine()
        analysis = multi_engine.analyze_radiograph(raw_gray, base["probability"], zonation)

        return {
            **base,
            "primary_finding": analysis["primary_finding"],
            "primary_display_name": analysis["primary_display_name"],
            "primary_confidence": analysis["primary_confidence"],
            "is_pathology_present": analysis["is_pathology_present"],
            "priority": analysis["priority"],
            "priority_rank": analysis["priority_rank"],
            "clinical_impression": analysis["clinical_impression"],
            "secondary_findings": analysis["secondary_findings"],
            "all_findings": analysis["all_findings"],
            "detected_findings": analysis["detected_findings"]
        }

_model_instance: Optional[PneumoniaCNNModel] = None

def get_model() -> PneumoniaCNNModel:
    global _model_instance
    if _model_instance is None:
        _model_instance = PneumoniaCNNModel()
    return _model_instance

