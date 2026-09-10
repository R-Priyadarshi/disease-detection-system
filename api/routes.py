from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pathlib import Path
import numpy as np
import tensorflow as tf
import cv2
import uuid
import datetime
import hashlib
from typing import List, Dict, Any, Optional

from core.config import settings
from core.preprocessor import preprocessor, ImagePreprocessingError
from core.sample_generator import ensure_sample_assets
from core.dicom_handler import is_dicom_bytes, parse_dicom_file
from api.schemas import (
    PredictionResponse,
    HealthResponse,
    SamplesListResponse,
    SampleItem,
    ClinicalReportRequest,
    ClinicalReportResponse,
    AnatomicalZonation,
    DicomMetadataModel,
    WorklistResponse,
    WorklistStudyItem,
    BatchTriageResponse,
    SignoffRequest,
    SignoffResponse,
    BatchDeleteRequest,
    BatchDeleteResponse
)

from core.model import get_model, PneumoniaCNNModel
from core.gradcam import GradCAMGenerator

router = APIRouter()

# In-memory singletons and triage worklist cache
_model: Optional[PneumoniaCNNModel] = None
_gradcam: Optional[GradCAMGenerator] = None
_WORKLIST_CACHE: Optional[List[WorklistStudyItem]] = None

def get_engine():
    """Access or lazily initialize the preloaded model and Grad-CAM generator."""
    global _model, _gradcam
    if _model is None:
        _model = get_model()
        _gradcam = GradCAMGenerator(_model)
    return _model, _gradcam

@router.get("/health", response_model=HealthResponse, tags=["Diagnostics & System Health"])
async def healthcheck():
    """Returns engine diagnostics, hardware acceleration, and system status."""
    model, _ = get_engine()
    devices = tf.config.list_physical_devices('GPU')
    device_name = "GPU (Accelerated)" if len(devices) > 0 else "CPU (Optimized AVX2)"

    return HealthResponse(
        status="healthy",
        project_name=settings.PROJECT_NAME,
        system_title=settings.PROJECT_FULL_TITLE,
        version=settings.PROJECT_VERSION,
        model_loaded=(model.model is not None),
        tensorflow_version=tf.__version__,
        device=device_name
    )

@router.post("/api/v1/predict", response_model=PredictionResponse, tags=["Radiologic Classification"])
async def predict_chest_xray(
    file: UploadFile = File(..., description="Chest radiograph or binary DICOM (.dcm, .jpg, .png, .tif)"),
    apply_clahe: bool = Form(False, description="Apply CLAHE contrast enhancement for soft tissue visualization"),
    colormap: str = Form("inferno", description="Medical colormap: inferno (default), viridis, plasma, hot, jet"),
    heatmap_alpha: float = Form(0.45, description="Grad-CAM overlay blending opacity [0.1, 0.9]")
):
    """
    Evaluates a thoracic radiograph or native 16-bit DICOM file, executes forward neural pass,
    calculates pulmonary anatomical zonation, auto-extracts clinical DICOM tags,
    and synthesizes intensity-weighted Grad-CAM heatmaps.
    """
    model, gradcam = get_engine()

    valid_extensions = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff", ".dcm", ".dicom"}
    file_ext = Path(file.filename or "upload.jpg").suffix.lower()
    if file_ext not in valid_extensions and file.content_type and not (file.content_type.startswith("image/") or "dicom" in file.content_type):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format '{file_ext}'. Please upload standard radiographs or binary DICOM (.dcm)."
        )

    try:
        raw_bytes = await file.read()
        if len(raw_bytes) == 0:
            raise HTTPException(status_code=400, detail="Uploaded file buffer is empty.")

        # 1. Seamless DICOM or Standard Radiograph Ingestion
        raw_gray, dicom_meta = preprocessor.load_image_or_dicom(raw_bytes, filename=file.filename)

        # 2. Medical Preprocessing & Tensor Normalization
        if apply_clahe:
            proc_gray = preprocessor.apply_clahe(raw_gray)
        else:
            proc_gray = raw_gray

        resized = cv2.resize(proc_gray, (settings.INPUT_WIDTH, settings.INPUT_HEIGHT), interpolation=cv2.INTER_AREA)
        tensor = resized.reshape(1, settings.INPUT_HEIGHT, settings.INPUT_WIDTH, 1).astype(np.float32) / settings.NORMALIZATION_SCALE

        # 3. Forward Neural Classification
        inference_result = model.predict_tensor(tensor)

        # 4. Grad-CAM Synthesis with Anatomical Quadrant Zonation
        blended_bgr, heatmap_bgr, zonation = gradcam.generate_overlay(
            original_gray=proc_gray,
            tensor=tensor,
            colormap_name=colormap,
            alpha=float(np.clip(heatmap_alpha, 0.1, 0.9))
        )

        # 5. High-Efficiency Base64 Encodings
        orig_b64 = preprocessor.to_base64_jpeg(proc_gray)
        blended_b64 = preprocessor.to_base64_jpeg(blended_bgr)
        heatmap_b64 = preprocessor.to_base64_jpeg(heatmap_bgr)

        return PredictionResponse(
            filename=file.filename or "radiograph.dcm",
            diagnosis=inference_result["diagnosis"],
            is_pneumonia=inference_result["is_pneumonia"],
            probability=inference_result["probability"],
            confidence_percentage=inference_result["confidence_percentage"],
            risk_tier=inference_result["risk_tier"],
            clinical_recommendation=inference_result["clinical_recommendation"],
            latency_ms=inference_result["latency_ms"],
            colormap=colormap,
            zonation=AnatomicalZonation(**zonation),
            original_image_b64=orig_b64,
            gradcam_overlay_b64=blended_b64,
            gradcam_heatmap_b64=heatmap_b64,
            dicom_metadata=DicomMetadataModel(**dicom_meta)
        )

    except HTTPException:
        raise
    except ImagePreprocessingError as e:
        raise HTTPException(status_code=422, detail=f"Radiograph decoding failed: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Inference execution error: {str(e)}")

