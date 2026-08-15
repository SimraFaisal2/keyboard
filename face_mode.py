"""face_mode.py — biometric face identification (OpenCV LBPH).

Trains a Local Binary Patterns Histograms recognizer on photos in
``known_faces/`` and identifies people live from the camera feed:

    known_faces/
        Alex/         → one folder per person (any number of photos inside)
            a1.jpg
        Sam.jpg       → or a single photo per person, named "<name>.jpg"

The recognizer is the classic LBPH algorithm (cv2.face) — no extra
dependencies beyond opencv-contrib (already used by the app).
"""

from __future__ import annotations

import os
import threading

import cv2
import numpy as np

KNOWN_DIR = "known_faces"
IMG_EXTS = (".jpg", ".jpeg", ".png")
MATCH_CONFIDENCE = 60.0   # LBPH confidence below this = a match


class FaceID:
    """Detect + identify faces. thread-safe (predict/train take a lock)."""

    def __init__(self, known_dir: str = KNOWN_DIR):
        self.known_dir = known_dir
        self.cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        self.names: list[str] = []
        self.model = None          # cv2.face.LBPHFaceRecognizer or None
        self._lock = threading.Lock()
        self.reload()

    # ------------------------------------------------------------- training
    def reload(self) -> int:
        """Re-scan known_faces/ and retrain. Returns the number of people."""
        with self._lock:
            self.names, self.model = [], None
            xs, ys = [], []
            if not os.path.isdir(self.known_dir):
                return 0
            for label, entry in enumerate(sorted(os.listdir(self.known_dir))):
                full = os.path.join(self.known_dir, entry)
                imgs: list[str] = []
                if os.path.isdir(full):
                    name = entry
                    imgs = [os.path.join(full, f) for f in sorted(os.listdir(full))
                            if f.lower().endswith(IMG_EXTS)]
                elif entry.lower().endswith(IMG_EXTS):
                    name = os.path.splitext(entry)[0]
                    imgs = [full]
                if not imgs:
                    continue
                self.names.append(name)
                for p in imgs:
                    prep = self._prep(cv2.imread(p))
                    if prep is not None:
                        xs.append(prep)
                        ys.append(label)
            if xs:
                model = cv2.face.LBPHFaceRecognizer_create()
                model.train(xs, np.array(ys, dtype=np.int32))
                self.model = model
            return len(self.names)

    @staticmethod
    def _prep(img):
        if img is None:
            return None
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray = cv2.resize(gray, (100, 100))
        return cv2.equalizeHist(gray)

    # ------------------------------------------------------------- runtime
    def detect(self, frame):
        """Return a list of (x, y, w, h) face boxes in the frame."""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        return self.cascade.detectMultiScale(
            gray, scaleFactor=1.15, minNeighbors=5, minSize=(60, 60))

    def identify(self, face_img) -> tuple[str | None, float]:
        """Return (name, confidence) or (None, confidence) for a face crop."""
        if self.model is None:
            return None, 999.0
        prep = self._prep(face_img)
        if prep is None:
            return None, 999.0
        with self._lock:
            label, conf = self.model.predict(prep)
        if conf < MATCH_CONFIDENCE and 0 <= label < len(self.names):
            return self.names[label], float(conf)
        return None, float(conf)

    def trained_count(self) -> int:
        return len(self.names) if self.model is not None else 0
