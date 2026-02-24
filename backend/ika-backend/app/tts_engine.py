"""
TTS Engine - Google Cloud Text-to-Speech with IPA phonemes (SSML).
Ika → IPA → SSML <phoneme> → synthesize_mp3_from_ssml → MP3 bytes.
"""
import logging
from typing import Optional

from google.cloud import texttospeech
from google.api_core import exceptions as google_exceptions

from tts.ssml import text_to_ssml_with_phonemes, load_ipa_dictionary

logger = logging.getLogger(__name__)

# Cached IPA dict and client
_ipa_dict: Optional[dict] = None
_tts_client: Optional[texttospeech.TextToSpeechClient] = None

# Default voice (English; IPA from <phoneme> drives pronunciation)
DEFAULT_VOICE_NAME = "en-US-Standard-C"
DEFAULT_LANGUAGE_CODE = "en-US"


def _get_ipa_dict():
    global _ipa_dict
    if _ipa_dict is None:
        _ipa_dict = load_ipa_dictionary()
    return _ipa_dict


def _get_client() -> texttospeech.TextToSpeechClient:
    global _tts_client
    if _tts_client is None:
        _tts_client = texttospeech.TextToSpeechClient()
    return _tts_client


def synthesize_mp3_from_ssml(
    ssml: str,
    voice: str = "default",
    speaking_rate: float = 1.0,
    pitch: float = 0.0,
) -> bytes:
    """
    Call Google Cloud TTS with SSML input; return MP3 bytes.
    Voice "default" uses en-US-Standard-C (IPA from <phoneme> tags controls pronunciation).

    Raises:
        ValueError: if SSML empty
        Exception: on TTS API errors (e.g. permission denied — check IAM).
    """
    if not ssml or not ssml.strip():
        raise ValueError("SSML cannot be empty")
    client = _get_client()
    voice_name = DEFAULT_VOICE_NAME if voice == "default" else voice
    synthesis_input = texttospeech.SynthesisInput(ssml=ssml)
    voice_params = texttospeech.VoiceSelectionParams(
        language_code=DEFAULT_LANGUAGE_CODE,
        name=voice_name,
    )
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3,
        speaking_rate=speaking_rate,
        pitch=pitch,
    )
    try:
        response = client.synthesize_speech(
            input=synthesis_input,
            voice=voice_params,
            audio_config=audio_config,
        )
        return response.audio_content
    except google_exceptions.PermissionDenied as e:
        logger.error("TTS permission denied (check IAM for Text-to-Speech): %s", e)
        raise RuntimeError(
            "Text-to-Speech permission denied. "
            "Ensure the service account has the required IAM permission to call Cloud Text-to-Speech. "
            "See docs/tts_iam.md for how to verify and fix."
        ) from e
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
    text_clean = text.strip()
    if not text_clean:
        raise ValueError("Text cannot be empty")
    ipa_dict = _get_ipa_dict()
    ssml = text_to_ssml_with_phonemes(text_clean, ipa_dict)
    logger.info("SSML length: %d chars", len(ssml))
    return synthesize_mp3_from_ssml(ssml, voice=voice, speaking_rate=speaking_rate, pitch=pitch)


async def generate_tts_audio(text: str, voice: str = "default") -> bytes:
    """Async wrapper; kept for compatibility with audio_cache."""
    return generate_tts_audio_mp3(text, voice=voice)
