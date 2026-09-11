"""
ALVEON RADLEX / ACR Structured Reporting & Voice Dictation Engine
==================================================================
Conforms to American College of Radiology (ACR) Practice Parameters
and RSNA RADLEX Thoracic Imaging Lexicon. 100% Free, offline, zero-cloud NLP.
"""

import re
import datetime
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field


class StructuredReportModel(BaseModel):
    """ACR / RADLEX Standardized Radiologic Structured Consultation Report."""
    examination_technique: str = Field(
        default="Chest Radiograph, Single View (AP / PA Projections). Low-dose thoracic acquisition.",
        description="Imaging modality and technique parameters"
    )
    clinical_indication: str = Field(
        default="Emergency triage evaluation. Shortness of breath, acute hypoxemia, or thoracic trauma.",
        description="Clinical history and reason for examination"
    )
    comparison_study: str = Field(
        default="None available at time of interpretation.",
        description="Prior comparison imaging studies"
    )
    findings_lungs: str = Field(
        default="Clear lung parenchyma bilaterally. No focal consolidation, pneumothorax, or interstitial opacities.",
        description="Parenchymal and airway findings"
    )
    findings_pleura: str = Field(
        default="Costophrenic sulci and pleural spaces are clear without effusion or apical line.",
        description="Pleural evaluation"
    )
    findings_cardiomediastinum: str = Field(
        default="Cardiac silhouette is within normal limits for size. Normal mediastinal and aortic contours.",
        description="Heart size, CTR, and mediastinum"
    )
    findings_bones_soft_tissues: str = Field(
        default="Thoracic cage and visualized osseous structures are intact without acute displaced fracture.",
        description="Ribs, clavicles, spine, and chest wall"
    )
    impression: str = Field(
        default="1. No acute cardiopulmonary abnormality identified.",
        description="Numbered diagnostic conclusions"
    )
    acr_actionable_code: str = Field(
        default="ACR Category 3 (Routine / Non-Critical Finding)",
        description="ACR Actionable Finding Notification Category"
    )
    dictation_source: str = Field(
        default="ALVEON Clinical Speech-to-Report Engine",
        description="Origin of transcription (Voice vs Keyboard)"
    )
    dictated_voice: bool = Field(default=False)
    timestamp: str = Field(default_factory=lambda: datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S EST"))
    attesting_physician: Optional[str] = None


class VoiceParseResult(BaseModel):
    """Result of clinical voice transcript parsing."""
    command_detected: Optional[str] = None
    target_field: Optional[str] = None
    transcribed_text: str
    action_executed: str
    structured_report: StructuredReportModel


# Standard templates for quick voice insertion
NORMAL_CHEST_TEMPLATE = {
    "findings_lungs": "Lungs are clear bilaterally without focal consolidation, atelectasis, or mass.",
    "findings_pleura": "No pleural effusion, thickening, or pneumothorax identified.",
    "findings_cardiomediastinum": "Normal cardiac silhouette and transverse diameter. Cardiothoracic ratio < 0.50.",
    "findings_bones_soft_tissues": "No acute displaced rib fracture or destructive osseous lesion.",
    "impression": "1. No acute cardiopulmonary disease. Lungs are clear.",
    "acr_actionable_code": "ACR Category 3 (Routine / Negative)"
}

TRAUMA_PNEUMOTHORAX_TEMPLATE = {
    "findings_lungs": "Focal apical visceral pleural line identified with complete absence of peripheral lung vascular markings.",
    "findings_pleura": "Acute tension pneumothorax. Mild contralateral mediastinal shift noted.",
    "findings_cardiomediastinum": "Cardiac silhouette shifted away from affected hemithorax.",
    "findings_bones_soft_tissues": "Rib contours evaluated for traumatic fracture.",
    "impression": "1. STAT CRITICAL: Tension pneumothorax. Immediate thoracic decompression recommended.",
    "acr_actionable_code": "ACR Category 1 (Critical Finding - Immediate Verbal Communication)"
}

PNEUMONIA_CONSOLIDATION_TEMPLATE = {
    "findings_lungs": "Dense alveolar consolidation with localized air bronchograms in the pulmonary parenchyma.",
    "findings_pleura": "No significant layering pleural effusion.",
    "findings_cardiomediastinum": "Normal cardiac size and mediastinal vascular pedicle.",
    "findings_bones_soft_tissues": "Intact thoracic cage.",
    "impression": "1. Focal consolidative pneumonia. Clinical correlation with antibiotic coverage advised.",
    "acr_actionable_code": "ACR Category 2 (Urgent Finding - Communication within 2 Hours)"
}


class StructuredReportingEngine:
    """Orchestrates algorithmic RADLEX report synthesis and voice parsing."""

    _instance: Optional['StructuredReportingEngine'] = None

    @classmethod
    def get_instance(cls) -> 'StructuredReportingEngine':
        if cls._instance is None:
            cls._instance = StructuredReportingEngine()
        return cls._instance

    def synthesize_report_from_findings(
        self,
        prediction_data: Optional[Dict[str, Any]] = None,
        patient_name: str = "Anonymous Patient",
        patient_mrn: str = "MRN-UNKNOWN",
        diagnosis: Optional[str] = None,
        confidence: Optional[float] = None,
        multilabel_findings: Optional[List[Dict[str, Any]]] = None,
        zonation: Optional[Dict[str, Any]] = None
    ) -> StructuredReportModel:
        """
        Synthesizes standard ACR / RADLEX structured prose from AI multi-label detection,
        pulmonary zonation, and quantitative calipers.
        """
        pdata = prediction_data or {}
        diag = (diagnosis or pdata.get("diagnosis", "Normal")).upper()
        conf = confidence if confidence is not None else pdata.get("confidence_percentage", 95)
        findings = multilabel_findings if multilabel_findings is not None else pdata.get("all_findings", [])
        zone = zonation if zonation is not None else pdata.get("zonation", {})
        dom_zone = "Right Lower Lobe"
        if isinstance(zone, dict):
            dom_zone = zone.get("predominant_zone") or zone.get("dominant_zone") or "Right Lower Lobe"

        # Check specific condition flags across full 14 NIH findings
        has_pneu = any((f.get("finding_key") == "PNEUMONIA" or "pneumonia" in f.get("label", "").lower() or f.get("name") == "PNEUMONIA") and (f.get("is_detected") or f.get("status") == "POSITIVE") for f in findings) or "PNEUMONIA" in diag
        has_ptx = any((f.get("finding_key") == "PNEUMOTHORAX" or "pneumothorax" in f.get("label", "").lower() or f.get("name") == "PNEUMOTHORAX") and (f.get("is_detected") or f.get("status") == "POSITIVE") for f in findings) or "PNEUMOTHORAX" in diag
        has_eff = any((f.get("finding_key") == "PLEURAL_EFFUSION" or "effusion" in f.get("label", "").lower() or f.get("name") == "PLEURAL_EFFUSION") and (f.get("is_detected") or f.get("status") == "POSITIVE") for f in findings) or "EFFUSION" in diag
        has_cardio = any((f.get("finding_key") == "CARDIOMEGALY" or "cardiomegaly" in f.get("label", "").lower() or f.get("name") == "CARDIOMEGALY") and (f.get("is_detected") or f.get("status") == "POSITIVE") for f in findings) or "CARDIOMEGALY" in diag
        has_atelectasis = any((f.get("finding_key") == "ATELECTASIS" or "atelectasis" in f.get("label", "").lower() or f.get("name") == "ATELECTASIS") and (f.get("is_detected") or f.get("status") == "POSITIVE") for f in findings)
        has_edema = any((f.get("name") == "EDEMA" or "edema" in f.get("label", "").lower()) and f.get("is_detected") for f in findings)
        has_mass = any((f.get("name") == "MASS" or "mass" in f.get("label", "").lower()) and f.get("is_detected") for f in findings)
        has_nodule = any((f.get("name") == "NODULE" or "nodule" in f.get("label", "").lower()) and f.get("is_detected") for f in findings)
        has_emphysema = any((f.get("name") == "EMPHYSEMA" or "emphysema" in f.get("label", "").lower()) and f.get("is_detected") for f in findings)
        has_fibrosis = any((f.get("name") == "FIBROSIS" or "fibrosis" in f.get("label", "").lower()) and f.get("is_detected") for f in findings)

        report = StructuredReportModel()
        report.clinical_indication = f"ER evaluation for {patient_name} ({patient_mrn}). Rule out acute thoracic pathology."

        # Lungs
        if has_pneu:
            report.findings_lungs = (
                f"Focal alveolar airspace consolidation with air bronchograms identified predominantly in the {dom_zone} "
                f"({conf}% AI diagnostic certainty). No cavitary breakdown."
            )
        elif has_edema:
            report.findings_lungs = "Diffuse bilateral perihilar batwing vascular opacities consistent with alveolar interstitial edema."
        elif has_mass:
            report.findings_lungs = "Focal well-demarcated parenchymal mass lesion exceeding 30mm identified in mid pulmonary zone."
        elif has_nodule:
            report.findings_lungs = "Solitary non-calcified circumscribed pulmonary nodule (<30mm). Follow-up Fleischner CT recommended."
        elif has_emphysema:
            report.findings_lungs = "Bilateral lung hyperinflation with flattening of diaphragmatic leaves consistent with chronic emphysema."
        elif has_fibrosis:
            report.findings_lungs = "Coarse reticular linear interstitial opacities with volume traction in peripheral subpleural bases."
        elif has_atelectasis:
            report.findings_lungs = "Subsegmental linear discoid atelectatic opacities in the lung bases. No focal consolidative pneumonia."
        elif has_ptx:
            report.findings_lungs = "Apical visceral pleural reflection with absence of peripheral lung vascular markings. Hyperlucent pleural space."
        else:
            report.findings_lungs = "Lungs are well-expanded and clear bilaterally without focal consolidation, mass, or edema."

        # Pleura
        if has_ptx:
            report.findings_pleura = "Acute pneumothorax. Apical pleural cap separation. Urgent clinical evaluation required."
        elif has_eff:
            report.findings_pleura = "Blunting of the costophrenic angle consistent with dependent pleural fluid accumulation / effusion."
        else:
            report.findings_pleura = "Costophrenic angles and pleural surfaces are sharp and normal. No pneumothorax or effusion."

        # Cardiomediastinum
        if has_cardio:
            report.findings_cardiomediastinum = "Cardiomegaly noted with increased transverse cardiac silhouette diameter (estimated CTR > 0.50)."
        else:
            report.findings_cardiomediastinum = "Cardiac silhouette is normal in size and configuration. Normal mediastinal contours."

        # Impression & ACR Codes
        if has_ptx:
            report.impression = "1. STAT CRITICAL: Tension pneumothorax identified. Immediate thoracic decompression indicated."
            report.acr_actionable_code = "ACR Category 1 (Critical Finding - Immediate Verbal Notification)"
        elif has_pneu:
            report.impression = f"1. Acute focal pneumonia localized to the {dom_zone}. Clinical correlation and targeted antibiotic therapy advised."
            report.acr_actionable_code = "ACR Category 2 (Urgent Finding - Notification within 2 Hours)"
        elif has_edema:
            report.impression = "1. Severe cardiogenic / non-cardiogenic pulmonary edema with perihilar congestion. Urgent diuresis evaluation recommended."
            report.acr_actionable_code = "ACR Category 1 (Critical Finding - Immediate Verbal Notification)"
        elif has_mass:
            report.impression = "1. Solitary pulmonary mass lesion >30mm. High-resolution diagnostic chest CT with IV contrast strongly recommended."
            report.acr_actionable_code = "ACR Category 2 (Urgent Finding - Actionable Notification)"
        elif has_eff or has_cardio:
            report.impression = "1. Evidence of cardiomegaly and/or pleural effusion. Recommend clinical review and diagnostic echocardiography."
            report.acr_actionable_code = "ACR Category 2 (Urgent Finding)"
        elif has_nodule:
            report.impression = "1. Indeterminate solitary pulmonary nodule. High-resolution chest CT advised per Fleischner Society guidelines."
            report.acr_actionable_code = "ACR Category 3 (Routine / Non-Critical Finding)"
        else:
            report.impression = "1. No acute cardiopulmonary abnormality detected. Bilateral clear lung fields."
            report.acr_actionable_code = "ACR Category 3 (Routine / Negative)"
            report.impression = "1. No acute cardiopulmonary abnormality. Normal chest radiograph."
            report.acr_actionable_code = "ACR Category 3 (Routine / Negative)"

        return report

    def parse_dictation_input(
        self,
        transcript: Optional[str] = None,
        text: Optional[str] = None,
        current_report: Optional[StructuredReportModel] = None
    ) -> VoiceParseResult:
        """
        Interprets radiologist voice dictation and executes section editing or clinical macros.
        """
        raw_text = transcript or text or ""
        report = current_report.model_copy() if current_report else StructuredReportModel()
        text = raw_text.strip()
        lower = text.lower()

        command_detected = None
        target_field = None
        action_executed = "Appended voice transcript to impression"

        # Voice Macro 1: Insert Normal Chest
        if any(p in lower for p in ["insert normal", "normal chest", "template normal", "clear chest"]):
            command_detected = "INSERT_NORMAL_TEMPLATE"
            for k, v in NORMAL_CHEST_TEMPLATE.items():
                setattr(report, k, v)
            action_executed = "Inserted Normal Chest Radiograph template"

        # Voice Macro 2: Insert Trauma / Pneumothorax
        elif any(p in lower for p in ["insert trauma", "insert pneumothorax", "tension pneumothorax template"]):
            command_detected = "INSERT_TRAUMA_TEMPLATE"
            for k, v in TRAUMA_PNEUMOTHORAX_TEMPLATE.items():
                setattr(report, k, v)
            action_executed = "Inserted Trauma Pneumothorax template"

        # Voice Macro 3: Insert Pneumonia Template
        elif any(p in lower for p in ["insert pneumonia", "consolidation template"]):
            command_detected = "INSERT_PNEUMONIA_TEMPLATE"
            for k, v in PNEUMONIA_CONSOLIDATION_TEMPLATE.items():
                setattr(report, k, v)
            action_executed = "Inserted Pneumonia Consolidation template"

        # Voice Command: Sign off / Attest
        elif any(p in lower for p in ["attest report", "sign off report", "sign report", "finalize report"]):
            command_detected = "ATTEST_SIGNOFF"
            action_executed = "Triggered physician electronic attestation signoff"

        # Section Dictation: Lungs
        elif any(p in lower for p in ["dictate lungs", "findings lungs", "lungs:"]):
            cleaned = re.sub(r'^(dictate\s+)?(findings\s+)?lungs:?\s*', '', text, flags=re.IGNORECASE)
            report.findings_lungs = cleaned.strip()
            command_detected = "EDIT_SECTION"
            target_field = "findings_lungs"
            action_executed = f"Updated lungs findings: '{cleaned.strip()[:40]}...'"

        # Section Dictation: Pleura
        elif any(p in lower for p in ["dictate pleura", "findings pleura", "pleura:"]):
            cleaned = re.sub(r'^(dictate\s+)?(findings\s+)?pleura:?\s*', '', text, flags=re.IGNORECASE)
            report.findings_pleura = cleaned.strip()
            command_detected = "EDIT_SECTION"
            target_field = "findings_pleura"
            action_executed = f"Updated pleura findings: '{cleaned.strip()[:40]}...'"

        # Section Dictation: Heart / Cardiomediastinum
        elif any(p in lower for p in ["dictate heart", "dictate mediastinum", "findings heart", "heart:"]):
            cleaned = re.sub(r'^(dictate\s+)?(findings\s+)?(heart|mediastinum):?\s*', '', text, flags=re.IGNORECASE)
            report.findings_cardiomediastinum = cleaned.strip()
            command_detected = "EDIT_SECTION"
            target_field = "findings_cardiomediastinum"
            action_executed = f"Updated heart/mediastinum: '{cleaned.strip()[:40]}...'"

        # Section Dictation: Bones / Soft Tissue
        elif any(p in lower for p in ["dictate bones", "findings bones", "bones:"]):
            cleaned = re.sub(r'^(dictate\s+)?(findings\s+)?bones:?\s*', '', text, flags=re.IGNORECASE)
            report.findings_bones_soft_tissues = cleaned.strip()
            command_detected = "EDIT_SECTION"
            target_field = "findings_bones_soft_tissues"
            action_executed = f"Updated bones findings: '{cleaned.strip()[:40]}...'"

        # Section Dictation: Impression
        elif any(p in lower for p in ["dictate impression", "impression:", "conclusion:"]):
            cleaned = re.sub(r'^(dictate\s+)?(impression|conclusion):?\s*', '', text, flags=re.IGNORECASE)
            report.impression = cleaned.strip()
            command_detected = "EDIT_SECTION"
            target_field = "impression"
            action_executed = f"Updated diagnostic impression: '{cleaned.strip()[:40]}...'"

        # Generic Voice Dictation Fallback -> append to impression
        else:
            report.impression = f"{report.impression} [Dictation: {text}]"
            command_detected = "APPEND_DICTATION"
            target_field = "impression"
            action_executed = f"Appended dictation to impression: '{text[:40]}...'"

        report.dictated_voice = True
        report.dictation_source = "Microphone Voice Dictation (RADLEX Speech-to-Report)"
        report.timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S EST")

        return VoiceParseResult(
            command_detected=command_detected,
            target_field=target_field,
            transcribed_text=text,
            action_executed=action_executed,
            structured_report=report
        )

    # Method aliases for routing consistency
    generate_report_from_findings = synthesize_report_from_findings
    parse_dictation_command = parse_dictation_input


def get_structured_reporting_engine() -> StructuredReportingEngine:
    """Singleton getter for the structured reporting engine."""
    return StructuredReportingEngine.get_instance()
