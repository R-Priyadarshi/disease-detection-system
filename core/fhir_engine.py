"""
ALVEON Enterprise Hospital PACS - HL7 FHIR R4 REST Resource Engine
Generates standard FHIR R4 JSON resources for modern healthcare interoperability:
- DiagnosticReport (Complete radiologic study report with conclusions & codes)
- Observation (Atomic quantitative AI disease confidences & CTR metrics)
- ImagingStudy (DICOM metadata, series instances & WADO-RS endpoints)
- Patient (Demographics and MRN references)
100% Free & Open-Source (Zero proprietary FHIR server licenses).
"""

from datetime import datetime, timezone
import uuid
from typing import Dict, Any, List, Optional


# Standard SNOMED CT and LOINC Clinical Codes
SNOMED_CODES = {
    "PNEUMONIA": {"code": "233604007", "display": "Pneumonia (disorder)"},
    "PNEUMOTHORAX": {"code": "36118008", "display": "Pneumothorax (disorder)"},
    "PLEURAL EFFUSION": {"code": "60046008", "display": "Pleural effusion (disorder)"},
    "CARDIOMEGALY": {"code": "8186001", "display": "Cardiomegaly (disorder)"},
    "ATELECTASIS": {"code": "46621007", "display": "Atelectasis (disorder)"},
    "NORMAL": {"code": "17621005", "display": "Normal chest (finding)"}
}

LOINC_CODES = {
    "CHEST_XR": {"code": "18748-4", "display": "Diagnostic imaging study"},
    "RADIOLOGY_REPORT": {"code": "11528-7", "display": "Radiology Report"},
    "IMPRESSION": {"code": "19005-8", "display": "Radiology Impression"},
    "FINDINGS": {"code": "18782-3", "display": "Radiology Study Findings"}
}


