import os
import uuid
import datetime
from pathlib import Path
from typing import Optional
import numpy as np
import tensorflow as tf
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Query
from fastapi.responses import JSONResponse

from core.config import settings
from core.model import get_model, PneumoniaCNNModel
from core.preprocessor import preprocessor, ImagePreprocessingError
from core.gradcam import GradCAMGenerator
from core.sample_generator import ensure_sample_assets
from api.schemas import (
    HealthResponse,
    PredictionResponse,
    SamplesListResponse,
    SampleItem,
    ClinicalReportRequest,
    ClinicalReportResponse,
    ErrorResponse
)

router = APIRouter()

# Initialize model and Grad-CAM
_model: Optional[PneumoniaCNNModel] = None
_gradcam: Optional[GradCAMGenerator] = None

def get_engine():
    global _model, _gradcam
    if _model is None:
        _model = get_model()
        _gradcam = GradCAMGenerator(_model)
    return _model, _gradcam

@router.get("/health", response_model=HealthResponse, tags=["System"])
async def healthcheck():
    """System healthcheck, model initialization state, and device availability."""
    model, _ = get_engine()
    devices = tf.config.list_physical_devices('GPU')
    device_name = "GPU" if len(devices) > 0 else "CPU"
    
    return HealthResponse(
        status="healthy",
        project_name=settings.PROJECT_NAME,
        version=settings.PROJECT_VERSION,
        model_loaded=(model.model is not None),
        tensorflow_version=tf.__version__,
        device=device_name
    )

@router.post("/api/v1/predict", response_model=PredictionResponse, tags=["Diagnostic Inference"])
async def predict_chest_xray(
    file: UploadFile = File(..., description="Chest radiograph image (JPEG, PNG, WEBP, TIFF)"),
    apply_clahe: bool = Form(False, description="Apply CLAHE contrast enhancement for low-exposure films"),
    heatmap_alpha: float = Form(0.45, description="Grad-CAM overlay blending opacity [0.0, 1.0]")
):
    """
    Analyzes an uploaded chest radiograph, produces a calibrated diagnostic prediction,
    calculates clinical risk tiers, and generates Grad-CAM heatmaps for explainability.
    """
    model, gradcam = get_engine()

    # Verify content type
    valid_extensions = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff"}
    file_ext = Path(file.filename or "upload.jpg").suffix.lower()
    if file_ext not in valid_extensions and file.content_type and not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail=f"Unsupported file type '{file_ext}'. Allowed formats: JPEG, PNG, WEBP, TIFF.")

    try:
        image_bytes = await file.read()
        if len(image_bytes) == 0:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")

        # 1. Preprocess image
        tensor, raw_gray = preprocessor.prepare_tensor(image_bytes, apply_clahe=apply_clahe)

        # 2. Forward inference
        inference_result = model.predict_tensor(tensor)

        # 3. Generate Grad-CAM explanation
        blended_bgr, heatmap_bgr = gradcam.generate_overlay(
            original_gray=raw_gray,
            tensor=tensor,
            alpha=float(np.clip(heatmap_alpha, 0.1, 0.9))
        )

        # 4. Base64 encoding
        orig_b64 = preprocessor.to_base64_jpeg(raw_gray)
        blended_b64 = preprocessor.to_base64_jpeg(blended_bgr)
        heatmap_b64 = preprocessor.to_base64_jpeg(heatmap_bgr)

        return PredictionResponse(
            filename=file.filename or "uploaded_xray.jpg",
            diagnosis=inference_result["diagnosis"],
            is_pneumonia=inference_result["is_pneumonia"],
            probability=inference_result["probability"],
            confidence_percentage=inference_result["confidence_percentage"],
            risk_tier=inference_result["risk_tier"],
            clinical_recommendation=inference_result["clinical_recommendation"],
            latency_ms=inference_result["latency_ms"],
            original_image_b64=orig_b64,
            gradcam_overlay_b64=blended_b64,
            gradcam_heatmap_b64=heatmap_b64
        )

    except HTTPException:
        raise
    except ImagePreprocessingError as e:
        raise HTTPException(status_code=422, detail=f"Image processing error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Inference error: {str(e)}")

