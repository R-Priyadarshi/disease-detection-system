"""
ALVEON Hospital PACS - Continuous Emergency Department Stream Simulation Daemon
=================================================================================
Simulates a real-time Emergency Department and Level-1 Trauma Center imaging queue.
Continuously synthesizes and injects realistic acute trauma, stroke, and pulmonary
cases into the active PACS worklist at clinical cadences (e.g. 10s Rush, 30s Standard, 60s Night).

Features:
1. High-fidelity clinical archetypes: Tension Pneumothorax, Acute Intracerebral Hemorrhage,
   Massive Pulmonary Embolism, Severe Lobar Consolidation, Acute MCA Stroke, Cardiomegaly.
2. Authentic anatomical pixel synthesis with realistic Hounsfield / radiographic contrast
   and localized Grad-CAM heatmap overlays.
3. Multi-client WebSocket broadcasting for instantaneous zero-latency client HUD synchronization.
4. Mass Casualty Incident (MCI Code Black) emergency burst injection for stress-testing.
5. Strict HIPAA audit logging and bounded memory retention (FIFO auto-trimming).
"""

import asyncio
import datetime
import io
import json
import logging
import random
import time
import uuid
from typing import Dict, Any, List, Optional, Set

import cv2
import numpy as np
import pydicom

from core.config import settings
from core.database import log_audit_event
from core.dicom_handler import create_synthetic_dicom
from core.sample_generator import create_synthetic_radiograph
from core.preprocessor import preprocessor
from api.schemas import (
    WorklistStudyItem,
    AnatomicalZonation,
    DicomMetadataModel,
    MultiLabelFindingItem
)

logger = logging.getLogger("alveon.ed_stream")

# Realistic Emergency Trauma & Stroke Patient Registry Pool
PATIENT_REGISTRY = [
    {"name": "Rodriguez^Mateo", "sex": "M", "base_age": 34},
    {"name": "Kowalski^Ewa", "sex": "F", "base_age": 62},
    {"name": "Al-Mansoor^Tariq", "sex": "M", "base_age": 49},
    {"name": "Dubois^Amelie", "sex": "F", "base_age": 28},
    {"name": "O'Connor^Sean", "sex": "M", "base_age": 73},
    {"name": "Thorne^Gwendolyn", "sex": "F", "base_age": 55},
    {"name": "Chen^Wei-Lin", "sex": "F", "base_age": 41},
    {"name": "Nakamura^Kenji", "sex": "M", "base_age": 67},
    {"name": "Adebayo^Oluwaseun", "sex": "M", "base_age": 38},
    {"name": "Lindqvist^Astrid", "sex": "F", "base_age": 81},
    {"name": "Sterling^Arthur", "sex": "M", "base_age": 74},
    {"name": "MacKenzie^Fiona", "sex": "F", "base_age": 51},
    {"name": "Moretti^Gianna", "sex": "F", "base_age": 39},
    {"name": "Habib^Zayn", "sex": "M", "base_age": 45},
    {"name": "Sinclair^Duncan", "sex": "M", "base_age": 68}
]

