"""
ALVEON External PACS SCU Client & Network Bridge
================================================
Provides enterprise DICOM Service Class User (SCU) client functionality:
- C-ECHO (Ping external PACS nodes)
- C-STORE (Push local/CADe studies to external hospital archives)
- C-FIND (Query external PACS study worklists)
- C-MOVE (Request remote PACS to route studies to ALVEON listener)
"""

import io
import time
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Union

import pydicom
from pydicom.dataset import Dataset
from pynetdicom import AE, StoragePresentationContexts, QueryRetrievePresentationContexts
from pynetdicom.sop_class import (
    Verification,
    PatientRootQueryRetrieveInformationModelFind,
    StudyRootQueryRetrieveInformationModelFind,
    DigitalXRayImageStorageForPresentation,
    DigitalXRayImageStorageForProcessing,
    ComputedRadiographyImageStorage,
    SecondaryCaptureImageStorage
)

logger = logging.getLogger("alveon.pacs_client")

class ExternalPacsClient:
    """Enterprise DICOM SCU client for bi-directional hospital PACS connectivity."""

    def __init__(self, local_ae_title: str = "ALVEON_SCU"):
        self.local_ae_title = local_ae_title[:16]

    def ping(self, host: str, port: int, remote_ae: str = "ANY_SCP", timeout: int = 5) -> Dict[str, Any]:
        """
        Sends DICOM C-ECHO verification request to external PACS.
        """
        ae = AE(ae_title=self.local_ae_title)
        ae.network_timeout = timeout
        ae.acse_timeout = timeout
        ae.dimse_timeout = timeout
        ae.add_requested_context(Verification)

        t0 = time.perf_counter()
        assoc = ae.associate(host, port, ae_title=remote_ae.strip()[:16])
        if not assoc.is_established:
            return {
                "status": "offline",
                "success": False,
                "message": f"Could not establish association with {remote_ae}@{host}:{port}",
                "latency_ms": None
            }

        status = assoc.send_c_echo()
        latency_ms = round((time.perf_counter() - t0) * 1000, 2)
        assoc.release()

        is_ok = bool(status and status.Status == 0)
        return {
            "status": "online" if is_ok else "error",
            "success": is_ok,
            "dicom_status_code": hex(status.Status) if status else None,
            "target": f"{remote_ae}@{host}:{port}",
            "latency_ms": latency_ms
        }

    def push_study(
        self,
        dcm_input: Union[str, Path, bytes, Dataset],
        host: str,
        port: int,
        remote_ae: str = "ALVEON_PACS",
        timeout: int = 15
    ) -> Dict[str, Any]:
        """
        Transmits a DICOM study dataset to external PACS via C-STORE.
        """
        if isinstance(dcm_input, (str, Path)):
            ds = pydicom.dcmread(str(dcm_input), force=True)
        elif isinstance(dcm_input, bytes):
            ds = pydicom.dcmread(io.BytesIO(dcm_input), force=True)
        elif isinstance(dcm_input, Dataset):
            ds = dcm_input
        else:
            raise ValueError("Unsupported dcm_input type for C-STORE transmission.")

        # Ensure SOPClassUID is available
        sop_class = getattr(ds, "SOPClassUID", "1.2.840.10008.5.1.4.1.1.1")

        ae = AE(ae_title=self.local_ae_title)
        ae.network_timeout = timeout
        ae.acse_timeout = timeout
        ae.dimse_timeout = timeout
        # Register storage contexts
        ae.requested_contexts = StoragePresentationContexts[:64]
        try:
            ae.add_requested_context(sop_class)
        except Exception:
            pass

        t0 = time.perf_counter()
        assoc = ae.associate(host, port, ae_title=remote_ae.strip()[:16])
        if not assoc.is_established:
            return {
                "status": "error",
                "success": False,
                "message": f"Connection refused or association rejected by {remote_ae}@{host}:{port}"
            }

        status = assoc.send_c_store(ds)
        latency_ms = round((time.perf_counter() - t0) * 1000, 2)
        assoc.release()

        success = bool(status and status.Status == 0x0000)
        return {
            "status": "success" if success else "failed",
            "success": success,
            "dicom_status_code": hex(status.Status) if status else "None",
            "patient_id": getattr(ds, "PatientID", "UNKNOWN"),
            "patient_name": str(getattr(ds, "PatientName", "UNKNOWN")),
            "sop_instance_uid": getattr(ds, "SOPInstanceUID", "UNKNOWN"),
            "destination": f"{remote_ae}@{host}:{port}",
            "latency_ms": latency_ms
        }

    def query_studies(
        self,
        host: str,
        port: int,
        remote_ae: str,
        patient_id: Optional[str] = None,
        patient_name: Optional[str] = None,
        study_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Executes C-FIND query against remote PACS for study metadata.
        """
        ae = AE(ae_title=self.local_ae_title)
        ae.add_requested_context(StudyRootQueryRetrieveInformationModelFind)

        assoc = ae.associate(host, port, ae_title=remote_ae.strip()[:16])
        if not assoc.is_established:
            logger.error("Could not associate for C-FIND with %s@%s:%d", remote_ae, host, port)
            return []

        query_ds = Dataset()
        query_ds.QueryRetrieveLevel = "STUDY"
        query_ds.PatientID = patient_id or ""
        query_ds.PatientName = patient_name or ""
        query_ds.StudyDate = study_date or ""
        query_ds.StudyInstanceUID = ""
        query_ds.Modality = ""
        query_ds.StudyDescription = ""

        results: List[Dict[str, Any]] = []
        responses = assoc.send_c_find(query_ds, StudyRootQueryRetrieveInformationModelFind)

        for status, identifier in responses:
            if status and status.Status in (0xFF00, 0xFF01) and identifier:
                results.append({
                    "patient_id": getattr(identifier, "PatientID", ""),
                    "patient_name": str(getattr(identifier, "PatientName", "")),
                    "study_date": getattr(identifier, "StudyDate", ""),
                    "study_uid": getattr(identifier, "StudyInstanceUID", ""),
                    "modality": getattr(identifier, "Modality", ""),
                    "description": getattr(identifier, "StudyDescription", "")
                })

        assoc.release()
        return results

# Global client singleton
_pacs_client: Optional[ExternalPacsClient] = None

def get_pacs_client() -> ExternalPacsClient:
    global _pacs_client
    if _pacs_client is None:
        _pacs_client = ExternalPacsClient()
    return _pacs_client
