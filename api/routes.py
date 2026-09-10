from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Body, Request, Response
from fastapi.responses import StreamingResponse, JSONResponse
from core.pdf_generator import generate_clinical_report_pdf
from core.dicom_listener import get_dicom_scp
from core.multilabel import get_multilabel_engine
from core.dicomweb import (
    dataset_to_dicom_json,
    study_item_to_dicom_json,
    study_item_to_pydicom,
    parse_multipart_dicom,
    render_dicom_frame
)
from core.pacs_client import get_pacs_client
from pathlib import Path
import numpy as np
import tensorflow as tf
import cv2
import io
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
    BatchDeleteResponse,
    MultiLabelFindingItem,
    PacsPingRequest,
    PacsPushRequest
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

        # 3. Grad-CAM Synthesis with Anatomical Quadrant Zonation
        blended_bgr, heatmap_bgr, zonation = gradcam.generate_overlay(
            original_gray=proc_gray,
            tensor=tensor,
            colormap_name=colormap,
            alpha=float(np.clip(heatmap_alpha, 0.1, 0.9))
        )

        # 4. Multi-Label Neural & Radiomic Diagnostic Classification
        inference_result = model.predict_multilabel(tensor, proc_gray, zonation)
        findings_objs = [MultiLabelFindingItem(**f) for f in inference_result["all_findings"]]

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
            dicom_metadata=DicomMetadataModel(**dicom_meta),
            primary_finding=inference_result["primary_finding"],
            primary_display_name=inference_result["primary_display_name"],
            secondary_findings=inference_result["secondary_findings"],
            findings=findings_objs,
            clinical_impression=inference_result["clinical_impression"]
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
        
        _, _, zonation = gradcam.generate_overlay(raw_gray, tensor, colormap_name="inferno", alpha=0.5)
        pred = model.predict_multilabel(tensor, raw_gray, zonation)
        blended_bgr, _, _ = gradcam.generate_overlay(raw_gray, tensor, colormap_name="inferno", alpha=0.5)

        is_pneu = pred["is_pneumonia"]
        conf = pred["confidence_percentage"]
        priority = pred["priority"]
        rank = pred["priority_rank"]

        findings_objs = [MultiLabelFindingItem(**f) for f in pred["all_findings"]]

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
            dicom_metadata=DicomMetadataModel(**dicom_meta),
            primary_finding=pred["primary_finding"],
            secondary_findings=pred["secondary_findings"],
            findings=findings_objs
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

            _, _, zonation = gradcam.generate_overlay(raw_gray, tensor, colormap_name="inferno", alpha=0.5)
            pred = model.predict_multilabel(tensor, raw_gray, zonation)
            blended_bgr, _, _ = gradcam.generate_overlay(raw_gray, tensor, colormap_name="inferno", alpha=0.5)

            is_pneu = pred["is_pneumonia"]
            conf = pred["confidence_percentage"]
            prio = pred["priority"]
            rank = pred["priority_rank"]

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
            findings_objs = [MultiLabelFindingItem(**item_f) for item_f in pred["all_findings"]]

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
                dicom_metadata=DicomMetadataModel(**dicom_meta),
                primary_finding=pred["primary_finding"],
                secondary_findings=pred["secondary_findings"],
                findings=findings_objs
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

