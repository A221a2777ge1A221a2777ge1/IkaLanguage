import os
import re
from collections import Counter

import firebase_admin
from firebase_admin import credentials, firestore

PROJECT_ID = os.getenv("PROJECT_ID", "ikause")
DICTIONARY_COLLECTION = os.getenv("DICTIONARY_COLLECTION", "words")
DRY_RUN = os.getenv("DRY_RUN", "1") == "1"   # 1 = no writes
ENGLISH_FIELD = os.getenv("ENGLISH_FIELD", "word")  # <-- IMPORTANT: your schema uses "word"
POS_FIELD = os.getenv("POS_FIELD", "pos")

import nltk
from nltk import pos_tag
nltk.download("averaged_perceptron_tagger_eng", quiet=True)

def normalize_pos(english_word: str) -> str:
    w = (english_word or "").strip().lower()
    if not w:
        return "unknown"

    tokens = re.findall(r"[A-Za-z']+", w)
    if not tokens:
        return "unknown"

    tag = pos_tag([tokens[0]])[0][1]  # NN, VB, JJ, PRP, ...

    if tag.startswith("NN"): return "noun"
    if tag.startswith("VB"): return "verb"
    if tag.startswith("JJ"): return "adjective"
    if tag.startswith("RB"): return "adverb"
    if tag in ("PRP", "PRP$"): return "pronoun"
    if tag == "IN": return "preposition"
    if tag == "DT": return "determiner"
    if tag == "CC": return "conjunction"
    if tag == "UH": return "interjection"
    if tag == "CD": return "number"
    return "other"

def main():
    if not firebase_admin._apps:
        firebase_admin.initialize_app(credentials.ApplicationDefault(), {"projectId": PROJECT_ID})
    db = firestore.client()
    col = db.collection(DICTIONARY_COLLECTION)

    docs = list(col.stream())
    print(f"Project: {PROJECT_ID}")
    print(f"Collection: {DICTIONARY_COLLECTION}")
    print(f"DRY_RUN: {DRY_RUN}")
    print(f"ENGLISH_FIELD: {ENGLISH_FIELD}")
    print(f"Docs found: {len(docs)}")

    pos_counts = Counter()
    skipped_has_pos = 0
    skipped_missing_english = 0
    will_update = 0

    batch = db.batch()
    batch_size = 0

    for d in docs:
        data = d.to_dict() or {}

        english = data.get(ENGLISH_FIELD)

        if not english:
            skipped_missing_english += 1
            continue

        if data.get(POS_FIELD):
            pos_counts[str(data[POS_FIELD])] += 1
            skipped_has_pos += 1
            continue

        pos_value = normalize_pos(str(english))
        pos_counts[pos_value] += 1
        will_update += 1

        if DRY_RUN:
            continue

        batch.set(d.reference, {POS_FIELD: pos_value}, merge=True)
        batch_size += 1

        if batch_size >= 450:
            batch.commit()
            batch = db.batch()
            batch_size = 0

    if not DRY_RUN and batch_size > 0:
        batch.commit()

    print("\nSummary:")
    print("Will update:" if DRY_RUN else "Updated:", will_update)
    print("Skipped (already has pos):", skipped_has_pos)
    print("Skipped (missing english field):", skipped_missing_english)
    print("POS distribution:", dict(pos_counts))

    if DRY_RUN:
        print("\nNothing written. Set DRY_RUN=0 to apply changes.")

if __name__ == "__main__":
    main()