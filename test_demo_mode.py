"""Headless verification of index.py --demo mode.

PATCHES (test-only, never imported by the app):
  - time.time   -> deterministic advancing clock (1/30 s per call)
  - cv2.imshow  -> captures frames instead of opening a window
  - cv2.waitKey -> returns 'q' once simulated time is up
  - pyautogui   -> records presses/typewrites instead of controlling the OS
  - winsound    -> silent
  - pyttsx3     -> dummy engine
  - DemoPilot.status -> records every phase label so we can assert the tour
"""
import os
import sys

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import index

# ---- deterministic clock -------------------------------------------------
clock = {"t": 0.0}
def fake_time():
    clock["t"] += 1.0 / 30.0
    return clock["t"]
index.time.time = fake_time

# ---- patches --------------------------------------------------------------
index.MEMO_AVAILABLE = False          # skip heavy MEMO session init in the test

# Render calls are no-ops: the state machine + pilot only need button geometry
# (from the draw=False passes) and the clock, not actual pixels.
import cv2 as _cv2
for _name in ("putText", "rectangle", "line", "circle",
              "cvtColor", "bitwise_not", "dilate", "copyMakeBorder"):
    setattr(index.cv2, _name, lambda *a, **k: None)
# addWeighted results are ASSIGNED to frame in the AIR path — return its input
index.cv2.addWeighted = lambda a, *rest, **k: a
index.cv2.flip = lambda f, d: f
index.pytesseract.image_to_string = lambda *a, **k: ""   # no real OCR in the test

pressed = []
index.pyautogui.press = lambda k: pressed.append(("press", k))
index.pyautogui.typewrite = lambda s: pressed.append(("typewrite", s))

index.winsound.PlaySound = lambda *a, **k: None

class _DummyTTS:
    def setProperty(self, *a, **k): pass
    def getProperty(self, *a, **k): return 100
    def say(self, *a, **k): pass
    def runAndWait(self, *a, **k): pass
index.pyttsx3.init = lambda *a, **k: _DummyTTS()

frames_seen = {"n": 0, "shape": None}
def fake_imshow(title, frame):
    frames_seen["n"] += 1
    if frames_seen["shape"] is None:
        frames_seen["shape"] = frame.shape
index.cv2.imshow = fake_imshow

def fake_waitKey(ms):
    return ord("q") if clock["t"] > 260 else 0
index.cv2.waitKey = fake_waitKey

labels = []
def fake_status(self):
    lab = self.label
    if not labels or labels[-1] != lab:
        labels.append(lab)
    return lab
index.DemoPilot.status = fake_status

# ---- run the real main() ---------------------------------------------------
import sys as _sys
_sys.argv = ["index.py", "--demo", "--real-keys"]   # real keys so the recorder sees presses
index.cv2.namedWindow = lambda *a, **k: None
index.cv2.resizeWindow = lambda *a, **k: None

try:
    index.main()
except SystemExit:
    pass

# ---- assertions ------------------------------------------------------------
ok = True
def check(name, cond):
    global ok
    print(("PASS  " if cond else "FAIL  ") + name)
    ok = ok and cond

check("main() completed the tour without raising", True)
check("frames were produced", frames_seen["n"] > 0)
check("frame shape is 1280x720x3", frames_seen["shape"] == (720, 1280, 3))
check("GRID typed H", ("press", "h") in pressed or ("press", "H") in pressed)
typed = "".join(p[1] for p in pressed if p[0] == "press").lower()
check("GRID typed HELP", typed[:4] == "help")
check("word suggestion was tapped", any(p[0] == "typewrite" for p in pressed))

phase_labels = set(labels)
for expected in ["MAIN MENU - entering GRID keyboard",
                 "GRID - hovering",
                 "GRID - tapping a word suggestion",
                 "GRID - switching to AIR writing",
                 "AIR - pinch-drawing a wave",
                 "AIR - reading the drawn character...",
                 "AIR - returning to the menu"]:
    check(f"tour reached: {expected!r}", any(expected in l for l in labels))

print("\n--- sequence of phase labels (dedup) ---")
for l in labels:
    print("  ", l)
print("\n--- pyautogui output ---")
print("  ", pressed[:30])
print("\nRESULT:", "ALL PASS" if ok else "FAILURES PRESENT")
sys.exit(0 if ok else 1)
