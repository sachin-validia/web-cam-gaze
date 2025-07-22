# Installation Guide - WebCam Gaze Estimation

## 🚀 Automatic Installation (Recommended)

The installation script will automatically download and install Python 3.8+ if needed.

### One-Command Installation

```bash
# This works on any platform and handles Python installation
python setup/install.py
```

**What it does:**
1. 🔍 Detects your platform (Mac/Windows/Linux/WSL2)
2. 🐍 Checks for Python 3.8+ (downloads/installs if missing)
3. 📦 Creates virtual environment
4. 🔧 Installs all required packages with platform optimizations
5. 🧪 Tests the installation
6. 📝 Creates startup scripts

## 📋 Prerequisites

### If You Don't Have Python

**No problem!** The installer will automatically:

#### Windows
- Download Python 3.8.18 installer from python.org
- Install locally (no admin rights needed)
- Set up everything automatically

#### Mac (Intel & Apple Silicon)
- Download appropriate .pkg installer
- Install using system installer (requires admin password)
- Supports both Intel and M1/M2/M3 Macs

#### Linux/WSL2
- Try package manager installation first:
  - Ubuntu/Debian: `apt install python3.8`
  - CentOS/RHEL: `yum install python38`
  - Fedora: `dnf install python3.8`
- Fall back to source compilation if needed

### Manual Python Installation (Optional)

If you prefer to install Python manually first:

