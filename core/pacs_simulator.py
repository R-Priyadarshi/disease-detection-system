"""
ALVEON Hospital Modality & VNA Network Simulator
Simulates emergency hospital acquisition modalities (Digital Radiography & Multi-Detector CT)
and Vendor-Neutral Archives (VNA). Performs automated C-STORE network transmissions over port 11112
and bi-directional C-FIND query matching.
"""

import time
import uuid
import io
import pydicom
import numpy as np
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from core.dicom_handler import create_synthetic_dicom
from core.pacs_client import get_pacs_client, ExternalPacsClient



class ModalityDevice(BaseModel):
    device_id: str
    ae_title: str
    modality_type: str  # XR or CT
    manufacturer: str
    model_name: str
    institution: str
    department: str
    ip_address: str
    port: int = 104


# Pre-configured simulated hospital imaging infrastructure
HOSPITAL_MODALITIES: Dict[str, ModalityDevice] = {
    "XR_EMERGENCY_BAY_1": ModalityDevice(
        device_id="MOD-XR-BAY1",
        ae_title="SIEMENS_LUMOS_XR",
        modality_type="XR",
        manufacturer="Siemens Healthineers",
        model_name="YSIO X.pree Digital Radiography",
        institution="St. Jude Metropolitan Medical Center",
        department="Emergency Trauma Center - Bay 1",
        ip_address="192.168.10.45",
        port=104
    ),
    "CT_TRAUMA_SCANNER_2": ModalityDevice(
        device_id="MOD-CT-SCAN2",
        ae_title="GE_REVOLUTION_CT",
        modality_type="CT",
        manufacturer="GE Healthcare",
        model_name="Revolution Apex Elite 256-Slice CT",
        institution="St. Jude Metropolitan Medical Center",
        department="Emergency Radiology Core",
        ip_address="192.168.10.60",
        port=104
    ),
    "ENTERPRISE_VNA_ARCHIVE": ModalityDevice(
        device_id="VNA-CENTRAL-01",
        ae_title="CENTRAL_HOSPITAL_VNA",
        modality_type="VNA",
        manufacturer="Sectra / Agfa HealthCare",
        model_name="Enterprise VNA Medical Repository",
        institution="Metropolitan Health System",
        department="Enterprise Medical Imaging",
        ip_address="10.200.5.12",
        port=11112
    )
}


class SimulatedStudy(BaseModel):
    accession_number: str
    patient_id: str
    patient_name: str
    modality: str
    study_description: str
    acuity_level: str
    pathology_type: str
    sensor_kvp: int
    exposure_time_ms: int


# Catalog of emergency cases ready for simulated hospital modality push
SIMULATED_STUDIES_CATALOG: List[SimulatedStudy] = [
    SimulatedStudy(
        accession_number="ACC-SIM-XR-9901",
        patient_id="MRN-TRAUMA-4410",
        patient_name="Sterling^Connor",
        modality="CR",
        study_description="STAT Chest AP Mobile (Trauma Resuscitation)",
        acuity_level="STAT CRITICAL",
        pathology_type="Pneumothorax / Tension Pleural Air",
        sensor_kvp=125,
        exposure_time_ms=12
    ),
    SimulatedStudy(
        accession_number="ACC-SIM-XR-9902",
        patient_id="MRN-RESP-5520",
        patient_name="Montgomery^Clara",
        modality="DX",
        study_description="Chest PA/Lateral (Acute Hypoxemic Respiratory Distress)",
        acuity_level="STAT CRITICAL",
        pathology_type="Multilobar Pneumonia",
        sensor_kvp=120,
        exposure_time_ms=14
    ),
    SimulatedStudy(
        accession_number="ACC-SIM-CT-9903",
        patient_id="MRN-CARD-6630",
        patient_name="Benton^Harold",
        modality="CT",
        study_description="CT Chest with IV Contrast (Rule out Pulmonary Embolism & Effusion)",
        acuity_level="URGENT",
        pathology_type="Pleural Effusion & Cardiomegaly",
        sensor_kvp=100,
        exposure_time_ms=500
    )
]


