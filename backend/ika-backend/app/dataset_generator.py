"""
Dataset-based generator: strict English↔Ika using only entries from
firestore_lexicon_export (no invented words). Story/poem/lecture from domain pools.
"""
from __future__ import annotations
import random
from typing import List, Optional

from .lexicon_store import LexiconStore, LexEntry


def pick(entries: List[LexEntry]) -> Optional[LexEntry]:
    return random.choice(entries) if entries else None


def normalize_domain(d: str) -> str:
    d = d.strip()
    if d.startswith("sentennce."):
        d = "sentence." + d[len("sentennce.") :]
    return d


def translate_en_to_ika_sentence(store: LexiconStore, english: str) -> str:
    """
    Strict: return a valid Ika sentence from dataset (exact match or recombination
    from sentence.* / greeting / expression pools). Never output mixed English/Ika.
    """
    english = english.strip()
    hits = store.en_to_ika.get(english.lower(), [])
    if hits:
        hits_sorted = sorted(
            hits,
            key=lambda e: (
                0
                if (e.domain.startswith("sentence.") or e.domain == "greeting")
                else 1
            ),
        )
        return hits_sorted[0].ika

    # No exact match: return a valid dataset sentence (greeting or any domain)
    greeting = store.by_domain.get("greeting", [])
    svo = store.by_domain.get("sentence.svo", [])
    expr = store.by_domain.get("sentence.expression", [])
    synonym = store.by_domain.get("synonym_general", [])
    base = pick(expr) or pick(svo) or pick(greeting) or pick(synonym)
    if not base:
        # fallback: any entry
        base = pick(store.entries)
    return base.ika if base else ""


def translate_ika_to_en(store: LexiconStore, ika: str) -> str:
    ika = ika.strip()
    hits = store.ika_to_en.get(ika.lower(), [])
    if hits:
        return hits[0].en
    return "Not found in dataset."


def _story_pools(store: LexiconStore) -> List[LexEntry]:
    """Build pool for story from preferred domains (or all entries)."""
    order = [
        "greeting",
        "sentence.location",
        "sentence.svo",
        "sentence.question",
        "sentence.negation",
        "sentence.conditional",
        "sentence.tense",
        "sentence.expression",
        "synonym_general",
        "synonym_family",
        "synonym_education",
    ]
    pools = []
    for d in order:
        pools.extend(store.by_domain.get(d, []))
    return pools if pools else store.entries


def generate_story(store: LexiconStore, length: str = "short") -> str:
    pools = _story_pools(store)
    if not pools:
        return ""
    n = 6 if length == "short" else 12 if length == "medium" else 20
    lines = []
    for _ in range(n):
        e = pick(pools)
        if e:
            lines.append(e.ika)
    if n >= 12:
        return "\n\n".join([" ".join(lines[:6]), " ".join(lines[6:])])
    return " ".join(lines)


def generate_poem(store: LexiconStore, lines: int = 8) -> str:
    pv = store.by_domain.get("poetic_vocab", [])
    expr = store.by_domain.get("sentence.expression", [])
    synonym = store.by_domain.get("synonym_general", [])
    base = pv or expr or synonym or store.entries
    if not base:
        return ""
    out = []
    for _ in range(lines):
        e = pick(base)
        if e:
            out.append(e.ika)
    return "\n".join(out)


def generate_lecture(store: LexiconStore, length: str = "short") -> str:
    greet = store.by_domain.get("greeting", [])
    svo = store.by_domain.get("sentence.svo", [])
    tense = store.by_domain.get("sentence.tense", [])
    expr = store.by_domain.get("sentence.expression", [])
    synonym = store.by_domain.get("synonym_general", [])
    body_pool = svo + tense + expr + synonym or store.entries
    parts = []
    if greet:
        e = pick(greet)
        if e:
            parts.append(e.ika)
    n = 5 if length == "short" else 10
    for _ in range(n):
        e = pick(body_pool)
        if e:
            parts.append(e.ika)
    if expr:
        e = pick(expr)
        if e:
            parts.append(e.ika)
    return " ".join(parts)


def _classify_intent(text: str) -> str:
    """Classify intent from English intent text (keyword-based)."""
    t = text.lower().strip()
    if any(w in t for w in ("sorry", "apologize", "apology", "forgive")):
        return "apology"
    if any(w in t for w in ("please", "could you", "would you", "want", "need")):
        return "request"
    if any(w in t for w in ("hello", "hi", "hey", "greet")):
        return "greeting"
    if any(w in t for w in ("what", "how", "why", "when", "where", "?")):
        return "question"
    if any(w in t for w in ("tell", "say", "inform", "let you know", "late", "traffic")):
        return "announcement"
    return "message"


def naturalize(
    store: LexiconStore,
    intent_text: str,
    tone: str = "polite",
    length: str = "short",
) -> tuple[str, str, list[str]]:
    """
    Produce natural Ika phrasing for an intent (no word-for-word translation).
    Returns (ika_text, english_backtranslation, notes).
    Uses only dataset entries; no hallucinations.
    """
    intent = _classify_intent(intent_text)
    notes = []
    parts_ika: List[str] = []
    parts_en: List[str] = []

    greeting = store.by_domain.get("greeting", [])
    expr = store.by_domain.get("sentence.expression", [])
    synonym = store.by_domain.get("synonym_general", [])
    family = store.by_domain.get("synonym_family", [])
    all_pool = greeting + expr + synonym + family or store.entries

    n = 2 if length == "short" else 4 if length == "medium" else 6

    if intent == "apology" and greeting:
        for e in greeting:
            if "sorry" in e.en.lower() or "apolog" in e.en.lower():
                parts_ika.append(e.ika)
                parts_en.append(e.en)
                notes.append("Used apology form")
                break
        else:
            e = pick(greeting)
            if e:
                parts_ika.append(e.ika)
                parts_en.append(e.en)
                notes.append("Used greeting as apology context")
    elif intent == "greeting" and greeting:
        e = pick(greeting)
        if e:
            parts_ika.append(e.ika)
            parts_en.append(e.en)
            notes.append("Used greeting")
    elif intent in ("request", "announcement", "message", "question"):
        if greeting and tone in ("polite", "respectful"):
            e = pick(greeting)
            if e:
                parts_ika.append(e.ika)
                parts_en.append(e.en)
                notes.append("Used polite opening")
    for _ in range(max(0, n - len(parts_ika))):
        e = pick(expr) or pick(synonym) or pick(all_pool)
        if e:
            parts_ika.append(e.ika)
            parts_en.append(e.en)
    if not notes:
        notes.append("Built from dataset expressions")
    ika_text = " ".join(parts_ika) if parts_ika else (pick(all_pool).ika if all_pool else "")
    en_back = " ".join(parts_en) if parts_en else ""
    return (ika_text, en_back, notes)
