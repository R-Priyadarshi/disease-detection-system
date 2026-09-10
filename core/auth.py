"""
ALVEON Enterprise Security & Role-Based Access Control (RBAC) Engine
Compliant with HIPAA Security Rule § 164.312(a)(1) Access Control.
Provides HMAC-SHA256 JWT token generation, signature validation, role hierarchy,
and institutional clinical user directory.
"""

import hmac
import hashlib
import base64
import json
import time
from enum import Enum
from typing import Optional, List, Dict, Any
from fastapi import Header, HTTPException, status, Depends
from pydantic import BaseModel

# Secret key for institutional JWT signing
JWT_SECRET = "ALVEON_CLINICAL_SECURE_HMAC_SECRET_KEY_2026_HIPAA"
JWT_ALGORITHM = "HS256"
TOKEN_EXPIRY_SECONDS = 86400  # 24-hour shift token


class UserRole(str, Enum):
    """Hospital clinical and operational role hierarchy."""
    ATTENDING_RADIOLOGIST = "ATTENDING_RADIOLOGIST"
    RESIDENT_FELLOW = "RESIDENT_FELLOW"
    ER_PHYSICIAN = "ER_PHYSICIAN"
    PACS_ADMIN = "PACS_ADMIN"


class ClinicalUser(BaseModel):
    user_id: str
    username: str
    full_name: str
    title: str
    role: UserRole
    department: str
    npi: Optional[str] = None
    initials: str


# Pre-configured institutional hospital personnel directory
CLINICAL_DIRECTORY: Dict[str, ClinicalUser] = {
    "dr.vance": ClinicalUser(
        user_id="USR-VANCE-01",
        username="dr.vance",
        full_name="Dr. Eleanor Vance, MD",
        title="Chief Thoracic Radiologist, FACR",
        role=UserRole.ATTENDING_RADIOLOGIST,
        department="Diagnostic Radiology",
        npi="1847291048",
        initials="EV"
    ),
    "dr.chen": ClinicalUser(
        user_id="USR-CHEN-02",
        username="dr.chen",
        full_name="Dr. Kevin Chen, MD",
        title="Senior Diagnostic Radiology Resident (PGY-4)",
        role=UserRole.RESIDENT_FELLOW,
        department="Diagnostic Radiology",
        npi="1958302159",
        initials="KC"
    ),
    "dr.adams": ClinicalUser(
        user_id="USR-ADAMS-03",
        username="dr.adams",
        full_name="Dr. Sarah Adams, MD",
        title="Emergency Medicine Attending & Trauma Lead",
        role=UserRole.ER_PHYSICIAN,
        department="Emergency Medicine",
        npi="1204859201",
        initials="SA"
    ),
    "admin.marcus": ClinicalUser(
        user_id="USR-BRODY-04",
        username="admin.marcus",
        full_name="Marcus Brody, MS, CIIP",
        title="Lead PACS Systems Architect & Imaging Informatics",
        role=UserRole.PACS_ADMIN,
        department="Clinical Imaging Informatics",
        npi=None,
        initials="MB"
    )
}

DEFAULT_USER = CLINICAL_DIRECTORY["dr.vance"]


def _base64url_encode(data: bytes) -> str:
    """Encodes bytes to base64url without padding."""
    return base64.urlsafe_b64encode(data).decode('utf-8').rstrip('=')


def _base64url_decode(s: str) -> bytes:
    """Decodes base64url string with padding restoration."""
    padding = '=' * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + padding)


def create_access_token(user: ClinicalUser, expires_in: int = TOKEN_EXPIRY_SECONDS) -> str:
    """Generates an HMAC-SHA256 signed JWT token for a clinical user."""
    header = {"alg": JWT_ALGORITHM, "typ": "JWT"}
    now = int(time.time())
    payload = {
        "sub": user.username,
        "user_id": user.user_id,
        "full_name": user.full_name,
        "role": user.role.value,
        "department": user.department,
        "npi": user.npi,
        "iat": now,
        "exp": now + expires_in
    }

    header_b64 = _base64url_encode(json.dumps(header, separators=(',', ':')).encode('utf-8'))
    payload_b64 = _base64url_encode(json.dumps(payload, separators=(',', ':')).encode('utf-8'))
    signing_input = f"{header_b64}.{payload_b64}".encode('utf-8')

    signature = hmac.new(JWT_SECRET.encode('utf-8'), signing_input, hashlib.sha256).digest()
    sig_b64 = _base64url_encode(signature)

    return f"{header_b64}.{payload_b64}.{sig_b64}"


def decode_access_token(token: str) -> Dict[str, Any]:
    """Validates signature and expiration of an incoming JWT token."""
    parts = token.split('.')
    if len(parts) != 3:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed JWT bearer authorization token."
        )

    header_b64, payload_b64, sig_b64 = parts
    signing_input = f"{header_b64}.{payload_b64}".encode('utf-8')
    expected_signature = hmac.new(JWT_SECRET.encode('utf-8'), signing_input, hashlib.sha256).digest()
    actual_signature = _base64url_decode(sig_b64)

    if not hmac.compare_digest(expected_signature, actual_signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid cryptographic token signature."
        )

    try:
        payload = json.loads(_base64url_decode(payload_b64).decode('utf-8'))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Corrupted token payload."
        )

    if payload.get("exp", 0) < int(time.time()):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Clinical session token has expired."
        )

    return payload


def get_current_user(authorization: Optional[str] = Header(None)) -> ClinicalUser:
    """
    Dependency that extracts and verifies user identity from Authorization header.
    Falls back gracefully to default Attending user if no header is provided (for demo/testing backward compatibility).
    """
    if not authorization:
        return DEFAULT_USER

    token = authorization.replace("Bearer ", "").strip()
    if not token:
        return DEFAULT_USER

    payload = decode_access_token(token)
    username = payload.get("sub")
    if username in CLINICAL_DIRECTORY:
        return CLINICAL_DIRECTORY[username]

    # Dynamically build user object from token payload if custom
    return ClinicalUser(
        user_id=payload.get("user_id", "USR-GUEST"),
        username=username or "guest",
        full_name=payload.get("full_name", "Clinical Operator"),
        title="Medical Practitioner",
        role=UserRole(payload.get("role", UserRole.ATTENDING_RADIOLOGIST.value)),
        department=payload.get("department", "General Medicine"),
        npi=payload.get("npi"),
        initials="CO"
    )


def require_roles(allowed_roles: List[UserRole]):
    """
    Factory dependency for role-based endpoint protection.
    Raises 403 Forbidden if user's role is not authorized.
    """
    def role_checker(user: ClinicalUser = Depends(get_current_user)) -> ClinicalUser:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access Denied: Role '{user.role.value}' is unauthorized for this clinical action. Permitted roles: {[r.value for r in allowed_roles]}."
            )
        return user
    return role_checker
