"""
API routes: /api/translate, /api/audio, /api/generate, /api/review
Uses LexiconService (local JSON only) for translation and audio lookup.
"""
import json
import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List

import httpx
from fastapi import APIRouter, HTTPException, Query, Request, Depends
from fastapi.responses import Response, StreamingResponse

from .lexicon_service import LexiconService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["api"])

# --- Dependency: LexiconService from app state ---
def get_lexicon_service(request: Request) -> LexiconService:
    svc = getattr(request.app.state, "lexicon_service", None)
    if svc is None:
        raise HTTPException(status_code=503, detail="Lexicon service not loaded (missing exports)")
    return svc


# --- Translation (local JSON only) ---
@router.get("/translate/en-ika")
async def translate_en_ika(
    q: str = Query(..., min_length=1),
    lexicon: LexiconService = Depends(get_lexicon_service),
):
    """
    English -> Ika lookup using exact_en_lookup.json only.
    Returns candidates with id, domain, audio_url, or not_found with suggestions.
    """
    result = lexicon.lookup_en_to_ika(q)
    return result


@router.get("/translate/ika-en")
async def translate_ika_en(
    q: str = Query(..., min_length=1),
    lexicon: LexiconService = Depends(get_lexicon_service),
):
    """Ika -> English lookup using ika_to_en.json."""
    result = lexicon.lookup_ika_to_en(q)
    return result


@router.get("/dictionary")
async def list_dictionary(
    lexicon: LexiconService = Depends(get_lexicon_service),
    domain: Optional[str] = Query(None, description="Filter by domain"),
    limit: int = Query(500, ge=1, le=2000),
):
    """List lexicon entries (for Show all). Optional domain filter, alphabetical."""
    entries = lexicon.list_en_keys(domain=domain, limit=limit)
    return {"entries": entries}


# --- Audio: proxy with correct headers ---
@router.get("/audio/health")
async def audio_health():
    """Simple health check for audio service."""
    return {"ok": True}


@router.get("/audio")
async def get_audio(
    request: Request,
    id: str = Query(..., alias="id", description="Lexicon entry id"),
):
    """
    Stream/proxy audio for lexicon entry.
    Uses audio_url from lexicon when available.
    Content-Type: audio/mp4, Content-Disposition: attachment; filename="<id>.m4a"
    """
    lexicon = getattr(request.app.state, "lexicon_service", None)
    if not lexicon:
        raise HTTPException(status_code=503, detail="Lexicon service not loaded")
    audio_url = lexicon.get_audio_url(id)
    if not audio_url:
        raise HTTPException(status_code=404, detail=f"No audio URL for lexicon id: {id}")

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.get(audio_url)
            resp.raise_for_status()
            content = resp.content
        except Exception as e:
            logger.warning("Audio fetch failed for id=%s: %s", id, e)
            raise HTTPException(status_code=502, detail="Failed to fetch audio from storage") from e

    return Response(
        content=content,
        media_type="audio/mp4",
        headers={
            "Content-Disposition": f'attachment; filename="{id}.m4a"',
            "Cache-Control": "public, max-age=86400",
        },
    )


# --- Generate: uses app.state.generator ---
class ApiGenerateBody:
    def __init__(self, mode: str, topic: str, length: str = "medium", input_lang: str = "en"):
        self.mode = mode
        self.topic = topic
        self.length = length
        self.input_lang = input_lang


@router.post("/generate")
async def api_generate(
    request: Request,
    body: dict = None,
):
    """
    Generate Ika text: story|poem|lecture|sentence.
    Uses grammar templates + lexicon only; returns only Ika tokens from dataset.
    Body: { "mode": "story|poem|lecture|sentence", "topic": "...", "length": "short|medium|long", "input_lang": "en|ika" }
    """
    if not body:
        raise HTTPException(status_code=400, detail="JSON body required")
    mode = (body.get("mode") or "sentence").strip().lower()
    topic = (body.get("topic") or "").strip()
    length = (body.get("length") or "medium").strip().lower()
    input_lang = (body.get("input_lang") or "en").strip().lower()

    if mode not in ("story", "poem", "lecture", "sentence"):
        raise HTTPException(status_code=400, detail="mode must be story, poem, lecture, or sentence")
    if not topic:
        raise HTTPException(status_code=400, detail="topic required")

    generator = getattr(request.app.state, "generator", None)
    if not generator:
        raise HTTPException(status_code=503, detail="Generator not available")

    try:
        if mode == "sentence":
            # Single sentence: use translation of topic phrase
            result = generator.translate(text=topic, tense="present", mode="rule_based")
            text = result.get("text", "")
            meta = result.get("meta", {})
            used_sources = {e.get("source", "").lower() for e in meta.get("lexicon_entries", [])}
            missing = [w for w in topic.split() if w.lower() not in used_sources]
        else:
            result = generator.generate(kind=mode, topic=topic, tone="neutral", length=length)
            text = result.get("text", "")
            meta = result.get("meta", {})
            missing = []

        return {
            "text": text,
            "meta": {**meta, "mode": mode, "length": length, "input_lang": input_lang},
            "missing_concepts": missing if missing else None,
        }
    except Exception as e:
        logger.exception("api_generate failed")
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}") from e