@router.get("/api/v1/worklist", response_model=WorklistResponse, tags=["Emergency Triage & Worklist"])
async def get_emergency_worklist():
    """
    Serves the live Emergency Department Triage Worklist, automatically sorted
    by clinical acuity with STAT / CRITICAL consolidation cases at the top.
    """
    global _WORKLIST_CACHE
    if _WORKLIST_CACHE is not None:
        stat_cnt = sum(1 for s in _WORKLIST_CACHE if s.priority == "STAT_CRITICAL")
        pend_cnt = sum(1 for s in _WORKLIST_CACHE if s.status == "PENDING")
        return WorklistResponse(
            total_cases=len(_WORKLIST_CACHE),
            stat_critical_count=stat_cnt,
            pending_count=pend_cnt,
            studies=_WORKLIST_CACHE
        )

    ensure_sample_assets()
    samples_dir = settings.SAMPLES_DIR
    model, gradcam = get_engine()

    # Define 5 realistic emergency patient cohort studies
    cohort_specs = [
        {
            "study_id": "ALV-STAT-09",
            "file": samples_dir / "sample_stat_pneumonia.dcm",
            "patient_mrn": "MRN-90214",
            "patient_name": "VANCE^ELEANOR",
            "patient_age_sex": "48Y / F",
            "study_time": "14:28 EST",
            "clinical_hx": "Sudden onset dyspnea, pyrexia 39.1C, productive rusty sputum.",
            "status": "PENDING",
            "modality": "DX (16-bit)"
        },
        {
            "study_id": "ALV-STAT-02",
            "file": samples_dir / "sample_pneumonia.jpg",
            "patient_mrn": "MRN-88410",
            "patient_name": "KOVACS^LASZLO",
            "patient_age_sex": "71Y / M",
            "study_time": "14:15 EST",
            "clinical_hx": "Post-fall hip pain, tachypneic in ER bay 4, O2 sat 88%.",
            "status": "PENDING",
            "modality": "CR"
        },
        {
            "study_id": "ALV-URG-15",
            "file": samples_dir / "sample_pneumonia.jpg",
            "patient_mrn": "MRN-72390",
            "patient_name": "PATEL^SUNITA",
            "patient_age_sex": "36Y / F",
            "study_time": "13:50 EST",
            "clinical_hx": "Persistent dry cough x 10 days, pleuritic left-sided pain.",
            "status": "PENDING",
            "modality": "CR"
        },
        {
            "study_id": "ALV-CHK-42",
            "file": samples_dir / "sample_clear_normal.dcm",
            "patient_mrn": "MRN-64219",
            "patient_name": "MERCER^THOMAS",
            "patient_age_sex": "52Y / M",
            "study_time": "13:30 EST",
            "clinical_hx": "Pre-operative elective surgical screening (Cholecystectomy).",
            "status": "SIGNED",
            "modality": "DX (16-bit)"
        },
        {
            "study_id": "ALV-CHK-88",
            "file": samples_dir / "sample_normal.jpg",
            "patient_mrn": "MRN-55102",
            "patient_name": "CHEN^WEI",
            "patient_age_sex": "29Y / F",
            "study_time": "13:05 EST",
            "clinical_hx": "Routine annual occupational health screening.",
            "status": "PENDING",
            "modality": "CR"
        }
    ]

    studies: List[WorklistStudyItem] = []

    for spec in cohort_specs:
        file_path = spec["file"]
        if not file_path.exists():
            continue

        raw_bytes = file_path.read_bytes()
        raw_gray, dicom_meta = preprocessor.load_image_or_dicom(raw_bytes, filename=file_path.name)
        
        # Override metadata with spec if necessary
        dicom_meta["patient_id"] = spec["patient_mrn"]
        dicom_meta["patient_name"] = spec["patient_name"]

        resized = cv2.resize(raw_gray, (settings.INPUT_WIDTH, settings.INPUT_HEIGHT), interpolation=cv2.INTER_AREA)
        tensor = resized.reshape(1, settings.INPUT_HEIGHT, settings.INPUT_WIDTH, 1).astype(np.float32) / settings.NORMALIZATION_SCALE
        
        pred = model.predict_tensor(tensor)
        blended_bgr, _, zonation = gradcam.generate_overlay(raw_gray, tensor, colormap_name="inferno", alpha=0.5)

        is_pneu = pred["is_pneumonia"]
        conf = pred["confidence_percentage"]

        # Acuity Priority Assignment
        if is_pneu and conf >= 85.0:
            priority = "STAT_CRITICAL"
            rank = 1
        elif is_pneu:
            priority = "URGENT"
            rank = 2
        else:
            priority = "ROUTINE"
            rank = 3

        studies.append(WorklistStudyItem(
            study_id=spec["study_id"],
            patient_mrn=spec["patient_mrn"],
            patient_name=spec["patient_name"],
            patient_age_sex=spec["patient_age_sex"],
            study_time=spec["study_time"],
            priority=priority,
            priority_rank=rank,
            diagnosis=pred["diagnosis"],
            is_pneumonia=is_pneu,
            confidence_percentage=conf,
            dominant_zone=zonation.get("dominant_zone", "Right Lower Lobe"),
            status=spec["status"],
            modality=spec["modality"],
            image_b64=preprocessor.to_base64_jpeg(raw_gray),
            gradcam_overlay_b64=preprocessor.to_base64_jpeg(blended_bgr),
            zonation=AnatomicalZonation(**zonation),
            dicom_metadata=DicomMetadataModel(**dicom_meta)
        ))

    # Acuity Sort: Rank 1 (STAT) -> Rank 2 (URGENT) -> Rank 3 (ROUTINE)
    studies.sort(key=lambda s: (s.priority_rank, s.status == "SIGNED"))
    _WORKLIST_CACHE = studies

    stat_cnt = sum(1 for s in studies if s.priority == "STAT_CRITICAL")
    pend_cnt = sum(1 for s in studies if s.status == "PENDING")

    return WorklistResponse(
        total_cases=len(studies),
        stat_critical_count=stat_cnt,
        pending_count=pend_cnt,
        studies=studies
    )

