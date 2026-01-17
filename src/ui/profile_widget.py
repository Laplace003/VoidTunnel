"""
Profile Widget - Server profile management
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QFrame, QLineEdit, QMenu,
    QDialog, QFormLayout, QComboBox, QSpinBox, QTextEdit,
    QMessageBox, QInputDialog, QCheckBox, QFileDialog
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QAction

from src.core.profile_manager import ProfileManager
from src.core.protocol_parser import ServerProfile, ProtocolParser, Protocol
from src.utils.helpers import get_protocol_icon, get_protocol_color
from src.utils.network import tcp_ping


class ProfileListItem(QWidget):
    """Custom widget for profile list items"""
    
    def __init__(self, profile: ServerProfile):
        super().__init__()
        self.profile = profile
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        
        # Protocol icon
        icon = QLabel(get_protocol_icon(self.profile.protocol))
        icon.setFont(QFont("Inter", 16))
        icon.setStyleSheet("color: #f85149;")  # Red for protocol icon
        layout.addWidget(icon)
        
        # Server info
        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)
        
        # Server name with clear styling
        name = QLabel(self.profile.name)
        name.setFont(QFont("Inter", 12, QFont.Weight.Medium))
        name.setStyleSheet("""
            QLabel {
                color: #e6edf3;
                text-decoration: none;
                background: transparent;
            }
        """)
        info_layout.addWidget(name)
        
        # Server address
        address = QLabel(f"{self.profile.address}:{self.profile.port}")
        address.setFont(QFont("Inter", 10))
        address.setStyleSheet("color: #8b949e;")
        info_layout.addWidget(address)
        
        layout.addLayout(info_layout, 1)
        
        # Latency
        latency_text = f"{self.profile.latency}ms" if self.profile.latency >= 0 else "--"
        self.latency_label = QLabel(latency_text)
        self.latency_label.setFont(QFont("Inter", 11, QFont.Weight.Medium))
        if self.profile.latency >= 0:
            if self.profile.latency < 100:
                self.latency_label.setStyleSheet("color: #3fb950;")
            elif self.profile.latency < 300:
                self.latency_label.setStyleSheet("color: #d29922;")
            else:
                self.latency_label.setStyleSheet("color: #f85149;")
        layout.addWidget(self.latency_label)
    
    def update_latency(self, latency: int):
        """Update latency display"""
        self.profile.latency = latency
        self.latency_label.setText(f"{latency}ms" if latency >= 0 else "--")
        if latency >= 0:
            if latency < 100:
                self.latency_label.setStyleSheet("color: #3fb950;")
            elif latency < 300:
                self.latency_label.setStyleSheet("color: #d29922;")
            else:
                self.latency_label.setStyleSheet("color: #f85149;")


class ProfileWidget(QWidget):
    """Widget for managing server profiles"""
    
    profile_selected = pyqtSignal(object)
    
    def __init__(self, profile_manager: ProfileManager):
        super().__init__()
        self.profile_manager = profile_manager
        self._setup_ui()
        self._load_profiles()
    
    def _setup_ui(self):
        """Setup the UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 16, 24, 16)
        layout.setSpacing(16)
        
        # Header
        header = QHBoxLayout()
        
        title = QLabel("Servers")
        title.setFont(QFont("Inter", 18, QFont.Weight.Bold))
        header.addWidget(title)
        
        header.addStretch()
        
        # Search
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Search servers...")
        self.search_input.setFixedWidth(200)
        self.search_input.textChanged.connect(self._filter_profiles)
        header.addWidget(self.search_input)
        
        # Actions
        add_btn = QPushButton("+ Add")
        add_btn.clicked.connect(self._add_profile)
        header.addWidget(add_btn)
        
        import_btn = QPushButton("📥 Import")
        import_btn.clicked.connect(self._import_profiles)
        header.addWidget(import_btn)
        
        ping_btn = QPushButton("📶 Ping All")
        ping_btn.clicked.connect(self._ping_all)
        header.addWidget(ping_btn)
        
        layout.addLayout(header)
        
        # Profile list
        self.profile_list = QListWidget()
        self.profile_list.setSpacing(4)
        self.profile_list.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.profile_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.profile_list.customContextMenuRequested.connect(self._show_context_menu)
        layout.addWidget(self.profile_list, 1)
        
        # Footer
        footer = QHBoxLayout()
        
        self.count_label = QLabel("0 servers")
        self.count_label.setObjectName("subtitleLabel")
        footer.addWidget(self.count_label)
        
        footer.addStretch()
        
        layout.addLayout(footer)
    
    def _load_profiles(self):
        """Load profiles into the list"""
        self.profile_list.clear()
        profiles = self.profile_manager.get_all()
        
        for profile in profiles:
            item = QListWidgetItem()
            widget = ProfileListItem(profile)
            item.setSizeHint(QSize(0, 60))
            item.setData(Qt.ItemDataRole.UserRole, profile)
            self.profile_list.addItem(item)
            self.profile_list.setItemWidget(item, widget)
        
        self.count_label.setText(f"{len(profiles)} servers")
    
    def _filter_profiles(self, text: str):
        """Filter profiles by search text"""
        for i in range(self.profile_list.count()):
            item = self.profile_list.item(i)
            profile = item.data(Qt.ItemDataRole.UserRole)
            visible = text.lower() in profile.name.lower() or text.lower() in profile.address.lower()
            item.setHidden(not visible)
    
    def _on_item_double_clicked(self, item: QListWidgetItem):
        """Handle double-click on profile"""
        profile = item.data(Qt.ItemDataRole.UserRole)
        self.profile_selected.emit(profile)
    
    def _show_context_menu(self, pos):
        """Show context menu for profile"""
        item = self.profile_list.itemAt(pos)
        if not item:
            return
        
        profile = item.data(Qt.ItemDataRole.UserRole)
        
        menu = QMenu(self)
        
        select_action = QAction("Select", self)
        select_action.triggered.connect(lambda: self.profile_selected.emit(profile))
        menu.addAction(select_action)
        
        menu.addSeparator()
        
        ping_action = QAction("Ping", self)
        ping_action.triggered.connect(lambda: self._ping_profile(item))
        menu.addAction(ping_action)
        
        edit_action = QAction("Edit", self)
        edit_action.triggered.connect(lambda: self._edit_profile(profile))
        menu.addAction(edit_action)
        
        duplicate_action = QAction("Duplicate", self)
        duplicate_action.triggered.connect(lambda: self._duplicate_profile(profile))
        menu.addAction(duplicate_action)
        
        menu.addSeparator()
        
        copy_url_action = QAction("Copy URL", self)
        copy_url_action.triggered.connect(lambda: self._copy_profile_url(profile))
        menu.addAction(copy_url_action)
        
        qr_action = QAction("Show QR Code", self)
        qr_action.triggered.connect(lambda: self._show_qr_code(profile))
        menu.addAction(qr_action)
        
        menu.addSeparator()
        
        delete_action = QAction("Delete", self)
        delete_action.triggered.connect(lambda: self._delete_profile(profile))
        menu.addAction(delete_action)
        
        menu.exec(self.profile_list.mapToGlobal(pos))
    
    def _add_profile(self):
        """Add a new profile"""
        dialog = AddProfileDialog(self)
        if dialog.exec():
            url = dialog.get_url()
            if url:
                profile = self.profile_manager.add_from_url(url)
                if profile:
                    self._load_profiles()
                else:
                    QMessageBox.warning(self, "Error", "Invalid URL format")
    
    def _import_profiles(self):
        """Import profiles from URLs or subscription"""
        dialog = ImportDialog(self)
        if dialog.exec():
            urls = dialog.get_urls()
            sub_url = dialog.get_subscription_url()
            
            if sub_url:
                profiles = self.profile_manager.import_from_subscription(sub_url)
            elif urls:
                profiles = self.profile_manager.import_from_urls(urls)
            else:
                profiles = []
            
            if profiles:
                self._load_profiles()
                QMessageBox.information(
                    self, "Import Complete", 
                    f"Imported {len(profiles)} server(s)"
                )
    
    def _ping_profile(self, item: QListWidgetItem):
        """Ping a single profile"""
        profile = item.data(Qt.ItemDataRole.UserRole)
        widget = self.profile_list.itemWidget(item)
        
        import threading
        def ping():
            latency = tcp_ping(profile.address, profile.port)
            self.profile_manager.update_latency(profile.id, latency)
            if isinstance(widget, ProfileListItem):
                widget.update_latency(latency)
        
        threading.Thread(target=ping, daemon=True).start()
    
    def _ping_all(self):
        """Ping all profiles"""
        import threading
        
        def ping_all():
            for i in range(self.profile_list.count()):
                item = self.profile_list.item(i)
                profile = item.data(Qt.ItemDataRole.UserRole)
                widget = self.profile_list.itemWidget(item)
                
                latency = tcp_ping(profile.address, profile.port)
                self.profile_manager.update_latency(profile.id, latency)
                
                if isinstance(widget, ProfileListItem):
                    widget.update_latency(latency)
        
        threading.Thread(target=ping_all, daemon=True).start()
    
    def _edit_profile(self, profile: ServerProfile):
        """Edit a profile"""
        dialog = EditProfileDialog(profile, self)
        if dialog.exec():
            updated = dialog.get_profile()
            self.profile_manager.update(updated)
            self._load_profiles()
    
    def _duplicate_profile(self, profile: ServerProfile):
        """Duplicate a profile"""
        self.profile_manager.duplicate(profile.id)
        self._load_profiles()
    
    def _copy_profile_url(self, profile: ServerProfile):
        """Copy profile URL to clipboard"""
        from PyQt6.QtWidgets import QApplication
        url = ProtocolParser.to_url(profile)
        QApplication.clipboard().setText(url)
    
    def _show_qr_code(self, profile: ServerProfile):
        """Show QR code for profile"""
        from ..utils.helpers import generate_qr_code
        from PyQt6.QtWidgets import QDialog, QLabel
        from PyQt6.QtGui import QPixmap
        
        url = ProtocolParser.to_url(profile)
        qr_data = generate_qr_code(url, 300)
        
        dialog = QDialog(self)
        dialog.setWindowTitle(f"QR Code - {profile.name}")
        dialog.setFixedSize(350, 400)
        
        layout = QVBoxLayout(dialog)
        
        # QR image
        pixmap = QPixmap()
        pixmap.loadFromData(qr_data)
        qr_label = QLabel()
        qr_label.setPixmap(pixmap)
        qr_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(qr_label)
        
        # Profile name
        name_label = QLabel(profile.name)
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_label.setFont(QFont("Inter", 12, QFont.Weight.Bold))
        layout.addWidget(name_label)
        
        dialog.exec()
    
    def _delete_profile(self, profile: ServerProfile):
        """Delete a profile"""
        reply = QMessageBox.question(
            self, "Delete Server",
            f"Are you sure you want to delete '{profile.name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.profile_manager.delete(profile.id)
            self._load_profiles()


class AddProfileDialog(QDialog):
    """Dialog for adding a new profile via URL"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Server")
        self.setFixedWidth(500)
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        
        # URL input
        layout.addWidget(QLabel("Enter server URL:"))
        
        self.url_input = QTextEdit()
        self.url_input.setPlaceholderText(
            "Paste VMess/VLESS/Trojan/Shadowsocks/SSH URL here...\n\n"
            "Examples:\n"
            "vmess://eyJ2IjoiMiIsInBzIjoi...\n"
            "vless://uuid@server:port?type=ws#name\n"
            "trojan://password@server:port#name"
        )
        self.url_input.setMinimumHeight(100)
        layout.addWidget(self.url_input)
        
        # Buttons
        buttons = QHBoxLayout()
        buttons.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(cancel_btn)
        
        add_btn = QPushButton("Add")
        add_btn.setObjectName("primaryButton")
        add_btn.clicked.connect(self.accept)
        buttons.addWidget(add_btn)
        
        layout.addLayout(buttons)
    
    def get_url(self) -> str:
        return self.url_input.toPlainText().strip()


class ImportDialog(QDialog):
    """Dialog for importing multiple profiles"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Import Servers")
        self.setFixedWidth(500)
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        
        # Subscription URL
        layout.addWidget(QLabel("Subscription URL (optional):"))
        self.sub_input = QLineEdit()
        self.sub_input.setPlaceholderText("https://example.com/subscription")
        layout.addWidget(self.sub_input)
        
        # Or separator
        or_layout = QHBoxLayout()
        or_layout.addWidget(QFrame())
        or_label = QLabel("OR")
        or_label.setObjectName("subtitleLabel")
        or_layout.addWidget(or_label)
        or_layout.addWidget(QFrame())
        layout.addLayout(or_layout)
        
        # URLs
        layout.addWidget(QLabel("Server URLs (one per line):"))
        self.urls_input = QTextEdit()
        self.urls_input.setPlaceholderText("Paste multiple server URLs here...")
        self.urls_input.setMinimumHeight(150)
        layout.addWidget(self.urls_input)
        
        # Buttons
        buttons = QHBoxLayout()
        buttons.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(cancel_btn)
        
        import_btn = QPushButton("Import")
        import_btn.setObjectName("primaryButton")
        import_btn.clicked.connect(self.accept)
        buttons.addWidget(import_btn)
        
        layout.addLayout(buttons)
    
    def get_subscription_url(self) -> str:
        return self.sub_input.text().strip()
    
    def get_urls(self) -> str:
        return self.urls_input.toPlainText().strip()


