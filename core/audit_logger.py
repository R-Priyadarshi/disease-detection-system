"""
ALVEON HIPAA Security Rule § 164.312(b) Audit Controls Engine
Maintains an immutable, tamper-evident audit ledger for all Protected Health Information (PHI)
access, neural inference, diagnostic measurements, and legal electronic sign-offs.
Uses chained cryptographic SHA-256 hashes (blockchain-style) to guarantee audit record integrity.
"""

import json
import time
import hashlib
import uuid
from pathlib import Path
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

AUDIT_LOG_DIR = Path("/home/rishikesh/.gemini/antigravity-ide/scratch/disease-detection-system/data")
AUDIT_LOG_FILE = AUDIT_LOG_DIR / "hipaa_audit_trail.jsonl"
GENESIS_HASH = "0000000000000000ALVEON_HIPAA_GENESIS_BLOCK_2026_SECURITY"


class AuditEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: f"AUD-{uuid.uuid4().hex[:12].upper()}")
    timestamp_utc: str
    timestamp_epoch: float
    user_id: str
    username: str
    user_role: str
    action: str  # LOGIN, PHI_VIEW, AI_INFERENCE, CALIPER_MEASURED, ATTESTATION_SIGNED, PDF_EXPORTED, STUDY_DELETED, COHORT_INGESTED
    patient_mrn: Optional[str] = None
    study_id: Optional[str] = None
    ip_address: str = "127.0.0.1"
    details: Dict[str, Any] = Field(default_factory=dict)
    prev_hash: str
    record_hash: str


class AuditLogger:
    """Manages appending and verifying chained SHA-256 HIPAA audit events."""

    _instance: Optional['AuditLogger'] = None

    def __init__(self, log_path: Path = AUDIT_LOG_FILE):
        self.log_path = log_path
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._last_hash = self._get_latest_hash()

    @classmethod
    def get_instance(cls) -> 'AuditLogger':
        if cls._instance is None:
            cls._instance = AuditLogger()
        return cls._instance

    def _get_latest_hash(self) -> str:
        """Reads the last line of the audit log to retrieve the previous block hash."""
        if not self.log_path.exists() or self.log_path.stat().st_size == 0:
            return GENESIS_HASH

        try:
            with open(self.log_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                if not lines:
                    return GENESIS_HASH
                last_line = lines[-1].strip()
                if not last_line:
                    return GENESIS_HASH
                data = json.loads(last_line)
                return data.get("record_hash", GENESIS_HASH)
        except Exception:
            return GENESIS_HASH

    def log(
        self,
        action: str,
        user_id: str,
        username: str,
        user_role: str,
        patient_mrn: Optional[str] = None,
        study_id: Optional[str] = None,
        ip_address: str = "127.0.0.1",
        details: Optional[Dict[str, Any]] = None
    ) -> AuditEvent:
        """Appends a cryptographically verified event to the HIPAA audit ledger."""
        now = time.time()
        timestamp_utc = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(now))
        event_id = f"AUD-{uuid.uuid4().hex[:12].upper()}"
        details_clean = details or {}

        # Canonical hashing payload
        hash_payload = {
            "event_id": event_id,
            "timestamp_epoch": now,
            "user_id": user_id,
            "username": username,
            "user_role": user_role,
            "action": action,
            "patient_mrn": patient_mrn,
            "study_id": study_id,
            "ip_address": ip_address,
            "prev_hash": self._last_hash,
            "details": details_clean
        }
        canonical_str = json.dumps(hash_payload, sort_keys=True, separators=(',', ':'))
        record_hash = hashlib.sha256(canonical_str.encode('utf-8')).hexdigest()

        event = AuditEvent(
            event_id=event_id,
            timestamp_utc=timestamp_utc,
            timestamp_epoch=now,
            user_id=user_id,
            username=username,
            user_role=user_role,
            action=action,
            patient_mrn=patient_mrn,
            study_id=study_id,
            ip_address=ip_address,
            details=details_clean,
            prev_hash=self._last_hash,
            record_hash=record_hash
        )

        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event.model_dump()) + "\n")

        self._last_hash = record_hash
        return event

    def query(self, limit: int = 50, action: Optional[str] = None) -> List[AuditEvent]:
        """Retrieves recent audit events in reverse chronological order."""
        if not self.log_path.exists():
            return []

        events = []
        try:
            with open(self.log_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        event_dict = json.loads(line)
                        if action and event_dict.get("action") != action:
                            continue
                        events.append(AuditEvent(**event_dict))
        except Exception:
            return []

        events.reverse()
        return events[:limit]

    def verify_integrity(self) -> Dict[str, Any]:
        """
        Cryptographically verifies the entire chained-hash ledger.
        Returns whether the audit trail is untampered, total blocks verified, and any corrupted block.
        """
        if not self.log_path.exists() or self.log_path.stat().st_size == 0:
            return {
                "is_valid": True,
                "total_events": 0,
                "message": "Audit ledger is empty (Genesis state)."
            }

        expected_prev_hash = GENESIS_HASH
        count = 0

        with open(self.log_path, "r", encoding="utf-8") as f:
            for idx, line in enumerate(f):
                line = line.strip()
                if not line:
                    continue
                count += 1
                record = json.loads(line)

                # Check chained previous hash
                if record.get("prev_hash") != expected_prev_hash:
                    return {
                        "is_valid": False,
                        "corrupted_event_id": record.get("event_id"),
                        "index": idx,
                        "error": f"Hash chain broken at index {idx}. Expected prev_hash {expected_prev_hash[:12]}..., got {record.get('prev_hash')[:12]}..."
                    }

                # Recompute record hash
                hash_payload = {
                    "event_id": record["event_id"],
                    "timestamp_epoch": record["timestamp_epoch"],
                    "user_id": record["user_id"],
                    "username": record["username"],
                    "user_role": record["user_role"],
                    "action": record["action"],
                    "patient_mrn": record.get("patient_mrn"),
                    "study_id": record.get("study_id"),
                    "ip_address": record.get("ip_address", "127.0.0.1"),
                    "prev_hash": record["prev_hash"],
                    "details": record.get("details", {})
                }
                canonical_str = json.dumps(hash_payload, sort_keys=True, separators=(',', ':'))
                recomputed = hashlib.sha256(canonical_str.encode('utf-8')).hexdigest()

                if recomputed != record.get("record_hash"):
                    return {
                        "is_valid": False,
                        "corrupted_event_id": record.get("event_id"),
                        "index": idx,
                        "error": f"Data integrity violation at event {record.get('event_id')}. Hash does not match content."
                    }

                expected_prev_hash = record["record_hash"]

        return {
            "is_valid": True,
            "total_events": count,
            "latest_hash": expected_prev_hash,
            "message": f"Cryptographic integrity verified. {count} chained audit blocks confirmed untampered."
        }


def get_audit_logger() -> AuditLogger:
    """Singleton getter for the HIPAA audit logger."""
    return AuditLogger.get_instance()