class PacsSimulatorEngine:
    """Orchestrates modality image generation and network push over port 11112."""

    _instance: Optional['PacsSimulatorEngine'] = None

    def __init__(self):
        self.client = get_pacs_client()

    @classmethod
    def get_instance(cls) -> 'PacsSimulatorEngine':
        if cls._instance is None:
            cls._instance = PacsSimulatorEngine()
        return cls._instance

    def list_modalities(self) -> List[ModalityDevice]:
        """Returns all simulated hospital imaging equipment."""
        return list(HOSPITAL_MODALITIES.values())

    def simulate_modality_transmission(
        self,
        modality_key: str,
        target_ae: str = "ALVEON_PACS",
        target_host: str = "127.0.0.1",
        target_port: int = 11112,
        study_idx: int = 0
    ) -> Dict[str, Any]:
        """
        Simulates an on-modality exam completion and automated DICOM C-STORE network push
        into ALVEON's Storage SCP node.
        """
        device = HOSPITAL_MODALITIES.get(modality_key, HOSPITAL_MODALITIES["XR_EMERGENCY_BAY_1"])
        idx = max(0, min(study_idx, len(SIMULATED_STUDIES_CATALOG) - 1))
        study_meta = SIMULATED_STUDIES_CATALOG[idx]

        # Generate synthetic pixel array calibrated to pathology
        np.random.seed(int(time.time() * 1000) % 10000)
        img_array = np.random.randint(2000, 4000, (512, 512), dtype=np.uint16)
        # Create lung field contrast
        y, x = np.ogrid[:512, :512]
        lung_mask = ((x - 170)**2 / 70**2 + (y - 250)**2 / 120**2 <= 1.0) | \
                    ((x - 340)**2 / 70**2 + (y - 250)**2 / 120**2 <= 1.0)
        img_array[lung_mask] = 1200  # Radiolucent

        if "Pneumothorax" in study_meta.pathology_type:
            # Apical hyperlucency
            img_array[50:180, 280:400] = 600
        elif "Pneumonia" in study_meta.pathology_type:
            # Opacification
            img_array[240:380, 100:230] = 3200

        # Construct true DICOM Part 10 dataset with simulated modality headers
        dcm_bytes = create_synthetic_dicom(
            pixel_array=img_array,
            patient_name=study_meta.patient_name,
            patient_id=study_meta.patient_id,
            institution=device.institution
        )
        dataset = pydicom.dcmread(io.BytesIO(dcm_bytes), force=True)
        dataset.StudyDescription = study_meta.study_description
        dataset.Modality = study_meta.modality
        dataset.AccessionNumber = study_meta.accession_number
        dataset.Manufacturer = device.manufacturer
        dataset.ManufacturerModelName = device.model_name
        dataset.InstitutionName = device.institution
        dataset.InstitutionalDepartmentName = device.department
        dataset.StationName = device.ae_title
        dataset.KVP = study_meta.sensor_kvp
        dataset.ExposureTime = study_meta.exposure_time_ms


        t0 = time.time()
        # Perform C-STORE push over socket
        push_res = self.client.push_study(
            dcm_input=dataset,
            host=target_host,
            port=target_port,
            remote_ae=target_ae
        )
        latency_ms = round((time.time() - t0) * 1000.0, 2)

        raw_code = push_res.get("dicom_status_code", "0x0000" if push_res.get("success") else "0xC000")
        if raw_code in ("0x0", "0x0000"):
            status_code = "0x0000"
        else:
            status_code = raw_code

        return {
            "success": push_res.get("success", False),
            "status_code": status_code,
            "modality_device": device.model_dump(),
            "study_transmitted": study_meta.model_dump(),
            "target_node": f"{target_ae}@{target_host}:{target_port}",
            "network_latency_ms": latency_ms,
            "sop_instance_uid": str(dataset.SOPInstanceUID),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S EST")
        }


def get_pacs_simulator() -> PacsSimulatorEngine:
    """Singleton getter for the PACS & Modality simulator."""
    return PacsSimulatorEngine.get_instance()