@router.post("/api/v1/batch/triage", response_model=BatchTriageResponse, tags=["Emergency Triage & Worklist"])
async def batch_triage_radiographs(
    files: List[UploadFile] = File(..., description="Multiple radiographs or DICOM files for cohort triage")
):
    """
    Ingests a cohort of chest radiographs/DICOM files simultaneously,
    executes concurrent CADe evaluation, auto-sorts by acuity severity,
    and inserts them dynamically into the triage queue.
    """
    model, gradcam = get_engine()
    triaged: List[WorklistStudyItem] = []

    for idx, f in enumerate(files):
        try:
            raw_bytes = await f.read()
            if len(raw_bytes) == 0:
                continue

            raw_gray, dicom_meta = preprocessor.load_image_or_dicom(raw_bytes, filename=f.filename)
            resized = cv2.resize(raw_gray, (settings.INPUT_WIDTH, settings.INPUT_HEIGHT), interpolation=cv2.INTER_AREA)
            tensor = resized.reshape(1, settings.INPUT_HEIGHT, settings.INPUT_WIDTH, 1).astype(np.float32) / settings.NORMALIZATION_SCALE

            pred = model.predict_tensor(tensor)
            blended_bgr, _, zonation = gradcam.generate_overlay(raw_gray, tensor, colormap_name="inferno", alpha=0.5)

            is_pneu = pred["is_pneumonia"]
            conf = pred["confidence_percentage"]

            if is_pneu and conf >= 85.0:
                prio = "STAT_CRITICAL"
                rank = 1
            elif is_pneu:
                prio = "URGENT"
                rank = 2
            else:
                prio = "ROUTINE"
                rank = 3

            # Clean patient name and MRN
            raw_pname = dicom_meta.get("patient_name")
            if raw_pname and raw_pname not in ("ANONYMOUS PATIENT", "Anonymous Patient"):
                clean_pname = str(raw_pname).replace("^", ", ")
            elif f.filename:
                stem = Path(f.filename).stem.replace("_", " ").replace("-", " ").strip()
                clean_pname = stem.title() if stem.islower() else stem
            else:
                clean_pname = f"PATIENT #{idx + 1}"

            study_id = f"ALV-BAT-{uuid.uuid4().hex[:6].upper()}"
            item = WorklistStudyItem(
                study_id=study_id,
                patient_mrn=dicom_meta.get("patient_id", f"MRN-{uuid.uuid4().hex[:5].upper()}"),
                patient_name=clean_pname,
                patient_age_sex=f"{dicom_meta.get('patient_age', '50Y')} / {dicom_meta.get('patient_sex', 'U')}",
                study_time=datetime.datetime.now().strftime("%H:%M EST"),
                priority=prio,
                priority_rank=rank,
                diagnosis=pred["diagnosis"],
                is_pneumonia=is_pneu,
                confidence_percentage=conf,
                dominant_zone=zonation.get("dominant_zone", "Right Lower Lobe"),
                status="PENDING",
                modality="DX" if dicom_meta.get("is_dicom") else "CR",
                image_b64=preprocessor.to_base64_jpeg(raw_gray),
                gradcam_overlay_b64=preprocessor.to_base64_jpeg(blended_bgr),
                zonation=AnatomicalZonation(**zonation),
                dicom_metadata=DicomMetadataModel(**dicom_meta)
            )
            triaged.append(item)
        except Exception:
            continue

    # Sort triaged cases with STAT_CRITICAL first
    triaged.sort(key=lambda s: s.priority_rank)

    # Insert into global cache
    global _WORKLIST_CACHE
    if _WORKLIST_CACHE is None:
        _WORKLIST_CACHE = []
    _WORKLIST_CACHE = triaged + _WORKLIST_CACHE
    _WORKLIST_CACHE.sort(key=lambda s: (s.priority_rank, s.status == "SIGNED"))

    stat_count = sum(1 for s in triaged if s.priority == "STAT_CRITICAL")

    return BatchTriageResponse(
        total_ingested=len(triaged),
        critical_stat_count=stat_count,
        triaged_studies=triaged
    )

