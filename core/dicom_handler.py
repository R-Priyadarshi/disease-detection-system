"""
ALVEON THORACIC PACS - Native DICOM Engine
Handles 16-bit/12-bit uncompressed binary DICOM (.dcm) ingestion,
Modality LUT rescale, Photometric Interpretation polarity, Window/Level calibration,
authentic DICOM tag extraction, and synthetic DICOM generation.
"""

import io
from typing import Tuple, Dict, Any, Optional
import numpy as np
import cv2
import pydicom
from pydicom.dataset import Dataset, FileDataset, FileMetaDataset
from pydicom.uid import ExplicitVRLittleEndian, SecondaryCaptureImageStorage, generate_uid

DICOM_PREAMBLE_PREFIX = b"DICM"

def is_dicom_bytes(data: bytes) -> bool:
    """Checks if raw byte stream contains standard DICOM preamble or signature."""
    if len(data) >= 132 and data[128:132] == DICOM_PREAMBLE_PREFIX:
        return True
    try:
        pydicom.dcmread(io.BytesIO(data), stop_before_pixels=True)
        return True
    except Exception:
        return False

def parse_dicom_file(data: bytes) -> Tuple[np.ndarray, Dict[str, Any]]:
    """
    Parses binary DICOM bytes, extracts calibrated 8-bit image for neural processing,
    and returns a comprehensive dictionary of authentic clinical DICOM tags.
    """
    ds = pydicom.dcmread(io.BytesIO(data), force=True)

    # 1. Extract raw pixel array
    try:
        pixel_array = ds.pixel_array.astype(np.float32)
    except Exception as e:
        raise ValueError(f"Could not decompress DICOM pixel array: {str(e)}")

    # 2. Apply Rescale Slope & Intercept if present (Modality LUT)
    slope = float(getattr(ds, "RescaleSlope", 1.0))
    intercept = float(getattr(ds, "RescaleIntercept", 0.0))
    pixel_array = pixel_array * slope + intercept

    # 3. Handle Photometric Interpretation Polarity
    # MONOCHROME1: 0 is white, max is black (older fluoroscopy/film convention).
    # Standard radiologic convention (MONOCHROME2): 0 is black, max is white (air is dark, bone is light).
    photometric = str(getattr(ds, "PhotometricInterpretation", "MONOCHROME2")).strip().upper()
    if photometric == "MONOCHROME1":
        pixel_array = np.max(pixel_array) - pixel_array

    # 4. Window/Level Contrast Calibration
    wc = getattr(ds, "WindowCenter", None)
    ww = getattr(ds, "WindowWidth", None)

    if isinstance(wc, (list, pydicom.multival.MultiValue)):
        wc = float(wc[0])
    elif wc is not None:
        try:
            wc = float(wc)
        except Exception:
            wc = None

    if isinstance(ww, (list, pydicom.multival.MultiValue)):
        ww = float(ww[0])
    elif ww is not None:
        try:
            ww = float(ww)
        except Exception:
            ww = None

    if wc is not None and ww is not None and ww > 0:
        # Linear Window/Level transformation
        lower = wc - (ww / 2.0)
        upper = wc + (ww / 2.0)
        clipped = np.clip(pixel_array, lower, upper)
        norm_img = ((clipped - lower) / (upper - lower) * 255.0).astype(np.uint8)
    else:
        # Robust min-max percentile contrast stretch
        p_min, p_max = np.percentile(pixel_array, (0.5, 99.5))
        if p_max - p_min > 1e-4:
            clipped = np.clip(pixel_array, p_min, p_max)
            norm_img = ((clipped - p_min) / (p_max - p_min) * 255.0).astype(np.uint8)
        else:
            norm_img = np.zeros_like(pixel_array, dtype=np.uint8)

    # 5. Extract Authentic Clinical DICOM Tags
    all_tags = []
    for elem in ds:
        if elem.tag == 0x7FE00010:  # Skip binary pixel data payload
            continue
        try:
            val_str = str(elem.value)
            if len(val_str) > 64:
                val_str = val_str[:61] + "..."
            all_tags.append({
                "tag": f"({elem.tag.group:04X},{elem.tag.element:04X})",
                "vr": str(elem.VR),
                "name": str(elem.name),
                "value": val_str
            })
        except Exception:
            continue

    metadata: Dict[str, Any] = {
        "is_dicom": True,
        "patient_id": str(getattr(ds, "PatientID", "ALV-UNKNOWN")),
        "patient_name": str(getattr(ds, "PatientName", "Anonymous Patient")),
        "patient_age": str(getattr(ds, "PatientAge", "54Y")),
        "patient_sex": str(getattr(ds, "PatientSex", "O")),
        "study_date": str(getattr(ds, "StudyDate", "20260910")),
        "study_time": str(getattr(ds, "StudyTime", "120000")),
        "modality": str(getattr(ds, "Modality", "CR")),
        "body_part_examined": str(getattr(ds, "BodyPartExamined", "CHEST")),
        "view_position": str(getattr(ds, "ViewPosition", "PA")),
        "kvp": f"{getattr(ds, 'KVP', 120)} kVp",
        "exposure_time": f"{getattr(ds, 'ExposureTime', 12)} ms",
        "tube_current": f"{getattr(ds, 'XRayTubeCurrent', 250)} mA",
        "institution_name": str(getattr(ds, "InstitutionName", "ALVEON Memorial Radiology PACS")),
        "station_name": str(getattr(ds, "StationName", "WORKSTATION-01")),
        "photometric_interpretation": photometric,
        "window_center": int(wc) if wc is not None else 128,
        "window_width": int(ww) if ww is not None else 256,
        "rows": int(getattr(ds, "Rows", norm_img.shape[0])),
        "columns": int(getattr(ds, "Columns", norm_img.shape[1])),
        "bits_allocated": int(getattr(ds, "BitsAllocated", 16)),
        "bits_stored": int(getattr(ds, "BitsStored", 12)),
        "transfer_syntax_uid": str(getattr(ds.file_meta, "TransferSyntaxUID", "1.2.840.10008.1.2.1")) if hasattr(ds, "file_meta") else "1.2.840.10008.1.2.1",
        "sop_instance_uid": str(getattr(ds, "SOPInstanceUID", generate_uid())),
        "all_tags": all_tags
    }

    return norm_img, metadata

