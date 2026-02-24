"""
Local audio cache: store TTS output in data/audio_cache/ and serve via GET /audio/{filename}.
Deterministic hash from text + voice + speed + format for stable URLs.
"""
from __future__ import annotations
import hashlib
import logging
from pathlib import Path

from .tts_engine import generate_tts_audio

logger = logging.getLogger(__name__)

# Directory under backend root: data/audio_cache/
def _cache_dir() -> Path:
    base = Path(__file__).resolve().parents[1]
    return base / "data" / "audio_cache"


def _ensure_cache_dir() -> Path:
    d = _cache_dir()
    d.mkdir(parents=True, exist_ok=True)
    return d


def _cache_key(text: str, voice: str, speed: str, fmt: str) -> str:
    raw = f"{text.strip()}|{voice}|{speed}|{fmt}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


async def get_or_generate(
    text: str,
    voice: str = "default",
    speed: str = "1.0",
    fmt: str = "mp3",
) -> tuple[bool, str, str]:
    """
    Get or generate audio; store as MP3 in data/audio_cache/.

    Returns:
        (cache_hit, audio_url_path, filename)
        e.g. (True, "/audio/abc123.mp3", "abc123.mp3")
    """
    text_clean = text.strip()
    if not text_clean:
        raise ValueError("Text cannot be empty")

    key = _cache_key(text_clean, voice, speed, fmt)
    filename = f"{key}.mp3"
    cache_dir = _ensure_cache_dir()
    file_path = cache_dir / filename

    if file_path.exists():
        logger.info("Found cached audio: %s", filename)
        return (True, f"/audio/{filename}", filename)

    logger.info("Generating TTS for text: %s...", text_clean[:50])
    audio_bytes = await generate_tts_audio(text_clean, voice)
    file_path.write_bytes(audio_bytes)
    logger.info("Cached audio: %s", filename)
    return (False, f"/audio/{filename}", filename)


def get_cache_dir() -> Path:
    return _ensure_cache_dir()


def get_file_path(filename: str) -> Path | None:
    """Return Path to cached file if it exists and filename is safe; else None."""
    if not filename.endswith(".mp3"):
        return None
    name = filename[:-4]
    if not name or not all(c in "abcdef0123456789" for c in name):
        return None
    path = _cache_dir() / filename
    return path if path.exists() else None
