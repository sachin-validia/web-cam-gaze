"""
Gaze estimation service wrapping the existing PLGaze model
"""

import sys
from pathlib import Path
import numpy as np
import cv2
from typing import Dict, Optional, Tuple, Any
import structlog
import base64
from io import BytesIO
from PIL import Image

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.append(str(project_root))
# Also add src directory for plgaze imports
sys.path.append(str(project_root / "src"))

from plgaze.gaze_estimator import GazeEstimator
from plgaze.common import Face
from omegaconf import OmegaConf

logger = structlog.get_logger()


class GazeService:
    """Service wrapper for PLGaze gaze estimation"""

    def __init__(self, config_path: Optional[str] = None):
        """Initialize gaze service with PLGaze model"""
        self.estimator = None
        self.config_path = config_path or str(
            project_root / "src/plgaze/data/configs/eth-xgaze.yaml"
        )
        self._initialize_model()

    def _initialize_model(self):
        """Initialize the PLGaze model"""
        try:
            # Set PACKAGE_ROOT for config interpolation
            package_root = str(project_root / "src")
            OmegaConf.register_new_resolver("PACKAGE_ROOT", lambda: package_root)

            # Load configuration
            config = OmegaConf.load(self.config_path)
            config.device = "cpu"  # Use CPU for web server compatibility

            # Override paths to use absolute paths
            config.gaze_estimator.checkpoint = str(
                project_root / "src/plgaze/models/eth-xgaze/eth-xgaze_resnet18.pth"
            )
            config.gaze_estimator.camera_params = str(
                project_root / "src/plgaze/data/calib/sample_params.yaml"
            )
            config.gaze_estimator.normalized_camera_params = str(
                project_root / "src/plgaze/data/normalized_camera_params/eth-xgaze.yaml"
            )

            # Initialize gaze estimator
            self.estimator = GazeEstimator(config)
            logger.info(
                "Gaze model initialized successfully", config_path=self.config_path
            )
        except Exception as e:
            logger.error("Failed to initialize gaze model", error=str(e))
            raise RuntimeError(f"Failed to initialize gaze model: {e}")

    def decode_base64_image(self, base64_string: str) -> np.ndarray:
        """Decode base64 image to numpy array"""
        try:
            # Remove data URL prefix if present
            if "," in base64_string:
                base64_string = base64_string.split(",")[1]

            sanitized = base64_string.strip()

            # Consolidate whitespace/newlines that sometimes appear in large JSON strings
            sanitized = "".join(sanitized.split())  # remove all whitespace characters

            # Some browsers convert '+' -> ' ' inside JSON bodies; restore
            if " " in sanitized and "+" not in sanitized:
                sanitized = sanitized.replace(" ", "+")

            # Ensure proper base-64 padding (len % 4 should be 0)
            padding_needed = (-len(sanitized)) % 4
            if padding_needed:
                sanitized += "=" * padding_needed

            img_bytes = base64.b64decode(sanitized, validate=False)

            if len(img_bytes) == 0:
                raise ValueError(
                    "Decoded image bytes are empty – likely bad base64 input"
                )

            # --- Primary decode path: Pillow --------------------------------
            try:
                img = Image.open(BytesIO(img_bytes))
                img_array = np.array(img)
            except Exception:
                # Fallback: OpenCV decode; handles slight corruption better
                img_array = cv2.imdecode(
                    np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_COLOR
                )
                if img_array is None:
                    raise  # re-raise to outer except handler

            # Ensure BGR ordering for downstream OpenCV pipeline
            if len(img_array.shape) == 3 and img_array.shape[2] == 3:
                img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)

            return img_array
        except Exception as e:
            logger.error("Failed to decode base64 image", error=str(e))
            raise ValueError(f"Invalid base64 image data: {e}")

    # ------------------------------------------------------------------
    # New helpers for multipart file uploads (raw JPEG/PNG bytes)
    # ------------------------------------------------------------------

    @staticmethod
    def decode_image_bytes(img_bytes: bytes) -> np.ndarray:
        """Convert raw image bytes (JPEG/PNG) to BGR numpy array."""
        try:
            img = Image.open(BytesIO(img_bytes))
            img_array = np.array(img)
            if len(img_array.shape) == 3 and img_array.shape[2] == 3:
                img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
            return img_array
        except Exception as e:
            logger.error("Failed to decode image bytes", error=str(e))
            raise ValueError(f"Invalid image bytes: {e}")

    # Public wrapper ----------------------------------------------------

    def process_calibration_frame_bytes(
        self, frame_bytes: bytes, target_position: Dict[str, float]
    ) -> Dict[str, Any]:
        """Same as process_calibration_frame but works with raw bytes."""
        try:
            frame = self.decode_image_bytes(frame_bytes)

            height, width = frame.shape[:2]
            faces = self.estimator.detect_faces(frame)
            if not faces:
                return {
                    "success": False,
                    "error": "No face detected",
                    "frame_shape": (height, width),
                }

            face = faces[0]
            self.estimator.estimate_gaze(frame, face)

            gaze_result = {
                "success": True,
                "gaze_vector": getattr(face, 'gaze_vector', np.array([0, 0, 0])).tolist() if hasattr(face, 'gaze_vector') and hasattr(face.gaze_vector, 'tolist') else [0, 0, 0],
                "normalized_gaze_angles": getattr(face, 'normalized_gaze_angles', np.array([0, 0])).tolist() if hasattr(face, 'normalized_gaze_angles') and hasattr(face.normalized_gaze_angles, 'tolist') else [0, 0],
                "angle_to_vector": getattr(face, 'angle_to_vector', np.array([0, 0, 0])).tolist() if hasattr(face, 'angle_to_vector') and hasattr(face.angle_to_vector, 'tolist') else [0, 0, 0],
                "head_pose_rot": {
                    "yaw": float(face.head_pose_rot.as_euler("XYZ")[1]) if hasattr(face, 'head_pose_rot') else 0.0,
                    "pitch": float(face.head_pose_rot.as_euler("XYZ")[0]) if hasattr(face, 'head_pose_rot') else 0.0,
                    "roll": float(face.head_pose_rot.as_euler("XYZ")[2]) if hasattr(face, 'head_pose_rot') else 0.0,
                },
                "bbox": getattr(face, 'bbox', np.array([0, 0, 0, 0])).tolist() if hasattr(face, 'bbox') and hasattr(face.bbox, 'tolist') else [0, 0, 0, 0],
                "frame_shape": (height, width),
                "target_position": target_position,
            }

            if hasattr(face, "eye_centers") and face.eye_centers is not None:
                try:
                    if len(face.eye_centers) >= 2:
                        gaze_result["eye_centers"] = {
                            "left": face.eye_centers[0].tolist() if hasattr(face.eye_centers[0], 'tolist') else [0, 0],
                            "right": face.eye_centers[1].tolist() if hasattr(face.eye_centers[1], 'tolist') else [0, 0],
                        }
                except (IndexError, AttributeError):
                    pass  # Skip if eye_centers format is unexpected

            # preliminary gaze point
            gx, gy = gaze_result["gaze_vector"][:2]
            gaze_result["estimated_gaze_point"] = {"x": float(gx), "y": float(gy)}

            return gaze_result
        except Exception as e:
            logger.error("Failed to process calibration frame (bytes)", error=str(e))
            return {"success": False, "error": str(e)}

    def process_frame(self, frame_data: str) -> Dict[str, Any]:
        """
        Process a single frame and return gaze estimation data

        Args:
            frame_data: Base64 encoded image data

        Returns:
            Dictionary containing gaze estimation results
        """
        try:
            # Decode image
            frame = self.decode_base64_image(frame_data)

            # Get image dimensions
            height, width = frame.shape[:2]

            # Detect faces (using estimator's face detector)
            faces = self.estimator.detect_faces(frame)

            if not faces:
                return {
                    "success": False,
                    "error": "No face detected",
                    "frame_shape": (height, width),
                }

            # Use the first detected face
            face = faces[0]

            # Estimate gaze
            self.estimator.estimate_gaze(frame, face)

            # Extract gaze data with safe attribute access
            gaze_data = {
                "success": True,
                "gaze_vector": getattr(face, 'gaze_vector', np.array([0, 0, 0])).tolist() if hasattr(face, 'gaze_vector') and hasattr(face.gaze_vector, 'tolist') else [0, 0, 0],
                "normalized_gaze_angles": getattr(face, 'normalized_gaze_angles', np.array([0, 0])).tolist() if hasattr(face, 'normalized_gaze_angles') and hasattr(face.normalized_gaze_angles, 'tolist') else [0, 0],
                "angle_to_vector": getattr(face, 'angle_to_vector', np.array([0, 0, 0])).tolist() if hasattr(face, 'angle_to_vector') and hasattr(face.angle_to_vector, 'tolist') else [0, 0, 0],
                "landmarks": (
                    face.landmarks.tolist() if hasattr(face, "landmarks") and hasattr(face.landmarks, 'tolist') else []
                ),
                "head_pose_rot": {
                    "yaw": float(face.head_pose_rot.as_euler("XYZ")[1]) if hasattr(face, 'head_pose_rot') else 0.0,
                    "pitch": float(face.head_pose_rot.as_euler("XYZ")[0]) if hasattr(face, 'head_pose_rot') else 0.0,
                    "roll": float(face.head_pose_rot.as_euler("XYZ")[2]) if hasattr(face, 'head_pose_rot') else 0.0,
                },
                "bbox": getattr(face, 'bbox', np.array([0, 0, 0, 0])).tolist() if hasattr(face, 'bbox') and hasattr(face.bbox, 'tolist') else [0, 0, 0, 0],
                "frame_shape": (height, width),
            }

            # Add eye center positions if available
            if hasattr(face, "eye_centers") and face.eye_centers is not None:
                try:
                    if len(face.eye_centers) >= 2:
                        gaze_data["eye_centers"] = {
                            "left": face.eye_centers[0].tolist() if hasattr(face.eye_centers[0], 'tolist') else [0, 0],
                            "right": face.eye_centers[1].tolist() if hasattr(face.eye_centers[1], 'tolist') else [0, 0],
                        }
                except (IndexError, AttributeError):
                    pass  # Skip if eye_centers format is unexpected

            return gaze_data

        except Exception as e:
            logger.error("Failed to process frame", error=str(e))
            return {"success": False, "error": str(e)}

    def process_calibration_frame(
        self, frame_data: str, target_position: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        Process a frame during calibration with known target position

        Args:
            frame_data: Base64 encoded image data
            target_position: Dictionary with 'x' and 'y' screen coordinates

        Returns:
            Dictionary containing gaze data and target position
        """
        try:
            # Get basic gaze estimation
            gaze_result = self.process_frame(frame_data)

            if not gaze_result["success"]:
                return gaze_result

            # Add calibration-specific data
            gaze_result["target_position"] = target_position
            gaze_result["timestamp"] = None  # Will be set by caller

            # Calculate gaze point on screen (preliminary, before calibration)
            # This will be refined after calibration is complete
            if "gaze_vector" in gaze_result:
                # Simple projection for initial estimate
                gaze_x = gaze_result["gaze_vector"][0]
                gaze_y = gaze_result["gaze_vector"][1]
                gaze_result["estimated_gaze_point"] = {
                    "x": float(gaze_x),
                    "y": float(gaze_y),
                }

            return gaze_result

        except Exception as e:
            logger.error(
                "Failed to process calibration frame",
                error=str(e),
                target_position=target_position,
            )
            return {
                "success": False,
                "error": str(e),
                "target_position": target_position,
            }

    def validate_calibration_data(self, calibration_frames: list) -> Dict[str, Any]:
        """
        Validate collected calibration data

        Args:
            calibration_frames: List of processed calibration frames

        Returns:
            Validation result with quality metrics
        """
        try:
            if not calibration_frames:
                return {"valid": False, "error": "No calibration frames provided"}

            # Check minimum frames per target
            target_counts = {}
            for frame in calibration_frames:
                if "target_position" in frame:
                    key = f"{frame['target_position']['x']},{frame['target_position']['y']}"
                    target_counts[key] = target_counts.get(key, 0) + 1

            min_frames_per_target = min(target_counts.values()) if target_counts else 0

            # Calculate quality metrics
            face_detection_rate = sum(
                1 for f in calibration_frames if f.get("success", False)
            ) / len(calibration_frames)

            # Check head pose stability
            head_poses = []
            for frame in calibration_frames:
                if frame.get("success") and "head_pose_rot" in frame:
                    head_poses.append(
                        [
                            frame["head_pose_rot"]["yaw"],
                            frame["head_pose_rot"]["pitch"],
                            frame["head_pose_rot"]["roll"],
                        ]
                    )

            head_pose_std = np.std(head_poses, axis=0) if head_poses else [0, 0, 0]
            head_stability = float(
                np.mean(head_pose_std < 0.1)
            )  # Threshold for stability

            validation_result = {
                "valid": (
                    len(target_counts) >= 4  # At least 4 targets
                    and min_frames_per_target >= 10  # At least 10 frames per target
                    and face_detection_rate > 0.8  # 80% face detection rate
                ),
                "metrics": {
                    "total_frames": len(calibration_frames),
                    "unique_targets": len(target_counts),
                    "min_frames_per_target": min_frames_per_target,
                    "face_detection_rate": face_detection_rate,
                    "head_stability": head_stability,
                    "head_pose_std": (
                        head_pose_std.tolist()
                        if isinstance(head_pose_std, np.ndarray)
                        else head_pose_std
                    ),
                },
                "target_counts": target_counts,
            }

            if not validation_result["valid"]:
                reasons = []
                if len(target_counts) < 4:
                    reasons.append(f"Only {len(target_counts)} targets (need 4)")
                if min_frames_per_target < 10:
                    reasons.append(
                        f"Only {min_frames_per_target} frames per target (need 10+)"
                    )
                if face_detection_rate < 0.8:
                    reasons.append(
                        f"Face detection rate {face_detection_rate:.1%} (need 80%+)"
                    )
                validation_result["error"] = "; ".join(reasons)

            return validation_result

        except Exception as e:
            logger.error("Failed to validate calibration data", error=str(e))
            return {"valid": False, "error": str(e)}
