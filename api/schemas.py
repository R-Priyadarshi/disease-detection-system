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

class DicomMetadataModel(BaseModel):
    is_dicom: bool = True
    patient_id: str = "ALV-STAT-09"
    patient_name: str = "Anonymous Patient"
    patient_age: str = "048Y"
    patient_sex: str = "F"
    study_date: str = "20260910"
    study_time: str = "143000"
    modality: str = "DX"
    body_part_examined: str = "CHEST"
    view_position: str = "PA"
    kvp: str = "125 kVp"
    exposure_time: str = "14 ms"
    tube_current: str = "300 mA"
    institution_name: str = "ALVEON Regional Medical Center"
    station_name: str = "STAT-PACS-01"
    photometric_interpretation: str = "MONOCHROME2"
    window_center: int = 128
    window_width: int = 256
    rows: int = 150
    columns: int = 150
    bits_allocated: int = 16
    bits_stored: int = 12
    transfer_syntax_uid: str = "1.2.840.10008.1.2.1"
    sop_instance_uid: Optional[str] = None

class MultiLabelFindingItem(BaseModel):
    name: str = Field(..., description="Standard pathology identifier (e.g. PNEUMOTHORAX, PNEUMONIA)")
    display_name: str = Field(..., description="Human-readable clinical finding title")
    probability: float = Field(..., description="Independent sigmoid probability [0.0, 1.0]")
    confidence_percentage: float = Field(..., description="Calibrated confidence [0.0, 100.0]%")
    is_detected: bool = Field(..., description="True if probability exceeds clinical decision threshold")
    severity: str = Field(..., description="'CRITICAL', 'URGENT', 'WARNING', 'BENIGN', or 'NORMAL'")
    clinical_description: str
    anatomical_focus: str

class PredictionResponse(BaseModel):
    status: str = "success"
    filename: str
    diagnosis: str = Field(..., description="'PNEUMONIA' or 'NORMAL' (backward compatible)")
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
    dicom_metadata: Optional[DicomMetadataModel] = None
    primary_finding: Optional[str] = None
    primary_display_name: Optional[str] = None
    secondary_findings: Optional[List[str]] = None
    findings: Optional[List[MultiLabelFindingItem]] = None
    clinical_impression: Optional[str] = None

class WorklistStudyItem(BaseModel):
    study_id: str
    patient_mrn: str
    patient_name: str
    patient_age_sex: str
    study_time: str
    priority: str = Field(..., description="'STAT_CRITICAL', 'URGENT', or 'ROUTINE'")
    priority_rank: int = Field(..., description="1 = STAT, 2 = Urgent, 3 = Routine")
    diagnosis: str
    is_pneumonia: bool
    confidence_percentage: float
    dominant_zone: str
    status: str = Field("PENDING", description="'PENDING' or 'SIGNED'")
    is_signed: bool = False
    modality: str = "DX"
    image_b64: str
    gradcam_overlay_b64: Optional[str] = None
    zonation: Optional[AnatomicalZonation] = None
    dicom_metadata: Optional[DicomMetadataModel] = None
    primary_finding: Optional[str] = None
    secondary_findings: Optional[List[str]] = None
    findings: Optional[List[MultiLabelFindingItem]] = None

class PacsNodeConfig(BaseModel):
    name: str = "Local PACS Listener"
    host: str = "127.0.0.1"
    port: int = 11112
    ae_title: str = "ALVEON_PACS"

class PacsPingRequest(BaseModel):
    host: str = "127.0.0.1"
    port: int = 11112
    ae_title: str = "ALVEON_PACS"

class PacsPushRequest(BaseModel):
    study_id: str
    host: str = "127.0.0.1"
    port: int = 11112
    ae_title: str = "ALVEON_PACS"

class WorklistResponse(BaseModel):
    status: str = "success"
    total_cases: int
    stat_critical_count: int
    pending_count: int
    studies: List[WorklistStudyItem]

class SignoffRequest(BaseModel):
    study_id: str

    physician_name: str = "Dr. Attending Radiologist, MD"
    physician_license: str = "ABR-984210"
    clinical_notes: Optional[str] = "Radiologic findings verified. Alveolar consolidation confirmed on Grad-CAM localization."

class SignoffResponse(BaseModel):
    status: str = "success"
    study_id: str
    timestamp: str
    physician_signature: str
    signoff_badge: str
    audit_hash: str

