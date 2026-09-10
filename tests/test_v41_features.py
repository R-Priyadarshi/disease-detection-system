"""
Tests for ALVEON v4.1 Enterprise Features:
- Health and Readiness Probes (/healthz, /readyz)
- Diagnostic Web Viewer Bridge & OHIF Config (/viewer, /api/v1/ohif/config)
- RADLEX Voice Dictation Parser (/api/v1/voice/parse-dictation)
- Structured Reporting Engine (/api/v1/report/structured)
- Orthanc PACS Integration (/api/v1/pacs/orthanc/status, sync)
- ACR / RADLEX Structured PDF Generation
"""

import pytest
from fastapi.testclient import TestClient
from api.app import app
from core.structured_reporting import (
    get_structured_reporting_engine,
    StructuredReportModel,
    NORMAL_CHEST_TEMPLATE,
    TRAUMA_PNEUMOTHORAX_TEMPLATE,
    PNEUMONIA_CONSOLIDATION_TEMPLATE
)
from core.orthanc_integration import get_orthanc_engine
from core.pdf_generator import generate_clinical_report_pdf


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_production_healthz_and_readyz_probes(client):
    """Verify Kubernetes / Nginx probes return 200 OK with component telemetry."""
    res = client.get("/healthz")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["version"] == "4.1.0"
    assert "components" in data
    assert data["components"]["pacs_scp"] == "listening:11112"

    res_ready = client.get("/readyz")
    assert res_ready.status_code == 200
    assert res_ready.json()["status"] == "healthy"


def test_ohif_viewer_and_config_endpoints(client):
    """Verify OHIF configuration and viewer bridge delivery."""
    cfg_res = client.get("/api/v1/ohif/config")
    assert cfg_res.status_code == 200
    cfg = cfg_res.json()
    assert "servers" in cfg
    assert "dicomWeb" in cfg["servers"]
    assert cfg["servers"]["dicomWeb"][0]["wadoRoot"] == "/dicomweb"

    viewer_res = client.get("/viewer")
    assert viewer_res.status_code == 200
    assert "Diagnostic" in viewer_res.text and "OHIF" in viewer_res.text


def test_voice_dictation_macros(client):
    """Verify speech-to-report macro triggers in voice engine."""
    # Normal macro
    res_normal = client.post("/api/v1/voice/parse-dictation", json={
        "transcript": "computer insert normal chest radiograph template"
    })
    assert res_normal.status_code == 200
    data_normal = res_normal.json()
    assert data_normal["command_detected"] == "INSERT_NORMAL_TEMPLATE"
    assert "clear" in data_normal["structured_report"]["findings_lungs"].lower()
    assert data_normal["structured_report"]["dictated_voice"] is True

    # Trauma macro
    res_trauma = client.post("/api/v1/voice/parse-dictation", json={
        "transcript": "insert trauma pneumothorax template immediately"
    })
    assert res_trauma.status_code == 200
    data_trauma = res_trauma.json()
    assert data_trauma["command_detected"] == "INSERT_TRAUMA_TEMPLATE"
    assert "tension pneumothorax" in data_trauma["structured_report"]["findings_pleura"].lower()

    # Signoff voice command
    res_sign = client.post("/api/v1/voice/parse-dictation", json={
        "transcript": "attest report signoff"
    })
    assert res_sign.status_code == 200
    assert res_sign.json()["command_detected"] == "ATTEST_SIGNOFF"


def test_voice_dictation_section_edits(client):
    """Verify targeting specific anatomical sections via voice commands."""
    res_lungs = client.post("/api/v1/voice/parse-dictation", json={
        "transcript": "dictate lungs dense retrocardiac consolidation left lower lobe"
    })
    assert res_lungs.status_code == 200
    d = res_lungs.json()
    assert d["command_detected"] == "EDIT_SECTION"
    assert d["target_field"] == "findings_lungs"
    assert "dense retrocardiac consolidation left lower lobe" in d["structured_report"]["findings_lungs"]


def test_structured_report_synthesis(client):
    """Verify synthesizing RADLEX report from AI findings."""
    res = client.post("/api/v1/report/structured", json={
        "diagnosis": "PNEUMONIA",
        "confidence_percentage": 97.4,
        "all_findings": [
            {"label": "Pneumonia / Consolidation", "probability": 0.974, "status": "POSITIVE"},
            {"label": "Pleural Effusion", "probability": 0.62, "status": "POSITIVE"}
        ],
        "zonation": {
            "predominant_zone": "Left Lower Zone",
            "left_lower": 78.4
        }
    })
    assert res.status_code == 200
    report = res.json()["structured_report"]
    assert "Left Lower Zone" in report["findings_lungs"]
    assert "pneumonia" in report["impression"].lower()
    assert "ACR Category" in report["acr_actionable_code"]


def test_orthanc_pacs_endpoints(client):
    """Verify Orthanc status ping and sync endpoints."""
    res_status = client.get("/api/v1/pacs/orthanc/status")
    assert res_status.status_code == 200
    data = res_status.json()
    assert "orthanc" in data
    assert data["orthanc"]["ae_title"] == "ORTHANC_PACS"

    res_sync = client.post("/api/v1/pacs/orthanc/sync")
    assert res_sync.status_code == 200
    sync_data = res_sync.json()
    assert sync_data["status"] == "success"
    assert sync_data["synced_studies_count"] >= 0


def test_pdf_generation_with_radlex_structured_block():
    """Verify PDF generator embeds the RADLEX structured reporting block."""
    engine = get_structured_reporting_engine()
    rep = engine.generate_report_from_findings(
        diagnosis="PNEUMONIA",
        confidence=94.5,
        multilabel_findings=[{"label": "Pneumonia", "probability": 0.945, "status": "POSITIVE"}],
        zonation={"predominant_zone": "Right Mid Zone"}
    )
    rep.dictated_voice = True
    rep.attesting_physician = "Dr. Elena Rostova, MD (Attending Radiologist)"

    buf = generate_clinical_report_pdf({
        "patient_name": "TEST^PATIENT",
        "patient_mrn": "MRN-TEST-V41",
        "study_id": "ALV-V41-01",
        "modality": "DX",
        "exam_date": "2026-09-10",
        "prediction_label": "PNEUMONIA",
        "confidence_pct": 94.5,
        "zonation": {"predominant_zone": "Right Mid Zone", "right_mid": 75.0},
        "multilabel_findings": [{"label": "Pneumonia / Consolidation", "probability": 0.945, "status": "POSITIVE"}],
        "structured_report": rep.model_dump()
    })
    pdf_bytes = buf.getvalue()

    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 2000
    assert pdf_bytes.startswith(b"%PDF")
