import os
import uuid
import datetime
from pathlib import Path
from typing import Optional
import numpy as np
import tensorflow as tf
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse

from core.config import settings
from core.model import get_model, PneumoniaCNNModel
from core.preprocessor import preprocessor, ImagePreprocessingError
from core.gradcam import GradCAMGenerator
from core.sample_generator import ensure_sample_assets
from api.schemas import (
    HealthResponse,
    PredictionResponse,
    AnatomicalZonation,
    SamplesListResponse,
    SampleItem,
    ClinicalReportRequest,
    ClinicalReportResponse,
    ErrorResponse
)

router = APIRouter()

_model: Optional[PneumoniaCNNModel] = None
_gradcam: Optional[GradCAMGenerator] = None

def get_engine():
    global _model, _gradcam
    if _model is None:
        _model = get_model()
        _gradcam = GradCAMGenerator(_model)
    return _model, _gradcam

@router.get("/health", response_model=HealthResponse, tags=["System Diagnostics"])
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
    file: UploadFile = File(..., description="Chest radiograph file (JPEG, PNG, WEBP, TIFF)"),
    apply_clahe: bool = Form(False, description="Apply CLAHE contrast enhancement for soft tissue visualization"),
    colormap: str = Form("inferno", description="Medical colormap: inferno (default), viridis, plasma, hot, jet"),
    heatmap_alpha: float = Form(0.45, description="Grad-CAM overlay blending opacity [0.1, 0.9]")
):
    """
    Evaluates a thoracic radiograph, executes forward neural pass, calculates
    pulmonary anatomical zonation distribution, and synthesizes Grad-CAM heatmaps.
    """
    model, gradcam = get_engine()

    valid_extensions = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff"}
    file_ext = Path(file.filename or "upload.jpg").suffix.lower()
    if file_ext not in valid_extensions and file.content_type and not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format '{file_ext}'. Please upload standard medical images (JPEG, PNG, TIFF)."
        )

    try:
        image_bytes = await file.read()
        if len(image_bytes) == 0:
            raise HTTPException(status_code=400, detail="Uploaded file buffer is empty.")

        # 1. Medical preprocessing & normalization
        tensor, raw_gray = preprocessor.prepare_tensor(image_bytes, apply_clahe=apply_clahe)

        # 2. Forward inference pass
        inference_result = model.predict_tensor(tensor)

        # 3. Grad-CAM synthesis with chosen medical colormap & zonation
        blended_bgr, heatmap_bgr, zonation = gradcam.generate_overlay(
            original_gray=raw_gray,
            tensor=tensor,
            colormap_name=colormap,
            alpha=float(np.clip(heatmap_alpha, 0.1, 0.9))
        )

        # 4. High-efficiency base64 encoding
        orig_b64 = preprocessor.to_base64_jpeg(raw_gray)
        blended_b64 = preprocessor.to_base64_jpeg(blended_bgr)
        heatmap_b64 = preprocessor.to_base64_jpeg(heatmap_bgr)

        return PredictionResponse(
            filename=file.filename or "radiograph.jpg",
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
            gradcam_heatmap_b64=heatmap_b64
        )

    except HTTPException:
        raise
    except ImagePreprocessingError as e:
        raise HTTPException(status_code=422, detail=f"Radiograph decoding failed: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Inference execution error: {str(e)}")

@router.get("/api/v1/samples", response_model=SamplesListResponse, tags=["PACS Verification Samples"])
async def get_sample_radiographs():
    """Serves calibrated verification radiographs for rapid clinical validation."""
    ensure_sample_assets()
    samples_dir = settings.SAMPLES_DIR

    normal_path = samples_dir / "sample_normal.jpg"
    pneumonia_path = samples_dir / "sample_pneumonia.jpg"

    samples = []
    if normal_path.exists():
        raw_norm = preprocessor.load_image(str(normal_path))
        norm_b64 = preprocessor.to_base64_jpeg(raw_norm)
        samples.append(SampleItem(
            id="sample_normal",
            title="Calibrated Normal Film",
            expected_condition="NORMAL",
            description="Clear bilateral pulmonary parenchyma, sharp costophrenic recesses, normal mediastinal silhouette.",
            image_b64=norm_b64
        ))

    if pneumonia_path.exists():
        raw_pneu = preprocessor.load_image(str(pneumonia_path))
        pneu_b64 = preprocessor.to_base64_jpeg(raw_pneu)
        samples.append(SampleItem(
            id="sample_pneumonia",
            title="Consolidative Infiltrate Film",
            expected_condition="PNEUMONIA",
            description="Dense alveolar airspace consolidation localized predominantly in right lower/mid pulmonary zone.",
            image_b64=pneu_b64
        ))

    return SamplesListResponse(samples=samples)

@router.post("/api/v1/report", response_model=ClinicalReportResponse, tags=["Consultation Reporting"])
async def generate_clinical_report(report_data: ClinicalReportRequest):
    """Formats an official, hospital-grade radiology consultation note."""
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
