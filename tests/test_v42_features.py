"""
Tests for ALVEON v4.2 Production Enterprise Features:
- Option A: Hospital EHR Interoperability (HL7 v2 ORM^O01 / ORU^R01 / ACK + FHIR R4 Bundle & Resources)
- Option B: Local AI Patient Discharge Summarizer (Grade 6 Multi-Lingual: EN, ES, FR, HI, ZH)
- Option C: STAT Critical Trauma Alerting & Closed-Loop Verbal Readback with SHA-256 Audit Ledger
- Option D: Multi-Modality Brain CT Stroke & Hemorrhage Suite (Hounsfield Windowing, ASPECTS 10-zone, Midline Shift)
"""

import pytest
from fastapi.testclient import TestClient
from api.app import app
from core.hl7_engine import get_hl7_engine
from core.fhir_engine import get_fhir_engine
from core.patient_summary import get_patient_summary_engine
from core.alerting_engine import get_alerting_engine
from core.neuro_engine import get_neuro_engine
from core.volumetric import get_volumetric_engine


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


# =====================================================================
# OPTION A: HL7 v2 & FHIR R4 INTEROPERABILITY TESTS
# =====================================================================

def test_hl7_order_ingestion_and_ack(client):
    """Test receiving inbound HL7 ORM^O01 order and producing ACK^R01."""
    raw_orm = (
        "MSH|^~\\&|EPIC_EHR|METRO_HOSPITAL|ALVEON_AI|RADIOLOGY|20260911000000||ORM^O01|MSG-99201|P|2.5\r"
        "PID|1||MRN-HL7-TEST^^^HOSPITAL||DOE^JANE||19850412|F\r"
        "PV1|1|E|ER-TRAUMA-BAY-2\r"
        "ORC|NW|ORD-99201|||||||20260911000000\r"
        "OBR|1|ORD-99201||71045^CHEST XR 2-VIEWS^CPT|||20260911000000|||||||||||||||||CRITICAL CHEST PAIN"
    )

    res = client.post("/api/v1/hl7/order", json={"raw_hl7": raw_orm})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["order"]["patient_mrn"] == "MRN-HL7-TEST"
    assert data["order"]["patient_name"] == "DOE, JANE"
    assert "MSA|AA|MSG-99201" in data["ack_message"]


def test_hl7_oru_result_generation(client):
    """Test retrieving synthesized HL7 ORU^R01 observation message."""
    res = client.get("/api/v1/hl7/report/STUDY-CHEST-9901")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["study_id"] == "STUDY-CHEST-9901"
    raw_oru = data["raw_oru_r01"]
    assert "ORU^R01" in raw_oru
    assert "ALVEON Primary Diagnosis" in raw_oru
    assert "ACR Category 1" in raw_oru


def test_fhir_r4_resources(client):
    """Test standard FHIR R4 DiagnosticReport, Observation, and ImagingStudy."""
    study_id = "STUDY-CHEST-9901"

    # DiagnosticReport
    res_report = client.get(f"/api/v1/fhir/DiagnosticReport/{study_id}")
    assert res_report.status_code == 200
    report_data = res_report.json()
    assert report_data["resourceType"] == "DiagnosticReport"
    assert report_data["status"] == "final"
    assert "code" in report_data
    assert len(report_data["result"]) >= 1

    # Observation Bundle
    res_obs = client.get(f"/api/v1/fhir/Observation/{study_id}")
    assert res_obs.status_code == 200
    obs_bundle = res_obs.json()
    assert obs_bundle["resourceType"] == "Bundle"
    assert obs_bundle["entry"][0]["resource"]["resourceType"] == "Observation"

    # ImagingStudy
    res_study = client.get(f"/api/v1/fhir/ImagingStudy/{study_id}")
    assert res_study.status_code == 200
    study_data = res_study.json()
    assert study_data["resourceType"] == "ImagingStudy"
    assert study_id.lower() in study_data["id"]


# =====================================================================
# OPTION B: PATIENT DISCHARGE SUMMARIZER (MULTI-LINGUAL GRADE 6)
# =====================================================================

