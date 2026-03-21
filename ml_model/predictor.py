"""
CareSync Disease Predictor Utility
==================================
FINAL FIXED VERSION (Django-safe)
- Module-level caching of model and indices
- Preserves EXACT symptom order
- Prevents shape mismatch
- Robust handling of symptom_index.pkl values
"""

import os
import numpy as np
import joblib
import warnings
from tensorflow.keras.models import load_model

# ── Paths ────────────────────────────────────────────────────────────────
HERE = os.path.dirname(os.path.abspath(__file__))

MODEL_PATH = os.path.join(HERE, "disease_model.keras")
SYMPTOM_PATH = os.path.join(HERE, "symptom_index.pkl")
ENCODER_PATH = os.path.join(HERE, "disease_encoder.pkl")

# ── Global State ─────────────────────────────────────────────────────────
_READY = False

_model = None
_symptom_index = {}
_symptom_list = []
_symptom_pos_map = {}
_disease_encoder = None
_norm_index = {}

# ── Helpers ──────────────────────────────────────────────────────────────
def _normalize_name(text):
    return str(text).strip().lower().replace(" ", "_")

def _extract_position(value, fallback_pos=None):
    """
    Convert whatever is stored in symptom_index.pkl into a usable integer position.
    Supports:
    - int
    - numpy int
    - dict with 'index'
    - list/tuple where first item is index
    """
    try:
        if isinstance(value, (int, np.integer)):
            return int(value)

        if isinstance(value, dict):
            if "index" in value:
                return int(value["index"])
            if "idx" in value:
                return int(value["idx"])

        if isinstance(value, (list, tuple)) and len(value) > 0:
            return int(value[0])

    except Exception:
        pass

    return fallback_pos

def _build_indexes():
    global _norm_index, _symptom_pos_map, _symptom_list

    _symptom_list = list(_symptom_index.keys())  # preserve original order
    _symptom_pos_map = {}

    for fallback_pos, key in enumerate(_symptom_list):
        raw_value = _symptom_index.get(key)
        pos = _extract_position(raw_value, fallback_pos=fallback_pos)
        _symptom_pos_map[key] = pos

    _norm_index = {
        _normalize_name(k): (k, _symptom_pos_map[k])
        for k in _symptom_list
    }

def _vector_from_selected(symptoms):
    vector = np.zeros(len(_symptom_list), dtype=np.float32)
    recognized = []

    for s in symptoms:
        key = str(s).strip()

        if key in _symptom_pos_map:
            idx = _symptom_pos_map[key]
            if 0 <= idx < len(vector):
                vector[idx] = 1
                recognized.append(key)
            continue

        nk = _normalize_name(key)
        if nk in _norm_index:
            real_key, idx = _norm_index[nk]
            if 0 <= idx < len(vector):
                vector[idx] = 1
                recognized.append(real_key)

    # remove duplicates while keeping order
    recognized = list(dict.fromkeys(recognized))
    return vector, recognized

def _vector_from_text(text):
    vector = np.zeros(len(_symptom_list), dtype=np.float32)
    recognized = []

    cleaned = str(text).replace(",", " ").replace(".", " ").replace(";", " ")
    tokens = cleaned.split()

    # token matching
    for t in tokens:
        nk = _normalize_name(t)
        if nk in _norm_index:
            real_key, idx = _norm_index[nk]
            if 0 <= idx < len(vector):
                vector[idx] = 1
                recognized.append(real_key)

    # full-phrase matching against known symptom names
    full_text = _normalize_name(text)
    for norm_name, (real_key, idx) in _norm_index.items():
        phrase = norm_name.replace("_", " ")
        if phrase in full_text.replace("_", " "):
            if 0 <= idx < len(vector):
                vector[idx] = 1
                recognized.append(real_key)

    recognized = list(dict.fromkeys(recognized))
    return vector, recognized

# ── Load symptom index ───────────────────────────────────────────────────
try:
    _symptom_index = joblib.load(SYMPTOM_PATH)

    if not isinstance(_symptom_index, dict):
        raise RuntimeError("symptom_index.pkl did not load as a dict")

    _build_indexes()
    print("[ML] ✅ Symptom index loaded")
    print(f"[ML] Total symptoms: {len(_symptom_list)}")
except Exception as e:
    warnings.warn(f"[ML] Symptom index load failed: {e}")

# ── Load model ───────────────────────────────────────────────────────────
try:
    _model = load_model(MODEL_PATH)
    _disease_encoder = joblib.load(ENCODER_PATH)

    if len(_symptom_list) == 0:
        raise RuntimeError("Symptom index is empty; cannot build input vector")

    test_vec = np.zeros((1, len(_symptom_list)), dtype=np.float32)
    _ = _model.predict(test_vec, verbose=0)

    _READY = True
    print("[ML] ✅ Disease model READY")
except Exception as e:
    warnings.warn(f"[ML] Model NOT available: {e}")
    _READY = False
    print(f"[ML] DEBUG: _READY stayed False because of: {e}")

# ── Public API ───────────────────────────────────────────────────────────
def is_ready():
    return _READY

def get_symptom_list():
    return list(_symptom_list)

def predict_from_selected(selected, top_n=3):
    if not _READY or not selected:
        return None

    vector, recognized = _vector_from_selected(selected)

    print("[ML] predict_from_selected input:", selected)
    print("[ML] recognized:", recognized)
    print("[ML] active features:", int(vector.sum()))

    if vector.sum() == 0:
        return None

    probs = _model.predict(vector.reshape(1, -1), verbose=0)[0]
    top_idx = probs.argsort()[-top_n:][::-1]

    return {
        "top": [
            {
                "disease": _disease_encoder.inverse_transform([int(i)])[0],
                "confidence": round(float(probs[i] * 100), 2),
            }
            for i in top_idx
        ],
        "recognized": recognized,
    }

def predict_from_text(text):
    if not _READY or not text:
        return None

    vector, recognized = _vector_from_text(text)

    print("[ML] predict_from_text input:", text)
    print("[ML] recognized:", recognized)
    print("[ML] active features:", int(vector.sum()))

    if vector.sum() == 0:
        return None

    probs = _model.predict(vector.reshape(1, -1), verbose=0)[0]
    idx = int(np.argmax(probs))

    return {
        "disease": _disease_encoder.inverse_transform([idx])[0],
        "confidence": round(float(probs[idx] * 100), 2),
        "recognized": recognized,
    }

def get_top_predictions(text, top_n=3):
    if not _READY:
        return None

    vector, recognized = _vector_from_text(text)

    if vector.sum() == 0:
        return None

    probs = _model.predict(vector.reshape(1, -1), verbose=0)[0]
    top_idx = probs.argsort()[-top_n:][::-1]

    return {
        "top": [
            {
                "disease": _disease_encoder.inverse_transform([int(i)])[0],
                "confidence": round(float(probs[i] * 100), 2),
            }
            for i in top_idx
        ],
        "recognized": recognized,
    }