# --- Review workflow ---
def _reviews_dir(request: Request) -> Path:
    base = Path(__file__).parent.parent / "data"
    reviews = base / "reviews"
    reviews.mkdir(parents=True, exist_ok=True)
    return reviews


@router.get("/review/uncertain")
async def get_review_uncertain(request: Request):
    """Return list from uncertain_sentences.json."""
    path = Path(__file__).parent.parent / "data" / "exports" / "uncertain_sentences.json"
    if not path.exists():
        return {"items": []}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {"items": data}
    except Exception as e:
        logger.warning("get_review_uncertain: %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/review/uncertain")
async def post_review_uncertain(request: Request, body: dict = None):
    """
    Append decision to review_decisions.json.
    Body: { "id": "...", "action": "keep"|"delete", "note": "..." }
    """
    if not body or "id" not in body or "action" not in body:
        raise HTTPException(status_code=400, detail="id and action required")
    action = (body.get("action") or "").strip().lower()
    if action not in ("keep", "delete"):
        raise HTTPException(status_code=400, detail="action must be keep or delete")

    decisions_path = _reviews_dir(request) / "review_decisions.json"
    decisions: List[Dict] = []
    if decisions_path.exists():
        try:
            with open(decisions_path, "r", encoding="utf-8") as f:
                decisions = json.load(f)
        except Exception:
            pass
    decisions.append({
        "id": body.get("id"),
        "action": action,
        "note": (body.get("note") or "").strip(),
    })
    with open(decisions_path, "w", encoding="utf-8") as f:
        json.dump(decisions, f, indent=2, ensure_ascii=False)
    return {"ok": True, "saved": "review_decisions.json"}


@router.get("/review/pos")
async def get_review_pos(request: Request):
    """Return list from pos_review.json."""
    path = Path(__file__).parent.parent / "data" / "exports" / "pos_review.json"
    if not path.exists():
        return {"items": []}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {"items": data}
    except Exception as e:
        logger.warning("get_review_pos: %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/review/pos")
async def post_review_pos(request: Request, body: dict = None):
    """
    Record verified POS for an entry; append to pos_verified and update pos_review_done / pos_final.
    Body: { "id": "...", "ika_word": "...", "pos": "noun|verb|adjective|...", "notes": "..." }
    """
    if not body or "id" not in body:
        raise HTTPException(status_code=400, detail="id required")
    rev_dir = _reviews_dir(request)
    pos_verified_path = rev_dir / "pos_verified.json"
    pos_done_path = rev_dir / "pos_review_done.json"
    pos_final_path = rev_dir / "pos_final.json"

    verified: List[Dict] = []
    if pos_verified_path.exists():
        try:
            with open(pos_verified_path, "r", encoding="utf-8") as f:
                verified = json.load(f)
        except Exception:
            pass
    entry = {
        "id": body.get("id"),
        "ika_word": body.get("ika_word") or body.get("target_text", ""),
        "pos": (body.get("pos") or "").strip(),
        "notes": (body.get("notes") or "").strip(),
    }
    verified.append(entry)
    with open(pos_verified_path, "w", encoding="utf-8") as f:
        json.dump(verified, f, indent=2, ensure_ascii=False)

    # pos_final: ika_word -> POS
    pos_final: Dict[str, str] = {}
    if pos_final_path.exists():
        try:
            with open(pos_final_path, "r", encoding="utf-8") as f:
                pos_final = json.load(f)
        except Exception:
            pass
    if entry.get("ika_word") and entry.get("pos"):
        pos_final[entry["ika_word"]] = entry["pos"]
    with open(pos_final_path, "w", encoding="utf-8") as f:
        json.dump(pos_final, f, indent=2, ensure_ascii=False)

    return {"ok": True, "saved": ["pos_verified.json", "pos_final.json"]}
