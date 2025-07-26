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

# Add project paths
project_root = pathlib.Path(__file__).parent.parent.parent
sys.path.append(str(project_root / 'src'))
sys.path.append(str(project_root))

from src.plgaze.model_pl_gaze import GazeModel
from src.gaze_tracking.homtransform import HomTransform
from utils.platform_utils import get_platform_manager

class InterviewCalibrationSystem:
    """
    System to collect calibration data for interview candidates
    """
    
    def __init__(self, config_path=None):
        # Get platform manager
        self.platform_manager = get_platform_manager()
        
        # Load gaze estimation config
        if config_path is None:
            project_root = pathlib.Path(__file__).parent.parent.parent
            package_root = project_root / 'src'
            config_path = package_root / 'plgaze/data/configs/eth-xgaze.yaml'
        
        self.config = OmegaConf.load(config_path)
        self.config.PACKAGE_ROOT = (project_root / 'src').as_posix()
        
        # Platform-specific optimizations
        self._optimize_config_for_platform()
        
        # Results directory
        self.calibration_dir = pathlib.Path("results/interview_calibrations")
        self.calibration_dir.mkdir(exist_ok=True, parents=True)
    
    def _optimize_config_for_platform(self):
        """Optimize config for current platform"""
        if self.platform_manager.is_mac_silicon:
            # Mac Silicon optimizations
            if hasattr(self.config, 'device'):
                self.config.device = 'mps'
        elif self.platform_manager.system == 'windows':
            # Windows optimizations
            if hasattr(self.config, 'num_workers'):
                self.config.num_workers = min(self.config.get('num_workers', 4), 2)
    
    def _setup_cross_platform_camera(self, camera_source=0):
        """Setup camera with platform-specific backend"""
        if self.platform_manager.system == 'darwin':
            cap = cv2.VideoCapture(camera_source, cv2.CAP_AVFOUNDATION)
        elif self.platform_manager.system == 'windows':
            cap = cv2.VideoCapture(camera_source, cv2.CAP_DSHOW)
        else:
            cap = cv2.VideoCapture(camera_source, cv2.CAP_V4L2)
        
        if not cap.isOpened():
            cap = cv2.VideoCapture(camera_source)
        
        return cap
    
    def _create_cross_platform_window(self, window_name, fullscreen=False):
        """Create window with platform-specific settings"""
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        if fullscreen:
            cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
        return window_name
        
    def collect_screen_info(self, candidate_id, manual_input=True):
        """
        Collect screen dimension information from candidate
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
        try:
            monitors = screeninfo.get_monitors()
        except Exception as e:
            print(f"Screen detection failed: {e}")
            monitors = []
        
        if not monitors:
            print("ERROR: No monitors detected! Falling back to manual input.")
            manual_input = True
        else:
            # Find primary monitor or use first one
            primary_monitor = None
            for monitor in monitors:
                if hasattr(monitor, 'is_primary') and monitor.is_primary:
                    primary_monitor = monitor
                    break
            
            if not primary_monitor:
                primary_monitor = monitors[0]
                print(f"No primary monitor found, using first monitor")
            else:
                print(f"Using primary monitor")
            
            # Get screen dimensions
            screen_width = primary_monitor.width
            screen_height = primary_monitor.height
            screen_width_mm = getattr(primary_monitor, 'width_mm', None)
            screen_height_mm = getattr(primary_monitor, 'height_mm', None)
            
            print(f"Detected screen resolution: {screen_width}x{screen_height} pixels")
            
            # Handle missing physical dimensions
            if not screen_width_mm or not screen_height_mm or screen_width_mm <= 0 or screen_height_mm <= 0:
                print("\nPhysical screen dimensions not detected automatically.")
                print("Applying automatic conversion (1 pixel = 0.2645833333 mm)")
                
                # Automatic conversion from pixels to mm (96 DPI assumption)
                px_to_mm = 25.4 / 96  # 96 DPI standard
                screen_width_mm = screen_width * px_to_mm
                screen_height_mm = screen_height * px_to_mm
                
                print(f"Calculated physical dimensions: {screen_width_mm:.1f}x{screen_height_mm:.1f} mm")
                print(f"(Based on {screen_width}x{screen_height} pixels at 96 DPI)")
                
                # Ask user to confirm or override
                use_auto = input("\nUse these automatically calculated dimensions? (y/n) [default: y]: ").strip().lower()
                if use_auto == 'n':
                    print("\nPlease provide physical screen size manually:")
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
                'monitor_name': getattr(primary_monitor, 'name', 'unknown')
            })
            
            print(f"\nScreen diagonal: {diagonal_inches:.1f} inches")
            print(f"DPI: {screen_info['dpi']:.1f}")
            
            manual_input = False
        
        if manual_input:
            # Fallback to manual input
            print("Manual screen information input:")
            while True:
                try:
                    screen_width = int(input("Screen width in pixels (e.g., 1920): "))
                    screen_height = int(input("Screen height in pixels (e.g., 1080): "))
                    if screen_width > 0 and screen_height > 0:
                        break
                    else:
                        print("Please enter positive numbers")
                except ValueError:
                    print("Please enter valid numbers")
            
            print("\nFor accurate gaze mapping, we need physical screen size:")
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
        cap = self._setup_cross_platform_camera(camera_source)
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
            
            window_name = self._create_cross_platform_window("Interview Calibration", fullscreen=False)
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
            
            # Save complete calibration state
            calib_state = {
                'STransG': STransG,
                'StG': homtrans.StG if hasattr(homtrans, 'StG') else None,
                'SetValues': homtrans.SetValues if hasattr(homtrans, 'SetValues') else None
            }
            
            # Save transformation data
            transform_path = self.calibration_dir / f"{candidate_id}_transform_matrix.npz"
            np.savez(transform_path, **calib_state)
            
            print(f"Calibration completed successfully!")
            print(f"Calibration data saved to: {calib_data_path}")
            print(f"Transform matrix saved to: {transform_path}")
            
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
        # Try structured directory first, then fallback to flat structure
        candidate_dir = self.calibration_dir / candidate_id
        
        # Load screen info
        info_path = candidate_dir / f"{candidate_id}_screen_info.json"
        if not info_path.exists():
            # Fallback to flat structure
            info_path = self.calibration_dir / f"{candidate_id}_screen_info.json"
            if not info_path.exists():
                raise FileNotFoundError(f"No screen info found for candidate {candidate_id}")
        
        with open(info_path, 'r') as f:
            screen_info = json.load(f)
        
        # Load transform matrix (try structured directory first)
        transform_path_npz = candidate_dir / f"{candidate_id}_transform_matrix.npz"
        transform_path_npy = candidate_dir / f"{candidate_id}_transform_matrix.npy"
        
        # Fallback to flat structure
        if not transform_path_npz.exists() and not transform_path_npy.exists():
            transform_path_npz = self.calibration_dir / f"{candidate_id}_transform_matrix.npz"
            transform_path_npy = self.calibration_dir / f"{candidate_id}_transform_matrix.npy"
        
        calib_state = {}
        if transform_path_npz.exists():
            # Load new format with complete state
            data = np.load(transform_path_npz, allow_pickle=True)
            calib_state = {
                'STransG': data['STransG'],
                'StG': data['StG'] if 'StG' in data else None,
                'SetValues': data['SetValues'] if 'SetValues' in data else None
            }
        elif transform_path_npy.exists():
            # Load old format (just STransG)
            calib_state = {
                'STransG': np.load(transform_path_npy),
                'StG': None,
                'SetValues': None
            }
        else:
            raise FileNotFoundError(f"No calibration matrix found for candidate {candidate_id}")
        
        # Load calibration data (try structured directory first)
        calib_data_path = candidate_dir / f"{candidate_id}_calibration.csv"
        if not calib_data_path.exists():
            # Fallback to flat structure
            calib_data_path = self.calibration_dir / f"{candidate_id}_calibration.csv"
        calibration_data = None
        if calib_data_path.exists():
            calibration_data = pd.read_csv(calib_data_path)
        
        return {
            'screen_info': screen_info,
            'transform_matrix': calib_state['STransG'],
            'calibration_data': calibration_data,
            'calib_state': calib_state  # Include full calibration state
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
            print(f"🎬 You can now start the interview recording")
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