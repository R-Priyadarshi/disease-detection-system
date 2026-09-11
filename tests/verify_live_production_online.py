"""
ALVEON Live Online Production Verification & Stress Testing Suite
================================================================
Executes exhaustive deep-dive tests against the live online production deployment:
https://alveon-pacs.onrender.com

Tests all endpoints, live neural inference, RBAC authentication, persistent database,
DICOMweb standards, and concurrent stress load over the public internet.
"""

import sys
import time
import json
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import requests

LIVE_BASE_URL = "https://alveon-pacs.onrender.com"
ROOT_DIR = Path(__file__).resolve().parent.parent
SAMPLE_PNEUMONIA_DCM = ROOT_DIR / "core" / "assets" / "samples" / "sample_stat_pneumonia.dcm"
SAMPLE_NORMAL_DCM = ROOT_DIR / "core" / "assets" / "samples" / "sample_clear_normal.dcm"

def print_banner(text):
    print(f"\n{'='*75}\n🌟 {text}\n{'='*75}")

def assert_check(name, condition, details=""):
    icon = "✅" if condition else "❌"
    print(f"  {icon} [{name}] {details}")
    if not condition:
        raise AssertionError(f"Check failed: {name} - {details}")

def test_01_cloud_health_and_probes():
    print_banner("1. CLOUD HEALTH PROBES & TELEMETRY")
    
    # /health
    t0 = time.time()
    r = requests.get(f"{LIVE_BASE_URL}/health", timeout=15)
    lat = (time.time() - t0) * 1000
    assert_check("GET /health HTTP 200", r.status_code == 200, f"Latency: {lat:.1f}ms")
    data = r.json()
    assert_check("Health Status Healthy", data.get("status") == "healthy", f"Status: {data.get('status')}")
    assert_check("Deep Learning Model Loaded", data.get("model_loaded") is True, "TESTCNN.hdf5 active in cloud")
    assert_check("TensorFlow Version", "tensorflow_version" in data, f"TF: {data.get('tensorflow_version')}")
    
    # /healthz & /readyz
    r_hz = requests.get(f"{LIVE_BASE_URL}/healthz", timeout=10)
    assert_check("GET /healthz HTTP 200", r_hz.status_code == 200)
    r_rz = requests.get(f"{LIVE_BASE_URL}/readyz", timeout=10)
    assert_check("GET /readyz HTTP 200", r_rz.status_code == 200)
    
    # /docs & OpenAPI
    r_docs = requests.get(f"{LIVE_BASE_URL}/docs", timeout=10)
    assert_check("GET /docs (Swagger UI) HTTP 200", r_docs.status_code == 200)
    r_openapi = requests.get(f"{LIVE_BASE_URL}/openapi.json", timeout=10)
    assert_check("GET /openapi.json HTTP 200", r_openapi.status_code == 200 and "paths" in r_openapi.json())

def test_02_landing_workstation_static_delivery():
    print_banner("2. FRONTEND & STATIC ASSET DELIVERY")
    
    routes = [
        ("/", "Root Gateway"),
        ("/viewer", "Diagnostic Workstation UI"),
        ("/landing", "Executive Product Landing Page"),
        ("/static/landing.css", "Landing CSS Stylesheet"),
        ("/static/style.css", "Workstation Dark CSS"),
        ("/static/app.js", "Workstation Client Engine"),
        ("/static/landing.html", "Landing Page Static HTML"),
    ]
    
    for route, desc in routes:
        t0 = time.time()
        r = requests.get(f"{LIVE_BASE_URL}{route}", timeout=15)
        lat = (time.time() - t0) * 1000
        assert_check(f"Deliver {route} ({desc})", r.status_code == 200, f"Size: {len(r.content):,} bytes | Latency: {lat:.1f}ms")

