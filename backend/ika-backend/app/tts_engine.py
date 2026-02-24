"""
TTS Engine

This module provides a single async function:

    generate_tts_audio(text: str, voice: str = "default") -> bytes

It returns audio bytes for the given text.

Current implementation:
- Google Cloud Text-to-Speech (MP3 output)
  - Works in Cloud Run using the service account (ADC)
  - Works in Cloud Shell / local dev if you are logged in with gcloud

Future options (CPU/offline):
- Piper (CPU)
- Coqui TTS (CPU)
- A custom Ika voice model

IMPORTANT:
- Do NOT paste terminal commands (cd, cat, etc.) inside this file.
"""

from __future__ import annotations

import logging
from typing import Dict

from google.cloud import texttospeech

logger = logging.getLogger(__name__)

# Simple "voice" aliases you use in your API -> real Google voice names.
# Edit these to match voices you prefer.
VOICE_MAP: Dict[str, str] = {
    "default": "en-GB-Standard-A",
    "uk_male": "en-GB-Standard-D",
    "us_female": "en-US-Standard-C",
    "us_male": "en-US-Standard-B",
}

# Output format (MP3 is usually easiest for web/mobile streaming)
AUDIO_ENCODING = texttospeech.AudioEncoding.MP3


def _pick_voice_name(alias: str) -> str:
    """Return a valid Google voice name from a simple alias."""
    return VOICE_MAP.get(alias, VOICE_MAP["default"])


def _language_code_from_voice_name(voice_name: str) -> str:
    """
    Extract language code from a Google voice name.
    Example: 'en-GB-Standard-A' -> 'en-GB'
    """
    parts = voice_name.split("-")
    return "-".join(parts[:2]) if len(parts) >= 2 else "en-GB"


async def generate_tts_audio(text: str, voice: str = "default") -> bytes:
    """
    Generate speech audio for the given text (Google Cloud TTS).

    Args:
        text: The text to speak (Ika/English/etc. - depends on chosen voice).
        voice: A short alias in VOICE_MAP (e.g. "default", "uk_male").

    Returns:
        MP3 audio bytes.

    Notes:
        - In Cloud Run: Authentication uses the service account automatically (ADC).
        - In Cloud Shell: Uses your current gcloud auth context.
        - This function is async for API consistency, but the Google client call is blocking.
          That’s okay for light usage; for high throughput, we can offload to a thread pool.
    """
    if not text or not text.strip():
        return b""

    voice_name = _pick_voice_name(voice)
    language_code = _language_code_from_voice_name(voice_name)

    logger.info("TTS request: voice=%s voice_name=%s lang=%s chars=%d",
                voice, voice_name, language_code, len(text))

    client = texttospeech.TextToSpeechClient()

    synthesis_input = texttospeech.SynthesisInput(text=text)

    voice_params = texttospeech.VoiceSelectionParams(
        language_code=language_code,
        name=voice_name,
    )

    audio_config = texttospeech.AudioConfig(audio_encoding=AUDIO_ENCODING)

    response = client.synthesize_speech(
        input=synthesis_input,
        voice=voice_params,
        audio_config=audio_config,
    )

    return response.audio_content


# ------------------------------------------------------------
# OPTIONAL: CPU / Offline TTS (placeholder notes)
# ------------------------------------------------------------
# If you later want CPU-based TTS, keep the same function signature and
# replace the body of generate_tts_audio() with one of these approaches:
#
# 1) Piper (fast CPU)
#    - run piper as a subprocess and capture WAV bytes
#
# 2) Coqui TTS (CPU)
#    from TTS.api import TTS
#    tts = TTS(model_name="tts_models/...your_model...", gpu=False)
#    wav = tts.tts(text=text)
#    # then encode wav -> bytes (wav/mp3) using soundfile/pydub/ffmpeg
#
# Keep your API stable: always return bytes.