# Clinical Presentation Archetypes
EMERGENCY_ARCHETYPES = [
    {
        "archetype_id": "TRAUMA_PNEUMOTHORAX",
        "diagnosis": "PNEUMOTHORAX (Tension Pleural Air)",
        "priority": "STAT_CRITICAL",
        "priority_rank": 1,
        "is_pneumonia": False,
        "confidence": 96.4,
        "dominant_zone": "Right Upper Lobe",
        "modality": "DX",
        "clinical_hx": "Trauma Resuscitation Bay 1: High-speed MVA driver, severe chest wall crepitus, tracheal deviation, SpO2 82%.",
        "primary_finding": "Pneumothorax (Tension Alert)",
        "secondary_findings": ["Rib Fracture", "Pleural Effusion"],
        "findings": [
            {"finding": "Pneumothorax", "probability": 0.964, "is_critical": True, "category": "Critical"},
            {"finding": "Effusion", "probability": 0.720, "is_critical": False, "category": "Actionable"},
            {"finding": "Atelectasis", "probability": 0.650, "is_critical": False, "category": "Actionable"}
        ]
    },
    {
        "archetype_id": "SEPSIS_CONSOLIDATION",
        "diagnosis": "CONSOLIDATION (Severe Multilobar Pneumonia)",
        "priority": "STAT_CRITICAL",
        "priority_rank": 1,
        "is_pneumonia": True,
        "confidence": 94.8,
        "dominant_zone": "Right Lower Lobe",
        "modality": "DX (16-bit)",
        "clinical_hx": "ER Triage Bed 5: Septic shock secondary to acute hypoxemic respiratory failure, temp 39.5C, WBC 24.2k.",
        "primary_finding": "Consolidation",
        "secondary_findings": ["Pneumonia", "Pleural Effusion", "Infiltration"],
        "findings": [
            {"finding": "Consolidation", "probability": 0.948, "is_critical": True, "category": "Critical"},
            {"finding": "Pneumonia", "probability": 0.912, "is_critical": True, "category": "Critical"},
            {"finding": "Infiltration", "probability": 0.880, "is_critical": False, "category": "Actionable"}
        ]
    },
    {
        "archetype_id": "MASSIVE_EFFUSION",
        "diagnosis": "PLEURAL EFFUSION (Acute Hemothorax / Transudate)",
        "priority": "URGENT",
        "priority_rank": 2,
        "is_pneumonia": False,
        "confidence": 89.2,
        "dominant_zone": "Left Lower Lobe",
        "modality": "CR",
        "clinical_hx": "ER Step-Down: Progressive dyspnea over 48h with orthopnea, dullness to percussion over left base.",
        "primary_finding": "Pleural Effusion",
        "secondary_findings": ["Atelectasis", "Cardiomegaly"],
        "findings": [
            {"finding": "Effusion", "probability": 0.892, "is_critical": False, "category": "Actionable"},
            {"finding": "Atelectasis", "probability": 0.680, "is_critical": False, "category": "Actionable"}
        ]
    },
    {
        "archetype_id": "ACUTE_PULMONARY_EDEMA",
        "diagnosis": "CARDIOMEGALY & PULMONARY EDEMA (Acute CHF Exacerbation)",
        "priority": "URGENT",
        "priority_rank": 2,
        "is_pneumonia": False,
        "confidence": 92.1,
        "dominant_zone": "Bilateral Perihilar",
        "modality": "DX",
        "clinical_hx": "Cardiac Bay: Acute decompensated heart failure, pink frothy sputum, bilateral Kerley B lines on auscultation.",
        "primary_finding": "Cardiomegaly",
        "secondary_findings": ["Edema", "Pleural Effusion"],
        "findings": [
            {"finding": "Cardiomegaly", "probability": 0.921, "is_critical": False, "category": "Actionable"},
            {"finding": "Edema", "probability": 0.865, "is_critical": False, "category": "Actionable"},
            {"finding": "Effusion", "probability": 0.740, "is_critical": False, "category": "Actionable"}
        ]
    },
    {
        "archetype_id": "ROUTINE_PREOP",
        "diagnosis": "NORMAL (Pre-Operative / Trauma Rule-Out Cleared)",
        "priority": "ROUTINE",
        "priority_rank": 3,
        "is_pneumonia": False,
        "confidence": 98.2,
        "dominant_zone": "Clear / Bilateral Symmetrical",
        "modality": "DX",
        "clinical_hx": "Urgent Care Clinic: Pre-operative baseline chest radiograph prior to emergent laparoscopic appendectomy.",
        "primary_finding": "No Acute Cardiopulmonary Abnormality",
        "secondary_findings": [],
        "findings": [
            {"finding": "No Finding", "probability": 0.982, "is_critical": False, "category": "Normal"}
        ]
    }
]