@router.post("/api/v1/signoff", response_model=SignoffResponse, tags=["Emergency Triage & Worklist"])
async def signoff_study(req: SignoffRequest):
    """
    Registers a radiologist's electronic verification signature,
    updates the study status to 'SIGNED', and generates an SHA-256 audit stamp.
    """
    global _WORKLIST_CACHE
    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    audit_data = f"{req.study_id}:{req.physician_license}:{timestamp}"
    audit_hash = hashlib.sha256(audit_data.encode()).hexdigest()[:16].upper()

    if _WORKLIST_CACHE:
        for s in _WORKLIST_CACHE:
            if s.study_id == req.study_id:
                s.status = "SIGNED"
                break

    return SignoffResponse(
        status="success",
        study_id=req.study_id,
        timestamp=timestamp,
        physician_signature=f"Electronically signed by {req.physician_name} ({req.physician_license})",
        signoff_badge="VERIFIED & SIGNED",
        audit_hash=audit_hash
    )

@router.delete("/api/v1/worklist/{study_id}", tags=["Emergency Triage & Worklist"])
async def delete_worklist_study(study_id: str):
    """
    Deletes an individual study from the triage worklist cache.
    """
    global _WORKLIST_CACHE
    if _WORKLIST_CACHE is None:
        raise HTTPException(status_code=404, detail="Worklist is uninitialized or empty.")
    initial_len = len(_WORKLIST_CACHE)
    _WORKLIST_CACHE = [s for s in _WORKLIST_CACHE if s.study_id != study_id]
    if len(_WORKLIST_CACHE) == initial_len:
        raise HTTPException(status_code=404, detail=f"Study {study_id} not found in worklist.")
    return {
        "status": "success",
        "deleted_study_id": study_id,
        "remaining_count": len(_WORKLIST_CACHE)
    }