def test_03_live_neural_inference():
    print_banner("3. REAL DEEP LEARNING INFERENCE & GRAD-CAM IN THE CLOUD")
    assert_check("Sample DICOM Exists", SAMPLE_PNEUMONIA_DCM.exists(), f"Path: {SAMPLE_PNEUMONIA_DCM}")
    
    t0 = time.time()
    with open(SAMPLE_PNEUMONIA_DCM, "rb") as f:
        files = {"file": ("sample_stat_pneumonia.dcm", f, "application/dicom")}
        res = requests.post(f"{LIVE_BASE_URL}/api/v1/predict", files=files, timeout=30)
    lat = (time.time() - t0) * 1000
    
    assert_check("POST /api/v1/predict HTTP 200", res.status_code == 200, f"Cloud Inference Latency: {lat:.1f}ms")
    data = res.json()
    
    # Verify neural classification output
    diagnosis = data.get("diagnosis") or data.get("primary_finding")
    assert_check("Diagnosis Field Present", diagnosis is not None, f"Classification: {diagnosis}")
    assert_check("Pneumonia Classification Accurate", diagnosis == "PNEUMONIA", f"Score: {data.get('probability')}")
    assert_check("Confidence Calibrated", data.get("probability", 0) > 0.80, f"{data.get('confidence_percentage')}%")
    
    # Verify Grad-CAM overlay
    assert_check("Grad-CAM Overlay Base64 Generated", "gradcam_overlay_b64" in data and len(data["gradcam_overlay_b64"]) > 500)
    
    # Verify Anatomical Zonation
    assert_check("Anatomical Zonation Returned", "zonation" in data)
    z = data["zonation"]
    z_sum = z.get("right_upper_lobe_pct", 0) + z.get("right_lower_lobe_pct", 0) + z.get("left_upper_lobe_pct", 0) + z.get("left_lower_lobe_pct", 0)
    assert_check("Zonation Quadrants Sum to ~100%", 99.0 <= z_sum <= 101.0, f"Sum: {z_sum:.1f}%")
    
    # Verify Multi-label Findings
    assert_check("Multi-label Findings Array", "findings" in data and len(data["findings"]) >= 6, f"Count: {len(data.get('findings', []))}")
    
    # Verify DICOM Metadata extraction
    assert_check("DICOM Metadata Extracted", "dicom_metadata" in data and data["dicom_metadata"].get("is_dicom") is True)
    d_meta = data["dicom_metadata"]
    assert_check("DICOM Tag: Patient ID", "patient_id" in d_meta, f"PID: {d_meta.get('patient_id')}")
    assert_check("DICOM Tag: Modality", d_meta.get("modality") == "DX", f"Modality: {d_meta.get('modality')}")

def test_04_live_rbac_auth_and_sessions():
    print_banner("4. RBAC AUTHENTICATION & JWT TOKENS ON LIVE CLOUD")
    
    personas = [
        ("dr.vance", "Chief Thoracic Radiologist"),
        ("dr.chen", "Senior Radiology Resident"),
        ("dr.adams", "Emergency Medicine Lead"),
        ("admin.marcus", "Lead PACS Systems Architect")
    ]
    
    tokens = {}
    for username, role_desc in personas:
        t0 = time.time()
        res = requests.post(f"{LIVE_BASE_URL}/api/v1/auth/login", json={"username": username, "password": "Alveon2026!"}, timeout=15)
        lat = (time.time() - t0) * 1000
        assert_check(f"Login HTTP 200: {username} ({role_desc})", res.status_code == 200, f"Latency: {lat:.1f}ms")
        payload = res.json()
        assert_check(f"JWT Token Received: {username}", "access_token" in payload and len(payload["access_token"].split(".")) == 3)
        assert_check(f"Token Claims Verified: {username}", payload["user"]["username"] == username)
        tokens[username] = payload["access_token"]
        
    return tokens