#### Windows
1. Download from [python.org](https://www.python.org/downloads/windows/)
2. Choose Python 3.8+ (recommended: 3.8.18)
3. ✅ Check "Add Python to PATH"
4. ✅ Check "Install pip"

#### Mac
```bash
# Using Homebrew (recommended)
brew install python@3.8

# Or download from python.org
```

#### Linux
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3.8 python3.8-venv python3.8-dev python3-pip

# CentOS/RHEL
sudo yum install python38 python38-devel

# Fedora
sudo dnf install python3.8 python3.8-devel

# Arch Linux
sudo pacman -S python
```

## 🔧 Installation Steps

### Step 1: Download/Clone Repository
```bash
git clone <repository-url>
cd web-cam-gaze
```

### Step 2: Run Installer
```bash
# Automatic installation (handles everything)
python setup/install.py
```

### Step 3: Test Installation
```bash
# Test everything is working
python -c "from utils.platform_utils import get_platform_manager; pm = get_platform_manager(); print(f'Platform: {pm.system}, Device: {pm.get_model_device()}')"
```

### Step 4: Start Using
```bash
# Windows
start_windows.bat

# Mac/Linux
./start_unix.sh
```

## 🔧 Manual Installation (Advanced)

If you want to install manually:

```bash
# 1. Ensure Python 3.8+
python --version  # Should show 3.8+

# 2. Create virtual environment
python -m venv venv

# 3. Activate virtual environment
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# 4. Install requirements
pip install -r setup/requirements_cross_platform.txt

# 5. Test installation
python -c "from utils.platform_utils import get_platform_manager; pm = get_platform_manager(); print('Installation test passed')"
```

## 🎯 Platform-Specific Notes

### Windows 🪟
- **Python Installation**: Downloaded to local `python38/` folder
- **No Admin Rights**: Installation doesn't require administrator privileges
- **Camera**: Uses DirectShow backend for webcam access
- **Startup**: Use `start_windows.bat` for easy launching

### Mac 🍎
#### Intel Mac
- **Python Installation**: Installed to `/Library/Frameworks/Python.framework/`
- **Camera**: Uses AVFoundation for optimal performance
- **GPU**: CPU optimization (CUDA if available)

#### Apple Silicon (M1/M2/M3)
- **Python Installation**: ARM64-native installer
- **Camera**: Native ARM64 camera support
- **GPU**: Metal Performance Shaders (MPS) acceleration
- **Rosetta**: Some packages may need compatibility mode

### Linux 🐧
- **Python Installation**: Uses package manager first, then source compilation
- **Camera**: V4L2 backend with multiple fallbacks
- **GPU**: CUDA if available, otherwise CPU
- **Permissions**: May need `sudo` for package installation

### WSL2 🐧🪟
- **Python Installation**: Same as Linux but with WSL2 optimizations
- **Camera**: Limited camera access (may need Windows host)
- **Display**: X11 forwarding required for GUI
- **Performance**: Reduced processing load for better compatibility

## 🧪 Troubleshooting

### Python Installation Issues

#### "Permission Denied" on Windows
```bash
# Run as regular user (no admin needed)
python setup/install.py
```

#### "Command not found: python" on Mac/Linux
```bash
# Try with python3
python3 setup/install.py

# Or install Python first
brew install python@3.8  # Mac
sudo apt install python3.8  # Ubuntu
```

#### WSL2 Camera Issues
```bash
# Check if camera is accessible
ls /dev/video*

# If no cameras, use Windows host for camera access
```

### Installation Verification

```bash
# Test platform detection
python -c "from utils.platform_utils import get_platform_manager; pm = get_platform_manager(); print(f'Platform: {pm.system}, Device: {pm.get_model_device()}')"

# Test camera backend
python -c "import cv2; print(f'OpenCV: {cv2.__version__}')"

# Test screen detection
python -c "import screeninfo; print(f'Monitors: {len(screeninfo.get_monitors())}')"

# Test PyTorch
python -c "import torch; print(f'PyTorch: {torch.__version__}, Device: {torch.device(\"mps\" if torch.backends.mps.is_available() else \"cuda\" if torch.cuda.is_available() else \"cpu\")}')"
```

### Common Issues

#### Issue: "ModuleNotFoundError: No module named 'cv2'"
**Solution:**
```bash
# Activate virtual environment first
source venv/bin/activate  # Mac/Linux
# or
venv\Scripts\activate     # Windows

# Reinstall OpenCV
pip uninstall opencv-python
pip install opencv-python
```

#### Issue: "No module named 'torch'"
**Solution:**
```bash
# Platform-specific PyTorch installation
python setup/install.py  # Will fix this automatically
```

#### Issue: Camera not detected
**Solutions:**
- **Windows**: Check Privacy Settings → Camera → Allow apps to access camera
- **Mac**: System Preferences → Security & Privacy → Camera
- **Linux**: Check permissions: `sudo usermod -a -G video $USER`

#### Issue: "ModuleNotFoundError: No module named 'utils.platform_utils'"
**Solution:**
```bash
# Run from project root directory
cd web-cam-gaze
python scripts/interview/calibration.py
```

## 📊 Installation Verification

After installation, you should see:

```
✅ Platform detection working
✅ Python 3.8+ available
✅ Virtual environment created
✅ All packages installed
✅ Camera backend detected
✅ Screen detection working
✅ Gaze model loadable
✅ Cross-platform features enabled
```

## 🚀 Quick Start After Installation

```bash
# 1. Setup candidate calibration
python scripts/interview/calibration.py

# 2. Analyze interview videos
python scripts/interview/analyzer.py

# 3. Run main gaze estimation (alternative)
python src/main.py

# 4. Run PyTorch Lightning version (alternative)
python src/main_pl.py
```

## 📁 File Structure After Installation

```
web-cam-gaze/
├── python38/                         # Custom Python (if installed)
├── python_downloads/                 # Downloaded installers
├── venv/                            # Virtual environment
├── setup/                           # Installation files
│   ├── install.py                   # Main installer
│   ├── requirements_cross_platform.txt
├── scripts/                         # Main executable scripts
│   └── interview/
│       ├── calibration.py          # Interview calibration system
│       └── analyzer.py             # Interview video analyzer
├── src/                            # Source code
│   ├── main.py                     # Main gaze estimation
│   ├── main_pl.py                  # PyTorch Lightning version
│   ├── plgaze/                     # PL-GAZE model implementation
│   ├── gaze_tracking/              # Gaze tracking utilities
│   └── utilities/                  # General utilities
├── utils/                          # Platform utilities
│   └── platform_utils.py          # Cross-platform support
├── config/                         # Configuration files
│   └── paths.py                    # Centralized path management
├── start_windows.bat               # Windows launcher
├── start_unix.sh                   # Mac/Linux launcher
├── camera_data/                    # Camera calibration data
└── results/                        # Output directories
    ├── interview_calibrations/
    ├── interview_analysis/
    └── video_analysis/
```

## 🔄 Updating Installation

To update or reinstall:

```bash
# Clean installation
rm -rf venv python38 python_downloads

# Reinstall
python setup/install.py
```

## 💡 Tips

1. **First Time**: Always test platform detection after installation
2. **Camera Issues**: Test camera permissions before calibration
3. **Performance**: Mac Silicon and CUDA GPUs get automatic acceleration
4. **WSL2 Users**: Consider using Windows for camera access
5. **Offline Use**: Installers are cached in `python_downloads/` for reuse
6. **Virtual Environment**: Always activate `venv` before running scripts
7. **Project Root**: Run all commands from the `web-cam-gaze/` directory

## 🎯 Available Scripts

### Interview System
- `scripts/interview/calibration.py` - Setup candidate calibration
- `scripts/interview/analyzer.py` - Analyze interview videos

### Core Gaze Estimation
- `src/main.py` - Main gaze estimation system
- `src/main_pl.py` - PyTorch Lightning based system

### Camera Utilities
- `camera_data/main_camera_calibration.py` - Camera calibration

### Platform Testing
- `utils/platform_utils.py` - Platform detection and optimization

The installation system is designed to "just work" on any platform with minimal user intervention! 🎉