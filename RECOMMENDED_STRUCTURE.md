# Recommended Directory Structure

```
web-cam-gaze/
├── 📁 core/                          # Core application files
│   ├── interview_calibration_system.py
│   ├── video_gaze_analyzer.py
│   └── platform_utils.py
│
├── 📁 src/                           # Source code modules
│   ├── plgaze/                       # Gaze estimation models
│   ├── gaze_tracking/                # Gaze tracking logic
│   ├── sfm/                          # Structure from Motion
│   └── utilities/                    # Utility functions
│
├── 📁 models/                        # Pre-trained models
│   ├── intel/                        # OpenVINO models
│   └── plgaze/                       # PyTorch models
│
├── 📁 setup/                         # Installation and setup
│   ├── install_cross_platform.py
│   ├── python_installer.py
│   ├── requirements.txt
│   ├── requirements_cross_platform.txt
│   └── requirements_pl_gaze.txt
│
├── 📁 scripts/                       # Utility scripts
│   ├── start_unix.sh
│   ├── start_windows.bat
│   ├── test_cross_platform.py
│   └── test_single_video.py
│
├── 📁 tools/                         # Optional tools
│   ├── camera_data/                  # Camera calibration
│   ├── batch_process_videos.py
│   └── process_one_video.py
│
├── 📁 docs/                          # Documentation
│   ├── README.md
│   ├── INSTALL_GUIDE.md
│   ├── README_CROSS_PLATFORM.md
│   └── README_INTERVIEW_SYSTEM.md
│
├── 📁 examples/                      # Example usage
│   └── demo_processing.py
│
├── .gitignore                        # Git ignore file
└── README.md                         # Main readme
```

## Files to NOT commit to Git:
- `results/` - Generated results
- `example-videos/` - Video files (too large)
- `venv/` - Virtual environment
- `*.log` - Log files
- `__pycache__/` - Python cache
- `*.pyc` - Python bytecode