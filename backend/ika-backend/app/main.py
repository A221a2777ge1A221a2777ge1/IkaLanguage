"""
IKA Language Engine Backend - FastAPI Application
Option A: Rule-based generator using Firestore lexicon + grammar patterns
"""
import os
import logging
from fastapi import FastAPI, HTTPException, Depends, Security, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

from firebase_client import get_firestore_client, get_storage_client
from lexicon_repo import LexiconRepository
from pattern_repo import PatternRepository
from rule_engine import RuleEngine
from slot_filler import SlotFiller
from generator import Generator
from templates_engine import TemplatesEngine
from audio_cache import AudioCache
from validators import validate_on_startup

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


async def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Verify authentication token (Cloud Run handles this, but we validate presence)"""
    if not credentials:
        raise HTTPException(status_code=401, detail="Missing authorization token")
    return credentials.credentials


@app.on_event("startup")
async def startup_event():
    """Initialize all components on startup"""
    global firestore_client, storage_client, lexicon_repo, pattern_repo
    global rule_engine, slot_filler, generator, templates_engine, audio_cache
    
    logger.info(f"Initializing IKA backend for project: {PROJECT_ID}")
    
    # Validate data files before starting
    try:
        validate_on_startup()
        logger.info("Data validation passed")
    except Exception as e:
        logger.error(f"Data validation failed: {e}")
        raise RuntimeError(f"Cannot start: validation failed - {e}")
    
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
    text: str
    voice: Optional[str] = "default"


class GenerateAudioResponse(BaseModel):
    audio_url: str


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


@app.post("/translate", response_model=TranslateResponse)
async def translate(
    request: TranslateRequest,
    token: str = Depends(verify_token)
):
    """
    Translate English text to Ika using rule-based generation.
    Returns text only - NO audio generation.
    """
    try:
        result = generator.translate(
            text=request.text,
            tense=request.tense,
            mode=request.mode
        )
        return TranslateResponse(
            text=result["text"],
            meta=result["meta"]
        )
    except Exception as e:
        logger.error(f"Translation error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Translation failed: {str(e)}")


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


@app.post("/generate-audio", response_model=GenerateAudioResponse)
async def generate_audio(
    request: GenerateAudioRequest,
    token: str = Depends(verify_token)
):
    """
    Generate or retrieve audio for Ika text.
    This is the ONLY endpoint that generates audio.

    Logic:
    1. Hash text with SHA256
    2. Check Firebase Storage cache
    3. If exists, return URL
    4. Else generate TTS, upload, return URL
    """
    try:
        audio_url = await audio_cache.get_or_generate_audio(
            text=request.text,
            voice=request.voice
        )
        return GenerateAudioResponse(audio_url=audio_url)
    except Exception as e:
        logger.error(f"Audio generation error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Audio generation failed: {str(e)}")


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
