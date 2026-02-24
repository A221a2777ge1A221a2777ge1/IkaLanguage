# IKA Language Engine Backend

FastAPI backend for the IKA language translation and generation engine, deployed on Google Cloud Run.

**Option A: Rule-based generator** using Firestore lexicon + grammar patterns.

## Overview

This backend provides:
- **Translation**: English to Ika using rule-based generation with Firestore lexicon
- **Generation**: Poem/story/lecture generation using templates and patterns
- **Audio**: On-demand audio generation (only when `/generate-audio` is called)
- **Grammar**: Ika grammar patterns loaded from `data/ika_grammar_patterns.json`

## Architecture

- **Primary Dictionary**: Firestore collection `lexicon` (659+ documents)
- **Grammar Patterns**: `data/ika_grammar_patterns.json` (source of truth)
- **Grammar Rules**: `data/grammar_rules.json` (tense, negation, questions)
- **Pronouns**: `data/pronouns.json` (subject/object/possessive)
- **Connectors**: `data/connectors.json` (and, but, because, etc.)
- **Templates**: `data/templates.json` (poem/story/lecture structures)
- **Audio Strategy**: On-demand only - cached in Firebase Storage

## Environment Variables

Set these in Cloud Run or via `.env`:

```bash
PROJECT_ID=ikause
LEXICON_COLLECTION=lexicon
FIREBASE_STORAGE_BUCKET=ikause.appspot.com
AUDIO_CACHE_PREFIX=audio-cache
PORT=8080
```

## Local Development

1. **Install dependencies**:
   ```bash
   cd backend/ika-backend
   pip install -r requirements.txt
   ```

2. **Set up Application Default Credentials**:
   ```bash
   gcloud auth application-default login
   ```

3. **Set environment variables** (or use `.env` file):
   ```bash
   export PROJECT_ID=ikause
   export LEXICON_COLLECTION=lexicon
   export FIREBASE_STORAGE_BUCKET=ikause.appspot.com
   export AUDIO_CACHE_PREFIX=audio-cache
   ```

4. **Run the server**:
   ```bash
   uvicorn app.main:app --reload --port 8080
   ```

## Validation

### Run Validator Script

Before deploying, validate grammar patterns:

```bash
python3 backend/tools/validate_ika_examples.py
```

This script checks:
- No `example_language` fields in patterns
- No banned tokens in examples: `akwukwo`, `anyi`, `umunna`, `ga eje`, `ya mere`, `mgbe`

The validator is also run automatically on startup - the service will refuse to start if validation fails.

## Deployment to Cloud Run

### Prerequisites

- GCP project `ikause` set up
- Service account `ika-cloudrun-sa@ikause.iam.gserviceaccount.com` with required roles
- Firestore database with `lexicon` collection populated
- APIs enabled (run `backend/scripts/setup_gcp.sh`)

### TTS permissions

The `/generate-audio` endpoint uses **Google Cloud Text-to-Speech** with IPA phonemes (SSML).

- **Enable the API**: In GCP Console, enable **Cloud Text-to-Speech API** for your project.
- **Service account permissions**: The Cloud Run service account (`ika-cloudrun-sa@ikause.iam.gserviceaccount.com`) must be allowed to call Text-to-Speech. Options:
  - **Testing**: Grant `roles/editor` (or project Editor) to the service account so it can call the API.
  - **Production**: Grant the narrow role **Cloud Text-to-Speech API User** (or a custom role with `cloudtts.synthesize`) to the service account.
- After changing roles, redeploy or wait for the next request; no restart needed.

### Deploy

```bash
cd backend/ika-backend
gcloud run deploy ika-backend \
  --source . \
  --region europe-west2 \
  --service-account ika-cloudrun-sa@ikause.iam.gserviceaccount.com \
  --set-env-vars PROJECT_ID=ikause,LEXICON_COLLECTION=lexicon,FIREBASE_STORAGE_BUCKET=ikause.appspot.com,AUDIO_CACHE_PREFIX=audio-cache \
  --allow-unauthenticated=false
```

