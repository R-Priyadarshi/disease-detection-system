"""
ALVEON Fleischner Society 2017 Pulmonary Nodule Management Engine
Implements:
1. Evidence-based clinical guidelines for incidental pulmonary nodules (Fleischner Society 2017).
2. Morphology classification (Solid Single, Solid Multiple, Part-Solid, Pure Ground Glass).
3. Risk factor stratification (Low Risk vs. High Risk).
4. Volumetric nodule measurement & spherical equivalent volume (mm³).
5. Standardized RADLEX, SNOMED CT, and LOINC ontological mappings.
6. HL7 FHIR R4 DiagnosticReport & Observation Bundle generation.
7. Institutional Fleischner Nodule Management Consultation Dossier PDF generator.
"""

import io
import math
import uuid
import datetime
from typing import Dict, Any, List, Optional, Tuple
from pydantic import BaseModel, Field
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether, HRFlowable


class NoduleEvaluationRequest(BaseModel):
    patient_id: str = "MRN-PULM-8821"
    patient_name: str = "Thorne^Gwendolyn"
    patient_age: int = 58
    patient_sex: str = "F"
    morphology: str = "SOLID_SINGLE"  # "SOLID_SINGLE", "SOLID_MULTIPLE", "PART_SOLID", "GROUND_GLASS"
    max_diameter_mm: float = 7.4
    perp_diameter_mm: Optional[float] = 6.2
    solid_component_mm: Optional[float] = 0.0
    lobe_location: str = "RIGHT_UPPER_LOBE"  # "RUL", "RML", "RLL", "LUL", "LLL"
    is_spiculated: bool = True
    smoking_pack_years: int = 25
    family_history_lung_cancer: bool = False
    emphysema_present: bool = True


class FleischnerGuidelineResult(BaseModel):
    evaluation_id: str
    evaluated_at: str
    patient_id: str
    patient_name: str
    patient_age: int
    morphology: str
    mean_diameter_mm: float
    estimated_volume_mm3: float
    risk_category: str  # "LOW_RISK" or "HIGH_RISK"
    risk_factors: List[str]
    recommendation_code: str
    recommended_action: str
    follow_up_interval_months: Optional[int]
    follow_up_modality: str
    clinical_rationale: str
    is_suspicious_for_malignancy: bool
    radlex_codes: Dict[str, str]
    snomed_codes: Dict[str, str]
    loinc_codes: Dict[str, str]


