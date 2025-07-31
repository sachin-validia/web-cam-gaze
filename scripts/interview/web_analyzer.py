"""
Web Calibration Video Analyzer
==============================

Analyzes recorded interview videos using calibration data from the web interface.
This is a standalone analyzer that works exclusively with web calibration data.
"""

import pathlib
import cv2
import numpy as np
import pandas as pd
import json
import matplotlib.pyplot as plt
import sys
from omegaconf import OmegaConf

# Add project paths
project_root = pathlib.Path(__file__).parent.parent.parent
sys.path.append(str(project_root / 'src'))
sys.path.append(str(project_root))

from src.plgaze.model_pl_gaze import GazeModel
from src.gaze_tracking.homtransform import HomTransform
from utils.platform_utils import get_platform_manager


class WebCalibrationAnalyzer:
    """
    Analyzes interview videos using web calibration data
    """
    
    def __init__(self):
        # Get platform manager
        self.platform_manager = get_platform_manager()
        
        # Load gaze estimation config
        project_root = pathlib.Path(__file__).parent.parent.parent
        package_root = project_root / 'src'
        config_path = package_root / 'plgaze/data/configs/eth-xgaze.yaml'
        self.config = OmegaConf.load(config_path)
        self.config.PACKAGE_ROOT = package_root.as_posix()
        
        # Optimize config for current platform
        self._optimize_config_for_platform()
        
        # Results directory
        self.analysis_dir = pathlib.Path("results/web_video_analysis")
        self.analysis_dir.mkdir(exist_ok=True, parents=True)
        
        # Calibration directory (where web calibration saves data)
        self.calibration_dir = pathlib.Path("results/interview_calibrations")
        
        # Initialize gaze model
        self.gaze_model = GazeModel(self.config)
    
    def _optimize_config_for_platform(self):
        """Optimize config for current platform"""
        if self.platform_manager.is_mac_silicon:
            if hasattr(self.config, 'device'):
                self.config.device = 'mps'
        elif self.platform_manager.system == 'windows':
            if hasattr(self.config, 'num_workers'):
                self.config.num_workers = min(self.config.get('num_workers', 4), 2)
    
    def load_web_calibration(self, candidate_id):
        """
        Load calibration data saved by web interface
        """
        candidate_dir = self.calibration_dir / candidate_id
        
        # Load screen info
        screen_info_path = candidate_dir / f"{candidate_id}_screen_info.json"
        if not screen_info_path.exists():
            # Try flat structure
            screen_info_path = self.calibration_dir / f"{candidate_id}_screen_info.json"
        
        if not screen_info_path.exists():
            raise FileNotFoundError(f"No screen info found for candidate {candidate_id}")
        
        with open(screen_info_path, 'r') as f:
            screen_info = json.load(f)
        
        # Load transform matrix
        transform_path = candidate_dir / f"{candidate_id}_transform_matrix.npz"
        if not transform_path.exists():
            # Try flat structure
            transform_path = self.calibration_dir / f"{candidate_id}_transform_matrix.npz"
        
        if not transform_path.exists():
            raise FileNotFoundError(f"No calibration matrix found for candidate {candidate_id}")
        
        # Load calibration state
        data = np.load(transform_path, allow_pickle=True)
        calib_state = {
            'STransG': data['STransG'],
            'StG': data['StG'] if 'StG' in data else None,
            'SetValues': data['SetValues'] if 'SetValues' in data else None
        }
        
        # Load calibration CSV if available
        calib_csv_path = candidate_dir / f"{candidate_id}_calibration.csv"
        if not calib_csv_path.exists():
            calib_csv_path = self.calibration_dir / f"{candidate_id}_calibration.csv"
        
        calibration_data = None
        if calib_csv_path.exists():
            calibration_data = pd.read_csv(calib_csv_path)
        
        return {
            'screen_info': screen_info,
            'transform_matrix': calib_state['STransG'],
            'calibration_data': calibration_data,
            'calib_state': calib_state
        }
    
    def analyze_video(self, video_path, candidate_id, output_name=None):
        """
        Analyze a video using web calibration data
        """
        print(f"\n=== Analyzing Video with Web Calibration ===")
        print(f"Candidate: {candidate_id}")
        print(f"Video: {video_path}")
        
        # Load web calibration
        try:
            calib_data = self.load_web_calibration(candidate_id)
            screen_info = calib_data['screen_info']
            transform_matrix = calib_data['transform_matrix']
            calib_state = calib_data.get('calib_state', {})
            print(f"✅ Loaded web calibration data for {candidate_id}")
        except FileNotFoundError as e:
            print(f"❌ Error: {e}")
            print(f"Please ensure web calibration was completed for candidate {candidate_id}")
            return None
        
        # Setup output directory
        if output_name is None:
            output_name = f"{candidate_id}_{pathlib.Path(video_path).stem}"
        
        output_dir = self.analysis_dir / output_name
        output_dir.mkdir(exist_ok=True, parents=True)
        
        # Process video
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print(f"❌ Error: Could not open video {video_path}")
            return None
        
        # Get video properties
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        duration = total_frames / fps if fps > 0 else 0
        
        print(f"Video properties: {width}x{height}, {fps:.1f} fps, {total_frames} frames ({duration:.1f}s)")
        
        # Process frames
        results = []
        frame_count = 0
        detected_count = 0
        
        # Setup HomTransform for coordinate conversion
        homtrans = HomTransform(".")
        homtrans.STransG = transform_matrix
        homtrans.width = screen_info['screen_width_px']
        homtrans.height = screen_info['screen_height_px']
        homtrans.width_mm = screen_info['screen_width_mm']
        homtrans.height_mm = screen_info['screen_height_mm']
        
        # Load complete calibration state if available
        if calib_state and 'StG' in calib_state and calib_state['StG'] is not None:
            if isinstance(calib_state['StG'], (list, np.ndarray)) and len(calib_state['StG']) > 0:
                # Check if StG contains valid data
                is_valid = False
                for stg in calib_state['StG']:
                    if isinstance(stg, np.ndarray) and not np.allclose(stg, 0):
                        is_valid = True
                        break
                
                if is_valid:
                    homtrans.StG = calib_state['StG']
                    if 'SetValues' in calib_state and calib_state['SetValues'] is not None:
                        homtrans.SetValues = calib_state['SetValues']
                    print(f"✅ Loaded complete calibration state")
                else:
                    print(f"⚠️ StG contains only zeros, using fallback")
                    homtrans.StG = []
                    homtrans.SetValues = homtrans.CalTargetMM()
            else:
                print(f"⚠️ Invalid StG structure, using fallback")
                homtrans.StG = []
                homtrans.SetValues = homtrans.CalTargetMM()
        else:
            print(f"⚠️ Missing calibration state, using fallback")
            homtrans.StG = []
            homtrans.SetValues = homtrans.CalTargetMM()
        
        print("Processing frames...")
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            frame_count += 1
            timestamp = frame_count / fps if fps > 0 else frame_count
            
            # Get gaze estimation
            eye_info = self.gaze_model.get_gaze(frame, imshow=False)
            
            if eye_info is not None:
                detected_count += 1
                gaze_vector = eye_info['gaze']
                
                # Convert to screen coordinates using calibration
                try:
                    screen_coords_mm = self._gaze_to_screen_coords(gaze_vector, homtrans)
                    screen_coords_px = self._mm_to_pixels(screen_coords_mm, screen_info)
                    
                    # Determine screen zones
                    zones = self._classify_gaze_zones(screen_coords_px, screen_info)
                    
                    row = {
                        'frame_number': frame_count,
                        'timestamp': timestamp,
                        'gaze_x': float(gaze_vector[0]),
                        'gaze_y': float(gaze_vector[1]),
                        'gaze_z': float(gaze_vector[2]),
                        'screen_x_mm': float(screen_coords_mm[0]),
                        'screen_y_mm': float(screen_coords_mm[1]),
                        'screen_x_px': float(screen_coords_px[0]),
                        'screen_y_px': float(screen_coords_px[1]),
                        'yaw': float(eye_info['HeadPosAnglesYPR'][0]),
                        'pitch': float(eye_info['HeadPosAnglesYPR'][1]),
                        'roll': float(eye_info['HeadPosAnglesYPR'][2]),
                        'zone_horizontal': zones['horizontal'],
                        'zone_vertical': zones['vertical'],
                        'on_screen': zones['on_screen'],
                        'detected': True
                    }
                except Exception as e:
                    # Fallback if coordinate conversion fails
                    row = {
                        'frame_number': frame_count,
                        'timestamp': timestamp,
                        'gaze_x': float(gaze_vector[0]),
                        'gaze_y': float(gaze_vector[1]),
                        'gaze_z': float(gaze_vector[2]),
                        'screen_x_mm': np.nan,
                        'screen_y_mm': np.nan,
                        'screen_x_px': np.nan,
                        'screen_y_px': np.nan,
                        'yaw': float(eye_info['HeadPosAnglesYPR'][0]),
                        'pitch': float(eye_info['HeadPosAnglesYPR'][1]),
                        'roll': float(eye_info['HeadPosAnglesYPR'][2]),
                        'zone_horizontal': 'unknown',
                        'zone_vertical': 'unknown',
                        'on_screen': False,
                        'detected': True
                    }
            else:
                # No face detected
                row = {
                    'frame_number': frame_count,
                    'timestamp': timestamp,
                    'gaze_x': np.nan,
                    'gaze_y': np.nan,
                    'gaze_z': np.nan,
                    'screen_x_mm': np.nan,
                    'screen_y_mm': np.nan,
                    'screen_x_px': np.nan,
                    'screen_y_px': np.nan,
                    'yaw': np.nan,
                    'pitch': np.nan,
                    'roll': np.nan,
                    'zone_horizontal': 'no_face',
                    'zone_vertical': 'no_face',
                    'on_screen': False,
                    'detected': False
                }
            
            results.append(row)
            
            # Progress indicator
            if frame_count % 100 == 0:
                progress = (frame_count / total_frames) * 100
                print(f"Progress: {progress:.1f}% ({frame_count}/{total_frames})")
        
        cap.release()
        
        # Save results
        df = pd.DataFrame(results)
        csv_path = output_dir / f"{output_name}_gaze_analysis.csv"
        df.to_csv(csv_path, index=False)
        
        # Generate analysis report
        analysis_report = self._generate_analysis_report(df, candidate_id, video_path, screen_info)
        
        # Save report
        report_path = output_dir / f"{output_name}_analysis_report.json"
        with open(report_path, 'w') as f:
            json.dump(self._to_json_serializable(analysis_report), f, indent=2)
        
        # Generate visualizations
        self._generate_visualizations(df, output_dir, output_name, screen_info)
        
        print(f"\n✅ Analysis completed!")
        print(f"📊 Results saved to: {output_dir}")
        print(f"📈 Detection rate: {detected_count}/{frame_count} ({detected_count/frame_count*100:.1f}%)")
        
        return analysis_report
    
    def _gaze_to_screen_coords(self, gaze_vector, homtrans):
        """Convert gaze vector to screen coordinates using calibration"""
        FSgaze, Sgaze, Sgaze2 = homtrans._getGazeOnScreen(gaze_vector)
        if isinstance(Sgaze, np.ndarray) and Sgaze.size > 2:
            return [float(Sgaze.flat[0]), float(Sgaze.flat[1])]
        else:
            return [float(Sgaze[0]), float(Sgaze[1])]
    
    def _mm_to_pixels(self, coords_mm, screen_info):
        """Convert mm coordinates to pixel coordinates"""
        x_mm, y_mm = coords_mm
        x_px = float(x_mm / screen_info['screen_width_mm']) * screen_info['screen_width_px']
        y_px = float(y_mm / screen_info['screen_height_mm']) * screen_info['screen_height_px']
        return [x_px, y_px]
    
    def _classify_gaze_zones(self, coords_px, screen_info):
        """Classify gaze into screen zones for cheating detection"""
        x_px, y_px = coords_px
        width = screen_info['screen_width_px']
        height = screen_info['screen_height_px']
        
        on_screen = (0 <= x_px <= width) and (0 <= y_px <= height)
        
        # Horizontal zones
        if x_px < width * 0.33:
            h_zone = 'left'
        elif x_px < width * 0.67:
            h_zone = 'center'
        else:
            h_zone = 'right'
        
        # Vertical zones
        if y_px < height * 0.33:
            v_zone = 'top'
        elif y_px < height * 0.67:
            v_zone = 'middle'
        else:
            v_zone = 'bottom'
        
        return {
            'horizontal': h_zone,
            'vertical': v_zone,
            'on_screen': on_screen
        }
    
    def _to_json_serializable(self, obj):
        """Convert numpy/pandas types to JSON-serializable types"""
        if pd.isna(obj):
            return None
        elif isinstance(obj, np.bool_):
            return bool(obj)
        elif isinstance(obj, (np.integer, np.int64, np.int32, np.int16, np.int8)):
            return int(obj)
        elif isinstance(obj, (np.floating, np.float64, np.float32, np.float16)):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, dict):
            return {str(k): self._to_json_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._to_json_serializable(item) for item in obj]
        elif isinstance(obj, pd.Series):
            return self._to_json_serializable(obj.to_dict())
        return obj
    
    def _generate_analysis_report(self, df, candidate_id, video_path, screen_info):
        """Generate comprehensive analysis report"""
        total_frames = len(df)
        detected_frames = df['detected'].sum()
        on_screen_frames = df['on_screen'].sum()
        
        # Time analysis
        total_duration = df['timestamp'].max() if not df['timestamp'].empty else 0
        detection_rate = (detected_frames / total_frames) * 100
        on_screen_rate = (on_screen_frames / detected_frames) * 100 if detected_frames > 0 else 0
        
        # Zone analysis
        zone_counts = df[df['detected']].groupby(['zone_horizontal', 'zone_vertical']).size()
        
        # Suspicious behavior detection
        suspicious_indicators = self._detect_suspicious_behavior(df)
        
        report = {
            'candidate_id': candidate_id,
            'video_path': video_path,
            'analysis_timestamp': pd.Timestamp.now().isoformat(),
            'calibration_type': 'web',
            'video_stats': {
                'total_frames': total_frames,
                'total_duration_seconds': total_duration,
                'fps': total_frames / total_duration if total_duration > 0 else 0
            },
            'detection_stats': {
                'detected_frames': detected_frames,
                'detection_rate_percent': detection_rate,
                'on_screen_frames': on_screen_frames,
                'on_screen_rate_percent': on_screen_rate
            },
            'gaze_distribution': {
                'zone_counts': zone_counts.to_dict() if not zone_counts.empty else {},
                'avg_screen_x': df['screen_x_px'].mean(),
                'avg_screen_y': df['screen_y_px'].mean(),
                'gaze_std_x': df['screen_x_px'].std(),
                'gaze_std_y': df['screen_y_px'].std()
            },
            'suspicious_behavior': suspicious_indicators,
            'screen_info': screen_info
        }
        
        return report
    
    def _detect_suspicious_behavior(self, df):
        """Detect patterns that might indicate cheating"""
        detected_df = df[df['detected']].copy()
        
        indicators = {
            'high_off_screen_rate': False,
            'excessive_left_right_movement': False,
            'prolonged_look_away': False,
            'frequent_zone_changes': False
        }
        
        if len(detected_df) == 0:
            return indicators
        
        # 1. High off-screen rate
        off_screen_rate = (len(detected_df) - detected_df['on_screen'].sum()) / len(detected_df)
        indicators['high_off_screen_rate'] = off_screen_rate > 0.3
        
        # 2. Excessive horizontal movement
        left_right_changes = (detected_df['zone_horizontal'].shift() != detected_df['zone_horizontal']).sum()
        indicators['excessive_left_right_movement'] = left_right_changes > len(detected_df) * 0.2
        
        # 3. Prolonged look away periods
        off_screen_sequences = []
        current_seq = 0
        for on_screen in detected_df['on_screen']:
            if not on_screen:
                current_seq += 1
            else:
                if current_seq > 0:
                    off_screen_sequences.append(current_seq)
                current_seq = 0
        
        # Check for sequences longer than 3 seconds (assuming 30fps)
        long_sequences = [seq for seq in off_screen_sequences if seq > 90]
        indicators['prolonged_look_away'] = len(long_sequences) > 0
        
        # 4. Frequent zone changes
        zone_changes = (detected_df['zone_horizontal'].shift() != detected_df['zone_horizontal']).sum()
        zone_changes += (detected_df['zone_vertical'].shift() != detected_df['zone_vertical']).sum()
        indicators['frequent_zone_changes'] = zone_changes > len(detected_df) * 0.15
        
        return indicators
    
    def _generate_visualizations(self, df, output_dir, output_name, screen_info):
        """Generate visualization plots for gaze analysis"""
        detected_df = df[df['detected']].copy()
        
        if len(detected_df) == 0:
            print("No detected gaze data for visualization")
            return
        
        # Create subplots
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle(f'Web Calibration Gaze Analysis: {output_name}', fontsize=16)
        
        # 1. Gaze heatmap on screen
        ax1 = axes[0, 0]
        valid_coords = detected_df.dropna(subset=['screen_x_px', 'screen_y_px'])
        if len(valid_coords) > 0:
            ax1.scatter(valid_coords['screen_x_px'], valid_coords['screen_y_px'], 
                       alpha=0.6, s=10, c='blue')
            ax1.set_xlim(0, screen_info['screen_width_px'])
            ax1.set_ylim(screen_info['screen_height_px'], 0)  # Invert Y axis
            ax1.set_xlabel('Screen X (pixels)')
            ax1.set_ylabel('Screen Y (pixels)')
            ax1.set_title('Gaze Points on Screen')
            ax1.grid(True, alpha=0.3)
        
        # 2. Zone distribution
        ax2 = axes[0, 1]
        zone_counts = detected_df.groupby(['zone_horizontal', 'zone_vertical']).size()
        if not zone_counts.empty:
            zone_counts.plot(kind='bar', ax=ax2)
            ax2.set_title('Gaze Distribution by Screen Zones')
            ax2.set_xlabel('Zone (Horizontal, Vertical)')
            ax2.set_ylabel('Frame Count')
            ax2.tick_params(axis='x', rotation=45)
        
        # 3. Gaze timeline
        ax3 = axes[1, 0]
        ax3.plot(detected_df['timestamp'], detected_df['on_screen'].astype(int), 
                label='On Screen', alpha=0.7)
        ax3.set_xlabel('Time (seconds)')
        ax3.set_ylabel('On Screen (1=Yes, 0=No)')
        ax3.set_title('Gaze On/Off Screen Timeline')
        ax3.legend()
        ax3.grid(True, alpha=0.3)
        
        # 4. Head pose over time
        ax4 = axes[1, 1]
        ax4.plot(detected_df['timestamp'], detected_df['yaw'], label='Yaw', alpha=0.7)
        ax4.plot(detected_df['timestamp'], detected_df['pitch'], label='Pitch', alpha=0.7)
        ax4.set_xlabel('Time (seconds)')
        ax4.set_ylabel('Angle (degrees)')
        ax4.set_title('Head Pose Over Time')
        ax4.legend()
        ax4.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        # Save plot
        plot_path = output_dir / f"{output_name}_analysis_plots.png"
        plt.savefig(plot_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        print(f"📈 Visualizations saved to: {plot_path}")
    
    def list_candidates(self):
        """List all candidates with web calibration data"""
        candidates = []
        
        if self.calibration_dir.exists():
            for item in self.calibration_dir.iterdir():
                if item.is_dir():
                    # Check if this is a valid calibration directory
                    screen_info_path = item / f"{item.name}_screen_info.json"
                    if screen_info_path.exists():
                        candidates.append(item.name)
                else:
                    # Check flat structure files
                    if item.name.endswith("_screen_info.json"):
                        candidate_id = item.name.replace("_screen_info.json", "")
                        if candidate_id not in candidates:
                            candidates.append(candidate_id)
        
        return sorted(candidates)


def main():
    """Main function for web calibration video analysis"""
    analyzer = WebCalibrationAnalyzer()
    
    print("\n" + "="*50)
    print("Web Calibration Video Analyzer")
    print("="*50)
    print("1. Analyze video with web calibration")
    print("2. List available web calibrations")
    print("3. Batch analyze multiple videos")
    print("4. Exit")
    
    choice = input("\nEnter choice (1-4): ").strip()
    
    if choice == "1":
        candidate_id = input("Enter candidate ID: ").strip()
        video_path = input("Enter video path: ").strip()
        
        if candidate_id and video_path:
            if pathlib.Path(video_path).exists():
                analyzer.analyze_video(video_path, candidate_id)
            else:
                print(f"❌ Video file not found: {video_path}")
        else:
            print("❌ Invalid input")
    
    elif choice == "2":
        candidates = analyzer.list_candidates()
        if candidates:
            print("\nAvailable web calibrations:")
            for i, candidate in enumerate(candidates, 1):
                print(f"{i}. {candidate}")
        else:
            print("No web calibrations found")
    
    elif choice == "3":
        candidate_id = input("Enter candidate ID: ").strip()
        video_dir = input("Enter directory path containing videos: ").strip()
        
        if candidate_id and video_dir:
            video_path = pathlib.Path(video_dir)
            if video_path.exists() and video_path.is_dir():
                video_files = list(video_path.glob("*.mp4")) + list(video_path.glob("*.mov"))
                if video_files:
                    print(f"\nFound {len(video_files)} videos")
                    for video in video_files:
                        print(f"\nAnalyzing: {video.name}")
                        analyzer.analyze_video(str(video), candidate_id)
                else:
                    print("No video files found in directory")
            else:
                print("❌ Directory not found")
        else:
            print("❌ Invalid input")
    
    elif choice == "4":
        print("Goodbye!")
    
    else:
        print("❌ Invalid choice")


if __name__ == "__main__":
    main()