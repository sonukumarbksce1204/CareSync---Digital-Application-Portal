import os
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CareSync.settings")
import django
django.setup()

from django.core.management import call_command

try:
    call_command("collectstatic", "--noinput", clear=True, verbosity=3)
    print("\n✅ Collectstatic completed successfully.")
except Exception as e:
    import traceback
    print("\n❌ Collectstatic failed:")
    traceback.print_exc()
