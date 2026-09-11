"""
Deep-Dive Real-Data Verification: HIPAA Safe-Harbor DICOM De-Identification & Anonymizer
Tests real hospital DICOM files from data/dicom_storage/ against DICOM PS 3.15 Annex E
and HIPAA 45 CFR § 164.514(b)(2).
"""

import os
import sys
import glob
import pydicom
import requests
import hashlib

from core.anonymizer import get_dicom_anonymizer, HIPAA_CLEARED_TAGS

def test_real_dicom_deidentification():
    print("=" * 70)
    print("🔬 DEEP-DIVE: REAL-DATA HIPAA DE-IDENTIFICATION & DICOM INTEGRITY")
    print("=" * 70)

    dicom_files = sorted(glob.glob("data/dicom_storage/*.dcm"))
    if not dicom_files:
        raise FileNotFoundError("No DICOM files found in data/dicom_storage/")

    print(f"Found {len(dicom_files)} authentic DICOM files in data/dicom_storage/")

    engine = get_dicom_anonymizer()

    # Select 5 diverse sample DICOM files
    test_samples = dicom_files[:5]
    
    for idx, fpath in enumerate(test_samples, 1):
        fname = os.path.basename(fpath)
        print(f"\n--- [Sample {idx}/5]: {fname} ---")
        
        orig_ds = pydicom.dcmread(fpath)
        orig_name = str(orig_ds.get("PatientName", "Unknown"))
        orig_id = str(orig_ds.get("PatientID", "Unknown"))
        orig_study_uid = str(orig_ds.get("StudyInstanceUID", "Unknown"))
        orig_rows = orig_ds.get("Rows", None)
        orig_cols = orig_ds.get("Columns", None)
        orig_pixel_len = len(orig_ds.PixelData) if hasattr(orig_ds, "PixelData") else 0

        print(f"Original PatientName     : {orig_name}")
        print(f"Original PatientID       : {orig_id}")
        print(f"Original StudyInstanceUID: {orig_study_uid[:35]}...")
        print(f"Original Dimensions      : {orig_rows} x {orig_cols} (Pixels: {orig_pixel_len} bytes)")

        # 1. Audit before anonymization
        pre_audit = engine.audit_deidentification(orig_ds)
        print(f"Pre-anonymization Audit  : is_compliant={pre_audit['is_compliant']}, leaks_found={pre_audit['leaks_found']}")
        
        # 2. Anonymize dataset with custom pseudonyms
        custom_pseudo = f"CLINICAL_TRIAL_SUBJ_{idx:03d}"
        anon_ds, audit_summary = engine.anonymize_dataset(
            orig_ds,
            patient_pseudonym=custom_pseudo
        )

        # 3. Verify Safe Harbor Replacements
        assert str(anon_ds.PatientName) == custom_pseudo, f"PatientName mismatch: {anon_ds.PatientName}"
        assert anon_ds.PatientID.startswith("ANON-MRN-"), f"PatientID mismatch: {anon_ds.PatientID}"
        assert anon_ds.AccessionNumber.startswith("AN-ACC-"), f"AccessionNumber mismatch: {anon_ds.AccessionNumber}"
        assert len(anon_ds.AccessionNumber) <= 16, f"AccessionNumber VR SH overflow: {len(anon_ds.AccessionNumber)}"
        assert anon_ds.StudyID.startswith("ANON-ST-"), f"StudyID mismatch: {anon_ds.StudyID}"
        assert len(anon_ds.StudyID) <= 16, f"StudyID VR SH overflow: {len(anon_ds.StudyID)}"

        # 4. Verify UID Regeneration
        assert anon_ds.StudyInstanceUID != orig_study_uid, "StudyInstanceUID was not regenerated!"
        assert anon_ds.StudyInstanceUID.startswith("1.2.826.0.1.3680043.8.498."), "Invalid UID root!"
        assert len(anon_ds.StudyInstanceUID) <= 64, "UID exceeds 64 chars DICOM VR UI constraint!"

        # 5. Verify 25+ Direct Tags Cleared
        for tag in HIPAA_CLEARED_TAGS:
            assert tag not in anon_ds, f"Found uncleared sensitive tag: ({tag[0]:04X},{tag[1]:04X})"

        # 6. Verify DICOM PS 3.15 Annex E Attributes
        assert anon_ds.PatientIdentityRemoved == "YES", "PatientIdentityRemoved != YES"
        assert "Safe Harbor" in anon_ds.DeidentificationMethod
        assert hasattr(anon_ds, "DeidentificationMethodCodeSequence")
        code_seq = anon_ds.DeidentificationMethodCodeSequence
        assert len(code_seq) > 0
        assert code_seq[0].CodeValue == "113100"
        assert code_seq[0].CodingSchemeDesignator == "DCM"

        # 7. Verify Pixel Data & Geometry Completely Intact
        assert anon_ds.Rows == orig_rows, "Rows altered!"
        assert anon_ds.Columns == orig_cols, "Columns altered!"
        if hasattr(orig_ds, "PixelData"):
            assert len(anon_ds.PixelData) == orig_pixel_len, "PixelData length altered!"
            # Hash comparison of raw pixel data
            orig_hash = hashlib.sha256(orig_ds.PixelData).hexdigest()
            anon_hash = hashlib.sha256(anon_ds.PixelData).hexdigest()
            assert orig_hash == anon_hash, "PixelData content corrupted or mutated!"
            print(f"Pixel Buffer SHA-256     : {orig_hash[:16]}... (Identical, bit-for-bit preserved)")

        # 8. Audit after anonymization
        post_audit = engine.audit_deidentification(anon_ds)
        print(f"Post-anonymization Audit : is_compliant={post_audit['is_compliant']}, leaks_found={post_audit['leaks_found']}")
        assert post_audit["is_compliant"] is True, "Post audit failed: marked as not compliant"
        assert post_audit["leaks_found"] == 0, f"Found remaining leaks: {post_audit['leaks']}"

        # 9. Save and re-read from disk
        saved_path, out_fname, fsize = engine.save_anonymized_dataset(anon_ds)
        assert os.path.exists(saved_path), f"File not written to {saved_path}"
        reread_ds = pydicom.dcmread(saved_path)
        assert reread_ds.PatientIdentityRemoved == "YES"
        assert str(reread_ds.PatientName) == custom_pseudo
        print(f"Disk Persistence Readback: {out_fname} ({fsize} bytes) verified OK")

        # Clean up temporary test output file
        if os.path.exists(saved_path):
            os.remove(saved_path)

    print("\n✅ ALL 5 REAL-DATA DICOM DATASETS PASSED SAFE-HARBOR AUDIT WITH BIT-FOR-BIT PIXEL FIDELITY!")

