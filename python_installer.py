#!/usr/bin/env python3
"""
Python 3.8 Installer for WebCam Gaze Estimation
==============================================

Standalone script to ensure Python 3.8+ is available
"""

import platform
import subprocess
import sys
import pathlib
import urllib.request
import os

def get_system_info():
    """Get system information"""
    system = platform.system().lower()
    machine = platform.machine().lower()
    is_wsl = False
    is_mac_silicon = False
    
    if system == 'linux':
        try:
            with open('/proc/version', 'r') as f:
                version_info = f.read().lower()
            is_wsl = 'microsoft' in version_info or 'wsl' in version_info
        except:
            pass
    
    if system == 'darwin':
        is_mac_silicon = machine in ['arm64', 'aarch64']
    
    return system, machine, is_wsl, is_mac_silicon

def check_existing_python():
    """Check if Python 3.8+ already exists"""
    python_candidates = [
        "python3.8", "python3.9", "python3.10", "python3.11", "python3.12",
        "python3", "python"
    ]
    
    for candidate in python_candidates:
        try:
            result = subprocess.run([candidate, '--version'], capture_output=True, text=True)
            if result.returncode == 0:
                version_str = result.stdout.strip()
                version_parts = version_str.split()[1].split('.')
                major, minor = int(version_parts[0]), int(version_parts[1])
                
                if major == 3 and minor >= 8:
                    print(f"✅ Found Python {version_str} at: {candidate}")
                    return candidate
        except:
            continue
    
    return None

def install_python_with_package_manager():
    """Try to install Python using system package manager"""
    system, _, is_wsl, _ = get_system_info()
    
    if system in ['linux'] or is_wsl:
        # Try different package managers
        commands = [
            ["sudo", "apt", "update"],
            ["sudo", "apt", "install", "-y", "python3.8", "python3.8-venv", "python3.8-dev", "python3-pip"],
            ["sudo", "yum", "install", "-y", "python38", "python38-devel"],
            ["sudo", "dnf", "install", "-y", "python3.8", "python3.8-devel"],
        ]
        
        for cmd in commands:
            try:
                print(f"🔧 Trying: {' '.join(cmd)}")
                subprocess.run(cmd, check=True, capture_output=True)
                
                # Check if it worked
                python_cmd = check_existing_python()
                if python_cmd:
                    return python_cmd
            except:
                continue
    
    elif system == 'darwin':  # Mac
        try:
            # Try Homebrew
            subprocess.run(["brew", "install", "python@3.8"], check=True)
            return check_existing_python()
        except:
            pass
    
    return None

def download_and_install_python():
    """Download and install Python from python.org"""
    system, machine, is_wsl, is_mac_silicon = get_system_info()
    python_version = "3.8.18"
    
    print(f"📥 Downloading Python {python_version}...")
    
    # Determine download URL
    if system == 'windows':
        if machine in ['amd64', 'x86_64']:
            url = f"https://www.python.org/ftp/python/{python_version}/python-{python_version}-amd64.exe"
        else:
            url = f"https://www.python.org/ftp/python/{python_version}/python-{python_version}.exe"
    elif system == 'darwin':
        if is_mac_silicon:
            url = f"https://www.python.org/ftp/python/{python_version}/python-{python_version}-macos11.pkg"
        else:
            url = f"https://www.python.org/ftp/python/{python_version}/python-{python_version}-macosx10.9.pkg"
    else:
        print("❌ Direct installation not supported for this Linux distribution")
        print("💡 Please install Python 3.8+ manually using your package manager:")
        print("   Ubuntu/Debian: sudo apt install python3.8 python3.8-venv python3.8-dev")
        print("   CentOS/RHEL: sudo yum install python38 python38-devel")
        print("   Fedora: sudo dnf install python3.8 python3.8-devel")
        return None
    
    # Download
    filename = url.split('/')[-1]
    downloads_dir = pathlib.Path("python_downloads")
    downloads_dir.mkdir(exist_ok=True)
    download_path = downloads_dir / filename
    
    if not download_path.exists():
        try:
            print(f"🌐 Downloading from: {url}")
            urllib.request.urlretrieve(url, download_path)
            print(f"✅ Downloaded: {download_path}")
        except Exception as e:
            print(f"❌ Download failed: {e}")
            return None
    
    # Install
    if system == 'windows':
        return install_windows_python(download_path)
    elif system == 'darwin':
        return install_mac_python(download_path)
    
    return None

def install_windows_python(installer_path):
    """Install Python on Windows"""
    print("🔧 Installing Python on Windows...")
    
    install_dir = pathlib.Path.cwd() / "python38"
    
    cmd = [
        str(installer_path),
        "/quiet",
        f"InstallAllUsers=0",
        f"TargetDir={install_dir}",
        "PrependPath=0",
        "Include_pip=1",
        "Include_dev=1"
    ]
    
    try:
        subprocess.run(cmd, check=True)
        python_exe = install_dir / "python.exe"
        
        if python_exe.exists():
            print(f"✅ Python installed to: {install_dir}")
            return str(python_exe)
        else:
            print("❌ Installation verification failed")
            return None
    except Exception as e:
        print(f"❌ Installation failed: {e}")
        return None

def install_mac_python(installer_path):
    """Install Python on Mac"""
    print("🔧 Installing Python on Mac...")
    print("🔐 This requires administrator privileges")
    
    try:
        cmd = ["sudo", "installer", "-pkg", str(installer_path), "-target", "/"]
        subprocess.run(cmd, check=True)
        
        # Find installed Python
        python_candidates = [
            "/Library/Frameworks/Python.framework/Versions/3.8/bin/python3",
            "/usr/local/bin/python3.8",
            "/opt/homebrew/bin/python3.8"
        ]
        
        for candidate in python_candidates:
            if pathlib.Path(candidate).exists():
                print(f"✅ Python installed: {candidate}")
                return candidate
        
        print("❌ Installation verification failed")
        return None
        
    except Exception as e:
        print(f"❌ Installation failed: {e}")
        return None

def main():
    """Main function"""
    print("Python 3.8+ Installer for WebCam Gaze Estimation")
    print("=" * 50)
    
    system, machine, is_wsl, is_mac_silicon = get_system_info()
    print(f"🔍 System: {system} ({machine})")
    if is_wsl:
        print("🔍 WSL2 detected")
    if is_mac_silicon:
        print("🔍 Mac Silicon (M1/M2) detected")
    
    # Check existing Python
    existing_python = check_existing_python()
    if existing_python:
        print(f"✅ Python 3.8+ already available: {existing_python}")
        return 0
    
    print("❌ No compatible Python found. Installing Python 3.8...")
    
    # Try package manager first
    python_cmd = install_python_with_package_manager()
    if python_cmd:
        print(f"✅ Python installed via package manager: {python_cmd}")
        return 0
    
    # Try direct download
    python_cmd = download_and_install_python()
    if python_cmd:
        print(f"✅ Python installed: {python_cmd}")
        return 0
    
    print("❌ Failed to install Python automatically")
    print("\n💡 Manual installation options:")
    print("   • Windows: Download from python.org")
    print("   • Mac: Use Homebrew (brew install python@3.8)")
    print("   • Linux: Use package manager (apt install python3.8)")
    
    return 1

if __name__ == "__main__":
    sys.exit(main())