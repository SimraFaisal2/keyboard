# MemoryMate (MEMO) — Assistive Communication & Memory System

<img src="photo.png" alt="Simra Faisal" width="140" align="right"/>

An on-device assistive system for people with limited mobility, speech difficulties, or early cognitive decline — plus a caregiver dashboard for visibility without being intrusive.

> **Elevator pitch:** camera-first interaction (hand gestures, air writing, sign input) combined with a dementia-support layer — teach personal objects, guide daily routines, trigger calm reminders, and share a caregiver dashboard. Everything runs locally for privacy and low friction.

## What it solves

Standard keyboards and phones are hard to use for the primary users, while familiar objects and routines become harder to track without support. MemoryMate replaces that with:

- **Camera-first interaction** — MediaPipe hand tracking for hover, pinch, and sign input
- **Local memory storage** — objects, routines, and logs stay on-device
- **Caregiver-aware assistance** — visibility without being intrusive

## Modes

| Mode | What it does |
| --- | --- |
| `GRID` | Hover-to-click virtual keyboard with word prediction |
| `AIR` | Pinch-to-draw air writing with OCR support |
| `ASL` | Sign-based typing from hand landmarks |
| `ASSIST` | Emergency gesture recognition (help / pain / water / urgent) with spoken alerts |
| `MEMO` | Personal object memory, reminders, comfort, and caregiver support |

## Dementia support features

- **Patient profile** — preferred name, voice rate, contacts, triggers, safe places
- **Editable routines** — morning, medication, bedtime, and other caregiver-defined routines
- **Guided tasks** — step-by-step prompts for medication, bedtime prep, and more
- **Comfort mode** — validation prompts, family photos, calming support
- **Safety monitor** — records possible exit-risk events with explicit uncertainty
- **Caregiver reports** — daily summaries that separate facts from interpretation

## Run locally

Requires Python 3.9+.

```bash
# 1) Install the core deps (fast, reliable — everything the web app needs)
pip install -r requirements-core.txt

# 2) Start the app (patient + caregiver in one process)
python memory_mate.py          # serves on http://localhost:5000
```

Open http://localhost:5000 — patient pages (`/`, `/objects`, `/family`,
`/comfort`, `/tasks`, `/today`) and the caregiver console at `/caregiver`.

> **Optional — camera/gesture modes (GRID / AIR / ASL / ASSIST):** those
> modules additionally need MediaPipe, PyAutoGUI, pytesseract (plus the
> tesseract binary), and the rest of `requirements.txt`. The main app does
> not require them.

Standalone helpers: `caregiver_dashboard.py` is the local Flask dashboard
for objects, routines, tasks, and logs; `caregiver_web.py` is the older
caregiver server.

## Privacy

Everything runs on-device. No cloud account, no data leaves the machine — speech prompts use offline TTS and all memory is stored locally.

## Project status

See `ALL_PHASES_COMPLETE.md` / `FINAL_STATUS.md` for the build-out history, `PORTFOLIO.md` for a one-page demo/interview guide, and `AGENTS.md` for development conventions.
