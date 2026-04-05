# ── Base image ────────────────────────────────────────────────────────────────
FROM python:3.10-slim

# ── System dependencies for Postgres and image processing ────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# ── Working directory ─────────────────────────────────────────────────────────
WORKDIR /app

# ── Non-root user required by Hugging Face ────────────────────────────────────
RUN useradd -m -u 1000 user

# ── Install Python dependencies ───────────────────────────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Copy project files (including ml_model/, templates/, static/, etc.) ───────
COPY --chown=user:user . /app

# ── Verify ML model files were included in the image ────────────────────────
# This step intentionally FAILS the build if any model file is missing,
# giving a clear error message instead of a silent runtime prediction failure.
RUN python - <<'EOF'
import os, sys
files = {
    "ml_model/disease_model.keras":  "/app/ml_model/disease_model.keras",
    "ml_model/symptom_index.pkl":    "/app/ml_model/symptom_index.pkl",
    "ml_model/disease_encoder.pkl":  "/app/ml_model/disease_encoder.pkl",
}
missing = [name for name, path in files.items() if not os.path.exists(path)]
if missing:
    print("ERROR: The following ML model files are MISSING from the Docker image:")
    for f in missing:
        print(f"  ✗  {f}")
    print("\nFix: make sure these files are committed to git (not in .gitignore)")
    print("     and that deploy_to_hf.py is not excluding them.")
    sys.exit(1)
for name, path in files.items():
    size = os.path.getsize(path)
    print(f"  ✓  {name}  ({size:,} bytes)")
print("ML model files verified OK.")
EOF

# ── Collect static files at BUILD time ───────────────────────────────────────
# We inject a dummy SECRET_KEY so Django can load settings without a real key.
# DATABASE_URL and CLOUDINARY_URL are intentionally absent here — collectstatic
# does not need a database connection or Cloudinary (static files are served by
# WhiteNoise, NOT Cloudinary). The dummy CLOUDINARY_URL below allows the
# cloudinary package to import without raising a missing config error.
RUN SECRET_KEY=dummy-build-key-not-real \
    CLOUDINARY_URL="" \
    SPACE_ID=dummy-build \
    python manage.py collectstatic --noinput

# ── Fix ownership after collectstatic writes staticfiles/ ────────────────────
RUN chown -R user:user /app

# ── Switch to non-root user ───────────────────────────────────────────────────
USER user
ENV PATH="/home/user/.local/bin:$PATH"

# ── Expose Hugging Face required port ────────────────────────────────────────
EXPOSE 7860

# ── Startup: run migrations then start gunicorn ───────────────────────────────
#
# Gunicorn notes:
#  --workers 1   : Only one worker. TensorFlow/Keras model loading is
#                  memory-intensive. Using 2+ workers on HF free tier can
#                  cause OOM kills. One worker is stable and sufficient.
#  --timeout 300 : Allow 5 min for the first request so TF model can load
#                  on cold start without gunicorn killing the worker.
#  NO --preload  : TensorFlow has known issues sharing GPU/CPU session state
#                  across forked worker processes. Lazy loading (default) is
#                  safer. The model loads on first request and stays cached.
#
CMD python manage.py migrate --noinput && \
    gunicorn CareSync.wsgi:application \
        --bind 0.0.0.0:7860 \
        --workers 1 \
        --timeout 300
