"""
TTS Engine - Google Cloud Text-to-Speech with IPA phonemes (SSML).
Ika → IPA → SSML <phoneme> → synthesize_mp3_from_ssml → MP3 bytes.

Upgrades:
- Adds build_ssml_with_ipa() for legacy compatibility (scripts/test_tts.py).
- Lazy-initializes Google TTS client (import-safe, easier testing).
- Stronger validation + clearer error messages.
- SSML auto-detection helper.
- Keeps existing public APIs (synthesize_mp3_from_ssml, generate_tts_audio_mp3, generate_tts_audio).
"""

import logging
from typing import Optional, Dict

from google.api_core import exceptions as google_exceptions

try:
    # Optional IPA/phoneme SSML support (only if app/tts/ssml.py exists)
    from .tts.ssml import text_to_ssml_with_phonemes, load_ipa_dictionary  # type: ignore
except ModuleNotFoundError:
    text_to_ssml_with_phonemes = None  # type: ignore
    load_ipa_dictionary = None  # type: ignore


logger = logging.getLogger(__name__)

# Cached IPA dict and client
_ipa_dict: Optional[Dict] = None
_tts_client = None  # lazy client cache


# Default voice (English; IPA from <phoneme> drives pronunciation)
DEFAULT_VOICE_NAME = "en-US-Standard-C"
DEFAULT_LANGUAGE_CODE = "en-US"


def _get_ipa_dict() -> Dict:
    global _ipa_dict
    if load_ipa_dictionary is None:
        return {}
    if _ipa_dict is None:
        _ipa_dict = load_ipa_dictionary()
    return _ipa_dict


def _tts_types():
    """Lazy import for google.cloud.texttospeech types/constants."""
    from google.cloud import texttospeech
    return texttospeech


def _get_client():
    """Lazy client getter."""
    global _tts_client
    if _tts_client is None:
        texttospeech = _tts_types()
        _tts_client = texttospeech.TextToSpeechClient()
    return _tts_client


def _is_ssml(s: str) -> bool:
    t = (s or "").lstrip()
    return t.lower().startswith("<speak")


# ----------------------------
# Backward-compatible helpers
# ----------------------------
def build_ssml_with_ipa(text: str) -> str:
    """
    Legacy helper expected by scripts/test_tts.py.

    If IPA/phoneme SSML helpers are available (app/tts/ssml.py), use them.
    Otherwise, fall back to minimal SSML wrapping.
    """
    text_clean = (text or "").strip()
    if not text_clean:
        raise ValueError("Text cannot be empty")

    if text_to_ssml_with_phonemes is None:
        return f"<speak>{text_clean}</speak>"

    ipa_dict = _get_ipa_dict()
    return text_to_ssml_with_phonemes(text_clean, ipa_dict)


def synthesize_mp3_from_ssml(
    ssml: str,
    voice: str = "default",
    speaking_rate: float = 1.0,
    pitch: float = 0.0,
) -> bytes:
    """
    Call Google Cloud TTS with SSML input; return MP3 bytes.

    Raises:
        ValueError: if SSML empty / invalid request.
        RuntimeError: if permission denied (IAM).
        Exception: on other TTS API errors.
    """
    ssml_clean = (ssml or "").strip()
    if not ssml_clean:
        raise ValueError("SSML cannot be empty")

    if not _is_ssml(ssml_clean):
        # If caller accidentally passed plain text, wrap it so Google accepts it as SSML.
        ssml_clean = f"<speak>{ssml_clean}</speak>"

    client = _get_client()
    texttospeech = _tts_types()

    voice_name = DEFAULT_VOICE_NAME if voice == "default" else voice

    synthesis_input = texttospeech.SynthesisInput(ssml=ssml_clean)
    voice_params = texttospeech.VoiceSelectionParams(
        language_code=DEFAULT_LANGUAGE_CODE,
        name=voice_name,
    )
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3,
        speaking_rate=float(speaking_rate),
        pitch=float(pitch),
    )

    try:
        response = client.synthesize_speech(
            input=synthesis_input,
            voice=voice_params,
            audio_config=audio_config,
        )
        audio = response.audio_content
        if not audio:
            raise RuntimeError("TTS returned empty audio content")
        return audio

    except google_exceptions.PermissionDenied as e:
        logger.error("TTS permission denied (check IAM for Text-to-Speech): %s", e)
        raise RuntimeError(
            "Text-to-Speech permission denied. Ensure the service account has the required IAM "
            "permission to call Cloud Text-to-Speech."
        ) from e

    except google_exceptions.InvalidArgument as e:
        logger.error("TTS invalid argument (bad SSML/params): %s", e)
        raise ValueError("Invalid TTS request (check SSML/voice/speaking_rate/pitch).") from e

    except Exception as e:
        logger.error("TTS synthesis failed: %s", e, exc_info=True)
        raise


def generate_tts_audio_mp3(
    text: str,
    voice: str = "default",
    speaking_rate: float = 1.0,
    pitch: float = 0.0,
) -> bytes:
    """
    Generate MP3 from Ika text: text → IPA → SSML → Google TTS → MP3 bytes.
    """
    text_clean = (text or "").strip()
    if not text_clean:
        raise ValueError("Text cannot be empty")

    ssml = build_ssml_with_ipa(text_clean)
    logger.info("SSML length: %d chars", len(ssml))

    return synthesize_mp3_from_ssml(
        ssml,
        voice=voice,
        speaking_rate=speaking_rate,
        pitch=pitch,
    )


async def generate_tts_audio(text: str, voice: str = "default") -> bytes:
    """Async wrapper; kept for compatibility with audio_cache."""
    return generate_tts_audio_mp3(text, voice=voice)
