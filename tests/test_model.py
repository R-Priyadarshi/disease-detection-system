import pytest
import numpy as np
import tensorflow as tf

from core.config import settings
from core.model import PneumoniaCNNModel, get_model

def test_model_architecture():
    """Verify that the CNN architecture has the expected layers and parameters."""
    model_wrapper = get_model()
    assert model_wrapper.model is not None

    layer_names = [l.name for l in model_wrapper.model.layers]
    assert "conv2d" in layer_names
    assert "conv2d_1" in layer_names
    assert "conv2d_2" in layer_names
    assert "dense_1" in layer_names

    # Check total trainable parameters match the trained weights ~319K
    trainable_count = int(np.sum([np.prod(v.shape) for v in model_wrapper.model.trainable_weights]))
    assert trainable_count > 300_000

def test_model_inference():
    """Verify that tensor prediction returns properly formatted clinical dictionary."""
    model_wrapper = get_model()
    # Dummy normalized tensor
    dummy_input = np.ones((1, settings.INPUT_HEIGHT, settings.INPUT_WIDTH, 1), dtype=np.float32) * 0.5
    
    result = model_wrapper.predict_tensor(dummy_input)
    assert "diagnosis" in result
    assert result["diagnosis"] in {"PNEUMONIA", "NORMAL"}
    assert 0.0 <= result["probability"] <= 1.0
    assert 0.0 <= result["confidence_percentage"] <= 100.0
    assert "risk_tier" in result
    assert "latency_ms" in result
    assert result["latency_ms"] >= 0.0
