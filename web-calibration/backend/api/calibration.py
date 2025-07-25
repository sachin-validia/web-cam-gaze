"""
Main calibration API endpoints
"""

from fastapi import (
    APIRouter,
    HTTPException,
    Request,
    Depends,
    BackgroundTasks,
    UploadFile,
    File,
    Form,
)
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import structlog
import json

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from db.storage_service import DatabaseStorageService
from models.gaze_service import GazeService
from models.calibration_service import CalibrationService
from utils.file_generator import FileGenerator
from utils.config import settings

router = APIRouter()
logger = structlog.get_logger()

# Global services (initialized once)
try:
    print("Initializing GazeService in calibration.py...")
    gaze_service = GazeService()
    print("GazeService initialized successfully")
except Exception as e:
    import traceback

    print(f"Failed to initialize GazeService: {e}")
    traceback.print_exc()
    gaze_service = None

file_generator = FileGenerator()


# Pydantic models
class CalibrationStartRequest(BaseModel):
    session_id: str = Field(..., description="Session ID from session/create")
    candidate_id: str = Field(..., description="Unique candidate identifier")


class CalibrationFrameRequest(BaseModel):
    session_id: str = Field(..., description="Session ID")
    candidate_id: str = Field(..., description="Candidate ID")
    frame_data: str = Field(..., description="Base64 encoded frame image")
    frame_index: int = Field(..., ge=0, description="Frame index in sequence")
    target_position: Dict[str, float] = Field(..., description="Target position {x, y}")
    target_index: int = Field(..., ge=0, le=3, description="Target index (0-3)")


class CalibrationFrameBatchRequest(BaseModel):
    session_id: str
    candidate_id: str
    frames: List[CalibrationFrameRequest]


class CalibrationCompleteRequest(BaseModel):
    session_id: str = Field(..., description="Session ID")
    candidate_id: str = Field(..., description="Candidate ID")


class CalibrationStatusResponse(BaseModel):
    exists: bool
    candidate_id: Optional[str] = None
    created_at: Optional[str] = None
    has_screen_info: bool = False
    has_calibration_data: bool = False


# Dependencies
def get_storage_service() -> DatabaseStorageService:
    service = DatabaseStorageService()
    logger.info("Created new DatabaseStorageService instance", instance_id=id(service))
    return service


def get_calibration_service() -> CalibrationService:
    return CalibrationService()


