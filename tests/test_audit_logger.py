"""
Tests for ALVEON HIPAA Security Rule § 164.312(b) Audit Controls & Chained Hash Integrity
"""

import pytest
import tempfile
import json
from pathlib import Path
from fastapi.testclient import TestClient
from api.app import app
from core.audit_logger import AuditLogger, GENESIS_HASH

client = TestClient(app)


def test_audit_logger_chained_hashing():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_log = Path(tmpdir) / "test_audit.jsonl"
        logger = AuditLogger(log_path=tmp_log)

        # 1. Log first event (linked to GENESIS)
        ev1 = logger.log(
            action="LOGIN",
            user_id="USR-TEST-01",
            username="dr.test",
            user_role="ATTENDING_RADIOLOGIST"
        )
        assert ev1.prev_hash == GENESIS_HASH
        assert len(ev1.record_hash) == 64

        # 2. Log second event (linked to ev1.record_hash)
        ev2 = logger.log(
            action="PHI_VIEW",
            user_id="USR-TEST-01",
            username="dr.test",
            user_role="ATTENDING_RADIOLOGIST",
            patient_mrn="MRN-TEST-100"
        )
        assert ev2.prev_hash == ev1.record_hash

        # 3. Verify integrity
        verify = logger.verify_integrity()
        assert verify["is_valid"] is True
        assert verify["total_events"] == 2


def test_audit_logger_tamper_detection():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_log = Path(tmpdir) / "tamper_audit.jsonl"
        logger = AuditLogger(log_path=tmp_log)

        logger.log(action="LOGIN", user_id="U1", username="dr.one", user_role="ATTENDING_RADIOLOGIST")
        logger.log(action="PHI_VIEW", user_id="U1", username="dr.one", user_role="ATTENDING_RADIOLOGIST", patient_mrn="MRN-ORIGINAL")
        logger.log(action="PDF_EXPORTED", user_id="U1", username="dr.one", user_role="ATTENDING_RADIOLOGIST")

        # Confirm valid before tampering
        assert logger.verify_integrity()["is_valid"] is True

        # Maliciously tamper with the file content
        with open(tmp_log, "r") as f:
            lines = f.readlines()
        
        tampered = json.loads(lines[1])
        tampered["patient_mrn"] = "MRN-TAMPERED-BY-ATTACKER"
        lines[1] = json.dumps(tampered) + "\n"

        with open(tmp_log, "w") as f:
            f.writelines(lines)

        # Integrity check MUST fail!
        verify_tampered = logger.verify_integrity()
        assert verify_tampered["is_valid"] is False
        assert "Data integrity violation" in verify_tampered["error"] or "Hash chain broken" in verify_tampered["error"]


def test_api_audit_endpoints():
    # 1. Query audit trail endpoint
    res_logs = client.get("/api/v1/audit/logs?limit=10")
    assert res_logs.status_code == 200
    data = res_logs.json()
    assert data["status"] == "success"
    assert "events" in data

    # 2. Verify audit integrity endpoint
    res_verify = client.get("/api/v1/audit/verify")
    assert res_verify.status_code == 200
    vdata = res_verify.json()
    assert vdata["is_valid"] is True
