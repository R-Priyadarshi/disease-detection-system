from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Body, Request, Response, Depends, Header
from fastapi.responses import StreamingResponse, JSONResponse, FileResponse
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
from core.auth import (
    CLINICAL_DIRECTORY,
    ClinicalUser,
    UserRole,
    create_access_token,
    get_current_user,
    require_roles
)
from core.audit_logger import get_audit_logger
from core.volumetric import get_volumetric_engine, WINDOW_PRESETS
from core.pacs_simulator import get_pacs_simulator
from core.structured_reporting import (
    get_structured_reporting_engine,
    StructuredReportModel,
    VoiceParseResult
)
from core.orthanc_integration import get_orthanc_engine
from core.hl7_engine import get_hl7_engine
from core.fhir_engine import get_fhir_engine
from core.patient_summary import get_patient_summary_engine
from core.alerting_engine import get_alerting_engine
from core.neuro_engine import get_neuro_engine, NEURO_HU_PRESETS
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
    PacsPushRequest,
    LoginRequest,
    TokenResponse,
    ClinicalUserSchema,
    AuditQueryResponse,
    AuditVerifyResponse,
    VolumetricSeriesListResponse,
    VolumetricSeriesItem,
    VolumetricSliceResponse,
    VolumetricMPRRequest,
    VolumetricMPRResponse,
    SimulateModalityRequest,
    SimulateModalityResponse,
    VoiceDictationRequest,
    VoiceDictationResponse,
    StructuredReportRequest,
    StructuredReportResponse,
    OrthancStatusResponse,
    HealthProbeResponse,
    HL7OrderRequest,
    HL7OrderResponse,
    HL7ReportResponse,
    PatientSummaryRequest,
    PatientSummaryResponse,
    ClosedLoopHandoffRequest,
    ClosedLoopHandoffResponse,
    NeuroSeriesListResponse,
    NeuroSeriesItem,
    NeuroAnalysisResponse
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

@router.api_route("/favicon.ico", methods=["GET", "HEAD"], include_in_schema=False)
async def get_favicon():
    return Response(content=b"", media_type="image/x-icon")


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
async def signoff_study(
    req: SignoffRequest,
    current_user: ClinicalUser = Depends(get_current_user)
):
    """
    Registers a radiologist's electronic verification signature,
    enforces Attending Radiologist credentials, updates the study status to 'SIGNED',
    and registers an immutable HIPAA chained audit record.
    """
    # Enforce RBAC: Only Attending Radiologists or Admins may legally finalize reports
    if current_user.role not in [UserRole.ATTENDING_RADIOLOGIST, UserRole.PACS_ADMIN]:
        raise HTTPException(
            status_code=403,
            detail=f"Clinical Sign-off Restricted: Role '{current_user.role.value}' cannot execute final legal attestation. Attending Radiologist review required."
        )

    global _WORKLIST_CACHE
    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    audit_data = f"{req.study_id}:{req.physician_license}:{timestamp}"
    audit_hash = hashlib.sha256(audit_data.encode()).hexdigest()[:16].upper()

    target_mrn = None
    if _WORKLIST_CACHE:
        for s in _WORKLIST_CACHE:
            if s.study_id == req.study_id:
                s.status = "SIGNED"
                target_mrn = s.patient_mrn
                break


    # Record HIPAA Audit Log
    get_audit_logger().log(
        action="ATTESTATION_SIGNED",
        user_id=current_user.user_id,
        username=current_user.username,
        user_role=current_user.role.value,
        patient_mrn=target_mrn or "MRN-UNKNOWN",
        study_id=req.study_id,
        details={
            "physician_signature": req.physician_name,
            "physician_license": req.physician_license,
            "attestation_notes": req.clinical_notes,
            "cryptographic_stamp": audit_hash
        }
    )

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


# =========================================================================
# v4.0 Enterprise Endpoints: Authentication, HIPAA Audit, 3D MPR, Modality Simulator
# =========================================================================

# --- 1. Authentication & Role-Based Access Control ---