@router.post("/api/v1/worklist/batch-delete", response_model=BatchDeleteResponse, tags=["Emergency Triage & Worklist"])
async def batch_delete_worklist_studies(req: BatchDeleteRequest):
    """
    Deletes multiple selected studies from the triage worklist cache simultaneously.
    """
    global _WORKLIST_CACHE
    if _WORKLIST_CACHE is None:
        return BatchDeleteResponse(status="success", deleted_count=0, remaining_count=0)

    to_delete = set(req.study_ids)
    before_count = len(_WORKLIST_CACHE)
    _WORKLIST_CACHE = [s for s in _WORKLIST_CACHE if s.study_id not in to_delete]
    deleted_count = before_count - len(_WORKLIST_CACHE)

    return BatchDeleteResponse(
        status="success",
        deleted_count=deleted_count,
        remaining_count=len(_WORKLIST_CACHE)
    )

@router.delete("/api/v1/worklist", tags=["Emergency Triage & Worklist"])
async def clear_worklist_cohort(uploaded_only: bool = True):
    """
    Removes uploaded cohort studies or purges the entire active worklist queue.
    """
    global _WORKLIST_CACHE
    if _WORKLIST_CACHE is None:
        _WORKLIST_CACHE = []
        return {"status": "success", "remaining_count": 0}

    if uploaded_only:
        _WORKLIST_CACHE = [s for s in _WORKLIST_CACHE if not s.study_id.startswith("ALV-BAT-")]
    else:
        _WORKLIST_CACHE = []

    return {
        "status": "success",
        "purged_uploaded_only": uploaded_only,
        "remaining_count": len(_WORKLIST_CACHE)
    }

@router.post("/api/v1/worklist/reset", tags=["Emergency Triage & Worklist"])
async def reset_worklist_to_baseline():
    """
    Resets the emergency triage worklist back to standard baseline calibration studies.
    """
    global _WORKLIST_CACHE
    _WORKLIST_CACHE = None
    return {"status": "success", "message": "Worklist reset to baseline calibration cohort."}

