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

---

## Camera app — `index.py` (Emergency AI Communication Interface)

The camera-first interface behind the gesture modes: a hand-tracked virtual
keyboard, air writing, and sign input, all controlled by your fingers in front
of a webcam (MediaPipe hand tracking).

### Modes

| Mode | What it does |
| --- | --- |
| `GRID`   | Hover-to-click virtual keyboard with live word prediction (type by hovering each key) |
| `AIR`    | Pinch thumb + index together and write in the air; pause 1.5 s to auto-read the character (OCR) |
| `ASL`    | Hold a single-letter hand sign steady to type (A B C D E F I K L O R U V W X Y) |
| `ASSIST` | Emergency gestures (HELP / EMERGENCY / PAIN / WATER / FOOD / TOILET / YES / NO) — needs `train_model.py` to build the model first |
| `MEMO`   | Personal object memory — teach an object, say its name, recall it later |

### Run it

```bash
pip install -r requirements.txt        # heavy deps: mediapipe, pyautogui, pytesseract, symspellpy
python index.py                        # opens your webcam (GRID mode from the main menu)
python index.py --camera 1             # pick a different webcam index
python index.py --demo                 # self-driving tour — NO webcam needed
```

The `--demo` flag drives a synthetic hand through the real state machine
(main menu → type "HELP" on the GRID keyboard → tap a word suggestion →
AIR pinch-drawing → back to the menu), so the project can be demonstrated on
any machine — no camera required.

Controls: hover a key for ~0.45 s to click it; pinch thumb + index for 1.5 s in
GRID mode to switch to ASL; show two open palms to escape to the main menu;
press `q` to quit. Note: keys are pressed into whatever window has focus
(`pyautogui`), so point it at a text editor to see the output.

> **Demo tip:** `--demo` keeps keystrokes on-screen only — it won't type into
> your other apps. Pass `--real-keys` to also send real keystrokes. The window
> opens resized to fit small screens (drag to resize; content is 1280×720).
