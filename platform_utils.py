"""
Cross-platform utilities for WebCam Gaze Estimation
==================================================

Handles platform-specific differences between Mac, Windows, and Linux (WSL2)
"""

import platform
import sys
import cv2
import numpy as np
import pathlib
import os

class PlatformManager:
    """
    Manages platform-specific configurations and optimizations
    """
    
    def __init__(self):
        self.system = platform.system().lower()
        self.machine = platform.machine().lower()
        self.is_wsl = self._detect_wsl()
        self.is_mac_silicon = self._detect_mac_silicon()
        
        print(f"Platform detected: {self.system}")
        print(f"Architecture: {self.machine}")
        if self.is_wsl:
            print("Running in WSL2 environment")
        if self.is_mac_silicon:
            print("Mac Silicon (M1/M2) detected")
    
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
        """Detect if running on Mac Silicon (M1/M2)"""
        if self.system == 'darwin':
            return self.machine in ['arm64', 'aarch64']
        return False
    
    def get_camera_backend(self):
        """Get optimal camera backend for platform"""
        if self.system == 'darwin':  # Mac
            return cv2.CAP_AVFOUNDATION
        elif self.system == 'windows':
            return cv2.CAP_DSHOW
        elif self.is_wsl:
            # WSL2 needs special handling for camera access
            return cv2.CAP_V4L2
        else:  # Linux
            return cv2.CAP_V4L2
    
    def get_camera_settings(self):
        """Get platform-specific camera settings"""
        settings = {
            'width': 1280,
            'height': 960,
            'fps': 30,
            'autofocus': False
        }
        
        if self.system == 'darwin':
            # Mac-specific optimizations
            settings.update({
                'width': 1280,
                'height': 720,  # More common on Mac
                'fps': 30
            })
        elif self.system == 'windows':
            # Windows-specific optimizations
            settings.update({
                'width': 1280,
                'height': 960,
                'fps': 30
            })
        elif self.is_wsl:
            # WSL2 might have limited camera access
            settings.update({
                'width': 640,
                'height': 480,
                'fps': 15
            })
        
        return settings
    
    def setup_camera(self, camera_id=0):
        """Setup camera with platform-specific optimizations"""
        backend = self.get_camera_backend()
        settings = self.get_camera_settings()
        
        print(f"Initializing camera with backend: {backend}")
        
        try:
            cap = cv2.VideoCapture(camera_id, backend)
        except:
            print("Failed with specific backend, trying default...")
            cap = cv2.VideoCapture(camera_id)
        
        if not cap.isOpened():
            # Try alternative camera IDs
            for alt_id in [1, 2, -1]:
                print(f"Trying camera ID: {alt_id}")
                try:
                    cap = cv2.VideoCapture(alt_id, backend)
                    if cap.isOpened():
                        break
                except:
                    continue
        
        if cap.isOpened():
            # Apply platform-specific settings
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, settings['width'])
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, settings['height'])
            cap.set(cv2.CAP_PROP_FPS, settings['fps'])
            
            # Try to disable autofocus if supported
            try:
                cap.set(cv2.CAP_PROP_AUTOFOCUS, 0)
            except:
                pass
            
            # Mac-specific settings
            if self.system == 'darwin':
                try:
                    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
                except:
                    pass
            
            # Get actual settings
            actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            actual_fps = cap.get(cv2.CAP_PROP_FPS)
            
            print(f"Camera initialized: {actual_width}x{actual_height} @ {actual_fps:.1f} fps")
        else:
            print("❌ Failed to initialize camera")
            
        return cap
    
    def get_display_settings(self):
        """Get platform-specific display settings"""
        if self.is_wsl:
            # WSL2 has limited display capabilities
            return {
                'fullscreen_supported': False,
                'window_flags': cv2.WINDOW_NORMAL,
                'display_method': 'windowed'
            }
        else:
            return {
                'fullscreen_supported': True,
                'window_flags': cv2.WINDOW_NORMAL,
                'display_method': 'fullscreen'
            }
    
    def create_display_window(self, window_name, fullscreen=True):
        """Create display window with platform-specific settings"""
        display_settings = self.get_display_settings()
        
        cv2.namedWindow(window_name, display_settings['window_flags'])
        
        if fullscreen and display_settings['fullscreen_supported']:
            try:
                cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
            except:
                print("Fullscreen not supported, using windowed mode")
        
        return window_name
    
    def get_model_device(self):
        """Get optimal device for ML models"""
        if self.is_mac_silicon:
            # Mac Silicon can use MPS (Metal Performance Shaders) if available
            try:
                import torch
                if hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                    return 'mps'
            except:
                pass
        
        # Check for CUDA
        try:
            import torch
            if torch.cuda.is_available():
                return 'cuda'
        except:
            pass
        
        # Fallback to CPU
        return 'cpu'
    
    def optimize_for_platform(self, config):
        """Optimize configuration for current platform"""
        device = self.get_model_device()
        config.device = device
        
        print(f"Using device: {device}")
        
        # Platform-specific optimizations
        if self.is_wsl:
            # WSL2 optimizations - reduce processing load
            config.demo.wait_time = 10  # Slower processing
        elif self.system == 'darwin' and not self.is_mac_silicon:
            # Intel Mac optimizations
            config.demo.wait_time = 5
        elif self.is_mac_silicon:
            # Mac Silicon optimizations
            config.demo.wait_time = 1
        
        return config
    
    def get_path_separator(self):
        """Get platform-specific path separator"""
        return os.sep
    
    def fix_path(self, path_str):
        """Fix path separators for current platform"""
        if isinstance(path_str, str):
            return str(pathlib.Path(path_str))
        return path_str

# Global platform manager instance
platform_manager = PlatformManager()

def get_platform_manager():
    """Get the global platform manager instance"""
    return platform_manager

def setup_cross_platform_camera(camera_id=0):
    """Convenience function to setup camera cross-platform"""
    return platform_manager.setup_camera(camera_id)

def create_cross_platform_window(window_name, fullscreen=True):
    """Convenience function to create display window cross-platform"""
    return platform_manager.create_display_window(window_name, fullscreen)

def optimize_config_for_platform(config):
    """Convenience function to optimize config for current platform"""
    return platform_manager.optimize_for_platform(config)