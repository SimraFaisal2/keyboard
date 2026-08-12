"""
reminders.py — Phase 2: Time-based routine reminders with voice cues.
Triggers reminders based on time of day, object detection, location changes.
"""

import datetime
import pyttsx3
from typing import List, Dict, Optional, Callable
from enum import Enum
import json
import os


class ReminderType(Enum):
    """Types of reminders for different contexts."""
    MORNING = "morning"
    MEDICATION = "medication"
    LUNCH = "lunch"
    EVENING = "evening"
    BEDTIME = "bedtime"
    ROUTINE = "routine"


class VoiceCue:
    """Voice reminder with appropriate tone for dementia patients."""
    
    VOICE_RATES = {
        "calm": 100,      # Slow, reassuring
        "clear": 120,     # Normal but clear
        "urgent": 80,     # Very slow for emergencies
    }
    
    def __init__(self, message: str, voice_type: str = "calm"):
        """
        Args:
            message: Text to speak
            voice_type: "calm" (100 wpm), "clear" (120 wpm), "urgent" (80 wpm)
        """
        self.message = message
        self.voice_type = voice_type
        self.rate = self.VOICE_RATES.get(voice_type, 100)
    
    def speak(self, tts_engine: pyttsx3.init):
        """Deliver voice cue with appropriate tone."""
        try:
            original_rate = tts_engine.getProperty('rate')
            tts_engine.setProperty('rate', self.rate)
            tts_engine.say(self.message)
            tts_engine.runAndWait()
            tts_engine.setProperty('rate', original_rate)
        except Exception as e:
            print(f"⚠️  Voice cue failed: {e}")