@router.get("/api/v1/samples", response_model=SamplesListResponse, tags=["Demonstration Samples"])
async def get_sample_radiographs():
    """Returns verified sample radiographs for instant demonstration."""
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
            title="Sample 1: Healthy Thoracic Radiograph",
            expected_condition="NORMAL",
            description="Clear bilateral pulmonary parenchyma, sharp costophrenic angles, normal cardiac silhouette.",
            image_b64=norm_b64
        ))

    if pneumonia_path.exists():
        raw_pneu = preprocessor.load_image(str(pneumonia_path))
        pneu_b64 = preprocessor.to_base64_jpeg(raw_pneu)
        samples.append(SampleItem(
            id="sample_pneumonia",
            title="Sample 2: Focal Consolidation (Pneumonia)",
            expected_condition="PNEUMONIA",
            description="Dense opacification and alveolar airspace consolidation localized in right lower/mid zone.",
            image_b64=pneu_b64
        ))

    return SamplesListResponse(samples=samples)

@router.post("/api/v1/report", response_model=ClinicalReportResponse, tags=["Clinical Reporting"])
async def generate_clinical_report(report_data: ClinicalReportRequest):
    """Generates an official printable clinical radiograph consultation summary."""
    report_id = f"RPT-{uuid.uuid4().hex[:8].upper()}"
    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    status_color = "#f43f5e" if report_data.diagnosis == "PNEUMONIA" else "#10b981"

    html_content = f"""
    <div class="printable-report" style="font-family: Arial, sans-serif; color: #1e293b; padding: 24px;">
        <div style="border-bottom: 2px solid #06b6d4; padding-bottom: 12px; margin-bottom: 20px;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <h1 style="font-size: 22px; margin: 0; color: #0f172a;">AI Radiology Consultation Summary</h1>
                <span style="font-weight: bold; color: #64748b;">Report ID: {report_id}</span>
            </div>
            <p style="margin: 4px 0 0 0; color: #64748b; font-size: 13px;">Generated on {timestamp} | System v{settings.PROJECT_VERSION}</p>
        </div>

        <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; background: #f8fafc; padding: 16px; border-radius: 8px; margin-bottom: 20px;">
            <div><strong>Patient ID:</strong> {report_data.patient_id}</div>
            <div><strong>Patient Name:</strong> {report_data.patient_name}</div>
            <div><strong>Demographics:</strong> {report_data.patient_age} yrs / {report_data.patient_gender}</div>
            <div><strong>Physician:</strong> {report_data.referring_physician}</div>
        </div>

        <div style="border-left: 5px solid {status_color}; background: #f1f5f9; padding: 16px; border-radius: 0 8px 8px 0; margin-bottom: 20px;">
            <div style="font-size: 18px; font-weight: bold; color: {status_color};">
                PRIMARY IMPRESSION: {report_data.diagnosis} ({report_data.confidence_percentage}% Confidence)
            </div>
            <div style="margin-top: 4px; font-size: 14px; color: #334155;">
                <strong>Risk Category:</strong> {report_data.risk_tier.replace('_', ' ')}
            </div>
            <p style="margin: 8px 0 0 0; font-size: 13px; color: #475569;">
                <strong>Recommendation:</strong> {report_data.clinical_recommendation}
            </p>
        </div>

        <div style="display: flex; gap: 20px; margin-bottom: 24px;">
            <div style="flex: 1; text-align: center;">
                <p style="font-weight: bold; margin-bottom: 6px; font-size: 13px;">Pre-Processed Radiograph</p>
                <img src="{report_data.original_image_b64}" style="width: 100%; max-width: 260px; border-radius: 6px; border: 1px solid #cbd5e1;" alt="X-ray" />
            </div>
            <div style="flex: 1; text-align: center;">
                <p style="font-weight: bold; margin-bottom: 6px; font-size: 13px;">Grad-CAM Explainability Heatmap</p>
                <img src="{report_data.gradcam_overlay_b64}" style="width: 100%; max-width: 260px; border-radius: 6px; border: 1px solid #cbd5e1;" alt="Grad-CAM" />
            </div>
        </div>

        <div style="margin-top: 30px; border-top: 1px dashed #cbd5e1; padding-top: 16px; display: flex; justify-content: space-between; font-size: 12px; color: #64748b;">
            <div>
                <em>Notice: AI assistive tool for clinical decision support. Must be validated by a board-certified radiologist.</em>
            </div>
            <div style="text-align: right; min-width: 200px;">
                <div style="border-bottom: 1px solid #000; height: 35px; margin-bottom: 4px;"></div>
                Physician Signature / Date
            </div>
        </div>
    </div>
    """

    return ClinicalReportResponse(
        report_id=report_id,
        timestamp=timestamp,
        summary_html=html_content
    )
