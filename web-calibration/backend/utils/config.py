"""
Configuration settings for the calibration API
"""

from pydantic_settings import BaseSettings
from typing import List
import os
from pathlib import Path
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Load environment variables BEFORE the Settings class is instantiated.
# Priority order:
#   1. `.env` inside the backend package (same directory as app.py)
#   2. Project-root `.env`
# This lets users keep credentials out of source control yet avoids the
# "Access denied (using password: NO)" error when defaults are picked.
# ---------------------------------------------------------------------------
CURRENT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = CURRENT_DIR.parent
PROJECT_ROOT = BACKEND_DIR.parent.parent  # web-calibration or repo root

# Try backend/.env first, then fallback to project root
for candidate in (BACKEND_DIR / ".env", PROJECT_ROOT / ".env"):
    if candidate.exists():
        load_dotenv(dotenv_path=candidate, override=False)
        break


class Settings(BaseSettings):
    """Application settings"""

    # API Settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True

    # Database Settings
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_USER: str = "calibration_user"
    DB_PASSWORD: str = ""
    DB_NAME: str = "calibration_db"

    # Security Settings
    SECRET_KEY: str = "your-secret-key-here-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # CORS Settings
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000",
    ]

    # File paths
    PROJECT_ROOT: Path = PROJECT_ROOT
    RESULTS_DIR: Path = PROJECT_ROOT / "results" / "interview_calibrations"

    # Calibration settings
    CALIBRATION_TIMEOUT_SECONDS: int = 300  # 5 minutes
    MAX_FRAMES_PER_TARGET: int = 60  # 2 seconds at 30fps
    TARGET_DISPLAY_TIME: float = 2.0  # seconds

    # Model paths (relative to project root)
    PLGAZE_CONFIG: str = "src/plgaze/data/configs/eth-xgaze.yaml"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


settings = Settings()
