"""
ALVEON Production Backend Stress Testing Suite
==============================================
Stress tests:
1. High-concurrency HTTP load (50 parallel requests across endpoints)
2. High-concurrency SQLite WAL database persistence (simultaneous reports & signatures)
3. DIMSE DICOM socket stress (rapid concurrent C-ECHO & C-STORE over port 11112)
4. Latency profiling (P50, P95, P99)
"""

import sys
import time
import sqlite3
import concurrent.futures
from pathlib import Path
import requests
import pydicom
from pynetdicom import AE
from pynetdicom.sop_class import Verification

ROOT_DIR = Path(__file__).resolve().parent.parent
BASE_URL = "http://127.0.0.1:8000"
DB_PATH = ROOT_DIR / "data" / "alveon.db"
SAMPLE_PNEUMONIA_DCM = ROOT_DIR / "core" / "assets" / "samples" / "sample_stat_pneumonia.dcm"

def log_header(msg):
    print(f"\n{'='*75}\n⚡ {msg}\n{'='*75}")

def stress_test_concurrent_http():
    log_header("TEST 1: High-Concurrency Multi-Endpoint HTTP Load (50 Requests)")
    
    endpoints = [
        ("GET", f"{BASE_URL}/health"),
        ("GET", f"{BASE_URL}/healthz"),
        ("GET", f"{BASE_URL}/readyz"),
        ("GET", f"{BASE_URL}/api/v1/worklist"),
        ("GET", f"{BASE_URL}/api/v1/reports"),
        ("GET", f"{BASE_URL}/dicomweb/studies"),
    ]
    
    # Expand to 60 requests (10 of each)
    request_tasks = endpoints * 10
    latencies = []
    status_codes = []

    start_time = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
        futures = []
        for method, url in request_tasks:
            def do_req(u=url, m=method):
                t0 = time.time()
                r = requests.get(u, timeout=5.0)
                elapsed = (time.time() - t0) * 1000
                return r.status_code, elapsed
            futures.append(executor.submit(do_req))

        for f in concurrent.futures.as_completed(futures):
            code, lat = f.result()
            status_codes.append(code)
            latencies.append(lat)

    total_time = time.time() - start_time
    latencies.sort()
    p50 = latencies[len(latencies) // 2]
    p95 = latencies[int(len(latencies) * 0.95)]
    p99 = latencies[int(len(latencies) * 0.99)]
    success_count = sum(1 for c in status_codes if c == 200)

    print(f"  Total Requests: {len(status_codes)}")
    print(f"  Success (HTTP 200): {success_count}/{len(status_codes)} ({success_count/len(status_codes)*100:.1f}%)")
    print(f"  Total Batch Time: {total_time:.2f}s (Throughput: {len(status_codes)/total_time:.1f} req/sec)")
    print(f"  Latencies: Min={latencies[0]:.1f}ms | P50={p50:.1f}ms | P95={p95:.1f}ms | P99={p99:.1f}ms | Max={latencies[-1]:.1f}ms")

    assert success_count == len(status_codes), "All concurrent requests must return HTTP 200"
    assert p95 < 200.0, f"P95 latency should be sub-200ms (got {p95:.1f}ms)"
    print("  ✅ HTTP Concurrent Load Test PASSED with zero dropped requests!")

def stress_test_concurrent_sqlite_wal():
    log_header("TEST 2: Concurrent SQLite WAL Write & Signature Hashing Stress (20 Writers)")

    # Authenticate as Dr. Vance
    login_res = requests.post(f"{BASE_URL}/api/v1/auth/login", json={"username": "dr.vance", "password": "Alveon2026!"}).json()
    token = login_res["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    def save_worker(worker_id):
        study_id = f"STRESS-STU-{worker_id}-{int(time.time()*1000)}"
        body = {
            "study_uid": study_id,
            "patient_mrn": f"MRN-STRESS-{worker_id:03d}",
            "patient_name": f"Stress Patient {worker_id}",
            "impression": f"High concurrency stress test attestation by worker {worker_id}.",
            "caliper_measurements": [
                {"label": f"Lesion-{worker_id}", "lengthMm": 20.0 + worker_id, "startX": 100, "startY": 100, "endX": 200, "endY": 200}
            ],
            "status": "FINAL_SIGNED"
        }
        t0 = time.time()
        res = requests.post(f"{BASE_URL}/api/v1/reports/save", json=body, headers=headers, timeout=5.0)
        return res.status_code, (time.time() - t0) * 1000, study_id

    workers = list(range(20))
    results = []
    start_time = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(save_worker, w) for w in workers]
        for f in concurrent.futures.as_completed(futures):
            results.append(f.result())

    total_time = time.time() - start_time
    codes = [r[0] for r in results]
    success = sum(1 for c in codes if c == 200)
    avg_lat = sum(r[1] for r in results) / len(results)

    print(f"  Concurrent Database Writers: {len(workers)}")
    print(f"  Successful Writes: {success}/{len(workers)} (100% committed)")
    print(f"  Total Duration: {total_time:.2f}s | Average Write Latency: {avg_lat:.1f}ms")

    assert success == len(workers), "All concurrent SQLite writes must succeed without database locks"

    # Verify report records in SQLite directly
    conn = sqlite3.connect(str(DB_PATH))
    count = conn.execute("SELECT count(*) FROM radiology_reports WHERE study_uid LIKE 'STRESS-STU-%';").fetchone()[0]
    conn.close()
    print(f"  Direct SQLite Verification: {count} stress reports committed cleanly to disk")
    assert count >= len(workers), f"Expected at least {len(workers)} reports in SQLite, found {count}"
    print("  ✅ Concurrent SQLite WAL Write Test PASSED!")

def stress_test_dimse_socket():
    log_header("TEST 3: DIMSE DICOM Socket Stress (Port 11112 Rapid Pings & Transfers)")

    # 1. 10 rapid sequential C-ECHO pings
    echo_statuses = []
    ae = AE(ae_title="STRESS_PING")
    ae.add_requested_context(Verification)
    
    t0 = time.time()
    for i in range(10):
        assoc = ae.associate("127.0.0.1", 11112, ae_title="ALVEON_PACS")
        if assoc.is_established:
            status = assoc.send_c_echo()
            echo_statuses.append(status.Status if status else -1)
            assoc.release()
        else:
            echo_statuses.append(-1)
    echo_time = time.time() - t0
    
    passed_echos = sum(1 for s in echo_statuses if s == 0)
    print(f"  C-ECHO Pings: {passed_echos}/10 Successful in {echo_time:.2f}s (Avg: {echo_time/10*1000:.1f}ms/ping)")
    assert passed_echos == 10, "All 10 C-ECHO pings must return status 0x0000"

    # 2. C-STORE of real study
    ds = pydicom.dcmread(str(SAMPLE_PNEUMONIA_DCM))
    store_ae = AE(ae_title="STRESS_MOD")
    store_ae.add_requested_context(ds.SOPClassUID)
    assoc_s = store_ae.associate("127.0.0.1", 11112, ae_title="ALVEON_PACS")
    assert assoc_s.is_established, "Association for C-STORE must be established"
    res = assoc_s.send_c_store(ds)
    assoc_s.release()
    assert res and res.Status == 0, "C-STORE must return status 0x0000"
    print("  C-STORE Transfer: Study received and stored in queue with Status 0x0000")
    print("  ✅ DIMSE Socket Stress Test PASSED!")

def main():
    print("="*75)
    print("🚀 ALVEON PACS - HIGH-CONCURRENCY BACKEND STRESS TEST SUITE")
    print("="*75)
    try:
        stress_test_concurrent_http()
        stress_test_concurrent_sqlite_wal()
        stress_test_dimse_socket()
        print("\n" + "="*75)
        print("🏆 ALL BACKEND STRESS TESTS PASSED WITH 100% PRODUCTION INTEGRITY!")
        print("="*75 + "\n")
        return 0
    except Exception as e:
        print(f"\n❌ Stress test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