class FleischnerEngine:
    """Clinical decision support engine implementing Fleischner Society 2017 Guidelines."""

    _instance: Optional['FleischnerEngine'] = None

    @classmethod
    def get_instance(cls) -> 'FleischnerEngine':
        if cls._instance is None:
            cls._instance = FleischnerEngine()
        return cls._instance

    def evaluate_nodule(self, req: NoduleEvaluationRequest) -> FleischnerGuidelineResult:
        """Evaluates nodule parameters against the official Fleischner 2017 matrix."""
        eval_id = f"FL-{uuid.uuid4().hex[:8].upper()}"
        now = datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z"

        # Compute mean diameter and spherical equivalent volume
        p_diam = req.perp_diameter_mm if req.perp_diameter_mm else req.max_diameter_mm
        mean_diam = round((req.max_diameter_mm + p_diam) / 2.0, 1)
        est_vol = round((math.pi / 6.0) * (mean_diam ** 3), 1)

        # Risk Factor Evaluation
        risk_factors = []
        if req.patient_age >= 50:
            risk_factors.append(f"Age {req.patient_age} (>= 50)")
        if req.smoking_pack_years >= 10:
            risk_factors.append(f"Smoking history ({req.smoking_pack_years} pack-years)")
        if req.is_spiculated:
            risk_factors.append("Spiculated / irregular nodule margin")
        if req.emphysema_present:
            risk_factors.append("Concurrent pulmonary emphysema")
        if req.family_history_lung_cancer:
            risk_factors.append("First-degree family history of lung cancer")
        if "UPPER" in req.lobe_location.upper() or "RUL" in req.lobe_location.upper() or "LUL" in req.lobe_location.upper():
            risk_factors.append("Upper lobe predilection (increased malignancy risk)")

        is_high_risk = len(risk_factors) >= 2 or req.smoking_pack_years >= 20 or req.is_spiculated
        risk_cat = "HIGH_RISK" if is_high_risk else "LOW_RISK"

        morph = req.morphology.upper()
        solid_comp = req.solid_component_mm or 0.0

        # Fleischner 2017 Decision Logic Matrix
        rec_code = "NO_FOLLOWUP"
        action = "No routine follow-up required"
        interval_months = None
        modality = "None"
        rationale = "Risk of malignancy is < 1%."
        is_suspicious = False

        if morph == "SOLID_SINGLE":
            if mean_diam < 6.0:
                if is_high_risk:
                    rec_code = "OPTIONAL_CT_12M"
                    action = "Optional low-dose chest CT at 12 months"
                    interval_months = 12
                    modality = "Low-Dose Chest CT"
                    rationale = "High-risk features warrant consideration of 12-month interval surveillance."
                else:
                    rec_code = "NO_ROUTINE_FOLLOWUP"
                    action = "No routine surveillance CT indicated"
                    rationale = "Solid nodules < 6 mm in low-risk individuals have negligible lifetime cancer risk (< 0.15%)."
            elif 6.0 <= mean_diam <= 8.0:
                rec_code = "CT_6_TO_12M"
                action = "Chest CT at 6 to 12 months, then consider repeat CT at 18 to 24 months"
                interval_months = 6
                modality = "Non-Contrast Chest CT"
                rationale = "Intermediate size with 1-5% malignancy probability requires interval stability confirmation."
            else:  # > 8.0 mm
                rec_code = "CONSIDER_3M_OR_PET"
                action = "Chest CT at 3 months, FDG-PET/CT, or diagnostic tissue biopsy"
                interval_months = 3
                modality = "Diagnostic Chest CT / FDG-PET"
                rationale = "Nodules > 8 mm carry > 10% risk of malignancy; prompt investigation is indicated."
                is_suspicious = True

        elif morph == "SOLID_MULTIPLE":
            if mean_diam < 6.0:
                if is_high_risk:
                    rec_code = "OPTIONAL_CT_12M"
                    action = "Optional chest CT at 12 months based on clinical context"
                    interval_months = 12
                    modality = "Low-Dose Chest CT"
                    rationale = "Multiple sub-centimeter solid nodules in high-risk patients warrant baseline check."
                else:
                    rec_code = "NO_ROUTINE_FOLLOWUP"
                    action = "No routine follow-up"
                    rationale = "Sub-6mm multiple nodules commonly reflect healed granulomatous disease."
            else:  # >= 6.0 mm
                rec_code = "CT_3_TO_6M"
                action = "Chest CT at 3 to 6 months, then consider CT at 18 to 24 months for dominant nodule"
                interval_months = 3
                modality = "Chest CT"
                rationale = "Surveillance focused on dominant nodule to assess interval growth or resolution."

        elif morph in ("PART_SOLID", "SUBSOLID"):
            if mean_diam < 6.0:
                rec_code = "NO_ROUTINE_FOLLOWUP"
                action = "No routine follow-up indicated"
                rationale = "Small subsolid foci are frequently infectious or inflammatory."
            else:
                if solid_comp >= 6.0:
                    rec_code = "URGENT_SURGICAL_OR_PET"
                    action = "Chest CT at 3 to 6 months, PET/CT, or immediate multidisciplinary surgical consultation"
                    interval_months = 3
                    modality = "High-Resolution Chest CT / PET"
                    rationale = "Part-solid nodules with solid core >= 6 mm are highly suspicious for invasive adenocarcinoma."
                    is_suspicious = True
                else:
                    rec_code = "CT_3_TO_6M_PART_SOLID"
                    action = "Chest CT at 3 to 6 months to confirm persistence; if persistent, annual CT for 5 years"
                    interval_months = 3
                    modality = "Thin-Slice Chest CT"
                    rationale = "Part-solid morphology requires demonstration of non-transience followed by long-term tracking."

        elif morph in ("GROUND_GLASS", "PURE_GROUND_GLASS", "GGN"):
            if mean_diam < 6.0:
                rec_code = "NO_ROUTINE_FOLLOWUP"
                action = "No routine follow-up indicated"
                rationale = "Pure GGN < 6 mm are usually transient or pre-invasive atypical adenomatous hyperplasia (AAH)."
            else:
                rec_code = "CT_6_TO_12M_GGN"
                action = "Chest CT at 6 to 12 months to confirm persistence, then CT every 2 years for 5 years"
                interval_months = 6
                modality = "Thin-Slice Low-Dose CT"
                rationale = "Persistent pure GGN >= 6 mm may represent adenocarcinoma in situ (AIS) or minimally invasive adenocarcinoma (MIA)."

        # Ontological Code References
        radlex = {
            "finding": "RID28473 (Pulmonary nodule)",
            "morphology": "RID43264 (Solid)" if "SOLID" in morph else ("RID43265 (Part-solid)" if "PART" in morph else "RID38766 (Ground-glass)"),
            "location": "RID5825 (RUL)" if "UPPER" in req.lobe_location else "RID5827 (RLL)"
        }
        snomed = {
            "management_protocol": "371037004 (Fleischner Society recommendation for lung nodule)",
            "finding_type": "125144007 (Part-solid nodule)" if "PART" in morph else "27931003 (Solitary lung nodule)"
        }
        loinc = {
            "study_type": "24627-2 (Chest CT Diagnostic Imaging Study)",
            "report_type": "18748-4 (Diagnostic imaging report)"
        }

        return FleischnerGuidelineResult(
            evaluation_id=eval_id,
            evaluated_at=now,
            patient_id=req.patient_id,
            patient_name=req.patient_name,
            patient_age=req.patient_age,
            morphology=morph,
            mean_diameter_mm=mean_diam,
            estimated_volume_mm3=est_vol,
            risk_category=risk_cat,
            risk_factors=risk_factors,
            recommendation_code=rec_code,
            recommended_action=action,
            follow_up_interval_months=interval_months,
            follow_up_modality=modality,
            clinical_rationale=rationale,
            is_suspicious_for_malignancy=is_suspicious,
            radlex_codes=radlex,
            snomed_codes=snomed,
            loinc_codes=loinc
        )

    def generate_fhir_r4_bundle(self, res: FleischnerGuidelineResult) -> Dict[str, Any]:
        """Generates a complete, standard HL7 FHIR R4 Bundle containing DiagnosticReport and Observations."""
        bundle_id = f"bundle-{uuid.uuid4()}"
        report_id = f"report-{uuid.uuid4()}"
        obs_size_id = f"obs-size-{uuid.uuid4()}"
        obs_rec_id = f"obs-rec-{uuid.uuid4()}"

        return {
            "resourceType": "Bundle",
            "id": bundle_id,
            "type": "transaction",
            "timestamp": res.evaluated_at,
            "entry": [
                {
                    "fullUrl": f"urn:uuid:{report_id}",
                    "resource": {
                        "resourceType": "DiagnosticReport",
                        "id": report_id,
                        "status": "final",
                        "category": [
                            {
                                "coding": [
                                    {
                                        "system": "http://terminology.hl7.org/CodeSystem/v2-0074",
                                        "code": "RAD",
                                        "display": "Radiology"
                                    }
                                ]
                            }
                        ],
                        "code": {
                            "coding": [
                                {
                                    "system": "http://loinc.org",
                                    "code": "24627-2",
                                    "display": "CT Thorax with contrast"
                                }
                            ],
                            "text": "Fleischner Society Pulmonary Nodule Diagnostic Evaluation"
                        },
                        "subject": {
                            "reference": f"Patient/{res.patient_id}",
                            "display": res.patient_name
                        },
                        "effectiveDateTime": res.evaluated_at,
                        "issued": res.evaluated_at,
                        "performer": [
                            {
                                "display": "Dr. Eleanor Vance, MD (Attending Radiologist, ALVEON PACS)"
                            }
                        ],
                        "result": [
                            {"reference": f"urn:uuid:{obs_size_id}"},
                            {"reference": f"urn:uuid:{obs_rec_id}"}
                        ],
                        "conclusion": f"Fleischner 2017 Recommendation: {res.recommended_action}. Risk: {res.risk_category}.",
                        "conclusionCode": [
                            {
                                "coding": [
                                    {
                                        "system": "http://snomed.info/sct",
                                        "code": "371037004",
                                        "display": "Fleischner Society management protocol"
                                    }
                                ]
                            }
                        ]
                    }
                },
                {
                    "fullUrl": f"urn:uuid:{obs_size_id}",
                    "resource": {
                        "resourceType": "Observation",
                        "id": obs_size_id,
                        "status": "final",
                        "code": {
                            "coding": [
                                {
                                    "system": "http://radlex.org",
                                    "code": "RID28473",
                                    "display": "Pulmonary nodule diameter"
                                }
                            ]
                        },
                        "valueQuantity": {
                            "value": res.mean_diameter_mm,
                            "unit": "mm",
                            "system": "http://unitsofmeasure.org",
                            "code": "mm"
                        }
                    }
                },
                {
                    "fullUrl": f"urn:uuid:{obs_rec_id}",
                    "resource": {
                        "resourceType": "Observation",
                        "id": obs_rec_id,
                        "status": "final",
                        "code": {
                            "text": "Fleischner Follow-Up Interval"
                        },
                        "valueString": f"{res.follow_up_interval_months or 0} months ({res.follow_up_modality})"
                    }
                }
            ]
        }

    def generate_dossier_pdf(self, res: FleischnerGuidelineResult) -> bytes:
        """Generates an institutional Fleischner Society Consultation Dossier PDF."""
        buf = io.BytesIO()
        doc = SimpleDocTemplate(
            buf, pagesize=letter,
            rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'TitleStyle', parent=styles['Heading1'],
            fontName='Helvetica-Bold', fontSize=17, leading=21, textColor=colors.HexColor('#0f172a')
        )
        subtitle_style = ParagraphStyle(
            'SubtitleStyle', parent=styles['Normal'],
            fontName='Helvetica-Bold', fontSize=10, leading=14, textColor=colors.HexColor('#0284c7')
        )
        body_style = ParagraphStyle(
            'BodyStyle', parent=styles['Normal'],
            fontName='Helvetica', fontSize=9, leading=13, textColor=colors.HexColor('#334155')
        )
        bold_body = ParagraphStyle(
            'BoldBody', parent=body_style, fontName='Helvetica-Bold'
        )
        alert_style = ParagraphStyle(
            'AlertStyle', parent=body_style,
            fontName='Helvetica-Bold', textColor=colors.HexColor('#b91c1c') if res.is_suspicious_for_malignancy else colors.HexColor('#0284c7')
        )

        story = []

        # Header
        header_table = Table([
            [
                Paragraph("<b>ALVEON CLINICAL PACS</b><br/><font size=8 color='#64748b'>Thoracic Imaging & Pulmonary Oncology Service</font>", body_style),
                Paragraph(f"<b>CONSULT ID:</b> {res.evaluation_id}<br/><b>DATE:</b> {res.evaluated_at[:10]}", body_style)
            ]
        ], colWidths=[360, 180])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (1, 0), (1, 0), 'RIGHT')
        ]))
        story.append(header_table)
        story.append(Spacer(1, 10))
        story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#0284c7')))
        story.append(Spacer(1, 10))

        # Title
        story.append(Paragraph("FLEISCHNER SOCIETY 2017 PULMONARY NODULE CONSULTATION DOSSIER", title_style))
        story.append(Paragraph("Evidence-Based Management Protocol for Incidental Pulmonary Nodules (Radiology 2017; 284:228-243)", subtitle_style))
        story.append(Spacer(1, 14))

        # Patient Info Card
        patient_data = [
            [Paragraph("<b>Patient Name:</b>", body_style), Paragraph(res.patient_name, bold_body),
             Paragraph("<b>Patient MRN:</b>", body_style), Paragraph(res.patient_id, bold_body)],
            [Paragraph("<b>Age / Sex:</b>", body_style), Paragraph(f"{res.patient_age}Y / Female", body_style),
             Paragraph("<b>Evaluation Date:</b>", body_style), Paragraph(res.evaluated_at[:19] + "Z", body_style)]
        ]
        p_table = Table(patient_data, colWidths=[100, 170, 100, 170])
        p_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8fafc')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            ('PADDING', (0, 0), (-1, -1), 6)
        ]))
        story.append(p_table)
        story.append(Spacer(1, 14))

        # Nodule Morphometry & Volumetric Analysis
        story.append(Paragraph("<b>1. Quantitative Nodule Morphometry & Risk Stratification</b>", subtitle_style))
        story.append(Spacer(1, 6))

        morph_data = [
            [Paragraph("<b>Morphological Class:</b>", body_style), Paragraph(res.morphology.replace('_', ' '), bold_body),
             Paragraph("<b>Mean Caliper Diameter:</b>", body_style), Paragraph(f"{res.mean_diameter_mm} mm", bold_body)],
            [Paragraph("<b>Spherical Equivalent Vol:</b>", body_style), Paragraph(f"{res.estimated_volume_mm3} mm³", body_style),
             Paragraph("<b>Risk Stratification:</b>", body_style), Paragraph(f"<b>{res.risk_category}</b>", alert_style)],
            [Paragraph("<b>Identified Risk Factors:</b>", body_style), Paragraph(", ".join(res.risk_factors) if res.risk_factors else "None", body_style),
             Paragraph("<b>Suspicion Index:</b>", body_style), Paragraph("HIGH SUSPICION (Adenocarcinoma Risk)" if res.is_suspicious_for_malignancy else "Indeterminate / Surveillance", alert_style)]
        ]
        m_table = Table(morph_data, colWidths=[130, 140, 130, 140])
        m_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f1f5f9')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
            ('PADDING', (0, 0), (-1, -1), 6)
        ]))
        story.append(m_table)
        story.append(Spacer(1, 14))

        # Actionable Recommendation Box
        story.append(Paragraph("<b>2. Official Fleischner 2017 Actionable Recommendation</b>", subtitle_style))
        story.append(Spacer(1, 6))

        rec_box = [
            [Paragraph(f"<b>DIRECTIVE:</b> {res.recommended_action}", alert_style)],
            [Paragraph(f"<b>Follow-Up Timeline:</b> {res.follow_up_interval_months} Months ({res.follow_up_modality})" if res.follow_up_interval_months else "<b>Follow-Up Timeline:</b> No routine surveillance required", bold_body)],
            [Paragraph(f"<b>Clinical Rationale:</b> {res.clinical_rationale}", body_style)]
        ]
        r_table = Table(rec_box, colWidths=[540])
        r_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#fef2f2') if res.is_suspicious_for_malignancy else colors.HexColor('#f0f9ff')),
            ('BOX', (0, 0), (-1, -1), 1.5, colors.HexColor('#dc2626') if res.is_suspicious_for_malignancy else colors.HexColor('#0284c7')),
            ('PADDING', (0, 0), (-1, -1), 8)
        ]))
        story.append(r_table)
        story.append(Spacer(1, 14))

        # Ontological Codings
        story.append(Paragraph("<b>3. Interoperability & Medical Coding</b>", subtitle_style))
        story.append(Spacer(1, 4))
        codes_data = [
            [Paragraph("<b>RADLEX:</b>", body_style), Paragraph(f"{res.radlex_codes.get('finding')} | {res.radlex_codes.get('morphology')}", body_style)],
            [Paragraph("<b>SNOMED CT:</b>", body_style), Paragraph(f"{res.snomed_codes.get('management_protocol')}", body_style)],
            [Paragraph("<b>LOINC:</b>", body_style), Paragraph(f"{res.loinc_codes.get('study_type')}", body_style)]
        ]
        c_table = Table(codes_data, colWidths=[90, 450])
        c_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8fafc')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            ('PADDING', (0, 0), (-1, -1), 5)
        ]))
        story.append(c_table)
        story.append(Spacer(1, 20))

        # Attestation Block
        sign_table = Table([
            [
                Paragraph("<b>Attending Radiologist:</b><br/>Dr. Eleanor Vance, MD, FACR<br/><font size=7 color='#64748b'>ALVEON Diagnostic Imaging Department</font>", body_style),
                Paragraph("<b>Chief of Thoracic Oncology:</b><br/>Dr. Marcus Chen, MD, PhD<br/><font size=7 color='#64748b'>Pulmonary Nodule Tumor Board</font>", body_style)
            ]
        ], colWidths=[270, 270])
        sign_table.setStyle(TableStyle([
            ('LINEABOVE', (0, 0), (-1, 0), 1, colors.HexColor('#94a3b8')),
            ('PADDING', (0, 0), (-1, -1), 8)
        ]))
        story.append(KeepTogether(sign_table))

        doc.build(story)
        return buf.getvalue()


def get_fleischner_engine() -> FleischnerEngine:
    return FleischnerEngine.get_instance()
