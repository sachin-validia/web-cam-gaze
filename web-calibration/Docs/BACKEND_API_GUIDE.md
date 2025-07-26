# Backend API Guide & Troubleshooting

## Overview
This document covers the FastAPI backend implementation for the web-based calibration system, including all endpoints, common issues encountered, and their solutions.

## Backend Setup Summary

### Prerequisites
- Python 3.10 (IMPORTANT: Not 3.11+ due to mediapipe compatibility)
- MySQL 5.7+ or MariaDB
- Main project dependencies (PLGaze, mediapipe, dlib)

### Quick Start
```bash
# From main project directory
source venv/bin/activate  # Use main project venv (Python 3.10)
cd web-calibration/backend

# Configure environment
cp .env.example .env
# Edit .env with your MySQL credentials

# Create database
mysql -u root -p -e "CREATE DATABASE calibration_db;"
mysql -u root -p -e "CREATE USER 'validia'@'localhost' IDENTIFIED BY 'your_password';"
mysql -u root -p -e "GRANT ALL PRIVILEGES ON calibration_db.* TO 'validia'@'localhost';"
mysql -u root -p calibration_db < db/schema.sql

# Run backend
python app.py
```

## API Endpoints Reference

Base URL: `http://localhost:8000`

### 1. Session Management

#### Create Session
```bash
POST /api/calibration/session/create
Content-Type: application/json

{
  "candidate_id": "test_candidate_001",
  "interview_id": "interview_001"  # Optional
}

Response:
{
  "session_id": "554a6b4a-46a5-423e-9518-1700b51c9bbc",
  "candidate_id": "test_candidate_001",
  "status": "in_progress",
  "created_at": "2025-07-24T02:55:59.482111",
  "interview_id": "interview_001",
  "metadata": null
}
```

#### Get Session Status
```bash
GET /api/calibration/session/{session_id}

Response:
{
  "exists": true,
  "session_id": "554a6b4a-46a5-423e-9518-1700b51c9bbc",
  "status": "in_progress",
  "created_at": "2025-07-24T02:55:59",
  "updated_at": "2025-07-24T03:00:56",
  "error_message": null
}
```

#### Resume Session
```bash
POST /api/calibration/session/{session_id}/resume
```

#### Link Session to Interview
```bash
POST /api/calibration/session/{session_id}/link?interview_id=new_interview_id
Note: interview_id is a QUERY parameter, not in the body
```

### 2. Screen Information

#### Save Screen Info
```bash
POST /api/screen/info
Content-Type: application/json

{
  "candidate_id": "test_candidate_001",
  "screen_width_px": 1920,      # Note: _px suffix required
  "screen_height_px": 1080,     # Note: _px suffix required
  "dpi": 96                     # Optional, defaults to 96
}

Response:
{
  "success": true,
  "candidate_id": "test_candidate_001",
  "timestamp": "2025-07-24T03:04:53.301191",
  "message": "Screen information saved successfully"
}
```

#### Get Screen Info
```bash
GET /api/screen/info/{candidate_id}

Response:
{
  "candidate_id": "test_candidate_001",
  "screen_width_px": 1920,
  "screen_height_px": 1080,
  "screen_width_mm": 508.0,     # Calculated from DPI
  "screen_height_mm": 285.75,   # Calculated from DPI
  "dpi": 96.0,
  "diagonal_inches": null,
  "monitor_name": "Unknown",
  "camera_position": "top-center",
  "distance_cm": "60",
  "collection_method": "automatic",
  "timestamp": "2025-07-24T03:04:53.301191"
}
```

#### Detect Screen (Auto-detect)
```bash
POST /api/screen/detect
Content-Type: application/json
{}  # Empty body required
```

### 3. Calibration Process

#### Start Calibration
```bash
POST /api/calibration/start
Content-Type: application/json

{
  "session_id": "554a6b4a-46a5-423e-9518-1700b51c9bbc",
  "candidate_id": "test_candidate_001"  # REQUIRED
}

Response:
{
  "session_id": "554a6b4a-46a5-423e-9518-1700b51c9bbc",
  "candidate_id": "test_candidate_001",
  "status": "ready",
  "screen_info": {...},
  "calibration_config": {
    "target_display_time": 2.0,
    "max_frames_per_target": 60,
    "targets": [
      {"index": 0, "position": {"x": 0.1, "y": 0.1}},
      {"index": 1, "position": {"x": 0.9, "y": 0.1}},
      {"index": 2, "position": {"x": 0.1, "y": 0.9}},
      {"index": 3, "position": {"x": 0.9, "y": 0.9}}
    ]
  }
}
```

#### Process Frame
```bash
POST /api/calibration/frame
Content-Type: application/json

{
  "session_id": "554a6b4a-46a5-423e-9518-1700b51c9bbc",
  "candidate_id": "test_candidate_001",
  "frame_data": "data:image/jpeg;base64,...",  # Base64 encoded image
  "frame_index": 0,
  "target_position": {"x": 192, "y": 108},     # Pixel coordinates
  "target_index": 0                             # 0-3
}
```