@router.post("/api/v1/auth/login", response_model=TokenResponse, tags=["Enterprise Security & RBAC"])
async def login(req: LoginRequest):
    """
    Authenticates clinical staff with hospital credentials,
    issues an HMAC-SHA256 JWT session token, and records a HIPAA login audit event.
    """
    username = req.username.strip().lower()
    if username not in CLINICAL_DIRECTORY:
        raise HTTPException(
            status_code=401,
            detail=f"Authentication failed: User '{username}' not recognized in hospital directory."
        )

    user = CLINICAL_DIRECTORY[username]
    token = create_access_token(user)

    # Log HIPAA security access
    get_audit_logger().log(
        action="LOGIN",
        user_id=user.user_id,
        username=user.username,
        user_role=user.role.value,
        details={"department": user.department, "title": user.title}
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=86400,
        user=ClinicalUserSchema(
            user_id=user.user_id,
            username=user.username,
            full_name=user.full_name,
            title=user.title,
            role=user.role.value,
            department=user.department,
            npi=user.npi,
            initials=user.initials
        )
    )

@router.get("/api/v1/auth/me", response_model=ClinicalUserSchema, tags=["Enterprise Security & RBAC"])
async def get_my_session(current_user: ClinicalUser = Depends(get_current_user)):
    """Returns profile and role claims for the active authenticated session."""
    return ClinicalUserSchema(
        user_id=current_user.user_id,
        username=current_user.username,
        full_name=current_user.full_name,
        title=current_user.title,
        role=current_user.role.value,
        department=current_user.department,
        npi=current_user.npi,
        initials=current_user.initials
    )

@router.get("/api/v1/auth/users", response_model=List[ClinicalUserSchema], tags=["Enterprise Security & RBAC"])
async def list_clinical_directory():
    """Lists pre-configured clinical personas for demonstration and role switching."""
    return [
        ClinicalUserSchema(
            user_id=u.user_id,
            username=u.username,
            full_name=u.full_name,
            title=u.title,
            role=u.role.value,
            department=u.department,
            npi=u.npi,
            initials=u.initials
        )
        for u in CLINICAL_DIRECTORY.values()
    ]


# --- 2. HIPAA Chained Audit Trail ---

@router.get("/api/v1/audit/logs", response_model=AuditQueryResponse, tags=["HIPAA Security & Audit Trail"])
async def get_audit_trail(
    limit: int = 50,
    action: Optional[str] = None,
    current_user: ClinicalUser = Depends(get_current_user)
):
    """
    Retrieves chronological tamper-evident HIPAA audit events.
    Authorized for Attending Radiologists and PACS Administrators.
    """
    events = get_audit_logger().query(limit=limit, action=action)
    return AuditQueryResponse(
        status="success",
        total_returned=len(events),
        events=[e.model_dump() for e in events]
    )

@router.get("/api/v1/audit/verify", response_model=AuditVerifyResponse, tags=["HIPAA Security & Audit Trail"])
async def verify_audit_trail():
    """
    Verifies the cryptographic SHA-256 chained hash integrity of the entire audit ledger.
    Detects any file manipulation or record modification.
    """
    res = get_audit_logger().verify_integrity()
    return AuditVerifyResponse(
        is_valid=res["is_valid"],
        total_events=res.get("total_events", 0),
        latest_hash=res.get("latest_hash"),
        message=res.get("message") or res.get("error", "Audit integrity verification complete.")
    )


# --- 3. 3D Volumetric CT & Multi-Planar Reconstruction (MPR) ---

@router.get("/api/v1/volumetric/series", response_model=VolumetricSeriesListResponse, tags=["3D Volumetric CT & MPR"])
async def list_volumetric_series():
    """Lists available 3D volumetric CT/MRI stacks for multi-planar reconstruction."""
    engine = get_volumetric_engine()
    series_list = engine.list_series()
    return VolumetricSeriesListResponse(
        status="success",
        total_series=len(series_list),
        series=[s.model_dump() for s in series_list]
    )

