# Calibration Migration Plan: Desktop to React Web Platform

## Overview
This document outlines the complete migration plan for converting the current desktop-based calibration system to a React web application while maintaining full compatibility with the existing analyzer.py workflow.

## Migration Super-Prompt
Our coding style should be following software engineering principles which is to form files in proper directory and sub-directory structure. Each file should be designed to be a microservice and integrated and connected with other files. At each moment we have to keep a log of the files in the directories and we have to get rid of the old files that are no longer in use.  

## Current System Analysis

### Data Format Requirements (CRITICAL - DO NOT CHANGE)
The analyzer expects these exact files per candidate:
```
results/interview_calibrations/
├── {candidate_id}_screen_info.json
├── {candidate_id}_calibration.csv  
└── {candidate_id}_transform_matrix.npz
```

### Screen Info JSON Format
```json
{
  "candidate_id": "string",
  "timestamp": "ISO datetime",
  "collection_method": "automatic|manual",
  "screen_width_px": int,
  "screen_height_px": int,
  "screen_width_mm": float,
  "screen_height_mm": float,
  "camera_position": "string",
  "distance_cm": "string",
  "dpi": float,
  "diagonal_inches": float,
  "monitor_name": "string"
}
```

### Calibration CSV Format
```csv
Unnamed: 0,Timestamp,idx,gaze_x,gaze_y,gaze_z,REyePos_x,REyePos_y,LEyePos_x,LEyePos_y,yaw,pitch,roll,HeadBox_xmin,HeadBox_ymin,RightEyeBox_xmin,RightEyeBox_ymin,LeftEyeBox_xmin,LeftEyeBox_ymin,ROpenClose,LOpenClose,set_x,set_y,set_z,WTransG,[16 WTransG columns which are named as WTransG.1, WTransG.2 and so on till WTransG.15],candidate_id
```

### Transform Matrix NPZ Format
```python
{
  'STransG': numpy.ndarray,     # Main transformation matrix
  'StG': numpy.ndarray,         # Secondary transform (optional)
  'SetValues': numpy.ndarray    # Calibration target positions (optional)
}
```

## Migration Architecture

### System Components
```
┌─────────────────────┐    ┌─────────────────────────┐
│   React Frontend    │◄──►│   Python Backend API    │
├─────────────────────┤    ├─────────────────────────┤
│ • Screen Detection  │    │ • Gaze Processing       │
│ • Camera Access     │    │ • Transform Calculation │
│ • Calibration UI    │    │ • File Generation       │
│ • Target Display    │    │ • API Endpoints         │
└─────────────────────┘    └─────────────────────────┘
                                      │
                              ┌─────────────────┐
                              │ File Generation │
                              │ (Same Format)   │
                              └─────────────────┘
                                      │
                              ┌─────────────────┐
                              │   analyzer.py   │
                              │ (No Changes)    │
                              └─────────────────┘
```

## Phase-by-Phase Implementation Plan

### Phase 0: Integration Planning
**Duration**: 1-2 days
**Goal**: Map integration points with existing platform and video recording workflow

#### Step 0.1: Platform Integration Analysis
- Map existing authentication systems (SSO, JWT)
- Identify video recording bot integration points
- Document data flow from calibration → recording → analysis
- Design storage architecture for cross-system access

#### Step 0.2: Data Persistence Architecture
```
┌─────────────────────┐
│  React Frontend     │
└──────────┬──────────┘
           │
┌──────────▼──────────┐
│  Backend API        │
└──────────┬──────────┘
           │
┌──────────▼──────────┐     ┌─────────────────┐
│  MySQL Database     │◄────┤ Recording Bot   │
│  (Calibration Data)│     └─────────────────┘
└──────────┬──────────┘              │
           │                         │
           └──────────┬──────────────┘
                      ▼
               ┌─────────────────┐
               │  analyzer.py    │
               └─────────────────┘
```