@router.get("/api/v1/samples", response_model=SamplesListResponse, tags=["PACS Verification Samples"])
async def get_sample_radiographs():
    """Serves calibrated verification radiographs and native DICOM files."""
    ensure_sample_assets()
    samples_dir = settings.SAMPLES_DIR

    normal_path = samples_dir / "sample_normal.jpg"
    pneumonia_path = samples_dir / "sample_pneumonia.jpg"
    dicom_stat_path = samples_dir / "sample_stat_pneumonia.dcm"
    dicom_clear_path = samples_dir / "sample_clear_normal.dcm"

    samples = []
    if dicom_stat_path.exists():
        raw_dcm, _ = preprocessor.load_image_or_dicom(dicom_stat_path.read_bytes(), filename="stat.dcm")
        samples.append(SampleItem(
            id="sample_stat_dicom",
            title="STAT Native DICOM (16-bit) - Vance, E.",
            expected_condition="PNEUMONIA",
            description="Native 16-bit uncompressed chest DICOM with dense alveolar airspace consolidation in right lung.",
            image_b64=preprocessor.to_base64_jpeg(raw_dcm),
            is_dicom=True
        ))

    if dicom_clear_path.exists():
        raw_dcm_c, _ = preprocessor.load_image_or_dicom(dicom_clear_path.read_bytes(), filename="clear.dcm")
        samples.append(SampleItem(
            id="sample_clear_dicom",
            title="Routine Native DICOM (16-bit) - Mercer, T.",
            expected_condition="NORMAL",
            description="Native 16-bit uncompressed chest DICOM with sharp costophrenic recesses and clear lung fields.",
            image_b64=preprocessor.to_base64_jpeg(raw_dcm_c),
            is_dicom=True
        ))

    if pneumonia_path.exists():
        raw_pneu = preprocessor.load_image(str(pneumonia_path))
        samples.append(SampleItem(
            id="sample_pneumonia",
            title="Consolidative Infiltrate Film (JPEG)",
            expected_condition="PNEUMONIA",
            description="Dense alveolar airspace consolidation localized predominantly in right lower/mid pulmonary zone.",
            image_b64=preprocessor.to_base64_jpeg(raw_pneu),
            is_dicom=False
        ))

    if normal_path.exists():
        raw_norm = preprocessor.load_image(str(normal_path))
        samples.append(SampleItem(
            id="sample_normal",
            title="Calibrated Normal Film (JPEG)",
            expected_condition="NORMAL",
            description="Clear bilateral pulmonary parenchyma, sharp costophrenic recesses, normal mediastinal silhouette.",
            image_b64=preprocessor.to_base64_jpeg(raw_norm),
            is_dicom=False
        ))

    return SamplesListResponse(samples=samples)

