"""
Screen information API endpoints
"""

from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime
import structlog

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from db.storage_service import DatabaseStorageService

router = APIRouter()
logger = structlog.get_logger()

# Pydantic models
class ScreenInfoRequest(BaseModel):
    candidate_id: str = Field(..., description="Unique candidate identifier")
    screen_width_px: int = Field(..., gt=0, description="Screen width in pixels")
    screen_height_px: int = Field(..., gt=0, description="Screen height in pixels")
    screen_width_mm: Optional[float] = Field(None, gt=0, description="Screen width in mm")
    screen_height_mm: Optional[float] = Field(None, gt=0, description="Screen height in mm")
    dpi: Optional[float] = Field(96.0, gt=0, description="Screen DPI")
    diagonal_inches: Optional[float] = Field(None, gt=0, description="Screen diagonal in inches")
    monitor_name: Optional[str] = Field("Unknown", description="Monitor name/model")
    camera_position: Optional[str] = Field("top-center", description="Camera position relative to screen")
    distance_cm: Optional[str] = Field("60", description="Estimated distance from screen")
    collection_method: Optional[str] = Field("automatic", description="How screen info was collected")
    
    @validator('camera_position')
    def validate_camera_position(cls, v):
        valid_positions = [
            "top-center", "top-left", "top-right",
            "bottom-center", "bottom-left", "bottom-right",
            "left-center", "right-center", "embedded"
        ]
        if v not in valid_positions:
            raise ValueError(f"Invalid camera position. Must be one of: {valid_positions}")
        return v

class ScreenInfoResponse(BaseModel):
    success: bool
    candidate_id: str
    timestamp: str
    message: Optional[str] = None

# Dependency
def get_storage_service() -> DatabaseStorageService:
    return DatabaseStorageService()

@router.post("/info", response_model=ScreenInfoResponse)
async def save_screen_info(
    request: ScreenInfoRequest,
    req: Request,
    storage: DatabaseStorageService = Depends(get_storage_service)
):
    """Save screen information for calibration"""
    try:
        # Prepare screen data
        screen_data = request.dict()
        screen_data['timestamp'] = datetime.utcnow().isoformat()
        
        # Calculate missing dimensions if possible
        if not screen_data.get('screen_width_mm') and screen_data.get('dpi'):
            screen_data['screen_width_mm'] = (
                screen_data['screen_width_px'] / screen_data['dpi'] * 25.4
            )
            screen_data['screen_height_mm'] = (
                screen_data['screen_height_px'] / screen_data['dpi'] * 25.4
            )
        
        # Save to database
        success = storage.save_screen_info(request.candidate_id, screen_data)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to save screen info")
        
        # Log audit event
        storage.log_audit_event(
            candidate_id=request.candidate_id,
            action="screen_info_saved",
            user_agent=req.headers.get("user-agent"),
            ip_address=req.client.host if req.client else None,
            details={
                "resolution": f"{screen_data['screen_width_px']}x{screen_data['screen_height_px']}",
                "dpi": screen_data.get('dpi')
            }
        )
        
        logger.info("Screen info saved", 
                   candidate_id=request.candidate_id,
                   resolution=f"{screen_data['screen_width_px']}x{screen_data['screen_height_px']}")
        
        return ScreenInfoResponse(
            success=True,
            candidate_id=request.candidate_id,
            timestamp=screen_data['timestamp'],
            message="Screen information saved successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to save screen info", 
                    candidate_id=request.candidate_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/info/{candidate_id}")
async def get_screen_info(
    candidate_id: str,
    storage: DatabaseStorageService = Depends(get_storage_service)
):
    """Get saved screen information for a candidate"""
    try:
        screen_info = storage.get_screen_info(candidate_id)
        
        if not screen_info:
            raise HTTPException(status_code=404, detail="Screen info not found")
        
        return screen_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get screen info", 
                    candidate_id=candidate_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/detect")
async def detect_screen_info(request: Request):
    """
    Endpoint for automatic screen detection.
    Note: This is primarily handled client-side using JavaScript APIs
    """
    try:
        # This endpoint can be used to validate screen detection from client
        data = await request.json()
        
        # Validate detected values
        validation_result = {
            "valid": True,
            "warnings": []
        }
        
        # Check screen dimensions
        width = data.get('screen_width_px', 0)
        height = data.get('screen_height_px', 0)
        
        if width < 800 or height < 600:
            validation_result["warnings"].append("Screen resolution seems too low")
        
        if width > 7680 or height > 4320:
            validation_result["warnings"].append("Screen resolution seems unusually high")
        
        # Check DPI
        dpi = data.get('dpi', 96)
        if dpi < 72 or dpi > 300:
            validation_result["warnings"].append(f"Unusual DPI value: {dpi}")
        
        # Calculate physical dimensions if not provided
        if not data.get('screen_width_mm'):
            data['screen_width_mm'] = width / dpi * 25.4
            data['screen_height_mm'] = height / dpi * 25.4
        
        # Add detection timestamp
        data['detection_timestamp'] = datetime.utcnow().isoformat()
        data['validation'] = validation_result
        
        logger.info("Screen detection validated", 
                   resolution=f"{width}x{height}",
                   dpi=dpi,
                   warnings=len(validation_result["warnings"]))
        
        return data
        
    except Exception as e:
        logger.error("Failed to process screen detection", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))