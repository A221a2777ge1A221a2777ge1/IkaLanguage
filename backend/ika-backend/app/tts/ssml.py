"""
SSML helpers for TTS with IPA phonemes.
Word → IPA via dictionary with optional fallback rules.
Text → SSML with <phoneme> tags and proper escaping.
"""
import re
import json
import os
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Module-level cache for IPA dictionary
_ipa_dict_cache: Optional[Dict[str, str]] = None

# Minimal grapheme→phoneme fallback for common Ika (when not in dictionary)
# Extend via ipa_dictionary.json; this is last resort so TTS doesn't skip the word
_FALLBACK_IPA: Dict[str, str] = {
    "a": "a", "e": "e", "i": "i", "o": "o", "u": "u",
    "n": "n", "m": "m", "b": "b", "k": "k", "d": "d", "g": "g",
    "ya": "ja", "nde": "nde", "biko": "biko",
}


def _escape_ssml(s: str) -> str:
    """Escape &, <, >, " for use inside SSML (content or attribute)."""
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def tokenize_words(text: str) -> List[str]:
    """
    Split text into words and punctuation tokens.
    Keeps punctuation as separators so we can preserve spaces when rebuilding SSML.
    """
    if not text or not text.strip():
        return []
    pattern = re.compile(r"(\s+|[^\w\s]|\w+)")
    tokens = pattern.findall(text)
    return [t for t in tokens if t]


def word_to_ipa(word: str, ipa_dict: Optional[Dict[str, str]] = None) -> Optional[str]:
    """
    Look up IPA for a word (lowercase).
    1. Uses ipa_dict if provided (or loaded IPA dictionary).
    2. Simple fallback rules for common Ika graphemes if not found.
    Returns None only if no mapping exists.
    """
    key = word.lower().strip()
    if not key:
        return None
    d = ipa_dict if ipa_dict is not None else load_ipa_dictionary()
    out = d.get(key)
    if out is not None:
        return out
    # Fallback: use small rule set (identity for single chars we know)
    return _FALLBACK_IPA.get(key)


def text_to_ssml(text: str, ipa_dict: Optional[Dict[str, str]] = None) -> str:
    """
    Build SSML with <speak>...</speak> and <phoneme alphabet="ipa" ph="..."> for known words.
    Unknown words left as normal text. Punctuation and spaces preserved.
    Escapes &, <, >, " properly.
    """
    if not text.strip():
        return "<speak></speak>"
    d = ipa_dict if ipa_dict is not None else load_ipa_dictionary()
    return text_to_ssml_with_phonemes(text, d)


def text_to_ssml_with_phonemes(text: str, ipa_dict: Dict[str, str]) -> str:
    """
    Build SSML with <phoneme alphabet="ipa" ph="..."> for known words.
    Unknown words are included as raw text. Spaces preserved. Escapes SSML properly.
    """
    if not text.strip():
        return "<speak></speak>"
    tokens = tokenize_words(text)
    parts: List[str] = []
    for t in tokens:
        if not t.strip():
            parts.append(t)
            continue
        if re.match(r"^\s+$", t):
            parts.append(t)
            continue
        if re.match(r"^[^\w]+$", t):
            parts.append(_escape_ssml(t))
            continue
        ipa = word_to_ipa(t, ipa_dict)
        if ipa:
            ipa_esc = _escape_ssml(ipa)
            word_esc = _escape_ssml(t)
            parts.append(f'<phoneme alphabet="ipa" ph="{ipa_esc}">{word_esc}</phoneme>')
        else:
            parts.append(_escape_ssml(t))
    body = "".join(parts)
    return f"<speak>{body}</speak>"


def load_ipa_dictionary(data_dir: Optional[str] = None) -> Dict[str, str]:
    """
    Load IPA dictionary from JSON. Cached at module level.
    Searches: data_dir/ipa_dictionary.json, then app/data, then ./data.
    """
    global _ipa_dict_cache
    if _ipa_dict_cache is not None:
        return _ipa_dict_cache

    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    candidates = [
        os.path.join(data_dir, "ipa_dictionary.json") if data_dir else None,
        os.path.join(base, "data", "ipa_dictionary.json"),
        os.path.join(os.getcwd(), "data", "ipa_dictionary.json"),
    ]
    for path in candidates:
        if path and os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    _ipa_dict_cache = json.load(f)
                logger.info("Loaded IPA dictionary from %s (%d entries)", path, len(_ipa_dict_cache))
                return _ipa_dict_cache
            except Exception as e:
                logger.warning("Failed to load IPA dict from %s: %s", path, e)

    logger.warning("No ipa_dictionary.json found; using empty dict")
    _ipa_dict_cache = {}
    return _ipa_dict_cache