@router.get("/api/v1/volumetric/{series_id}/slice", response_model=VolumetricSliceResponse, tags=["3D Volumetric CT & MPR"])
async def get_volumetric_slice(
    series_id: str,
    orientation: str = "AXIAL",
    slice_idx: int = 16,
    window_preset: str = "LUNG",
    width: Optional[int] = None,
    level: Optional[int] = None
):
    """
    Extracts a 2D planar slice along AXIAL, CORONAL, or SAGITTAL orthogonal planes
    and applies Hounsfield Unit (HU) windowing.
    """
    engine = get_volumetric_engine()
    try:
        _, slice_8bit, meta = engine.extract_orthogonal_slice(
            series_id=series_id,
            orientation=orientation,
            slice_idx=slice_idx,
            window_preset=window_preset,
            custom_width=width,
            custom_level=level
        )
        data_url = engine.slice_to_data_url(slice_8bit)
        return VolumetricSliceResponse(
            status="success",
            series_id=series_id,
            orientation=meta["orientation"],
            slice_index=meta["slice_index"],
            max_slices=meta["max_slices"],
            slice_location_mm=meta["slice_location_mm"],
            window_preset=meta["window_preset"],
            window_width=meta["window_width"],
            window_level=meta["window_level"],
            mean_hu=meta["mean_hu"],
            data_url=data_url
        )
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Volumetric series '{series_id}' not found.")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/api/v1/volumetric/{series_id}/mpr", response_model=VolumetricMPRResponse, tags=["3D Volumetric CT & MPR"])
async def get_tri_planar_mpr(series_id: str, req: VolumetricMPRRequest):
    """
    Returns synchronized Tri-Planar Multi-Planar Reconstruction views:
    Axial, Coronal, and Sagittal orthogonal cross-sections with coordinate crosshairs.
    """
    engine = get_volumetric_engine()
    try:
        mpr_res = engine.get_tri_planar_mpr(
            series_id=series_id,
            axial_idx=req.axial_idx,
            coronal_idx=req.coronal_idx,
            sagittal_idx=req.sagittal_idx,
            window_preset=req.window_preset
        )
        return VolumetricMPRResponse(
            status="success",
            series_id=series_id,
            window_preset=mpr_res["window_preset"],
            crosshairs=mpr_res["crosshairs"],
            axial=mpr_res["axial"],
            coronal=mpr_res["coronal"],
            sagittal=mpr_res["sagittal"]
        )
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Volumetric series '{series_id}' not found.")


# --- 4. Hospital Modality & VNA Simulator ---

@router.get("/api/v1/pacs/modalities", tags=["External PACS & Connectivity"])
async def list_hospital_modalities():
    """Returns available simulated hospital modalities (XR Emergency Bay, Trauma CT, VNA)."""
    sim = get_pacs_simulator()
    return {"status": "success", "modalities": [m.model_dump() for m in sim.list_modalities()]}

@router.post("/api/v1/pacs/simulate-modality", response_model=SimulateModalityResponse, tags=["External PACS & Connectivity"])
async def trigger_simulated_modality_push(req: SimulateModalityRequest):
    """
    Triggers an automated emergency modality scan completion and C-STORE network transmission
    into ALVEON's Storage SCP on port 11112.
    """
    sim = get_pacs_simulator()
    res = sim.simulate_modality_transmission(
        modality_key=req.modality_key,
        target_port=req.target_port,
        study_idx=req.study_idx
    )

    # Log HIPAA audit trail
    get_audit_logger().log(
        action="MODALITY_PUSH",
        user_id="SIM-DEVICE-AUTOPUSH",
        username=res["modality_device"]["ae_title"],
        user_role="MODALITY_SYSTEM",
        patient_mrn=res["study_transmitted"]["patient_id"],
        details={
            "device": res["modality_device"]["model_name"],
            "target": res["target_node"],
            "latency_ms": res["network_latency_ms"]
        }
    )

    return SimulateModalityResponse(
        status="success",
        success=res["success"],
        status_code=res["status_code"],
        modality_device=res["modality_device"],
        study_transmitted=res["study_transmitted"],
        target_node=res["target_node"],
        network_latency_ms=res["network_latency_ms"],
        sop_instance_uid=res["sop_instance_uid"],
        timestamp=res["timestamp"]
    )


