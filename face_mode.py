"""face_mode.py — biometric face identification (InsightFace embeddings).

Replaces the old LBPH recognizer (which could not bridge lighting / pose
drift between enrollment and runtime) with a modern face-embedding engine:

  InsightFace (buffalo_s)  →  512-d normalized embedding per face
  identity                  →  cosine similarity against enrolled people

The model (buffalo_s: detector + landmarks + recognizer, ~150 MB) is
downloaded automatically on first run and cached in ~/.insightface.
Enrollments are stored per person as ``known_faces/<Name>/embedding.npy``
plus the raw ``sample_*.jpg`` captures for reference.
"""

from __future__ import annotations

import os
import threading

import numpy as np

KNOWN_DIR = "known_faces"
# Cosine similarity at/above this = the same person. Measured on this
# camera: same person 0.94–0.98, so 0.5 leaves a huge safety margin.
MATCH_SIMILARITY = 0.5


class FaceID:
    """Detect + identify faces with InsightFace embeddings.

    The model initializes in a background thread (it takes a few seconds
    and downloads on first run), so the app can start immediately.
    """

    def __init__(self, known_dir: str = KNOWN_DIR):
        self.known_dir = known_dir
        self.app = None            # FaceAnalysis or None until ready
        self.init_error = ""
        self.embeddings: dict[str, tuple[np.ndarray, int]] = {}  # name -> (mean emb, n)
        self._lock = threading.Lock()
        threading.Thread(target=self._init_app, daemon=True).start()
        self._load_from_disk()

    # ------------------------------------------------------------ model init
    def _init_app(self):
        try:
            from insightface.app import FaceAnalysis
            app = FaceAnalysis(name="buffalo_s", providers=["CPUExecutionProvider"])
            app.prepare(ctx_id=-1, det_size=(640, 640))
            with self._lock:
                self.app = app
        except Exception as e:      # pragma: no cover
            self.init_error = str(e)

    def ready(self) -> bool:
        return self.app is not None

    # ------------------------------------------------------------ storage
    def _load_from_disk(self) -> int:
        """Load every person's stored embedding. Returns the person count."""
        with self._lock:
            self.embeddings = {}
            if not os.path.isdir(self.known_dir):
                return 0
            for entry in os.listdir(self.known_dir):
                emb_path = os.path.join(self.known_dir, entry, "embedding.npy")
                if os.path.isfile(emb_path):
                    try:
                        emb = np.load(emb_path)
                        self.embeddings[entry] = (emb.astype(np.float32), 1)
                    except Exception:
                        continue
            return len(self.embeddings)

    def add_person(self, name: str, embeddings: list[np.ndarray]) -> int:
        """Persist a person: mean of the captured embeddings + sample files
        are saved by the caller. Returns the new total person count."""
        mean = np.mean(embeddings, axis=0).astype(np.float32)
        norm = float(np.linalg.norm(mean))
        if norm > 0:
            mean = mean / norm
        with self._lock:
            self.embeddings[name] = (mean, len(embeddings))
        d = os.path.join(self.known_dir, name)
        os.makedirs(d, exist_ok=True)
        np.save(os.path.join(d, "embedding.npy"), mean)
        return len(self.embeddings)

    def trained_count(self) -> int:
        return len(self.embeddings)

    def names(self) -> list[str]:
        return sorted(self.embeddings)

    # ------------------------------------------------------------ runtime
    def process(self, frame) -> list[dict]:
        """Detect + identify every face in the frame.

        Returns a list of:
          {"bbox": (x1, y1, x2, y2), "name": str|None,
           "similarity": float, "embedding": ndarray|None}
        """
        if self.app is None:
            return []
        faces = self.app.get(frame)
        out = []
        for f in faces:
            emb = f.normed_embedding
            name, sim = None, 0.0
            if emb is not None:
                name, sim = self._match(emb)
            out.append({
                "bbox": tuple(float(v) for v in f.bbox),
                "name": name,
                "similarity": sim,
                "embedding": emb,
                "face": f,
            })
        return out

    def _match(self, emb) -> tuple[str | None, float]:
        """Return (best name, similarity) for an embedding, or (None, best)."""
        best_name, best_sim = None, 0.0
        for nm, (mean, _) in self.embeddings.items():
            sim = float(np.dot(emb, mean))
            if sim > best_sim:
                best_sim, best_name = sim, nm
        if best_sim >= MATCH_SIMILARITY:
            return best_name, best_sim
        return None, best_sim
