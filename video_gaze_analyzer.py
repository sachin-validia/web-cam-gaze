"""
Video Gaze Analyzer for Interview Cheating Detection
====================================================

This system analyzes recorded interview videos to detect when candidates
are looking outside the screen boundaries, which may indicate cheating behavior.
"""

import cv2
import numpy as np
import pandas as pd
import json
import pathlib
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
import sys
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')

sys.path.append('src')
from plgaze.model_pl_gaze import GazeModel
from gaze_tracking.homtransform import HomTransform
from interview_calibration_system import InterviewCalibrationSystem

class VideoGazeAnalyzer:
    """
    Analyzes recorded interview videos to detect off-screen gaze patterns
    """
    
    def __init__(self, config_path=None):
        # Initialize the calibration system to load candidate data
        self.calibration_system = InterviewCalibrationSystem(config_path)
        
        # Results directory
        self.results_dir = pathlib.Path("results/video_analysis")
        self.results_dir.mkdir(exist_ok=True, parents=True)
        
    def analyze_video(self, video_path: str, candidate_id: str, 
                     output_prefix: str = None, frame_skip: int = 1) -> Dict:
        """
        Analyze a video to detect off-screen gaze patterns
        
        Args:
            video_path: Path to the video file
            candidate_id: ID of the candidate (must have calibration data)
            output_prefix: Optional prefix for output files
            frame_skip: Process every nth frame (default: 1 = every frame)
            
        Returns:
            Dictionary containing analysis results
        """
        print(f"Starting video analysis for candidate {candidate_id}")
        print(f"Video: {video_path}")
        
        # Load calibration data
        try:
            calib_data = self.calibration_system.load_candidate_calibration(candidate_id)
            screen_info = calib_data['screen_info']
            transform_matrix = calib_data['transform_matrix']
            
            print(f"Screen dimensions: {screen_info['screen_width_px']}x{screen_info['screen_height_px']} pixels")
            print(f"Physical dimensions: {screen_info['screen_width_mm']}x{screen_info['screen_height_mm']} mm")
            
        except Exception as e:
            raise RuntimeError(f"Failed to load calibration data for candidate {candidate_id}: {e}")
        
        # Initialize gaze model
        model = GazeModel(self.calibration_system.config)
        
        # Setup HomTransform with calibration data
        homtrans = HomTransform(".")
        homtrans.width = int(screen_info['screen_width_px'])
        homtrans.height = int(screen_info['screen_height_px'])
        homtrans.width_mm = float(screen_info['screen_width_mm'])
        homtrans.height_mm = float(screen_info['screen_height_mm'])
        homtrans.STransG = transform_matrix
        
        # Debug: Check if calibration matrix is loaded
        print(f"DEBUG: STransG matrix shape: {transform_matrix.shape}")
        print(f"DEBUG: STransG matrix:\n{transform_matrix}")
        
        # We need to initialize StG array for the _getGazeOnScreen method to work
        # This is normally done during calibration, but we'll approximate it
        try:
            # Load calibration data if available
            calib_csv_path = pathlib.Path(f"results/interview_calibrations/{candidate_id}_calibration.csv")
            if calib_csv_path.exists():
                print(f"DEBUG: Loading calibration data from {calib_csv_path}")
                calib_df = pd.read_csv(calib_csv_path)
                # Initialize StG with some default values based on calibration
                # This is a simplified approach
                homtrans.StG = [np.array([[homtrans.width_mm/4], [homtrans.height_mm/4], [homtrans.width_mm]]) for _ in range(4)]
        except Exception as e:
            print(f"DEBUG: Could not load calibration CSV: {e}")
            # Use default values
            homtrans.StG = [np.array([[homtrans.width_mm/4], [homtrans.height_mm/4], [homtrans.width_mm]]) for _ in range(4)]
        
        # Open video
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise RuntimeError(f"Could not open video: {video_path}")
        
        # Get video properties
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps
        
        print(f"Video properties: {fps:.2f} FPS, {total_frames} frames, {duration:.2f} seconds")
        
        # Analysis results
        results = {
            'candidate_id': candidate_id,
            'video_path': video_path,
            'screen_info': screen_info,
            'video_info': {
                'fps': fps,
                'total_frames': total_frames,
                'duration': duration
            },
            'gaze_data': [],
            'off_screen_events': [],
            'statistics': {}
        }
        
        frame_count = 0
        processed_frames = 0
        off_screen_count = 0
        
        print("Processing video frames...")
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
                
            frame_count += 1
            
            # Skip frames if needed
            if frame_count % frame_skip != 0:
                continue
                
            processed_frames += 1
            timestamp = frame_count / fps
            
            # Progress indicator
            if processed_frames % 100 == 0:
                progress = (frame_count / total_frames) * 100
                print(f"Progress: {progress:.1f}% ({processed_frames} frames processed)")
            
            # Get gaze estimation
            try:
                eye_info = model.get_gaze(frame, imshow=False)
                
                if eye_info is None or eye_info.get('gaze') is None:
                    # No face detected or gaze estimation failed
                    gaze_data = {
                        'timestamp': timestamp,
                        'frame_number': frame_count,
                        'face_detected': False,
                        'gaze_detected': False,
                        'gaze_x_px': None,
                        'gaze_y_px': None,
                        'on_screen': None,
                        'off_screen_direction': None
                    }
                    results['gaze_data'].append(gaze_data)
                    continue
                
                # Convert gaze to screen coordinates
                gaze_vector = eye_info['gaze']
                screen_gaze = self._gaze_to_screen_coordinates(gaze_vector, homtrans)
                
                # Check if gaze is on screen
                on_screen, off_screen_direction = self._is_gaze_on_screen(
                    screen_gaze, screen_info['screen_width_px'], screen_info['screen_height_px']
                )
                
                if not on_screen:
                    off_screen_count += 1
                
                # Store gaze data
                gaze_data = {
                    'timestamp': timestamp,
                    'frame_number': frame_count,
                    'face_detected': True,
                    'gaze_detected': True,
                    'gaze_x_px': screen_gaze[0],
                    'gaze_y_px': screen_gaze[1],
                    'on_screen': on_screen,
                    'off_screen_direction': off_screen_direction,
                    'head_yaw': eye_info['HeadPosAnglesYPR'][0],
                    'head_pitch': eye_info['HeadPosAnglesYPR'][1],
                    'head_roll': eye_info['HeadPosAnglesYPR'][2]
                }
                
                results['gaze_data'].append(gaze_data)
                
            except Exception as e:
                print(f"Error processing frame {frame_count}: {e}")
                continue
        
        cap.release()
        
        # Process results
        print(f"\nAnalysis complete!")
        print(f"Processed {processed_frames} frames")
        print(f"Off-screen gaze detected in {off_screen_count} frames")
        
        # Generate statistics and events
        results['statistics'] = self._generate_statistics(results['gaze_data'])
        results['off_screen_events'] = self._detect_off_screen_events(results['gaze_data'])
        
        # Save results
        output_prefix = output_prefix or f"{candidate_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self._save_results(results, output_prefix)
        
        return results
    
    def _gaze_to_screen_coordinates(self, gaze_vector: np.ndarray, homtrans: HomTransform) -> Tuple[float, float]:
        """Convert gaze vector to screen pixel coordinates"""
        try:
            # Debug: print the gaze vector
            print(f"DEBUG: gaze_vector = {gaze_vector}")
            
            # Method 1: Try direct transformation using the calibration matrix
            if hasattr(homtrans, 'STransG') and homtrans.STransG is not None:
                # Get the scale factor for the gaze vector
                scale_gaze = homtrans._getScale(gaze_vector, homtrans.STransG)
                print(f"DEBUG: scale_gaze = {scale_gaze}")
                
                # Apply transformation: STransG * [scale*gaze, 1]
                gaze_homogeneous = np.vstack((scale_gaze * gaze_vector[:, None], 1))
                screen_coords_mm = (homtrans.STransG @ gaze_homogeneous)[:3]
                
                print(f"DEBUG: screen_coords_mm = {screen_coords_mm.flatten()}")
                
                # Convert from mm to pixels - need to handle the 3D coordinate properly
                screen_coords_2d = screen_coords_mm[:2].flatten()  # Take only x,y coordinates
                print(f"DEBUG: screen_coords_2d = {screen_coords_2d}")
                
                # Manual conversion from mm to pixels
                screen_gaze_px_x = screen_coords_2d[0] * homtrans.width / homtrans.width_mm
                screen_gaze_px_y = screen_coords_2d[1] * homtrans.height / homtrans.height_mm
                
                print(f"DEBUG: screen_gaze_px = [{screen_gaze_px_x}, {screen_gaze_px_y}]")
                
                return float(screen_gaze_px_x), float(screen_gaze_px_y)
            
            # Method 2: Fallback - simple projection
            else:
                print("DEBUG: Using fallback method")
                # Simple projection assuming gaze vector points from center
                # This is a simplified approach when calibration matrix is not available
                center_x = homtrans.width / 2
                center_y = homtrans.height / 2
                
                # Scale gaze vector to screen size (approximate)
                scale_factor = 500  # Adjust this based on your screen size
                gaze_x = center_x + gaze_vector[0] * scale_factor
                gaze_y = center_y - gaze_vector[1] * scale_factor  # Flip Y axis
                
                return float(gaze_x), float(gaze_y)
            
        except Exception as e:
            print(f"DEBUG: Error in gaze conversion: {e}")
            # If conversion fails, return center of screen
            return homtrans.width / 2, homtrans.height / 2
    
    def _is_gaze_on_screen(self, gaze_point: Tuple[float, float], 
                          screen_width: int, screen_height: int) -> Tuple[bool, Optional[str]]:
        """
        Check if gaze point is within screen boundaries
        
        Returns:
            (is_on_screen, off_screen_direction)
        """
        x, y = gaze_point
        
        # Add some tolerance for edge cases
        tolerance = 50  # pixels
        
        # Check boundaries
        if x < -tolerance:
            return False, "left"
        elif x > screen_width + tolerance:
            return False, "right"
        elif y < -tolerance:
            return False, "up"
        elif y > screen_height + tolerance:
            return False, "down"
        else:
            return True, None
    
    def _detect_off_screen_events(self, gaze_data: List[Dict]) -> List[Dict]:
        """Detect continuous off-screen gaze events"""
        events = []
        current_event = None
        
        for data in gaze_data:
            if not data['gaze_detected']:
                continue
                
            if not data['on_screen']:
                # Start new event or continue existing one
                if current_event is None:
                    current_event = {
                        'start_timestamp': data['timestamp'],
                        'end_timestamp': data['timestamp'],
                        'duration': 0,
                        'direction': data['off_screen_direction'],
                        'frame_count': 1
                    }
                elif current_event['direction'] == data['off_screen_direction']:
                    # Continue current event
                    current_event['end_timestamp'] = data['timestamp']
                    current_event['duration'] = current_event['end_timestamp'] - current_event['start_timestamp']
                    current_event['frame_count'] += 1
                else:
                    # Direction changed, save current event and start new one
                    if current_event['duration'] > 0.5:  # Only save events longer than 0.5 seconds
                        events.append(current_event)
                    
                    current_event = {
                        'start_timestamp': data['timestamp'],
                        'end_timestamp': data['timestamp'],
                        'duration': 0,
                        'direction': data['off_screen_direction'],
                        'frame_count': 1
                    }
            else:
                # Back on screen, end current event
                if current_event is not None:
                    current_event['end_timestamp'] = data['timestamp']
                    current_event['duration'] = current_event['end_timestamp'] - current_event['start_timestamp']
                    
                    if current_event['duration'] > 0.5:  # Only save events longer than 0.5 seconds
                        events.append(current_event)
                    
                    current_event = None
        
        # Close any remaining event
        if current_event is not None and current_event['duration'] > 0.5:
            events.append(current_event)
        
        return events
    
    def _generate_statistics(self, gaze_data: List[Dict]) -> Dict:
        """Generate analysis statistics"""
        total_frames = len(gaze_data)
        if total_frames == 0:
            return {}
        
        face_detected_frames = sum(1 for d in gaze_data if d['face_detected'])
        gaze_detected_frames = sum(1 for d in gaze_data if d['gaze_detected'])
        on_screen_frames = sum(1 for d in gaze_data if d['on_screen'] == True)
        off_screen_frames = sum(1 for d in gaze_data if d['on_screen'] == False)
        
        # Off-screen direction statistics
        direction_counts = {}
        for data in gaze_data:
            if data['off_screen_direction']:
                direction = data['off_screen_direction']
                direction_counts[direction] = direction_counts.get(direction, 0) + 1
        
        stats = {
            'total_frames': total_frames,
            'face_detected_frames': face_detected_frames,
            'gaze_detected_frames': gaze_detected_frames,
            'on_screen_frames': on_screen_frames,
            'off_screen_frames': off_screen_frames,
            'face_detection_rate': face_detected_frames / total_frames if total_frames > 0 else 0,
            'gaze_detection_rate': gaze_detected_frames / total_frames if total_frames > 0 else 0,
            'on_screen_rate': on_screen_frames / gaze_detected_frames if gaze_detected_frames > 0 else 0,
            'off_screen_rate': off_screen_frames / gaze_detected_frames if gaze_detected_frames > 0 else 0,
            'off_screen_direction_counts': direction_counts
        }
        
        return stats
    
    def _save_results(self, results: Dict, output_prefix: str):
        """Save analysis results to files"""
        
        # Save complete results as JSON
        results_file = self.results_dir / f"{output_prefix}_results.json"
        with open(results_file, 'w') as f:
            # Convert numpy arrays to lists for JSON serialization
            json_results = self._prepare_for_json(results)
            json.dump(json_results, f, indent=2)
        
        # Save gaze data as CSV
        if results['gaze_data']:
            gaze_df = pd.DataFrame(results['gaze_data'])
            gaze_csv = self.results_dir / f"{output_prefix}_gaze_data.csv"
            gaze_df.to_csv(gaze_csv, index=False)
        
        # Save off-screen events as CSV
        if results['off_screen_events']:
            events_df = pd.DataFrame(results['off_screen_events'])
            events_csv = self.results_dir / f"{output_prefix}_off_screen_events.csv"
            events_df.to_csv(events_csv, index=False)
        
        # Generate report
        self._generate_report(results, output_prefix)
        
        print(f"\nResults saved to: {self.results_dir}")
        print(f"- Complete results: {results_file}")
        if results['gaze_data']:
            print(f"- Gaze data: {gaze_csv}")
        if results['off_screen_events']:
            print(f"- Off-screen events: {events_csv}")
    
    def _prepare_for_json(self, obj):
        """Convert numpy arrays and other non-serializable objects for JSON"""
        if isinstance(obj, dict):
            return {k: self._prepare_for_json(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._prepare_for_json(item) for item in obj]
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        else:
            return obj
    
    def _generate_report(self, results: Dict, output_prefix: str):
        """Generate a summary report"""
        stats = results['statistics']
        events = results['off_screen_events']
        
        report_file = self.results_dir / f"{output_prefix}_report.txt"
        
        with open(report_file, 'w') as f:
            f.write("GAZE ANALYSIS REPORT\n")
            f.write("=" * 50 + "\n\n")
            
            f.write(f"Candidate ID: {results['candidate_id']}\n")
            f.write(f"Video: {results['video_path']}\n")
            f.write(f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("VIDEO INFORMATION\n")
            f.write("-" * 20 + "\n")
            video_info = results['video_info']
            f.write(f"Duration: {video_info['duration']:.2f} seconds\n")
            f.write(f"FPS: {video_info['fps']:.2f}\n")
            f.write(f"Total Frames: {video_info['total_frames']}\n\n")
            
            f.write("SCREEN INFORMATION\n")
            f.write("-" * 20 + "\n")
            screen_info = results['screen_info']
            f.write(f"Resolution: {screen_info['screen_width_px']}x{screen_info['screen_height_px']} pixels\n")
            f.write(f"Physical Size: {screen_info['screen_width_mm']}x{screen_info['screen_height_mm']} mm\n\n")
            
            f.write("DETECTION STATISTICS\n")
            f.write("-" * 20 + "\n")
            f.write(f"Face Detection Rate: {stats['face_detection_rate']:.2%}\n")
            f.write(f"Gaze Detection Rate: {stats['gaze_detection_rate']:.2%}\n")
            f.write(f"On-Screen Rate: {stats['on_screen_rate']:.2%}\n")
            f.write(f"Off-Screen Rate: {stats['off_screen_rate']:.2%}\n\n")
            
            f.write("OFF-SCREEN GAZE ANALYSIS\n")
            f.write("-" * 25 + "\n")
            f.write(f"Total Off-Screen Events: {len(events)}\n")
            
            if events:
                total_off_screen_time = sum(event['duration'] for event in events)
                f.write(f"Total Off-Screen Time: {total_off_screen_time:.2f} seconds\n")
                f.write(f"Average Event Duration: {total_off_screen_time/len(events):.2f} seconds\n\n")
                
                f.write("Off-Screen Direction Distribution:\n")
                for direction, count in stats['off_screen_direction_counts'].items():
                    f.write(f"  {direction.capitalize()}: {count} frames\n")
                
                f.write("\nDETAILED OFF-SCREEN EVENTS\n")
                f.write("-" * 30 + "\n")
                for i, event in enumerate(events, 1):
                    f.write(f"Event {i}:\n")
                    f.write(f"  Time: {event['start_timestamp']:.2f}s - {event['end_timestamp']:.2f}s\n")
                    f.write(f"  Duration: {event['duration']:.2f} seconds\n")
                    f.write(f"  Direction: {event['direction']}\n")
                    f.write(f"  Frame Count: {event['frame_count']}\n\n")
            
            f.write("ANALYSIS SUMMARY\n")
            f.write("-" * 20 + "\n")
            
            if stats['off_screen_rate'] > 0.1:  # More than 10% off-screen
                f.write("⚠️  HIGH OFF-SCREEN ACTIVITY DETECTED\n")
                f.write("   This may indicate potential cheating behavior.\n")
            elif stats['off_screen_rate'] > 0.05:  # 5-10% off-screen
                f.write("⚠️  MODERATE OFF-SCREEN ACTIVITY DETECTED\n")
                f.write("   This may warrant further investigation.\n")
            else:
                f.write("✅ LOW OFF-SCREEN ACTIVITY\n")
                f.write("   Normal gaze patterns observed.\n")
        
        print(f"- Analysis report: {report_file}")

def main():
    """Main function for video analysis"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Analyze interview video for gaze patterns")
    parser.add_argument("video_path", help="Path to the video file")
    parser.add_argument("candidate_id", help="Candidate ID (must have calibration data)")
    parser.add_argument("--output", "-o", help="Output prefix for result files")
    parser.add_argument("--frame-skip", "-s", type=int, default=1, 
                       help="Process every nth frame (default: 1)")
    
    args = parser.parse_args()
    
    # Initialize analyzer
    analyzer = VideoGazeAnalyzer()
    
    # Analyze video
    try:
        results = analyzer.analyze_video(
            args.video_path, 
            args.candidate_id, 
            args.output,
            args.frame_skip
        )
        
        print(f"\n✅ Analysis completed successfully!")
        print(f"Off-screen rate: {results['statistics']['off_screen_rate']:.2%}")
        print(f"Total off-screen events: {len(results['off_screen_events'])}")
        
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()