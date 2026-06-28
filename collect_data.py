"""
collect_data.py — Emergency AI Communication Interface
======================================================
Records 30-frame sequences of MediaPipe hand landmarks for each gesture.
Each sample is saved as a (30, 63) numpy array under  ./data/{GESTURE}/{seq_id}.npy

Run this script ONCE before training. Follow the on-screen prompts.
"""

import cv2
import numpy as np
import mediapipe as mp
import os
import time
import json

# ─── Config ───────────────────────────────────────────────────────────────────
GESTURES        = ["HELP", "EMERGENCY", "PAIN", "WATER", "FOOD", "TOILET", "YES", "NO"]
SEQUENCES       = 30      # training samples per gesture
FRAMES_PER_SEQ  = 30      # frames per sample  (≈1 second at 30 fps)
COUNTDOWN_SEC   = 3       # pause between recordings so user can reset hand
DATA_DIR        = "data"
TYPING_SAMPLES   = 100
TYPING_DATA_DIR  = os.path.join(DATA_DIR, "typing")

# Landmark colours
mp_hands = mp.solutions.hands
hands    = mp_hands.Hands(max_num_hands=1,
                          min_detection_confidence=0.7,
                          min_tracking_confidence=0.7)
mp_draw  = mp.solutions.drawing_utils

# ─── Helpers ──────────────────────────────────────────────────────────────────
def extract_keypoints(landmarks, frame_w, frame_h):
    """Flatten 21 landmarks × (x, y, z) → shape (63,)  (normalised 0-1)."""
    pts = []
    for lm in landmarks.landmark:
        pts.extend([lm.x, lm.y, lm.z])
    return np.array(pts, dtype=np.float32)

def make_dirs():
    for gesture in GESTURES:
        for seq in range(SEQUENCES):
            os.makedirs(os.path.join(DATA_DIR, gesture, str(seq)), exist_ok=True)

