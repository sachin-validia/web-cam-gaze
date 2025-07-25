# Calibration Monitoring Guide

This guide helps you monitor the web calibration process for candidate ID: `test_candidate_002`

## Available Monitoring Tools

### 1. Calibration Dashboard (Recommended)
The most comprehensive monitoring tool with real-time metrics and progress tracking.

```bash
# Run in terminal 1:
python calibration_dashboard.py test_candidate_002
```

Features:
- Real-time frame counting
- Success rate and confidence metrics
- Target coverage visualization
- Progress bar
- Recent events log
- Database error tracking

### 2. Database Monitor
Focused monitoring of database activity and frame insertions.

```bash
# Run in terminal 2:
python monitor_calibration.py test_candidate_002
```

Features:
- Session tracking
- Frame-by-frame insertion monitoring
- Target coverage analysis
- Database error detection

### 3. Backend Log Monitor
Monitors backend console output for errors and events.

```bash
# Run in terminal 3:
python monitor_backend_logs.py
```

Features:
- Real-time log parsing
- Error highlighting
- API call tracking
- Frame save confirmations

### 4. Troubleshooting Tool
Run this if you encounter issues:

```bash
python troubleshoot_calibration.py test_candidate_002
```

Features:
- Database connectivity check
- Table structure verification
- Foreign key constraint validation
- Recent error analysis
- Automated fix suggestions

## Quick Start Monitoring Setup

1. **Before Starting Calibration:**
   ```bash
   # Run troubleshooting to ensure system is ready
   python troubleshoot_calibration.py test_candidate_002
   ```

2. **Start Primary Monitor:**
   ```bash
   # In a new terminal window
   python calibration_dashboard.py test_candidate_002
   ```

3. **Start Backend (if not already running):**
   ```bash
   # In another terminal
   python app.py
   ```

4. **Begin Calibration:**
   - Open browser to http://localhost:5173
   - Enter candidate ID: `test_candidate_002`
   - Follow calibration process

## What to Watch For

### ✅ Good Signs:
- Frames incrementing steadily
- Success rate > 80%
- All 4 targets getting coverage
- No database errors
- Confidence scores > 0.7

### ❌ Warning Signs:
- Frames not incrementing
- Database errors appearing
- Success rate < 50%
- Missing target coverage
- Session status showing "failed"

## Common Issues and Fixes

1. **No frames being saved:**
   - Check if session was created successfully
   - Verify screen info was saved first
   - Look for database connection errors

2. **Low success rate:**
   - Check camera permissions
   - Ensure good lighting
   - Verify GazeService is initialized

3. **Database errors:**
   - Run troubleshooting tool
   - Check MySQL is running
   - Verify table structure

## Terminal Layout Suggestion

For best monitoring experience, arrange terminals as follows:

```
┌─────────────────────────┬─────────────────────────┐
│                         │                         │
│  Calibration Dashboard  │   Backend Server        │
│  (calibration_dashboard)│   (python app.py)       │
│                         │                         │
├─────────────────────────┼─────────────────────────┤
│                         │                         │
│  Database Monitor       │   Browser               │
│  (monitor_calibration)  │   (localhost:5173)      │
│                         │                         │
└─────────────────────────┴─────────────────────────┘
```

## Export Monitoring Data

To save monitoring results:

```bash
# Redirect output to file
python calibration_dashboard.py test_candidate_002 > calibration_log.txt 2>&1
```

## Keyboard Shortcuts

- `Ctrl+C`: Stop monitoring and show summary
- `Ctrl+Z`: Pause monitoring (use `fg` to resume)

## Support

If you encounter persistent issues:
1. Run the troubleshooting tool
2. Check backend logs for detailed errors
3. Verify all dependencies are installed
4. Ensure MySQL service is running