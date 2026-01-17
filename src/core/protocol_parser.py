"""
Protocol Parser - Parse VPN protocol URLs
Supports: VMess, VLESS, Trojan, Shadowsocks, SSH
"""

import base64
import json
import urllib.parse
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any
from enum import Enum


class Protocol(Enum):
    VMESS = "vmess"
    VLESS = "vless"
    TROJAN = "trojan"
    SHADOWSOCKS = "ss"
    SSH = "ssh"


@dataclass
class ServerProfile:
    """Represents a VPN server profile"""
    id: str = ""
    name: str = ""
    protocol: str = ""
    address: str = ""
    port: int = 443
    
    # Authentication
    uuid: str = ""  # For VMess/VLESS
    password: str = ""  # For Trojan/SS/SSH
    username: str = ""  # For SSH
    
    # VMess specific
    alter_id: int = 0
    security: str = "auto"
    
    # Transport settings
    network: str = "tcp"  # tcp, ws, grpc, http, quic
    tls: bool = True
    sni: str = ""
    alpn: str = ""
    fingerprint: str = ""
    
    # WebSocket settings
    ws_path: str = ""
    ws_host: str = ""
    
    # gRPC settings
    grpc_service_name: str = ""
    grpc_mode: str = "gun"
    
    # HTTP settings
    http_path: str = ""
    http_host: str = ""
    
    # Shadowsocks specific
    ss_method: str = "aes-256-gcm"
    
    # SSH specific
    ssh_key: str = ""
    
    # Payload/Header injection (NetMod feature)
    payload_enabled: bool = False
    payload_data: str = ""
    custom_headers: Dict[str, str] = field(default_factory=dict)
    
    # Status
    is_active: bool = False
    latency: int = -1  # -1 means not tested
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ServerProfile':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class ProtocolParser:
    """Parse various VPN protocol URLs into ServerProfile objects"""
    
    @staticmethod
    def parse(url: str) -> Optional[ServerProfile]:
        """Parse a protocol URL and return a ServerProfile"""
        url = url.strip()
        
        if url.startswith("vmess://"):
            return ProtocolParser._parse_vmess(url)
        elif url.startswith("vless://"):
            return ProtocolParser._parse_vless(url)
        elif url.startswith("trojan://"):
            return ProtocolParser._parse_trojan(url)
        elif url.startswith("ss://"):
            return ProtocolParser._parse_shadowsocks(url)
        elif url.startswith("ssh://"):
            return ProtocolParser._parse_ssh(url)
        else:
            return None
    
    @staticmethod
    def _parse_vmess(url: str) -> Optional[ServerProfile]:
        """Parse VMess URL (base64 encoded JSON)"""
        try:
            # Remove vmess:// prefix
            encoded = url[8:]
            
            # Add padding if needed
            padding = 4 - len(encoded) % 4
            if padding != 4:
                encoded += "=" * padding
            
            # Decode base64
            decoded = base64.urlsafe_b64decode(encoded).decode('utf-8')
            data = json.loads(decoded)
            
            profile = ServerProfile(
                id=data.get("id", ""),
                name=data.get("ps", data.get("add", "VMess Server")),
                protocol=Protocol.VMESS.value,
                address=data.get("add", ""),
                port=int(data.get("port", 443)),
                uuid=data.get("id", ""),
                alter_id=int(data.get("aid", 0)),
                security=data.get("scy", "auto"),
                network=data.get("net", "tcp"),
                tls=data.get("tls", "") == "tls",
                sni=data.get("sni", ""),
                ws_path=data.get("path", ""),
                ws_host=data.get("host", ""),
            )
            
            return profile
        except Exception as e:
            print(f"Error parsing VMess URL: {e}")
            return None
    
    @staticmethod
    def _parse_vless(url: str) -> Optional[ServerProfile]:
        """Parse VLESS URL"""
        try:
            # vless://uuid@address:port?params#name
            parsed = urllib.parse.urlparse(url)
            params = urllib.parse.parse_qs(parsed.query)
            
            profile = ServerProfile(
                id=parsed.username or "",
                name=urllib.parse.unquote(parsed.fragment) if parsed.fragment else "VLESS Server",
                protocol=Protocol.VLESS.value,
                address=parsed.hostname or "",
                port=parsed.port or 443,
                uuid=parsed.username or "",
                network=params.get("type", ["tcp"])[0],
                tls=params.get("security", ["none"])[0] in ["tls", "reality"],
                sni=params.get("sni", [""])[0],
                fingerprint=params.get("fp", [""])[0],
                alpn=params.get("alpn", [""])[0],
                ws_path=params.get("path", [""])[0],
                ws_host=params.get("host", [""])[0],
                grpc_service_name=params.get("serviceName", [""])[0],
            )
            
            return profile
        except Exception as e:
            print(f"Error parsing VLESS URL: {e}")
            return None
    
    @staticmethod
    def _parse_trojan(url: str) -> Optional[ServerProfile]:
        """Parse Trojan URL"""
        try:
            # trojan://password@address:port?params#name
            parsed = urllib.parse.urlparse(url)
            params = urllib.parse.parse_qs(parsed.query)
            
            profile = ServerProfile(
                id=parsed.username or "",
                name=urllib.parse.unquote(parsed.fragment) if parsed.fragment else "Trojan Server",
                protocol=Protocol.TROJAN.value,
                address=parsed.hostname or "",
                port=parsed.port or 443,
                password=parsed.username or "",
                network=params.get("type", ["tcp"])[0],
                tls=True,  # Trojan always uses TLS
                sni=params.get("sni", [""])[0],
                fingerprint=params.get("fp", [""])[0],
                alpn=params.get("alpn", [""])[0],
                ws_path=params.get("path", [""])[0],
                ws_host=params.get("host", [""])[0],
            )
            
            return profile
        except Exception as e:
            print(f"Error parsing Trojan URL: {e}")
            return None
    
    @staticmethod
    def _parse_shadowsocks(url: str) -> Optional[ServerProfile]:
        """Parse Shadowsocks URL"""
        try:
            # ss://base64(method:password)@address:port#name
            # or ss://base64(method:password@address:port)#name
            
            parsed = urllib.parse.urlparse(url)
            name = urllib.parse.unquote(parsed.fragment) if parsed.fragment else "Shadowsocks Server"
            
            if parsed.username:
                # New format: ss://base64@address:port#name
                decoded = base64.urlsafe_b64decode(parsed.username + "==").decode('utf-8')
                method, password = decoded.split(":", 1)
                address = parsed.hostname
                port = parsed.port
            else:
                # Old format: ss://base64#name
                encoded = url[5:].split("#")[0]
                padding = 4 - len(encoded) % 4
                if padding != 4:
                    encoded += "=" * padding
                decoded = base64.urlsafe_b64decode(encoded).decode('utf-8')
                
                if "@" in decoded:
                    user_info, server_info = decoded.rsplit("@", 1)
                    method, password = user_info.split(":", 1)
                    address, port_str = server_info.rsplit(":", 1)
                    port = int(port_str)
                else:
                    return None
            
            profile = ServerProfile(
                name=name,
                protocol=Protocol.SHADOWSOCKS.value,
                address=address,
                port=port,
                password=password,
                ss_method=method,
                tls=False,
            )
            
            return profile
        except Exception as e:
            print(f"Error parsing Shadowsocks URL: {e}")
            return None
    
    @staticmethod
    def _parse_ssh(url: str) -> Optional[ServerProfile]:
        """Parse SSH URL"""
        try:
            # ssh://username:password@address:port#name
            parsed = urllib.parse.urlparse(url)
            
            profile = ServerProfile(
                name=urllib.parse.unquote(parsed.fragment) if parsed.fragment else "SSH Server",
                protocol=Protocol.SSH.value,
                address=parsed.hostname or "",
                port=parsed.port or 22,
                username=parsed.username or "",
                password=parsed.password or "",
                tls=False,
            )
            
            return profile
        except Exception as e:
            print(f"Error parsing SSH URL: {e}")
            return None
    
    @staticmethod
    def to_url(profile: ServerProfile) -> str:
        """Convert a ServerProfile back to a protocol URL"""
        if profile.protocol == Protocol.VMESS.value:
            return ProtocolParser._to_vmess_url(profile)
        elif profile.protocol == Protocol.VLESS.value:
            return ProtocolParser._to_vless_url(profile)
        elif profile.protocol == Protocol.TROJAN.value:
            return ProtocolParser._to_trojan_url(profile)
        elif profile.protocol == Protocol.SHADOWSOCKS.value:
            return ProtocolParser._to_ss_url(profile)
        elif profile.protocol == Protocol.SSH.value:
            return ProtocolParser._to_ssh_url(profile)
        return ""
    
    @staticmethod
    def _to_vmess_url(profile: ServerProfile) -> str:
        """Convert profile to VMess URL"""
        data = {
            "v": "2",
            "ps": profile.name,
            "add": profile.address,
            "port": str(profile.port),
            "id": profile.uuid,
            "aid": str(profile.alter_id),
            "scy": profile.security,
            "net": profile.network,
            "tls": "tls" if profile.tls else "",
            "sni": profile.sni,
            "path": profile.ws_path,
            "host": profile.ws_host,
        }
        encoded = base64.urlsafe_b64encode(json.dumps(data).encode()).decode()
        return f"vmess://{encoded}"
    
    @staticmethod
    def _to_vless_url(profile: ServerProfile) -> str:
        """Convert profile to VLESS URL"""
        params = {
            "type": profile.network,
            "security": "tls" if profile.tls else "none",
        }
        if profile.sni:
            params["sni"] = profile.sni
        if profile.ws_path:
            params["path"] = profile.ws_path
        if profile.ws_host:
            params["host"] = profile.ws_host
        if profile.grpc_service_name:
            params["serviceName"] = profile.grpc_service_name
        
        query = urllib.parse.urlencode(params)
        name = urllib.parse.quote(profile.name)
        return f"vless://{profile.uuid}@{profile.address}:{profile.port}?{query}#{name}"
    
    @staticmethod
    def _to_trojan_url(profile: ServerProfile) -> str:
        """Convert profile to Trojan URL"""
        params = {"type": profile.network}
        if profile.sni:
            params["sni"] = profile.sni
        if profile.ws_path:
            params["path"] = profile.ws_path
        
        query = urllib.parse.urlencode(params)
        name = urllib.parse.quote(profile.name)
        return f"trojan://{profile.password}@{profile.address}:{profile.port}?{query}#{name}"
    
    @staticmethod
    def _to_ss_url(profile: ServerProfile) -> str:
        """Convert profile to Shadowsocks URL"""
        user_info = f"{profile.ss_method}:{profile.password}"
        encoded = base64.urlsafe_b64encode(user_info.encode()).decode().rstrip("=")
        name = urllib.parse.quote(profile.name)
        return f"ss://{encoded}@{profile.address}:{profile.port}#{name}"
    
    @staticmethod
    def _to_ssh_url(profile: ServerProfile) -> str:
        """Convert profile to SSH URL"""
        name = urllib.parse.quote(profile.name)
        return f"ssh://{profile.username}:{profile.password}@{profile.address}:{profile.port}#{name}"
