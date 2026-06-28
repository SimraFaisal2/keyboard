# MEMO Portfolio & Interview Guide

One-page reference for demos, interviews, and README material.

---

## Elevator Pitch

> I built an on-device assistive communication and memory system that combines hand-gesture control, air writing, sign-language input, emergency gesture recognition, and a dementia support layer called MEMO. The app lets users teach personal objects, guide daily routines, trigger calm reminders, and share a caregiver dashboard. Everything runs locally for privacy and low friction.

---

## What It Solves

**Primary users:** people with limited mobility, speech difficulties, or early cognitive decline, plus caregivers who need visibility without being intrusive.

**Core problem:** standard keyboards and phones are hard to use, while familiar objects and routines become harder to track without support.

**Approach:** camera-first interaction, gesture-based control, local memory storage, and caregiver-aware assistance.

---

## Product Summary

| Area | What it does |
|------|--------------|
| Hand input | MediaPipe-based hand tracking for hover, pinch, and sign input |
| Emergency mode | Gesture classifier for help / pain / water / urgent cues |
| Memory mode | Teach and recall personal objects with location and context |
| Dementia support | Routine prompts, comfort mode, guided tasks, safety events |
| Caregiver view | Local Flask dashboard for objects, routines, tasks, and logs |
| Speech | Offline TTS prompts with calm voice settings |

---

## Modes

| Mode | What it does |
|------|--------------|
| `GRID` | Hover-to-click virtual keyboard with word prediction |
| `AIR` | Pinch-to-draw air writing with OCR support |
| `ASL` | Sign-based typing from hand landmarks |
| `ASSIST` | Emergency gesture recognition and spoken alerts |
| `MEMO` | Personal object memory, reminders, comfort, and caregiver support |

---

## Dementia Features

| Feature | Purpose |
|---------|---------|
| Patient profile | Stores preferred name, voice rate, contacts, triggers, and safe places |
| Editable routines | Morning, medication, bedtime, and other caregiver-defined routines |
| Guided tasks | Step-by-step prompts for medication, bedtime prep, and other activities |
| Comfort mode | Validation prompts, family photos, and calming support |
| Safety monitor | Records possible exit-risk events with explicit uncertainty |
| Caregiver reports | Daily summary that separates facts from interpretation |

---

## 2-Minute Demo

1. Open `python index.py` and show the camera UI.
2. Switch to `ASSIST` and trigger a gesture like `WATER` or `HELP`.
3. Switch to `MEMO` and teach a personal object.
4. Recall the object and show the spoken cue plus matching evidence.
5. Open the caregiver dashboard and show routines, tasks, and safety events.
6. Trigger comfort mode and show the calm response flow.

---

## Offline Demo

```powershell
python create_demo_images.py
python collect_memo.py --folder demo_objects/
python evaluate_memo.py --folder demo_objects/
python caregiver_dashboard.py
```

---

## Architecture

```text
Webcam
  -> hand landmarks / ROI
  -> mode router in index.py
  -> MEMO state machine or gesture classifier
  -> local storage and TTS
  -> caregiver dashboard and logs
```

MEMO itself combines:

```text
camera crop -> embedder -> similarity match -> spoken cue
camera context -> task/routine engine -> step guidance
profile + time context -> comfort or safety response
events -> caregiver report
```

---

## Strong Files To Show

| File | Why it matters |
|------|----------------|
| `index.py` | Main runtime and mode switcher |
| `memo_mode.py` | Earlier MEMO interaction flow and camera UI |
| `memo_mode_integrated.py` | Higher-level MEMO orchestration with comfort, family, routines |
| `memory/object_model.py` | Local object vault and metadata |
| `memory/routines.py` | Editable routine and reminder store |
| `memory/task_guidance.py` | Step-by-step task flow |
| `memory/safety_monitor.py` | Conservative safety event tracking |
| `memory/reporting.py` | Caregiver summaries and exports |
| `caregiver_web.py` | Flask dashboard and API layer |
| `train_model.py` | Gesture training pipeline |
| `evaluate_memo.py` | Recall and matching evaluation |

---

## Interview Talking Points

- Accessibility-first interaction: large targets, hover delays, pinch confirmation, calm prompts.
- Privacy by default: local inference and local storage, no cloud dependency.
- Practical ML: gesture classification for fixed actions, embedding retrieval for open-ended object memory.
- Caregiver-aware design: dashboard visibility, routine control, and event logging.
- Safe uncertainty: the system reports what it observed, not medical certainty.

---

## Setup

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python index.py
```

If you want the caregiver dashboard separately:

```powershell
python caregiver_web.py
```

---

## Future Work

- Better object matching with stronger embeddings and more reference views
- Better caregiver task editing from the dashboard
- Voice-driven task confirmation
- Optional wearable or tablet form factor
- Analytics for routine adherence and recall trends

---

## Disclaimer

This is an assistive prototype for orientation, reminders, and caregiver support. It is not a medical device, not a diagnostic tool, and not a substitute for human supervision.
