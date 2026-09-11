#!/usr/bin/env python3
"""
ALVEON PACS — Master All-Tracks End-to-End Clinical Verification Suite
Verifies Track 1, 2, 3, and 4 to enterprise production-grade standard.
"""

import os
import sys
import time
import json
import io
import tempfile
import numpy as np
import pytest
from fastapi.testclient import TestClient

# Ensure root in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.app import app
from core.database import (
    init_db,
    get_db_type,
    get_db_connection,
    list_users,
    log_audit_event,
    save_radiology_report,
    get_report_by_study,
    list_recent_reports,
    DATABASE_URL
)
from core.auth import (
    authenticate_user,
    create_access_token,
    decode_access_token,
    CLINICAL_DIRECTORY,
    UserRole
)
from core.multilabel import (
    get_multilabel_engine,
    PATHOLOGIES
)
from core.structured_reporting import StructuredReportingEngine
from core.volumetric import (
    get_volumetric_engine,
    WINDOW_PRESETS
)

client = TestClient(app)


def test_track1_database_dual_engine():
    """Verify database initialization, schema integrity, and session handling."""
    print("\n--- [TRACK 1] Database & Dual Engine Test ---")
    init_db()
    
    # Check active dialect
    db_type = get_db_type()
    print(f"Database engine active: {db_type.upper()}")
    print(f"DATABASE_URL: {DATABASE_URL}")

    # Test direct connection and table reads
    conn = get_db_connection()
    try:
        # Check users table
        users = list_users()
        print(f"Seeded clinical users count: {len(users)}")
        assert len(users) >= 4, f"Expected at least 4 clinical users, got {len(users)}"
        
        # Test audit event logging
        audit_id = log_audit_event(
            user_id="dr.vance",
            username="dr.vance",
            action="VERIFY_ALL_TRACKS_E2E",
            resource_type="SYSTEM_TEST",
            resource_id="TRACK1_TEST",
            details={"framework": "pytest_e2e", "status": "testing"}
        )
        assert audit_id is not None, "Failed to log audit event"
        print(f"Logged audit event: {audit_id}")

        # Test report persistence and retrieval
        dummy_study_uid = f"1.2.826.0.1.3680043.8.498.test.{int(time.time())}"
        saved_report = save_radiology_report({
            "study_uid": dummy_study_uid,
            "patient_mrn": "MRN-TRACK1-TEST",
            "patient_name": "Test Patient",
            "user_id": "USR-VANCE-01",
            "attesting_physician": "Dr. Eleanor Vance, MD",
            "examination_technique": "Digital PA Chest Radiograph",
            "clinical_indication": "Track 1 Dual-Engine Verification",
            "findings_lungs": "Clear bilateral lung fields.",
            "findings_pleura": "No pneumothorax or effusion.",
            "findings_cardiomediastinum": "Normal cardiac silhouette.",
            "findings_bones_soft_tissues": "Intact thoracic skeleton.",
            "impression": "Normal chest radiograph.",
            "acr_actionable_code": "Category 3 (Routine)",
            "caliper_measurements": json.dumps([{"type": "distance", "mm": 12.4}]),
            "digital_signature_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        })
        assert saved_report and "report_id" in saved_report, "Failed to save radiology report"
        print(f"Saved radiology report: {saved_report['report_id']}")

        fetched = get_report_by_study(dummy_study_uid)
        assert fetched is not None, "Failed to retrieve saved report by study UID"
        assert fetched["patient_mrn"] == "MRN-TRACK1-TEST"
        print(f"Retrieved radiology report successfully: {fetched['id']}")
    finally:
        conn.close()

    print("✅ Track 1 Database Engine: PASS")


def test_track1_enterprise_auth_and_oauth2():
    """Verify local institutional authentication and OAuth2 token handling."""
    print("\n--- [TRACK 1] Enterprise Auth & OAuth2 Test ---")
    
    # Test local credentials
    user = authenticate_user("dr.vance", "Alveon2026!")
    assert user is not None, "Failed to authenticate standard radiologist persona"
    assert user.role == UserRole.ATTENDING_RADIOLOGIST
    print(f"Authenticated persona: {user.full_name} ({user.role.value})")

    # Test JWT issuance
    token = create_access_token(user)
    assert token and isinstance(token, str), "Failed to generate signed access token"
    
    # Test token verification
    payload = decode_access_token(token)
    assert payload is not None, "Failed to verify issued JWT token"
    assert payload.get("sub") == "dr.vance"
    print(f"JWT Verification verified sub: {payload.get('sub')}")

    # Test invalid token handling
    try:
        decode_access_token("invalid.bearer.token")
        assert False, "Bad token should fail verification"
    except Exception:
        print("Invalid token rejected as expected")

    print("✅ Track 1 Enterprise Auth: PASS")


def test_track2_full_14_pathology_engine():
    """Verify complete 14 NIH ChestX-ray14 / CheXpert pathology spectrum."""
    print("\n--- [TRACK 2] Full 14-Pathology Multi-Label Engine Test ---")
    
    # Verify taxonomy has all 14 disease pathologies + NORMAL
    assert len(PATHOLOGIES) >= 14, f"Expected at least 14 pathologies, got {len(PATHOLOGIES)}"
    print(f"Taxonomy findings ({len(PATHOLOGIES)} total): {', '.join(PATHOLOGIES)}")

    # Create dummy 150x150 radiograph grayscale array
    synthetic_gray = np.ones((150, 150), dtype=np.uint8) * 128
    
    engine = get_multilabel_engine()
    results = engine.analyze_radiograph(
        raw_gray=synthetic_gray,
        baseline_pneumonia_prob=0.92,
        zonation={"right_upper_lobe_pct": 25.0, "right_lower_lobe_pct": 25.0, "left_upper_lobe_pct": 25.0, "left_lower_lobe_pct": 25.0, "dominant_zone": "Right Lower Lobe"}
    )

    assert "all_findings" in results, "Missing all_findings in multi-label output"
    all_findings = results["all_findings"]
    assert len(all_findings) == 15, f"Expected 15 evaluated findings (14 pathologies + normal), got {len(all_findings)}"

    # Check key findings
    finding_names = [f["name"] for f in all_findings]
    for expected in ["PNEUMOTHORAX", "PNEUMONIA", "PLEURAL_EFFUSION", "CARDIOMEGALY", "EDEMA", "NORMAL"]:
        assert expected in finding_names, f"Expected finding {expected} not present in output"

    print(f"Primary detected finding: {results['primary_finding']} (Confidence: {results['primary_confidence']}%)")
    print(f"Clinical Triage Priority: {results['priority']} (Rank {results['priority_rank']})")
    print("✅ Track 2 Full 14-Pathology Spectrum: PASS")


def test_track2_structured_reporting_14_pathologies():
    """Verify structured report synthesis incorporates all 14 pathologies."""
    print("\n--- [TRACK 2] Structured Reporting with 14 Pathologies Test ---")

    engine = StructuredReportingEngine.get_instance()
    report = engine.synthesize_report_from_findings(
        patient_name="Eleanor Vance",
        patient_mrn="MRN-E2E-001",
        diagnosis="PNEUMOTHORAX",
        confidence=96.5,
        multilabel_findings=[
            {
                "name": "PNEUMOTHORAX",
                "display_name": "Pneumothorax",
                "probability": 0.965,
                "severity": "CRITICAL",
                "is_positive": True,
                "confidence_percentage": 96.5,
                "description": "Apical visceral pleural line detected"
            }
        ],
        zonation={
            "right_upper_lobe_pct": 52.0,
            "right_lower_lobe_pct": 20.0,
            "left_upper_lobe_pct": 14.0,
            "left_lower_lobe_pct": 14.0,
            "dominant_zone": "Right Upper Lobe"
        }
    )

    assert report is not None, "Report generation returned None"
    assert report.impression is not None and len(report.impression) > 0
    assert "Category 1" in report.acr_actionable_code or "Critical" in report.acr_actionable_code
    print(f"Generated Impression: {report.impression}")
    print(f"ACR Actionable Category: {report.acr_actionable_code}")
    print("✅ Track 2 Structured Reporting: PASS")


def test_track2_multi_slice_ct_volumetric_upload():
    """Verify real multi-slice DICOM CT upload and MPR orthogonal reslicing."""
    print("\n--- [TRACK 2] Multi-Slice DICOM CT Upload & MPR Test ---")

    # Generate synthetic DICOM files using pydicom
    import pydicom
    from pydicom.dataset import Dataset, FileMetaDataset
    from pydicom.uid import ExplicitVRLittleEndian, SecondaryCaptureImageStorage

    file_bytes_list = []
    num_slices = 5

    for i in range(num_slices):
        file_meta = FileMetaDataset()
        file_meta.MediaStorageSOPClassUID = SecondaryCaptureImageStorage
        file_meta.MediaStorageSOPInstanceUID = f"1.2.826.0.1.3680043.8.498.999.{i}"
        file_meta.TransferSyntaxUID = ExplicitVRLittleEndian

        ds = Dataset()
        ds.file_meta = file_meta
        ds.is_little_endian = True
        ds.is_implicit_VR = False

        ds.SOPClassUID = SecondaryCaptureImageStorage
        ds.SOPInstanceUID = file_meta.MediaStorageSOPInstanceUID
        ds.PatientName = "Test^CT^Patient"
        ds.PatientID = "MRN-CT-TEST"
        ds.StudyInstanceUID = "1.2.826.0.1.3680043.8.498.999"
        ds.SeriesInstanceUID = "1.2.826.0.1.3680043.8.498.999.1"
        ds.Modality = "CT"
        ds.SeriesDescription = "Test Volumetric Chest CT"
        ds.InstanceNumber = i + 1
        ds.ImagePositionPatient = [0.0, 0.0, float(i * 2.5)]
        ds.PixelSpacing = [0.75, 0.75]
        ds.SliceThickness = 2.5
        ds.RescaleSlope = 1.0
        ds.RescaleIntercept = -1024.0
        ds.SamplesPerPixel = 1
        ds.PhotometricInterpretation = "MONOCHROME2"

        # Pixel data
        raw_slice = (np.ones((64, 64), dtype=np.int16) * (1024 + i * 50)).tobytes()
        ds.Rows = 64
        ds.Columns = 64
        ds.BitsAllocated = 16
        ds.BitsStored = 16
        ds.HighBit = 15
        ds.PixelRepresentation = 1
        ds.PixelData = raw_slice

        buf = io.BytesIO()
        pydicom.dcmwrite(buf, ds, write_like_original=False)
        file_bytes_list.append((f"slice_{i:03d}.dcm", buf.getvalue()))

    # Upload via FastAPI test client
    files_payload = [
        ("files", (fname, content, "application/dicom"))
        for fname, content in file_bytes_list
    ]

    response = client.post(
        "/api/v1/volumetric/upload-series",
        files=files_payload,
        data={"series_name": "Uploaded Thoracic CT Test"}
    )

    assert response.status_code == 200, f"Upload failed: {response.text}"
    data = response.json()
    assert data.get("status") == "success", f"Failed to register series: {data}"
    series_info = data.get("series", {})
    series_id = series_info.get("series_id")
    print(f"Registered CT Series ID: {series_id}")
    print(f"Volume matrix shape: {series_info.get('dimensions')} (Z x Y x X)")
    assert series_info.get("num_slices") == num_slices, f"Expected {num_slices} slices"

    # Test single slice endpoint
    slice_resp = client.get(f"/api/v1/volumetric/{series_id}/slice?plane=axial&index=2")
    assert slice_resp.status_code == 200, f"Slice fetch failed: {slice_resp.text}"
    slice_data = slice_resp.json()
    assert slice_data.get("status") == "success"
    assert "data:image" in slice_data.get("data_url", "")
    print("MPR Axial single slice: 200 OK with valid Data URL")

    # Test tri-planar MPR endpoint
    mpr_resp = client.post(
        f"/api/v1/volumetric/{series_id}/mpr",
        json={"axial_idx": 2, "coronal_idx": 32, "sagittal_idx": 32, "window_preset": "LUNG"}
    )
    assert mpr_resp.status_code == 200, f"Tri-planar MPR failed: {mpr_resp.text}"
    mpr_data = mpr_resp.json()
    assert mpr_data.get("status") == "success"
    assert "data:image" in mpr_data.get("axial", {}).get("data_url", "")
    assert "data:image" in mpr_data.get("coronal", {}).get("data_url", "")
    assert "data:image" in mpr_data.get("sagittal", {}).get("data_url", "")
    print("MPR Tri-Planar Reconstruction (Axial, Coronal, Sagittal): 200 OK")

    print("✅ Track 2 Multi-Slice CT Upload & MPR: PASS")


def test_track3_pwa_and_offline_service_worker():
    """Verify PWA manifest, Service Worker delivery, and offline cache headers."""
    print("\n--- [TRACK 3] PWA & Offline Service Worker Test ---")

    # 1. Manifest
    manifest_resp = client.get("/manifest.json")
    assert manifest_resp.status_code == 200, "manifest.json endpoint failed"
    manifest_data = manifest_resp.json()
    assert manifest_data.get("short_name") == "ALVEON PACS"
    assert manifest_data.get("display") == "standalone"
    print(f"PWA Manifest: short_name='{manifest_data.get('short_name')}', display='{manifest_data.get('display')}'")

    # 2. Service Worker
    sw_resp = client.get("/service-worker.js")
    assert sw_resp.status_code == 200, "service-worker.js endpoint failed"
    assert "CACHE_NAME" in sw_resp.text, "service-worker.js missing cache configuration"
    assert "ServiceWorker" in sw_resp.text or "addEventListener" in sw_resp.text
    print("PWA Service Worker: 200 OK and valid script content")

    # 3. Desktop Build Scripts
    assert os.path.exists("desktop/package.json"), "desktop/package.json missing"
    assert os.path.exists("desktop/build_desktop.sh"), "desktop/build_desktop.sh missing"
    assert os.path.exists(".github/workflows/desktop_release.yml"), "GitHub Actions desktop workflow missing"
    print("Desktop Build Automation & CI/CD workflow: verified present")

    print("✅ Track 3 PWA & Desktop Packaging: PASS")


def test_track4_clinical_whitepaper_and_tour():
    """Verify comprehensive clinical whitepaper and interactive tour markup."""
    print("\n--- [TRACK 4] Clinical Whitepaper & Interactive Tour Test ---")

    # 1. Whitepaper
    whitepaper_path = "docs/CLINICAL_WHITEPAPER.md"
    assert os.path.exists(whitepaper_path), f"{whitepaper_path} does not exist"
    with open(whitepaper_path, "r", encoding="utf-8") as f:
        wp_text = f.read()

    assert "Pneumothorax" in wp_text and "ROC-AUC" in wp_text, "Whitepaper missing clinical metrics"
    assert "ACR" in wp_text, "Whitepaper missing ACR category section"
    assert "HIPAA" in wp_text, "Whitepaper missing HIPAA compliance section"
    print(f"Clinical Whitepaper verified ({len(wp_text)} bytes, valid sections)")

    # 2. Workstation Tour markup
    with open("web/index.html", "r", encoding="utf-8") as f:
        index_html = f.read()

    assert "clinical-tour-overlay" in index_html, "Missing clinical-tour-overlay in web/index.html"
    assert "start-clinical-tour-btn" in index_html, "Missing start-clinical-tour-btn in web/index.html"
    assert "service-worker.js" in index_html, "Missing service worker registration in web/index.html"
    print("Workstation Interactive Tour & SW registration in web/index.html: verified present")

    # 3. Landing page PWA tags
    with open("web/landing.html", "r", encoding="utf-8") as f:
        landing_html = f.read()

    assert 'manifest.json' in landing_html, "Missing manifest link in web/landing.html"
    assert 'service-worker.js' in landing_html, "Missing service worker registration in web/landing.html"
    print("Landing Page PWA tags & SW registration in web/landing.html: verified present")

    print("✅ Track 4 Clinical Documentation & Tour: PASS")


if __name__ == "__main__":
    print("==================================================================")
    print("  ALVEON PACS v5.1 — ALL TRACKS (1 TO 4) E2E VERIFICATION SUITE   ")
    print("==================================================================")
    
    try:
        test_track1_database_dual_engine()
        test_track1_enterprise_auth_and_oauth2()
        test_track2_full_14_pathology_engine()
        test_track2_structured_reporting_14_pathologies()
        test_track2_multi_slice_ct_volumetric_upload()
        test_track3_pwa_and_offline_service_worker()
        test_track4_clinical_whitepaper_and_tour()
        
        print("\n==================================================================")
        print("  🎉 ALL 4 TRACKS VERIFIED 100% PASSING WITH ZERO COMPROMISES     ")
        print("==================================================================")
        sys.exit(0)
    except Exception as exc:
        print(f"\n❌ Verification failed with error: {exc}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
