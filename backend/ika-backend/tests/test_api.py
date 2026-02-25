"""
Unit tests for /api translation lookup and LexiconService.
(Audio endpoint header behavior can be verified manually or via integration test with running server.)
"""
import pytest
import sys
from pathlib import Path

_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_root))


def test_lexicon_service_exact_match():
    """LexiconService.lookup_en_to_ika returns found and candidates for exact match."""
    from app.lexicon_service import LexiconService
    exports_dir = _root / "data" / "exports"
    exact_path = exports_dir / "indexes" / "exact_en_lookup.json"
    if not exact_path.exists():
        pytest.skip("exports/indexes/exact_en_lookup.json not present")
    svc = LexiconService(exports_dir)
    svc.load()
    result = svc.lookup_en_to_ika("hello")
    assert result["found"] is True
    assert "candidates" in result
    assert len(result["candidates"]) >= 1
    assert result["candidates"][0].get("ika") is not None
    assert result["candidates"][0].get("id") is not None
    assert result["query"] == "hello"


def test_lexicon_service_normalize():
    """Query is normalized (lowercase, collapse spaces)."""
    from app.lexicon_service import LexiconService
    exports_dir = _root / "data" / "exports"
    exact_path = exports_dir / "indexes" / "exact_en_lookup.json"
    if not exact_path.exists():
        pytest.skip("exports not present")
    svc = LexiconService(exports_dir)
    svc.load()
    result = svc.lookup_en_to_ika("  HELLO  ")
    assert result["query"] == "hello"


def test_lexicon_service_not_found_returns_suggestions():
    """When no exact match, returns found=False and suggestions list."""
    from app.lexicon_service import LexiconService
    exports_dir = _root / "data" / "exports"
    exact_path = exports_dir / "indexes" / "exact_en_lookup.json"
    if not exact_path.exists():
        pytest.skip("exports not present")
    svc = LexiconService(exports_dir)
    svc.load()
    result = svc.lookup_en_to_ika("xyznonexistent")
    assert result["found"] is False
    assert "suggestions" in result


def test_lexicon_service_ika_to_en():
    """Ika -> English lookup returns meanings when key exists."""
    from app.lexicon_service import LexiconService
    exports_dir = _root / "data" / "exports"
    ika_path = exports_dir / "indexes" / "ika_to_en.json"
    if not ika_path.exists():
        pytest.skip("ika_to_en.json not present")
    svc = LexiconService(exports_dir)
    svc.load()
    result = svc.lookup_ika_to_en("ya")
    assert "meanings" in result
    if result.get("found"):
        assert "hello" in result["meanings"] or any("hello" in str(m) for m in result["meanings"])


def test_lexicon_service_audio_url():
    """get_audio_url returns URL for known lexicon id."""
    from app.lexicon_service import LexiconService
    exports_dir = _root / "data" / "exports"
    exact_path = exports_dir / "indexes" / "exact_en_lookup.json"
    if not exact_path.exists():
        pytest.skip("exports not present")
    svc = LexiconService(exports_dir)
    svc.load()
    url = svc.get_audio_url("1")
    assert url is not None
    assert "audio" in url or "firebasestorage" in url or "m4a" in url
    assert svc.get_audio_url("999999") is None


def test_audio_health_route():
    """GET /api/audio/health returns ok."""
    import asyncio
    from app.api_routes import audio_health
    result = asyncio.run(audio_health())
    assert result == {"ok": True}
