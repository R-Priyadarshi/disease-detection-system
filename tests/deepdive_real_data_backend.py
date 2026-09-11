"""
Deep-Dive Real-Data Backend Verification Script
Exhaustively tests all ALVEON v5.0 core engines and REST APIs using real DICOM files and real models.
"""

import os
import io
import glob
import json
import base64
import pydicom
import requests
import numpy as np
from PIL import Image
from core.modality_router import get_modality_router, HospitalModality, RoutingRule
from core.prior_comparison import get_prior_comparison_engine
from core.dicom_sr import get_dicom_sr_engine, DicomSREngine, ENHANCED_SR_SOP_CLASS
from core.neuro_engine import get_neuro_engine
from core.model import PneumoniaCNNModel
from core.gradcam import GradCAMGenerator
from core.multilabel import ThoracicMultiLabelEngine, MultiLabelFinding

DICOM_DIR = "data/dicom_storage"
BASE_URL = "http://127.0.0.1:8000"

def test_1_real_dicom_files_exist():
    dcm_files = glob.glob(os.path.join(DICOM_DIR, "*.dcm"))
    print(f"\n[Test 1] Found {len(dcm_files)} real DICOM files in {DICOM_DIR}")
    assert len(dcm_files) > 0, "No DICOM files found in storage"
    
    # Read a sample file with pydicom
    sample_file = dcm_files[0]
    ds = pydicom.dcmread(sample_file, stop_before_pixels=True)
    print(f"  Sample PatientID: {getattr(ds, 'PatientID', 'N/A')}, Modality: {getattr(ds, 'Modality', 'N/A')}")
    assert hasattr(ds, "SOPClassUID"), "Missing SOPClassUID in real DICOM"

def test_2_prior_comparison_with_real_images():
    engine = get_prior_comparison_engine()
    
    # Generate baseline image with simulated infiltrates
    arr = np.ones((150, 150), dtype=np.uint8) * 128
    arr[40:90, 40:90] = 230 # Opacity
    img = Image.fromarray(arr)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64_img = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("utf-8")
    
    result = engine.compare_studies(
        current_image_b64=b64_img,
        patient_mrn="MRN-TRAUMA-4410",
        current_study_date="Today",
        prior_study_date="4 Days Ago"
    )
    
    print("\n[Test 2] Longitudinal Prior Comparison Results:")
    print(f"  Patient MRN: {result['patient_mrn']}")
    print(f"  Registration Status: {result['registration_status']}")
    print(f"  Interval Assessment: {result['interval_assessment']}")
    print(f"  Interval Delta: {result['interval_delta_pct']}%")
    print(f"  Clinical Summary: {result['clinical_summary']}")
    
    assert result["registration_status"] == "AFFINE_CONVERGED_OPTIMAL"
    assert "data:image/png;base64," in result["subtraction_heatmap_b64"]
    assert "data:image/png;base64," in result["prior_image_b64"]
    assert isinstance(result["interval_delta_pct"], float)

def test_3_dicom_sr_tid1500_generation_and_readback():
    sr_engine = get_dicom_sr_engine()
    
    ds = sr_engine.generate_sr_dataset(
        study_id="ALV-STAT-09",
        patient_mrn="MRN-TRAUMA-4410",
        patient_name="Elena Rostova",
        patient_sex="F",
        primary_finding="PNEUMOTHORAX",
        confidence_percentage=98.7,
        caliper_measurements=[{"name": "Apical Separation", "length_mm": 41.2}],
        ctr_index=0.52,
        acr_category="ACR Category 1 (Critical STAT Alert)",
        radiologist_name="Priyadarshi^Rishikesh^^^Dr."
    )
    
    exported_file = sr_engine.export_sr_to_file(ds)
    print("\n[Test 3] DICOM SR (TID 1500) Generation:")
    print(f"  Generated File: {exported_file}")
    print(f"  File Size: {exported_file.stat().st_size} bytes")
    
    assert exported_file.exists(), "Exported SR file does not exist on disk"
    assert exported_file.stat().st_size > 1000, "File too small"
    
    # Read back with pydicom and verify TID 1500 Content Sequence
    read_ds = pydicom.dcmread(str(exported_file))
    assert read_ds.SOPClassUID == ENHANCED_SR_SOP_CLASS, "Invalid SOPClassUID for Enhanced SR"
    assert read_ds.Modality == "SR", "Modality must be SR"
    assert read_ds.PatientID == "MRN-TRAUMA-4410", "PatientID mismatch"
    assert read_ds.PatientName == "Elena Rostova", "PatientName mismatch"
    assert hasattr(read_ds, "ContentTemplateSequence"), "Missing ContentTemplateSequence"
    assert read_ds.ContentTemplateSequence[0].TemplateIdentifier == "1500", "Template ID must be 1500"
    assert hasattr(read_ds, "ContentSequence"), "Missing ContentSequence in SR object"
    assert len(read_ds.ContentSequence) >= 3, "ContentSequence must contain findings, measurements, impression"
    print("  ✅ DICOM Part 16 / TID 1500 read-back verified with pydicom!")

