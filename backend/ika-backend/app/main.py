"""
IKA Language Engine Backend - FastAPI Application
Option A: Rule-based generator using Firestore lexicon + grammar patterns
"""
import os
import logging
from fastapi import FastAPI, HTTPException, Depends, Security, Query
from fastapi.responses import FileResponse
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
from local_audio_cache import get_or_generate as local_audio_get_or_generate, get_file_path as local_audio_get_file_path

try:
    from lexicon_store import get_store
    from dataset_generator import (
        translate_en_to_ika_sentence,
        translate_ika_to_en,
        generate_story as dataset_generate_story,
        generate_poem as dataset_generate_poem,
        generate_lecture as dataset_generate_lecture,
        naturalize as dataset_naturalize,
    )
    _dataset_available = True
except Exception as e:
    logging.getLogger(__name__).warning("Dataset (lexicon_store) not available: %s", e)
    _dataset_available = False
    get_store = None
    translate_en_to_ika_sentence = translate_ika_to_en = None
    dataset_generate_story = dataset_generate_poem = dataset_generate_lecture = None
    dataset_naturalize = None

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
store = None  # LexiconStore from firestore_lexicon_export.json when available


async def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Verify authentication token (Cloud Run handles this, but we validate presence)"""
    if not credentials:
        raise HTTPException(status_code=401, detail="Missing authorization token")
    return credentials.credentials


@app.on_event("startup")
async def startup_event():
    """Initialize all components on startup. Server still starts if Firestore/dataset fail."""
    global firestore_client, storage_client, lexicon_repo, pattern_repo
    global rule_engine, slot_filler, generator, templates_engine, audio_cache, store

    logger.info(f"Initializing IKA backend for project: {PROJECT_ID}")

    # Validate data files (required for rule-based engine)
    try:
        validate_on_startup()
        logger.info("Data validation passed")
    except Exception as e:
        logger.error(f"Data validation failed: {e}")
        raise RuntimeError(f"Cannot start: validation failed - {e}")

    # Initialize Firebase and repos (non-blocking: allow start even if Firestore fails)
    try:
        firestore_client = get_firestore_client(PROJECT_ID)
        storage_client = get_storage_client(PROJECT_ID, FIREBASE_STORAGE_BUCKET)
        lexicon_repo = LexiconRepository(firestore_client, LEXICON_COLLECTION)
        pattern_repo = PatternRepository()
        rule_engine = RuleEngine()
        slot_filler = SlotFiller(lexicon_repo, pattern_repo, rule_engine)
        templates_engine = TemplatesEngine(pattern_repo, slot_filler, rule_engine)
        generator = Generator(lexicon_repo, pattern_repo, rule_engine, slot_filler, templates_engine)
        audio_cache = AudioCache(storage_client, FIREBASE_STORAGE_BUCKET, AUDIO_CACHE_PREFIX)
    except Exception as e:
        logger.warning("Firebase/repos init failed (some endpoints may return 503): %s", e)
        firestore_client = storage_client = None
        lexicon_repo = pattern_repo = rule_engine = slot_filler = None
        templates_engine = generator = audio_cache = None

    # Dataset from JSON (optional; file may be gitignored in deploy)
    if _dataset_available and get_store:
        try:
            store = get_store()
            logger.info("Dataset (firestore_lexicon_export) loaded: %d entries", len(store.entries))
        except Exception as e:
            logger.warning("Dataset not loaded (add data/firestore_lexicon_export.json for full features): %s", e)
            store = None
    else:
        store = None

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


class StoryIn(BaseModel):
    """Request body for POST /generate-story (app sends prompt + length)."""
    prompt: str
    length: Optional[str] = "short"


class GenerateAudioRequest(BaseModel):
    text: str
    voice: Optional[str] = "default"
    speed: Optional[str] = "1.0"
    format: Optional[str] = "mp3"


class GenerateAudioResponse(BaseModel):
    cache_hit: bool
    audio_url: str  # e.g. /audio/abc123.mp3
    filename: str
    text: str


class NaturalizeIn(BaseModel):
    intent_text: str
    tone: Optional[str] = "polite"  # polite|casual|respectful|romantic
    length: Optional[str] = "short"


class NaturalizeOut(BaseModel):
    ika: str
    english_backtranslation: str
    notes: List[str]


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
    Translate: use dataset (strict Ika patterns) when mode is auto|en_to_ika|ika_to_en
    and store is loaded; otherwise rule-based. Returns text + meta (source_lang/target_lang when dataset).
    """
    mode = (request.mode or "rule_based").lower()
    if store is None and generator is None:
        raise HTTPException(status_code=503, detail="Translation unavailable (backend not fully initialized)")
    if store is not None and mode in ("auto", "en_to_ika", "ika_to_en"):
        try:
            text = request.text.strip()
            if mode == "ika_to_en":
                result_text = translate_ika_to_en(store, text)
                return TranslateResponse(
                    text=result_text,
                    meta={"source_lang": "ika", "target_lang": "en"}
                )
            if mode == "en_to_ika":
                result_text = translate_en_to_ika_sentence(store, text)
                return TranslateResponse(
                    text=result_text,
                    meta={"source_lang": "en", "target_lang": "ika"}
                )
            # auto: detect by is_ika_text
            if store.is_ika_text(text):
                result_text = translate_ika_to_en(store, text)
                return TranslateResponse(
                    text=result_text,
                    meta={"source_lang": "ika", "target_lang": "en"}
                )
            result_text = translate_en_to_ika_sentence(store, text)
            return TranslateResponse(
                text=result_text,
                meta={"source_lang": "en", "target_lang": "ika"}
            )
        except Exception as e:
            logger.error(f"Dataset translation error: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Translation failed: {str(e)}")
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
    if store is None and generator is None:
        raise HTTPException(status_code=503, detail="Generation unavailable (backend not fully initialized)")
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


