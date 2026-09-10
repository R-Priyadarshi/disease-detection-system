from typing import Optional, List, Any
from pydantic import BaseModel, Field

class HealthResponse(BaseModel):
    status: str = Field("healthy", description="API health status")
    project_name: str
    version: str
    model_loaded: bool
    tensorflow_version: str
    device: str

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
    patient_id: str = "PNT-2026-X01"
    patient_name: str = "Patient Anonymous"
    patient_age: int = 42
    patient_gender: str = "Unspecified"
    referring_physician: str = "Attending Pulmonologist"
    clinical_notes: Optional[str] = "Routine post-acute radiograph evaluation"
    diagnosis: str
    confidence_percentage: float
    risk_tier: str
    clinical_recommendation: str
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
