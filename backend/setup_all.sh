#!/usr/bin/env bash
set -euo pipefail

# =========================
# CONFIG (edit these 3)
# =========================
PROJECT_ID="${PROJECT_ID:-ikause}"          # <-- change if needed
REGION="${REGION:-europe-west2}"            # <-- change if needed (e.g. us-central1)
SERVICE_NAME="${SERVICE_NAME:-ika-backend}"
SA_NAME="${SA_NAME:-ika-cloudrun-sa}"
BUCKET="${BUCKET:-}"                        # if empty, script will try to auto-detect

# =========================
# Helpers
# =========================
log() { echo -e "\n==> $*\n"; }

need_cmd() { command -v "$1" >/dev/null 2>&1 || { echo "Missing command: $1"; exit 1; }; }

need_cmd gcloud
need_cmd git

log "Using PROJECT_ID=$PROJECT_ID REGION=$REGION SERVICE_NAME=$SERVICE_NAME"
gcloud config set project "$PROJECT_ID" >/dev/null
gcloud config set run/region "$REGION" >/dev/null

# =========================
# STEP 1: Enable APIs
# =========================
log "Enabling required APIs..."
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  iam.googleapis.com \
  firestore.googleapis.com \
  secretmanager.googleapis.com \
  cloudresourcemanager.googleapis.com >/dev/null

# =========================
# STEP 2: Create Service Account (Cloud Run runtime identity)
# =========================
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

log "Ensuring service account exists: $SA_EMAIL"
if ! gcloud iam service-accounts describe "$SA_EMAIL" >/dev/null 2>&1; then
  gcloud iam service-accounts create "$SA_NAME" \
    --display-name="Ika Cloud Run Runtime SA" >/dev/null
else
  echo "Service account already exists."
fi

# =========================
# STEP 3: Grant IAM roles (Firestore + Storage + Signed URLs)
# =========================
log "Granting IAM roles to $SA_EMAIL (Firestore + Storage + Signed URLs)..."
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${SA_EMAIL}" --role="roles/datastore.user" >/dev/null || true

gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${SA_EMAIL}" --role="roles/storage.objectAdmin" >/dev/null || true

gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${SA_EMAIL}" --role="roles/iam.serviceAccountTokenCreator" >/dev/null || true

# Optional if you later store secrets in Secret Manager:
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${SA_EMAIL}" --role="roles/secretmanager.secretAccessor" >/dev/null || true

# =========================
# STEP 4: Detect Firebase Storage bucket if not provided
# =========================
log "Detecting Firebase Storage bucket..."
if [[ -z "${BUCKET}" ]]; then
  # Prefer main bucket if present
  if gsutil ls "gs://${PROJECT_ID}.appspot.com" >/dev/null 2>&1; then
    BUCKET="${PROJECT_ID}.appspot.com"
  else
    # fallback: pick first bucket listed
    BUCKET="$(gsutil ls 2>/dev/null | head -n 1 | sed 's#gs://##; s#/$##' || true)"
  fi
fi

if [[ -z "${BUCKET}" ]]; then
  echo "ERROR: Could not detect Storage bucket. Set BUCKET env var and rerun."
  echo "Example: export BUCKET='${PROJECT_ID}.appspot.com'"
  exit 1
fi

log "Using FIREBASE_STORAGE_BUCKET=$BUCKET"

# =========================
# STEP 5: Create backend folder + starter code
# =========================
log "Creating backend project structure in ./ika-backend ..."
mkdir -p ika-backend/app ika-backend/data ika-backend/scripts

# --- config.json (optional app config) ---
cat > ika-backend/config.json <<JSON
{
  "project_id": "${PROJECT_ID}",
  "region": "${REGION}",
  "audio_policy": "on_demand_only",
  "audio_cache_prefix": "audio-cache",
  "default_voice_id": "ika_default"
}
JSON

# --- requirements.txt ---
cat > ika-backend/requirements.txt <<'REQ'
fastapi==0.115.5
uvicorn[standard]==0.30.6
pydantic==2.8.2
python-multipart==0.0.9
firebase-admin==6.5.0
google-cloud-storage==2.18.2
REQ

# --- Dockerfile ---
cat > ika-backend/Dockerfile <<'DOCKER'
FROM python:3.10-slim

WORKDIR /app
COPY . .

RUN pip install --no-cache-dir -r requirements.txt

ENV PORT=8080
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
DOCKER

# --- firebase_client.py ---
cat > ika-backend/app/firebase_client.py <<'PY'
import os
import firebase_admin
from firebase_admin import credentials, firestore, storage

_firestore = None
_bucket = None

def init_firebase():
    global _firestore, _bucket
    if firebase_admin._apps:
        return
    project_id = os.environ.get("PROJECT_ID")
    bucket_name = os.environ.get("FIREBASE_STORAGE_BUCKET")

    # Uses Cloud Run service account (Application Default Credentials)
    firebase_admin.initialize_app(credentials.ApplicationDefault(), {
        "projectId": project_id,
        "storageBucket": bucket_name,
    })
    _firestore = firestore.client()
    _bucket = storage.bucket()

def db():
    if _firestore is None:
        init_firebase()
    return _firestore