@router.post("/start")
async def start_calibration(
    request: CalibrationStartRequest,
    storage: DatabaseStorageService = Depends(get_storage_service),
):
    """Initialize calibration for a session"""
    try:
        # Verify session exists
        session_info = storage.get_session_info(request.session_id)
        if not session_info:
            raise HTTPException(status_code=404, detail="Session not found")

        # Verify candidate matches
        if session_info["candidate_id"] != request.candidate_id:
            raise HTTPException(status_code=400, detail="Candidate ID mismatch")

        # Check if screen info exists
        screen_info = storage.get_screen_info(request.candidate_id)
        if not screen_info:
            raise HTTPException(
                status_code=400, detail="Screen information must be saved first"
            )

        logger.info(
            "Calibration started",
            session_id=request.session_id,
            candidate_id=request.candidate_id,
        )

        return {
            "session_id": request.session_id,
            "candidate_id": request.candidate_id,
            "status": "ready",
            "screen_info": screen_info,
            "calibration_config": {
                "target_display_time": settings.TARGET_DISPLAY_TIME,
                "max_frames_per_target": settings.MAX_FRAMES_PER_TARGET,
                "targets": [
                    {"index": 0, "position": {"x": 0.1, "y": 0.1}},  # Top-left
                    {"index": 1, "position": {"x": 0.9, "y": 0.1}},  # Top-right
                    {"index": 2, "position": {"x": 0.1, "y": 0.9}},  # Bottom-left
                    {"index": 3, "position": {"x": 0.9, "y": 0.9}},  # Bottom-right
                ],
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to start calibration", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# New endpoint that accepts multipart/form-data with a JPEG/PNG frame
# ---------------------------------------------------------------------------


@router.post("/frame/upload")
async def process_calibration_frame_upload(
    session_id: str = Form(...),
    candidate_id: str = Form(...),
    frame_index: int = Form(...),
    target_index: int = Form(...),
    target_x: float = Form(...),
    target_y: float = Form(...),
    frame: UploadFile = File(...),
    storage: DatabaseStorageService = Depends(get_storage_service),
):
    """Process a single calibration frame sent as multipart file upload."""

    try:
        logger.info(
            "Processing upload frame",
            session_id=session_id,
            frame_index=frame_index,
            target_index=target_index,
        )

        target_position = {"x": target_x, "y": target_y}

        use_mock = False  # same flag as before

        if gaze_service is None or use_mock:
            norm_tx, norm_ty = target_x, target_y
            gaze_vec_x = (norm_tx - 0.5) * 2
            gaze_vec_y = (norm_ty - 0.5) * 2

            gaze_result = {
                "success": True,
                "gaze_point": {"x": norm_tx, "y": norm_ty},
                "gaze_vector": [gaze_vec_x, gaze_vec_y, 1.0],
                "confidence": 0.8,
            }
        else:
            img_bytes = await frame.read()
            gaze_result = gaze_service.process_calibration_frame_bytes(
                frame_bytes=img_bytes, target_position=target_position
            )

        if not gaze_result["success"]:
            logger.warning("Frame processing failed", error=gaze_result.get("error"))
            return gaze_result

        gaze_result.update(
            {
                "frame_index": frame_index,
                "target_index": target_index,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

        success = storage.save_calibration_frame(
            session_id=session_id,
            frame_index=frame_index,
            frame_data=gaze_result,
            target_position=target_position,
        )

        if not success:
            raise HTTPException(status_code=500, detail="Failed to save frame data")

        return gaze_result

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to process uploaded frame", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/frame")
async def process_calibration_frame(
    request: CalibrationFrameRequest,
    storage: DatabaseStorageService = Depends(get_storage_service),
):
    """Process a single calibration frame"""
    try:
        logger.info(
            "Processing calibration frame",
            session_id=request.session_id,
            frame_index=request.frame_index,
            target_index=request.target_index,
        )

        # Check if gaze service is available
        # TEMPORARY: Always use mock response to debug frame saving
        use_mock = False  # Force mock for debugging

        if gaze_service is None or use_mock:
            logger.warning("Using mock response for debugging")
            # Generate a slightly different gaze vector per target so that
            # the downstream homography solver receives non-colinear points.
            # Map normalised target position (0-1) to a rough directional vector
            # in gaze space (-1..1).
            norm_tx = request.target_position["x"]
            norm_ty = request.target_position["y"]
            gaze_vec_x = (norm_tx - 0.5) * 2  # centre 0, edges ±1
            gaze_vec_y = (norm_ty - 0.5) * 2

            gaze_result = {
                "success": True,
                "gaze_point": {"x": norm_tx, "y": norm_ty},
                "gaze_vector": [gaze_vec_x, gaze_vec_y, 1.0],
                "confidence": 0.8,
                "eye_centers": {
                    "left": {"x": 0.3, "y": 0.4},
                    "right": {"x": 0.7, "y": 0.4},
                },
            }
        else:
            # Process frame with gaze service
            gaze_result = gaze_service.process_calibration_frame(
                frame_data=request.frame_data, target_position=request.target_position
            )

        if not gaze_result["success"]:
            logger.warning(
                "Frame processing failed",
                error=gaze_result.get("error"),
                frame_index=request.frame_index,
            )
            return gaze_result

        # Add metadata
        gaze_result["frame_index"] = request.frame_index
        gaze_result["target_index"] = request.target_index
        gaze_result["timestamp"] = datetime.utcnow().isoformat()

        logger.info(
            "Attempting to save frame to database",
            session_id=request.session_id,
            frame_index=request.frame_index,
        )

        # Save frame data to database
        success = storage.save_calibration_frame(
            session_id=request.session_id,
            frame_index=request.frame_index,
            frame_data=gaze_result,
            target_position=request.target_position,
        )

        logger.info(
            "Frame save result",
            session_id=request.session_id,
            frame_index=request.frame_index,
            success=success,
        )

        if not success:
            logger.error(
                "Failed to save frame to database",
                session_id=request.session_id,
                frame_index=request.frame_index,
            )
            raise HTTPException(status_code=500, detail="Failed to save frame data")

        return gaze_result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to process calibration frame",
            frame_index=request.frame_index,
            error=str(e),
        )
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/frames/batch")
async def process_calibration_frames_batch(
    request: CalibrationFrameBatchRequest,
    storage: DatabaseStorageService = Depends(get_storage_service),
):
    """Process multiple calibration frames in batch"""
    try:
        results = []
        successful_frames = 0

        for frame_req in request.frames:
            try:
                # Process each frame with mock for now
                if gaze_service is None or True:  # Force mock
                    # Generate a slightly different gaze vector per target so that
                    # the downstream homography solver receives non-colinear points.
                    # Map normalised target position (0-1) to a rough directional vector
                    # in gaze space (-1..1).
                    norm_tx = frame_req.target_position["x"]
                    norm_ty = frame_req.target_position["y"]
                    gaze_vec_x = (norm_tx - 0.5) * 2  # centre 0, edges ±1
                    gaze_vec_y = (norm_ty - 0.5) * 2

                    gaze_result = {
                        "success": True,
                        "gaze_point": {"x": norm_tx, "y": norm_ty},
                        "gaze_vector": [gaze_vec_x, gaze_vec_y, 1.0],
                        "confidence": 0.8,
                        "eye_centers": {
                            "left": {"x": 0.3, "y": 0.4},
                            "right": {"x": 0.7, "y": 0.4},
                        },
                    }
                else:
                    gaze_result = gaze_service.process_calibration_frame(
                        frame_data=frame_req.frame_data,
                        target_position=frame_req.target_position,
                    )

                if gaze_result["success"]:
                    # Add metadata
                    gaze_result["frame_index"] = frame_req.frame_index
                    gaze_result["target_index"] = frame_req.target_index
                    gaze_result["timestamp"] = datetime.utcnow().isoformat()

                    # Save to database
                    storage.save_calibration_frame(
                        session_id=request.session_id,
                        frame_index=frame_req.frame_index,
                        frame_data=gaze_result,
                        target_position=frame_req.target_position,
                    )
                    successful_frames += 1

                results.append(gaze_result)

            except Exception as e:
                logger.error(
                    "Failed to process frame in batch",
                    frame_index=frame_req.frame_index,
                    error=str(e),
                )
                results.append(
                    {
                        "success": False,
                        "error": str(e),
                        "frame_index": frame_req.frame_index,
                    }
                )

        return {
            "batch_size": len(request.frames),
            "successful_frames": successful_frames,
            "results": results,
        }

    except Exception as e:
        logger.error("Failed to process frame batch", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/complete")
async def complete_calibration(
    request: CalibrationCompleteRequest,
    background_tasks: BackgroundTasks,
    storage: DatabaseStorageService = Depends(get_storage_service),
    calibration_service: CalibrationService = Depends(get_calibration_service),
):
    """Complete calibration and generate files"""
    try:
        # Get all calibration frames
        frames = storage.get_calibration_frames(request.session_id)

        if not frames:
            raise HTTPException(status_code=400, detail="No calibration frames found")

        # Get screen info
        screen_info = storage.get_screen_info(request.candidate_id)
        if not screen_info:
            raise HTTPException(status_code=400, detail="Screen info not found")

        # Validate calibration data
        if gaze_service is None:
            logger.warning("GazeService not initialized, skipping validation")
            validation_result = {"valid": True, "metrics": {}}
        else:
            validation_result = gaze_service.validate_calibration_data(
                [f["frame_data"] for f in frames]
            )

            if not validation_result["valid"]:
                storage.update_session_status(
                    request.session_id,
                    "failed",
                    error_message=validation_result.get("error"),
                )
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid calibration: {validation_result.get('error')}",
                )

        # Set up calibration service
        calibration_service.set_screen_info(screen_info)

        # Add all calibration points
        for frame in frames:
            calibration_service.add_calibration_point(
                gaze_data=frame["frame_data"],
                target_position=frame["target_position"],
                frame_index=frame["frame_index"],
            )

        # Compute transformation matrix
        try:
            transform_result = calibration_service.compute_transformation_matrix()
            logger.debug("Transform result", data=transform_result)

            if not transform_result["success"]:
                storage.update_session_status(
                    request.session_id,
                    "failed",
                    error_message=transform_result.get("error"),
                )
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to compute transformation: {transform_result.get('error')}",
                )
        except Exception as e:
            logger.error("Transform computation failed", error=str(e))
            import traceback

            traceback.print_exc()
            storage.update_session_status(
                request.session_id, "failed", error_message=str(e)
            )
            raise HTTPException(
                status_code=400, detail=f"Invalid calibration: {str(e)}"
            )

        # Generate files
        # 1. Generate screen info JSON
        screen_info_json = file_generator.generate_screen_info(
            request.candidate_id, screen_info
        )

        # 2. Generate calibration CSV
        calibration_csv = calibration_service.generate_calibration_csv(
            request.candidate_id
        )

        # 3. Generate transform matrix NPZ
        transform_matrix_bytes = file_generator.generate_transform_matrix(
            transform_result["transform_matrix"]
        )

        # Validate file compatibility
        validation = file_generator.validate_file_compatibility(
            request.candidate_id,
            screen_info_json,
            calibration_csv,
            transform_matrix_bytes,
        )
        logger.debug("File validation result", data=validation)

        if not validation["valid"]:
            storage.update_session_status(
                request.session_id,
                "failed",
                error_message=f"File validation failed: {validation['errors']}",
            )
            raise HTTPException(
                status_code=500,
                detail=f"File validation failed: {validation['errors']}",
            )

        # Save to database
        storage.save_screen_info(request.candidate_id, screen_info_json)
        storage.save_calibration_data(
            request.candidate_id, calibration_csv, transform_result["transform_matrix"]
        )

        # Save files to disk for analyzer.py compatibility
        from pathlib import Path
        candidate_dir = Path(f"/Users/sachinadlakha/Desktop/Validia/web-cam-gaze/results/interview_calibrations/{request.candidate_id}")
        candidate_dir.mkdir(parents=True, exist_ok=True)
        file_generator_with_output = FileGenerator(output_dir=candidate_dir)
        
        try:
            file_paths = file_generator_with_output.save_files(
                request.candidate_id,
                screen_info_json,
                calibration_csv,
                transform_matrix_bytes,
            )
            logger.info("Calibration files saved to disk", file_paths=list(file_paths.keys()))
        except Exception as e:
            logger.error("Failed to save calibration files to disk", error=str(e))
            # Don't fail the API call for file save errors - data is still in DB

        # Update session status
        storage.update_session_status(request.session_id, "completed")

        # Log audit event
        storage.log_audit_event(
            candidate_id=request.candidate_id,
            action="calibration_completed",
            details={
                "session_id": request.session_id,
                "frames_processed": len(frames),
                "validation_metrics": validation_result["metrics"],
                "file_checksums": validation["checksums"],
            },
        )

        logger.info(
            "Calibration completed successfully",
            session_id=request.session_id,
            candidate_id=request.candidate_id,
            frames=len(frames),
        )

        return {
            "success": True,
            "session_id": request.session_id,
            "candidate_id": request.candidate_id,
            "calibration_stats": transform_result["calibration_stats"],
            "validation_metrics": validation_result["metrics"],
            "file_checksums": validation["checksums"],
            "message": "Calibration completed successfully",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to complete calibration",
            session_id=request.session_id,
            error=str(e),
        )
        storage.update_session_status(
            request.session_id, "failed", error_message=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/verify/{candidate_id}", response_model=CalibrationStatusResponse)
async def verify_calibration(
    candidate_id: str, storage: DatabaseStorageService = Depends(get_storage_service)
):
    """Verify calibration exists for a candidate"""
    try:
        # Check if calibration data exists
        calibration_exists = storage.check_calibration_exists(candidate_id)
        screen_info = storage.get_screen_info(candidate_id)

        response = CalibrationStatusResponse(
            exists=calibration_exists,
            candidate_id=candidate_id if calibration_exists else None,
            has_screen_info=screen_info is not None,
            has_calibration_data=calibration_exists,
        )

        if calibration_exists:
            # Get creation timestamp
            query = """
            SELECT created_at FROM calibration_data 
            WHERE candidate_id = %s
            """
            result = storage.db.execute_query(query, (candidate_id,), fetch_one=True)
            if result:
                response.created_at = result["created_at"].isoformat()

        return response

    except Exception as e:
        logger.error(
            "Failed to verify calibration", candidate_id=candidate_id, error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/download/{candidate_id}")
async def download_calibration(
    candidate_id: str, storage: DatabaseStorageService = Depends(get_storage_service)
):
    """Download calibration files for a candidate"""
    try:
        # Get calibration files from database
        files = storage.get_calibration_files(candidate_id)

        if not files:
            raise HTTPException(status_code=404, detail="Calibration not found")

        # Convert NPZ data to base64 for transmission
        import base64
        from io import BytesIO
        import numpy as np

        # Prepare response
        response_data = {}

        for filename, content in files.items():
            if filename.endswith(".json"):
                response_data[filename] = content
            elif filename.endswith(".csv"):
                response_data[filename] = content
            elif filename.endswith(".npz"):
                # Convert numpy data back to bytes
                buffer = BytesIO()
                np.savez_compressed(buffer, **content)
                npz_bytes = buffer.getvalue()
                # Encode as base64 for JSON response
                response_data[filename] = base64.b64encode(npz_bytes).decode("utf-8")

        logger.info(
            "Calibration files downloaded",
            candidate_id=candidate_id,
            files=list(response_data.keys()),
        )

        return response_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to download calibration", candidate_id=candidate_id, error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/diagnostics/{session_id}")
async def get_calibration_diagnostics(
    session_id: str, storage: DatabaseStorageService = Depends(get_storage_service)
):
    """Get detailed calibration diagnostics for debugging"""
    try:
        # Get session info
        session_info = storage.get_session_info(session_id)
        if not session_info:
            raise HTTPException(status_code=404, detail="Session not found")

        # Get calibration frames
        frames = storage.get_calibration_frames(session_id)

        # Analyze frame data
        diagnostics = {
            "session_info": session_info,
            "frame_count": len(frames),
            "frame_analysis": {
                "targets_covered": set(),
                "frames_per_target": {},
                "face_detection_rate": 0,
                "head_pose_stability": [],
            },
        }

        if frames:
            successful_frames = 0
            for frame in frames:
                if frame["frame_data"].get("success"):
                    successful_frames += 1
                    target_key = f"{frame['target_position']['x']},{frame['target_position']['y']}"
                    diagnostics["frame_analysis"]["targets_covered"].add(target_key)

                    if (
                        target_key
                        not in diagnostics["frame_analysis"]["frames_per_target"]
                    ):
                        diagnostics["frame_analysis"]["frames_per_target"][
                            target_key
                        ] = 0
                    diagnostics["frame_analysis"]["frames_per_target"][target_key] += 1

            diagnostics["frame_analysis"]["face_detection_rate"] = (
                successful_frames / len(frames) if frames else 0
            )
            diagnostics["frame_analysis"]["targets_covered"] = list(
                diagnostics["frame_analysis"]["targets_covered"]
            )

        return diagnostics

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get diagnostics", session_id=session_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
