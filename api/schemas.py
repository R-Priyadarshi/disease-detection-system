from typing import Optional, List, Any, Dict
from pydantic import BaseModel, Field

class HealthResponse(BaseModel):
    status: str = Field("healthy", description="API health status")
    project_name: str
    system_title: str
    version: str
    model_loaded: bool
    tensorflow_version: str
    device: str

class AnatomicalZonation(BaseModel):
    right_upper_lobe_pct: float = Field(..., description="Right upper quadrant opacity percentage")
    right_lower_lobe_pct: float = Field(..., description="Right lower quadrant opacity percentage")
    left_upper_lobe_pct: float = Field(..., description="Left upper quadrant opacity percentage")
    left_lower_lobe_pct: float = Field(..., description="Left lower quadrant opacity percentage")
    dominant_zone: str = Field(..., description="Anatomical zone with highest radiographic activation")

class PredictionResponse(BaseModel):
    status: str = "success"
    filename: str
    diagnosis: str = Field(..., description="'PNEUMONIA' or 'NORMAL'")
    is_pneumonia: bool
    probability: float = Field(..., description="Raw model sigmoid output [0.0, 1.0]")
    confidence_percentage: float = Field(..., description="Confidence score [0.0, 100.0]%")
    risk_tier: str
    clinical_recommendation: str
    latency_ms: float
    colormap: str = "inferno"
    zonation: AnatomicalZonation
    original_image_b64: str
    gradcam_overlay_b64: Optional[str] = None
    gradcam_heatmap_b64: Optional[str] = None

class SampleItem(BaseModel):
    id: str
    title: str
    expected_condition: str
    description: str
    image_b64: str

class SamplesListResponse(BaseModel):
    status: str = "success"
    samples: List[SampleItem]

class ClinicalReportRequest(BaseModel):
    patient_id: str = "ALV-2026-X84"
    patient_name: str = "Patient Anonymous"
    patient_age: int = 48
    patient_gender: str = "M"
    referring_physician: str = "Dr. Attending Pulmonologist"
    clinical_notes: Optional[str] = "Acute presentation with productive cough, dyspnea, and fever."
    diagnosis: str
    confidence_percentage: float
    risk_tier: str
    clinical_recommendation: str
    dominant_zone: Optional[str] = "Right Lower Lobe"
    zonation: Optional[Dict[str, Any]] = None
    original_image_b64: str
    gradcam_overlay_b64: str

class ClinicalReportResponse(BaseModel):
    status: str = "success"
    report_id: str
    timestamp: str
    summary_html: str

class ErrorResponse(BaseModel):
    status: str = "error"
    message: str
    detail: Optional[Any] = None
