from pathlib import Path
from dataclasses import dataclass

BASE_DIR = Path(__file__).resolve().parent.parent

@dataclass(frozen=True)
class Settings:
    PROJECT_NAME: str = "Chest X-Ray Pneumonia Diagnostic Intelligence"
    PROJECT_VERSION: str = "2.0.0"
    
    # Model parameters
    MODEL_WEIGHTS_PATH: Path = BASE_DIR / "TESTCNN.hdf5"
    INPUT_HEIGHT: int = 150
    INPUT_WIDTH: int = 150
    INPUT_CHANNELS: int = 1
    
    # Training Normalization scale compatibility
    # Original training notebook normalized using X / 225.0
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
