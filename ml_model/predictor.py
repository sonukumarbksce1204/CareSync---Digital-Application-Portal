"""
CareSync Disease Predictor Utility
===================================
Production-safe version with path diagnostics to help debug model-not-found
errors in Docker / Hugging Face without changing the core prediction logic.

Changes:
- compile=False on load_model() → safe for inference-only; avoids optimizer
  config errors when TF version differs between save-env and deploy-env.
- Full traceback logged via logging + traceback modules instead of
  warnings.warn (warnings can be suppressed in production; logging is not).
- Directory listing logged on failure to confirm files reached the container.
"""

import os
import logging
import traceback
import numpy as np
import joblib
from tensorflow.keras.models import load_model

logger = logging.getLogger(__name__)

# ── Paths ─────────────────────────────────────────────────────────────────────
HERE = os.path.dirname(os.path.abspath(__file__))

MODEL_PATH   = os.path.join(HERE, "disease_model.keras")
SYMPTOM_PATH = os.path.join(HERE, "symptom_index.pkl")
ENCODER_PATH = os.path.join(HERE, "disease_encoder.pkl")

# ── Startup diagnostics ───────────────────────────────────────────────────────
# Logged at INFO so they appear in gunicorn stdout even when DEBUG=False.
_model_exists   = os.path.exists(MODEL_PATH)
_symptom_exists = os.path.exists(SYMPTOM_PATH)
_encoder_exists = os.path.exists(ENCODER_PATH)

logging.basicConfig(level=logging.INFO)
logger.info("[ML] predictor module directory : %s", HERE)
logger.info("[ML] model path    : %s  — exists=%s", MODEL_PATH,   _model_exists)
logger.info("[ML] symptom path  : %s  — exists=%s", SYMPTOM_PATH, _symptom_exists)
logger.info("[ML] encoder path  : %s  — exists=%s", ENCODER_PATH, _encoder_exists)

try:
    _dir_contents = os.listdir(HERE)
except Exception:
    _dir_contents = ["<could not list directory>"]
logger.info("[ML] files in model dir : %s", _dir_contents)

# ── Global state ──────────────────────────────────────────────────────────────
_READY = False

_model          = None
_symptom_index  = {}
_symptom_list   = []
_symptom_pos_map = {}
_disease_encoder = None
_norm_index     = {}

# ── Helpers ───────────────────────────────────────────────────────────────────
def _normalize_name(text):
    return str(text).strip().lower().replace(" ", "_")

def _extract_position(value, fallback_pos=None):
    """
    Convert whatever is stored in symptom_index.pkl into a usable integer position.
    Supports: int, numpy int, dict with 'index'/'idx', list/tuple.
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

    _symptom_list    = list(_symptom_index.keys())   # preserve original order
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
    vector     = np.zeros(len(_symptom_list), dtype=np.float32)
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

    recognized = list(dict.fromkeys(recognized))
    return vector, recognized

def _vector_from_text(text):
    vector     = np.zeros(len(_symptom_list), dtype=np.float32)
    recognized = []

    cleaned = str(text).replace(",", " ").replace(".", " ").replace(";", " ")
    tokens  = cleaned.split()

    for t in tokens:
        nk = _normalize_name(t)
        if nk in _norm_index:
            real_key, idx = _norm_index[nk]
            if 0 <= idx < len(vector):
                vector[idx] = 1
                recognized.append(real_key)

    full_text = _normalize_name(text)
    for norm_name, (real_key, idx) in _norm_index.items():
        phrase = norm_name.replace("_", " ")
        if phrase in full_text.replace("_", " "):
            if 0 <= idx < len(vector):
                vector[idx] = 1
                recognized.append(real_key)

    recognized = list(dict.fromkeys(recognized))
    return vector, recognized


# ── Load symptom index ────────────────────────────────────────────────────────
try:
    if not os.path.exists(SYMPTOM_PATH):
        raise FileNotFoundError(f"Symptom index not found at: {SYMPTOM_PATH}")

    _symptom_index = joblib.load(SYMPTOM_PATH)

    if not isinstance(_symptom_index, dict):
        raise RuntimeError("symptom_index.pkl did not load as a dict")

    _build_indexes()
    logger.info("[ML] ✅ Symptom index loaded — %d symptoms", len(_symptom_list))

except Exception as e:
    logger.error("[ML] ❌ Symptom index load failed: %s", e)
    logger.error("%s", traceback.format_exc())


# ── Load model ────────────────────────────────────────────────────────────────
# compile=False: skips rebuilding the optimizer graph at load time.
# This is correct for inference-only usage and avoids failures when the TF
# version at load time differs from the version used to save the model
# (e.g. a newer tensorflow-cpu on Hugging Face vs. an older local version).
try:
    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(
            f"Model file not found at: {MODEL_PATH}\n"
            f"Files in model dir: {os.listdir(HERE)}"
        )
    if not os.path.exists(ENCODER_PATH):
        raise FileNotFoundError(
            f"Encoder file not found at: {ENCODER_PATH}\n"
            f"Files in model dir: {os.listdir(HERE)}"
        )

    logger.info("[ML] Loading Keras model (compile=False) …")
    _model = load_model(MODEL_PATH, compile=False)
    logger.info("[ML] Keras model loaded successfully")

    _disease_encoder = joblib.load(ENCODER_PATH)
    logger.info("[ML] Disease encoder loaded successfully")

    if len(_symptom_list) == 0:
        raise RuntimeError("Symptom index is empty — cannot build input vector")

    # Smoke-test: verify the model accepts our symptom-vector shape
    test_vec = np.zeros((1, len(_symptom_list)), dtype=np.float32)
    _ = _model.predict(test_vec, verbose=0)

    _READY = True
    logger.info("[ML] ✅ Disease model READY — %d symptom features", len(_symptom_list))

except Exception as e:
    _READY = False
    logger.error("[ML] ❌ Model load FAILED — _READY=False")
    logger.error("[ML] Exception: %s", e)
    logger.error("[ML] Full traceback:\n%s", traceback.format_exc())
    try:
        logger.error("[ML] Files in model dir: %s", os.listdir(HERE))
    except Exception:
        pass


# ── Public API ────────────────────────────────────────────────────────────────
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

    probs   = _model.predict(vector.reshape(1, -1), verbose=0)[0]
    top_idx = probs.argsort()[-top_n:][::-1]

    return {
        "top": [
            {
                "disease":    _disease_encoder.inverse_transform([int(i)])[0],
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
    idx   = int(np.argmax(probs))

    return {
        "disease":    _disease_encoder.inverse_transform([idx])[0],
        "confidence": round(float(probs[idx] * 100), 2),
        "recognized": recognized,
    }

def get_top_predictions(text, top_n=3):
    if not _READY:
        return None

    vector, recognized = _vector_from_text(text)

    if vector.sum() == 0:
        return None

    probs   = _model.predict(vector.reshape(1, -1), verbose=0)[0]
    top_idx = probs.argsort()[-top_n:][::-1]

    return {
        "top": [
            {
                "disease":    _disease_encoder.inverse_transform([int(i)])[0],
                "confidence": round(float(probs[i] * 100), 2),
            }
            for i in top_idx
        ],
        "recognized": recognized,
    }
