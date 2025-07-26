# Calibration System Debugging Guide

## Data Flow Overview

### 1. Frontend to Backend Flow

```
PreCheckPage.tsx
    ↓
    POST /api/calibration/session/create
    Request: { candidate_id, session_type }
    Response: { session_id, candidate_id, created_at, status }
    ↓
CalibrationPage.tsx
    ↓
    Step 1: ScreenSetup.tsx
        ↓
        POST /api/screen/info
        Request: { candidate_id, screen_width_px, screen_height_px, dpi }
        ↓
    Step 2: CameraCheck.tsx
        ↓
        (No API calls, just camera permission)
        ↓
    Step 3: CalibrationTargets.tsx
        ↓
        POST /api/calibration/start
        Request: { session_id, candidate_id }
        ↓
        POST /api/calibration/frame (multiple times)
        Request: { session_id, candidate_id, frame_data, frame_index, target_position, target_index }
        ↓
        POST /api/calibration/complete
        Request: { session_id, candidate_id }
        Response: { success, message, files_generated, calibration_quality }
```

### 2. Backend Processing Flow

```
calibration.py endpoints
    ↓
    storage_service.py (Database operations)
    ↓
    MySQL Database Tables:
    - calibration_sessions
    - screen_info  
    - calibration_frames
    - calibration_data
    - calibration_audit_log
```

## Identified Issues

### 1. 400 Error on /api/calibration/complete

The error occurs when:
- No calibration frames found in database
- Screen info not found for candidate
- Validation of calibration data fails

### 2. Fullscreen Permission Error

Browser blocks automatic fullscreen without user gesture. Need to add explicit permission request.

### 3. Database Initialization

The GazeService might not be initializing properly, causing mock data to be used.

## Debugging Steps

### Step 1: Check Backend Logs

```bash
# Check if backend is running
ps aux | grep uvicorn

# Check backend logs for errors
# Look for:
# - "Initializing GazeService in calibration.py..."
# - "Failed to initialize GazeService"
# - Database connection errors
```

### Step 2: Verify Database State

```sql
-- Check if tables exist
SHOW TABLES;

-- Check recent sessions
SELECT * FROM calibration_sessions ORDER BY created_at DESC LIMIT 5;

-- Check if frames are being saved
SELECT session_id, COUNT(*) as frame_count 
FROM calibration_frames 
GROUP BY session_id 
ORDER BY session_id DESC;

-- Check screen info
SELECT * FROM screen_info ORDER BY created_at DESC LIMIT 5;
```

### Step 3: Test API Endpoints Manually

```bash
# 1. Create session
curl -X POST http://localhost:8000/api/calibration/session/create \
     -H 'Content-Type: application/json' \
     -d '{"candidate_id": "test_debug_001"}'

# Save the session_id from response

# 2. Save screen info
curl -X POST http://localhost:8000/api/screen/info \
     -H 'Content-Type: application/json' \
     -d '{"candidate_id": "test_debug_001", "screen_width_px": 1920, "screen_height_px": 1080}'

# 3. Start calibration
curl -X POST http://localhost:8000/api/calibration/start \
     -H 'Content-Type: application/json' \
     -d '{"session_id": "<SESSION_ID>", "candidate_id": "test_debug_001"}'

# 4. Send a test frame
curl -X POST http://localhost:8000/api/calibration/frame \
     -H 'Content-Type: application/json' \
     -d '{
       "session_id": "<SESSION_ID>",
       "candidate_id": "test_debug_001",
       "frame_data": "test_base64_data",
       "frame_index": 0,
       "target_position": {"x": 0.1, "y": 0.1},
       "target_index": 0
     }'

# 5. Complete calibration
curl -X POST http://localhost:8000/api/calibration/complete \
     -H 'Content-Type: application/json' \
     -d '{"session_id": "<SESSION_ID>", "candidate_id": "test_debug_001"}'
```

### Step 4: Browser DevTools Debugging

1. Open Chrome DevTools (F12)
2. Go to Network tab
3. Clear network log
4. Go through calibration process
5. Look for failed requests (red entries)
6. Click on failed request to see:
   - Request headers
   - Request payload
   - Response data

### Step 5: Add Debug Logging

Add console.log statements in frontend:

```typescript
// In CalibrationTargets.tsx
console.log('Sending frame:', {
  session_id: sessionId,
  frame_index: frameData.frameIndex,
  target_index: frameData.targetIndex
});

// In calibration.api.ts
console.log('API Response:', response);
```

## Common Issues and Solutions

### Issue 1: Frames not saving to database

**Possible causes:**
- Session ID mismatch
- Database connection issues
- Transaction not committing

**Solution:**
Check storage_service.py save_calibration_frame method

### Issue 2: GazeService not initialized

**Possible causes:**
- Missing dependencies
- Model files not found
- CUDA/GPU issues

**Solution:**
Check backend startup logs for initialization errors

### Issue 3: Transform matrix computation failing

**Possible causes:**
- Insufficient calibration points
- Invalid gaze data
- Mathematical computation errors

**Solution:**
Check calibration_service.py compute_transformation_matrix

## Next Steps

1. Add request/response logging middleware
2. Create health check endpoint
3. Add database connection pool monitoring
4. Implement retry logic for failed frames
5. Add progress tracking in UI