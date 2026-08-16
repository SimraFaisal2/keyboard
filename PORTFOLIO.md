# MemoryMate Portfolio & Interview Guide

One-page reference for demos, interviews, and README material.

---

## Elevator Pitch

> I built an on-device assistive communication and memory system that combines hand-gesture control, air writing, sign-language input, emergency gesture recognition, and a dementia support layer called MEMO. The app lets users teach personal objects, guide daily routines, trigger calm reminders, and share a caregiver dashboard. Everything runs locally for privacy and low friction.

**One line for a resume/LinkedIn:**

> MemoryMate — an offline-first assistive system fusing real-time computer vision (MediaPipe hand tracking, InsightFace embeddings, OCR air-writing), gesture-driven accessibility (GRID/AIR/ASL/ASSIST), and a caregiver dashboard over a single shared local data core.

**Alternate lines:**

> Built a camera-driven accessibility platform where a user navigates a virtual keyboard, writes in air, signs, and signals emergencies — with a Flask caregiver console that surfaces every event from one local-first data layer.

> Real-time CV + accessibility + privacy architecture: hand-gesture HCI, biometric face ID via 512-d embeddings, and a unified patient/caregiver system that never leaves the device.

> End-to-end assistive-tech product: from MediaPipe hand landmarks to a caregiver daily report, with memory recall, safety monitoring, and voice enrollment — one command to run, fully offline.

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
| Caregiver view | Local Flask console for objects, routines, tasks, alerts, and logs |
| Face ID | InsightFace embeddings — learn a face by voice, greeted by name |
| Speech | Offline TTS prompts with calm voice settings |

---

## Unified Architecture

**One entry point, three surfaces — all sharing one local data core:**

```text
python memorymate.py --web       →  Flask :5000  (patient pages + /caregiver console)
python memorymate.py --camera    →  gesture interface (GRID/AIR/ASL/FACE/ASSIST/MEMO)
python memorymate.py --demo      →  synthetic-hand tour + auto-starts --web side-by-side

memory/  ← single source of truth
 ├─ objects.db          EnhancedMemoryVault (objects, thumbnails, embeddings)
 ├─ activity_log.jsonl  reminders/tasks/gestures
 ├─ alerts.jsonl        ASSIST-mode HELP/PAIN/urgent gestures (camera → caregiver)
 └─ safety_events.jsonl  exit-risk events, surfaced in the console + daily report
```

The camera app is a **client** of the shared core, not a parallel app: an object taught by camera appears in `/objects`, an emergency gesture lands in the caregiver console and daily report.

---

## Modes

| Mode | What it does |
|------|--------------|
| `GRID` | Hover-to-click virtual keyboard with word prediction |
| `AIR` | Pinch-to-draw air writing with OCR support |
| `ASL` | Sign-based typing from hand landmarks |
| `ASSIST` | Emergency gesture recognition + spoken alerts → caregiver alerts log |
| `FACE` | InsightFace biometric ID — voice-name enrollment, "Hello, <name>" greeting |
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

## 2-Minute Demo (no camera needed)

```bash
python memorymate.py --demo
```

One command spins up the web app **and** runs the synthetic-hand tour together, so a reviewer can watch the whole loop:

1. Teach an object via the camera UI → appears in `/objects`
2. Trigger a routine reminder → logged to activity
3. Signal an emergency gesture (HELP) → lands in `memory/alerts.jsonl`
4. Watch it appear on the caregiver console and in the daily report

---

## Interview Talking Points

- **Real-time CV range:** MediaPipe hand landmarks → hover/pinch HCI, ASL heuristics, OCR air-writing (Tesseract), InsightFace face embeddings for biometric ID.
- **Accessibility-first interaction:** large targets, hover delays, pinch confirmation, calm prompts, voice-driven enrollment.
- **Privacy by default:** local inference and local storage, no cloud dependency — nothing leaves the device.
- **Full-stack integration:** camera client + Flask console reading one shared data core; alerts, recalls, and safety events all surface in the caregiver view and daily report.
- **Safe uncertainty:** the system reports what it observed, not medical certainty.
- **Practical ML:** gesture classification for fixed actions, embedding retrieval (cosine similarity) for open-ended face/object memory.

---

## Architecture

```text
Webcam
  -> hand landmarks / ROI (MediaPipe)
  -> mode router in index.py (GRID/AIR/ASL/FACE/ASSIST/MEMO)
  -> shared local core in memory/ (vault, alerts, activity, safety)
  -> caregiver console + daily report (Flask)
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
| `memorymate.py` | Single unified entry point (`--web` / `--camera` / `--demo`) |
| `index.py` | Camera runtime and mode router |
| `memo_mode.py` | MEMO interaction flow and camera UI |
| `face_mode.py` | InsightFace embedding engine (detect, enroll, greet) |
| `memory/alerts.py` | Camera→caregiver alert bridge (single source of truth) |
| `memory/object_model.py` | Local object vault and metadata |
| `memory/routines.py` | Editable routine and reminder store |
| `memory/task_guidance.py` | Step-by-step task flow |
| `memory/safety_monitor.py` | Conservative safety event tracking |
| `memory/reporting.py` | Caregiver summaries and exports |
| `train_model.py` | Gesture training pipeline |

---

## Setup

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python memorymate.py --demo      # watch the whole loop
python memorymate.py --web       # caregiver console at http://localhost:5000/caregiver
python memorymate.py --camera    # full gesture interface
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