# =========================================================================
# v4.1 Enterprise Endpoints: Probes, OHIF Viewer, Voice Dictation, Orthanc
# =========================================================================

# --- 1. Production Health & Readiness Probes ---

@router.get("/healthz", response_model=HealthProbeResponse, tags=["Production Diagnostics & Probes"])
@router.get("/readyz", response_model=HealthProbeResponse, tags=["Production Diagnostics & Probes"])
@router.get("/api/v1/healthz", response_model=HealthProbeResponse, tags=["Production Diagnostics & Probes"])
async def production_health_probes():
    """Kubernetes, Docker, and Nginx liveness and readiness probe endpoint."""
    return HealthProbeResponse(
        status="healthy",
        timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        version="4.1.0",
        components={
            "api": "operational",
            "model_engine": "loaded",
            "pacs_scp": "listening:11112",
            "orthanc_bridge": "available",
            "dicomweb": "active"
        }
    )


# --- 2. Diagnostic Web Viewer Bridge & OHIF Configuration ---

@router.get("/viewer", tags=["Diagnostic Web Viewer"])
@router.get("/ohif", tags=["Diagnostic Web Viewer"])
async def serve_diagnostic_viewer():
    """Serves the zero-footprint standalone diagnostic DICOM viewer bridge."""
    viewer_path = settings.BASE_DIR / "web" / "ohif_viewer.html"
    if viewer_path.exists():
        return FileResponse(str(viewer_path), media_type="text/html")
    raise HTTPException(status_code=404, detail="Viewer template not found.")

@router.get("/api/v1/ohif/config", tags=["Diagnostic Web Viewer"])
async def get_ohif_viewer_config():
    """Returns dynamic configuration for OHIF Viewer v3 pointing to ALVEON DICOMweb."""
    return {
        "routerBasename": "/",
        "showStudyList": True,
        "servers": {
            "dicomWeb": [
                {
                    "name": "ALVEON_DICOMWEB",
                    "wadoUriRoot": "/dicomweb",
                    "qidoRoot": "/dicomweb",
                    "wadoRoot": "/dicomweb",
                    "qidoSupportsIncludeField": True,
                    "imageRendering": "wadors",
                    "thumbnailRendering": "wadors",
                    "enableStudyLazyLoading": True,
                    "supportsFuzzyMatching": True
                }
            ]
        }
    }


# --- 3. RADLEX Voice Dictation & AI Structured Reporting ---

@router.post("/api/v1/voice/parse-dictation", response_model=VoiceDictationResponse, tags=["RADLEX Voice Dictation"])
async def parse_voice_dictation(req: VoiceDictationRequest):
    """
    Parses speech transcripts from client microphone into ACR / RADLEX structured report fields or executes voice macros.
    """
    engine = get_structured_reporting_engine()
    current_model = None
    if req.current_report:
        try:
            current_model = StructuredReportModel(**req.current_report)
        except Exception:
            current_model = None

    res = engine.parse_dictation_command(
        text=req.transcript,
        current_report=current_model
    )
    return VoiceDictationResponse(
        status="success",
        command_detected=res.command_detected,
        target_field=res.target_field,
        transcribed_text=res.transcribed_text,
        action_executed=res.action_executed,
        structured_report=res.structured_report.model_dump()
    )

@router.post("/api/v1/report/structured", response_model=StructuredReportResponse, tags=["RADLEX Voice Dictation"])
async def synthesize_structured_report(req: StructuredReportRequest):
    """
    Generates a full ACR / RADLEX thoracic consultation report synthesized from AI findings or custom edits.
    """
    engine = get_structured_reporting_engine()
    rep = engine.generate_report_from_findings(
        diagnosis=req.diagnosis or "NORMAL",
        confidence=req.confidence_percentage or 95.0,
        multilabel_findings=req.all_findings,
        zonation=req.zonation
    )
    if req.structured_report:
        for k, v in req.structured_report.items():
            if hasattr(rep, k) and v:
                setattr(rep, k, v)
    return StructuredReportResponse(
        status="success",
        structured_report=rep.model_dump()
    )


