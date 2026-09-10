import io
import numpy as np
import pytest
from PIL import Image

from core import dicom_handler, preprocessor

def test_create_and_parse_synthetic_dicom(tmp_path):
    """Test generating a native 16-bit DICOM and parsing it back."""
    # Create test 16-bit pixel data
    pixels = (np.ones((256, 256), dtype=np.uint16) * 1200)
    # Add a bright region
    pixels[100:150, 100:150] = 3000

    dcm_bytes = dicom_handler.create_synthetic_dicom(
        pixel_array=pixels,
        patient_id="MRN-TEST-99",
        patient_name="DOE^JANE",
        kvp=120.0,
        exposure_time=15,
        bits_allocated=16
    )

    assert isinstance(dcm_bytes, bytes)
    assert len(dcm_bytes) > 1000

    # Parse DICOM bytes
    parsed_array, meta = dicom_handler.parse_dicom(dcm_bytes)

    assert parsed_array.ndim == 2
    assert parsed_array.dtype == np.uint8
    assert parsed_array.shape == (256, 256)
    assert meta["is_dicom"] is True
    assert meta["patient_id"] == "MRN-TEST-99"
    assert meta["patient_name"] == "DOE^JANE"
    assert "120" in str(meta["kvp"])
    assert "15" in str(meta["exposure_time"])
    assert meta["bits_allocated"] == 16
    assert len(meta["all_tags"]) > 0

def test_dicom_monochrome1_inversion():
    """Test that MONOCHROME1 interpretation properly inverts intensities."""
    # Gradient 0 to 4095
    pixels = np.linspace(0, 4095, 256 * 256, dtype=np.uint16).reshape((256, 256))
    
    dcm_bytes = dicom_handler.create_synthetic_dicom(
        pixel_array=pixels,
        photometric="MONOCHROME1"
    )

    parsed_array, meta = dicom_handler.parse_dicom(dcm_bytes)
    assert meta["photometric_interpretation"] == "MONOCHROME1"
    assert parsed_array.dtype == np.uint8
    # Under MONOCHROME1, pixel 0 (minimum) is inverted to 255 (bright)
    assert parsed_array[0, 0] > 240
    assert parsed_array[-1, -1] < 15

def test_preprocessor_load_image_or_dicom_with_dicom():
    """Test load_image_or_dicom with binary DICOM payload."""
    pixels = (np.ones((128, 128), dtype=np.uint16) * 2000)
    dcm_bytes = dicom_handler.create_synthetic_dicom(
        pixel_array=pixels,
        patient_id="MRN-PRE-1"
    )

    image_array, meta = preprocessor.load_image_or_dicom(dcm_bytes, filename="test_scan.dcm")
    assert image_array.shape == (128, 128)
    assert meta["is_dicom"] is True
    assert meta["patient_id"] == "MRN-PRE-1"

def test_preprocessor_load_image_or_dicom_with_standard_image():
    """Test load_image_or_dicom with standard JPEG payload."""
    img = Image.new("L", (100, 100), color=128)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    jpeg_bytes = buf.getvalue()

    image_array, meta = preprocessor.load_image_or_dicom(jpeg_bytes, filename="chest_xray.jpg")
    assert image_array.shape == (100, 100)
    assert meta["is_dicom"] is False
    assert meta["patient_id"] == "CHEST_XRAY"

def test_preprocessor_load_image_or_dicom_invalid_file():
    """Test error handling on corrupted binary input."""
    with pytest.raises(ValueError, match="DICOM decompression failed|Unsupported"):
        preprocessor.load_image_or_dicom(b"NOT_A_VALID_IMAGE_OR_DICOM", filename="bad.dcm")
