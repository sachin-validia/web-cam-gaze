# Cross-Platform WebCam Gaze Estimation

This system now works seamlessly across **Mac (Intel & Apple Silicon)**, **Windows**, and **Linux (including WSL2)**.

## 🚀 Quick Installation

### Option 1: Automated Installation (Recommended)

```bash
# Download and run the cross-platform installer
python3 install_cross_platform.py
```

### Option 2: Manual Installation

#### For Mac (Intel/Apple Silicon)
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install requirements
pip install -r requirements_cross_platform.txt

# Mac Silicon gets MPS acceleration automatically
# Intel Mac uses CPU/CUDA if available
```

#### For Windows
```batch
REM Create virtual environment
python -m venv venv
venv\Scripts\activate

REM Install requirements
pip install -r requirements_cross_platform.txt

REM Windows uses CPU optimization by default
```

#### For Linux/WSL2
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install requirements
pip install -r requirements_cross_platform.txt

# WSL2 uses CPU with special camera handling
```

## 🔧 Platform-Specific Features

### Mac Optimizations
- **Apple Silicon (M1/M2)**: Automatic MPS (Metal Performance Shaders) acceleration
- **Intel Mac**: CPU/CUDA optimization
- **Camera**: AVFoundation backend for best compatibility
- **Display**: Native fullscreen support

### Windows Optimizations
- **Camera**: DirectShow backend for webcam access
- **Processing**: CPU-optimized PyTorch builds
- **Display**: Native Windows display handling
- **Startup**: Batch file for easy launching

### Linux/WSL2 Optimizations
- **WSL2 Detection**: Automatic WSL2 environment detection
- **Camera**: V4L2 backend with fallbacks
- **Display**: X11 forwarding support
- **Reduced Load**: Lower processing requirements for WSL2

## 🎯 Starting the System

### Windows
```batch
# Easy start
start_windows.bat

# OR manually
venv\Scripts\activate
python interview_calibration_system.py
```

### Mac/Linux
```bash
# Easy start
./start_unix.sh

# OR manually
source venv/bin/activate
python interview_calibration_system.py
```

## 📋 Cross-Platform Workflow

### 1. Setup Candidate Calibration
```bash
python interview_calibration_system.py
```
**Works on all platforms:**
- Automatic screen detection
- Cross-platform camera access
- Adaptive UI for different screens

### 2. Analyze Interview Videos
```bash
python interview_video_analyzer.py
```
**Platform adaptations:**
- Video codec compatibility
- Memory optimization per platform
- Path handling (Windows vs Unix)

### 3. Detect Cheating Behavior
```bash
python cheating_detection_system.py
```
**Consistent across platforms:**
- Same detection algorithms
- Platform-optimized visualization
- Cross-platform file handling

## 🔍 Platform Detection

The system automatically detects:
- **Operating System**: Mac, Windows, Linux, WSL2
- **Architecture**: Intel x64, Apple Silicon ARM64
- **Capabilities**: Camera backends, display support, GPU acceleration

```python
from platform_utils import get_platform_manager

pm = get_platform_manager()
print(f"Platform: {pm.system}")
print(f"Device: {pm.get_model_device()}")  # mps, cuda, or cpu
```

## 🎥 Camera Compatibility

### Mac
- **Built-in cameras**: Full support via AVFoundation
- **External USB cameras**: Automatic detection
- **Settings**: Resolution/FPS adaptation

### Windows  
- **Webcams**: DirectShow backend
- **External cameras**: USB Video Class support
- **Settings**: Windows-optimized camera properties

### Linux/WSL2
- **V4L2 devices**: Native Linux camera support
- **WSL2 limitations**: May need camera passthrough
- **Fallbacks**: Multiple backend attempts

## 📊 Performance Optimization

### Device Selection Priority
1. **Mac Silicon**: MPS (Metal Performance Shaders)
2. **NVIDIA GPU**: CUDA acceleration  
3. **CPU**: Optimized CPU inference

### Memory Management
- **Mac**: Native memory mapping
- **Windows**: DirectX memory optimization
- **Linux**: Shared memory optimization
- **WSL2**: Reduced memory footprint

## 🛠️ Troubleshooting

### Mac Issues
```bash
# Camera permission
# System Preferences > Security & Privacy > Camera

# Homebrew conflicts
brew install python@3.9

# M1 Rosetta mode
arch -x86_64 python install_cross_platform.py
```

### Windows Issues
```batch
REM Camera access
REM Settings > Privacy > Camera > Allow apps

REM Python PATH
where python
python --version

REM Virtual environment
python -m pip install --upgrade pip
```

### Linux/WSL2 Issues
```bash
# WSL2 camera passthrough
# Use Windows host camera or USB passthrough

# X11 forwarding for GUI
export DISPLAY=:0

# Permission issues  
sudo usermod -a -G video $USER
```

## 📁 Cross-Platform File Structure

```
WebCamGazeEstimation/
├── platform_utils.py              # Cross-platform compatibility
├── requirements_cross_platform.txt # Universal requirements
├── install_cross_platform.py      # Automated installer
├── start_windows.bat              # Windows launcher
├── start_unix.sh                  # Mac/Linux launcher
├── interview_calibration_system.py # Platform-adaptive calibration
├── interview_video_analyzer.py    # Cross-platform analysis
├── cheating_detection_system.py   # Universal detection
└── results/                       # Cross-platform results
    ├── interview_calibrations/
    ├── interview_analysis/
    └── cheating_analysis/
```

## 🧪 Testing Your Installation

```bash
# Test all platforms
python -c "from platform_utils import get_platform_manager; pm = get_platform_manager(); print(f'Platform: {pm.system}, Device: {pm.get_model_device()}')"

# Test camera (without opening)
python -c "import cv2; print(f'OpenCV: {cv2.__version__}')"

# Test screen detection
python -c "import screeninfo; print(f'Monitors: {len(screeninfo.get_monitors())}')"
```

## 🚨 Known Limitations

### WSL2
- Limited camera access (may need Windows host)
- GUI applications need X11 server
- Reduced performance vs native Linux

### Mac Silicon
- Some packages may need Rosetta 2
- CUDA not available (uses MPS instead)
- Intel packages may need translation

### Windows
- Camera permissions must be granted
- Some antivirus may flag ML models
- Path separators handled automatically

## 📞 Platform Support

- ✅ **Mac Intel**: Full support
- ✅ **Mac Apple Silicon**: Full support with MPS
- ✅ **Windows 10/11**: Full support
- ✅ **Linux**: Full support
- ⚠️ **WSL2**: Limited camera support
- ⚠️ **Docker**: Not recommended for camera access

## 🔄 Migration from Single Platform

If you were using the system on one platform:

1. **Backup calibration data**:
   ```bash
   cp -r results/interview_calibrations/ backup/
   ```

2. **Run cross-platform installer**:
   ```bash
   python install_cross_platform.py
   ```

3. **Restore calibration data**:
   ```bash
   cp -r backup/ results/interview_calibrations/
   ```

The calibration data format is cross-platform compatible!