class BatchTriageResponse(BaseModel):
    status: str = "success"
    total_ingested: int
    critical_stat_count: int
    triaged_studies: List[WorklistStudyItem]

class SampleItem(BaseModel):
    id: str
    title: str
    expected_condition: str
    description: str
    image_b64: str
    is_dicom: bool = False

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
    dicom_metadata: Optional[Dict[str, Any]] = None

class ClinicalReportResponse(BaseModel):
    status: str = "success"
    report_id: str
    timestamp: str
    summary_html: str

class ErrorResponse(BaseModel):
    status: str = "error"
    message: str
    detail: Optional[Any] = None

class BatchDeleteRequest(BaseModel):
    study_ids: List[str]

class BatchDeleteResponse(BaseModel):
    status: str = "success"
    deleted_count: int
    remaining_count: int

# =========================================================================
# v4.0 Enterprise Schemas: Auth, HIPAA Audit, 3D Volumetric, Modality Simulator
# =========================================================================

class LoginRequest(BaseModel):
    username: str
    password: Optional[str] = "clinical_demo_pass"

class ClinicalUserSchema(BaseModel):
    user_id: str
    username: str
    full_name: str
    title: str
    role: str
    department: str
    npi: Optional[str] = None
    initials: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 86400
    user: ClinicalUserSchema

class AuditLogItem(BaseModel):
    event_id: str
    timestamp_utc: str
    timestamp_epoch: float
    user_id: str
    username: str
    user_role: str
    action: str
    patient_mrn: Optional[str] = None
    study_id: Optional[str] = None
    ip_address: str
    details: Dict[str, Any] = Field(default_factory=dict)
    prev_hash: str
    record_hash: str

class AuditQueryResponse(BaseModel):
    status: str = "success"
    total_returned: int
    events: List[AuditLogItem]

class AuditVerifyResponse(BaseModel):
    is_valid: bool
    total_events: int
    latest_hash: Optional[str] = None
    message: str

class VolumetricSeriesItem(BaseModel):
    series_id: str
    patient_id: str
    patient_name: str
    modality: str
    description: str
    num_slices: int
    dimensions: List[int]
    slice_thickness_mm: float
    pixel_spacing_mm: List[float]
    default_window: str = "LUNG"

class VolumetricSeriesListResponse(BaseModel):
    status: str = "success"
    total_series: int
    series: List[VolumetricSeriesItem]

class VolumetricSliceResponse(BaseModel):
    status: str = "success"
    series_id: str
    orientation: str
    slice_index: int
    max_slices: int
    slice_location_mm: float
    window_preset: str
    window_width: int
    window_level: int
    mean_hu: float
    data_url: str

class VolumetricMPRRequest(BaseModel):
    axial_idx: int = 16
    coronal_idx: int = 80
    sagittal_idx: int = 80
    window_preset: str = "LUNG"

class VolumetricMPRResponse(BaseModel):
    status: str = "success"
    series_id: str
    window_preset: str
    crosshairs: Dict[str, int]
    axial: Dict[str, Any]
    coronal: Dict[str, Any]
    sagittal: Dict[str, Any]

class SimulateModalityRequest(BaseModel):
    modality_key: str = "XR_EMERGENCY_BAY_1"
    study_idx: int = 0
    target_port: int = 11112

class SimulateModalityResponse(BaseModel):
    status: str = "success"
    success: bool
    status_code: str
    modality_device: Dict[str, Any]
    study_transmitted: Dict[str, Any]
    target_node: str
    network_latency_ms: float
    sop_instance_uid: str
    timestamp: str

# =========================================================================
# v4.1 Enterprise Schemas: Voice Dictation, RADLEX, Orthanc, Probes
# =========================================================================

class VoiceDictationRequest(BaseModel):
    transcript: str
    study_id: Optional[str] = None
    current_report: Optional[Dict[str, Any]] = None

class VoiceDictationResponse(BaseModel):
    status: str = "success"
    command_detected: Optional[str] = None
    target_field: Optional[str] = None
    transcribed_text: str
    action_executed: str
    structured_report: Dict[str, Any]

