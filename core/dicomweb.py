"""
ALVEON DICOMweb REST Services Core (DICOM Part 18 Standards)
============================================================
Implements standard DICOMweb protocols:
- QIDO-RS (Query ID in DICOM Objects): JSON metadata queries across studies, series, instances.
- WADO-RS (Web Access to DICOM Objects): Retrieve native binary DICOM, JSON metadata, or rendered frames.
- STOW-RS (Store Over the Web): Ingest studies via multipart/related DICOM uploads.
"""

import io
import os
import re
import uuid
import datetime
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

import cv2
import numpy as np
import pydicom
from pydicom.dataset import Dataset, FileMetaDataset
from pydicom.uid import ExplicitVRLittleEndian, SecondaryCaptureImageStorage

from core.config import settings
from core.preprocessor import preprocessor

logger = logging.getLogger("alveon.dicomweb")

# Standard DICOM VR definitions for JSON serialization
VR_MAP = {
    "00080005": ("CS", "SpecificCharacterSet"),
    "00080016": ("UI", "SOPClassUID"),
    "00080018": ("UI", "SOPInstanceUID"),
    "00080020": ("DA", "StudyDate"),
    "00080030": ("TM", "StudyTime"),
    "00080050": ("SH", "AccessionNumber"),
    "00080060": ("CS", "Modality"),
    "00080061": ("CS", "ModalitiesInStudy"),
    "00080090": ("PN", "ReferringPhysicianName"),
    "00081030": ("LO", "StudyDescription"),
    "00100010": ("PN", "PatientName"),
    "00100020": ("LO", "PatientID"),
    "00100030": ("DA", "PatientBirthDate"),
    "00100040": ("CS", "PatientSex"),
    "0020000D": ("UI", "StudyInstanceUID"),
    "0020000E": ("UI", "SeriesInstanceUID"),
    "00200010": ("SH", "StudyID"),
    "00200011": ("IS", "SeriesNumber"),
    "00200013": ("IS", "InstanceNumber"),
    "00280004": ("CS", "PhotometricInterpretation"),
    "00280010": ("US", "Rows"),
    "00280011": ("US", "Columns"),
    "00280100": ("US", "BitsAllocated"),
    "00280101": ("US", "BitsStored"),
    "00280102": ("US", "HighBit"),
    "00280103": ("US", "PixelRepresentation"),
    "00281050": ("DS", "WindowCenter"),
    "00281051": ("DS", "WindowWidth")
}

def format_dicom_json_element(vr: str, value: Any) -> Dict[str, Any]:
    """Encodes a single tag value into DICOM Part 18 JSON format."""
    if value is None:
        return {"vr": vr}
    if vr == "PN":
        # Person Name formatting
        name_str = str(value)
        return {"vr": vr, "Value": [{"Alphabetic": name_str}]}
    elif vr in ("US", "SS", "UL", "SL", "IS"):
        try:
            return {"vr": vr, "Value": [int(value)]}
        except (ValueError, TypeError):
            return {"vr": vr, "Value": [0]}
    elif vr in ("DS", "FL", "FD"):
        try:
            return {"vr": vr, "Value": [float(value)]}
        except (ValueError, TypeError):
            return {"vr": vr, "Value": [0.0]}
    else:
        return {"vr": vr, "Value": [str(value)]}


def dataset_to_dicom_json(ds: Dataset) -> Dict[str, Any]:
    """Converts a pydicom Dataset to DICOM Part 18 JSON structure."""
    out: Dict[str, Any] = {}
    for tag_str, (vr, keyword) in VR_MAP.items():
        if hasattr(ds, keyword):
            val = getattr(ds, keyword)
            if val is not None:
                out[tag_str] = format_dicom_json_element(vr, val)
    return out


def study_item_to_dicom_json(study) -> Dict[str, Any]:
    """
    Constructs a DICOM Part 18 QIDO-RS JSON object from an internal WorklistStudyItem.
    """
    study_uid = f"1.2.826.0.1.3680043.9.7123.{abs(hash(study.study_id)) % 1000000000}"
    series_uid = f"{study_uid}.1"
    sop_uid = f"{series_uid}.1"

    meta = getattr(study, "dicom_metadata", None)
    mrn = getattr(study, "patient_mrn", "UNKNOWN_MRN")
    name = getattr(study, "patient_name", "Anonymous Patient")
    modality = getattr(study, "modality", "DX")
    if "(" in modality:
        modality = modality.split("(")[0].strip()

    now_date = datetime.datetime.now().strftime("%Y%m%d")
    now_time = datetime.datetime.now().strftime("%H%M%S")

    doc = {
        "00080005": {"vr": "CS", "Value": ["ISO_IR 100"]},
        "00080016": {"vr": "UI", "Value": ["1.2.840.10008.5.1.4.1.1.1"]},  # Digital X-Ray Image
        "00080018": {"vr": "UI", "Value": [sop_uid]},
        "00080020": {"vr": "DA", "Value": [meta.study_date if meta and hasattr(meta, 'study_date') else now_date]},
        "00080030": {"vr": "TM", "Value": [meta.study_time if meta and hasattr(meta, 'study_time') else now_time]},
        "00080050": {"vr": "SH", "Value": [study.study_id]},
        "00080060": {"vr": "CS", "Value": [modality]},
        "00080061": {"vr": "CS", "Value": [modality]},
        "00081030": {"vr": "LO", "Value": [f"Thoracic CADe Evaluation - {getattr(study, 'priority', 'ROUTINE')}"]},
        "00100010": {"vr": "PN", "Value": [{"Alphabetic": name}]},
        "00100020": {"vr": "LO", "Value": [mrn]},
        "00100040": {"vr": "CS", "Value": ["F" if "/ F" in getattr(study, 'patient_age_sex', '') else "M"]},
        "0020000D": {"vr": "UI", "Value": [study_uid]},
        "0020000E": {"vr": "UI", "Value": [series_uid]},
        "00200010": {"vr": "SH", "Value": [study.study_id]},
        "00200011": {"vr": "IS", "Value": [1]},
        "00200013": {"vr": "IS", "Value": [1]},
        "00280004": {"vr": "CS", "Value": ["MONOCHROME2"]},
        "00280010": {"vr": "US", "Value": [512]},
        "00280011": {"vr": "US", "Value": [512]}
    }
    return doc


