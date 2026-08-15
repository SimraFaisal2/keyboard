"""
index.py â€” Emergency AI Communication Interface
================================================
Modes:
  GRID   â€” hover-to-click virtual keyboard
  AIR    â€” pinch-to-draw air writing (OCR)
  ASL    â€” heuristic single-letter sign language
  ASSIST â€” Stacked BiLSTM emergency gesture recognition
           (HELP / EMERGENCY / PAIN / WATER / FOOD / TOILET / YES / NO)
  MEMO   â€” personal object memory (teach & recall for dementia cueing)
"""

# ─── Console encoding: keep emoji prints from crashing on cp1252 terminals ──
import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import argparse
from types import SimpleNamespace

import cv2
import numpy as np
import pyautogui
import time
import math
import os
import datetime
import collections
import pkg_resources
from symspellpy import SymSpell, Verbosity
import pytesseract

try:
    pytesseract.get_tesseract_version()
    TESSERACT_OK = True
except Exception:
    # PATH may be stale right after install — fall back to the standard
    # Windows install location before giving up.
    TESSERACT_OK = False
    for _p in (r"C:\Program Files\Tesseract-OCR\tesseract.exe",
               r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"):
        if os.path.exists(_p):
            pytesseract.pytesseract.tesseract_cmd = _p
            try:
                pytesseract.get_tesseract_version()
                TESSERACT_OK = True
            except Exception:
                pass
            break
    if not TESSERACT_OK:
        print("⚠️  Tesseract OCR binary not found — AIR mode can draw, but auto-read needs it installed.")
import winsound
import pyttsx3
import threading

# â”€â”€â”€ Suppress TensorFlow warnings during MediaPipe import â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
try:
    import mediapipe as mp
except Exception as e:
    print(f"âš ï¸  MediaPipe import warning (non-critical): {e}")
    import mediapipe as mp

try:
    from memo_mode import MemoSession
    MEMO_AVAILABLE = True
except ImportError as e:
    MEMO_AVAILABLE = False
    print(f"â„¹ï¸  MEMO mode unavailable: {e}")

# â”€â”€â”€ MediaPipe â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
try:
    from face_mode import FaceID
    FACE_AVAILABLE = True
except ImportError as e:
    FACE_AVAILABLE = False
    print(f"FACE mode unavailable: {e}")

mp_hands = mp.solutions.hands
hands = mp_hands.Hands(max_num_hands=2,
                       min_detection_confidence=0.5,
                       min_tracking_confidence=0.5)
mp_draw = mp.solutions.drawing_utils

# â”€â”€â”€ Keyboard Layout â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
keys = [
    ["1","2","3","4","5","6","7","8","9","0"],
    ["Q","W","E","R","T","Y","U","I","O","P"],
    ["A","S","D","F","G","H","J","K","L"],
    ["Z","X","C","V","B","N","M","<","Space"]
]

# â”€â”€â”€ Tuning â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
HOVER_DELAY        = 0.45
BACKSPACE_COOLDOWN = 0.25
EMA_ALPHA          = 0.6
ASL_HOLD_TIME      = 1.5
PINCH_HOLD         = 1.5
ASSIST_THRESHOLD   = 0.85   # LSTM confidence threshold
ASSIST_FRAMES      = 30     # sequence length (must match training)
ASSIST_COOLDOWN    = 2.5    # seconds between LSTM triggers

GESTURES = ["HELP","EMERGENCY","PAIN","WATER","FOOD","TOILET","YES","NO"]
MODEL_PATH = "model.keras"
LABELS_PATH = "labels.npy"
ALERTS_LOG = "alerts_log.txt"

# â”€â”€â”€ NLP â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
sym_spell = SymSpell(max_dictionary_edit_distance=2, prefix_length=7)
sym_spell.load_dictionary(
    pkg_resources.resource_filename("symspellpy", "frequency_dictionary_en_82_765.txt"),
    term_index=0, count_index=1
)

_pred_prefix, _pred_results = None, []

def get_predictions(text):
    """Return the 3 most likely word completions for the current word.

    Uses frequency-ordered prefix completion over the loaded dictionary.
    (SymSpell.lookup is a typo-correction engine: for a partial word like
    "hel" it returns corrections such as "heal" that don't start with the
    typed prefix, so a startswith filter silently empties the prediction
    bar. Scanning the dictionary for real prefixes is both correct and,
    cached per prefix, effectively free since the text only changes on keypress.)
    """
    global _pred_prefix, _pred_results
    words = text.split(" ")
    last = words[-1].lower() if words else ""
    if not last:
        return []
    if last == _pred_prefix:
        return _pred_results
    candidates = [(count, term) for term, count in sym_spell.words.items()
                  if term.startswith(last) and term != last]
    candidates.sort(key=lambda t: -t[0])
    _pred_prefix, _pred_results = last, [term for _, term in candidates[:3]]
    return _pred_results

# â”€â”€â”€ Drawing utils â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def draw_rounded_rect(img, pt1, pt2, color, thickness=-1, radius=10):
    x1,y1=pt1; x2,y2=pt2
    if thickness==-1:
        cv2.rectangle(img,(x1+radius,y1),(x2-radius,y2),color,-1)
        cv2.rectangle(img,(x1,y1+radius),(x2,y2-radius),color,-1)
        for cx,cy in [(x1+radius,y1+radius),(x2-radius,y1+radius),
                      (x1+radius,y2-radius),(x2-radius,y2-radius)]:
            cv2.circle(img,(cx,cy),radius,color,-1)
    else:
        cv2.rectangle(img,(x1+radius,y1),(x2-radius,y2),color,thickness)
        cv2.rectangle(img,(x1,y1+radius),(x2,y2-radius),color,thickness)

# â”€â”€â”€ Themes â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def _glass(frame, x1, y1, x2, y2, color, alpha=0.55, radius=10):
    """Translucent rounded-rect fill blended over the current frame."""
    ov = frame.copy()
    draw_rounded_rect(ov, (x1, y1), (x2, y2), color, -1, radius)
    cv2.addWeighted(ov, alpha, frame, 1.0 - alpha, 0, frame)


THEMES = [
    # slate/navy + cyan hover + violet accent (default)
    {"bg": (10, 12, 18),      "border": (40, 48, 66),   "key_bg": (22, 28, 42), "key_border": (52, 64, 90),
     "hover": (56, 189, 248), "press": (52, 211, 153),  "text": (229, 234, 242), "accent": (167, 139, 250),
     "panel": (15, 19, 30),   "text_dim": (150, 165, 185)},
    # deep violet + teal hover
    {"bg": (13, 9, 26),       "border": (72, 42, 126),  "key_bg": (28, 18, 54), "key_border": (104, 62, 168),
     "hover": (0, 255, 235),  "press": (196, 92, 255),  "text": (231, 226, 255), "accent": (196, 122, 255),
     "panel": (17, 12, 34),   "text_dim": (172, 152, 214)},
    # monochrome light-on-dark
    {"bg": (9, 9, 12),        "border": (46, 46, 54),   "key_bg": (19, 19, 24), "key_border": (62, 62, 74),
     "hover": (222, 222, 232),"press": (255, 255, 255),"text": (202, 202, 212), "accent": (182, 182, 202),
     "panel": (13, 13, 17),   "text_dim": (132, 132, 148)},
]

# â”€â”€â”€ ASL heuristic helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def _dist(a,b): return math.hypot(a[0]-b[0],a[1]-b[1])
def _angle(a,b,c):
    ba=(a[0]-b[0],a[1]-b[1]); bc=(c[0]-b[0],c[1]-b[1])
    dot=ba[0]*bc[0]+ba[1]*bc[1]
    mag=max(math.hypot(*ba)*math.hypot(*bc),1e-6)
    return math.degrees(math.acos(max(-1,min(1,dot/mag))))
def _up(lm,tip,pip): return lm[tip][1]<lm[pip][1]

def get_asl_letter(lm):
    i_up=_up(lm,8,6); m_up=_up(lm,12,10); r_up=_up(lm,16,14); p_up=_up(lm,20,18)
    thm=lm[4][0]<lm[3][0]
    pw=max(_dist(lm[5],lm[17]),1)
    d_ti=_dist(lm[4],lm[8]); d_im=_dist(lm[8],lm[12])
    if not i_up and not m_up and not r_up and not p_up and thm:        return "A"
    if i_up and m_up and r_up and p_up and not thm:                    return "B"
    if not i_up and not m_up and not r_up and not p_up and not thm:
        if 0.05<d_ti/pw<0.45: return "O"
        if 0.3<d_ti/pw<1.1:   return "C"
        if d_ti/pw<0.3:        return "E"
    if i_up and not m_up and not r_up and not p_up:
        ang=_angle(lm[6],lm[7],lm[8])
        if not thm and ang<160: return "X"
        if thm: return "L"
        return "D"
    if not i_up and m_up and r_up and p_up and d_ti/pw<0.4:           return "F"
    if not i_up and not m_up and not r_up and p_up and not thm:        return "I"
    if i_up and m_up and not r_up and not p_up:
        if thm: return "K"
        if d_im/pw<0.2: return "R"
        if _angle(lm[8],lm[5],lm[12])<30: return "V"
        return "U"
    if i_up and m_up and r_up and not p_up and not thm:               return "W"
    if not i_up and not m_up and not r_up and p_up and thm:           return "Y"
    return ""

# â”€â”€â”€ LSTM Action Engine â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
ASSIST_COLORS = {
    "HELP":      (0, 0, 220),
    "EMERGENCY": (0, 0, 180),
    "PAIN":      (0, 80, 200),
    "WATER":     (180, 100, 0),
    "FOOD":      (0, 160, 80),
    "TOILET":    (150, 100, 30),
    "YES":       (30, 200, 60),
    "NO":        (0, 50, 200),
}
ASSIST_MESSAGES = {
    "HELP":      "Patient needs help immediately.",
    "EMERGENCY": "Emergency! Please call for assistance now.",
    "PAIN":      "Patient is reporting pain.",
    "WATER":     "Patient is requesting water.",
    "FOOD":      "Patient is requesting food.",
    "TOILET":    "Patient needs to use the toilet.",
    "YES":       "Yes.",
    "NO":        "No.",
}

def log_alert(gesture, confidence):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}]  GESTURE: {gesture:<12}  CONFIDENCE: {confidence*100:.1f}%\n"
    with open(ALERTS_LOG, "a") as f:
        f.write(line)
    print(line.strip())