class StructuredReportRequest(BaseModel):
    study_id: Optional[str] = None
    patient_name: Optional[str] = "Anonymous Patient"
    patient_mrn: Optional[str] = "MRN-UNKNOWN"
    diagnosis: Optional[str] = "NORMAL"
    confidence_percentage: Optional[float] = 95.0
    all_findings: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    zonation: Optional[Dict[str, Any]] = Field(default_factory=dict)
    structured_report: Optional[Dict[str, Any]] = None

class StructuredReportResponse(BaseModel):
    status: str = "success"
    structured_report: Dict[str, Any]

class OrthancStatusResponse(BaseModel):
    status: str = "success"
    orthanc: Dict[str, Any]

class HealthProbeResponse(BaseModel):
    status: str = "healthy"
    timestamp: str
    version: str = "4.2.0"
    components: Dict[str, str] = Field(default_factory=dict)

# =========================================================================
# v4.2 Enterprise Schemas: HL7 v2, FHIR R4, Patient Summary, Closed-Loop, Neuro CT
# =========================================================================

class HL7OrderRequest(BaseModel):
    raw_hl7: Optional[str] = None
    patient_mrn: Optional[str] = None
    patient_name: Optional[str] = None
    accession_number: Optional[str] = None
    clinical_indication: Optional[str] = None

class HL7OrderResponse(BaseModel):
    status: str = "success"
    order: Dict[str, Any]
    ack_message: str

class HL7ReportResponse(BaseModel):
    status: str = "success"
    study_id: str
    patient_mrn: str
    accession_number: str
    raw_oru_r01: str
    message_control_id: str

class PatientSummaryRequest(BaseModel):
    diagnosis: str
    confidence_percentage: Optional[float] = 98.0
    clinical_impression: Optional[str] = ""
    language: Optional[str] = "en"
    patient_name: Optional[str] = "Patient"
    patient_mrn: Optional[str] = "MRN-101"

class PatientSummaryResponse(BaseModel):
    status: str = "success"
    ai_engine: str
    language: str
    patient_mrn: str
    patient_name: str
    reading_level: str
    title: str
    what_was_found: str
    what_you_need_to_do: str
    warning_signs: str
    follow_up: str
    disclaimer: str
    timestamp: str

class ClosedLoopHandoffRequest(BaseModel):
    study_id: str
    patient_mrn: str
    patient_name: str
    critical_finding: str
    radiologist_name: str
    er_physician_name: str
    communication_method: Optional[str] = "Trauma Bay Hotline"
    readback_confirmed: Optional[bool] = True
    notes: Optional[str] = ""

class ClosedLoopHandoffResponse(BaseModel):
    status: str = "success"
    handoff: Dict[str, Any]

class NeuroSeriesItem(BaseModel):
    series_id: str
    patient_mrn: str
    patient_name: str
    patient_age_sex: str
    primary_neuro_finding: str
    aspects_score: Optional[int] = None
    midline_shift_mm: float = 0.0
    matrix_shape: List[int]
    modality: str = "CT (Non-Contrast Head)"

class NeuroSeriesListResponse(BaseModel):
    status: str = "success"
    series: List[NeuroSeriesItem]

class NeuroAnalysisResponse(BaseModel):
    status: str = "success"
    series_id: str
    patient_mrn: str
    patient_name: str
    modality: str
    primary_diagnosis: str
    aspects_score: Optional[int] = None
    midline_shift_mm: float
    critical_neurosurgical_alert: bool
    acr_category: str
    recommended_action: str
    hu_window_presets: Dict[str, Any]

# --- Enterprise Modality Router Schemas ---

class ModalityItem(BaseModel):
    modality_id: str
    name: str
    ae_title: str
    host: str
    port: int
    modality_type: str
    department: str
    status: str
    last_ping_ms: Optional[float] = None
    last_verified_at: Optional[str] = None
    transfer_syntaxes: Optional[List[str]] = None

class ModalityListResponse(BaseModel):
    status: str = "success"
    modalities: List[Dict[str, Any]]

class ModalityVerifyRequest(BaseModel):
    modality_id: Optional[str] = None
    ae_title: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None

class ModalityVerifyResponse(BaseModel):
    status: str = "success"
    verification: Dict[str, Any]

class ModalityQueryRetrieveRequest(BaseModel):
    modality_id: str
    study_instance_uid: Optional[str] = None
    patient_mrn: Optional[str] = None
    patient_name: Optional[str] = None

