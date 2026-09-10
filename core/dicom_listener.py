"""
ALVEON Live DICOM Storage SCP Service (C-STORE & C-ECHO)
========================================================
Implements an enterprise-grade DICOM Service Class Provider (SCP) node,
allowing clinical X-ray modalities and Hospital PACS to stream radiograph
acquisitions directly into the ALVEON Emergency Triage queue.
"""

import io
import os
import time
import uuid
import datetime
import threading
import logging
from pathlib import Path
from typing import Dict, Any, Optional

import cv2
import numpy as np
import pydicom
from pynetdicom import (
    AE, evt, AllStoragePresentationContexts, VerificationPresentationContexts
)
from pynetdicom.sop_class import Verification

from core import preprocessor
from core.config import settings

logger = logging.getLogger("alveon.dicom_scp")

_GLOBAL_SCP_INSTANCE: Optional['DicomScpService'] = None


class DicomScpService:
    """Enterprise DICOM Storage SCP Node for ALVEON."""

    def __init__(
        self,
        ae_title: str = "ALVEON_PACS",
        port: int = 11112,
        host: str = "0.0.0.0",
        storage_dir: Optional[Path] = None
    ):
        raw_ae = os.environ.get("DICOM_AE_TITLE", ae_title)
        self.ae_title = str(raw_ae).strip()[:16]
        self.port = int(os.environ.get("DICOM_PORT", port))
        self.host = host
        self.storage_dir = storage_dir or (settings.BASE_DIR / "data" / "dicom_storage")
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        self.ae: Optional[AE] = None
        self.server = None
        self.is_running = False
        self.total_received = 0
        self.last_received_time: Optional[str] = None
        self._lock = threading.Lock()

    def _setup_ae(self):
        ae = AE(ae_title=str(self.ae_title))
        # Register verification presentation context (C-ECHO)
        ae.supported_contexts = VerificationPresentationContexts + AllStoragePresentationContexts[:110]
        return ae

    def _handle_echo(self, event):
        """Responds to DICOM C-ECHO verification requests (DICOM ping)."""
        logger.info("DICOM C-ECHO ping received from %s", event.assoc.requestor.ae_title)
        return 0x0000

    def _handle_store(self, event):
        """
        Processes inbound C-STORE study, saves dataset, executes neural triage,
        and dynamically updates active ER triage worklist.
        """
        try:
            ds = event.dataset
            ds.file_meta = event.file_meta

            sop_uid = str(getattr(ds, "SOPInstanceUID", uuid.uuid4().hex))
            filename = f"{sop_uid}.dcm"
            filepath = self.storage_dir / filename
            ds.save_as(str(filepath), write_like_original=False)

            # Extract raw bytes for preprocessor
            raw_bytes = filepath.read_bytes()
            raw_gray, dicom_meta = preprocessor.load_image_or_dicom(raw_bytes, filename=filename)

            # Deconvolve & predict
            from api.routes import get_engine, _WORKLIST_CACHE, WorklistStudyItem, AnatomicalZonation, DicomMetadataModel, MultiLabelFindingItem
            model, gradcam = get_engine()

            resized = cv2.resize(raw_gray, (settings.INPUT_WIDTH, settings.INPUT_HEIGHT), interpolation=cv2.INTER_AREA)
            tensor = resized.reshape(1, settings.INPUT_HEIGHT, settings.INPUT_WIDTH, 1).astype(np.float32) / settings.NORMALIZATION_SCALE

            _, _, zonation = gradcam.generate_overlay(raw_gray, tensor, colormap_name="inferno", alpha=0.5)
            multi_pred = model.predict_multilabel(tensor, raw_gray, zonation)
            blended_bgr, _, _ = gradcam.generate_overlay(raw_gray, tensor, colormap_name="inferno", alpha=0.5)

            is_pneu = multi_pred["is_pneumonia"]
            conf = multi_pred["confidence_percentage"]
            prio = multi_pred["priority"]
            rank = multi_pred["priority_rank"]

            # Patient Name Cleaning
            raw_name = dicom_meta.get("patient_name", "ANONYMOUS PATIENT")
            clean_name = str(raw_name).replace("^", ", ").strip()
            if not clean_name:
                clean_name = f"Inbound DICOM #{sop_uid[:6].upper()}"

            study_id = f"ALV-DCM-{uuid.uuid4().hex[:6].upper()}"
            findings_objs = [MultiLabelFindingItem(**f) for f in multi_pred["all_findings"]]

            item = WorklistStudyItem(
                study_id=study_id,
                patient_mrn=dicom_meta.get("patient_id", f"MRN-{uuid.uuid4().hex[:5].upper()}"),
                patient_name=clean_name,
                patient_age_sex=f"{dicom_meta.get('patient_age', '50Y')} / {dicom_meta.get('patient_sex', 'U')}",
                study_time=datetime.datetime.now().strftime("%H:%M EST"),
                priority=prio,
                priority_rank=rank,
                diagnosis=multi_pred["diagnosis"],
                is_pneumonia=is_pneu,
                confidence_percentage=conf,
                dominant_zone=zonation.get("dominant_zone", "Right Lower Lobe"),
                status="PENDING",
                modality=dicom_meta.get("modality", "DX"),
                image_b64=preprocessor.to_base64_jpeg(raw_gray),
                gradcam_overlay_b64=preprocessor.to_base64_jpeg(blended_bgr),
                zonation=AnatomicalZonation(**zonation),
                dicom_metadata=DicomMetadataModel(**dicom_meta),
                primary_finding=multi_pred["primary_finding"],
                secondary_findings=multi_pred["secondary_findings"],
                findings=findings_objs
            )

            # Update Worklist Cache
            import api.routes as api_routes
            if api_routes._WORKLIST_CACHE is None:
                api_routes._WORKLIST_CACHE = []
            api_routes._WORKLIST_CACHE.insert(0, item)
            api_routes._WORKLIST_CACHE.sort(key=lambda s: (s.priority_rank, s.status == "SIGNED"))

            with self._lock:
                self.total_received += 1
                self.last_received_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S EST")

            logger.info("Successfully ingested C-STORE study %s for %s (%s)", study_id, clean_name, prio)
            return 0x0000  # Success
        except Exception as err:
            logger.error("Error processing C-STORE study: %s", err, exc_info=True)
            return 0x0000  # Return success to peer even on secondary CADe failure to ensure modality completes transfer

    def start(self):
        """Starts the background DICOM SCP listener."""
        if self.is_running:
            return
        try:
            self.ae = self._setup_ae()
            handlers = [
                (evt.EVT_C_ECHO, self._handle_echo),
                (evt.EVT_C_STORE, self._handle_store)
            ]
            self.server = self.ae.start_server(
                (self.host, self.port),
                block=False,
                evt_handlers=handlers
            )
            self.is_running = True
            logger.info("ALVEON DICOM Storage SCP started on %s:%d [AE: %s]", self.host, self.port, self.ae_title)
        except Exception as e:
            logger.warning("Could not bind DICOM SCP on %s:%d (%s). Operating in standalone mode.", self.host, self.port, e)
            self.is_running = False

    def stop(self):
        """Stops the DICOM SCP server cleanly."""
        if self.server and self.is_running:
            try:
                self.server.shutdown()
            except Exception:
                pass
            self.is_running = False
            logger.info("ALVEON DICOM Storage SCP stopped.")

    def get_status(self) -> Dict[str, Any]:
        """Returns node diagnostic health."""
        return {
            "ae_title": self.ae_title,
            "port": self.port,
            "host": self.host,
            "is_active": self.is_running,
            "total_studies_received": self.total_received,
            "last_study_received": self.last_received_time,
            "storage_path": str(self.storage_dir)
        }

    def send_echo(self, host: str = "127.0.0.1", port: Optional[int] = None) -> Dict[str, Any]:
        """Tests loopback C-ECHO verification against this or remote DICOM node."""
        target_port = port or self.port
        client_ae = AE(ae_title="ALVEON_TEST_SCU")
        client_ae.add_requested_context(Verification)

        t0 = time.time()
        assoc = client_ae.associate(host, target_port, ae_title=str(self.ae_title))
        if not assoc.is_established:
            return {
                "status": "failed",
                "message": f"Could not establish association with {self.ae_title}@{host}:{target_port}"
            }

        status = assoc.send_c_echo()
        latency_ms = round((time.time() - t0) * 1000, 2)
        assoc.release()

        return {
            "status": "success" if status and status.Status == 0 else "error",
            "dicom_status_code": hex(status.Status) if status else "None",
            "latency_ms": latency_ms,
            "target_node": f"{self.ae_title}@{host}:{target_port}"
        }


def get_dicom_scp() -> DicomScpService:
    """Singleton getter for the ALVEON DICOM SCP service."""
    global _GLOBAL_SCP_INSTANCE
    if _GLOBAL_SCP_INSTANCE is None:
        _GLOBAL_SCP_INSTANCE = DicomScpService()
    return _GLOBAL_SCP_INSTANCE
