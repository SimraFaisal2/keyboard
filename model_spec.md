On-Device Predictive-Text Model Spec
===================================

Goal
----
Provide a small, fast on-device next-word / suggestion model that produces 3 ranked suggestions given the typed context. Priorities: low latency (<< 100ms on CPU), small size (< 10–20MB), acceptable accuracy for keystroke savings.

Design choices (high level)
---------------------------
- Tokenization: character-level + wordpiece fallback. Default pipeline: simple whitespace tokenization + char-level fallback so model gracefully handles out-of-vocab.
- Model family: two-phase plan
  - Baseline: n-gram model (KenLM) for immediate low-effort iteration and tiny memory footprint.
  - Primary: tiny Transformer language model (distilled) with quantized weights for best accuracy/size tradeoff.
- Context window: last 8 words (or whole current word + previous 7 words). Use last-word prefix for completion suggestions.
- Output: top-K token suggestions (K=3) with scores/probabilities.

Model architecture (tiny transformer prototype)
----------------------------------------------
- Input embedding dim: 128
- Layers: 2 transformer encoder layers (causal LM style) or decoder-only blocks
- Attention heads: 4
- Feed-forward dim: 512
- Vocabulary: 20k most common wordpieces, plus special tokens (PAD, UNK, BOS, EOS)
- Sequence length: 32 tokens max

Training
--------
- Data: Use `data/typing/sessions.jsonl` + optional synthetic corpora (OpenSubtitles, TinyStories) if user opts in.
- Preprocessing:
  - Normalize unicode to NFKC, lowercase (option), collapse whitespace, strip punctuation per policy.
  - Tokenize to wordpieces using SentencePiece or simple whitespace + char fallback.
  - Create input-target pairs using sliding window over tokens for next-token prediction.
- Batch size: 32; LR schedule: warmup + cosine decay; epochs: 10 (tune to validation loss)
- Checkpoints: save best by validation perplexity/top-k accuracy.

Evaluation
----------
- Metrics: top-1/top-3 accuracy on held-out set, perplexity.
- Latency: measure CPU (single-thread) 95th percentile inference time on target device.
- Keystroke savings: simulate typing and compute reduction in keystrokes using top-1/top-3 acceptance heuristic.

Export & Inference
------------------
- Export formats: ONNX (preferred) and PyTorch .pt. Also keep a small n-gram fallback (KenLM binary).
- Quantization: int8 post-training quantization for ONNX or PyTorch quantization. Aim for ~4–8× size reduction.
- Inference API (summary):
  - `load_model(path)` — loads quantized model and tokenizer.
  - `predict_next(context: str, k=3) -> List[(token, score)]` — returns top-k suggestions quickly.
  - `update_cache(context)` — optional incremental cache for repeated calls.
- Threading: run inference on a background thread or process to avoid blocking the main UI and meet latency targets.

Integration with existing app
-----------------------------
- Storage:
  - Model: `models/predictor.onnx`
  - Tokenizer/vocab: `models/tokenizer.*`
- Runtime hooks:
  - Add a lightweight predictor module `predictor.py` with `Predictor` class exposing `predict(context)` and async queue.
  - Call `keyboard.update_predictions(typed_text)` already used in `main.py` and swap in results to update `PRED_*` key labels.
  - Display top-3 as dynamic `PRED_0`, `PRED_1`, `PRED_2` keys in HUD.

Fallback & Privacy
------------------
- On-device only by default. If the user opts into cloud-backed improvements, require explicit consent and document the flow.
- Allow user to clear personalized data (i.e. remove `data/typing/*`) and disable personalization.

Optimizations
-------------
- Use caching keyed by last N tokens to reuse predictions across keystrokes.
- Quantize & prune model; use ONNX Runtime with CPU optimizations.
- Use batched prefix completion when user holds down suggestions to compute multiple candidates.

Files to add/modify
-------------------
- `model_spec.md` (this file)
- `collect_data.py` — append typing session helper (already updated)
- `train_model.py` — training script: preprocess, train, export quantized model
- `predictor.py` — inference wrapper (ONNX/PyTorch + tokenizer)
- Update `main.py` (or `index.py`) to call predictor and render suggestions in HUD

Next steps (minimal first PR)
----------------------------
1. Implement `predictor.py` with a simple n-gram (KenLM) wrapper as a fast baseline.
2. Extend `train_model.py` to ingest `data/typing/sessions.jsonl` and train a tiny transformer; export to ONNX.
3. Wire `predictor.py` into the app and render suggestions in the HUD.

Notes
-----
- This spec focuses on a pragmatic on-device solution balancing accuracy, size, and latency.
- If you want a purely char-level model (works better for air-writing & noisy input), adjust tokenizer and increase sequence length accordingly.


Contact
-------
If you want, I can now:
- Draft `predictor.py` baseline (KenLM wrapper) and update `train_model.py` preprocessing.
- Or implement the tiny transformer training pipeline in `train_model.py` and export steps.