class FHIREngine:
    """FHIR R4 JSON Resource Generator for Enterprise Health Interoperability."""
    _instance = None

    @classmethod
    def get_instance(cls) -> "FHIREngine":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def generate_patient_resource(self, mrn: str, name: str, gender: str = "female", birthdate: str = "1985-04-12") -> Dict[str, Any]:
        """Generates a standard FHIR R4 Patient resource."""
        clean_name = name.replace("^", " ").replace(",", "")
        name_parts = clean_name.split()
        family = name_parts[0] if name_parts else "Patient"
        given = name_parts[1:] if len(name_parts) > 1 else ["Anonymous"]

        return {
            "resourceType": "Patient",
            "id": mrn.replace("#", "").replace("-", "_").lower(),
            "identifier": [
                {
                    "use": "usual",
                    "type": {
                        "coding": [{
                            "system": "http://terminology.hl7.org/CodeSystem/v2-0203",
                            "code": "MR",
                            "display": "Medical Record Number"
                        }]
                    },
                    "system": "http://hospital.alveon.internal/mrn",
                    "value": mrn
                }
            ],
            "active": True,
            "name": [
                {
                    "use": "official",
                    "family": family,
                    "given": given
                }
            ],
            "gender": gender.lower() if gender.lower() in ["male", "female", "other", "unknown"] else "unknown",
            "birthDate": birthdate
        }

    def generate_imaging_study_resource(
        self,
        study_id: str,
        patient_mrn: str,
        modality: str = "DX",
        series_uid: Optional[str] = None,
        instance_uid: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generates a standard FHIR R4 ImagingStudy resource."""
        sid = study_id.replace("STUDY-", "")
        suid = series_uid or f"1.2.826.0.1.3680043.8.498.{uuid.uuid4().int % 100000000}"
        iuid = instance_uid or f"1.2.826.0.1.3680043.8.498.{uuid.uuid4().int % 100000000}"

        return {
            "resourceType": "ImagingStudy",
            "id": f"imaging-study-{sid.lower()}",
            "identifier": [
                {
                    "system": "urn:dicom:uid",
                    "value": f"urn:oid:1.2.826.0.1.3680043.8.498.{sid}"
                }
            ],
            "status": "available",
            "modality": [
                {
                    "system": "http://dicom.nema.org/resources/ontology/DCM",
                    "code": modality,
                    "display": "Digital Radiography" if modality == "DX" else "Computed Tomography"
                }
            ],
            "subject": {
                "reference": f"Patient/{patient_mrn.replace('#', '').replace('-', '_').lower()}",
                "display": f"MRN: {patient_mrn}"
            },
            "started": datetime.now(timezone.utc).isoformat(),
            "endpoint": [
                {
                    "reference": "Endpoint/alveon-wado-rs",
                    "display": "ALVEON Native WADO-RS Service"
                }
            ],
            "numberOfSeries": 1,
            "numberOfInstances": 1,
            "series": [
                {
                    "uid": suid,
                    "number": 1,
                    "modality": {
                        "system": "http://dicom.nema.org/resources/ontology/DCM",
                        "code": modality
                    },
                    "description": "Chest Radiograph AP/PA View",
                    "numberOfInstances": 1,
                    "bodySite": {
                        "system": "http://snomed.info/sct",
                        "code": "51185008",
                        "display": "Thorax (body structure)"
                    },
                    "instance": [
                        {
                            "uid": iuid,
                            "sopClass": {
                                "system": "urn:ietf:rfc:3986",
                                "value": "urn:oid:1.2.840.10008.5.1.4.1.1.1" # Digital X-Ray Image Storage
                            },
                            "number": 1,
                            "title": "STAT Emergency Chest XR"
                        }
                    ]
                }
            ]
        }

    def generate_observation_resource(
        self,
        observation_id: str,
        patient_mrn: str,
        study_id: str,
        diagnosis_label: str,
        probability: float,
        status: str = "final"
    ) -> Dict[str, Any]:
        """Generates a standard FHIR R4 Observation resource representing an AI finding."""
        norm_key = diagnosis_label.upper().replace(" / CONSOLIDATION", "").replace(" / PLEURAL", "").strip()
        snomed = SNOMED_CODES.get(norm_key, {"code": "410515003", "display": "Known finding (finding)"})

        return {
            "resourceType": "Observation",
            "id": f"obs-{observation_id}",
            "status": status,
            "category": [
                {
                    "coding": [{
                        "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                        "code": "imaging",
                        "display": "Imaging"
                    }]
                }
            ],
            "code": {
                "coding": [{
                    "system": "http://snomed.info/sct",
                    "code": snomed["code"],
                    "display": snomed["display"]
                }],
                "text": diagnosis_label
            },
            "subject": {
                "reference": f"Patient/{patient_mrn.replace('#', '').replace('-', '_').lower()}"
            },
            "focus": [
                {
                    "reference": f"ImagingStudy/imaging-study-{study_id.replace('STUDY-', '').lower()}"
                }
            ],
            "effectiveDateTime": datetime.now(timezone.utc).isoformat(),
            "valueQuantity": {
                "value": round(probability * 100, 1),
                "unit": "%",
                "system": "http://unitsofmeasure.org",
                "code": "%"
            },
            "interpretation": [
                {
                    "coding": [{
                        "system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation",
                        "code": "A" if probability >= 0.5 and norm_key != "NORMAL" else "N",
                        "display": "Abnormal" if probability >= 0.5 and norm_key != "NORMAL" else "Normal"
                    }]
                }
            ],
            "device": {
                "display": "ALVEON Deep Learning Multi-Label Diagnostic Engine v4.2"
            }
        }

    def generate_diagnostic_report(
        self,
        study_id: str,
        patient_mrn: str,
        patient_name: str,
        diagnosis: str,
        confidence_percentage: float,
        all_findings: Optional[List[Dict[str, Any]]] = None,
        impression: str = "",
        acr_category: str = "ACR Category 1 (Critical STAT Alert)",
        attesting_physician: str = "Dr. Eleanor Vance, MD",
        is_signed: bool = True
    ) -> Dict[str, Any]:
        """
        Generates a fully compliant FHIR R4 DiagnosticReport resource.
        Integrates observations, clinical conclusions, ACR codes, and practitioner attestations.
        """
        sid = study_id.replace("STUDY-", "").lower()
        now_iso = datetime.now(timezone.utc).isoformat()
        norm_diag = diagnosis.upper().replace(" / CONSOLIDATION", "").strip()
        snomed = SNOMED_CODES.get(norm_diag, {"code": "233604007", "display": "Thoracic finding"})

        # Build list of observation references
        obs_refs = []
        findings = all_findings or [{"label": diagnosis, "probability": confidence_percentage / 100.0}]
        for idx, f in enumerate(findings):
            obs_id = f"{sid}-f{idx}"
            obs_refs.append({
                "reference": f"Observation/obs-{obs_id}",
                "display": f"{f.get('label', diagnosis)} ({round(f.get('probability', 0.99) * 100, 1)}%)"
            })

        return {
            "resourceType": "DiagnosticReport",
            "id": f"report-{sid}",
            "identifier": [
                {
                    "system": "http://hospital.alveon.internal/diagnostic-reports",
                    "value": f"ALV-RPT-{sid.upper()}"
                }
            ],
            "status": "final" if is_signed else "preliminary",
            "category": [
                {
                    "coding": [{
                        "system": "http://loinc.org",
                        "code": LOINC_CODES["CHEST_XR"]["code"],
                        "display": LOINC_CODES["CHEST_XR"]["display"]
                    }]
                }
            ],
            "code": {
                "coding": [{
                    "system": "http://www.ama-assn.org/go/cpt",
                    "code": "71045",
                    "display": "Radiologic examination, chest; single view"
                }],
                "text": "Chest Radiograph Single View (AP/PA Projections)"
            },
            "subject": {
                "reference": f"Patient/{patient_mrn.replace('#', '').replace('-', '_').lower()}",
                "display": f"{patient_name} (MRN: {patient_mrn})"
            },
            "effectiveDateTime": now_iso,
            "issued": now_iso,
            "performer": [
                {
                    "display": attesting_physician
                },
                {
                    "display": "ALVEON AI Emergency Triage System"
                }
            ],
            "resultsInterpreter": [
                {
                    "display": attesting_physician
                }
            ],
            "imagingStudy": [
                {
                    "reference": f"ImagingStudy/imaging-study-{sid}"
                }
            ],
            "result": obs_refs,
            "conclusion": impression or f"Radiologic evaluation demonstrates evidence of {diagnosis} with {confidence_percentage:.1f}% confidence. Assigned: {acr_category}.",
            "conclusionCode": [
                {
                    "coding": [{
                        "system": "http://snomed.info/sct",
                        "code": snomed["code"],
                        "display": snomed["display"]
                    }]
                },
                {
                    "coding": [{
                        "system": "http://acr.org/actionable-findings",
                        "code": "CAT1" if "Category 1" in acr_category else "CAT2" if "Category 2" in acr_category else "CAT3",
                        "display": acr_category
                    }]
                }
            ],
            "presentedForm": [
                {
                    "contentType": "application/pdf",
                    "url": f"/api/v1/report/pdf/{study_id}",
                    "title": "ALVEON Certified Radiology Report PDF"
                }
            ]
        }


def get_fhir_engine() -> FHIREngine:
    return FHIREngine.get_instance()