class ModalityQueryRetrieveResponse(BaseModel):
    status: str = "success"
    message: str
    retrieval_log: Dict[str, Any]

class RoutingRuleItem(BaseModel):
    rule_id: str
    name: str
    condition_type: str
    condition_value: str
    target_modality_id: str
    enabled: bool = True
    priority: int = 1

class RoutingRulesResponse(BaseModel):
    status: str = "success"
    rules: List[Dict[str, Any]]

class ModalityRouteRequest(BaseModel):
    study_id: str
    target_modality_id: Optional[str] = None
    patient_mrn: Optional[str] = None
    primary_finding: Optional[str] = None

class ModalityRouteResponse(BaseModel):
    status: str = "success"
    dispatched: List[Dict[str, Any]]

# --- Longitudinal Prior Comparison Schemas ---

class PriorCompareRequest(BaseModel):
    current_study_id: Optional[str] = None
    prior_study_id: Optional[str] = None
    patient_mrn: Optional[str] = "MRN-TRAUMA-4410"
    current_image_b64: Optional[str] = None
    prior_image_b64: Optional[str] = None

class PriorCompareResponse(BaseModel):
    status: str = "success"
    patient_mrn: str
    current_study_date: str
    prior_study_date: str
    registration_status: str
    interval_assessment: str
    interval_delta_pct: float
    current_density_score: float
    prior_density_score: float
    clinical_summary: str
    prior_image_b64: str
    subtraction_heatmap_b64: str
    resolution_clearance_pct: float
    analyzed_at: str

# --- DICOM Part 16 Structured Reporting (TID 1500) Schemas ---

class DicomSRGenerateRequest(BaseModel):
    study_id: str
    patient_mrn: Optional[str] = "MRN-TRAUMA-4410"
    patient_name: Optional[str] = "Elena Rostova"
    patient_sex: Optional[str] = "F"
    primary_finding: Optional[str] = "PNEUMOTHORAX"
    confidence_percentage: Optional[float] = 99.8
    caliper_measurements: Optional[List[Dict[str, Any]]] = None
    ctr_index: Optional[float] = 0.46
    acr_category: Optional[str] = "ACR Category 1 (Critical STAT Alert)"
    radiologist_name: Optional[str] = "Dr. S. Vance, MD"

class DicomSRGenerateResponse(BaseModel):
    status: str = "success"
    study_id: str
    filename: str
    file_size_bytes: int
    sop_instance_uid: str
    download_url: str
    standard_conformance: str = "DICOM PS 3.16 / TID 1500"

class DicomSRForwardRequest(BaseModel):
    study_id: str
    target_modality_id: Optional[str] = "PACS-ORTHANC"
    target_ae_title: Optional[str] = "ORTHANC_VNA"

class DicomSRForwardResponse(BaseModel):
    status: str = "success"
    message: str
    forward_details: Dict[str, Any]

# --- HIPAA Safe-Harbor DICOM De-Identification & Anonymizer Schemas ---

class AnonymizeRequest(BaseModel):
    study_id: Optional[str] = None
    input_dicom_path: Optional[str] = None
    custom_patient_name: Optional[str] = None
    pseudonym: Optional[str] = None
    custom_patient_id: Optional[str] = None
    patient_id: Optional[str] = None
    custom_accession_number: Optional[str] = None
    keep_patient_age: bool = True
    keep_patient_sex: bool = True

class AnonymizeResponse(BaseModel):
    status: str = "success"
    anonymized_filename: str
    download_url: str
    sop_instance_uid: str
    study_instance_uid: str
    series_instance_uid: str
    original_patient_name: str
    anonymized_patient_name: str
    original_patient_id: str
    anonymized_patient_id: str
    hipaa_rules_cleared: int
    tags_modified_count: int
    diff_table: List[Dict[str, Any]]
    standard_conformance: str = "HIPAA § 164.514(b)(2) / DICOM PS 3.15 Annex E"
    anonymized_at: str

class AuditDeidentificationRequest(BaseModel):
    study_id: Optional[str] = None
    file_path: Optional[str] = None

class AuditDeidentificationResponse(BaseModel):
    status: str = "success"
    is_compliant: bool
    phi_detected_count: int
    phi_detected: List[Dict[str, Any]]
    hipaa_checklist: Dict[str, bool]
    recommendations: List[str]