def test_live_anonymizer_api():
    print("\n" + "=" * 70)
    print("🌐 DEEP-DIVE: LIVE REST API PROBING ON http://127.0.0.1:8000")
    print("=" * 70)

    # 1. Test POST /api/v1/anonymize with study_id
    payload = {
        "study_id": "ALV-STAT-09",
        "pseudonym": "TEST^ER^DEEPDIVE",
        "patient_id": "ER-TEST-99",
        "remove_private_tags": True
    }
    resp = requests.post("http://127.0.0.1:8000/api/v1/anonymize", json=payload, timeout=10)
    print(f"POST /api/v1/anonymize status: {resp.status_code}")
    assert resp.status_code == 200, f"Failed: {resp.text}"
    data = resp.json()
    assert data["status"] == "success"
    assert "HIPAA" in data["standard_conformance"]
    assert len(data["diff_table"]) >= 10
    print(f"  - Generated File Name: {data['anonymized_filename']}")
    print(f"  - Download URL       : {data['download_url']}")
    print(f"  - Audited Diff Tags  : {len(data['diff_table'])}")

    # 2. Test GET download endpoint
    dl_resp = requests.get(f"http://127.0.0.1:8000{data['download_url']}", timeout=10)
    print(f"GET {data['download_url']} status: {dl_resp.status_code}")
    assert dl_resp.status_code == 200
    assert len(dl_resp.content) > 1000
    print(f"  - Downloaded Binary Size: {len(dl_resp.content)} bytes")

    # Verify downloaded content is valid DICOM
    import io
    dl_ds = pydicom.dcmread(io.BytesIO(dl_resp.content))
    assert dl_ds.PatientIdentityRemoved == "YES"
    assert str(dl_ds.PatientName) == "TEST^ER^DEEPDIVE"
    print("  - Binary Stream readback verified with pydicom: PatientIdentityRemoved='YES'")

    # Clean up downloaded file from disk
    file_on_disk = os.path.join("data/anonymized", data["anonymized_filename"])
    if os.path.exists(file_on_disk):
        os.remove(file_on_disk)

    # 3. Test POST /api/v1/anonymize/audit
    audit_resp = requests.post(
        "http://127.0.0.1:8000/api/v1/anonymize/audit",
        json={"study_id": "ALV-STAT-09"},
        timeout=10
    )
    print(f"POST /api/v1/anonymize/audit status: {audit_resp.status_code}")
    assert audit_resp.status_code == 200
    audit_data = audit_resp.json()
    print(f"  - Audit Status   : {audit_data['status']}")
    print(f"  - Is Compliant   : {audit_data['is_compliant']}")
    print(f"  - PHI Tags Found : {audit_data['phi_detected_count']}")
    assert audit_data["status"] == "success"

    print("\n✅ ALL LIVE REST API ENDPOINTS VALIDATED SUCCESSFULLY!")

if __name__ == "__main__":
    try:
        test_real_dicom_deidentification()
        test_live_anonymizer_api()
        print("\n" + "=" * 70)
        print("🎉 ALL REAL-DATA DEEP-DIVE CHECKS PASSED WITH 0 DEFECTS!")
        print("=" * 70)
    except Exception as e:
        print(f"\n❌ Deep-Dive Verification Failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
