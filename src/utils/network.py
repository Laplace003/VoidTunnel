"""
Network Utilities - Ping, speed test, and network checks
"""

import socket
import time
import subprocess
import threading
from typing import Callable, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor


def tcp_ping(host: str, port: int, timeout: float = 5.0) -> int:
    """
    Perform a TCP ping to measure latency.
    Returns latency in milliseconds, or -1 if failed.
    """
    try:
        start = time.time()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((host, port))
        sock.close()
        latency = int((time.time() - start) * 1000)
        return latency
    except:
        return -1


def batch_ping(servers: list[Tuple[str, str, int]], 
               callback: Callable[[str, int], None] = None,
               max_workers: int = 10) -> dict[str, int]:
    """
    Ping multiple servers concurrently.
    servers: list of (id, host, port) tuples
    callback: function(id, latency) called for each result
    Returns dict of {id: latency}
    """
    results = {}
    
    def ping_server(server_info):
        server_id, host, port = server_info
        latency = tcp_ping(host, port)
        results[server_id] = latency
        if callback:
            callback(server_id, latency)
        return server_id, latency
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        executor.map(ping_server, servers)
    
    return results


def check_internet_connection(timeout: float = 5.0) -> bool:
    """Check if internet is accessible"""
    test_hosts = [
        ("8.8.8.8", 53),      # Google DNS
        ("1.1.1.1", 53),      # Cloudflare DNS
        ("208.67.222.222", 53)  # OpenDNS
    ]
    
    for host, port in test_hosts:
        if tcp_ping(host, port, timeout) >= 0:
            return True
    return False


def check_proxy_connection(host: str = "127.0.0.1", 
                          socks_port: int = 10808,
                          http_port: int = 10809) -> Tuple[bool, str]:
    """Check if the local proxy is working"""
    # Check SOCKS port
    socks_ok = tcp_ping(host, socks_port, 2.0) >= 0
    # Check HTTP port
    http_ok = tcp_ping(host, http_port, 2.0) >= 0
    
    if socks_ok and http_ok:
        return True, "Proxy is running"
    elif socks_ok:
        return True, "SOCKS proxy running, HTTP not available"
    elif http_ok:
        return True, "HTTP proxy running, SOCKS not available"
    else:
        return False, "Proxy not running"


def get_public_ip(use_proxy: bool = False, 
                  proxy_host: str = "127.0.0.1",
                  proxy_port: int = 10809) -> Optional[str]:
    """Get public IP address"""
    import requests
    
    ip_services = [
        "https://api.ipify.org",
        "https://icanhazip.com", 
        "https://ifconfig.me/ip",
        "https://api.ip.sb/ip",
    ]
    
    for url in ip_services:
        try:
            if use_proxy:
                # Use HTTP proxy (port 10809 by default)
                proxies = {
                    'http': f'http://{proxy_host}:{proxy_port}',
                    'https': f'http://{proxy_host}:{proxy_port}',
                }
                response = requests.get(url, proxies=proxies, timeout=10, 
                                        headers={'User-Agent': 'curl/7.68.0'})
            else:
                response = requests.get(url, timeout=10,
                                        headers={'User-Agent': 'curl/7.68.0'})
            
            if response.status_code == 200:
                ip = response.text.strip()
                if ip and len(ip) < 50:  # Valid IP should be short
                    return ip
        except Exception as e:
            continue
    
    return None


def resolve_dns(hostname: str, dns_server: str = "8.8.8.8") -> Optional[str]:
    """Resolve a hostname using a specific DNS server"""
    try:
        result = subprocess.run(
            ["dig", f"@{dns_server}", hostname, "+short"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            ips = result.stdout.strip().split('\n')
            return ips[0] if ips else None
    except:
        pass
    
    # Fallback to system resolver
    try:
        return socket.gethostbyname(hostname)
    except:
        return None


class SpeedTester:
    """Simple download speed tester"""
    
    TEST_URLS = [
        ("Cloudflare", "https://speed.cloudflare.com/__down?bytes=10000000"),
        ("Google", "https://www.google.com/images/branding/googlelogo/2x/googlelogo_color_272x92dp.png"),
    ]
    
    def __init__(self, use_proxy: bool = False, 
                 proxy_host: str = "127.0.0.1",
                 proxy_port: int = 10808):
        self.use_proxy = use_proxy
        self.proxy_host = proxy_host
        self.proxy_port = proxy_port
    
    def test_download_speed(self, callback: Callable[[str, float], None] = None) -> float:
        """
        Test download speed.
        Returns speed in Mbps.
        callback: function(status, speed_mbps) for progress updates
        """
        import urllib.request
        
        for name, url in self.TEST_URLS:
            try:
                if callback:
                    callback(f"Testing with {name}...", 0)
                
                if self.use_proxy:
                    proxy_handler = urllib.request.ProxyHandler({
                        'http': f'socks5://{self.proxy_host}:{self.proxy_port}',
                        'https': f'socks5://{self.proxy_host}:{self.proxy_port}',
                    })
                    opener = urllib.request.build_opener(proxy_handler)
                else:
                    opener = urllib.request.build_opener()
                
                opener.addheaders = [('User-Agent', 'Mozilla/5.0')]
                
                start_time = time.time()
                response = opener.open(url, timeout=30)
                data = response.read()
                elapsed = time.time() - start_time
                
                # Calculate speed in Mbps
                bytes_downloaded = len(data)
                speed_mbps = (bytes_downloaded * 8 / 1_000_000) / elapsed
                
                if callback:
                    callback(f"Completed: {speed_mbps:.2f} Mbps", speed_mbps)
                
                return speed_mbps
                
            except Exception as e:
                if callback:
                    callback(f"Failed with {name}: {str(e)}", 0)
                continue
        
        return 0.0
