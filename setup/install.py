#!/usr/bin/env python3
"""
Cross-platform installation script for WebCam Gaze Estimation
============================================================

Handles installation on Mac (Intel/Apple Silicon), Windows, and Linux (WSL2)
"""

import platform
import subprocess
import sys
import os
import pathlib
import urllib.request
import shutil
import tempfile

class CrossPlatformInstaller:
    """
    Handles cross-platform installation and setup
    """
    
    def __init__(self):
        self.system = platform.system().lower()
        self.machine = platform.machine().lower()
        self.is_wsl = self._detect_wsl()
        self.is_mac_silicon = self._detect_mac_silicon()
        self.python_cmd = None  # Will be set after ensuring Python 3.8+
        self.python_version = "3.8.18"  # Target Python version
        self.python_dir = None  # Will store custom Python installation path
        
        print(f"🔍 Detected platform: {self.system}")
        print(f"🔍 Architecture: {self.machine}")
        if self.is_wsl:
            print("🔍 WSL2 environment detected")
        if self.is_mac_silicon:
            print("🔍 Mac Silicon (M1/M2) detected")
    
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
    
    def _get_python_command(self):
        """Get the correct Python command for the platform"""
        for cmd in ['python3', 'python']:
            try:
                result = subprocess.run([cmd, '--version'], capture_output=True, text=True)
                if result.returncode == 0 and 'Python 3' in result.stdout:
                    return cmd
            except FileNotFoundError:
                continue
        return 'python3'  # Default fallback
    
    def get_python_download_url(self):
        """Get the appropriate Python download URL for the platform"""
        version = self.python_version
        
        if self.system == 'windows':
            if self.machine in ['amd64', 'x86_64']:
                return f"https://www.python.org/ftp/python/{version}/python-{version}-amd64.exe"
            else:
                return f"https://www.python.org/ftp/python/{version}/python-{version}.exe"
        
        elif self.system == 'darwin':  # Mac
            if self.is_mac_silicon:
                return f"https://www.python.org/ftp/python/{version}/python-{version}-macos11.pkg"
            else:
                return f"https://www.python.org/ftp/python/{version}/python-{version}-macosx10.9.pkg"
        
        else:  # Linux/WSL2 - will use package manager or compile from source
            return f"https://www.python.org/ftp/python/{version}/Python-{version}.tgz"
    
    def download_python(self):
        """Download Python installer for the platform"""
        print(f"📥 Downloading Python {self.python_version}...")
        
        url = self.get_python_download_url()
        filename = url.split('/')[-1]
        
        # Create downloads directory
        downloads_dir = pathlib.Path("python_downloads")
        downloads_dir.mkdir(exist_ok=True)
        
        download_path = downloads_dir / filename
        
        if download_path.exists():
            print(f"✅ Python installer already downloaded: {download_path}")
            return download_path
        
        try:
            print(f"🌐 Downloading from: {url}")
            urllib.request.urlretrieve(url, download_path)
            print(f"✅ Downloaded Python installer: {download_path}")
            return download_path
        except Exception as e:
            print(f"❌ Failed to download Python: {e}")
            return None
    
    def install_python_windows(self, installer_path):
        """Install Python on Windows"""
        print("🔧 Installing Python on Windows...")
        
        # Install to a local directory
        install_dir = pathlib.Path.cwd() / "python38"
        
        try:
            # Run installer silently
            cmd = [
                str(installer_path),
                "/quiet",
                f"InstallAllUsers=0",
                f"TargetDir={install_dir}",
                "PrependPath=0",
                "Shortcuts=0",
                "Include_doc=0",
                "Include_debug=0",
                "Include_dev=1",
                "Include_exe=1",
                "Include_launcher=0",
                "InstallLauncherAllUsers=0",
                "Include_lib=1",
                "Include_pip=1",
                "Include_symbols=0",
                "Include_tcltk=1",
                "Include_test=0",
                "Include_tools=0"
            ]
            
            subprocess.run(cmd, check=True)
            
            # Set python command
            self.python_dir = install_dir
            self.python_cmd = str(install_dir / "python.exe")
            
            print(f"✅ Python installed to: {install_dir}")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install Python: {e}")
            return False
    
    def install_python_mac(self, installer_path):
        """Install Python on Mac"""
        print("🔧 Installing Python on Mac...")
        
        try:
            # Run the .pkg installer
            cmd = ["sudo", "installer", "-pkg", str(installer_path), "-target", "/"]
            
            print("🔐 Administrative privileges required for Python installation")
            subprocess.run(cmd, check=True)
            
            # Find the installed Python
            python_framework = f"/Library/Frameworks/Python.framework/Versions/{self.python_version[:3]}/bin/python3"
            
            if pathlib.Path(python_framework).exists():
                self.python_cmd = python_framework
                print(f"✅ Python installed: {python_framework}")
                return True
            else:
                print("❌ Python installation verification failed")
                return False
                
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install Python: {e}")
            return False
    
    def install_python_linux(self):
        """Install Python on Linux using package manager or compilation"""
        print("🔧 Installing Python on Linux...")
        
        # Try package managers first
        package_managers = [
            # Ubuntu/Debian
            ["apt", "update"],
            ["apt", "install", "-y", "python3.8", "python3.8-venv", "python3.8-dev", "python3-pip"],
            # CentOS/RHEL/Fedora
            ["yum", "install", "-y", "python38", "python38-devel"],
            ["dnf", "install", "-y", "python3.8", "python3.8-devel"],
            # Arch Linux
            ["pacman", "-S", "--noconfirm", "python"],
        ]
        
        for cmd in package_managers:
            try:
                print(f"🔧 Trying: {' '.join(cmd)}")
                subprocess.run(["sudo"] + cmd, check=True, capture_output=True)
                
                # Check if python3.8 is now available
                for python_candidate in ["python3.8", "python3", "python"]:
                    try:
                        result = subprocess.run([python_candidate, "--version"], capture_output=True, text=True)
                        if "Python 3.8" in result.stdout:
                            self.python_cmd = python_candidate
                            print(f"✅ Python 3.8 installed via package manager: {python_candidate}")
                            return True
                    except:
                        continue
                        
            except subprocess.CalledProcessError:
                continue
        
        print("⚠️ Package manager installation failed, will compile from source...")
        return self.compile_python_from_source()
    
    def compile_python_from_source(self):
        """Compile Python from source as last resort"""
        print("🔨 Compiling Python from source...")
        
        # Download source
        source_url = self.get_python_download_url()
        source_filename = source_url.split('/')[-1]
        source_path = pathlib.Path("python_downloads") / source_filename
        
        if not source_path.exists():
            try:
                urllib.request.urlretrieve(source_url, source_path)
            except Exception as e:
                print(f"❌ Failed to download Python source: {e}")
                return False
        
        # Extract and compile
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                # Extract
                subprocess.run(["tar", "-xzf", str(source_path), "-C", temp_dir], check=True)
                
                # Find extracted directory
                extracted_dir = pathlib.Path(temp_dir) / f"Python-{self.python_version}"
                
                # Configure, compile, and install locally
                install_dir = pathlib.Path.cwd() / "python38"
                
                os.chdir(extracted_dir)
                
                subprocess.run(["./configure", f"--prefix={install_dir}", "--enable-optimizations"], check=True)
                subprocess.run(["make", "-j4"], check=True)
                subprocess.run(["make", "altinstall"], check=True)
                
                # Set python command
                self.python_dir = install_dir
                self.python_cmd = str(install_dir / "bin" / "python3.8")
                
                print(f"✅ Python compiled and installed to: {install_dir}")
                return True
                
            except Exception as e:
                print(f"❌ Failed to compile Python from source: {e}")
                return False
    
    def ensure_python_38(self):
        """Ensure Python 3.8+ is available, install if necessary"""
        print("🔍 Checking for Python 3.8+...")
        
        # First, try to find existing Python 3.8+
        python_candidates = ["python3.8", "python3.9", "python3.10", "python3.11", "python3.12", "python3", "python"]
        
        for candidate in python_candidates:
            try:
                result = subprocess.run([candidate, '--version'], capture_output=True, text=True)
                if result.returncode == 0:
                    version_str = result.stdout.strip()
                    version_parts = version_str.split()[1].split('.')
                    major, minor = int(version_parts[0]), int(version_parts[1])
                    
                    if major == 3 and minor >= 8:
                        self.python_cmd = candidate
                        print(f"✅ Found compatible Python: {version_str}")
                        return True
            except:
                continue
        
        print("❌ No compatible Python found. Installing Python 3.8...")
        
        # Download Python installer
        installer_path = self.download_python()
        if not installer_path:
            return False
        
        # Install based on platform
        if self.system == 'windows':
            return self.install_python_windows(installer_path)
        elif self.system == 'darwin':
            return self.install_python_mac(installer_path)
        else:  # Linux/WSL2
            return self.install_python_linux()
    
    def check_python_version(self):
        """Check if Python version is compatible (after ensuring 3.8+)"""
        if not self.python_cmd:
            return False
            
        try:
            result = subprocess.run([self.python_cmd, '--version'], capture_output=True, text=True)
            version_str = result.stdout.strip()
            print(f"🐍 Using Python: {version_str}")
            
            # Extract version numbers
            version_parts = version_str.split()[1].split('.')
            major, minor = int(version_parts[0]), int(version_parts[1])
            
            if major < 3 or (major == 3 and minor < 8):
                print("❌ Python 3.8+ is required")
                return False
            else:
                print("✅ Python version compatible")
                return True
        except Exception as e:
            print(f"❌ Error checking Python version: {e}")
            return False
    
    def create_virtual_environment(self):
        """Create virtual environment"""
        venv_path = pathlib.Path("venv")
        
        if venv_path.exists():
            print("📁 Virtual environment already exists")
            return True
        
        print("📦 Creating virtual environment...")
        try:
            subprocess.run([self.python_cmd, '-m', 'venv', 'venv'], check=True)
            print("✅ Virtual environment created")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to create virtual environment: {e}")
            return False
    
    def get_activation_command(self):
        """Get the command to activate virtual environment"""
        if self.system == 'windows':
            return 'venv\\Scripts\\activate'
        else:
            return 'source venv/bin/activate'
    
    def get_pip_command(self):
        """Get the pip command for the platform"""
        if self.system == 'windows':
            return 'venv\\Scripts\\pip'
        else:
            return 'venv/bin/pip'
    
    def get_python_executable(self):
        """Get the Python executable path for virtual environment"""
        if self.system == 'windows':
            return 'venv\\Scripts\\python'
        else:
            return 'venv/bin/python'
    
    def install_base_requirements(self):
        """Install base requirements"""
        print("📦 Installing base requirements...")
        pip_cmd = self.get_pip_command()
        
        # Upgrade pip first
        try:
            subprocess.run([pip_cmd, 'install', '--upgrade', 'pip'], check=True)
            print("✅ Pip upgraded")
        except subprocess.CalledProcessError as e:
            print(f"⚠️ Warning: Could not upgrade pip: {e}")
        
        # Install requirements - check setup directory
        req_files = [
            "setup/requirements_cross_platform.txt",
            "setup/requirements_pl_gaze.txt",
            "setup/requirements.txt"
        ]
        
        req_file = None
        for rf in req_files:
            if pathlib.Path(rf).exists():
                req_file = rf
                break
        
        if req_file:
            try:
                subprocess.run([pip_cmd, 'install', '-r', req_file], check=True)
                print(f"✅ Requirements installed from {req_file}")
                
                # Install web-calibration backend requirements
                backend_req_file = "web-calibration/backend/requirements.txt"
                if pathlib.Path(backend_req_file).exists():
                    print("📦 Installing web-calibration backend requirements...")
                    try:
                        subprocess.run([pip_cmd, 'install', '-r', backend_req_file], check=True)
                        print("✅ Web-calibration backend requirements installed")
                    except subprocess.CalledProcessError as e:
                        print(f"⚠️ Warning: Failed to install some backend requirements: {e}")
                
                return True
            except subprocess.CalledProcessError as e:
                print(f"❌ Failed to install requirements: {e}")
                return False
        else:
            print("❌ No requirements file found")
            return False
    
    def install_platform_specific_packages(self):
        """Install platform-specific packages"""
        pip_cmd = self.get_pip_command()
        
        print(f"🔧 Installing platform-specific packages for {self.system}...")
        
        packages = []
        
        if self.system == 'darwin':  # Mac
            if self.is_mac_silicon:
                print("🍎 Installing Mac Silicon optimizations...")
                # Mac Silicon specific packages
                packages.extend([
                    'torch',  # Will use MPS if available
                    'torchvision',
                ])
            else:
                print("🍎 Installing Intel Mac packages...")
                packages.extend([
                    'torch==1.10.0',
                    'torchvision==0.11.1',
                ])
        
        elif self.system == 'windows':
            print("🪟 Installing Windows packages...")
            packages.extend([
                'torch==1.10.0+cpu',
                'torchvision==0.11.1+cpu',
                '--extra-index-url', 'https://download.pytorch.org/whl/cpu'
            ])
        
        elif self.is_wsl:
            print("🐧 Installing WSL2 packages...")
            packages.extend([
                'torch==1.10.0+cpu',
                'torchvision==0.11.1+cpu',
                '--extra-index-url', 'https://download.pytorch.org/whl/cpu'
            ])
        
        else:  # Regular Linux
            print("🐧 Installing Linux packages...")
            packages.extend([
                'torch==1.10.0',
                'torchvision==0.11.1',
            ])
        
        # Install additional packages
        additional_packages = [
            'screeninfo',
            'keyboard',
        ]
        
        if self.is_wsl:
            # WSL2 might need additional packages for GUI
            additional_packages.extend([
                'tkinter',  # For GUI fallbacks
            ])
        
        all_packages = packages + additional_packages
        
        if all_packages:
            try:
                subprocess.run([pip_cmd, 'install'] + all_packages, check=True)
                print("✅ Platform-specific packages installed")
                return True
            except subprocess.CalledProcessError as e:
                print(f"⚠️ Warning: Some platform-specific packages failed to install: {e}")
                return False
        
        return True
    
    def check_mysql_installed(self):
        """Check if MySQL is installed and accessible"""
        mysql_commands = ['mysql', 'mysql.exe'] if self.system == 'windows' else ['mysql']
        
        for cmd in mysql_commands:
            try:
                result = subprocess.run([cmd, '--version'], capture_output=True, text=True)
                if result.returncode == 0:
                    print(f"✅ MySQL found: {result.stdout.strip()}")
                    return True
            except FileNotFoundError:
                continue
        
        return False
    
    def install_mysql(self):
        """Install MySQL based on platform"""
        print("🗄️ Installing MySQL...")
        
        if self.system == 'darwin':  # Mac
            # Check if Homebrew is installed
            try:
                subprocess.run(['brew', '--version'], capture_output=True, check=True)
                print("🍺 Installing MySQL via Homebrew...")
                subprocess.run(['brew', 'install', 'mysql'], check=True)
                subprocess.run(['brew', 'services', 'start', 'mysql'], check=True)
                print("✅ MySQL installed and started")
                return True
            except:
                print("❌ Homebrew not found. Please install MySQL manually:")
                print("   Visit: https://dev.mysql.com/downloads/mysql/")
                return False
        
        elif self.system == 'windows':
            print("⚠️ Please install MySQL manually on Windows:")
            print("   1. Download MySQL Community Server from:")
            print("      https://dev.mysql.com/downloads/mysql/")
            print("   2. Run the installer and follow the setup wizard")
            print("   3. Remember your root password!")
            return False
        
        else:  # Linux/WSL
            print("🐧 Installing MySQL via package manager...")
            try:
                subprocess.run(['sudo', 'apt', 'update'], check=True)
                subprocess.run(['sudo', 'apt', 'install', '-y', 'mysql-server'], check=True)
                subprocess.run(['sudo', 'systemctl', 'start', 'mysql'], check=True)
                print("✅ MySQL installed and started")
                return True
            except:
                print("❌ Failed to install MySQL. Please install manually:")
                print("   sudo apt update && sudo apt install mysql-server")
                return False
    
    def setup_database(self):
        """Setup MySQL database for web-calibration"""
        print("🗄️ Setting up calibration database...")
        
        # Check if MySQL is installed
        if not self.check_mysql_installed():
            if not self.install_mysql():
                print("⚠️ MySQL not installed. Please install it manually and re-run setup.")
                return False
        
        # Create .env file if it doesn't exist
        env_file = pathlib.Path("web-calibration/backend/.env")
        if not env_file.exists():
            print("📝 Creating .env configuration file...")
            env_content = """# Database Configuration
DB_HOST=localhost
DB_PORT=3306
DB_USER=calibration_user
DB_PASSWORD=calibration_password
DB_NAME=calibration_db

# API Configuration
SECRET_KEY=your-secret-key-here-change-in-production
"""
            env_file.parent.mkdir(parents=True, exist_ok=True)
            with open(env_file, 'w') as f:
                f.write(env_content)
            print(f"✅ Created {env_file}")
        
        # Create database setup script
        db_setup_script = """
CREATE DATABASE IF NOT EXISTS calibration_db;
CREATE USER IF NOT EXISTS 'calibration_user'@'localhost' IDENTIFIED BY 'calibration_password';
GRANT ALL PRIVILEGES ON calibration_db.* TO 'calibration_user'@'localhost';
FLUSH PRIVILEGES;
"""
        
        setup_sql_file = pathlib.Path("setup_calibration_db.sql")
        with open(setup_sql_file, 'w') as f:
            f.write(db_setup_script)
        
        print("⚠️ Please run the following command to setup the database:")
        print(f"   mysql -u root -p < {setup_sql_file}")
        print("   Then run: mysql -u root -p calibration_db < web-calibration/backend/db/schema.sql")
        print("\n📝 Database credentials (update .env if needed):")
        print("   User: calibration_user")
        print("   Password: calibration_password")
        print("   Database: calibration_db")
        
        return True
    
    def check_nodejs_installed(self):
        """Check if Node.js is installed"""
        try:
            result = subprocess.run(['node', '--version'], capture_output=True, text=True)
            if result.returncode == 0:
                version = result.stdout.strip()
                print(f"✅ Node.js found: {version}")
                
                # Check npm as well
                npm_result = subprocess.run(['npm', '--version'], capture_output=True, text=True)
                if npm_result.returncode == 0:
                    print(f"✅ npm found: v{npm_result.stdout.strip()}")
                    return True
        except FileNotFoundError:
            pass
        
        return False
    
    def install_nodejs(self):
        """Install Node.js based on platform"""
        print("📦 Installing Node.js...")
        
        if self.system == 'darwin':  # Mac
            try:
                subprocess.run(['brew', '--version'], capture_output=True, check=True)
                print("🍺 Installing Node.js via Homebrew...")
                subprocess.run(['brew', 'install', 'node'], check=True)
                print("✅ Node.js installed")
                return True
            except:
                print("❌ Homebrew not found. Please install Node.js manually:")
                print("   Visit: https://nodejs.org/")
                return False
        
        elif self.system == 'windows':
            print("⚠️ Please install Node.js manually on Windows:")
            print("   1. Download Node.js from: https://nodejs.org/")
            print("   2. Run the installer (includes npm)")
            print("   3. Restart your terminal after installation")
            return False
        
        else:  # Linux/WSL
            print("🐧 Installing Node.js via NodeSource...")
            try:
                # Install Node.js 18.x LTS
                subprocess.run(['curl', '-fsSL', 'https://deb.nodesource.com/setup_18.x', '|', 'sudo', '-E', 'bash', '-'], shell=True, check=True)
                subprocess.run(['sudo', 'apt', 'install', '-y', 'nodejs'], check=True)
                print("✅ Node.js installed")
                return True
            except:
                print("❌ Failed to install Node.js. Please install manually:")
                print("   Visit: https://nodejs.org/")
                return False
    
    def setup_frontend(self):
        """Setup web-calibration frontend"""
        print("🌐 Setting up web-calibration frontend...")
        
        # Check if Node.js is installed
        if not self.check_nodejs_installed():
            if not self.install_nodejs():
                print("⚠️ Node.js not installed. Please install it manually and re-run setup.")
                return False
        
        # Navigate to frontend directory and install dependencies
        frontend_dir = pathlib.Path("web-calibration/frontend")
        if not frontend_dir.exists():
            print(f"❌ Frontend directory not found: {frontend_dir}")
            return False
        
        try:
            print("📦 Installing frontend dependencies...")
            # Change to frontend directory and run npm install
            original_dir = os.getcwd()
            os.chdir(frontend_dir)
            
            subprocess.run(['npm', 'install'], check=True)
            print("✅ Frontend dependencies installed")
            
            # Return to original directory
            os.chdir(original_dir)
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install frontend dependencies: {e}")
            os.chdir(original_dir)  # Make sure to return to original directory
            return False
    
    def test_installation(self):
        """Test if installation is working"""
        print("🧪 Testing installation...")
        
        python_cmd = self.get_python_executable()
        
        test_script = '''
import sys
sys.path.append(".")

import cv2
import numpy as np
import torch
import pandas as pd
import matplotlib.pyplot as plt
import screeninfo
from utils.platform_utils import get_platform_manager

# Test web-calibration backend imports
try:
    import fastapi
    import uvicorn
    import mysql.connector
    print("✅ Web-calibration backend imports successful")
except ImportError as e:
    print(f"⚠️ Web-calibration backend import failed: {e}")

pm = get_platform_manager()
print(f"Platform manager initialized: {pm.system}")
print(f"Device: {pm.get_model_device()}")

# Test camera detection (don't actually open)
try:
    monitors = screeninfo.get_monitors()
    print(f"Detected {len(monitors)} monitor(s)")
except Exception as e:
    print(f"Monitor detection: {e}")

print("✅ All core imports successful!")
'''
        
        try:
            subprocess.run([python_cmd, '-c', test_script], check=True)
            print("✅ Installation test passed")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Installation test failed: {e}")
            return False
    
    def create_startup_scripts(self):
        """Create platform-specific startup scripts"""
        print("📝 Creating startup scripts...")
        
        if self.system == 'windows':
            # Windows batch file
            script_content = f'''@echo off
echo Starting WebCam Gaze Estimation System...
call venv\\Scripts\\activate
echo Virtual environment activated
echo.
echo Available commands:
echo   === Core System ===
echo   python scripts/interview/calibration.py - Setup interview calibration
echo   python scripts/interview/analyzer.py - Analyze interview videos
echo.
echo   === Web Calibration System ===
echo   cd web-calibration/backend && python app.py - Start web calibration backend
echo   cd web-calibration/frontend && npm run dev - Start web calibration frontend
echo.
echo   === Database Management ===
echo   mysql -u root -p calibration_db - Access calibration database
echo.
cmd /k
'''
            with open('start_windows.bat', 'w') as f:
                f.write(script_content)
            print("✅ Created start_windows.bat")
            
            # Create web-calibration start scripts
            backend_script = '''@echo off
echo Starting Web Calibration Backend...
cd web-calibration\\backend
call ..\\..\\venv\\Scripts\\activate
python app.py
'''
            with open('start_backend_windows.bat', 'w') as f:
                f.write(backend_script)
            print("✅ Created start_backend_windows.bat")
            
            frontend_script = '''@echo off
echo Starting Web Calibration Frontend...
cd web-calibration\\frontend
npm run dev
'''
            with open('start_frontend_windows.bat', 'w') as f:
                f.write(frontend_script)
            print("✅ Created start_frontend_windows.bat")
        
        else:
            # Unix shell script
            script_content = f'''#!/bin/bash
echo "Starting WebCam Gaze Estimation System..."
source venv/bin/activate
echo "Virtual environment activated"
echo ""
echo "Available commands:"
echo "  === Core System ==="
echo "  python scripts/interview/calibration.py - Setup interview calibration"
echo "  python scripts/interview/analyzer.py - Analyze interview videos"
echo ""
echo "  === Web Calibration System ==="
echo "  cd web-calibration/backend && python app.py - Start web calibration backend"
echo "  cd web-calibration/frontend && npm run dev - Start web calibration frontend"
echo ""
echo "  === Database Management ==="
echo "  mysql -u root -p calibration_db - Access calibration database"
echo ""
exec bash
'''
            script_name = 'start_unix.sh'
            with open(script_name, 'w') as f:
                f.write(script_content)
            
            # Make executable
            os.chmod(script_name, 0o755)
            print(f"✅ Created {script_name}")
            
            # Create web-calibration start scripts
            backend_script = '''#!/bin/bash
echo "Starting Web Calibration Backend..."
cd web-calibration/backend
source ../../venv/bin/activate
python app.py
'''
            with open('start_backend.sh', 'w') as f:
                f.write(backend_script)
            os.chmod('start_backend.sh', 0o755)
            print("✅ Created start_backend.sh")
            
            frontend_script = '''#!/bin/bash
echo "Starting Web Calibration Frontend..."
cd web-calibration/frontend
npm run dev
'''
            with open('start_frontend.sh', 'w') as f:
                f.write(frontend_script)
            os.chmod('start_frontend.sh', 0o755)
            print("✅ Created start_frontend.sh")
    
    def show_next_steps(self):
        """Show next steps for the user"""
        print("\n" + "="*60)
        print("🎉 INSTALLATION COMPLETE!")
        print("="*60)
        
        activation_cmd = self.get_activation_command()
        
        if self.system == 'windows':
            print("🚀 To get started on Windows:")
            print("   1. Double-click 'start_windows.bat'")
            print("   OR")
            print(f"   1. Run: {activation_cmd}")
            print("   2. Run: python scripts/interview/calibration.py")
            
            print("\n🌐 To start Web Calibration System:")
            print("   Backend: Double-click 'start_backend_windows.bat'")
            print("   Frontend: Double-click 'start_frontend_windows.bat'")
        else:
            print("🚀 To get started on Mac/Linux:")
            print("   1. Run: ./start_unix.sh")
            print("   OR")
            print(f"   1. Run: {activation_cmd}")
            print("   2. Run: python scripts/interview/calibration.py")
            
            print("\n🌐 To start Web Calibration System:")
            print("   Backend: ./start_backend.sh")
            print("   Frontend: ./start_frontend.sh")
        
        print("\n📚 Workflow Options:")
        print("   === Option 1: Command Line (Original) ===")
        print("   1. Setup calibration: python scripts/interview/calibration.py")
        print("   2. Analyze interview: python scripts/interview/analyzer.py")
        
        print("\n   === Option 2: Web Interface (New) ===")
        print("   1. Start backend: cd web-calibration/backend && python app.py")
        print("   2. Start frontend: cd web-calibration/frontend && npm run dev")
        print("   3. Open browser: http://localhost:3000")
        
        print("\n🗄️ Database:")
        print("   • MySQL database: calibration_db")
        print("   • User: calibration_user")
        print("   • Password: calibration_password")
        print("   • Update credentials in: web-calibration/backend/.env")
        
        if self.is_wsl:
            print("\n⚠️  WSL2 Notes:")
            print("   • Camera access may be limited")
            print("   • GUI applications need X11 forwarding")
            print("   • Consider using Windows Subsystem for GUI")
        
        if self.is_mac_silicon:
            print("\n🍎 Mac Silicon Notes:")
            print("   • Using optimized MPS acceleration when available")
            print("   • Some packages may need Rosetta 2 compatibility")
        
        if self.python_dir:
            print(f"\n🐍 Custom Python Installation:")
            print(f"   • Python installed to: {self.python_dir}")
            print(f"   • Python executable: {self.python_cmd}")
        
        print("\n📁 Results will be saved to:")
        print("   • Command line: results/interview_calibrations/")
        print("   • Web interface: Stored in MySQL database")
        print("   • Analysis results: results/interview_analysis/")
        
        print("\n📖 Documentation:")
        print("   • Setup guide: Docs/LOCAL_SETUP_GUIDE.md")
        print("   • Backend API: web-calibration/backend/README.md")
        print("   • Frontend: web-calibration/frontend/README.md")
    
    def run_installation(self):
        """Run the complete installation process"""
        print("🚀 Starting WebCam Gaze Estimation installation...\n")
        
        # Ensure Python 3.8+ is available
        if not self.ensure_python_38():
            print("❌ Failed to ensure Python 3.8+ is available")
            return False
        
        # Check Python version
        if not self.check_python_version():
            return False
        
        # Create virtual environment
        if not self.create_virtual_environment():
            return False
        
        # Install base requirements
        if not self.install_base_requirements():
            return False
        
        # Install platform-specific packages
        if not self.install_platform_specific_packages():
            print("⚠️ Warning: Some platform-specific packages failed, but continuing...")
        
        # Setup database for web-calibration
        print("\n🗄️ Database Setup")
        if not self.setup_database():
            print("⚠️ Warning: Database setup incomplete, but continuing...")
        
        # Setup frontend for web-calibration
        print("\n🌐 Frontend Setup")
        if not self.setup_frontend():
            print("⚠️ Warning: Frontend setup incomplete, but continuing...")
        
        # Test installation
        if not self.test_installation():
            print("⚠️ Warning: Installation test failed, but files are installed")
        
        # Create startup scripts
        self.create_startup_scripts()
        
        # Show next steps
        self.show_next_steps()
        
        return True

def main():
    """Main installation function"""
    installer = CrossPlatformInstaller()
    
    print("WebCam Gaze Estimation - Cross-Platform Installation")
    print("="*55)
    
    success = installer.run_installation()
    
    if success:
        print("\n✅ Installation completed successfully!")
    else:
        print("\n❌ Installation encountered errors")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())