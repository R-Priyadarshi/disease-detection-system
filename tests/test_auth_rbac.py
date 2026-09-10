"""
Tests for ALVEON Enterprise Authentication & Role-Based Access Control (RBAC)
Verifies JWT token issuance, verification, role hierarchy, and signoff authorization rules.
"""

import pytest
from fastapi.testclient import TestClient
from api.app import app
from core.auth import (
    CLINICAL_DIRECTORY,
    ClinicalUser,
    UserRole,
    create_access_token,
    decode_access_token
)

client = TestClient(app)


def test_jwt_token_creation_and_decoding():
    user = CLINICAL_DIRECTORY["dr.vance"]
    token = create_access_token(user, expires_in=3600)
    assert token is not None
    assert len(token.split('.')) == 3

    payload = decode_access_token(token)
    assert payload["sub"] == "dr.vance"
    assert payload["role"] == UserRole.ATTENDING_RADIOLOGIST.value
    assert payload["full_name"] == "Dr. Eleanor Vance, MD"


def test_auth_login_endpoint_success():
    res = client.post("/api/v1/auth/login", json={"username": "dr.vance"})
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["username"] == "dr.vance"
    assert data["user"]["role"] == "ATTENDING_RADIOLOGIST"


def test_auth_login_invalid_username():
    res = client.post("/api/v1/auth/login", json={"username": "imposter.hacker"})
    assert res.status_code == 401
    assert "not recognized" in res.json()["detail"]


def test_auth_me_endpoint_with_and_without_token():
    # Without token: falls back gracefully to default attending
    res_default = client.get("/api/v1/auth/me")
    assert res_default.status_code == 200
    assert res_default.json()["username"] == "dr.vance"

    # With Resident token:
    token_chen = create_access_token(CLINICAL_DIRECTORY["dr.chen"])
    res_chen = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token_chen}"})
    assert res_chen.status_code == 200
    assert res_chen.json()["username"] == "dr.chen"
    assert res_chen.json()["role"] == "RESIDENT_FELLOW"


def test_rbac_signoff_permission_enforcement():
    # 1. Attending Radiologist CAN sign off
    token_attending = create_access_token(CLINICAL_DIRECTORY["dr.vance"])
    res_attending = client.post(
        "/api/v1/signoff",
        json={
            "study_id": "ALV-STAT-09",
            "physician_name": "Dr. Eleanor Vance, MD",
            "physician_license": "FACR-99210",
            "clinical_notes": "Attending review and final legal verification."
        },
        headers={"Authorization": f"Bearer {token_attending}"}
    )
    assert res_attending.status_code == 200
    assert res_attending.json()["signoff_badge"] == "VERIFIED & SIGNED"

    # 2. Resident Fellow CANNOT sign off final report (403 Forbidden)
    token_resident = create_access_token(CLINICAL_DIRECTORY["dr.chen"])
    res_resident = client.post(
        "/api/v1/signoff",
        json={
            "study_id": "ALV-STAT-09",
            "physician_name": "Dr. Kevin Chen, MD",
            "physician_license": "PGY4-RESIDENT",
            "clinical_notes": "Preliminary resident read."
        },
        headers={"Authorization": f"Bearer {token_resident}"}
    )
    assert res_resident.status_code == 403
    assert "Attending Radiologist review required" in res_resident.json()["detail"]

    # 3. ER Physician CANNOT sign off final radiology report (403 Forbidden)
    token_er = create_access_token(CLINICAL_DIRECTORY["dr.adams"])
    res_er = client.post(
        "/api/v1/signoff",
        json={
            "study_id": "ALV-STAT-09",
            "physician_name": "Dr. Sarah Adams, MD",
            "physician_license": "ER-MD-12048",
            "clinical_notes": "ER review."
        },
        headers={"Authorization": f"Bearer {token_er}"}
    )
    assert res_er.status_code == 403