Note: `--allow-unauthenticated=false` keeps the service private (requires authentication).

## API Endpoints

### 1. Health Check

```bash
GET /health
```

Response:
```json
{"ok": true}
```

### 2. Translate

```bash
POST /translate
Content-Type: application/json

{
  "text": "hello world",
  "tense": "present",
  "mode": "rule_based"
}
```

Response:
```json
{
  "text": "ika translation",
  "meta": {
    "pattern_ids": [],
    "lexicon_entries": [
      {
        "doc_id": "1",
        "source": "hello",
        "target": "ya"
      }
    ],
    "tense": "present",
    "mode": "rule_based"
  }
}
```

**Note**: Returns text only. **NO audio generation**.

### 3. Generate

```bash
POST /generate
Content-Type: application/json

{
  "kind": "poem",
  "topic": "nature",
  "tone": "poetic",
  "length": "medium"
}
```

Response:
```json
{
  "text": "generated ika text",
  "meta": {
    "kind": "poem",
    "topic": "nature",
    "tone": "poetic",
    "length": "medium",
    "pattern_ids": ["simple_sentence", "verb_phrase"],
    "lexicon_entries": [...]
  }
}
```

**Note**: Returns text only. **NO audio generation**.

### 4. Generate Audio

```bash
POST /generate-audio
Content-Type: application/json

{
  "text": "ika text",
  "voice": "default",
  "speaking_rate": 1.0,
  "pitch": 0.0
}
```

- **text**: Ika text to synthesize (optional if `prompt` is set).
- **prompt**: If set and `text` is omitted, the backend generates Ika text from the prompt (e.g. story), then synthesizes that.
- **voice**, **speaking_rate**, **pitch**: Optional TTS parameters (cache key includes them).

**Response**: Raw MP3 bytes (`Content-Type: audio/mpeg`), with header `Content-Disposition: attachment; filename="ika.mp3"`.

**Example — save MP3 to file:**

```bash
curl -o out.mp3 -X POST "https://ika-backend-516421484935.europe-west2.run.app/generate-audio" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"text": "hello water", "voice": "default"}'
```

**Note**: Uses Google Cloud Text-to-Speech with IPA SSML. IAM: see **docs/tts_iam.md** if you get permission errors.

## Testing in Cloud Shell

### Get Authentication Token

```bash
TOKEN="$(gcloud auth print-identity-token)"
```

### Test Health Endpoint

```bash
curl -X GET "https://ika-backend-<hash>-ew.a.run.app/health" \
  -H "Authorization: Bearer $TOKEN"
```

### Test Translate Endpoint

```bash
curl -X POST "https://ika-backend-<hash>-ew.a.run.app/translate" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "hello world",
    "tense": "present",
    "mode": "rule_based"
  }'
```

### Test Generate Endpoint

```bash
curl -X POST "https://ika-backend-<hash>-ew.a.run.app/generate" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "kind": "poem",
    "topic": "nature",
    "tone": "poetic",
    "length": "medium"
  }'
```

### Test Generate Audio Endpoint

Saves MP3 to `out.mp3` and prints file size:

```bash
curl -X POST "https://ika-backend-<hash>-ew.a.run.app/generate-audio" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"text": "hello water", "voice": "default"}' \
  -o out.mp3
ls -la out.mp3
```

## Firestore Schema

### Lexicon Collection

Document ID: numeric string (e.g., "1")

