#!/usr/bin/env bash
# Smoke test for POST /generate-audio: request MP3 and save to out.mp3
# Usage:
#   export BASE_URL=https://ika-backend-516421484935.europe-west2.run.app
#   export TOKEN=$(gcloud auth print-identity-token)
#   ./backend/scripts/test_tts.sh
# Or for local: BASE_URL=http://localhost:8080 TOKEN=dev ./backend/scripts/test_tts.sh

set -e
BASE_URL="${BASE_URL:-http://localhost:8080}"
TOKEN="${TOKEN:-}"

if [ -z "$TOKEN" ]; then
  echo "Set TOKEN (e.g. TOKEN=\$(gcloud auth print-identity-token))"
  exit 1
fi

OUT="${1:-out.mp3}"
echo "POST $BASE_URL/generate-audio -> $OUT"
curl -sS -X POST "$BASE_URL/generate-audio" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"text": "hello water", "voice": "default"}' \
  -o "$OUT"

if [ ! -f "$OUT" ]; then
  echo "Failed: no output file"
  exit 1
fi
SIZE=$(wc -c < "$OUT" | tr -d ' ')
echo "Saved $OUT ($SIZE bytes)"
if [ "$SIZE" -lt 100 ]; then
  echo "Warning: file very small, might be JSON error body"
  head -c 200 "$OUT" | cat -v
  exit 1
fi
echo "OK"
