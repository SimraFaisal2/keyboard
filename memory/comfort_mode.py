"""
comfort_mode.py — Phase 4: Emotional support for anxiety/agitation.
Plays calming audio, shows family photos, validates emotions.
"""

import cv2
import numpy as np
import os
import json
from typing import List, Optional, Dict
import pyttsx3
from datetime import datetime


class ComfortMode:
    """Provides emotional support during anxiety or agitation."""
    
    COMFORT_MESSAGES = {
        "anxiety": [
            "It's okay, you're safe here.",
            "Take a deep breath. I'm here with you.",
            "Everything is going to be alright.",
            "You are loved and cared for.",
        ],
        "confusion": [
            "Let me help you remember. What would you like to know?",
            "We can figure this out together.",
            "That's okay, it happens to everyone.",
            "Let me show you something familiar.",
        ],
        "agitation": [
            "Let's take a moment to relax.",
            "I understand you're feeling frustrated.",
            "Would you like to sit down for a moment?",
            "Let's find something calming to do.",
        ],
        "loneliness": [
            "You are not alone. I'm here.",
            "Would you like to see photos of your family?",
            "Let me tell you about someone special.",
            "Your family loves you very much.",
        ]
    }
    
    def __init__(self, tts_engine=None):
        self.tts = tts_engine or pyttsx3.init()
        self.active = False
        self.family_photos_dir = "memory/family_photos"
        self.comfort_audio_dir = "memory/comfort_audio"
        self._ensure_directories()
        
        self.family_relations: Dict[str, dict] = {}
        self._load_family_relations()
    
    def _ensure_directories(self):
        """Create directories if they don't exist."""
        for d in [self.family_photos_dir, self.comfort_audio_dir]:
            os.makedirs(d, exist_ok=True)
    
    def _load_family_relations(self):
        """Load family information from disk."""
        filepath = "memory/family_relations.json"
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r') as f:
                    self.family_relations = json.load(f)
            except Exception as e:
                print(f"⚠️  Failed to load family relations: {e}")
    
    def add_family_member(self, name: str, relation: str, photo_path: Optional[str] = None,
                          voice_path: Optional[str] = None):
        """Register family member for comfort mode."""
        self.family_relations[name] = {
            "name": name,
            "relation": relation,  # "grandson", "daughter", etc.
            "photo_path": photo_path,
            "voice_path": voice_path,
            "added_at": datetime.now().isoformat()
        }
        self._save_family_relations()
    
    def _save_family_relations(self):
        """Save family information to disk."""
        try:
            with open("memory/family_relations.json", 'w') as f:
                json.dump(self.family_relations, f, indent=2)
        except Exception as e:
            print(f"⚠️  Failed to save family relations: {e}")
    
    def activate_comfort_mode(self, emotion: str = "anxiety") -> str:
        """Activate comfort mode for specific emotion."""
        self.active = True
        
        # Select comfort message
        messages = self.COMFORT_MESSAGES.get(emotion, self.COMFORT_MESSAGES["anxiety"])
        import random
        message = random.choice(messages)
        
        # Speak in very calm voice
        self.tts.setProperty('rate', 90)  # Very slow
        self.tts.say(message)
        self.tts.runAndWait()
        
        return message
    
    def show_family_gallery(self, frame: np.ndarray) -> np.ndarray:
        """Display family photo gallery on screen."""
        if not self.family_relations:
            return frame
        
        h, w = frame.shape[:2]
        
        # Create gallery section
        family_text = "👨‍👩‍👧‍👦 Your Family"
        cv2.putText(frame, family_text, (20, 40),
                   cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 2)
        
        y_offset = 80
        for name, info in list(self.family_relations.items())[:5]:
            text = f"{name} ({info['relation']})"
            cv2.putText(frame, text, (20, y_offset),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
            y_offset += 40
        
        return frame
    
    def get_family_introduction(self, name: str) -> Optional[str]:
        """Get introduction for family member."""
        if name not in self.family_relations:
            return None
        
        info = self.family_relations[name]
        relation = info.get('relation', 'family member')
        return f"This is {name}, your {relation}. They care about you very much."
    
    def deactivate_comfort_mode(self):
        """Exit comfort mode."""
        self.active = False
        msg = "Thank you for spending time with me. You're doing great!"
        self.tts.setProperty('rate', 100)
        self.tts.say(msg)
        self.tts.runAndWait()


class SpatialMemory:
    """Phase 4: Remember room layout and object locations."""
    
    def __init__(self):
        self.rooms: Dict[str, dict] = {}
        self.current_room = None
        self._load_rooms()
    
    def _load_rooms(self):
        """Load room layout from disk."""
        filepath = "memory/room_layouts.json"
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r') as f:
                    self.rooms = json.load(f)
                    if self.rooms:
                        self.current_room = list(self.rooms.keys())[0]
            except Exception as e:
                print(f"⚠️  Failed to load room layouts: {e}")
    
    def _save_rooms(self):
        """Save room layout to disk."""
        try:
            with open("memory/room_layouts.json", 'w') as f:
                json.dump(self.rooms, f, indent=2)
        except Exception as e:
            print(f"⚠️  Failed to save room layouts: {e}")
    
    def add_room(self, room_name: str, description: str = ""):
        """Register a new room."""
        self.rooms[room_name] = {
            "name": room_name,
            "description": description,
            "object_zones": {},  # "bed": [x1, y1, x2, y2]
            "created_at": datetime.now().isoformat()
        }
        if not self.current_room:
            self.current_room = room_name
        self._save_rooms()
    
    def set_current_room(self, room_name: str):
        """Set the current room context."""
        if room_name in self.rooms:
            self.current_room = room_name
    
    def add_object_zone(self, room_name: str, object_name: str, 
                        x1: int, y1: int, x2: int, y2: int):
        """Mark where an object typically is in a room."""
        if room_name not in self.rooms:
            self.add_room(room_name)
        
        self.rooms[room_name]["object_zones"][object_name] = {
            "coords": [x1, y1, x2, y2],
            "updated_at": datetime.now().isoformat()
        }
        self._save_rooms()
    
    def where_is_object(self, object_name: str, room_name: Optional[str] = None) -> Optional[str]:
        """Get spatial description of object location."""
        room = room_name or self.current_room
        if not room or room not in self.rooms:
            return None
        
        zones = self.rooms[room]["object_zones"]
        if object_name not in zones:
            return None
        
        coords = zones[object_name]["coords"]
        x1, y1, x2, y2 = coords
        
        # Describe location in natural language
        if x1 < 320:  # Camera width typically 640
            horizontal = "left side"
        else:
            horizontal = "right side"
        
        if y1 < 240:  # Camera height typically 480
            vertical = "top"
        else:
            vertical = "bottom"
        
        return f"Your {object_name} is on the {vertical} {horizontal} of {room}"
    
    def draw_spatial_overlay(self, frame: np.ndarray, room_name: Optional[str] = None) -> np.ndarray:
        """Draw spatial zones on camera frame."""
        room = room_name or self.current_room
        if not room or room not in self.rooms:
            return frame
        
        zones = self.rooms[room]["object_zones"]
        
        # Draw zones
        for obj_name, zone_data in zones.items():
            x1, y1, x2, y2 = zone_data["coords"]
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 100), 2)
            cv2.putText(frame, obj_name, (x1, y1 - 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 100), 2)
        
        # Show room name
        cv2.putText(frame, f"Room: {room}", (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        
        return frame
    
    def get_room_summary(self, room_name: Optional[str] = None) -> str:
        """Get text summary of room contents."""
        room = room_name or self.current_room
        if not room or room not in self.rooms:
            return "No room selected"
        
        zones = self.rooms[room]["object_zones"]
        if not zones:
            return f"No objects registered in {room}"
        
        objects = ", ".join(zones.keys())
        return f"In {room}, you have: {objects}"
