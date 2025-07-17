import pathlib
import cv2
import numpy as np
import pandas as pd
import sys
from omegaconf import OmegaConf

sys.path.append('src')
from plgaze.model_pl_gaze import GazeModel

def process_single_video(video_name):
    """Process a single video and save results"""
    
    video_path = f"example-videos/{video_name}"
    print(f"Processing: {video_path}")
    
    # Load config
    package_root = pathlib.Path(__file__).parent / 'src'
    config_path = package_root / 'plgaze/data/configs/eth-xgaze.yaml'
    config = OmegaConf.load(config_path)
    config.PACKAGE_ROOT = package_root.as_posix()
    
    # Create output directory
    output_dir = pathlib.Path(f"results/batch_processing/{pathlib.Path(video_name).stem}")
    output_dir.mkdir(exist_ok=True, parents=True)
    config.demo.output_dir = str(output_dir)
    
    # Initialize model
    model = GazeModel(config)
    
    # Open video
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Error: Could not open {video_path}")
        return
    
    # Get video properties
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    print(f"Video: {width}x{height}, {fps:.1f} fps, {total_frames} frames")
    
    # Process frames
    results = []
    frame_count = 0
    detected_count = 0
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        frame_count += 1
        timestamp = frame_count / fps if fps > 0 else frame_count
        
        # Process frame
        eye_info = model.get_gaze(frame, imshow=False)
        
        if eye_info is not None:
            detected_count += 1
            row = {
                'frame_number': frame_count,
                'timestamp': timestamp,
                'gaze_x': eye_info['gaze'][0],
                'gaze_y': eye_info['gaze'][1],
                'gaze_z': eye_info['gaze'][2],
                'yaw': eye_info['HeadPosAnglesYPR'][0],
                'pitch': eye_info['HeadPosAnglesYPR'][1],
                'roll': eye_info['HeadPosAnglesYPR'][2],
                'head_x': eye_info['HeadPosInFrame'][0],
                'head_y': eye_info['HeadPosInFrame'][1]
            }
        else:
            row = {
                'frame_number': frame_count,
                'timestamp': timestamp,
                'gaze_x': np.nan,
                'gaze_y': np.nan,
                'gaze_z': np.nan,
                'yaw': np.nan,
                'pitch': np.nan,
                'roll': np.nan,
                'head_x': np.nan,
                'head_y': np.nan
            }
        
        results.append(row)
        
        # Progress
        if frame_count % 50 == 0:
            progress = (frame_count / total_frames) * 100
            print(f"Progress: {progress:.1f}% ({frame_count}/{total_frames})")
    
    cap.release()
    
    # Save results
    df = pd.DataFrame(results)
    csv_path = output_dir / f"{pathlib.Path(video_name).stem}_gaze_results.csv"
    df.to_csv(csv_path, index=False)
    
    # Save summary
    detection_rate = (detected_count / frame_count) * 100
    summary = {
        'video_name': video_name,
        'total_frames': frame_count,
        'detected_frames': detected_count,
        'detection_rate': detection_rate,
        'avg_gaze_x': df['gaze_x'].mean(),
        'avg_gaze_y': df['gaze_y'].mean(),
        'avg_gaze_z': df['gaze_z'].mean()
    }
    
    summary_path = output_dir / f"{pathlib.Path(video_name).stem}_summary.txt"
    with open(summary_path, 'w') as f:
        for key, value in summary.items():
            f.write(f"{key}: {value}\n")
    
    print(f"Completed: {detected_count}/{frame_count} frames detected ({detection_rate:.1f}%)")
    print(f"Results saved to: {output_dir}")
    
    return summary

if __name__ == "__main__":
    if len(sys.argv) > 1:
        video_name = sys.argv[1]
        process_single_video(video_name)
    else:
        print("Usage: python process_one_video.py <video_filename>")
        print("Example: python process_one_video.py test-video.mp4")