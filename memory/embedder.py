"""
memory/embedder.py — On-device visual embeddings via MobileNetV2 (TensorFlow).
Falls back to color-histogram features if TensorFlow is unavailable.
"""

import numpy as np
import cv2

EMBED_DIM = 1280  # MobileNetV2 pooled output
INPUT_SIZE = (224, 224)


class ObjectEmbedder:
    def __init__(self):
        self._model = None
        self._backend = "histogram"
        self._load_model()

    def _load_model(self):
        try:
            import tensorflow as tf
            from tensorflow.keras.applications.mobilenet_v2 import (
                MobileNetV2,
                preprocess_input,
            )

            base = MobileNetV2(
                weights="imagenet",
                include_top=False,
                pooling="avg",
                input_shape=(*INPUT_SIZE, 3),
            )
            self._model = base
            self._preprocess = preprocess_input
            self._backend = "mobilenet"
            print("[MEMO] embedder: MobileNetV2 loaded")
        except Exception as e:
            print(f"[MEMO] embedder: using histogram fallback ({e})")

    @property
    def backend(self) -> str:
        return self._backend

    def crop_center(self, frame_bgr, cx: int, cy: int, size: int = 280):
        h, w = frame_bgr.shape[:2]
        half = size // 2
        x1 = max(0, cx - half)
        y1 = max(0, cy - half)
        x2 = min(w, cx + half)
        y2 = min(h, cy + half)
        return frame_bgr[y1:y2, x1:x2].copy(), (x1, y1, x2, y2)

    def crop_roi(self, frame_bgr, roi: tuple):
        x1, y1, x2, y2 = roi
        h, w = frame_bgr.shape[:2]
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)
        if x2 <= x1 or y2 <= y1:
            return None, roi
        return frame_bgr[y1:y2, x1:x2].copy(), (x1, y1, x2, y2)

    def embed(self, image_bgr: np.ndarray) -> np.ndarray:
        if image_bgr is None or image_bgr.size == 0:
            return np.zeros(EMBED_DIM if self._backend == "mobilenet" else 512, dtype=np.float32)

        if self._backend == "mobilenet":
            rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
            resized = cv2.resize(rgb, INPUT_SIZE)
            batch = np.expand_dims(resized.astype(np.float32), 0)
            batch = self._preprocess(batch)
            vec = self._model.predict(batch, verbose=0)[0]
        else:
            vec = self._histogram_embed(image_bgr)

        norm = np.linalg.norm(vec)
        if norm > 1e-8:
            vec = vec / norm
        return vec.astype(np.float32)

    def _histogram_embed(self, image_bgr: np.ndarray) -> np.ndarray:
        """Lightweight fallback: HSV + spatial color bins."""
        small = cv2.resize(image_bgr, (64, 64))
        hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
        hist_h = cv2.calcHist([hsv], [0], None, [32], [0, 180]).flatten()
        hist_s = cv2.calcHist([hsv], [1], None, [32], [0, 256]).flatten()
        hist_v = cv2.calcHist([hsv], [2], None, [32], [0, 256]).flatten()
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        edge_hist = cv2.calcHist([edges], [0], None, [32], [0, 256]).flatten()
        vec = np.concatenate([hist_h, hist_s, hist_v, edge_hist])
        return vec.astype(np.float32)

    def to_bytes(self, vec: np.ndarray) -> bytes:
        return vec.astype(np.float32).tobytes()

    def from_bytes(self, data: bytes) -> np.ndarray:
        return np.frombuffer(data, dtype=np.float32)
