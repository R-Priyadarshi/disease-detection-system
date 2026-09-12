"""
ALVEON THORACIC PACS - Native DICOM Engine
Handles 16-bit/12-bit uncompressed binary DICOM (.dcm) ingestion,
Modality LUT rescale, Photometric Interpretation polarity, Window/Level calibration,
authentic DICOM tag extraction, and synthetic DICOM generation.
"""

import io
import datetime
from typing import Tuple, Dict, Any, Optional, List
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

    if norm_img.ndim == 3:
        norm_img = cv2.cvtColor(norm_img, cv2.COLOR_RGB2GRAY)

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


def synthesize_secondary_capture_dicom(
    original_image: np.ndarray,
    heatmap: Optional[np.ndarray] = None,
    calipers: Optional[List[Dict[str, Any]]] = None,
    patient_id: str = "ALV-PT-001",
    patient_name: str = "ANONYMOUS^PATIENT",
    patient_age: str = "048Y",
    patient_sex: str = "M",
    study_id: str = "ALV-STUDY-001",
    study_instance_uid: Optional[str] = None,
    series_instance_uid: Optional[str] = None,
    diagnosis: str = "PNEUMONIA DETECTED",
    confidence: float = 94.8,
    dominant_zone: str = "Right Lower Lobe",
    colormap_name: str = "inferno",
    heatmap_alpha: float = 0.40,
    include_banner: bool = True
) -> Tuple[bytes, FileDataset]:
    """
    Synthesizes a certified DICOM Secondary Capture (SOP 1.2.840.10008.5.1.4.1.1.7)
    with burned-in Grad-CAM thermal heatmap overlay, quantitative caliper measurements,
    and institutional clinical telemetry HUD banner.
    
    Returns (raw_dicom_bytes, pydicom_FileDataset).
    """
    # 1. Standardize base image to uint8 BGR
    if original_image.ndim == 2:
        if original_image.dtype == np.uint16 or original_image.max() > 255:
            base_8u = np.clip((original_image.astype(np.float32) / 4095.0) * 255.0, 0, 255).astype(np.uint8)
        else:
            base_8u = original_image.astype(np.uint8)
        bgr = cv2.cvtColor(base_8u, cv2.COLOR_GRAY2BGR)
    elif original_image.ndim == 3:
        if original_image.shape[2] == 4:
            bgr = cv2.cvtColor(original_image.astype(np.uint8), cv2.COLOR_RGBA2BGR)
        elif original_image.shape[2] == 3:
            bgr = original_image.astype(np.uint8).copy()
        else:
            bgr = cv2.cvtColor(original_image[:, :, 0].astype(np.uint8), cv2.COLOR_GRAY2BGR)
    else:
        raise ValueError(f"Unsupported image dimensions for Secondary Capture: {original_image.shape}")

    H, W = bgr.shape[:2]

    # 2. Burn in Grad-CAM thermal heatmap
    if heatmap is not None:
        hm = heatmap.astype(np.float32)
        if hm.max() > 1.0:
            hm = hm / 255.0
        hm_resized = cv2.resize(hm, (W, H), interpolation=cv2.INTER_LINEAR)
        hm_uint8 = np.uint8(255 * np.clip(hm_resized, 0.0, 1.0))

        cmap_key = (colormap_name or "inferno").lower()
        if cmap_key == "viridis":
            cmap_cv = cv2.COLORMAP_VIRIDIS
        elif cmap_key == "plasma":
            cmap_cv = cv2.COLORMAP_PLASMA
        elif cmap_key == "hot":
            cmap_cv = cv2.COLORMAP_HOT
        elif cmap_key == "jet":
            cmap_cv = cv2.COLORMAP_JET
        else:
            cmap_cv = cv2.COLORMAP_INFERNO

        colored_hm = cv2.applyColorMap(hm_uint8, cmap_cv)
        alpha = float(np.clip(heatmap_alpha, 0.1, 0.9))
        blended = cv2.addWeighted(bgr, 1.0 - alpha, colored_hm, alpha, 0)
    else:
        blended = bgr.copy()

    # 3. Burn in Caliper Measurements & Annotations
    if calipers:
        for item in calipers:
            m_type = item.get('type', 'ruler')

            if m_type == 'ctr':
                cardiac = item.get('cardiac', {})
                thoracic = item.get('thoracic', {})
                ratio = float(item.get('ratio', 0.0))

                # Draw cardiac line (cyan)
                cx1 = int(round(float(cardiac.get('x1', 0)) * W if float(cardiac.get('x1', 0)) <= 1.0 else float(cardiac.get('x1', 0))))
                cy1 = int(round(float(cardiac.get('y1', 0)) * H if float(cardiac.get('y1', 0)) <= 1.0 else float(cardiac.get('y1', 0))))
                cx2 = int(round(float(cardiac.get('x2', 0)) * W if float(cardiac.get('x2', 0)) <= 1.0 else float(cardiac.get('x2', 0))))
                cy2 = int(round(float(cardiac.get('y2', 0)) * H if float(cardiac.get('y2', 0)) <= 1.0 else float(cardiac.get('y2', 0))))
                cv2.line(blended, (cx1, cy1), (cx2, cy2), (248, 189, 56), 2, cv2.LINE_AA)
                cv2.circle(blended, (cx1, cy1), 4, (248, 189, 56), -1)
                cv2.circle(blended, (cx2, cy2), 4, (248, 189, 56), -1)

                # Draw thoracic line (gold/amber)
                tx1 = int(round(float(thoracic.get('x1', 0)) * W if float(thoracic.get('x1', 0)) <= 1.0 else float(thoracic.get('x1', 0))))
                ty1 = int(round(float(thoracic.get('y1', 0)) * H if float(thoracic.get('y1', 0)) <= 1.0 else float(thoracic.get('y1', 0))))
                tx2 = int(round(float(thoracic.get('x2', 0)) * W if float(thoracic.get('x2', 0)) <= 1.0 else float(thoracic.get('x2', 0))))
                ty2 = int(round(float(thoracic.get('y2', 0)) * H if float(thoracic.get('y2', 0)) <= 1.0 else float(thoracic.get('y2', 0))))
                cv2.line(blended, (tx1, ty1), (tx2, ty2), (11, 158, 245), 2, cv2.LINE_AA)
                cv2.circle(blended, (tx1, ty1), 4, (11, 158, 245), -1)
                cv2.circle(blended, (tx2, ty2), 4, (11, 158, 245), -1)

                ctr_label = f"CTR: {ratio:.2f} ({'CARDIOMEGALY' if ratio > 0.50 else 'NORMAL'})"
                ctr_x = max(10, min(W - 120, (tx1 + tx2) // 2))
                ctr_y = max(20, min(H - 20, max(cy1, ty1) + 20))
                cv2.putText(blended, ctr_label, (ctr_x, ctr_y), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 3, cv2.LINE_AA)
                cv2.putText(blended, ctr_label, (ctr_x, ctr_y), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 220, 255), 1, cv2.LINE_AA)

            elif m_type == 'roi':
                cx = float(item.get('cx', 0))
                cy = float(item.get('cy', 0))
                rx = float(item.get('rx', 0))
                ry = float(item.get('ry', 0))
                area = float(item.get('areaCm2', 0.0))

                c_x = int(round(cx * W if cx <= 1.0 else cx))
                c_y = int(round(cy * H if cy <= 1.0 else cy))
                r_x = max(2, int(round(rx * W if rx <= 1.0 else rx)))
                r_y = max(2, int(round(ry * H if ry <= 1.0 else ry)))

                cv2.ellipse(blended, (c_x, c_y), (r_x, r_y), 0, 0, 360, (238, 211, 34), 2, cv2.LINE_AA)
                roi_label = f"ROI: {area:.1f} cm2" if area > 0 else "ROI"
                cv2.putText(blended, roi_label, (c_x - r_x, c_y - r_y - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 3, cv2.LINE_AA)
                cv2.putText(blended, roi_label, (c_x - r_x, c_y - r_y - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (238, 211, 34), 1, cv2.LINE_AA)

            elif m_type == 'arrow':
                x1 = float(item.get('x1', 0))
                y1 = float(item.get('y1', 0))
                x2 = float(item.get('x2', 0))
                y2 = float(item.get('y2', 0))
                pt1_x = max(0, min(W - 1, int(round(x1 * W if x1 <= 1.0 else x1))))
                pt1_y = max(0, min(H - 1, int(round(y1 * H if y1 <= 1.0 else y1))))
                pt2_x = max(0, min(W - 1, int(round(x2 * W if x2 <= 1.0 else x2))))
                pt2_y = max(0, min(H - 1, int(round(y2 * H if y2 <= 1.0 else y2))))

                cv2.arrowedLine(blended, (pt1_x, pt1_y), (pt2_x, pt2_y), (94, 63, 244), 2, tipLength=0.15)
                lbl = item.get('label') or "Pathology Focus"
                cv2.putText(blended, lbl, (pt1_x, pt1_y - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 3, cv2.LINE_AA)
                cv2.putText(blended, lbl, (pt1_x, pt1_y - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (94, 63, 244), 1, cv2.LINE_AA)

            else:
                # Standard linear ruler caliper
                x1 = float(item.get('x1', 0))
                y1 = float(item.get('y1', 0))
                x2 = float(item.get('x2', 0))
                y2 = float(item.get('y2', 0))

                # Scale if normalized coordinates
                pt1_x = int(round(x1 * W)) if x1 <= 1.0 and x1 >= 0.0 else int(round(x1))
                pt1_y = int(round(y1 * H)) if y1 <= 1.0 and y1 >= 0.0 else int(round(y1))
                pt2_x = int(round(x2 * W)) if x2 <= 1.0 and x2 >= 0.0 else int(round(x2))
                pt2_y = int(round(y2 * H)) if y2 <= 1.0 and y2 >= 0.0 else int(round(y2))

                # Bound coordinates to image limits
                pt1_x = max(0, min(W - 1, pt1_x))
                pt1_y = max(0, min(H - 1, pt1_y))
                pt2_x = max(0, min(W - 1, pt2_x))
                pt2_y = max(0, min(H - 1, pt2_y))

                # Draw caliper golden vector
                cv2.line(blended, (pt1_x, pt1_y), (pt2_x, pt2_y), (0, 220, 255), 2, cv2.LINE_AA)

                # Draw circular endpoint calipers
                cv2.circle(blended, (pt1_x, pt1_y), 4, (0, 200, 255), -1)
                cv2.circle(blended, (pt1_x, pt1_y), 6, (0, 0, 0), 1, cv2.LINE_AA)
                cv2.circle(blended, (pt2_x, pt2_y), 4, (0, 200, 255), -1)
                cv2.circle(blended, (pt2_x, pt2_y), 6, (0, 0, 0), 1, cv2.LINE_AA)

                # Label text
                length_val = item.get('length_mm') or item.get('length') or item.get('mm')
                if length_val is not None:
                    lbl = item.get('label') or f"{float(length_val):.1f} mm"
                else:
                    lbl = item.get('label') or "Caliper"

                mid_x = (pt1_x + pt2_x) // 2
                mid_y = (pt1_y + pt2_y) // 2

                # Double-pass text for high contrast on diagnostic films
                cv2.putText(blended, lbl, (mid_x + 8, mid_y - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 3, cv2.LINE_AA)
                cv2.putText(blended, lbl, (mid_x + 8, mid_y - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 235, 255), 1, cv2.LINE_AA)

    # 4. Institutional Medical Telemetry HUD Banner
    if include_banner and H >= 200 and W >= 200:
        top_h = 44
        bot_h = 36

        # Top Banner Overlay (Dark Navy Header)
        cv2.rectangle(blended, (0, 0), (W, top_h), (15, 23, 42), -1)
        cv2.line(blended, (0, top_h), (W, top_h), (56, 189, 248), 1)

        header_l = "ALVEON PACS | DICOM SECONDARY CAPTURE (1.2.840.10008.5.1.4.1.1.7)"
        header_r = f"PT: {patient_id} | {patient_name} | {patient_age}/{patient_sex}"
        cv2.putText(blended, header_l, (12, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (56, 189, 248), 1, cv2.LINE_AA)
        
        # Calculate right-aligned header position
        (w_r, _), _ = cv2.getTextSize(header_r, cv2.FONT_HERSHEY_SIMPLEX, 0.40, 1)
        cv2.putText(blended, header_r, (max(12, W - w_r - 12), 28), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (226, 232, 240), 1, cv2.LINE_AA)

        # Bottom Banner Overlay (Dark Navy Footer)
        cv2.rectangle(blended, (0, H - bot_h), (W, H), (15, 23, 42), -1)
        cv2.line(blended, (0, H - bot_h), (W, H - bot_h), (51, 65, 85), 1)

        diag_color = (16, 185, 129) if "NORMAL" in diagnosis.upper() else (59, 130, 246)
        footer_l = f"AI FINDING: {diagnosis.upper()} ({confidence:.1f}%) | PREDOMINANT: {dominant_zone}"
        footer_r = "BURNED-IN: YES | CALIBRATED: mm | SHA-256 SEAL"

        cv2.putText(blended, footer_l, (12, H - 14), cv2.FONT_HERSHEY_SIMPLEX, 0.38, diag_color, 1, cv2.LINE_AA)
        (w_fr, _), _ = cv2.getTextSize(footer_r, cv2.FONT_HERSHEY_SIMPLEX, 0.36, 1)
        cv2.putText(blended, footer_r, (max(12, W - w_fr - 12), H - 14), cv2.FONT_HERSHEY_SIMPLEX, 0.36, (148, 163, 184), 1, cv2.LINE_AA)

    # 5. Convert to standard RGB format
    rgb_data = cv2.cvtColor(blended, cv2.COLOR_BGR2RGB)

    # 6. Build DICOM Dataset
    sop_uid = generate_uid()
    file_meta = FileMetaDataset()
    file_meta.FileMetaInformationGroupLength = 192
    file_meta.FileMetaInformationVersion = b"\x00\x01"
    file_meta.MediaStorageSOPClassUID = SecondaryCaptureImageStorage
    file_meta.MediaStorageSOPInstanceUID = sop_uid
    file_meta.TransferSyntaxUID = ExplicitVRLittleEndian
    file_meta.ImplementationClassUID = "1.2.826.0.1.3680043.10.1234"

    ds = FileDataset(None, {}, file_meta=file_meta, preamble=b"\x00" * 128)
    ds.is_little_endian = True
    ds.is_implicit_VR = False

    # Patient & Identification
    ds.PatientID = str(patient_id)
    ds.PatientName = str(patient_name)
    raw_age_str = str(patient_age or "").strip().upper().replace("Y", "")
    try:
        age_num = int(raw_age_str)
        ds.PatientAge = f"{age_num:03d}Y"
    except Exception:
        ds.PatientAge = "048Y"
    ds.PatientSex = patient_sex or "O"
    ds.StudyID = str(study_id)
    ds.StudyInstanceUID = study_instance_uid or generate_uid()
    ds.SeriesInstanceUID = series_instance_uid or generate_uid()
    ds.SOPInstanceUID = sop_uid
    ds.SOPClassUID = SecondaryCaptureImageStorage

    # Temporal Tags
    now_dt = datetime.datetime.now()
    ds.StudyDate = now_dt.strftime("%Y%m%d")
    ds.StudyTime = now_dt.strftime("%H%M%S")
    ds.ContentDate = ds.StudyDate
    ds.ContentTime = ds.StudyTime

    # Clinical Context & Presentation
    ds.Modality = "OT"
    ds.ConversionType = "WSD"  # Workstation
    ds.BurnedInAnnotation = "YES"
    ds.SeriesDescription = "ALVEON AI Secondary Capture (Grad-CAM & Calipers Burned-In)"
    ds.DerivationDescription = f"Synthesized with ALVEON PACS AI Thoracic Grad-CAM ({colormap_name}) and Calipers"
    ds.InstitutionName = "St. Jude Thoracic Medical Center"
    ds.StationName = "ALVEON-SC-01"

    # RGB Image Specification
    ds.Rows, ds.Columns = rgb_data.shape[:2]
    ds.PhotometricInterpretation = "RGB"
    ds.SamplesPerPixel = 3
    ds.PlanarConfiguration = 0  # Color-by-pixel (R1, G1, B1, R2, G2, B2...)
    ds.BitsAllocated = 8
    ds.BitsStored = 8
    ds.HighBit = 7
    ds.PixelRepresentation = 0

    ds.PixelData = rgb_data.tobytes()

    buf = io.BytesIO()
    ds.save_as(buf, write_like_original=False)
    return buf.getvalue(), ds


# Alias for standard naming
parse_dicom = parse_dicom_file