##### MySQL Database Schema
```sql
-- Calibration sessions table
CREATE TABLE calibration_sessions (
    id VARCHAR(36) PRIMARY KEY,
    candidate_id VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    status ENUM('in_progress', 'completed', 'failed') DEFAULT 'in_progress',
    interview_id VARCHAR(255),
    INDEX idx_candidate_id (candidate_id),
    INDEX idx_status (status)
);

-- Screen information table
CREATE TABLE screen_info (
    id INT AUTO_INCREMENT PRIMARY KEY,
    candidate_id VARCHAR(255) NOT NULL UNIQUE,
    screen_data JSON NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_candidate_id (candidate_id)
);

-- Calibration data table
CREATE TABLE calibration_data (
    id INT AUTO_INCREMENT PRIMARY KEY,
    candidate_id VARCHAR(255) NOT NULL,
    calibration_csv LONGTEXT NOT NULL,
    transform_matrix_data LONGBLOB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_candidate_id (candidate_id),
    UNIQUE KEY unique_candidate (candidate_id)
);

-- Calibration frames table (for real-time processing)
CREATE TABLE calibration_frames (
    id INT AUTO_INCREMENT PRIMARY KEY,
    session_id VARCHAR(36) NOT NULL,
    frame_index INT NOT NULL,
    frame_data JSON NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_session_id (session_id),
    FOREIGN KEY (session_id) REFERENCES calibration_sessions(id)
);
```

#### Step 0.3: Session Management Design
- Design calibration session lifecycle
- Plan candidate authentication flow
- Define calibration validity periods
- Create session-interview linking mechanism

### Phase 1: Backend API Foundation
**Duration**: 2-3 days
**Goal**: Create Python backend that can process calibration data

#### Step 1.1: Project Structure Setup
```
web-calibration/
├── backend/
│   ├── app.py              # FastAPI/Flask main app
│   ├── models/
│   │   ├── gaze_service.py # Wrap existing GazeModel
│   │   └── calibration_service.py # Wrap HomTransform
│   ├── api/
│   │   ├── calibration.py  # Calibration endpoints
│   │   └── screen.py       # Screen info endpoints
│   └── utils/
│       └── file_generator.py # Generate exact format files
├── frontend/              # React app (Phase 2)
└── shared/
    └── types.py          # Shared data structures
```

#### Step 1.2: Extract Core Services
- Create `GazeService` class wrapping existing `GazeModel`
- Create `CalibrationService` class wrapping existing `HomTransform`
- Ensure services can process individual frames vs video streams

#### Step 1.3: API Endpoints
```python
# Core Calibration Endpoints
POST /api/calibration/start           # Initialize calibration session
POST /api/calibration/frame          # Process single frame with target position
POST /api/calibration/complete       # Finalize and generate files
POST /api/screen/info               # Store screen information
GET  /api/calibration/{candidate_id} # Retrieve calibration status

# Session Management Endpoints
POST /api/calibration/session/create    # Create unique session ID
POST /api/calibration/session/resume    # Resume interrupted calibration
GET  /api/calibration/session/{id}      # Check session status
POST /api/calibration/session/link      # Link to interview ID

# Data Access Endpoints (for External Systems)
GET  /api/calibration/verify/{candidate_id}  # Verify calibration exists
GET  /api/calibration/download/{candidate_id} # Download calibration files
# Note: These endpoints are for any system that needs calibration data

# Diagnostics & Support
GET  /api/calibration/diagnostics/{id}  # Detailed calibration logs
POST /api/calibration/validate/{id}     # Validate calibration files
GET  /api/calibration/replay/{id}       # Replay calibration for debugging
```

#### Step 1.4: File Generation Service
- Create `FileGenerator` class that produces exact format files
- **CRITICAL**: Validate output files work with existing analyzer.py
- Implement byte-for-byte comparison tests

