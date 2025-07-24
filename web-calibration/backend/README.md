# Web Calibration Backend API

This is the backend API for the web-based gaze calibration system. It provides REST endpoints for managing calibration sessions, processing gaze data, and storing calibration results.

## Setup

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your database credentials
   python -c "import secrets; print(secrets.token_urlsafe(32))" # for jwt security key
   ```

3. **Ensure database is set up**:
   - The database schema should already be created using `db/schema.sql`
   - Update the `.env` file with your database credentials

4. **Run the server**:
   ```bash
   python app.py
   ```

   Or with uvicorn directly:
   ```bash
   uvicorn app:app --reload --host 0.0.0.0 --port 8000
   ```

## API Documentation

Once the server is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API Endpoints

### Session Management
- `POST /api/calibration/session/create` - Create new calibration session
- `GET /api/calibration/session/{session_id}` - Get session status
- `POST /api/calibration/session/{session_id}/resume` - Resume interrupted session
- `POST /api/calibration/session/{session_id}/link` - Link session to interview

### Screen Information
- `POST /api/screen/info` - Save screen configuration
- `GET /api/screen/info/{candidate_id}` - Get saved screen info
- `POST /api/screen/detect` - Validate detected screen info

### Calibration
- `POST /api/calibration/start` - Initialize calibration
- `POST /api/calibration/frame` - Process single calibration frame
- `POST /api/calibration/frames/batch` - Process multiple frames
- `POST /api/calibration/complete` - Complete calibration and generate files
- `GET /api/calibration/verify/{candidate_id}` - Verify calibration exists
- `GET /api/calibration/download/{candidate_id}` - Download calibration files
- `GET /api/calibration/diagnostics/{session_id}` - Get calibration diagnostics

## Architecture

```
backend/
├── api/              # API endpoint definitions
├── models/           # Core services (gaze, calibration)
├── db/               # Database connectivity and storage
├── utils/            # Utilities (config, file generation)
└── app.py           # Main FastAPI application
```

## Integration

The backend integrates with:
- Existing PLGaze model for gaze estimation
- HomTransform for calibration transformation
- MySQL database for persistent storage
- Future React frontend for web interface