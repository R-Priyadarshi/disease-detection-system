import io
import base64
from typing import Union, Tuple, Optional, Dict, Any
import numpy as np
import cv2
from PIL import Image

from core.config import settings
from core.dicom_handler import is_dicom_bytes, parse_dicom_file

class ImagePreprocessingError(ValueError):
    """Raised when an image cannot be read, decoded, or processed."""
    pass

class MedicalImagePreprocessor:
    """Production-grade medical imaging preprocessor for Chest X-Ray analysis."""

    def __init__(
        self,
        target_size: Tuple[int, int] = (settings.INPUT_WIDTH, settings.INPUT_HEIGHT),
        normalization_scale: float = settings.NORMALIZATION_SCALE
    ):
        self.target_size = target_size
        self.normalization_scale = normalization_scale
        # Medical CLAHE filter for radiology contrast enhancement
        self._clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))

    def load_image_or_dicom(
        self,
        image_source: Union[str, bytes, np.ndarray, Image.Image],
        filename: Optional[str] = None
    ) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Loads either a standard image or native binary DICOM (.dcm).
        Returns:
            (raw_gray_uint8, metadata_dict)
        """
        # Check if source is DICOM by extension or bytes signature
        is_dcm_ext = bool(filename and filename.lower().endswith((".dcm", ".dicom")))

        if isinstance(image_source, (bytes, bytearray)):
            if is_dcm_ext or is_dicom_bytes(image_source):
                try:
                    return parse_dicom_file(bytes(image_source))
                except Exception as e:
                    raise ImagePreprocessingError(f"DICOM decompression failed: {str(e)}")
            raw_img = self.load_image(image_source)
        elif isinstance(image_source, str) and (is_dcm_ext or image_source.lower().endswith((".dcm", ".dicom"))):
            try:
                with open(image_source, "rb") as f:
                    return parse_dicom_file(f.read())
            except Exception as e:
                raise ImagePreprocessingError(f"DICOM file load failed: {str(e)}")
        else:
            raw_img = self.load_image(image_source)

        # Standard non-DICOM image metadata stub
        pat_id = filename.rsplit(".", 1)[0].upper() if filename else f"ALV-{np.random.randint(1000, 9999)}"
        if filename:
            clean_stem = filename.rsplit(".", 1)[0].replace("_", " ").replace("-", " ").strip()
            pat_name = clean_stem.title() if clean_stem.islower() else clean_stem
        else:
            pat_name = "ANONYMOUS PATIENT"

        default_meta: Dict[str, Any] = {
            "is_dicom": False,
            "patient_id": pat_id,
            "patient_name": pat_name,
            "patient_age": "52Y",
            "patient_sex": "U",
            "study_date": "20260910",
            "study_time": "120000",
            "modality": "CR (Converted)",
            "body_part_examined": "CHEST",
            "view_position": "PA",
            "kvp": "120 kVp",
            "exposure_time": "12 ms",
            "tube_current": "250 mA",
            "institution_name": "ALVEON Department of Radiology",
            "station_name": "PACS-INSPECT-01",
            "photometric_interpretation": "MONOCHROME2",
            "window_center": 128,
            "window_width": 256,
            "rows": int(raw_img.shape[0]),
            "columns": int(raw_img.shape[1]),
            "bits_allocated": 8,
            "bits_stored": 8,
            "transfer_syntax_uid": "Explicit VR Little Endian (Standard)",
            "sop_instance_uid": f"1.2.826.0.1.3680043.{np.random.randint(100000, 999999)}",
        }
        return raw_img, default_meta

    def load_image(self, image_source: Union[str, bytes, np.ndarray, Image.Image]) -> np.ndarray:
        """
        Loads and decodes image into a 2D grayscale uint8 numpy array.
        Supports file path, raw bytes, numpy array, or PIL Image.
        """
        if isinstance(image_source, (str, bytes, bytearray)):
            if isinstance(image_source, str):
                # File path
                img = cv2.imread(image_source, cv2.IMREAD_GRAYSCALE)
                if img is None:
                    raise ImagePreprocessingError(f"Could not load image from path: {image_source}")
                return img
            else:
                # Raw bytes
                if not image_source:
                    raise ImagePreprocessingError("Received empty image byte buffer.")
                nparr = np.frombuffer(image_source, np.uint8)
                img = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)
                if img is None:
                    raise ImagePreprocessingError("Failed to decode image from byte buffer.")
                return img

        elif isinstance(image_source, Image.Image):
            # PIL Image
            gray_pil = image_source.convert("L")
            return np.array(gray_pil, dtype=np.uint8)

        elif isinstance(image_source, np.ndarray):
            if image_source.ndim == 3:
                if image_source.shape[2] == 4:
                    return cv2.cvtColor(image_source, cv2.COLOR_BGRA2GRAY)
                elif image_source.shape[2] == 3:
                    return cv2.cvtColor(image_source, cv2.COLOR_BGR2GRAY)
                elif image_source.shape[2] == 1:
                    return image_source.squeeze(axis=-1)
            elif image_source.ndim == 2:
                return image_source.astype(np.uint8)
            raise ImagePreprocessingError(f"Unsupported array dimensions: {image_source.shape}")

        raise ImagePreprocessingError(f"Unsupported image source type: {type(image_source)}")

    def apply_clahe(self, gray_img: np.ndarray) -> np.ndarray:
        """Applies Contrast Limited Adaptive Histogram Equalization for pulmonary visibility."""
        if gray_img.dtype != np.uint8:
            gray_img = np.clip(gray_img, 0, 255).astype(np.uint8)
        return self._clahe.apply(gray_img)

    def prepare_tensor(
        self,
        image_source: Union[str, bytes, np.ndarray, Image.Image],
        apply_clahe: bool = False
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Prepares standard input tensor for model prediction.
        
        Returns:
            tensor: (1, 150, 150, 1) float32 normalized array
            resized_display: (150, 150) uint8 grayscale image for display/Grad-CAM
        """
        raw_gray = self.load_image(image_source)

        if apply_clahe:
            processed_gray = self.apply_clahe(raw_gray)
        else:
            processed_gray = raw_gray

        # Resize to standard model input dimensions
        resized = cv2.resize(processed_gray, self.target_size, interpolation=cv2.INTER_AREA)

        # Reshape to (1, H, W, 1)
        tensor = resized.reshape(1, self.target_size[1], self.target_size[0], 1).astype(np.float32)

        # Normalize pixel values
        tensor = tensor / self.normalization_scale

        return tensor, resized

    @staticmethod
    def to_base64_jpeg(image: np.ndarray, quality: int = 90) -> str:
        """Converts an OpenCV uint8 image (grayscale or BGR) to base64 JPEG data URL."""
        if image.ndim == 2:
            bgr = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        else:
            bgr = image

        success, buffer = cv2.imencode(".jpg", bgr, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
        if not success:
            raise ImagePreprocessingError("Failed to encode image to JPEG.")

        b64_str = base64.b64encode(buffer).decode("utf-8")
        return f"data:image/jpeg;base64,{b64_str}"

preprocessor = MedicalImagePreprocessor()
load_image_or_dicom = preprocessor.load_image_or_dicom
load_image = preprocessor.load_image
prepare_tensor = preprocessor.prepare_tensor
to_base64_jpeg = preprocessor.to_base64_jpeg