#### Step 1.5: Database Storage Service
```python
import mysql.connector
import json
import base64
import numpy as np
from io import BytesIO

class DatabaseStorageService:
    """Handles calibration data storage and retrieval using MySQL"""
    
    def __init__(self, db_config):
        self.db_config = db_config
        
    def save_screen_info(self, candidate_id: str, screen_data: dict):
        """Save screen information to database"""
        conn = mysql.connector.connect(**self.db_config)
        cursor = conn.cursor()
        
        query = """
        INSERT INTO screen_info (candidate_id, screen_data) 
        VALUES (%s, %s) 
        ON DUPLICATE KEY UPDATE screen_data = VALUES(screen_data)
        """
        cursor.execute(query, (candidate_id, json.dumps(screen_data)))
        conn.commit()
        cursor.close()
        conn.close()
        
    def save_calibration_data(self, candidate_id: str, csv_data: str, transform_matrix: dict):
        """Save calibration CSV and transform matrix to database"""
        conn = mysql.connector.connect(**self.db_config)
        cursor = conn.cursor()
        
        # Serialize numpy arrays to bytes
        buffer = BytesIO()
        np.savez_compressed(buffer, **transform_matrix)
        matrix_bytes = buffer.getvalue()
        
        query = """
        INSERT INTO calibration_data (candidate_id, calibration_csv, transform_matrix_data) 
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE 
            calibration_csv = VALUES(calibration_csv),
            transform_matrix_data = VALUES(transform_matrix_data)
        """
        cursor.execute(query, (candidate_id, csv_data, matrix_bytes))
        conn.commit()
        cursor.close()
        conn.close()
        
    def get_calibration_files(self, candidate_id: str) -> dict:
        """Retrieve calibration files from database and reconstruct file format"""
        conn = mysql.connector.connect(**self.db_config)
        cursor = conn.cursor()
        
        # Get screen info
        cursor.execute("SELECT screen_data FROM screen_info WHERE candidate_id = %s", (candidate_id,))
        screen_result = cursor.fetchone()
        
        # Get calibration data
        cursor.execute("SELECT calibration_csv, transform_matrix_data FROM calibration_data WHERE candidate_id = %s", (candidate_id,))
        calib_result = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if not screen_result or not calib_result:
            return None
            
        # Reconstruct files
        files = {
            f"{candidate_id}_screen_info.json": json.loads(screen_result[0]),
            f"{candidate_id}_calibration.csv": calib_result[0],
            f"{candidate_id}_transform_matrix.npz": BytesIO(calib_result[1])
        }
        
        return files
        
    def check_calibration_exists(self, candidate_id: str) -> bool:
        """Verify calibration data exists in database"""
        conn = mysql.connector.connect(**self.db_config)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT COUNT(*) FROM calibration_data 
            WHERE candidate_id = %s
        """, (candidate_id,))
        
        count = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        
        return count > 0
```

#### Step 1.6: Platform Integration Services
```python
class AuthService:
    """Handle authentication with main platform"""
    
    def verify_jwt_token(self, token: str) -> dict:
        """Verify JWT from main platform"""
        
    def get_candidate_info(self, token: str) -> dict:
        """Get candidate details from token"""

class WebhookService:
    """Send notifications to main platform"""
    
    def send_calibration_complete(self, candidate_id: str, status: dict):
        """Notify platform when calibration completes"""
        
    def send_calibration_failed(self, candidate_id: str, error: dict):
        """Notify platform of calibration failures"""
```

### Phase 2: React Frontend Development
**Duration**: 3-4 days
**Goal**: Create web-based calibration interface

#### Step 2.1: React App Setup
```bash
npx create-react-app web-calibration-frontend
cd web-calibration-frontend
npm install axios react-webcam
```

#### Step 2.2: Core Components
```
src/
├── components/
│   ├── ScreenSetup.jsx        # Screen dimension collection
│   ├── CalibrationSequence.jsx # 4-dot calibration display
│   ├── CameraPreview.jsx      # WebRTC camera access
│   └── ProgressIndicator.jsx  # Calibration progress
├── hooks/
│   ├── useCamera.js           # Camera access logic
│   ├── useFullscreen.js       # Fullscreen API wrapper
│   └── useCalibration.js      # Calibration state management
├── services/
│   └── api.js                 # Backend API calls
└── utils/
    ├── screenDetection.js     # Screen dimension detection
    └── calibrationTargets.js  # Target position calculations
```

#### Step 2.3: Screen Detection Implementation
```javascript
// Use JavaScript Screen API
const screenInfo = {
  screen_width_px: screen.width,
  screen_height_px: screen.height,
  dpi: window.devicePixelRatio * 96,
  // Physical dimensions calculation or manual input
};
```

