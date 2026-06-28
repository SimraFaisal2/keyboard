**AGENTS — AI agent instructions for this repo**

Purpose: give concise, actionable guidance for AI coding agents working on this project.

Key entrypoints
- **Spec:** [model_spec.md](model_spec.md)
- **Data collection:** [collect_data.py](collect_data.py)
- **Training:** [train_model.py](train_model.py)
- **App / runtime:** [index.py](index.py)

Quick workflow (Windows)
- Create venv: `python -m venv .venv`
- Activate: `.venv\Scripts\activate`
- Install (preferred): `pip install -r requirements.txt` (or see suggested list below)
- Collect data: `python collect_data.py`
- Train model: `python train_model.py`
- Run app: `python index.py`

Conventions and artifacts
- Sequence shape: 30 frames × 63 features (21 landmarks × 3). Code assumes `SEQUENCES=30`.
- Data layout: `data/{GESTURE}/{seq}/sequence.npy` and `data/typing/sessions.jsonl`.
- Model artifacts: `model.keras`, `labels.npy`, `confusion_matrix.png`, `training_history.png`.

Common pitfalls
- `index.py` imports `ollama` and other system-level tools — verify availability or stub/remove when running tests.
- TensorFlow on Windows may require `tensorflow-cpu` if default install fails; prefer using the environment described above.
- Camera/OpenCV permissions can cause silent failures during `collect_data.py` or `index.py` runs.

Guidance for AI agents
- Follow "link, don't embed": link to existing docs instead of copying large sections.
- Make minimal, reversible changes. Prefer adding tests, `requirements.txt`, or small helper scripts over large refactors.
- When adding run or CI automation, ensure camera- or hardware-dependent pieces are optional or mocked.

Suggested next customizations
- `requirements.txt` — pin observed packages: `numpy`, `opencv-python`, `mediapipe`, `tensorflow`, `scikit-learn`, `matplotlib`, `seaborn`, `symspellpy`, `pytesseract`, `pyautogui`, `pyttsx3`, `ollama`.
- `predictor.py` — minimal placeholder for the transformer-based predictor proposed in `model_spec.md`.
- Lightweight CI job that installs deps, runs a short smoke test of `train_model.py` (with a tiny synthetic dataset) and checks `index.py` imports.

If you want changes tailored to a specific area (training, inference, CI), tell me which and I'll propose the exact files to create or edit.
