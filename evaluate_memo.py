"""
evaluate_memo.py — Evaluation harness for object memory matching.
Computes precision/recall on held-out images per object folder.

Usage:
  python evaluate_memo.py --folder demo_objects/
  python evaluate_memo.py --folder demo_objects/ --holdout 0.3
"""

import argparse
import glob
import os
from collections import defaultdict

import cv2
import numpy as np

from memory.embedder import ObjectEmbedder
from memory.matcher import ObjectMatcher


def evaluate(folder: str, holdout: float = 0.3, threshold: float = 0.78):
    embedder = ObjectEmbedder()
    matcher = ObjectMatcher(embedder, threshold=threshold)

    objects = {}
    for sd in sorted(os.listdir(folder)):
        path = os.path.join(folder, sd)
        if not os.path.isdir(path):
            continue
        imgs = []
        for ext in ("*.jpg", "*.jpeg", "*.png"):
            imgs.extend(glob.glob(os.path.join(path, ext)))
        if len(imgs) >= 2:
            objects[sd] = sorted(imgs)

    if not objects:
        print("Need subfolders with at least 2 images each.")
        return

    tp = fp = fn = tn_attempts = 0
    confusions = defaultdict(int)

    print(f"\n{'='*60}")
    print(f"  MEMO Evaluation — backend: {embedder.backend}")
    print(f"{'='*60}\n")

    for name, imgs in objects.items():
        n_test = max(1, int(len(imgs) * holdout))
        train_imgs = imgs[:-n_test]
        test_imgs = imgs[-n_test:]

        catalog = []
        for i, path in enumerate(train_imgs):
            img = cv2.imread(path)
            if img is None:
                continue
            vec = embedder.embed(img)
            catalog.append({
                "embed_id": i,
                "object_id": hash(name) % 10000,
                "vector": embedder.to_bytes(vec),
                "name": name.replace("_", " "),
                "note": "",
                "thumbnail_path": path,
                "is_medication": 0,
            })

        for path in test_imgs:
            img = cv2.imread(path)
            if img is None:
                continue
            vec = embedder.embed(img)
            match = matcher.match(vec, catalog)
            if match and match.name.replace(" ", "_") == name.replace(" ", "_"):
                tp += 1
            elif match:
                fp += 1
                confusions[(name, match.name)] += 1
            else:
                fn += 1

    total = tp + fp + fn
    precision = tp / (tp + fp) if (tp + fp) else 0
    recall = tp / (tp + fn) if (tp + fn) else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0

    print(f"  True positives:  {tp}")
    print(f"  False positives: {fp}")
    print(f"  False negatives: {fn}")
    print(f"  Precision:       {precision*100:.1f}%")
    print(f"  Recall:          {recall*100:.1f}%")
    print(f"  F1:              {f1*100:.1f}%")
    if confusions:
        print("\n  Confusions:")
        for (true, pred), count in confusions.items():
            print(f"    {true} → {pred}: {count}")
    print()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--folder", "-f", required=True)
    p.add_argument("--holdout", type=float, default=0.3)
    p.add_argument("--threshold", type=float, default=0.78)
    args = p.parse_args()
    evaluate(args.folder, args.holdout, args.threshold)


if __name__ == "__main__":
    main()
