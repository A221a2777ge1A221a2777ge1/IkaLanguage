from __future__ import annotations

from typing import Dict, Tuple, Any
from app.nlp.phrasebank import load_default_phrasebank, tokenize_en
from app.nlp.phrasebank import phrasebank_ika_to_en

_PHRASEBANK = None

def get_phrasebank():
    global _PHRASEBANK
    if _PHRASEBANK is None:
        _PHRASEBANK = load_default_phrasebank()
    return _PHRASEBANK

def phrasebank_translate(en_text: str) -> Tuple[str, Dict[str, Any]]:
    pb = get_phrasebank()
    ika_chunks, matches = pb.chunk(en_text)

    debug = {
        "engine": "phrasebank",
        "tokens_en": tokenize_en(en_text),
        "matches": [
            {
                "id": m.id,
                "english": m.english,
                "ika": m.ika,
                "start": m.start,
                "end": m.end,
                "tags": m.tags,
            }
            for m in matches
        ],
        "ika_chunks": ika_chunks,
    }

    ika = " ".join([c for c in ika_chunks if c]).strip()
    return ika, debug
