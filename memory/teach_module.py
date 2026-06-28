"""
teach_module.py — Phase 1 object teaching workflow for dementia memory system.
Guides user: capture photos → name → importance → location → voice description
"""

import cv2
import numpy as np
import time
import os
import uuid
from typing import Optional, List
import pyttsx3
import sounddevice as sd
import soundfile as sf

from memory.object_model import PersonalObject, EnhancedMemoryVault

# ─── Teaching State Machine ───────────────────────────────────────────────────
class TeachSession:
    """One object teaching session."""
    
    STATES = {
        "IDLE": "Ready to teach. Show object to camera.",
        "CAPTURING": "Hold object steady. Capturing photos...",
        "NAMING": "What is this? Say its name:",
        "IMPORTANCE": "How important? (1=misc, 5=medicine):",
        "LOCATION": "Where do you keep this? (e.g., bedroom):",
        "VOICE": "Tell me about it (hold hand up to speak):",
        "REVIEW": "Review and save?",
        "SAVED": "✅ Saved! Next object?"
    }
    
    def __init__(self, vault: EnhancedMemoryVault, tts_engine: pyttsx3.init = None):
        self.vault = vault
        self.tts = tts_engine
        self.state = "IDLE"
        self.obj_id = str(uuid.uuid4())[:8]
        
        # Captures
        self.captured_photos: List[np.ndarray] = []
        self.captured_name: str = ""
        self.captured_importance: int = 3
        self.captured_location: str = ""
        self.captured_voice_path: Optional[str] = None
        
        # Timing
        self.state_start_time = time.time()
        self.capture_interval = 0.5
        self.last_capture = 0
        self.speech_active = False
        
        if self.tts:
            self.tts.setProperty('rate', 100)  # Calm, clear speech
    
    def speak(self, message: str):
        """Speak a message calmly."""
        if self.tts:
            self.tts.say(message)
            self.tts.runAndWait()
        print(f"🎤 {message}")
    
    def next_state(self):
        """Advance to next state."""
        states_list = list(self.STATES.keys())
        current_idx = states_list.index(self.state) if self.state in states_list else 0
        if current_idx < len(states_list) - 1:
            self.state = states_list[current_idx + 1]
            self.state_start_time = time.time()
            self.speak(self.STATES[self.state])
    
    def update(self, frame: np.ndarray, hand_present: bool = False) -> dict:
        """Process one frame. Returns {state, message, action}."""
        elapsed = time.time() - self.state_start_time
        message = self.STATES.get(self.state, "")
        action = None
        
        if self.state == "IDLE":
            if hand_present and elapsed > 0.5:
                self.next_state()  # → CAPTURING
        
        elif self.state == "CAPTURING":
            # Capture 3 photos of the object
            if hand_present and (time.time() - self.last_capture) > self.capture_interval:
                self.captured_photos.append(frame.copy())
                self.last_capture = time.time()
                action = f"captured_{len(self.captured_photos)}_of_3"
                
                if len(self.captured_photos) >= 3:
                    self.next_state()  # → NAMING
        
        elif self.state == "NAMING":
            # Wait for text input or voice
            if self.captured_name:
                self.next_state()  # → IMPORTANCE
        
        elif self.state == "IMPORTANCE":
            # Set importance (1-5) via fingers
            if self.captured_importance > 0:
                self.next_state()  # → LOCATION
        
        elif self.state == "LOCATION":
            # Get location description
            if self.captured_location:
                self.next_state()  # → VOICE
        
        elif self.state == "VOICE":
            # Record voice description
            if self.captured_voice_path:
                self.next_state()  # → REVIEW
        
        elif self.state == "REVIEW":
            # Show summary, confirm save
            message = f"Object: {self.captured_name} | Importance: {self.captured_importance}/5 | Location: {self.captured_location}"
            # If user confirms (e.g., all fingers raised), save
            if elapsed > 2:  # Auto-advance for demo
                self.save_object()
                self.next_state()  # → SAVED
        
        elif self.state == "SAVED":
            if elapsed > 2:
                self.reset()  # Ready for next object
        
        return {
            "state": self.state,
            "message": message,
            "progress": len(self.captured_photos) / 3.0 if self.state == "CAPTURING" else 1.0,
            "action": action
        }
    
    def save_object(self) -> bool:
        """Save captured object to vault."""
        try:
            # Save photos
            photo_paths = []
            for idx, photo in enumerate(self.captured_photos):
                photo_path = os.path.join(self.vault.photos_dir, f"{self.obj_id}_{idx}.jpg")
                cv2.imwrite(photo_path, photo)
                photo_paths.append(photo_path)
            
            # Create object
            obj = PersonalObject(
                id=self.obj_id,
                name=self.captured_name,
                category="personal",  # Can be enhanced
                importance=self.captured_importance,
                location=self.captured_location,
                photo_paths=photo_paths,
                voice_path=self.captured_voice_path,
                description=f"Taught {time.strftime('%Y-%m-%d %H:%M')}"
            )
            
            # Save to vault
            success = self.vault.add_object(obj)
            if success:
                print(f"✅ Saved '{self.captured_name}' to memory vault")
            return success
        except Exception as e:
            print(f"❌ Error saving object: {e}")
            return False
    
    def reset(self):
        """Reset for next object."""
        self.obj_id = str(uuid.uuid4())[:8]
        self.state = "IDLE"
        self.captured_photos = []
        self.captured_name = ""
        self.captured_importance = 3
        self.captured_location = ""
        self.captured_voice_path = None
        self.state_start_time = time.time()


# ─── Voice Recording Helper ───────────────────────────────────────────────────
def record_voice(duration: float = 5.0, output_path: str = "recording.wav") -> Optional[str]:
    """
    Record audio from microphone.
    Args:
        duration: seconds to record
        output_path: where to save WAV file
    Returns: path to saved file, or None if failed
    """
    try:
        print(f"🎤 Recording for {duration} seconds...")
        SAMPLE_RATE = 44100
        audio = sd.rec(int(duration * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=1, dtype=np.int16)
        sd.wait()
        sf.write(output_path, audio, SAMPLE_RATE)
        print(f"✅ Saved recording to {output_path}")
        return output_path
    except Exception as e:
        print(f"❌ Recording error: {e}")
        return None