@router.post("/api/v1/report/pdf", tags=["Clinical Consultation & Export"])
async def export_consultation_pdf(report: Dict[str, Any] = Body(...)):
    """
    Generates and streams a certified hospital radiologic consultation PDF document.
    """
    try:
        pdf_buffer = generate_clinical_report_pdf(report)
        study_id = report.get("study_id", "ALVEON-REPORT")
        filename = f"ALVEON_Consultation_{study_id}_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
        return StreamingResponse(
            pdf_buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF Generation failed: {str(e)}")

@router.get("/api/v1/worklist/{study_id}/pdf", tags=["Clinical Consultation & Export"])
async def export_study_pdf_by_id(study_id: str):
    """
    Generates a certified clinical consultation PDF for a specific study ID in active triage queue.
    """
    global _WORKLIST_CACHE
    if not _WORKLIST_CACHE:
        # Load baseline if empty
        await get_emergency_worklist()
    study = next((s for s in _WORKLIST_CACHE if s.study_id == study_id), None)
    if not study:
        raise HTTPException(status_code=404, detail=f"Study {study_id} not found.")

    report_data = {
        "study_id": study.study_id,
        "patient_name": study.patient_name,
        "patient_mrn": study.patient_mrn,
        "patient_age_sex": study.patient_age_sex,
        "study_time": study.study_time,
        "modality": study.modality,
        "priority": study.priority,
        "diagnosis": study.diagnosis,
        "is_pneumonia": study.is_pneumonia,
        "confidence_percentage": study.confidence_percentage,
        "dominant_zone": study.dominant_zone,
        "zonation": study.zonation.model_dump() if hasattr(study.zonation, 'model_dump') else study.zonation,
        "original_image_b64": study.image_b64,
        "gradcam_overlay_b64": study.gradcam_overlay_b64,
        "status": study.status
    }
    pdf_buffer = generate_clinical_report_pdf(report_data)
    filename = f"ALVEON_Report_{study.study_id}.pdf"
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@router.get("/api/v1/dicom/status", tags=["DICOM Storage SCP Node"])
async def get_dicom_node_status():
    """
    Returns active state and diagnostic telemetry for the ALVEON DICOM Storage SCP node.
    """
    scp = get_dicom_scp()
    return scp.get_status()

@router.post("/api/v1/dicom/echo", tags=["DICOM Storage SCP Node"])
async def trigger_dicom_echo():
    """
    Executes a loopback C-ECHO verification against the local DICOM listener node.
    """
    scp = get_dicom_scp()
    if not scp.is_running:
        return {
            "status": "offline",
            "message": f"DICOM SCP listener is not active on port {scp.port}. Start service or verify network permissions."
        }
    res = scp.send_echo(host="127.0.0.1")
    return res

# ==============================================================================
# EXTERNAL PACS & DICOM INTEROPERABILITY ENDPOINTS
# ==============================================================================

@router.post("/api/v1/pacs/ping", tags=["External PACS & Connectivity"])
async def ping_external_pacs_node(req: PacsPingRequest):
    """
    Executes a DICOM C-ECHO verification request to an external PACS or local listener.
    """
    client = get_pacs_client()
    return client.ping(host=req.host, port=req.port, remote_ae=req.ae_title)

@router.post("/api/v1/pacs/push", tags=["External PACS & Connectivity"])
async def push_study_to_external_pacs(req: PacsPushRequest):
    """
    Transmits an existing triage study to an external PACS destination via C-STORE.
    """
    global _WORKLIST_CACHE
    if not _WORKLIST_CACHE:
        await get_emergency_worklist()
    study = next((s for s in _WORKLIST_CACHE if s.study_id == req.study_id), None)
    if not study:
        raise HTTPException(status_code=404, detail=f"Study {req.study_id} not found in active triage worklist.")

    ds = study_item_to_pydicom(study)
    client = get_pacs_client()
    return client.push_study(ds, host=req.host, port=req.port, remote_ae=req.ae_title)

@router.post("/api/v1/pacs/inject-cohort", tags=["External PACS & Connectivity"])
async def inject_external_pacs_cohort():
    """
    Generates and ingests a diverse 6-patient clinical cohort representing distinct
    thoracic pathologies (Tension Pneumothorax, Lobar Pneumonia, Pleural Effusion,
    Cardiomegaly, Atelectasis, Normal) into the live ER worklist.
    """
    from tests.test_external_pacs_cohort import generate_cohort_datasets
    datasets = generate_cohort_datasets()
    client = get_pacs_client()
    results = []
    for ds in datasets:
        res = client.push_study(ds, host="127.0.0.1", port=11112, remote_ae="ALVEON_PACS")
        results.append(res)
    return {
        "status": "success",
        "cohort_count": len(results),
        "results": results
    }

# ==============================================================================
# DICOMweb REST SERVICES (DICOM PS 3.18 / QIDO-RS, WADO-RS, STOW-RS)
# ==============================================================================

def _find_study(identifier: str) -> Optional[WorklistStudyItem]:
    global _WORKLIST_CACHE
    if not _WORKLIST_CACHE:
        return None
    for s in _WORKLIST_CACHE:
        uid = f"1.2.826.0.1.3680043.9.7123.{abs(hash(s.study_id)) % 1000000000}"
        if s.study_id == identifier or uid == identifier:
            return s
    return None

@router.get("/dicomweb/studies", tags=["DICOMweb REST Services (DICOM Part 18)"])
async def qido_search_studies(
    PatientID: Optional[str] = None,
    PatientName: Optional[str] = None,
    StudyDate: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
):
    """
    QIDO-RS (Query ID in DICOM Objects): Search studies conforming to DICOM Part 18 JSON.
    """
    global _WORKLIST_CACHE
    if not _WORKLIST_CACHE:
        await get_emergency_worklist()

    matches = []
    for s in _WORKLIST_CACHE:
        if PatientID and PatientID.lower() not in s.patient_mrn.lower():
            continue
        if PatientName and PatientName.lower() not in s.patient_name.lower():
            continue
        matches.append(study_item_to_dicom_json(s))

    return JSONResponse(
        content=matches[offset:offset + limit],
        media_type="application/dicom+json"
    )

@router.get("/dicomweb/studies/{study_uid}/series", tags=["DICOMweb REST Services (DICOM Part 18)"])
async def qido_search_series(study_uid: str):
    """
    QIDO-RS: Returns series for a study.
    """
    study = _find_study(study_uid)
    if not study:
        raise HTTPException(status_code=404, detail="Study not found.")
    doc = study_item_to_dicom_json(study)
    series_doc = {
        "0020000D": doc["0020000D"],
        "0020000E": doc["0020000E"],
        "00080060": doc["00080060"],
        "00200011": doc["00200011"],
        "0008103E": {"vr": "LO", "Value": ["Thoracic Radiograph Series"]}
    }
    return JSONResponse(content=[series_doc], media_type="application/dicom+json")

@router.get("/dicomweb/studies/{study_uid}/series/{series_uid}/instances", tags=["DICOMweb REST Services (DICOM Part 18)"])
async def qido_search_instances(study_uid: str, series_uid: str):
    """
    QIDO-RS: Returns instances for a series.
    """
    study = _find_study(study_uid)
    if not study:
        raise HTTPException(status_code=404, detail="Study not found.")
    doc = study_item_to_dicom_json(study)
    return JSONResponse(content=[doc], media_type="application/dicom+json")

@router.get("/dicomweb/studies/{study_uid}/series/{series_uid}/instances/{instance_uid}", tags=["DICOMweb REST Services (DICOM Part 18)"])
async def wado_retrieve_instance(study_uid: str, series_uid: str, instance_uid: str):
    """
    WADO-RS: Retrieves native binary DICOM instance.
    """
    study = _find_study(study_uid)
    if not study:
        raise HTTPException(status_code=404, detail="Instance not found.")
    ds = study_item_to_pydicom(study)
    bio = io.BytesIO()
    ds.save_as(bio, write_like_original=False)
    bio.seek(0)
    return Response(content=bio.getvalue(), media_type="application/dicom")

@router.get("/dicomweb/studies/{study_uid}/series/{series_uid}/instances/{instance_uid}/metadata", tags=["DICOMweb REST Services (DICOM Part 18)"])
async def wado_retrieve_instance_metadata(study_uid: str, series_uid: str, instance_uid: str):
    """
    WADO-RS: Retrieves full DICOM JSON metadata for instance.
    """
    study = _find_study(study_uid)
    if not study:
        raise HTTPException(status_code=404, detail="Instance not found.")
    doc = study_item_to_dicom_json(study)
    return JSONResponse(content=[doc], media_type="application/dicom+json")

@router.get("/dicomweb/studies/{study_uid}/series/{series_uid}/instances/{instance_uid}/rendered", tags=["DICOMweb REST Services (DICOM Part 18)"])
async def wado_retrieve_rendered_instance(study_uid: str, series_uid: str, instance_uid: str):
    """
    WADO-RS: Retrieves windowed diagnostic rendered frame (JPEG).
    """
    study = _find_study(study_uid)
    if not study:
        raise HTTPException(status_code=404, detail="Instance not found.")
    ds = study_item_to_pydicom(study)
    jpg_bytes = render_dicom_frame(ds)
    return Response(content=jpg_bytes, media_type="image/jpeg")

@router.post("/dicomweb/studies", tags=["DICOMweb REST Services (DICOM Part 18)"])
async def stow_store_instances(request: Request):
    """
    STOW-RS (Store Over the Web): Stores DICOM instances submitted via multipart/related
    or raw application/dicom binary, executes multi-label AI triage, and updates worklist.
    """
    content_type = request.headers.get("content-type", "")
    body = await request.body()
    if not body:
        raise HTTPException(status_code=400, detail="Empty request payload for STOW-RS.")

    dicom_binaries = parse_multipart_dicom(body, content_type)
    if not dicom_binaries:
        raise HTTPException(status_code=400, detail="No valid DICOM instances extracted from STOW-RS payload.")

    model, gradcam = get_engine()
    ingested_count = 0

    for raw_dcm in dicom_binaries:
        try:
            raw_gray, dicom_meta = preprocessor.load_image_or_dicom(raw_dcm, filename="stow.dcm")
            resized = cv2.resize(raw_gray, (settings.INPUT_WIDTH, settings.INPUT_HEIGHT), interpolation=cv2.INTER_AREA)
            tensor = resized.reshape(1, settings.INPUT_HEIGHT, settings.INPUT_WIDTH, 1).astype(np.float32) / settings.NORMALIZATION_SCALE

            _, _, zonation = gradcam.generate_overlay(raw_gray, tensor, colormap_name="inferno", alpha=0.5)
            multi_pred = model.predict_multilabel(tensor, raw_gray, zonation)
            blended_bgr, _, _ = gradcam.generate_overlay(raw_gray, tensor, colormap_name="inferno", alpha=0.5)

            study_id = f"ALV-STOW-{uuid.uuid4().hex[:6].upper()}"
            findings_objs = [MultiLabelFindingItem(**item_f) for item_f in multi_pred["all_findings"]]

            raw_pname = dicom_meta.get("patient_name", "STOW Patient")
            clean_name = str(raw_pname).replace("^", ", ") if raw_pname else "STOW Patient"

            item = WorklistStudyItem(
                study_id=study_id,
                patient_mrn=dicom_meta.get("patient_id", f"MRN-{uuid.uuid4().hex[:5].upper()}"),
                patient_name=clean_name,
                patient_age_sex=f"{dicom_meta.get('patient_age', '50Y')} / {dicom_meta.get('patient_sex', 'U')}",
                study_time=datetime.datetime.now().strftime("%H:%M EST"),
                priority=multi_pred["priority"],
                priority_rank=multi_pred["priority_rank"],
                diagnosis=multi_pred["diagnosis"],
                is_pneumonia=multi_pred["is_pneumonia"],
                confidence_percentage=multi_pred["confidence_percentage"],
                dominant_zone=zonation.get("dominant_zone", "Right Lower Lobe"),
                status="PENDING",
                modality="DX",
                image_b64=preprocessor.to_base64_jpeg(raw_gray),
                gradcam_overlay_b64=preprocessor.to_base64_jpeg(blended_bgr),
                zonation=AnatomicalZonation(**zonation),
                dicom_metadata=DicomMetadataModel(**dicom_meta),
                primary_finding=multi_pred["primary_finding"],
                secondary_findings=multi_pred["secondary_findings"],
                findings=findings_objs
            )

            global _WORKLIST_CACHE
            if _WORKLIST_CACHE is None:
                _WORKLIST_CACHE = []
            _WORKLIST_CACHE.insert(0, item)
            _WORKLIST_CACHE.sort(key=lambda s: (s.priority_rank, s.status == "SIGNED"))
            ingested_count += 1
        except Exception as e:
            pass

    return JSONResponse(
        status_code=200,
        content={
            "00081199": {
                "vr": "SQ",
                "Value": [{"00081190": {"vr": "UR", "Value": ["/dicomweb/studies"]}}]
            },
            "status": "success",
            "ingested_count": ingested_count
        },
        media_type="application/dicom+json"
    )

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
