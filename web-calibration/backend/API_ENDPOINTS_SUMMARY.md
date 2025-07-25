# API Endpoints Summary

This document provides a comprehensive overview of all API endpoints in the Web Calibration API, with their request/response schemas.

## Base URL
- Local development: `http://0.0.0.0:8000`
- API documentation (Swagger): `http://0.0.0.0:8000/docs`
- OpenAPI schema: `http://0.0.0.0:8000/openapi.json`

## API Endpoints Overview

### 1. Session Management (`/api/calibration/session`)

#### **POST /api/calibration/session/create** ⭐
Creates a new calibration session for a candidate.

**Request Body:**
```json
{
  "candidate_id": "string",      // Required: Unique candidate identifier
  "interview_id": "string",      // Optional: Associated interview ID
  "metadata": {}                 // Optional: Additional metadata
}
```

**Response (200 OK):**
```json
{
  "session_id": "string",        // Generated UUID for the session
  "candidate_id": "string",      // Echo of the candidate ID
  "status": "in progress",       // Session status
  "created_at": "2024-01-20T10:30:00", // ISO timestamp
  "interview_id": "string",      // Optional
  "metadata": {}                 // Optional
}
```

**Possible Errors:**
- 422: Validation Error (missing required fields)
- 500: Database error

#### **GET /api/calibration/session/{session_id}**
Retrieves the status of a calibration session.

**Path Parameters:**
- `session_id`: string (required)

**Response (200 OK):**
```json
{
  "exists": true,
  "session_id": "string",
  "status": "in_progress",       // in_progress, completed, failed
  "created_at": "2024-01-20T10:30:00",
  "updated_at": "2024-01-20T10:35:00",
  "error_message": null          // Present if status is failed
}
```

### 2. Screen Information (`/api/screen`)

#### **POST /api/screen/info** ⭐
Saves screen information for calibration. Must be called before calibration starts.

**Request Body:**
```json
{
  "candidate_id": "string",      // Required
  "screen_width_px": 1920,       // Required: Screen width in pixels
  "screen_height_px": 1080,      // Required: Screen height in pixels
  "screen_width_mm": 510.0,      // Optional: Physical width in mm
  "screen_height_mm": 287.0,     // Optional: Physical height in mm
  "dpi": 96.0,                   // Optional: Screen DPI (default: 96.0)
  "diagonal_inches": 23.8,       // Optional: Screen diagonal in inches
  "monitor_name": "Dell U2419H", // Optional: Monitor name (default: "Unknown")
  "camera_position": "top-center", // Optional: Camera position (default: "top-center")
  "distance_cm": "60",           // Optional: Distance from screen (default: "60")
  "collection_method": "automatic" // Optional: How info was collected (default: "automatic")
}
```

**Valid camera_position values:**
- "top-center", "top-left", "top-right"
- "bottom-center", "bottom-left", "bottom-right"
- "left-center", "right-center", "embedded"

**Response (200 OK):**
```json
{
  "success": true,
  "candidate_id": "string",
  "timestamp": "2024-01-20T10:30:00",
  "message": "Screen information saved successfully"
}
```

**Possible Errors:**
- 422: Validation Error (invalid camera_position, negative dimensions)
- 500: Database error

#### **GET /api/screen/info/{candidate_id}**
Retrieves saved screen information for a candidate.

**Response (200 OK):**
Returns the saved screen information object.

**Response (404 Not Found):**
When no screen info exists for the candidate.

### 3. Calibration Process (`/api/calibration`)

#### **POST /api/calibration/start** ⭐
Initializes calibration for a session. Verifies prerequisites are met.

**Request Body:**
```json
{
  "session_id": "string",        // Required: From session/create
  "candidate_id": "string"       // Required: Must match session's candidate
}
```

**Response (200 OK):**
```json
{
  "session_id": "string",
  "candidate_id": "string",
  "status": "ready",
  "screen_info": { /* saved screen info */ },
  "calibration_config": {
    "target_display_time": 3000,  // ms per target
    "max_frames_per_target": 30,  // max frames to capture
    "targets": [
      {"index": 0, "position": {"x": 0.1, "y": 0.1}},  // Top-left
      {"index": 1, "position": {"x": 0.9, "y": 0.1}},  // Top-right
      {"index": 2, "position": {"x": 0.1, "y": 0.9}},  // Bottom-left
      {"index": 3, "position": {"x": 0.9, "y": 0.9}}   // Bottom-right
    ]
  }
}
```