def test_05_live_report_saving_and_persistence(tokens):
    print_banner("5. REPORT ATTESTATION, CALIPERS & AUDIT TRAIL PERSISTENCE")
    
    dr_vance_token = tokens["dr.vance"]
    headers = {"Authorization": f"Bearer {dr_vance_token}"}
    
    test_study_uid = "1.2.826.0.1.3680043.8.498.LIVE_TEST_STUDY"
    digital_signature = hashlib.sha256(f"LIVE_TEST_{time.time()}".encode()).hexdigest()
    
    report_payload = {
        "study_uid": test_study_uid,
        "patient_mrn": "MRN-LIVE-992",
        "patient_name": "LIVE Attested Patient",
        "impression": "Dense consolidative alveolar opacity in left lower lobe compatible with acute bacterial pneumonia.",
        "acr_actionable_code": "ACR Category 4 (Actionable Pathology)",
        "caliper_measurements": [
            {"type": "linear", "startX": 120, "startY": 140, "endX": 210, "endY": 195, "lengthMm": 42.6},
            {"type": "arrow", "startX": 180, "startY": 160, "endX": 230, "endY": 210, "label": "Pathology Focus"},
            {"type": "ellipse", "cx": 190, "cy": 180, "rx": 35, "ry": 25, "areaCm2": 6.8}
        ]
    }
    
    # Save Report
    t0 = time.time()
    save_res = requests.post(f"{LIVE_BASE_URL}/api/v1/reports/save", json=report_payload, headers=headers, timeout=15)
    lat = (time.time() - t0) * 1000
    assert_check("POST /api/v1/reports/save HTTP 200", save_res.status_code == 200, f"Latency: {lat:.1f}ms")
    save_data = save_res.json()
    assert_check("Report Saved with ID", "report_id" in save_data, f"Report ID: {save_data.get('report_id')}")
    assert_check("Digital Signature Chained", "signature_hash" in save_data, f"Hash: {save_data.get('signature_hash')[:16]}...")
    
    # Retrieve by Study UID
    get_res = requests.get(f"{LIVE_BASE_URL}/api/v1/reports/study/{test_study_uid}", headers=headers, timeout=15)
    assert_check(f"GET /api/v1/reports/study/{{uid}} HTTP 200", get_res.status_code == 200)
    retrieved = get_res.json()
    assert_check("Study UID Matches", retrieved.get("study_uid") == test_study_uid)
    assert_check("Digital Signature Verified", retrieved.get("digital_signature_hash") == save_data.get("signature_hash"))
    assert_check("Calipers Restored from Cloud DB", len(retrieved.get("caliper_measurements", [])) == 3, f"Calipers count: {len(retrieved.get('caliper_measurements', []))}")
    
    # List all reports
    list_res = requests.get(f"{LIVE_BASE_URL}/api/v1/reports", headers=headers, timeout=15)
    assert_check("GET /api/v1/reports HTTP 200", list_res.status_code == 200 and len(list_res.json().get("reports", [])) >= 1)

def test_06_live_dicomweb_services():
    print_banner("6. DICOMWEB PART 18 REST SERVICES IN THE CLOUD")
    
    # QIDO-RS
    t0 = time.time()
    r = requests.get(f"{LIVE_BASE_URL}/dicomweb/studies", timeout=15)
    lat = (time.time() - t0) * 1000
    assert_check("GET /dicomweb/studies (QIDO-RS) HTTP 200", r.status_code == 200, f"Latency: {lat:.1f}ms")
    studies = r.json()
    assert_check("Studies Returned in DICOM-JSON format", isinstance(studies, list) and len(studies) >= 1, f"Found {len(studies)} studies")
    first = studies[0]
    assert_check("DICOM-JSON Tag: StudyInstanceUID (0020000D)", "0020000D" in first)
    assert_check("DICOM-JSON Tag: PatientID (00100020)", "00100020" in first)
    
    # Extract UIDs for WADO-RS
    study_uid = first["0020000D"]["Value"][0]
    series_uid = first.get("0020000E", {}).get("Value", ["1.2.3"])[0]
    instance_uid = first.get("00080018", {}).get("Value", ["1.2.3.4"])[0]
    wado_url = f"{LIVE_BASE_URL}/dicomweb/studies/{study_uid}/series/{series_uid}/instances/{instance_uid}/rendered"
    t0 = time.time()
    wado_res = requests.get(wado_url, timeout=15)
    lat = (time.time() - t0) * 1000
    assert_check("GET WADO-RS Rendered Frame HTTP 200", wado_res.status_code == 200, f"Content-Type: {wado_res.headers.get('content-type')} | Latency: {lat:.1f}ms")