#### Step 2.4: Calibration Sequence Implementation
- 4 target positions (corners): 10% and 90% from edges
- Each target displays for 2 seconds
- Red circle (15px radius) display
- Fullscreen mode during calibration
- Frame capture at 30fps during target display

##### Calibration Quality Feedback
```javascript
const CalibrationFeedback = {
  // Real-time quality indicators
  checkHeadStability: (headPose) => {
    // Return stability score 0-100
  },
  
  checkLightingQuality: (frameData) => {
    // Return lighting score 0-100
  },
  
  checkGazeDetection: (gazeConfidence) => {
    // Return detection confidence 0-100
  },
  
  // User guidance messages
  getUserGuidance: (quality) => {
    if (quality.headStability < 50) return "Please keep your head still";
    if (quality.lighting < 30) return "Please improve lighting";
    if (quality.detection < 70) return "Please move closer to camera";
    return "Good positioning!";
  }
};
```

#### Step 2.5: WebRTC Camera Integration
```javascript
const constraints = {
  video: {
    width: { ideal: 1280 },
    height: { ideal: 720 },
    frameRate: { ideal: 30 }
  }
};
```

### Phase 3: Integration & Data Flow
**Duration**: 2-3 days
**Goal**: End-to-end calibration workflow

#### Step 3.1: Calibration Workflow Implementation
1. **Screen Setup**: Collect screen dimensions
2. **Camera Access**: Request permissions and initialize
3. **Calibration Sequence**: Display targets and capture frames
4. **Data Processing**: Send frames to backend for processing
5. **File Generation**: Create analyzer-compatible files
6. **Validation**: Verify files work with analyzer.py

#### Step 3.2: Real-time Data Processing

##### Network Optimization Strategy
```javascript
// Frontend: Batch frame processing for efficiency
const FrameBatcher = {
  frames: [],
  batchSize: 5,
  
  async addFrame(frameData) {
    this.frames.push(frameData);
    
    if (this.frames.length >= this.batchSize) {
      await this.sendBatch();
    }
  },
  
  async sendBatch() {
    const batch = this.frames.splice(0, this.batchSize);
    await api.post('/api/calibration/frames/batch', {
      candidate_id: candidateId,
      frames: batch
    });
  }
};

// Adaptive frame rate based on network
const AdaptiveCapture = {
  async measureLatency() {
    const start = Date.now();
    await api.get('/api/ping');
    return Date.now() - start;
  },
  
  getOptimalFrameRate(latency) {
    if (latency < 50) return 30;    // Good connection
    if (latency < 150) return 15;   // Medium connection
    return 10;                       // Poor connection
  }
};
```

```python
# Backend: Process frames
@app.post("/api/calibration/frame")
async def process_frame(frame_data: FrameData):
    # Decode image
    frame = decode_base64_image(frame_data.frame_data)
    
    # Get gaze estimation
    eye_info = gaze_service.get_gaze(frame)
    
    # Store calibration data
    calibration_service.add_calibration_point(
        eye_info, frame_data.target_position, frame_data.target_index
    )
```

#### Step 3.3: File Generation & Validation
```python
class FileGenerator:
    def generate_screen_info(self, candidate_id: str, screen_data: dict):
        # Generate exact JSON format
        
    def generate_calibration_csv(self, candidate_id: str, calibration_data: list):
        # Generate exact CSV format with all required columns
        
    def generate_transform_matrix(self, candidate_id: str, transform_data: dict):
        # Generate exact NPZ format with STransG, StG, SetValues
```

### Phase 4: Testing & Validation
**Duration**: 2-3 days
**Goal**: Ensure complete compatibility

#### Step 4.1: Compatibility Testing
- **File Format Validation**: Compare generated files with current system output
- **Analyzer Integration**: Test generated files work with analyzer.py
- **Accuracy Testing**: Compare calibration accuracy between systems

#### Step 4.2: Cross-Browser Testing
- Chrome/Chromium (primary)
- Firefox
- Safari
- Edge

#### Step 4.3: Error Handling & Fallbacks
- Camera permission denied
- Fullscreen not supported
- WebRTC not available
- Network connectivity issues