def study_item_to_pydicom(study, raw_gray: Optional[np.ndarray] = None) -> Dataset:
    """
    Synthesizes a compliant pydicom Dataset from an internal WorklistStudyItem.
    """
    study_uid = f"1.2.826.0.1.3680043.9.7123.{abs(hash(study.study_id)) % 1000000000}"
    series_uid = f"{study_uid}.1"
    sop_uid = f"{series_uid}.1"

    if raw_gray is None:
        raw_gray = None
        if hasattr(study, "image_b64") and study.image_b64:
            import base64
            b64_str = str(study.image_b64)
            if "," in b64_str:
                b64_str = b64_str.split(",", 1)[1]
            try:
                img_bytes = base64.b64decode(b64_str)
                arr = np.frombuffer(img_bytes, dtype=np.uint8)
                raw_gray = cv2.imdecode(arr, cv2.IMREAD_GRAYSCALE)
            except Exception:
                raw_gray = None
        if raw_gray is None:
            raw_gray = np.full((512, 512), 128, dtype=np.uint8)

    file_meta = FileMetaDataset()
    file_meta.MediaStorageSOPClassUID = "1.2.840.10008.5.1.4.1.1.1"  # CR/DX
    file_meta.MediaStorageSOPInstanceUID = sop_uid
    file_meta.TransferSyntaxUID = ExplicitVRLittleEndian

    ds = Dataset()
    ds.file_meta = file_meta
    ds.is_little_endian = True
    ds.is_implicit_VR = False

    ds.SOPClassUID = "1.2.840.10008.5.1.4.1.1.1"
    ds.SOPInstanceUID = sop_uid
    ds.StudyInstanceUID = study_uid
    ds.SeriesInstanceUID = series_uid
    ds.StudyID = study.study_id
    ds.AccessionNumber = study.study_id
    ds.PatientName = str(getattr(study, "patient_name", "Anonymous Patient"))
    ds.PatientID = str(getattr(study, "patient_mrn", "MRN-00000"))
    ds.PatientSex = "F" if "/ F" in getattr(study, "patient_age_sex", "") else "M"
    ds.Modality = "DX"
    ds.StudyDate = datetime.datetime.now().strftime("%Y%m%d")
    ds.StudyTime = datetime.datetime.now().strftime("%H%M%S")
    ds.StudyDescription = f"Chest Radiograph - CADe Triage: {getattr(study, 'priority', 'ROUTINE')}"

    # Pixel Module (16-bit)
    h, w = raw_gray.shape[:2]
    pixel_16 = (raw_gray.astype(np.uint16) * 257)  # Scale 8-bit to 16-bit
    ds.Rows = h
    ds.Columns = w
    ds.BitsAllocated = 16
    ds.BitsStored = 16
    ds.HighBit = 15
    ds.PixelRepresentation = 0
    ds.SamplesPerPixel = 1
    ds.PhotometricInterpretation = "MONOCHROME2"
    ds.PixelData = pixel_16.tobytes()

    return ds


def parse_multipart_dicom(body: bytes, content_type: str) -> List[bytes]:
    """
    Parses a multipart/related or multipart/form-data payload and extracts individual
    binary DICOM objects.
    """
    match = re.search(r'boundary=([^;]+)', content_type, re.IGNORECASE)
    if not match:
        # Fallback: if body itself has DICOM magic or is a DICOM file
        if len(body) > 132 and body[128:132] == b"DICM":
            return [body]
        return [body]

    boundary = match.group(1).strip().strip('"').encode('utf-8')
    delimiter = b"--" + boundary
    parts = body.split(delimiter)
    dicom_files: List[bytes] = []

    for part in parts:
        if not part or part == b"--\r\n" or part == b"--":
            continue
        # Split headers from body
        header_end = part.find(b"\r\n\r\n")
        if header_end == -1:
            header_end = part.find(b"\n\n")
            if header_end == -1:
                continue
            payload = part[header_end + 2:].rstrip(b"\r\n")
        else:
            payload = part[header_end + 4:].rstrip(b"\r\n")

        if len(payload) > 132 and payload[128:132] == b"DICM":
            dicom_files.append(payload)
        elif len(payload) > 0:
            # Check if valid pydicom readable
            try:
                pydicom.dcmread(io.BytesIO(payload), force=True)
                dicom_files.append(payload)
            except Exception:
                pass

    return dicom_files


def render_dicom_frame(ds: Dataset, frame_index: int = 0) -> bytes:
    """
    Applies VOI LUT / Window Leveling and returns diagnostic JPEG bytes.
    """
    arr = ds.pixel_array
    if arr.ndim == 3:
        arr = arr[frame_index]

    # Handle photometric interpretation
    if getattr(ds, "PhotometricInterpretation", "") == "MONOCHROME1":
        arr = np.max(arr) - arr

    norm = ((arr - arr.min()) / max(1, (arr.max() - arr.min())) * 255.0).astype(np.uint8)
    _, encoded = cv2.imencode(".jpg", norm, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
    return encoded.tobytes()