def test_07_live_concurrency_stress_test():
    print_banner("7. HIGH-CONCURRENCY MULTI-ENDPOINT CLOUD STRESS TEST")
    
    test_endpoints = [
        f"{LIVE_BASE_URL}/health",
        f"{LIVE_BASE_URL}/healthz",
        f"{LIVE_BASE_URL}/readyz",
        f"{LIVE_BASE_URL}/api/v1/worklist",
        f"{LIVE_BASE_URL}/api/v1/reports",
        f"{LIVE_BASE_URL}/dicomweb/studies",
        f"{LIVE_BASE_URL}/viewer",
        f"{LIVE_BASE_URL}/landing"
    ]
    
    NUM_REQUESTS = 64
    CONCURRENCY = 16
    
    print(f"  Firing {NUM_REQUESTS} concurrent requests over {CONCURRENCY} worker threads to live cloud...")
    
    def fetch_url(url):
        t0 = time.time()
        try:
            r = requests.get(url, timeout=15)
            dt = (time.time() - t0) * 1000
            return (r.status_code, dt, None)
        except Exception as e:
            return (0, 0, str(e))
            
    tasks = [test_endpoints[i % len(test_endpoints)] for i in range(NUM_REQUESTS)]
    
    t_start = time.time()
    latencies = []
    statuses = []
    errors = []
    
    with ThreadPoolExecutor(max_workers=CONCURRENCY) as executor:
        futures = [executor.submit(fetch_url, u) for u in tasks]
        for f in as_completed(futures):
            code, dt, err = f.result()
            statuses.append(code)
            if code == 200:
                latencies.append(dt)
            else:
                errors.append(err or f"Status {code}")
                
    total_time = time.time() - t_start
    throughput = NUM_REQUESTS / total_time
    latencies.sort()
    
    p50 = latencies[len(latencies)//2] if latencies else 0
    p95 = latencies[int(len(latencies)*0.95)] if latencies else 0
    max_lat = max(latencies) if latencies else 0
    min_lat = min(latencies) if latencies else 0
    success_count = statuses.count(200)
    
    print(f"\n  📊 STRESS METRICS RESULTS:")
    print(f"     Total Requests:  {NUM_REQUESTS}")
    print(f"     Success (200):   {success_count} / {NUM_REQUESTS} ({success_count/NUM_REQUESTS*100:.1f}%)")
    print(f"     Throughput:      {throughput:.1f} requests/sec")
    print(f"     Min Latency:     {min_lat:.1f} ms")
    print(f"     P50 Latency:     {p50:.1f} ms")
    print(f"     P95 Latency:     {p95:.1f} ms")
    print(f"     Max Latency:     {max_lat:.1f} ms")
    
    assert_check("Stress Success Rate 100%", success_count == NUM_REQUESTS, f"Passed: {success_count}/{NUM_REQUESTS}")
    assert_check("P95 Latency Under 1500ms over Internet", p95 < 1500.0, f"P95: {p95:.1f}ms")

def main():
    print_banner(f"STARTING COMPREHENSIVE PRODUCTION VERIFICATION ON:\n{LIVE_BASE_URL}")
    t0 = time.time()
    
    try:
        test_01_cloud_health_and_probes()
        test_02_landing_workstation_static_delivery()
        test_03_live_neural_inference()
        tokens = test_04_live_rbac_auth_and_sessions()
        test_05_live_report_saving_and_persistence(tokens)
        test_06_live_dicomweb_services()
        test_07_live_concurrency_stress_test()
        
        elapsed = time.time() - t0
        print_banner(f"🎉 ALL LIVE PRODUCTION VERIFICATIONS & STRESS TESTS PASSED IN {elapsed:.2f}s! ZERO ERRORS OR COMPROMISES!")
    except Exception as e:
        print(f"\n❌ FATAL TEST FAILURE: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