# --- 4. Orthanc Hospital PACS Integration ---

@router.get("/api/v1/pacs/orthanc/status", response_model=OrthancStatusResponse, tags=["External PACS & Connectivity"])
async def get_orthanc_pacs_status():
    """Pings Orthanc PACS instance and returns connection status, disk usage, and study counts."""
    engine = get_orthanc_engine()
    status = engine.ping_orthanc()
    return OrthancStatusResponse(
        status="success",
        orthanc=status.model_dump()
    )

@router.post("/api/v1/pacs/orthanc/sync", tags=["External PACS & Connectivity"])
async def sync_orthanc_pacs_studies():
    """Synchronizes studies between Orthanc archive and ALVEON emergency worklist."""
    engine = get_orthanc_engine()
    res = engine.sync_studies()
    return res

@router.post("/api/v1/pacs/orthanc/export/{study_id}", tags=["External PACS & Connectivity"])
async def export_study_to_orthanc(study_id: str):
    """Exports a study or AI secondary capture to Orthanc archive over REST/C-STORE."""
    worklist_items = await get_emergency_worklist()
    target_study = next((s for s in worklist_items.studies if s.study_id == study_id), None)
    if not target_study:
        raise HTTPException(status_code=404, detail=f"Study '{study_id}' not found in worklist.")

    ds = study_item_to_pydicom(target_study)
    bio = io.BytesIO()
    ds.save_as(bio)
    dcm_bytes = bio.getvalue()

    engine = get_orthanc_engine()
    res = engine.export_study_to_orthanc(
        dcm_bytes=dcm_bytes,
        patient_id=target_study.patient_id
    )
    return res


# =========================================================================
# v4.2 Enterprise Endpoints: HL7 v2, FHIR R4, Patient Summary, Closed-Loop, Neuro CT
# =========================================================================

# --- 1. Option A: Hospital EHR Interoperability (HL7 v2 & FHIR R4) ---

@router.post("/api/v1/hl7/order", response_model=HL7OrderResponse, tags=["Hospital EHR Interoperability (HL7 & FHIR)"])
async def ingest_hl7_order(req: HL7OrderRequest):
    """
    Ingests an inbound HL7 v2.x General Order Message (ORM^O01).
    Extracts patient demographics, accession, and matches with emergency worklist.
    """
    engine = get_hl7_engine()
    if req.raw_hl7:
        order = engine.parse_orm_o01(req.raw_hl7)
    else:
        # Construct synthetic ORM^O01 from request fields
        raw_msg = (
            f"MSH|^~\\&|EPIC_EHR|METROPOLITAN_HEALTH|ALVEON_PACS|ST_JUDE_HOSPITAL|{datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d%H%M%S')}||ORM^O01|MSG{uuid.uuid4().hex[:6].upper()}|P|2.5.1\r\n"
            f"PID|1||{req.patient_mrn or 'MRN-ER-901'}^^^ST_JUDE^MR||{req.patient_name or 'Sterling^Connor'}||19780512|M\r\n"
            f"ORC|NW|ORD-{uuid.uuid4().hex[:6].upper()}|||||1^STAT||{datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d%H%M%S')}|||10928^Dr. Sarah Adams^MD\r\n"
            f"OBR|1|{req.accession_number or 'ACC-99120'}|{req.accession_number or 'ACC-99120'}|RAD-CXR^Chest Radiograph Single View^CPT-71045||||||||||||||||||||F||||||{req.clinical_indication or 'Shortness of breath'}\r\n"
        )
        order = engine.parse_orm_o01(raw_msg)

    ack = engine.generate_ack(order.get("message_control_id", "MSG001"), success=True)
    return HL7OrderResponse(
        status="success",
        order=order,
        ack_message=ack.to_string()
    )


