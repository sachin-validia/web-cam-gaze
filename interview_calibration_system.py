"""
Interview Calibration System for Cheating Detection
====================================================

This system collects screen dimensions and calibration data for interview candidates
to enable gaze tracking analysis on recorded videos.
"""

import pathlib
import cv2
import numpy as np
import pandas as pd
import json
import datetime
import sys
from omegaconf import OmegaConf
import screeninfo

sys.path.append('src')
from plgaze.model_pl_gaze import GazeModel
from gaze_tracking.homtransform import HomTransform
from platform_utils import get_platform_manager, setup_cross_platform_camera, create_cross_platform_window, optimize_config_for_platform

class InterviewCalibrationSystem:
    """
    System to collect calibration data for interview candidates
    """
    
    def __init__(self, config_path=None):
        # Get platform manager
        self.platform_manager = get_platform_manager()
        
        # Load gaze estimation config
        if config_path is None:
            package_root = pathlib.Path(__file__).parent / 'src'
            config_path = package_root / 'plgaze/data/configs/eth-xgaze.yaml'
        
        self.config = OmegaConf.load(config_path)
        self.config.PACKAGE_ROOT = (pathlib.Path(__file__).parent / 'src').as_posix()
        
        # Optimize config for current platform
        self.config = optimize_config_for_platform(self.config)
        
        # Results directory
        self.calibration_dir = pathlib.Path("results/interview_calibrations")
        self.calibration_dir.mkdir(exist_ok=True, parents=True)
        
    def collect_screen_info(self, candidate_id, manual_input=True):
        """
        Collect screen dimension information from candidate
        
        Methods:
        1. Automatic detection using screeninfo
        2. Manual input for missing information
        """
        
        print(f"\n=== Screen Information Collection for Candidate {candidate_id} ===")
        
        # Check if screen info already exists
        info_path = self.calibration_dir / f"{candidate_id}_screen_info.json"
        if info_path.exists():
            print(f"Found existing screen info for candidate {candidate_id}")
            with open(info_path, 'r') as f:
                existing_info = json.load(f)
            
            print(f"Screen: {existing_info.get('screen_width_px')}x{existing_info.get('screen_height_px')} pixels")
            print(f"Physical: {existing_info.get('screen_width_mm')}x{existing_info.get('screen_height_mm')} mm")
            
            use_existing = input("Use existing screen info? (y/n) [default: y]: ").strip().lower()
            if use_existing != 'n':
                return existing_info
        
        screen_info = {
            'candidate_id': candidate_id,
            'timestamp': datetime.datetime.now().isoformat(),
            'collection_method': 'automatic'
        }
        
        # Automatically detect screen information
        print("Automatically detecting screen information...")
        monitors = screeninfo.get_monitors()
        
        if not monitors:
            print("ERROR: No monitors detected! Falling back to manual input.")
            manual_input = True
        else:
            # Find primary monitor or use first one
            primary_monitor = None
            for monitor in monitors:
                if monitor.is_primary:
                    primary_monitor = monitor
                    break
            
            if not primary_monitor:
                primary_monitor = monitors[0]
                print(f"No primary monitor found, using: {primary_monitor.name}")
            else:
                print(f"Using primary monitor: {primary_monitor.name}")
            
            # Get screen dimensions
            screen_width = primary_monitor.width
            screen_height = primary_monitor.height
            screen_width_mm = primary_monitor.width_mm if hasattr(primary_monitor, 'width_mm') else None
            screen_height_mm = primary_monitor.height_mm if hasattr(primary_monitor, 'height_mm') else None
            
            print(f"Detected screen resolution: {screen_width}x{screen_height} pixels")
            
            # Handle missing physical dimensions
            if not screen_width_mm or not screen_height_mm or screen_width_mm <= 0 or screen_height_mm <= 0:
                print("\nPhysical screen dimensions not detected automatically.")
                print("Please provide physical screen size for accurate gaze mapping:")
                print("(You can find this in display settings or measure with a ruler)")
                
                while True:
                    try:
                        screen_width_mm = float(input("Screen width in mm (e.g., 345): "))
                        screen_height_mm = float(input("Screen height in mm (e.g., 194): "))
                        if screen_width_mm > 0 and screen_height_mm > 0:
                            break
                        else:
                            print("Please enter positive numbers")
                    except ValueError:
                        print("Please enter valid numbers")
            else:
                print(f"Detected physical dimensions: {screen_width_mm:.1f}x{screen_height_mm:.1f} mm")
            
            # Collect setup information
            print("\nPlease provide additional setup information:")
            camera_position = input("Camera position (webcam/external/laptop) [default: laptop]: ").strip()
            if not camera_position:
                camera_position = "laptop"
                
            distance_estimate = input("Estimated distance from screen in cm (e.g., 60) [default: 60]: ").strip()
            if not distance_estimate:
                distance_estimate = "60"
            
            # Calculate additional metrics
            diagonal_mm = (screen_width_mm**2 + screen_height_mm**2)**0.5
            diagonal_inches = diagonal_mm / 25.4
            
            screen_info.update({
                'screen_width_px': screen_width,
                'screen_height_px': screen_height,
                'screen_width_mm': screen_width_mm,
                'screen_height_mm': screen_height_mm,
                'camera_position': camera_position,
                'distance_cm': distance_estimate,
                'dpi': (screen_width / (screen_width_mm / 25.4)) if screen_width_mm > 0 else None,
                'diagonal_inches': diagonal_inches,
                'monitor_name': primary_monitor.name if not manual_input else 'unknown'
            })
            
            print(f"\nScreen diagonal: {diagonal_inches:.1f} inches")
            print(f"DPI: {screen_info['dpi']:.1f}")
            
            manual_input = False
        
        if manual_input:
            # Fallback to manual input
            # Collect screen dimensions
            while True:
                try:
                    screen_width = int(input("Screen width in pixels (e.g., 1920): "))
                    screen_height = int(input("Screen height in pixels (e.g., 1080): "))
                    break
                except ValueError:
                    print("Please enter valid numbers")
            
            # Collect physical dimensions
            print("\nFor accurate gaze mapping, we need physical screen size:")
            print("(You can find this in display settings or measure with a ruler)")
            
            while True:
                try:
                    screen_width_mm = float(input("Screen width in mm (e.g., 345): "))
                    screen_height_mm = float(input("Screen height in mm (e.g., 194): "))
                    break
                except ValueError:
                    print("Please enter valid numbers")
            
            # Collect setup information
            camera_position = input("Camera position (webcam/external/laptop): ").strip()
            distance_estimate = input("Estimated distance from screen in cm (e.g., 60): ").strip()
            
            screen_info.update({
                'screen_width_px': screen_width,
                'screen_height_px': screen_height,
                'screen_width_mm': screen_width_mm,
                'screen_height_mm': screen_height_mm,
                'camera_position': camera_position,
                'distance_cm': distance_estimate,
                'dpi': (screen_width / (screen_width_mm / 25.4)) if screen_width_mm > 0 else None,
                'collection_method': 'manual'
            })
        
        # Save screen info
        info_path = self.calibration_dir / f"{candidate_id}_screen_info.json"
        with open(info_path, 'w') as f:
            json.dump(screen_info, f, indent=2)
        
        print(f"Screen information saved to: {info_path}")
        return screen_info
    
    def run_calibration_sequence(self, candidate_id, camera_source=0):
        """
        Run calibration sequence before interview
        """
        print(f"\n=== Calibration Sequence for Candidate {candidate_id} ===")
        print("Please look at the calibration targets that will appear on your screen")
        print("Keep your head still and follow the targets with your eyes only")
        print("Press 's' to start calibration, 'q' to quit")
        
        # Load screen info for this candidate
        info_path = self.calibration_dir / f"{candidate_id}_screen_info.json"
        if info_path.exists():
            with open(info_path, 'r') as f:
                screen_info = json.load(f)
        else:
            raise RuntimeError(f"No screen info found for candidate {candidate_id}. Please run setup first.")
        
        # Initialize models
        model = GazeModel(self.config)
        homtrans = HomTransform(".")
        
        # Override the screen dimensions from collected info
        homtrans.width = int(screen_info.get('screen_width_px', 1920))
        homtrans.height = int(screen_info.get('screen_height_px', 1080))
        homtrans.width_mm = float(screen_info.get('screen_width_mm', 345))
        homtrans.height_mm = float(screen_info.get('screen_height_mm', 194))
        
        # Setup camera with cross-platform support
        cap = setup_cross_platform_camera(camera_source)
        if not cap.isOpened():
            raise RuntimeError(f"Could not open camera {camera_source} on {self.platform_manager.system}")
        
        # Wait for user to be ready
        while True:
            ret, frame = cap.read()
            if not ret:
                continue
                
            cv2.putText(frame, f"Calibration for {candidate_id}", (50, 50), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.putText(frame, "Press 's' to start calibration", (50, 100), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.putText(frame, "Press 'q' to quit", (50, 130), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            window_name = create_cross_platform_window("Interview Calibration", fullscreen=False)
            cv2.imshow(window_name, frame)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('s'):
                break
            elif key == ord('q'):
                cap.release()
                cv2.destroyAllWindows()
                return None
        
        # Run calibration
        print("Starting calibration...")
        try:
            # Test if face detection is working first
            ret, test_frame = cap.read()
            if ret:
                test_eye_info = model.get_gaze(test_frame, imshow=False)
                if test_eye_info is None or test_eye_info.get('gaze') is None:
                    raise Exception("Face detection or gaze estimation not working. Please ensure your face is visible to the camera.")
            
            STransG = homtrans.calibrate(model, cap, sfm=False)
            
            # Save calibration data with candidate ID
            calib_data_path = self.calibration_dir / f"{candidate_id}_calibration.csv"
            if pathlib.Path("results/Calibration.csv").exists():
                # Copy calibration data with candidate ID
                calib_df = pd.read_csv("results/Calibration.csv")
                calib_df['candidate_id'] = candidate_id
                calib_df.to_csv(calib_data_path, index=False)
            
            # Save transformation matrix
            transform_path = self.calibration_dir / f"{candidate_id}_transform_matrix.npy"
            np.save(transform_path, STransG)
            
            print(f"Calibration completed successfully!")
            print(f"Calibration data saved to: {calib_data_path}")
            print(f"Transform matrix saved to: {transform_path}")
            
            # Skip validation for now - calibration is complete
            # # Quick validation
            # print("Running quick validation...")
            # homtrans.RunGazeOnScreen(model, cap, sfm=False)
            
        except Exception as e:
            print(f"Calibration failed: {e}")
            STransG = None
        finally:
            cap.release()
            cv2.destroyAllWindows()
        
        return STransG
    
    def load_candidate_calibration(self, candidate_id):
        """
        Load existing calibration data for a candidate
        """
        # Load screen info
        info_path = self.calibration_dir / f"{candidate_id}_screen_info.json"
        if not info_path.exists():
            raise FileNotFoundError(f"No screen info found for candidate {candidate_id}")
        
        with open(info_path, 'r') as f:
            screen_info = json.load(f)
        
        # Load transform matrix
        transform_path = self.calibration_dir / f"{candidate_id}_transform_matrix.npy"
        if not transform_path.exists():
            raise FileNotFoundError(f"No calibration matrix found for candidate {candidate_id}")
        
        transform_matrix = np.load(transform_path)
        
        # Load calibration data
        calib_data_path = self.calibration_dir / f"{candidate_id}_calibration.csv"
        calibration_data = None
        if calib_data_path.exists():
            calibration_data = pd.read_csv(calib_data_path)
        
        return {
            'screen_info': screen_info,
            'transform_matrix': transform_matrix,
            'calibration_data': calibration_data
        }
    
    def setup_candidate(self, candidate_id, camera_source=0):
        """
        Complete setup process for a candidate
        """
        print(f"\n{'='*60}")
        print(f"INTERVIEW SETUP FOR CANDIDATE: {candidate_id}")
        print(f"{'='*60}")
        
        # Step 1: Collect screen information
        screen_info = self.collect_screen_info(candidate_id)
        
        # Step 2: Run calibration
        transform_matrix = self.run_calibration_sequence(candidate_id, camera_source)
        
        if transform_matrix is not None:
            print(f"\n✅ Setup completed successfully for {candidate_id}!")
            print(f"📁 Calibration files saved in: {self.calibration_dir}")
            print(f"🎥 You can now start the interview recording")
            print(f"📊 Use analyze_interview_video() to process the recorded video")
        else:
            print(f"\n❌ Setup failed for {candidate_id}")
            return False
        
        return True
    
    def list_candidates(self):
        """
        List all candidates with calibration data
        """
        candidates = set()
        for file in self.calibration_dir.glob("*_screen_info.json"):
            candidate_id = file.stem.replace("_screen_info", "")
            candidates.add(candidate_id)
        
        return sorted(list(candidates))

def main():
    """
    Main function for calibration system
    """
    system = InterviewCalibrationSystem()
    
    print("Interview Calibration System")
    print("1. Setup new candidate")
    print("2. List existing candidates")
    print("3. Exit")
    
    choice = input("Enter choice (1-3): ").strip()
    
    if choice == "1":
        candidate_id = input("Enter candidate ID: ").strip()
        if candidate_id:
            system.setup_candidate(candidate_id)
        else:
            print("Invalid candidate ID")
    
    elif choice == "2":
        candidates = system.list_candidates()
        if candidates:
            print("Existing candidates:")
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