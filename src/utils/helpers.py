"""
Helper utilities
"""

import os
import json
import qrcode
from io import BytesIO
from typing import Any, Dict, Optional


def get_app_dir() -> str:
    """Get the application data directory"""
    app_dir = os.path.expanduser("~/.config/voidtunnel")
    os.makedirs(app_dir, exist_ok=True)
    return app_dir


def get_logs_dir() -> str:
    """Get the logs directory"""
    logs_dir = os.path.join(get_app_dir(), "logs")
    os.makedirs(logs_dir, exist_ok=True)
    return logs_dir


def load_settings() -> Dict[str, Any]:
    """Load application settings"""
    settings_file = os.path.join(get_app_dir(), "settings.json")
    default_settings = {
        "socks_port": 10808,
        "http_port": 10809,
        "auto_connect": False,
        "enable_system_proxy": True,
        "start_minimized": False,
        "minimize_to_tray": True,
        "dns_servers": ["8.8.8.8", "8.8.4.4"],
        "theme": "dark",
        "language": "en",
        "log_level": "warning",
        "check_updates": True,
    }
    
    if os.path.exists(settings_file):
        try:
            with open(settings_file, 'r') as f:
                saved = json.load(f)
                default_settings.update(saved)
        except:
            pass
    
    return default_settings


def save_settings(settings: Dict[str, Any]):
    """Save application settings"""
    settings_file = os.path.join(get_app_dir(), "settings.json")
    try:
        with open(settings_file, 'w') as f:
            json.dump(settings, f, indent=2)
    except Exception as e:
        print(f"Error saving settings: {e}")


def generate_qr_code(data: str, size: int = 200) -> bytes:
    """Generate QR code as PNG bytes"""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=2,
    )
    qr.add_data(data)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    return buffer.getvalue()


def format_bytes(bytes_count: int) -> str:
    """Format bytes to human readable string"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_count < 1024:
            return f"{bytes_count:.2f} {unit}"
        bytes_count /= 1024
    return f"{bytes_count:.2f} PB"


def format_duration(seconds: int) -> str:
    """Format duration in seconds to human readable string"""
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        return f"{seconds // 60}m {seconds % 60}s"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours}h {minutes}m"


def sanitize_filename(filename: str) -> str:
    """Sanitize a filename by removing invalid characters"""
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    return filename.strip()


def get_protocol_color(protocol: str) -> str:
    """Get a color for each protocol type"""
    colors = {
        "vmess": "#3498db",    # Blue
        "vless": "#9b59b6",    # Purple
        "trojan": "#e74c3c",   # Red
        "ss": "#2ecc71",       # Green
        "ssh": "#f39c12",      # Orange
    }
    return colors.get(protocol.lower(), "#95a5a6")


def get_protocol_icon(protocol: str) -> str:
    """Get icon name for each protocol"""
    icons = {
        "vmess": "🔵",
        "vless": "🟣",
        "trojan": "🔴",
        "ss": "🟢",
        "ssh": "🟠",
    }
    return icons.get(protocol.lower(), "⚪")