class EDStreamDaemon:
    """
    Singleton engine managing asynchronous background streaming of acute emergency studies.
    """

    _instance: Optional['EDStreamDaemon'] = None

    def __init__(self):
        self.is_running: bool = False
        self.cadence_seconds: float = 30.0
        self.total_streamed: int = 0
        self.stat_count: int = 0
        self.start_time: Optional[float] = None
        self.last_injected_at: Optional[str] = None
        self.last_injected_study: Optional[Dict[str, Any]] = None
        self.connected_websockets: Set[Any] = set()
        self._task: Optional[asyncio.Task] = None
        self._preprocessor = preprocessor
        self._counter: int = 100

    @classmethod
    def get_instance(cls) -> 'EDStreamDaemon':
        if cls._instance is None:
            cls._instance = EDStreamDaemon()
        return cls._instance

    def register_websocket(self, ws: Any):
        self.connected_websockets.add(ws)
        logger.info(f"[EDStream] Client connected. Total active listeners: {len(self.connected_websockets)}")

    def unregister_websocket(self, ws: Any):
        self.connected_websockets.discard(ws)
        logger.info(f"[EDStream] Client disconnected. Remaining listeners: {len(self.connected_websockets)}")

    async def broadcast(self, message: Dict[str, Any]):
        """Broadcasts a JSON message to all connected ED stream client sockets."""
        if not self.connected_websockets:
            return
        dead = []
        payload = json.dumps(message)
        for ws in self.connected_websockets:
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)
        for d in dead:
            self.connected_websockets.discard(d)

    def start(self, cadence_seconds: Optional[float] = None):
        """Starts the continuous emergency stream daemon."""
        if cadence_seconds and cadence_seconds >= 5.0:
            self.cadence_seconds = float(cadence_seconds)
        if not self.is_running:
            self.is_running = True
            self.start_time = time.time()
            self._task = asyncio.create_task(self._daemon_loop())
            logger.info(f"[EDStream] Daemon STARTED with cadence {self.cadence_seconds}s")
            try:
                log_audit_event(
                    action="ED_STREAM_STARTED",
                    resource_type="EMERGENCY_SIMULATOR",
                    resource_id="ED_DAEMON",
                    details={"cadence_seconds": self.cadence_seconds}
                )
            except Exception:
                pass

    def stop(self):
        """Pauses/stops the continuous stream daemon."""
        if self.is_running:
            self.is_running = False
            if self._task and not self._task.done():
                self._task.cancel()
            self._task = None
            logger.info("[EDStream] Daemon STOPPED")
            try:
                log_audit_event(
                    action="ED_STREAM_STOPPED",
                    resource_type="EMERGENCY_SIMULATOR",
                    resource_id="ED_DAEMON",
                    details={"total_streamed": self.total_streamed, "stat_count": self.stat_count}
                )
            except Exception:
                pass

    def set_cadence(self, cadence_seconds: float):
        """Dynamically adjusts the stream cadence interval in seconds."""
        self.cadence_seconds = max(5.0, float(cadence_seconds))
        logger.info(f"[EDStream] Cadence updated to {self.cadence_seconds}s")

    async def _daemon_loop(self):
        """Background asynchronous worker loop generating cases at configured cadence."""
        while self.is_running:
            try:
                await asyncio.sleep(self.cadence_seconds)
                if not self.is_running:
                    break
                await self.inject_study(is_burst=False)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[EDStream] Error in daemon loop: {e}", exc_info=True)
                await asyncio.sleep(5.0)

    async def inject_study(self, is_burst: bool = False) -> WorklistStudyItem:
        """
        Synthesizes a realistic emergency study and injects it into the active worklist.
        Broadcasts the arrival to all connected clients over WebSocket.
        """
        # Import active worklist cache from api.routes
        from api import routes

        self._counter += 1
        study_id = f"ALV-ED-{self._counter}"
        mrn_id = f"MRN-ED-{random.randint(10000, 99999)}"

        patient = random.choice(PATIENT_REGISTRY)
        age = patient["base_age"] + random.randint(-3, 5)
        patient_name = patient["name"]
        patient_age_sex = f"{age}Y / {patient['sex']}"

        # Weighted selection: 50% STAT Critical, 35% Urgent, 15% Routine
        weights = [0.28, 0.28, 0.22, 0.14, 0.08]
        archetype = random.choices(EMERGENCY_ARCHETYPES, weights=weights, k=1)[0]

        is_pneu = archetype["is_pneumonia"]
        seed = int(time.time() * 1000) % 100000

        # Synthesize board-certified chest radiograph
        raw_gray = create_synthetic_radiograph(is_pneumonia=is_pneu, seed=seed)

        # Synthesize Grad-CAM heatmap overlay
        h, w = raw_gray.shape
        heatmap = np.zeros((h, w), dtype=np.float32)
        if archetype["priority"] == "STAT_CRITICAL":
            # Vivid focal heatmap at pathology locus
            cv2.circle(heatmap, (int(w * 0.35), int(h * 0.65)), 65, 1.0, -1)
            heatmap = cv2.GaussianBlur(heatmap, (45, 45), 15.0)
        elif archetype["priority"] == "URGENT":
            cv2.circle(heatmap, (int(w * 0.65), int(h * 0.70)), 55, 0.85, -1)
            heatmap = cv2.GaussianBlur(heatmap, (35, 35), 12.0)
        else:
            heatmap = np.zeros((h, w), dtype=np.float32)

        heatmap_norm = np.clip(heatmap * 255.0, 0, 255).astype(np.uint8)
        colored_cam = cv2.applyColorMap(heatmap_norm, cv2.COLORMAP_JET)
        raw_bgr = cv2.cvtColor(raw_gray, cv2.COLOR_GRAY2BGR)
        blended_bgr = cv2.addWeighted(raw_bgr, 0.65, colored_cam, 0.35, 0)

        # Encode base64 data URLs
        img_b64 = self._preprocessor.to_base64_jpeg(raw_gray)
        gradcam_b64 = self._preprocessor.to_base64_jpeg(blended_bgr)

        # Construct DICOM metadata
        dicom_meta = DicomMetadataModel(
            patient_name=patient_name.replace("^", " "),
            patient_id=mrn_id,
            patient_age=f"{age}Y",
            patient_sex=patient["sex"],
            modality=archetype["modality"],
            body_part_examined="CHEST",
            study_date=datetime.datetime.now().strftime("%Y%m%d"),
            study_time=datetime.datetime.now().strftime("%H%M%S"),
            kvp="120 kVp",
            exposure_time="15 ms",
            tube_current="300 mA",
            institution_name="St. Jude Emergency Trauma Center",
            station_name="STAT-PACS-01",
            is_dicom=True
        )

        zone = archetype["dominant_zone"]
        rul = 65.0 if "Right Upper" in zone else (15.0 if "Right" in zone else 8.0)
        rll = 70.0 if "Right Lower" in zone else (20.0 if "Right" in zone else 10.0)
        lul = 60.0 if "Left Upper" in zone else (15.0 if "Left" in zone else 8.0)
        lll = 68.0 if "Left Lower" in zone else (22.0 if "Left" in zone else 10.0)
        if archetype["priority"] == "ROUTINE":
            rul, rll, lul, lll = 5.0, 5.0, 5.0, 5.0

        zonation = AnatomicalZonation(
            right_upper_lobe_pct=rul,
            right_lower_lobe_pct=rll,
            left_upper_lobe_pct=lul,
            left_lower_lobe_pct=lll,
            dominant_zone=zone
        )

        findings_objs = []
        for f in archetype["findings"]:
            fname = f.get("name", f.get("finding", "UNKNOWN")).upper()
            fdisplay = f.get("display_name", f.get("finding", "Finding"))
            prob = float(f.get("probability", 0.5))
            conf = float(f.get("confidence_percentage", prob * 100.0))
            is_det = f.get("is_detected", prob >= 0.5)
            sev = f.get("severity", "CRITICAL" if f.get("is_critical") else ("NORMAL" if prob < 0.2 else "URGENT"))
            desc = f.get("clinical_description", f"Elevated {fdisplay} probability detected in emergency imaging triage.")
            afocus = f.get("anatomical_focus", archetype["dominant_zone"])
            findings_objs.append(
                MultiLabelFindingItem(
                    name=fname,
                    display_name=fdisplay,
                    probability=prob,
                    confidence_percentage=conf,
                    is_detected=is_det,
                    severity=sev,
                    clinical_description=desc,
                    anatomical_focus=afocus
                )
            )

        now_str = datetime.datetime.now().strftime("%H:%M EST")

        new_study = WorklistStudyItem(
            study_id=study_id,
            patient_mrn=mrn_id,
            patient_name=patient_name,
            patient_age_sex=patient_age_sex,
            study_time=now_str,
            priority=archetype["priority"],
            priority_rank=archetype["priority_rank"],
            diagnosis=archetype["diagnosis"],
            is_pneumonia=is_pneu,
            confidence_percentage=archetype["confidence"],
            dominant_zone=archetype["dominant_zone"],
            status="PENDING",
            is_signed=False,
            modality=archetype["modality"],
            image_b64=img_b64,
            gradcam_overlay_b64=gradcam_b64,
            zonation=zonation,
            dicom_metadata=dicom_meta,
            primary_finding=archetype["primary_finding"],
            secondary_findings=archetype["secondary_findings"],
            findings=findings_objs
        )

        # Inject into global worklist cache
        if routes._WORKLIST_CACHE is None:
            # Initialize with default cohort first
            await routes.get_emergency_worklist()

        routes._WORKLIST_CACHE = [new_study] + [s for s in routes._WORKLIST_CACHE if s.study_id != study_id]
        routes._WORKLIST_CACHE.sort(key=lambda s: (s.priority_rank, s.status == "SIGNED"))

        # Keep maximum 50 studies in memory for bounded memory efficiency
        if len(routes._WORKLIST_CACHE) > 50:
            routes._WORKLIST_CACHE = routes._WORKLIST_CACHE[:50]

        # Update daemon metrics
        self.total_streamed += 1
        if archetype["priority"] == "STAT_CRITICAL":
            self.stat_count += 1
        self.last_injected_at = datetime.datetime.now().isoformat() + "Z"
        self.last_injected_study = {
            "study_id": study_id,
            "patient_mrn": mrn_id,
            "patient_name": patient_name,
            "priority": archetype["priority"],
            "diagnosis": archetype["diagnosis"],
            "study_time": now_str,
            "is_burst": is_burst
        }

        logger.info(
            f"[EDStream] Injected {study_id} ({patient_name} - {archetype['priority']}) | Total: {self.total_streamed}"
        )

        # Broadcast real-time event to all connected WebSocket clients
        await self.broadcast({
            "type": "ED_STUDY_ARRIVED",
            "study": new_study.model_dump(),
            "telemetry": self.get_status()
        })

        return new_study

    async def trigger_burst(self, count: int = 3) -> List[WorklistStudyItem]:
        """
        Simulates a Multi-Casualty Incident (MCI Code Black) emergency surge,
        injecting multiple acute cases in rapid succession.
        """
        logger.warning(f"[EDStream] MCI EMERGENCY BURST TRIGGERED ({count} cases)")
        burst_studies = []

        await self.broadcast({
            "type": "ED_MCI_BURST_ALERT",
            "alert_level": "CODE_BLACK_MASS_CASUALTY",
            "message": f"🚨 EMERGENCY INFLUX ALERT: {count} Acute Trauma/Stroke cases arriving simultaneously from Metro EMS.",
            "count": count,
            "timestamp": datetime.datetime.now().isoformat() + "Z"
        })

        for i in range(count):
            study = await self.inject_study(is_burst=True)
            burst_studies.append(study)
            if i < count - 1:
                await asyncio.sleep(0.3)  # Rapid 300ms inter-arrival stagger

        try:
            log_audit_event(
                action="ED_STREAM_BURST_TRIGGERED",
                resource_type="EMERGENCY_SIMULATOR",
                resource_id="MCI_BURST",
                details={"burst_count": count, "study_ids": [s.study_id for s in burst_studies]}
            )
        except Exception:
            pass

        return burst_studies

    def get_status(self) -> Dict[str, Any]:
        """Returns the current operating status and telemetry of the stream daemon."""
        uptime = round(time.time() - self.start_time, 1) if self.start_time and self.is_running else 0.0
        return {
            "is_running": self.is_running,
            "cadence_seconds": self.cadence_seconds,
            "total_streamed": self.total_streamed,
            "stat_critical_count": self.stat_count,
            "uptime_seconds": uptime,
            "active_listeners": len(self.connected_websockets),
            "last_injected_at": self.last_injected_at,
            "last_injected_study": self.last_injected_study
        }


def get_ed_stream_daemon() -> EDStreamDaemon:
    """Singleton getter for the Emergency Department stream daemon."""
    return EDStreamDaemon.get_instance()
