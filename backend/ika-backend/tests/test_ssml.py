"""
Unit tests for text_to_ssml and related SSML helpers.
"""
import pytest
import sys
from pathlib import Path

# Ensure app is importable
_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_root))

from app.tts.ssml import (
    tokenize_words,
    word_to_ipa,
    text_to_ssml,
    text_to_ssml_with_phonemes,
    _escape_ssml,
)


def test_escape_ssml():
    assert _escape_ssml("a & b") == "a &amp; b"
    assert _escape_ssml("x < y") == "x &lt; y"
    assert _escape_ssml('say "hi"') == "say &quot;hi&quot;"


def test_tokenize_words():
    assert tokenize_words("hello world") == ["hello", " ", "world"]
    assert tokenize_words("  ") == []
    tokens = tokenize_words("biko, nde.")
    assert "biko" in tokens
    assert "nde" in tokens


def test_word_to_ipa_with_dict():
    d = {"hello": "hɛloʊ", "water": "wɔːtər"}
    assert word_to_ipa("hello", d) == "hɛloʊ"
    assert word_to_ipa("HELLO", d) == "hɛloʊ"
    assert word_to_ipa("water", d) == "wɔːtər"
    assert word_to_ipa("unknown", d) is None or word_to_ipa("unknown", d) == "unknown"  # fallback


def test_text_to_ssml_contains_speak():
    d = {"hello": "hɛloʊ"}
    out = text_to_ssml_with_phonemes("hello", d)
    assert out.startswith("<speak>")
    assert out.endswith("</speak>")


def test_text_to_ssml_contains_phoneme_for_known_word():
    d = {"hello": "hɛloʊ", "water": "wɔːtər"}
    out = text_to_ssml_with_phonemes("hello water", d)
    assert '<phoneme alphabet="ipa"' in out
    assert "hɛloʊ" in out or "ph=" in out
    assert "hello" in out
    assert "water" in out


def test_text_to_ssml_unknown_word_unchanged():
    d = {"hello": "hɛloʊ"}
    out = text_to_ssml_with_phonemes("hello xyz", d)
    assert "<speak>" in out
    assert "xyz" in out
    # hello should be in phoneme; xyz as plain text
    assert out.count("<phoneme") >= 1


def test_text_to_ssml_escaping():
    d = {}
    out = text_to_ssml_with_phonemes("a & b", d)
    assert "&amp;" in out
    assert "<speak>" in out