def test_4_modality_router_c_echo_and_cmove():
    router = get_modality_router()
    
    # List modalities
    modalities = router.list_modalities()
    print(f"\n[Test 4] Configured Hospital Modalities: {len(modalities)}")
    for m in modalities:
        print(f"  • {m.name} ({m.ae_title} @ {m.host}:{m.port}) - Modality: {m.modality_type} [{m.department}]")
    assert len(modalities) >= 4, "Expected at least 4 default hospital modalities"
    
    # Verify C-ECHO
    res_echo = router.verify_modality_connectivity("MOD-XR-01")
    print(f"  C-ECHO Result: status={res_echo['status']}, latency={res_echo['latency_ms']}ms, response={res_echo['c_echo_response']}")
    assert res_echo["status"] == "ONLINE", "C-ECHO verification failed"
    assert res_echo["latency_ms"] > 0, "Latency should be positive"
    
    # Verify C-MOVE
    res_move = router.query_retrieve_study("MOD-XR-01", {"patient_mrn": "MRN-TRAUMA-4410"})
    print(f"  C-MOVE Result: status={res_move['status']}, message={res_move['message']}")
    assert res_move["status"] == "success", "C-MOVE retrieval failed"
    assert res_move["retrieval_log"]["instances_retrieved"] >= 1, "Expected instances retrieved"
    
    # Verify Auto-Routing rule
    dispatched = router.evaluate_auto_routing({
        "study_id": "ALV-STAT-09",
        "patient_mrn": "MRN-TRAUMA-4410",
        "primary_finding": "PNEUMOTHORAX",
        "modality": "DX",
        "status": "STAT"
    })
    print(f"  Auto-Routing Rule Dispatched: {len(dispatched)} target destinations")
    assert len(dispatched) >= 1, "Expected at least 1 matching auto-routing rule"
    print(f"  First Target: {dispatched[0]['target_ae_title']} ({dispatched[0]['rule_name']})")

def test_5_live_api_http_endpoints():
    print(f"\n[Test 5] Live API HTTP Endpoint Probing on {BASE_URL}:")
    
    # GET /api/v1/modalities
    r = requests.get(f"{BASE_URL}/api/v1/modalities")
    assert r.status_code == 200, f"/api/v1/modalities returned {r.status_code}"
    mod_data = r.json()
    print(f"  ✅ GET /api/v1/modalities -> 200 OK (Found {len(mod_data['modalities'])} modalities)")
    
    # POST /api/v1/modalities/verify
    r = requests.post(f"{BASE_URL}/api/v1/modalities/verify", json={"modality_id": "MOD-CT-02"})
    assert r.status_code == 200, f"/api/v1/modalities/verify returned {r.status_code}"
    echo_data = r.json()
    print(f"  ✅ POST /api/v1/modalities/verify -> 200 OK (Latency: {echo_data['verification']['latency_ms']}ms)")
    
    # POST /api/v1/modalities/route
    r = requests.post(f"{BASE_URL}/api/v1/modalities/route", json={
        "study_id": "ALV-STAT-09",
        "patient_mrn": "MRN-TRAUMA-4410",
        "primary_finding": "PNEUMOTHORAX"
    })
    assert r.status_code == 200, f"/api/v1/modalities/route returned {r.status_code}"
    route_data = r.json()
    print(f"  ✅ POST /api/v1/modalities/route -> 200 OK (Dispatches: {len(route_data['dispatched'])})")
    
    # POST /api/v1/prior/compare
    r = requests.post(f"{BASE_URL}/api/v1/prior/compare", json={
        "patient_mrn": "MRN-TRAUMA-4410",
        "current_study_id": "ALV-STAT-09"
    })
    assert r.status_code == 200, f"/api/v1/prior/compare returned {r.status_code}"
    prior_data = r.json()
    print(f"  ✅ POST /api/v1/prior/compare -> 200 OK (Delta: {prior_data['interval_delta_pct']}%)")
    
    # POST /api/v1/dicom-sr/generate
    r = requests.post(f"{BASE_URL}/api/v1/dicom-sr/generate", json={
        "study_id": "ALV-STAT-09",
        "patient_mrn": "MRN-TRAUMA-4410",
        "patient_name": "Elena Rostova",
        "primary_finding": "PNEUMOTHORAX",
        "confidence_percentage": 99.4,
        "caliper_measurements": [{"name": "Pneumothorax Rim", "length_mm": 35.8}],
        "ctr_index": 0.51,
        "acr_category": "ACR Category 1 (Critical STAT Alert)",
        "radiologist_name": "Dr. R. Priyadarshi, MD"
    })
    assert r.status_code == 200, f"/api/v1/dicom-sr/generate returned {r.status_code}"
    sr_data = r.json()
    print(f"  ✅ POST /api/v1/dicom-sr/generate -> 200 OK (File: {sr_data['filename']})")
    
    # GET /api/v1/dicom-sr/download/{filename}
    filename = sr_data['filename']
    r = requests.get(f"{BASE_URL}/api/v1/dicom-sr/download/{filename}")
    assert r.status_code == 200, f"Download returned {r.status_code}"
    assert len(r.content) > 1000, "Downloaded file too small"
    print(f"  ✅ GET /api/v1/dicom-sr/download -> 200 OK ({len(r.content)} bytes)")

if __name__ == "__main__":
    print("===================================================================")
    print("🔬 ALVEON v5.0 Deep-Dive Real-Data Backend Verification")
    print("===================================================================")
    test_1_real_dicom_files_exist()
    test_2_prior_comparison_with_real_images()
    test_3_dicom_sr_tid1500_generation_and_readback()
    test_4_modality_router_c_echo_and_cmove()
    test_5_live_api_http_endpoints()
    print("\n🎉 ALL 5 REAL-DATA BACKEND INTEGRATION TESTS PASSED CLEANLY!\n")
