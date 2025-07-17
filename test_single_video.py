import pathlib
import cv2
import numpy as np
import sys
from omegaconf import OmegaConf

sys.path.append('src')
from plgaze.model_pl_gaze import GazeModel

def test_single_video():
    """Test processing on a single video file"""
    
    # Load config
    package_root = pathlib.Path(__file__).parent / 'src'
    config_path = package_root / 'plgaze/data/configs/eth-xgaze.yaml'
    config = OmegaConf.load(config_path)
    config.PACKAGE_ROOT = package_root.as_posix()
    config.demo.output_dir = str(pathlib.Path("results/test_output"))
    
    # Initialize gaze model
    model = GazeModel(config)
    print("Model initialized successfully")
    
    # Test with a single video
    video_path = "example-videos/test-video.mp4"
    cap = cv2.VideoCapture(video_path)
    
    if not cap.isOpened():
        print(f"Error: Could not open video {video_path}")
        return
    
    print(f"Video opened successfully: {video_path}")
    print(f"Video properties: {int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))}x{int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))}")
    
    # Process first 10 frames
    results = []
    for i in range(10):
        ret, frame = cap.read()
        if not ret:
            break
        
        print(f"Processing frame {i+1}/10")
        eye_info = model.get_gaze(frame, imshow=False)
        
        if eye_info is not None:
            results.append({
                'frame': i+1,
                'gaze_detected': True,
                'gaze_vector': eye_info['gaze']
            })
            print(f"  - Gaze detected: {eye_info['gaze']}")
        else:
            results.append({
                'frame': i+1,
                'gaze_detected': False,
                'gaze_vector': None
            })
            print(f"  - No gaze detected")
    
    cap.release()
    
    # Summary
    detected_frames = sum(1 for r in results if r['gaze_detected'])
    print(f"\nSummary:")
    print(f"Total frames processed: {len(results)}")
    print(f"Frames with gaze detection: {detected_frames}")
    print(f"Detection rate: {detected_frames/len(results)*100:.1f}%")
    
    return results

if __name__ == "__main__":
    test_single_video()