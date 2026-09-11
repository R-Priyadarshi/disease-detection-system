"""
ALVEON HIPAA Safe-Harbor DICOM De-Identification & Anonymizer Unit & Integration Tests
Verifies compliance with:
  1. HIPAA § 164.514(b)(2) Safe Harbor 18 PHI attributes
  2. DICOM PS 3.15 Annex E Basic Application Level Confidentiality Profile
"""

import pytest
import pydicom
from pydicom.dataset import Dataset, FileMetaDataset
from pydicom.uid import generate_uid, ExplicitVRLittleEndian
from fastapi.testclient import TestClient
from pathlib import Path

from core.anonymizer import get_dicom_anonymizer, DicomAnonymizerEngine, HIPAA_CLEARED_TAGS
from api.app import app


@pytest.fixture
def sample_phi_dataset() -> Dataset:
    """Creates a mock DICOM dataset populated with sensitive Protected Health Information (PHI)."""
    ds = Dataset()
    ds.PatientName = "Doe^John^Alexander"
    ds.PatientID = "MRN-SENSITIVE-99482"
    ds.PatientBirthDate = "19750824"
    ds.PatientSex = "M"
    ds.PatientAge = "051Y"
    ds.AccessionNumber = "ACC-HOSP-0911"
    ds.StudyID = "STUDY-REAL-01"
    ds.InstitutionName = "Mercy General Trauma Center"
    ds.StationName = "CT-BAY-03"
    ds.ReferringPhysicianName = "Dr. Robert Caldwell, MD"
    ds.StudyDate = "20260910"
    ds.Modality = "DX"
    ds.SOPClassUID = "1.2.840.10008.5.1.4.1.1.1"
    ds.StudyInstanceUID = "1.2.826.0.1.3680043.9.7123.11111"
    ds.SeriesInstanceUID = "1.2.826.0.1.3680043.9.7123.22222"
    ds.SOPInstanceUID = "1.2.826.0.1.3680043.9.7123.33333"

    # Add sensitive HIPAA tags from the cleared list
    ds.PatientAddress = "742 Evergreen Terrace, Springfield, OR"
    ds.PatientTelephoneNumbers = "+1-555-0199"
    ds.DeviceSerialNumber = "SN-GE-XR-994102"
    ds.PatientComments = "Patient allergic to iodinated contrast. Known cardiac history."

    # File meta
    file_meta = FileMetaDataset()
    file_meta.TransferSyntaxUID = ExplicitVRLittleEndian
    file_meta.MediaStorageSOPClassUID = ds.SOPClassUID
    file_meta.MediaStorageSOPInstanceUID = ds.SOPInstanceUID
    ds.file_meta = file_meta

    return ds


def test_pseudonym_generation():
    engine = get_dicom_anonymizer()
    p1 = engine.generate_pseudonym("John Doe", prefix="ANON-PT")
    p2 = engine.generate_pseudonym("John Doe", prefix="ANON-PT")
    p3 = engine.generate_pseudonym("Jane Smith", prefix="ANON-PT")

    assert p1 == p2, "Pseudonymization must be deterministic for identical input strings"
    assert p1 != p3, "Different identities must produce distinct pseudonyms"
    assert p1.startswith("ANON-PT-")


def test_hipaa_safe_harbor_dataset_cleansing(sample_phi_dataset):
    engine = get_dicom_anonymizer()
    orig_sop = sample_phi_dataset.SOPInstanceUID
    orig_study = sample_phi_dataset.StudyInstanceUID
    orig_series = sample_phi_dataset.SeriesInstanceUID
    orig_name = sample_phi_dataset.PatientName

    anon_ds, audit = engine.anonymize_dataset(
        sample_phi_dataset,
        patient_pseudonym="ANON^CLINICAL^TRIAL",
        mrn_pseudonym="ANON-MRN-4491"
    )

    # 1. Direct Name and MRN
    assert str(anon_ds.PatientName) == "ANON^CLINICAL^TRIAL"
    assert str(anon_ds.PatientID) == "ANON-MRN-4491"
    assert str(anon_ds.PatientName) != orig_name

    # 2. Date of Birth truncated to year or cleared
    assert str(anon_ds.PatientBirthDate) in ("19750101", "")

    # 3. Prohibited HIPAA tags wiped
    assert (0x0010, 0x1040) not in anon_ds, "Patient Address must be scrubbed"
    assert (0x0010, 0x2154) not in anon_ds, "Patient Phone must be scrubbed"
    assert (0x0018, 0x1000) not in anon_ds, "Device Serial Number must be scrubbed"
    assert not hasattr(anon_ds, "PatientComments"), "Patient Comments must be removed"

    # 4. UIDs re-generated
    assert anon_ds.SOPInstanceUID != orig_sop, "SOP Instance UID must be re-generated"
    assert anon_ds.StudyInstanceUID != orig_study
    assert anon_ds.SeriesInstanceUID != orig_series

    # 5. DICOM PS 3.15 Annex E Attributes
    assert getattr(anon_ds, "PatientIdentityRemoved", "") == "YES"
    assert "HIPAA" in getattr(anon_ds, "DeidentificationMethod", "")
    assert hasattr(anon_ds, "DeidentificationMethodCodeSequence")
    assert anon_ds.DeidentificationMethodCodeSequence[0].CodeValue == "113100"

    # 6. Audit summary dictionary
    assert audit["patient_identity_removed"] == "YES"
    assert audit["anonymized_patient_name"] == "ANON^CLINICAL^TRIAL"


def test_audit_deidentification_detection(sample_phi_dataset):
    engine = get_dicom_anonymizer()

    # Raw dataset with PHI should fail audit
    audit_pre = engine.audit_deidentification(sample_phi_dataset)
    assert audit_pre["is_compliant"] is False
    assert audit_pre["leaks_found"] > 0

    # Scrubbed dataset must pass audit
    anon_ds, _ = engine.anonymize_dataset(sample_phi_dataset)
    audit_post = engine.audit_deidentification(anon_ds)
    assert audit_post["is_compliant"] is True
    assert audit_post["leaks_found"] == 0
    assert audit_post["patient_identity_removed"] == "YES"


def test_api_anonymize_endpoints():
    client = TestClient(app)

    # 1. Execute Anonymization
    res = client.post("/api/v1/anonymize", json={
        "custom_patient_name": "ANON^VAL^TEST",
        "custom_patient_id": "ANON-MRN-9988"
    })
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["status"] == "success"
    assert data["anonymized_patient_name"] == "ANON^VAL^TEST"
    assert data["anonymized_patient_id"] == "ANON-MRN-9988"
    assert data["hipaa_rules_cleared"] == 18
    assert len(data["diff_table"]) > 0
    assert data["download_url"].startswith("/api/v1/anonymize/download/")

    # 2. Download Anonymized Binary DICOM
    dl_res = client.get(data["download_url"])
    assert dl_res.status_code == 200
    assert dl_res.headers["content-type"] == "application/dicom"
    assert len(dl_res.content) > 1000

    # 3. Audit Active Study
    audit_res = client.post("/api/v1/anonymize/audit", json={})
    assert audit_res.status_code == 200
    audit_data = audit_res.json()
    assert "hipaa_checklist" in audit_data
    assert audit_data["status"] == "success"
