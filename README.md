---
title: CareSync
emoji: 🏥
colorFrom: blue
colorTo: indigo
sdk: docker
pinned: false
---

<div align="center">

# 🏥 CareSync — Digital Application Portal

**A full-stack, AI-powered healthcare management system built with Django.**

[![Live Demo](https://img.shields.io/badge/Live%20Demo-Hugging%20Face%20Spaces-blue?logo=huggingface)](https://huggingface.co/spaces/Sonukumar1204/CareSync)
[![Python](https://img.shields.io/badge/Python-3.10-blue?logo=python)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-4.2+-green?logo=django)](https://www.djangoproject.com/)
[![TensorFlow](https://img.shields.io/badge/TensorFlow-CPU-orange?logo=tensorflow)](https://www.tensorflow.org/)
[![Docker](https://img.shields.io/badge/Docker-Deployed-blue?logo=docker)](https://www.docker.com/)

</div>

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Live Demo](#live-demo)
3. [Key Features](#key-features)
4. [System Architecture](#system-architecture)
5. [Tech Stack](#tech-stack)
6. [Project Structure](#project-structure)
7. [User Roles](#user-roles)
8. [Feature Breakdown](#feature-breakdown)
9. [ML Disease Predictor](#ml-disease-predictor)
10. [Database Models](#database-models)
11. [Local Installation](#local-installation)
12. [Environment Variables](#environment-variables)
13. [Docker Deployment](#docker-deployment)
14. [Deploying to Hugging Face](#deploying-to-hugging-face)
15. [Production Configuration](#production-configuration)
16. [Author](#author)

---

## Overview

CareSync is a comprehensive, production-ready **Digital Health Portal** that connects patients, doctors, and hospitals on a single platform. It features:

- **Patient self-service** — symptom logging, AI disease prediction, appointment booking, and a full medical history timeline.
- **Doctor clinical workspace** — patient search, AI prediction review, consultation records, prescription management, and hospital affiliations.
- **Hospital management panel** — doctor affiliation approval, patient record access, appointment tracking.
- **Admin control panel** — doctor registration, verification, hospital onboarding, and system oversight.
- **Family Health Hub** — group patients into family units, share medical visibility between family members, and manage family-head changes.

---

## Live Demo

🌐 **[https://huggingface.co/spaces/Sonukumar1204/CareSync](https://huggingface.co/spaces/Sonukumar1204/CareSync)**

> The app is deployed on Hugging Face Spaces as a Docker container with a Neon PostgreSQL database and Cloudinary media storage.

---

## Key Features

| Area | Highlights |
|------|-----------|
| 🤖 **AI Prediction** | Keras neural network predicts diseases from 131 symptoms with confidence scores |
| 👨‍👩‍👧 **Family Hub** | Group patients into families; family head sees all members' records |
| 🩺 **Doctor Portal** | Search patients by ID, review AI predictions, add consultations and prescriptions |
| 🏥 **Hospital Panel** | Manage affiliations, approve doctors, access patient records securely |
| 📅 **Appointments** | Book, reschedule, approve, reject, and cancel with full history |
| 🛡️ **Admin Panel** | Register and verify doctors, onboard hospitals, manage the platform |
| 🔐 **Role-based Access** | Patients, doctors, hospitals, and admins each have strict, isolated permissions |
| ☁️ **Cloud Storage** | Media files stored on Cloudinary; static files on WhiteNoise |
| 🐳 **Docker + HF Deploy** | Fully containerized; deployed on Hugging Face Spaces |

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Hugging Face Spaces                         │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                    Docker Container                      │    │
│  │                                                          │    │
│  │   Gunicorn (1 worker, port 7860)                        │    │
│  │        │                                                  │    │
│  │   Django WSGI App                                        │    │
│  │        │                                                  │    │
│  │   ┌────┴────────────────────────────────────────────┐   │    │
│  │   │             Django Apps                          │   │    │
│  │   │  patient │ doctor │ hospital │ admin_panel       │   │    │
│  │   │                    ml_model                      │   │    │
│  │   └────┬────────────────────────────────────────────┘   │    │
│  │        │                                                  │    │
│  │   WhiteNoise (static files)                              │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                   │
│  External Services:                                               │
│  ┌──────────────────┐  ┌──────────────────┐                     │
│  │  Neon PostgreSQL  │  │   Cloudinary CDN │                     │
│  │  (production DB)  │  │   (media files)  │                     │
│  └──────────────────┘  └──────────────────┘                     │
└─────────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer | Technology |
|-------|----------|
| **Language** | Python 3.10 |
| **Web Framework** | Django 4.2+ |
| **Frontend** | HTML5, CSS3, JavaScript (vanilla) |
| **ML Framework** | TensorFlow / Keras (CPU) |
| **ML Encoder** | scikit-learn LabelEncoder |
| **Data Serialization** | joblib, NumPy |
| **Database (local)** | SQLite |
| **Database (production)** | Neon PostgreSQL (via `dj-database-url`) |
| **Static Files** | WhiteNoise with Brotli compression |
| **Media Storage** | Cloudinary (`django-cloudinary-storage`) |
| **WSGI Server** | Gunicorn |
| **Containerization** | Docker |
| **Deployment Platform** | Hugging Face Spaces |
| **Secrets Management** | `.env` (local), HF Space Secrets (production) |

---

## Project Structure

```
CareSync---Digital-Application-Portal/
│
├── CareSync/                    # Django project configuration
│   ├── settings.py              # Unified local + production settings
│   ├── urls.py                  # Root URL configuration
│   ├── wsgi.py                  # WSGI entry point
│   └── storage.py               # Custom storage backends
│
├── patient/                     # Patient app
│   ├── models.py                # Patient, Family, Symptom, Appointment, etc.
│   ├── views.py                 # Dashboard, predictor, appointments, family hub
│   ├── urls.py                  # Patient URL routes
│   ├── forms.py                 # Signup, symptom, appointment forms
│   ├── services/                # Business logic services
│   │   ├── family_service.py    # Family creation, head changes
│   │   └── access_service.py    # Permission checks
│   └── templates/patient/       # All patient-facing HTML templates
│
├── doctor/                      # Doctor app
│   ├── models.py                # Doctor, Qualification, Affiliation, Verification
│   ├── views.py                 # Dashboard, patient search, consultations, AI review
│   ├── urls.py                  # Doctor URL routes
│   ├── forms.py                 # Doctor signup, consultation, affiliation forms
│   └── templates/doctor/        # Doctor panel HTML templates
│
├── hospital/                    # Hospital app
│   ├── models.py                # Hospital, Department, HospitalImage
│   ├── views.py                 # Hospital dashboard, affiliation management
│   └── templates/hospital/      # Hospital panel HTML templates
│
├── admin_panel/                 # Admin app
│   ├── models.py                # AdminUser model
│   ├── views.py                 # Admin dashboard, doctor management, hospital onboarding
│   └── templates/admin_panel/   # Admin panel HTML templates
│
├── ml_model/                    # Machine Learning module
│   ├── predictor.py             # Disease predictor (TF/Keras + sklearn)
│   ├── disease_model.keras      # Trained Keras neural network (~873 KB)
│   ├── symptom_index.pkl        # Symptom name → vector index mapping
│   ├── disease_encoder.pkl      # sklearn LabelEncoder for disease names
│   └── deseaseprediction.ipynb  # Training notebook
│
├── templates/                   # Shared base templates
├── static/                      # Source static assets (CSS, JS, images)
├── staticfiles/                 # Collected static files (auto-generated)
│
├── Dockerfile                   # Production Docker image definition
├── requirements.txt             # Python dependencies
├── manage.py                    # Django management CLI
├── deploy_to_hf.py              # Hugging Face deployment helper script
└── .env.example                 # Environment variable template
```

---

## User Roles

CareSync has **four distinct user roles**, each with a separate login, dashboard, and permission scope:

### 1. 🧑‍⚕️ Patient
- Registers with username/password and personal health profile.
- Logs symptoms with optional image and test report uploads.
- Uses AI to predict likely diseases from a 131-symptom selector.
- Views their full medical history timeline (symptoms + consultations + diseases).
- Books, reschedules, and cancels appointments with doctors or hospitals.
- Creates or joins a **Family Group** to share health records.

### 2. 👨‍⚕️ Doctor
- Registers independently (no Django auth) and awaits admin verification.
- Searches for patients by **Patient ID** or **Family ID**.
- Reviews AI disease predictions — can **approve**, **modify**, or **reject** them.
- Adds **Consultation Records** with diagnosis, notes, prescription documents, and follow-up dates.
- Manages a personal **Disease Catalog** (including marking hereditary conditions).
- Requests affiliations with hospitals; manages multiple hospital attachments.

### 3. 🏨 Hospital
- Has a dedicated login (separate from patients/doctors).
- Approves or rejects incoming doctor affiliation requests.
- Accesses patient records via Patient/Family ID lookup.
- Views all appointments booked at the hospital.

### 4. 🔑 Admin
- Registers new doctors and hospitals on their behalf.
- Reviews and verifies doctor license documents.
- Manages the disease catalog and platform users.
- Has oversight of all appointments and records.

---

## Feature Breakdown

### Patient Dashboard
- **Symptom Log**: Add medical records with description, duration, improvement status, images, and test reports.
- **AI Prediction chip**: Select symptoms from a 131-item list; AI instantly predicts the top disease with confidence %.
- **Medical Timeline**: Chronological view of symptoms, consultations, and active diseases.
- **Consultation History**: Read-only view of doctor notes, diagnoses, instructions, and prescriptions.

### Family Health Hub
- A patient can **create** a new family group (generates a unique 6-digit Family ID).
- Other patients can **request to join** an existing family by entering the Family ID.
- The family **head** approves or rejects join requests and assigns relationships (spouse, son, daughter, etc.).
- The family head can **view full medical records** of all family members.
- **Head transfer**: The current head can transfer leadership to another member with an audit log.
- Family disease summary shows aggregate health status across all members.

### Appointment System
- Patients book appointments specifying **doctor**, **hospital**, **date**, **time**, and **visit mode** (in-person or online).
- Doctors/hospitals **approve**, **reject**, or **reschedule** appointments.
- Patients can **accept or reject** reschedule proposals.
- Duplicate appointment detection prevents double-booking.
- Full history: upcoming, past (completed), and cancelled appointments shown separately.

### Doctor Clinical Workspace
- **Patient Search**: Look up any patient by their 4-character Patient ID or the family's 6-digit Family ID.
- **AI Review Panel**: Pending symptom predictions are listed for review; doctor can approve, add notes, or override with a catalog diagnosis.
- **Add Consultation**: Attach a clinical note, select a diagnosis from the catalog, upload a prescription PDF, and set a follow-up date.
- **My Patients**: View all patients previously accessed or treated.
- **Hospital Affiliations**: Request, view, and manage all hospital affiliations.
- **Disease Catalog**: Add diseases (with ICD codes and hereditary flags) to the platform catalog.

### Hospital Management Panel
- View and respond to doctor affiliation requests.
- Look up patients (by ID) to view their records.
- Track all appointment requests targeted at the hospital.

### Admin Panel
- Register and verify doctors (upload license, set verification status).
- Onboard new hospitals.
- Full audit visibility over the platform.

---

## ML Disease Predictor

The AI prediction engine is built as a standalone Django app module (`ml_model/`).

### How it Works

1. **Input**: Patient selects symptoms from a dropdown list of **131 possible symptoms**.
2. **Vectorization**: The selected symptoms are converted to a binary feature vector (0/1 per symptom).
3. **Model**: A **Keras Dense Neural Network** (compiled with CPU-safe `compile=False`) processes the vector.
4. **Output**: Top-3 disease predictions with confidence percentages.
5. **Encoding**: The numeric model output is decoded to disease names using a **scikit-learn LabelEncoder**.

### Model Files

| File | Description | Size |
|------|-----------|------|
| `disease_model.keras` | Trained Keras model weights | ~873 KB |
| `symptom_index.pkl` | `{symptom_name: vector_index}` mapping | ~2.7 KB |
| `disease_encoder.pkl` | sklearn `LabelEncoder` for disease names | ~1.1 KB |

### Production Safety

- `load_model(path, compile=False)` — skips optimizer reconstruction; avoids TF version mismatch errors.
- `os.path.dirname(os.path.abspath(__file__))` — fully portable path resolution; no hardcoded or CWD-relative paths.
- All three model files verified at Docker **build time** (build fails early with a clear message if files are missing).
- Full exception traceback logged to gunicorn stdout via Python `logging` module (not suppressible `warnings.warn`).

---

## Database Models

### Patient App

| Model | Purpose |
|-------|---------|
| `Patient` | Core patient profile (ID, age, blood group, emergency contact) |
| `Family` | Family group with unique 6-digit ID and designated head |
| `Symptom` | Medical record entry with AI prediction and doctor review status |
| `ConsultationRecord` | Doctor-authored consultation with notes, diagnosis, prescription |
| `DiseaseCatalog` | Master list of diseases with ICD codes and hereditary flags |
| `PatientDisease` | Active/past diseases assigned to a patient |
| `Appointment` | Appointment between patient ↔ doctor/hospital with reschedule support |
| `FamilyJoinRequest` | Request to join a family group (pending/approved/rejected) |
| `FamilyHeadChangeLog` | Audit trail of family head transfers |
| `DoctorAccessLog` | Records every time a doctor accesses a patient's records |
| `AIReviewLog` | Audit log of every AI prediction review action by a doctor |

### Doctor App

| Model | Purpose |
|-------|---------|
| `Doctor` | Doctor profile with custom auth (not Django User) |
| `Specialization` | Medical specialization tags |
| `Qualification` | Degree, institution, year for each doctor |
| `HospitalAffiliation` | Doctor ↔ Hospital affiliation with approval workflow |
| `DoctorVerification` | License document and verification status |

### Hospital App

| Model | Purpose |
|-------|---------|
| `Hospital` | Hospital profile (type, beds, emergency services, contact) |
| `Department` | Hospital departments |
| `HospitalImage` | Gallery images for a hospital |

---

## Local Installation

### Prerequisites
- Python 3.10+
- pip
- (Optional) `virtualenv` or `venv`

### Steps

```bash
# 1. Clone the repository
git clone https://github.com/Sonukumar1204/CareSync---Digital-Application-Portal.git
cd CareSync---Digital-Application-Portal

# 2. Create and activate a virtual environment
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS / Linux:
source venv/bin/activate

# 3. Install all dependencies
pip install -r requirements.txt

# 4. Create your local environment file
copy .env.example .env      # Windows
# cp .env.example .env      # macOS/Linux
# Edit .env and fill in your values (see Environment Variables below)

# 5. Apply database migrations
python manage.py migrate

# 6. (Optional) Create a Django superuser for /admin access
python manage.py createsuperuser

# 7. Start the development server
python manage.py runserver
```

Open **http://127.0.0.1:8000** in your browser.

---

## Environment Variables

Copy `.env.example` to `.env` and fill in the values:

```env
# Required for Django
SECRET_KEY=your-very-secret-key-here
DEBUG=True                      # Set to False in production

# Database — leave empty to use SQLite locally
DATABASE_URL=                   # postgresql://user:pass@host/dbname

# Cloudinary — leave empty to use local filesystem for media
CLOUDINARY_URL=                 # cloudinary://api_key:api_secret@cloud_name

# Hugging Face deployment token (only needed when running deploy_to_hf.py)
HF_TOKEN=                       # hf_xxxxxxxxxxxxxxxxxxxx
```

| Variable | Local | Production |
|----------|-------|-----------|
| `SECRET_KEY` | Any random string | Set as HF Space Secret |
| `DEBUG` | `True` | `False` |
| `DATABASE_URL` | Empty (uses SQLite) | Neon PostgreSQL URL |
| `CLOUDINARY_URL` | Empty (uses local media/) | Set as HF Space Secret |

---

## Docker Deployment

The included `Dockerfile` creates a production-ready container:

```dockerfile
FROM python:3.10-slim

# System dependencies
RUN apt-get update && apt-get install -y libpq-dev gcc

WORKDIR /app

# Install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project (includes ml_model/ with .keras and .pkl files)
COPY --chown=user:user . /app

# Build-time check: fails loudly if model files are missing
RUN python - <<'EOF'
# Verifies disease_model.keras, symptom_index.pkl, disease_encoder.pkl
EOF

# Collect static files
RUN python manage.py collectstatic --noinput

# Non-root user (required by Hugging Face)
USER user
EXPOSE 7860

# Migrate then start Gunicorn (1 worker, 5-min timeout for TF loading)
CMD python manage.py migrate --noinput && \
    gunicorn CareSync.wsgi:application --bind 0.0.0.0:7860 --workers 1 --timeout 300
```

### Build & run locally

```bash
docker build -t caresync .
docker run -p 7860:7860 \
  -e SECRET_KEY=test-key \
  -e DEBUG=False \
  caresync
```

---

## Deploying to Hugging Face

Use the included `deploy_to_hf.py` helper to push the project to your HF Space:

```bash
# Set your token in .env
echo "HF_TOKEN=hf_xxxx" >> .env

# Deploy (uploads all files, sets Space secrets)
python deploy_to_hf.py
```

The script:
1. Creates the HF Space (Docker SDK) if it doesn't exist.
2. Sets `SECRET_KEY`, `DEBUG`, `DATABASE_URL`, and `CLOUDINARY_URL` as Space secrets.
3. Uploads the full project using `huggingface_hub.upload_folder()`, including all ML model files.
4. HF automatically triggers a Docker build and redeploys.

---

## Production Configuration

### Static Files
- Served by **WhiteNoise** with `CompressedManifestStaticFilesStorage`.
- Content-hashed filenames enable long-lived browser caching.
- `collectstatic` runs at Docker build time — no runtime disk writes needed.

### Media Files
- Served by **Cloudinary** when `CLOUDINARY_URL` is set.
- Falls back to local filesystem storage when `CLOUDINARY_URL` is empty (local dev).

### Database
- Automatically uses **Neon PostgreSQL** in production (when `DATABASE_URL` env var is set and `SPACE_ID` is detected).
- Falls back to **SQLite** for local development with zero configuration.

### Security (Production Only)
- `SECURE_PROXY_SSL_HEADER` enabled for HTTPS detection behind the Hugging Face reverse proxy.
- `SESSION_COOKIE_SECURE` and `CSRF_COOKIE_SECURE` set to `True`.
- `CSRF_TRUSTED_ORIGINS` covers `*.hf.space`.

---

## Author

**Sonu Kumar**  
Student Developer passionate about building healthcare solutions with AI and Django.

- 🌐 Live: [https://huggingface.co/spaces/Sonukumar1204/CareSync](https://huggingface.co/spaces/Sonukumar1204/CareSync)

If this project helped you, please consider giving it a ⭐ on GitHub!

---

<div align="center">
  <sub>Built with ❤️ using Django · TensorFlow · PostgreSQL · Docker · Hugging Face Spaces</sub>
</div>
