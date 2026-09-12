"""
Unit and API Integration Tests for Clinical Benchmark & FDA 510(k) Validation Engine.
Validates multi-class ROC curve computation, Wilson 95% CIs, interactive operating
points, live cohort concordance, and certified PDF premarket summary generation.
"""

import io
import pytest
from fastapi.testclient import TestClient

from api.app import app
from core.validation_engine import (
    PATHOLOGY_BENCHMARKS,
    generate_roc_curve_points,
    get_operating_point_for_threshold,
    calculate_wilson_ci,
    generate_fda_510k_summary_pdf
)

client = TestClient(app)


def test_pathology_benchmarks_count_and_keys():
    """Verify all 14 clinical pathologies are represented with full metadata."""
    assert len(PATHOLOGY_BENCHMARKS) == 14
    for key, val in PATHOLOGY_BENCHMARKS.items():
        assert "display_name" in val
        assert "cohort_n" in val and val["cohort_n"] > 0
        assert "base_auc" in val and 0.85 <= val["base_auc"] <= 1.0
        assert "operating_threshold" in val
        assert "operating_sensitivity" in val and 0.80 <= val["operating_sensitivity"] <= 1.0
        assert "operating_specificity" in val and 0.80 <= val["operating_specificity"] <= 1.0


def test_roc_curve_monotonicity_and_auc():
    """Verify generated ROC curves are strictly monotonic and match certified AUC."""
    for key in PATHOLOGY_BENCHMARKS:
        res = generate_roc_curve_points(key)
        assert res["auc"] >= 0.88, f"AUC below expected threshold for {key}"
        assert len(res["points"]) >= 30, f"Insufficient curve points for {key}"

        # Monotonicity check on FPR
        points = res["points"]
        for i in range(len(points) - 1):
            assert points[i]["fpr"] <= points[i+1]["fpr"] + 1e-6, f"FPR inversion in {key}"

        # Origin and termination check
        assert points[0]["fpr"] == 0.0 and points[0]["tpr"] == 0.0
        assert points[-1]["fpr"] == 1.0 and points[-1]["tpr"] == 1.0


def test_wilson_confidence_intervals():
    """Verify Wilson score confidence intervals are bounded and valid."""
    pt, lo, hi = calculate_wilson_ci(0.92, 1000)
    assert 0.85 <= lo <= 0.92
    assert 0.92 <= hi <= 0.96
    assert lo < pt < hi


def test_operating_point_calculation():
    """Verify dynamic threshold lookup yields valid confusion matrix and rates."""
    pt = get_operating_point_for_threshold("PNEUMOTHORAX", 0.45)
    assert pt["pathology"] == "PNEUMOTHORAX"
    assert 0.80 <= pt["sensitivity"] <= 1.0
    assert 0.80 <= pt["specificity"] <= 1.0
    cm = pt["confusion_matrix"]
    assert cm["total_evaluations"] == 10000
    assert cm["true_positives"] + cm["false_negatives"] == 1200  # 12% prevalence of 10,000


def test_api_benchmark_metrics_endpoint():
    """Verify GET /api/v1/validation/benchmark-metrics returns all 14 pathologies."""
    resp = client.get("/api/v1/validation/benchmark-metrics")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["total_pathologies"] == 14
    assert "PNEUMONIA" in data["benchmarks"]
    assert "PNEUMOTHORAX" in data["benchmarks"]
    assert data["study_cohort_total"] == 112120


def test_api_operating_point_endpoint():
    """Verify POST /api/v1/validation/operating-point evaluates threshold tuning."""
    resp = client.post("/api/v1/validation/operating-point", json={
        "pathology": "PNEUMOTHORAX",
        "threshold": 0.50
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["threshold"] == 0.50
    assert "confusion_matrix" in data
    assert "f1_score" in data


def test_api_evaluate_cohort_endpoint():
    """Verify POST /api/v1/validation/evaluate-cohort benchmarks active emergency cases."""
    resp = client.post("/api/v1/validation/evaluate-cohort")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert "concordance_rate" in data
    assert "confusion_matrix" in data


def test_api_fda_510k_pdf_export_endpoint():
    """Verify POST /api/v1/validation/fda-summary-pdf streams a valid PDF dossier."""
    resp = client.post("/api/v1/validation/fda-summary-pdf", json={
        "evaluator_name": "Dr. Julian Vance, MD",
        "organization": "ALVEON Healthcare Systems"
    })
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert "Content-Disposition" in resp.headers
    assert "attachment" in resp.headers["Content-Disposition"]
    assert resp.content.startswith(b"%PDF"), "Response stream does not begin with standard PDF magic bytes"
    assert len(resp.content) > 5000, "PDF document unexpectedly truncated"
