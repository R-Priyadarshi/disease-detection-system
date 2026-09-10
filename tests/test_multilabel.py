"""
Unit tests for ALVEON Multi-Label Thoracic Diagnostic Intelligence Engine.
"""

import pytest
import numpy as np
from core.multilabel import get_multilabel_engine, ThoracicMultiLabelEngine
from core.model import get_model

def test_multilabel_engine_singleton():
    engine1 = get_multilabel_engine()
    engine2 = get_multilabel_engine()
    assert engine1 is engine2
    assert isinstance(engine1, ThoracicMultiLabelEngine)

def test_multilabel_pneumonia_classification():
    engine = get_multilabel_engine()
    raw_gray = np.full((150, 150), 128, dtype=np.uint8)
    
    # Baseline pneumonia probability = 0.92
    res = engine.analyze_radiograph(raw_gray, baseline_pneumonia_prob=0.92)
    assert res["is_pathology_present"] is True
    assert res["primary_finding"] == "PNEUMONIA"
    assert res["priority"] == "STAT_CRITICAL"
    assert res["priority_rank"] == 1

    pneu_finding = next(f for f in res["all_findings"] if f["name"] == "PNEUMONIA")
    assert pneu_finding["is_detected"] is True
    assert pneu_finding["severity"] == "CRITICAL"
    assert pneu_finding["confidence_percentage"] >= 90.0

def test_multilabel_clear_normal_classification():
    engine = get_multilabel_engine()
    raw_gray = np.full((150, 150), 20, dtype=np.uint8)
    
    # Baseline pneumonia probability = 0.02
    res = engine.analyze_radiograph(raw_gray, baseline_pneumonia_prob=0.02)
    assert "all_findings" in res
    assert len(res["all_findings"]) == 6

def test_model_predict_multilabel_integration():
    model = get_model()
    tensor = np.zeros((1, 150, 150, 1), dtype=np.float32)
    raw_gray = np.full((150, 150), 100, dtype=np.uint8)

    res = model.predict_multilabel(tensor, raw_gray)
    assert "diagnosis" in res
    assert "primary_finding" in res
    assert "all_findings" in res
    assert len(res["all_findings"]) == 6
    assert "priority" in res
    assert res["priority"] in ("STAT_CRITICAL", "URGENT", "ROUTINE")