@app.post("/generate-story", response_model=GenerateResponse)
async def generate_story(
    request: StoryIn,
    token: str = Depends(verify_token)
):
    """
    Generate Ika story. Uses dataset (659 entries) when loaded; else rule-based.
    """
    if store is None and generator is None:
        raise HTTPException(status_code=503, detail="Generation unavailable (backend not fully initialized)")
    if store is not None and dataset_generate_story is not None:
        try:
            length = request.length or "short"
            text = dataset_generate_story(store, length)
            return GenerateResponse(text=text, meta={"source": "dataset", "length": length})
        except Exception as e:
            logger.error(f"Dataset generate story error: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")
    try:
        result = generator.generate(
            kind="story",
            topic=request.prompt.strip(),
            tone="neutral",
            length=request.length or "short",
        )
        return GenerateResponse(
            text=result["text"],
            meta=result["meta"]
        )
    except Exception as e:
        logger.error(f"Generate story error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")


@app.post("/generate-poem", response_model=GenerateResponse)
async def generate_poem(
    request: StoryIn,
    token: str = Depends(verify_token)
):
    """Generate Ika poem from dataset (length short -> 8 lines, medium/long -> 14)."""
    if store is None and generator is None:
        raise HTTPException(status_code=503, detail="Generation unavailable (backend not fully initialized)")
    if store is not None and dataset_generate_poem is not None:
        try:
            length = request.length or "short"
            lines = 14 if length in ("medium", "long") else 8
            text = dataset_generate_poem(store, lines=lines)
            return GenerateResponse(text=text, meta={"source": "dataset", "lines": lines})
        except Exception as e:
            logger.error(f"Dataset generate poem error: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")
    try:
        result = generator.generate(
            kind="poem",
            topic=request.prompt.strip() or "poem",
            tone="neutral",
            length=request.length or "short",
        )
        return GenerateResponse(text=result["text"], meta=result["meta"])
    except Exception as e:
        logger.error(f"Generate poem error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")


@app.post("/generate-lecture", response_model=GenerateResponse)
async def generate_lecture(
    request: StoryIn,
    token: str = Depends(verify_token)
):
    """Generate Ika lecture from dataset."""
    if store is None and generator is None:
        raise HTTPException(status_code=503, detail="Generation unavailable (backend not fully initialized)")
    if store is not None and dataset_generate_lecture is not None:
        try:
            length = request.length or "short"
            text = dataset_generate_lecture(store, length)
            return GenerateResponse(text=text, meta={"source": "dataset", "length": length})
        except Exception as e:
            logger.error(f"Dataset generate lecture error: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")
    try:
        result = generator.generate(
            kind="lecture",
            topic=request.prompt.strip() or "lecture",
            tone="neutral",
            length=request.length or "short",
        )
        return GenerateResponse(text=result["text"], meta=result["meta"])
    except Exception as e:
        logger.error(f"Generate lecture error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")


@app.post("/naturalize", response_model=NaturalizeOut)
async def naturalize(
    request: NaturalizeIn,
    token: str = Depends(verify_token),
):
    """
    Naturalize: "Say it like an Ika person." Input is English intent;
    output is natural Ika phrasing from dataset (no word-for-word translation).
    """
    if store is None or dataset_naturalize is None:
        raise HTTPException(
            status_code=503,
            detail="Dataset not loaded; naturalize unavailable",
        )
    try:
        ika_text, en_back, notes = dataset_naturalize(
            store,
            intent_text=request.intent_text.strip(),
            tone=request.tone or "polite",
            length=request.length or "short",
        )
        return NaturalizeOut(
            ika=ika_text,
            english_backtranslation=en_back,
            notes=notes,
        )
    except Exception as e:
        logger.error(f"Naturalize error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Naturalize failed: {str(e)}")


@app.post("/generate-audio", response_model=GenerateAudioResponse)
async def generate_audio(
    request: GenerateAudioRequest,
    token: str = Depends(verify_token)
):
    """
    Generate or retrieve audio for Ika text. Uses local file cache (data/audio_cache/).
    Returns stable URL path /audio/<hash>.mp3 for download.
    """
    try:
        cache_hit, audio_url_path, filename = await local_audio_get_or_generate(
            text=request.text,
            voice=request.voice or "default",
            speed=request.speed or "1.0",
            fmt=(request.format or "mp3").lower(),
        )
        return GenerateAudioResponse(
            cache_hit=cache_hit,
            audio_url=audio_url_path,
            filename=filename,
            text=request.text.strip(),
        )
    except Exception as e:
        logger.error(f"Audio generation error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Audio generation failed: {str(e)}")


@app.get("/audio/{filename}")
async def serve_audio(filename: str):
    """
    Serve cached audio file. No auth required so the app can download by URL.
    Content-Type: audio/mpeg, Cache-Control: public, long-lived.
    """
    path = local_audio_get_file_path(filename)
    if path is None:
        raise HTTPException(status_code=404, detail="Audio file not found")
    return FileResponse(
        path,
        media_type="audio/mpeg",
        headers={
            "Cache-Control": "public, max-age=31536000, immutable",
        },
    )


@app.get("/dictionary", response_model=DictionaryResponse)
async def dictionary_lookup(
    q: str = Query(..., min_length=1),
    token: str = Depends(verify_token)
):
    """
    Dictionary lookup: type English word (or prefix) and get Ika word(s).
    Returns lexicon entries where source_text starts with the query (case-insensitive).
    """
    if lexicon_repo is None:
        raise HTTPException(status_code=503, detail="Dictionary unavailable (Firestore not connected)")
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
