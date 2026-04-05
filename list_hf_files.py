import os
from huggingface_hub import HfApi
from dotenv import load_dotenv

load_dotenv()
token = os.environ.get("HF_TOKEN")
api = HfApi(token=token)

repo_id = "Sonukumar1204/CareSync"
files = api.list_repo_files(repo_id=repo_id, repo_type="space")

static_files = [f for f in files if "static" in f]
print("All static-related files in repo:")
for sf in static_files:
    print(sf)
print(f"Total files in repo: {len(files)}")
