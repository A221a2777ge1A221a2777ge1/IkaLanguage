import json

flagged = json.load(open("exports/lexicon_flagged.json","r",encoding="utf-8"))
unc = [e for e in flagged if e.get("_igbo_label") == "uncertain"]
json.dump(unc, open("exports/uncertain_sentences.json","w",encoding="utf-8"), ensure_ascii=False, indent=2)
print("Wrote exports/uncertain_sentences.json:", len(unc))