def bucket():
    if _bucket is None:
        init_firebase()
    return _bucket
PY

# --- dictionary_engine.py ---
cat > ika-backend/app/dictionary_engine.py <<'PY'
import json
from pathlib import Path
from .firebase_client import db

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "ika_dictionary.json"

def load_local_dictionary():
    if DATA_PATH.exists():
        return json.loads(DATA_PATH.read_text(encoding="utf-8"))
    return {"entries": []}

def lookup_word(english: str):
    # Firestore first, fallback local JSON
    doc = db().collection("dictionary").document(english.lower()).get()
    if doc.exists:
        return doc.to_dict()
    local = load_local_dictionary()
    for e in local.get("entries", []):
        if str(e.get("english", "")).lower() == english.lower():
            return e
    return None
PY

# --- grammar_engine.py ---
cat > ika-backend/app/grammar_engine.py <<'PY'
import json
from pathlib import Path
from .firebase_client import db

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "ika_grammar_patterns.json"

def load_local_grammar():
    if DATA_PATH.exists():
        return json.loads(DATA_PATH.read_text(encoding="utf-8"))
    return {"patterns": []}

def get_patterns():
    # Firestore first, fallback local JSON
    docs = db().collection("grammar_patterns").stream()
    patterns = [d.to_dict() for d in docs]
    if patterns:
        return {"patterns": patterns}
    return load_local_grammar()
PY

# --- translator.py ---
cat > ika-backend/app/translator.py <<'PY'
import re
from .dictionary_engine import lookup_word

def translate_text(text: str) -> str:
    # MVP translator: word-by-word dictionary lookup, fallback to original token
    tokens = re.findall(r"[A-Za-z']+|[^A-Za-z']+", text)
    out = []
    for t in tokens:
        if re.match(r"[A-Za-z']+$", t):
            entry = lookup_word(t)
            out.append(entry.get("ika") if entry and entry.get("ika") else t)
        else:
            out.append(t)
    return "".join(out)
PY

# --- story_generator.py ---
cat > ika-backend/app/story_generator.py <<'PY'
from .translator import translate_text

def generate_story(prompt: str, length: str = "short") -> str:
    # MVP: simple template + translation
    base = f"Story: {prompt}. This is a {length} story in Ika."
    return translate_text(base)
PY

# --- main.py ---
cat > ika-backend/app/main.py <<'PY'
import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from .firebase_client import init_firebase
from .translator import translate_text
from .story_generator import generate_story

app = FastAPI(title="Ika Backend", version="0.1.0")

class TranslateIn(BaseModel):
    text: str
    mode: str | None = "dictionary"

class StoryIn(BaseModel):
    prompt: str
    length: str | None = "short"

@app.on_event("startup")
def startup():
    # Initialize Firebase using Cloud Run service account identity (ADC)
    init_firebase()

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/translate")
def translate(payload: TranslateIn):
    # HARD RULE: text only, NO audio generated here
    if not payload.text.strip():
        raise HTTPException(status_code=400, detail="text is required")
    ika = translate_text(payload.text)
    return {"text": ika, "meta": {"mode": payload.mode}}

@app.post("/generate-story")
def story(payload: StoryIn):
    # HARD RULE: text only, NO audio generated here
    if not payload.prompt.strip():
        raise HTTPException(status_code=400, detail="prompt is required")
    return {"text": generate_story(payload.prompt, payload.length or "short")}

@app.post("/generate-audio")
def generate_audio():
    # Placeholder endpoint for your next build step (TTS + caching).
    # HARD RULE: audio must be generated ONLY here.
    raise HTTPException(status_code=501, detail="generate-audio not implemented yet (add TTS + caching next)")
PY

# Add placeholder JSON files (you will replace these with YOUR real files)
cat > ika-backend/data/ika_dictionary.json <<'JSON'
{
  "version": "1.0",
  "entries": []
}
JSON

cat > ika-backend/data/ika_grammar_patterns.json <<'JSON'
{
  "patterns": []
}
JSON

# =========================
# STEP 6: Deploy to Cloud Run
# =========================
log "Deploying to Cloud Run (service: $SERVICE_NAME) ..."
cd ika-backend

gcloud run deploy "$SERVICE_NAME" \
  --source . \
  --region "$REGION" \
  --service-account "$SA_EMAIL" \
  --set-env-vars PROJECT_ID="$PROJECT_ID",FIREBASE_STORAGE_BUCKET="$BUCKET",AUDIO_POLICY=on_demand_only,AUDIO_CACHE_PREFIX=audio-cache \
  --no-allow-unauthenticated

log "Granting Cloud Run Invoker to allAuthenticatedUsers (recommended for Firebase-auth clients)..."
gcloud run services add-iam-policy-binding "$SERVICE_NAME" \
  --region "$REGION" \
  --member="allAuthenticatedUsers" \
  --role="roles/run.invoker" >/dev/null || true

log "DONE ✅"
echo "Service: $SERVICE_NAME"
echo "Region:  $REGION"
echo "Project: $PROJECT_ID"
echo "Bucket:  $BUCKET"
echo "SA:      $SA_EMAIL"
