import pathlib
import cv2
import numpy as np
import pandas as pd
import sys
from omegaconf import OmegaConf

sys.path.append('src')
from plgaze.model_pl_gaze import GazeModel

def demo_processing():
    """Demo processing on first few frames of multiple videos"""
    
    print("=== GAZE ESTIMATION BATCH PROCESSING DEMO ===\n")
    
    # Load config
    package_root = pathlib.Path(__file__).parent / 'src'
    config_path = package_root / 'plgaze/data/configs/eth-xgaze.yaml'
    config = OmegaConf.load(config_path)
    config.PACKAGE_ROOT = package_root.as_posix()
    
    # Create output directory
    output_dir = pathlib.Path("results/batch_processing")
    output_dir.mkdir(exist_ok=True, parents=True)
    config.demo.output_dir = str(output_dir)
    
    # Initialize model
    print("Initializing gaze estimation model...")
    model = GazeModel(config)
    print("Model initialized successfully!\n")
    
    # Get video files
    video_dir = pathlib.Path("example-videos")
    video_files = []
    for ext in ['*.mp4', '*.mov']:
        video_files.extend(video_dir.glob(ext))
    
    video_files = [f for f in video_files if 'Zone.Identifier' not in str(f)][:5]  # First 5 videos
    
    print(f"Processing {len(video_files)} videos (first 10 frames each):\n")
    
    all_results = []
    
    for video_file in video_files:
        print(f"Processing: {video_file.name}")
        
        # Open video
        cap = cv2.VideoCapture(str(video_file))
        if not cap.isOpened():
            print(f"  Error: Could not open {video_file}")
            continue
        
        # Get video properties
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        print(f"  Video: {width}x{height}, {fps:.1f} fps, {total_frames} frames")
        
        # Process first 10 frames
        frame_results = []
        detected_count = 0
        
        for i in range(min(10, total_frames)):
            ret, frame = cap.read()
            if not ret:
                break
            
            # Process frame
            eye_info = model.get_gaze(frame, imshow=False)
            
            if eye_info is not None:
                detected_count += 1
                frame_results.append({
                    'video': video_file.name,
                    'frame': i+1,
                    'gaze_x': eye_info['gaze'][0],
                    'gaze_y': eye_info['gaze'][1],
                    'gaze_z': eye_info['gaze'][2],
                    'yaw': eye_info['HeadPosAnglesYPR'][0],
                    'pitch': eye_info['HeadPosAnglesYPR'][1],
                    'detected': True
                })
            else:
                frame_results.append({
                    'video': video_file.name,
                    'frame': i+1,
                    'gaze_x': np.nan,
                    'gaze_y': np.nan,
                    'gaze_z': np.nan,
                    'yaw': np.nan,
                    'pitch': np.nan,
                    'detected': False
                })
        
        cap.release()
        
        detection_rate = (detected_count / len(frame_results)) * 100
        print(f"  Detection rate: {detected_count}/{len(frame_results)} frames ({detection_rate:.1f}%)")
        
        # Save individual video results
        video_output_dir = output_dir / video_file.stem
        video_output_dir.mkdir(exist_ok=True, parents=True)
        
        df = pd.DataFrame(frame_results)
        csv_path = video_output_dir / f"{video_file.stem}_sample_results.csv"
        df.to_csv(csv_path, index=False)
        
        # Summary for this video
        summary = {
            'video_name': video_file.name,
            'sample_frames': len(frame_results),
            'detected_frames': detected_count,
            'detection_rate': detection_rate,
            'avg_gaze_x': df['gaze_x'].mean() if detected_count > 0 else np.nan,
            'avg_gaze_y': df['gaze_y'].mean() if detected_count > 0 else np.nan,
            'avg_gaze_z': df['gaze_z'].mean() if detected_count > 0 else np.nan
        }
        
        summary_path = video_output_dir / f"{video_file.stem}_sample_summary.txt"
        with open(summary_path, 'w') as f:
            f.write(f"Sample Processing Summary for {video_file.name}\\n")
            f.write("=" * 50 + "\\n")
            for key, value in summary.items():
                f.write(f"{key}: {value}\\n")
        
        all_results.extend(frame_results)
        print(f"  Results saved to: {video_output_dir}")
        print()
    
    # Overall summary
    if all_results:
        overall_df = pd.DataFrame(all_results)
        overall_csv = output_dir / "sample_processing_summary.csv"
        overall_df.to_csv(overall_csv, index=False)
        
        total_frames = len(all_results)
        total_detected = sum(1 for r in all_results if r['detected'])
        overall_detection_rate = (total_detected / total_frames) * 100
        
        print("=== OVERALL SUMMARY ===")
        print(f"Videos processed: {len(video_files)}")
        print(f"Total sample frames: {total_frames}")
        print(f"Total detected frames: {total_detected}")
        print(f"Overall detection rate: {overall_detection_rate:.1f}%")
        print(f"Results saved to: {output_dir}")
        
        # Show some example gaze vectors
        detected_frames = [r for r in all_results if r['detected']]
        if detected_frames:
            print(f"\\nSample gaze vectors (first 5):")
            for i, frame in enumerate(detected_frames[:5]):
                print(f"  {frame['video']} frame {frame['frame']}: gaze=({frame['gaze_x']:.3f}, {frame['gaze_y']:.3f}, {frame['gaze_z']:.3f})")

if __name__ == "__main__":
    demo_processing()