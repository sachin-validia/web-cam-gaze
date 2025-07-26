# Web Calibration Gaze System - Local Setup Guide

## Overview
This guide provides comprehensive instructions for setting up the complete web-calibration gaze system and analyzer on a local development machine. The system consists of:

- **Web Calibration Frontend** (React + TypeScript)
- **Web Calibration Backend** (FastAPI + Python)
- **MySQL Database** (Calibration data storage)
- **Python Environment** (Core gaze estimation libraries)
- **Interview Analyzer** (Video analysis system)

## System Requirements

### Minimum Hardware
- **CPU**: Dual-core processor (Intel i5 or equivalent)
- **RAM**: 8GB (16GB recommended)
- **Storage**: 5GB available space
- **Camera**: USB webcam or built-in camera
- **OS**: Windows 10+, macOS 10.15+, or Linux (Ubuntu 18.04+)

### Software Prerequisites
- **Python**: 3.8+ (automatically installed by setup script)
- **Node.js**: 16+ (for frontend development)
- **MySQL**: 8.0+ (for database)
- **Git**: For repository management

## Quick Start (Automated Installation)

### 1. Clone Repository
```bash
git clone https://github.com/sachin-validia/web-cam-gaze
cd web-cam-gaze
```

### 2. Run Cross-Platform Setup
```bash
# On all platforms
python setup/install.py
```

This automated script will:
- Install Python 3.8+ if not available
- Create virtual environment
- Install all required dependencies
- Test the installation
- Create platform-specific startup scripts

### 3. Start Components
```bash
# Activate virtual environment
source venv/bin/activate  # Linux/Mac
# OR
venv\Scripts\activate     # Windows

# Start backend
cd web-calibration/
python -m backend.app

# Start frontend (in new terminal)
cd web-calibration/frontend
npm install
npm run dev
```

## Manual Installation (Step-by-Step)

### Step 1: Python Environment Setup

#### 1.1 Create Virtual Environment
```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

#### 1.2 Install Core Dependencies
```bash
# Upgrade pip
pip install --upgrade pip

# Install main dependencies
pip install -r setup/requirements_cross_platform.txt

# Install web backend dependencies
pip install -r web-calibration/backend/requirements.txt

Contact sachin@validia.ai if any issues in dependency installation 
```

### Step 2: Database Setup

#### 2.1 Install MySQL
**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install mysql-server mysql-client
sudo mysql_secure_installation
```

**macOS (with Homebrew):**
```bash
brew install mysql
brew services start mysql
mysql_secure_installation
```

**Windows:**
- Download MySQL installer from https://dev.mysql.com/downloads/installer/
- Run installer and follow setup wizard

#### 2.2 Create Database and User
```sql
-- Connect to MySQL as root
mysql -u root -p

-- Create database
CREATE DATABASE calibration_db;

-- Create user (recommended)
CREATE USER 'validia'@'localhost' IDENTIFIED BY 'your_password_here';
GRANT ALL PRIVILEGES ON calibration_db.* TO 'validia'@'localhost';
FLUSH PRIVILEGES;

-- Import schema
USE calibration_db;
SOURCE web-calibration/backend/db/schema.sql;
```

### Step 3: Environment Configuration

#### 3.1 Backend Environment Variables
Create `.env` file in `web-calibration/backend/`:

```env
# Database Configuration
DB_HOST=localhost
DB_PORT=3306
DB_USER=validia
DB_PASSWORD=your_password_here
DB_NAME=calibration_db

# API Configuration
HOST=0.0.0.0
PORT=8000
DEBUG=true

# Security
# generate a jwt key using 
python -c "import secrets; print(secrets.token_urlsafe(32))"
SECRET_KEY=your-secret-key-change-in-production  
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# CORS Origins
CORS_ORIGINS=["http://localhost:3000","http://localhost:8000","http://127.0.0.1:3000","http://127.0.0.1:8000"]
```

#### 3.2 Frontend Environment Variables
Create `.env` file in `web-calibration/frontend/`:

```env
VITE_API_BASE_URL=http://localhost:8000
VITE_DEBUG=true
```

### Step 4: Frontend Setup

#### 4.1 Install Node.js Dependencies
```bash
cd web-calibration/frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

#### 4.2 Build for Production (Optional)
```bash
npm run build
npm run preview
```

### Step 5: Verify Installation

#### 5.1 Test Backend
```bash
cd web-calibration/
python -m backend.app
```

Visit: http://localhost:8000 (should show API status)
Visit: http://localhost:8000/docs (Swagger documentation)

#### 5.2 Test Frontend
```bash
cd web-calibration/frontend
npm run dev
```

Visit: http://localhost:3000 (should show calibration interface)

#### 5.3 Test Database Connection
```bash
cd web-calibration/backend
python -c "
from db.database import init_db, get_db
init_db()
db = get_db()
print('Database connection successful!')
"
```

#### 5.4 Test Interview Analyzer
```bash
# Activate virtual environment
source venv/bin/activate

# Test analyzer import
python -c "
from scripts.interview.analyzer import InterviewVideoAnalyzer
analyzer = InterviewVideoAnalyzer()
print('Analyzer initialized successfully!')
"
```

## Usage Instructions

### 1. Web Calibration Process

#### 1.1 Start System
```bash
# Terminal 1: Backend
cd web-calibration/
source ../../venv/bin/activate
python -m backend.app

# Terminal 2: Frontend
cd web-calibration/frontend
npm run dev
```

#### 1.2 Perform Calibration
1. Open http://localhost:3000
2. Enter candidate ID
3. Complete screen setup (resolution detection)
4. Perform camera check
5. Follow calibration targets (9-point calibration)
6. Complete calibration and verify data storage

### 2. Interview Video Analysis

#### 2.1 Analyze Video
```bash
# Activate environment
source venv/bin/activate

