"""
File generation service for creating analyzer-compatible calibration files
"""

import json
import numpy as np
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
import structlog
import hashlib

logger = structlog.get_logger()


class FileGenerator:
    """Generates calibration files in exact format expected by analyzer.py"""

    def __init__(self, output_dir: Optional[Path] = None):
        """
        Initialize file generator

        Args:
            output_dir: Directory to save files (optional, for file-based storage)
        """
        self.output_dir = output_dir
        if output_dir:
            output_dir.mkdir(parents=True, exist_ok=True)

    def generate_screen_info(self, candidate_id: str, screen_data: dict) -> dict:
        """
        Generate screen info JSON in exact format

        Args:
            candidate_id: Unique candidate identifier
            screen_data: Screen configuration data

        Returns:
            Dictionary in exact format for screen_info.json
        """

        def safe_int(value, default=0):
            try:
                return int(value)
            except (TypeError, ValueError):
                return default

        def safe_float(value, default=0.0):
            try:
                return float(value)
            except (TypeError, ValueError):
                return default

        screen_info = {
            "candidate_id": candidate_id,
            "timestamp": screen_data.get("timestamp", datetime.utcnow().isoformat()),
            "collection_method": screen_data.get("collection_method", "automatic"),
            "screen_width_px": safe_int(screen_data.get("screen_width_px"), 1920),
            "screen_height_px": safe_int(screen_data.get("screen_height_px"), 1080),
            "screen_width_mm": safe_float(screen_data.get("screen_width_mm"), 0.0),
            "screen_height_mm": safe_float(screen_data.get("screen_height_mm"), 0.0),
            "camera_position": screen_data.get("camera_position", "top-center"),
            "distance_cm": str(screen_data.get("distance_cm", "60")),
            "dpi": safe_float(screen_data.get("dpi"), 96.0),
            "diagonal_inches": safe_float(screen_data.get("diagonal_inches"), 0.0),
            "monitor_name": screen_data.get("monitor_name", "Unknown"),
        }

        # Calculate missing values if possible
        if screen_info["screen_width_mm"] == 0 and screen_info["dpi"] > 0:
            screen_info["screen_width_mm"] = (
                screen_info["screen_width_px"] / screen_info["dpi"] * 25.4
            )
            screen_info["screen_height_mm"] = (
                screen_info["screen_height_px"] / screen_info["dpi"] * 25.4
            )

        if screen_info["diagonal_inches"] == 0 and screen_info["screen_width_mm"] > 0:
            width_in = screen_info["screen_width_mm"] / 25.4
            height_in = screen_info["screen_height_mm"] / 25.4
            screen_info["diagonal_inches"] = np.sqrt(width_in**2 + height_in**2)

        logger.info(
            "Screen info generated",
            candidate_id=candidate_id,
            resolution=f"{screen_info['screen_width_px']}x{screen_info['screen_height_px']}",
        )

        return screen_info

    def generate_calibration_csv(self, calibration_csv_content: str) -> str:
        """
        Validate and return calibration CSV content

        Args:
            calibration_csv_content: CSV content from calibration service

        Returns:
            Validated CSV string
        """
        # The calibration service already generates the CSV in correct format
        # This method validates it has the required structure

        lines = calibration_csv_content.strip().split("\n")
        if len(lines) < 2:
            raise ValueError("Invalid CSV content - no data rows")

        # Check header
        header = lines[0]
        required_columns = [
            "Unnamed: 0",
            "Timestamp",
            "idx",
            "gaze_x",
            "gaze_y",
            "gaze_z",
            "REyePos_x",
            "REyePos_y",
            "LEyePos_x",
            "LEyePos_y",
            "yaw",
            "pitch",
            "roll",
            "candidate_id",
        ]

        for col in required_columns:
            if col not in header:
                raise ValueError(f"Missing required column: {col}")

        logger.info(
            "Calibration CSV validated", rows=len(lines) - 1
        )  # Excluding header

        return calibration_csv_content

    def generate_transform_matrix(self, transform_data: dict) -> bytes:
        """
        Generate transform matrix NPZ file content

        Args:
            transform_data: Dictionary containing transformation matrices

        Returns:
            Bytes content of NPZ file
        """
        # Ensure required arrays are present
        if "STransG" not in transform_data:
            raise ValueError("Missing required STransG matrix")

        # Convert to numpy arrays if needed
        arrays_to_save = {}

        # Main transformation matrix (required)
        arrays_to_save["STransG"] = np.array(transform_data["STransG"])

        # Secondary transform (optional, use identity if not provided)
        if "StG" in transform_data:
            arrays_to_save["StG"] = np.array(transform_data["StG"])
        else:
            arrays_to_save["StG"] = np.eye(3)

        # Calibration target positions (optional)
        if "SetValues" in transform_data:
            arrays_to_save["SetValues"] = np.array(transform_data["SetValues"])

        # Create NPZ file in memory
        from io import BytesIO

        buffer = BytesIO()
        np.savez_compressed(buffer, **arrays_to_save)
        npz_bytes = buffer.getvalue()

        logger.info(
            "Transform matrix NPZ generated",
            size_bytes=len(npz_bytes),
            matrices=list(arrays_to_save.keys()),
        )

        return npz_bytes

    def save_files(
        self,
        candidate_id: str,
        screen_info: dict,
        calibration_csv: str,
        transform_matrix_bytes: bytes,
    ) -> Dict[str, Path]:
        """
        Save all calibration files to disk (for file-based storage)

        Args:
            candidate_id: Unique candidate identifier
            screen_info: Screen information dictionary
            calibration_csv: CSV content
            transform_matrix_bytes: NPZ file bytes

        Returns:
            Dictionary mapping file types to their paths
        """
        if not self.output_dir:
            raise ValueError("Output directory not set")

        file_paths = {}

        # Save screen info JSON
        screen_info_path = self.output_dir / f"{candidate_id}_screen_info.json"
        with open(screen_info_path, "w") as f:
            json.dump(screen_info, f, indent=2)
        file_paths["screen_info"] = screen_info_path

        # Save calibration CSV
        calibration_csv_path = self.output_dir / f"{candidate_id}_calibration.csv"
        with open(calibration_csv_path, "w") as f:
            f.write(calibration_csv)
        file_paths["calibration_csv"] = calibration_csv_path

        # Save transform matrix NPZ
        transform_matrix_path = self.output_dir / f"{candidate_id}_transform_matrix.npz"
        with open(transform_matrix_path, "wb") as f:
            f.write(transform_matrix_bytes)
        file_paths["transform_matrix"] = transform_matrix_path

        logger.info(
            "Calibration files saved",
            candidate_id=candidate_id,
            files=list(file_paths.keys()),
        )

        return file_paths

    def validate_file_compatibility(
        self,
        candidate_id: str,
        screen_info: dict,
        calibration_csv: str,
        transform_matrix_bytes: bytes,
    ) -> Dict[str, Any]:
        """
        Validate that generated files are compatible with analyzer.py

        Returns:
            Validation result with any warnings or errors
        """
        validation_result = {"valid": True, "warnings": [], "errors": []}

        # Validate screen info
        required_screen_fields = [
            "candidate_id",
            "timestamp",
            "screen_width_px",
            "screen_height_px",
        ]
        for field in required_screen_fields:
            if field not in screen_info:
                validation_result["errors"].append(
                    f"Missing screen info field: {field}"
                )
                validation_result["valid"] = False

        # Validate CSV structure
        csv_lines = calibration_csv.strip().split("\n")
        if len(csv_lines) < 5:  # Header + at least 4 data rows
            validation_result["warnings"].append("Very few calibration points")

        # Validate NPZ can be loaded
        try:
            from io import BytesIO

            buffer = BytesIO(transform_matrix_bytes)
            npz_data = np.load(buffer)

            if "STransG" not in npz_data:
                validation_result["errors"].append(
                    "Missing STransG in transform matrix"
                )
                validation_result["valid"] = False
            else:
                matrix_shape = npz_data["STransG"].shape
                if matrix_shape != (3, 3):
                    validation_result["warnings"].append(
                        f"Unexpected STransG shape: {matrix_shape}"
                    )

            npz_data.close()
        except Exception as e:
            validation_result["errors"].append(f"Invalid NPZ file: {str(e)}")
            validation_result["valid"] = False

        # Calculate checksums for verification
        validation_result["checksums"] = {
            "screen_info": hashlib.sha256(
                json.dumps(screen_info, sort_keys=True).encode()
            ).hexdigest()[:8],
            "calibration_csv": hashlib.sha256(calibration_csv.encode()).hexdigest()[:8],
            "transform_matrix": hashlib.sha256(transform_matrix_bytes).hexdigest()[:8],
        }

        logger.info(
            "File compatibility validated",
            candidate_id=candidate_id,
            valid=validation_result["valid"],
            warnings_count=len(validation_result["warnings"]),
            errors_count=len(validation_result["errors"]),
        )

        return validation_result
