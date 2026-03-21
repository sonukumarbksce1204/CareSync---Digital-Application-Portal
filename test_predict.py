import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hospital_management.settings")
django.setup()

from patient.views import _load_ml
ml = _load_ml()

print("Symptoms length:", len(ml['symptom_list']))
if ml['symptom_list']:
    print("Symptoms sample:", ml['symptom_list'][:5])

if ml['predict_selected']:
    pred = ml['predict_selected'](['itching'], top_n=3)
    print("Predict itching:", pred)

    pred2 = ml['predict_selected']([], top_n=3)
    print("Predict empty:", pred2)
else:
    print("predict_selected is None (ML not loaded)")
