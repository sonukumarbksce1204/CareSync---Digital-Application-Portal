import sys, os, traceback

out = []
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CareSync.settings")

try:
    import django; django.setup()
    out.append("Django: OK")
except Exception as e:
    out.append(f"Django: FAIL - {e}")

try:
    import tensorflow as tf
    out.append(f"TensorFlow: {tf.__version__}")
except Exception as e:
    out.append(f"TensorFlow: MISSING - {e}")

try:
    from ml_model.predictor import _READY, _symptom_index, get_symptom_list, predict_from_selected
    out.append(f"predictor _READY: {_READY}")
    out.append(f"_symptom_index size: {len(_symptom_index)}")
    syms = get_symptom_list()
    out.append(f"get_symptom_list: {len(syms)} symptoms")
    if syms:
        out.append(f"first 5: {syms[:5]}")

    if _READY and len(syms) >= 3:
        test = syms[:3]
        out.append(f"\nTesting predict_from_selected({test}):")
        result = predict_from_selected(test, top_n=3)
        out.append(f"Result: {result}")
    elif not _READY:
        out.append("predictor not ready - model load failed")
except Exception as e:
    out.append(f"predictor import FAILED: {e}")
    out.append(traceback.format_exc())

text = "\n".join(out)
with open("diag_output.txt", "w", encoding="utf-8") as f:
    f.write(text)
print(text)
