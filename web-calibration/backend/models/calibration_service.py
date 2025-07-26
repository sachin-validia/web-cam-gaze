"""
Calibration service wrapping the existing HomTransform functionality
"""

import sys
from pathlib import Path
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
import structlog
from datetime import datetime
import pandas as pd

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.append(str(project_root))

from src.gaze_tracking.homtransform import HomTransform

logger = structlog.get_logger()


class CalibrationService:
    """Service wrapper for calibration and coordinate transformation"""

    def __init__(self):
        """Initialize calibration service"""
        self.calibration_data = []
        self.screen_info = None
        self.transform = None
        self.candidate_id = None

    def set_screen_info(self, screen_info: Dict[str, Any]):
        """Set screen information for calibration"""
        self.screen_info = screen_info
        logger.info(
            "Screen info set",
            width=screen_info.get("screen_width_px"),
            height=screen_info.get("screen_height_px"),
        )

    def add_calibration_point(
        self,
        gaze_data: Dict[str, Any],
        target_position: Dict[str, float],
        frame_index: int,
    ):
        """
        Add a calibration point from processed gaze data

        Args:
            gaze_data: Processed gaze estimation data
            target_position: Target position on screen (x, y)
            frame_index: Frame index in the sequence
        """
        if not gaze_data.get("success"):
            logger.warning("Skipping failed gaze estimation", frame_index=frame_index)
            return

        # Extract relevant data for calibration
        calibration_point = {
            "timestamp": datetime.utcnow().isoformat(),
            "frame_index": frame_index,
            "target_x": target_position["x"],
            "target_y": target_position["y"],
            "gaze_vector": gaze_data.get("gaze_vector", [0.5, 0.5, 1.0]),
            "normalized_gaze_angles": gaze_data.get(
                "normalized_gaze_angles", [0.0, 0.0]
            ),
            "head_pose": gaze_data.get("head_pose_rot", [0.0, 0.0, 0.0]),
            "bbox": gaze_data.get("bbox", [0, 0, 100, 100]),
        }

        # Add eye centers if available
        if "eye_centers" in gaze_data:
            calibration_point["eye_centers"] = gaze_data["eye_centers"]

        self.calibration_data.append(calibration_point)
        logger.debug(
            "Calibration point added", frame_index=frame_index, target=target_position
        )

    def compute_transformation_matrix(self) -> Dict[str, Any]:
        """
        Compute the transformation matrix from collected calibration data

        Returns:
            Dictionary containing transformation matrices and metadata
        """
        if not self.calibration_data:
            raise ValueError("No calibration data available")

        if not self.screen_info:
            raise ValueError("Screen information not set")

        try:
            logger.info(
                "Starting transformation matrix computation",
                num_points=len(self.calibration_data),
            )
            # Group data by target position
            target_groups = {}
            for i, point in enumerate(self.calibration_data):
                try:
                    key = (point["target_x"], point["target_y"])
                    if key not in target_groups:
                        target_groups[key] = []
                    target_groups[key].append(point)
                except Exception as e:
                    logger.error(
                        f"Error processing point {i}",
                        error=str(e),
                        point_keys=list(point.keys()),
                        target_x_type=type(point.get("target_x")),
                        target_y_type=type(point.get("target_y")),
                    )
                    raise

            # Ensure we have all 4 calibration targets
            if len(target_groups) < 4:
                raise ValueError(
                    f"Only {len(target_groups)} calibration targets found (need 4)"
                )

            # Prepare data for HomTransform
            screen_points = []
            gaze_vectors = []

            # Average gaze vectors for each target
            for (target_x, target_y), points in target_groups.items():
                try:
                    # Target positions are already normalized (0.1, 0.9, etc)
                    # Just ensure they're floats
                    logger.debug(
                        f"Processing target ({target_x}, {target_y})",
                        tx_type=type(target_x),
                        ty_type=type(target_y),
                    )
                    norm_x = float(target_x)
                    norm_y = float(target_y)
                    screen_points.append([norm_x, norm_y])
                except Exception as e:
                    logger.error(
                        f"Error converting target coords",
                        error=str(e),
                        target_x=target_x,
                        target_y=target_y,
                        tx_type=type(target_x),
                        ty_type=type(target_y),
                    )
                    raise

                # Average gaze vectors for this target
                # Ensure all gaze vectors are numpy arrays
                gaze_vecs = []
                for p in points:
                    vec = p.get("gaze_vector", [0.5, 0.5, 1.0])  # Default if missing
                    if isinstance(vec, list):
                        vec = np.array(vec)
                    # Fix Z-axis orientation to match desktop convention
                    if len(vec) > 2:
                        vec[2] = -vec[2]  # Invert Z
                    gaze_vecs.append(vec)

                avg_gaze = np.mean(gaze_vecs, axis=0)
                gaze_vectors.append(avg_gaze)

            screen_points = np.array(screen_points)
            gaze_vectors = np.array(gaze_vectors)

            # Implement HomTransform's calibration algorithm directly (no dependencies)
            # Convert normalized screen points to mm coordinates
            width_mm = float(self.screen_info['screen_width_mm'])
            height_mm = float(self.screen_info['screen_height_mm'])
            width_px = int(self.screen_info['screen_width_px'])
            height_px = int(self.screen_info['screen_height_px'])
            
            # Define standard calibration positions (must match desktop)
            calibration_positions = [(0.1, 0.1), (0.9, 0.1), (0.1, 0.9), (0.9, 0.9)]
            
            # Sort target groups to ensure consistent ordering
            sorted_targets = sorted(target_groups.keys())
            
            # Map targets to standard positions and create arrays
            screen_points_mm = []
            ordered_gaze_vectors = []
            
            for std_x, std_y in calibration_positions:
                # Find closest target to this standard position
                best_target = None
                min_dist = float('inf')
                for target_key in sorted_targets:
                    dist = np.sqrt((target_key[0] - std_x)**2 + (target_key[1] - std_y)**2)
                    if dist < min_dist:
                        min_dist = dist
                        best_target = target_key
                
                if best_target and min_dist < 0.1:  # Within 10% tolerance
                    # Use the gaze vectors from this target
                    idx = list(target_groups.keys()).index(best_target)
                    ordered_gaze_vectors.append(gaze_vectors[idx])
                    
                    # Calculate mm position for this standard point
                    x_mm = std_x * width_mm
                    y_mm = std_y * height_mm
                    screen_points_mm.append([x_mm, y_mm, 0])
                else:
                    raise ValueError(f"No calibration data found for position ({std_x}, {std_y})")
            
            screen_points_mm = np.array(screen_points_mm)
            gaze_vectors = np.array(ordered_gaze_vectors)
            
            # HomTransform's calibration algorithm (extracted from _fitSTransG)
            from scipy import optimize as opt
            
            # Rotation matrix (same as desktop)
            SRotG = np.array([[-1,0,0],[0,-1,0],[0,0,1]])
            gaze_3d = gaze_vectors[:,:,np.newaxis]  # Shape: (N, 3, 1)
            SetVal_3d = screen_points_mm[:,:,np.newaxis]  # Shape: (N, 3, 1)
            
            # Optimization function (same as HomTransform)
            def alignError(x, *const):
                SRotG, gaze, SetVal = const
                StG = np.array([[x[0]],[x[1]],[x[2]]])
                Gz = np.array([[0],[0],[1]])
                mu = (Gz.T @ (-SRotG.T @ StG))/(Gz.T @ gaze)
                Sg = SRotG @ (mu*gaze) + StG
                error = SetVal - Sg
                return error.flatten()
            
            # Initial guess (screen center in mm and camera distance)
            const = (SRotG, gaze_3d, SetVal_3d)
            # Use mm coordinates for initial guess to match desktop calibration
            x0 = np.array([width_mm/2, height_mm/2, 600.0])  # Center in mm, 600mm camera distance
            
            # Add bounds to prevent optimization from drifting too far from screen
            bounds = (
                [0, 0, 400],  # Lower bounds: x_min=0, y_min=0, z_min=400mm
                [width_mm, height_mm, 800]  # Upper bounds: screen dimensions, z_max=800mm
            )
            
            try:
                # Solve optimization with bounds to prevent drift
                res = opt.least_squares(alignError, x0, args=const, bounds=bounds)
                xopt = res.x
                logger.info(f"Calibration optimization: optimality={res.optimality}, solution={xopt}")
                
                # Validate optimization result
                if not res.success:
                    logger.warning(f"Optimization may not have converged: {res.message}")
                
                # Build transformation matrix (same as desktop)
                # Ensure Z is negative (camera behind screen)
                StG = np.array([[xopt[0]],[xopt[1]],[-abs(xopt[2])]])
                transform_matrix = np.r_[np.c_[SRotG, StG], np.array([[0,0,0,1]])]
                
                # Generate StG for each calibration point (matching desktop calibration)
                StG_list = []
                SetValues_3d = []
                
                # Calculate scale using global transformation (needed for individual StG)
                Gz = np.array([[0],[0],[1]])
                
                for i in range(len(screen_points_mm)):
                    # Get gaze vector and target position for this calibration point
                    gaze_i = gaze_3d[i]
                    SetVal_i = SetVal_3d[i]
                    
                    # Calculate scale for this gaze vector using global StG
                    # This matches HomTransform._getScale() logic
                    GTransS = np.linalg.inv(transform_matrix)
                    GtS = GTransS[:3,3].reshape(3,1)
                    scaleGaze_i = (Gz.T @ GtS) / (Gz.T @ gaze_i)
                    
                    # Calculate mu for this calibration point
                    mu_i = (Gz.T @ (-SRotG.T @ StG))/(Gz.T @ gaze_i)
                    
                    # Calculate individual StG for this calibration point
                    # This creates the per-point transformation offset
                    StG_i = SetVal_i - SRotG @ (mu_i * gaze_i)
                    
                    StG_list.append(StG_i)
                    SetValues_3d.append(screen_points_mm[i].reshape(3,1))
                
                # Store for later use
                self.transform = transform_matrix
                
                # Prepare result with desktop-compatible format
                result = {
                    "success": True,
                    "transform_matrix": {
                        "STransG": transform_matrix,  # 4x4 transformation matrix (like desktop)
                        "StG": StG_list,  # List of 3x1 vectors
                        "SetValues": np.array(SetValues_3d),  # (N, 3, 1) array
                    },
                    "calibration_stats": {
                        "total_frames": len(self.calibration_data),
                        "targets_used": len(target_groups),
                        "frames_per_target": {
                            f"{k[0]},{k[1]}": len(v) for k, v in target_groups.items()
                        },
                    },
                    "timestamp": datetime.utcnow().isoformat(),
                }
                
            except Exception as e:
                logger.error("HomTransform calibration failed, falling back to simple method", error=str(e))
                # Fallback to original 2D method if HomTransform fails
                src_aug = np.hstack([gaze_vectors[:, :2], np.ones((gaze_vectors.shape[0], 1))])
                A, *_ = np.linalg.lstsq(src_aug, screen_points, rcond=None)
                transform_3x3 = np.vstack([A.T, np.array([0, 0, 1])])
                transform_matrix = np.eye(4)
                transform_matrix[:3, :3] = transform_3x3
                self.transform = transform_matrix
                
                result = {
                    "success": True,
                    "transform_matrix": {
                        "STransG": transform_matrix,
                        "StG": [],
                        "SetValues": np.column_stack([screen_points, np.ones(len(screen_points))]).reshape(-1, 3, 1),
                    },
                    "calibration_stats": {
                        "total_frames": len(self.calibration_data),
                        "targets_used": len(target_groups),
                        "frames_per_target": {
                            f"{k[0]},{k[1]}": len(v) for k, v in target_groups.items()
                        },
                    },
                    "timestamp": datetime.utcnow().isoformat(),
                }

            logger.info(
                "Transformation matrix computed successfully",
                targets=len(target_groups),
                total_frames=len(self.calibration_data),
            )

            return result

        except Exception as e:
            logger.exception("compute_transformation_matrix raised")
            # logger.error("Failed to compute transformation matrix", error=str(e))
            import traceback, tempfile, pathlib

            path = pathlib.Path(tempfile.gettempdir()) / "calib_tb.txt"
            path.write_text(traceback.format_exc())
            logger.error("Traceback written to %s", path)
            return {"success": False, "error": str(e)}

    def transform_gaze_to_screen(self, gaze_vector: List[float]) -> Tuple[float, float]:
        """
        Transform gaze vector to screen coordinates using calibration

        Args:
            gaze_vector: 3D gaze vector [x, y, z]

        Returns:
            Tuple of (x, y) screen coordinates
        """
        if self.transform is None:
            raise ValueError("Calibration not completed")

        # Apply 3×3 homogeneous transform to gaze vector (x, y)
        # Convert gaze vector (x, y) to homogeneous coords (x, y, 1)
        gaze_h = np.array([gaze_vector[0], gaze_vector[1], 1.0])
        screen_h = self.transform @ gaze_h
        # Normalize to Cartesian coordinates
        screen_point = screen_h[:2] / screen_h[2]

        # Convert from normalized to pixel coordinates
        screen_x = screen_point[0] * self.screen_info["screen_width_px"]
        screen_y = screen_point[1] * self.screen_info["screen_height_px"]

        return float(screen_x), float(screen_y)

    def generate_calibration_csv(self, candidate_id: str) -> str:
        """
        Generate calibration CSV in the exact format expected by analyzer.py

        Returns:
            CSV string with calibration data
        """
        if not self.calibration_data:
            raise ValueError("No calibration data available")

        # Prepare data for CSV
        rows = []
        for idx, point in enumerate(self.calibration_data):
            # Fix coordinate system: invert Z-axis to match desktop convention
            gaze_vector = point["gaze_vector"].copy() if isinstance(point["gaze_vector"], list) else list(point["gaze_vector"])
            if len(gaze_vector) > 2:
                gaze_vector[2] = -gaze_vector[2]  # Invert Z to match desktop
            
            row = {
                "Unnamed: 0": idx,
                "Timestamp": point["timestamp"],
                "idx": point["frame_index"],
                "gaze_x": gaze_vector[0],
                "gaze_y": gaze_vector[1],
                "gaze_z": (
                    gaze_vector[2] if len(gaze_vector) > 2 else 0
                ),
                "yaw": (
                    point["head_pose"][0]
                    if isinstance(point["head_pose"], list)
                    else point.get("head_pose", {}).get("yaw", 0)
                ),
                "pitch": (
                    point["head_pose"][1]
                    if isinstance(point["head_pose"], list)
                    else point.get("head_pose", {}).get("pitch", 0)
                ),
                "roll": (
                    point["head_pose"][2]
                    if isinstance(point["head_pose"], list)
                    else point.get("head_pose", {}).get("roll", 0)
                ),
                # Convert normalized target positions to mm coordinates to match desktop format
                "set_x": point["target_x"] * float(self.screen_info['screen_width_mm']),
                "set_y": point["target_y"] * float(self.screen_info['screen_height_mm']),
                "set_z": 0,  # Always 0 for screen calibration
                "candidate_id": candidate_id,
            }

            # Add placeholder values for missing columns
            # These will be filled with actual values if available
            row.update(
                {
                    "REyePos_x": 0,
                    "REyePos_y": 0,
                    "LEyePos_x": 0,
                    "LEyePos_y": 0,
                    "HeadBox_xmin": point["bbox"][0] if "bbox" in point else 0,
                    "HeadBox_ymin": point["bbox"][1] if "bbox" in point else 0,
                    "RightEyeBox_xmin": 0,
                    "RightEyeBox_ymin": 0,
                    "LeftEyeBox_xmin": 0,
                    "LeftEyeBox_ymin": 0,
                    "ROpenClose": 1,  # Assume eyes open
                    "LOpenClose": 1,  # Assume eyes open
                    "WTransG": 0,  # Will be expanded to 16 columns
                }
            )

            # Add eye positions if available
            if "eye_centers" in point:
                row["REyePos_x"] = point["eye_centers"]["right"][0]
                row["REyePos_y"] = point["eye_centers"]["right"][1]
                row["LEyePos_x"] = point["eye_centers"]["left"][0]
                row["LEyePos_y"] = point["eye_centers"]["left"][1]

            rows.append(row)

        # Create DataFrame
        df = pd.DataFrame(rows)

        # Add WTransG columns (16 columns as per spec)
        for i in range(16):
            col_name = "WTransG" if i == 0 else f"WTransG.{i}"
            if col_name not in df.columns:
                df[col_name] = 0

        # Ensure column order matches expected format
        expected_columns = [
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
            "HeadBox_xmin",
            "HeadBox_ymin",
            "RightEyeBox_xmin",
            "RightEyeBox_ymin",
            "LeftEyeBox_xmin",
            "LeftEyeBox_ymin",
            "ROpenClose",
            "LOpenClose",
            "set_x",
            "set_y",
            "set_z",
            "WTransG",
        ]

        # Add WTransG.1 through WTransG.15
        for i in range(1, 16):
            expected_columns.append(f"WTransG.{i}")

        expected_columns.append("candidate_id")

        # Reorder columns to match expected format
        df = df[expected_columns]

        # Convert to CSV string
        csv_string = df.to_csv(index=False)

        logger.info(
            "Calibration CSV generated", candidate_id=candidate_id, rows=len(df)
        )

        return csv_string

    def reset(self):
        """Reset calibration data for a new session"""
        self.calibration_data = []
        self.transform = None
        self.screen_info = None
        logger.info("Calibration service reset")
