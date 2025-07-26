"""
Database storage service for calibration data
"""

import json
import base64
import numpy as np
from io import BytesIO
from typing import Dict, Optional, Any
import hashlib
from datetime import datetime
import structlog

# Use intra-package import to ensure a SINGLE module instance (`backend.db.database`).
from .database import get_db

logger = structlog.get_logger()


class DatabaseStorageService:
    """Handles calibration data storage and retrieval using MySQL"""

    def __init__(self):
        self.db = get_db()

    def save_screen_info(self, candidate_id: str, screen_data: dict) -> bool:
        """Save screen information to database"""
        try:
            query = """
            INSERT INTO screen_info (candidate_id, screen_data) 
            VALUES (%s, %s) 
            ON DUPLICATE KEY UPDATE 
                screen_data = VALUES(screen_data),
                updated_at = CURRENT_TIMESTAMP
            """
            self.db.execute_query(query, (candidate_id, json.dumps(screen_data)))
            logger.info("Screen info saved", candidate_id=candidate_id)
            return True
        except Exception as e:
            logger.error(
                "Failed to save screen info", candidate_id=candidate_id, error=str(e)
            )
            return False

    def save_calibration_data(
        self, candidate_id: str, csv_data: str, transform_matrix: dict
    ) -> bool:
        """Save calibration CSV and transform matrix to database"""
        try:
            # Serialize numpy arrays to bytes
            buffer = BytesIO()
            np.savez_compressed(buffer, **transform_matrix)
            matrix_bytes = buffer.getvalue()

            # Calculate checksum for data validation
            checksum = hashlib.sha256(csv_data.encode() + matrix_bytes).hexdigest()

            query = """
            INSERT INTO calibration_data 
                (candidate_id, calibration_csv, transform_matrix_data, file_checksum) 
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE 
                calibration_csv = VALUES(calibration_csv),
                transform_matrix_data = VALUES(transform_matrix_data),
                file_checksum = VALUES(file_checksum),
                updated_at = CURRENT_TIMESTAMP
            """
            self.db.execute_query(
                query, (candidate_id, csv_data, matrix_bytes, checksum)
            )
            logger.info(
                "Calibration data saved", candidate_id=candidate_id, checksum=checksum
            )
            return True
        except Exception as e:
            logger.error(
                "Failed to save calibration data",
                candidate_id=candidate_id,
                error=str(e),
            )
            return False

    def get_screen_info(self, candidate_id: str) -> Optional[dict]:
        """Retrieve screen info for a candidate"""
        try:
            query = "SELECT screen_data FROM screen_info WHERE candidate_id = %s"
            result = self.db.execute_query(query, (candidate_id,), fetch_one=True)

            if result:
                return json.loads(result["screen_data"])
            return None
        except Exception as e:
            logger.error(
                "Failed to get screen info", candidate_id=candidate_id, error=str(e)
            )
            return None

    def get_calibration_files(self, candidate_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve calibration files from database and reconstruct file format"""
        try:
            # Get screen info
            screen_data = self.get_screen_info(candidate_id)
            if not screen_data:
                logger.warning("No screen info found", candidate_id=candidate_id)
                return None

            # Get calibration data
            query = """
            SELECT calibration_csv, transform_matrix_data, file_checksum 
            FROM calibration_data WHERE candidate_id = %s
            """
            result = self.db.execute_query(query, (candidate_id,), fetch_one=True)

            if not result:
                logger.warning("No calibration data found", candidate_id=candidate_id)
                return None

            # Verify checksum
            csv_data = result["calibration_csv"]
            matrix_bytes = result["transform_matrix_data"]
            expected_checksum = result["file_checksum"]

            actual_checksum = hashlib.sha256(
                csv_data.encode() + matrix_bytes
            ).hexdigest()

            if actual_checksum != expected_checksum:
                logger.error(
                    "Checksum mismatch",
                    candidate_id=candidate_id,
                    expected=expected_checksum,
                    actual=actual_checksum,
                )
                return None

            # Reconstruct transform matrix
            buffer = BytesIO(matrix_bytes)
            transform_data = np.load(buffer)

            # Return files in the expected format
            files = {
                f"{candidate_id}_screen_info.json": screen_data,
                f"{candidate_id}_calibration.csv": csv_data,
                f"{candidate_id}_transform_matrix.npz": transform_data,
            }

            logger.info("Calibration files retrieved", candidate_id=candidate_id)
            return files

        except Exception as e:
            logger.error(
                "Failed to get calibration files",
                candidate_id=candidate_id,
                error=str(e),
            )
            return None

    def check_calibration_exists(self, candidate_id: str) -> bool:
        """Verify calibration data exists in database"""
        try:
            query = """
            SELECT COUNT(*) as count FROM calibration_data 
            WHERE candidate_id = %s
            """
            result = self.db.execute_query(query, (candidate_id,), fetch_one=True)
            exists = result["count"] > 0

            logger.info(
                "Calibration existence check", candidate_id=candidate_id, exists=exists
            )
            return exists

        except Exception as e:
            logger.error(
                "Failed to check calibration existence",
                candidate_id=candidate_id,
                error=str(e),
            )
            return False

    def create_calibration_session(
        self, session_id: str, candidate_id: str, interview_id: Optional[str] = None
    ) -> bool:
        """Create a new calibration session"""
        try:
            # Check if pool is initialized
            if not self.db.pool:
                logger.error("Database pool not initialized")
                return False

            query = """
            INSERT INTO calibration_sessions 
                (id, candidate_id, interview_id, status) 
            VALUES (%s, %s, %s, %s)
            """
            self.db.execute_insert(
                query, (session_id, candidate_id, interview_id, "in_progress")
            )
            logger.info(
                "Calibration session created",
                session_id=session_id,
                candidate_id=candidate_id,
            )
            return True
        except Exception as e:
            logger.error(
                "Failed to create calibration session",
                session_id=session_id,
                error=str(e),
            )
            import traceback

            traceback.print_exc()
            return False

    def update_session_status(
        self, session_id: str, status: str, error_message: Optional[str] = None
    ) -> bool:
        """Update calibration session status"""
        try:
            if error_message:
                query = """
                UPDATE calibration_sessions 
                SET status = %s, error_message = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                """
                params = (status, error_message, session_id)
            else:
                query = """
                UPDATE calibration_sessions 
                SET status = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                """
                params = (status, session_id)

            rows_affected = self.db.execute_update(query, params)
            logger.info(
                "Session status updated",
                session_id=session_id,
                status=status,
                rows_affected=rows_affected,
            )
            return rows_affected > 0
        except Exception as e:
            logger.error(
                "Failed to update session status", session_id=session_id, error=str(e)
            )
            return False

    def get_session_info(self, session_id: str) -> Optional[dict]:
        """Get calibration session information"""
        try:
            query = """
            SELECT id, candidate_id, interview_id, status, error_message,
                   created_at, updated_at, metadata
            FROM calibration_sessions WHERE id = %s
            """
            result = self.db.execute_query(query, (session_id,), fetch_one=True)

            if result:
                # Convert datetime objects to strings
                if result["created_at"]:
                    result["created_at"] = result["created_at"].isoformat()
                if result["updated_at"]:
                    result["updated_at"] = result["updated_at"].isoformat()
                if result["metadata"]:
                    result["metadata"] = json.loads(result["metadata"])

            return result
        except Exception as e:
            logger.error(
                "Failed to get session info", session_id=session_id, error=str(e)
            )
            return None

    def save_calibration_frame(
        self, session_id: str, frame_index: int, frame_data: dict, target_position: dict
    ) -> bool:
        """Save individual calibration frame data"""
        try:
            logger.debug(
                "Saving frame", session_id=session_id[:12], frame_index=frame_index
            )

            query = """
            INSERT INTO calibration_frames 
                (session_id, frame_index, frame_data, target_position) 
            VALUES (%s, %s, %s, %s)
            """
            insert_id = self.db.execute_insert(
                query,
                (
                    session_id,
                    frame_index,
                    json.dumps(frame_data),
                    json.dumps(target_position),
                ),
            )

            logger.debug("Frame saved", frame_index=frame_index, insert_id=insert_id)

            return True
        except Exception as e:
            logger.error(
                "Failed to save calibration frame",
                session_id=session_id,
                frame_index=frame_index,
                error=str(e),
                error_type=type(e).__name__,
            )
            import traceback

            traceback.print_exc()
            return False

    def get_calibration_frames(self, session_id: str) -> list:
        """Get all calibration frames for a session"""
        try:
            query = """
            SELECT frame_index, frame_data, target_position, created_at
            FROM calibration_frames 
            WHERE session_id = %s 
            ORDER BY frame_index
            """
            results = self.db.execute_query(query, (session_id,))

            frames = []
            for row in results:
                frames.append(
                    {
                        "frame_index": row["frame_index"],
                        "frame_data": json.loads(row["frame_data"]),
                        "target_position": json.loads(row["target_position"]),
                        "timestamp": row["created_at"].isoformat(),
                    }
                )

            return frames
        except Exception as e:
            logger.error(
                "Failed to get calibration frames", session_id=session_id, error=str(e)
            )
            return []

    def log_audit_event(
        self,
        candidate_id: Optional[str],
        action: str,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None,
        details: Optional[dict] = None,
    ) -> bool:
        """Log an audit event"""
        try:
            query = """
            INSERT INTO calibration_audit_log 
                (candidate_id, action, user_agent, ip_address, details) 
            VALUES (%s, %s, %s, %s, %s)
            """
            details_json = json.dumps(details) if details else None
            self.db.execute_insert(
                query, (candidate_id, action, user_agent, ip_address, details_json)
            )
            return True
        except Exception as e:
            logger.error("Failed to log audit event", action=action, error=str(e))
            return False
