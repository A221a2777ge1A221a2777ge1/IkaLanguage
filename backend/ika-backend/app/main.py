"""
IKA Language Engine Backend - FastAPI Application
Option A: Rule-based generator using Firestore lexicon + grammar patterns
"""
import os
import logging
import uuid
from fastapi import FastAPI, HTTPException, Depends, Security, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import Response
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

from .firebase_client import get_firestore_client, get_storage_client
from .lexicon_repo import LexiconRepository
from .pattern_repo import PatternRepository
from .rule_engine import RuleEngine
from .slot_filler import SlotFiller
from .generator import Generator
from .templates_engine import TemplatesEngine
from .audio_cache import AudioCache
from .validators import validate_on_startup
from .tts.ssml import load_ipa_dictionary
from .tts_engine import generate_tts_audio_mp3

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables with defaults
PROJECT_ID = os.getenv("PROJECT_ID", "ikause")
LEXICON_COLLECTION = os.getenv("LEXICON_COLLECTION", "lexicon")
FIREBASE_STORAGE_BUCKET = os.getenv("FIREBASE_STORAGE_BUCKET", "ikause.appspot.com")
AUDIO_CACHE_PREFIX = os.getenv("AUDIO_CACHE_PREFIX", "audio-cache")

# Initialize FastAPI app
app = FastAPI(title="IKA Language Engine", version="1.0.0")

# Security for Cloud Run (requires authentication)
security = HTTPBearer()

# Global components
firestore_client = None
storage_client = None
lexicon_repo = None
pattern_repo = None
rule_engine = None
slot_filler = None
generator = None
templates_engine = None
audio_cache = None
ipa_dict = None