def create_synthetic_dicom(
    pixel_array: np.ndarray,
    patient_id: str = "ALV-STAT-01",
    patient_name: str = "VANCE^ELEANOR",
    patient_age: str = "048Y",
    patient_sex: str = "F",
    institution: str = "St. Jude Thoracic Medical Center",
    view_position: str = "PA",
    kvp: float = 125.0,
    exposure_time: int = 14,
    photometric: str = "MONOCHROME2",
    bits_allocated: int = 16
) -> bytes:
    """
    Synthesizes a compliant binary DICOM (.dcm) file with proper File Meta Information,
    16-bit pixel data, and full clinical header tags.
    """
    file_meta = FileMetaDataset()
    file_meta.FileMetaInformationGroupLength = 192
    file_meta.FileMetaInformationVersion = b"\x00\x01"
    file_meta.MediaStorageSOPClassUID = SecondaryCaptureImageStorage
    file_meta.MediaStorageSOPInstanceUID = generate_uid()
    file_meta.TransferSyntaxUID = ExplicitVRLittleEndian
    file_meta.ImplementationClassUID = "1.2.826.0.1.3680043.10.1234"

    # Scale 8-bit radiograph phantom into 16-bit DICOM dynamic range
    if pixel_array.dtype != np.uint16:
        scaled_16bit = (pixel_array.astype(np.float32) / 255.0 * 4095.0).astype(np.uint16)
    else:
        scaled_16bit = pixel_array

    ds = FileDataset(None, {}, file_meta=file_meta, preamble=b"\x00" * 128)
    ds.is_little_endian = True
    ds.is_implicit_VR = False

    # Patient & Institutional Tags
    ds.PatientID = patient_id
    ds.PatientName = patient_name
    ds.PatientAge = patient_age if len(patient_age) == 4 else "048Y"
    ds.PatientSex = patient_sex
    ds.StudyDate = "20260910"
    ds.StudyTime = "143000"
    ds.Modality = "DX"
    ds.BodyPartExamined = "CHEST"
    ds.ViewPosition = view_position
    ds.KVP = kvp
    ds.ExposureTime = exposure_time
    ds.XRayTubeCurrent = 300
    ds.InstitutionName = institution
    ds.StationName = "STAT-PACS-01"

    # Image Geometry & Presentation Tags
    ds.Rows, ds.Columns = scaled_16bit.shape[:2]
    ds.PhotometricInterpretation = photometric
    ds.SamplesPerPixel = 1
    ds.BitsAllocated = bits_allocated
    ds.BitsStored = 12 if bits_allocated == 16 else 8
    ds.HighBit = 11 if bits_allocated == 16 else 7
    ds.PixelRepresentation = 0
    ds.WindowCenter = 2048 if bits_allocated == 16 else 128
    ds.WindowWidth = 4096 if bits_allocated == 16 else 256
    ds.RescaleIntercept = 0
    ds.RescaleSlope = 1

    ds.SOPClassUID = SecondaryCaptureImageStorage
    ds.SOPInstanceUID = file_meta.MediaStorageSOPInstanceUID

    ds.PixelData = scaled_16bit.tobytes()

    buf = io.BytesIO()
    ds.save_as(buf, write_like_original=False)
    return buf.getvalue()

# Alias for standard naming
parse_dicom = parse_dicom_file
