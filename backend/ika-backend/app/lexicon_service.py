"""
LexiconService - Local JSON export-based translation and audio lookup.
Translation lookups use ONLY this local export data (no Firestore, no guessing).
"""
import json
import re
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

# Normalize: lowercase, collapse spaces, replace fancy quotes with ASCII
def _normalize(text: str) -> str:
    if not text or not isinstance(text, str):
        return ""
    t = text.strip().lower()
    t = re.sub(r"[\u201c\u201d\u2018\u2019\u2032\u2033]", "'", t)  # fancy quotes
    t = re.sub(r"\s+", " ", t)
    return t.strip()


def _token_overlap_score(query_tokens: set, key_tokens: set) -> int:
    """Number of query tokens that appear in key (for ranking suggestions)."""
    return len(query_tokens & key_tokens)


class LexiconService:
    """
    Loads exact_en_lookup.json, ika_to_en.json, and lexicon.json (for id->audio_url).
    All lookups are in-memory from these files only.
    """

    def __init__(self, exports_dir: Path):
        self.exports_dir = Path(exports_dir)
        self.indexes_dir = self.exports_dir / "indexes"
        self._exact_en: Dict[str, List[Dict]] = {}
        self._en_keys_sorted: List[str] = []
        self._ika_to_en: Dict[str, List[str]] = {}
        self._id_to_audio_url: Dict[str, str] = {}
        self._loaded = False

    def load(self) -> None:
        """Load exact_en_lookup, ika_to_en, and build id->audio_url from lexicon."""
        if self._loaded:
            return

        # exact_en_lookup.json: normalized EN -> list of {id, domain, ika, audio_url, ...}
        exact_path = self.indexes_dir / "exact_en_lookup.json"
        if not exact_path.exists():
            raise FileNotFoundError(f"Required index not found: {exact_path}")
        with open(exact_path, "r", encoding="utf-8") as f:
            self._exact_en = json.load(f)
        self._en_keys_sorted = sorted(self._exact_en.keys())

        # ika_to_en.json: Ika -> [English meanings]
        ika_path = self.indexes_dir / "ika_to_en.json"
        if ika_path.exists():
            with open(ika_path, "r", encoding="utf-8") as f:
                self._ika_to_en = json.load(f)
        else:
            self._ika_to_en = {}

        # id -> audio_url from lexicon.json (each doc has id and audio_url)
        lexicon_path = self.exports_dir / "lexicon.json"
        if lexicon_path.exists():
            with open(lexicon_path, "r", encoding="utf-8") as f:
                lexicon = json.load(f)
            for doc in lexicon:
                doc_id = doc.get("id") or doc.get("_doc_id")
                if doc_id is not None:
                    url = doc.get("audio_url")
                    if url:
                        self._id_to_audio_url[str(doc_id)] = url
            logger.info("LexiconService: loaded %d id->audio_url from lexicon.json", len(self._id_to_audio_url))
        else:
            # Fallback: build from exact_en_lookup candidates
            for candidates in self._exact_en.values():
                for c in candidates:
                    cid = c.get("id")
                    if cid is not None and c.get("audio_url"):
                        self._id_to_audio_url[str(cid)] = c["audio_url"]

        self._loaded = True
        logger.info(
            "LexiconService loaded: %d en keys, %d ika keys, %d audio urls",
            len(self._exact_en),
            len(self._ika_to_en),
            len(self._id_to_audio_url),
        )

    def lookup_en_to_ika(self, text: str) -> Dict[str, Any]:
        """
        Normalize text and look up in exact_en_lookup.
        Returns:
          - If exact match: {"found": True, "candidates": [...], "query": normalized}
          - If not found: {"found": False, "query": normalized, "suggestions": [...]}
          Suggestions: partial (contains/startswith) + up to 10 by token overlap.
        """
        self.load()
        norm = _normalize(text)
        if not norm:
            return {"found": False, "query": "", "candidates": [], "suggestions": []}

        if norm in self._exact_en:
            return {
                "found": True,
                "query": norm,
                "candidates": self._exact_en[norm],
                "suggestions": [],
            }

        # Suggestions: keys that contain query or start with query, plus token-overlap
        query_tokens = set(norm.split())
        partial = []
        for key in self._en_keys_sorted:
            if norm in key or key.startswith(norm) or norm.startswith(key):
                partial.append(key)
            if len(partial) >= 15:
                break

        overlap = []
        for key in self._en_keys_sorted:
            if key in partial:
                continue
            key_tokens = set(key.split())
            score = _token_overlap_score(query_tokens, key_tokens)
            if score > 0:
                overlap.append((score, key))
        overlap.sort(key=lambda x: (-x[0], x[1]))
        suggestion_keys = list(dict.fromkeys(partial + [k for _, k in overlap[:10]]))[:10]

        suggestions = []
        for k in suggestion_keys:
            for c in self._exact_en.get(k, [])[:1]:
                suggestions.append({"en": k, "ika": c.get("ika"), "id": c.get("id"), "domain": c.get("domain")})
                break

        return {
            "found": False,
            "query": norm,
            "candidates": [],
            "suggestions": suggestions,
        }

    def lookup_ika_to_en(self, ika_text: str) -> Dict[str, Any]:
        """
        Look up Ika phrase/word in ika_to_en.
        Normalize by stripping and lowercasing for key lookup; ika_to_en keys are ika strings.
        """
        self.load()
        norm = ika_text.strip()
        if not norm:
            return {"found": False, "query": norm, "meanings": []}

        # Exact key match (preserve original key for display)
        for key, meanings in self._ika_to_en.items():
            if key.strip().lower() == norm.lower():
                return {"found": True, "query": norm, "meanings": meanings, "ika_key": key}

        # Partial: keys that contain norm or that norm contains
        suggestions = []
        for key, meanings in self._ika_to_en.items():
            if norm.lower() in key.lower() or key.lower() in norm.lower():
                suggestions.append({"ika": key, "en": meanings})
        return {"found": False, "query": norm, "meanings": [], "suggestions": suggestions[:10]}

    def get_audio_url(self, lexicon_id: str) -> Optional[str]:
        """Return audio_url for lexicon id if available."""
        self.load()
        return self._id_to_audio_url.get(str(lexicon_id).strip())

    def list_en_keys(self, domain: Optional[str] = None, limit: int = 500) -> List[Dict[str, Any]]:
        """List entries for 'Show all' (alphabetical). If domain given, filter by domain."""
        self.load()
        out = []
        for key in self._en_keys_sorted:
            for c in self._exact_en.get(key, []):
                if domain and c.get("domain") != domain:
                    continue
                out.append({
                    "en": key,
                    "ika": c.get("ika"),
                    "id": c.get("id"),
                    "domain": c.get("domain"),
                    "audio_url": c.get("audio_url"),
                })
                if len(out) >= limit:
                    return out
        return out
