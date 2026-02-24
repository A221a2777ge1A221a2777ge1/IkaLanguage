"""
LexiconStore - Load firestore_lexicon_export.json and build indexes for
domain, English→Ika, Ika→English, and Ika token set (for language detection).
"""
from __future__ import annotations
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import DefaultDict, List
from collections import defaultdict

TOKEN_RE = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿỊịỌọỤụẸẹŃńŊŋʼ''-]+", re.UNICODE)


@dataclass(frozen=True)
class LexEntry:
    domain: str
    en: str
    ika: str


class LexiconStore:
    def __init__(self, export_path: str):
        self.export_path = Path(export_path)
        self.entries: List[LexEntry] = []
        self.by_domain: DefaultDict[str, List[LexEntry]] = defaultdict(list)
        self.en_to_ika: DefaultDict[str, List[LexEntry]] = defaultdict(list)
        self.ika_to_en: DefaultDict[str, List[LexEntry]] = defaultdict(list)
        self.ika_token_set: set = set()

    def load(self) -> None:
        raw = json.loads(self.export_path.read_text(encoding="utf-8"))
        docs = raw.get("docs", [])

        entries: List[LexEntry] = []
        for d in docs:
            domain = (d.get("domain") or d.get("category") or "").strip()
            en = (d.get("source_text") or d.get("sourceText") or "").strip()
            ika = (d.get("target_text") or d.get("targetText") or "").strip()
            if not domain or not en or not ika:
                continue
            e = LexEntry(domain=domain, en=en, ika=ika)
            entries.append(e)

        self.entries = entries
        self.by_domain.clear()
        self.en_to_ika.clear()
        self.ika_to_en.clear()
        self.ika_token_set.clear()

        for e in entries:
            self.by_domain[e.domain].append(e)
            self.en_to_ika[e.en.lower()].append(e)
            self.ika_to_en[e.ika.lower()].append(e)
            for t in TOKEN_RE.findall(e.ika):
                self.ika_token_set.add(t.lower())

    def is_ika_text(self, text: str) -> bool:
        toks = [t.lower() for t in TOKEN_RE.findall(text)]
        if not toks:
            return False
        hit = sum(1 for t in toks if t in self.ika_token_set)
        return hit / max(1, len(toks)) >= 0.35


def get_store() -> LexiconStore:
    base = Path(__file__).resolve().parents[1]
    export = base / "data" / "firestore_lexicon_export.json"
    store = LexiconStore(str(export))
    store.load()
    return store
