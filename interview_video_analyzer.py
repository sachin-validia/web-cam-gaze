"""
Interview Video Analyzer for Cheating Detection
==============================================

Analyzes recorded interview videos using pre-collected calibration data
to map gaze to screen coordinates and detect potential cheating behavior.
"""

import pathlib
import cv2
import numpy as np
import pandas as pd
import json
import matplotlib.pyplot as plt
import seaborn as sns
import sys
from omegaconf import OmegaConf

sys.path.append('src')
from plgaze.model_pl_gaze import GazeModel
from gaze_tracking.homtransform import HomTransform
from interview_calibration_system import InterviewCalibrationSystem
from platform_utils import get_platform_manager, optimize_config_for_platform

class InterviewVideoAnalyzer:
    """
    Analyzes interview videos for gaze patterns and potential cheating
    """
    
    def __init__(self):
        # Get platform manager
        self.platform_manager = get_platform_manager()
        
        # Initialize calibration system
        self.calib_system = InterviewCalibrationSystem()
        
        # Load gaze estimation config
        package_root = pathlib.Path(__file__).parent / 'src'
        config_path = package_root / 'plgaze/data/configs/eth-xgaze.yaml'
        self.config = OmegaConf.load(config_path)
        self.config.PACKAGE_ROOT = package_root.as_posix()
        
        # Optimize config for current platform
        self.config = optimize_config_for_platform(self.config)
        
        # Results directory
        self.analysis_dir = pathlib.Path("results/interview_analysis")
        self.analysis_dir.mkdir(exist_ok=True, parents=True)
        
        # Initialize gaze model
        self.gaze_model = GazeModel(self.config)
        
    def analyze_interview_video(self, video_path, candidate_id, output_name=None):
        """
        Analyze an interview video using the candidate's calibration data
        """
        print(f"\n=== Analyzing Interview Video for {candidate_id} ===")
        print(f"Video: {video_path}")
        
        # Load candidate calibration
        try:
            calib_data = self.calib_system.load_candidate_calibration(candidate_id)
            screen_info = calib_data['screen_info']
            transform_matrix = calib_data['transform_matrix']
            print(f"✅ Loaded calibration data for {candidate_id}")
        except FileNotFoundError as e:
            print(f"❌ Error: {e}")
            print(f"Please run calibration first for candidate {candidate_id}")
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
                        'gaze_x': gaze_vector[0],
                        'gaze_y': gaze_vector[1],
                        'gaze_z': gaze_vector[2],
                        'screen_x_mm': screen_coords_mm[0],
                        'screen_y_mm': screen_coords_mm[1],
                        'screen_x_px': screen_coords_px[0],
                        'screen_y_px': screen_coords_px[1],
                        'yaw': eye_info['HeadPosAnglesYPR'][0],
                        'pitch': eye_info['HeadPosAnglesYPR'][1],
                        'roll': eye_info['HeadPosAnglesYPR'][2],
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
                        'gaze_x': gaze_vector[0],
                        'gaze_y': gaze_vector[1],
                        'gaze_z': gaze_vector[2],
                        'screen_x_mm': np.nan,
                        'screen_y_mm': np.nan,
                        'screen_x_px': np.nan,
                        'screen_y_px': np.nan,
                        'yaw': eye_info['HeadPosAnglesYPR'][0],
                        'pitch': eye_info['HeadPosAnglesYPR'][1],
                        'roll': eye_info['HeadPosAnglesYPR'][2],
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
            json.dump(analysis_report, f, indent=2)
        
        # Generate visualizations
        self._generate_visualizations(df, output_dir, output_name, screen_info)
        
        print(f"\n✅ Analysis completed!")
        print(f"📊 Results saved to: {output_dir}")
        print(f"📈 Detection rate: {detected_count}/{frame_count} ({detected_count/frame_count*100:.1f}%)")
        
        return analysis_report
    
    def _gaze_to_screen_coords(self, gaze_vector, homtrans):
        """
        Convert gaze vector to screen coordinates using calibration
        """
        # Use the same method as in HomTransform._getGazeOnScreen
        FSgaze, Sgaze, Sgaze2 = homtrans._getGazeOnScreen(gaze_vector)
        return Sgaze[:2]  # Return x, y coordinates in mm
    
    def _mm_to_pixels(self, coords_mm, screen_info):
        """
        Convert mm coordinates to pixel coordinates
        """
        x_mm, y_mm = coords_mm
        
        # Convert to pixels based on screen dimensions
        x_px = (x_mm / screen_info['screen_width_mm']) * screen_info['screen_width_px']
        y_px = (y_mm / screen_info['screen_height_mm']) * screen_info['screen_height_px']
        
        return np.array([x_px, y_px])
    
    def _classify_gaze_zones(self, coords_px, screen_info):
        """
        Classify gaze into screen zones for cheating detection
        """
        x_px, y_px = coords_px
        width = screen_info['screen_width_px']
        height = screen_info['screen_height_px']
        
        # Check if on screen
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
    
    def _generate_analysis_report(self, df, candidate_id, video_path, screen_info):
        """
        Generate comprehensive analysis report
        """
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
        """
        Detect patterns that might indicate cheating
        """
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
        indicators['high_off_screen_rate'] = off_screen_rate > 0.3  # >30% off screen
        
        # 2. Excessive horizontal movement
        left_right_changes = (detected_df['zone_horizontal'].shift() != detected_df['zone_horizontal']).sum()
        indicators['excessive_left_right_movement'] = left_right_changes > len(detected_df) * 0.2
        
        # 3. Prolonged look away periods
        # Find consecutive off-screen sequences
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
        long_sequences = [seq for seq in off_screen_sequences if seq > 90]  # 3 seconds at 30fps
        indicators['prolonged_look_away'] = len(long_sequences) > 0
        
        # 4. Frequent zone changes
        zone_changes = (detected_df['zone_horizontal'].shift() != detected_df['zone_horizontal']).sum()
        zone_changes += (detected_df['zone_vertical'].shift() != detected_df['zone_vertical']).sum()
        indicators['frequent_zone_changes'] = zone_changes > len(detected_df) * 0.15
        
        return indicators
    
    def _generate_visualizations(self, df, output_dir, output_name, screen_info):
        """
        Generate visualization plots for gaze analysis
        """
        detected_df = df[df['detected']].copy()
        
        if len(detected_df) == 0:
            print("No detected gaze data for visualization")
            return
        
        # Create subplots
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle(f'Gaze Analysis: {output_name}', fontsize=16)
        
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

def main():
    """
    Main function for video analysis
    """
    analyzer = InterviewVideoAnalyzer()
    
    print("Interview Video Analyzer")
    print("1. Analyze video")
    print("2. List available candidates")
    print("3. Exit")
    
    choice = input("Enter choice (1-3): ").strip()
    
    if choice == "1":
        candidate_id = input("Enter candidate ID: ").strip()
        video_path = input("Enter video path: ").strip()
        
        if candidate_id and video_path:
            analyzer.analyze_interview_video(video_path, candidate_id)
        else:
            print("Invalid input")
    
    elif choice == "2":
        candidates = analyzer.calib_system.list_candidates()
        if candidates:
            print("Available candidates:")
            for i, candidate in enumerate(candidates, 1):
                print(f"{i}. {candidate}")
        else:
            print("No candidates found")
    
    elif choice == "3":
        print("Goodbye!")
    
    else:
        print("Invalid choice")

if __name__ == "__main__":
    main()