**Possible Errors:**
- 404: Session not found
- 400: Candidate ID mismatch or screen info not saved
- 500: Server error

#### **POST /api/calibration/frame** ⭐
Processes a single calibration frame with gaze detection.

**Request Body:**
```json
{
  "session_id": "string",        // Required
  "candidate_id": "string",      // Required
  "frame_data": "base64...",     // Required: Base64 encoded image
  "frame_index": 0,              // Required: Frame number (0-based)
  "target_position": {           // Required: Target coordinates (0-1 normalized)
    "x": 0.1,
    "y": 0.1
  },
  "target_index": 0              // Required: Target index (0-3)
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "gaze_point": {"x": 0.12, "y": 0.11},  // Detected gaze position
  "confidence": 0.85,                      // Detection confidence
  "eye_centers": {
    "left": {"x": 0.3, "y": 0.4},
    "right": {"x": 0.7, "y": 0.4}
  },
  "frame_index": 0,
  "target_index": 0,
  "timestamp": "2024-01-20T10:30:00"
}
```

**Response (when face detection fails):**
```json
{
  "success": false,
  "error": "No face detected",
  "frame_index": 0
}
```

#### **POST /api/calibration/complete** ⭐
Completes calibration, generates transformation matrix and output files.

**Request Body:**
```json
{
  "session_id": "string",        // Required
  "candidate_id": "string"       // Required
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "session_id": "string",
  "candidate_id": "string",
  "calibration_stats": {
    "frames_processed": 120,
    "average_error": 0.05,
    "calibration_quality": "good"
  },
  "validation_metrics": {
    "face_detection_rate": 0.95,
    "coverage": [true, true, true, true]  // All 4 targets covered
  },
  "file_checksums": {
    "screen_info.json": "sha256...",
    "calibration_data.csv": "sha256...",
    "transform_matrix.npz": "sha256..."
  },
  "message": "Calibration completed successfully"
}
```

**Possible Errors:**
- 400: No calibration frames found or invalid calibration data
- 500: Failed to compute transformation or file generation error

### 4. Additional Endpoints

#### **GET /api/calibration/verify/{candidate_id}**
Checks if calibration exists for a candidate.

**Response:**
```json
{
  "exists": true,
  "candidate_id": "string",
  "created_at": "2024-01-20T10:30:00",
  "has_screen_info": true,
  "has_calibration_data": true
}
```

#### **GET /api/calibration/download/{candidate_id}**
Downloads calibration files (JSON, CSV, NPZ).

#### **GET /api/calibration/diagnostics/{session_id}**
Returns detailed diagnostics for debugging calibration issues.

## Common Error Responses

### 422 Unprocessable Entity
Returned when request validation fails:
```json
{
  "detail": [
    {
      "loc": ["body", "field_name"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

### 500 Internal Server Error
Returned for database or processing errors:
```json
{
  "detail": "Error message describing the issue"
}
```

## Important Notes

1. **Order of Operations:**
   - Create session (`/api/calibration/session/create`)
   - Save screen info (`/api/screen/info`)
   - Start calibration (`/api/calibration/start`)
   - Process frames (`/api/calibration/frame`)
   - Complete calibration (`/api/calibration/complete`)

2. **Required Fields:**
   - All endpoints marked with ⭐ are critical for the calibration flow
   - Fields marked as "Required" must be present in requests
   - Optional fields will use defaults if not provided

3. **Data Types:**
   - `target_position`: Object with `x` and `y` as numbers (0-1 normalized)
   - `frame_data`: Base64 encoded image string
   - Timestamps: ISO 8601 format strings
   - All IDs: UUID strings

4. **Validation Rules:**
   - Screen dimensions must be positive integers
   - DPI must be positive (typically 72-300)
   - Target indices must be 0-3
   - Camera position must be from the allowed list