"""
Cross-platform utility functions for WebCam Gaze Estimation
==========================================================

Handles platform detection, device management, and cross-platform compatibility.
"""

import platform
import os
import sys
from pathlib import Path

class PlatformManager:
    """
    Manages platform-specific configurations and device detection
    """
    
    def __init__(self):
        self.system = platform.system().lower()
        self.machine = platform.machine().lower()
        self.is_wsl = self._detect_wsl()
        self.is_mac_silicon = self._detect_mac_silicon()
        
    def _detect_wsl(self):
        """Detect if running in WSL2"""
        if self.system == 'linux':
            try:
                with open('/proc/version', 'r') as f:
                    version_info = f.read().lower()
                return 'microsoft' in version_info or 'wsl' in version_info
            except:
                return False
        return False
    
    def _detect_mac_silicon(self):
        """Detect if running on Mac Silicon (M1/M2/M3)"""
        if self.system == 'darwin':
            return self.machine in ['arm64', 'aarch64']
        return False
    
    def get_model_device(self):
        """Get the appropriate device for ML models"""
        try:
            import torch
            
            # Mac Silicon - use MPS if available
            if self.is_mac_silicon:
                if hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                    return 'mps'
                else:
                    return 'cpu'
            
            # CUDA for NVIDIA GPUs
            if torch.cuda.is_available():
                return 'cuda'
            
            # Default to CPU
            return 'cpu'
            
        except ImportError:
            # PyTorch not available, default to CPU
            return 'cpu'
    
    def get_opencv_backend(self):
        """Get the appropriate OpenCV backend for the platform"""
        if self.system == 'darwin':
            # Mac - prefer AVFoundation
            return 'avfoundation'
        elif self.system == 'windows':
            # Windows - DirectShow or Media Foundation
            return 'dshow'
        elif self.is_wsl:
            # WSL - limited camera access
            return 'v4l2'
        else:
            # Linux - Video4Linux2
            return 'v4l2'
    
    def get_camera_indexes(self):
        """Get available camera indexes for the platform"""
        try:
            import cv2
            available_cameras = []
            
            # Test camera indexes 0-10
            for i in range(10):
                cap = cv2.VideoCapture(i)
                if cap.isOpened():
                    available_cameras.append(i)
                    cap.release()
            
            return available_cameras
            
        except ImportError:
            # OpenCV not available
            return [0]  # Default assumption
    
    def get_screen_info(self):
        """Get screen information for the platform"""
        try:
            import screeninfo
            monitors = screeninfo.get_monitors()
            
            screen_info = []
            for monitor in monitors:
                screen_info.append({
                    'width': monitor.width,
                    'height': monitor.height,
                    'x': monitor.x,
                    'y': monitor.y,
                    'is_primary': monitor.is_primary if hasattr(monitor, 'is_primary') else False
                })
            
            return screen_info
            
        except ImportError:
            # Fallback screen info
            return [{
                'width': 1920,
                'height': 1080,
                'x': 0,
                'y': 0,
                'is_primary': True
            }]
    
    def get_python_executable(self):
        """Get the current Python executable path"""
        return sys.executable
    
    def get_platform_info(self):
        """Get comprehensive platform information"""
        return {
            'system': self.system,
            'machine': self.machine,
            'platform': platform.platform(),
            'python_version': platform.python_version(),
            'is_wsl': self.is_wsl,
            'is_mac_silicon': self.is_mac_silicon,
            'device': self.get_model_device(),
            'opencv_backend': self.get_opencv_backend(),
            'available_cameras': self.get_camera_indexes(),
            'screen_info': self.get_screen_info()
        }
    
    def setup_environment(self):
        """Setup platform-specific environment variables"""
        if self.system == 'darwin' and self.is_mac_silicon:
            # Mac Silicon optimizations
            os.environ['PYTORCH_ENABLE_MPS_FALLBACK'] = '1'
        
        if self.is_wsl:
            # WSL2 display settings
            if 'DISPLAY' not in os.environ:
                os.environ['DISPLAY'] = ':0'
        
        # OpenCV optimizations
        os.environ['OPENCV_VIDEOIO_PRIORITY_MSMF'] = '0'  # Disable problematic backends
        os.environ['OPENCV_VIDEOIO_DEBUG'] = '0'  # Reduce verbose output

def get_platform_manager():
    """
    Factory function to get a PlatformManager instance
    """
    return PlatformManager()

# Convenience functions
def get_device():
    """Get the appropriate device for ML models"""
    pm = get_platform_manager()
    return pm.get_model_device()

def get_system():
    """Get the current system name"""
    pm = get_platform_manager()
    return pm.system

def is_mac_silicon():
    """Check if running on Mac Silicon"""
    pm = get_platform_manager()
    return pm.is_mac_silicon

def is_wsl():
    """Check if running in WSL2"""
    pm = get_platform_manager()
    return pm.is_wsl

def get_camera_count():
    """Get number of available cameras"""
    pm = get_platform_manager()
    return len(pm.get_camera_indexes())

def print_platform_info():
    """Print comprehensive platform information"""
    pm = get_platform_manager()
    info = pm.get_platform_info()
    
    print("="*50)
    print("Platform Information")
    print("="*50)
    print(f"System: {info['system']}")
    print(f"Architecture: {info['machine']}")
    print(f"Platform: {info['platform']}")
    print(f"Python: {info['python_version']}")
    print(f"WSL2: {info['is_wsl']}")
    print(f"Mac Silicon: {info['is_mac_silicon']}")
    print(f"ML Device: {info['device']}")
    print(f"OpenCV Backend: {info['opencv_backend']}")
    print(f"Available Cameras: {info['available_cameras']}")
    print(f"Screens: {len(info['screen_info'])}")
    print("="*50)

if __name__ == "__main__":
    # Test the platform manager
    print_platform_info()