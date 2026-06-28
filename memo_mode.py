"""
memo_mode.py — Simple Object Memory
====================================
Hold up an object  →  pinch to teach it  →  say its name
Next time you hold up the same object, the computer says its name.

States
------
  WATCHING   – camera constantly tries to match objects in vault.
               Recognised  → name shown + spoken.
               Unknown      → prompt "PINCH to teach this object".
  CAPTURING  – user is pinching; collect 3 embeddings over 1.5 s.
  NAMING     – ask user to say the name (voice) or type it.
"""

import cv2
import numpy as np
import time
import math
import threading
from typing import Optional, List, Tuple

from memory.object_model import EnhancedMemoryVault
from memory.embedder import ObjectEmbedder
from memory.matcher import ObjectMatcher, MatchResult

# ─── Tuning ───────────────────────────────────────────────────────────────────
MATCH_INTERVAL  = 0.4      # seconds between match attempts
RECALL_COOLDOWN = 20.0     # don't repeat the same name within this many seconds
MATCH_THRESHOLD = 0.72
PINCH_HOLD      = 1.5      # seconds to hold pinch before capture fires
CAPTURE_SAMPLES = 3        # embeddings to average per teach
LISTEN_TIMEOUT  = 6.0      # microphone listen window

# Colours (BGR)
C_CYAN    = (255, 220,  80)
C_GREEN   = ( 60, 220,  80)
C_PINK    = (180,  80, 180)
C_WHITE   = (255, 255, 255)
C_GREY    = (160, 160, 160)
C_DARK    = ( 20,  25,  35)
C_RED     = ( 40,  40, 220)
C_BLUE    = (220, 160,  60)


