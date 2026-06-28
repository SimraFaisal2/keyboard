# Dementia Memory Aid Implementation Plan

## Phase 1: Core Memory System (Weeks 1-2)

### 1.1 Object Recognition & Teaching
**Current:** `memo_mode.py` teaches objects via pinch gesture  
**Enhance:**
- [ ] Add **facial recognition** for family photos (teach who is in the photo)
- [ ] Implement **location tagging** (remember where objects belong)
- [ ] Add **context snippets** (when/why you need this, not just what it is)

**Code structure:**
```python
class PersonalObject:
    id: str                    # unique identifier
    photos: List[np.ndarray]  # reference images
    embeddings: np.ndarray     # feature vectors for matching
    name: str                  # "wedding ring"
    voice_path: str            # audio: "This is your wedding ring from..."
    location: str              # "left nightstand drawer"
    relationships: List[str]   # connections to other objects
    last_seen: datetime        # temporal memory
    importance: int            # 1-5 scale (med = 5, keys = 4)
```

### 1.2 Memory Storage (SQLite + Embeddings)
**File structure:**
```
memory/
├── vault.py              # Load/save object database
├── embedder.py          # Extract visual features (SIFT/ORB)
├── matcher.py           # Find similar objects in photos
└── database.db          # SQLite: objects, voice clips, timestamps
```

**Database schema:**
```sql
CREATE TABLE objects (
    id TEXT PRIMARY KEY,
    name TEXT,
    created_at TIMESTAMP,
    last_seen TIMESTAMP,
    voice_file TEXT,
    location TEXT,
    importance INT,
    category TEXT  -- 'medical', 'personal', 'family'
);

CREATE TABLE relationships (
    object_id TEXT,
    related_id TEXT,
    relation TEXT  -- 'stored_in', 'belongs_to'
);

CREATE TABLE reminders (
    id TEXT PRIMARY KEY,
    object_id TEXT,
    reminder_type TEXT,  -- 'morning', 'medication', 'routine'
    time_of_day TEXT,
    voice_prompt TEXT
);
```

---

## Phase 2: Smart Reminding (Weeks 3-4)

### 2.1 Routine-Based Reminders
**Morning routine:**
```python
MORNING_ROUTINE = [
    ("Take medication", "pill_bottle", 8),
    ("Put on glasses", "reading_glasses", 8:15),
    ("Check weather", None, 8:30),
]
```

**Triggered by:**
- [ ] **Time of day** (morning at 8 AM: "Where are your glasses?")
- [ ] **Camera detection** (sees pill bottle → "Take your medication")
- [ ] **Location changes** (person leaves bedroom → routine checklist)

### 2.2 Voice Cuing (TTS + Custom Audio)
**Implementation:**
```python
class VoiceCue:
    def __init__(self, message: str, voice_type: str = "calm"):
        # voice_type: "calm" (120 wpm), "clear" (100 wpm), "urgent" (80 wpm)
        self.message = message
        self.voice_type = voice_type
    
    def speak(self, tts_engine):
        """Deliver cue in appropriate tone"""
        # Dementia patients benefit from slow, reassuring voice
        tts_engine.setProperty('rate', VOICE_RATES[self.voice_type])
        tts_engine.say(self.message)
```

---

## Phase 3: Caregiver Dashboard (Weeks 5-6)

### 3.1 Web Interface (Flask)
```
app/
├── dashboard.py        # Real-time monitoring
├── templates/
│   ├── home.html       # Object catalog
│   ├── reminders.html  # Routine schedule
│   └── history.html    # Activity log
└── static/
    └── style.css
```

**Features:**
- [ ] View all stored objects & their locations
- [ ] Create/edit reminders
- [ ] Review detection history (when objects were recognized)
- [ ] Export memory for caregiver reports

### 3.2 Activity Logging
```python
LOG_FORMAT: {
    "timestamp": "2026-06-28 08:15:30",
    "event": "object_detected",
    "object": "wedding_ring",
    "confidence": 0.92,
    "location": "bedroom",
    "action": "voice_reminder_played"
}
```

---

