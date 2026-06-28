"""
create_demo_images.py — Generate sample demo images for MEMO mode testing.
Run: python create_demo_images.py
"""

import os
import math
import cv2
import numpy as np

OUT = os.path.join("demo_objects")


def _rotate(img, deg, scale=1.0):
    h, w = img.shape[:2]
    m = cv2.getRotationMatrix2D((w // 2, h // 2), deg, scale)
    return cv2.warpAffine(img, m, (w, h), borderMode=cv2.BORDER_REPLICATE)


def _noise(img, sigma=8):
    n = np.random.normal(0, sigma, img.shape).astype(np.int16)
    return np.clip(img.astype(np.int16) + n, 0, 255).astype(np.uint8)


def draw_keys(angle=0, bright=1.0):
    img = np.full((400, 400, 3), (35, 30, 25), dtype=np.uint8)
    cv2.rectangle(img, (20, 20), (380, 380), (50, 45, 40), -1)
    # Key 1
    cv2.circle(img, (140, 200), 38, (40, 180, 220), -1)
    cv2.rectangle(img, (170, 185), (240, 205), (40, 180, 220), -1)
    cv2.rectangle(img, (230, 175), (250, 215), (40, 180, 220), -1)
    cv2.rectangle(img, (245, 180), (265, 195), (40, 180, 220), -1)
    # Key 2
    cv2.circle(img, (220, 260), 32, (30, 160, 200), -1)
    cv2.rectangle(img, (245, 250), (310, 268), (30, 160, 200), -1)
    cv2.putText(img, "KEYS", (130, 80), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (200, 200, 200), 2)
    img = _rotate(img, angle)
    img = np.clip(img * bright, 0, 255).astype(np.uint8)
    return _noise(img, 6)


def draw_pill_bottle(angle=0, bright=1.0):
    img = np.full((400, 400, 3), (240, 235, 230), dtype=np.uint8)
    # Bottle body
    cv2.ellipse(img, (200, 260), (70, 110), 0, 0, 360, (40, 90, 200), -1)
    cv2.rectangle(img, (130, 160), (270, 220), (40, 90, 200), -1)
    # Cap
    cv2.rectangle(img, (150, 110), (250, 165), (220, 220, 220), -1)
    cv2.rectangle(img, (150, 110), (250, 130), (180, 180, 180), -1)
    # Label
    cv2.rectangle(img, (155, 200), (245, 280), (255, 255, 255), -1)
    cv2.putText(img, "Rx", (175, 250), cv2.FONT_HERSHEY_SIMPLEX, 1.4, (0, 60, 160), 3)
    cv2.putText(img, "MEDS", (155, 340), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (80, 80, 80), 2)
    img = _rotate(img, angle)
    img = np.clip(img * bright, 0, 255).astype(np.uint8)
    return _noise(img, 5)


def draw_family_photo(angle=0, bright=1.0):
    img = np.full((400, 400, 3), (25, 20, 15), dtype=np.uint8)
    # Frame
    cv2.rectangle(img, (60, 50), (340, 350), (180, 140, 80), 12)
    cv2.rectangle(img, (80, 70), (320, 330), (255, 245, 230), -1)
    # Simple faces
    cv2.circle(img, (160, 170), 45, (180, 140, 110), -1)
    cv2.circle(img, (250, 175), 40, (200, 160, 130), -1)
    cv2.circle(img, (200, 260), 55, (170, 130, 100), -1)
    cv2.putText(img, "FAMILY", (130, 380), cv2.FONT_HERSHEY_SIMPLEX, 0.85, (200, 180, 140), 2)
    img = _rotate(img, angle)
    img = np.clip(img * bright, 0, 255).astype(np.uint8)
    return _noise(img, 5)


def draw_reading_glasses(angle=0, bright=1.0):
    img = np.full((400, 400, 3), (200, 195, 190), dtype=np.uint8)
    cv2.ellipse(img, (150, 200), (55, 40), 0, 0, 360, (30, 30, 30), 3)
    cv2.ellipse(img, (250, 200), (55, 40), 0, 0, 360, (30, 30, 30), 3)
    cv2.line(img, (205, 200), (195, 200), (30, 30, 30), 3)
    cv2.line(img, (110, 195), (70, 180), (30, 30, 30), 3)
    cv2.line(img, (290, 195), (330, 180), (30, 30, 30), 3)
    cv2.putText(img, "GLASSES", (120, 320), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (60, 60, 60), 2)
    img = _rotate(img, angle)
    img = np.clip(img * bright, 0, 255).astype(np.uint8)
    return _noise(img, 5)


OBJECTS = {
    "house_keys": draw_keys,
    "pill_bottle": draw_pill_bottle,
    "family_photo": draw_family_photo,
    "reading_glasses": draw_reading_glasses,
}

VARIANTS = [
    ("angle1.jpg", 0, 1.0),
    ("angle2.jpg", 12, 0.95),
    ("angle3.jpg", -10, 1.05),
]


def main():
    np.random.seed(42)
    for name, drawer in OBJECTS.items():
        folder = os.path.join(OUT, name)
        os.makedirs(folder, exist_ok=True)
        for fname, angle, bright in VARIANTS:
            img = drawer(angle, bright)
            path = os.path.join(folder, fname)
            cv2.imwrite(path, img)
            print(f"  wrote {path}")
    print(f"\nDone — {len(OBJECTS)} object folders in {OUT}/")


if __name__ == "__main__":
    main()