def test_patient_discharge_summary_languages(client):
    """Verify 6th-grade layperson discharge summary across all 5 languages."""
    languages = [
        ("en", "pneumonia"),
        ("es", "neumonía"),
        ("fr", "pneumonie"),
        ("hi", "निमोनिया"),
        ("zh", "肺炎")
    ]

    for lang_code, exp_diag in languages:
        payload = {
            "diagnosis": "PNEUMONIA",
            "confidence_percentage": 96.5,
            "clinical_impression": "Airspace opacity in right lower lobe consistent with acute pneumonia.",
            "language": lang_code,
            "patient_name": "Elena Rostova",
            "patient_mrn": "MRN-101"
        }
        res = client.post("/api/v1/patient/summary", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["language"] == lang_code
        assert "6th Grade" in data["reading_level"]
        assert exp_diag.lower() in data["title"].lower() or exp_diag in data["what_was_found"]
        assert len(data["what_you_need_to_do"]) > 10
        assert len(data["warning_signs"]) > 10


def test_patient_discharge_trauma_layperson(client):
    """Verify layman explanation of Pneumothorax / Trauma findings in Spanish."""
    payload = {
        "diagnosis": "PNEUMOTHORAX",
        "confidence_percentage": 98.2,
        "clinical_impression": "Tension pneumothorax with visceral pleural line retraction.",
        "language": "es",
        "patient_name": "Carlos Gomez",
        "patient_mrn": "MRN-TRAUMA-ES"
    }
    res = client.post("/api/v1/patient/summary", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "colapso" in data["what_was_found"].lower() or "neumotórax" in data["title"].lower()


# =====================================================================
# OPTION C: STAT CRITICAL ALERTING & CLOSED-LOOP HANDOFF TESTS
# =====================================================================

def test_worklist_critical_alerts_and_acr(client):
    """Verify emergency worklist contains STAT critical alerts and ACR Category 1 flags."""
    res = client.get("/api/v1/worklist")
    assert res.status_code == 200
    studies = res.json()["studies"]
    assert len(studies) >= 1

    # Verify STAT critical triage prioritisation
    stat_studies = [s for s in studies if s.get("priority") == "STAT_CRITICAL"]
    assert len(stat_studies) >= 1
    assert stat_studies[0]["priority_rank"] == 1


def test_closed_loop_verbal_readback_and_audit_ledger(client):
    """Verify physician verbal readback sealing into HIPAA SHA-256 ledger."""
    study_id = "STUDY-CHEST-9901"
    payload = {
        "study_id": study_id,
        "patient_mrn": "MRN-TRAUMA-4410",
        "patient_name": "Sterling, Connor",
        "critical_finding": "Confirmed 35% tension pneumothorax right lung",
        "radiologist_name": "Dr. Elena Rostova, MD",
        "er_physician_name": "Dr. Mark Sloan, MD",
        "communication_method": "Trauma Bay Hotline",
        "readback_confirmed": True,
        "notes": "Immediate chest tube tray prepped."
    }

    res = client.post("/api/v1/alert/closed-loop", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["handoff"]["study_id"] == study_id
    assert data["handoff"]["readback_confirmed"] is True
    assert "audit_hash" in data["handoff"]
    assert len(data["handoff"]["audit_hash"]) == 64  # SHA-256 hex string

    # Verify query for this study
    res_get = client.get(f"/api/v1/alert/closed-loop/{study_id}")
    assert res_get.status_code == 200
    get_data = res_get.json()
    assert get_data["status"] == "recorded"
    assert get_data["handoff"]["er_physician_name"] == "Dr. Mark Sloan, MD"


# =====================================================================
# OPTION D: MULTI-MODALITY BRAIN CT STROKE & HEMORRHAGE SUITE TESTS
# =====================================================================

def test_neuro_series_listing(client):
    """Verify registered Brain CT series in Neuro suite."""
    res = client.get("/api/v1/neuro/series")
    assert res.status_code == 200
    series = res.json()["series"]
    assert len(series) >= 2

    series_ids = [s["series_id"] for s in series]
    assert "BRAIN-CT-STROKE-01" in series_ids
    assert "BRAIN-CT-SDH-02" in series_ids


def test_neuro_volume_ai_analysis(client):
    """Verify ASPECTS scoring, hemorrhage detection, and midline shift analysis."""
    # 1. Acute Ischemic Stroke Series
    res_stroke = client.post("/api/v1/neuro/analyze/BRAIN-CT-STROKE-01")
    assert res_stroke.status_code == 200
    data_stroke = res_stroke.json()
    assert data_stroke["series_id"] == "BRAIN-CT-STROKE-01"
    assert "Stroke" in data_stroke["primary_diagnosis"]
    assert data_stroke["aspects_score"] == 7
    assert data_stroke["critical_neurosurgical_alert"] is True
    assert "ACR Category 1" in data_stroke["acr_category"]

    # 2. Subdural Hematoma Series
    res_sdh = client.post("/api/v1/neuro/analyze/BRAIN-CT-SDH-02")
    assert res_sdh.status_code == 200
    data_sdh = res_sdh.json()
    assert data_sdh["series_id"] == "BRAIN-CT-SDH-02"
    assert "Hematoma" in data_sdh["primary_diagnosis"]
    assert data_sdh["midline_shift_mm"] >= 4.0
    assert data_sdh["critical_neurosurgical_alert"] is True


def test_neuro_volumetric_slice_and_mpr_rendering(client):
    """Verify Brain CT 3D volume slices and tri-planar MPR render properly."""
    series_id = "BRAIN-CT-STROKE-01"
    
    # 1. Planar slice endpoint
    res_slice = client.get(
        f"/api/v1/volumetric/{series_id}/slice?orientation=AXIAL&slice_idx=16&window_preset=BRAIN_TISSUE"
    )
    assert res_slice.status_code == 200
    slice_data = res_slice.json()
    assert slice_data["status"] == "success"
    assert slice_data["data_url"].startswith("data:image/png;base64,")

    # 2. Tri-planar MPR endpoint
    res_mpr = client.post(
        f"/api/v1/volumetric/{series_id}/mpr",
        json={"axial_idx": 16, "coronal_idx": 32, "sagittal_idx": 32, "window_preset": "BRAIN_TISSUE"}
    )
    assert res_mpr.status_code == 200
    mpr_data = res_mpr.json()
    assert mpr_data["status"] == "success"
    assert mpr_data["axial"]["data_url"].startswith("data:image/png;base64,")
    assert mpr_data["coronal"]["data_url"].startswith("data:image/png;base64,")
    assert mpr_data["sagittal"]["data_url"].startswith("data:image/png;base64,")
