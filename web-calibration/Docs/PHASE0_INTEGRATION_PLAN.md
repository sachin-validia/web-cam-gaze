# Phase 0: Integration Planning - Web Calibration System

## Current State Analysis

### Existing Desktop System
- **Calibration Entry**: `scripts/interview/calibration.py`
- **Data Processing**: `scripts/interview/analyzer.py`
- **Gaze Model**: `src/plgaze/gaze_estimator.py`
- **Transform Logic**: `src/gaze_tracking/calibration.py` (HomTransform)

### Data Flow (Current)
```
Desktop App → Local Files → Analyzer
```

### Data Flow (Target)
```
React Web → Backend API → MySQL Database → External Systems → Analyzer
```

## Integration Architecture

### 1. Authentication & Session Management
**Status**: No existing auth system
**Plan**: 
- JWT-based authentication to be integrated with main platform
- Session IDs for calibration tracking
- Candidate ID mapping

### 2. Data Persistence
**MySQL Schema Required**:
- `calibration_sessions` - Track calibration attempts
- `screen_info` - Store screen configuration data
- `calibration_data` - Store CSV and transform matrix
- `calibration_frames` - Real-time frame processing

### 3. API Design
**Core Endpoints**:
- `/api/calibration/start` - Initialize session
- `/api/calibration/frame` - Process calibration frames
- `/api/calibration/complete` - Finalize and store
- `/api/calibration/verify/{candidate_id}` - Check existence
- `/api/calibration/download/{candidate_id}` - Retrieve files

### 4. File Format Compatibility
**Critical Files** (must match exactly):
1. `{candidate_id}_screen_info.json`
2. `{candidate_id}_calibration.csv`
3. `{candidate_id}_transform_matrix.npz`

## Manual Tasks Required

### Database Setup (YOU NEED TO DO THIS)
1. Create MySQL database named `calibration_db`
2. Create user with appropriate permissions
3. Run schema creation script (will be provided)
4. Configure DataGrip connection

### Environment Configuration
1. Set up environment variables:
   - `DB_HOST`
   - `DB_PORT`
   - `DB_USER`
   - `DB_PASSWORD`
   - `DB_NAME`

### Integration Points
1. **Video Recording Bot**: Needs to access calibration data via API
2. **Analyzer**: Must be able to retrieve calibration files from database
3. **Main Platform**: Authentication and webhook integration

## Next Steps
1. Complete database setup (manual)
2. Create database schema
3. Begin Phase 1: Backend API development