import pathlib
import cv2
import numpy as np
import pandas as pd
import os
import datetime
import sys
from omegaconf import DictConfig, OmegaConf

sys.path.append('src')
from plgaze.model_pl_gaze import GazeModel
from platform_utils import get_platform_manager, optimize_config_for_platform

def process_video(video_path, output_dir):
    """Process a single video file and save results"""
    video_name = pathlib.Path(video_path).stem
    print(f"Processing video: {video_name}")
    
    # Load config
    package_root = pathlib.Path(__file__).parent / 'src'
    config_path = package_root / 'plgaze/data/configs/eth-xgaze.yaml'
    config = OmegaConf.load(config_path)
    config.PACKAGE_ROOT = package_root.as_posix()
    
    # Optimize for current platform
    config = optimize_config_for_platform(config)
    
    # Create output directory for this video
    video_output_dir = pathlib.Path(output_dir) / video_name
    video_output_dir.mkdir(exist_ok=True, parents=True)
    config.demo.output_dir = str(video_output_dir)
    
    # Initialize gaze model
    model = GazeModel(config)
    
    # Open video
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        print(f"Error: Could not open video {video_path}")
        return None
    
    # Get video properties
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    print(f"Video properties: {width}x{height}, {fps} fps, {total_frames} frames")
    
    # Process frames
    results = []
    frame_count = 0
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        frame_count += 1
        timestamp = frame_count / fps if fps > 0 else frame_count
        
        # Get gaze estimation
        eye_info = model.get_gaze(frame, imshow=False)
        
        if eye_info is not None:
            # Prepare data row
            row = {
                'frame_number': frame_count,
                'timestamp': timestamp,
                'gaze_x': eye_info['gaze'][0],
                'gaze_y': eye_info['gaze'][1],
                'gaze_z': eye_info['gaze'][2],
                'REyePos_x': eye_info['EyeRLCenterPos'][0],
                'REyePos_y': eye_info['EyeRLCenterPos'][1],
                'LEyePos_x': eye_info['EyeRLCenterPos'][2],
                'LEyePos_y': eye_info['EyeRLCenterPos'][3],
                'yaw': eye_info['HeadPosAnglesYPR'][0],
                'pitch': eye_info['HeadPosAnglesYPR'][1],
                'roll': eye_info['HeadPosAnglesYPR'][2],
                'HeadBox_xmin': eye_info['HeadPosInFrame'][0],
                'HeadBox_ymin': eye_info['HeadPosInFrame'][1],
                'RightEyeBox_xmin': eye_info['right_eye_box'][0],
                'RightEyeBox_ymin': eye_info['right_eye_box'][1],
                'LeftEyeBox_xmin': eye_info['left_eye_box'][0],
                'LeftEyeBox_ymin': eye_info['left_eye_box'][1],
                'ROpenClose': eye_info['EyeState'][0],
                'LOpenClose': eye_info['EyeState'][1]
            }
            results.append(row)
        else:
            # No face detected
            row = {
                'frame_number': frame_count,
                'timestamp': timestamp,
                'gaze_x': np.nan,
                'gaze_y': np.nan,
                'gaze_z': np.nan,
                'REyePos_x': np.nan,
                'REyePos_y': np.nan,
                'LEyePos_x': np.nan,
                'LEyePos_y': np.nan,
                'yaw': np.nan,
                'pitch': np.nan,
                'roll': np.nan,
                'HeadBox_xmin': np.nan,
                'HeadBox_ymin': np.nan,
                'RightEyeBox_xmin': np.nan,
                'RightEyeBox_ymin': np.nan,
                'LeftEyeBox_xmin': np.nan,
                'LeftEyeBox_ymin': np.nan,
                'ROpenClose': np.nan,
                'LOpenClose': np.nan
            }
            results.append(row)
        
        # Progress indicator
        if frame_count % 30 == 0:
            progress = (frame_count / total_frames) * 100
            print(f"Progress: {progress:.1f}% ({frame_count}/{total_frames} frames)")
    
    cap.release()
    
    # Save results
    if results:
        df = pd.DataFrame(results)
        csv_path = video_output_dir / f"{video_name}_gaze_results.csv"
        df.to_csv(csv_path, index=False)
        
        # Save summary statistics
        summary_stats = {
            'video_name': video_name,
            'total_frames': total_frames,
            'frames_with_detection': df['gaze_x'].notna().sum(),
            'detection_rate': (df['gaze_x'].notna().sum() / total_frames) * 100,
            'avg_gaze_x': df['gaze_x'].mean(),
            'avg_gaze_y': df['gaze_y'].mean(),
            'avg_gaze_z': df['gaze_z'].mean(),
            'avg_yaw': df['yaw'].mean(),
            'avg_pitch': df['pitch'].mean(),
        }
        
        stats_path = video_output_dir / f"{video_name}_summary.txt"
        with open(stats_path, 'w') as f:
            for key, value in summary_stats.items():
                f.write(f"{key}: {value}\n")
        
        print(f"Results saved to: {video_output_dir}")
        return summary_stats
    
    return None

def main():
    # Paths
    video_dir = pathlib.Path("example-videos")
    output_dir = pathlib.Path("results/batch_processing")
    
    # Find all video files
    video_files = []
    for ext in ['*.mp4', '*.mov']:
        video_files.extend(video_dir.glob(ext))
    
    # Filter out Zone.Identifier files
    video_files = [f for f in video_files if 'Zone.Identifier' not in str(f)]
    video_files.sort()
    
    print(f"Found {len(video_files)} video files to process")
    
    # Process each video
    all_results = []
    for video_file in video_files:
        try:
            result = process_video(video_file, output_dir)
            if result:
                all_results.append(result)
        except Exception as e:
            print(f"Error processing {video_file}: {e}")
            continue
    
    # Save overall summary
    if all_results:
        summary_df = pd.DataFrame(all_results)
        summary_path = output_dir / "overall_summary.csv"
        summary_df.to_csv(summary_path, index=False)
        print(f"\nOverall summary saved to: {summary_path}")
        
        # Print summary statistics
        print("\n=== BATCH PROCESSING SUMMARY ===")
        print(f"Total videos processed: {len(all_results)}")
        print(f"Average detection rate: {summary_df['detection_rate'].mean():.1f}%")
        print(f"Total frames processed: {summary_df['total_frames'].sum()}")
        print(f"Total frames with detection: {summary_df['frames_with_detection'].sum()}")

if __name__ == "__main__":
    main()