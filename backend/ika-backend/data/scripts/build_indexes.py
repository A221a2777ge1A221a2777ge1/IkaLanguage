import json, os, re
from collections import defaultdict

def norm(s):
    return re.sub(r"\s+", " ", (s or "").strip().lower())

def main():
    lexicon = json.load(open("exports/lexicon.json", "r", encoding="utf-8"))
    words = json.load(open("exports/words.json", "r", encoding="utf-8"))

    ika_to_pos = {}
    word_to_entry = {}
    for w in words:
        ika = norm(w.get("word"))
        if ika:
            ika_to_pos[ika] = w.get("pos") or ""

    en_to_ika = defaultdict(list)
    ika_to_en = defaultdict(list)
    audio_by_lexicon_id = {}

    for e in lexicon:
        en = norm(e.get("source_text"))
        ika = norm(e.get("target_text"))
        if en and ika:
            en_to_ika[en].append(ika)
            ika_to_en[ika].append(en)
        if e.get("id") and e.get("audio_url"):
            audio_by_lexicon_id[str(e["id"])] = e["audio_url"]

    os.makedirs("exports/indexes", exist_ok=True)
    json.dump(dict(en_to_ika), open("exports/indexes/en_to_ika.json","w",encoding="utf-8"), ensure_ascii=False, indent=2)
    json.dump(dict(ika_to_en), open("exports/indexes/ika_to_en.json","w",encoding="utf-8"), ensure_ascii=False, indent=2)
    json.dump(ika_to_pos, open("exports/indexes/ika_to_pos.json","w",encoding="utf-8"), ensure_ascii=False, indent=2)
    json.dump(audio_by_lexicon_id, open("exports/indexes/audio_by_lexicon_id.json","w",encoding="utf-8"), ensure_ascii=False, indent=2)

    print("Built indexes in exports/indexes/")
    print(f"ika_to_pos size: {len(ika_to_pos)}")
    print(f"en_to_ika size: {len(en_to_ika)}")
    print(f"audio_by_lexicon_id size: {len(audio_by_lexicon_id)}")

if __name__ == "__main__":
    main()