class EditProfileDialog(QDialog):
    """Dialog for editing a profile"""
    
    def __init__(self, profile: ServerProfile, parent=None):
        super().__init__(parent)
        self.profile = ServerProfile.from_dict(profile.to_dict())
        self.setWindowTitle(f"Edit - {profile.name}")
        self.setMinimumWidth(500)
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        
        form = QFormLayout()
        form.setSpacing(12)
        
        # Name
        self.name_input = QLineEdit(self.profile.name)
        form.addRow("Name:", self.name_input)
        
        # Address
        self.address_input = QLineEdit(self.profile.address)
        form.addRow("Address:", self.address_input)
        
        # Port
        self.port_input = QSpinBox()
        self.port_input.setRange(1, 65535)
        self.port_input.setValue(self.profile.port)
        form.addRow("Port:", self.port_input)
        
        # Protocol (read-only)
        protocol_label = QLabel(self.profile.protocol.upper())
        form.addRow("Protocol:", protocol_label)
        
        # TLS
        self.tls_check = QCheckBox()
        self.tls_check.setChecked(self.profile.tls)
        form.addRow("TLS:", self.tls_check)
        
        # SNI
        self.sni_input = QLineEdit(self.profile.sni)
        form.addRow("SNI:", self.sni_input)
        
        layout.addLayout(form)
        
        # Buttons
        buttons = QHBoxLayout()
        buttons.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(cancel_btn)
        
        save_btn = QPushButton("Save")
        save_btn.setObjectName("primaryButton")
        save_btn.clicked.connect(self.accept)
        buttons.addWidget(save_btn)
        
        layout.addLayout(buttons)
    
    def get_profile(self) -> ServerProfile:
        self.profile.name = self.name_input.text()
        self.profile.address = self.address_input.text()
        self.profile.port = self.port_input.value()
        self.profile.tls = self.tls_check.isChecked()
        self.profile.sni = self.sni_input.text()
        return self.profile
