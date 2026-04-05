"""
push_fix.py - Push only the two changed files to trigger a new HF build.
"""
import os, sys
from dotenv import load_dotenv

load_dotenv()

HF_TOKEN = os.environ.get("HF_TOKEN")
if not HF_TOKEN:
    print("ERROR: HF_TOKEN not set in .env")
    sys.exit(1)

from huggingface_hub import HfApi

api = HfApi(token=HF_TOKEN)
me = api.whoami()
repo_id = f"{me['name']}/CareSync"
print(f"Pushing to: {repo_id}")

base = os.path.dirname(os.path.abspath(__file__))

files = [
    # (local path, path in repo)
    ("patient/static/patient/dashboard.css", "patient/static/patient/dashboard.css"),
    ("Dockerfile", "Dockerfile"),
]

for local_rel, repo_path in files:
    local_abs = os.path.join(base, local_rel)
    print(f"  Uploading {local_rel} ...", end=" ", flush=True)
    api.upload_file(
        path_or_fileobj=local_abs,
        path_in_repo=repo_path,
        repo_id=repo_id,
        repo_type="space",
        commit_message=f"fix: collectstatic errors - {local_rel}",
    )
    print("done")

print("\nDone! HF Spaces build triggered.")
print(f"Monitor: https://huggingface.co/spaces/{repo_id}/logs")
