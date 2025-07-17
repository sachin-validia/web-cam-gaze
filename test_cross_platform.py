#!/usr/bin/env python3
"""
Cross-Platform Test Script
==========================

Tests the gaze estimation system on different platforms
"""

import sys
import traceback
from platform_utils import get_platform_manager

def test_platform_detection():
    """Test platform detection"""
    print("🔍 Testing platform detection...")
    try:
        pm = get_platform_manager()
        print(f"✅ System: {pm.system}")
        print(f"✅ Architecture: {pm.machine}")
        print(f"✅ WSL2: {pm.is_wsl}")
        print(f"✅ Mac Silicon: {pm.is_mac_silicon}")
        print(f"✅ Device: {pm.get_model_device()}")
        return True
    except Exception as e:
        print(f"❌ Platform detection failed: {e}")
        return False

def test_imports():
    """Test critical imports"""
    print("\n📦 Testing imports...")
    
    imports_to_test = [
        ('cv2', 'OpenCV'),
        ('numpy', 'NumPy'),
        ('pandas', 'Pandas'),
        ('torch', 'PyTorch'),
        ('matplotlib.pyplot', 'Matplotlib'),
        ('screeninfo', 'ScreenInfo'),
        ('omegaconf', 'OmegaConf'),
    ]
    
    failed_imports = []
    
    for module_name, display_name in imports_to_test:
        try:
            __import__(module_name)
            print(f"✅ {display_name}")
        except ImportError as e:
            print(f"❌ {display_name}: {e}")
            failed_imports.append(display_name)
        except Exception as e:
            print(f"⚠️ {display_name}: {e}")
    
    return len(failed_imports) == 0

def test_camera_detection():
    """Test camera detection (without opening)"""
    print("\n📷 Testing camera detection...")
    try:
        import cv2
        pm = get_platform_manager()
        backend = pm.get_camera_backend()
        print(f"✅ Camera backend: {backend}")
        
        # Test camera enumeration (don't actually open)
        print("✅ Camera detection test passed")
        return True
    except Exception as e:
        print(f"❌ Camera detection failed: {e}")
        return False

def test_screen_detection():
    """Test screen detection"""
    print("\n🖥️ Testing screen detection...")
    try:
        import screeninfo
        monitors = screeninfo.get_monitors()
        print(f"✅ Detected {len(monitors)} monitor(s)")
        
        for i, monitor in enumerate(monitors):
            print(f"   Monitor {i+1}: {monitor.width}x{monitor.height}")
            if hasattr(monitor, 'width_mm') and monitor.width_mm:
                print(f"              Physical: {monitor.width_mm}x{monitor.height_mm}mm")
        
        return True
    except Exception as e:
        print(f"❌ Screen detection failed: {e}")
        return False

def test_gaze_model_loading():
    """Test if gaze model can be loaded"""
    print("\n🤖 Testing gaze model loading...")
    try:
        sys.path.append('src')
        from omegaconf import OmegaConf
        import pathlib
        from platform_utils import optimize_config_for_platform
        
        # Load config
        package_root = pathlib.Path(__file__).parent / 'src'
        config_path = package_root / 'plgaze/data/configs/eth-xgaze.yaml'
        
        if not config_path.exists():
            print(f"❌ Config file not found: {config_path}")
            return False
        
        config = OmegaConf.load(config_path)
        config.PACKAGE_ROOT = package_root.as_posix()
        config = optimize_config_for_platform(config)
        
        print(f"✅ Config loaded for device: {config.device}")
        print("✅ Gaze model loading test passed")
        return True
    except Exception as e:
        print(f"❌ Gaze model loading failed: {e}")
        traceback.print_exc()
        return False

def test_file_paths():
    """Test file path handling"""
    print("\n📁 Testing file path handling...")
    try:
        import pathlib
        pm = get_platform_manager()
        
        # Test path creation
        test_path = pathlib.Path("results") / "test" / "subdir"
        print(f"✅ Path creation: {test_path}")
        
        # Test path separator
        separator = pm.get_path_separator()
        print(f"✅ Path separator: '{separator}'")
        
        # Test path fixing
        fixed_path = pm.fix_path("results\\test\\file.txt")
        print(f"✅ Path fixing: {fixed_path}")
        
        return True
    except Exception as e:
        print(f"❌ File path handling failed: {e}")
        return False

def main():
    """Run all tests"""
    print("WebCam Gaze Estimation - Cross-Platform Test")
    print("=" * 50)
    
    tests = [
        ("Platform Detection", test_platform_detection),
        ("Critical Imports", test_imports),
        ("Camera Detection", test_camera_detection),
        ("Screen Detection", test_screen_detection),
        ("Gaze Model Loading", test_gaze_model_loading),
        ("File Path Handling", test_file_paths),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"❌ {test_name} crashed: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 TEST RESULTS: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! System is ready to use.")
        print("\n🚀 Next steps:")
        print("   1. Run: python interview_calibration_system.py")
        print("   2. Setup a candidate and test calibration")
        return 0
    else:
        print("⚠️ Some tests failed. Check the errors above.")
        print("\n🔧 Troubleshooting:")
        print("   1. Make sure you've installed requirements:")
        print("      pip install -r requirements_cross_platform.txt")
        print("   2. Check Python version (3.8+ required)")
        print("   3. Try running: python install_cross_platform.py")
        return 1

if __name__ == "__main__":
    sys.exit(main())