### Phase 5: Platform Integration & Testing
**Duration**: 2-3 days
**Goal**: Integrate with existing platform and video recording workflow

#### Step 5.1: External System Integration
- Implement calibration verification endpoint for external systems
- Add calibration file download capability via API
- Create flexible integration pattern for future systems
- Test calibration data retrieval and file reconstruction
- Note: Specific integration with video recording systems can be implemented later

#### Step 5.2: Authentication Integration
- Integrate with existing platform authentication
- Implement JWT token validation
- Add candidate session management
- Test SSO flow if applicable

#### Step 5.3: Webhook Implementation
- Setup calibration event webhooks
- Implement retry logic for failed notifications
- Add webhook security (HMAC signatures)
- Test integration with platform event system

### Phase 6: Deployment Preparation
**Duration**: 1-2 days
**Goal**: Production-ready deployment

#### Step 6.1: Production Configuration
- Environment variables for backend
- Build optimization for React
- CORS configuration
- SSL/HTTPS setup
- MySQL connection pooling configuration
- Database credentials and connection limits

#### Step 6.2: Documentation
- API documentation (Swagger/OpenAPI)
- Frontend component documentation
- Deployment instructions
- Troubleshooting guide
- Integration guide for recording bot

#### Step 6.3: Monitoring & Logging
- Setup application monitoring (APM)
- Configure structured logging
- Add performance metrics
- Create monitoring dashboards

## Critical Success Factors

### Data Compatibility (NON-NEGOTIABLE)
1. **Exact File Formats**: Generated files must be byte-for-byte compatible
2. **Coordinate Systems**: Screen coordinate calculations must match exactly
3. **Transform Matrix**: Calibration mathematics must be identical

### Testing Requirements
1. **Regression Testing**: Every change must be tested against analyzer.py
2. **Accuracy Validation**: Calibration accuracy must meet or exceed current system
3. **End-to-End Testing**: Complete workflow from web calibration to analysis

### Risk Mitigation
1. **Parallel Systems**: Run both systems during transition period
2. **Rollback Plan**: Maintain ability to revert to desktop system
3. **Comprehensive Logging**: Log all calibration data for debugging

## Implementation Guidelines

### Code Standards
- Follow existing Python code style in the project
- Use TypeScript for React components where possible
- Comprehensive error handling and logging
- Unit tests for all critical functions

### Performance Requirements
- Calibration sequence must complete in under 30 seconds
- Real-time frame processing (30fps minimum)
- Responsive UI during calibration
- Network latency < 200ms for frame processing
- Support degraded mode for poor connections

### Security Considerations
- Secure camera access permissions
- Input validation on all API endpoints
- No sensitive data in browser storage
- JWT token validation for all API calls
- Encrypted storage of calibration data
- GDPR compliance for biometric data

### Data Governance
```yaml
calibration_data_lifecycle:
  retention_period: 90_days
  deletion_policy: automatic
  
  access_control:
    - candidate: read_own_data
    - recording_bot: read_with_token
    - analyzer: read_with_credentials
    - admin: full_access
  
  audit_logging:
    - all_access_attempts
    - data_modifications
    - deletion_events
  
  privacy_compliance:
    - biometric_data_consent_required
    - right_to_deletion
    - data_portability
    - anonymization_option
```

### Time Synchronization
- All timestamps in UTC
- Millisecond precision required
- NTP sync validation on backend
- Store timezone with calibration metadata
- Frame timestamp format: ISO 8601 with milliseconds

## Validation Checklist

Before considering migration complete, verify:

### File Format Compatibility
- [ ] Generated screen_info.json matches exact format
- [ ] Generated calibration.csv has all required columns
- [ ] Generated transform_matrix.npz loads correctly
- [ ] analyzer.py processes web-generated files successfully
- [ ] Byte-for-byte comparison passes for test data

### System Integration
- [ ] Recording bot can access calibration data from MySQL
- [ ] Authentication flow works end-to-end
- [ ] Webhooks fire correctly for all events
- [ ] MySQL database read/write operations work reliably
- [ ] Database connection pooling handles concurrent requests
- [ ] Session management handles interruptions

