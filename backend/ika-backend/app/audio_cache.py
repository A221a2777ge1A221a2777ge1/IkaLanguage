"""
Audio Cache - Manages on-demand audio generation and caching (URL or bytes).
"""
from google.cloud import storage
from typing import Optional
import hashlib
import logging
from datetime import timedelta
from tts_engine import generate_tts_audio

logger = logging.getLogger(__name__)


def _cache_key(text: str, voice: str, speaking_rate: float, pitch: float) -> str:
    """Cache key from content and TTS params."""
    raw = f"{text.strip()}|{voice}|{speaking_rate}|{pitch}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class AudioCache:
    """Manages audio caching in Firebase Storage (signed URL or raw bytes)."""

    def __init__(self, storage_client: storage.Client, bucket_name: str, cache_prefix: str = "audio-cache"):
        self.storage_client = storage_client
        self.bucket_name = bucket_name
        self.cache_prefix = cache_prefix
        self.bucket = storage_client.bucket(bucket_name)

    def get_cached_audio_bytes(
        self,
        text: str,
        voice: str = "default",
        speaking_rate: float = 1.0,
        pitch: float = 0.0,
    ) -> Optional[bytes]:
        """Return cached MP3 bytes if present, else None."""
        key = _cache_key(text, voice, speaking_rate, pitch)
        path = f"{self.cache_prefix}/{key}.mp3"
        blob = self.bucket.blob(path)
        try:
            if not blob.exists():
                return None
            return blob.download_as_bytes()
        except Exception as e:
            logger.warning("Cache read failed for %s: %s", path, e)
            return None

    def put_cached_audio_bytes(
        self,
        text: str,
        audio_bytes: bytes,
        voice: str = "default",
        speaking_rate: float = 1.0,
        pitch: float = 0.0,
    ) -> None:
        """Store MP3 bytes in cache."""
        key = _cache_key(text, voice, speaking_rate, pitch)
        path = f"{self.cache_prefix}/{key}.mp3"
        blob = self.bucket.blob(path)
        try:
            blob.upload_from_string(audio_bytes, content_type="audio/mpeg")
            logger.info("Cached audio: %s", path)
        except Exception as e:
            logger.warning("Cache write failed for %s: %s", path, e)

    async def get_or_generate_audio(
        self,
        text: str,
        voice: str = "default"
    ) -> str:
        """
        Get or generate audio for Ika text.
        This is the ONLY place audio is generated.
        
        Logic:
        1. Hash text with SHA256
        2. Check Firebase Storage cache at gs://<bucket>/<AUDIO_CACHE_PREFIX>/<hash>.wav
        3. If exists, return its signed URL
        4. Else generate TTS, upload, return signed URL
        
        Args:
            text: Ika text
            voice: Voice identifier
        
        Returns:
            Audio URL (signed URL or public URL)
        """
        text_clean = text.strip()
        if not text_clean:
            raise ValueError("Text cannot be empty")
        
        cache_key = hashlib.sha256(text_clean.encode("utf-8")).hexdigest()
        storage_path = f"{self.cache_prefix}/{cache_key}.mp3"
        
        blob = self.bucket.blob(storage_path)
        
        # Check if cached
        try:
            if blob.exists():
                logger.info(f"Found cached audio: {storage_path}")
                # Generate signed URL (valid for 1 hour)
                signed_url = blob.generate_signed_url(
                    expiration=timedelta(hours=1),
                    method="GET"
                )
                return signed_url
        except Exception as e:
            logger.warning(f"Error checking cache: {e}, proceeding to TTS generation")
        
        # Generate TTS
        logger.info(f"Generating TTS for text: {text_clean[:50]}...")
        
        try:
            # Generate audio using TTS engine
            audio_data = await generate_tts_audio(text_clean, voice)
            
            blob.upload_from_string(audio_data, content_type="audio/mpeg")
            
            # Generate signed URL
            signed_url = blob.generate_signed_url(
                expiration=timedelta(hours=1),
                method="GET"
            )
            
            logger.info(f"Generated and cached audio: {storage_path}")
            return signed_url
            
        except Exception as e:
            logger.error(f"TTS generation failed: {e}", exc_info=True)
            raise
