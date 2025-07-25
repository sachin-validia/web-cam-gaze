"""
Session management API endpoints
"""

from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
import uuid
import structlog

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from db.storage_service import DatabaseStorageService
from utils.config import settings

router = APIRouter()
logger = structlog.get_logger()

# Pydantic models for request/response
class CreateSessionRequest(BaseModel):
    candidate_id: str = Field(..., description="Unique candidate identifier")
    interview_id: Optional[str] = Field(None, description="Associated interview ID")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")

class SessionResponse(BaseModel):
    session_id: str
    candidate_id: str
    status: str
    created_at: str
    interview_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class SessionStatusResponse(BaseModel):
    exists: bool
    session_id: Optional[str] = None
    status: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    error_message: Optional[str] = None

# Dependency to get storage service
def get_storage_service() -> DatabaseStorageService:
    return DatabaseStorageService()

@router.post("/create", response_model=SessionResponse)
async def create_calibration_session(
    request: CreateSessionRequest,
    req: Request,
    storage: DatabaseStorageService = Depends(get_storage_service)
):
    """Create a new calibration session"""
    try:
        # Generate unique session ID
        session_id = str(uuid.uuid4())
        
        # Create session in database
        success = storage.create_calibration_session(
            session_id=session_id,
            candidate_id=request.candidate_id,
            interview_id=request.interview_id
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to create session")
        
        # Log audit event
        storage.log_audit_event(
            candidate_id=request.candidate_id,
            action="session_created",
            user_agent=req.headers.get("user-agent"),
            ip_address=req.client.host if req.client else None,
            details={
                "session_id": session_id,
                "interview_id": request.interview_id
            }
        )
        
        logger.info("Calibration session created", 
                   session_id=session_id,
                   candidate_id=request.candidate_id)
        
        return SessionResponse(
            session_id=session_id,
            candidate_id=request.candidate_id,
            status="in_progress",
            created_at=datetime.utcnow().isoformat(),
            interview_id=request.interview_id,
            metadata=request.metadata
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to create calibration session", error=str(e))
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/{session_id}", response_model=SessionStatusResponse)
async def get_session_status(
    session_id: str,
    storage: DatabaseStorageService = Depends(get_storage_service)
):
    """Get calibration session status"""
    try:
        session_info = storage.get_session_info(session_id)
        
        if not session_info:
            return SessionStatusResponse(exists=False)
        
        return SessionStatusResponse(
            exists=True,
            session_id=session_info['id'],
            status=session_info['status'],
            created_at=session_info['created_at'],
            updated_at=session_info['updated_at'],
            error_message=session_info.get('error_message')
        )
        
    except Exception as e:
        logger.error("Failed to get session status", 
                    session_id=session_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{session_id}/resume")
async def resume_calibration_session(
    session_id: str,
    storage: DatabaseStorageService = Depends(get_storage_service)
):
    """Resume an interrupted calibration session"""
    try:
        # Check if session exists
        session_info = storage.get_session_info(session_id)
        
        if not session_info:
            raise HTTPException(status_code=404, detail="Session not found")
        
        if session_info['status'] == 'completed':
            raise HTTPException(status_code=400, detail="Session already completed")
        
        # Update session status to in_progress
        success = storage.update_session_status(session_id, "in_progress")
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to resume session")
        
        # Get calibration frames if any
        frames = storage.get_calibration_frames(session_id)
        
        logger.info("Calibration session resumed", 
                   session_id=session_id,
                   existing_frames=len(frames))
        
        return {
            "session_id": session_id,
            "status": "resumed",
            "existing_frames": len(frames),
            "candidate_id": session_info['candidate_id']
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to resume session", 
                    session_id=session_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{session_id}/link")
async def link_session_to_interview(
    session_id: str,
    interview_id: str,
    storage: DatabaseStorageService = Depends(get_storage_service)
):
    """Link calibration session to an interview"""
    try:
        # Check if session exists
        session_info = storage.get_session_info(session_id)
        
        if not session_info:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Update session with interview ID
        query = """
        UPDATE calibration_sessions 
        SET interview_id = %s, updated_at = CURRENT_TIMESTAMP
        WHERE id = %s
        """
        rows_affected = storage.db.execute_update(query, (interview_id, session_id))
        
        if rows_affected == 0:
            raise HTTPException(status_code=500, detail="Failed to link session")
        
        logger.info("Session linked to interview", 
                   session_id=session_id,
                   interview_id=interview_id)
        
        return {
            "session_id": session_id,
            "interview_id": interview_id,
            "status": "linked"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to link session", 
                    session_id=session_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))