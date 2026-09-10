from pathlib import Path
from dataclasses import dataclass

BASE_DIR = Path(__file__).resolve().parent.parent

@dataclass(frozen=True)
class Settings:
    PROJECT_NAME: str = "ALVEON"
    PROJECT_FULL_TITLE: str = "ALVEON — Thoracic Diagnostic Intelligence & Clinical PACS"
    PROJECT_VERSION: str = "3.0.0"
    BASE_DIR: Path = BASE_DIR
    
    # Model parameters
    MODEL_WEIGHTS_PATH: Path = BASE_DIR / "TESTCNN.hdf5"
    INPUT_HEIGHT: int = 150
    INPUT_WIDTH: int = 150
    INPUT_CHANNELS: int = 1
    
    # Training Normalization scale compatibility
    NORMALIZATION_SCALE: float = 225.0
    
    # Clinical decision thresholds
    CONFIDENCE_THRESHOLD_POSITIVE: float = 0.50
    RISK_THRESHOLD_HIGH: float = 0.75
    RISK_THRESHOLD_MODERATE: float = 0.40
    
    # Server configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Static & asset directories
    WEB_DIR: Path = BASE_DIR / "web"
    SAMPLES_DIR: Path = BASE_DIR / "core" / "assets" / "samples"

settings = Settings()