### Quality & Performance
- [ ] Calibration accuracy meets current system standards
- [ ] Cross-browser compatibility confirmed
- [ ] Network optimization handles poor connections
- [ ] Real-time feedback improves calibration quality
- [ ] 30fps capture rate achieved consistently

### Error Handling & Recovery
- [ ] Camera permission denial handled gracefully
- [ ] Network disconnection recovery works
- [ ] Partial calibration resume functionality
- [ ] Clear error messages for all failure modes
- [ ] Diagnostic data available for support

### Security & Compliance
- [ ] JWT authentication properly implemented
- [ ] Data encryption in transit and at rest
- [ ] GDPR compliance for biometric data
- [ ] Audit logging captures all events
- [ ] Data retention policies enforced

## Future Considerations

### Scalability
- Database storage for calibration data
- Multi-user concurrent calibrations
- Cloud deployment options
- CDN for static assets
- Microservices architecture for high load

### Feature Enhancements
- Real-time calibration accuracy feedback
- Advanced screen detection methods
- Mobile device support
- Multi-monitor support
- Offline calibration with sync
- ML-based calibration quality prediction

### Advanced Integration
- Video conferencing platform plugins
- Browser extensions for easier access
- Native mobile apps for calibration
- CI/CD integration for automated testing

---

**Note**: This document serves as the definitive guide for the migration. Any deviations from this plan must be documented and approved to ensure system compatibility.

## Appendix: Critical Integration Points

### External System Access Pattern (Open-Ended)
```python
# Example: Any external system that needs calibration data
response = requests.get(f"{API_URL}/api/calibration/verify/{candidate_id}",
                       headers={"Authorization": f"Bearer {system_token}"})

if response.status_code == 200:
    # Download calibration files from API (which fetches from MySQL)
    files = requests.get(f"{API_URL}/api/calibration/download/{candidate_id}",
                        headers={"Authorization": f"Bearer {system_token}"})
    
    # The API returns calibration data in standard format
    calibration_data = files.json()
    
    # External systems can use this data as needed
    # For example, saving to local files for video analysis:
    for filename, content in calibration_data.items():
        # Process based on file type
        # This is just an example - actual implementation depends on your needs
        pass
else:
    # Handle missing calibration
    print(f"No calibration found for candidate {candidate_id}")
```

### Analyzer Integration Pattern
```python
# Analyzer loads calibration from database via API
def load_calibration_from_database(candidate_id):
    # Option 1: Direct database access
    db_service = DatabaseStorageService(db_config)
    files = db_service.get_calibration_files(candidate_id)
    
    if not files:
        raise ValueError(f"No calibration found for {candidate_id}")
    
    # Save to expected local paths
    for filename, content in files.items():
        path = f"results/interview_calibrations/{filename}"
        
        if filename.endswith('.json'):
            with open(path, 'w') as f:
                json.dump(content, f)
        elif filename.endswith('.csv'):
            with open(path, 'w') as f:
                f.write(content)
        elif filename.endswith('.npz'):
            # content is BytesIO object from database
            with open(path, 'wb') as f:
                f.write(content.getvalue())
    
    # Continue with existing analyzer workflow
    return analyze_with_calibration(candidate_id)

# Option 2: Via API (recommended for consistency)
def load_calibration_via_api(candidate_id):
    response = requests.get(
        f"{API_URL}/api/calibration/download/{candidate_id}",
        headers={"Authorization": f"Bearer {analyzer_token}"}
    )
    
    if response.status_code != 200:
        raise ValueError(f"Failed to load calibration: {response.text}")
    
    # Process and save files as shown above
    save_calibration_files(response.json())
    return analyze_with_calibration(candidate_id)
```

### Database Connection Configuration
```python
# Production database configuration
DB_CONFIG = {
    'host': os.environ.get('DB_HOST', 'localhost'),
    'port': int(os.environ.get('DB_PORT', 3306)),
    'user': os.environ.get('DB_USER'),
    'password': os.environ.get('DB_PASSWORD'),
    'database': os.environ.get('DB_NAME', 'calibration_db'),
    'pool_name': 'calibration_pool',
    'pool_size': 10,
    'pool_reset_session': True,
    'autocommit': True
}
```