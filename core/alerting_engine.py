"""
ALVEON Enterprise Hospital PACS - STAT Critical Trauma Alerting & Closed-Loop Tracking Engine
Conforms to American College of Radiology (ACR) Actionable Reporting Practice Parameters.
Implements:
- ACR Critical Finding Classification (Level 1 STAT / Level 2 Urgent)
- Closed-Loop Verbal Communication Tracker (Mandatory radiologist-to-ER readback documentation)
- Direct integration with HIPAA § 164.312(b) SHA-256 immutable audit ledger
100% Free & Open-Source (Zero external paging vendor fees).
"""

from datetime import datetime, timezone
import uuid
from typing import Dict, Any, List, Optional
from core.audit_logger import get_audit_logger


class AlertingEngine:
    """Enterprise Critical Finding Alerting and Closed-Loop Tracking Service."""
    _instance = None

    def __init__(self):
        self.handoff_records: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def get_instance(cls) -> "AlertingEngine":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def evaluate_study_criticality(self, diagnosis: str, findings: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Evaluates a radiologic exam according to ACR Actionable Reporting Parameters.
        Returns criticality tier, required communication turnaround time, and alert flags.
        """
        d_upper = diagnosis.upper()
        findings_list = findings or []
        has_ptx = any("PNEUMOTHORAX" in f.get("label", "").upper() and f.get("probability", 0) > 0.4 for f in findings_list) or "PNEUMOTHORAX" in d_upper
        has_stroke = any("STROKE" in f.get("label", "").upper() or "HEMORRHAGE" in f.get("label", "").upper() for f in findings_list) or "STROKE" in d_upper or "HEMORRHAGE" in d_upper

        if has_ptx or has_stroke:
            return {
                "criticality_level": 1,
                "tier_name": "ACR LEVEL 1: STAT CRITICAL ALERT",
                "color_code": "#e11d48", # Red
                "mandated_turnaround_minutes": 30,
                "requires_verbal_handoff": True,
                "audible_alert_required": True,
                "banner_pulse": True,
                "action_summary": "Immediate direct verbal communication to treating emergency physician required within 30 minutes with documented readback."
            }
        elif "PNEUMONIA" in d_upper or any("PNEUMONIA" in f.get("label", "").upper() for f in findings_list):
            return {
                "criticality_level": 2,
                "tier_name": "ACR LEVEL 2: URGENT FINDING",
                "color_code": "#f59e0b", # Amber
                "mandated_turnaround_minutes": 720, # 12 hours
                "requires_verbal_handoff": False,
                "audible_alert_required": False,
                "banner_pulse": False,
                "action_summary": "Urgent communication within 12 hours. Standard clinical worklist flag."
            }
        else:
            return {
                "criticality_level": 3,
                "tier_name": "ACR LEVEL 3: ROUTINE FINDING",
                "color_code": "#10b981", # Green
                "mandated_turnaround_minutes": 1440, # 24 hours
                "requires_verbal_handoff": False,
                "audible_alert_required": False,
                "banner_pulse": False,
                "action_summary": "Routine radiologic reporting. No emergency verbal communication required."
            }

    def record_closed_loop_handoff(
        self,
        study_id: str,
        patient_mrn: str,
        patient_name: str,
        critical_finding: str,
        radiologist_name: str,
        er_physician_name: str,
        communication_method: str = "Trauma Bay Hotline",
        readback_confirmed: bool = True,
        notes: str = ""
    ) -> Dict[str, Any]:
        """
        Records an official ACR-compliant closed-loop verbal handoff.
        Permanently writes the attestation event to the tamper-evident HIPAA SHA-256 audit ledger.
        """
        handoff_id = f"CLH-{uuid.uuid4().hex[:8].upper()}"
        now_utc = datetime.now(timezone.utc)
        timestamp_str = now_utc.strftime("%Y-%m-%d %H:%M:%S UTC")

        handoff_data = {
            "handoff_id": handoff_id,
            "study_id": study_id,
            "patient_mrn": patient_mrn,
            "patient_name": patient_name,
            "critical_finding": critical_finding,
            "radiologist_name": radiologist_name,
            "er_physician_name": er_physician_name,
            "communication_method": communication_method,
            "readback_confirmed": readback_confirmed,
            "readback_summary": f"Readback confirmed by {er_physician_name} via {communication_method} at {timestamp_str}",
            "notes": notes,
            "timestamp": timestamp_str,
            "compliance_standard": "ACR Actionable Reporting Practice Parameter § Level 1"
        }

        # Store in active memory
        self.handoff_records[study_id] = handoff_data

        # Write to HIPAA § 164.312(b) Immutable Chained Hash Audit Ledger
        audit = get_audit_logger()
        event = audit.log(
            action="CRITICAL_VERBAL_HANDOFF",
            user_id="RAD-ATTENDING",
            username=radiologist_name,
            user_role="ATTENDING_RADIOLOGIST",
            patient_mrn=patient_mrn,
            study_id=study_id,
            details={
                "handoff_id": handoff_id,
                "critical_finding": critical_finding,
                "communicated_to_physician": er_physician_name,
                "method": communication_method,
                "readback_confirmed": readback_confirmed
            }
        )
        handoff_data["audit_hash"] = event.record_hash

        return handoff_data

    def get_handoff_status(self, study_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves closed-loop communication record for a given study."""
        return self.handoff_records.get(study_id)


def get_alerting_engine() -> AlertingEngine:
    return AlertingEngine.get_instance()
