"""
Xray Controller - Manage Xray-core process lifecycle
"""

import os
import sys
import subprocess
import threading
import time
import platform
import stat
import urllib.request
import zipfile
import tarfile
from typing import Optional, Callable, List
from PyQt6.QtCore import QObject, pyqtSignal


class XrayController(QObject):
    """Controls the Xray-core process"""
    
    # Signals
    status_changed = pyqtSignal(bool)  # connected/disconnected
    log_received = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    download_progress = pyqtSignal(int)  # 0-100
    
    XRAY_VERSION = "1.8.7"
    
    def __init__(self, xray_path: str = None, config_path: str = None):
        super().__init__()
        
        self.base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        if xray_path is None:
            xray_path = os.path.join(self.base_dir, "src", "resources", "xray", "xray")
        if config_path is None:
            config_path = os.path.expanduser("~/.config/voidtunnel/config.json")
        
        self.xray_path = xray_path
        self.config_path = config_path
        self.process: Optional[subprocess.Popen] = None
        self._log_thread: Optional[threading.Thread] = None
        self._running = False
    
    @property
    def is_running(self) -> bool:
        return self.process is not None and self.process.poll() is None
    
    def check_xray_exists(self) -> bool:
        """Check if Xray-core binary exists"""
        return os.path.exists(self.xray_path) and os.access(self.xray_path, os.X_OK)
    
    def download_xray(self) -> bool:
        """Download Xray-core binary"""
        try:
            # Determine platform and architecture
            system = platform.system().lower()
            machine = platform.machine().lower()
            
            if system == "linux":
                if machine in ["x86_64", "amd64"]:
                    arch = "linux-64"
                elif machine in ["aarch64", "arm64"]:
                    arch = "linux-arm64-v8a"
                elif machine.startswith("arm"):
                    arch = "linux-arm32-v7a"
                else:
                    arch = "linux-64"
            else:
                self.error_occurred.emit(f"Unsupported platform: {system}")
                return False
            
            # Download URL
            url = f"https://github.com/XTLS/Xray-core/releases/download/v{self.XRAY_VERSION}/Xray-{arch}.zip"
            
            # Create directory
            xray_dir = os.path.dirname(self.xray_path)
            os.makedirs(xray_dir, exist_ok=True)
            
            zip_path = os.path.join(xray_dir, "xray.zip")
            
            # Download with progress
            def report_progress(block_num, block_size, total_size):
                if total_size > 0:
                    progress = int((block_num * block_size / total_size) * 100)
                    self.download_progress.emit(min(progress, 100))
            
            urllib.request.urlretrieve(url, zip_path, report_progress)
            
            # Extract
            with zipfile.ZipFile(zip_path, 'r') as zf:
                zf.extractall(xray_dir)
            
            # Make executable
            os.chmod(self.xray_path, os.stat(self.xray_path).st_mode | stat.S_IEXEC)
            
            # Clean up zip
            os.remove(zip_path)
            
            self.download_progress.emit(100)
            return True
            
        except Exception as e:
            self.error_occurred.emit(f"Failed to download Xray-core: {e}")
            return False
    
    def start(self, config_path: str = None) -> bool:
        """Start Xray-core with the given configuration"""
        if self.is_running:
            return True
        
        if config_path:
            self.config_path = config_path
        
        if not self.check_xray_exists():
            self.error_occurred.emit("Xray-core not found. Please download it first.")
            return False
        
        if not os.path.exists(self.config_path):
            self.error_occurred.emit(f"Configuration not found: {self.config_path}")
            return False
        
        try:
            # Start xray process
            self.process = subprocess.Popen(
                [self.xray_path, "run", "-c", self.config_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            
            self._running = True
            
            # Start log reading thread
            self._log_thread = threading.Thread(target=self._read_logs, daemon=True)
            self._log_thread.start()
            
            # Wait a moment to check if process started successfully
            time.sleep(0.5)
            
            if self.process.poll() is not None:
                # Process exited
                self._running = False
                self.error_occurred.emit("Xray-core failed to start")
                return False
            
            self.status_changed.emit(True)
            return True
            
        except Exception as e:
            self.error_occurred.emit(f"Failed to start Xray-core: {e}")
            return False
    
    def stop(self) -> bool:
        """Stop Xray-core"""
        if not self.is_running:
            return True
        
        try:
            self._running = False
            self.process.terminate()
            
            # Wait for process to terminate
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
            
            self.process = None
            self.status_changed.emit(False)
            return True
            
        except Exception as e:
            self.error_occurred.emit(f"Failed to stop Xray-core: {e}")
            return False
    
    def restart(self, config_path: str = None) -> bool:
        """Restart Xray-core"""
        self.stop()
        time.sleep(0.5)
        return self.start(config_path)
    
    def _read_logs(self):
        """Read logs from Xray-core process"""
        try:
            while self._running and self.process and self.process.stdout:
                line = self.process.stdout.readline()
                if line:
                    self.log_received.emit(line.strip())
                elif self.process.poll() is not None:
                    break
        except Exception as e:
            self.error_occurred.emit(f"Log reading error: {e}")
    
    def test_config(self, config_path: str) -> tuple[bool, str]:
        """Test a configuration file"""
        if not self.check_xray_exists():
            return False, "Xray-core not found"
        
        try:
            result = subprocess.run(
                [self.xray_path, "run", "-test", "-c", config_path],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                return True, "Configuration is valid"
            else:
                return False, result.stderr or result.stdout
                
        except subprocess.TimeoutExpired:
            return False, "Configuration test timed out"
        except Exception as e:
            return False, str(e)
    
    def get_version(self) -> str:
        """Get Xray-core version"""
        if not self.check_xray_exists():
            return "Not installed"
        
        try:
            result = subprocess.run(
                [self.xray_path, "version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.stdout.split('\n')[0] if result.returncode == 0 else "Unknown"
        except:
            return "Unknown"
