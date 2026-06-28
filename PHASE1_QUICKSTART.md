# Phase 1 Demo: Dementia Memory System Quick Start

## What's New

✅ **ASL Mode + Pinch Integration** — Pinch thumb & index fingers for 1.5 seconds in GRID mode to enter ASL  
✅ **Phase 1 Object Teaching** — Teach the system about personal objects with full context  
✅ **Caregiver Dashboard** — Web interface to monitor all objects  

---

## Quick Demo (5 minutes)

### Step 1: Test Pinch-to-ASL in GRID Mode
```bash
python index.py
# In GRID mode, pinch thumb + index finger for 1.5 seconds
# Should see: "↔ PINCH HOLD FOR ASL MODE ↔"
# Release = enters ASL mode automatically
```

### Step 2: Teach an Object to the System
```python
from memory.object_model import EnhancedMemoryVault, PersonalObject
import datetime

vault = EnhancedMemoryVault()

# Create a test object
obj = PersonalObject(
    id="test_wedding_ring",
    name="Wedding Ring",
    category="personal",
    importance=5,  # High priority
    location="left nightstand drawer",
    description="Gold wedding ring from grandmother",
    routines=["morning", "bedtime"]
)

# Save to vault
vault.add_object(obj)
print(f"✅ Saved '{obj.name}' to memory vault")

# Later... retrieve it
retrieved = vault.get_object("test_wedding_ring")
print(f"Found: {retrieved.name} in {retrieved.location}")
```

### Step 3: Run Caregiver Dashboard
```bash
# Terminal 1: Run keyboard app
python index.py

# Terminal 2: Start dashboard
python caregiver_web.py

# Open browser: http://localhost:5000
# See dashboard with all objects
```

---

## Architecture: Phase 1 Components

### `memory/object_model.py` — Core Storage
```
PersonalObject
├── id, name, category, importance
├── location (where person keeps it)
├── photo_paths (3+ reference images)
├── voice_path (audio description)
├── relationships (links to other objects)
├── routines (morning, bedtime, etc)
└── metadata (created_at, last_seen, detection_count)

EnhancedMemoryVault
├── SQLite database (objects.db)
├── File storage (/memory/objects/)
└── Methods: add_object(), get_object(), mark_detected()
```

### `memory/teach_module.py` — Teaching Workflow
```
TeachSession (state machine)
├── IDLE → Show object to camera
├── CAPTURING → Take 3 reference photos
├── NAMING → "What is this?"
├── IMPORTANCE → "How important? (1-5)"
├── LOCATION → "Where do you keep it?"
├── VOICE → Record description
├── REVIEW → Confirm save
└── SAVED → Ready for next object
```

### `caregiver_web.py` — Dashboard
```
Flask web app:
- /api/objects → List all objects
- /api/stats → Dashboard statistics
- / → HTML dashboard (auto-updates every 5s)
```

---

## Key Features: Phase 1

| Feature | Description |
|---------|-----------|
| **Object Context** | Name + location + importance + voice description |
| **Photo Reference** | 3+ angles for visual recognition |
| **Location Tagging** | "bedroom dresser" helps person remember where |
| **Importance Levels** | 5 = medication, 4 = keys, 3 = glasses, etc |
| **Voice Recording** | "This is your wedding ring from..." |
| **Family Relationships** | Link objects (e.g., "left shoe" → "right shoe") |
| **Routines** | Mark as morning/bedtime object for reminders |
| **Detection Tracking** | Know how many times object was found |

---

## Integration with Index.py

### Current Changes:
1. **Pinch Detection** (index.py line ~530)
   - Added thumb + index finger distance check
   - When distance < 40 pixels AND held for PINCH_HOLD (1.5s) → enters ASL mode
   - Visual feedback: "↔ PINCH HOLD FOR ASL MODE ↔"

2. **State Variables** (index.py line ~370)
   - Added: `pinch_active`, `pinch_start` for gesture tracking

3. **Enhanced Imports** (memo_mode.py)
   - Now uses `EnhancedMemoryVault` instead of old `MemoryVault`
   - Added `TeachSession` for Phase 1 workflow

---

## Next Steps: Phase 2 (Time-based Reminders)

```python
# Coming soon...

class RoutineReminder:
    def __init__(self):
        self.routines = {
            "morning": {
                "time": (8, 0),  # 8 AM
                "objects": ["meditation_glasses", "medication"],
                "message": "Good morning! Where are your glasses?"
            },
            "bedtime": {
                "time": (21, 0),  # 9 PM
                "objects": ["wedding_ring", "phone_charger"],
                "message": "It's time for bed. Make sure you have..."
            }
        }
    
    def check(self):
        """Check if any reminders should fire based on current time"""
        # Implementation coming Phase 2
```

---

## Testing Checklist

- [ ] Pinch in GRID mode enters ASL without pressing key
- [ ] Can create PersonalObject and save to vault
- [ ] Can retrieve object by ID
- [ ] Dashboard loads at http://localhost:5000
- [ ] Dashboard shows stats and object list
- [ ] Can run index.py and caregiver_web.py simultaneously

---

## File Structure

```
keyboard/
├── index.py                    (pinch-to-ASL integration ✅)
├── memo_mode.py               (Phase 1 imports ✅)
├── caregiver_web.py          (NEW - dashboard)
├── memory/
│   ├── __init__.py
│   ├── object_model.py        (NEW - Phase 1 core)
│   ├── teach_module.py        (NEW - teaching workflow)
│   ├── vault.py               (existing - compatibility)
│   ├── embedder.py            (existing)
│   ├── matcher.py             (existing)
│   ├── routines.py            (existing)
│   └── voice.py               (existing)
├── memory/
│   ├── objects/
│   │   ├── photos/            (reference images)
│   │   ├── voices/            (audio recordings)
│   │   └── objects.db         (SQLite)
└── DEMENTIA_MEMORY_PLAN.md    (full implementation guide)
```

---

## Running the Full Demo

### Terminal 1: Main keyboard app
```bash
cd c:\Users\simra\keyboard
python index.py
```

### Terminal 2: Caregiver dashboard
```bash
cd c:\Users\simra\keyboard
python caregiver_web.py
```

### Terminal 3: Optional - View database
```bash
cd c:\Users\simra\keyboard
sqlite3 memory/objects.db
sqlite> SELECT name, importance, location FROM objects;
```

---

## Troubleshooting

**Q: Pinch doesn't trigger ASL mode**  
A: Make sure your thumb (landmark #4) and index finger (landmark #8) are close together (<40 pixels)

**Q: Dashboard won't load**  
A: Check that Flask is installed (`pip install flask`), and port 5000 is free

**Q: Objects don't save**  
A: Verify `/memory/objects/` directory exists and is writable

---

## Questions?

See [DEMENTIA_MEMORY_PLAN.md](DEMENTIA_MEMORY_PLAN.md) for full 8-week roadmap and architecture details.