#### Complete Calibration
```bash
POST /api/calibration/complete
Content-Type: application/json

{
  "session_id": "554a6b4a-46a5-423e-9518-1700b51c9bbc",
  "candidate_id": "test_candidate_001"
}
```

#### Verify Calibration Exists
```bash
GET /api/calibration/verify/{candidate_id}

Response:
{
  "exists": false,  # true if calibration complete
  "candidate_id": null,
  "created_at": null,
  "has_screen_info": true,
  "has_calibration_data": false
}
```

#### Get Session Diagnostics
```bash
GET /api/calibration/diagnostics/{session_id}

Response:
{
  "session_info": {...},
  "frame_count": 0,
  "frame_analysis": {
    "targets_covered": [],
    "frames_per_target": {},
    "face_detection_rate": 0,
    "head_pose_stability": []
  }
}
```

### 4. Utility Endpoints

```bash
GET /                    # API info
GET /health             # Health check
GET /api/ping           # Latency test
GET /docs               # Interactive API documentation (Swagger UI)
GET /redoc              # Alternative API documentation
```

## Common Issues & Solutions

### Issue 1: Python Version Mismatch
**Problem**: Trying to create separate venv with Python 3.11, but mediapipe requires Python 3.10.

**Solution**: Use the main project's venv (Python 3.10) instead of creating a new one:
```bash
# DON'T create new venv in web-calibration
# DO use main project venv
source /path/to/main/project/venv/bin/activate
```

### Issue 2: Database Status ENUM Mismatch
**Problem**: Error "Data truncated for column 'status'" when creating sessions.

**Root Cause**: Database schema had `ENUM('in progress', 'completed', 'failed')` with spaces, but code used 'in_progress' with underscore.

**Solution**: Update database schema to use underscores:
```sql
ALTER TABLE calibration_sessions 
MODIFY COLUMN status ENUM('in_progress', 'completed', 'failed') DEFAULT 'in_progress';
```

### Issue 3: Missing PACKAGE_ROOT in PLGaze Config
**Problem**: `InterpolationKeyError: 'PACKAGE_ROOT' not found` when initializing GazeService.

**Solution**: Register PACKAGE_ROOT resolver in gaze_service.py:
```python
package_root = str(project_root / "src")
OmegaConf.register_new_resolver("PACKAGE_ROOT", lambda: package_root)
```

### Issue 4: Import Path Issues
**Problem**: `ModuleNotFoundError: No module named 'src.gaze_tracking.calibration'`

**Root Cause**: Wrong filename - it's `homtransform.py` not `calibration.py`.

**Solution**: Fix import:
```python
# Wrong
from src.gaze_tracking.calibration import HomTransform
# Correct
from src.gaze_tracking.homtransform import HomTransform
```

### Issue 5: MediaPipe Protobuf Conflicts
**Problem**: TypeError related to protobuf descriptors when MediaPipe loads.

**Root Cause**: Anaconda Python (3.11) being used instead of venv Python (3.10).

**Solution**: Use full path to venv Python or set PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION:
```bash
export PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python
/path/to/venv/bin/python app.py
```

### Issue 6: API Parameter Naming
**Problem**: Pydantic validation errors for missing fields.

**Examples**:
- Field names must match exactly: `screen_width_px` not `screen_width`
- Some parameters are query params, not body: `interview_id` in link endpoint
- Empty body still needs `{}` for POST endpoints like `/api/screen/detect`

## Database Connection Test Script

Save as `test_db_connection.py`:
```python
#!/usr/bin/env python3
import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

config = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', 3306)),
    'user': os.getenv('DB_USER', 'validia'),
    'password': os.getenv('DB_PASSWORD', 'validia123@'),
    'database': os.getenv('DB_NAME', 'calibration_db')
}

try:
    connection = mysql.connector.connect(**config)
    if connection.is_connected():
        print("✓ Successfully connected to MySQL")
        cursor = connection.cursor()
        cursor.execute("SHOW TABLES")
        tables = [table[0] for table in cursor.fetchall()]
        print(f"✓ Found {len(tables)} tables: {', '.join(tables)}")
        connection.close()
except Exception as e:
    print(f"✗ Error: {e}")
```

## Testing Order

1. Test database connection
2. Create session
3. Save screen info
4. Start calibration
5. Process frames (requires webcam data from frontend)
6. Complete calibration
7. Verify and download files

## Notes for Frontend Development

- All endpoints expect JSON content type
- Base64 encode webcam frames before sending
- Session ID is required for most calibration operations
- Target positions are in normalized coordinates (0-1) in config but pixel coordinates in frame requests
- Check `/docs` for interactive testing and detailed schemas

## Environment Variables (.env)

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
DEBUG=True

# Security
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# CORS Origins
CORS_ORIGINS=["http://localhost:3000","http://localhost:8000"]
```

## Next Steps

With the backend fully operational, the React frontend can now:
1. Create calibration sessions via API
2. Capture webcam frames
3. Send frames to backend for processing
4. Display calibration targets
5. Monitor calibration progress
6. Download generated files

The backend handles all the heavy lifting (gaze estimation, homography transformation, file generation) while the frontend focuses on user interaction and webcam capture.