class RoutineReminder:
    """Manages time-based reminders for routines."""
    
    def __init__(self, vault=None, tts_engine=None):
        self.vault = vault
        self.tts = tts_engine or pyttsx3.init()
        self.last_reminder_time: Dict[str, float] = {}
        self.reminder_cooldown = 300  # 5 minutes between same reminders
        
        # Define routines by time of day
        self.routines = {
            ReminderType.MORNING: {
                "time": (8, 0),
                "enabled": True,
                "objects": ["reading_glasses", "meditation_chair", "coffee_cup"],
                "prompts": [
                    "Good morning! Where are your glasses?",
                    "Time to meditate. Is your chair ready?",
                    "Would you like some coffee?",
                ]
            },
            ReminderType.MEDICATION: {
                "time": (12, 0),
                "enabled": True,
                "objects": ["pill_bottle", "water_glass"],
                "prompts": [
                    "It's time to take your medication. Where is your pill bottle?",
                    "Take your medication with water.",
                ]
            },
            ReminderType.LUNCH: {
                "time": (12, 30),
                "enabled": True,
                "objects": None,
                "prompts": [
                    "It's lunchtime. Are you hungry?",
                ]
            },
            ReminderType.EVENING: {
                "time": (18, 0),
                "enabled": True,
                "objects": ["house_keys", "wallet"],
                "prompts": [
                    "Evening check: Where are your keys?",
                    "Don't forget your wallet.",
                ]
            },
            ReminderType.BEDTIME: {
                "time": (21, 0),
                "enabled": True,
                "objects": ["wedding_ring", "phone_charger", "bedroom_slippers"],
                "prompts": [
                    "It's getting late. Let's prepare for bed.",
                    "Don't forget to charge your phone.",
                    "Your slippers are ready.",
                ]
            }
        }
        
        self.activity_log: List[dict] = []
        self.log_file = "memory/activity_log.jsonl"
        self._ensure_log_file()
    
    def _ensure_log_file(self):
        """Create activity log file if it doesn't exist."""
        os.makedirs("memory", exist_ok=True)
        if not os.path.exists(self.log_file):
            open(self.log_file, 'w').close()
    
    def log_activity(self, event_type: str, details: dict):
        """Log activity with timestamp."""
        entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "event": event_type,
            **details
        }
        self.activity_log.append(entry)
        
        # Write to file
        try:
            with open(self.log_file, 'a') as f:
                f.write(json.dumps(entry) + '\n')
        except Exception as e:
            print(f"⚠️  Failed to log activity: {e}")
    
    def check_time_reminders(self) -> Optional[VoiceCue]:
        """Check if any time-based reminder should trigger."""
        now = datetime.datetime.now()
        current_time = (now.hour, now.minute)
        
        for reminder_type, routine in self.routines.items():
            if not routine["enabled"]:
                continue
            
            routine_time = routine["time"]
            
            # Check if current time matches routine (within 1 minute window)
            if (current_time[0] == routine_time[0] and 
                abs(current_time[1] - routine_time[1]) < 1):
                
                # Check cooldown to avoid repeating
                key = f"{reminder_type.value}_{current_time[0]}"
                last_time = self.last_reminder_time.get(key, 0)
                
                if (now.timestamp() - last_time) > self.reminder_cooldown:
                    self.last_reminder_time[key] = now.timestamp()
                    
                    # Get random prompt
                    import random
                    prompt = random.choice(routine["prompts"])
                    
                    self.log_activity("routine_reminder", {
                        "routine": reminder_type.value,
                        "prompt": prompt
                    })
                    
                    return VoiceCue(prompt, voice_type="calm")
        
        return None
    
    def check_detection_reminders(self, detected_objects: List[str]) -> List[VoiceCue]:
        """Generate reminders based on detected objects."""
        cues = []
        
        for obj_name in detected_objects:
            # Check if object has associated reminder
            if self.vault:
                obj = self.vault.get_object(obj_name)
                if obj and hasattr(obj, 'routines'):
                    for routine in obj.routines:
                        prompt = f"I see your {obj_name}. Remember to {routine}."
                        cues.append(VoiceCue(prompt, voice_type="clear"))
                        
                        self.log_activity("detection_reminder", {
                            "object": obj_name,
                            "routine": routine
                        })
        
        return cues
    
    def get_missing_objects_reminder(self) -> Optional[VoiceCue]:
        """Remind user if expected objects are missing."""
        now = datetime.datetime.now()
        current_hour = now.hour
        
        # Morning check (after 8 AM)
        if 8 <= current_hour < 12:
            if self.vault:
                objects = self.vault.list_objects()
                high_priority = [o for o in objects if o.importance >= 4]
                
                if high_priority:
                    missing = []
                    for obj in high_priority:
                        if not obj.last_seen or (
                            now - obj.last_seen
                        ).total_seconds() > 3600:
                            missing.append(obj.name)
                    
                    if missing:
                        msg = f"I haven't seen your {', '.join(missing[:2])}. "
                        msg += f"Do you remember where they are?"
                        
                        self.log_activity("missing_object_reminder", {
                            "objects": missing
                        })
                        
                        return VoiceCue(msg, voice_type="clear")
        
        return None
    
    def get_activity_log(self, hours: int = 24) -> List[dict]:
        """Retrieve recent activity log (in-memory + persisted file)."""
        cutoff = datetime.datetime.now() - datetime.timedelta(hours=hours)

        # In-memory entries from this session
        entries = list(self.activity_log)

        # Entries persisted by previous runs
        if os.path.exists(self.log_file):
            try:
                with open(self.log_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            entries.append(json.loads(line))
                        except Exception:
                            continue
            except Exception as e:
                print(f"⚠️  Failed to read activity log: {e}")

        # De-duplicate (session entries exist both in memory and on disk)
        seen = set()
        recent = []
        for entry in entries:
            try:
                key = (
                    entry.get("timestamp"),
                    entry.get("event"),
                    json.dumps(entry.get("details", {}), sort_keys=True),
                )
            except Exception:
                key = json.dumps(entry, sort_keys=True)
            if key in seen:
                continue
            seen.add(key)
            try:
                entry_time = datetime.datetime.fromisoformat(entry["timestamp"])
            except Exception:
                continue
            if entry_time >= cutoff:
                recent.append(entry)

        recent.sort(key=lambda e: e.get("timestamp", ""))
        return recent
    
    def export_activity_report(self, filepath: str = "memory/activity_report.json"):
        """Export activity log for caregiver review."""
        try:
            with open(filepath, 'w') as f:
                json.dump(self.activity_log, f, indent=2)
            return True
        except Exception as e:
            print(f"⚠️  Failed to export report: {e}")
            return False
    
    def set_routine_enabled(self, routine_type: ReminderType, enabled: bool):
        """Enable/disable specific routine."""
        if routine_type in self.routines:
            self.routines[routine_type]["enabled"] = enabled
            self.log_activity("routine_config_changed", {
                "routine": routine_type.value,
                "enabled": enabled
            })