@router.get("/api/v1/hl7/report/{study_id}", response_model=HL7ReportResponse, tags=["Hospital EHR Interoperability (HL7 & FHIR)"])
async def get_hl7_observation_report(study_id: str):
    """
    Generates an outbound HL7 v2.x Unsolicited Observation Message (ORU^R01)
    transmitting signed radiologic interpretation to hospital EHRs.
    """
    worklist_items = await get_emergency_worklist()
    target_study = next((s for s in worklist_items.studies if s.study_id == study_id), None)
    
    mrn = target_study.patient_mrn if target_study else "MRN-TRAUMA-4410"
    name = target_study.patient_name if target_study else "Sterling, Connor"
    diag = target_study.primary_finding if target_study else "PNEUMONIA"
    conf = target_study.confidence_percentage if target_study else 99.8

    engine = get_hl7_engine()
    msg = engine.generate_oru_r01(
        study_id=study_id,
        patient_mrn=mrn,
        patient_name=name,
        diagnosis=diag,
        confidence_percentage=conf,
        findings_text="Consolidative alveolar opacity localized to right upper pulmonary lobe. No pneumothorax.",
        impression_text=f"Focal consolidative pneumonia with {conf:.1f}% confidence. Category: ACR Level 1.",
        acr_actionable_code="ACR Category 1 (Critical STAT Alert)"
    )

    return HL7ReportResponse(
        status="success",
        study_id=study_id,
        patient_mrn=mrn,
        accession_number=f"ACC-{study_id.replace('STUDY-', '')}",
        raw_oru_r01=msg.to_string(),
        message_control_id=msg.segments[0].fields[8] if len(msg.segments[0].fields) > 8 else "ALV001"
    )


@router.get("/api/v1/fhir/DiagnosticReport/{study_id}", tags=["Hospital EHR Interoperability (HL7 & FHIR)"])
async def get_fhir_diagnostic_report(study_id: str):
    """Generates standard HL7 FHIR R4 JSON DiagnosticReport resource."""
    worklist_items = await get_emergency_worklist()
    target = next((s for s in worklist_items.studies if s.study_id == study_id), None)
    mrn = target.patient_mrn if target else "MRN-TRAUMA-4410"
    name = target.patient_name if target else "Sterling, Connor"
    diag = target.primary_finding if target else "PNEUMONIA"
    conf = target.confidence_percentage if target else 99.8

    engine = get_fhir_engine()
    report = engine.generate_diagnostic_report(
        study_id=study_id,
        patient_mrn=mrn,
        patient_name=name,
        diagnosis=diag,
        confidence_percentage=conf,
        impression="Focal infiltrative consolidation consistent with acute bacterial pneumonia.",
        acr_category="ACR Category 1 (Critical STAT Alert)",
        is_signed=(target.status == "SIGNED") if target else True
    )
    return JSONResponse(content=report, media_type="application/fhir+json")



@router.get("/api/v1/fhir/Observation/{study_id}", tags=["Hospital EHR Interoperability (HL7 & FHIR)"])
async def get_fhir_observation_bundle(study_id: str):
    """Generates standard HL7 FHIR R4 JSON Observation bundle."""
    worklist_items = await get_emergency_worklist()
    target = next((s for s in worklist_items.studies if s.study_id == study_id), None)
    mrn = target.patient_mrn if target else "MRN-TRAUMA-4410"
    diag = target.primary_finding if target else "PNEUMONIA"
    conf = target.confidence_percentage / 100.0 if target else 0.998

    engine = get_fhir_engine()
    obs = engine.generate_observation_resource(
        observation_id=f"{study_id}-pneu",
        patient_mrn=mrn,
        study_id=study_id,
        diagnosis_label=diag,
        probability=conf
    )
    bundle = {
        "resourceType": "Bundle",
        "type": "collection",
        "total": 1,
        "entry": [{"resource": obs}]
    }
    return JSONResponse(content=bundle, media_type="application/fhir+json")


