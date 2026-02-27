from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Dict, List, Optional, Tuple

WORD_RE = re.compile(r"[a-z]+(?:'[a-z]+)?", re.IGNORECASE)


def tokenize_en(text: str) -> List[str]:
    if not text:
        return []
    text = text.lower().replace("’", "'")
    return [m.group(0).lower() for m in WORD_RE.finditer(text)]


@dataclass(frozen=True)
class PhraseItem:
    id: str
    english: str
    ika: str
    tags: List[str]


@dataclass(frozen=True)
class PhraseMatch:
    id: str
    english: str
    ika: str
    start: int
    end: int
    tags: List[str]


class _TrieNode:
    __slots__ = ("children", "items")

    def __init__(self) -> None:
        self.children: Dict[str, _TrieNode] = {}
        self.items: List[PhraseItem] = []


class PhraseBank:
    """
    Verified-only phrase matcher.
    Longest-match with left-to-right greedy scan.
    """

    def __init__(self, items: List[PhraseItem]) -> None:
        self._root = _TrieNode()
        self._items = items
        self._build_trie(items)

    @staticmethod
    def load(path: str) -> "PhraseBank":
        with open(path, "r", encoding="utf-8") as f:
            obj = json.load(f)

        raw_items = obj.get("items", [])
        items: List[PhraseItem] = []
        for it in raw_items:
            if (it.get("status") or "").lower() != "verified":
                continue

            eng = (it.get("english") or "").strip()
            if not eng:
                continue

            items.append(
                PhraseItem(
                    id=str(it.get("id") or ""),
                    english=eng,
                    ika=(it.get("ika") or "").strip(),
                    tags=list(it.get("tags") or []),
                )
            )

        # longer phrases first helps with determinism
        items.sort(key=lambda x: len(tokenize_en(x.english)), reverse=True)
        return PhraseBank(items)

    def _build_trie(self, items: List[PhraseItem]) -> None:
        for item in items:
            toks = tokenize_en(item.english)
            if not toks:
                continue
            node = self._root
            for t in toks:
                node = node.children.setdefault(t, _TrieNode())
            node.items.append(item)

    def find_longest_at(self, tokens: List[str], i: int) -> Optional[Tuple[PhraseItem, int]]:
        node = self._root
        best: Optional[PhraseItem] = None
        best_end = i

        j = i
        while j < len(tokens):
            t = tokens[j]
            if t not in node.children:
                break
            node = node.children[t]
            if node.items:
                # because we sorted items by length, first is deterministic
                best = node.items[0]
                best_end = j + 1
            j += 1

        if best is None:
            return None
        return best, best_end

    def chunk(self, english_text: str) -> Tuple[List[str], List[PhraseMatch]]:
        tokens = tokenize_en(english_text)
        matches: List[PhraseMatch] = []
        ika_out: List[str] = []

        i = 0
        while i < len(tokens):
            found = self.find_longest_at(tokens, i)
            if not found:
                i += 1
                continue

            item, end = found
            matches.append(
                PhraseMatch(
                    id=item.id,
                    english=item.english,
                    ika=item.ika,
                    start=i,
                    end=end,
                    tags=item.tags,
                )
            )

            # emit only if ika is non-empty (some phrases are "silent")
            if item.ika:
                ika_out.append(item.ika)

            i = end

        return ika_out, matches


def load_default_phrasebank() -> PhraseBank:
    path = os.environ.get("PHRASEBANK_PATH", "./exports/pattern_study/phrasebank.json")
    return PhraseBank.load(path)


@lru_cache(maxsize=1)
def load_phrasebank() -> PhraseBank:
    # cached alias
    return load_default_phrasebank()


@lru_cache(maxsize=1)
def _ika_to_en_map() -> Dict[str, str]:
    pb = load_phrasebank()
    m: Dict[str, str] = {}
    for it in pb._items:
        ika = (it.ika or "").strip().lower()
        en = (it.english or "").strip()
        if ika and en:
            m[ika] = en
    return m


def phrasebank_ika_to_en(text_ika: str) -> Optional[str]:
    """Exact Ika->English lookup (single phrase only)."""
    key = " ".join((text_ika or "").strip().lower().split())
    if not key:
        return None
    return _ika_to_en_map().get(key)


def phrasebank_ika_to_en_fuzzy(text_ika: str) -> Optional[str]:
    """
    Best-effort Ika->English for phrasebank outputs.

    Handles multi-chunk phrasebank outputs like: "jẹn afịa"
    by splitting and mapping each chunk, then joining the English parts.
    """
    if not text_ika:
        return None

    s = " ".join((text_ika or "").strip().lower().split())
    if not s:
        return None

    # 1) exact match first
    exact = _ika_to_en_map().get(s)
    if exact:
        return exact

    # 2) try chunk-by-chunk (space separated)
    parts = s.split()
    mapped: List[str] = []
    for p in parts:
        en = _ika_to_en_map().get(p)
        if en:
            mapped.append(en)

    if mapped:
        return " ".join(mapped)

    return None