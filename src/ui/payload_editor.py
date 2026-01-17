"""
Payload Editor - NetMod-style HTTP header/payload injection
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QLineEdit, QTextEdit, QComboBox, QCheckBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QGroupBox, QFormLayout
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from src.core.profile_manager import ProfileManager
from src.core.protocol_parser import ServerProfile


class PayloadEditor(QWidget):
    """Widget for editing HTTP payload/headers (NetMod feature)"""
    
    def __init__(self, profile_manager: ProfileManager):
        super().__init__()
        self.profile_manager = profile_manager
        self.current_profile: ServerProfile = None
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 16, 24, 16)
        layout.setSpacing(16)
        
        # Header
        header = QHBoxLayout()
        
        title = QLabel("Payload Editor")
        title.setFont(QFont("Inter", 18, QFont.Weight.Bold))
        header.addWidget(title)
        
        header.addStretch()
        
        # Profile selector
        header.addWidget(QLabel("Profile:"))
        self.profile_combo = QComboBox()
        self.profile_combo.setMinimumWidth(200)
        self.profile_combo.currentIndexChanged.connect(self._on_profile_changed)
        header.addWidget(self.profile_combo)
        
        layout.addLayout(header)
        
        # Enable switch
        enable_layout = QHBoxLayout()
        self.enable_check = QCheckBox("Enable Payload Injection")
        self.enable_check.setFont(QFont("Inter", 12))
        self.enable_check.toggled.connect(self._on_enable_toggled)
        enable_layout.addWidget(self.enable_check)
        enable_layout.addStretch()
        layout.addLayout(enable_layout)
        
        # Payload section
        self.payload_group = QGroupBox("HTTP Payload")
        payload_layout = QVBoxLayout(self.payload_group)
        
        # Method and Host
        method_layout = QHBoxLayout()
        
        method_layout.addWidget(QLabel("Method:"))
        self.method_combo = QComboBox()
        self.method_combo.addItems(["GET", "POST", "CONNECT", "HEAD", "PUT", "DELETE"])
        self.method_combo.setFixedWidth(100)
        method_layout.addWidget(self.method_combo)
        
        method_layout.addWidget(QLabel("Host:"))
        self.host_input = QLineEdit()
        self.host_input.setPlaceholderText("example.com")
        method_layout.addWidget(self.host_input, 1)
        
        payload_layout.addLayout(method_layout)
        
        # Path
        path_layout = QHBoxLayout()
        path_layout.addWidget(QLabel("Path:"))
        self.path_input = QLineEdit()
        self.path_input.setPlaceholderText("/")
        path_layout.addWidget(self.path_input, 1)
        payload_layout.addLayout(path_layout)
        
        layout.addWidget(self.payload_group)
        
        # Custom Headers section
        self.headers_group = QGroupBox("Custom Headers")
        headers_layout = QVBoxLayout(self.headers_group)
        
        # Headers table
        self.headers_table = QTableWidget()
        self.headers_table.setColumnCount(2)
        self.headers_table.setHorizontalHeaderLabels(["Header Name", "Value"])
        self.headers_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.headers_table.setMinimumHeight(150)
        headers_layout.addWidget(self.headers_table)
        
        # Add/Remove buttons
        header_btns = QHBoxLayout()
        
        add_header_btn = QPushButton("+ Add Header")
        add_header_btn.clicked.connect(self._add_header_row)
        header_btns.addWidget(add_header_btn)
        
        remove_header_btn = QPushButton("- Remove Selected")
        remove_header_btn.clicked.connect(self._remove_header_row)
        header_btns.addWidget(remove_header_btn)
        
        header_btns.addStretch()
        
        # Common headers dropdown
        header_btns.addWidget(QLabel("Quick Add:"))
        self.common_headers_combo = QComboBox()
        self.common_headers_combo.addItems([
            "Select...",
            "User-Agent",
            "Accept",
            "Accept-Language",
            "Connection",
            "Upgrade",
            "X-Forwarded-For",
            "X-Real-IP",
            "Cache-Control",
            "Pragma"
        ])
        self.common_headers_combo.currentTextChanged.connect(self._add_common_header)
        header_btns.addWidget(self.common_headers_combo)
        
        headers_layout.addLayout(header_btns)
        
        layout.addWidget(self.headers_group)
        
        # Payload Preview
        preview_group = QGroupBox("Payload Preview")
        preview_layout = QVBoxLayout(preview_group)
        
        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setFont(QFont("Consolas", 11))
        self.preview_text.setMaximumHeight(120)
        self.preview_text.setStyleSheet("""
            QTextEdit {
                background-color: #0d1117;
                border: 1px solid #21262d;
                border-radius: 6px;
            }
        """)
        preview_layout.addWidget(self.preview_text)
        
        # Generate preview button
        preview_btn = QPushButton("🔄 Generate Preview")
        preview_btn.clicked.connect(self._generate_preview)
        preview_layout.addWidget(preview_btn)
        
        layout.addWidget(preview_group)
        
        # Save button
        save_layout = QHBoxLayout()
        save_layout.addStretch()
        
        save_btn = QPushButton("💾 Save Changes")
        save_btn.setObjectName("primaryButton")
        save_btn.setMinimumWidth(150)
        save_btn.clicked.connect(self._save_changes)
        save_layout.addWidget(save_btn)
        
        layout.addLayout(save_layout)
        
        # Load profiles
        self._load_profiles()
        
        # Initially disable payload editing
        self._on_enable_toggled(False)
        
        # Add some default headers
        self._add_header_row()
    
    def _load_profiles(self):
        """Load profiles into combo box"""
        self.profile_combo.clear()
        profiles = self.profile_manager.get_all()
        
        for profile in profiles:
            self.profile_combo.addItem(
                f"{profile.name} ({profile.protocol})",
                profile
            )
        
        if profiles:
            self._on_profile_changed(0)
    
    def _on_profile_changed(self, index: int):
        """Handle profile selection change"""
        if index >= 0:
            self.current_profile = self.profile_combo.currentData()
            if self.current_profile:
                self._load_profile_payload()
    
    def _load_profile_payload(self):
        """Load payload settings from current profile"""
        if not self.current_profile:
            return
        
        self.enable_check.setChecked(self.current_profile.payload_enabled)
        
        # Parse payload data if exists
        if self.current_profile.payload_data:
            lines = self.current_profile.payload_data.split('\n')
            if lines:
                # Parse first line (method, path, version)
                first_line = lines[0].split()
                if len(first_line) >= 2:
                    method = first_line[0]
                    path = first_line[1]
                    
                    idx = self.method_combo.findText(method)
                    if idx >= 0:
                        self.method_combo.setCurrentIndex(idx)
                    self.path_input.setText(path)
        
        # Load custom headers
        self.headers_table.setRowCount(0)
        if self.current_profile.custom_headers:
            for name, value in self.current_profile.custom_headers.items():
                row = self.headers_table.rowCount()
                self.headers_table.insertRow(row)
                self.headers_table.setItem(row, 0, QTableWidgetItem(name))
                self.headers_table.setItem(row, 1, QTableWidgetItem(value))
        
        if self.current_profile.ws_host:
            self.host_input.setText(self.current_profile.ws_host)
        elif self.current_profile.address:
            self.host_input.setText(self.current_profile.address)
        
        self._generate_preview()
    
    def _on_enable_toggled(self, enabled: bool):
        """Handle enable checkbox toggle"""
        self.payload_group.setEnabled(enabled)
        self.headers_group.setEnabled(enabled)
    
    def _add_header_row(self):
        """Add a new header row"""
        row = self.headers_table.rowCount()
        self.headers_table.insertRow(row)
        self.headers_table.setItem(row, 0, QTableWidgetItem(""))
        self.headers_table.setItem(row, 1, QTableWidgetItem(""))
    
    def _remove_header_row(self):
        """Remove selected header row"""
        current_row = self.headers_table.currentRow()
        if current_row >= 0:
            self.headers_table.removeRow(current_row)
    
    def _add_common_header(self, text: str):
        """Add a common header with default value"""
        if text == "Select...":
            return
        
        defaults = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Connection": "keep-alive",
            "Upgrade": "websocket",
            "X-Forwarded-For": "127.0.0.1",
            "X-Real-IP": "127.0.0.1",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache"
        }
        
        row = self.headers_table.rowCount()
        self.headers_table.insertRow(row)
        self.headers_table.setItem(row, 0, QTableWidgetItem(text))
        self.headers_table.setItem(row, 1, QTableWidgetItem(defaults.get(text, "")))
        
        self.common_headers_combo.setCurrentIndex(0)
    
    def _generate_preview(self):
        """Generate payload preview"""
        method = self.method_combo.currentText()
        host = self.host_input.text() or "example.com"
        path = self.path_input.text() or "/"
        
        # Build payload
        lines = [
            f"{method} {path} HTTP/1.1",
            f"Host: {host}",
        ]
        
        # Add custom headers
        for row in range(self.headers_table.rowCount()):
            name_item = self.headers_table.item(row, 0)
            value_item = self.headers_table.item(row, 1)
            
            if name_item and value_item:
                name = name_item.text().strip()
                value = value_item.text().strip()
                if name and value:
                    lines.append(f"{name}: {value}")
        
        lines.append("")
        lines.append("")
        
        self.preview_text.setText('\n'.join(lines))
    
    def _save_changes(self):
        """Save payload changes to profile"""
        if not self.current_profile:
            QMessageBox.warning(self, "Warning", "No profile selected")
            return
        
        self.current_profile.payload_enabled = self.enable_check.isChecked()
        self.current_profile.ws_host = self.host_input.text()
        self.current_profile.ws_path = self.path_input.text() or "/"
        
        # Save custom headers
        headers = {}
        for row in range(self.headers_table.rowCount()):
            name_item = self.headers_table.item(row, 0)
            value_item = self.headers_table.item(row, 1)
            
            if name_item and value_item:
                name = name_item.text().strip()
                value = value_item.text().strip()
                if name:
                    headers[name] = value
        
        self.current_profile.custom_headers = headers
        
        # Generate and save payload data
        self._generate_preview()
        self.current_profile.payload_data = self.preview_text.toPlainText()
        
        # Update profile
        self.profile_manager.update(self.current_profile)
        
        QMessageBox.information(
            self, "Saved",
            f"Payload settings saved for '{self.current_profile.name}'"
        )
