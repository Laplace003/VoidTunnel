"""
Download Dialog - Xray-core download with progress
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton, QProgressBar
)
from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtGui import QFont

from src.core.xray_controller import XrayController


class DownloadDialog(QDialog):
    """Dialog for downloading Xray-core"""
    
    def __init__(self, xray_controller: XrayController, parent=None):
        super().__init__(parent)
        self.xray_controller = xray_controller
        self.setWindowTitle("Download Xray-core")
        self.setFixedSize(400, 180)
        self.setModal(True)
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        """Setup the UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)
        
        # Title
        title = QLabel("Downloading Xray-core")
        title.setFont(QFont("Inter", 14, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Status
        self.status_label = QLabel("Preparing download...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)
        
        # Progress bar
        self.progress = QProgressBar()
        self.progress.setMinimum(0)
        self.progress.setMaximum(100)
        self.progress.setValue(0)
        layout.addWidget(self.progress)
        
        # Buttons
        self.download_btn = QPushButton("Start Download")
        self.download_btn.setObjectName("primaryButton")
        self.download_btn.clicked.connect(self._start_download)
        layout.addWidget(self.download_btn)
    
    def _connect_signals(self):
        """Connect Xray controller signals"""
        self.xray_controller.download_progress.connect(self._on_progress)
        self.xray_controller.error_occurred.connect(self._on_error)
    
    def _start_download(self):
        """Start the download"""
        self.download_btn.setEnabled(False)
        self.download_btn.setText("Downloading...")
        self.status_label.setText("Downloading Xray-core...")
        
        import threading
        def download():
            success = self.xray_controller.download_xray()
            if success:
                self._on_complete()
            else:
                self._on_failed()
        
        threading.Thread(target=download, daemon=True).start()
    
    @pyqtSlot(int)
    def _on_progress(self, value: int):
        """Handle progress updates"""
        self.progress.setValue(value)
        self.status_label.setText(f"Downloading... {value}%")
    
    def _on_complete(self):
        """Handle download complete"""
        self.status_label.setText("Download complete!")
        self.download_btn.setText("Close")
        self.download_btn.setEnabled(True)
        self.download_btn.clicked.disconnect()
        self.download_btn.clicked.connect(self.accept)
        self.progress.setValue(100)
    
    def _on_failed(self):
        """Handle download failure"""
        self.status_label.setText("Download failed. Please try again.")
        self.download_btn.setText("Retry")
        self.download_btn.setEnabled(True)
        self.download_btn.clicked.disconnect()
        self.download_btn.clicked.connect(self._start_download)
    
    @pyqtSlot(str)
    def _on_error(self, error: str):
        """Handle errors"""
        self.status_label.setText(f"Error: {error}")
        self._on_failed()