# Run analyzer
# for now the main script is to be fixed and under process but the one to test with both web and desktop calibration is working 

## alt script in the root directory
python calibration_comparison_test.py

## for the above you would also need to perform desktop-calibration using the option 1 in the menu first,
## then once we have the calibration from both the desktop-calibration and web. 
## You can then RUN OPTION 3 in the menu option to use analyzer.py on both desktop and web verison of calibration 


## main script 
python scripts/interview/analyzer.py

# Follow prompts:
# 1. Enter candidate ID (from calibration)
# 2. Enter video file path
# 3. Wait for processing
```

#### 2.2 View Results
Results are saved to:
- `results/interview_analysis/{candidate_id}_{video_name}/`
  - `*_gaze_analysis.csv` - Frame-by-frame gaze data
  - `*_analysis_report.json` - Summary statistics
  - `*_analysis_plots.png` - Visualization charts

### 3. Data Flow Verification

#### 3.1 Calibration Data Storage
```bash
# Check calibration files
ls results/interview_calibrations/

# Should contain:
# {candidate_id}_calibration.csv
# {candidate_id}_screen_info.json  
# {candidate_id}_transform_matrix.npz
```

#### 3.2 Database Verification
```sql
-- Connect to database
mysql -u validia -p calibration_db

-- Check tables
SHOW TABLES;

-- Verify calibration data
SELECT candidate_id, created_at FROM calibration_data;
SELECT candidate_id, status FROM calibration_sessions;
```

## Troubleshooting

### After running python setup/install.py
  mysql -u root -p < setup_calibration_db.sql
  mysql -u root -p calibration_db < web-calibration/backend/db/schema.sql

### Common Issues

#### 1. Database Connection Errors
```bash
# Check MySQL service
sudo systemctl status mysql  # Linux
brew services list | grep mysql  # Mac

# Test connection
mysql -u calibration_user -p -h localhost
```

#### 2. Python Import Errors
```bash
# Verify virtual environment
which python  # Should show venv path
pip list  # Check installed packages

# Reinstall requirements
pip install -r setup/requirements_cross_platform.txt
```

#### 3. Camera Access Issues
```bash
# Test camera access
python -c "
import cv2
cap = cv2.VideoCapture(0)
if cap.isOpened():
    print('Camera accessible')
    cap.release()
else:
    print('Camera not accessible')
"
```

#### 4. Frontend Build Issues
```bash
# Clear node modules
rm -rf node_modules package-lock.json
npm install

# Check Node version
node --version  # Should be 16+
npm --version
```

#### 5. Port Conflicts
```bash
# Check port usage
lsof -i :8000  # Backend port
lsof -i :3000  # Frontend port

# Kill process if needed
kill -9 <PID>
```

### Performance Optimization

#### 1. Database Tuning
```sql
-- Optimize MySQL for calibration workload
SET GLOBAL innodb_buffer_pool_size = 256M;
SET GLOBAL max_connections = 100;
```

#### 2. Python Performance
```bash
# Install optimized packages for your platform
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu

# For Mac Silicon
pip install torch torchvision  # Uses MPS acceleration
```

## Platform-Specific Notes

### macOS
- **Camera Permissions**: System Preferences → Security & Privacy → Camera
- **Microphone Access**: May be required for some calibration modes
- **Apple Silicon**: Uses MPS acceleration when available

### Windows
- **Antivirus**: May flag Python executables, add exclusions
- **Windows Defender**: Add project folder to exclusions
- **PowerShell**: Use PowerShell instead of Command Prompt

### Linux (Ubuntu/WSL2)
- **Camera Access**: User must be in `video` group
  ```bash
  sudo usermod -a -G video $USER
  ```
- **X11 Forwarding**: Required for WSL2 GUI applications
- **Permissions**: May need `sudo` for some operations

## File Structure Overview

```
web-cam-gaze/
├── web-calibration/           # Web-based calibration system
│   ├── backend/              # FastAPI backend
│   │   ├── api/              # API endpoints
│   │   ├── db/               # Database connection & schema
│   │   ├── models/           # Business logic
│   │   └── utils/            # Configuration & utilities
│   └── frontend/             # React frontend
│       ├── src/
│       │   ├── components/   # UI components
│       │   ├── pages/        # Page components
│       │   └── api/          # API integration
│       └── public/           # Static assets
├── scripts/interview/        # Analysis scripts
│   ├── analyzer.py           # Video analysis
│   └── calibration.py        # Desktop calibration
├── src/                      # Core gaze estimation
│   ├── plgaze/              # PLGaze model
│   └── gaze_tracking/       # Tracking utilities
├── results/                  # Output directory
│   ├── interview_calibrations/  # Calibration data
│   └── interview_analysis/      # Analysis results
└── setup/                    # Installation scripts
```

## Support and Maintenance

### Regular Maintenance
1. **Database Cleanup**: Remove old calibration sessions periodically
2. **Log Rotation**: Monitor backend logs for errors
3. **Dependency Updates**: Keep packages updated for security

### Backup Procedures
1. **Database Backup**:
   ```bash
   mysqldump -u calibration_user -p calibration_db > backup.sql
   ```

2. **Results Backup**:
   ```bash
   tar -czf results_backup.tar.gz results/
   ```

### Performance Monitoring
- Monitor CPU/RAM usage during video analysis
- Check database query performance
- Monitor disk space for results storage

---

**Note**: This system processes biometric data. Ensure compliance with local privacy regulations and implement appropriate security measures in production environments.