"""
LocalLexiconRepo - Lexicon repository backed by exported lexicon.json only.
Used by Generator when running with USE_LOCAL_LEXICON (no Firestore).
Implements the same interface as LexiconRepository for drop-in use.
"""
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class LocalLexiconRepo:
    """Read-only lexicon from data/exports/lexicon.json."""

    def __init__(self, exports_dir: Path):
        self.exports_dir = Path(exports_dir)
        self._docs: List[Dict] = []
        self._by_source: Dict[str, List[Dict]] = {}
        self._by_source_lower: Dict[str, List[Dict]] = {}
        self._loaded = False

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        path = self.exports_dir / "lexicon.json"
        if not path.exists():
            logger.warning("LocalLexiconRepo: lexicon.json not found at %s", path)
            self._loaded = True
            return
        with open(path, "r", encoding="utf-8") as f:
            self._docs = json.load(f)
        for doc in self._docs:
            d = dict(doc)
            d["doc_id"] = str(doc.get("id") or doc.get("_doc_id", ""))
            src = (doc.get("source_text") or "").strip()
            if src:
                self._by_source.setdefault(src, []).append(d)
                src_lower = src.lower()
                self._by_source_lower.setdefault(src_lower, []).append(d)
        self._loaded = True
        logger.info("LocalLexiconRepo: loaded %d entries from lexicon.json", len(self._docs))

    def find_by_source_text(self, source_text: str) -> Optional[Dict]:
        source_lower = (source_text or "").lower().strip()
        self._ensure_loaded()
        for key, entries in self._by_source_lower.items():
            if key == source_lower:
                return entries[0]
        return None

    def find_by_target_text(self, target_text: str) -> Optional[Dict]:
        target_lower = (target_text or "").lower().strip()
        self._ensure_loaded()
        for doc in self._docs:
            t = (doc.get("target_text") or "").lower().strip()
            if t == target_lower:
                d = dict(doc)
                d["doc_id"] = str(doc.get("id") or doc.get("_doc_id", ""))
                return d
        return None

    def find_by_pos(self, pos: str, domain: Optional[str] = None, limit: int = 10) -> List[Dict]:
        self._ensure_loaded()
        out = []
        for doc in self._docs:
            if doc.get("pos") != pos:
                continue
            if domain and doc.get("domain") != domain:
                continue
            d = dict(doc)
            d["doc_id"] = str(doc.get("id") or doc.get("_doc_id", ""))
            out.append(d)
            if len(out) >= limit:
                break
        return out

    def find_by_domain(self, domain: str, limit: int = 20) -> List[Dict]:
        self._ensure_loaded()
        out = []
        for doc in self._docs:
            if doc.get("domain") != domain:
                continue
            d = dict(doc)
            d["doc_id"] = str(doc.get("id") or doc.get("_doc_id", ""))
            out.append(d)
            if len(out) >= limit:
                break
        return out

    def get_all(self) -> List[Dict]:
        self._ensure_loaded()
        return [
            dict(doc, doc_id=str(doc.get("id") or doc.get("_doc_id", "")))
            for doc in self._docs
        ]

    def search_by_source_prefix(self, prefix: str, limit: int = 25) -> List[Dict]:
        prefix_lower = (prefix or "").lower().strip()
        if not prefix_lower:
            return []
        self._ensure_loaded()
        out = []
        for key, entries in self._by_source_lower.items():
            if key.startswith(prefix_lower):
                out.extend(entries)
                if len(out) >= limit:
                    return out[:limit]
        return out
