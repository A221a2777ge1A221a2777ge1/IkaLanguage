"""
IKA Language Engine Backend - FastAPI Application
Option A: Rule-based generator using Firestore lexicon + grammar patterns
"""
import os
import logging
from app.nlp.phrasebank import phrasebank_ika_to_en
from typing import Optional, Dict, Any, List, Tuple
from fastapi import FastAPI, HTTPException, Depends, Security, Query, Request
from app.nlp.phrasebank import phrasebank_ika_to_en_fuzzy
from app.nlp.local_translate_phrasebank import phrasebank_translate
from fastapi.responses import FileResponse
from app.nlp.local_translate_phrasebank import phrasebank_translate
from app.nlp.phrasebank import phrasebank_ika_to_en
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

import firebase_admin
from firebase_admin import auth as fb_auth

from app.firebase_client import get_firestore_client, get_storage_client
from app.lexicon_repo import LexiconRepository
from app.pattern_repo import PatternRepository
from app.rule_engine import RuleEngine
from app.slot_filler import SlotFiller
from app.generator import Generator
from app.templates_engine import TemplatesEngine
from app.audio_cache import AudioCache
from app.validators import validate_on_startup
from app.build_info import get_build_info
from app.local_audio_cache import (
    get_or_generate as local_audio_get_or_generate,
    get_file_path as local_audio_get_file_path,
)

