"""
Config Manager - Generate and manage Xray-core configurations
"""

import json
import os
from typing import Dict, Any, Optional
from .protocol_parser import ServerProfile, Protocol


class ConfigManager:
    """Manages Xray-core JSON configurations"""
    
    DEFAULT_LOCAL_PORT = 10808
    DEFAULT_HTTP_PORT = 10809
    
    def __init__(self, config_dir: str = None):
        if config_dir is None:
            config_dir = os.path.expanduser("~/.config/voidtunnel")
        self.config_dir = config_dir
        self.config_file = os.path.join(config_dir, "config.json")
        os.makedirs(config_dir, exist_ok=True)
    
    def generate_config(self, profile: ServerProfile, 
                        local_port: int = DEFAULT_LOCAL_PORT,
                        http_port: int = DEFAULT_HTTP_PORT,
                        dns_servers: list = None,
                        routing_rules: list = None) -> Dict[str, Any]:
        """Generate Xray-core configuration from a profile"""
        
        if dns_servers is None:
            dns_servers = ["8.8.8.8", "8.8.4.4", "1.1.1.1"]
        
        config = {
            "log": {
                "loglevel": "warning"
            },
            "stats": {},  # Enable statistics
            "api": {
                "tag": "api",
                "services": ["StatsService"]
            },
            "dns": {
                "servers": dns_servers
            },
            "inbounds": [
                {
                    "tag": "socks-in",
                    "port": local_port,
                    "listen": "127.0.0.1",
                    "protocol": "socks",
                    "settings": {
                        "auth": "noauth",
                        "udp": True
                    },
                    "sniffing": {
                        "enabled": True,
                        "destOverride": ["http", "tls"]
                    }
                },
                {
                    "tag": "http-in",
                    "port": http_port,
                    "listen": "127.0.0.1",
                    "protocol": "http",
                    "settings": {}
                },
                {
                    "tag": "api-in",
                    "port": 10085,
                    "listen": "127.0.0.1",
                    "protocol": "dokodemo-door",
                    "settings": {
                        "address": "127.0.0.1"
                    }
                }
            ],
            "outbounds": [
                self._generate_outbound(profile),
                {
                    "tag": "direct",
                    "protocol": "freedom",
                    "settings": {}
                },
                {
                    "tag": "block",
                    "protocol": "blackhole",
                    "settings": {}
                }
            ],
            "routing": {
                "domainStrategy": "AsIs",
                "rules": [
                    {
                        "type": "field",
                        "inboundTag": ["api-in"],
                        "outboundTag": "api"
                    }
                ] + (routing_rules or [
                    {
                        "type": "field",
                        "outboundTag": "direct",
                        "domain": ["geosite:private"]
                    },
                    {
                        "type": "field",
                        "outboundTag": "block",
                        "domain": ["geosite:category-ads-all"]
                    }
                ])
            },
            "policy": {
                "system": {
                    "statsInboundUplink": True,
                    "statsInboundDownlink": True,
                    "statsOutboundUplink": True,
                    "statsOutboundDownlink": True
                }
            }
        }
        
        return config
    
    def _generate_outbound(self, profile: ServerProfile) -> Dict[str, Any]:
        """Generate outbound configuration based on protocol"""
        
        if profile.protocol == Protocol.VMESS.value:
            return self._vmess_outbound(profile)
        elif profile.protocol == Protocol.VLESS.value:
            return self._vless_outbound(profile)
        elif profile.protocol == Protocol.TROJAN.value:
            return self._trojan_outbound(profile)
        elif profile.protocol == Protocol.SHADOWSOCKS.value:
            return self._shadowsocks_outbound(profile)
        else:
            raise ValueError(f"Unsupported protocol: {profile.protocol}")
    
    def _vmess_outbound(self, profile: ServerProfile) -> Dict[str, Any]:
        """Generate VMess outbound"""
        outbound = {
            "tag": "proxy",
            "protocol": "vmess",
            "settings": {
                "vnext": [{
                    "address": profile.address,
                    "port": profile.port,
                    "users": [{
                        "id": profile.uuid,
                        "alterId": profile.alter_id,
                        "security": profile.security
                    }]
                }]
            },
            "streamSettings": self._stream_settings(profile)
        }
        return outbound
    
    def _vless_outbound(self, profile: ServerProfile) -> Dict[str, Any]:
        """Generate VLESS outbound"""
        outbound = {
            "tag": "proxy",
            "protocol": "vless",
            "settings": {
                "vnext": [{
                    "address": profile.address,
                    "port": profile.port,
                    "users": [{
                        "id": profile.uuid,
                        "encryption": "none"
                    }]
                }]
            },
            "streamSettings": self._stream_settings(profile)
        }
        return outbound
    
    def _trojan_outbound(self, profile: ServerProfile) -> Dict[str, Any]:
        """Generate Trojan outbound"""
        outbound = {
            "tag": "proxy",
            "protocol": "trojan",
            "settings": {
                "servers": [{
                    "address": profile.address,
                    "port": profile.port,
                    "password": profile.password
                }]
            },
            "streamSettings": self._stream_settings(profile)
        }
        return outbound
    
    def _shadowsocks_outbound(self, profile: ServerProfile) -> Dict[str, Any]:
        """Generate Shadowsocks outbound"""
        outbound = {
            "tag": "proxy",
            "protocol": "shadowsocks",
            "settings": {
                "servers": [{
                    "address": profile.address,
                    "port": profile.port,
                    "password": profile.password,
                    "method": profile.ss_method
                }]
            }
        }
        return outbound
    
    def _stream_settings(self, profile: ServerProfile) -> Dict[str, Any]:
        """Generate stream settings (transport layer)"""
        settings = {
            "network": profile.network
        }
        
        # TLS settings
        if profile.tls:
            settings["security"] = "tls"
            tls_settings = {
                "allowInsecure": True  # Like NetMod - skip cert verification for SNI bypass
            }
            if profile.sni:
                tls_settings["serverName"] = profile.sni
            if profile.fingerprint:
                tls_settings["fingerprint"] = profile.fingerprint
            if profile.alpn:
                tls_settings["alpn"] = profile.alpn.split(",")
            settings["tlsSettings"] = tls_settings
        else:
            settings["security"] = "none"
        
        # Transport specific settings
        if profile.network == "ws":
            ws_settings = {}
            if profile.ws_path:
                ws_settings["path"] = profile.ws_path
            if profile.ws_host or profile.custom_headers:
                headers = dict(profile.custom_headers) if profile.custom_headers else {}
                if profile.ws_host:
                    headers["Host"] = profile.ws_host
                ws_settings["headers"] = headers
            settings["wsSettings"] = ws_settings
            
        elif profile.network == "grpc":
            settings["grpcSettings"] = {
                "serviceName": profile.grpc_service_name,
                "multiMode": profile.grpc_mode == "multi"
            }
            
        elif profile.network == "http" or profile.network == "h2":
            http_settings = {}
            if profile.http_path:
                http_settings["path"] = profile.http_path
            if profile.http_host:
                http_settings["host"] = [profile.http_host]
            settings["httpSettings"] = http_settings
        
        return settings
    
    def save_config(self, config: Dict[str, Any], path: str = None) -> str:
        """Save configuration to file"""
        if path is None:
            path = self.config_file
        
        with open(path, 'w') as f:
            json.dump(config, f, indent=2)
        
        return path
    
    def load_config(self, path: str = None) -> Optional[Dict[str, Any]]:
        """Load configuration from file"""
        if path is None:
            path = self.config_file
        
        if not os.path.exists(path):
            return None
        
        with open(path, 'r') as f:
            return json.load(f)
