"""
collect_memo.py — Batch-import object photos into the memory vault.
Usage: python collect_memo.py --folder demo_objects/
Each subfolder name becomes the object name; all images inside are embedded.
"""

import argparse
import os
import glob

import cv2

from memory.vault import MemoryVault
from memory.embedder import ObjectEmbedder


def import_folder(folder: str, note: str = "", is_medication: bool = False):
    vault = MemoryVault()
    embedder = ObjectEmbedder()

    if os.path.isfile(folder):
        folders = [(os.path.basename(folder), [folder])]
    elif os.path.isdir(folder):
        subdirs = [d for d in os.listdir(folder)
                   if os.path.isdir(os.path.join(folder, d))]
        if subdirs:
            folders = []
            for sd in subdirs:
                path = os.path.join(folder, sd)
                imgs = []
                for ext in ("*.jpg", "*.jpeg", "*.png", "*.webp"):
                    imgs.extend(glob.glob(os.path.join(path, ext)))
                if imgs:
                    folders.append((sd.replace("_", " "), imgs))
        else:
            imgs = []
            for ext in ("*.jpg", "*.jpeg", "*.png", "*.webp"):
                imgs.extend(glob.glob(os.path.join(folder, ext)))
            name = os.path.basename(folder.rstrip("/\\")) or "object"
            folders = [(name, imgs)]
    else:
        print(f"Not found: {folder}")
        return

    for name, images in folders:
        if not images:
            continue
        pairs = []
        for img_path in images[:5]:
            img = cv2.imread(img_path)
            if img is None:
                continue
            vec = embedder.embed(img)
            thumb = vault.save_thumbnail(img, prefix="import")
            pairs.append((embedder.to_bytes(vec), thumb))
        if pairs:
            oid = vault.add_object(
                name=name,
                note=note,
                embeddings=pairs,
                is_medication=is_medication,
            )
            print(f"  [ok] {name} - {len(pairs)} embedding(s), id={oid}")

    print(f"\nVault now has {len(vault.list_objects())} object(s).")


def main():
    p = argparse.ArgumentParser(description="Import object photos into MEMO vault")
    p.add_argument("--folder", "-f", required=True, help="Folder of images or subfolders")
    p.add_argument("--note", default="", help="Optional note for all imported objects")
    p.add_argument("--medication", action="store_true", help="Mark as medication")
    args = p.parse_args()
    import_folder(args.folder, args.note, args.medication)


if __name__ == "__main__":
    main()
