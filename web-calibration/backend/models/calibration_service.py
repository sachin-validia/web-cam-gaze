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
        logger.info("Screen info set", 
                   width=screen_info.get('screen_width_px'),
                   height=screen_info.get('screen_height_px'))
    
    def add_calibration_point(self, gaze_data: Dict[str, Any], 
                            target_position: Dict[str, float],
                            frame_index: int):
        """
        Add a calibration point from processed gaze data
        
        Args:
            gaze_data: Processed gaze estimation data
            target_position: Target position on screen (x, y)
            frame_index: Frame index in the sequence
        """
        if not gaze_data.get('success'):
            logger.warning("Skipping failed gaze estimation", 
                         frame_index=frame_index)
            return
        
        # Extract relevant data for calibration
        calibration_point = {
            'timestamp': datetime.utcnow().isoformat(),
            'frame_index': frame_index,
            'target_x': target_position['x'],
            'target_y': target_position['y'],
            'gaze_vector': gaze_data['gaze_vector'],
            'normalized_gaze_angles': gaze_data['normalized_gaze_angles'],
            'head_pose': gaze_data['head_pose_rot'],
            'bbox': gaze_data['bbox']
        }
        
        # Add eye centers if available
        if 'eye_centers' in gaze_data:
            calibration_point['eye_centers'] = gaze_data['eye_centers']
        
        self.calibration_data.append(calibration_point)
        logger.debug("Calibration point added", 
                    frame_index=frame_index,
                    target=target_position)
    
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
            # Group data by target position
            target_groups = {}
            for point in self.calibration_data:
                key = (point['target_x'], point['target_y'])
                if key not in target_groups:
                    target_groups[key] = []
                target_groups[key].append(point)
            
            # Ensure we have all 4 calibration targets
            if len(target_groups) < 4:
                raise ValueError(f"Only {len(target_groups)} calibration targets found (need 4)")
            
            # Prepare data for HomTransform
            screen_points = []
            gaze_vectors = []
            
            # Average gaze vectors for each target
            for (target_x, target_y), points in target_groups.items():
                # Convert screen coordinates to normalized coordinates
                norm_x = target_x / self.screen_info['screen_width_px']
                norm_y = target_y / self.screen_info['screen_height_px']
                screen_points.append([norm_x, norm_y])
                
                # Average gaze vectors for this target
                avg_gaze = np.mean([p['gaze_vector'] for p in points], axis=0)
                gaze_vectors.append(avg_gaze)
            
            screen_points = np.array(screen_points)
            gaze_vectors = np.array(gaze_vectors)
            
            # Initialize and fit HomTransform
            self.transform = HomTransform()
            self.transform.get_matrix(
                source_points=gaze_vectors[:, :2],  # Use x,y components
                target_points=screen_points
            )
            
            # Get transformation matrix
            transform_matrix = self.transform.M
            
            # Prepare result
            result = {
                'success': True,
                'transform_matrix': {
                    'STransG': transform_matrix,  # Main transformation matrix
                    'StG': np.eye(3),  # Secondary transform (identity for now)
                    'SetValues': screen_points  # Calibration target positions
                },
                'calibration_stats': {
                    'total_frames': len(self.calibration_data),
                    'targets_used': len(target_groups),
                    'frames_per_target': {
                        f"{k[0]},{k[1]}": len(v) for k, v in target_groups.items()
                    }
                },
                'timestamp': datetime.utcnow().isoformat()
            }
            
            logger.info("Transformation matrix computed successfully",
                       targets=len(target_groups),
                       total_frames=len(self.calibration_data))
            
            return result
            
        except Exception as e:
            logger.error("Failed to compute transformation matrix", error=str(e))
            return {
                'success': False,
                'error': str(e)
            }
    
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
        
        # Use HomTransform to convert gaze to screen coordinates
        gaze_point = np.array([gaze_vector[0], gaze_vector[1]])
        screen_point = self.transform.transform(gaze_point)
        
        # Convert from normalized to pixel coordinates
        screen_x = screen_point[0] * self.screen_info['screen_width_px']
        screen_y = screen_point[1] * self.screen_info['screen_height_px']
        
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
            row = {
                'Unnamed: 0': idx,
                'Timestamp': point['timestamp'],
                'idx': point['frame_index'],
                'gaze_x': point['gaze_vector'][0],
                'gaze_y': point['gaze_vector'][1],
                'gaze_z': point['gaze_vector'][2] if len(point['gaze_vector']) > 2 else 0,
                'yaw': point['head_pose']['yaw'],
                'pitch': point['head_pose']['pitch'],
                'roll': point['head_pose']['roll'],
                'set_x': point['target_x'],
                'set_y': point['target_y'],
                'set_z': 0,  # Always 0 for screen calibration
                'candidate_id': candidate_id
            }
            
            # Add placeholder values for missing columns
            # These will be filled with actual values if available
            row.update({
                'REyePos_x': 0,
                'REyePos_y': 0,
                'LEyePos_x': 0,
                'LEyePos_y': 0,
                'HeadBox_xmin': point['bbox'][0] if 'bbox' in point else 0,
                'HeadBox_ymin': point['bbox'][1] if 'bbox' in point else 0,
                'RightEyeBox_xmin': 0,
                'RightEyeBox_ymin': 0,
                'LeftEyeBox_xmin': 0,
                'LeftEyeBox_ymin': 0,
                'ROpenClose': 1,  # Assume eyes open
                'LOpenClose': 1,  # Assume eyes open
                'WTransG': 0  # Will be expanded to 16 columns
            })
            
            # Add eye positions if available
            if 'eye_centers' in point:
                row['REyePos_x'] = point['eye_centers']['right'][0]
                row['REyePos_y'] = point['eye_centers']['right'][1]
                row['LEyePos_x'] = point['eye_centers']['left'][0]
                row['LEyePos_y'] = point['eye_centers']['left'][1]
            
            rows.append(row)
        
        # Create DataFrame
        df = pd.DataFrame(rows)
        
        # Add WTransG columns (16 columns as per spec)
        for i in range(16):
            col_name = 'WTransG' if i == 0 else f'WTransG.{i}'
            if col_name not in df.columns:
                df[col_name] = 0
        
        # Ensure column order matches expected format
        expected_columns = [
            'Unnamed: 0', 'Timestamp', 'idx', 'gaze_x', 'gaze_y', 'gaze_z',
            'REyePos_x', 'REyePos_y', 'LEyePos_x', 'LEyePos_y',
            'yaw', 'pitch', 'roll',
            'HeadBox_xmin', 'HeadBox_ymin', 
            'RightEyeBox_xmin', 'RightEyeBox_ymin',
            'LeftEyeBox_xmin', 'LeftEyeBox_ymin',
            'ROpenClose', 'LOpenClose',
            'set_x', 'set_y', 'set_z',
            'WTransG'
        ]
        
        # Add WTransG.1 through WTransG.15
        for i in range(1, 16):
            expected_columns.append(f'WTransG.{i}')
        
        expected_columns.append('candidate_id')
        
        # Reorder columns to match expected format
        df = df[expected_columns]
        
        # Convert to CSV string
        csv_string = df.to_csv(index=False)
        
        logger.info("Calibration CSV generated", 
                   candidate_id=candidate_id,
                   rows=len(df))
        
        return csv_string
    
    def reset(self):
        """Reset calibration data for a new session"""
        self.calibration_data = []
        self.transform = None
        self.screen_info = None
        logger.info("Calibration service reset")