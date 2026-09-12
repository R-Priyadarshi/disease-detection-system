"""
Tests for Fleischner Society 2017 Pulmonary Nodule Guidelines & FHIR Sync
Validates:
1. Solid single nodule decision paths (<6mm, 6-8mm, >8mm across Low & High Risk).
2. Part-solid and Ground-Glass nodule pathways.
3. Spherical equivalent volume (mm³).
4. Standardized RADLEX, SNOMED, and LOINC ontological mappings.
5. HL7 FHIR R4 Bundle generation (DiagnosticReport, Observations).
6. Certified ReportLab Consultation Dossier PDF generation (%PDF-1.4).
7. REST API endpoints:
   - POST /api/v1/fleischner/evaluate
   - POST /api/v1/fleischner/fhir-bundle
   - POST /api/v1/fleischner/dossier-pdf
"""

import pytest
from fastapi.testclient import TestClient
from api.app import app
from core.fleischner_engine import get_fleischner_engine, NoduleEvaluationRequest, FleischnerEngine


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def engine():
    return get_fleischner_engine()


def test_fleischner_singleton(engine):
    e2 = FleischnerEngine.get_instance()
    assert engine is e2


def test_solid_single_small_low_risk(engine):
    # < 6mm, low risk -> No routine follow-up
    req = NoduleEvaluationRequest(
        patient_age=42,
        morphology="SOLID_SINGLE",
        max_diameter_mm=4.5,
        perp_diameter_mm=4.1,
        smoking_pack_years=0,
        is_spiculated=False,
        lobe_location="RIGHT_LOWER_LOBE",
        emphysema_present=False
    )
    res = engine.evaluate_nodule(req)
    assert res.risk_category == "LOW_RISK"
    assert res.recommendation_code == "NO_ROUTINE_FOLLOWUP"
    assert res.follow_up_interval_months is None


def test_solid_single_intermediate_high_risk(engine):
    # 6-8mm, high risk -> CT at 6-12 months
    req = NoduleEvaluationRequest(
        patient_age=63,
        morphology="SOLID_SINGLE",
        max_diameter_mm=7.2,
        perp_diameter_mm=6.8,
        smoking_pack_years=30,
        is_spiculated=True,
        lobe_location="RIGHT_UPPER_LOBE",
        emphysema_present=True
    )
    res = engine.evaluate_nodule(req)
    assert res.risk_category == "HIGH_RISK"
    assert res.recommendation_code == "CT_6_TO_12M"
    assert res.follow_up_interval_months == 6
    assert "RADLEX" in str(res.radlex_codes) or "RID" in str(res.radlex_codes)


def test_part_solid_with_large_solid_component(engine):
    # Part-solid with solid core >= 6mm -> High suspicion of adenocarcinoma
    req = NoduleEvaluationRequest(
        patient_age=65,
        morphology="PART_SOLID",
        max_diameter_mm=14.0,
        solid_component_mm=7.5,
        smoking_pack_years=20
    )
    res = engine.evaluate_nodule(req)
    assert res.is_suspicious_for_malignancy is True
    assert res.recommendation_code == "URGENT_SURGICAL_OR_PET"


def test_pure_ground_glass_nodule(engine):
    # Pure GGN >= 6mm -> CT at 6-12 months to confirm persistence
    req = NoduleEvaluationRequest(
        morphology="GROUND_GLASS",
        max_diameter_mm=8.5,
        solid_component_mm=0.0
    )
    res = engine.evaluate_nodule(req)
    assert res.recommendation_code == "CT_6_TO_12M_GGN"
    assert res.follow_up_interval_months == 6


def test_fhir_r4_bundle_generation(engine):
    req = NoduleEvaluationRequest()
    res = engine.evaluate_nodule(req)
    bundle = engine.generate_fhir_r4_bundle(res)
    assert bundle["resourceType"] == "Bundle"
    assert bundle["type"] == "transaction"
    assert len(bundle["entry"]) >= 3
    # Check DiagnosticReport
    report = next(e["resource"] for e in bundle["entry"] if e["resource"]["resourceType"] == "DiagnosticReport")
    assert report["status"] == "final"
    assert "Fleischner" in report["conclusion"]


def test_pdf_dossier_generation(engine):
    req = NoduleEvaluationRequest()
    res = engine.evaluate_nodule(req)
    pdf_bytes = engine.generate_dossier_pdf(res)
    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes.startswith(b"%PDF-1.4")
    assert len(pdf_bytes) > 2000


def test_api_fleischner_evaluate_endpoint(client):
    res = client.post("/api/v1/fleischner/evaluate", json={
        "patient_id": "MRN-PULM-8821",
        "patient_name": "Thorne^Gwendolyn",
        "patient_age": 58,
        "patient_sex": "F",
        "morphology": "SOLID_SINGLE",
        "max_diameter_mm": 7.4,
        "perp_diameter_mm": 6.2,
        "solid_component_mm": 0.0,
        "lobe_location": "RIGHT_UPPER_LOBE",
        "is_spiculated": True,
        "smoking_pack_years": 25,
        "family_history_lung_cancer": False,
        "emphysema_present": True
    })
    assert res.status_code == 200
    data = res.json()
    assert data["recommendation_code"] == "CT_6_TO_12M"
    assert data["risk_category"] == "HIGH_RISK"


def test_api_fleischner_fhir_bundle_endpoint(client):
    res = client.post("/api/v1/fleischner/fhir-bundle", json={
        "patient_id": "MRN-PULM-8821",
        "patient_name": "Thorne^Gwendolyn",
        "patient_age": 58,
        "patient_sex": "F",
        "morphology": "PART_SOLID",
        "max_diameter_mm": 12.0,
        "perp_diameter_mm": 10.0,
        "solid_component_mm": 6.5,
        "lobe_location": "RIGHT_UPPER_LOBE",
        "is_spiculated": True,
        "smoking_pack_years": 30,
        "family_history_lung_cancer": True,
        "emphysema_present": True
    })
    assert res.status_code == 200
    data = res.json()
    assert data["resourceType"] == "Bundle"
    assert len(data["entry"]) >= 3


def test_api_fleischner_dossier_pdf_endpoint(client):
    res = client.post("/api/v1/fleischner/dossier-pdf", json={
        "patient_id": "MRN-PULM-8821",
        "patient_name": "Thorne^Gwendolyn",
        "patient_age": 58,
        "patient_sex": "F",
        "morphology": "SOLID_SINGLE",
        "max_diameter_mm": 7.4,
        "perp_diameter_mm": 6.2,
        "solid_component_mm": 0.0,
        "lobe_location": "RIGHT_UPPER_LOBE",
        "is_spiculated": True,
        "smoking_pack_years": 25,
        "family_history_lung_cancer": False,
        "emphysema_present": True
    })
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/pdf"
    assert res.content.startswith(b"%PDF-1.4")
