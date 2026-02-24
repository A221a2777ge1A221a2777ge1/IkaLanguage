"""
Audio Cache - Manages on-demand audio generation and caching
"""
from google.cloud import storage
from typing import Optional
import hashlib
import logging
from datetime import timedelta
from app.lexicon_repo import LexiconRepository
from app.tts_engine import generate_tts_audio

logger = logging.getLogger(__name__)


class AudioCache:
    """Manages audio caching in Firebase Storage with lexicon priority"""
    
    def __init__(self, storage_client: storage.Client, bucket_name: str, cache_prefix: str = "audio-cache"):
        self.storage_client = storage_client
        self.bucket_name = bucket_name
        self.cache_prefix = cache_prefix
        self.bucket = storage_client.bucket(bucket_name)
    
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
        
        # Generate cache key (SHA256 hash)
        cache_key = hashlib.sha256(text_clean.encode('utf-8')).hexdigest()
        storage_path = f"{self.cache_prefix}/{cache_key}.wav"
        
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
            
            # Upload to Firebase Storage
            blob.upload_from_string(
                audio_data,
                content_type="audio/wav"
            )
            
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
