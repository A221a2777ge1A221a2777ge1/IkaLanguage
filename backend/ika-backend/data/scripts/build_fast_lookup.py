import json, re, os
from collections import defaultdict

def norm(s: str) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"[“”\"'`]", "", s)
    s = re.sub(r"[^\w\u00C0-\u024F\u1E00-\u1EFF\s\?\!\.\,\-]", "", s)
    return s.strip()

lexicon_path = "backend/ika-backend/data/exports/lexicon.json"
lexicon = json.load(open(lexicon_path, "r", encoding="utf-8"))

exact = defaultdict(list)
for e in lexicon:
    en = norm(e.get("source_text", ""))
    ika = (e.get("target_text") or "").strip()
    if not en or not ika:
        continue
    exact[en].append({
        "id": str(e.get("id","")),
        "domain": e.get("domain",""),
        "ika": ika,
        "audio_url": e.get("audio_url",""),
        "target_lang": e.get("target_lang","ika_ng"),
        "source_lang": e.get("source_lang","en")
    })

out_dir = "backend/ika-backend/data/exports/indexes"
os.makedirs(out_dir, exist_ok=True)
out_path = os.path.join(out_dir, "exact_en_lookup.json")
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(exact, f, ensure_ascii=False, indent=2)

print("Wrote", out_path, "keys:", len(exact))
