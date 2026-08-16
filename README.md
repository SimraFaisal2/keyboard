# MemoryMate — Assistive Communication & Memory System

<img src="photo.png" alt="Simra Faisal" width="140" align="right"/>

**MemoryMate is an on-device communication and memory aid for people with limited mobility, speech difficulties, or early cognitive decline — with a caregiver dashboard that makes everything visible without being intrusive.**

A person who struggles to type or speak can wave at a camera: hover to type on a virtual keyboard, write in the air, sign letters, fire an emergency HELP gesture, or hold up an object and hear it named. A caregiver opens one local dashboard and sees every object taught, every recall, every emergency gesture, and every safety event — no cloud, no account, nothing leaves the device.

## The 10-second demo (no camera, no setup)

```bash
python memorymate.py --demo
```

That one command runs the **synthetic-hand camera tour** *and* the **caregiver dashboard** together: the hand types HELP on the virtual keyboard while the dashboard fills with labelled DEMO events — an object taught, an emergency gesture fired, a safety event — so the whole loop is visible in under two minutes.

## Quickstart

Requires Python 3.9+.

```bash
# Everything the web app needs (fast, reliable install)
pip install -r requirements-core.txt

# One entry point, four surfaces:
python memorymate.py            # web app — patient pages + caregiver console (:5000)
python memorymate.py --web      # same as above (default mode)
python memorymate.py --camera   # camera/gesture interface (needs requirements.txt + webcam)
python memorymate.py --demo     # camera-free tour + dashboard, nothing to configure
```

Open `http://localhost:5000` — patient pages (`/`, `/objects`, `/family`,
`/comfort`, `/tasks`, `/today`) and the caregiver console at `/caregiver`.
The caregiver console polls `/api/live`, so camera events appear on it in real
time without reloading.

> **Camera modes need more:** GRID / AIR / ASL / ASSIST / FACE additionally
> require MediaPipe, PyAutoGUI, pytesseract (+ the tesseract binary), and the
> rest of `requirements.txt`. The web app alone does not.

## Architecture — one core, two surfaces

The gesture interface and the web app are **clients of one shared storage
layer** (`memory/`), not parallel apps:

```
                    ┌──────────────────────────────────────┐
                    │            memory/  (local)          │
                    │  objects.db       objects + embeddings│
                    │  recalls.jsonl    camera recognitions │
                    │  gesture_alerts.jsonl  HELP/PAIN…     │
                    │  safety_events.jsonl   exit-risk      │
                    │  activity_log.jsonl  reminders/tasks  │
                    │  routines/ tasks/ family/ profile/    │
                    └───────┬───────────────────────┬───────┘
                            │ reads & writes       │ reads & writes
              ┌─────────────▼──────────┐   ┌────────▼─────────────┐
              │  index.py              │   │  memory_mate.py       │
              │  camera / gesture      │   │  Flask web app        │
              │  GRID AIR ASL FACE     │   │  patient pages        │
              │  ASSIST MEMO           │   │  caregiver console    │
              └─────────────┬──────────┘   └──────────────────────┘
                            │  emergency gestures, recalls
                            └──────────► appear on the dashboard live
```

- **Teach an object in MEMO mode (camera)** → it lands in `objects.db` and
  shows up in the web app's `/objects` and the caregiver console.
- **Fire an emergency gesture (ASSIST)** → it's appended to
  `gesture_alerts.jsonl`, which the caregiver console and the daily report
  (`memory.reporting.CaregiverReport`) both read.
- **Safety monitor events** are written to `safety_events.jsonl` and surfaced
  in the console with explicit uncertainty (facts ≠ interpretation).

## Modes

| Mode | What it does |
| --- | --- |
| `GRID` | Hover-to-click virtual keyboard with live word prediction |
| `AIR` | Pinch thumb + index and write in the air; pause 1.5 s to auto-read (OCR) |
| `ASL` | Hold a single-letter hand sign steady to type (A B C D E F I K L O R U V W X Y) |
| `FACE` | Biometric face identification (InsightFace embeddings) — greet people by voice, teach new faces by speaking their name |
| `ASSIST` | Emergency gestures (HELP / EMERGENCY / PAIN / WATER / FOOD / TOILET / YES / NO) — needs `train_model.py` first |
| `MEMO` | Personal object memory — teach an object, say its name, recall it later |

## Dementia support features

- **Patient profile** — preferred name, voice rate, contacts, triggers, safe places
- **Editable routines** — morning, medication, bedtime, and other caregiver-defined routines
- **Guided tasks** — step-by-step prompts for medication, bedtime prep, and more
- **Comfort mode** — validation prompts, family photos, calming support
- **Safety monitor** — records possible exit-risk events with explicit uncertainty
- **Caregiver reports** — daily summaries that separate facts from interpretation
- **FACE enrolment by voice** — press LEARN, the app captures your face for ~2 s,
  then asks you to say your name; from then on it greets you by name (embeddings
  compared by cosine similarity, threshold 0.5 — robust to lighting/pose drift)

## Privacy

**Everything runs on-device.** No cloud account, no telemetry, no data leaves
the machine — speech prompts use local TTS, recognition runs locally
(MediaPipe / InsightFace / OCR), and all memory, recalls, alerts, and safety
events are stored in the local `memory/` directory. Enrolled biometric data
(`known_faces/`) is gitignored. The caregiver console binds to `127.0.0.1`.

## Repo layout

```
memorymate.py           unified entry point (--web / --camera / --demo)
memory_mate.py          Flask web app: patient pages + caregiver console
index.py                camera/gesture interface (GRID AIR ASL FACE ASSIST MEMO)
face_mode.py            InsightFace embedding engine (FACE mode)
memo_mode.py            object teach/recall state machine (MEMO mode)
memory/                 the shared on-device storage + domain modules
  object_model.py       objects + embeddings (SQLite) + recall log
  alerts.py             gesture-alert bridge between camera and console
  safety_monitor.py     conservative exit-risk monitoring
  reporting.py          daily caregiver reports (facts / interpretation)
  routines.py reminders.py comfort_mode.py task_guidance.py family_relations.py …
templates/              patient.html + caregiver.html
test_demo_mode.py       headless verification of the demo tour
```

## Camera app details

Controls: hover a key for ~0.45 s to click it; pinch thumb + index for 1.5 s in
GRID mode to switch to ASL; show two open palms to escape to the main menu;
press `q` to quit. `--demo` keeps keystrokes on-screen only (no hijacking your
keyboard); pass `--real-keys` to also send real keystrokes. The window opens
resized to fit small screens.

**FACE enrolment:** press LEARN in FACE mode → look at the camera for ~2 s →
say your name when prompted → it saves embeddings under that name and greets
you on every visit. You can also drop photos in `known_faces/<Name>.jpg` or
`known_faces/<Name>/` to pre-seed it.

## Docs

- `PORTFOLIO.md` — one-page interview/demo guide + suggested resume lines
- `AGENTS.md` — development conventions for AI agents working in this repo
- `model_spec.md` — gesture-recognition model spec and data collection