```json
{
  "id": 1,
  "source_text": "hello",
  "target_text": "ya",
  "audio_url": "https://firebasestorage.googleapis.com/.../audio%2F1.m4a?...",
  "domain": "greeting",
  "source_lang": "en",
  "target_lang": "ika_ng",
  "status": "done",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

Optional fields:
- `pos`: Part of speech (noun, verb, adjective, etc.)
- `source_text_lc`: Lowercase version of source_text (for efficient queries)
- `target_text_lc`: Lowercase version of target_text (for efficient queries)

## Data Files

### `data/ika_grammar_patterns.json`

Grammar patterns structure. **IMPORTANT**:
- Must NOT contain `example_language` field
- Examples must NOT contain banned tokens
- Examples are display-only and never used in generation

### `data/grammar_rules.json`

Tense markers, negation rules, question formation.

### `data/pronouns.json`

Subject, object, and possessive pronouns mapping.

### `data/connectors.json`

Connector words (and, but, because, etc.).

### `data/templates.json`

Templates for poem/story/lecture generation. Must reference valid `pattern_id` values.

## Audio Generation

**IMPORTANT**: Audio is **on-demand only**. It is generated:
- **ONLY** when `/generate-audio` endpoint is called
- **NEVER** automatically in `/translate` or `/generate`

Audio caching:
1. Hash text with SHA256
2. Check Firebase Storage cache: `gs://<bucket>/<AUDIO_CACHE_PREFIX>/<hash>.wav`
3. If exists, return signed URL
4. Else generate TTS (CPU-based), upload, return signed URL

## TTS Implementation

The TTS engine (`app/tts_engine.py`) is currently stubbed. To implement:

1. Choose a CPU-based TTS solution:
   - Coqui TTS (CPU)
   - Piper TTS (CPU)
   - Custom TTS model
2. Update `generate_tts_audio()` function
3. Ensure output is WAV format (bytes)

## Security

- Cloud Run service is **private** (requires authentication)
- Uses Application Default Credentials (no key files)
- Service account has minimal required permissions

## Project Structure

```
backend/ika-backend/
├── app/
│   ├── main.py              # FastAPI application
│   ├── firebase_client.py   # Firebase Admin SDK initialization
│   ├── lexicon_repo.py      # Firestore lexicon queries
│   ├── pattern_repo.py      # Grammar pattern loading
│   ├── rule_engine.py       # Grammar rules (tense/negation/questions)
│   ├── slot_filler.py       # Pattern slot filling
│   ├── generator.py         # Main generation engine
│   ├── templates_engine.py  # Poem/story/lecture templates
│   ├── tts_engine.py        # TTS generation (stubbed)
│   ├── audio_cache.py       # Audio caching
│   └── validators.py        # Startup validation
├── data/
│   ├── ika_grammar_patterns.json  # Grammar patterns (source of truth)
│   ├── grammar_rules.json         # Tense/negation/question rules
│   ├── pronouns.json               # Pronouns mapping
│   ├── connectors.json             # Connector words
│   └── templates.json              # Generation templates
├── requirements.txt
├── Dockerfile
└── README.md

backend/tools/
└── validate_ika_examples.py  # Validation script
```

## Troubleshooting

### Validation Errors

If validation fails on startup:
1. Check `data/ika_grammar_patterns.json` for `example_language` fields
2. Check examples for banned tokens
3. Run validator manually: `python3 backend/tools/validate_ika_examples.py`

### Firestore Connection Issues

Verify service account has `roles/datastore.user`:
```bash
gcloud projects get-iam-policy ikause \
  --flatten="bindings[].members" \
  --filter="bindings.members:ika-cloudrun-sa@ikause.iam.gserviceaccount.com"
```

### Storage Access Issues

Verify service account has `roles/storage.objectAdmin`:
```bash
gcloud projects get-iam-policy ikause \
  --flatten="bindings[].members" \
  --filter="bindings.members:ika-cloudrun-sa@ikause.iam.gserviceaccount.com"
```

### Authentication Errors

Ensure you're using the correct token:
```bash
TOKEN="$(gcloud auth print-identity-token)"
```

## Notes

- **Option A (Rule-based)**: Generator uses lexicon + patterns + rules. Examples in patterns are display-only.
- **Audio on-demand**: Audio is NEVER generated unless `/generate-audio` is explicitly called.
- **Validation**: Patterns are validated on startup - service refuses to start if invalid.
- **No paid APIs**: All generation is rule-based using local data files and Firestore.
