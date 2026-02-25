import json, re

lexicon = json.load(open("exports/lexicon.json","r",encoding="utf-8"))

rows = []
for e in lexicon:
    ika = (e.get("target_text") or "").strip()
    en  = (e.get("source_text") or "").strip()
    dom = e.get("domain")
    # focus on single words / short phrases
    if len(re.split(r"\s+", ika)) <= 2:
        rows.append({
            "id": str(e.get("id","")),
            "source_text": en,
            "target_text": ika,
            "domain": dom,
            "pos_verified": "",
            "notes": ""
        })

json.dump(rows, open("exports/pos_review.json","w",encoding="utf-8"), ensure_ascii=False, indent=2)
print("Wrote exports/pos_review.json rows:", len(rows))