def draw_overlay(frame, gesture, seq, collecting, frame_idx, countdown_left=0):
    h, w = frame.shape[:2]
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, 100), (10, 8, 6), -1)
    cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)

    cv2.putText(frame, f"Gesture:  {gesture}",
                (20, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (100, 200, 255), 2)
    cv2.putText(frame, f"Sample:   {seq+1} / {SEQUENCES}",
                (20, 68), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (200, 200, 200), 1)

    if countdown_left > 0:
        cv2.putText(frame, f"Get ready... {countdown_left:.1f}s",
                    (w//2 - 180, h//2), cv2.FONT_HERSHEY_DUPLEX, 1.4,
                    (255, 200, 50), 3, cv2.LINE_AA)
    elif collecting:
        # Red recording dot
        cv2.circle(frame, (w - 40, 40), 16, (0, 0, 255), -1)
        cv2.putText(frame, f"REC  {frame_idx}/{FRAMES_PER_SEQ}",
                    (w - 200, 52), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 0, 255), 2)
    else:
        cv2.putText(frame, "Waiting for hand...",
                    (w//2 - 200, h//2), cv2.FONT_HERSHEY_SIMPLEX, 1.0,
                    (180, 180, 180), 2, cv2.LINE_AA)

def main():
    make_dirs()
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    total_gestures = len(GESTURES)

    for g_idx, gesture in enumerate(GESTURES):
        print(f"\n{'='*60}")
        print(f"  Gesture {g_idx+1}/{total_gestures}: {gesture}")
        print(f"  You will perform this {SEQUENCES} times.")
        print(f"  Press SPACE to begin, Q to quit.")
        print(f"{'='*60}")

        # Wait for SPACE to start this gesture
        while True:
            ok, frame = cap.read()
            if not ok: break
            frame = cv2.flip(frame, 1)
            h, w = frame.shape[:2]
            cv2.putText(frame,
                        f"NEXT GESTURE: {gesture}  ({g_idx+1}/{total_gestures})",
                        (40, h//2 - 60), cv2.FONT_HERSHEY_DUPLEX, 1.3,
                        (100, 255, 100), 3, cv2.LINE_AA)
            cv2.putText(frame, "Press SPACE to start recording",
                        (40, h//2), cv2.FONT_HERSHEY_SIMPLEX, 0.9,
                        (200, 200, 200), 2, cv2.LINE_AA)
            cv2.imshow("Data Collector — Emergency AI Interface", frame)
            key = cv2.waitKey(1) & 0xFF
            if key == ord(' '): break
            if key == ord('q'):
                cap.release(); cv2.destroyAllWindows(); return

        for seq in range(SEQUENCES):
            sequence_data = []

            # ── Countdown ────────────────────────────────────────────────────
            countdown_end = time.time() + COUNTDOWN_SEC
            while time.time() < countdown_end:
                ok, frame = cap.read()
                if not ok: break
                frame = cv2.flip(frame, 1)
                left = countdown_end - time.time()
                draw_overlay(frame, gesture, seq, False, 0, countdown_left=left)
                cv2.imshow("Data Collector — Emergency AI Interface", frame)
                cv2.waitKey(1)

            # ── Record 30 frames ─────────────────────────────────────────────
            frame_idx = 0
            while frame_idx < FRAMES_PER_SEQ:
                ok, frame = cap.read()
                if not ok: break
                frame = cv2.flip(frame, 1)
                h, w = frame.shape[:2]

                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                result = hands.process(rgb)

                if result.multi_hand_landmarks:
                    for handLms in result.multi_hand_landmarks:
                        mp_draw.draw_landmarks(frame, handLms, mp_hands.HAND_CONNECTIONS)
                        kp = extract_keypoints(handLms, w, h)
                        sequence_data.append(kp)
                        frame_idx += 1
                else:
                    # If no hand, append zeros so we don't freeze recording
                    sequence_data.append(np.zeros(63, dtype=np.float32))
                    frame_idx += 1

                draw_overlay(frame, gesture, seq, True, frame_idx)
                cv2.imshow("Data Collector — Emergency AI Interface", frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    cap.release(); cv2.destroyAllWindows(); return

            # Save sequence
            arr = np.array(sequence_data[:FRAMES_PER_SEQ])  # shape (30, 63)
            save_path = os.path.join(DATA_DIR, gesture, str(seq), "sequence.npy")
            np.save(save_path, arr)
            print(f"  ✓ Saved: {gesture}/seq_{seq} — shape {arr.shape}")

        print(f"\n✅ Done recording {gesture}!")

    cap.release()
    cv2.destroyAllWindows()
    print("\n" + "="*60)
    print("  ALL DATA COLLECTED! Now run:  python train_model.py")
    print("="*60)

    # Optional: prompt for typing session collection to support predictive-text training
    try:
        ans = input("\nCollect typing samples for predictive-text training now? (y/N): ").strip().lower()
    except Exception:
        ans = 'n'

    if ans == 'y':
        collect_typing_sessions()

if __name__ == "__main__":
    main()


def collect_typing_sessions():
    """Interactive helper to collect raw typed sentences for on-device language model training.

    Saves newline-delimited JSON records to `data/typing/sessions.jsonl` with fields:
      - text: the typed sentence
      - timestamp: unix epoch seconds
      - user: optional placeholder
    """
    os.makedirs(TYPING_DATA_DIR, exist_ok=True)
    out_path = os.path.join(TYPING_DATA_DIR, "sessions.jsonl")

    try:
        n = int(input(f"How many typing samples to record? (default {TYPING_SAMPLES}): ") or TYPING_SAMPLES)
    except Exception:
        n = TYPING_SAMPLES

    print("\nType each sentence and press Enter. Empty line will skip sample.")
    with open(out_path, "a", encoding="utf-8") as fh:
        for i in range(n):
            try:
                txt = input(f"[{i+1}/{n}] > ").strip()
            except Exception:
                txt = ""
            if not txt:
                print("  (skipped)")
                continue
            rec = {"text": txt, "timestamp": int(time.time()), "user": "local"}
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            print("  ✓ saved")

    print(f"\nSaved typing samples to: {out_path}")