def fire_action(gesture, confidence, tts_engine, frame_shape):
    """Speak, log, and return an alert overlay color."""
    msg = ASSIST_MESSAGES.get(gesture, gesture)
    log_alert(gesture, confidence)
    winsound.PlaySound("SystemHand", winsound.SND_ALIAS|winsound.SND_ASYNC)
    try:
        tts_engine.say(msg)
        tts_engine.runAndWait()
    except Exception:
        pass
    return ASSIST_COLORS.get(gesture, (0,0,180))

def draw_assist_overlay(frame, gesture, confidence, alert_color, alert_until):
    h, w = frame.shape[:2]
    now = time.time()

    # Alert flash (red/colored border for 2 seconds after detection)
    if now < alert_until:
        pulse = int(255 * abs(math.sin((now*4) % math.pi)))
        cv2.rectangle(frame, (0,0), (w-1,h-1),
                      (alert_color[0], alert_color[1], min(255,pulse+100)), 8)

    # Panel
    overlay = frame.copy()
    cv2.rectangle(overlay, (25,125), (w-25,580), (10,8,6), -1)
    cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)
    cv2.rectangle(frame, (25,125), (w-25,580), (60,60,200), 2, cv2.LINE_AA)

    cv2.putText(frame, "EMERGENCY AI COMMUNICATION INTERFACE",
                (50, 170), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (100,150,255), 2, cv2.LINE_AA)
    cv2.putText(frame, "Supported gestures:",
                (50, 205), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (160,160,160), 1)

    signs = list(ASSIST_MESSAGES.keys())
    for i, g in enumerate(signs):
        col = 50 + (i % 4) * 290
        row = 230 + (i // 4) * 36
        color = (100,255,100) if g == gesture else (180,180,180)
        cv2.putText(frame, g, (col, row), cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 2)

    if gesture:
        gcolor = ASSIST_COLORS.get(gesture, (100,200,255))
        # Big gesture word
        cv2.putText(frame, gesture, (50, 420),
                    cv2.FONT_HERSHEY_DUPLEX, 4.0,
                    (gcolor[2], gcolor[1], gcolor[0]), 8, cv2.LINE_AA)
        # Confidence bar
        bar_x1, bar_y1, bar_x2, bar_y2 = 50, 440, w-50, 460
        cv2.rectangle(frame, (bar_x1,bar_y1), (bar_x2,bar_y2), (40,40,40), -1)
        fill = int((bar_x2-bar_x1)*confidence)
        bar_color = (0,200,0) if confidence>ASSIST_THRESHOLD else (0,160,200)
        cv2.rectangle(frame, (bar_x1,bar_y1), (bar_x1+fill,bar_y2), bar_color, -1)
        cv2.putText(frame, f"{confidence*100:.0f}% confidence",
                    (bar_x1+10, bar_y2-3),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255,255,255), 1)
        # Message
        cv2.putText(frame, ASSIST_MESSAGES.get(gesture,""),
                    (50, 500), cv2.FONT_HERSHEY_SIMPLEX, 0.75,
                    (220,220,220), 2, cv2.LINE_AA)
    else:
        cv2.putText(frame, "Show a gesture to the camera...",
                    (50, 390), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (80,80,80), 2)

# â”€â”€â”€ 
# ────────────────── Welcome Screen & Navigation ──────────────────────────────────────────────────────────
def _pill(frame, x, y, w, h, color, filled=True, radius=10):
    """Draw a rounded rect (pill shape)."""
    import cv2, numpy as np
    overlay = frame.copy()
    cv2.rectangle(overlay, (x + radius, y), (x + w - radius, y + h), color, -1)
    cv2.rectangle(overlay, (x, y + radius), (x + w, y + h - radius), color, -1)
    for cx, cy in [(x+radius,y+radius),(x+w-radius,y+radius),(x+radius,y+h-radius),(x+w-radius,y+h-radius)]:
        cv2.circle(overlay, (cx, cy), radius, color, -1)
    cv2.addWeighted(overlay, 1.0, frame, 0.0, 0, frame)
    if not filled:
        cv2.rectangle(frame, (x,y), (x+w,y+h), color, 2)


def draw_main_menu(frame, hover_key, progress, draw=True):
    """Portfolio-style dark welcome screen."""
    import cv2, numpy as np
    button_list = []
    fh, fw = frame.shape[:2]
    VIOLET = (167, 139, 250)
    CYAN   = (56, 189, 248)
    WHITE  = (235, 238, 245)
    DIM    = (150, 165, 185)

    if draw:
        # Solid dark background — the main menu shows ONLY the menu, no camera
        # feed behind it. (The fingertip is re-drawn on top by the main loop.)
        frame[:] = (12, 14, 20)

        # ── Header ─────────────────────────────────────────────────
        cv2.putText(frame, "HI, I'M", (80, 140),
                    cv2.FONT_HERSHEY_DUPLEX, 1.8, DIM, 2, cv2.LINE_AA)
        # "SIMRA FAISAL" — thick white with a thin dark outline
        cv2.putText(frame, "SIMRA FAISAL", (80, 250),
                    cv2.FONT_HERSHEY_DUPLEX, 3.4, WHITE, 10, cv2.LINE_AA)
        cv2.putText(frame, "SIMRA FAISAL", (80, 250),
                    cv2.FONT_HERSHEY_DUPLEX, 3.4, (10, 12, 18), 2, cv2.LINE_AA)
        # violet accent underline
        cv2.rectangle(frame, (84, 268), (460, 274), VIOLET, -1)

        cv2.putText(frame, "AI COMMUNICATION SYSTEM", (80, 330),
                    cv2.FONT_HERSHEY_DUPLEX, 0.85, VIOLET, 2, cv2.LINE_AA)
        cv2.putText(frame, "Hover over a mode to get started.", (80, 385),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, DIM, 1, cv2.LINE_AA)

    # ── Mode buttons (row layout) ────────────────────────────────
    modes = [
        ("GRID",   "ON-SCREEN|KEYBOARD",  VIOLET, True),
        ("ASL",    "ASL|TRANSLATOR",      (255, 255, 255), False),
        ("AIR",    "AIR|HAND-WRITING",    (255, 255, 255), False),
        ("FACE",   "FACE|BIOMETRIC ID",   (255, 255, 255), False),
        ("ASSIST", "COGNITIVE|ASSISTANCE",(255, 255, 255), False),
    ]
    if MEMO_AVAILABLE:
        modes.append(("MEMO", "OBJECT|MEMORY", (255, 255, 255), False))

    n = len(modes)
    gap = 18 if n >= 6 else 24
    bw  = (fw - 160 - (n - 1) * gap) // n
    bh  = 90
    total = n * bw + (n - 1) * gap
    sx    = (fw - total) // 2
    sy    = 520

    for i, (mid, label, col, filled) in enumerate(modes):
        x = sx + i * (bw + gap)
        hovered = hover_key and hover_key[0] == mid

        if draw:
            bg_col = (40, 34, 72) if filled else (16, 20, 32)
            bd_col = VIOLET if filled else (58, 70, 96)
            if hovered:
                _glass(frame, x, sy, x + bw, sy + bh, VIOLET, alpha=0.28, radius=14)
                bd_col = (200, 185, 255)
            else:
                draw_rounded_rect(frame, (x, sy), (x + bw, sy + bh), bg_col, -1, 14)
            draw_rounded_rect(frame, (x, sy), (x + bw, sy + bh), bd_col, 1, 14)
            if hovered:
                pw = int(bw * progress)
                cv2.rectangle(frame, (x + 4, sy + bh - 7), (x + 4 + pw, sy + bh - 3), CYAN, -1)

            # Label (two lines: mode name + subtitle)
            lines = label.split("|")
            ty = sy + 26
            for li, ln in enumerate(lines):
                fnt = cv2.FONT_HERSHEY_DUPLEX if li == 0 else cv2.FONT_HERSHEY_SIMPLEX
                sc  = 0.66 if li == 0 else 0.52
                sz  = cv2.getTextSize(ln, fnt, sc, 2)
                tx  = x + (bw - sz[0][0]) // 2
                colr = WHITE if (hovered or li == 0) else DIM
                cv2.putText(frame, ln, (tx, ty + li * 32), fnt, sc, colr,
                            2 if li == 0 else 1, cv2.LINE_AA)

        button_list.append([mid, x, sy, bw, bh, col, label])

    return button_list


