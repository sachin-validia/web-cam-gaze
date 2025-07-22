"""
Centralized path configuration for the web-cam-gaze project.
This module provides consistent path handling across all scripts.
"""

from pathlib import Path

# Root directory of the project
ROOT_DIR = Path(__file__).parent.parent

# Source directories
SRC_DIR = ROOT_DIR / "src"
GAZE_TRACKING_DIR = SRC_DIR / "gaze_tracking"
PLGAZE_DIR = SRC_DIR / "plgaze"
SFM_DIR = SRC_DIR / "sfm"
UTILITIES_DIR = SRC_DIR / "utilities"

# Script directories
SCRIPTS_DIR = ROOT_DIR / "scripts"
INTERVIEW_SCRIPTS_DIR = SCRIPTS_DIR / "interview"
BATCH_SCRIPTS_DIR = SCRIPTS_DIR / "batch"
ANALYSIS_SCRIPTS_DIR = SCRIPTS_DIR / "analysis"

# Setup and test directories
SETUP_DIR = ROOT_DIR / "setup"
TESTS_DIR = ROOT_DIR / "tests"
UTILS_DIR = ROOT_DIR / "utils"

# Data directories
CAMERA_DATA_DIR = ROOT_DIR / "camera_data"
INTEL_DIR = ROOT_DIR / "intel"
EXAMPLE_VIDEOS_DIR = ROOT_DIR / "example-videos"
RESULTS_DIR = ROOT_DIR / "results"
OLD_SCRIPTS_DIR = ROOT_DIR / "old_scripts"

# Results subdirectories
CALIBRATION_DIR = RESULTS_DIR / "interview_calibrations"
VIDEO_ANALYSIS_DIR = RESULTS_DIR / "video_analysis"

# Model directories
PLGAZE_MODELS_DIR = PLGAZE_DIR / "models"
PLGAZE_DATA_DIR = PLGAZE_DIR / "data"

# Intel model directories
PUPIL_SEGMENTATION_DIR = INTEL_DIR / "PupilSegmentation"
FACE_DETECTION_DIR = INTEL_DIR / "face-detection-adas-0001"
FACIAL_LANDMARKS_DIR = INTEL_DIR / "facial-landmarks-35-adas-0002"
GAZE_ESTIMATION_DIR = INTEL_DIR / "gaze-estimation-adas-0002"
HEAD_POSE_ESTIMATION_DIR = INTEL_DIR / "head-pose-estimation-adas-0001"
LANDMARKS_REGRESSION_DIR = INTEL_DIR / "landmarks-regression-retail-0009"
OPEN_CLOSED_EYE_DIR = INTEL_DIR / "open-closed-eye-0001"

def ensure_dir(path):
    """Ensure a directory exists, creating it if necessary."""
    Path(path).mkdir(parents=True, exist_ok=True)
    return path

def get_model_path(model_type, precision="FP32"):
    """Get the path to a specific Intel model with given precision."""
    model_dirs = {
        "face_detection": FACE_DETECTION_DIR,
        "facial_landmarks": FACIAL_LANDMARKS_DIR,
        "gaze_estimation": GAZE_ESTIMATION_DIR,
        "head_pose": HEAD_POSE_ESTIMATION_DIR,
        "landmarks_regression": LANDMARKS_REGRESSION_DIR,
        "open_closed_eye": OPEN_CLOSED_EYE_DIR,
        "pupil_segmentation": PUPIL_SEGMENTATION_DIR
    }
    
    if model_type not in model_dirs:
        raise ValueError(f"Unknown model type: {model_type}")
    
    model_dir = model_dirs[model_type]
    
    # Pupil segmentation doesn't have precision subdirectories
    if model_type == "pupil_segmentation":
        return model_dir
    
    return model_dir / precision