try:
    from app.lexicon_store import get_store
    from app.dataset_generator import (
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

# Security
security = HTTPBearer(auto_error=False)

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

# Firebase init guard
_firebase_inited = False


def _init_firebase_once() -> None:
    """
    Initialize firebase_admin once (ADC on Cloud Run).
    This enables fb_auth.verify_id_token for Firebase ID tokens.
    """
    global _firebase_inited
    if _firebase_inited:
        return
    try:
        firebase_admin.get_app()
    except ValueError:
        firebase_admin.initialize_app()
    _firebase_inited = True


from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
security = HTTPBearer(auto_error=False)

async def verify_token(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> Dict[str, Any]:
    # Local dev bypass (localhost only)
    client_host = request.client.host if request.client else ""
    if client_host in ("127.0.0.1", "localhost"):
        return {"uid": "local-dev", "auth": "bypass"}

    token = credentials.credentials if credentials else None
    if not token:
        raise HTTPException(status_code=401, detail="Missing authorization token")

    _init_firebase_once()
    try:
        decoded = fb_auth.verify_id_token(token, check_revoked=False)
        return decoded
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


@app.on_event("startup")
async def startup_event():
    """Initialize all components on startup. Server still starts if Firestore/dataset fail."""
    global firestore_client, storage_client, lexicon_repo, pattern_repo
    global rule_engine, slot_filler, generator, templates_engine, audio_cache, store

    logger.info("Initializing IKA backend for project: %s", PROJECT_ID)

    # Validate data files (log only; do not block startup so Cloud Run can see the port)
    try:
        validate_on_startup()
        logger.info("Data validation passed")
    except Exception as e:
        logger.warning("Data validation failed (continuing): %s", e)

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

    # Dataset from JSON (optional)
    if _dataset_available and get_store:
        try:
            store = get_store()
            logger.info("Dataset loaded: %d entries", len(store.entries))
        except Exception as e:
            logger.warning("Dataset not loaded (add data/firestore_lexicon_export.json): %s", e)
            store = None
    else:
        store = None

    logger.info("IKA backend initialized successfully")


# -----------------------------
# Models (new contract + legacy)
# -----------------------------

class ApiResponse(BaseModel):
    """
    New contract:
      - ika_text: Ika output text
      - english_meaning: English meaning of the produced Ika output
      - trace: debug-only structure used for development (pattern ids, lexicon ids, etc.)

    Backward-compat (temporary):
      - text: same as ika_text
      - meta: legacy meta object
    """
    ika_text: str
    english_meaning: str
    trace: Dict[str, Any] = {}
    # legacy
    text: str
    meta: Dict[str, Any] = {}


class TranslateRequest(BaseModel):
    text: str
    tense: Optional[str] = "present"  # present|past|future|progressive
    mode: Optional[str] = "rule_based"


class GenerateRequest(BaseModel):
    kind: str  # sentence|poem|story|lecture|song
    topic: str
    tone: Optional[str] = "neutral"   # neutral|formal|poetic
    length: Optional[str] = "medium"  # short|medium|long


class StoryIn(BaseModel):
    """Request body for POST /generate-story /generate-poem /generate-lecture."""
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


class DictionaryEntry(BaseModel):
    source_text: str
    target_text: str
    pos: Optional[str] = None
    domain: Optional[str] = None
    doc_id: Optional[str] = None
    # future: audio_id/audio_url for original recordings
    audio_id: Optional[str] = None
    audio_url: Optional[str] = None


class DictionaryResponse(BaseModel):
    entries: List[DictionaryEntry]


# -----------------------------
# Helpers
# -----------------------------

def _make_response(
    ika_text: str,
    english_meaning: str,
    *,
    legacy_meta: Optional[Dict[str, Any]] = None,
    trace: Optional[Dict[str, Any]] = None,
) -> ApiResponse:
    legacy_meta = legacy_meta or {}
    trace = trace or {}
    return ApiResponse(
        ika_text=ika_text,
        english_meaning=english_meaning,
        trace=trace,
        # legacy
        text=ika_text,
        meta=legacy_meta,
    )


def _extract_trace_from_meta(meta: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize legacy meta into a trace block used for debugging and future UI.
    """
    trace: Dict[str, Any] = {}
    if not isinstance(meta, dict):
        return trace
    if "pattern_ids" in meta:
        trace["pattern_ids"] = meta.get("pattern_ids", [])
    if "lexicon_entries" in meta:
        # keep doc_id + source/target for debugging
        trace["lexicon_entries"] = meta.get("lexicon_entries", [])
    if "tense" in meta:
        trace["tense"] = meta.get("tense")
    if "mode" in meta:
        trace["mode"] = meta.get("mode")
    if "source_lang" in meta:
        trace["source_lang"] = meta.get("source_lang")
    if "target_lang" in meta:
        trace["target_lang"] = meta.get("target_lang")
    return trace


def _english_meaning_for_ika_output(
    produced_ika_text: str,
    *,
    source_text: str,
    mode: str,
) -> str:
    """
    English meaning should reflect the meaning of what we produced in Ika,
    not the topic.
    Strategy:
      - If store is available and we can translate ika->en, use that.
      - Else fallback to the original English input (best-effort).
    """
    if store is not None and translate_ika_to_en is not None:
        try:
            # If we produced Ika, back-translate it to English meaning.
            return translate_ika_to_en(store, produced_ika_text)
        except Exception:
            pass
    # Fallback: if user input was English, keep it as meaning baseline
    return source_text.strip()


# -----------------------------
# Endpoints
# -----------------------------

@app.get("/health")
async def health():
    """Health check endpoint (no auth). Returns ok + build fingerprint."""
    try:
        build = get_build_info()
    except Exception:
        build = {"git_sha": "unknown", "dataset_sha256": "error", "dataset_files_count": 0}
    return {"ok": True, "build": build}


@app.get("/build-info")
async def build_info():
    """Build and dataset fingerprint (no auth)."""
    try:
        return get_build_info()
    except Exception:
        return {"git_sha": "unknown", "dataset_sha256": "error", "dataset_files_count": 0}

    # --- Phrasebank local chunker (fast, exact phrase matches) ---
    pb_text, pb_meta = phrasebank_translate(text)
    if pb_text and pb_text.strip():
        return {
            "ok": True,
            "data": {
                "target_text": pb_text,
                "source": "phrasebank",
                "confidence": "high",
                "meta": pb_meta,
            },
        }
def _is_not_found_en(en_text: str | None) -> bool:
    if not en_text:
        return True
    t = en_text.strip().lower()
    return t in ("not found in dataset.", "not found", "")


def _is_not_found_en(en_text: str | None) -> bool:
    t = (en_text or "").strip().lower()
    return (not t) or (t in ("not found in dataset.", "not found"))


@app.post("/translate", response_model=ApiResponse)
async def translate(req: TranslateRequest, decoded: Dict[str, Any] = Depends(verify_token)):
    """
    Translate:
      - Phrasebank first (fast phrase chunks) for English->Ika in (auto|en_to_ika)
      - Dataset store next (auto|en_to_ika|ika_to_en) when available
      - Rule-based generator last
    """
    mode = (req.mode or "rule_based").lower()
    text_in = (req.text or "").strip()

    if not text_in:
        raise HTTPException(status_code=422, detail="text is required")

    if store is None and generator is None:
        raise HTTPException(status_code=503, detail="Translation unavailable (backend not fully initialized)")

    # ======================================================
    # Phrasebank FIRST (English -> Ika)
    # Only for: en_to_ika, auto(when input is NOT ika)
    # Meaning must be the original English input.
    # ======================================================
    try:
        if mode in ("en_to_ika", "auto"):
            is_ika = (store is not None and store.is_ika_text(text_in))
            if not is_ika:
                pb_ika, pb_meta = phrasebank_translate(text_in)
                if pb_ika and pb_ika.strip():
                    return _make_response(
                        ika_text=pb_ika.strip(),
                        english_meaning=text_in,  # ✅ original English input
                        legacy_meta={**(pb_meta or {}), "engine": "phrasebank"},
                        trace={
                            "source_lang": "en",
                            "target_lang": "ika",
                            "mode": mode,
                            "engine": "phrasebank",
                            "meaning_source": "original_input",
                        },
                    )
    except Exception as e:
        logger.warning("phrasebank failed (ignored): %s", str(e), exc_info=True)

    # ======================================================
    # Dataset-driven path (supports ika_to_en too)
    # ======================================================
    if store is not None and mode in ("auto", "en_to_ika", "ika_to_en"):
        try:
            # -------------------------
            # IKA -> EN (dataset first, then phrasebank FUZZY fallback)
            # -------------------------
            if mode == "ika_to_en":
                en_text = translate_ika_to_en(store, text_in)

                if _is_not_found_en(en_text):
                    pb_en = phrasebank_ika_to_en_fuzzy(text_in)  # ✅ fuzzy handles "jẹn afịa"
                    if pb_en and pb_en.strip():
                        return _make_response(
                            ika_text=text_in,
                            english_meaning=pb_en.strip(),
                            legacy_meta={"source_lang": "ika", "target_lang": "en", "engine": "phrasebank"},
                            trace={
                                "source_lang": "ika",
                                "target_lang": "en",
                                "mode": mode,
                                "engine": "phrasebank",
                                "meaning_source": "phrasebank_fuzzy",
                            },
                        )

                return _make_response(
                    ika_text=text_in,
                    english_meaning=(en_text or "").strip(),
                    legacy_meta={"source_lang": "ika", "target_lang": "en", "engine": "dataset"},
                    trace={"source_lang": "ika", "target_lang": "en", "mode": mode, "engine": "dataset"},
                )

            # -------------------------
            # EN -> IKA (dataset)
            # Meaning should be original English input for this endpoint contract.
            # -------------------------
            if mode == "en_to_ika":
                ika_text = translate_en_to_ika_sentence(store, text_in)
                return _make_response(
                    ika_text=ika_text,
                    english_meaning=text_in,  # ✅ original English input
                    legacy_meta={"source_lang": "en", "target_lang": "ika", "engine": "dataset"},
                    trace={"source_lang": "en", "target_lang": "ika", "mode": mode, "engine": "dataset"},
                )

            # -------------------------
            # AUTO
            # -------------------------
            if mode == "auto":
                # If input looks like Ika => Ika->En path
                if store.is_ika_text(text_in):
                    en_text = translate_ika_to_en(store, text_in)

                    if _is_not_found_en(en_text):
                        pb_en = phrasebank_ika_to_en_fuzzy(text_in)  # ✅ fuzzy fallback
                        if pb_en and pb_en.strip():
                            return _make_response(
                                ika_text=text_in,
                                english_meaning=pb_en.strip(),
                                legacy_meta={"source_lang": "ika", "target_lang": "en", "engine": "phrasebank"},
                                trace={
                                    "source_lang": "ika",
                                    "target_lang": "en",
                                    "mode": mode,
                                    "engine": "phrasebank",
                                    "meaning_source": "phrasebank_fuzzy",
                                },
                            )

                    return _make_response(
                        ika_text=text_in,
                        english_meaning=(en_text or "").strip(),
                        legacy_meta={"source_lang": "ika", "target_lang": "en", "engine": "dataset"},
                        trace={"source_lang": "ika", "target_lang": "en", "mode": mode, "engine": "dataset"},
                    )

                # Otherwise input is English => En->Ika path
                ika_text = translate_en_to_ika_sentence(store, text_in)
                return _make_response(
                    ika_text=ika_text,
                    english_meaning=text_in,
                    legacy_meta={"source_lang": "en", "target_lang": "ika", "engine": "dataset"},
                    trace={"source_lang": "en", "target_lang": "ika", "mode": mode, "engine": "dataset"},
                )

        except Exception as e:
            logger.error("Dataset translation error: %s", str(e), exc_info=True)
            raise HTTPException(status_code=500, detail=f"Translation failed: {str(e)}")

    # ======================================================
    # Rule-based path (last)
    # ======================================================
    try:
        result = generator.translate(text=text_in, tense=req.tense, mode=req.mode)
        ika_text = (result.get("text") or "").strip()
        meta = result.get("meta", {}) or {}
        trace = _extract_trace_from_meta(meta)

        english_meaning = _english_meaning_for_ika_output(
            ika_text, source_text=text_in, mode=mode
        )

        return _make_response(
            ika_text=ika_text,
            english_meaning=english_meaning,
            legacy_meta={**meta, "engine": "rule_based"},
            trace=trace,
        )
    except Exception as e:
        logger.error("Translation error: %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Translation failed: {str(e)}")
@app.post("/generate-poem", response_model=ApiResponse)
async def generate_poem(
    request: StoryIn,
    _claims: Dict[str, Any] = Depends(verify_token),
):
    """Generate Ika poem (dataset when available, else rule-based)."""
    if store is None and generator is None:
        raise HTTPException(status_code=503, detail="Generation unavailable (backend not fully initialized)")

    prompt = (request.prompt or "").strip()
    length = (request.length or "short").strip().lower()

    if store is not None and dataset_generate_poem is not None:
        try:
            lines = 14 if length in ("medium", "long") else 8
            ika_text = dataset_generate_poem(store, lines=lines)
            english_meaning = _english_meaning_for_ika_output(
                ika_text, source_text=prompt, mode="generate_poem"
            )
            return _make_response(
                ika_text=ika_text,
                english_meaning=english_meaning,
                legacy_meta={"source": "dataset", "lines": lines},
                trace={"source": "dataset", "lines": lines},
            )
        except Exception as e:
            logger.error("Dataset generate poem error: %s", str(e), exc_info=True)
            raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")

    try:
        result = generator.generate(kind="poem", topic=prompt or "poem", tone="neutral", length=length)
        ika_text = (result.get("text") or "").strip()
        meta = result.get("meta", {}) or {}
        trace = _extract_trace_from_meta(meta)
        english_meaning = _english_meaning_for_ika_output(
            ika_text, source_text=prompt, mode="generate_poem"
        )
        return _make_response(ika_text=ika_text, english_meaning=english_meaning, legacy_meta=meta, trace=trace)
    except Exception as e:
        logger.error("Generate poem error: %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")


@app.post("/generate-lecture", response_model=ApiResponse)
async def generate_lecture(
    request: StoryIn,
    _claims: Dict[str, Any] = Depends(verify_token),
):
    """Generate Ika lecture (dataset when available, else rule-based)."""
    if store is None and generator is None:
        raise HTTPException(status_code=503, detail="Generation unavailable (backend not fully initialized)")

    prompt = (request.prompt or "").strip()
    length = (request.length or "short").strip().lower()

    if store is not None and dataset_generate_lecture is not None:
        try:
            ika_text = dataset_generate_lecture(store, length)
            english_meaning = _english_meaning_for_ika_output(
                ika_text, source_text=prompt, mode="generate_lecture"
            )
            return _make_response(
                ika_text=ika_text,
                english_meaning=english_meaning,
                legacy_meta={"source": "dataset", "length": length},
                trace={"source": "dataset", "length": length},
            )
        except Exception as e:
            logger.error("Dataset generate lecture error: %s", str(e), exc_info=True)
            raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")

    try:
        result = generator.generate(kind="lecture", topic=prompt or "lecture", tone="neutral", length=length)
        ika_text = (result.get("text") or "").strip()
        meta = result.get("meta", {}) or {}
        trace = _extract_trace_from_meta(meta)
        english_meaning = _english_meaning_for_ika_output(
            ika_text, source_text=prompt, mode="generate_lecture"
        )
        return _make_response(ika_text=ika_text, english_meaning=english_meaning, legacy_meta=meta, trace=trace)
    except Exception as e:
        logger.error("Generate lecture error: %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")


@app.post("/naturalize", response_model=ApiResponse)
async def naturalize(
    request: NaturalizeIn,
    _claims: Dict[str, Any] = Depends(verify_token),
):
    """
    Naturalize: "Say it like an Ika person."
    Returns new contract (ika_text + english_meaning).
    """
    if store is None or dataset_naturalize is None:
        raise HTTPException(status_code=503, detail="Dataset not loaded; naturalize unavailable")
    try:
        ika_text, en_back, notes = dataset_naturalize(
            store,
            intent_text=request.intent_text.strip(),
            tone=request.tone or "polite",
            length=request.length or "short",
        )
        # Here, english meaning is what dataset already provides as backtranslation
        return _make_response(
            ika_text=ika_text,
            english_meaning=en_back,
            legacy_meta={"notes": notes},
            trace={"notes": notes},
        )
    except Exception as e:
        logger.error("Naturalize error: %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Naturalize failed: {str(e)}")


@app.post("/generate-audio", response_model=GenerateAudioResponse)
async def generate_audio(
    request: GenerateAudioRequest,
    _claims: Dict[str, Any] = Depends(verify_token),
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
        logger.error("Audio generation error: %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Audio generation failed: {str(e)}")


@app.get("/audio/{filename}")
async def serve_audio(filename: str):
    """
    Serve cached audio file. No auth required so the app can download by URL.
    """
    path = local_audio_get_file_path(filename)
    if path is None:
        raise HTTPException(status_code=404, detail="Audio file not found")
    return FileResponse(
        path,
        media_type="audio/mpeg",
        headers={"Cache-Control": "public, max-age=31536000, immutable"},
    )


@app.get("/dictionary", response_model=DictionaryResponse)
async def dictionary_lookup(
    q: str = Query("", description="English word or prefix; empty = return all entries"),
    limit: int = Query(700, ge=1, le=1000, description="Max entries"),
    _claims: Dict[str, Any] = Depends(verify_token),
):
    """
    Dictionary lookup.
    NOTE: To fully support original audios, your lexicon repo must store audio_id/audio_url fields.
    """
    if lexicon_repo is None:
        raise HTTPException(status_code=503, detail="Dictionary unavailable (Firestore not connected)")

    try:
        query = (q or "").strip()
        if not query:
            entries = lexicon_repo.get_all()[:limit]
        else:
            entries = lexicon_repo.search_by_source_prefix(prefix=query, limit=min(limit, 200))

        out = []
        for e in entries:
            out.append(
                DictionaryEntry(
                    source_text=e.get("source_text", ""),
                    target_text=e.get("target_text", ""),
                    pos=e.get("pos"),
                    domain=e.get("domain"),
                    doc_id=e.get("doc_id"),
                    audio_id=e.get("audio_id"),
                    audio_url=e.get("audio_url"),
                )
            )

        return DictionaryResponse(entries=out)
    except Exception as e:
        logger.error("Dictionary lookup error: %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Dictionary lookup failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)