class MemoSession:
    """One MEMO-mode session; call update() each frame."""

    def __init__(self, tts_engine=None):
        self.vault    = EnhancedMemoryVault()
        self.embedder = ObjectEmbedder()
        self.matcher  = ObjectMatcher(self.embedder, threshold=MATCH_THRESHOLD)
        self.tts      = tts_engine

        # ── runtime state ────────────────────────────────────────────
        self.state         = "WATCHING"   # WATCHING | CAPTURING | NAMING
        self.status_msg    = "Hold up an object — I'll remember it for you."
        self.last_match: Optional[MatchResult] = None
        self.last_spoken: dict = {}       # object_id → timestamp last spoken
        self.last_match_t  = 0.0

        # teach workflow
        self.pinch_active  = False
        self.pinch_start   = 0.0
        self.teach_crops: List[np.ndarray] = []
        self.teach_name_buf = ""          # typed name buffer

        # voice listener thread result
        self._listen_result: Optional[str] = None
        self._listening      = False

        # cached catalog (refreshed each frame)
        self._catalog: list = []

    # ─── TTS ──────────────────────────────────────────────────────────────────
    def _speak(self, text: str):
        if not self.tts or not text:
            return
        try:
            self.tts.setProperty("rate", 120)
            self.tts.say(text)
            self.tts.runAndWait()
        except Exception:
            pass

    def _speak_bg(self, text: str):
        """Non-blocking speak so the camera loop doesn't freeze."""
        t = threading.Thread(target=self._speak, args=(text,), daemon=True)
        t.start()

    # ─── Geometry helpers ─────────────────────────────────────────────────────
    @staticmethod
    def _is_pinching(lm, cx, cy) -> bool:
        tx, ty = lm[4][0], lm[4][1]
        return math.hypot(cx - tx, cy - ty) < 45

    @staticmethod
    def _hand_roi(lm, w, h, frame):
        xs = [lm[i][0] for i in range(21)]
        ys = [lm[i][1] for i in range(21)]
        pad = 90
        x1, y1 = max(0, min(xs) - pad), max(0, min(ys) - pad)
        x2, y2 = min(w, max(xs) + pad), min(h, max(ys) + pad)
        crop = frame[y1:y2, x1:x2].copy() if x2 > x1 and y2 > y1 else None
        return crop, (x1, y1, x2, y2)

    # ─── Voice listener (background thread) ───────────────────────────────────
    def _start_listening(self):
        if self._listening:
            return
        self._listening     = True
        self._listen_result = None
        threading.Thread(target=self._listen_thread, daemon=True).start()

    def _listen_thread(self):
        try:
            import speech_recognition as sr
            r = sr.Recognizer()
            with sr.Microphone() as source:
                r.adjust_for_ambient_noise(source, duration=0.3)
                audio = r.listen(source, timeout=LISTEN_TIMEOUT, phrase_time_limit=5)
            text = r.recognize_google(audio).strip()
            self._listen_result = text if text else None
        except Exception:
            self._listen_result = None
        finally:
            self._listening = False

    # ─── Teach: save captured crops ───────────────────────────────────────────
    def _save_object(self, name: str):
        if not self.teach_crops or not name.strip():
            self.status_msg = "Need an object capture AND a name."
            return

        # Average multiple embeddings for robustness
        vecs  = [self.embedder.embed(c) for c in self.teach_crops]
        avg   = np.mean(vecs, axis=0).astype(np.float32)
        norm  = np.linalg.norm(avg)
        if norm > 1e-8:
            avg /= norm
        vec_bytes = self.embedder.to_bytes(avg)

        # Save one thumbnail
        thumb = self.vault.save_thumbnail(self.teach_crops[0], prefix="memo")

        self.vault.add_object(
            name=name.strip(),
            note="",
            embeddings=[(vec_bytes, thumb)],
        )
        self._catalog = []                # force catalog refresh
        self._speak_bg(f"Got it. I'll remember your {name.strip()}.")
        self.status_msg   = f"✅ Remembered: {name.strip()}"
        self.teach_crops  = []
        self.teach_name_buf = ""
        self.state        = "WATCHING"

    # ─── Main update (called every frame) ─────────────────────────────────────
    def update(
        self,
        frame,
        lm,
        cx: int,
        cy: int,
        typed_text: str = "",
        hover_key=None,
        progress: float = 0.0,
        draw: bool = True,
    ) -> Tuple[List, str]:
        """
        Process one frame.  Returns (button_list, typed_text).
        """
        h, w = frame.shape[:2]

        # Refresh embedding catalog lazily
        if not self._catalog:
            self._catalog = self.vault.get_all_embeddings()

        # ── State machine ────────────────────────────────────────────────────
        if self.state == "WATCHING":
            typed_text = self._tick_watching(frame, lm, cx, cy, w, h)

        elif self.state == "CAPTURING":
            typed_text = self._tick_capturing(frame, lm, cx, cy, w, h)

        elif self.state == "NAMING":
            typed_text = self._tick_naming(frame, lm, cx, cy, w, h)

        # ── Draw UI ──────────────────────────────────────────────────────────
        button_list = []
        if draw:
            button_list = self._draw_ui(frame, hover_key, progress, w, h)

        return button_list, typed_text

    # ─── State: WATCHING ─────────────────────────────────────────────────────
    def _tick_watching(self, frame, lm, cx, cy, w, h):
        now = time.time()

        if lm and now - self.last_match_t >= MATCH_INTERVAL and self._catalog:
            self.last_match_t = now
            crop, roi = self._hand_roi(lm, w, h, frame)
            if crop is not None and crop.size > 0:
                vec   = self.embedder.embed(crop)
                match = self.matcher.match(vec, self._catalog)
                if match:
                    self.last_match = match
                    # Speak name if cooldown elapsed
                    last = self.last_spoken.get(match.object_id, 0)
                    if now - last > RECALL_COOLDOWN:
                        self.last_spoken[match.object_id] = now
                        self._speak_bg(f"This is your {match.name}.")
                    self.status_msg = f"I know this: {match.name}"
                else:
                    self.last_match = None
                    self.status_msg = "Unknown object.  PINCH to teach me its name."

        # Pinch → enter CAPTURING
        if lm and self._is_pinching(lm, cx, cy):
            if not self.pinch_active:
                self.pinch_active = True
                self.pinch_start  = time.time()
            elif time.time() - self.pinch_start >= PINCH_HOLD:
                self.state        = "CAPTURING"
                self.teach_crops  = []
                self.pinch_active = False
                self.status_msg   = "Hold the object still — capturing…"
        else:
            self.pinch_active = False

        return ""   # typed_text unchanged

    # ─── State: CAPTURING ────────────────────────────────────────────────────
    def _tick_capturing(self, frame, lm, cx, cy, w, h):
        if lm:
            crop, _ = self._hand_roi(lm, w, h, frame)
            if crop is not None and crop.size > 0:
                self.teach_crops.append(crop)
                if len(self.teach_crops) >= CAPTURE_SAMPLES:
                    # Enough samples — move to naming
                    self.state      = "NAMING"
                    self.status_msg = "Say the object name, or type it below."
                    self._listen_result = None
                    self._start_listening()
                else:
                    self.status_msg = (
                        f"Captured {len(self.teach_crops)}/{CAPTURE_SAMPLES}…"
                    )
        else:
            # Lost hand during capture — restart
            self.state       = "WATCHING"
            self.teach_crops = []
            self.status_msg  = "Hand lost. Try again."

        return ""

    # ─── State: NAMING ───────────────────────────────────────────────────────
    def _tick_naming(self, frame, lm, cx, cy, w, h):
        # Voice result arrived
        if not self._listening and self._listen_result is not None:
            name = self._listen_result
            self._listen_result = None
            self._save_object(name)

        # Voice timed out with nothing — stay in NAMING so user can type
        elif not self._listening and self._listen_result is None and self.teach_name_buf == "":
            self.status_msg = "Couldn't hear. Type the name below and hover SAVE."

        return ""

    # ─── Draw ────────────────────────────────────────────────────────────────
    def _draw_ui(self, frame, hover_key, progress, w, h) -> List:
        button_list = []

        # ── Dark panel background ────────────────────────────────────────────
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, h), C_DARK, -1)
        cv2.addWeighted(overlay, 0.55, frame, 0.45, 0, frame)

        # ── Title ────────────────────────────────────────────────────────────
        cv2.putText(frame, "MEMO — Object Memory",
                    (30, 55), cv2.FONT_HERSHEY_DUPLEX, 1.1, C_CYAN, 2, cv2.LINE_AA)
        objs = len(self.vault.list_objects())
        cv2.putText(frame, f"{objs} object(s) remembered",
                    (30, 85), cv2.FONT_HERSHEY_SIMPLEX, 0.55, C_GREY, 1)

        # ── State-specific visuals ───────────────────────────────────────────
        if self.state == "WATCHING":
            self._draw_watching(frame, w, h)
        elif self.state == "CAPTURING":
            self._draw_capturing(frame, w, h)
        elif self.state == "NAMING":
            button_list += self._draw_naming(frame, hover_key, progress, w, h)

        # ── Status bar ───────────────────────────────────────────────────────
        msg_y = h - 40
        cv2.rectangle(frame, (0, msg_y - 30), (w, h), (10, 15, 25), -1)
        cv2.putText(frame, self.status_msg[:90], (20, msg_y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, C_WHITE, 2, cv2.LINE_AA)

        # ── Pinch progress bar (WATCHING) ─────────────────────────────────────
        if self.state == "WATCHING" and self.pinch_active:
            elapsed = time.time() - self.pinch_start
            prog    = min(elapsed / PINCH_HOLD, 1.0)
            bx1, by1, bx2, by2 = 30, h - 75, 500, h - 57
            cv2.rectangle(frame, (bx1, by1), (bx2, by2), (40, 40, 40), -1)
            cv2.rectangle(frame, (bx1, by1),
                          (bx1 + int((bx2 - bx1) * prog), by2), C_PINK, -1)
            cv2.putText(frame, "Hold pinch to teach…",
                        (bx1 + 6, by1 - 5), cv2.FONT_HERSHEY_SIMPLEX,
                        0.5, C_PINK, 1)

        return button_list

    def _draw_watching(self, frame, w, h):
        if self.last_match:
            m = self.last_match
            # Big name
            cv2.putText(frame, m.name.upper(),
                        (30, h // 2 - 20),
                        cv2.FONT_HERSHEY_DUPLEX, 3.5, C_GREEN, 6, cv2.LINE_AA)
            cv2.putText(frame, f"{m.confidence * 100:.0f}% confidence",
                        (30, h // 2 + 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.85, C_GREEN, 2)
            # Thumbnail if available
            if m.thumbnail_path:
                try:
                    timg = cv2.imread(m.thumbnail_path)
                    if timg is not None:
                        timg = cv2.resize(timg, (140, 140))
                        frame[h // 2 - 60: h // 2 + 80,
                              w - 170: w - 30] = timg
                except Exception:
                    pass
        else:
            # No match yet — gentle prompt
            cv2.putText(frame, "Show me an object…",
                        (30, h // 2),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.4, C_GREY, 2, cv2.LINE_AA)
            cv2.putText(frame,
                        "Pinch (thumb + index) for 1.5 s to teach a new one",
                        (30, h // 2 + 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.62, C_GREY, 1)

    def _draw_capturing(self, frame, w, h):
        n   = len(self.teach_crops)
        pct = n / CAPTURE_SAMPLES
        cv2.putText(frame, "CAPTURING OBJECT…",
                    (30, h // 2 - 30),
                    cv2.FONT_HERSHEY_DUPLEX, 1.6, C_CYAN, 3, cv2.LINE_AA)
        # Progress dots
        for i in range(CAPTURE_SAMPLES):
            col = C_GREEN if i < n else (60, 60, 60)
            cv2.circle(frame, (30 + i * 50, h // 2 + 20), 18, col, -1)
        cv2.putText(frame, f"{n}/{CAPTURE_SAMPLES} frames captured",
                    (30, h // 2 + 65),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.75, C_WHITE, 2)

    def _draw_naming(self, frame, hover_key, progress, w, h) -> List:
        button_list = []

        # Listening indicator
        if self._listening:
            pulse = int(180 + 75 * abs(math.sin(time.time() * 4)))
            cv2.putText(frame, "🎤  LISTENING…",
                        (30, h // 2 - 50),
                        cv2.FONT_HERSHEY_DUPLEX, 1.5, (0, pulse, pulse), 3, cv2.LINE_AA)
            cv2.putText(frame, "Say the object name now",
                        (30, h // 2),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.85, C_WHITE, 2)
        else:
            cv2.putText(frame, "Type the name:",
                        (30, h // 2 - 50),
                        cv2.FONT_HERSHEY_DUPLEX, 1.1, C_CYAN, 2, cv2.LINE_AA)

        # Text input display
        display = self.teach_name_buf or "(type name…)"
        cv2.rectangle(frame, (30, h // 2 - 10), (700, h // 2 + 52), (30, 40, 55), -1)
        cv2.rectangle(frame, (30, h // 2 - 10), (700, h // 2 + 52), C_CYAN, 1)
        cv2.putText(frame, display[-30:], (42, h // 2 + 32),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, C_WHITE, 2)

        # Mini A-Z keyboard
        kw, kh, gap = 46, 40, 4
        rows  = [list("ABCDEFGHI"), list("JKLMNOPQR"), list("STUVWXYZ")]
        y0    = h // 2 + 70
        for ri, row in enumerate(rows):
            for ci, ch in enumerate(row):
                x   = 30 + ci * (kw + gap)
                y   = y0 + ri * (kh + gap)
                kid = f"MEMO_KEY_{ch}"
                hov = hover_key and hover_key[0] == kid
                col = C_PINK if hov else (50, 70, 100)
                cv2.rectangle(frame, (x, y), (x + kw, y + kh), col, -1)
                cv2.rectangle(frame, (x, y), (x + kw, y + kh), (100, 140, 180), 1)
                cv2.putText(frame, ch, (x + 13, y + 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, C_WHITE, 2)
                if hov:
                    pw = int(kw * progress)
                    cv2.rectangle(frame, (x + 2, y + kh - 5),
                                  (x + pw - 2, y + kh - 2), (255, 230, 80), -1)
                button_list.append([kid, x, y, kw, kh, col, ch])

        # Special keys: SPACE  BACK  SAVE  LISTEN
        sy = y0 + 3 * (kh + gap)
        specials = [
            ("MEMO_KEY_SPACE", "SPACE",  30,  130, (50, 90, 50)),
            ("MEMO_KEY_BACK",  "BACK",  170,   90, (80, 50, 50)),
            ("MEMO_SAVE_NAME", "SAVE ✓",270,  100, (30,110, 50)),
            ("MEMO_LISTEN",    "🎤 RE-LISTEN", 380, 160, (70, 50,100)),
        ]
        for kid, label, bx, bw, base_col in specials:
            hov = hover_key and hover_key[0] == kid
            col = C_PINK if hov else base_col
            cv2.rectangle(frame, (bx, sy), (bx + bw, sy + kh), col, -1)
            cv2.rectangle(frame, (bx, sy), (bx + bw, sy + kh), (120, 180, 140), 1)
            cv2.putText(frame, label, (bx + 8, sy + 27),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, C_WHITE, 2)
            if hov:
                pw = int(bw * progress)
                cv2.rectangle(frame, (bx + 3, sy + kh - 5),
                              (bx + pw - 3, sy + kh - 2), (255, 230, 80), -1)
            button_list.append([kid, bx, sy, bw, kh, col, label])

        return button_list

    # ─── Button handler (called by index.py hover-click) ─────────────────────
    def handle_button(self, button_id: str, typed_text: str = "") -> str:
        if button_id == "MEMO_KEY_SPACE":
            self.teach_name_buf += " "
        elif button_id == "MEMO_KEY_BACK":
            self.teach_name_buf = self.teach_name_buf[:-1]
        elif button_id == "MEMO_SAVE_NAME":
            name = self.teach_name_buf.strip() or typed_text.strip()
            if name:
                self._save_object(name)
                return ""
            else:
                self.status_msg = "Type a name first, then hover SAVE."
        elif button_id == "MEMO_LISTEN":
            if not self._listening:
                self._listen_result = None
                self._start_listening()
                self.status_msg = "Listening… say the name now."
        elif button_id.startswith("MEMO_KEY_") and len(button_id) == 10:
            self.teach_name_buf += button_id[-1]
        return typed_text

    # ─── Called when entering MEMO mode ──────────────────────────────────────
    def on_enter(self):
        self._catalog = []        # force refresh
        n = len(self.vault.list_objects())
        self.status_msg = f"MEMO mode — {n} object(s) memorised."
        self._speak_bg("Memory mode. Show me an object, or pinch to teach me something new.")
