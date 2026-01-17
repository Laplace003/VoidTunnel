"""
Log Viewer - Real-time connection logs display
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QPlainTextEdit, QComboBox, QCheckBox, QFileDialog
)
from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtGui import QFont, QTextCharFormat, QColor, QTextCursor
import datetime


class LogViewer(QWidget):
    """Widget for displaying connection logs"""
    
    MAX_LINES = 1000
    
    def __init__(self):
        super().__init__()
        self.log_count = 0
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 16, 24, 16)
        layout.setSpacing(16)
        
        # Header
        header = QHBoxLayout()
        
        title = QLabel("Connection Logs")
        title.setFont(QFont("Inter", 18, QFont.Weight.Bold))
        header.addWidget(title)
        
        header.addStretch()
        
        # Log level filter
        self.level_filter = QComboBox()
        self.level_filter.addItems(["All", "Info", "Warning", "Error"])
        self.level_filter.currentIndexChanged.connect(self._apply_filter)
        header.addWidget(QLabel("Level:"))
        header.addWidget(self.level_filter)
        
        # Auto-scroll
        self.auto_scroll = QCheckBox("Auto-scroll")
        self.auto_scroll.setChecked(True)
        header.addWidget(self.auto_scroll)
        
        # Actions
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self._clear_logs)
        header.addWidget(clear_btn)
        
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self._save_logs)
        header.addWidget(save_btn)
        
        layout.addLayout(header)
        
        # Log display
        self.log_text = QPlainTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 11))
        self.log_text.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.log_text.setStyleSheet("""
            QPlainTextEdit {
                background-color: #0d1117;
                border: 1px solid #21262d;
                border-radius: 8px;
                padding: 12px;
            }
        """)
        layout.addWidget(self.log_text, 1)
        
        # Footer
        footer = QHBoxLayout()
        self.line_count_label = QLabel("0 lines")
        self.line_count_label.setObjectName("subtitleLabel")
        footer.addWidget(self.line_count_label)
        footer.addStretch()
        layout.addLayout(footer)
    
    @pyqtSlot(str)
    def append_log(self, log: str):
        """Append a log message"""
        # Trim if too many lines
        if self.log_count >= self.MAX_LINES:
            cursor = self.log_text.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            cursor.movePosition(QTextCursor.MoveOperation.Down, QTextCursor.MoveMode.KeepAnchor, 100)
            cursor.removeSelectedText()
            self.log_count -= 100
        
        # Determine log level and color
        log_lower = log.lower()
        
        if "error" in log_lower or "failed" in log_lower:
            color = "#f85149"  # Red
        elif "warning" in log_lower or "warn" in log_lower:
            color = "#d29922"  # Yellow
        elif "connected" in log_lower or "accepted" in log_lower:
            color = "#3fb950"  # Green
        else:
            color = "#8b949e"  # Gray
        
        # Format log entry
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        formatted = f"[{timestamp}] {log}"
        
        # Append with color
        cursor = self.log_text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(color))
        cursor.insertText(formatted + "\n", fmt)
        
        self.log_count += 1
        self.line_count_label.setText(f"{self.log_count} lines")
        
        # Auto-scroll
        if self.auto_scroll.isChecked():
            self.log_text.verticalScrollBar().setValue(
                self.log_text.verticalScrollBar().maximum()
            )
    
    def _apply_filter(self):
        """Apply log level filter"""
        # This is a placeholder - full implementation would filter stored logs
        pass
    
    def _clear_logs(self):
        """Clear all logs"""
        self.log_text.clear()
        self.log_count = 0
        self.line_count_label.setText("0 lines")
    
    def _save_logs(self):
        """Save logs to file"""
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Logs", "netmod_logs.txt", "Text Files (*.txt);;All Files (*)"
        )
        
        if filename:
            with open(filename, 'w') as f:
                f.write(self.log_text.toPlainText())