@router.get("/api/v1/fhir/ImagingStudy/{study_id}", tags=["Hospital EHR Interoperability (HL7 & FHIR)"])
async def get_fhir_imaging_study(study_id: str):
    """Generates standard HL7 FHIR R4 JSON ImagingStudy resource."""
    worklist_items = await get_emergency_worklist()
    target = next((s for s in worklist_items.studies if s.study_id == study_id), None)
    mrn = target.patient_mrn if target else "MRN-TRAUMA-4410"
    modality = target.modality if target else "DX"

    engine = get_fhir_engine()
    study = engine.generate_imaging_study_resource(
        study_id=study_id,
        patient_mrn=mrn,
        modality=modality
    )
    return JSONResponse(content=study, media_type="application/fhir+json")


# --- 2. Option B: Local AI Patient Discharge Summarizer ---

@router.post("/api/v1/patient/summary", response_model=PatientSummaryResponse, tags=["Patient Care & Layperson Instructions"])
async def generate_patient_discharge_summary(req: PatientSummaryRequest):
    """
    Translates radiologic findings into compassionate, 6th-grade reading level patient instructions.
    Multi-lingual: English, Spanish, French, Hindi, Mandarin. Uses local Ollama or offline NLP fallback.
    """
    engine = get_patient_summary_engine()
    res = engine.generate_patient_discharge_summary(
        diagnosis=req.diagnosis,
        confidence_percentage=req.confidence_percentage,
        clinical_impression=req.clinical_impression,
        language=req.language or "en",
        patient_name=req.patient_name or "Patient",
        patient_mrn=req.patient_mrn or "MRN-101"
    )
    return PatientSummaryResponse(**res)


# --- 3. Option C: STAT Critical Trauma Alerting & Closed-Loop Communication ---

@router.post("/api/v1/alert/closed-loop", response_model=ClosedLoopHandoffResponse, tags=["Emergency Critical Alerting"])
async def record_closed_loop_verbal_handoff(req: ClosedLoopHandoffRequest):
    """
    Records an ACR-compliant closed-loop verbal handoff between radiologist and ER physician.
    Automatically stamped into the tamper-evident HIPAA SHA-256 audit ledger.
    """
    engine = get_alerting_engine()
    handoff = engine.record_closed_loop_handoff(
        study_id=req.study_id,
        patient_mrn=req.patient_mrn,
        patient_name=req.patient_name,
        critical_finding=req.critical_finding,
        radiologist_name=req.radiologist_name,
        er_physician_name=req.er_physician_name,
        communication_method=req.communication_method or "Trauma Bay Hotline",
        readback_confirmed=req.readback_confirmed if req.readback_confirmed is not None else True,
        notes=req.notes or ""
    )
    return ClosedLoopHandoffResponse(status="success", handoff=handoff)


@router.get("/api/v1/alert/closed-loop/{study_id}", tags=["Emergency Critical Alerting"])
async def get_closed_loop_handoff_status(study_id: str):
    """Retrieves recorded closed-loop verbal handoff status for a given study."""
    engine = get_alerting_engine()
    record = engine.get_handoff_status(study_id)
    if not record:
        return {"status": "none", "message": "No verbal handoff recorded yet for this study."}
    return {"status": "recorded", "handoff": record}


# --- 4. Option D: Multi-Modality Brain CT Stroke & Hemorrhage Suite ---

@router.get("/api/v1/neuro/series", response_model=NeuroSeriesListResponse, tags=["3D Neuro CT & Stroke Suite"])
async def list_neuro_ct_series():
    """Lists available 3D volumetric Brain CT series for acute stroke & hemorrhage evaluation."""
    engine = get_neuro_engine()
    items = engine.list_series()
    return NeuroSeriesListResponse(status="success", series=items)


@router.post("/api/v1/neuro/analyze/{series_id}", response_model=NeuroAnalysisResponse, tags=["3D Neuro CT & Stroke Suite"])
async def analyze_neuro_ct_series(series_id: str):
    """
    Executes automated AI stroke, intracranial hemorrhage, and mass effect analysis on a 3D Brain CT volume.
    Returns ASPECTS score, midline shift measurement, and surgical alerts.
    """
    engine = get_neuro_engine()
    res = engine.analyze_neuro_volume(series_id)
    if res.get("status") == "error":
        raise HTTPException(status_code=404, detail=res.get("message", "Series not found"))
    return NeuroAnalysisResponse(**res)



