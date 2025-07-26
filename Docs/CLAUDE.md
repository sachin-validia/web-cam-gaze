# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Installation & Setup
```bash
# One-command cross-platform installation (handles Python, venv, dependencies)
python setup/install.py

# Manual virtual environment activation
source venv/bin/activate  # Mac/Linux
venv\Scripts\activate     # Windows

# Startup scripts (activates venv and shows available commands)
./start_unix.sh          # Mac/Linux
start_windows.bat        # Windows
```

### Main Applications
```bash
# Interview system - setup candidate calibration
python scripts/interview/calibration.py

# Interview system - analyze recorded videos for cheating detection
python scripts/interview/analyzer.py

# Alternative gaze estimation systems
python src/main.py       # Traditional OpenCV gaze tracking
python src/main_pl.py    # PyTorch Lightning gaze estimation

# Camera calibration utility
python camera_data/main_camera_calibration.py
```

### Testing & Verification
```bash
# Test platform detection and device compatibility
python -c "from utils.platform_utils import get_platform_manager; pm = get_platform_manager(); print(f'Platform: {pm.system}, Device: {pm.get_model_device()}')"

# Test installations
python -c "import cv2; print(f'OpenCV: {cv2.__version__}')"
python -c "import torch; print(f'PyTorch: {torch.__version__}')"
python -c "import screeninfo; print(f'Monitors: {len(screeninfo.get_monitors())}')"
```

## Architecture

### Core Systems
This is a **web camera gaze estimation and cheating detection system** with two main architectural approaches:

1. **Interview System** (Primary): For analyzing recorded interviews to detect cheating behavior
   - `scripts/interview/calibration.py` - Pre-interview candidate setup and screen calibration
   - `scripts/interview/analyzer.py` - Post-interview video analysis for cheating detection
   - Uses candidate-specific calibration data stored in `results/interview_calibrations/`
   - Outputs detailed analysis reports to `results/interview_analysis/`

2. **Real-time Gaze Tracking** (Alternative): For live gaze estimation
   - `src/main.py` - Traditional OpenCV-based approach using Intel OpenVINO models
   - `src/main_pl.py` - PyTorch Lightning approach using trained gaze models

### Key Components

#### Gaze Estimation Models
- **PL-GAZE** (`src/plgaze/`): PyTorch Lightning implementation with ETH-XGaze, MPIIGaze models
  - `gaze_estimator.py` - Main estimation pipeline
  - `model_pl_gaze.py` - Model wrapper with platform optimization
  - Pre-trained models: eth-xgaze, mpiifacegaze, mpiigaze
- **Intel OpenVINO** (`intel/`): Hardware-accelerated models for face detection, landmarks, head pose, gaze estimation

#### Platform Adaptation
- `utils/platform_utils.py` - Cross-platform compatibility layer
  - Detects Mac Silicon (M1/M2/M3), Windows, Linux, WSL2
  - Automatic device selection: MPS (Mac), CUDA (GPU), CPU
  - Platform-specific camera backend optimization

#### Homography & Calibration
- `src/gaze_tracking/homtransform.py` - Screen-to-gaze coordinate transformation
- Screen calibration enables mapping raw gaze vectors to screen pixel coordinates
- Supports retrospective analysis using stored calibration data

#### Structure from Motion (SFM)
- `src/sfm/` - 3D reconstruction utilities for enhanced accuracy
- Used for robust head pose estimation and gaze vector computation

### Data Flow Architecture

#### Interview Cheating Detection Workflow:
1. **Calibration Phase**: Candidate performs screen calibration → Stores screen dimensions + transformation matrix
2. **Interview Recording**: Standard video recording (no special software needed)
3. **Analysis Phase**: Video + calibration data → Gaze tracking → Screen mapping → Cheating detection

#### Key Data Paths:
- **Input**: `example-videos/` - Sample interview recordings
- **Calibration**: `results/interview_calibrations/` - Per-candidate screen calibration
- **Analysis Output**: `results/interview_analysis/` - Detailed behavioral analysis + plots
- **Models**: `intel/` (OpenVINO), `src/plgaze/models/` (PyTorch)

### Cross-Platform Considerations
- **Installation**: `setup/install.py` handles Python installation across all platforms
- **Dependencies**: `setup/requirements_cross_platform.txt` with platform-specific PyTorch
- **Camera Access**: Different backends (DirectShow-Windows, AVFoundation-Mac, V4L2-Linux)
- **GPU Acceleration**: Automatic selection of MPS/CUDA/CPU based on platform

### Configuration System
- YAML-based configs in `src/plgaze/data/configs/`
- Platform-specific optimizations applied automatically
- Centralized path management in `config/paths.py`

## Important Notes
- Always run from project root directory
- Virtual environment must be activated for all operations
- Camera permissions required on Mac/Windows
- GPU acceleration auto-detected and configured
- Results directories created automatically as needed