@router.post("/api/v1/report", response_model=ClinicalReportResponse, tags=["Consultation Reporting"])
async def generate_clinical_report(report_data: ClinicalReportRequest):
    """Formats an official, hospital-grade radiology consultation note with accession tracking."""
    report_id = f"ALV-{uuid.uuid4().hex[:8].upper()}"
    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    status_color = "#e11d48" if report_data.diagnosis == "PNEUMONIA" else "#059669"
    status_bg = "rgba(225, 29, 72, 0.08)" if report_data.diagnosis == "PNEUMONIA" else "rgba(5, 150, 105, 0.08)"

    zonation_html = ""
    if report_data.zonation:
        z = report_data.zonation
        zonation_html = f"""
        <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-top: 14px; font-size: 12px;">
            <div style="background: #fff; padding: 8px; border: 1px solid #e2e8f0; border-radius: 4px; text-align: center;">
                <div style="color: #64748b; font-size: 11px;">R. UPPER LOBE</div>
                <div style="font-weight: bold; color: #0f172a; font-size: 14px;">{z.get('right_upper_lobe_pct', 0)}%</div>
            </div>
            <div style="background: #fff; padding: 8px; border: 1px solid #e2e8f0; border-radius: 4px; text-align: center;">
                <div style="color: #64748b; font-size: 11px;">R. LOWER LOBE</div>
                <div style="font-weight: bold; color: #0f172a; font-size: 14px;">{z.get('right_lower_lobe_pct', 0)}%</div>
            </div>
            <div style="background: #fff; padding: 8px; border: 1px solid #e2e8f0; border-radius: 4px; text-align: center;">
                <div style="color: #64748b; font-size: 11px;">L. UPPER LOBE</div>
                <div style="font-weight: bold; color: #0f172a; font-size: 14px;">{z.get('left_upper_lobe_pct', 0)}%</div>
            </div>
            <div style="background: #fff; padding: 8px; border: 1px solid #e2e8f0; border-radius: 4px; text-align: center;">
                <div style="color: #64748b; font-size: 11px;">L. LOWER LOBE</div>
                <div style="font-weight: bold; color: #0f172a; font-size: 14px;">{z.get('left_lower_lobe_pct', 0)}%</div>
            </div>
        </div>
        """

    html_content = f"""
    <div class="alveon-report" style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #0f172a; padding: 32px; background: #ffffff; max-width: 800px; margin: 0 auto;">
        <!-- Institutional Header -->
        <div style="display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 2px solid #0f172a; padding-bottom: 16px; margin-bottom: 24px;">
            <div>
                <div style="font-size: 22px; font-weight: 800; letter-spacing: -0.5px; color: #0f172a;">ALVEON THORACIC PACS</div>
                <div style="font-size: 12px; color: #64748b; margin-top: 2px; text-transform: uppercase; letter-spacing: 0.5px;">Department of Diagnostic & Interventional Radiology</div>
            </div>
            <div style="text-align: right; font-size: 12px; color: #475569;">
                <div><strong>ACCESSION:</strong> {report_id}</div>
                <div><strong>STUDY DATE:</strong> {timestamp}</div>
                <div><strong>SYSTEM:</strong> ALVEON Core v{settings.PROJECT_VERSION}</div>
            </div>
        </div>

        <!-- Patient Demographics Bar -->
        <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 14px 18px; margin-bottom: 24px; font-size: 13px;">
            <div><span style="color: #64748b; display: block; font-size: 11px;">PATIENT MRN</span><strong>{report_data.patient_id}</strong></div>
            <div><span style="color: #64748b; display: block; font-size: 11px;">PATIENT NAME</span><strong>{report_data.patient_name}</strong></div>
            <div><span style="color: #64748b; display: block; font-size: 11px;">AGE / SEX</span><strong>{report_data.patient_age} Y / {report_data.patient_gender}</strong></div>
            <div><span style="color: #64748b; display: block; font-size: 11px;">ORDERING MD</span><strong>{report_data.referring_physician}</strong></div>
        </div>

        <!-- Diagnostic Impression Box -->
        <div style="border-left: 4px solid {status_color}; background: {status_bg}; padding: 18px; border-radius: 0 6px 6px 0; margin-bottom: 24px;">
            <div style="font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; color: {status_color}; margin-bottom: 4px;">
                PRIMARY RADIOLOGIC IMPRESSION
            </div>
            <div style="font-size: 19px; font-weight: 800; color: #0f172a; margin-bottom: 6px;">
                {report_data.diagnosis}: {report_data.confidence_percentage}% Probability ({report_data.risk_tier.replace('_', ' ')})
            </div>
            <p style="font-size: 13px; line-height: 1.5; color: #334155; margin: 0;">
                {report_data.clinical_recommendation}
            </p>
            {zonation_html}
        </div>

        <!-- Radiographic Plate Visuals -->
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin-bottom: 28px;">
            <div style="text-align: center;">
                <div style="font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; color: #64748b; margin-bottom: 8px;">Pre-Processed Radiograph</div>
                <img src="{report_data.original_image_b64}" style="width: 100%; max-width: 280px; border-radius: 4px; border: 1px solid #cbd5e1; background: #000;" alt="Chest X-Ray" />
            </div>
            <div style="text-align: center;">
                <div style="font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; color: #64748b; margin-bottom: 8px;">Grad-CAM Pathological Activation</div>
                <img src="{report_data.gradcam_overlay_b64}" style="width: 100%; max-width: 280px; border-radius: 4px; border: 1px solid #cbd5e1; background: #000;" alt="Grad-CAM Overlay" />
            </div>
        </div>

        <!-- Clinical Attestation & Sign-off -->
        <div style="border-top: 1px solid #e2e8f0; padding-top: 20px; display: flex; justify-content: space-between; align-items: flex-end; font-size: 11px; color: #64748b;">
            <div style="max-width: 420px; line-height: 1.4;">
                <strong>Regulatory Decision Support Disclaimer:</strong><br>
                ALVEON is calibrated for computer-aided detection (CADe/CADx) assistance. Final diagnosis must be verified in accordance with ACR/RSNA clinical guidelines by a credentialed radiologist.
            </div>
            <div style="text-align: right; min-width: 220px;">
                <div style="border-bottom: 1px solid #0f172a; height: 35px; margin-bottom: 6px;"></div>
                <div>Electronically Signed & Attested</div>
                <div style="font-family: monospace; font-size: 10px; color: #94a3b8; margin-top: 2px;">HASH: {uuid.uuid4().hex[:16]}</div>
            </div>
        </div>
    </div>
    """

    return ClinicalReportResponse(
        report_id=report_id,
        timestamp=timestamp,
        summary_html=html_content
    )
