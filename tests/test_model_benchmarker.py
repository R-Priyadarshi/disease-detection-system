"""
Tests for Multi-Model Deep Learning Architecture Benchmarking Engine
Validates:
1. Retrieval of 4 computer vision architectures (DenseNet, ResNet, ViT, ConvNeXt).
2. Architectural parameters, FLOPs, and latency comparisons.
3. Multi-model comparative inference on studies.
4. Consensus vs. discrepant finding classification.
5. Cohen's Kappa agreement matrix arithmetic.
6. REST API endpoints:
   - GET /api/v1/benchmark/architectures
   - POST /api/v1/benchmark/compare-inference
"""

import pytest
from fastapi.testclient import TestClient
from api.app import app
from core.model_benchmarker import get_model_benchmarker, ModelBenchmarker


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def benchmarker():
    return get_model_benchmarker()


def test_benchmarker_singleton(benchmarker):
    b2 = ModelBenchmarker.get_instance()
    assert benchmarker is b2


def test_list_architectures_count_and_keys(benchmarker):
    archs = benchmarker.list_architectures()
    assert len(archs) == 4
    ids = {a.id for a in archs}
    assert "densenet_121" in ids
    assert "resnet_50_d" in ids
    assert "vit_b_16" in ids
    assert "convnext_tiny" in ids


def test_architecture_parameter_order(benchmarker):
    archs = {a.id: a for a in benchmarker.list_architectures()}
    # DenseNet-121 should have fewest parameters (~7M)
    assert archs["densenet_121"].parameters_million < 10.0
    # ViT should have most parameters (~86M) and highest GFLOPs
    assert archs["vit_b_16"].parameters_million > 80.0
    assert archs["vit_b_16"].gflops > 30.0


def test_cohens_kappa_calculation(benchmarker):
    # Perfect agreement
    y1 = [1, 1, 0, 0, 1]
    y2 = [1, 1, 0, 0, 1]
    assert benchmarker._calculate_cohens_kappa(y1, y2) == 1.0

    # Strong agreement
    y3 = [1, 1, 0, 0, 0]
    kappa = benchmarker._calculate_cohens_kappa(y1, y3)
    assert 0.5 < kappa < 1.0


def test_compare_inference_study(benchmarker):
    res = benchmarker.compare_inference_on_study("STUDY-CHEST-9901")
    assert len(res.architectures) == 4
    assert len(res.model_predictions) == 4
    assert "Pneumonia" in res.consensus_findings
    assert "Consolidation" in res.consensus_findings
    # Cohen's Kappa matrix should have 1.0 on diagonals
    for a in res.architectures:
        assert res.cohens_kappa_matrix[a.id][a.id] == 1.0


def test_api_benchmark_architectures_endpoint(client):
    res = client.get("/api/v1/benchmark/architectures")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 4
    names = [d["display_name"] for d in data]
    assert any("CheXNet" in n for n in names)
    assert any("Transformer" in n for n in names)


def test_api_compare_inference_endpoint(client):
    res = client.post("/api/v1/benchmark/compare-inference", json={
        "study_id": "STUDY-CHEST-9901",
        "base_probabilities": {
            "Pneumonia": 0.91,
            "Consolidation": 0.95,
            "Infiltration": 0.88,
            "Effusion": 0.20
        }
    })
    assert res.status_code == 200
    data = res.json()
    assert data["study_id"] == "STUDY-CHEST-9901"
    assert "Consolidation" in data["consensus_findings"]
    assert "densenet_121" in data["model_predictions"]
    assert "vit_b_16" in data["model_predictions"]