## Phase 4: Advanced Features (Weeks 7-8)

### 4.1 Emotional Comfort Mode
**For anxiety/agitation:**
- [ ] Play familiar family voice recordings
- [ ] Show photo album of loved ones
- [ ] Validate emotions ("It's okay, I'm here")
- [ ] Play calming music

### 4.2 Spatial Memory (Room Layout)
**Remember room geography:**
```python
class RoomMemory:
    room_name: str           # "bedroom"
    layout: np.ndarray       # camera-view spatial map
    object_zones: dict       # "bed": [x1, y1, x2, y2]
    
    def where_is(self, object_name: str) -> str:
        """Return "Your keys are on the nightstand (right side of camera)"""
```

### 4.3 Family Tree / Relationships
```python
class FamilyRelation:
    person: str      # "John"
    relation: str    # "grandson"
    photo: np.ndarray
    voice: str       # audio saying "Hi, it's your grandson John"
    visits: List[date]
```

---

## Phase 5: UX for Dementia (Throughout)

### Visual Design
- [ ] **Large buttons** (40+ px, high contrast)
- [ ] **Few options** (max 3 choices at a time)
- [ ] **Consistent layout** (same buttons always in same place)
- [ ] **Clear icons** + text (not text alone)

### Interaction
- [ ] **Long-hold gestures** (1-2 sec, gives time to decide)
- [ ] **Voice feedback** on every action ("Okay, I'll find your keys")
- [ ] **Undo capability** (15-sec window to cancel)
- [ ] **No error messages** (redirect, don't scold)

### Example: Better Reminder
```
INSTEAD OF:  "Object not recognized. Try again."
SAY:         "Let me get a clearer look. Can you turn it toward the camera?"
```

---

## Integration with Existing Code

### Quick Start: Enhance Current System

**1. Improve TEACH phase:**
```python
# Add to memo_mode.py - TEACH_CAPTURE state
- Capture 3 angles (front, left, right)
- Ask: "What room is this in?" 
- Ask: "Is this important? (medicine, keys, personal, other)"
- Record voice: "Tell me about this item"
```

**2. Add ROUTINE checking:**
```python
# Before RECALL loop, check if it's:
- Morning (before 9 AM) → play morning checklist
- Lunch time (12-1 PM) → medication reminder
- Evening (6 PM) → "Where are your keys?"
```

**3. Simple caregiver app:**
```python
# Run on phone/tablet on local WiFi
flask run --host=0.0.0.0
# View at: http://[computer-ip]:5000
# Shows: All objects, last seen, confidence scores
```

---

## Recommended Tech Stack

| Component | Library | Why |
|-----------|---------|-----|
| Object Detection | SIFT/ORB | Fast, works on CPU |
| Storage | SQLite | No server needed |
| Voice | pyttsx3 | Offline, works on Windows |
| Web Dashboard | Flask | Lightweight, Python |
| Photo Storage | /memory/photos/ | Local filesystem |
| Embeddings | scikit-learn | KNN matching |

---

## Milestones & Testing

**Week 1:** Teach & store first object  
**Week 2:** Object detection working (camera → match → voice)  
**Week 3:** Time-based reminders (morning routine)  
**Week 4:** Multiple objects (3-5) with different contexts  
**Week 5:** Caregiver can view all objects via web  
**Week 6:** Test with family member (feedback)  
**Week 7:** Refine UX based on feedback  
**Week 8:** Production deployment  

---

## Testing Checklist

- [ ] Can teach object with 3 photos + voice + location
- [ ] Camera detects object at 80%+ confidence
- [ ] Voice reminder plays at correct time
- [ ] Caregiver can see object list on phone
- [ ] Person forgets item → camera finds it → reminder helps
- [ ] Undo works (user can cancel action)
- [ ] No crashes after 2 hours continuous use

---

## Next Step: Which Phase to Start?

**Recommended:** Phase 1 + Phase 2 (most impactful for dementia care)
- Teaches person to identify own objects
- Provides automatic reminders
- Build in 2-3 weeks with existing code

**Requires:** ~500 lines of code + database design
