"""
train_model.py — Emergency AI Communication Interface
======================================================
Loads the collected numpy sequences, builds a stacked Bidirectional LSTM,
trains it, prints accuracy + confusion matrix, and saves model.keras.

Run this AFTER collect_data.py has finished.
"""

import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import os
import numpy as np
import matplotlib
matplotlib.use("Agg")   # headless backend — no display needed
import matplotlib.pyplot as plt

from sklearn.model_selection import train_test_split
from sklearn.metrics import confusion_matrix, classification_report
import seaborn          # optional pretty confusion matrix; falls back gracefully

# TensorFlow / Keras
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import (LSTM, Dense, Dropout,
                                     Bidirectional, BatchNormalization)
from tensorflow.keras.callbacks import (EarlyStopping, ReduceLROnPlateau,
                                        ModelCheckpoint)
from tensorflow.keras.utils import to_categorical

# ─── Config (must match collect_data.py) ─────────────────────────────────────
GESTURES       = ["HELP", "EMERGENCY", "PAIN", "WATER", "FOOD", "TOILET", "YES", "NO"]
SEQUENCES      = 30
FRAMES_PER_SEQ = 30
FEATURES       = 63    # 21 landmarks × (x, y, z)
DATA_DIR       = "data"
MODEL_OUT      = "model.keras"
LABELS_OUT     = "labels.npy"

print(f"\n{'='*60}")
print("  Emergency AI Communication Interface — LSTM Trainer")
print(f"{'='*60}\n")

# ─── 1. Load data ─────────────────────────────────────────────────────────────
print("Loading training data...")
X, y = [], []

for label_idx, gesture in enumerate(GESTURES):
    loaded = 0
    for seq in range(SEQUENCES):
        path = os.path.join(DATA_DIR, gesture, str(seq), "sequence.npy")
        if os.path.exists(path):
            arr = np.load(path)               # shape (30, 63)
            if arr.shape == (FRAMES_PER_SEQ, FEATURES):
                X.append(arr)
                y.append(label_idx)
                loaded += 1
    print(f"  {gesture:<12} — {loaded} sequences loaded")

X = np.array(X, dtype=np.float32)            # (N, 30, 63)
y = np.array(y, dtype=np.int32)

if len(X) == 0:
    print("\n❌ No data found. Run collect_data.py first.")
    exit(1)

print(f"\nDataset: {X.shape[0]} total sequences  •  shape per sample: {X.shape[1:]}")

# ─── 2. One-hot encode & split ────────────────────────────────────────────────
n_classes = len(GESTURES)
Y         = to_categorical(y, num_classes=n_classes)

X_train, X_test, Y_train, Y_test = train_test_split(
    X, Y, test_size=0.15, random_state=42, stratify=y
)
print(f"Train: {len(X_train)}   Test: {len(X_test)}\n")

# ─── 3. Build Stacked Bidirectional LSTM ─────────────────────────────────────
model = Sequential([
    # First BiLSTM — returns sequences so the next layer sees time steps
    Bidirectional(LSTM(64, return_sequences=True, activation='tanh'),
                  input_shape=(FRAMES_PER_SEQ, FEATURES)),
    BatchNormalization(),
    Dropout(0.3),

    # Second BiLSTM — returns sequences
    Bidirectional(LSTM(128, return_sequences=True, activation='tanh')),
    BatchNormalization(),
    Dropout(0.3),

    # Third LSTM — returns single vector
    LSTM(64, return_sequences=False, activation='tanh'),
    BatchNormalization(),
    Dropout(0.2),

    # Classification head
    Dense(64, activation='relu'),
    Dropout(0.2),
    Dense(n_classes, activation='softmax')
], name="EmergencyASL_BiLSTM")

model.summary()

model.compile(
    optimizer=tf.keras.optimizers.Adam(learning_rate=1e-3),
    loss='categorical_crossentropy',
    metrics=['accuracy']
)

# ─── 4. Callbacks ────────────────────────────────────────────────────────────
callbacks = [
    EarlyStopping(monitor='val_loss', patience=15, restore_best_weights=True),
    ReduceLROnPlateau(monitor='val_loss', factor=0.5, patience=7, min_lr=1e-6),
    ModelCheckpoint(MODEL_OUT, save_best_only=True, monitor='val_accuracy',
                    verbose=1)
]

# ─── 5. Train ────────────────────────────────────────────────────────────────
print("\nTraining Bidirectional LSTM...\n")
history = model.fit(
    X_train, Y_train,
    validation_data=(X_test, Y_test),
    epochs=60,
    batch_size=16,
    callbacks=callbacks,
    verbose=1
)

# ─── 6. Evaluate ─────────────────────────────────────────────────────────────
print("\n" + "="*60)
loss, acc = model.evaluate(X_test, Y_test, verbose=0)
print(f"  Test Accuracy : {acc*100:.2f}%")
print(f"  Test Loss     : {loss:.4f}")
print("="*60)

# ─── 7. Confusion matrix ─────────────────────────────────────────────────────
y_pred  = np.argmax(model.predict(X_test, verbose=0), axis=1)
y_true  = np.argmax(Y_test, axis=1)
cm      = confusion_matrix(y_true, y_pred)

print("\nClassification Report:")
print(classification_report(y_true, y_pred, target_names=GESTURES))

try:
    import seaborn as sns
    fig, ax = plt.subplots(figsize=(9, 7))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
                xticklabels=GESTURES, yticklabels=GESTURES, ax=ax)
    ax.set_title("Confusion Matrix — Emergency ASL BiLSTM", fontsize=14, pad=12)
    ax.set_ylabel("True Label")
    ax.set_xlabel("Predicted Label")
    plt.tight_layout()
    plt.savefig("confusion_matrix.png", dpi=150)
    print("\n📊 Confusion matrix saved to confusion_matrix.png")
except Exception:
    pass   # seaborn optional

# ─── 8. Save label map ────────────────────────────────────────────────────────
np.save(LABELS_OUT, np.array(GESTURES))

# ─── 9. Plot training history ─────────────────────────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(12, 4))
axes[0].plot(history.history['accuracy'],     label='Train Acc')
axes[0].plot(history.history['val_accuracy'], label='Val Acc')
axes[0].set_title('Accuracy')
axes[0].legend(); axes[0].grid(True)

axes[1].plot(history.history['loss'],     label='Train Loss')
axes[1].plot(history.history['val_loss'], label='Val Loss')
axes[1].set_title('Loss')
axes[1].legend(); axes[1].grid(True)

plt.suptitle('Emergency ASL BiLSTM — Training History', fontsize=13)
plt.tight_layout()
plt.savefig("training_history.png", dpi=150)
print("📈 Training history saved to training_history.png")

print(f"\n✅ Model saved to {MODEL_OUT}")
print("   Now run:  python index.py   and switch to ASSIST mode.\n")
