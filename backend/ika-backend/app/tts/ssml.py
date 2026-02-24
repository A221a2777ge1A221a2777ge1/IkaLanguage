"""
SSML helpers for TTS with IPA phonemes.
"""
import re
import json
import os
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Module-level cache for IPA dictionary
_ipa_dict_cache: Optional[Dict[str, str]] = None


def tokenize_words(text: str) -> List[str]:
    """
    Split text into words and punctuation tokens.
    Keeps punctuation as separators so we can preserve spaces when rebuilding SSML.
    """
    if not text or not text.strip():
        return []
    # Split on word boundaries: keep sequences of letters/numbers/unicode letters
    pattern = re.compile(r"(\s+|[^\w\s]|\w+)")
    tokens = pattern.findall(text)
    return [t for t in tokens if t]


def word_to_ipa(word: str, ipa_dict: Dict[str, str]) -> Optional[str]:
    """
    Look up IPA for a word (lowercase). Return None if not found.
    """
    key = word.lower().strip()
    return ipa_dict.get(key)


def text_to_ssml_with_phonemes(text: str, ipa_dict: Dict[str, str]) -> str:
    """
    Build SSML with <phoneme alphabet="ipa" ph="..."> for known words.
    Unknown words are included as raw text. Spaces are preserved.
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
            parts.append(t)
            continue
        ipa = word_to_ipa(t, ipa_dict)
        if ipa:
            # Escape XML in IPA: & < >
            ipa_esc = ipa.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            word_esc = t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            parts.append(f'<phoneme alphabet="ipa" ph="{ipa_esc}">{word_esc}</phoneme>')
        else:
            word_esc = t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            parts.append(word_esc)
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