async def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Verify authentication token (Cloud Run handles this, but we validate presence)"""
    if not credentials:
        raise HTTPException(status_code=401, detail="Missing authorization token")
    return credentials.credentials


@app.on_event("startup")
async def startup_event():
    """Initialize all components on startup"""
    global firestore_client, storage_client, lexicon_repo, pattern_repo
    global rule_engine, slot_filler, generator, templates_engine, audio_cache, ipa_dict

    logger.info("Initializing IKA backend for project: %s", PROJECT_ID)

    # Validate data files before starting
    try:
        validate_on_startup()
        logger.info("Data validation passed")
    except Exception as e:
        logger.error("Data validation failed: %s", e)
        raise RuntimeError(f"Cannot start: validation failed - {e}") from e

    # Load IPA dictionary for TTS (cached in tts.ssml)
    data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
    ipa_dict = load_ipa_dictionary(data_dir)

    # Initialize Firebase clients
    firestore_client = get_firestore_client(PROJECT_ID)
    storage_client = get_storage_client(PROJECT_ID, FIREBASE_STORAGE_BUCKET)
    
    # Initialize repositories and engines
    lexicon_repo = LexiconRepository(firestore_client, LEXICON_COLLECTION)
    pattern_repo = PatternRepository()
    rule_engine = RuleEngine()
    slot_filler = SlotFiller(lexicon_repo, pattern_repo, rule_engine)
    templates_engine = TemplatesEngine(pattern_repo, slot_filler, rule_engine)
    generator = Generator(lexicon_repo, pattern_repo, rule_engine, slot_filler, templates_engine)
    audio_cache = AudioCache(storage_client, FIREBASE_STORAGE_BUCKET, AUDIO_CACHE_PREFIX)
    
    logger.info("IKA backend initialized successfully")


# Request/Response models
class TranslateRequest(BaseModel):
    text: str
    tense: Optional[str] = "present"  # present|past|future|progressive
    mode: Optional[str] = "rule_based"


class TranslateResponse(BaseModel):
    text: str
    meta: Dict[str, Any]


class GenerateRequest(BaseModel):
    kind: str  # poem|story|lecture
    topic: str
    tone: Optional[str] = "neutral"  # neutral|formal|poetic
    length: Optional[str] = "medium"  # short|medium|long


class GenerateResponse(BaseModel):
    text: str
    meta: Dict[str, Any]


class GenerateAudioRequest(BaseModel):
    text: Optional[str] = None
    prompt: Optional[str] = None
    voice: Optional[str] = "default"
    speaking_rate: Optional[float] = 1.0
    pitch: Optional[float] = 0.0


class DictionaryEntry(BaseModel):
    source_text: str
    target_text: str
    pos: Optional[str] = None
    domain: Optional[str] = None
    doc_id: Optional[str] = None


class DictionaryResponse(BaseModel):
    entries: List[DictionaryEntry]


# Endpoints
@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"ok": True}


@app.post("/translate")
async def translate(
    request: TranslateRequest,
    token: str = Depends(verify_token)
):
    """
    Translate English text to Ika, or dictionary lookup.
    - mode=rule_based (default): returns {"text": "...", "meta": {...}}
    - mode=dictionary: returns {"entries": [{"source_text", "target_text", ...}]}
    """
    mode = (request.mode or "rule_based").strip().lower()
    text = request.text.strip()

    if mode == "dictionary":
        try:
            entries = lexicon_repo.search_by_source_prefix(prefix=text, limit=25)
            out = [
                {
                    "source_text": e.get("source_text", ""),
                    "target_text": e.get("target_text", ""),
                    "pos": e.get("pos"),
                    "domain": e.get("domain"),
                    "doc_id": e.get("doc_id"),
                }
                for e in entries
            ]
            return {"entries": out}
        except Exception as e:
            logger.error("Dictionary lookup error: %s", str(e), exc_info=True)
            raise HTTPException(status_code=500, detail="Dictionary lookup failed") from e

    try:
        result = generator.translate(
            text=request.text,
            tense=request.tense,
            mode=request.mode
        )
        return {
            "text": result["text"],
            "meta": result["meta"],
        }
    except Exception as e:
        logger.error("Translation error: %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Translation failed: {str(e)}") from e


@app.post("/generate", response_model=GenerateResponse)
async def generate(
    request: GenerateRequest,
    token: str = Depends(verify_token)
):
    """
    Generate Ika text (poem/story/lecture) based on topic and parameters.
    Returns text only - NO audio generation.
    """
    try:
        result = generator.generate(
            kind=request.kind,
            topic=request.topic,
            tone=request.tone,
            length=request.length
        )
        return GenerateResponse(
            text=result["text"],
            meta=result["meta"]
        )
    except Exception as e:
        logger.error(f"Generation error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")


@app.post("/generate-audio")
async def generate_audio(
    request: GenerateAudioRequest,
    token: str = Depends(verify_token)
):
    """
    Generate audio for Ika text using Google Cloud TTS + IPA SSML.
    - If "text" is provided: synthesize that Ika text.
    - If "prompt" is provided (and no text): generate Ika text from prompt, then synthesize.
    Returns raw MP3 (Content-Type: audio/mpeg).
    """
    request_id = str(uuid.uuid4())[:8]
    voice = request.voice or "default"
    speaking_rate = request.speaking_rate if request.speaking_rate is not None else 1.0
    pitch = request.pitch if request.pitch is not None else 0.0

    input_text: Optional[str] = (request.text or "").strip() or None
    if not input_text and (request.prompt or "").strip():
        try:
            result = generator.generate(
                kind="story",
                topic=(request.prompt or "").strip(),
                tone="neutral",
                length="short",
            )
            input_text = (result.get("text") or "").strip()
        except Exception as e:
            logger.error("generate_audio request_id=%s generate from prompt failed: %s", request_id, e)
            raise HTTPException(
                status_code=500,
                detail={"error": "Ika generation from prompt failed", "request_id": request_id},
            ) from e
    if not input_text:
        raise HTTPException(status_code=400, detail="Missing 'text' or 'prompt' in request body")

    try:
        cached = audio_cache.get_cached_audio_bytes(input_text, voice, speaking_rate, pitch)
        if cached is not None:
            logger.info("generate_audio request_id=%s cache hit len=%d", request_id, len(cached))
            return Response(
                content=cached,
                media_type="audio/mpeg",
                headers={"Content-Disposition": 'attachment; filename="ika.mp3"'},
            )
        audio_bytes = generate_tts_audio_mp3(
            input_text,
            voice=voice,
            speaking_rate=speaking_rate,
            pitch=pitch,
        )
        audio_cache.put_cached_audio_bytes(input_text, audio_bytes, voice, speaking_rate, pitch)
        logger.info("generate_audio request_id=%s len=%d", request_id, len(audio_bytes))
        return Response(
            content=audio_bytes,
            media_type="audio/mpeg",
            headers={"Content-Disposition": 'attachment; filename="ika.mp3"'},
        )
    except RuntimeError as e:
        if "permission" in str(e).lower() or "IAM" in str(e):
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "Audio generation failed (likely IAM/permission). See docs/tts_iam.md.",
                    "request_id": request_id,
                },
            ) from e
        raise HTTPException(status_code=500, detail={"error": str(e), "request_id": request_id}) from e
    except Exception as e:
        logger.error("generate_audio request_id=%s error: %s", request_id, str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"error": "Audio generation failed", "request_id": request_id},
        ) from e


@app.get("/dictionary", response_model=DictionaryResponse)
async def dictionary_lookup(
    q: str = Query(..., min_length=1),
    token: str = Depends(verify_token)
):
    """
    Dictionary lookup: type English word (or prefix) and get Ika word(s).
    Returns lexicon entries where source_text starts with the query (case-insensitive).
    """
    try:
        entries = lexicon_repo.search_by_source_prefix(prefix=q, limit=25)
        out = [
            DictionaryEntry(
                source_text=e.get("source_text", ""),
                target_text=e.get("target_text", ""),
                pos=e.get("pos"),
                domain=e.get("domain"),
                doc_id=e.get("doc_id"),
            )
            for e in entries
        ]
        return DictionaryResponse(entries=out)
    except Exception as e:
        logger.error(f"Dictionary lookup error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Dictionary lookup failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
