"""
TTS Engine - Google Cloud Text-to-Speech with IPA phonemes (SSML).
"""
import logging
from typing import Optional

from google.cloud import texttospeech

from tts.ssml import text_to_ssml_with_phonemes, load_ipa_dictionary

logger = logging.getLogger(__name__)

# Cached IPA dict and client
_ipa_dict: Optional[dict] = None
_tts_client: Optional[texttospeech.TextToSpeechClient] = None


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


def generate_tts_audio_mp3(text: str, voice: str = "default") -> bytes:
    """
    Generate MP3 audio from Ika text using Google Cloud TTS with IPA SSML.
    Uses en-US voice; pronunciation is forced via <phoneme> tags.

    Args:
        text: Ika text to synthesize
        voice: Voice identifier (currently only default used)

    Returns:
        MP3 audio bytes
    """
    text_clean = text.strip()
    if not text_clean:
        raise ValueError("Text cannot be empty")

    ipa_dict = _get_ipa_dict()
    ssml = text_to_ssml_with_phonemes(text_clean, ipa_dict)
    # Log length only, not full SSML
    logger.info("SSML length: %d chars", len(ssml))

    client = _get_client()

    synthesis_input = texttospeech.SynthesisInput(ssml=ssml)
    voice_params = texttospeech.VoiceSelectionParams(
        language_code="en-US",
        name="en-US-Standard-C",
    )
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3,
    )

    response = client.synthesize_speech(
        input=synthesis_input,
        voice=voice_params,
        audio_config=audio_config,
    )

    return response.audio_content


async def generate_tts_audio(text: str, voice: str = "default") -> bytes:
    """
    Async wrapper for generate_tts_audio_mp3.
    Returns MP3 bytes (kept for compatibility with audio_cache if needed).
    """
    return generate_tts_audio_mp3(text, voice)
