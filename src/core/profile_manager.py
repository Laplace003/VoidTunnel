"""
Profile Manager - Save, load, and manage VPN server profiles
"""

import os
import json
import uuid
from typing import List, Optional, Dict, Any
from .protocol_parser import ServerProfile, ProtocolParser


class ProfileManager:
    """Manages VPN server profiles (save, load, import, export)"""
    
    def __init__(self, profiles_dir: str = None):
        if profiles_dir is None:
            profiles_dir = os.path.expanduser("~/.config/voidtunnel/profiles")
        self.profiles_dir = profiles_dir
        self.profiles_file = os.path.join(profiles_dir, "profiles.json")
        os.makedirs(profiles_dir, exist_ok=True)
        
        self._profiles: List[ServerProfile] = []
        self._load_profiles()
    
    def _load_profiles(self):
        """Load profiles from disk"""
        if os.path.exists(self.profiles_file):
            try:
                with open(self.profiles_file, 'r') as f:
                    data = json.load(f)
                    self._profiles = [ServerProfile.from_dict(p) for p in data]
            except Exception as e:
                print(f"Error loading profiles: {e}")
                self._profiles = []
    
    def _save_profiles(self):
        """Save profiles to disk"""
        try:
            with open(self.profiles_file, 'w') as f:
                data = [p.to_dict() for p in self._profiles]
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving profiles: {e}")
    
    def get_all(self) -> List[ServerProfile]:
        """Get all profiles"""
        return self._profiles.copy()
    
    def get_by_id(self, profile_id: str) -> Optional[ServerProfile]:
        """Get a profile by its ID"""
        for profile in self._profiles:
            if profile.id == profile_id:
                return profile
        return None
    
    def get_active(self) -> Optional[ServerProfile]:
        """Get the currently active profile"""
        for profile in self._profiles:
            if profile.is_active:
                return profile
        return None
    
    def add(self, profile: ServerProfile) -> ServerProfile:
        """Add a new profile"""
        if not profile.id:
            profile.id = str(uuid.uuid4())
        self._profiles.append(profile)
        self._save_profiles()
        return profile
    
    def add_from_url(self, url: str) -> Optional[ServerProfile]:
        """Parse a URL and add as a new profile"""
        profile = ProtocolParser.parse(url)
        if profile:
            profile.id = str(uuid.uuid4())
            self._profiles.append(profile)
            self._save_profiles()
            return profile
        return None
    
    def update(self, profile: ServerProfile):
        """Update an existing profile"""
        for i, p in enumerate(self._profiles):
            if p.id == profile.id:
                self._profiles[i] = profile
                self._save_profiles()
                return
    
    def delete(self, profile_id: str):
        """Delete a profile by ID"""
        self._profiles = [p for p in self._profiles if p.id != profile_id]
        self._save_profiles()
    
    def set_active(self, profile_id: str):
        """Set a profile as active (deactivates others)"""
        for profile in self._profiles:
            profile.is_active = (profile.id == profile_id)
        self._save_profiles()
    
    def clear_active(self):
        """Clear the active profile"""
        for profile in self._profiles:
            profile.is_active = False
        self._save_profiles()
    
    def import_from_urls(self, urls: str) -> List[ServerProfile]:
        """Import multiple profiles from URLs (one per line)"""
        added = []
        for line in urls.strip().split('\n'):
            url = line.strip()
            if url:
                profile = self.add_from_url(url)
                if profile:
                    added.append(profile)
        return added
    
    def export_to_urls(self, profile_ids: List[str] = None) -> str:
        """Export profiles to URLs"""
        profiles = self._profiles if profile_ids is None else [
            p for p in self._profiles if p.id in profile_ids
        ]
        urls = [ProtocolParser.to_url(p) for p in profiles]
        return '\n'.join(urls)
    
    def import_from_subscription(self, sub_url: str) -> List[ServerProfile]:
        """Import profiles from a subscription URL"""
        import requests
        import base64
        
        try:
            response = requests.get(sub_url, timeout=30)
            response.raise_for_status()
            
            # Try to decode as base64
            try:
                content = base64.b64decode(response.text).decode('utf-8')
            except:
                content = response.text
            
            return self.import_from_urls(content)
        except Exception as e:
            print(f"Error importing subscription: {e}")
            return []
    
    def update_latency(self, profile_id: str, latency: int):
        """Update the latency for a profile"""
        for profile in self._profiles:
            if profile.id == profile_id:
                profile.latency = latency
                self._save_profiles()
                return
    
    def reorder(self, profile_ids: List[str]):
        """Reorder profiles based on the given ID order"""
        id_to_profile = {p.id: p for p in self._profiles}
        self._profiles = [id_to_profile[id] for id in profile_ids if id in id_to_profile]
        self._save_profiles()
    
    def duplicate(self, profile_id: str) -> Optional[ServerProfile]:
        """Duplicate a profile"""
        profile = self.get_by_id(profile_id)
        if profile:
            new_profile = ServerProfile.from_dict(profile.to_dict())
            new_profile.id = str(uuid.uuid4())
            new_profile.name = f"{profile.name} (Copy)"
            new_profile.is_active = False
            self._profiles.append(new_profile)
            self._save_profiles()
            return new_profile
        return None