def draw_top_nav(frame, hover_key, progress, mode, draw=True):
    """Persistent back button + optional SPEAK button."""
    import cv2
    button_list = []
    VIOLET = (167, 139, 250)

    # Back button
    x, y, w, h = 20, 20, 220, 54
    hovered = hover_key and hover_key[0] == "MAIN_MENU"
    if draw:
        if hovered:
            _glass(frame, x, y, x + w, y + h, VIOLET, alpha=0.55, radius=12)
        else:
            draw_rounded_rect(frame, (x, y), (x + w, y + h), (18, 23, 36), -1, 12)
        draw_rounded_rect(frame, (x, y), (x + w, y + h), VIOLET, 1, 12)
        cv2.putText(frame, "<  MAIN MENU", (x + 18, y + 35),
                    cv2.FONT_HERSHEY_DUPLEX, 0.62, (240, 240, 245), 2, cv2.LINE_AA)
        if hovered:
            pw = int(w * progress)
            cv2.rectangle(frame, (x + 4, y + h - 7), (x + 4 + pw, y + h - 3),
                          (56, 189, 248), -1)
    button_list.append(["MAIN_MENU", x, y, w, h, VIOLET, "BACK"])

    # ASL speak button
    if mode == "ASL":
        sx, sy2, sw, sh = 1080, 75, 170, 55
        shov = hover_key and hover_key[0] == "SPEAK"
        if draw:
            if shov:
                _glass(frame, sx, sy2, sx + sw, sy2 + sh, (46, 210, 120), alpha=0.55, radius=12)
            else:
                draw_rounded_rect(frame, (sx, sy2), (sx + sw, sy2 + sh), (14, 40, 28), -1, 12)
            draw_rounded_rect(frame, (sx, sy2), (sx + sw, sy2 + sh), (60, 220, 130), 1, 12)
            sz = cv2.getTextSize("SPEAK", cv2.FONT_HERSHEY_SIMPLEX, 0.72, 2)[0]
            cv2.putText(frame, "SPEAK", (sx + (sw - sz[0]) // 2, sy2 + 35),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.72, (235, 245, 240), 2, cv2.LINE_AA)
            if shov:
                pw = int(sw * progress)
                cv2.rectangle(frame, (sx + 4, sy2 + sh - 7), (sx + 4 + pw, sy2 + sh - 3),
                              (56, 189, 248), -1)
        button_list.append(["SPEAK", sx, sy2, sw, sh, (60, 220, 130), "SPEAK"])

    return button_list


def draw_face_overlay(frame, overlay, hover_key=None, progress=0.0,
                      typed_text="", theme_idx=0, draw=True, learn_status=""):
    """FACE mode: green tag on recognised people, amber on strangers, plus a
    LEARN button (enrolls the largest face under the name in the text box).
    ``overlay`` is a list of (x, y, w, h, name, confidence) tuples."""
    import cv2
    T = THEMES[theme_idx]
    buttons = []
    h, w = frame.shape[:2]

    if draw:
        for (fx, fy, fw, fh, name, conf) in overlay:
            col = (60, 220, 130) if name else (225, 185, 70)
            cv2.rectangle(frame, (fx, fy), (fx + fw, fy + fh), col, 2, cv2.LINE_AA)
            label = f"{name} | {conf:.0f}" if name else "unknown"
            sz = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)[0]
            cv2.rectangle(frame, (fx, fy - 30), (fx + fw, fy), col, -1)
            cv2.putText(frame, label, (fx + 8, fy - 9),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (10, 14, 18), 2, cv2.LINE_AA)
            if not name:
                tip = "LEARN to save this face"
                tsz = cv2.getTextSize(tip, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1)[0]
                cv2.putText(frame, tip, (fx + 8, fy + fh + 22),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.55, (225, 185, 70), 1, cv2.LINE_AA)

    # LEARN button — top right, mirrors the ASL SPEAK button
    name = (typed_text or "Person").strip().split()
    name = name[0] if name else "Person"
    bx, by, bw, bh = w - 260, 20, 240, 54
    hovered = hover_key and hover_key[0] == "LEARN_FACE"
    if draw:
        if hovered:
            _glass(frame, bx, by, bx + bw, by + bh, (60, 220, 130), alpha=0.55, radius=12)
        else:
            draw_rounded_rect(frame, (bx, by), (bx + bw, by + bh), (14, 40, 28), -1, 12)
        draw_rounded_rect(frame, (bx, by), (bx + bw, by + bh), (60, 220, 130), 1, 12)
        label = f"LEARN: {name}"
        sz = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.62, 2)[0]
        cv2.putText(frame, label, (bx + (bw - sz[0]) // 2, by + 35),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.62, (235, 245, 240), 2, cv2.LINE_AA)
        if hovered:
            pw = int(bw * progress)
            cv2.rectangle(frame, (bx + 4, by + bh - 7), (bx + 4 + pw, by + bh - 3),
                          (56, 189, 248), -1)
        if learn_status:
            sz = cv2.getTextSize(learn_status, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1)[0]
            cv2.putText(frame, learn_status, (bx + (bw - sz[0]) // 2, by + 76),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (56, 189, 248), 1, cv2.LINE_AA)
        elif not overlay:
            sz = cv2.getTextSize("No face in view", cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1)[0]
            cv2.putText(frame, "No face in view", (bx + (bw - sz[0]) // 2, by + 76),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (140, 150, 165), 1, cv2.LINE_AA)
    buttons.append(["LEARN_FACE", bx, by, bw, bh, (60, 220, 130), "LEARN"])
    return buttons


# ─── Voice enrollment helpers (FACE mode) ──────────────────────────────────
def _listen_for_name():
    """Record a short utterance and recognize a spoken name (best-effort).

    Returns (name | None, message). Uses speech_recognition with the Google
    recognizer; falls back gracefully if the mic or service fails.
    """
    try:
        import speech_recognition as sr
    except ImportError:
        return None, "speech module missing"
    try:
        r = sr.Recognizer()
        with sr.Microphone() as source:
            r.adjust_for_ambient_noise(source, duration=0.6)
            audio = r.listen(source, timeout=2.5, phrase_time_limit=3.5)
        try:
            text = r.recognize_google(audio, language="en-US").strip().title()
        except sr.UnknownValueError:
            return None, "couldn't hear a clear name"
        except sr.RequestError:
            return None, "speech service unreachable"
        except Exception:
            return None, "speech failed"
        first = text.split()[0] if text else ""
        return (first or None), (f"heard: {first}" if first else "heard nothing")
    except Exception as e:
        return None, f"mic error: {e}"


def _listen_worker(holder):
    """Runs _listen_for_name in a background thread (mic is blocking)."""
    res, msg = _listen_for_name()
    holder["name"] = res
    holder["msg"] = msg
    holder["done"] = True


def _save_learned(tts, face_id, nm, samples):
    """Persist enrollment samples under known_faces/<name>/ and retrain."""
    legacy = os.path.join("known_faces", f"{nm}.jpg")
    if os.path.exists(legacy):
        os.remove(legacy)   # replace any old single-photo entry
    d = os.path.join("known_faces", nm)
    os.makedirs(d, exist_ok=True)
    for i, s in enumerate(samples[:15]):
        cv2.imwrite(os.path.join(d, f"sample_{i:02d}.jpg"), s)
    n = face_id.reload()
    try:
        tts.say(f"Learned {nm}. I now know {n} people.")
        tts.runAndWait()
    except Exception:
        pass
    return n


def check_escape_gesture(results, frame_w, frame_h):
    """Return True if both hands are open palms (escape gesture)."""
    if not results.multi_hand_landmarks or len(results.multi_hand_landmarks) < 2:
        return False
    open_hands = 0
    for handLms in results.multi_hand_landmarks:
        lm = [(int(l.x*frame_w), int(l.y*frame_h)) for l in handLms.landmark]
        tips = [8, 12, 16, 20]
        pips = [6, 10, 14, 18]
        up = sum(1 for t, p in zip(tips, pips) if lm[t][1] < lm[p][1])
        if up >= 3:
            open_hands += 1
    return open_hands >= 2

# Keyboard Renderer ──────────────────────────────────────────────────────────
def draw_keyboard(frame, highlight_key=None, progress=0.0,
                  predictions=None, mode="GRID", theme_idx=0,
                  asl_letter="", asl_progress=0.0, draw=True):
    if predictions is None: predictions = []
    button_list = []
    T = THEMES[theme_idx]

    mode_color = (highlight_key[5] if highlight_key
                  and highlight_key[0] == "TOGGLE_MODE" else T["accent"])
    if draw:
        if highlight_key and highlight_key[0] == "TOGGLE_MODE":
            _glass(frame, 1080, 10, 1250, 65, T["accent"], alpha=0.65, radius=10)
        else:
            draw_rounded_rect(frame, (1080, 10), (1250, 65), (30, 26, 54), -1, 10)
            draw_rounded_rect(frame, (1080, 10), (1250, 65), T["accent"], 1, 10)
        sz = cv2.getTextSize(f"MODE: {mode}", cv2.FONT_HERSHEY_SIMPLEX, 0.62, 2)[0]
        cv2.putText(frame, f"MODE: {mode}", (1080 + (170 - sz[0]) // 2, 45),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.62, (240, 240, 250), 2, cv2.LINE_AA)
        if highlight_key and highlight_key[0] == "TOGGLE_MODE":
            pw = int(170 * progress)
            cv2.rectangle(frame, (1084, 57), (1084 + pw, 61), (240, 240, 250), -1)
    button_list.append(["TOGGLE_MODE", 1080, 10, 170, 55, mode_color, "TOGGLE_MODE"])

    if mode in ("ASSIST", "MEMO", "FACE"):
        return button_list
    elif mode == "ASL":
        if draw:
            _glass(frame, 30, 130, 700, 520, T["panel"], alpha=0.72, radius=16)
            draw_rounded_rect(frame, (30, 130), (700, 520), T["accent"], 1, 16)
            cv2.putText(frame, "ASL SIGN LANGUAGE MODE", (50, 175),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.85, (110, 170, 255), 2, cv2.LINE_AA)
            cv2.putText(frame, "Hold a hand sign steady to type a letter",
                        (50, 212), cv2.FONT_HERSHEY_SIMPLEX, 0.6, T["text_dim"], 1, cv2.LINE_AA)
            cv2.putText(frame, "Detects: A B C D E F I K L O R U V W X Y",
                        (50, 248), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (150, 150, 210), 1)
            if asl_letter:
                cv2.putText(frame, asl_letter, (270, 440),
                            cv2.FONT_HERSHEY_DUPLEX, 8.0, T["accent"], 6, cv2.LINE_AA)
                cv2.putText(frame, "Hold steady...", (50, 478),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (215, 220, 230), 2)
                b1, b2 = 50, 650
                cv2.rectangle(frame, (b1, 494), (b2, 507), (45, 52, 70), -1)
                cv2.rectangle(frame, (b1, 494), (b1 + int((b2 - b1) * asl_progress), 507),
                              T["press"], -1)
            else:
                cv2.putText(frame, "Show a sign...", (120, 390),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.4, (90, 96, 110), 2)
        return button_list
    elif mode == "AIR":
        if draw:
            cv2.putText(frame, "AIR WRITING - pinch thumb & index to draw",
                        (60, 180), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (110, 220, 160), 2, cv2.LINE_AA)
            cv2.putText(frame, "Pause 1.5 s to auto-read the character",
                        (60, 218), cv2.FONT_HERSHEY_SIMPLEX, 0.58, T["text_dim"], 1, cv2.LINE_AA)
        cc = (highlight_key[5] if highlight_key
              and highlight_key[0] == "CLEAR_CANVAS" else (70, 90, 160))
        if draw:
            if highlight_key and highlight_key[0] == "CLEAR_CANVAS":
                _glass(frame, 1080, 75, 1250, 130, (70, 90, 160), alpha=0.7, radius=10)
            else:
                draw_rounded_rect(frame, (1080, 75), (1250, 130), (24, 30, 46), -1, 10)
            draw_rounded_rect(frame, (1080, 75), (1250, 130), (110, 140, 220), 1, 10)
            sz = cv2.getTextSize("CLEAR", cv2.FONT_HERSHEY_SIMPLEX, 0.72, 2)[0]
            cv2.putText(frame, "CLEAR", (1080 + (170 - sz[0]) // 2, 110),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.72, (235, 240, 250), 2, cv2.LINE_AA)
        button_list.append(["CLEAR_CANVAS", 1080, 75, 170, 55, cc, "CLEAR_CANVAS"])
        return button_list
    else:
        sc = (highlight_key[5] if highlight_key
              and highlight_key[0] == "SPEAK" else (46, 130, 210))
        if draw:
            if highlight_key and highlight_key[0] == "SPEAK":
                _glass(frame, 1080, 75, 1250, 130, (46, 130, 210), alpha=0.7, radius=10)
            else:
                draw_rounded_rect(frame, (1080, 75), (1250, 130), (18, 30, 46), -1, 10)
            draw_rounded_rect(frame, (1080, 75), (1250, 130), (70, 160, 230), 1, 10)
            sz = cv2.getTextSize("SPEAK", cv2.FONT_HERSHEY_SIMPLEX, 0.72, 2)[0]
            cv2.putText(frame, "SPEAK", (1080 + (170 - sz[0]) // 2, 110),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.72, (235, 242, 250), 2, cv2.LINE_AA)
        button_list.append(["SPEAK", 1080, 75, 170, 55, sc, "SPEAK"])

        tc = (highlight_key[5] if highlight_key
              and highlight_key[0] == "THEME" else (120, 96, 220))
        if draw:
            if highlight_key and highlight_key[0] == "THEME":
                _glass(frame, 1080, 140, 1250, 195, (120, 96, 220), alpha=0.7, radius=10)
            else:
                draw_rounded_rect(frame, (1080, 140), (1250, 195), (28, 24, 46), -1, 10)
            draw_rounded_rect(frame, (1080, 140), (1250, 195), (160, 140, 250), 1, 10)
            sz = cv2.getTextSize("THEME", cv2.FONT_HERSHEY_SIMPLEX, 0.72, 2)[0]
            cv2.putText(frame, "THEME", (1080 + (170 - sz[0]) // 2, 175),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.72, (238, 236, 250), 2, cv2.LINE_AA)
        button_list.append(["THEME", 1080, 140, 170, 55, tc, "THEME"])

    # ─── GRID: prediction row + key grid on a floating console deck ───
    if draw:
        # Solid rounded console over the camera feed (video shows around the
        # edges) — replaces the old flat full-width band
        draw_rounded_rect(frame, (45, 130), (925, 590), T["panel"], -1, 18)
        draw_rounded_rect(frame, (45, 130), (925, 590), T["border"], 1, 18)
        # header + divider inside the deck
        cv2.putText(frame, "GRID KEYBOARD", (68, 143),
                    cv2.FONT_HERSHEY_DUPLEX, 0.6, T["accent"], 2, cv2.LINE_AA)
        cv2.line(frame, (68, 152), (910, 152), T["border"], 1)

    # Prediction row (word suggestions)
    for idx in range(3):
        pw = predictions[idx] if idx < len(predictions) else "..."
        px = 60 + idx * 260; kid = f"PRED_{idx}"
        color = (highlight_key[5] if highlight_key
                 and highlight_key[0] == kid else T["key_bg"])
        hovered = highlight_key and highlight_key[0] == kid and color == T["hover"]
        if draw:
            if hovered:
                _glass(frame, px - 4, 156, px + 244, 214, T["accent"], alpha=0.30, radius=10)
            draw_rounded_rect(frame, (px, 160), (px + 240, 210),
                              T["hover"] if hovered else T["key_bg"], -1, 8)
            draw_rounded_rect(frame, (px, 160), (px + 240, 210),
                              T["accent"] if hovered else T["key_border"], 1, 8)
            txt_col = (8, 14, 24) if hovered else (T["text"] if pw != "..." else T["text_dim"])
            cv2.putText(frame, pw, (px + 14, 192),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.62, txt_col, 2, cv2.LINE_AA)
            if hovered:
                bw = int(240 * progress)
                cv2.rectangle(frame, (px + 6, 205), (px + 6 + bw, 209), T["press"], -1)
        button_list.append([kid, px, 160, 240, 50, color, pw])

    # Key grid
    row_off = [0, 20, 40, 60]
    for i, row in enumerate(keys):
        for j, key in enumerate(row):
            w, h = 75, 65
            if key == "Space": w = 210
            elif key == "<":   w = 100
            x = 60 + j * 85 + row_off[i]; y = 240 + i * 78
            color = (highlight_key[5] if highlight_key
                     and highlight_key[0] == key
                     and highlight_key[1] == x
                     and highlight_key[2] == y else T["key_bg"])
            active = (highlight_key and highlight_key[0] == key
                      and highlight_key[1] == x and highlight_key[2] == y)
            if draw:
                hovered = active and color == T["hover"]
                if hovered:
                    # soft outer glow so the target key pops off the deck
                    _glass(frame, x - 5, y - 5, x + w + 5, y + h + 5,
                           T["hover"], alpha=0.28, radius=12)
                draw_rounded_rect(frame, (x, y), (x + w, y + h), color, -1, 8)
                # top highlight + bottom shadow for a keycap feel
                cv2.line(frame, (x + 8, y + 2), (x + w - 8, y + 2),
                         (min(255, color[0] + 28), min(255, color[1] + 28),
                          min(255, color[2] + 36)), 1)
                draw_rounded_rect(frame, (x + 2, y + h - 6), (x + w - 2, y + h - 2),
                                  (14, 18, 28) if color == T["key_bg"] else (10, 18, 26), -1, 4)
                draw_rounded_rect(frame, (x, y), (x + w, y + h),
                                  T["key_border"] if color == T["key_bg"] else (10, 22, 34), 1, 8)
                disp = {"Space": "SPACE", "<": "DEL"}.get(key, key)
                fnt_sz = 0.75 if len(key) == 1 else 0.55
                sz = cv2.getTextSize(disp, cv2.FONT_HERSHEY_SIMPLEX, fnt_sz, 2)[0]
                txt_col = (8, 14, 24) if color != T["key_bg"] else T["text"]
                cv2.putText(frame, disp, (x + (w - sz[0]) // 2, y + (h + sz[1]) // 2 - 2),
                            cv2.FONT_HERSHEY_SIMPLEX, fnt_sz, txt_col, 2, cv2.LINE_AA)
                if hovered:
                    bw = int((w - 12) * progress)
                    cv2.rectangle(frame, (x + 6, y + h - 8), (x + 6 + bw, y + h - 4),
                                  T["press"], -1)
            button_list.append([key, x, y, w, h, color, key])
    return button_list

def get_hovered_key(x8,y8,bl):
    for item in bl:
        k,x,y,w,h=item[0],item[1],item[2],item[3],item[4]
        if x<x8<x+w and y<y8<y+h: return item
    return None

# â”€â”€â”€ Main â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
class DemoPilot:
    """Synthetic-hand auto-pilot: drives the real state machine with no webcam.

    Generates plausible MediaPipe-style hand landmarks and frames so every
    existing mode (hover-to-click keyboard, word predictions, AIR pinch-drawing)
    runs unmodified. The scenario loops a tour:

        MAIN MENU -> type "HELP" on the GRID keyboard -> tap a word suggestion
        -> switch to AIR -> pinch-draw a wave -> back to the main menu
    """
    # 21-landmark offsets (normalized) relative to the index fingertip (#8).
    # Fingers point "up" (smaller y); y grows downward in image space.
    _OPEN = {
        0: (0.00, 0.22),  1: (-0.02, 0.18), 2: (-0.04, 0.14), 3: (-0.05, 0.09), 4: (-0.06, 0.04),
        5: (0.00, 0.11),  6: (0.00, 0.07),  7: (0.00, 0.03),  8: (0.00, 0.00),
        9: (0.02, 0.11), 10: (0.02, 0.07), 11: (0.02, 0.03), 12: (0.02, -0.02),
       13: (0.045, 0.115), 14: (0.045, 0.075), 15: (0.045, 0.035), 16: (0.045, -0.005),
       17: (0.065, 0.12), 18: (0.065, 0.085), 19: (0.065, 0.05), 20: (0.065, 0.02),
    }
    # "Pointing" pose: index up, other fingertips curled below their knuckles —
    # deliberately NOT an open palm so the GRID volume gesture never fires.
    _POINT = dict(_OPEN)
    _POINT.update({12: (0.02, 0.10), 16: (0.045, 0.12), 20: (0.065, 0.13)})
    # "Pinch" pose: thumb tip pulled next to the index tip (dist < 40 px).
    _PINCH = dict(_OPEN)
    _PINCH[4] = (0.015, 0.015)

    WORD = "HELP"

    def __init__(self):
        self.frame_w, self.frame_h = 1280, 720
        self._bg = None
        self.phase = "menu"   # menu -> grid_type -> grid_pred -> air_switch -> air_draw -> air_idle -> back_to_menu
        self.phase_start = time.time()
        self.letter_idx = 0
        self.word_start_len = 0
        self.label = "waiting..."

    # ------------------------------------------------------------ frames
    def next_frame(self):
        if self._bg is None:
            bg = np.full((self.frame_h, self.frame_w, 3), (14, 16, 22), dtype=np.uint8)
            for x in range(0, self.frame_w, 64):
                cv2.line(bg, (x, 0), (x, self.frame_h), (24, 28, 36), 1)
            for y in range(0, self.frame_h, 64):
                cv2.line(bg, (0, y), (self.frame_w, y), (24, 28, 36), 1)
            self._bg = bg
        return self._bg.copy()

    # ------------------------------------------------------------- hands
    class _FakeLm(SimpleNamespace):
        """Protobuf-compatible landmark: mediapipe's renderer calls HasField()."""
        def HasField(self, name):
            return False

    def _hand(self, target, pose):
        offs = self._PINCH if pose == "pinch" else (self._POINT if pose == "point" else self._OPEN)
        lms = [self._FakeLm(x=target[0] + dx, y=target[1] + dy, z=0.0)
               for dx, dy in (offs[i] for i in range(21))]
        return SimpleNamespace(landmark=lms)

    def next_result(self, button_list, input_mode, typed_text):
        target, pose = self._plan(button_list, input_mode, typed_text)
        hand = self._hand(target, pose)
        return SimpleNamespace(multi_hand_landmarks=[hand], multi_handedness=[])

    def status(self):
        return self.label

    # ------------------------------------------------------------ logic
    def _center(self, b):
        if not b:
            return (0.5, 0.4)
        cx = (b[1] + b[3] / 2.0) / self.frame_w
        cy = (b[2] + b[4] / 2.0) / self.frame_h
        return (min(max(cx, 0.02), 0.98), min(max(cy, 0.02), 0.98))

    @staticmethod
    def _find(bl, ident):
        for b in bl:
            if b and b[0] == ident:
                return b
        return None

    @staticmethod
    def _find_pred(bl):
        for b in bl:
            if b and b[0].startswith("PRED_") and len(b) > 6 and b[6] != "...":
                return b
        return None

    def _plan(self, bl, mode, text):
        now = time.time()
        # --- reactive transitions (driven by the real state machine) ---
        if mode == "MAIN_MENU" and self.phase != "menu":
            self.phase, self.phase_start = "menu", now
        elif mode == "GRID" and self.phase == "menu":
            self.phase, self.phase_start = "grid_type", now
            self.letter_idx, self.word_start_len = 0, len(text)
        elif mode == "AIR" and self.phase == "air_switch":
            self.phase, self.phase_start = "air_draw", now

        # --- phase targets ---
        if self.phase == "grid_type":
            if len(text) >= self.word_start_len + len(self.WORD):
                self.phase, self.phase_start = "grid_pred", now
                self.word_start_len = len(text)   # re-anchor: text must GROW to mean the PRED click
            else:
                ch = self.WORD[self.letter_idx]
                if len(text) >= self.word_start_len + self.letter_idx + 1:
                    self.letter_idx = min(self.letter_idx + 1, len(self.WORD) - 1)
                    ch = self.WORD[self.letter_idx]
                self.label = f"GRID - hovering '{ch}'"
                return self._center(self._find(bl, ch)), "point"
        if self.phase == "grid_pred":
            # The only way text grows in this phase is the PRED click itself
            # (it replaces the word + appends a space) — advance on any change.
            if len(text) != self.word_start_len:
                self.phase, self.phase_start = "air_switch", now
            else:
                b = self._find_pred(bl)
                if b is None:
                    if now - self.phase_start > 3.0:
                        self.phase, self.phase_start = "air_switch", now
                    self.label = "GRID - waiting for word suggestions..."
                    return (0.80, 0.58), "point"
                self.label = "GRID - tapping a word suggestion"
                return self._center(b), "point"
        if self.phase == "air_switch":
            self.label = "GRID - switching to AIR writing"
            return self._center(self._find(bl, "TOGGLE_MODE")), "point"
        if self.phase == "air_draw":
            frac = min((now - self.phase_start) / 3.5, 1.0)
            if frac >= 1.0:
                self.phase, self.phase_start = "air_idle", now
            else:
                x = 0.30 + 0.40 * frac
                y = 0.45 + 0.12 * math.sin(frac * 3 * 2 * math.pi)
                self.label = "AIR - pinch-drawing a wave"
                return (x, y), "pinch"
        if self.phase == "air_idle":
            if now - self.phase_start > 2.2:
                self.phase, self.phase_start = "back_to_menu", now
            self.label = "AIR - reading the drawn character..."
            return (0.78, 0.62), "point"
        if self.phase == "back_to_menu":
            self.label = "AIR - returning to the menu"
            return self._center(self._find(bl, "MAIN_MENU")), "point"

        self.label = "MAIN MENU - entering GRID keyboard"
        return self._center(self._find(bl, "GRID")), "point"


def main():
    parser = argparse.ArgumentParser(
        description="Emergency AI Communication Interface — hand-tracked keyboard & air writing")
    parser.add_argument("--demo", action="store_true",
                        help="run with a synthetic hand — no webcam needed (self-driving tour)")
    parser.add_argument("--camera", type=int, default=0,
                        help="webcam index (default: 0)")
    parser.add_argument("--real-keys", action="store_true",
                        help="in --demo mode, also send real keystrokes (default: demo only shows them on-screen)")
    args = parser.parse_args()

    demo = DemoPilot() if args.demo else None
    cap = None if args.demo else cv2.VideoCapture(args.camera)
    if cap is not None:
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    # Demo mode must not hijack the user's keyboard: show keystrokes on-screen
    # only, unless --real-keys is given.
    if demo and not args.real_keys:
        class _SilentKeys:
            def press(self, *a, **k): pass
            def typewrite(self, *a, **k): pass
        global pyautogui
        pyautogui = _SilentKeys()

    # Resizable window scaled to fit small laptop screens (content is 1280x720),
    # positioned on-screen (a previous session once restored the window off-screen).
    WIN_NAME = "Emergency AI Communication Interface"
    cv2.namedWindow(WIN_NAME, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(WIN_NAME, 960, 540)
    try:
        cv2.moveWindow(WIN_NAME, 40, 30)   # cosmetic; fine if it fails headless
    except cv2.error:
        pass

    tts = pyttsx3.init()
    tts.setProperty('rate', 150)

    # Try loading LSTM model
    lstm_model, label_map = None, None
    if os.path.exists(MODEL_PATH) and os.path.exists(LABELS_PATH):
        try:
            import tensorflow as tf
            lstm_model = tf.keras.models.load_model(MODEL_PATH)
            label_map  = list(np.load(LABELS_PATH, allow_pickle=True))
            print(f"âœ… LSTM model loaded â€” {len(label_map)} gestures")
        except Exception as e:
            print(f"âš ï¸  Could not load LSTM model: {e}")
    else:
        print("â„¹ï¸  No model.keras found â€” ASSIST mode disabled until you run train_model.py")

    typed_text      = ""
    current_hover   = None
    hover_start     = 0.0
    last_press_time = 0.0
    vis_key         = None
    vis_time        = 0.0

    MODES         = ["GRID","AIR","ASL","FACE","ASSIST","MEMO","MAIN_MENU"]
    input_mode    = "MAIN_MENU"
    px, py        = 0, 0
    last_draw     = 0.0
    air_notice    = ""
    air_notice_until = 0.0
    x_prev        = None
    y_prev        = None
    current_theme = 0
    trail         = []
    last_vol_y    = None
    last_hand     = None   # last detected hand, for re-drawing over solid UIs
    last_cur      = (0, 0)
    escape_start  = 0.0

    # ASL state
    asl_stable    = ""
    asl_t0        = 0.0
    pinch_active  = False
    pinch_start   = 0.0

    # ASSIST state
    frame_buffer      = collections.deque(maxlen=ASSIST_FRAMES)
    assist_gesture    = ""
    assist_conf       = 0.0
    assist_alert_until= 0.0
    assist_last_fire  = 0.0
    alert_color       = (0,0,180)

    drawing_canvas = None

    memo_session = None
    if MEMO_AVAILABLE:
        try:
            memo_session = MemoSession(tts_engine=tts)
            print("✅ MEMO mode ready — personal object memory")
        except Exception as e:
            print(f"⚠️  MEMO init failed: {e}")

    # Biometric face identification (LBPH — see face_mode.py)
    face_id = FaceID() if FACE_AVAILABLE else None
    if face_id is not None:
        n = face_id.trained_count()
        print(f"✅ FACE mode ready — {n} known person(s)" if n else
              "ℹ️  FACE mode ready — no known_faces/ photos yet; drop <name>.jpg to enable ID")
    face_overlay      = []      # (x, y, w, h, name, conf) from the last detection
    face_announce_until = 0.0   # cooldown so we don't say hello every frame
    # voice enrollment: LEARN collects face frames over ~2 s, then asks the
    # user to SAY their name; the next time the face appears the app greets
    # them by name. phases: "" -> "capturing" -> "listening"
    face_learn_phase    = ""
    face_learn_name     = ""
    face_learn_until    = 0.0
    face_learn_timeout  = 0.0
    face_learn_samples  = []
    face_learn_last     = 0.0
    face_learn_status   = ""
    face_listen         = {"name": None, "msg": "", "done": False}

    # Per-frame UI state — initialised here so frame-1 never raises UnboundLocalError
    active_highlight = None
    progress_pct     = 0.0

    try:
        while True:
            if demo:
                ok, frame = True, demo.next_frame()
            else:
                ok, frame = cap.read()
            if not ok: break
            frame = cv2.flip(frame, 1)

            if drawing_canvas is None or drawing_canvas.shape!=frame.shape:
                drawing_canvas = np.zeros_like(frame)

            h, w, _ = frame.shape
            predictions = get_predictions(typed_text)

            # FACE mode: detect + identify faces every frame (independent of the
            # hand) so tags stay live even when the user isn't gesturing.
            if input_mode == "FACE" and face_id is not None:
                face_overlay = []
                for (fx, fy, fw, fh) in face_id.detect(frame):
                    crop = frame[fy:fy + fh, fx:fx + fw]
                    name, conf = face_id.identify(crop)
                    face_overlay.append((fx, fy, fw, fh, name, conf))

                # ── enrollment state machine (works with or without a hand) ──
                #   capturing: collect face frames for ~2 s
                #   listening: prompt the name, then recognize it from the mic
                now = time.time()
                if face_learn_phase == "capturing":
                    if now < face_learn_until:
                        largest = max(face_overlay, key=lambda b: b[2] * b[3], default=None)
                        if largest is None:
                            face_learn_status = (f"capturing {face_learn_name}... "
                                                 f"face not in view")
                        elif now - face_learn_last > 0.18:
                            fx, fy, fw, fh = largest[:4]
                            # pad the crop ~25% so the face fills the frame
                            # consistently across samples
                            px, py = int(fw * 0.25), int(fh * 0.25)
                            x0, y0 = max(0, fx - px), max(0, fy - py)
                            x1, y1 = min(w, fx + fw + px), min(h, fy + fh + py)
                            crop = frame[y0:y1, x0:x1]
                            if crop.size:
                                face_learn_samples.append(crop)
                                face_learn_last = now
                                face_learn_status = (f"capturing {face_learn_name}... "
                                                     f"{len(face_learn_samples)} samples")
                    else:
                        # capture window closed — ask for the spoken name
                        face_learn_phase = "listening"
                        face_learn_status = "SAY YOUR NAME NOW..."
                        face_learn_timeout = now + 9.0
                        face_listen = {"name": None, "msg": "", "done": False}
                        try:
                            tts.say("Say your name now")
                            tts.runAndWait()
                        except Exception:
                            pass
                        threading.Thread(target=_listen_worker,
                                         args=(face_listen,), daemon=True).start()
                elif face_learn_phase == "listening":
                    if face_listen["done"] or now > face_learn_timeout:
                        nm = face_listen.get("name")
                        if not nm:
                            # recognition failed — fall back to the text box
                            fb = (typed_text or "Person").strip().split()
                            nm = fb[0] if fb else "Person"
                            print(f"⚠️  Voice: {face_listen.get('msg', 'no name')} - "
                                  f"saved as {nm}")
                        if face_learn_samples:
                            try:
                                _save_learned(tts, face_id, nm, face_learn_samples)
                                face_learn_status = f"learned {nm}!"
                                print(f"✅ Learned {nm} from "
                                      f"{len(face_learn_samples)} samples")
                            except Exception as e:
                                face_learn_status = "learn failed - try again"
                                print(f"⚠️  LEARN failed: {e}")
                        else:
                            face_learn_status = "no face samples - try again"
                            print("⚠️  LEARN skipped - no face samples captured")
                        face_learn_phase = ""
                        face_learn_samples = []

            # Compute the clickable layout first so the demo pilot can aim at buttons.
            if input_mode == "MAIN_MENU":
                button_list = draw_main_menu(frame, active_highlight, progress_pct, draw=False)
            else:
                button_list = draw_top_nav(frame, active_highlight, progress_pct, input_mode, draw=False)
                # MEMO buttons are collected in the hand / no-hand branches below
                # so the state machine runs exactly once per frame with real hand data.
                if input_mode not in ("ASSIST", "AIR", "MEMO", "FACE"):
                    button_list += draw_keyboard(frame, predictions=predictions,
                                                 mode=input_mode,
                                                 theme_idx=current_theme,
                                                 asl_letter=asl_stable,
                                                 asl_progress=min((time.time()-asl_t0)/ASL_HOLD_TIME,1.0) if asl_stable else 0.0,
                                                 draw=False)

            rgb    = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            if demo:
                result = demo.next_result(button_list, input_mode, typed_text)
            else:
                result = hands.process(rgb)

            active_highlight = None
            progress_pct     = 0.0

            if result.multi_hand_landmarks:
                if check_escape_gesture(result, w, h):
                    if escape_start == 0.0:
                        escape_start = time.time()
                    elif time.time() - escape_start > 2.0:
                        input_mode = "MAIN_MENU"
                        escape_start = 0.0
                        cv2.putText(frame, "ESCAPING...", (w//2-150, h//2),
                                    cv2.FONT_HERSHEY_DUPLEX, 1.5, (0,0,255), 4)
                else:
                    escape_start = 0.0

                handLms = result.multi_hand_landmarks[0]
                lm = [(int(l.x*w),int(l.y*h)) for l in handLms.landmark]
                if True:
                    pass  # indent guard

                    # EMA smoothing on index fingertip
                    rx,ry = float(lm[8][0]),float(lm[8][1])
                    if x_prev is None:
                        x_prev,y_prev = rx,ry; filt_x,filt_y = rx,ry
                    else:
                        filt_x = EMA_ALPHA*rx+(1-EMA_ALPHA)*x_prev
                        filt_y = EMA_ALPHA*ry+(1-EMA_ALPHA)*y_prev
                        x_prev,y_prev = filt_x,filt_y
                    cx,cy = int(filt_x),int(filt_y)

                    # Magic trail
                    trail.append((cx,cy))
                    if len(trail)>20: trail.pop(0)
                    for ti in range(1,len(trail)):
                        th=int(np.interp(ti,[0,len(trail)],[1,10]))
                        cv2.line(frame,trail[ti-1],trail[ti],
                                 THEMES[current_theme]["hover"],th)

                    # â”€â”€ ASSIST mode: feed LSTM â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
                    if input_mode == "ASSIST":
                        # Build 63-dim vector from landmarks
                        vec = np.array([[l.x,l.y,l.z]
                                        for l in handLms.landmark],
                                       dtype=np.float32).flatten()
                        frame_buffer.append(vec)

                        if len(frame_buffer)==ASSIST_FRAMES and lstm_model is not None:
                            seq    = np.expand_dims(np.array(frame_buffer), 0)  # (1,30,63)
                            probs  = lstm_model.predict(seq, verbose=0)[0]
                            best   = int(np.argmax(probs))
                            conf   = float(probs[best])
                            g_name = label_map[best] if label_map else GESTURES[best]

                            assist_gesture = g_name
                            assist_conf    = conf

                            if conf >= ASSIST_THRESHOLD and (time.time()-assist_last_fire) > ASSIST_COOLDOWN:
                                assist_last_fire  = time.time()
                                assist_alert_until= time.time() + 3.0
                                alert_color = fire_action(g_name, conf, tts, frame.shape)
                                typed_text += f"[{g_name}] "
                        elif lstm_model is None:
                            cv2.putText(frame,
                                        "Run train_model.py first to enable ASSIST mode",
                                        (50,350),cv2.FONT_HERSHEY_SIMPLEX,0.75,(0,100,255),2)

                        draw_assist_overlay(frame, assist_gesture, assist_conf,
                                            alert_color, assist_alert_until)

                    # â”€â”€ AIR mode â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
                    elif input_mode == "AIR":
                        # Compare RAW thumb vs RAW index for the pinch: the filtered
                        # index tip lags during motion, which used to break strokes
                        # mid-draw once the lag pushed the distance over the threshold.
                        tx, ty = lm[4][0], lm[4][1]
                        ix, iy = lm[8][0], lm[8][1]
                        if math.hypot(ix - tx, iy - ty) < 45:
                            if px == 0 and py == 0: px, py = cx, cy
                            cv2.line(drawing_canvas, (px, py), (cx, cy), (255, 255, 255), 16)
                            px, py = cx, cy; last_draw = time.time()
                        else:
                            px, py = 0, 0

                    # â”€â”€ ASL mode â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
                    elif input_mode == "ASL":
                        letter = get_asl_letter(lm)
                        if letter:
                            if letter==asl_stable:
                                elapsed=time.time()-asl_t0
                                if elapsed>=ASL_HOLD_TIME and (time.time()-last_press_time)>ASL_HOLD_TIME:
                                    typed_text+=letter; pyautogui.press(letter.lower())
                                    last_press_time=time.time()
                                    asl_stable=""; asl_t0=0.0
                                    winsound.PlaySound("SystemDefault",winsound.SND_ALIAS|winsound.SND_ASYNC)
                            else:
                                asl_stable=letter; asl_t0=time.time()
                        else:
                            asl_stable=""
                        # += not =: keep the top-nav MAIN MENU / SPEAK buttons
                        # hoverable — overwriting here dropped them, so the
                        # back button could not be clicked while a hand was visible.
                        button_list += draw_keyboard(frame, mode=input_mode,
                                                     theme_idx=current_theme,
                                                     asl_letter=asl_stable,
                                                     asl_progress=min((time.time()-asl_t0)/ASL_HOLD_TIME,1.0) if asl_stable else 0.0)

                    # â”€â”€ MEMO mode â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
                    elif input_mode == "MEMO":
                        if memo_session:
                            memo_buttons, typed_text = memo_session.update(frame, lm, cx, cy, typed_text, draw=False)
                            button_list += memo_buttons
                        else:
                            cv2.putText(frame, "MEMO init failed", (50, 350), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

                    # ─── FACE mode ──────────────────────────────────────────
                    elif input_mode == "FACE":
                        if face_id is not None:
                            # Say hello once when a known person appears (cooldown)
                            now = time.time()
                            if face_overlay and now > face_announce_until:
                                seen = sorted({n for (_, _, _, _, n, _) in face_overlay if n})
                                if seen:
                                    try:
                                        tts.say("Hello, " + seen[0])
                                        tts.runAndWait()
                                    except Exception:
                                        pass
                                    face_announce_until = now + 5.0
                            # LEARN button joins the hover list (drawn later with
                            # resolved hover state so it still paints over the feed)
                            button_list += draw_face_overlay(
                                frame, face_overlay, hover_key=None, progress=0.0,
                                typed_text=typed_text, theme_idx=current_theme,
                                draw=False, learn_status=face_learn_status)

                    # GRID mode gestures
                    elif input_mode=="GRID":
                        # Pinch detection (thumb + index finger) â†’ ASL mode entry
                        thumb_idx_dist=_dist(lm[4],lm[8])
                        if thumb_idx_dist<40:  # Pinch detected
                            if not pinch_active:
                                pinch_start=time.time()
                                pinch_active=True
                                cv2.putText(frame,"PINCH HOLD FOR ASL MODE",(60,50),
                                            cv2.FONT_HERSHEY_SIMPLEX,0.75,(0,255,255),2)
                            else:
                                elapsed_pinch=time.time()-pinch_start
                                if elapsed_pinch>=PINCH_HOLD:
                                    input_mode="ASL"
                                    asl_stable=""; trail.clear()
                                    winsound.PlaySound("SystemDefault",winsound.SND_ALIAS|winsound.SND_ASYNC)
                                    pinch_active=False
                        else:
                            pinch_active=False
                        
                        # Volume gesture (four fingers up)
                        fi=[1 if lm[8][1]<lm[6][1] else 0,
                            1 if lm[12][1]<lm[10][1] else 0,
                            0 if lm[16][1]>lm[14][1] else 1,
                            0 if lm[20][1]>lm[18][1] else 1]
                        if fi==[1,1,0,0]:
                            cv2.putText(frame,"VOLUME CONTROL",(60,50),
                                        cv2.FONT_HERSHEY_SIMPLEX,0.8,(100,255,100),2)
                            vy=lm[8][1]
                            if last_vol_y is not None:
                                dy=vy-last_vol_y
                                if dy<-15:  pyautogui.press('volumeup');  last_vol_y=vy
                                elif dy>15: pyautogui.press('volumedown');last_vol_y=vy
                            else: last_vol_y=vy
                        else: last_vol_y=None

                    # Cursor dot
                    cv2.circle(frame,(cx,cy),6,(255,255,255),cv2.FILLED)
                    cv2.circle(frame,(cx,cy),14,THEMES[current_theme]["hover"],2,cv2.LINE_AA)

                    # Hover-to-click
                    dk=get_hovered_key(cx,cy,button_list)
                    if dk:
                        kid=dk[0]
                        if current_hover!=kid: current_hover=kid; hover_start=time.time()
                        elapsed=time.time()-hover_start
                        climit=BACKSPACE_COOLDOWN if kid=="<" else HOVER_DELAY
                        progress_pct=min(elapsed/climit,1.0)
                        dk[5]=THEMES[current_theme]["hover"]
                        active_highlight=dk

                        if elapsed>=climit and (time.time()-last_press_time)>climit:
                            last_press_time=time.time()
                            dk[5]=THEMES[current_theme]["press"]
                            vis_key=dk; vis_time=time.time()
                            winsound.PlaySound("SystemDefault",winsound.SND_ALIAS|winsound.SND_ASYNC)

                            if kid=="TOGGLE_MODE":
                                idx=MODES.index(input_mode)
                                input_mode=MODES[(idx+1)%len(MODES)]
                                drawing_canvas=np.zeros_like(frame)
                                asl_stable=""; trail.clear()
                                frame_buffer.clear(); assist_gesture=""
                                if input_mode == "MEMO" and memo_session:
                                    memo_session.on_enter()
                            elif kid=="MAIN_MENU":
                                input_mode = "MAIN_MENU"
                                escape_start = 0.0
                            elif kid == "FACE":
                                # keep typed_text: it's the name LEARN will enroll
                                input_mode = "FACE"
                                drawing_canvas = np.zeros_like(frame)
                                asl_stable = ""; trail.clear()
                            elif kid in ("GRID", "ASL", "AIR", "ASSIST", "MEMO"):
                                input_mode = kid
                                drawing_canvas = np.zeros_like(frame)
                                asl_stable = ""; trail.clear(); typed_text = ""
                                if kid == "MEMO" and memo_session:
                                    memo_session.on_enter()
                            elif kid=="CLEAR_CANVAS": drawing_canvas=np.zeros_like(frame)
                            elif kid=="THEME":        current_theme=(current_theme+1)%len(THEMES)
                            elif kid=="SPEAK":
                                if typed_text.strip():
                                    try:
                                        tts.say(typed_text)
                                        tts.runAndWait()
                                    except Exception as e:
                                        print(f"TTS Speech Error: {e}")
                            elif kid.startswith("PRED_"):
                                word=dk[6]
                                if word!="...":
                                    ws=typed_text.split(" ")
                                    for _ in range(len(ws[-1])): pyautogui.press('backspace')
                                    ws[-1]=word; typed_text=" ".join(ws)+" "
                                    pyautogui.typewrite(word+" ")
                            elif kid == "LEARN_FACE":
                                if face_id is not None:
                                    # 1) capture ~2 s of face frames, then
                                    # 2) ask the user to SAY their name, then
                                    # 3) next time the face appears -> greeting
                                    nm = (typed_text or "Person").strip().split()
                                    nm = nm[0] if nm else "Person"
                                    face_learn_name = nm
                                    face_learn_phase = "capturing"
                                    face_learn_until = time.time() + 2.0
                                    face_learn_timeout = 0.0
                                    face_learn_samples = []
                                    face_learn_last = 0.0
                                    face_learn_status = (f"capturing {nm}... "
                                                         "look at the camera")
                                    print(f"🎥 Capturing {nm} for 2s - then say your name")
                            elif kid.startswith("MEMO_"):
                                if memo_session:
                                    typed_text = memo_session.handle_button(kid, typed_text)
                            else:
                                kc=dk[0]
                                if   kc=="Space": typed_text+=" ";           pyautogui.press('space')
                                elif kc=="<":     typed_text=typed_text[:-1];pyautogui.press('backspace')
                                elif kc.isdigit():typed_text+=kc;            pyautogui.press(kc)
                                else:             typed_text+=kc;            pyautogui.press(kc.lower())
                    else:
                        current_hover=None

                    mp_draw.draw_landmarks(frame,handLms,mp_hands.HAND_CONNECTIONS)
                    last_hand = handLms
                    last_cur  = (cx, cy)
            else:
                last_hand = None
                trail.clear()
                if input_mode=="ASSIST" and time.time()<assist_alert_until:
                    draw_assist_overlay(frame,assist_gesture,assist_conf,
                                        alert_color,assist_alert_until)
                elif input_mode=="MEMO" and memo_session:
                    # No hand — still refresh button list for hover detection; draw happens later
                    memo_buttons, typed_text = memo_session.update(
                        frame, None, -1, -1, typed_text,
                        hover_key=None, progress=0.0, draw=False
                    )
                    button_list += memo_buttons
                asl_stable=""

            # AIR mode: auto-read the canvas after 1.5s of no drawing — runs
            # whether or not the hand is still visible (lift hand to submit).
            if input_mode == "AIR" and last_draw > 0 and (time.time() - last_draw) > 1.5:
                if not TESSERACT_OK:
                    air_notice = "OCR unavailable - install tesseract to auto-read"
                    air_notice_until = time.time() + 3.0
                else:
                    try:
                        gray = cv2.cvtColor(drawing_canvas, cv2.COLOR_BGR2GRAY)
                        gray = cv2.bitwise_not(gray)
                        gray = cv2.dilate(gray, np.ones((5, 5), np.uint8), iterations=2)
                        gray = cv2.copyMakeBorder(gray, 100, 100, 100, 100,
                                                  cv2.BORDER_CONSTANT, value=[255, 255, 255])
                        det = pytesseract.image_to_string(
                            gray, config='--psm 10 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
                        ).strip()
                        if det:
                            typed_text += det
                            pyautogui.typewrite(det)
                            air_notice = f"read: {det}"
                        else:
                            air_notice = "couldn't read that - draw one clear letter"
                    except Exception:
                        air_notice = "OCR failed - try again"
                    air_notice_until = time.time() + 2.5
                drawing_canvas = np.zeros_like(frame)
                last_draw = 0.0

            if vis_key and (time.time()-vis_time<0.15): active_highlight=vis_key

            if input_mode == "MAIN_MENU":
                draw_main_menu(frame, hover_key=active_highlight, progress=progress_pct, draw=True)
                if last_hand is not None:
                    # the solid menu covers the hand — re-draw the fingertip so
                    # the user can still see where they are aiming
                    mp_draw.draw_landmarks(frame, last_hand, mp_hands.HAND_CONNECTIONS)
                    cv2.circle(frame, last_cur, 6, (255, 255, 255), cv2.FILLED)
                    cv2.circle(frame, last_cur, 14, THEMES[current_theme]["hover"], 2, cv2.LINE_AA)
            else:
                draw_top_nav(frame, hover_key=active_highlight, progress=progress_pct, mode=input_mode, draw=True)
                if input_mode == "MEMO" and memo_session:
                    # draw=True pass: render MEMO UI with resolved hover state.
                    # run_state=False → paint only, never re-runs the state machine.
                    memo_session.update(
                        frame, None, -1, -1, typed_text,
                        hover_key=active_highlight, progress=progress_pct,
                        draw=True, run_state=False
                    )
                elif input_mode == "FACE" and face_id is not None:
                    # paint tags + LEARN with the resolved hover state
                    draw_face_overlay(frame, face_overlay,
                                      hover_key=active_highlight,
                                      progress=progress_pct,
                                      typed_text=typed_text,
                                      theme_idx=current_theme, draw=True,
                                      learn_status=face_learn_status)
                elif input_mode not in ("ASSIST", "AIR", "FACE"):
                    # GRID draws its own solid console deck inside draw_keyboard
                    draw_keyboard(frame, highlight_key=active_highlight,
                                  progress=progress_pct, predictions=predictions,
                                  mode=input_mode, theme_idx=current_theme, draw=True)

            if input_mode == "AIR":
                frame = cv2.addWeighted(frame, 0.3, np.zeros_like(frame), 0.7, 0)
                frame = cv2.addWeighted(frame, 1, drawing_canvas, 1.0, 0)
                if air_notice and time.time() < air_notice_until:
                    cv2.putText(frame, air_notice, (60, 262),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (120, 235, 170), 2, cv2.LINE_AA)
            elif input_mode == "ASSIST":
                ui_overlay = frame.copy()
                frame[:] = (20, 25, 30)
                cv2.addWeighted(ui_overlay, 1.0, frame, 0.0, 0, frame)

            if input_mode in ("GRID", "AIR", "ASL"):
                T = THEMES[current_theme]
                _glass(frame, 260, 20, 1030, 74, T["panel"], alpha=0.82, radius=10)
                cv2.rectangle(frame, (260, 20), (1030, 74), T["accent"], 1, cv2.LINE_AA)
                txt = typed_text[-24:]
                cv2.putText(frame, txt, (280, 56),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.0, T["text"], 2, cv2.LINE_AA)
                # blinking caret
                if int(time.time() * 2) % 2 == 0:
                    sz = cv2.getTextSize(txt, cv2.FONT_HERSHEY_SIMPLEX, 1.0, 2)[0]
                    cv2.rectangle(frame, (282 + sz[0], 30), (290 + sz[0], 58), T["hover"], -1)

            if demo:
                cv2.rectangle(frame, (0, h-26), (w, h), (0, 0, 0), -1)
                cv2.putText(frame, "DEMO MODE - synthetic hand (no webcam)  |  " + demo.status(),
                            (10, h-8), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (60, 200, 255), 1, cv2.LINE_AA)

            cv2.imshow("Emergency AI Communication Interface", frame)
            # 30 fps pacing in demo mode so the synthetic hand glides instead of teleporting
            if cv2.waitKey(33 if demo else 1)&0xFF==ord('q'): break
    finally:
        if cap is not None:
            cap.release()
        cv2.destroyAllWindows()

if __name__=="__main__":
    main()
