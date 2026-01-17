"""
Proxy Manager - Configure Linux system proxy settings
Supports GNOME, KDE, and environment variable methods
"""

import os
import subprocess
import shutil
from typing import Optional, Tuple
from enum import Enum


class ProxyMode(Enum):
    NONE = "none"
    MANUAL = "manual"
    AUTO = "auto"


class ProxyManager:
    """Manages Linux system proxy settings"""
    
    def __init__(self, socks_port: int = 10808, http_port: int = 10809):
        self.socks_port = socks_port
        self.http_port = http_port
        self.socks_host = "127.0.0.1"
        self.http_host = "127.0.0.1"
        
        # Detect desktop environment
        self.desktop_env = self._detect_desktop()
    
    def _detect_desktop(self) -> str:
        """Detect the current desktop environment"""
        desktop = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()
        session = os.environ.get("DESKTOP_SESSION", "").lower()
        
        if "gnome" in desktop or "gnome" in session or "ubuntu" in desktop:
            return "gnome"
        elif "kde" in desktop or "plasma" in desktop or "kde" in session:
            return "kde"
        elif "xfce" in desktop:
            return "xfce"
        elif "cinnamon" in desktop:
            return "cinnamon"
        else:
            return "unknown"
    
    def enable_system_proxy(self) -> Tuple[bool, str]:
        """Enable system-wide proxy"""
        if self.desktop_env == "gnome":
            return self._enable_gnome_proxy()
        elif self.desktop_env == "kde":
            return self._enable_kde_proxy()
        elif self.desktop_env in ["xfce", "cinnamon"]:
            return self._enable_gnome_proxy()  # Uses gsettings
        else:
            return self._enable_env_proxy()
    
    def disable_system_proxy(self) -> Tuple[bool, str]:
        """Disable system-wide proxy"""
        if self.desktop_env == "gnome":
            return self._disable_gnome_proxy()
        elif self.desktop_env == "kde":
            return self._disable_kde_proxy()
        elif self.desktop_env in ["xfce", "cinnamon"]:
            return self._disable_gnome_proxy()
        else:
            return self._disable_env_proxy()
    
    def _enable_gnome_proxy(self) -> Tuple[bool, str]:
        """Enable proxy for GNOME/GTK environments"""
        try:
            commands = [
                ["gsettings", "set", "org.gnome.system.proxy", "mode", "manual"],
                ["gsettings", "set", "org.gnome.system.proxy.socks", "host", self.socks_host],
                ["gsettings", "set", "org.gnome.system.proxy.socks", "port", str(self.socks_port)],
                ["gsettings", "set", "org.gnome.system.proxy.http", "host", self.http_host],
                ["gsettings", "set", "org.gnome.system.proxy.http", "port", str(self.http_port)],
                ["gsettings", "set", "org.gnome.system.proxy.https", "host", self.http_host],
                ["gsettings", "set", "org.gnome.system.proxy.https", "port", str(self.http_port)],
            ]
            
            for cmd in commands:
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    return False, f"Failed to set GNOME proxy: {result.stderr}"
            
            return True, "System proxy enabled (GNOME)"
            
        except FileNotFoundError:
            return False, "gsettings not found"
        except Exception as e:
            return False, str(e)
    
    def _disable_gnome_proxy(self) -> Tuple[bool, str]:
        """Disable proxy for GNOME/GTK environments"""
        try:
            result = subprocess.run(
                ["gsettings", "set", "org.gnome.system.proxy", "mode", "none"],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                return True, "System proxy disabled (GNOME)"
            else:
                return False, f"Failed to disable GNOME proxy: {result.stderr}"
                
        except FileNotFoundError:
            return False, "gsettings not found"
        except Exception as e:
            return False, str(e)
    
    def _enable_kde_proxy(self) -> Tuple[bool, str]:
        """Enable proxy for KDE Plasma"""
        try:
            # KDE uses kwriteconfig5 or kwriteconfig6
            kwrite = self._find_kwriteconfig()
            if not kwrite:
                return False, "kwriteconfig not found"
            
            commands = [
                [kwrite, "--file", "kioslaverc", "--group", "Proxy Settings", 
                 "--key", "ProxyType", "1"],
                [kwrite, "--file", "kioslaverc", "--group", "Proxy Settings",
                 "--key", "socksProxy", f"socks://{self.socks_host}:{self.socks_port}"],
                [kwrite, "--file", "kioslaverc", "--group", "Proxy Settings",
                 "--key", "httpProxy", f"http://{self.http_host}:{self.http_port}"],
                [kwrite, "--file", "kioslaverc", "--group", "Proxy Settings",
                 "--key", "httpsProxy", f"http://{self.http_host}:{self.http_port}"],
            ]
            
            for cmd in commands:
                subprocess.run(cmd, capture_output=True)
            
            # Notify KDE to reload settings
            subprocess.run(["dbus-send", "--type=signal", "/KIO/Scheduler",
                          "org.kde.KIO.Scheduler.reparseSlaveConfiguration", "string:''"],
                         capture_output=True)
            
            return True, "System proxy enabled (KDE)"
            
        except Exception as e:
            return False, str(e)
    
    def _disable_kde_proxy(self) -> Tuple[bool, str]:
        """Disable proxy for KDE Plasma"""
        try:
            kwrite = self._find_kwriteconfig()
            if not kwrite:
                return False, "kwriteconfig not found"
            
            subprocess.run([kwrite, "--file", "kioslaverc", "--group", "Proxy Settings",
                          "--key", "ProxyType", "0"], capture_output=True)
            
            # Notify KDE to reload settings
            subprocess.run(["dbus-send", "--type=signal", "/KIO/Scheduler",
                          "org.kde.KIO.Scheduler.reparseSlaveConfiguration", "string:''"],
                         capture_output=True)
            
            return True, "System proxy disabled (KDE)"
            
        except Exception as e:
            return False, str(e)
    
    def _find_kwriteconfig(self) -> Optional[str]:
        """Find kwriteconfig binary"""
        for cmd in ["kwriteconfig6", "kwriteconfig5", "kwriteconfig"]:
            if shutil.which(cmd):
                return cmd
        return None
    
    def _enable_env_proxy(self) -> Tuple[bool, str]:
        """Set environment variables for proxy (fallback method)"""
        try:
            proxy_env = {
                "http_proxy": f"http://{self.http_host}:{self.http_port}",
                "https_proxy": f"http://{self.http_host}:{self.http_port}",
                "HTTP_PROXY": f"http://{self.http_host}:{self.http_port}",
                "HTTPS_PROXY": f"http://{self.http_host}:{self.http_port}",
                "all_proxy": f"socks5://{self.socks_host}:{self.socks_port}",
                "ALL_PROXY": f"socks5://{self.socks_host}:{self.socks_port}",
            }
            
            for key, value in proxy_env.items():
                os.environ[key] = value
            
            # Write to profile.d for persistence
            self._write_proxy_profile(proxy_env)
            
            return True, "Environment proxy variables set"
            
        except Exception as e:
            return False, str(e)
    
    def _disable_env_proxy(self) -> Tuple[bool, str]:
        """Unset environment variables for proxy"""
        try:
            for key in ["http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY", 
                       "all_proxy", "ALL_PROXY"]:
                if key in os.environ:
                    del os.environ[key]
            
            # Remove profile file
            profile_path = os.path.expanduser("~/.config/voidtunnel/proxy.env")
            if os.path.exists(profile_path):
                os.remove(profile_path)
            
            return True, "Environment proxy variables cleared"
            
        except Exception as e:
            return False, str(e)
    
    def _write_proxy_profile(self, proxy_env: dict):
        """Write proxy settings to a file for other applications"""
        try:
            config_dir = os.path.expanduser("~/.config/voidtunnel")
            os.makedirs(config_dir, exist_ok=True)
            
            profile_path = os.path.join(config_dir, "proxy.env")
            with open(profile_path, 'w') as f:
                for key, value in proxy_env.items():
                    f.write(f"export {key}={value}\n")
        except:
            pass
    
    def get_current_proxy_status(self) -> Tuple[bool, str]:
        """Check if system proxy is currently enabled"""
        if self.desktop_env == "gnome":
            try:
                result = subprocess.run(
                    ["gsettings", "get", "org.gnome.system.proxy", "mode"],
                    capture_output=True,
                    text=True
                )
                mode = result.stdout.strip().strip("'")
                return mode == "manual", f"Mode: {mode}"
            except:
                return False, "Unknown"
        elif self.desktop_env == "kde":
            try:
                kread = self._find_kwriteconfig().replace("write", "read") if self._find_kwriteconfig() else None
                if kread:
                    result = subprocess.run(
                        [kread, "--file", "kioslaverc", "--group", "Proxy Settings", "--key", "ProxyType"],
                        capture_output=True,
                        text=True
                    )
                    proxy_type = result.stdout.strip()
                    return proxy_type == "1", f"ProxyType: {proxy_type}"
            except:
                pass
            return False, "Unknown"
        else:
            is_set = "http_proxy" in os.environ or "HTTP_PROXY" in os.environ
            return is_set, "Environment variables" if is_set else "Not set"
    
    def update_ports(self, socks_port: int = None, http_port: int = None):
        """Update the proxy ports"""
        if socks_port:
            self.socks_port = socks_port
        if http_port:
            self.http_port = http_port
