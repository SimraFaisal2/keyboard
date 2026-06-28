"""
memory/matcher.py — Cosine-similarity object matching against stored embeddings.
"""

import numpy as np
from typing import List, Optional, Tuple, Dict, Any

from memory.embedder import ObjectEmbedder


class MatchResult:
    __slots__ = ("object_id", "name", "note", "confidence", "embed_id",
                 "thumbnail_path", "voice_clip_path", "is_medication")

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class ObjectMatcher:
    def __init__(
        self,
        embedder: ObjectEmbedder,
        threshold: float = 0.78,
        margin: float = 0.04,
    ):
        self.embedder = embedder
        self.threshold = threshold
        self.margin = margin  # top1 must beat top2 by this much

    def match(
        self,
        query_vec: np.ndarray,
        catalog: List[Dict[str, Any]],
    ) -> Optional[MatchResult]:
        if not catalog or query_vec is None:
            return None

        scores = []
        for entry in catalog:
            stored = self.embedder.from_bytes(entry["vector"])
            sim = float(np.dot(query_vec, stored))
            scores.append((sim, entry))

        scores.sort(key=lambda x: x[0], reverse=True)
        best_sim, best_entry = scores[0]

        if best_sim < self.threshold:
            return None

        if len(scores) > 1:
            second_sim = scores[1][0]
            if best_sim - second_sim < self.margin:
                return None

        return MatchResult(
            object_id=best_entry["object_id"],
            name=best_entry["name"],
            note=best_entry.get("note") or "",
            confidence=best_sim,
            embed_id=best_entry["embed_id"],
            thumbnail_path=best_entry.get("thumbnail_path"),
            voice_clip_path=best_entry.get("voice_clip_path"),
            is_medication=bool(best_entry.get("is_medication")),
        )

    def top_k(
        self,
        query_vec: np.ndarray,
        catalog: List[Dict[str, Any]],
        k: int = 3,
    ) -> List[Tuple[float, Dict[str, Any]]]:
        if not catalog:
            return []
        scored = []
        for entry in catalog:
            stored = self.embedder.from_bytes(entry["vector"])
            sim = float(np.dot(query_vec, stored))
            scored.append((sim, entry))
        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[:k]
