"""
Debug endpoints for troubleshooting calibration issues
"""

from fastapi import APIRouter, Depends
from typing import Dict, Any, Optional
import structlog

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from db.storage_service import DatabaseStorageService
from db.database import get_db

router = APIRouter()
logger = structlog.get_logger()

def get_storage_service() -> DatabaseStorageService:
    return DatabaseStorageService()

@router.get("/session/{session_id}")
async def debug_session(
    session_id: str,
    storage: DatabaseStorageService = Depends(get_storage_service)
):
    """Get complete debug information for a session"""
    try:
        db = get_db()
        
        # Get session info
        session_query = """
        SELECT * FROM calibration_sessions WHERE id = %s
        """
        session = db.execute_query(session_query, (session_id,), fetch_one=True)
        
        if not session:
            return {"error": "Session not found"}
        
        candidate_id = session['candidate_id']
        
        # Get screen info
        screen_info = storage.get_screen_info(candidate_id)
        
        # Get frame count
        frame_count_query = """
        SELECT COUNT(*) as count FROM calibration_frames WHERE session_id = %s
        """
        frame_count = db.execute_query(frame_count_query, (session_id,), fetch_one=True)
        
        # Get frame distribution
        frame_dist_query = """
        SELECT 
            CONCAT(JSON_EXTRACT(target_position, '$.x'), ',', JSON_EXTRACT(target_position, '$.y')) as target,
            COUNT(*) as count
        FROM calibration_frames 
        WHERE session_id = %s
        GROUP BY target
        """
        frame_distribution = db.execute_query(frame_dist_query, (session_id,))
        
        # Check calibration data
        cal_exists = storage.check_calibration_exists(candidate_id)
        
        # Get recent frames sample
        recent_frames_query = """
        SELECT frame_index, created_at, 
               JSON_EXTRACT(frame_data, '$.success') as success,
               target_position
        FROM calibration_frames 
        WHERE session_id = %s
        ORDER BY frame_index DESC
        LIMIT 5
        """
        recent_frames = db.execute_query(recent_frames_query, (session_id,))
        
        return {
            "session": {
                "id": session['id'],
                "candidate_id": session['candidate_id'],
                "status": session['status'],
                "created_at": str(session['created_at']),
                "error_message": session['error_message']
            },
            "screen_info_exists": screen_info is not None,
            "screen_info": screen_info,
            "frames": {
                "total_count": frame_count['count'] if frame_count else 0,
                "distribution": [{"target": f['target'], "count": f['count']} for f in frame_distribution],
                "recent_samples": [
                    {
                        "frame_index": f['frame_index'],
                        "created_at": str(f['created_at']),
                        "success": bool(f['success']),
                        "target_position": f['target_position']
                    } for f in recent_frames
                ]
            },
            "calibration_data_exists": cal_exists,
            "diagnostics": {
                "ready_for_completion": (
                    screen_info is not None and 
                    frame_count and frame_count['count'] > 0
                ),
                "missing_requirements": []
            }
        }
        
    except Exception as e:
        logger.error("Debug endpoint error", error=str(e))
        return {"error": str(e)}

@router.get("/candidate/{candidate_id}/history")
async def debug_candidate_history(
    candidate_id: str,
    storage: DatabaseStorageService = Depends(get_storage_service)
):
    """Get complete history for a candidate"""
    try:
        db = get_db()
        
        # Get all sessions
        sessions_query = """
        SELECT id, status, created_at, error_message
        FROM calibration_sessions 
        WHERE candidate_id = %s
        ORDER BY created_at DESC
        """
        sessions = db.execute_query(sessions_query, (candidate_id,))
        
        # Get audit logs
        audit_query = """
        SELECT action, created_at, details
        FROM calibration_audit_log
        WHERE candidate_id = %s
        ORDER BY created_at DESC
        LIMIT 20
        """
        audit_logs = db.execute_query(audit_query, (candidate_id,))
        
        return {
            "candidate_id": candidate_id,
            "sessions": [
                {
                    "id": s['id'],
                    "status": s['status'],
                    "created_at": str(s['created_at']),
                    "error_message": s['error_message']
                } for s in sessions
            ],
            "audit_logs": [
                {
                    "action": a['action'],
                    "created_at": str(a['created_at']),
                    "details": a['details']
                } for a in audit_logs
            ],
            "has_calibration_data": storage.check_calibration_exists(candidate_id),
            "has_screen_info": storage.get_screen_info(candidate_id) is not None
        }
        
    except Exception as e:
        logger.error("Debug endpoint error", error=str(e))
        return {"error": str(e)}

@router.get("/health")
async def debug_health():
    """Check system health"""
    try:
        db = get_db()
        storage = DatabaseStorageService()
        
        # Test database connection
        db_test = db.execute_query("SELECT 1 as test", fetch_one=True)
        db_healthy = db_test is not None
        
        # Check GazeService
        from models.gaze_service import GazeService
        try:
            gaze_service = GazeService()
            gaze_healthy = True
        except:
            gaze_healthy = False
        
        # Get table counts
        tables = ['calibration_sessions', 'screen_info', 'calibration_frames', 
                 'calibration_data', 'calibration_audit_log']
        table_counts = {}
        
        for table in tables:
            try:
                result = db.execute_query(f"SELECT COUNT(*) as count FROM {table}", fetch_one=True)
                table_counts[table] = result['count'] if result else 0
            except:
                table_counts[table] = -1
        
        return {
            "status": "healthy" if db_healthy else "unhealthy",
            "components": {
                "database": db_healthy,
                "gaze_service": gaze_healthy,
                "storage_service": True
            },
            "table_counts": table_counts
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }